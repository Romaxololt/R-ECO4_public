# REX — Documentation complète

> Compilateur pour le langage **REX** (syntaxe inspirée de Python) qui se résout vers **REX-SL** (lui-même compilé vers C puis vers un exécutable).
>
> ```
> REX (.rex) --[REX.py]--> REX-SL (.rexsl) --[REX-SL.py]--> C (.c) --> exécutable
> ```
>
> - Version alpha du compilateur : `0.1.0`
> - Version REX-SL ciblée : `4.0.0` (générateur `REX-SL.py`, ligne de commande compatible avec `-f/--file`)
> - Compatible avec REX-SL `0.0.21`
> - Copyright (c) 2026 R-ECO4

---

## Sommaire

1. [Installation / utilisation en ligne de commande](#installation--utilisation-en-ligne-de-commande)
2. [Structure d'un fichier REX](#structure-dun-fichier-rex)
3. [Types](#types)
4. [Déclaration de variables (`var`)](#déclaration-de-variables-var)
5. [`None` / `none` / `null`](#none--none--null)
6. [Expressions](#expressions)
7. [Collections (list, tuple, set, dict)](#collections-list-tuple-set-dict)
8. [Indexation et slices à la Python](#indexation-et-slices-à-la-python)
9. [Fonctions](#fonctions)
10. [`func` comme objet (pointeurs de fonction)](#func-comme-objet-pointeurs-de-fonction)
11. [Fonctions natives (builtins)](#fonctions-natives-builtins)
12. [Affichage (`show`)](#affichage-show)
13. [Fichiers (lecture / écriture)](#fichiers-lecture--écriture)
14. [Conditions (`if` / `elif` / `else`)](#conditions-if--elif--else)
15. [Boucles (`repeat`, `while`, `for`)](#boucles-repeat-while-for)
16. [`break` / `continue`](#break--continue)
17. [Sauts explicites (`label` / `go`)](#sauts-explicites-label--go)
18. [Déballage de tuple](#déballage-de-tuple)
19. [List comprehensions](#list-comprehensions)
20. [Chaînes formatées (f-strings)](#chaînes-formatées-f-strings)
21. [Imports (`import`)](#imports-import)
22. [Modules avec espace de noms (`import ... as`)](#modules-avec-espace-de-noms-import--as)
23. [Retypage dynamique des variables](#retypage-dynamique-des-variables)
24. [Erreurs](#erreurs)
25. [Limitations connues (héritées de REX-SL)](#limitations-connues-héritées-de-rex-sl)
26. [Architecture interne du compilateur](#architecture-interne-du-compilateur)
27. [Historique des versions](#historique-des-versions)

---

## Installation / utilisation en ligne de commande

```
python REX.py -f script.rex -c -k -s -r
python REX.py -o "var x = 5; show(x)" -c -r
```

| Option              | Effet                                                                          |
|---------------------|---------------------------------------------------------------------------------|
| `-f`, `--file`      | fichier `.rex` source (doit commencer par le header `# REX>`)                  |
| `-o`, `--oneline`   | code REX passé directement en ligne de commande, instructions séparées par `;` |
| `-O`, `--output`    | nom de base du `.rexsl` / `.c` / exécutable généré (défaut : nom du fichier source, ou `rex_output` en mode `-o`) |
| `-c`, `--compiler`  | compile REX → REX-SL → C → exécutable                                          |
| `-r`, `--run`       | exécute l'exécutable généré (implique `-c`)                                    |
| `-k`, `--keep-c`    | conserve le `.c` intermédiaire au lieu de le supprimer                         |
| `-s`, `--keep-rsl`  | conserve le `.rexsl` intermédiaire au lieu de le supprimer                     |
| `-d`, `--debug`     | affiche les étapes internes (tokens, code REX-SL généré, ...)                  |

Sans `-c` ni `-r`, seul le `.rexsl` est généré/affiché (mode inspection).

`-o`/`--oneline` et `-f`/`--file` sont mutuellement exclusifs, et un des deux est obligatoire.

L'exécutable `REX-SL` (ou `REX-SL.exe` sous Windows) doit se trouver à côté du script/exécutable `REX` pour que `-c`/`-r` fonctionnent (il assure l'étape REX-SL → C → binaire).

---

## Structure d'un fichier REX

Un fichier `.rex` utilisé en mode `-f` doit commencer par un en-tête sur la première ligne non vide :

```
# REX>
```

(le format historique avec numéro de version, ex. `# REX> 0.0.5`, n'est plus requis depuis la 0.0.6 — seule la forme sans numéro `# REX>` est reconnue).

Le reste du fichier suit une syntaxe à la Python :

- indentation par espaces ou tabulations (1 tabulation = 4 espaces) pour délimiter les blocs (`if`, `while`, `for`, `func`, `repeat`, ...) — plus d'accolades `{}` pour les blocs de code ;
- `;` optionnel pour séparer plusieurs instructions sur une même ligne logique ;
- commentaires ligne `# ...` et commentaires bloc `#* ... *#` ;
- les sauts de ligne à l'intérieur de `(...)`/`[...]` sont ignorés (continuation implicite, comme en Python).

En mode `-o`/`--oneline`, aucun header ni indentation n'est nécessaire : tout tient sur une seule ligne, les instructions étant séparées par `;`.

---

## Types

```
number   float   bool   str   list   dict   set   tuple   func
```

`tuple` et `set` n'existent pas nativement en REX-SL : ils sont représentés en interne comme une `list` REX-SL. Le `set` est dédupliqué **à la compilation** pour ses éléments littéraux.

`func` est un pseudo-type utilisé uniquement pour déclarer une variable *pointeur de fonction* (`var func f = maFonction;`, voir plus bas) — en interne le compilateur le trace sous le nom `funcref`.

---

## Déclaration de variables (`var`)

```
var x                    # number, valeur par défaut 0
var x = 5                # type inféré
var x = (2 + 3) * 4      # expression complète (calcul, appel de fonction, ...)
var number x = 5         # type explicite
var list l = [1, 2, 3]   # collection, type explicite
var l = [1, 2, 3]        # collection, type inféré depuis le littéral
```

- Sans valeur : type par défaut `number`, valeur `0` (sauf si un type explicite est donné : valeur par défaut du type — `0.0` pour `float`, `false` pour `bool`, `""` pour `str`, collection vide pour `list`/`dict`/`set`/`tuple`).
- Avec valeur : le type est soit inféré depuis l'expression, soit vérifié contre le type explicite annoté (avec promotion `number` → `float` acceptée).

### Type explicite vs type inféré

- **Type explicite** (`var number x = 5`, `var list l = [...]`) : le type est **verrouillé**. Toute tentative ultérieure de changement de type sur cette variable lève une erreur de compilation.
- **Type inféré** (`var x = 5`, `var s = carre(i)`) : le type peut être **changé dynamiquement** par une réaffectation ultérieure (voir [Retypage dynamique](#retypage-dynamique-des-variables)).

---

## `None` / `none` / `null`

Depuis la 0.1.0, REX simule `None` à la Python (`None`, `none` et `null` sont strictement équivalents), bien que REX-SL n'ait aucun type nullable natif. Le mécanisme repose sur une valeur concrète + un **drapeau booléen caché** par variable.

```
var x = None              # x est "number" par défaut, marqué None
var list l = None         # collection marquée None
x = None                  # réassignation à None (efface le contenu selon le type)
if x is None:
    show("x est vide")
if x is not None:
    show("x a une valeur")
```

Comportements notables :

- `var <type> x = None;` est autorisé et déclare `x` avec la valeur par défaut du type, plus un drapeau interne marqué "None".
- `x = None;` (réaffectation) marque le drapeau sans changer le type.
- `x is None` / `x is not None` (ou `x == None` / `x != None`) sont reconnus dans les conditions (`if`/`while`/...).
- `show(x)` sur une variable actuellement `None` affiche `"None"`.
- `return None;` n'est **pas** supporté explicitement (une fonction sans aucun `return` textuel se comporte déjà comme si elle retournait `None` lorsqu'elle est appelée dans une expression).
- `None` n'est **pas** utilisable comme argument de fonction.
- `var func f = None;` (typage `func`) est refusé.

---

## Expressions

Opérateurs `+ - * / % **`, parenthèses, moins unaire, priorité standard :

```
niveau 0 (le + faible) : + -
niveau 1               : * / %
niveau 2 (le + fort)   : ** (exposant, associatif à droite)
```

Promotion automatique `number → float` dès qu'un `float` intervient dans une opération arithmétique.

`str` n'est valide qu'avec :
- `+` (concaténation `str + str`)
- `-` (suppression d'occurrences `str - str`)
- `*` (répétition `str * number`)

Exemples :
```
var x = (2 + 3) * 4        # 20
var y = 2 ** 10             # 1024
var z = 2 ** -1              # 0.5 (float)
var s = "ab" * 3             # "ababab"
```

---

## Collections (list, tuple, set, dict)

Littéraux de collection, syntaxe Python, utilisables comme valeur d'un `var` ou d'une réaffectation :

```
[1, 2, 3]                # list
(1, 2, 3)   ()   (x,)    # tuple (y compris tuple vide et singleton)
{1, 2, 3}                # set (dédupliqué à la compilation pour les éléments littéraux)
{"cle": 1, "autre": 2}   # dict (clés obligatoirement des chaînes littérales)
```

Restrictions :
- éléments de `list`/`tuple`/`set` : `number`/`float`/`str`/`bool` uniquement (limitation REX-SL : `append` n'accepte que ces types) ;
- clés de `dict` : toujours des chaînes **littérales** ;
- valeurs de `dict` : `number`/`float`/`str`/`bool` uniquement.

### Ajout d'éléments (`append`)

```
var l = [1, 2, 3]
append(l, 4)
```

`append(liste, valeur)` est une instruction autonome (pas utilisable dans une expression) qui délègue à l'opcode REX-SL `append`. Le type de la valeur doit rester cohérent avec le type d'élément déjà déterminé pour la liste (liste "homogène").

### Affichage d'une collection

`show(...)` sur une collection dont **tous les éléments sont des littéraux connus à la compilation** affiche sa représentation figée (capturée au moment de la déclaration). Une collection modifiée ensuite au runtime (via `append`, indexation, boucle, retour de fonction...) est sérialisée dynamiquement via les opcodes REX-SL `list_str`/`dict_str`.

---

## Indexation et slices à la Python

### Indexation générique `x[clé]`

```
var l = [10, 20, 30]
show(l[1])                 # 20

var d = {"a": 1, "b": 2}
show(d["a"])                # 1

var s = "bonjour"
show(s[0])                  # "b"
```

- `l[i]` (list/tuple/set) : l'index doit être `number`, le type d'élément doit être connu et homogène à la compilation.
- `d["cle"]` (dict) : la clé doit être `str`, le type de valeur doit être connu et homogène.
- `s[i]` (str) : sucre syntaxique pour `charat(s, i)`.

### Affectation indexée `x[clé] = valeur;`

```
l[0] = 99;
d["a"] = 42;
```

- Sur `dict` : délègue à l'opcode REX-SL `set`.
- Sur `list`/`tuple`/`set` : REX-SL n'a pas d'opcode dédié — l'écriture se fait via injection C directe (`scrc`), avec vérification de dépassement d'index à l'exécution.

### Slice `x[début:fin]` (str uniquement)

```
var s = "bonjour"
show(s[:3])       # "bon"
show(s[3:])       # "jour"
show(s[:])        # copie complète
show(s[1:][0:2])  # chaînable
```

### Slice avec pas `x[début:fin:pas]` (str uniquement)

```
show(s[::-1])     # inversion complète
show(s[::2])      # un caractère sur deux
show(s[1:5:2])
```

Le pas doit être un **entier littéral** connu à la compilation (positif ou négatif, jamais nul).

---

## Fonctions

```
func nom(type arg1, type arg2, ...):
    ...
    return expr
```

Compile vers de vraies fonctions REX-SL (`func` / `endfunc`), avec support de la **récursion**.

Types de paramètres acceptés : `number`, `float`, `bool`, `str`, `list`, `dict` (les collections sont passées par pointeur, sans copie).

### Valeurs par défaut et type de retour explicite

```
func add(number a, number b = 10) -> number:
    return a + b
```

- `b = 10` : valeur par défaut (doit être un littéral).
- `-> number` : type de retour explicite, utile notamment pour qu'un appel **récursif utilisé dans une expression** (`return n * f(n-1)`) fonctionne dès le premier passage.

### Arguments nommés

```
func f(number a, number y = 5):
    return a + y

show(f(1, y=10))
```

### `*args` / `**kwargs`

Les paramètres `*args` (représenté en interne comme `list`) et `**kwargs` (représenté comme `dict`) sont reconnus dans la signature d'une fonction.

### Annotation d'élément pour un paramètre `list`

```
func total(list[number] valeurs) -> number:
    ...
```

`list[number]`, `list[float]`, `list[str]`, `list[bool]` permettent d'annoter le type d'élément d'un paramètre `list`, indispensable pour indexer ou itérer sur ce paramètre dans le corps de la fonction.

### `return`

- Valide uniquement à l'intérieur d'un `func`.
- Tous les `return` d'une même fonction doivent partager le même type.
- Une fonction sans aucun `return` se comporte comme si elle retournait `None` (à la Python) lorsqu'elle est appelée dans une expression.
- `list`/`dict` en retour sont supportés (le pointeur est transféré, sans copie profonde).

### Limitation : `RX_ret`

REX-SL utilise un registre global unique `RX_ret`, **monotype pour toute la durée du programme**. Le compilateur REX contourne automatiquement les conflits de type (deux fonctions à types de retour différents appelées dans le même programme) en basculant sur une injection C directe (`scrc`) pour les appels en conflit — transparent pour l'utilisateur.

---

## `func` comme objet (pointeurs de fonction)

```
func carre(number x) -> number:
    return x * x

var func f = carre;
show(f(5));          # 25

f = autreFonction;   # réassignation
```

- `var func <nom> = <fonction>;` déclare une variable de type interne `funcref` (aucun `var` REX-SL émis : le pointeur C est injecté via `scrc`).
- `<nom>(args)` dans une expression est compilé en appel indirect via ce pointeur.
- `<nom> = <autreFonction>;` (réassignation) est supporté.

**Limitations** : aucune closure ; la signature de la cible n'est vérifiée qu'à la déclaration (pas à la réassignation) ; la valeur `None` n'est pas acceptée.

---

## Fonctions natives (builtins)

Utilisables dans n'importe quelle expression, **prioritaires** sur les fonctions `func` utilisateur de même nom (comme les builtins Python) :

| Fonction              | Arité | Description                                              |
|------------------------|-------|------------------------------------------------------------|
| `len(s)`               | 1     | longueur — `str` ou collection (list/tuple/set/dict)       |
| `type(x)`               | 1     | nom du type (str)                                          |
| `str(x)`                | 1     | conversion en texte                                         |
| `int(x)`                | 1     | conversion en `number`                                      |
| `float(x)`              | 1     | conversion en `float`                                       |
| `upper(s)`              | 1     | majuscules                                                   |
| `lower(s)`              | 1     | minuscules                                                    |
| `trim(s)`               | 1     | supprime les espaces en bordure                              |
| `reverse(s)`            | 1     | inverse la chaîne                                            |
| `charat(s, i)`          | 2     | caractère à l'index `i`                                       |
| `find(s, sous)`         | 2     | position d'une sous-chaîne                                    |
| `slice(s, a, b)`        | 3     | sous-chaîne `[a:b]`                                            |
| `replace(s, old, new)`  | 3     | remplacement de sous-chaîne                                    |

Ces fonctions déléguent toutes à un opcode REX-SL du même nom (aucune modification de `REX-SL.py`). Les arguments nommés ne sont **pas** supportés pour les builtins.

---

## Affichage (`show`)

`show(...)` se comporte **exactement** comme `print()` en Python :

```
show(x)                       # affiche x, retour à la ligne (end="\n" par défaut)
show(a, b, c)                  # affiche "a b c" (valeurs séparées par sep=" " par défaut)
show(a, b, sep=", ")           # séparateur personnalisé : "a, b"
show(x, "")                    # forme positionnelle historique, équivalente à end=""
show(x, end="")                # pas de retour à la ligne
show(x, end="...")             # tout autre 'end'
show(a, b, sep="-", end="!")   # combinable, comme print()
```

- Nombre quelconque de valeurs positionnelles, concaténées avec `sep` entre chacune.
- Chaque valeur non-`str` est automatiquement convertie en texte.
- Types affichables : `number`/`float`/`str`/`bool`, plus les collections **entièrement littérales** (voir [Collections](#collections-list-tuple-set-dict)).
- En interne, tout est concaténé en une seule chaîne puis émis via un unique `show`/`showln` REX-SL final (limitation REX-SL : ces opcodes n'acceptent qu'une seule valeur à la fois).

---

## Fichiers (lecture / écriture)

Gestion de fichier à la Python (délègue directement aux opcodes REX-SL `read`/`readlines`/`write`/`writelines`) :

```
var contenu = read("data.txt")          # lit tout le fichier dans un str
var lignes = readlines("data.txt")      # lit le fichier, une entrée par ligne (list)
write("out.txt", contenu)                # écrit une valeur (mode "w", écrase)
writelines("out.txt", lignes)            # écrit une liste, un élément par ligne
```

Limitations (héritées de REX-SL) :
- lecture/écriture **complète** en un seul appel — pas d'objet "fichier" ouvert/fermé explicitement ;
- pas de mode append ;
- `read`/`readlines` s'utilisent uniquement comme valeur d'un `var` ;
- `write`/`writelines` sont des instructions (pas utilisables dans une expression) ;
- `writelines` attend le nom d'une variable liste déjà déclarée (pas un littéral inline).

---

## Conditions (`if` / `elif` / `else`)

```
if cond:
    ...
elif autre_cond:
    ...
else:
    ...
```

`cond` supporte :
- les comparateurs `== != < <= > >=` ;
- `and`, `or`, `not`, avec court-circuit logique correct (compilés en séquences `cdn`/`go` REX-SL) ;
- le groupement par parenthèses : `(a > b) and (c < d)` ;
- `in` / `not in` (appartenance à une `str` ou une collection) ;
- `is None` / `is not None` (voir [None](#none--none--null)) ;
- une simple expression `bool` : `if flag:`.

Une seule comparaison à la fois par atome (pas de chaînage à la `a < b < c`).

---

## Boucles (`repeat`, `while`, `for`)

### `repeat`

```
repeat 3:
    ...

repeat 3 times:    # forme historique, "times" optionnel
    ...
```

Boucle exécutée `<expr>` fois **au runtime** (jamais déroulée à la compilation).

### `while`

```
while <cond>:
    ...
```

`<cond>` supporte exactement la même syntaxe que la condition d'un `if`.

### `for` — plage numérique (`range`)

```
for i in range(5):            # 0, 1, 2, 3, 4
    ...
for i in range(2, 8):         # 2, 3, ..., 7
    ...
for i in range(10, 0, -2):    # 10, 8, 6, 4, 2
    ...
```

`range()` accepte 1 à 3 arguments (`stop` / `start, stop` / `start, stop, step`). Le `step`, s'il est fourni, doit être un entier **littéral** connu à la compilation.

### `for` — caractère par caractère

```
for c in "bonjour":     # boucle runtime, jamais déroulée
    show(c)
```

### `for` — sur un littéral de collection (déroulé à la compilation)

```
for x in [1, 2, 3]:
    show(x)
```

Le corps est dupliqué à la compilation, une fois par élément du littéral.

### `for` — sur une variable list/tuple/set (boucle runtime)

```
var l = [10, 20, 30]
for x in l:
    show(x)
```

Boucle runtime via les opcodes `len`/`get` — nécessite que la liste soit homogène et son type d'élément connu.

### `for ... enumerate(...)`

```
for i, v in enumerate([10, 20, 30]):
    show(i, v)

for i, c in enumerate("abc"):
    show(i, c)
```

Uniquement cette forme à deux variables — pas de déballage de tuple général dans un `for`.

---

## `break` / `continue`

Gérés dans `while`, `for` et `repeat` (pile d'étiquettes par boucle, une entrée par niveau imbriqué) :

```
while true:
    if x == 0:
        break
    if x < 0:
        continue
    ...
```

- `break;` : sort entièrement de la boucle la plus proche.
- `continue;` : passe directement à l'itération suivante (réévaluation de la condition pour `while`, incrément puis réévaluation pour `for`/`repeat`).

---

## Sauts explicites (`label` / `go`)

```
label debut;
...
go debut;
```

Compile directement vers les opcodes REX-SL `lbl`/`go` (`go` est traduit en saut inconditionnel via `cdn on;` puis `go`).

---

## Déballage de tuple

```
a, b = 1, 2;          # deux scalaires
a, b = b, a;           # échange (les droites sont évaluées avant toute affectation)
a, b, c = 1, 2, 3;      # N cibles = N valeurs

a, b = f();             # f() retourne une list -> déballage indexé
```

- Forme scalaire : `N` expressions pour `N` cibles, chaque cible pouvant être nouvelle (déclaration inférée) ou déjà déclarée (réaffectation dynamique).
- Forme "liste unique" : uniquement si le type d'élément de la liste retournée est connu à la compilation.
- Limitation : les cibles doivent être de simples variables (pas d'indexation `a[i], b = ...`, pas de déballage imbriqué).

---

## List comprehensions

```
var carres = [x * x for x in range(10)]
var pairs = [x for x in range(20) if x % 2 == 0]
```

`[expr for var in iterable [if cond]]`, compilée en `var list` + boucle + `append`. Reprend les mêmes 4 stratégies d'itération que `for` (range, littéral déroulé, variable list/tuple/set, str).

Utilisable aussi bien comme valeur directe d'un `var`/réaffectation que comme **sous-expression** ailleurs (argument de fonction, f-string, `show(...)`, ...).

---

## Chaînes formatées (f-strings)

```
var nom = "Ada"
var age = 36
show(f"{nom} a {age} ans")     # "Ada a 36 ans"
show(f"progrès: {{{i}}}")      # accolades doublées -> accolade littérale : "progrès: {3}"
```

- `f"..."` / `f'...'` fonctionne partout où une chaîne est attendue.
- Chaque `{expr}` est évalué puis converti en texte (`number`/`float`/`str`/`bool`).
- `{{` / `}}` produisent une accolade littérale.

### Spécificateurs de format `{expr:spec}`

```
show(f"{pi:.2f}")        # 2 décimales
show(f"{n:5d}")           # largeur 5
show(f"{n:05d}")          # rempli de zéros
show(f"{n:<5d}")          # aligné à gauche
```

Formes supportées : `[<|>][0][largeur][.précision][d|f|g|e|s]` (`d` : entier ; `f`/`e`/`g` : flottant ; `s` : chaîne). L'alignement centré `^` n'est pas supporté. Compilé via `snprintf` en C (injection `scrc`).

---

## Imports (`import`)

```
import "utils.rex";
```

- Colle **textuellement** le contenu du fichier importé **à la place** de la ligne `import` (comme un `#include` C), avant toute analyse lexicale.
- Chemin résolu relativement au dossier du fichier qui importe.
- Récursif, avec détection des imports circulaires.
- L'en-tête `# REX>` du fichier importé est retirée automatiquement.
- L'instruction doit occuper une **ligne entière** à elle seule.
- Disponible uniquement en **mode fichier** (`-f`/`--file`) — pas de dossier de référence en mode `-o`/`--oneline`.

---

## Modules avec espace de noms (`import ... as`)

```
import "geometrie.rex" as geo;

show(geo.aire_cercle(5));
```

- Les fonctions du fichier importé sont renommées `__rx_mod_<alias>_<fn>` dans le code inliné, puis enregistrées sous l'alias.
- `alias.fn(args)` est reconnu dans les expressions **et** comme instruction autonome.
- Les **variables globales** du module ne sont **pas** exportées (limitation documentée : espace de noms de fonctions uniquement).

---

## Retypage dynamique des variables

Comportement "à la Python" : une variable dont le type n'a **pas** été annoté explicitement peut changer de type par réaffectation.

```
var s = carre(i)     # inféré "number"
s = {1, 2, 3}          # OK : retype "s" en set
s = {4, 5, 6}          # OK : nouvelle réaffectation

var x = 5
x = "abc"               # OK : retype "x" en str (0.0.12)
```

Un type **explicite** (`var number s = 0`, `var list l = [...]`) reste verrouillé : toute tentative de changement de type lève une erreur de compilation.

> **Note d'implémentation** : chaque retypage alloue en interne un nom REX-SL frais (`__rx_col<N>_<nom>`) pour éviter toute collision avec la déclaration précédente dans la table de symboles REX-SL (qui persiste pour toute la durée du programme généré). Les noms commençant par `__rx_` sont **réservés au compilateur** et ne peuvent pas être utilisés comme noms de variable par l'utilisateur.

---

## Erreurs

Toute erreur de résolution REX → REX-SL lève une `RexResolveError` (sous-classe de `REXERROR`), rapportée sur stderr sous la forme :

```
Erreur de resolution: <message>
```

Les erreurs du lexer sont préfixées `[Lexer]`. Les erreurs REX-SL elles-mêmes (issues de `REX-SL.py`, en aval) sont préfixées `[REX-SL]`.

---

## Limitations connues (héritées de REX-SL)

- Pas d'indexation générique sur une variable `list`/`dict` sans type d'élément/valeur connu et homogène à la compilation.
- Pas d'itération directe sur une variable `list` sans passer par la boucle runtime dédiée (`len`/`get`) — REX-SL n'exposant aucune primitive de longueur pour une variable liste au sens général de la 0.0.11 (résolu depuis via ces opcodes).
- Les slices (`x[a:b]`, `x[a:b:c]`) ne sont disponibles que sur `str`.
- `show(...)` n'affiche que `number`/`float`/`str`/`bool`, plus les collections entièrement littérales ou sérialisées via `list_str`/`dict_str`.
- `read`/`readlines`/`write`/`writelines` : pas de mode append, pas d'objet fichier.
- `RX_ret` est un registre global monotype (contourné automatiquement, voir [Fonctions](#fonctions)).
- Pas de closures pour les pointeurs de fonction (`funcref`).
- `None` est entièrement simulé côté REX.py (aucun type nullable réel côté REX-SL).

---

## Architecture interne du compilateur

Pour les contributeurs souhaitant étendre le langage :

| Composant                 | Rôle                                                                          |
|-----------------------------|----------------------------------------------------------------------------|
| `REX_Lexer`                 | Découpe le source en tokens (gère indentation à la Python, f-strings, groupements `()`/`[]`/`{}`) |
| `ExprParser` / `ExprCodegen`| Analyse et génère le code des expressions (priorité des opérateurs, appels, indexation, slices, f-strings) |
| `Emitter`                    | Accumule le code REX-SL généré + table des symboles (types, alias de retypage, fonctions, modules, funcrefs) |
| `REX_Resolver`               | Point d'entrée : reconstruit la structure d'instructions (`_Line`/`_Block`) et délègue à chaque "statement compiler" |
| `LINE_HANDLERS`               | Dictionnaire nom de mot-clé → fonction de compilation pour les instructions simples (`var`, `show`, `return`, ...) |
| `BLOCK_HANDLERS`              | Idem pour les instructions à bloc (`func`, `repeat`, `while`, `for`) |
| `REX_IfStatement`             | Compilateur dédié pour les conditions complexes (`and`/`or`/`not`, court-circuit) |

Ajouter une nouvelle instruction REX ne demande qu'une nouvelle fonction/classe `compile(tokens, emitter)` (ou `compile(header, body, emitter, resolver)` pour un bloc) + une entrée dans `LINE_HANDLERS`/`BLOCK_HANDLERS`. Ajouter un nouvel opérateur revient à ajouter une entrée dans `ExprParser.PRECEDENCE`.

---

## Historique des versions

| Version | Points marquants |
|---------|-------------------|
| 0.0.1   | Lexer et compilateur de base |
| 0.0.2   | Résolveur de calcul |
| 0.0.3   | Blocs par indentation + `;` à la Python |
| 0.0.4   | `var` + résolveur d'expressions complet |
| 0.0.5   | Blocs à la Python (`:` + indentation), `func`/`return`, `go`/`label`, `repeat ... times` |
| 0.0.6   | Header simplifié `# REX>`, `repeat` sans `times`, littéraux de collection Python, `if`/`elif`/`else` (comparaison simple) |
| 0.0.7   | Conditions complexes `and`/`or`/`not` avec court-circuit, parenthèses de groupement |
| 0.0.8   | Retypage de variable par réaffectation de collection (types inférés uniquement) |
| 0.0.9   | Fix retypage : noms REX-SL internes frais (`__rx_col<N>_<nom>`) pour éviter les collisions |
| 0.0.10  | Fix opérateurs `!=`/`<=`/`>=` dans les conditions complexes, fix `and`/`or`/`not`, ajout de `show(...)` |
| 0.0.11  | `while`, `for range(...)`, `break`/`continue`, f-strings, lecture/écriture fichier, `import` |
| 0.0.12  | `for` étendu (str, collections littérales, `enumerate`), fonctions natives, retypage scalaire dynamique |
| 0.0.13  | Slice `x[a:b]`, fix affichage de collections littérales |
| 0.0.14  | `+=`/`-=`/`*=`/`/=`/`%=`, `**`, `len()` étendu, retour de collection, slice avec pas, déballage de tuple, list comprehensions, f-strings avec format specs |
| 0.0.15  | Modules réels (`import ... as`), `func` comme objet (pointeurs de fonction) |
| 0.1.0   | `None`/`none`/`null`, `is`/`is not`, `in`/`not in` dans les conditions |

---

*Documentation générée à partir des commentaires et de la structure du code source de `REX.py`.*
