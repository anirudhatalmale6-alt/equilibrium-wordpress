# -*- coding: utf-8 -*-
"""Compare le RENDU des deux versions, pas leur code source.

verifie.py lit du HTML. Celui-ci ouvre les deux sites dans un vrai Chromium, a
la meme largeur, et compare les images pixel a pixel. Une feuille de style qui
ne se charge pas, une regle qui ne s'applique plus, un SVG absent : cela ne se
voit qu'ici. Lire la feuille de style ne dit jamais quelle regle a gagne.

On compare la premiere fenetre de chaque page. Jamais la page entiere : une
capture de page longue depasse les limites de taille et ne se lit plus.

    python3 visuel.py                 comparer les deux sites
    python3 visuel.py --mutation      prouver que la comparaison PEUT echouer

EQ_WP permet de relancer exactement la meme comparaison contre le site RESTAURE
depuis l'archive livree, et pas seulement contre celui de developpement : c'est
l'artefact livre qu'il faut regarder, pas sa source.
"""
import os
import shutil
import sys

from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(ICI, "captures")
WP = os.environ.get("EQ_WP", "http://127.0.0.1:8881").rstrip("/")
ST = os.environ.get("EQ_STATIQUE", "http://127.0.0.1:8882").rstrip("/")
SUFFIXE = os.environ.get("EQ_SUFFIXE", "")
CSS = os.path.join(ICI, "wp", "wp-content", "themes", "equilibrium", "assets", "site.css")

# (nom, chemin WordPress, chemin statique)
PAGES = [
    ("accueil",     "/",             "/index.html"),
    ("principes",   "/principles/",  "/principles.html"),
    ("mouvement",   "/movement/",    "/movement.html"),
    ("rejoindre",   "/join/",        "/join.html"),
    ("services",    "/services/",    "/services.html"),
    ("lobbying",    "/lobbying/",    "/lobbying.html"),
    ("cercle",      "/circle/",      "/circle.html"),
    ("portail",     "/portal/",      "/portal.html"),
    ("espace",      "/portal-area/", "/portal-area.html"),
]

LARGEURS = [(1280, 720), (390, 720)]
SEUIL = 0.20        # en pour cent de pixels differents

ok = True


def v(cond, msg):
    global ok
    print(("  OK    " if cond else "  ECHEC ") + msg)
    if not cond:
        ok = False


def capture(page, url, chemin):
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(400)
    page.screenshot(path=chemin)


def ecart(a, b):
    """Proportion de pixels qui different, en pour cent."""
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return 100.0
    diff = ImageChops.difference(ia, ib)
    # un pixel compte comme different des qu'un canal s'ecarte de plus de 8
    boite = diff.point(lambda p: 255 if p > 8 else 0).convert("L")
    return 100.0 * sum(1 for p in boite.getdata() if p) / (ia.size[0] * ia.size[1])


def compare(nav, pages=None, bruyant=True):
    """Renvoie l'ecart maximum mesure sur l'ensemble des comparaisons."""
    pire = 0.0
    # Un CONTEXTE neuf a chaque passage, et pas seulement un onglet neuf : les
    # contextes ont leur propre cache. Sans cela, le banc de mutation
    # remesurerait la feuille de style d'avant la mutation et conclurait que la
    # comparaison ne detecte rien — un faux vert, le pire des resultats.
    for largeur, hauteur in LARGEURS:
        ctx = nav.new_context(viewport={"width": largeur, "height": hauteur})
        page = ctx.new_page()
        for nom, wp, st in (pages or PAGES):
            a = os.path.join(SORTIE, "%s-%d-wp%s.png" % (nom, largeur, SUFFIXE))
            b = os.path.join(SORTIE, "%s-%d-statique%s.png" % (nom, largeur, SUFFIXE))
            capture(page, WP + wp, a)
            capture(page, ST + st, b)
            e = ecart(a, b)
            pire = max(pire, e)
            if bruyant:
                v(e < SEUIL, "%-11s %4dpx  ecart %.3f %%" % (nom, largeur, e))
        page.close()
        ctx.close()
    return pire


def mutation(nav):
    """Le banc de mutation : un controle vert ne vaut rien si on n'a pas montre
    qu'il peut virer au rouge. On casse une seule regle de couleur du theme, on
    remesure, puis on restaure et on remesure une derniere fois."""
    sauvegarde = CSS + ".sauvegarde"
    shutil.copy2(CSS, sauvegarde)
    try:
        with open(CSS, encoding="utf-8") as f:
            css = f.read()
        # le fond du site, defini une seule fois
        mute = css.replace("#07080A", "#3A0A0A", 1)
        if mute == css:
            print("  ECHEC la mutation n'a rien change dans la feuille de style")
            return False
        with open(CSS, "w", encoding="utf-8") as f:
            f.write(mute)
        e = compare(nav, pages=PAGES[:1], bruyant=False)
        print("  fond du site altere        -> ecart %.3f %%" % e)
        casse = e >= SEUIL
    finally:
        shutil.move(sauvegarde, CSS)
    r = compare(nav, pages=PAGES[:1], bruyant=False)
    print("  feuille de style restauree -> ecart %.3f %%" % r)
    v(casse, "la comparaison DETECTE une regle de couleur changee")
    v(r < SEUIL, "et redevient verte une fois la regle remise")
    return casse and r < SEUIL


def main():
    os.makedirs(SORTIE, exist_ok=True)
    with sync_playwright() as p:
        nav = p.chromium.launch()
        if "--mutation" in sys.argv:
            print("\nBANC DE MUTATION")
            mutation(nav)
        else:
            print("\n%d pages x %d largeurs" % (len(PAGES), len(LARGEURS)))
            compare(nav)
        nav.close()
    print("\n" + ("LE RENDU EST IDENTIQUE" if ok else "DES PAGES DIFFERENT"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
