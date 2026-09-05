# -*- coding: utf-8 -*-
"""Compare le rendu WordPress au rendu de la version statique deja verifiee.

Le site statique a passe sa propre suite (1354 controles). La question ici
n'est donc pas « est-ce que le site est bon » mais « est-ce que WordPress rend
EXACTEMENT la meme chose ». C'est une comparaison rendu contre rendu, apres
avoir ramene les deux a une forme canonique — seules les URL s'ecrivent
differemment, et elles seules.

Ce que ce banc regarde, page par page : le contenu de <main> caractere par
caractere, l'en-tete, le pied de page, le titre du document, la meta
description, le marqueur de page courante, l'absence de tout appel sortant et
l'absence de script.

Usage :
    python3 verifie.py
    EQ_WP=http://... EQ_STATIQUE=http://... python3 verifie.py
"""
import html as htmllib
import os
import re
import sys
import urllib.error
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(ICI), "equilibrium"))
import contenu  # noqa: E402  le texte de reference, dont la declaration citee

WP = os.environ.get("EQ_WP", "http://127.0.0.1:8881").rstrip("/")
ST = os.environ.get("EQ_STATIQUE", "http://127.0.0.1:8882").rstrip("/")

PAGES = [
    ("home",        "index.html",       "",             "statement"),
    ("principles",  "principles.html",  "principles/",  "principles"),
    ("movement",    "movement.html",    "movement/",    "movement"),
    ("join",        "join.html",        "join/",        "join"),
    ("services",    "services.html",    "services/",    "services"),
    ("lobbying",    "lobbying.html",    "lobbying/",    "lobbying"),
    ("circle",      "circle.html",      "circle/",      "circle"),
    ("portal",      "portal.html",      "portal/",      "portal"),
    ("portal-area", "portal-area.html", "portal-area/", "circle"),
]

ASSETS = ("site.css", "mark.svg", "seal.svg", "multipolar.svg", "wall.svg",
          "hero.svg", "hero-practice.svg", "p-balance.svg", "p-diplomacy.svg",
          "p-economy.svg", "p-sovereignty.svg", "p-stability.svg")

_ok = 0
_ko = []


def verifie(intitule, condition, detail=""):
    global _ok
    if condition:
        _ok += 1
        print("  ok    %s" % intitule)
    else:
        _ko.append(intitule)
        print("  ECHEC %s   %s" % (intitule, detail))


def prend(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return r.getcode(), r.read().decode("utf-8")


def code_de(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return r.getcode()
    except urllib.error.HTTPError as e:
        return e.code


def canon(page, cote):
    """Ramene les deux versions a la meme ecriture des URL et des espaces.

    C'est la SEULE difference qu'on s'autorise a effacer. Tout le reste — un
    mot, un attribut, une classe, un espace insecable — doit se voir.
    """
    if cote == "wp":
        page = page.replace(WP + "/wp-content/themes/equilibrium/assets/", "ASSET:")
        page = re.sub(re.escape(WP) + r"/([a-z][a-z\-]*)/", r"PAGE:\1", page)
        page = page.replace(WP + "/", "PAGE:home").replace(WP, "PAGE:home")
    else:
        page = re.sub(r"(?:\./)?assets/", "ASSET:", page)
        page = re.sub(r"\b([a-z][a-z\-]*)\.html",
                      lambda m: "PAGE:" + ("home" if m.group(1) == "index" else m.group(1)),
                      page)
    page = re.sub(r"\?(?:v|ver)=[0-9A-Za-z.\-]+", "", page)   # ?v=7 / ?ver=1.0.0
    page = re.sub(r"\s+", " ", page)
    page = re.sub(r">\s+<", "><", page)
    return page.strip()


def region(page, debut, fin):
    i = page.index(debut)
    j = page.index(fin, i) + len(fin)
    return page[i:j]


def entete(page):
    return region(page, '<div class="demo">', "</header>")


def pied(page):
    return region(page, '<footer class="ft">', "</footer>")


def principal(page):
    i = page.index(">", page.index("<main")) + 1
    return page[i:page.index("</main>")]


def titre(page):
    return re.search(r"<title>(.*?)</title>", page, re.S).group(1).strip()


def description(page):
    m = re.search(r'<meta name="description" content="([^"]*)"', page)
    return m.group(1) if m else ""


def premiere_difference(a, b):
    """Ou exactement les deux versions divergent. Un « c'est different » sans
    l'endroit oblige a relire deux pages entieres a l'oeil."""
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return "col %d : wp %r / statique %r" % (i, a[i:i + 70], b[i:i + 70])
    if len(a) != len(b):
        return "longueurs %d vs %d, suite : %r" % (len(a), len(b), (a or b)[n:n + 70])
    return ""


def main():
    print("\n1. LES 9 PAGES : WORDPRESS REND-IL LA MEME CHOSE QUE LE STATIQUE ?")
    for cle, fichier, chemin, nav in PAGES:
        print("\n  -- %s" % cle)
        cw, pw = prend("%s/%s" % (WP, chemin))
        cs, ps = prend("%s/%s" % (ST, fichier))
        verifie("%-12s repond 200" % cle, cw == 200 and cs == 200, "%s / %s" % (cw, cs))

        verifie("%-12s titre du document identique" % cle,
                titre(pw) == titre(ps), "%r vs %r" % (titre(pw), titre(ps)))
        verifie("%-12s meta description identique" % cle,
                description(pw) == description(ps),
                "%r vs %r" % (description(pw)[:60], description(ps)[:60]))

        aw, as_ = canon(principal(pw), "wp"), canon(principal(ps), "st")
        verifie("%-12s <main> identique caractere par caractere" % cle,
                aw == as_, premiere_difference(aw, as_))

        hw, hs = canon(entete(pw), "wp"), canon(entete(ps), "st")
        verifie("%-12s en-tete identique" % cle, hw == hs, premiere_difference(hw, hs))

        fw, fs = canon(pied(pw), "wp"), canon(pied(ps), "st")
        verifie("%-12s pied de page identique" % cle, fw == fs, premiere_difference(fw, fs))

        # Aucun appel sortant : c'etait la regle de la version statique, et
        # WordPress est precisement le genre d'outil qui en ajoute tout seul.
        dehors = [u for u in re.findall(r'(?:src|href)="(https?://[^"]+)"', pw)
                  if not u.startswith(WP)]
        verifie("%-12s aucune ressource hors du domaine" % cle, not dehors, str(dehors[:3]))
        verifie("%-12s aucun script" % cle, "<script" not in pw,
                pw[pw.find("<script"):pw.find("<script") + 90] if "<script" in pw else "")

        # Le marqueur de page courante : exactement un DANS L'EN-TETE, et sur
        # le bon element. On ne cherche pas dans la page entiere : l'espace
        # membre a ses propres onglets, qui portent legitimement un
        # aria-current, et le site statique fait pareil.
        marques = re.findall(r'<a[^>]*aria-current="page"[^>]*>(.*?)</a>', entete(pw), re.S)
        attendu = {"statement": "Statement", "principles": "Principles",
                   "movement": "The movement", "join": "Join", "services": "Services",
                   "lobbying": "Lobbying", "circle": "Circle",
                   "portal": "Member sign-in"}[nav]
        verifie("%-12s page courante marquee sur « %s »" % (cle, attendu),
                len(marques) == 1 and marques[0].strip() == attendu, str(marques))

    print("\n2. LES RESSOURCES DU THEME REPONDENT")
    for nom in ASSETS:
        u = "%s/wp-content/themes/equilibrium/assets/%s" % (WP, nom)
        verifie("asset %-20s 200" % nom, code_de(u) == 200)

    print("\n3. LA DECLARATION EST CITEE MOT POUR MOT")
    # C'est l'affirmation centrale du site : sa parole est citee, tout le reste
    # est de la redaction. Une conversion de CMS qui abime une citation abime
    # la seule chose que le site promet de ne pas toucher.
    _, accueil = prend(WP + "/")
    texte = re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", principal(accueil))))
    for i, para in enumerate(contenu.DECLARATION, 1):
        attendu_p = re.sub(r"\s+", " ", htmllib.unescape(para)).strip()
        verifie("declaration, paragraphe %d present mot pour mot" % i,
                attendu_p in texte, attendu_p[:70])

    print("\n4. CE QUE WORDPRESS AJOUTE DE LUI-MEME, ET QU'ON A RETIRE")
    for motif, quoi in (("wp-emoji", "le script des emoji"),
                        ("wp-json", "le lien vers l'API REST"),
                        ("oembed", "la decouverte oEmbed"),
                        ('name="generator"', "la version de WordPress"),
                        ("wp-block-library", "la feuille de style des blocs")):
        verifie("absent de l'accueil : %s" % quoi, motif not in accueil, motif)

    print("\n5. ADRESSES")
    verifie("l'accueil du site est bien la declaration",
            "Balance rather than domination" in accueil)
    verifie("une adresse inconnue rend un 404",
            code_de(WP + "/cette-page-n-existe-pas/") == 404)
    verifie("le site est en preproduction (noindex)",
            "noindex" in accueil)

    total = _ok + len(_ko)
    print("\n" + "=" * 66)
    print("%d controles sur %d passent." % (_ok, total))
    if _ko:
        print("ECHECS :")
        for k in _ko:
            print("  - %s" % k)
        return 1
    print("Aucun echec.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
