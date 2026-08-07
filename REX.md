# REX

Compilateur pour le langage **REX**, a la syntaxe inspiree de Python
(indentation, blocs `:`), qui se resout vers **REX-SL** (compile ensuite
vers C par `REX-SL.py`) plutot que d'etre execute directement.

```
REX (.rex) --[REX.py]--> REX-SL (.rexsl) --[REX-SL.py]--> C (.c) --> executable
```

## Utilisation en ligne de commande

```
python REX.py -f script.rex -c -k -s -r
python REX.py -o "var x = 5; show(x)" -c -r
```

| Option              | Effet                                                                 |
|---------------------|------------------------------------------------------------------------|
| `-f`, `--file`      | fichier `.rex` source (doit commencer par le header `# REX>`)          |
| `-o`, `--oneline`   | code REX passe directement en ligne de commande, instructions separees par `;` |
| `-O`, `--output`    | nom de base du `.rexsl`/`.c`/executable genere (defaut : nom du fichier source) |
| `-c`, `--compiler`  | compile REX -> REX-SL -> C -> executable                               |
| `-r`, `--run`       | execute l'executable genere (implique `-c`)                            |
| `-k`, `--keep-c`    | conserve le `.c` intermediaire au lieu de le supprimer                 |
| `-s`, `--keep-rsl`  | conserve le `.rexsl` intermediaire au lieu de le supprimer             |
| `-d`, `--debug`     | affiche les etapes internes (tokens, code REX-SL genere, ...)          |

Sans `-c` ni `-r`, seul le `.rexsl` est genere/affiche (mode inspection).

## Types

`number`, `float`, `bool`, `str`, `list`, `dict`, `set`, `tuple`.

`tuple` et `set` n'existent pas nativement en REX-SL : ils sont representes
en interne comme une `list` (le set est deduplique **a la compilation**
pour les elements litteraux).

## Declaration de variables (`var`)

```
var x                    # number, valeur par defaut 0
var x = 5                # type infere
var x = (2 + 3) * 4      # expression complete (calcul, appel de fonction, ...)
var number x = 5         # type explicite
var list l = [1, 2, 3]   # collection, type explicite
var l = [1, 2, 3]        # collection, type infere depuis le litteral
```

Litteraux de collection (syntaxe Python) :

```
[1, 2, 3]                # list
(1, 2, 3)   ()   (x,)    # tuple
{1, 2, 3}                # set (deduplique a la compilation)
{"cle": 1, "autre": 2}   # dict (cles obligatoirement des chaines litterales)
```

### Retypage par reaffectation

Une variable dont le type a ete **infere** (non annote explicitement) peut
etre reaffectee vers un litteral de collection, y compris d'un type
different :

```
var s = carre(i)   # infere "number"
s = {1, 2, 3}       # OK : retype "s" en set
s = {4, 5, 6}       # OK : nouvelle reaffectation
```

Un type **explicite** (`var number s = 0`, `var list l = [...]`) reste
verrouille : toute tentative de changement de type leve une erreur de
compilation.

> Note d'implementation : chaque retypage alloue en interne un nom REX-SL
> frais (`__rx_col<N>_<nom>`, via `Emitter._aliases` /
> `Emitter.retype_as_collection`) pour eviter toute collision avec la
> declaration precedente dans la table de symboles de REX-SL (qui persiste
> pour toute la duree du programme genere). Les noms commencant par
> `__rx_` sont reserves au compilateur et ne peuvent pas etre utilises
> comme noms de variable.

## Expressions

Operateurs `+ - * / %`, parentheses, moins unaire, priorite standard,
promotion automatique `number -> float` des qu'un `float` intervient.
`str` n'est valide qu'avec `+` (concatenation), `-` (suppression
d'occurrences) et `*` (repetition `str * number`).

## Fonctions

```
func nom(type arg1, type arg2, ...):
    ...
    return expr
```

Compile vers de vraies fonctions REX-SL (`func` / `endfunc`). Types de
parametres acceptes : `number`, `float`, `bool`, `str` (pas de collection
en parametre). `return` n'est valide qu'a l'interieur d'un `func`, et tous
les `return` d'une meme fonction doivent partager le meme type.

## Fichiers (a la Python)

```
var contenu = read("data.txt")          # lit tout le fichier dans un str
var lignes = readlines("data.txt")      # lit le fichier, une entree par ligne (list)
write("out.txt", contenu)                # ecrit une valeur (mode "w", ecrase)
writelines("out.txt", lignes)            # ecrit une liste, un element par ligne
```

Delegue directement aux opcodes REX-SL `read`/`readlines`/`write`/
`writelines` : lecture/ecriture complete en un seul appel, pas d'objet
"fichier" ouvert/ferme explicitement, pas de mode append (limitations
REX-SL actuelles). `read`/`readlines` s'utilisent uniquement comme valeur
d'un `var` ; `write`/`writelines` sont des instructions.

## Imports (`import`)

```
import "utils.rex";
```

Colle **textuellement** le contenu du fichier importe **a la place** de la
ligne `import` (comme un `#include` C), avant toute analyse lexicale.
Chemin resolu relativement au dossier du fichier qui importe ; recursif ;
detection des imports circulaires ; l'entete `# REX>` du fichier importe
est retiree automatiquement (elle est verifiee, mais pas dupliquee dans le
resultat). L'instruction doit occuper une ligne entiere a elle seule et
n'est disponible qu'en mode fichier (`-f`/`--file`) - pas de dossier de
reference en mode `-o`/`--oneline`.

## Chaines formatees (f-strings)

```
var nom = "Ada"
var age = 36
show(f"{nom} a {age} ans")     # "Ada a 36 ans"
show(f"progres: {{{i}}}")      # accolades doublees {{ }} -> accolade litterale : "progres: {3}"
```

`f"..."` (ou `f'...'`) fonctionne partout ou une chaine est attendue (`var`,
`show`, argument de fonction, ...). Chaque `{expr}` est evalue puis converti
en texte (`number`/`float`/`str`/`bool` uniquement) et concatene au reste.
`{{` / `}}` produisent une accolade litterale, comme en Python.

## Affichage (`show`)

`show(...)` se comporte exactement comme `print()` en Python :

```
show(x)                       # affiche x, retour a la ligne (end="\n" par defaut)
show(a, b, c)                  # affiche "a b c" (valeurs separees par sep=" " par defaut)
show(a, b, sep=", ")           # separateur personnalise : "a, b"
show(x, "")                    # forme positionnelle historique, equivalente a end=""
show(x, end="")                # pas de retour a la ligne
show(x, end="...")             # tout autre 'end'
show(a, b, sep="-", end="!")   # combinable
```

Chaque valeur affichee doit etre de type `number`/`float`/`str`/`bool`
(limitation REX-SL : pas d'affichage direct de `list`/`dict`/`set`/`tuple`) ;
les valeurs non-`str` sont automatiquement converties en texte (comme
`print`), puis toutes les valeurs sont concatenees avec `sep` entre chacune
avant d'etre affichees en un seul `show`/`showln` REX-SL final.

## Conditions

```
if cond:
    ...
elif autre_cond:
    ...
else:
    ...
```

`cond` supporte `and`, `or`, `not` et le groupement par parentheses
(`(a > b) and (c < d)`), compiles en sequences `cdn`/`go` REX-SL avec
court-circuit logique. Une seule comparaison a la fois par atome (pas de
chainage du style `a < b < c`).

## Boucles (`repeat`)

```
repeat 3:
    ...

repeat 3 times:    # forme historique, "times" optionnel
    ...
```

Boucle executee `<expr>` fois **au runtime** (jamais deroulee a la
compilation), equivalente a un compteur + `while` REX-SL.

## Boucles (`while`, `for`)

```
while <cond>:
    ...
```

`<cond>` supporte exactement la meme syntaxe que la condition d'un `if`
(`and`/`or`/`not`, parentheses de groupement, comparaisons).

```
for i in range(5):            # 0, 1, 2, 3, 4
    ...
for i in range(2, 8):         # 2, 3, ..., 7
    ...
for i in range(10, 0, -2):    # 10, 8, 6, 4, 2
    ...
```

Seule la forme `for <nom> in range(...):` est supportee (pas d'iteration
directe sur une liste : REX-SL n'expose aucune primitive de longueur de
liste). `range()` accepte 1 a 3 arguments (`stop` / `start, stop` /
`start, stop, step`), comme en Python. Le `step`, s'il est fourni, doit
etre un entier **litteral** connu a la compilation (positif ou negatif,
jamais nul) - la comparaison de fin de boucle (`<` ou `>`) est choisie
selon son signe.

`break` et `continue` sont geres dans `while`, `for` et `repeat` (chacun
saute vers la fin, resp. l'increment/la reevaluation de la condition, de
la boucle la plus proche qui l'englobe).

## Sauts explicites

```
label debut;
...
go debut;
```

Compile directement vers les opcodes REX-SL `lbl`/`go`.

## Erreurs

Toute erreur de resolution REX -> REX-SL leve une `RexResolveError` (sous-
classe de `REXERROR`), rapportee sur stderr sous la forme
`Erreur de resolution: <message>`. Les erreurs REX-SL elles-memes (issues
de `REX-SL.py`, en aval) sont prefixees `[REX-SL]`.