<?php
/**
 * Fixe le compte administrateur du site de developpement, celui qui partira
 * dans la sauvegarde livree.
 *
 * Pourquoi ce script existe : une restauration — .wpress comme UpdraftPlus —
 * remplace la table des utilisateurs de la cible. Le compte avec lequel le
 * client est connecte au moment de l'import disparait donc au profit de celui
 * qui se trouve dans la sauvegarde. S'il n'est pas le meme, le client se
 * retrouve devant un site correct dont il n'a plus la cle.
 *
 * On passe donc par WordPress lui-meme (wp_set_password), et pas par un hash
 * ecrit a la main : la fabrication du hash a change avec WordPress 6.8, et
 * seule la fonction du coeur sait ce que la version cible saura relire.
 *
 * Le mot de passe n'est jamais ecrit ici ni affiche : il arrive par
 * l'environnement et ressort uniquement sous forme de hash dans la base.
 *
 * Un SECOND compte administrateur est cree en meme temps. Il n'est pas la par
 * gout de la ceinture et des bretelles : le premier compte reprend un mot de
 * passe transmis dans une conversation, ou l'on ne distingue pas toujours la
 * ponctuation de la fin d'un mot de passe. Si cette lecture est fausse, le
 * client se retrouve enferme dehors — et sur une installation neuve, la
 * procedure « mot de passe oublie » passe par un courriel qui, tant que
 * l'envoi n'est pas configure, n'arrive jamais. Le second compte est la seule
 * porte qui ne depend d'aucune supposition.
 *
 * Usage : EQ_LOGIN=... EQ_PASS=... EQ_LOGIN2=... EQ_PASS2=... php compte.php <wordpress>
 */

if ( php_sapi_name() !== 'cli' ) { exit( 1 ); }

$racine = rtrim( $argv[1] ?? '', '/' );
$login  = getenv( 'EQ_LOGIN' );
$pass   = getenv( 'EQ_PASS' );
if ( ! $racine || ! $login || ! $pass ) {
	fwrite( STDERR, "usage: EQ_LOGIN=... EQ_PASS=... php compte.php <wordpress>\n" );
	exit( 1 );
}

require $racine . '/wp-load.php';

global $wpdb;

$id = 1;
$avant = get_userdata( $id );
if ( ! $avant ) {
	fwrite( STDERR, "utilisateur 1 introuvable\n" );
	exit( 1 );
}

$wpdb->update(
	$wpdb->users,
	array(
		'user_login'    => $login,
		'user_nicename' => sanitize_title( $login ),
		'display_name'  => $login,
	),
	array( 'ID' => $id )
);
clean_user_cache( $id );
update_user_meta( $id, 'nickname', $login );
wp_set_password( $pass, $id );
clean_user_cache( $id );

/* Relecture. Un update qui ne dit rien n'a pas forcement ecrit, et un cache
   d'objet rend volontiers l'ancienne valeur : on redemande la ligne a la base,
   puis on demande a WordPress de valider le mot de passe comme il le fera a la
   connexion. Verifier que le champ « existe » ne prouverait rien. */
$apres = $wpdb->get_row( $wpdb->prepare(
	"SELECT user_login, user_nicename, display_name, user_pass FROM {$wpdb->users} WHERE ID = %d", $id ) );

if ( $apres->user_login !== $login ) {
	fwrite( STDERR, sprintf( "ECHEC : user_login vaut %s\n", $apres->user_login ) );
	exit( 1 );
}
if ( ! wp_check_password( $pass, $apres->user_pass, $id ) ) {
	fwrite( STDERR, "ECHEC : le hash ecrit ne valide pas le mot de passe\n" );
	exit( 1 );
}
/* Controle positif : la meme fonction doit REFUSER autre chose. Sans lui, un
   wp_check_password qui rendrait vrai pour tout passerait inapercu. */
if ( wp_check_password( $pass . 'x', $apres->user_pass, $id ) ) {
	fwrite( STDERR, "ECHEC : le hash valide aussi un mauvais mot de passe\n" );
	exit( 1 );
}

printf( "compte %d : %s (avant : %s), hash %s, verifie par wp_check_password\n",
	$id, $apres->user_login, $avant->user_login, substr( $apres->user_pass, 0, 7 ) . '...' );

/* Le compte de secours. */
$login2 = getenv( 'EQ_LOGIN2' );
$pass2  = getenv( 'EQ_PASS2' );
if ( $login2 && $pass2 ) {
	$id2 = username_exists( $login2 );
	if ( ! $id2 ) {
		$id2 = wp_insert_user( array(
			'user_login'   => $login2,
			'user_pass'    => $pass2,
			'user_email'   => 'secours@equilibriumcircle.com',
			'display_name' => $login2,
			'role'         => 'administrator',
		) );
		if ( is_wp_error( $id2 ) ) {
			fwrite( STDERR, "ECHEC : " . $id2->get_error_message() . "\n" );
			exit( 1 );
		}
	} else {
		wp_set_password( $pass2, $id2 );
	}
	clean_user_cache( $id2 );

	$u2 = new WP_User( $id2 );
	if ( ! in_array( 'administrator', (array) $u2->roles, true ) ) {
		fwrite( STDERR, "ECHEC : le compte de secours n'est pas administrateur\n" );
		exit( 1 );
	}
	$hash2 = $wpdb->get_var( $wpdb->prepare(
		"SELECT user_pass FROM {$wpdb->users} WHERE ID = %d", $id2 ) );
	if ( ! wp_check_password( $pass2, $hash2, $id2 ) || wp_check_password( $pass2 . 'x', $hash2, $id2 ) ) {
		fwrite( STDERR, "ECHEC : le hash du compte de secours ne se comporte pas comme attendu\n" );
		exit( 1 );
	}
	printf( "compte %d : %s, administrateur, hash verifie par wp_check_password\n",
		$id2, $u2->user_login );
}
