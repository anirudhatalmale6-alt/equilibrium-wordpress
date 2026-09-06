# -*- coding: utf-8 -*-
"""Remplace une adresse de site dans un dump SQL, longueurs serialisees comprises.

Ce code est ecrit une seule fois et partage par restaure.py (qui refait ce que
fait All-in-One WP Migration a l'import) et par updraft.py (qui fabrique la
sauvegarde UpdraftPlus). Deux copies auraient derive : celle qu'on corrige et
celle qu'on oublie.

Le point delicat : une chaine PHP serialisee porte sa longueur devant elle,
s:19:"...". Remplacer l'adresse sans corriger la longueur ne casse rien de
visible dans le fichier — c'est PHP qui, plus tard, refuse de deserialiser et
rend une option vide, en silence.

Le piege du piege, et c'est pour lui que ce fichier ne se contente pas d'une
expression reguliere : dans un dump SQL, la valeur est ECHAPPEE. Une chaine
qui contient du HTML porte donc des \\" a l'interieur d'elle-meme :

    s:154:\\"<!-- wp:group --><div class=\\"wp-block-group\\">...\\"

Un motif qui cherche « du texte sans antislash entre deux \\" » s'arrete au
premier guillemet interne : il lit une valeur de 28 caracteres la ou elle en
fait 154, et si l'adresse se trouvait dans ces 28 premiers caracteres, la
« correction » de longueur ecrirait s:28 sur une chaine de 154 octets. Le
fichier deviendrait illisible pour PHP a l'endroit precis qu'on croyait
reparer.

On ne devine donc pas la fin de la chaine : on la COMPTE, en octets reels,
comme le fait PHP. La longueur declaree sert de guide, et le guillemet fermant
attendu a l'arrivee sert de preuve que le compte etait bon.

Auto-test : python3 adresse.py
"""

# Echappement produit par dump.php (eq_sql), qui est celui de MySQL.
DESECHAPPE = {'\\': '\\', "'": "'", '"': '"', 'n': '\n', 'r': '\r',
              '0': '\x00', 'Z': '\x1a'}
ECHAPPE = {'\\': '\\\\', "'": "\\'", '"': '\\"', '\n': '\\n',
           '\r': '\\r', '\x00': '\\0', '\x1a': '\\Z'}


def echappe(valeur):
    return ''.join(ECHAPPE.get(c, c) for c in valeur)


def _lit_chaine(texte, i, n, echappee):
    """Lit n OCTETS de valeur a partir de i, en desechappant au passage.

    Rend (valeur, i_apres) ou (None, None) si le compte ne tombe pas juste —
    c'est-a-dire si la longueur declaree est fausse ou si le fichier est
    tronque."""
    octets = 0
    morceaux = []
    while octets < n and i < len(texte):
        c = texte[i]
        if echappee and c == '\\' and i + 1 < len(texte):
            suivant = texte[i + 1]
            c = DESECHAPPE.get(suivant, suivant)
            i += 2
        else:
            i += 1
        morceaux.append(c)
        octets += len(c.encode('utf-8'))
    if octets != n:
        return None, None
    return ''.join(morceaux), i


def chaines(texte):
    """Parcourt les chaines serialisees du texte.

    Rend des tuples (debut, fin, n_declare, valeur, ferme_correctement) ou
    debut/fin encadrent la sequence complete s:N:"...".
    """
    i = 0
    while True:
        i = texte.find('s:', i)
        if i < 0:
            return
        j = i + 2
        chiffres = ''
        while j < len(texte) and texte[j].isdigit():
            chiffres += texte[j]
            j += 1
        if not chiffres or j >= len(texte) or texte[j] != ':':
            i += 2
            continue
        j += 1
        if texte.startswith('\\"', j):
            echappee, ouvre = True, 2
        elif texte.startswith('"', j):
            echappee, ouvre = False, 1
        else:
            i += 2
            continue
        n = int(chiffres)
        valeur, apres = _lit_chaine(texte, j + ouvre, n, echappee)
        if valeur is None:
            yield i, j + ouvre, n, None, False
            i = j + ouvre
            continue
        ferme = texte.startswith('\\"' if echappee else '"', apres)
        fin = apres + (2 if echappee else 1) if ferme else apres
        yield i, fin, n, valeur, ferme
        i = fin


def remplace(texte, ancienne, nouvelle):
    """Rend (texte, chaines_vues, chaines_touchees, occurrences_remplacees).

    Les occurrences hors chaine serialisee sont remplacees telles quelles ;
    celles a l'interieur d'une chaine entrainent la reecriture de la longueur.
    """
    sortie = []
    curseur = 0
    vues = 0
    touchees = 0
    occurrences = 0
    for debut, fin, n, valeur, ferme in chaines(texte):
        if valeur is None or not ferme:
            continue
        vues += 1
        if ancienne not in valeur:
            continue
        touchees += 1
        occurrences += valeur.count(ancienne)
        neuve = valeur.replace(ancienne, nouvelle)
        echappee = texte.startswith('\\"', debut + len('s:%d:' % n))
        guillemet = '\\"' if echappee else '"'
        corps = echappe(neuve) if echappee else neuve
        sortie.append(texte[curseur:debut])
        sortie.append('s:%d:%s%s%s' % (len(neuve.encode('utf-8')), guillemet,
                                       corps, guillemet))
        curseur = fin
    sortie.append(texte[curseur:])
    texte = ''.join(sortie)

    # Le reste du fichier : les URL qui ne sont pas dans une chaine serialisee
    # (colonnes ordinaires, GUID, contenu des articles).
    occurrences += texte.count(ancienne)
    texte = texte.replace(ancienne, nouvelle)
    return texte, vues, touchees, occurrences


def longueurs_coherentes(texte):
    """Relit le resultat. Rend (relues, fausses) : une chaine est fausse si le
    nombre d'octets annonce ne mene pas exactement au guillemet fermant."""
    relues = 0
    fausses = 0
    for _debut, _fin, _n, valeur, ferme in chaines(texte):
        relues += 1
        if valeur is None or not ferme:
            fausses += 1
    return relues, fausses


def _autotest():
    """Le controle qui manquait la premiere fois : un cas ou la valeur contient
    ses propres guillemets echappes, et un controle positif qui prouve que la
    verification SAIT echouer."""
    url = 'http://127.0.0.1:8881'
    html = '<div class="a">%s/x</div>' % url          # contient " et l'adresse
    dump = 'a:1:{s:7:\\"content\\";s:%d:\\"%s\\";}' % (
        len(html.encode()), echappe(html))

    relues, fausses = longueurs_coherentes(dump)
    assert (relues, fausses) == (2, 0), (relues, fausses)

    neuf, vues, touchees, occ = remplace(dump, url, 'https://exemple.test')
    assert vues == 2 and touchees == 1 and occ == 1, (vues, touchees, occ)
    relues, fausses = longueurs_coherentes(neuf)
    assert (relues, fausses) == (2, 0), (relues, fausses)
    valeurs = [v for _d, _f, _n, v, _c in chaines(neuf)]
    attendu = html.replace(url, 'https://exemple.test')
    assert valeurs[1] == attendu, valeurs[1]

    # Controle positif : une longueur fausse doit etre vue.
    casse = neuf.replace('s:%d:' % len(attendu.encode()), 's:5:')
    relues, fausses = longueurs_coherentes(casse)
    assert fausses == 1, (relues, fausses)

    # Controle positif : l'ancien motif naif se trompait sur ce cas.
    import re
    naif = re.findall(r's:(\d+):\\"([^\\]*?)\\"', dump)
    assert any(int(n) != len(v.encode()) for n, v in naif), \
        "le cas de test ne reproduit plus le piege"

    print("adresse.py : auto-test OK (%d chaines, guillemets internes compris)"
          % relues)


if __name__ == '__main__':
    _autotest()
