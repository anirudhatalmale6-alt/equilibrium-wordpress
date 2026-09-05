<?php
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
