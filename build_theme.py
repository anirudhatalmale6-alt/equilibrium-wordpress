# -*- coding: utf-8 -*-
"""Fabrique le theme WordPress « equilibrium » A PARTIR du site statique livre.

Principe, le meme que pour la Seigneurie : on n'ecrit pas le site une deuxieme
fois. L'habillage (bandeau de demonstration, en-tete, navigation, porte du
portail, pied de page) est EXTRAIT des pages statiques elles-memes et
transforme en gabarits PHP. Retaper les textes serait le moyen le plus sur
d'introduire une difference invisible entre la version statique deja verifiee
(1354 controles) et la version WordPress.

Ce que le script produit :
  wp/wp-content/themes/equilibrium/   le theme complet
  eqwp/pages.json                     la liste des pages, lue par seed.php

Ce qu'il ne fait pas : creer les pages. C'est le travail de seed.php, qui parle
a WordPress et non au disque.
"""
import json
import os
import re
import shutil

ICI = os.path.dirname(os.path.abspath(__file__))
STATIQUE = os.path.join(os.path.dirname(ICI), "equilibrium")
THEME = os.path.join(ICI, "wp", "wp-content", "themes", "equilibrium")

# --------------------------------------------------------------------------
# La carte des pages. Elle est ECRITE ICI et nulle part ailleurs : le
# reecrivain de liens, le semeur de pages et les menus la lisent tous les
# trois. Une seule source, donc pas de derive possible entre eux.
#
# nav = quel element de la navigation porte aria-current sur cette page. Ce
# n'est PAS toujours la page elle-meme : `portal-area` est dans la branche du
# Cercle et marque « Circle », et `portal` marque la porte du portail, qui est
# hors du <nav>. C'est ce que fait le site statique ; on le reproduit au lieu
# de le deviner a partir de l'URL.
# (fichier, slug, titre d'admin, libelle de menu, cle de navigation courante)
# --------------------------------------------------------------------------
PAGES = [
    ("index.html",       "home",        "Equilibrium",     "Statement",     "statement"),
    ("principles.html",  "principles",  "Principles",      "Principles",    "principles"),
    ("movement.html",    "movement",    "The movement",    "The movement",  "movement"),
    ("join.html",        "join",        "Join",            "Join",          "join"),
    ("support.html",     "support",     "Support",         "Support",       "support"),
    ("services.html",    "services",    "Services",        "Services",      "services"),
    ("lobbying.html",    "lobbying",    "Lobbying",        "Lobbying",      "lobbying"),
    ("circle.html",      "circle",      "Circle",          "Circle",        "circle"),
    ("portal.html",      "portal",      "Member sign-in",  "Member sign-in","portal"),
    ("portal-area.html", "portal-area", "Member area",     "Member area",   "circle"),
]

# Le menu principal du site statique : huit entrees, dont la premiere est une
# ancre vers l'accueil et non une page. Le separateur visuel se place AVANT
# « Services » — c'est la ou le site statique le met, et c'est ce qui separe
# le mouvement de la pratique.
MENU_PRINCIPAL = [
    {"cle": "statement",  "ancre": "#statement", "page": "home",      "sep": False},
    {"cle": "principles", "ancre": "",           "page": "principles","sep": False},
    {"cle": "movement",   "ancre": "",           "page": "movement",  "sep": False},
    {"cle": "join",       "ancre": "",           "page": "join",      "sep": False},
    {"cle": "support",    "ancre": "",           "page": "support",   "sep": False},
    {"cle": "services",   "ancre": "",           "page": "services",  "sep": True},
    {"cle": "lobbying",   "ancre": "",           "page": "lobbying",  "sep": False},
    {"cle": "circle",     "ancre": "",           "page": "circle",    "sep": False},
]
# Le pied reprend les memes huit entrees, sans separateur.
MENU_PIED = [dict(e, sep=False) for e in MENU_PRINCIPAL]

# Les pages qui n'apparaissent dans aucun menu : la porte du portail est un
# element a part de l'en-tete, et l'espace membre ne se donne pas en menu.
HORS_MENU = ("portal", "portal-area")

# --------------------------------------------------------------------------
# Reecriture des liens : chemin statique -> chemin WordPress
# --------------------------------------------------------------------------
CHEMIN = {}
for fichier, slug, _t, _m, _n in PAGES:
    CHEMIN[fichier] = "/" if slug == "home" else "/%s/" % slug


def reecrit(html, mode="php"):
    """Remplace liens et ressources du site statique par ceux du theme.

    mode « php »     : pour les gabarits du theme -> appels PHP (home_url,
                       get_theme_file_uri). Le site marche alors quel que soit
                       le domaine ET quel que soit le sous-dossier.
    mode « contenu » : pour le contenu des pages, stocke en base. On y ecrit
                       des URL ABSOLUES, parce que c'est ce que All-in-One WP
                       Migration sait reecrire a l'import. Un chemin commencant
                       par « / » ne serait PAS reecrit et casserait une
                       installation en sous-dossier.
    """
    def cible(ref):
        if ref.startswith("#"):
            return ref
        chemin, _, ancre = ref.partition("#")
        ancre = ("#" + ancre) if ancre else ""
        chemin = chemin.split("?")[0]
        if chemin.startswith("assets/"):
            nom = chemin.split("assets/", 1)[1]
            if mode == "contenu":
                return "%%URL%%/wp-content/themes/equilibrium/assets/" + nom + ancre
            return ("<?php echo esc_url( get_theme_file_uri( 'assets/%s' ) ); ?>%s"
                    % (nom, ancre))
        if chemin in CHEMIN:
            if mode == "contenu":
                return "%%URL%%" + CHEMIN[chemin] + ancre
            return ("<?php echo esc_url( home_url( '%s' ) ); ?>%s"
                    % (CHEMIN[chemin], ancre))
        raise KeyError("lien non cartographie : %r" % ref)

    def sub(m):
        return '%s="%s"' % (m.group(1), cible(m.group(2)))

    return re.sub(r'\b(href|src)="([^"]+)"', sub, html)


def lire(fichier):
    with open(os.path.join(STATIQUE, fichier), encoding="utf-8") as f:
        return f.read()


def morceaux(html):
    """Decoupe une page statique en habillage haut / contenu / habillage bas."""
    corps = html[html.index("<body>") + len("<body>"):]
    haut = corps[:corps.index("<main")]
    i = corps.index(">", corps.index("<main")) + 1
    contenu = corps[i:corps.index("</main>")]
    bas = corps[corps.index("</main>") + len("</main>"):]
    return haut, contenu, bas[:bas.index("</body>")]


def php_haut():
    """L'en-tete, extrait de la page d'accueil.

    Deux substitutions, et deux seulement : le <nav> devient un menu WordPress,
    la porte du portail devient un appel PHP qui sait poser aria-current. Les
    deux COMPTENT leurs remplacements et levent si ce n'est pas exactement 1 :
    une regex qui ne matche plus figerait le balisage sans rien dire.
    """
    haut, _, _ = morceaux(lire("index.html"))
    haut = haut.replace(' aria-current="page"', '')   # pose par le PHP

    # Les deux substitutions se font sur le balisage BRUT, avant la reecriture
    # des liens : une fois le href remplace par un appel PHP, il contient un
    # « > » et « <a class="signin"[^>]*> » s'arrete au milieu de l'appel.
    haut, n1 = re.subn(r'<nav class="nav">.*?</nav>',
                       "@@MENU@@", haut, flags=re.S)
    haut, n2 = re.subn(r'<a class="signin"[^>]*>(.*?)</a>',
                       lambda m: "@@PORTE:%s@@" % m.group(1),
                       haut, flags=re.S)
    if (n1, n2) != (1, 1):
        raise AssertionError("en-tete : nav=%d porte=%d" % (n1, n2))

    haut = reecrit(haut)
    haut = haut.replace("@@MENU@@", "<?php eq_menu( 'principal' ); ?>")
    haut = re.sub(r'@@PORTE:(.*?)@@',
                  lambda m: "<?php eq_porte( %s ); ?>" % php_chaine(m.group(1)),
                  haut, flags=re.S)
    return haut


def php_bas():
    """Le pied de page, extrait de la page d'accueil.

    Le <nav> du pied devient un menu WordPress. Le reste — les trois clauses du
    bas — est du texte de gouvernance qui ne bouge pas : la separation entre le
    mouvement et la pratique, et l'absence de toute revendication de statut.
    Il est dans footer.php et PAS dans une page, exactement pour cette raison :
    il ne doit pas pouvoir disparaitre dans une modification de contenu.
    """
    _, _, bas = morceaux(lire("index.html"))
    bas, n1 = re.subn(r'<nav>.*?</nav>', "@@MENU@@", bas, flags=re.S)
    if n1 != 1:
        raise AssertionError("pied : nav=%d" % n1)
    return reecrit(bas).replace("@@MENU@@", "<?php eq_menu( 'pied' ); ?>")


def php_chaine(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def contenu_page(fichier):
    _, contenu, _ = morceaux(lire(fichier))
    return reecrit(contenu, mode="contenu").strip()


def tete_de(fichier):
    html = lire(fichier)
    tete = html[:html.index("</head>")]
    titre = re.search(r"<title>(.*?)</title>", tete, re.S).group(1)
    desc = re.search(r'<meta name="description" content="([^"]*)"', tete)
    return titre, (desc.group(1) if desc else "")


# --------------------------------------------------------------------------
# Le theme
# --------------------------------------------------------------------------
STYLE_CSS = """/*
Theme Name: Equilibrium
Description: Theme du site Equilibrium (mouvement, pratique et Cercle). Aucune ressource exterieure : la feuille de style et les visuels sont servis par le theme lui-meme. Aucun script.
Version: 1.1.0
Requires at least: 6.0
Tested up to: 7.1
Requires PHP: 7.4
Text Domain: equilibrium
*/

/* La feuille de style reelle est assets/site.css, mise en file d'attente par
   functions.php. Ce fichier n'existe que parce que WordPress exige un
   style.css portant l'en-tete du theme. */
"""

FUNCTIONS_PHP = r"""<?php
/**
 * Equilibrium — fonctions du theme.
 *
 * Regle de ce site, tenue ici comme dans la version statique : AUCUNE requete
 * ne quitte le domaine. Pas de police distante, pas de CDN, pas de mesure
 * d'audience, et aucun script. On retire donc aussi ce que WordPress ajoute de
 * lui-meme et qui sortirait du domaine ou chargerait la page sans servir.
 */

if ( ! defined( 'ABSPATH' ) ) { exit; }

define( 'EQ_VERSION', '1.1.0' );

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

/* ------------------------------------------------------- adresse de don */

/**
 * L'adresse du portefeuille, et l'UNIQUE endroit ou elle est ecrite.
 *
 * Le contenu de la page de soutien porte un emplacement marque par deux
 * commentaires HTML, <!--EQ_BTC--> ... <!--/EQ_BTC-->. Ce qui se trouve entre
 * les deux est remplace ici, au rendu, par la valeur de l'option
 * `eq_adresse_btc`.
 *
 * Pourquoi pas l'adresse ecrite directement dans la page : elle serait alors
 * dans le contenu d'un article, c'est-a-dire recopiee dans les revisions,
 * dans toute sauvegarde et dans toute exportation. Le jour ou elle change, il
 * faudrait la corriger a plusieurs endroits — et une adresse de portefeuille
 * corrigee a moitie envoie l'argent chez un inconnu, de maniere irreversible.
 * Une option, c'est un endroit, et un seul.
 *
 * Tant que l'option est vide — c'est son etat de depart — la page affiche la
 * meme pastille « To be decided » que partout ailleurs sur ce site, et ne
 * peut recevoir aucun paiement.
 *
 *   la poser   : wp option update eq_adresse_btc '<adresse>'
 *   la retirer : wp option delete eq_adresse_btc
 */
function eq_adresse_btc() {
	$v = trim( (string) get_option( 'eq_adresse_btc', '' ) );
	/* Une adresse ne contient que des caracteres alphanumeriques, en base58
	   ou en bech32. Tout le reste est soit une faute de frappe, soit une
	   injection. On REFUSE au lieu de nettoyer : une adresse nettoyee reste
	   une adresse d'apparence valide, mais ce n'est plus la bonne, et rien a
	   l'ecran ne le dirait. */
	if ( '' === $v || ! preg_match( '/\A[a-zA-Z0-9]{25,64}\z/', $v ) ) { return ''; }
	return $v;
}

function eq_pose_adresse( $contenu ) {
	if ( false === strpos( $contenu, '<!--EQ_BTC-->' ) ) { return $contenu; }
	$adresse = eq_adresse_btc();
	$dedans  = $adresse
		? '<span class="adr">' . esc_html( $adresse ) . '</span>'
		: '<span class="tbd">To be decided</span>';
	/* Remplacement par CALLBACK et non par chaine : dans une chaine de
	   remplacement, preg_replace interprete $1 et les antislashs. Une adresse
	   n'en contient pas aujourd'hui, mais le jour ou l'option contiendrait
	   autre chose, l'erreur serait silencieuse et porterait sur l'adresse. */
	return preg_replace_callback(
		'/<!--EQ_BTC-->.*?<!--\/EQ_BTC-->/s',
		function () use ( $dedans ) { return '<!--EQ_BTC-->' . $dedans . '<!--/EQ_BTC-->'; },
		$contenu );
}
add_filter( 'the_content', 'eq_pose_adresse', 20 );

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
"""

HEADER_PHP_MODELE = """<?php
/**
 * En-tete du site. L'habillage vient de la version statique, extrait d'elle et
 * non retape : bandeau de demonstration, marque, navigation, porte du portail.
 *
 * Le bandeau de demonstration est volontairement conserve. Il dit que rien
 * n'est publie et que le texte attend l'approbation du mouvement — c'est vrai
 * tant que les decisions ouvertes ne sont pas tranchees. Il se retire en
 * supprimant sa ligne ici, le jour ou ce ne sera plus vrai.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }
?><!doctype html>
<html lang="en">
<head>
<meta charset="<?php bloginfo( 'charset' ); ?>">
<meta name="viewport" content="width=device-width, initial-scale=1">
<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
%HAUT%
"""

FOOTER_PHP_MODELE = """<?php
/**
 * Pied de page. Meme principe que l'en-tete : le balisage vient de la version
 * statique.
 *
 * Les trois clauses du bas ne sont PAS dans une page, et c'est deliberé :
 * elles disent que la declaration est citee mot pour mot, qu'aucun statut
 * n'est revendique, et que le mouvement et la pratique sont separes. Une
 * regle de gouvernance qui peut disparaitre dans une modification de contenu
 * ne vaut rien.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }
?>
%BAS%
<?php wp_footer(); ?>
</body>
</html>
"""

PAGE_PHP = """<?php
/**
 * Une page. Le contenu editable est ce qu'il y a entre <main> et </main> dans
 * la version statique : tout ce que le client voudra changer se change dans
 * l'editeur, l'habillage reste au theme.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }
get_header();
?>
<main>
<?php
while ( have_posts() ) {
	the_post();
	the_content();
}
?>
</main>
<?php
get_footer();
"""

INDEX_PHP = """<?php
/**
 * Gabarit de repli. Le site n'a que des pages ; ce fichier existe parce que
 * WordPress exige un index.php.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }
get_header();
?>
<main>
<section><div class="wrap">
<?php
if ( have_posts() ) {
	while ( have_posts() ) {
		the_post();
		echo '<div class="sec-h"><h2>' . esc_html( get_the_title() ) . '</h2></div>';
		the_content();
	}
}
?>
</div></section>
</main>
<?php
get_footer();
"""

QUATRECENTQUATRE_PHP = """<?php
/**
 * Page introuvable. Elle ne promet rien et renvoie au menu.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }
get_header();
?>
<main>
<section><div class="wrap">
  <div class="filet"></div>
  <div class="sec-h">
    <span class="eyebrow">Not found</span>
    <h2>This address matches no page</h2>
    <p>Every section of this site is reachable from the navigation above.</p>
  </div>
</div></section>
</main>
<?php
get_footer();
"""


def ecrire(chemin, texte):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(texte)


# Les ressources copiees, nommees une par une. Jamais un « cp -r » d'un dossier
# de travail : on ne copie que ce qu'on a nomme. hero.svg et hero-practice.svg
# ne sont references par aucune page — ils sont appeles par background-image
# depuis site.css, et un controle d'orphelins qui ne regarde que document.images
# les declarerait inutilises.
ASSETS = ("site.css", "mark.svg", "seal.svg", "multipolar.svg", "wall.svg",
          "hero.svg", "hero-practice.svg",
          "p-balance.svg", "p-diplomacy.svg", "p-economy.svg",
          "p-sovereignty.svg", "p-stability.svg")


def main():
    if os.path.isdir(THEME):
        shutil.rmtree(THEME)
    os.makedirs(THEME)

    dst = os.path.join(THEME, "assets")
    os.makedirs(dst)
    for nom in ASSETS:
        shutil.copy2(os.path.join(STATIQUE, "assets", nom), os.path.join(dst, nom))

    ecrire(os.path.join(THEME, "style.css"), STYLE_CSS)
    ecrire(os.path.join(THEME, "functions.php"), FUNCTIONS_PHP)
    ecrire(os.path.join(THEME, "header.php"), HEADER_PHP_MODELE.replace("%HAUT%", php_haut()))
    ecrire(os.path.join(THEME, "footer.php"), FOOTER_PHP_MODELE.replace("%BAS%", php_bas()))
    ecrire(os.path.join(THEME, "page.php"), PAGE_PHP)
    ecrire(os.path.join(THEME, "front-page.php"), PAGE_PHP)
    ecrire(os.path.join(THEME, "index.php"), INDEX_PHP)
    ecrire(os.path.join(THEME, "404.php"), QUATRECENTQUATRE_PHP)

    pages = []
    for fichier, slug, titre, menu, nav in PAGES:
        titre_doc, desc = tete_de(fichier)
        pages.append({
            "fichier": fichier,
            "slug": slug,
            "cle": slug,
            "titre": titre,
            "menu": menu,
            "nav": nav,
            "titre_doc": titre_doc,
            "description": desc,
            "hors_menu": slug in HORS_MENU,
            "contenu": contenu_page(fichier),
        })
    ecrire(os.path.join(ICI, "pages.json"), json.dumps({
        "pages": pages,
        "menu_principal": MENU_PRINCIPAL,
        "menu_pied": MENU_PIED,
    }, ensure_ascii=False, indent=1))

    print("theme ecrit : %s" % THEME)
    print("ressources  : %d" % len(ASSETS))
    print("pages.json  : %d pages" % len(pages))


if __name__ == "__main__":
    main()
