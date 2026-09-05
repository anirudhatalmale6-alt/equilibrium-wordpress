<?php
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

<div class="demo">Demonstration mockup — content awaiting the movement&rsquo;s approval. Nothing on this site is published.</div><header class="hdr"><div class="wrap">
  <a class="brand" href="<?php echo esc_url( home_url( '/' ) ); ?>">
    <img src="<?php echo esc_url( get_theme_file_uri( 'assets/mark.svg' ) ); ?>" alt="" width="26" height="26">
    <span class="nm">Equilibrium</span>
  </a>
  <?php eq_menu( 'principal' ); ?>
  <?php eq_porte( 'Member sign-in' ); ?>
</div></header>

