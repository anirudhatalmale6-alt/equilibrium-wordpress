# -*- coding: utf-8 -*-
"""Remet package.json en PREMIERE entree d'une archive .wpress.

Pourquoi ce script existe. All-in-One WP Migration valide un fichier televerse
en lisant UNIQUEMENT le premier en-tete de 4377 octets, et en exigeant que le
nom qui s'y trouve soit exactement « package.json » :

    if ( AI1WM_PACKAGE_NAME === trim( $file_data['filename'] ) ) return true;
    ...sinon : "Invalid file data. Please ensure your file is a .wpress backup"

(all-in-one-wp-migration/functions.php, ai1wm_is_filedata_supported, appelee
par lib/model/import/class-ai1wm-import-upload.php). L'archive livree avait
database.sql en premier : le contenu etait bon, l'ordre ne l'etait pas.

Ce script NE RECONSTRUIT RIEN. Il relit les entrees de l'archive existante et
les recopie octet pour octet dans un nouvel ordre. Reconstruire le site pour
corriger un ordre ferait repasser tout le contenu par la case depart, et
chacune des corrections deja faites redeviendrait une hypothese.

Usage : python3 reordonne.py source.wpress cible.wpress
"""
import os
import sys

HDR = 4377
FIN = b"\x00" * HDR


def entrees(chemin):
    """Rend (en-tete, contenu) pour chaque entree, sans rien interpreter du
    contenu : ce qui entre ressort identique."""
    with open(chemin, "rb") as f:
        while True:
            h = f.read(HDR)
            if len(h) < HDR:
                raise ValueError("archive tronquee : %d octets d'en-tete" % len(h))
            if h == FIN:
                return
            taille = int(h[255:269].rstrip(b"\x00") or 0)
            corps = f.read(taille)
            if len(corps) != taille:
                raise ValueError("entree tronquee : %d octets sur %d"
                                 % (len(corps), taille))
            yield h, corps


def nom(h):
    return h[:255].rstrip(b"\x00").decode("utf-8")


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    source, cible = sys.argv[1], sys.argv[2]

    liste = list(entrees(source))
    noms = [nom(h) for h, _ in liste]
    if "package.json" not in noms:
        print("ECHEC : l'archive ne contient aucun package.json")
        return 1
    if noms[0] == "package.json":
        print("rien a faire : package.json est deja la premiere entree")
        return 0

    premier = [e for e in liste if nom(e[0]) == "package.json"]
    reste = [e for e in liste if nom(e[0]) != "package.json"]
    with open(cible, "wb") as sortie:
        for h, corps in premier + reste:
            sortie.write(h)
            sortie.write(corps)
        sortie.write(FIN)

    # Relecture. Deux choses a prouver, et la deuxieme compte autant que la
    # premiere : que package.json est passe devant, ET que rien d'autre n'a
    # bouge. Un reordonnancement qui perdrait une entree en chemin passerait le
    # premier controle sans probleme.
    apres = list(entrees(cible))
    if nom(apres[0][0]) != "package.json":
        print("ECHEC : package.json n'est pas en tete apres reecriture")
        return 1
    if len(apres) != len(liste):
        print("ECHEC : %d entrees avant, %d apres" % (len(liste), len(apres)))
        return 1
    avant_set = sorted((nom(h), len(c), h[269:281], h[281:]) for h, c in liste)
    apres_set = sorted((nom(h), len(c), h[269:281], h[281:]) for h, c in apres)
    if avant_set != apres_set:
        print("ECHEC : le jeu d'entrees a change (nom, taille, date ou chemin)")
        return 1
    octets_avant = sum(len(c) for _, c in liste)
    octets_apres = sum(len(c) for _, c in apres)
    if octets_avant != octets_apres:
        print("ECHEC : %d octets de contenu avant, %d apres"
              % (octets_avant, octets_apres))
        return 1

    print("%s" % cible)
    print("  %d entrees, %d octets de contenu, identiques a la source"
          % (len(apres), octets_apres))
    print("  ordre : %s" % ", ".join(nom(h) for h, _ in apres[:3]))
    print("  taille du fichier : %d octets" % os.path.getsize(cible))
    return 0


if __name__ == "__main__":
    sys.exit(main())
