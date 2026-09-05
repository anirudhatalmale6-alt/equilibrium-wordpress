<?php
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

<footer class="ft"><div class="wrap">
  <div class="haut">
    <div>
      <span class="brand">
        <img src="<?php echo esc_url( get_theme_file_uri( 'assets/mark.svg' ) ); ?>" alt="" width="26" height="26">
        <span class="nm">Equilibrium</span>
      </span>
      <p class="ligne">Global political &amp; diplomatic movement. Restoring balance through diplomacy, sovereignty, economic cooperation &amp; strategic stability.</p>
    </div>
    <?php eq_menu( 'pied' ); ?>
  </div>
  <div class="bas">
    <p>The statement on this site is quoted verbatim. All other text is draft
    copy written from that statement and is subject to the movement&rsquo;s
    approval.</p>
    <p>No legal form, place of registration, membership, funding, registration
    as a representative, accreditation or official status of any kind is
    claimed anywhere on this site. Those are open decisions and are listed as
    such on <a href="<?php echo esc_url( home_url( '/movement/' ) ); ?>#decisions">The movement</a>.</p>
    <p>The movement publishes positions in its own name. The practice speaks
    for clients, in theirs. The rule that separates the two is set out on
    <a href="<?php echo esc_url( home_url( '/lobbying/' ) ); ?>#wall">Lobbying</a>.</p>
  </div>
</div></footer>

<?php wp_footer(); ?>
</body>
</html>
