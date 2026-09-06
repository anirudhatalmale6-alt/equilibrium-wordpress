# -*- coding: utf-8 -*-
"""Fabrique un jeu de sauvegarde au format UpdraftPlus.

Pourquoi ce script existe : le client ne veut plus passer par All-in-One WP
Migration, il veut restaurer avec UpdraftPlus. Le format est different, et
surtout la regle de rejeu est differente.

Ce qu'UpdraftPlus verifie, dans SON code, et qui commande tout ce fichier :

1. Le NOM. Un fichier televerse doit correspondre a
       /^backup_([\\-0-9]{15})_.*_([0-9a-f]{12})-([\\-a-z]+)([0-9]+)?(\\.(zip|gz|gz\\.crypt))?$/i
   (admin.php). Sinon : « Bad filename format - this does not look like a file
   created by UpdraftPlus ». L'horodatage fait 15 caracteres, l'empreinte 12
   hexadecimaux, et c'est elle qui regroupe les fichiers en UN jeu.

2. L'ADRESSE DU SITE, lue dans l'en-tete du dump :
       preg_match('/^\\# Backup of: (http(.*))$/', $buffer, $matches)
   (class-updraftplus.php, analyse_db_file). Si elle differe de celle du site
   ou l'on restaure, UpdraftPlus annonce une MIGRATION et repond « You need the
   Migrator add-on in order to make this work » — l'extension gratuite ne
   reecrit pas les adresses. Le dump est donc ecrit directement a l'adresse de
   destination : il n'y a alors rien a migrer.

3. LES TABLES, reperees ligne a ligne :
       preg_match('/^\\s*create table \\`?([^\\`\\(]*)\\`?\\s*\\(/i', ...)
   La capture est gourmande : sans accents graves autour du nom, elle emporte
   l'espace qui precede la parenthese, le nom ne correspond plus a la liste
   attendue et le client lit « This database backup is missing core WordPress
   tables: users, options, posts... » sur une sauvegarde pourtant complete.
   C'est dump.php qui pose les accents graves ; ici on le VERIFIE.

Usage : python3 updraft.py
"""
import datetime
import gzip
import hashlib
import os
import subprocess
import sys
import zipfile

import adresse

ICI = os.path.dirname(os.path.abspath(__file__))
PAQUET = os.path.join(ICI, "paquet")
LIVRAISON = os.path.join(ICI, "updraft")
WP = os.path.join(ICI, "wp")

URL_DEV = "http://127.0.0.1:8881"
CIBLE = os.environ.get("EQ_CIBLE", "https://equilibriumcircle.com")
PREFIXE = "wp_"

TABLES_ATTENDUES = ["terms", "term_taxonomy", "term_relationships",
                    "commentmeta", "comments", "links", "options", "postmeta",
                    "posts", "users", "usermeta"]


def version_wordpress():
    with open(os.path.join(WP, "wp-includes", "version.php"), encoding="utf-8") as f:
        for ligne in f:
            if ligne.startswith("$wp_version"):
                return ligne.split("'")[1]
    raise RuntimeError("version de WordPress introuvable")


def entete(cible, wp_version, php_version, mysql_version, updraft_version):
    """L'en-tete que lit analyse_db_file(). Chaque ligne est une reponse a une
    question que le code pose ; on n'en invente aucune."""
    return "\n".join([
        "# WordPress MySQL database backup",
        "# Created by UpdraftPlus version %s (https://updraftplus.com)" % updraft_version,
        "# WordPress Version: %s, running on PHP %s (nginx), MySQL %s"
        % (wp_version, php_version, mysql_version),
        "# Backup of: %s" % cible,
        "# Home URL: %s" % cible,
        "# Content URL: %s/wp-content" % cible,
        "# Uploads URL: %s/wp-content/uploads" % cible,
        "# Table prefix: %s" % PREFIXE,
        "# Filtered table prefix: %s" % PREFIXE,
        "# ABSPATH: /",
        "# UpdraftPlus plugin slug: updraftplus/updraftplus.php",
        "# Site info: multisite=0",
        "# Site info: end",
        "",
        "# --------------------------------------------------------",
        "",
    ]) + "\n"


def main():
    sql_source = os.path.join(PAQUET, "database.sql")
    contenu = os.path.join(PAQUET, "wp-content")
    if not os.path.isfile(sql_source):
        print("paquet/database.sql absent : lancer paquet.py d'abord")
        return 1

    os.makedirs(LIVRAISON, exist_ok=True)
    for vieux in sorted(os.listdir(LIVRAISON)):
        os.remove(os.path.join(LIVRAISON, vieux))

    print("--- adresse du site ---")
    with open(sql_source, encoding="utf-8") as f:
        texte = f.read()
    texte, vues, touchees, occurrences = adresse.remplace(texte, URL_DEV, CIBLE)
    print("  %s -> %s" % (URL_DEV, CIBLE))
    print("  %d chaines serialisees lues, %d touchees, %d occurrences remplacees"
          % (vues, touchees, occurrences))
    relues, fausses = adresse.longueurs_coherentes(texte)
    if fausses:
        print("  ECHEC : %d longueurs serialisees fausses sur %d" % (fausses, relues))
        return 1
    print("  longueurs serialisees : %d justes sur %d" % (relues, relues))
    if URL_DEV in texte:
        print("  ECHEC : l'adresse de developpement est encore presente")
        return 1

    # Les accents graves autour des noms de table, relus ici et pas supposes.
    manquantes = [t for t in TABLES_ATTENDUES
                  if ("CREATE TABLE `%s%s` (" % (PREFIXE, t)) not in texte]
    if manquantes:
        print("  ECHEC : tables sans accents graves ou absentes : %s"
              % ", ".join(manquantes))
        return 1
    print("  %d tables coeur ecrites en `prefixe_table`" % len(TABLES_ATTENDUES))

    print("--- versions ---")
    wp_version = version_wordpress()
    php_version = subprocess.run(["php", "-r", "echo PHP_VERSION;"],
                                 capture_output=True).stdout.decode().strip()
    socket = os.environ.get("EQ_SOCKET", "")
    mysql_version = "8.0"
    if socket:
        r = subprocess.run(["mysql", "--socket=" + socket, "-u", "root", "-N", "-e",
                            "select version();"], capture_output=True)
        if not r.returncode:
            mysql_version = r.stdout.decode().strip()
    updraft_version = os.environ.get("EQ_UPDRAFT_VERSION", "1.26.7")
    print("  WordPress %s, PHP %s, MySQL %s, format UpdraftPlus %s"
          % (wp_version, php_version, mysql_version, updraft_version))

    # L'empreinte de 12 hexadecimaux est ce qui REGROUPE les fichiers en un
    # seul jeu de sauvegarde : la meme pour la base et pour les themes, sinon
    # UpdraftPlus affiche deux sauvegardes incompletes.
    horodatage = os.environ.get(
        "EQ_HORODATAGE",
        datetime.datetime.now().strftime("%Y-%m-%d-%H%M"))
    nonce = hashlib.sha1(("equilibrium-" + horodatage).encode()).hexdigest()[:12]
    base = "backup_%s_Equilibrium_%s" % (horodatage, nonce)

    print("--- base de donnees ---")
    db = os.path.join(LIVRAISON, base + "-db.gz")
    corps = entete(CIBLE, wp_version, php_version, mysql_version, updraft_version) + texte
    with gzip.open(db, "wb") as f:
        f.write(corps.encode("utf-8"))
    print("  %s (%d octets compresses)" % (os.path.basename(db), os.path.getsize(db)))

    print("--- themes ---")
    themes = os.path.join(LIVRAISON, base + "-themes.zip")
    racine = os.path.join(contenu, "themes")
    n = 0
    with zipfile.ZipFile(themes, "w", zipfile.ZIP_DEFLATED) as z:
        for dossier, _sd, fichiers in sorted(os.walk(racine)):
            for nom in sorted(fichiers):
                chemin = os.path.join(dossier, nom)
                z.write(chemin, os.path.relpath(chemin, racine).replace(os.sep, "/"))
                n += 1
    print("  %s (%d fichiers, %d octets)"
          % (os.path.basename(themes), n, os.path.getsize(themes)))

    print("--- relecture ---")
    # Ce qu'on vient d'ecrire, relu depuis le fichier et pas depuis les
    # variables : un gzip tronque et un gzip complet ne se distinguent qu'ici.
    with gzip.open(db, "rt", encoding="utf-8") as f:
        relu = f.read()
    if relu != corps:
        print("  ECHEC : le .gz relu ne rend pas ce qui a ete ecrit")
        return 1
    print("  db.gz : %d octets une fois decompresse, identiques a la source"
          % len(relu.encode("utf-8")))
    with zipfile.ZipFile(themes) as z:
        mauvais = z.testzip()
        if mauvais:
            print("  ECHEC : entree corrompue dans le zip : %s" % mauvais)
            return 1
        premiers = sorted({e.split("/")[0] for e in z.namelist()})
    print("  themes.zip : racine = %s" % ", ".join(premiers))
    if "equilibrium" not in premiers:
        print("  ECHEC : le theme doit etre a la racine du zip, pas dans un sous-dossier")
        return 1

    for chemin in (db, themes):
        with open(chemin, "rb") as f:
            print("  md5 %s  %s" % (hashlib.md5(f.read()).hexdigest(),
                                    os.path.basename(chemin)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
