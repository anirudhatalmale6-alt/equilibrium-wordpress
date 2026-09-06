<?php
/**
 * Exporte la base du site de developpement en SQL MySQL.
 *
 * Le WordPress de developpement tourne sur SQLite ; le site du client tournera
 * sur MySQL. Le fichier produit ici est donc le seul endroit du chantier ou
 * l'on traduit d'un moteur a l'autre, et c'est aussi celui que personne
 * n'execute avant l'import chez le client — d'ou restaure.py, qui l'importe
 * pour de vrai dans un MySQL vierge avant la livraison.
 *
 * Le SCHEMA n'est pas devine a partir de SQLite : il est demande a WordPress
 * lui-meme (wp_get_db_schema), qui le decrit en MySQL. Seules les DONNEES
 * viennent de la base de developpement.
 *
 * Usage : php dump.php /chemin/vers/wordpress /chemin/de/sortie/database.sql
 */

if ( php_sapi_name() !== 'cli' ) { exit( 1 ); }

$racine = rtrim( $argv[1] ?? '', '/' );
$sortie = $argv[2] ?? '';
if ( ! $racine || ! $sortie ) {
	fwrite( STDERR, "usage: dump.php <wordpress> <database.sql>\n" );
	exit( 1 );
}

require $racine . '/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/schema.php';

global $wpdb;

$COLLATE = 'DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_520_ci';

/** Echappement MySQL, ecrit ici parce que le pilote SQLite n'en fournit pas. */
function eq_sql( $v ) {
	if ( is_null( $v ) ) { return 'NULL'; }
	return "'" . str_replace(
		array( '\\', "'", '"', "\n", "\r", "\x00", "\x1a" ),
		array( '\\\\', "\\'", '\\"', '\\n', '\\r', '\\0', '\\Z' ),
		(string) $v ) . "'";
}

/* Le schema, tel que WordPress le decrit en MySQL. On decoupe le bloc en
   instructions CREATE TABLE, une par table. */
$schema = wp_get_db_schema( 'all' );
$creations = array();
foreach ( preg_split( '/;\s*[\r\n]+/', $schema ) as $bout ) {
	$bout = trim( $bout );
	if ( '' === $bout || 0 !== stripos( $bout, 'CREATE TABLE' ) ) { continue; }
	if ( ! preg_match( '/CREATE TABLE\s+`?([A-Za-z0-9_]+)`?/i', $bout, $m ) ) { continue; }
	/* Le nom de table entre accents graves, et colle a la parenthese.
	   wp_get_db_schema() ecrit « CREATE TABLE wp_users ( ». UpdraftPlus lit le
	   fichier avec :
	       preg_match('/^\s*create table \`?([^\`\(]*)\`?\s*\(/i', ...)
	   Sans accent grave, la capture gourmande emporte l'espace : le nom
	   devient « wp_users », espace compris, il ne correspond plus a la liste
	   des tables attendues, et le client voit « This database backup is
	   missing core WordPress tables: users, options, posts... » sur une
	   sauvegarde pourtant complete. */
	$bout = preg_replace( '/^CREATE TABLE\s+`?([A-Za-z0-9_]+)`?\s*\(/i',
		'CREATE TABLE `$1` (', $bout, 1 );
	/* Si le pilote ne rend pas de jeu de caracteres, la table prendrait celui
	   du serveur du client, qui peut etre latin1 : on l'ecrit toujours. */
	if ( false === stripos( $bout, 'CHARACTER SET' ) ) {
		$bout .= ' ' . $GLOBALS['COLLATE'];
	}
	$creations[ $m[1] ] = $bout;
}

$lignes = array();
$lignes[] = "-- Equilibrium — sauvegarde de la base, format MySQL.";
$lignes[] = "-- Schema : wp_get_db_schema(). Donnees : base de developpement.";
$lignes[] = "SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO';";
$lignes[] = "SET NAMES utf8mb4;";
$lignes[] = "";

/**
 * Les transitoires sont des CACHES, jamais des donnees.
 *
 * Deux raisons de ne pas les emporter. La premiere est qu'ils decrivent le
 * site de developpement et pas celui du client : _site_transient_update_plugins
 * contient le resultat de la derniere verification des mises a jour, donc le
 * nom des extensions d'ici — dont le pilote SQLite, qui n'a rien a faire chez
 * un client en MySQL. La seconde est qu'ils sont datés : livres tels quels,
 * ils font croire au site d'arrivee qu'une verification vient d'avoir lieu.
 *
 * WordPress les recreera tout seul a la premiere page.
 */
function eq_est_transitoire( $table, $row ) {
	if ( 'wp_options' !== $table ) { return false; }
	$nom = $row['option_name'];
	return 0 === strpos( $nom, '_transient_' ) || 0 === strpos( $nom, '_site_transient_' );
}

$total = 0;
$ignorees = 0;
foreach ( $creations as $table => $creation ) {
	$rows = $wpdb->get_results( "SELECT * FROM `$table`", ARRAY_A );
	if ( null === $rows ) { $rows = array(); }
	$avant = count( $rows );
	$rows = array_values( array_filter( $rows, function ( $row ) use ( $table ) {
		return ! eq_est_transitoire( $table, $row );
	} ) );
	$ignorees += $avant - count( $rows );

	$lignes[] = "DROP TABLE IF EXISTS `$table`;";
	$lignes[] = $creation . ';';

	foreach ( $rows as $row ) {
		$cols = array();
		$vals = array();
		foreach ( $row as $c => $v ) {
			$cols[] = '`' . $c . '`';
			$vals[] = eq_sql( $v );
		}
		$lignes[] = "INSERT INTO `$table` (" . implode( ', ', $cols ) . ') VALUES ('
			. implode( ', ', $vals ) . ');';
	}
	$lignes[] = "";
	$total += count( $rows );
	fwrite( STDOUT, sprintf( "  %-26s %5d lignes\n", $table, count( $rows ) ) );
}

file_put_contents( $sortie, implode( "\n", $lignes ) . "\n" );
fwrite( STDOUT, sprintf( "\n%d tables, %d lignes (%d transitoires ecartes) -> %s (%d octets)\n",
	count( $creations ), $total, $ignorees, $sortie, filesize( $sortie ) ) );
