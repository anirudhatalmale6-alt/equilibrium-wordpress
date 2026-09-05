<?php
/**
 * Equilibrium — fonctions du theme.
 *
 * Regle de ce site, tenue ici comme dans la version statique : AUCUNE requete
 * ne quitte le domaine. Pas de police distante, pas de CDN, pas de mesure
 * d'audience, et aucun script. On retire donc aussi ce que WordPress ajoute de
 * lui-meme et qui sortirait du domaine ou chargerait la page sans servir.
 */

if ( ! defined( 'ABSPATH' ) ) { exit; }

define( 'EQ_VERSION', '1.0.0' );

/* ------------------------------------------------------------------ socle */

function eq_setup() {
	add_theme_support( 'title-tag' );
	add_theme_support( 'html5', array( 'style', 'script' ) );
	register_nav_menus( array(
		'principal' => 'Navigation principale',
		'pied'      => 'Pied de page',
	) );
}
add_action( 'after_setup_theme', 'eq_setup' );

function eq_assets() {
	wp_enqueue_style( 'equilibrium', get_theme_file_uri( 'assets/site.css' ), array(), EQ_VERSION );
}
add_action( 'wp_enqueue_scripts', 'eq_assets' );

/* Rien de tout cela n'existait dans la version statique : on ne l'ajoute pas. */
remove_action( 'wp_head', 'print_emoji_detection_script', 7 );
remove_action( 'wp_print_styles', 'print_emoji_styles' );
remove_action( 'wp_head', 'wp_generator' );
remove_action( 'wp_head', 'wlwmanifest_link' );
remove_action( 'wp_head', 'rsd_link' );
remove_action( 'wp_head', 'wp_shortlink_wp_head' );
remove_action( 'wp_head', 'wp_oembed_add_discovery_links' );
remove_action( 'wp_head', 'wp_oembed_add_host_js' );
remove_action( 'wp_head', 'rest_output_link_wp_head' );
remove_action( 'wp_head', 'feed_links', 2 );
remove_action( 'wp_head', 'feed_links_extra', 3 );
remove_action( 'wp_head', 'wp_resource_hints', 2 );
remove_action( 'wp_enqueue_scripts', 'wp_enqueue_global_styles' );
remove_action( 'wp_footer', 'wp_enqueue_global_styles', 1 );
remove_action( 'wp_body_open', 'wp_global_styles_render_svg_filters' );
add_filter( 'emoji_svg_url', '__return_false' );
add_filter( 'the_generator', '__return_empty_string' );
add_filter( 'wp_img_tag_add_auto_sizes', '__return_false' );
/* WordPress 6.8 imprime un <script type="speculationrules"> qui fait
   pre-charger les pages par le navigateur. C'est le SEUL script que la page
   contiendrait, sur un site qui n'en a aucun, et il decide tout seul d'aller
   chercher des adresses. On le coupe par son filtre de configuration. */
add_filter( 'wp_speculation_rules_configuration', '__return_null' );
add_action( 'wp_enqueue_scripts', function () {
	wp_dequeue_style( 'wp-block-library' );
	wp_dequeue_style( 'wp-block-library-theme' );
	wp_dequeue_style( 'global-styles' );
	wp_dequeue_style( 'classic-theme-styles' );
	wp_dequeue_style( 'wp-img-auto-sizes-contain' );
}, 100 );

/**
 * Le contenu des pages est du HTML deja mis en forme, decoupe en blocs
 * « HTML personnalise ». wpautop ajouterait des <p> au milieu de ce balisage.
 *
 * wp_filter_content_tags reecrit les <img> (fetchpriority, decoding,
 * loading="lazy") : la version statique a ete mesuree SANS ces attributs, et
 * on ne laisse pas WordPress modifier un balisage deja verifie. La PRIORITE
 * fait partie de l'identite du filtre — sans le 12, remove_filter cherche a la
 * priorite 10 et ne retire RIEN, en silence.
 */
add_action( 'wp', function () {
	if ( is_singular() && get_post_meta( get_queried_object_id(), '_eq_cle', true ) ) {
		remove_filter( 'the_content', 'wpautop' );
		remove_filter( 'the_content', 'shortcode_unautop' );
		remove_filter( 'the_content', 'wp_filter_content_tags', 12 );
		/* wptexturize remplace l'apostrophe droite par &#8217; DANS LE RENDU.
		   Le texte stocke ne bouge pas, ce qui rend le defaut invisible a la
		   relecture en base : seule la comparaison du rendu au rendu le voit.
		   Le site statique ecrit ses apostrophes typographiques la ou il en
		   veut ; WordPress n'a pas a en decider a sa place. */
		remove_filter( 'the_content', 'wptexturize' );
	}
} );

/* ------------------------------------------------------------ navigation */

/**
 * La cle de navigation a marquer comme courante sur la page affichee.
 *
 * Elle est portee par la page (metadonnee _eq_nav) et n'est PAS deduite de
 * l'URL : l'espace membre marque « Circle », et la page de connexion marque la
 * porte du portail, qui n'est pas dans le menu. Deviner a partir de l'URL
 * donnerait un resultat faux sur ces deux pages-la.
 */
function eq_nav_courante() {
	$id = get_queried_object_id();
	return $id ? (string) get_post_meta( $id, '_eq_nav', true ) : '';
}

/**
 * Rend un menu WordPress avec le balisage exact du site statique : une suite
 * de <a> nus, et pour le menu principal un separateur avant l'entree qui
 * ouvre la pratique.
 *
 * Le separateur suit une CLASSE d'entree de menu (`eq-sep`), pas une position :
 * s'il etait pose au 5e rang, reordonner le menu dans l'administration le
 * laisserait au mauvais endroit sans prevenir.
 */
class EQ_Walker extends Walker_Nav_Menu {
	/* Le pied de page ne marque PAS la page courante : le site statique ne le
	   fait pas, et deux aria-current="page" dans un meme document sont une
	   erreur d'accessibilite, pas une redondance sans effet. */
	public $marque = true;
	public function start_lvl( &$sortie, $profondeur = 0, $args = null ) {}
	public function end_lvl( &$sortie, $profondeur = 0, $args = null ) {}
	public function start_el( &$sortie, $element, $profondeur = 0, $args = null, $id = 0 ) {
		$classes = is_array( $element->classes ) ? $element->classes : array();
		if ( in_array( 'eq-sep', $classes, true ) ) {
			$sortie .= '<span class="sep" aria-hidden="true"></span>';
		}
		$cle = '';
		foreach ( $classes as $c ) {
			if ( 0 === strpos( $c, 'eq-nav-' ) ) { $cle = substr( $c, 7 ); }
		}
		$courant = ( $this->marque && '' !== $cle && $cle === eq_nav_courante() );
		$sortie .= sprintf( '<a href="%s"%s>%s</a>',
			esc_url( $element->url ),
			$courant ? ' aria-current="page"' : '',
			esc_html( $element->title ) );
	}
	public function end_el( &$sortie, $element, $profondeur = 0, $args = null ) {}
}

function eq_menu( $ou ) {
	if ( ! has_nav_menu( $ou ) ) { return; }
	// Le conteneur est ecrit ici et pas laisse a wp_nav_menu : quand
	// container_class est vide, WordPress fabrique tout seul une classe
	// « menu-<slug>-container » que la version statique n'a pas.
	$walker = new EQ_Walker();
	$walker->marque = ( 'principal' === $ou );
	$items = wp_nav_menu( array(
		'theme_location' => $ou,
		'container'      => false,
		'items_wrap'     => '%3$s',
		'depth'          => 1,
		'walker'         => $walker,
		'fallback_cb'    => false,
		'echo'           => false,
	) );
	$items = trim( (string) $items );
	echo ( 'principal' === $ou ) ? '<nav class="nav">' . $items . '</nav>'
	                             : '<nav>' . $items . '</nav>';
}

/**
 * La porte du portail. Elle est un enfant de l'en-tete et volontairement HORS
 * du <nav> : dedans, des que la navigation passait sur deux lignes elle
 * s'exilait seule sur la seconde.
 */
function eq_porte( $libelle ) {
	$p = get_page_by_path( 'portal' );
	$courant = ( 'portal' === eq_nav_courante() );
	printf( '<a class="signin" href="%s"%s>%s</a>',
		esc_url( $p ? get_permalink( $p ) : home_url( '/portal/' ) ),
		$courant ? ' aria-current="page"' : '',
		esc_html( $libelle ) );
}

/* ----------------------------------------------------------------- en-tete */

/**
 * Le titre du document est celui de la version statique, mot pour mot.
 * WordPress fabriquerait « Page – Nom du site » avec son propre separateur.
 */
function eq_titre( $titre ) {
	$id = get_queried_object_id();
	if ( $id ) {
		$t = get_post_meta( $id, '_eq_title', true );
		if ( $t ) { return $t; }
	}
	return $titre;
}
add_filter( 'pre_get_document_title', 'eq_titre' );

function eq_tete() {
	$id = get_queried_object_id();
	$desc = $id ? get_post_meta( $id, '_eq_desc', true ) : '';
	if ( $desc ) {
		printf( '<meta name="description" content="%s">' . "\n", esc_attr( $desc ) );
	}
}
add_action( 'wp_head', 'eq_tete' );
