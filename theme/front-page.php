<?php
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
