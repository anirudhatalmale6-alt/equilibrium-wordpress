<?php
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
