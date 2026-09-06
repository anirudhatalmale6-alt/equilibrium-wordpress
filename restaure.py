# -*- coding: utf-8 -*-
"""Restaure le .wpress LIVRE dans un WordPress neuf, sur MySQL, a une AUTRE
adresse — puis verifie que le site rendu est le meme.

Pourquoi ce controle existe : tout le reste a ete verifie sur le WordPress de
developpement, qui tourne sur SQLite a l'adresse ou l'archive a ete fabriquee.
Deux choses ne sont donc jamais eprouvees par les autres controles :

  1. le database.sql est-il du VRAI MySQL ? Il est genere par un script, et il
     n'est execute par personne avant l'import chez le client.
  2. le site survit-il au changement d'adresse ? Le contenu contient des URL
     absolues, comme tout WordPress.

Ce script refait donc ce que fait All-in-One WP Migration : il ouvre
l'archive, remet wp-content en place, remplace l'ancienne adresse par la
nouvelle dans le SQL, importe dans une base MySQL vierge, et sert le resultat.
La comparaison visuelle tourne ensuite contre CE site-la.

Usage : restaure.py <archive.wpress> <dossier-de-travail> <ancienne-url> <nouvelle-url>
"""
import os
import shutil
import subprocess
import sys

import adresse

HDR = 4377


def entrees(chemin):
    with open(chemin, "rb") as f:
        while True:
            h = f.read(HDR)
            if len(h) < HDR or h == b"\x00" * HDR:
                return
            nom = h[0:255].rstrip(b"\x00").decode("utf-8")
            taille = int(h[255:269].rstrip(b"\x00") or 0)
            prefixe = h[281:HDR].rstrip(b"\x00").decode("utf-8")
            yield nom, prefixe, taille, f
            f.seek(taille, 1)


def extrait(archive, vers):
    """Sort l'archive sur le disque et rend le chemin du database.sql."""
    sql = None
    n = 0
    with open(archive, "rb") as f:
        while True:
            h = f.read(HDR)
            if len(h) < HDR or h == b"\x00" * HDR:
                break
            nom = h[0:255].rstrip(b"\x00").decode("utf-8")
            taille = int(h[255:269].rstrip(b"\x00") or 0)
            prefixe = h[281:HDR].rstrip(b"\x00").decode("utf-8")
            dossier = vers if prefixe in ("", ".") else os.path.join(vers, prefixe)
            os.makedirs(dossier, exist_ok=True)
            cible = os.path.join(dossier, nom)
            restant = taille
            with open(cible, "wb") as g:
                while restant:
                    bloc = f.read(min(restant, 1 << 20))
                    if not bloc:
                        raise IOError("archive tronquee sur %s" % nom)
                    g.write(bloc)
                    restant -= len(bloc)
            if nom == "database.sql":
                sql = cible
            n += 1
    print("  %d entrees extraites" % n)
    return sql


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        return 1
    archive, travail, ancienne, nouvelle = sys.argv[1:5]
    socket = os.environ.get("EQ_SOCKET", "")
    base = os.environ.get("EQ_BASE", "eq")
    if not socket:
        print("EQ_SOCKET manquant (socket du serveur MySQL de test)")
        return 1

    print("--- extraction de l'archive livree ---")
    # Dans un .wpress, la racine de l'archive EST wp-content ; database.sql et
    # package.json sont a cote, hors du contenu. On refait exactement ce
    # rangement, sinon le theme atterrirait a la racine du site.
    brut = os.path.join(travail, "_archive")
    contenu = os.path.join(travail, "wp-content")
    for d in (brut, contenu):
        if os.path.isdir(d):
            shutil.rmtree(d)
    sql = extrait(archive, brut)
    if not sql:
        print("  ECHEC : pas de database.sql dans l'archive")
        return 1
    os.makedirs(contenu)
    for nom in sorted(os.listdir(brut)):
        if nom in ("database.sql", "package.json"):
            continue
        shutil.move(os.path.join(brut, nom), os.path.join(contenu, nom))
    print("  wp-content : %s" % ", ".join(sorted(os.listdir(contenu))))

    print("--- remplacement de l'adresse ---")
    with open(sql, encoding="utf-8") as f:
        texte = f.read()
    texte, total, concernees, occurrences = adresse.remplace(texte, ancienne, nouvelle)
    print("  chaines serialisees : %d lues, %d contiennent l'adresse"
          % (total, concernees))
    verifiees, fausses = adresse.longueurs_coherentes(texte)
    if fausses:
        print("  ECHEC : %d longueurs serialisees fausses sur %d relues"
              % (fausses, verifiees))
        return 1
    print("  longueurs serialisees relues : %d justes sur %d" % (verifiees, verifiees))
    with open(sql, "w", encoding="utf-8") as f:
        f.write(texte)
    print("  %d occurrences remplacees" % occurrences)


    print("--- import dans MySQL ---")
    for commande in (
        ["mysql", "--socket=" + socket, "-u", "root", "-e",
         "drop database if exists %s; create database %s charset utf8mb4;" % (base, base)],
    ):
        subprocess.run(commande, check=True)
    with open(sql, "rb") as f:
        r = subprocess.run(["mysql", "--socket=" + socket, "-u", "root", base],
                           stdin=f, capture_output=True)
    if r.returncode:
        print("  ECHEC a l'import :")
        print(r.stderr.decode()[:2000])
        return 1
    r = subprocess.run(
        ["mysql", "--socket=" + socket, "-u", "root", base, "-N", "-e",
         "select count(*) from wp_posts where post_type='page' and post_status='publish';"
         "select option_value from wp_options where option_name='siteurl';"],
        capture_output=True, check=True)
    print("  " + r.stdout.decode().strip().replace("\n", "  |  "))
    print("\nRESTAURATION FAITE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
