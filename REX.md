# Documentation du compilateur REX

> Version alpha 0.1.8 — copyright © 2026 R-ECO4  
> Cible REX-SL : 0.0.23

---

## Sommaire

1. [Vue d'ensemble](#1-vue-densemble)
2. [Pipeline de compilation](#2-pipeline-de-compilation)
3. [Utilisation en ligne de commande](#3-utilisation-en-ligne-de-commande)
4. [Syntaxe du langage REX](#4-syntaxe-du-langage-rex)
   - 4.1 [En-tête de fichier](#41-en-tête-de-fichier)
   - 4.2 [Types](#42-types)
   - 4.3 [Variables (`var`)](#43-variables-var)
   - 4.4 [Expressions et opérateurs](#44-expressions-et-opérateurs)
   - 4.5 [Affichage (`show`)](#45-affichage-show)
   - 4.6 [Conditions (`if` / `elif` / `else`)](#46-conditions-if--elif--else)
   - 4.7 [Boucles](#47-boucles)
   - 4.8 [Fonctions (`func`)](#48-fonctions-func)
   - 4.9 [Imports](#49-imports)
   - 4.10 [Fichiers I/O](#410-fichiers-io)
   - 4.11 [F-strings](#411-f-strings)
   - 4.12 [Sauts explicites (`go` / `label`)](#412-sauts-explicites-go--label)
   - 4.13 [None](#413-none)
   - 4.14 [Collections](#414-collections)
   - 4.15 [Fonctions natives (builtins)](#415-fonctions-natives-builtins)
   - 4.16 [Fonctions comme objets (funcref)](#416-fonctions-comme-objets-funcref)
   - 4.17 [Opérateur ternaire](#417-opérateur-ternaire)
   - 4.18 [Opérateurs binaires bit à bit](#418-opérateurs-binaires-bit-à-bit)
   - 4.19 [Assertion (`assert`)](#419-assertion-assert)
   - 4.20 [Filtrage par valeur (`match` / `case` / `default`)](#420-filtrage-par-valeur-match--case--default)
   - 4.21 [Gestion d'exceptions (`try` / `except` / `finally` / `raise`)](#421-gestion-dexceptions-try--except--finally--raise)
   - 4.22 [Classes (`class`)](#422-classes-class)
5. [Architecture interne](#5-architecture-interne)
   - 5.1 [REX_Lexer](#51-rex_lexer)
   - 5.2 [ExprParser](#52-exprparser)
   - 5.3 [ExprCodegen](#53-exprcodegen)
   - 5.4 [Emitter](#54-emitter)
   - 5.5 [Instructions (statements)](#55-instructions-statements)
   - 5.6 [Préprocesseur d'imports](#56-préprocesseur-dimports)
6. [Gestion des erreurs et avertissements](#6-gestion-des-erreurs-et-avertissements)
7. [Limitations connues](#7-limitations-connues)
8. [Historique des versions](#8-historique-des-versions)

---

## 1. Vue d'ensemble

**REX** est un langage de programmation à syntaxe inspirée de Python (indentation obligatoire, blocs terminés par `:`) qui se compile en **REX-SL**, lui-même compilé en **C** par `REX-SL.py` avant d'être transformé en exécutable natif via `gcc`.

REX n'est pas interprété : chaque construction du langage est traduite statiquement en opcodes REX-SL équivalents lors de la compilation.

```
fichier.rex  ──[REX.py]──▶  fichier.rexsl  ──[REX-SL.py]──▶  fichier.c  ──[gcc]──▶  exécutable
```

Le compilateur `REX.py` est entièrement écrit en Python et ne dépend d'aucune bibliothèque externe.

---

## 2. Pipeline de compilation

| Étape | Outil | Entrée | Sortie |
|-------|-------|--------|--------|
| 1 — Prétraitement | `preprocess_imports()` | Source `.rex` brut | Source avec imports inlinés |
| 2 — Analyse lexicale | `REX_Lexer` | Source REX | Liste de tokens / groupes |
| 3 — Résolution REX→REX-SL | `resolve_to_rexsl()` | Tokens | Code REX-SL (texte) |
| 4 — Compilation REX-SL→C→exe | `REX-SL` (exécutable externe) | Fichier `.rexsl` | Exécutable natif |

Les étapes 1 à 3 sont entièrement gérées par `REX.py`. L'étape 4 est déléguée à l'exécutable `REX-SL` (ou `REX-SL.exe` sur Windows) qui doit être présent dans le même dossier que `REX.py`.

---

## 3. Utilisation en ligne de commande

```bash
# Compiler un fichier source
python REX.py -f script.rex -c

# Compiler et exécuter
python REX.py -f script.rex -r

# Passer du code directement (mode one-liner)
python REX.py -o "var x = 5; show(x)" -c -r

# Conserver les fichiers intermédiaires
python REX.py -f script.rex -c -k -s

# Mode inspection : génère uniquement le .rexsl (sans compiler)
python REX.py -f script.rex
```

### Options

| Option | Forme longue | Description |
|--------|-------------|-------------|
| `-f FILE` | `--file` | Fichier `.rex` source (doit commencer par `# REX>`) |
| `-o CODE` | `--oneline` | Code REX passé directement, instructions séparées par `;` |
| `-O NOM` | `--output` | Nom de base des fichiers générés (défaut : nom du fichier source sans extension, ou `rex_output` en mode `-o`) |
| `-c` | `--compiler` | Compile REX → REX-SL → C → exécutable |
| `-r` | `--run` | Exécute l'exécutable après compilation (implique `-c`) |
| `-k` | `--keep-c` | Conserve le fichier `.c` intermédiaire |
| `-s` | `--keep-rsl` | Conserve le fichier `.rexsl` intermédiaire |
| `-d` | `--debug` | Affiche les étapes internes (tokens, code REX-SL généré, etc.) |

Sans `-c` ni `-r`, seul le fichier `.rexsl` est généré (mode inspection).

---

## 4. Syntaxe du langage REX

### 4.1 En-tête de fichier

Tout fichier `.rex` doit commencer par la ligne suivante (première ligne non vide) :

```
# REX>
```

Cette ligne est vérifiée avant toute analyse. En mode `-o`/`--oneline`, elle n'est pas requise.

Les commentaires sont identiques à Python :

```python
# commentaire de ligne

#* commentaire
   de bloc *#
```

---

### 4.2 Types

| Type REX | Description | Représentation REX-SL |
|----------|-------------|----------------------|
| `number` | Entier | `long long` C |
| `float` | Flottant | `double` C |
| `bool` | Booléen (`true`/`false`) | `bool` C |
| `str` | Chaîne de caractères | `char*` C (heap) |
| `list` | Liste ordonnée | Structure liste REX-SL |
| `dict` | Dictionnaire clé→valeur | Structure dict REX-SL |
| `set` | Ensemble (dédupliqué à la compilation) | `list` REX-SL |
| `tuple` | N-uplet immuable | `list` REX-SL |
| `none` | Valeur nulle | `void*` C = NULL |

`set` et `tuple` n'ont pas de type dédié en REX-SL : ils sont tous deux représentés comme des `list`. Les éléments d'un `set` littéral sont dédupliqués **à la compilation**.

La promotion automatique `number → float` s'applique dès qu'un `float` intervient dans une expression arithmétique.

---

### 4.3 Variables (`var`)

```python
var x                       # number, valeur par défaut 0
var x = 5                   # type inféré depuis la valeur
var x = (2 + 3) * 4         # expression complète
var number x = 5            # type explicite (verrouillé)
var float pi = 3.14
var str nom = "Alice"
var bool actif = true
var list l = [1, 2, 3]
var none ptr               # pointeur void* initialisé à NULL
var x = None               # équivalent à var none x
```

#### Réaffectation

```python
x = nouvelle_valeur         # réaffecte une variable existante
x += 5                      # opérateurs composés : += -= *= /= %=
```

#### Retypage par réaffectation

Une variable dont le type a été **inféré** (non annoté explicitement) peut changer de type par réaffectation. Le compilateur émet l'opcode REX-SL `retype <var> <type>;` pour gérer la transition.

```python
var s = calcul(i)           # type inféré : number
s = {1, 2, 3}              # OK : retype s en set
s = "texte"                 # OK : retype s en str
```

Un type **explicite** (`var number x = 5`) reste verrouillé et tout changement lève une erreur de compilation.

> **Note :** les noms commençant par `__rx_` sont réservés au compilateur.

#### Déballage de tuple

```python
a, b = e1, e2              # N expressions scalaires
a, b = b, a                # swap (sémantique Python : droites évaluées avant affectation)
```

---

### 4.4 Expressions et opérateurs

| Opérateur | Description |
|-----------|-------------|
| `+ - * / %` | Arithmétique standard |
| `**` | Exponentiation (priorité maximale, associatif à droite) |
| `()` | Groupement / priorité |
| `-x` | Moins unaire |
| `& \| ^ ~ << >>` | Opérateurs bit à bit (sur `number` uniquement — voir §4.18) |
| `str + str` | Concaténation |
| `str - str` | Suppression d'occurrences |
| `str * number` | Répétition |
| `x[a:b]` | Slice sur `str` (bornes optionnelles) |
| `x[a:b:c]` | Slice avec pas sur `str` |
| `x[i]` | Indexation via `charat(x, i)` ou `get` |
| `alias.fn(args)` | Appel qualifié de module |
| `val_vrai if cond else val_faux` | Expression ternaire (voir §4.17) |

---

### 4.5 Affichage (`show`)

`show` se comporte exactement comme `print()` en Python :

```python
show(x)                         # affiche x suivi d'un retour à la ligne
show(a, b, c)                   # "a b c" (séparateur " " par défaut)
show(a, b, sep=", ")            # "a, b"
show(x, end="")                 # sans retour à la ligne
show(a, b, sep="-", end="!")    # combiné
```

Chaque valeur doit être de type `number`, `float`, `str` ou `bool`. Les valeurs non-`str` sont automatiquement converties en texte. `print()` est un alias de `show()`.

---

### 4.6 Conditions (`if` / `elif` / `else`)

```python
if condition:
    ...
elif autre_condition:
    ...
else:
    ...
```

Les conditions supportent `and`, `or`, `not` et les parenthèses de groupement, compilés en séquences `cdn`/`go` REX-SL avec court-circuit logique.

```python
if (a > b) and (c < d):
    ...

if not x == 0 or y > 10:
    ...

if x is None:
    ...

if x == None:               # équivalent à is None
    ...
```

Opérateurs de comparaison supportés : `==`, `!=`, `<`, `>`, `<=`, `>=`, `is None`, `in`, `not in`.

---

### 4.7 Boucles

#### `repeat`

```python
repeat 3:
    ...

repeat n times:             # le mot-clé "times" est optionnel
    ...
```

Boucle exécutée `<expr>` fois au **runtime** (jamais déroulée à la compilation), via un compteur interne + `lbl`/`cdn`/`go` REX-SL.

#### `while`

```python
while condition:
    ...
```

La condition supporte la même syntaxe que `if` (`and`/`or`/`not`, parenthèses).

#### `for` — range

```python
for i in range(5):              # 0, 1, 2, 3, 4
    ...
for i in range(2, 8):           # 2, 3, ..., 7
    ...
for i in range(10, 0, -2):      # 10, 8, 6, 4, 2  (le pas doit être un entier littéral)
    ...
```

#### `for` — itération sur une chaîne

```python
for c in ma_chaine:             # itère caractère par caractère au runtime
    ...
```

#### `for` — itération sur un littéral de collection

```python
for x in [1, 2, 3]:            # déroulé à la compilation
    ...

for i, v in enumerate([10, 20, 30]):  # deux variables (index, valeur)
    ...
```

L'itération directe sur une **variable** de type `list` n'est pas supportée (REX-SL n'expose pas de primitive de longueur de liste variable).

#### `break` et `continue`

Supportés dans `while`, `for` et `repeat`. Sautent respectivement vers la fin ou vers l'incrément/réévaluation de la boucle la plus proche.

#### List comprehensions

```python
var carres = [x * x for x in range(10)]
var pairs  = [x for x in range(20) if x % 2 == 0]
```

Compilées en variable `list` + boucle + `append`.

---

### 4.8 Fonctions (`func`)

```python
func nom(number a, str b, float c):
    ...
    return expr

func calcul(number x) -> number:   # type de retour explicite (optionnel)
    return x * 2

func afficher(str msg) -> none:    # fonction void (pas de valeur de retour)
    show(msg)
```

Types de paramètres acceptés : `number`, `float`, `bool`, `str`. Les collections (`list`, `dict`) ne peuvent pas être passées en paramètre directement (limitation REX-SL).

`return` n'est valide qu'à l'intérieur d'un `func`. Tous les `return` d'une même fonction doivent partager le même type.

---

### 4.9 Imports

#### Import textuel (inline)

```python
import "utils.rex";
```

Le contenu du fichier est **collé textuellement** à la place de la ligne `import`, avant toute analyse lexicale (comme `#include` en C). L'en-tête `# REX>` du fichier importé est automatiquement retirée. Récursif, avec détection des imports circulaires.

Disponible uniquement en mode `-f`/`--file` (pas en mode `-o`).

#### Import avec espace de noms

```python
import "math.rex" as math;

var r = math.carre(5)       # appel qualifié
var v = math.ma_var         # accès à une variable globale exportée du module
```

Les fonctions **et les variables globales** du fichier importé sont renommées `__rx_mod_<alias>_<nom>` dans le code inline et enregistrées dans `Emitter.modules[alias]`. L'accès qualifié `alias.nom` fonctionne aussi bien pour les fonctions que pour les variables.

#### Import sans guillemets — evo-import

```python
import module
import module as alias
```

Cherche `module.rex` ou l'exécutable `module` dans le chemin courant. Lorsque la cible est un exécutable, les variables globales qu'il exporte (champ `"variables"` de sa métadonnée JSON) sont accessibles via `alias.var_name` — l'exécutable doit traiter la commande `metavar <nom> <chemin>` en écrivant la valeur dans `<chemin>`.

> **Note :** les retours de type `list`/`dict`/`tuple`/`set` depuis un evo-import sont explicitement rejetés avec un message d'orientation. Les arguments chaînes contenant des espaces sont transmis via `fork`/`execv`.

---

### 4.10 Fichiers I/O

```python
var contenu  = read("data.txt")         # lit tout le fichier dans un str
var lignes   = readlines("data.txt")    # lit le fichier ligne par ligne (list)

write("out.txt", contenu)               # écrit une valeur (écrase le fichier)
writelines("out.txt", lignes)           # écrit une liste, un élément par ligne
```

Délégué directement aux opcodes REX-SL `read`/`readlines`/`write`/`writelines`. Pas d'objet "fichier" ouvert/fermé, pas de mode append (limitation REX-SL).

---

### 4.11 F-strings

```python
var nom = "Ada"
var age = 36
show(f"{nom} a {age} ans")          # "Ada a 36 ans"
show(f"accolade : {{{age}}}")       # "accolade : {36}"
```

Disponibles partout où une chaîne est attendue. Chaque `{expr}` est converti en texte et concaténé. `{{` / `}}` produisent une accolade littérale.

#### Spécificateurs de format

```python
show(f"{pi:.2f}")       # flottant avec 2 décimales
show(f"{n:05d}")        # entier sur 5 chiffres, complété de zéros
show(f"{s:>10s}")       # chaîne alignée à droite sur 10 caractères
```

Formes supportées : `[<|>][0][largeur][.précision][d|f|g|e|s]`.

---

### 4.12 Sauts explicites (`go` / `label`)

```python
label debut;
...
go debut;
```

Compilé directement vers les opcodes REX-SL `lbl`/`go`. Usage déconseillé dans les nouvelles structures de contrôle, mais pleinement supporté.

---

### 4.13 None

```python
var x = None                # déclare une variable de type 'none' (void* = NULL)
var none x                  # forme explicite équivalente

x = None                    # remet x à NULL

if x is None:               # test de nullité natif (opcode isnone)
    ...

show(x)                     # affiche "None"

func f() -> none:           # fonction void
    return None
```

`None`, `none` et `null` sont strictement équivalents comme mots-clés. Utilise l'opcode REX-SL natif `isnone` — pas de simulation par flag booléen.

---

### 4.14 Collections

#### Déclaration

```python
var l = [1, 2, 3]              # list
var t = (1, 2, 3)              # tuple (représenté comme list en REX-SL)
var s = {1, 2, 3}              # set (dédupliqué à la compilation)
var d = {"a": 1, "b": 2}      # dict (clés : chaînes littérales uniquement)
```

#### Opérations sur les listes

```python
var n = len(l)                 # longueur d'une list (opcode REX-SL len)
```

L'itération directe sur une variable `list` au runtime n'est pas supportée (voir la section `for` — itération sur un littéral de collection).

#### Affichage de collections

`show(coll)` est supporté uniquement si tous les éléments de la collection sont des **littéraux** connus à la compilation. La représentation est capturée via `repr()` Python au moment de la déclaration et injectée comme chaîne figée.

---

### 4.15 Fonctions natives (builtins)

Les fonctions suivantes sont utilisables dans n'importe quelle expression :

| Catégorie | Fonctions |
|-----------|-----------|
| Longueur | `len(x)` — str et list |
| Type | `type(x)` |
| Conversions | `str(x)`, `int(x)`, `float(x)`, `bool(x)` |
| Chaînes | `upper(s)`, `lower(s)`, `trim(s)`, `reverse(s)`, `charat(s, i)`, `find(s, sub)`, `slice(s, a, b)`, `replace(s, old, new)` |
| Math | `abs(x)`, `pow(x, y)`, `pow(x, y, mod)`, `round(x)`, `divmod(x, y)` |
| Collections | `sum(l)`, `min(l)`, `max(l)`, `sorted(l)`, `reversed(l)`, `list(x)`, `tuple(x)`, `set(x)`, `dict(x)` |
| Caractères | `chr(n)`, `ord(c)`, `hex(n)`, `oct(n)`, `bin(n)` |
| Logique | `all(l)`, `any(l)` |
| Divers | `repr(x)`, `ascii(x)`, `hash(x)`, `id(x)`, `callable(x)`, `isinstance(x, t)`, `format(x, spec)`, `input()` |

`print()` est un alias de `show()`.

---

### 4.16 Fonctions comme objets (funcref)

```python
func carre(number x) -> number:
    return x * x

var func f = carre              # déclare un pointeur de fonction
var r = f(5)                    # appel indirect : r = 25

f = autre_func                  # réassignation du pointeur
```

Aucune closure. La signature de la cible est vérifiée à la **déclaration** uniquement ; la réassignation n'est pas vérifiée.

---

### 4.17 Opérateur ternaire

```python
var abs_x = x if x >= 0 else -x
var msg = "pair" if n % 2 == 0 else "impair"
```

Syntaxe : `valeur_si_vrai if condition else valeur_si_faux`. Les deux branches doivent être du même type scalaire (`number`, `float`, `str`, `bool`), avec promotion `number → float` admise. L'opérateur a la priorité la plus basse de toutes les expressions.

---

### 4.18 Opérateurs binaires bit à bit

```python
var masque = a & 0xFF           # ET bit à bit
var flags  = a | b              # OU bit à bit
var diff   = a ^ b              # XOR bit à bit
var inv    = ~a                 # NOT bit à bit (unaire)
var dec    = a >> 2             # décalage à droite
var aug    = a << 3             # décalage à gauche
```

Disponibles uniquement sur le type `number`. Les opérations sont effectuées en C sur des entiers non signés, le résultat est recasté en `int`.

Priorité (de la plus faible à la plus forte) : `|` → `^` → `&` → `<<` / `>>`.

---

### 4.19 Assertion (`assert`)

```python
assert x > 0
assert x > 0, "x doit être positif"
```

Si la condition est fausse, le message (ou un message générique) est affiché sur `stderr` et le programme se termine avec `exit(1)`. Les conditions complexes (`and`/`or`/`not`) sont supportées.

---

### 4.20 Filtrage par valeur (`match` / `case` / `default`)

```python
match jour:
    case 1:
        show("lundi")
    case 2:
        show("mardi")
    default:
        show("autre jour")
```

L'expression du `match` est évaluée **une seule fois** dans un temporaire. `default` joue le rôle de `else`. Pas de fallthrough entre les cas. Compilé en chaîne de comparaisons `cdn`/`go`/`lbl`, à la manière d'un `if`/`elif`/`else`.

---

### 4.21 Gestion d'exceptions (`try` / `except` / `finally` / `raise`)

```python
try:
    var r = risque()
except as e:
    show(f"Erreur : {e}")
finally:
    show("nettoyage")
```

```python
raise "valeur invalide"
raise f"erreur sur {nom}"
```

Compilé via injection C brute (`setjmp`/`longjmp`) sans modification de REX-SL. La clause `except as e` expose le message d'exception dans la variable `e` (type `str`), déclarée automatiquement si absente. La clause `finally` s'exécute toujours (après le corps `try` normal ou après `except`).

`raise` accepte n'importe quel type — la valeur est convertie en `str` avant d'être propagée. Sans gestionnaire englobant, `raise` affiche le message sur `stderr` et termine le programme.

#### Limitations

- Pas de filtrage par type d'exception (`except ValueError:` non supporté).
- Pas de `raise` nu (rethrow sans message).
- Pas de `except (A, B):` multi-types.
- Un `return` au premier niveau d'un corps `try` lève une erreur de compilation (il bypasse le `finally` — limitation `setjmp`/`longjmp`).
- Imbrication limitée à 64 niveaux.

---

### 4.22 Classes (`class`)

```python
class Compteur:
    def __init__(self, number start):
        self.val = start

    def incrementer(self):
        self.val = self.val + 1

    def get(self) -> number:
        return self.val

var c = Compteur(0)
c.incrementer()
show(c.get())
```

#### Héritage simple

```python
class Enfant(Compteur):
    def double(self):
        self.val = self.val * 2
```

L'héritage copie la struct du parent et initialise les champs hérités via le constructeur parent lorsque les types de paramètres du constructeur courant coïncident (en préfixe) avec ceux du parent.

#### Stratégie de compilation

Les classes sont compilées entièrement via injection C brute (`gscrc`) sans modification de REX-SL :

- Un `typedef struct __rx_cls_Nom` est généré avec un champ par attribut `self.x` déclaré dans `__init__`.
- Un constructeur C `__rx_new_Nom(...)` est généré.
- Chaque méthode produit une fonction C `__rx_mth_Nom_methode(self, ...)`.
- Ces définitions sont placées en portée **globale** C (`gscrc`), donc visibles depuis les fonctions `func` et depuis le flux principal.

#### Utilisation dans les méthodes

Les structures de contrôle `if`/`elif`/`else`, `while` et `for range` sont supportées dans les corps de méthodes (depuis alpha 0.1.8). `show()` est également supporté dans les méthodes.

> **Note :** `break`/`continue` et `for var in list` restent non supportés dans les méthodes (limitation du chemin C brut).

#### Limitations

- Pas d'héritage multiple.
- Pas de `super()`.
- Pas de méthodes de classe (`@classmethod`) ni statiques.
- Les attributs doivent être déclarés dans `__init__` via `self.attr = expr`.
- Types d'attributs supportés : `number`, `float`, `bool`, `str`.
- Les méthodes ne peuvent pas retourner de collections (`list`/`dict`) via le registre `RX_ret`.
- `self` doit être le premier paramètre de chaque méthode.

---

## 5. Architecture interne

### 5.1 REX_Lexer

**Rôle :** découpe le source REX en une liste de tokens/groupes.

**Fonctionnement :**

- Les parenthèses `(...)` produisent une **sous-liste Python imbriquée** (pas de token `(` ou `)`).
- Les crochets `[...]` produisent un objet `Group(kind="[]", items=[...])`.
- Les accolades `{...}` produisent un objet `Group(kind="{}", items=[...])` (littéraux dict/set uniquement — jamais pour délimiter des blocs).
- L'indentation est gérée à la Python : tokens `INDENT` / `DEDENT` émis à chaque changement de niveau. 1 tabulation = 4 espaces.
- `;` est un simple token `PUNCT` (séparateur d'instructions en mode one-liner).

**Types de tokens produits :**

| Type | Valeur |
|------|--------|
| `IDENT` | Identifiant utilisateur |
| `KEYWORD` | Mot-clé REX (`if`, `var`, `func`, `class`, `match`, `try`, `assert`, etc.) |
| `NUMBER` | Entier, flottant, hexadécimal, binaire |
| `STRING` | Chaîne littérale |
| `FSTRING` | F-string (liste de segments) |
| `OP` | Opérateur (`+`, `**`, `+=`, `&`, `|`, `^`, `~`, `<<`, `>>`, etc.) |
| `PUNCT` | Ponctuation (`;`, `,`, `:`, `.`) |
| `NEWLINE` | Fin de ligne logique |
| `INDENT` | Augmentation du niveau d'indentation |
| `DEDENT` | Diminution du niveau d'indentation |

**Commentaires :** ligne (`# ...`) et bloc (`#* ... *#`).

---

### 5.2 ExprParser

**Rôle :** parseur récursif descendant d'expressions arithmétiques.

**Priorité des opérateurs (de la plus faible à la plus forte) :**

1. `val if cond else val` (opérateur ternaire)
2. `|` (OU bit à bit)
3. `^` (XOR bit à bit)
4. `&` (ET bit à bit)
5. `<<`, `>>` (décalages)
6. `+`, `-` (addition, soustraction, concaténation)
7. `*`, `/`, `%` (multiplication, division, modulo)
8. `**` (exponentiation, associatif à droite)
9. Moins unaire `-x`, NOT bit à bit `~x`
10. Primaires : littéraux, identifiants, appels de fonction, groupements `(...)`, slices `[a:b]`, indexations `[i]`

**Nœuds AST produits :**

| Nœud | Signification |
|------|---------------|
| `("lit", valeur)` | Littéral |
| `("ident", nom)` | Identifiant |
| `("binop", opcode, gauche, droite)` | Opération binaire |
| `("neg", nœud)` | Moins unaire |
| `("bitnot", nœud)` | NOT bit à bit `~` |
| `("call", nom, args)` | Appel de fonction |
| `("modcall", alias, fn, args)` | Appel qualifié de module |
| `("fstring", segments)` | F-string |
| `("slice", expr, début, fin)` | Slice |
| `("slicestep", expr, début, fin, pas)` | Slice avec pas |
| `("index", expr, clé)` | Indexation |
| `("none",)` | Valeur None |
| `("listcomp", ...)` | List comprehension |
| `("ternary", cond, vrai, faux)` | Expression ternaire |

---

### 5.3 ExprCodegen

**Rôle :** génère le code REX-SL correspondant à un nœud AST d'expression. Alloue des variables temporaires pour stocker les résultats intermédiaires.

**Responsabilités principales :**

- Résolution de type des sous-expressions.
- Promotion automatique `number → float`.
- Génération des f-strings (conversion en `str` + concaténation).
- Appel des builtins natifs (`BUILTIN_ARITY` + `_call_builtin`).
- Gestion des conversions de type via l'opcode REX-SL `change`.
- Génération des slices (`slice`, `slicestep`), indexations (`get`), et appels de module.
- Génération des opérateurs bit à bit et de l'opérateur ternaire via injection C brute (`scrc`).

---

### 5.4 Emitter

**Rôle :** état global de l'émission REX-SL. Centralise toutes les informations de compilation et fournit les méthodes d'émission d'opcodes.

**État maintenu :**

| Attribut | Description |
|----------|-------------|
| `lines` | Liste des lignes REX-SL générées |
| `types` | `{nom_var: type_rexsl}` |
| `functions` | `{nom_fn: (param_types, param_names, defaults, return_type, ...)}` |
| `modules` | `{alias: set_de_fonctions_et_variables_exportées}` |
| `funcrefs` | `{nom_var: (mangled_name, ...)}` |
| `_explicit_types` | Ensemble des variables dont le type est annoté explicitement |
| `_loop_stack` | Pile de labels `(label_break, label_continue)` pour `break`/`continue` |
| `_temp_counter` | Compteur de variables temporaires `__rx_tmp<N>` |
| `try_runtime_emitted` | Drapeau : infrastructure `setjmp`/`longjmp` déjà émise |
| `warnings` | Liste des avertissements non bloquants collectés pendant la compilation |

**Méthodes clés :**

- `emit(ligne)` — ajoute une ligne REX-SL.
- `declare_literal(nom, type, explicit)` — émet `var <type> <nom>;`.
- `reassign(nom, type, valeur)` — émet `<nom> <valeur>;`.
- `assign_dynamic(nom, type, valeur)` — réaffectation avec gestion du retypage.
- `retype_as_collection(nom, type)` — émet `retype <nom> <type>;`.
- `push_loop_labels(brk, cont)` / `pop_loop_labels()` — gestion de la pile de boucles.
- `render()` — retourne le code REX-SL complet avec l'en-tête.

---

### 5.5 Instructions (statements)

Chaque construction REX est gérée par une classe dédiée :

| Classe | Instruction(s) REX |
|--------|--------------------|
| `REX_VarStatement` | `var x = ...` |
| `REX_AssignStatement` | `x = ...`, `x += ...`, etc. |
| `REX_UnpackStatement` | `a, b = e1, e2` |
| `REX_ShowStatement` | `show(...)` |
| `REX_IfStatement` | `if/elif/else` |
| `REX_WhileStatement` | `while` |
| `REX_ForStatement` | `for ... in range(...)` / `for ... in str` / `for ... in [...]` |
| `REX_RepeatStatement` | `repeat N` |
| `REX_FuncStatement` | `func nom(...):` |
| `REX_ReturnStatement` | `return expr` |
| `REX_ImportStatement` | `import "..."` |
| `REX_GoStatement` | `go label;` |
| `REX_LabelStatement` | `label nom;` |
| `REX_WriteStatement` | `write(...)`, `writelines(...)` |
| `REX_ListComprehension` | `[expr for x in ...]` |
| `REX_NoneSupport` | Gestion de `None`/`none`/`null` |
| `REX_CollectionLiteral` | Littéraux `[...]`, `(...)`, `{...}`, `{"k": v}` |
| `REX_AssertStatement` | `assert expr[, "message"]` |
| `REX_MatchStatement` | `match expr: / case val: / default:` |
| `REX_TryStatement` | `try: / except [as e]: / finally:` |
| `REX_RaiseStatement` | `raise expr` |
| `REX_ClassStatement` | `class Nom[(Parent)]: / def methode(self, ...):` |

#### Compilation des conditions (`REX_IfStatement`)

Les conditions `if`/`elif`/`else` avec `and`/`or`/`not` sont compilées selon la technique standard du **jumping code** à deux destinations `true_lbl`/`false_lbl`. L'une des deux peut valoir le sentinel `FALL` (None) pour autoriser un fallthrough explicite. Cela garantit un court-circuit logique correct pour toutes les combinaisons d'opérateurs booléens.

---

### 5.6 Préprocesseur d'imports

`preprocess_imports(source, base_dir)` est appelé avant toute analyse lexicale. Il effectue une résolution récursive des directives `import` :

1. Recherche les lignes correspondant aux patterns `IMPORT_LINE_RE`, `IMPORT_LINE_AS_RE` ou `IMPORT_BARE_RE`.
2. Lit le fichier cible, vérifie son en-tête `# REX>`, retire cette en-tête.
3. Si la forme `as alias` est utilisée, renomme toutes les fonctions **et variables globales** du module en `__rx_mod_<alias>_<nom>` et enregistre les exports dans `Emitter.modules`.
4. Pour un evo-import (sans guillemets), génère un getter zero-argument par variable exportée via `_emit_evo_var_accessor()` si l'exécutable expose un champ `"variables"` dans sa métadonnée JSON.
5. Colle le contenu à la place de la ligne `import`.
6. Détecte les imports circulaires via un ensemble `seen` d'en cours de traitement.

---

## 6. Gestion des erreurs et avertissements

| Classe | Déclenchement |
|--------|---------------|
| `REXERROR` | Classe de base pour toutes les erreurs REX |
| `RexResolveError` (sous-classe) | Erreurs de résolution REX → REX-SL |

Les erreurs sont rapportées avec un préfixe indiquant l'étape, chaque ligne du message étant indentée pour rester lisible sur les messages multi-lignes :

```
[REX] erreur de résolution :
  variable non déclarée : x
  > var r = x + 1
  conseil : déclarez x avec 'var x = ...' avant cette ligne
```

En plus des erreurs bloquantes, le compilateur collecte des **avertissements non bloquants** (retypages automatiques, promotions implicites, paramètres non annotés, etc.) qui sont affichés groupés après la compilation :

```
[REX] 2 avertissement(s) :
  [1] retypage automatique : s (number → str)
  [2] promotion implicite : number → float dans l'expression
```

Les erreurs issues de l'étape REX-SL (exécutable externe) sont préfixées `[REX-SL]`.

---

## 7. Limitations connues

Ces limitations sont inhérentes à REX-SL 0.0.23 ou à l'état actuel du compilateur :

- Pas d'itération runtime sur une variable `list` (pas de primitive de longueur de liste).
- `len()` sur `str` uniquement pour les variables (pas de `len` sur une variable `list` variable — seulement sur des littéraux).
- Pas d'affichage de collection contenant des éléments non-littéraux (calculés).
- Le pas (`step`) d'un `for ... in range(...)` doit être un entier **littéral** connu à la compilation.
- Les collections ne peuvent pas être passées en paramètre de fonction directement.
- Pas de mode append pour les fichiers (écriture complète uniquement).
- Pas de fermeture explicite de fichier (lecture/écriture en un seul appel).
- Pas de closures pour les fonctions comme objets (`funcref`).
- Les slices `x[a:b]` et `x[a:b:c]` ne fonctionnent que sur `str`.
- `x[i]` sans `:` n'est pas une indexation générique directe sur `str` : utiliser `charat(s, i)`.
- Les clés d'un `dict` littéral doivent être des chaînes littérales.
- Import disponible uniquement en mode `-f`/`--file` (pas en mode `-o`/`--oneline`).
- Les variables globales d'un module importé **sans** `as` ne sont pas exportées.
- Exceptions : pas de filtrage par type, pas de `raise` nu, pas de `except (A, B):` multi-types, `return` dans un `try` lève une erreur de compilation.
- Classes : pas d'héritage multiple, pas de `super()`, pas de méthodes statiques/de classe, attributs de types scalaires uniquement, `break`/`continue` et itération sur `list` non supportés dans les méthodes.

---

## 8. Historique des versions

| Version | Principales nouveautés |
|---------|------------------------|
| 0.0.1 | Lexer et compilateur de base |
| 0.0.2 | Résolveur de calculs |
| 0.0.3 | Blocs par indentation (Python-style) + `;` |
| 0.0.4 | Base modulable REX-SL, instruction `var`, résolveur d'expressions complet |
| 0.0.5 | Blocs à la Python, fonctions `func`/`return`, `go`/`label`, boucle `repeat` |
| 0.0.6 | En-tête simplifié, `repeat` sans `times`, littéraux de collection, `if`/`elif`/`else` |
| 0.0.7 | Conditions complexes `and`/`or`/`not` avec court-circuit |
| 0.0.8 | Retypage de variable par réaffectation |
| 0.0.9 | Fix retypage vers collection |
| 0.0.10 | Fix conditions complexes, instruction `show()` avec `end=` |
| 0.0.11 | Boucles `while`/`for`, `break`/`continue`, f-strings, gestion de fichiers, `import` |
| 0.0.12 | `for` étendu (str, littéraux, `enumerate`), fonctions natives (builtins), retypage scalaire automatique |
| 0.0.13 | Slice Python `x[a:b]`, fix `show` de collections littérales |
| 0.0.14 | `+=`/`-=`/etc., `**`, `len` sur collections, retour de collection depuis fonction, `x[a:b:c]`, déballage de tuple, list comprehensions, f-strings avec format specs |
| 0.0.15 | Modules avec espaces de noms (`import ... as alias`), fonctions comme objets (`funcref`) |
| 0.0.16 | Refactoring interne pour REX-SL 0.0.23 (opcode `retype` natif) |
| alpha 0.1.1 | Ajout de tous les builtins Python dans le compilateur |
| alpha 0.1.3 | Gestion native de `None` via le type REX-SL `none` |
| alpha 0.1.4 | Opérateur ternaire, `assert`, `match`/`case`/`default`, opérateurs bit à bit `& \| ^ ~ << >>` |
| alpha 0.1.5 | Gestion d'exceptions `try`/`except`/`finally`/`raise` via `setjmp`/`longjmp` |
| alpha 0.1.6 | Classes style Python (`class`, héritage simple, méthodes `def`, `self`) |
| alpha 0.1.7 | Classes utilisables dans les `func` (via `gscrc`), accès aux attributs d'instance depuis le flux principal et les fonctions, messages d'erreur enrichis (ligne, extrait source, conseil), avertissements non bloquants |
| alpha 0.1.8 | Fix `return` dans `try` (erreur explicite), `if`/`while`/`for` et `show()` dans les méthodes de classe, fix héritage (init des champs parents) |
| alpha 0.1.9 | Export des variables globales de modules (`import as`), variables exportées par evo-import via getter JSON |
