# Equilibrium — version WordPress

Le site Equilibrium, livré en WordPress, sous la forme d'une archive `.wpress`
importable par All-in-One WP Migration.

C'est le **même site** que la version statique déjà livrée : mêmes 9 pages,
même texte, même mise en page, mêmes couleurs. La seule différence est qu'il
est désormais administrable.

**Fichier à installer : `equilibrium-1.0.1.wpress` (401 Ko).**

L'archive elle-même n'est pas dans ce dépôt : elle contient la base du site,
donc le compte d'administration et l'empreinte de son mot de passe. Elle est
envoyée dans le fil de discussion, pas publiée. Ce dépôt contient tout le
reste — le thème, les scripts qui le fabriquent et ceux qui le vérifient.

---

## Avant d'installer — la seule chose qui peut faire des dégâts

Un `.wpress` n'est pas un ajout, c'est un **remplacement complet**. À l'import,
All-in-One WP Migration **efface la base de données et tout le `wp-content`**
du site cible avant d'écrire les siens.

Il s'installe donc :

- sur le WordPress **neuf** d'`equilibriumcircle.com`, ou
- sur un **sous-domaine dédié**,

et **jamais** par-dessus un site qui contient déjà quoi que ce soit.

## Installation

1. Sur le WordPress cible, installer l'extension **All-in-One WP Migration**.
2. `All-in-One WP Migration` → `Import` → `Import From` → `File`, puis choisir
   `equilibrium-1.0.1.wpress`.
3. Confirmer l'écrasement quand l'extension le demande.
4. À la fin, l'extension demande d'enregistrer deux fois les permaliens :
   `Réglages` → `Permaliens` → `Enregistrer`. C'est ce qui remet les adresses
   propres (`/principles/`, `/lobbying/`…) en service.

L'adresse du site est réécrite automatiquement à l'import : rien à modifier à
la main dans la base.

## Après l'import — trois choses à faire tout de suite

1. **Changer le mot de passe.** Le compte livré est `equilibrium`. Son mot de
   passe est envoyé séparément dans le fil. `Utilisateurs` → `Profil`.
2. **Vérifier l'adresse d'administration.** Elle est réglée sur
   `admin@equilibriumcircle.com`. Cette boîte doit **exister** : sans elle,
   aucune récupération de mot de passe n'est possible le jour où elle servira.
3. **Rendre le site visible aux moteurs quand il sera prêt.** Il est livré en
   `Réglages` → `Lecture` → *demander aux moteurs de ne pas indexer ce site*,
   **coché**. C'est volontaire : les décisions ouvertes ne sont pas tranchées,
   et le bandeau de démonstration le dit encore en haut de chaque page.
   Décocher le jour du lancement, pas avant.

## Ce qui est modifiable, et où

| Ce que tu veux changer | Où |
|---|---|
| Le texte d'une page | `Pages` → la page → l'éditeur. Chaque section est un bloc. |
| L'ordre ou le libellé du menu | `Apparence` → `Menus`. Deux menus : navigation principale, pied de page. |
| Le sigle, le sceau, les figures | `wp-content/themes/equilibrium/assets/` — ce sont des SVG. |
| Les couleurs, les espacements | `wp-content/themes/equilibrium/assets/site.css` |
| Le bandeau de démonstration | `header.php` du thème, une seule ligne à supprimer. |
| Les trois clauses du pied de page | `footer.php` du thème. Elles sont là et **pas** dans une page exprès : elles disent que la déclaration est citée mot pour mot, qu'aucun statut n'est revendiqué, et que le mouvement et la pratique sont séparés. Une règle de gouvernance qui peut disparaître dans une modification de contenu ne vaut rien. |

Les neuf pages : `Statement` (accueil), `Principles`, `The movement`, `Join`,
`Services`, `Lobbying`, `Circle`, `Member sign-in`, `Member area`.

Le séparateur du menu, entre `Join` et `Services`, suit une **classe**
d'entrée de menu (`eq-sep`) et pas un rang : si tu réordonnes le menu dans
l'administration, il suit l'entrée à laquelle il est attaché.

## Ce que le thème ne fait pas, volontairement

- **Aucune requête sortante.** Pas de Google Fonts, pas de CDN, pas de mesure
  d'audience. C'était déjà la règle sur la version statique ; elle est tenue
  ici et vérifiée page par page.
- **Aucun script.** WordPress 6.8 ajoute de lui-même un
  `<script type="speculationrules">` qui fait précharger des pages par le
  navigateur : il est coupé. C'était le seul script qu'aurait porté un site
  qui n'en a aucun.
- **Aucun contenu inventé.** Rien n'a été ajouté ni retiré au texte livré. Les
  **39** mentions `To be decided` du site — dont les 22 du tableau des
  décisions — sont toujours là où elles étaient. (Compté sur le rendu, pas sur
  la source.)
- **Pas de commentaires**, désactivés sur tout le site.
- **Aucune extension livrée.** L'import remplace tout le `wp-content` : le site
  repart sans extension, ce qui est voulu.

## Comment cette version a été vérifiée

Le site statique avait déjà passé sa propre suite (1354 contrôles, mesurés à la
livraison de la version statique le 2 septembre 2026 ; non rejoués ici — le site
statique n'a pas changé depuis, il sert de référence). La question
n'était donc pas « est-ce que le site est bon » mais « est-ce que WordPress rend
**exactement** la même chose ». Trois contrôles, dans cet ordre :

1. **`verifie.py` — 106 contrôles.** Il compare, page par page, le HTML rendu
   par WordPress au HTML de la version statique, après avoir ramené les deux à
   une forme canonique — seules les URL s'écrivent différemment, et elles
   seules. Le contenu de `<main>` **caractère par caractère**, l'en-tête, le
   pied de page, le titre du document, la méta description, le marqueur de page
   courante, l'absence de tout appel sortant, l'absence de script, et les cinq
   paragraphes de la déclaration cités mot pour mot.

2. **`visuel.py` — 18 comparaisons d'images.** Les deux sites sont ouverts dans
   un vrai Chromium, à 1280 px et à 390 px, et les captures sont comparées
   pixel à pixel. Écart mesuré : **0,000 % sur les 18**. Le banc est éprouvé
   par mutation (`python3 visuel.py --mutation`) : une seule règle de couleur
   changée dans le thème fait monter l'écart à **3,47 %**, et le remettre le
   ramène à 0,000 %. Un contrôle vert veut donc dire quelque chose.

3. **`restaure.py` — la restauration pour de vrai.** Les deux contrôles
   ci-dessus tournent sur le WordPress de développement, qui est en SQLite à
   l'adresse où l'archive a été fabriquée. Deux choses n'y sont donc jamais
   éprouvées : est-ce que le `database.sql` est du vrai MySQL, et est-ce que le
   site survit au changement d'adresse. Ce script refait ce que fait All-in-One
   WP Migration — il ouvre l'archive livrée, remet `wp-content` en place,
   remplace l'ancienne adresse par une nouvelle, importe dans une base
   **MySQL 8 vierge** et sert le résultat. **Les 106 contrôles et les 18
   comparaisons d'images ont ensuite été relancés contre ce site-là**, et ce
   sont ces résultats qui comptent. La connexion à l'administration a été
   essayée sur ce site restauré, pas seulement supposée.

## Quatre défauts trouvés par cette comparaison

Aucun ne se voyait à l'œil nu.

1. **`wptexturize` remplaçait chaque apostrophe droite par `&#8217;` dans le
   RENDU.** Le texte stocké en base ne bouge pas : le défaut est invisible à la
   relecture du contenu, et seule la comparaison du rendu au rendu le voit.

2. **Le pied de page marquait lui aussi la page courante.** Deux
   `aria-current="page"` dans un même document, ce qui est une erreur
   d'accessibilité et pas une redondance sans effet. Le marqueur est désormais
   posé par la navigation principale seulement.

3. **WordPress fabriquait tout seul une classe `menu-pied-de-page-container`**
   autour du menu du pied, que la version statique n'a pas.

4. **La racine de l'archive doit ÊTRE `wp-content`, pas le contenir.** Ma
   première archive rangeait tout sous `wp-content/...`, ce qui aurait déposé
   le thème dans `wp-content/wp-content` — un site sans aucun style à l'import.
   `restaure.py` ne pouvait pas le voir : il lit ce que `paquet.py` écrit, donc
   il partage sa convention et reconstruit fidèlement un rangement faux.
   `paquet.py` porte maintenant un contrôle de rangement énoncé **à part**,
   qui relit l'archive écrite et refuse un préfixe `wp-content`.

## Les scripts

```bash
python3 build_theme.py            # fabrique le thème depuis le site statique
php seed.php ./wp ./pages.json    # crée les 9 pages et les 2 menus (idempotent)
python3 paquet.py                 # dump MySQL + archive .wpress
python3 verifie.py                # 106 contrôles  (les deux serveurs démarrés)
python3 visuel.py                 # 18 comparaisons d'images
python3 visuel.py --mutation      # prouve que la comparaison peut échouer
```

Le thème est **généré**. Ne jamais éditer `wp-content/themes/equilibrium` à la
main : relancer `build_theme.py`, puis `seed.php`.

## Ce qui reste ouvert

Les 22 décisions de la page `The movement` sont toujours ouvertes, et deux
d'entre elles bloquent tout le reste : **une personne morale ou deux ?** et
**quel pays ?** Aucune ne peut être tranchée par un site.

## 1.0.1 — pourquoi l'archive 1.0.0 était refusée à l'import

L'import de la 1.0.0 s'arrêtait sur :

> Invalid file data. Please ensure your file is a `.wpress` backup created with
> All-in-One WP Migration

Le contenu de l'archive était bon ; c'était l'**ordre des entrées** qui ne
l'était pas. All-in-One WP Migration valide un fichier téléversé en lisant
uniquement le **premier en-tête de 4377 octets** et en exigeant d'y trouver le
nom `package.json` :

```php
// all-in-one-wp-migration/functions.php — ai1wm_is_filedata_supported()
if ( AI1WM_PACKAGE_NAME === trim( $file_data['filename'] ) ) {
    return true;
}
```

La 1.0.0 avait `database.sql` en première entrée : le plugin refusait le fichier
sans jamais regarder le reste. Trois archives exportées par le plugin lui-même
(influus, revmetal, renosly) ont servi de témoin : dans les trois,
`package.json` est bien l'entrée n° 0.

La 1.0.1 contient **exactement les mêmes octets**, réordonnés : 26 entrées,
292 233 octets de contenu, même taille de fichier. Elle n'a pas été reconstruite
— `reordonne.py` recopie les entrées existantes sans les réinterpréter, pour ne
pas refaire passer le contenu déjà vérifié par la case départ.

Vérifications faites avant l'envoi, avec le code de ServMask et non le mien :

- `ai1wm_is_filedata_supported()` exécutée telle quelle : 1.0.0 **refusée**,
  1.0.1 **acceptée**, une archive du plugin acceptée (témoin) ;
- `Ai1wm_Extractor`, le vrai lecteur du plugin, déroule la 1.0.1 en entier :
  26 entrées, 292 233 octets, et les fichiers extraits sont identiques octet
  pour octet au thème et au dump d'origine.

`paquet.py` écrit désormais `package.json` en tête et relit l'archive pour le
vérifier ; le contrôle a été essayé sur la 1.0.0, où il échoue bien.
