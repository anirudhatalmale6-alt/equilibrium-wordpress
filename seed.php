<?php
/**
 * Cree le contenu du site Equilibrium dans WordPress a partir de pages.json.
 *
 * Le script est IDEMPOTENT : relance-le autant de fois que tu veux, il met a
 * jour les pages existantes au lieu d'en creer des doubles. C'est ce qui
 * permet de corriger le gabarit et de resemer sans repartir d'une base vide.
 *
 * Usage : php seed.php /chemin/vers/wordpress /chemin/vers/pages.json
 */

if ( php_sapi_name() !== 'cli' ) { exit( 1 ); }

$racine = rtrim( $argv[1] ?? '', '/' );
$json   = $argv[2] ?? '';
if ( ! $racine || ! $json ) {
	fwrite( STDERR, "usage: seed.php <wordpress> <pages.json>\n" );
	exit( 1 );
}

require $racine . '/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/post.php';

/* En ligne de commande il n'y a pas d'utilisateur connecte, donc WordPress
   applique kses au contenu qu'on lui donne : il retire les <form>, les <input>
   et les attributs onsubmit des maquettes de formulaire. Les pages Join et
   Member sign-in perdraient leurs champs sans le moindre message. */
kses_remove_filters();

$donnees = json_decode( file_get_contents( $json ), true );
if ( ! $donnees ) { fwrite( STDERR, "pages.json illisible\n" ); exit( 1 ); }

/* ------------------------------------------------------------------ reglages */

switch_theme( 'equilibrium' );
update_option( 'blogname', 'Equilibrium' );
update_option( 'blogdescription', '' );
/* Poser l'option ne suffit pas : $wp_rewrite a deja lu l'ancienne valeur au
   chargement, et get_permalink() rendrait des URL en ?page_id= pendant tout ce
   script — c'est-a-dire exactement les URL qu'on ecrirait ensuite en base. */
global $wp_rewrite;
$wp_rewrite->set_permalink_structure( '/%postname%/' );
update_option( 'default_comment_status', 'closed' );
update_option( 'default_ping_status', 'closed' );
update_option( 'comment_registration', 1 );
update_option( 'blog_public', 0 );          // preproduction : le site part en noindex
update_option( 'timezone_string', '' );
update_option( 'gmt_offset', 0 );
update_option( 'start_of_week', 1 );

/* Le contenu par defaut de WordPress n'a rien a faire sur ce site. */
foreach ( get_posts( array(
	'post_type'   => array( 'post', 'page' ),
	'post_status' => 'any',
	'numberposts' => -1,
	'fields'      => 'ids',
) ) as $id_defaut ) {
	if ( ! get_post_meta( $id_defaut, '_eq_cle', true ) ) {
		wp_delete_post( $id_defaut, true );
	}
}
update_option( 'wp_page_for_privacy_policy', 0 );

/* --------------------------------------------------------------------- pages */

/** Retrouve une page par sa cle de chantier, jamais par son titre. */
function eq_page_par_cle( $cle ) {
	$q = get_posts( array(
		'post_type'   => 'page',
		'post_status' => 'any',
		'numberposts' => 2,
		'meta_key'    => '_eq_cle',
		'meta_value'  => $cle,
		'fields'      => 'ids',
	) );
	return $q ? (int) $q[0] : 0;
}

/** Decoupe le contenu en blocs « HTML personnalise », un par element. */
function eq_blocs( $html ) {
	$blocs = array();
	foreach ( preg_split( '/\r?\n/', $html ) as $ligne ) {
		$ligne = trim( $ligne );
		if ( '' === $ligne ) { continue; }
		$blocs[] = "<!-- wp:html -->\n" . $ligne . "\n<!-- /wp:html -->";
	}
	return implode( "\n\n", $blocs );
}

$racine_url = untrailingslashit( home_url() );
$ids = array();

foreach ( $donnees['pages'] as $page ) {
	$contenu = str_replace( '%%URL%%', $racine_url, $page['contenu'] );

	$champs = array(
		'post_type'      => 'page',
		'post_status'    => 'publish',
		'post_author'    => 1,
		'post_title'     => $page['titre'],
		'post_name'      => $page['slug'],
		'post_content'   => eq_blocs( $contenu ),
		'comment_status' => 'closed',
		'ping_status'    => 'closed',
	);

	$id = eq_page_par_cle( $page['cle'] );
	if ( $id ) {
		$champs['ID'] = $id;
		wp_update_post( $champs );
	} else {
		$id = wp_insert_post( $champs, true );
		if ( is_wp_error( $id ) ) {
			fwrite( STDERR, 'echec : ' . $page['cle'] . ' : ' . $id->get_error_message() . "\n" );
			exit( 1 );
		}
	}
	update_post_meta( $id, '_eq_cle', $page['cle'] );
	update_post_meta( $id, '_eq_nav', $page['nav'] );
	update_post_meta( $id, '_eq_title', $page['titre_doc'] );
	update_post_meta( $id, '_eq_desc', $page['description'] );
	$ids[ $page['cle'] ] = $id;
	echo sprintf( "page %-14s -> #%d  %s\n", $page['cle'], $id, get_permalink( $id ) );
}

/* La declaration est la page d'accueil du site. */
update_option( 'show_on_front', 'page' );
update_option( 'page_on_front', $ids['home'] );
update_option( 'page_for_posts', 0 );

/* --------------------------------------------------------------------- menus */

/**
 * Deux menus : la navigation principale et le pied de page.
 *
 * Chaque entree porte une classe « eq-nav-<cle> » : c'est elle, et non le rang
 * de l'entree, qui dit a quelle page appartient le marqueur de page courante.
 * L'entree qui ouvre la pratique porte en plus « eq-sep », qui fait dessiner le
 * separateur devant elle. Une classe suit l'entree si le menu est reordonne
 * dans l'administration ; un rang, non.
 *
 * « Statement » est un lien personnalise et pas une page : il mene a une ancre
 * de l'accueil, et WordPress ne sait pas ajouter d'ancre a une entree de type
 * page.
 */
$emplacements = array();
foreach ( array( 'principal' => 'menu_principal', 'pied' => 'menu_pied' ) as $ou => $cle ) {
	$nom = ( 'principal' === $ou ) ? 'Navigation principale' : 'Pied de page';

	$menu = wp_get_nav_menu_object( $nom );
	if ( $menu ) {
		foreach ( wp_get_nav_menu_items( $menu->term_id ) as $item ) {
			wp_delete_post( $item->ID, true );
		}
		$menu_id = $menu->term_id;
	} else {
		$menu_id = wp_create_nav_menu( $nom );
		if ( is_wp_error( $menu_id ) ) {
			fwrite( STDERR, 'menu : ' . $menu_id->get_error_message() . "\n" );
			exit( 1 );
		}
	}

	foreach ( $donnees[ $cle ] as $entree ) {
		$titre = '';
		foreach ( $donnees['pages'] as $p ) {
			if ( $p['cle'] === $entree['page'] ) { $titre = $p['menu']; break; }
		}
		$classes = 'eq-nav-' . $entree['cle'] . ( $entree['sep'] ? ' eq-sep' : '' );
		$commun  = array(
			'menu-item-title'   => $titre,
			'menu-item-classes' => $classes,
			'menu-item-status'  => 'publish',
		);
		if ( '' !== $entree['ancre'] ) {
			$args = $commun + array(
				'menu-item-type' => 'custom',
				'menu-item-url'  => trailingslashit( get_permalink( $ids[ $entree['page'] ] ) ) . $entree['ancre'],
			);
		} else {
			$args = $commun + array(
				'menu-item-object-id' => $ids[ $entree['page'] ],
				'menu-item-object'    => 'page',
				'menu-item-type'      => 'post_type',
			);
		}
		wp_update_nav_menu_item( $menu_id, 0, $args );
	}
	$emplacements[ $ou ] = $menu_id;
	echo sprintf( "menu %-10s -> #%d  (%d entrees)\n", $ou, $menu_id, count( $donnees[ $cle ] ) );
}
set_theme_mod( 'nav_menu_locations', $emplacements );

/* ----------------------------------------------------------------- nettoyage */

/* Les revisions gardent l'historique de MES essais, y compris des versions
   intermediaires fausses. Elles n'ont rien a faire dans la sauvegarde livree. */
$revisions = get_posts( array(
	'post_type'   => 'revision',
	'post_status' => 'any',
	'numberposts' => -1,
	'fields'      => 'ids',
) );
foreach ( $revisions as $r ) { wp_delete_post_revision( $r ); }
echo sprintf( "revisions supprimees : %d\n", count( $revisions ) );

/* Les transitoires sont des traces de MON environnement : verifications de
   mise a jour, listes d'extensions, caches. L'un d'eux nomme le pilote SQLite
   du site de developpement, que l'archive livree ne contient pas — et une
   sauvegarde qui parle d'un fichier absent est une sauvegarde qui ment. */
global $wpdb;
$noms = $wpdb->get_col( "SELECT option_name FROM {$wpdb->options}" );
$efface = 0;
foreach ( $noms as $o ) {
	if ( 0 === strpos( $o, '_transient_' ) || 0 === strpos( $o, '_site_transient_' ) ) {
		delete_option( $o );
		$efface++;
	}
}
/* Aucune extension n'est livree : l'import remplace tout le wp-content, et
   laisser une extension active dans la base ferait chercher a WordPress un
   fichier qui n'existera pas. */
update_option( 'active_plugins', array() );
delete_option( 'recently_activated' );
echo sprintf( "transitoires supprimes : %d\n", $efface );

flush_rewrite_rules( true );

echo "\ntheme actif : " . get_stylesheet() . "\n";
echo "accueil     : " . home_url( '/' ) . "\n";
echo "pages       : " . count( $ids ) . "\n";
