# -*- coding: utf-8 -*-
"""Fabrique l'archive .wpress livree, au format All-in-One WP Migration.

Une archive .wpress est une suite d'entrees, chacune precedee d'un en-tete de
4377 octets : nom (255), taille (14), date (12), chemin (4096). La fin est
marquee par un en-tete entierement nul. La RACINE de l'archive est wp-content ;
database.sql et package.json sont a cote, hors du contenu.

Ce qui entre dans l'archive est NOMME ici, un fichier a la fois. En particulier
n'y entrent pas :

  - wp-content/db.php, le pilote SQLite du site de developpement. Sur
    l'hebergement du client, qui est en MySQL, ce fichier casserait le site
    avant meme la premiere page.
  - les extensions du site de developpement. L'import remplace tout le
    wp-content : le client repart avec un site sans extension, ce qui est
    exactement ce qu'on veut ici.

Usage : python3 paquet.py
"""
import json
import os
import shutil
import subprocess
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
WP = os.path.join(ICI, "wp")
PAQUET = os.path.join(ICI, "paquet")
THEME = os.path.join(WP, "wp-content", "themes", "equilibrium")
VERSION = "1.0.1"
ARCHIVE = os.path.join(ICI, "equilibrium-%s.wpress" % VERSION)
URL_DEV = "http://127.0.0.1:8881"

HDR = 4377
GARDE = "<?php\n// Silence is golden.\n"


def champ(valeur, taille):
    b = valeur.encode("utf-8")
    if len(b) > taille:
        raise ValueError("champ trop long : %r" % valeur)
    return b + b"\x00" * (taille - len(b))


def entete(nom, taille, mtime, prefixe):
    return (champ(nom, 255) + champ(str(taille), 14)
            + champ(str(int(mtime)), 12) + champ(prefixe, 4096))


def ecrire_archive(cible, contenu, racine_fichiers):
    """Ecrit l'archive.

    ATTENTION au rangement, c'est le seul detail du format qui ne se voit pas a
    la relecture : la RACINE de l'archive est wp-content lui-meme. Les entrees
    portent donc « themes/equilibrium », jamais « wp-content/themes/... ».
    Avec le prefixe en trop, l'import deposerait le theme dans
    wp-content/wp-content et le site s'ouvrirait sans aucun style.

    `racine_fichiers` sont les fichiers ranges a cote du contenu (database.sql,
    package.json), au prefixe « . ».
    """
    n = 0
    with open(cible, "wb") as sortie:
        for chemin in racine_fichiers:
            taille = os.path.getsize(chemin)
            sortie.write(entete(os.path.basename(chemin), taille,
                                os.path.getmtime(chemin), "."))
            with open(chemin, "rb") as f:
                shutil.copyfileobj(f, sortie, 1 << 20)
            n += 1
        for dossier, _sd, fichiers in sorted(os.walk(contenu)):
            prefixe = os.path.relpath(dossier, contenu).replace(os.sep, "/")
            for nom in sorted(fichiers):
                chemin = os.path.join(dossier, nom)
                taille = os.path.getsize(chemin)
                sortie.write(entete(nom, taille, os.path.getmtime(chemin), prefixe))
                with open(chemin, "rb") as f:
                    shutil.copyfileobj(f, sortie, 1 << 20)
                n += 1
        sortie.write(b"\x00" * HDR)
    return n


def version_wordpress():
    """La version reelle de WordPress, lue dans son fichier — pas ecrite a la
    main : une version fausse dans package.json ferait mentir l'archive sur ce
    qu'elle contient."""
    with open(os.path.join(WP, "wp-includes", "version.php"), encoding="utf-8") as f:
        for ligne in f:
            if ligne.startswith("$wp_version"):
                return ligne.split("'")[1]
    raise RuntimeError("version de WordPress introuvable")


def main():
    if not os.path.isdir(THEME):
        print("theme absent : lancer build_theme.py d'abord")
        return 1

    if os.path.isdir(PAQUET):
        shutil.rmtree(PAQUET)
    contenu = os.path.join(PAQUET, "wp-content")
    for d in ("themes", "plugins", "uploads"):
        os.makedirs(os.path.join(contenu, d))
        with open(os.path.join(contenu, d, "index.php"), "w", encoding="utf-8") as f:
            f.write(GARDE)
    with open(os.path.join(contenu, "index.php"), "w", encoding="utf-8") as f:
        f.write(GARDE)
    shutil.copytree(THEME, os.path.join(contenu, "themes", "equilibrium"))

    print("--- base de donnees ---")
    sql = os.path.join(PAQUET, "database.sql")
    r = subprocess.run(["php", os.path.join(ICI, "dump.php"), WP, sql],
                       capture_output=True)
    sys.stdout.write(r.stdout.decode())
    if r.returncode:
        sys.stderr.write(r.stderr.decode())
        return 1

    paquet_json = {
        "SiteURL": URL_DEV,
        "HomeURL": URL_DEV,
        "Plugin": {"Version": "7.78"},
        "WordPress": {
            "Version": version_wordpress(),
            "Content": contenu,
            "Plugins": os.path.join(contenu, "plugins"),
            "Themes": os.path.join(contenu, "themes"),
            "Uploads": os.path.join(contenu, "uploads"),
            "UploadsURL": URL_DEV + "/wp-content/uploads",
        },
        "Database": {"Prefix": "wp_"},
    }
    with open(os.path.join(PAQUET, "package.json"), "w", encoding="utf-8") as f:
        json.dump(paquet_json, f)

    print("--- archive ---")
    # package.json D'ABORD, et ce n'est pas une question de gout. All-in-One WP
    # Migration valide un fichier televerse en lisant UNIQUEMENT le premier
    # en-tete de 4377 octets et en exigeant d'y trouver ce nom exact
    # (functions.php, ai1wm_is_filedata_supported). Avec database.sql en tete,
    # l'import s'arrete sur « Invalid file data » sans meme regarder le reste :
    # archive parfaite, porte fermee.
    n = ecrire_archive(ARCHIVE, contenu,
                       [os.path.join(PAQUET, "package.json"), sql])
    print("  %s" % ARCHIVE)
    print("  %d entrees, %d octets" % (n, os.path.getsize(ARCHIVE)))

    # Une archive qui contiendrait le pilote SQLite ou un jeton serait
    # inutilisable ou dangereuse : on relit ce qu'on vient d'ecrire au lieu de
    # supposer que la liste de copie etait juste.
    with open(ARCHIVE, "rb") as f:
        brut = f.read()
    for motif in (b"db.php", b"sqlite-database-integration",
                  b"ghp_", b"github_pat_", b"x-access-token"):
        if motif in brut:
            print("  ECHEC : l'archive contient %r" % motif)
            return 1
    print("  relue : ni pilote SQLite, ni jeton")

    # Le rangement, relu depuis l'archive ecrite. Ce controle existe parce que
    # restaure.py, qui lit ce que ce script ecrit, partage forcement sa
    # convention : il reconstruit fidelement un rangement faux sans rien
    # remarquer. Seule une regle enoncee a part peut le voir.
    prefixes = set()
    with open(ARCHIVE, "rb") as f:
        while True:
            h = f.read(HDR)
            if len(h) < HDR or h == b"\x00" * HDR:
                break
            taille = int(h[255:269].rstrip(b"\x00") or 0)
            prefixes.add(h[281:HDR].rstrip(b"\x00").decode("utf-8"))
            f.seek(taille, 1)
    if any(p == "wp-content" or p.startswith("wp-content/") for p in prefixes):
        print("  ECHEC : la racine de l'archive doit ETRE wp-content, pas le contenir")
        return 1
    if "themes/equilibrium" not in prefixes or "." not in prefixes:
        print("  ECHEC : rangement inattendu : %s" % sorted(prefixes))
        return 1
    print("  rangement : racine = wp-content (%d prefixes)" % len(prefixes))

    # La porte d'entree du plugin, relue depuis l'archive ecrite. La regle est
    # enoncee ici telle que le plugin l'applique, et pas deduite de la facon
    # dont ce script range les entrees : c'est tout l'interet du controle.
    with open(ARCHIVE, "rb") as f:
        premier = f.read(255).rstrip(b"\x00").decode("utf-8")
    if premier != "package.json":
        print("  ECHEC : premiere entree = %r, All-in-One WP Migration exige "
              "package.json et refusera l'archive" % premier)
        return 1
    print("  premiere entree : package.json (ce que le plugin verifie)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
