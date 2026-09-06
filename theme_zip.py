# -*- coding: utf-8 -*-
"""Fabrique un .zip de THEME installable par WordPress lui-meme.

Pourquoi ce fichier existe a cote de updraft.py : les deux zips se ressemblent
mais ne s'adressent pas au meme lecteur.

  - backup_..._themes.zip est lu par UpdraftPlus. C'est une image du dossier
    wp-content/themes : il contient donc `equilibrium/` ET le `index.php`
    (« silence is golden ») qui vit a cote. C'est correct pour une restauration.

  - Le televerseur de themes de WordPress, lui, exige UNE SEULE entree a la
    racine de l'archive. WP_Upgrader::install_package() ne descend dans un
    sous-dossier que si dirlist() rend exactement un element :

        if ( 1 === count( $source_files ) && $wp_filesystem->is_dir( ... ) )

    Avec deux entrees, il prend la racine de l'archive comme source, puis
    Theme_Upgrader::check_package() ne trouve pas style.css a cet endroit et
    rend « The theme is missing the style.css stylesheet. »

Donc le zip de sauvegarde n'est PAS installable via Apparence > Themes, et ce
script produit celui qui l'est : une seule entree a la racine, le dossier du
theme. Le controle final est fait par le vrai Theme_Upgrader (installe_theme.php).

Usage : python3 theme_zip.py
"""
import hashlib
import os
import sys
import zipfile

ICI = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(ICI, "paquet", "wp-content", "themes", "equilibrium")
LIVRAISON = os.path.join(ICI, "updraft")
NOM = "equilibrium-theme-1.0.0.zip"


def main():
    if not os.path.isfile(os.path.join(SOURCE, "style.css")):
        print("ECHEC : %s/style.css introuvable" % SOURCE)
        return 1

    os.makedirs(LIVRAISON, exist_ok=True)
    cible = os.path.join(LIVRAISON, NOM)

    n = 0
    with zipfile.ZipFile(cible, "w", zipfile.ZIP_DEFLATED) as z:
        for dossier, _sd, fichiers in sorted(os.walk(SOURCE)):
            for nom in sorted(fichiers):
                chemin = os.path.join(dossier, nom)
                interne = "equilibrium/" + os.path.relpath(chemin, SOURCE).replace(os.sep, "/")
                z.write(chemin, interne)
                n += 1

    with zipfile.ZipFile(cible) as z:
        abime = z.testzip()
        if abime:
            print("ECHEC : entree abimee dans le zip : %s" % abime)
            return 1
        noms = z.namelist()
        racines = sorted({e.split("/")[0] for e in noms})

    print("%s : %d fichiers, %d octets" % (NOM, n, os.path.getsize(cible)))
    print("racine de l'archive : %s" % ", ".join(racines))
    if racines != ["equilibrium"]:
        print("ECHEC : le televerseur de themes exige UNE seule entree a la racine")
        return 1
    if "equilibrium/style.css" not in noms:
        print("ECHEC : style.css doit etre juste sous equilibrium/")
        return 1

    with open(cible, "rb") as f:
        print("md5 %s" % hashlib.md5(f.read()).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
