#* REX compiler (python)
#* > V : alpha 0.1.3
#* > R-ECO : 4.0.0
#* copyright (c) 2026 R-ECO4
#* > work with REX-SL 0.0.23

# 0.0.1     Basic lexer & compiler
# 0.0.2     resolver calcul
# 0.0.3     blocs par indentation (espaces/tabulations) + ';' a la Python
# 0.0.4     base modulable du resolveur REX -> REX-SL : instruction `var`
#           (var x / var x = val / var type x / var type x = val) +
#           resolveur d'expressions complet (+ - * / %, parentheses,
#           moins unaire, priorite des operateurs, promotion number->float)
# 0.0.5     blocs a la Python (entete se terminant par ':' + corps indente)
#           dans le resolveur + instructions : `func nom(type arg, ...):`
#           / `return expr` (-> vraies fonctions REX-SL func/endfunc),
#           appels de fonction dans les expressions `nom(a, b)`,
#           `go <label>;` / `label <nom>;` (goto REX-SL lbl/cdn/go),
#           boucle `repeat <expr> times:` (compteur + lbl/cdn/go, executee
#           au runtime, jamais deroulee a la compilation)
# 0.0.6     header de fichier simplifie `# REX>` (sans numero de version) ;
#           `repeat <expr>:` (le mot-cle `times` final devient optionnel,
#           les deux ecritures restent acceptees) ; litteraux de collection
#           a la syntaxe Python comme valeur d'un `var` : `[..]` (list),
#           `(a, b, ...)` (tuple, y compris `()` et `(x,)`), `{a, b, ...}`
#           (set, deduplique a la compilation), `{"cle": val, ...}` (dict) -
#           tuple/set sont representes en interne comme une `list` REX-SL,
#           REX-SL n'ayant pas de type dedie ; systeme conditionnel
#           `if <cond>: / elif <cond>: / else:` (corps indentes, compile
#           en lbl/cdn/go REX-SL - une seule comparaison a la fois par
#           condition, pas de `and`/`or` composes)
# 0.0.7     conditions complexes a la Python : `and`, `or`, `not` dans les
#           conditions `if`/`elif` (compile en sequences de cdn/go REX-SL
#           avec court-circuit logique - `and` = saute si faux, `or` = saute
#           si vrai) ; `not <cond>` inverse le sens de la comparaison ;
#           parentheses de groupement dans les conditions `(a > b) and (c < d)`
# 0.0.8     retypage de variable par reaffectation de collection : `s = {1,2,3}`
#           apres `var s = carre(i)` est autorise si le type de `s` n'etait
#           pas annote explicitement - le compilateur traque les types
#           "explicites" (annotes par l'utilisateur) vs "inferes" (deduits
#           par le compilateur) via Emitter._explicit_types ; les types
#           explicites restent verrouilles (erreur si changement tente) ;
# 0.0.9     fix : le retypage d'une variable inferee vers une collection
#           (ex: `var s = carre(i)` puis `s = {1,2,3}`, meme famille ou
#           type different) levait a tort "variable deja declaree : s".
#           Fix initial (0.0.9) : alias interne `__rx_col<N>_<nom>`.
#           Remplace en 0.0.23 par l'opcode REX-SL `retype <var> <type>;`
#           qui gere la collision de nom en interne (generation incrementee
#           cote REX-SL) — Emitter.retype_as_collection() et assign_dynamic()
#           emettent desormais directement `retype`, sans alias cote REX.
# 0.0.10    fix : deux bugs distincts dans la compilation des conditions
#           `if`/`elif` complexes (and/or/not), introduits en 0.0.7 :
#             1) REX_IfStatement.CDN_OPS/CDN_OPS_INVERTED utilisaient des
#                noms d'opcode REX-SL inventes ("nequal", "lequal", "gequal")
#                qui n'existent pas cote REX-SL (seuls "equal"/"not_equal"/
#                "greater"/"less"/"greater_equal"/"less_equal", + alias
#                courts, sont reconnus) - toute condition utilisant `!=`,
#                `<=` ou `>=` (ou leur equivalent invert par `not`/court-
#                circuit and/or) faisait echouer la compilation REX-SL avec
#                "operateur de condition non gere : nequal".
#             2) La generation de code court-circuit pour `and`/`or`/`not`
#                melangeait deux notions independantes (direction du saut
#                et "closure complete vs abregee") dans un seul booleen
#                `jump_on_true`, ce qui cassait `or` (une branche fausse
#                sautait directement au bloc suivant au lieu de tester la
#                branche suivante) et `not` applique a un atome terminal
#                (le cas faux tombait par erreur dans le corps du bloc).
#                Reecrit selon la technique standard de "jumping code" a
#                deux destinations true_lbl/false_lbl, l'une des deux
#                pouvant valoir le sentinel FALL (None) pour autoriser un
#                fallthrough explicite et controle (REX_IfStatement.
#                _emit_logic / _emit_atom).
#           feature : instruction `show(<expr>[, <end>])` a la Python
#           (`print(value, end=...)`) : `show(x)` <=> end="\n" par defaut,
#           `show(x, "")` / `show(x, end="")` supprime le retour a la
#           ligne, tout autre `end` est emis via un `show` supplementaire
#           (limitation REX-SL : show/showln n'acceptent qu'une seule valeur).
# 0.0.11    boucles `while <cond>:` et `for <nom> in range(...):` a la
#           Python, compilees en veritable lbl/cdn/go REX-SL (jamais
#           deroulees a la compilation) - `while` reutilise le compilateur
#           de conditions complexes de `if` (and/or/not/parentheses),
#           `for` supporte range(stop) / range(start, stop) /
#           range(start, stop, step) (le pas doit etre un entier litteral
#           connu a la compilation ; pas d'iteration directe sur une
#           liste, REX-SL n'exposant aucune primitive de longueur de
#           liste) ; `break`/`continue` desormais geres dans `while`,
#           `for` et `repeat` (pile de labels par boucle, Emitter.
#           push_loop_labels/pop_loop_labels) ;
#           f-strings a la Python : `f"texte {expr} texte"` (accolades
#           doublees `{{`/`}}` pour un caractere litteral), compilees en
#           concatenation `str` a la compilation (Emitter/ExprCodegen.
#           to_str convertit number/float/str/bool en str via l'opcode
#           REX-SL `change`, ou via un petit branchement cdn/go pour
#           `bool` qui ne passe pas par `change` directement) ;
#           `show(...)` se comporte desormais EXACTEMENT comme `print()`
#           en Python : nombre quelconque de valeurs positionnelles
#           (concatenees avec `sep` entre chacune, defaut `" "`), plus
#           les arguments nommes `sep=` et `end=` (defaut `end="\n"`) -
#           remplace l'ancienne forme limitee a une seule valeur + `end` ;
#           gestion de fichier a la Python : `read(<path>)` / `readlines(<path>)`
#           utilisables comme valeur d'un `var` (`var s = read("f.txt")`,
#           `var l = readlines("f.txt")`), `write(<path>, <valeur>);` /
#           `writelines(<path>, <liste>);` comme instructions - delegue
#           directement aux opcodes REX-SL `read`/`readlines`/`write`/
#           `writelines` (aucun objet "fichier" a la Python, lecture/
#           ecriture complete en un seul appel, pas de mode append/
#           fermeture explicite : limitation REX-SL) ;
#           `import "chemin/fichier.rex";` : colle textuellement le
#           contenu du fichier importe A LA PLACE de la ligne `import`
#           (comme un #include C), AVANT toute analyse lexicale - resolu
#           relativement au dossier du fichier important, recursif,
#           detection des imports circulaires, l'entete `# REX>` du
#           fichier importe est retiree pour eviter le conflit avec celle
#           du fichier principal ; disponible uniquement en mode fichier
#           (-f/--file), pas en mode -o/--oneline (pas de dossier de
#           reference) ; ne modifie strictement rien a REX-SL (REX-SL.py),
#           uniquement des opcodes REX-SL deja existants sont utilises.
# 0.0.12    (ne modifie toujours strictement rien a REX-SL.py, uniquement
#           des opcodes deja existants sont utilises)
#           `for` etendu a la Python au dela de `range(...)` :
#             - `for c in <expr str>:` : boucle RUNTIME caractere par
#               caractere (opcodes REX-SL `len`/`charat`), jamais deroulee ;
#             - `for x in [..]/(..)/{..}:` : quand l'iterable est un
#               LITTERAL de collection ecrit directement dans l'entete, la
#               boucle est deroulee A LA COMPILATION (REX-SL n'exposant
#               aucune primitive de longueur pour une VARIABLE `list`,
#               l'iteration directe sur une telle variable reste refusee
#               avec un message explicite) ;
#             - `for i, v in enumerate(<l'une des deux formes ci-dessus>):`
#               (uniquement cette forme a deux variables - pas de
#               deballage de tuple general) ;
#             - `break`/`continue` geres dans toutes ces formes (etiquettes
#               partagees entre les tours pour la forme deroulee).
#           fonctions natives (utilisables dans n'importe quelle expression,
#           prioritaires sur les fonctions `func` utilisateur de meme nom -
#           ExprCodegen.BUILTIN_ARITY/_call_builtin) : `len(s)` (str
#           uniquement - limitation REX-SL, pas de longueur de liste),
#           `type(x)`, `str(x)`/`int(x)`/`float(x)` (conversions, via
#           `to_str`/opcode `change` sur une copie), `upper(s)`/`lower(s)`/
#           `trim(s)`/`reverse(s)`/`charat(s,i)`/`find(s,sub)`/
#           `slice(s,a,b)`/`replace(s,old,new)` (delegent aux opcodes
#           REX-SL du meme nom, jusqu'ici reserves aux instructions).
#           retypage scalaire automatique a la Python (Emitter.
#           assign_dynamic, utilise par la reaffectation `nom = expr;` ET
#           par les variables de boucle `for`) : reaffecter une variable
#           dont le type n'a PAS ete annote explicitement (`var x = 5` puis
#           `x = "abc"`) change desormais son type au lieu d'echouer -
#           meme mecanisme d'alias interne que le retypage de collection
#           deja existant (0.0.8/0.0.9) ; une variable au type EXPLICITE
#           (`var number x = 5`) reste verrouillee comme avant.
# 0.0.13    (ne modifie toujours strictement rien a REX-SL.py, uniquement
#           des opcodes deja existants sont utilises)
#           slice a la syntaxe Python `x[debut:fin]`, postfixe sur
#           n'importe quelle expression de type 'str' (ExprParser.
#           _parse_slice / ExprCodegen._slice) : `s[a:b]`, avec bornes
#           optionnelles comme en Python - `s[:b]` (debut=0), `s[a:]` /
#           `s[:]` (fin=len(s)) ; chainable (`s[1:][0:2]`) ; delegue au
#           meme opcode REX-SL `slice` que le builtin `slice(s,a,b)`
#           deja existant (0.0.12), donc meme limitation (str uniquement -
#           `x[i]` sans ':' n'est pas une indexation generique, message
#           d'erreur explicite invitant a utiliser charat(s, i)).
#           fix : `show(...)` sur une variable list/tuple/set/dict DONT
#           TOUS LES ELEMENTS ETAIENT DES LITTERAUX a la compilation
#           (`var l = [1,2,3]`, `var d = {"a":1}`, ...) est desormais
#           autorise - REX-SL n'exposant aucun opcode de serialisation
#           collection->str, le resolveur REX capture la representation
#           Python (`repr`) de la collection AU MOMENT DE SA DECLARATION
#           (Emitter.collection_repr, alimente par REX_CollectionLiteral.
#           compile) et l'injecte comme litteral `str` fige dans
#           ExprCodegen.to_str ; une collection contenant au moins un
#           element non-litteral (calcule) n'est toujours pas affichable
#           (erreur explicite, comme avant).
# 0.0.14    ameliorations syntaxiques, la plupart sans modification de REX-SL.py
#           (deux nouvelles fonctionnalites delegent a des opcodes REX-SL
#           deja existants : pow, slicestep) :
#           `+=` / `-=` / `*=` / `/=` / `%=` : cables dans
#           REX_AssignStatement (reecrits en `x = x op expr` -> opcodes
#           REX-SL add/sub/mul/div/mod). Scalaires uniquement.
#           `**` (exposant) : ExprParser._parse_pow -> (binop, "pow", ...)
#           -> opcode REX-SL `pow` (pow() de <math.h>, cast number/float).
#           `len()` etendu aux list/tuple/set/dict (opcode REX-SL `len`).
#           retour de list/dict depuis une fonction dans une expression :
#           via _copy_into_temp (alias de pointeur C via scrc sans copie
#           profonde) - RX_ret reste monotype sur tout le programme.
#           slice avec pas `x[a:b:c]` -> noeud slicestep -> opcode REX-SL
#           `slicestep` (str uniquement, memes limitations que `slice`).
#           deballage de tuple `a, b = e1, e2;` : REX_UnpackStatement -
#           N expressions scalaires OU une list de type element connu ;
#           les droites sont evaluees avant toute affectation (semantique
#           Python, donc `a, b = b, a` fonctionne correctement).
#           list comprehensions `[expr for var in iterable [if cond]]` :
#           REX_ListComprehension - compiles en var list + boucle + append.
#           f-strings avec format specs `{expr:spec}` : lexer detecte le
#           ':' et produit ("tokens_fmt", ..., spec) ; ExprCodegen.
#           _apply_fmt_spec valide (d -> number/float, f/e/g -> float,
#           s -> str) et compile via scrc + snprintf (buffer 128o) ;
#           formes : [<|>][0][largeur][.precision][d|f|g|e|s].
#           Note : modules reels (import as, acces module.fn()) reportes
#           a 0.0.15 (refonte du systeme de symboles cross-fichiers).
# 0.0.15    modules reels avec espace de noms : `import "chemin.rex" as alias;`
#           (preprocess_imports etendu) - les fonctions du fichier importe
#           sont renommees `__rx_mod_<alias>_<fn>` dans le code inline, puis
#           enregistrees dans Emitter.modules[alias] ; l'acces qualifie
#           `alias.fn(args)` est reconnu dans ExprParser._parse_primary_base
#           (IDENT suivi de PUNCT '.' suivi de IDENT suivi de liste) et compile
#           vers l'appel direct `__rx_mod_<alias>_<fn>(args)` ; les variables
#           globales du module ne sont PAS exportees (limitation documentee :
#           espace de noms de fonctions uniquement, pas de variables) ;
#           `import "f.rex";` sans `as` reste inchange (inline textuel, 0.0.11).
#           func as object : `var func f = myfunc;` declare une variable de type
#           interne "funcref" sans emettre de `var` REX-SL - le pointeur de
#           fonction C est emis via `scrc` directement (RetType (*SL_f)(params)
#           = FUNC_myfunc;) ; `f(args)` dans une expression est reconnu par
#           ExprCodegen._call qui detecte le type "funcref" dans Emitter.funcrefs
#           et compile l'appel via un second `scrc` injectant l'appel C indirect ;
#           `f = otherfunc;` (reassignation) est supporte via REX_AssignStatement
#           (branch funcref dans assign_dynamic). Limitation : aucune closure,
#           la signature de la cible est verifiee a la declaration uniquement,
#           l'appel indirect n'est pas verifie a la reassignation.
# 0.0.16    refactoring interne pour REX-SL 0.0.23 (aucun changement de syntaxe
#           REX visible pour l'utilisateur) :
#           - Emitter._aliases / Emitter._col_counter / Emitter.rexsl_name() :
#             SUPPRIMES. Le retypage scalaire et collection est desormais
#             entierement delegue a l'opcode REX-SL `retype <var> <type>;`
#             (0.0.23), qui gere en interne la collision de nom (generation
#             incrementee cote REX-SL). Plus aucun alias de nom necessaire
#             cote REX ; tous les appels rexsl_name() ont ete inlines (la
#             methode etait un simple `return name`).
#           - Emitter.retype_as_collection() / assign_dynamic() : deja
#             simplifies en 0.0.15 pour emettre `retype`, le refactoring
#             supprime uniquement le code mort residuel (_aliases check).
#           - show_list/show_dict/show_set/show_tuple : deja utilises en
#             0.0.15 pour le chemin `show(coll)` ; to_str() conserve
#             list_str/dict_str pour la conversion str (f-strings etc.).
#           - Fix bug : _compile_from_list() referencait `emitter._aliases`
#             (inexistant depuis 0.0.23) -> remplace par acces direct.
# alpha 0.1.3  gestion NATIVE de None via REX-SL 0.0.23 (remplace la
#           simulation par flag bool de la 0.1.0/0.1.2) :
#           - `var x = None` / `var none x` emettra desormais `var none x;`
#             (type REX-SL reel) au lieu de `var number x 0; var bool flag false;`.
#           - `x = None` sur une variable de type 'none' emet `x none;` (RAZ
#             du pointeur C a NULL). Sur une variable d'un autre type, reaffecte
#             en `var none` (retype via `retype x none;`).
#           - `if x is None` / `if x == None` compile via `isnone <tmp> x;`
#             (opcode REX-SL natif) plutot que via le flag bool cache.
#           - `show(x)` quand x est de type 'none' emet `showln none;` /
#             `show none;` directement (REX-SL affiche "None" nativement).
#             Quand x est potentiellement none (type 'none' reel), meme
#             chemin direct. Plus de branchement cdn/go simule.
#           - `return None;` est desormais supporte : emet `return none;`
#             (REX-SL void return) dans une fonction de type de retour 'none'.
#           - `func f(...) -> none:` : type de retour 'none' accepte, compile
#             en `func f ... -> none;` REX-SL (fonction C void).
#           - Suppression de Emitter.none_flags / ensure_none_flag / mark_none /
#             clear_none / flag_name (plus necessaires, simulation abandonnee).
#           - TYPE_NAMES etendu avec "none" ; DEFAULT_VALUES inchange (none
#             n'a pas de valeur par defaut litterale cote REX).
#           - REX_NoneSupport.declare() : emet `var none x;` uniquement ;
#             l'eventuel type explicite different de 'none' sur `var T x = None`
#             (ex: `var number x = None`) devient une erreur explicite (impossibl
#             en REX-SL natif de typer une variable 'none' autrement que 'none').
#           - Emitter.reassign() et assign_dynamic() : branche 'none' ajoutee
#             (`x none;` / `retype x none; x none;`).
#           - ExprCodegen.to_str / to_str_for_value_node / _to_str_reuse :
#             vtype 'none' -> litterale "None" directement (pas de runtime check).
#           - Note : `isnone` fonctionne aussi sur str/list/dict (NULL possible)
#             mais REX.py n'utilise `isnone` que pour les variables de type 'none'.

# alpha 0.1.1  ajout de TOUTES les fonctions builtins Python dans le
#           compilateur REX (ExprCodegen.BUILTIN_ARITY + _call_builtin) :
#           abs(), bool(), chr(), ord(), hex(), oct(), bin(), repr(),
#           ascii(), hash(), id(), callable(), isinstance(), round(),
#           pow() (surcharge, avec forme 3-args modulaire), divmod(),
#           sum(), min(), max(), all(), any(), sorted(), reversed(),
#           list(), tuple(), set(), frozenset(), dict(), range() (forme
#           expression), iter(), print() (alias de show()), input(),
#           format() (avec spec litterale), help(), breakpoint() ;
#           les builtins non implementables en REX/REX-SL (eval, exec,
#           compile, open, super, property, classmethod, staticmethod,
#           issubclass, hasattr, getattr, setattr, delattr, dir, vars,
#           globals, locals, next, aiter, anext, object, zip, map,
#           filter, enumerate comme valeur, bytes, bytearray, memoryview,
#           complex) levent une RexResolveError explicite avec message
#           d'orientation — aucune modification de REX-SL.py (tout passe
#           par des opcodes REX-SL existants ou des injections `scrc`).

"""
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

`number`, `float`, `bool`, `str`, `list`, `dict`, `set`, `tuple`, `none`.

`tuple` et `set` n'existent pas nativement en REX-SL : ils sont representes
en interne comme une `list` (le set est deduplique **a la compilation**
pour les elements litteraux).

`none` correspond au type REX-SL natif `none` (0.0.23) : un pointeur void*
initialise a NULL. Utilisable comme `var none x`, `var x = None`, `x = None`,
`if x is None:`, `show(x)` (affiche "None"), `return None` dans `func -> none`.

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

> Note d'implementation : le retypage emet l'opcode REX-SL `retype <var>
> <type>;` (0.0.23), qui gere en interne la liberation de l'ancienne valeur
> et l'incrementation de generation — aucun alias de nom n'est cree cote
> REX. Les noms commencant par `__rx_` sont reserves au compilateur et ne
> peuvent pas etre utilises comme noms de variable.

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
"""



# =============================================================================
# IMPORTS & CONSTANTES GLOBALES
# =============================================================================

import argparse
import re
import subprocess
import os
import sys
from collections import namedtuple

DEBUG = False

REXSL_VERSION = "0.0.23"

# Un fichier REX (-f) doit commencer par une ligne d'entete de la forme :
#   # REX>
HEADER_RE = re.compile(r"^#\s*REX>\s*$")

# `import "chemin/fichier.rex";` doit occuper une ligne entiere a elle
# seule (le ';' final et les espaces autour du chemin sont optionnels).
IMPORT_LINE_RE = re.compile(r'^(?P<indent>[ \t]*)import\s+"(?P<path>[^"]+)"\s*;?\s*$')

# `import "chemin/fichier.rex" as alias;` : forme avec espace de noms (0.0.15).
# Le groupe `as` est optionnel : si absent c'est un import textuel classique.
IMPORT_LINE_AS_RE = re.compile(
    r'^(?P<indent>[ \t]*)import\s+"(?P<path>[^"]+)"\s+as\s+(?P<alias>[A-Za-z_][A-Za-z0-9_]*)\s*;?\s*$'
)

# evo-import (sans guillemets, a la Python) :
#   import module               -> cherche module.rex ou executable module
#   import module as alias      -> idem avec espace de noms
# Le nom de module est un identifiant simple ou un chemin relatif sans espaces.
IMPORT_BARE_RE = re.compile(
    r'^(?P<indent>[ \t]*)import\s+(?P<mod>[A-Za-z_][A-Za-z0-9_./\\-]*)'
    r'(?:\s+as\s+(?P<alias>[A-Za-z_][A-Za-z0-9_]*))?\s*;?\s*$'
)

# Detecte les declarations `func <nom> ...;` dans un fichier REX-SL inline
# (apres que preprocess_imports ait deja colle le contenu) pour extraire les
# noms de fonctions exportees d'un module. On cherche des lignes REX SOURCE
# (pas REX-SL) de la forme `func <nom>(...):` a l'indentation zero.
_FUNC_DEF_RE = re.compile(r'^func\s+([A-Za-z_][A-Za-z0-9_]*)\s*[\(:]')




# =============================================================================
# ERREURS
# =============================================================================

class REXERROR(Exception):
    pass




# =============================================================================
# INTERFACE EN LIGNE DE COMMANDE (CLI)
# =============================================================================

def build_arg_parser():
    """Construit le parseur d'arguments en ligne de commande du compilateur."""
    parser = argparse.ArgumentParser(
        prog="rex",
        description="REX compiler",
    )
    parser.add_argument(
        "-o", "--oneline",
        metavar="CODE",
        help="code REX a traiter (sur une seule ligne, instructions separees par ;)",
    )
    parser.add_argument(
        "-f", "--file",
        metavar="FILE",
        help="fichier REX a traiter (necessite le header REX, indentation par espaces ou tabulations)",
    )
    parser.add_argument(
        "-O", "--output",
        metavar="OUTPUT_FILE",
        dest="output",
        help="nom du fichier executable (et du .rexsl et .c intermediaire) genere. "
             "Par defaut : meme nom que le script source passe via -f/--file "
             "(sans son extension), ou 'rex_output' en mode -o/--oneline.",
    )
    parser.add_argument(
        "-c", "--compiler",
        action="store_true",
        help="compile le code REX en REX-SL puis en C puis en executable",
    )
    parser.add_argument(
        "-r", "--run",
        action="store_true",
        help="execute l'executable apres compilation (implique -c)",
    )
    parser.add_argument(
        "-k", "--keep-c",
        action="store_true",
        dest="keep_c",
        help="garde le fichier .c genere au lieu de le supprimer",
    )
    parser.add_argument(
        "-s", "--keep-rsl",
        action="store_true",
        dest="keep_rsl",
        help="garde le fichier .rexsl genere au lieu de le supprimer",
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="active le mode de debugage",
    )
    return parser




# =============================================================================
# TOKENS : Token (namedtuple) + Group
# =============================================================================

# ---------------------------------------------------------------------------
# Representation des tokens
# ---------------------------------------------------------------------------

# Un token de base : (type, valeur) + position pour les messages d'erreur.
# type in {"IDENT", "NUMBER", "STRING", "KEYWORD", "OP", "PUNCT",
#          "NEWLINE", "INDENT", "DEDENT"}
Token = namedtuple("Token", ["type", "value", "line", "col"])


class Group:
    """Represente un groupement `[...]` (tableau litteral / indexation).

    Les parentheses `(...)` servent uniquement a la priorite/au
    regroupement arithmetique et syntaxique (appels de fonction compris) :
    elles sont donc retranscrites comme une simple liste Python imbriquee,
    exactement comme decrit dans la docstring de REX_Lexer.

    Les crochets `[...]` portent une semantique differente (tableau /
    acces indexe) : on les represente donc avec ce petit wrapper afin de
    ne jamais les confondre avec un groupe de priorite lors des etapes
    suivantes du compilateur (resolveur, parseur, ...).

    Note : depuis la 0.0.3, les blocs de code ne s'ecrivent plus avec des
    accolades `{}` (qui n'existent plus dans REX) mais par indentation, a
    la maniere de Python -> voir REX_Lexer.
    """

    __slots__ = ("kind", "items", "line", "col")

    def __init__(self, kind, items, line, col):
        self.kind = kind        # "[]"
        self.items = items      # liste de tokens / sous-groupes / Group
        self.line = line
        self.col = col

    def __repr__(self):
        opening, closing = self.kind[0], self.kind[1]
        return f"{opening}{self.items!r}{closing}"

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __eq__(self, other):
        return (
            isinstance(other, Group)
            and self.kind == other.kind
            and self.items == other.items
        )




# =============================================================================
# LEXER : REX_Lexer
# =============================================================================

class REX_Lexer:
    """Lexer du langage REX (fonctionnement a la Python).

    Cette classe decoupe le code source en une liste de tokens qui peut
    elle meme contenir des sous-listes de tokens : chaque parenthese
    ouvrante `(` (regroupement/appel) ou crochet ouvrant `[` (tableau/
    index) demarre une nouvelle liste imbriquee, qui se referme sur le
    `)`/`]` correspondant, sans que la parenthese/le crochet lui-meme ne
    soit emis comme token. Ainsi :

        a = b + (c * 4)

    produit (schematiquement) :

        [
            Token("IDENT", "a"), Token("OP", "="),
            Token("IDENT", "b"), Token("OP", "+"),
            [
                Token("IDENT", "c"), Token("OP", "*"), Token("NUMBER", 4),
            ],
            Token("NEWLINE", ...),
        ]

    ce qui correspond a l'exemple :
        [("ident","a"),("op","="),("ident","b"),("op","+"),
         [("ident","c"),("op","*"),("number",4)]]
    (chaque Token se comporte comme un tuple (type, valeur, ligne, colonne),
    donc tok[0] et tok[1] redonnent (type, valeur)).

    Fonctionnement "a la Python" (0.0.3) :
      - Il n'y a plus d'accolades `{}` pour delimiter les blocs. Les
        blocs (corps de if/while/for/func, ...) sont delimites par
        l'INDENTATION, en utilisant des espaces ou des tabulations (1 tab = 4 espaces).
      - A chaque augmentation du niveau d'indentation, un token
        `Token("INDENT", niveau, ligne, 1)` est emis ; a chaque
        diminution, un ou plusieurs `Token("DEDENT", ...)`.
      - Chaque ligne logique de code se termine par un token
        `Token("NEWLINE", "\\n", ligne, colonne)` (comme en Python, les
        lignes vides et les lignes 100% commentaire ne comptent pas et
        n'emettent ni NEWLINE ni INDENT/DEDENT).
      - A l'interieur d'un groupe `(...)` ou `[...]`, les sauts de ligne
        sont ignores (continuation implicite, comme en Python) : aucune
        gestion d'indentation ni de NEWLINE n'y est effectuee.
      - `;` reste un simple token PUNCT : comme en Python, il sert (au
        niveau du parseur, pas du lexer) a separer plusieurs instructions
        sur une seule et meme ligne logique. C'est ce qui permet au mode
        `-o/--oneline` de fonctionner sans aucune notion d'indentation :
        tout tient sur une seule ligne, les instructions sont separees
        par `;`.

    Sont egalement geres :
      - les identifiants / mots-cles                (IDENT / KEYWORD)
      - les nombres entiers, flottants, hex, binaire (NUMBER)
      - les chaines de caracteres avec echappements  (STRING)
      - les operateurs mono et multi-caracteres      (OP)
      - la ponctuation ; , : .                       (PUNCT)
      - les commentaires ligne `# ...` et bloc `#* ... *#`
    """

    KEYWORDS = {
        "if", "elif", "else", "while", "for", "func", "return",
        "let", "const", "var", "true", "false", "null", "break", "continue",
        "import", "class", "and", "or", "not", "in", "is",
        "go", "label", "repeat", "times", "show",
        "write", "writelines",
        "None", "none",
    }

    # Tri par longueur decroissante pour un matching "greedy" correct
    # (ex : ">>=" doit etre teste avant ">>" et ">").
    MULTI_OPS = sorted(
        [
            "<<=", ">>=", "**=",
            "==", "!=", "<=", ">=", "&&", "||", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=", "->", "::", "..", "**",
        ],
        key=len,
        reverse=True,
    )

    SINGLE_OPS = set("+-*/%=<>!&|^~?")
    PUNCT = set("();,:.")

    # () et [] existent depuis la 0.0.3 ; {} est reintroduit en 0.0.6,
    # uniquement pour les litteraux dict/set (syntaxe Python) - jamais pour
    # delimiter un bloc de code (toujours par indentation, voir plus haut).
    OPEN_BRACKETS = {"(": ")", "[": "]", "{": "}"}
    CLOSE_BRACKETS = {")", "]", "}"}

    ESCAPES = {
        "n": "\n", "t": "\t", "r": "\r", "\\": "\\",
        "'": "'", '"': '"', "0": "\0",
    }

    def __init__(self, source):
        self.src = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.length = len(source)
        self.indent_stack = [0]
        self.pending = []  # tokens INDENT/DEDENT en attente d'insertion

    # -- utilitaires bas niveau ------------------------------------------------

    def _peek(self, offset=0):
        p = self.pos + offset
        if p < self.length:
            return self.src[p]
        return ""

    def _advance(self):
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _error(self, message):
        raise REXERROR(f"[Lexer] {message} (ligne {self.line}, colonne {self.col})")

    # -- gestion des lignes / indentation (a la Python) --------------------------

    def _handle_line_start(self):
        """Analyse le debut d'une ligne logique (uniquement appele au
        niveau racine, hors de tout `(`/`[`) : compte l'indentation en
        espaces et tabulations, ignore les lignes vides / 100% commentaire,
        et pousse les INDENT/DEDENT necessaires dans self.pending.

        Retourne True si la ligne contient effectivement du code a
        tokeniser, False si la ligne doit etre entierement ignoree
        (vide ou commentaire seul)."""
        indent = 0
        while True:
            ch = self._peek()
            if ch == " ":
                self._advance()
                indent += 1
            elif ch == "\t":
                self._advance()
                indent += 4  # Une tabulation équivaut à 4 espaces d'indentation
            else:
                break

        if self._peek() == "#" and self._peek(1) == "*":
            self._skip_block_comment()
        elif self._peek() == "#":
            self._skip_line_comment()

        if self._peek() in ("\n", ""):
            if self._peek() == "\n":
                self._advance()
            return False  # ligne vide ou 100% commentaire : ignoree

        self._apply_indent(indent)
        return True

    def _apply_indent(self, indent):
        top = self.indent_stack[-1]
        if indent > top:
            self.indent_stack.append(indent)
            self.pending.append(Token("INDENT", indent, self.line, 1))
        elif indent < top:
            while indent < self.indent_stack[-1]:
                self.indent_stack.pop()
                self.pending.append(Token("DEDENT", self.indent_stack[-1], self.line, 1))
            if indent != self.indent_stack[-1]:
                self._error(
                    "indentation incoherente : ce niveau ne correspond a "
                    "aucun niveau d'indentation ouvert"
                )
        # indent == top : rien a faire, meme niveau que la ligne precedente

    # -- espaces / commentaires -------------------------------------------------

    def _skip_inline(self, ignore_newline):
        """Consomme espaces/tabulations/commentaires. Si `ignore_newline`
        est vrai (on est a l'interieur d'un groupe `(`/`[`), les sauts de
        ligne sont eux aussi consommes comme de simples espaces
        (continuation implicite, comme en Python)."""
        while self.pos < self.length:
            ch = self._peek()
            if ch in (" ", "\t", "\r"):
                self._advance()
            elif ch == "\n" and ignore_newline:
                self._advance()
            elif ch == "#" and self._peek(1) == "*":
                self._skip_block_comment()
            elif ch == "#":
                self._skip_line_comment()
            else:
                break

    def _skip_line_comment(self):
        while self.pos < self.length and self._peek() != "\n":
            self._advance()

    def _skip_block_comment(self):
        start_line, start_col = self.line, self.col
        self._advance()  # '#'
        self._advance()  # '*'
        while True:
            if self.pos >= self.length:
                raise REXERROR(
                    f"[Lexer] commentaire bloc '#* ... *#' non ferme "
                    f"(ouvert ligne {start_line}, colonne {start_col})"
                )
            if self._peek() == "*" and self._peek(1) == "#":
                self._advance()
                self._advance()
                return
            self._advance()

    # -- scanners de tokens simples ----------------------------------------------

    def _scan_number(self):
        line, col = self.line, self.col
        start = self.pos
        is_float = False

        if self._peek() == "0" and self._peek(1) in ("x", "X"):
            self._advance()
            self._advance()
            while self._peek() and self._peek() in "0123456789abcdefABCDEF_":
                self._advance()
            text = self.src[start:self.pos].replace("_", "")
            return Token("NUMBER", int(text, 16), line, col)

        if self._peek() == "0" and self._peek(1) in ("b", "B"):
            self._advance()
            self._advance()
            while self._peek() in ("0", "1", "_"):
                self._advance()
            text = self.src[start:self.pos].replace("_", "")
            return Token("NUMBER", int(text, 2), line, col)

        while self._peek().isdigit() or self._peek() == "_":
            self._advance()

        if self._peek() == "." and self._peek(1).isdigit():
            is_float = True
            self._advance()
            while self._peek().isdigit() or self._peek() == "_":
                self._advance()

        if self._peek() in ("e", "E") and (
            self._peek(1).isdigit()
            or (self._peek(1) in "+-" and self._peek(2).isdigit())
        ):
            is_float = True
            self._advance()
            if self._peek() in "+-":
                self._advance()
            while self._peek().isdigit():
                self._advance()

        text = self.src[start:self.pos].replace("_", "")
        value = float(text) if is_float else int(text)
        return Token("NUMBER", value, line, col)

    def _scan_string(self):
        line, col = self.line, self.col
        quote = self._advance()  # ' ou "
        # Detection des triples guillemets `"""..."""` / `'''...'''`
        if self._peek() == quote and self._peek(1) == quote:
            self._advance()  # 2e guillemet
            self._advance()  # 3e guillemet
            return self._scan_triple_string(quote, line, col)
        # Chaine simple-ligne classique
        chars = []
        while True:
            if self.pos >= self.length:
                self._error("chaine de caracteres non fermee")
            ch = self._peek()
            if ch == quote:
                self._advance()
                break
            if ch == "\n":
                self._error("saut de ligne interdit dans une chaine (utilisez \\n ou des triples guillemets \"\"\"...\"\"\")")
            if ch == "\\":
                self._advance()
                esc = self._peek()
                if esc in self.ESCAPES:
                    chars.append(self.ESCAPES[esc])
                    self._advance()
                elif esc == "":
                    self._error("chaine de caracteres non fermee")
                else:
                    self._error(f"sequence d'echappement inconnue: \\{esc}")
            else:
                chars.append(ch)
                self._advance()
        return Token("STRING", "".join(chars), line, col)

    def _scan_triple_string(self, quote, line, col):
        """Scanne une chaine delimitee par des triples guillemets `\"\"\"...\"\"\"` ou
        `'''...'''` (deja consommes par l'appelant). Autorise les sauts de ligne
        et toutes les sequences d'echappement habituelles. La chaine se termine
        au premier `qqq` (trois fois le meme guillemet) non echappe."""
        chars = []
        while True:
            if self.pos >= self.length:
                self._error(
                    f"chaine triple-guillemets non fermee "
                    f"('{quote*3}' de fermeture manquant, ouvert ligne {line})"
                )
            ch = self._peek()
            # Fermeture : trois guillemets consecutifs non echappes
            if ch == quote and self._peek(1) == quote and self._peek(2) == quote:
                self._advance()
                self._advance()
                self._advance()
                break
            if ch == "\\":
                self._advance()
                esc = self._peek()
                if esc in self.ESCAPES:
                    chars.append(self.ESCAPES[esc])
                    self._advance()
                elif esc == "":
                    self._error("chaine triple-guillemets non fermee")
                else:
                    self._error(f"sequence d'echappement inconnue: \\{esc}")
            else:
                # Les sauts de ligne sont autorises dans les chaines triple-quoted
                chars.append(ch)
                self._advance()
        return Token("STRING", "".join(chars), line, col)

    def _scan_fstring(self):
        """Scanne une f-string `f"..."` / `f'...'` / `f\"\"\"...\"\"\"` / `f'''...'''`
        (le `f`/`F` a deja ete consomme par l'appelant). Retourne un Token("FSTRING", parts, ..)
        ou `parts` est une liste ordonnee de morceaux :
          - ("str", texte)          : texte litteral (echappements deja resolus)
          - ("tokens", token_list)  : contenu de `{expr}` deja tokenize (via
                                       un REX_Lexer recursif sur le texte de
                                       l'expression), pret pour ExprParser.
        `{{` et `}}` produisent une accolade litterale (comme en Python).
        Les f-strings triple-quoted autorisent les sauts de ligne."""
        line, col = self.line, self.col
        quote = self._advance()
        # Detection des triples guillemets f"""...""" / f'''...'''
        triple = False
        if self._peek() == quote and self._peek(1) == quote:
            self._advance()  # 2e guillemet
            self._advance()  # 3e guillemet
            triple = True
        parts = []
        buf = []

        def flush():
            if buf:
                parts.append(("str", "".join(buf)))
                buf.clear()

        while True:
            if self.pos >= self.length:
                self._error("f-string non fermee")
            ch = self._peek()
            # Fermeture
            if triple:
                if ch == quote and self._peek(1) == quote and self._peek(2) == quote:
                    self._advance(); self._advance(); self._advance()
                    break
            else:
                if ch == quote:
                    self._advance()
                    break
            if ch == "\n" and not triple:
                self._error("saut de ligne interdit dans une f-string (utilisez \\n ou des triples guillemets f\\\"\\\"\\\"...\\\"\\\"\\\")")
            if ch == "{" and self._peek(1) == "{":
                buf.append("{")
                self._advance()
                self._advance()
                continue
            if ch == "}" and self._peek(1) == "}":
                buf.append("}")
                self._advance()
                self._advance()
                continue
            if ch == "}":
                self._error("'}' inattendu dans une f-string (utilisez '}}' pour une accolade litterale)")
            if ch == "{":
                flush()
                self._advance()  # consomme '{'
                depth = 1
                expr_chars = []
                while True:
                    if self.pos >= self.length:
                        self._error("expression f-string non fermee (accolade '}' manquante)")
                    c2 = self._peek()
                    if c2 == "\n":
                        self._error("saut de ligne interdit dans une expression f-string")
                    if c2 == "{":
                        depth += 1
                    elif c2 == "}":
                        depth -= 1
                        if depth == 0:
                            self._advance()
                            break
                    expr_chars.append(c2)
                    self._advance()
                expr_text = "".join(expr_chars)
                if not expr_text.strip():
                    self._error("expression f-string vide entre accolades ('{}')")
                # 0.0.14 : format spec `{expr:spec}` a la Python.
                # On cherche le premier ':' au niveau zero des
                # parentheses/crochets (les accolades ont deja ete
                # consommees par la boucle de depth ci-dessus).
                fmt_spec = None
                depth2 = 0
                colon_pos = None
                for ci, ch2 in enumerate(expr_text):
                    if ch2 in ("(", "["):
                        depth2 += 1
                    elif ch2 in (")", "]"):
                        depth2 -= 1
                    elif ch2 == ":" and depth2 == 0:
                        colon_pos = ci
                        break
                if colon_pos is not None:
                    fmt_spec = expr_text[colon_pos + 1:].strip()
                    expr_text = expr_text[:colon_pos].strip()
                    if not expr_text:
                        self._error(
                            "expression f-string vide avant ':' (spec de format)"
                        )
                sub_tokens = REX_Lexer(expr_text).tokenize()
                if sub_tokens and isinstance(sub_tokens[-1], Token) and sub_tokens[-1].type == "NEWLINE":
                    sub_tokens = sub_tokens[:-1]
                if fmt_spec is not None:
                    parts.append(("tokens_fmt", sub_tokens, fmt_spec))
                else:
                    parts.append(("tokens", sub_tokens))
                continue
            if ch == "\\":
                self._advance()
                esc = self._peek()
                if esc in self.ESCAPES:
                    buf.append(self.ESCAPES[esc])
                    self._advance()
                elif esc == "":
                    self._error("f-string non fermee")
                else:
                    self._error(f"sequence d'echappement inconnue: \\{esc}")
                continue
            buf.append(ch)
            self._advance()

        flush()
        return Token("FSTRING", parts, line, col)

    def _scan_ident_or_keyword(self):
        line, col = self.line, self.col
        start = self.pos
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()
        text = self.src[start:self.pos]
        if text in self.KEYWORDS:
            return Token("KEYWORD", text, line, col)
        return Token("IDENT", text, line, col)

    def _scan_operator_or_punct(self):
        line, col = self.line, self.col
        for op in self.MULTI_OPS:
            if self.src.startswith(op, self.pos):
                for _ in op:
                    self._advance()
                return Token("OP", op, line, col)
        ch = self._peek()
        if ch in self.PUNCT:
            self._advance()
            return Token("PUNCT", ch, line, col)
        if ch in self.SINGLE_OPS:
            self._advance()
            return Token("OP", ch, line, col)
        self._error(f"caractere inattendu: {ch!r}")

    def _scan_single_token(self, ch):
        if ch in ("f", "F") and self._peek(1) in ("'", '"'):
            self._advance()  # consomme le prefixe 'f'/'F'
            return self._scan_fstring()
        if ch.isdigit() or (ch == "." and self._peek(1).isdigit()):
            return self._scan_number()
        if ch in ("'", '"'):
            return self._scan_string()
        if ch in ("s", "S") and self.src.startswith("scrc>", self.pos):
            # `scrc> "code C"` : instruction d'injection C brute (REX native).
            # On retourne un token synthetique KEYWORD "scrc>" afin que le
            # resolveur puisse le reconnaitre dans LINE_HANDLERS sans entrer
            # en conflit avec les IDENT ordinaires.
            tok_line, tok_col = self.line, self.col
            for _ in "scrc>":
                self._advance()
            return Token("KEYWORD", "scrc>", tok_line, tok_col)
        if ch.isalpha() or ch == "_":
            return self._scan_ident_or_keyword()
        return self._scan_operator_or_punct()

    # -- coeur recursif (regroupement par parentheses/crochets + lignes) --------

    def _lex_sequence(self, closing):
        """Lit des tokens jusqu'a rencontrer `closing`, ou la fin du
        fichier si `closing` vaut None (niveau racine).

        Au niveau racine (`closing is None`), la logique "a la Python"
        s'applique : indentation en tabulations/espaces (INDENT/DEDENT) et fin de
        ligne logique (NEWLINE). A l'interieur d'un groupe `(`/`[`, les
        sauts de ligne sont de simples espaces ignores (continuation
        implicite), exactement comme en Python."""
        top_level = closing is None
        tokens = []
        at_bol = top_level
        line_has_token = False

        while True:
            if top_level and at_bol:
                has_content = self._handle_line_start()
                tokens.extend(self.pending)
                self.pending = []
                if not has_content:
                    if self.pos >= self.length:
                        break
                    continue
                at_bol = False
                line_has_token = False

            self._skip_inline(ignore_newline=not top_level)

            if self.pos >= self.length:
                if closing is not None:
                    self._error(
                        f"parenthese/crochet non ferme, '{closing}' attendu"
                    )
                break

            ch = self._peek()

            if top_level and ch == "\n":
                self._advance()
                if line_has_token:
                    tokens.append(Token("NEWLINE", "\n", self.line - 1, self.col))
                at_bol = True
                continue

            if ch in self.CLOSE_BRACKETS:
                if closing is None or ch != closing:
                    self._error(
                        f"'{ch}' inattendu (fermeture attendue: "
                        f"{closing or 'aucune'})"
                    )
                self._advance()
                return tokens

            if ch in self.OPEN_BRACKETS:
                open_line, open_col = self.line, self.col
                bracket = self._advance()
                expected_close = self.OPEN_BRACKETS[bracket]
                inner = self._lex_sequence(expected_close)
                if bracket == "(":
                    tokens.append(inner)  # regroupement "nu" (priorite/appel/tuple)
                elif bracket == "[":
                    tokens.append(Group("[]", inner, open_line, open_col))
                else:
                    tokens.append(Group("{}", inner, open_line, open_col))
                if top_level:
                    line_has_token = True
                continue

            tok = self._scan_single_token(ch)
            tokens.append(tok)
            if top_level:
                line_has_token = True

        if top_level:
            if line_has_token:
                tokens.append(Token("NEWLINE", "\n", self.line, self.col))
            while len(self.indent_stack) > 1:
                self.indent_stack.pop()
                tokens.append(Token("DEDENT", self.indent_stack[-1], self.line, self.col))

        return tokens

    def tokenize(self):
        """Point d'entree public : retourne la liste (imbriquee) des
        tokens representant l'integralite du code source, avec
        NEWLINE/INDENT/DEDENT au niveau racine."""
        self.pos = 0
        self.line = 1
        self.col = 1
        self.indent_stack = [0]
        self.pending = []
        return self._lex_sequence(None)




# =============================================================================
# CONSTANTES DU RESOLVEUR
# =============================================================================


# ---------------------------------------------------------------------------
# Resolveur REX -> REX-SL
# ---------------------------------------------------------------------------
#
# Cette partie transpile l'arbre de tokens produit par REX_Lexer en code
# source REX-SL (texte, compatible avec REX-SL.py).
#
# Le tout est concu pour etre MODULABLE :
#   - chaque instruction REX (mot-cle en tete de ligne logique, ex: "var")
#     est geree par un "statement compiler" independant, enregistre dans
#     REX_Resolver.STATEMENT_HANDLERS. Ajouter une nouvelle instruction
#     (show, if, while, func...) ne demande qu'une nouvelle fonction/classe
#     "compile(tokens, emitter)" + une entree dans ce dictionnaire.
#   - la resolution des expressions (calculs) est geree par ExprParser
#     (analyse) + ExprCodegen (generation), et gere les parentheses ainsi
#     que la priorite des operateurs via ExprParser.PRECEDENCE : ajouter un
#     operateur revient a ajouter une entree dans cette table (du plus
#     faible au plus fort), sans toucher au reste du moteur.
#
# Alpha 0.0.4 : seule l'instruction "var" (declaration de variable, avec
# ou sans type explicite, avec ou sans valeur) et la resolution complete
# des calculs (+ - * / %, parentheses, moins unaire) sont implementees.
# Les autres instructions (show, if, while, func, ...) restent a ajouter
# en suivant exactement le meme schema.

TYPE_NAMES = {"number", "float", "bool", "str", "list", "dict", "set", "tuple", "func", "funcref", "none"}

# Valeur par defaut REX-SL utilisee quand une variable est declaree sans
# valeur explicite (`var x;` / `var number x;`). list/dict n'ont pas de
# valeur initiale en REX-SL (voir doc REX-SL : "var list <name>;").
DEFAULT_VALUES = {
    "number": "0",
    "float": "0.0",
    "bool": "false",
    "str": '""',
}

# opérande factice pour toute expression de type "none" - ne doit JAMAIS
# être émis tel quel dans une ligne REX-SL (chaque point de consommation
# intercepte le type "none" avant de l'utiliser).
NONE_REF = "__RX_NONE__"

class RexResolveError(REXERROR):
    """Erreur levee pendant la resolution REX -> REX-SL (typage, syntaxe
    d'une instruction, expression invalide, ...)."""
    pass




# =============================================================================
# EMITTER : gestion du code REX-SL et de la table des symboles
# =============================================================================

class Emitter:
    """Accumule le code REX-SL genere ainsi que la table des symboles
    (nom de variable -> type REX-SL) necessaire a l'inference de type des
    expressions et a la generation des variables temporaires.

    Point important (verifie dans REX-SL.py / REX_SL_CODE) :
      - `var <type> <name> [valeur];` exige que <valeur>, si presente,
        soit un LITTERAL du type declare (un identifiant y est refuse) ;
      - a l'inverse, les opcodes de calcul `add/sub/mul/div/mod <dest> ..;`
        AUTO-DECLARENT <dest> avec le type resultant s'il n'existe pas
        encore (cf. `is_declaration = dest_raw_name not in symbol_table["var"]`
        dans REX-SL.py).
    Le resolveur exploite donc cette auto-declaration pour les variables
    temporaires (jamais de `var` emis pour elles) et pour toute variable
    utilisateur initialisee par un calcul (elle est auto-declaree par le
    dernier opcode de la chaine, voir Emitter.assign_computed)."""

    def __init__(self):
        self.lines = []
        self.types = {}
        self._temp_counter = 0
        self._loop_counter = 0
        # name -> (param_types_list, return_type_or_None) ; alimente par
        # REX_FuncStatement (declaration) et consomme par ExprCodegen._call.
        self.functions = {}
        # pile d'instantanes de self.types, empilee/depilee a chaque entree/
        # sortie de 'func' pour isoler completement les parametres et les
        # variables locales de la fonction (jamais visibles a l'appelant).
        self._scope_stack = []
        # None hors de tout 'func', sinon {"name", "params", "return_type"}
        # le temps de compiler le corps de la fonction actuellement ouverte.
        self._current_func = None
        # Ensemble des variables dont le type a ete EXPLICITEMENT annote par
        # l'utilisateur (`var number x`, `var list l`, ...). Les variables
        # dont le type est INFERE (var x = expr, var s = carre(i), ...) n'y
        # figurent pas : leur type peut etre change par une reaffectation
        # ulterieure (s = {1,2,3} apres var s = carre(i)).
        # Depuis REX-SL 0.0.23, le retypage est delegue a l'opcode `retype`
        # de REX-SL : plus besoin de la couche _aliases/rexsl_name() cote REX.py
        # (supprimee en 0.0.23 — retype gere tout en interne dans REX-SL).
        self._explicit_types = set()
        # pile de (continue_lbl, break_lbl) : une entree par boucle REX
        # (while/for/repeat) actuellement ouverte, utilisee par 'break' et
        # 'continue' pour retrouver les etiquettes REX-SL de la boucle la
        # plus proche qui les englobe (cf. push_loop_labels/pop_loop_labels).
        self._loop_stack = []
        # collection_repr : conserve pour la compatibilite interne (utilise par
        # REX_IndexAssignStatement pour invalider le repr apres une modification).
        self.collection_repr = {}
        # nom REX-SL -> type d'element ('number'/'float'/'bool'/'str') pour une
        # collection list/tuple/set HOMOGENE (tous les elements connus a ce jour
        # etant du meme type) ; None si heterogene/inconnu (aucun element encore
        # ajoute, ou types differents rencontres) - alimente par
        # REX_CollectionLiteral.compile et REX_AppendStatement, consomme par
        # l'indexation generique `l[i]` (ExprCodegen._index) et par
        # `for x in <variable list>:` (REX_ForStatement) pour connaitre le type
        # a donner a l'opcode etendu `get <liste> <type> <dest> <idx>;`.
        self.elem_types = {}
        # meme principe que ci-dessus, pour la VALEUR d'un dict (les cles sont
        # toujours 'str', seul le type de la valeur varie) - alimente par
        # REX_CollectionLiteral.compile (branche dict), consomme par `d["cle"]`.
        self.dict_value_types = {}
        # Miroir cote REX.py de symbol_table["rx_ret_type"] (REX-SL.py) :
        # RX_ret est un registre C GLOBAL UNIQUE, monotype pour toute la
        # duree du programme genere (fige par le premier 'exec' vers une
        # fonction retournant une valeur - cf. REX-SL.py REX_SL_CODE.
        # exec_call). None tant qu'aucun 'exec' de ce type n'a encore ete
        # emis. Permet a ExprCodegen._call de detecter EN AMONT, cote
        # REX.py, un appel dont le type de retour entre en conflit avec
        # celui deja fige pour RX_ret - et de basculer sur une injection C
        # directe (scrc) plutot que de laisser REX-SL.py rejeter la
        # compilation avec "RX_ret est deja de type ...".
        self.rx_ret_type = None
        # 0.0.15 : registre des modules importes avec alias
        # {alias: {"funcs": {func_rex_name: mangled_name}, "base_dir": str}}
        # Alimente par preprocess_imports (enrichi) via Emitter.register_module().
        # Consomme par ExprCodegen pour resoudre `alias.fn(args)`.
        self.modules = {}
        # 0.0.15 : variables de type "funcref" (pointeurs de fonction).
        # {var_name: (mangled_func_name, param_types, param_names, defaults, return_type,
        #             elem_type, dict_value_type)}
        # Alimente par REX_VarStatement (branche "var func f = myfunc;").
        # Consomme par ExprCodegen._call pour les appels indirects `f(args)`.
        self.funcrefs = {}

        # Parametres de fonctions sans annotation de type (inferes "number" par defaut).
        # {func_name: {"line_idx": int, "param_positions": [(pos, param_name), ...]}}
        # Quand le premier appel est compile, on patche la ligne REX-SL emise
        # pour remplacer "number" par le type reel de l'argument.
        self.pending_func_sigs = {}

    def note_elem_type(self, emit_name, vtype):
        """Met a jour elem_types[emit_name] apres l'ajout d'un element de type
        `vtype` : premiere fois -> on retient ce type ; type different d'un
        appel precedent -> collection heterogene, elem_types passe a None
        (indexation generique refusee, message explicite)."""
        if emit_name not in self.elem_types:
            self.elem_types[emit_name] = vtype
        elif self.elem_types[emit_name] != vtype:
            self.elem_types[emit_name] = None

    def get_elem_type(self, emit_name):
        return self.elem_types.get(emit_name)

    def note_dict_value_type(self, emit_name, vtype):
        if emit_name not in self.dict_value_types:
            self.dict_value_types[emit_name] = vtype
        elif self.dict_value_types[emit_name] != vtype:
            self.dict_value_types[emit_name] = None

    def get_dict_value_type(self, emit_name):
        return self.dict_value_types.get(emit_name)

    def emit(self, line):
        self.lines.append(line)

    def declare_literal(self, name, vtype, literal_repr=None, explicit=False):
        """Emet `var <type> <name> [litteral];` (forme directe, valeur
        obligatoirement un litteral REX-SL ou absente).

        `explicit` doit etre True quand le type a ete annote explicitement
        par l'utilisateur (`var number x`, `var list l`, ...) : cela
        verrouille le type et interdit tout retypage ulterieur par une
        reaffectation de collection. Si False (type infere), une reaffectation
        vers un litteral de collection d'un type different reste autorisee."""
        if name in self.types:
            raise RexResolveError(f"variable deja declaree : {name}")
        if vtype not in TYPE_NAMES:
            raise RexResolveError(f"type inconnu : {vtype}")
        self.types[name] = vtype
        if explicit:
            self._explicit_types.add(name)
        # Le type 'none' n'accepte pas de valeur initiale en REX-SL (var none x;)
        if vtype == "none" or literal_repr is None:
            self.emit(f"var {vtype} {name};")
        else:
            self.emit(f"var {vtype} {name} {literal_repr};")

    def assign_computed(self, name, ref, source_type, target_type, explicit=False):
        """Assigne le resultat d'un calcul (`ref`, deja evalue par
        ExprCodegen, de type `source_type`) a une variable `name` pas
        encore declaree, via un opcode d'identite (add ... 0 / 0.0 / "")
        qui l'auto-declare avec le type `target_type` (promotion
        number -> float acceptee, comme pour une declaration `var`
        explicite).

        `explicit` : True si le type cible a ete annote explicitement par
        l'utilisateur (verrouille le type contre tout retypage ulterieur)."""
        if name in self.types:
            raise RexResolveError(f"variable deja declaree : {name}")
        promotable = source_type == target_type or (source_type == "number" and target_type == "float")
        if not promotable:
            raise RexResolveError(
                f"type declare '{target_type}' incompatible avec la valeur de type "
                f"'{source_type}' pour la variable '{name}'"
            )
        if target_type == "number":
            self.emit(f"add {name} {ref} 0;")
        elif target_type == "float":
            self.emit(f"add {name} {ref} 0.0;")
        elif target_type == "str":
            self.emit(f'add {name} {ref} "";')
        else:
            raise RexResolveError(
                f"impossible d'assigner un resultat calcule a une variable de type "
                f"'{target_type}' (limitation REX-SL actuelle : uniquement "
                "number/float/str peuvent etre obtenus par un calcul)"
            )
        self.types[name] = target_type
        if explicit:
            self._explicit_types.add(name)

    def reassign(self, name, ref, vtype):
        """Reaffecte une variable DEJA declaree (`name`) avec `ref` (deja
        evalue par ExprCodegen, de type `vtype` = type de `name`).

        number/float/str : opcode d'identite `add <dest> <ref> 0/0.0/"";`
        (add sur un <dest> deja declare reaffecte sans redeclarer).
        bool : reaffectation directe REX-SL `<nom> <ref>;` — depuis
        REX-SL 0.0.23 la reaffectation directe accepte aussi bien un
        litteral qu'une variable bool (la limite litteral-only est levee).
        none : reaffectation directe `<nom> none;` (RAZ du pointeur a NULL)."""
        if name not in self.types:
            raise RexResolveError(f"variable non declaree : {name}")
        if vtype == "number":
            self.emit(f"add {name} {ref} 0;")
        elif vtype == "float":
            self.emit(f"add {name} {ref} 0.0;")
        elif vtype == "str":
            self.emit(f'add {name} {ref} "";')
        elif vtype == "bool":
            self.emit(f"{name} {ref};")
        elif vtype == "none":
            self.emit(f"{name} none;")
        else:
            raise RexResolveError(f"reaffectation non supportee pour le type '{vtype}'")

    def is_explicit_type(self, name):
        """Retourne True si le type de `name` a ete annote explicitement."""
        return name in self._explicit_types

    def retype_as_collection(self, name, new_kind):
        """Retape une variable existante `name` vers le type collection
        `new_kind` (list/set/tuple/dict).  Autorise uniquement si le type
        actuel n'etait PAS explicite (infere par le compilateur).

        Depuis REX-SL 0.0.23, le retypage est delegue a l'opcode `retype`
        qui gere en interne la liberation de l'ancienne valeur et l'allocation
        du nouveau type, sans collision de nom (generation interne incrementee).
        On emet donc `retype <name> <new_rexsl_type>;` puis on met a jour
        self.types pour que les emissions suivantes (append/set) utilisent
        le bon type REX."""
        if name not in self.types:
            raise RexResolveError(f"variable non declaree : {name}")
        if name in self._explicit_types:
            old = self.types[name]
            raise RexResolveError(
                f"changement de type impossible : '{name}' a ete declare "
                f"explicitement comme '{old}' et ne peut pas etre retape en '{new_kind}'"
            )
        # list/set/tuple sont tous representes comme 'list' cote REX-SL.
        rexsl_kind = "dict" if new_kind == "dict" else "list"
        self.emit(f"retype {name} {rexsl_kind};")
        # Mise a jour du type tracker : declare_literal sera appele juste apres
        # par REX_CollectionLiteral.compile pour emettre les append/set.
        # On efface d'abord l'ancienne entree pour que declare_literal ne
        # leve pas "variable deja declaree" — mais on ne re-emet PAS de `var`
        # (c'est retype qui l'a fait). On re-enregistre directement le type.
        del self.types[name]

    def assign_dynamic(self, name, ref, vtype):
        """Affecte `ref` (deja evalue, de type `vtype`) a la variable `name`,
        en autorisant un changement de type A LA PYTHON si `name` n'a pas ete
        annote explicitement par l'utilisateur (0.0.12) : premiere affectation
        -> declaration inferee ; meme type -> reaffectation classique ; number
        affecte dans un float existant -> promotion habituelle (pas de
        retypage) ; sinon, si le type courant est infere, la variable est
        retapee via l'opcode REX-SL `retype` (0.0.23) puis reassignee ;
        si le type courant est explicite, erreur."""
        current = self.type_of_or_none(name)
        # --- affectation vers None (type natif REX-SL 0.0.23) ---
        if vtype == "none":
            if current is None:
                # Premiere declaration : `var none x;`
                self.declare_literal(name, "none")
                return
            if current == "none":
                # RAZ du pointeur : `x none;`
                self.reassign(name, ref, "none")
                return
            if self.is_explicit_type(name):
                raise RexResolveError(
                    f"reaffectation de '{name}' (type explicite '{current}') vers 'None' "
                    f"impossible : seule une variable de type 'none' peut recevoir None"
                )
            # Retypage vers none
            self.emit(f"retype {name} none;")
            self.types[name] = "none"
            self.emit(f"{name} none;")
            return
        if current is None:
            self.assign_computed(name, ref, vtype, vtype)
            return
        if current == vtype:
            self.reassign(name, ref, vtype)
            return
        if vtype == "number" and current == "float":
            self.reassign(name, ref, "float")
            return
        if self.is_explicit_type(name):
            raise RexResolveError(
                f"reaffectation de '{name}' (type explicite '{current}') avec une "
                f"valeur de type '{vtype}' incompatible"
            )
        # Retypage scalaire : delegue a l'opcode `retype` de REX-SL 0.0.23.
        self.emit(f"retype {name} {vtype};")
        self.types[name] = vtype
        self.reassign(name, ref, vtype)

    def is_none_type(self, name):
        """Retourne True si la variable `name` est de type REX-SL natif 'none'."""
        return self.types.get(name) == "none"

    def type_of(self, name):
        if name not in self.types:
            raise RexResolveError(f"variable non declaree utilisee dans une expression : {name}")
        return self.types[name]

    def type_of_or_none(self, name):
        """Comme type_of(), mais retourne None au lieu de lever une erreur
        si `name` n'est pas (encore) declaree - utilise par `for` pour
        savoir si la variable de boucle peut etre reutilisee (reassignee)
        plutot que redeclaree, entre deux `for` successifs sur le meme nom."""
        return self.types.get(name)

    # -- pile d'etiquettes de boucle (break/continue, 0.0.11) ----------------

    def push_loop_labels(self, continue_lbl, break_lbl):
        """Ouvre une nouvelle boucle : `continue_lbl` est l'etiquette vers
        laquelle sauter pour passer directement a l'iteration suivante
        (reevaluation de la condition pour 'while', increment puis
        reevaluation pour 'for'/'repeat'), `break_lbl` celle qui sort
        entierement de la boucle."""
        self._loop_stack.append((continue_lbl, break_lbl))

    def pop_loop_labels(self):
        self._loop_stack.pop()

    def current_loop_continue(self):
        if not self._loop_stack:
            raise RexResolveError("'continue' utilise en dehors de toute boucle (while/for/repeat)")
        return self._loop_stack[-1][0]

    def current_loop_break(self):
        if not self._loop_stack:
            raise RexResolveError("'break' utilise en dehors de toute boucle (while/for/repeat)")
        return self._loop_stack[-1][1]

    def new_temp_name(self):
        """Retourne un nouveau nom de temporaire, jamais declare via `var`
        (auto-declare par le premier opcode de calcul qui l'utilise comme
        <dest>). Prefixe `__rx_t`, reserve (voir REX_VarStatement)."""
        self._temp_counter += 1
        return f"__rx_t{self._temp_counter}"

    def new_loop_id(self):
        """Retourne un identifiant unique pour nommer les etiquettes/
        variables internes d'une boucle `repeat ... times` (jamais expose
        a l'utilisateur)."""
        self._loop_counter += 1
        return self._loop_counter

    # -- gestion des fonctions (`func` / `return` / appels) -----------------

    def enter_func_scope(self, name, param_types, param_names, defaults,
                          explicit_return_type=None):
        """Ouvre le scope d'une fonction `func <name>(...)`: sauvegarde la
        table des types de l'appelant (restauree telle quelle a la
        fermeture, cf. exit_func_scope) et interdit toute imbrication (les
        fonctions C reelles de REX-SL ne peuvent pas etre imbriquees).

        Enregistre AUSSI immediatement une entree (provisoire) dans
        self.functions, AVANT de compiler le corps : c'est ce qui permet a
        un appel RECURSIF (direct) situe DANS le corps de trouver la
        fonction via ExprCodegen._call plutot que d'echouer avec 'fonction
        inconnue' (REX-SL, lui, gere deja nativement la recursion via de
        vraies fonctions C avec prototypes en avant - seul REX.py devait
        etre mis a jour pour ne pas bloquer la resolution du NOM en amont).
        Si `explicit_return_type` est fourni (syntaxe 'func f(...) -> type:'),
        le type de retour est connu DES l'entree dans le scope : un appel
        recursif utilise DANS une expression (ex: 'return n * f(n-1)')
        fonctionne alors des le premier passage. Sans annotation explicite,
        le type de retour reste None tant qu'aucun 'return' n'a ete
        rencontre - un appel recursif AVANT le premier 'return' textuel de
        la fonction est alors traite comme un appel sans valeur utilisable
        dans une expression (meme limitation documentee cote REX-SL)."""
        if self._current_func is not None:
            raise RexResolveError(
                f"declaration de fonction imbriquee interdite : 'func {name}' "
                f"a l'interieur de 'func {self._current_func['name']}'"
            )
        if name in self.functions:
            raise RexResolveError(f"fonction deja declaree : {name}")
        self._scope_stack.append(
            (dict(self.types), set(self._explicit_types))
        )
        # Les fonctions C generees par REX-SL ont leurs propres variables
        # locales, completement isolees du scope global : on vide self.types
        # pour que declare_param() puisse enregistrer des parametres portant
        # le meme nom que des variables globales, et que type_of() dans le
        # corps ne resolve pas par erreur une variable globale homonyme
        # (comportement coherent avec Python : un parametre masque un global
        # de meme nom dans le corps de la fonction).
        self.types = {}
        self._explicit_types = set()
        self._current_func = {
            "name": name, "params": param_types, "param_names": param_names,
            "defaults": defaults, "return_type": explicit_return_type,
            "elem_type": None, "dict_value_type": None,
        }
        # forward/auto-reference : rend le nom resoluble des maintenant (recursion).
        # Forme du tuple (consommee par ExprCodegen._call / REX_CallStatement) :
        #   (param_types, param_names, defaults, return_type, elem_type, dict_value_type)
        self.functions[name] = (
            param_types, param_names, defaults, explicit_return_type, None, None
        )
        # Stocker le mapping sentinelle -> param reel pour ce nom de fonction,
        # afin que les sites d'appel puissent injecter les bons args.
        # none_sentinel_map[func_name] = liste ordonnee de (sentinel_name, real_param_name)
        # (dans l'ordre d'apparition dans la signature).
        if not hasattr(self, "none_sentinel_map"):
            self.none_sentinel_map = {}
        sentinels = []
        for i, pname in enumerate(param_names):
            if pname.startswith("__has_") and i + 1 < len(param_names):
                real_pname = param_names[i + 1]
                if not real_pname.startswith("__has_"):
                    sentinels.append((pname, real_pname))
        if sentinels:
            self.none_sentinel_map[name] = sentinels

    def declare_param(self, name, vtype):
        """Declare un parametre de fonction comme variable locale typee
        (aucun opcode `var` emis : REX-SL declare deja ses parametres via
        `func <name> <type1> <arg1> ...;`)."""
        if name.startswith("__rx_"):
            raise RexResolveError(f"nom de parametre reserve au compilateur : {name}")
        if name in self.types:
            raise RexResolveError(
                f"parametre '{name}' entre en collision avec une variable existante"
            )
        self.types[name] = vtype

    def note_return(self, vtype, elem_type=None, dict_value_type=None):
        """Enregistre le type d'un `return <expr>;` rencontre dans le corps
        de la fonction actuellement ouverte (erreur si hors de tout 'func',
        ou si incoherent avec un `return` precedent - ou avec l'annotation
        explicite '-> type' - de la meme fonction). `elem_type`/
        `dict_value_type` : si `vtype` est 'list'/'dict', type d'element/de
        valeur suivi pour la variable retournee (permet a l'appelant de
        continuer a indexer `f(...)[i]` sans perdre le suivi de type -
        seulement rempli quand `return` renvoie directement une variable
        DEJA suivie, cf. REX_ReturnStatement.compile)."""
        if self._current_func is None:
            raise RexResolveError(
                "'return' ne peut etre utilise qu'a l'interieur d'une fonction ('func')"
            )
        expected = self._current_func["return_type"]
        if expected is None:
            self._current_func["return_type"] = vtype
        elif expected != vtype:
            # Autoriser le melange none/autre type uniquement si le type annote est 'none'
            # (fonction void qui fait parfois `return none;` pour sortir tot)
            if not (expected == "none" and vtype == "none"):
                raise RexResolveError(
                    f"types de retour incoherents dans '{self._current_func['name']}' : "
                    f"'{expected}' puis '{vtype}'"
                )
        if vtype == "list" and elem_type is not None:
            self._current_func["elem_type"] = elem_type
        if vtype == "dict" and dict_value_type is not None:
            self._current_func["dict_value_type"] = dict_value_type

    def exit_func_scope(self):
        """Ferme le scope de fonction ouvert par enter_func_scope :
        finalise sa signature (types de parametres + type de retour deduit
        du/des `return` + type d'element/valeur pour une collection) pour
        les appels futurs, puis restaure integralement l'espace de noms de
        l'appelant."""
        info = self._current_func
        self.functions[info["name"]] = (
            info["params"], info["param_names"], info["defaults"], info["return_type"],
            info["elem_type"], info["dict_value_type"]
        )
        saved_types, saved_explicit = self._scope_stack.pop()
        self.types = saved_types
        self._explicit_types = saved_explicit
        self._current_func = None

    # -- gestion des modules avec espace de noms (0.0.15) --------------------

    def register_module(self, alias, func_map):
        """Enregistre un module importe `alias` : `func_map` est un dict
        {nom_rex: nom_mangle} des fonctions exportees par le module. Appele
        par preprocess_imports_with_alias apres avoir transforme les noms
        de fonctions dans le code inline."""
        if alias in self.modules:
            raise RexResolveError(f"module '{alias}' deja importe")
        self.modules[alias] = {"funcs": func_map}

    def resolve_module_func(self, alias, func_name):
        """Retourne le nom REX-SL mangle pour `alias.func_name`, ou leve
        une erreur si l'alias ou la fonction n'existent pas."""
        if alias not in self.modules:
            raise RexResolveError(
                f"module '{alias}' inconnu (importez-le avec "
                f"import \"fichier.rex\" as {alias};)"
            )
        funcs = self.modules[alias]["funcs"]
        if func_name not in funcs:
            known = ", ".join(sorted(funcs)) or "(aucune)"
            raise RexResolveError(
                f"fonction '{func_name}' inconnue dans le module '{alias}' "
                f"(fonctions disponibles : {known})"
            )
        return funcs[func_name]

    # -- gestion des func as object / funcref (0.0.15) -----------------------

    def register_funcref(self, var_name, mangled_name, func_info, c_decl_line):
        """Declare une variable funcref `var_name` pointant vers `mangled_name`.
        `func_info` = tuple (param_types, param_names, defaults, return_type,
        elem_type, dict_value_type) issu de self.functions.
        `c_decl_line` = code C a emettre via scrc pour declarer le pointeur."""
        if var_name in self.types:
            raise RexResolveError(f"variable deja declaree : {var_name}")
        self.types[var_name] = "funcref"
        self.funcrefs[var_name] = (mangled_name,) + func_info
        escaped = c_decl_line.replace("\\", "\\\\").replace('"', '\\"')
        self.emit(f'scrc "{escaped}";')

    def funcref_of(self, var_name):
        """Retourne le tuple (mangled_name, param_types, param_names, defaults,
        return_type, elem_type, dict_value_type) pour une variable funcref,
        ou leve une erreur."""
        if var_name not in self.funcrefs:
            raise RexResolveError(f"'{var_name}' n'est pas une variable de type 'func'")
        return self.funcrefs[var_name]

    def reassign_funcref(self, var_name, new_mangled, new_func_info, c_assign_line):
        """Reassigne une variable funcref existante vers une nouvelle cible.
        Met a jour funcrefs mais garde le type 'funcref' inchange."""
        if var_name not in self.funcrefs:
            raise RexResolveError(f"'{var_name}' n'est pas une variable de type 'func'")
        self.funcrefs[var_name] = (new_mangled,) + new_func_info
        escaped = c_assign_line.replace("\\", "\\\\").replace('"', '\\"')
        self.emit(f'scrc "{escaped}";')

    def render(self):
        header = f"# REX-SL> {REXSL_VERSION}"
        body = "\n".join(self.lines)
        return f"{header}\n{body}\n" if body else f"{header}\n"



# =============================================================================
# REX_NoneSupport : simulation de None a la Python
# =============================================================================

class REX_NoneSupport:
    """0.1.3 : `None` a la Python (`None`/`none`/`null`, formes strictement
    equivalentes). Delegue desormais au type natif REX-SL 0.0.23 `none`
    (void* = NULL) au lieu de la simulation par flag bool de la 0.1.0/0.1.2.

    - `var x = None`          -> `var none x;`
    - `var none x`            -> `var none x;`
    - `x = None`              -> `x none;` si x est de type 'none',
                                 sinon retypage via assign_dynamic.
    - `if x is None`          -> `isnone <tmp> x; cdn equal <tmp> true; ...`
    - `show(x)` (type 'none') -> `showln none;` / `show none;` natif REX-SL.
    - `return None`           -> `return none;` dans une func -> none.
    """

    LITERALS = ("None", "none", "null")

    @staticmethod
    def is_none_tokens(tokens):
        return (
            len(tokens) == 1
            and isinstance(tokens[0], Token)
            and tokens[0].type == "KEYWORD"
            and tokens[0].value in REX_NoneSupport.LITERALS
        )

    @staticmethod
    def declare(name, explicit_type, emitter):
        """Declare une variable de type 'none' (var none x;).
        Si explicit_type est fourni et different de 'none', erreur : en REX-SL
        natif, une variable initialisee a None EST de type 'none', aucun autre
        type n'est compatible (contrairement a l'ancienne simulation)."""
        if name in emitter.types:
            raise RexResolveError(f"variable deja declaree : {name}")
        if name.startswith("__rx_"):
            raise RexResolveError(f"nom de variable reserve au compilateur : {name}")
        if explicit_type is not None and explicit_type != "none":
            raise RexResolveError(
                f"impossible de declarer '{name}' de type explicite '{explicit_type}' "
                f"avec une valeur 'None' : en REX, une variable initialisee a None "
                f"doit etre de type 'none' (var none {name} = None, ou simplement "
                f"var {name} = None)"
            )
        emitter.declare_literal(name, "none", explicit=explicit_type is not None)

    @staticmethod
    def assign(name, emitter):
        """Reaffecte une variable existante a None (natif REX-SL 0.0.23).
        Delegue a assign_dynamic qui gere le cas 'none'."""
        if name not in emitter.types:
            raise RexResolveError(f"variable non declaree : {name}")
        emitter.assign_dynamic(name, "none", "none")



# =============================================================================
# PARSEUR D'EXPRESSIONS : ExprParser
# =============================================================================

def REX_ExprParser_expand_double_colon(items):
    """Eclate tout token OP '::' d'une liste de tokens plate en deux tokens
    PUNCT ':' consecutifs (meme ligne/colonne) - necessaire car le lexer
    fusionne greedily deux ':' adjacents en un seul token '::' (voir
    REX_Lexer.MULTI_OPS), ce qui casserait sinon la detection de slice avec
    pas `x[::c]`/`x[a::c]` dans ExprParser._parse_bracket (0.0.14)."""
    expanded = []
    for t in items:
        if isinstance(t, Token) and t.type == "OP" and t.value == "::":
            expanded.append(Token("PUNCT", ":", t.line, t.col))
            expanded.append(Token("PUNCT", ":", t.line, t.col + 1))
        else:
            expanded.append(t)
    return expanded


class ExprParser:
    """Parseur recursif descendant d'expressions arithmetiques REX.

    Prend en entree une liste plate de tokens/sous-listes correspondant a
    UNE expression (pas de NEWLINE dedans), telle que produite par
    REX_Lexer : un `(...)` y apparait deja comme une sous-liste Python
    imbriquee (voir la docstring de REX_Lexer), ce qui permet de gerer les
    parentheses simplement en recursant dessus.

    Priorite geree via PRECEDENCE, de la plus FAIBLE a la plus FORTE :
    modulable, il suffit d'ajouter une entree {operateur: opcode REX-SL}
    pour supporter un nouvel operateur binaire.
    """

    PRECEDENCE = [
        {"+": "add", "-": "sub"},
        {"*": "mul", "/": "div", "%": "mod"},
    ]

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    @staticmethod
    def _is_op(tok, value=None):
        return (
            isinstance(tok, Token)
            and tok.type == "OP"
            and (value is None or tok.value == value)
        )

    def parse(self):
        if not self.tokens:
            raise RexResolveError("expression vide")
        node = self._parse_level(0)
        if self.pos != len(self.tokens):
            raise RexResolveError(f"jeton inattendu dans l'expression : {self.tokens[self.pos]!r}")
        return node

    def _parse_level(self, level):
        if level >= len(self.PRECEDENCE):
            return self._parse_unary()
        ops = self.PRECEDENCE[level]
        node = self._parse_level(level + 1)
        while True:
            tok = self._peek()
            if not self._is_op(tok) or tok.value not in ops:
                break
            self._advance()
            right = self._parse_level(level + 1)
            node = ("binop", ops[tok.value], node, right)
        return node

    def _parse_unary(self):
        tok = self._peek()
        if self._is_op(tok, "-"):
            self._advance()
            return ("neg", self._parse_unary())
        if self._is_op(tok, "+"):
            self._advance()
            return self._parse_unary()
        return self._parse_pow()

    def _parse_pow(self):
        """`**` (exposant, 0.0.14) : priorite la plus forte de toutes (au
        dessus de */%), associativite a DROITE (2**3**2 == 2**(3**2)) et
        l'exposant peut lui-meme porter un signe unaire (2**-1) - d'ou la
        recursion sur _parse_unary a droite plutot que sur _parse_pow."""
        node = self._parse_primary()
        tok = self._peek()
        if self._is_op(tok, "**"):
            self._advance()
            right = self._parse_unary()
            node = ("binop", "pow", node, right)
        return node

    def _parse_primary(self):
        node = self._parse_primary_base()
        # postfix `[...]` a la Python juste apres n'importe quel primaire
        # (ident, appel, litteral, parenthesage, ou meme un autre slice/index
        # pour permettre le chainage `s[1:][0:2]`, `l[0][1]`, ...) : deux
        # formes reconnues (voir _parse_bracket) - `[debut:fin]` (slice,
        # 0.0.12) et `[cle]` sans ':' (indexation generique `l[i]`/`d["k"]`,
        # via l'opcode etendu REX-SL `get` - cf ExprCodegen._index).
        while True:
            tok = self._peek()
            if isinstance(tok, Group) and tok.kind == "[]":
                self._advance()
                node = self._parse_bracket(node, tok)
            else:
                break
        return node

    def _parse_primary_base(self):
        tok = self._peek()
        if tok is None:
            raise RexResolveError("expression incomplete (operande attendu)")

        # regroupement `(...)` : deja represente comme une sous-liste par
        # le lexer -> on recurse simplement dessus.
        if isinstance(tok, list):
            self._advance()
            return ExprParser(tok).parse()

        if isinstance(tok, Token):
            if tok.type == "NUMBER":
                self._advance()
                return ("lit", tok.value)
            if tok.type == "STRING":
                self._advance()
                return ("lit", tok.value)
            if tok.type == "FSTRING":
                self._advance()
                return ("fstring", tok.value)
            if tok.type == "KEYWORD" and tok.value in ("true", "false"):
                self._advance()
                return ("lit", tok.value == "true")
            if tok.type == "KEYWORD" and tok.value in REX_NoneSupport.LITERALS:
                self._advance()
                return ("none",)
            if tok.type == "IDENT":
                self._advance()
                # `alias.fn(...)` : acces qualifie de module (0.0.15).
                # Le '.' est un token PUNCT produit par le lexer, suivi
                # d'un IDENT (nom de fonction) puis d'une sous-liste "nue"
                # (parentheses d'appel). Si l'une de ces conditions manque,
                # on retombe sur l'acces simple `ident` ou `ident(...)`.
                nxt = self._peek()
                if (
                    isinstance(nxt, Token)
                    and nxt.type == "PUNCT" and nxt.value == "."
                ):
                    self._advance()  # consomme le '.'
                    fn_tok = self._peek()
                    if fn_tok is None or not (
                        isinstance(fn_tok, Token) and fn_tok.type == "IDENT"
                    ):
                        raise RexResolveError(
                            f"acces de module '{tok.value}.' : "
                            "nom de fonction attendu apres '.'"
                        )
                    self._advance()  # consomme le nom de fonction
                    arg_list = self._peek()
                    if not isinstance(arg_list, list):
                        raise RexResolveError(
                            f"acces de module '{tok.value}.{fn_tok.value}' : "
                            "parentheses d'appel attendues (seuls les appels "
                            "de fonctions sont supportes via l'acces qualifie, "
                            "pas la lecture de variable de module)"
                        )
                    self._advance()  # consomme la liste d'args
                    args = self._parse_call_args(arg_list)
                    # methode de liste `liste.append(val)` dans une expression
                    # -> sucre syntaxique pour append(liste, val) (0.0.23+).
                    if fn_tok.value == "append":
                        list_node = ("ident", tok.value)
                        full_args = [("pos", list_node)] + args
                        return ("call", "append", full_args)
                    # Nœud special ("modcall", alias, func_name, args) ;
                    # resolu par ExprCodegen.generate -> _call_module.
                    return ("modcall", tok.value, fn_tok.value, args)
                # `nom(...)` : appel de fonction ordinaire.
                if isinstance(nxt, list):
                    self._advance()
                    args = self._parse_call_args(nxt)
                    return ("call", tok.value, args)
                return ("ident", tok.value)

        if isinstance(tok, Group) and tok.kind == "[]":
            # comprehension de liste utilisee comme valeur au sein d'une
            # expression generale (pas seulement comme valeur de `var` ou
            # de reaffectation, cf. REX_ListComprehension) : reconnue ici
            # via le meme detecteur, puis compilee "a la volee" dans une
            # variable temporaire par ExprCodegen.generate (noeud "listcomp"),
            # cf. REX_ListComprehension.compile_to_ref.
            comp = REX_ListComprehension.detect([tok])
            if comp is not None:
                self._advance()
                items, for_idx = comp
                return ("listcomp", items, for_idx)
            raise RexResolveError(
                "litteral de liste '[...]' non supporte a cet endroit d'une "
                "expression (seule une comprehension '[expr for x in iterable "
                "[if cond]]' est acceptee ici) ; un litteral de liste doit "
                "etre affecte via 'var l = [...]' ou 'l = [...]'"
            )

        raise RexResolveError(f"element d'expression inattendu : {tok!r}")

    @staticmethod
    def _parse_bracket(base_node, group):
        """Compile un groupe `[...]` postfixe (deja consomme) en noeud
        d'indexation generique `("index", base, key_node)` (0.0.13, `l[i]`/
        `d["cle"]`, via l'opcode etendu REX-SL `get` - cf ExprCodegen._index)
        si aucun ':' n'est present, sinon en noeud de slice a la syntaxe
        Python `x[debut:fin]` (0.0.12, uniquement sur 'str') :
            x[a:b]  -> bornes explicites
            x[:b]   -> debut omis (0 par defaut, cf ExprCodegen._slice)
            x[a:]   -> fin omise (len(x) par defaut)
            x[:]    -> copie complete
        ou, avec un second ':', en noeud de slice AVEC PAS (0.0.14) :
            x[a:b:c]  -> ("slicestep", base, start, end, step)
            x[::c]    -> debuts/fin omis, dependent du signe de `c` a la
                         Python (cf ExprCodegen._slice_step)
        Le pas `x[a:b:]` (troisieme partie vide) est traite comme un slice
        normal (pas implicite de 1, meme opcode REX-SL 'slice' que sans
        second ':').

        Piege du lexer : deux ':' adjacents sont lexes comme un UNIQUE token
        OP '::' (reserve par ailleurs a une eventuelle syntaxe de namespace,
        cf REX_Lexer.MULTI_OPS), donc `x[::c]`/`x[a::c]` ne contiennent PAS
        deux tokens PUNCT ':' distincts en entree - ils sont eclates ici en
        deux avant toute detection."""
        items = REX_ExprParser_expand_double_colon(list(group.items))
        colon_positions = [
            i for i, t in enumerate(items)
            if isinstance(t, Token) and t.type == "PUNCT" and t.value == ":"
        ]
        if not colon_positions:
            if not items:
                raise RexResolveError("'[...]' vide non supporte (index/cle attendu)")
            key_node = ExprParser(items).parse()
            return ("index", base_node, key_node)
        if len(colon_positions) > 2:
            raise RexResolveError(
                "'[debut:fin:pas]' invalide : trop de ':' dans l'indexation"
            )
        if len(colon_positions) == 2:
            c1, c2 = colon_positions
            start_tokens = items[:c1]
            end_tokens = items[c1 + 1:c2]
            step_tokens = items[c2 + 1:]
            start_node = ExprParser(start_tokens).parse() if start_tokens else None
            end_node = ExprParser(end_tokens).parse() if end_tokens else None
            if not step_tokens:
                # `x[a:b:]` : pas omis -> equivalent a un slice normal.
                return ("slice", base_node, start_node, end_node)
            step_node = ExprParser(step_tokens).parse()
            return ("slicestep", base_node, start_node, end_node, step_node)
        colon_idx = colon_positions[0]
        start_tokens = items[:colon_idx]
        end_tokens = items[colon_idx + 1:]
        start_node = ExprParser(start_tokens).parse() if start_tokens else None
        end_node = ExprParser(end_tokens).parse() if end_tokens else None
        return ("slice", base_node, start_node, end_node)

    @staticmethod
    def _parse_call_args(arg_tokens):
        """Decoupe le contenu (deja "nu", sans les parentheses) d'un appel
        `nom(a, b, c)` sur les virgules de premier niveau, puis parse
        chaque segment comme une expression complete.

        Reconnait aussi les arguments NOMMES a la Python (`nom(a, y=5)`,
        cf. REX-SL 'exec f a y=5;') : un segment de la forme `<ident> = <expr>`
        (le '=' devant apparaitre en 2e position du segment) produit
        `("kwarg", <ident>, <noeud_expr>)` plutot qu'un noeud brut ; un
        segment ordinaire produit `("pos", <noeud_expr>)`. Consomme par
        ExprCodegen._call (fonctions REX 'func') - ExprCodegen._call_builtin
        (fonctions natives) refuse les arguments nommes."""
        if not arg_tokens:
            return []
        groups = []
        current = []
        for t in arg_tokens:
            if isinstance(t, Token) and t.type == "PUNCT" and t.value == ",":
                groups.append(current)
                current = []
            else:
                current.append(t)
        groups.append(current)
        args = []
        for g in groups:
            if not g:
                raise RexResolveError("argument vide dans un appel de fonction")
            if (
                len(g) >= 3
                and isinstance(g[0], Token) and g[0].type == "IDENT"
                and isinstance(g[1], Token) and g[1].type == "OP" and g[1].value == "="
            ):
                pname = g[0].value
                args.append(("kwarg", pname, ExprParser(g[2:]).parse()))
            else:
                args.append(("pos", ExprParser(g).parse()))
        return args




# =============================================================================
# GENERATEUR DE CODE D'EXPRESSIONS : ExprCodegen
# =============================================================================

class ExprCodegen:
    """Genere le code REX-SL (add/sub/mul/div/mod + variables temporaires)
    correspondant a l'arbre produit par ExprParser, en respectant la
    priorite/le regroupement deja encode dans cet arbre.

    generate(node) retourne un couple (operande, type) ou `operande` est
    soit un litteral REX-SL pret a l'emploi (ex: "5", '"abc"'), soit le
    nom d'une variable/temporaire deja declaree - directement utilisable
    comme argument d'un opcode REX-SL (`add <dest> <a> <b>;` accepte aussi
    bien un nom de variable qu'un litteral, cf. exemples REX-SL: `add n n 1;`).
    """

    def __init__(self, emitter):
        self.emitter = emitter

    def generate(self, node):
        """Evalue `node` et retourne (operande, type). `operande` est soit
        un litteral REX-SL pret a l'emploi, soit le nom d'une variable
        (utilisateur ou temporaire) deja evaluee - dans tous les cas
        directement utilisable comme argument d'un opcode REX-SL."""
        kind = node[0]
        if kind == "lit":
            return self._literal(node[1])
        if kind == "ident":
            name = node[1]
            # type_of() reste indexe par le nom REX logique ; l'operande
            # emis, lui, doit etre le nom REX-SL reel (potentiellement
            # aliase par un retypage anterieur, cf. Emitter.retype_as_collection).
            return name, self.emitter.type_of(name)
        if kind == "neg":
            return self._negate(node[1])
        if kind == "binop":
            return self._binop(node[1], node[2], node[3])
        if kind == "call":
            # Verifier d'abord si c'est un appel via funcref (0.0.15)
            if node[1] in self.emitter.funcrefs:
                return self._call_funcref(node[1], node[2])
            return self._call(node[1], node[2])
        if kind == "modcall":
            return self._call_module(node[1], node[2], node[3])
        if kind == "fstring":
            return self._fstring(node[1])
        if kind == "listcomp":
            return REX_ListComprehension.compile_to_ref(node[1], node[2], self.emitter)
        if kind == "slice":
            return self._slice(node[1], node[2], node[3])
        if kind == "slicestep":
            return self._slice_step(node[1], node[2], node[3], node[4])
        if kind == "index":
            return self._index(node[1], node[2])
        if kind == "none":
            return NONE_REF, "none"
        raise RexResolveError(f"noeud d'expression inconnu : {node!r}")

    def _literal(self, value):
        if isinstance(value, bool):
            return ("true" if value else "false"), "bool"
        if isinstance(value, int):
            return str(value), "number"
        if isinstance(value, float):
            return repr(value), "float"
        if isinstance(value, str):
            return self._quote(value), "str"
        raise RexResolveError(f"litteral non supporte : {value!r}")
    
    def to_str_for_value_node(self, node):
        ref, vtype = self.generate(node)
        # Type 'none' natif REX-SL 0.0.23 : la valeur est toujours None -> str "None"
        if vtype == "none":
            return self._quote("None")
        return self.to_str(ref, vtype)

    @staticmethod
    def _quote(text):
        escaped = (
            text.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\t", "\\t")
        )
        return f'"{escaped}"'

    def _negate(self, operand_node):
        ref, vtype = self.generate(operand_node)
        if vtype not in ("number", "float"):
            raise RexResolveError(f"moins unaire impossible sur un type '{vtype}'")
        zero = DEFAULT_VALUES[vtype]
        temp = self.emitter.new_temp_name()
        self.emitter.emit(f"sub {temp} {zero} {ref};")
        self.emitter.types[temp] = vtype
        return temp, vtype

    def _binop(self, opcode, left_node, right_node):
        left_ref, left_type = self.generate(left_node)
        right_ref, right_type = self.generate(right_node)
        result_type = self._result_type(opcode, left_type, right_type)
        temp = self.emitter.new_temp_name()
        self.emitter.emit(f"{opcode} {temp} {left_ref} {right_ref};")
        self.emitter.types[temp] = result_type
        return temp, result_type

    @staticmethod
    def _result_type(opcode, left_type, right_type):
        """Deduit le type du resultat en suivant la table de la doc
        REX-SL (section "Calcul") : number+number -> number, un float
        implique une promotion en float, str n'est valide qu'avec add
        (concatenation), sub (suppression d'occurrences) et mul
        (repetition str*number)."""
        if left_type == right_type == "number":
            return "number"
        if left_type in ("number", "float") and right_type in ("number", "float"):
            return "float"
        if left_type == "str" or right_type == "str":
            if opcode == "add" and left_type == right_type == "str":
                return "str"
            if opcode == "sub" and left_type == right_type == "str":
                return "str"
            if opcode == "mul" and {left_type, right_type} == {"str", "number"}:
                return "str"
            raise RexResolveError(
                f"operation '{opcode}' invalide entre types '{left_type}' et '{right_type}'"
            )
        raise RexResolveError(
            f"operation '{opcode}' invalide entre types '{left_type}' et '{right_type}'"
        )

    # -- fonctions natives / utilitaires a la Python (0.0.12) ---------------
    # nom -> nombre d'arguments attendu. Prioritaires sur les fonctions REX
    # utilisateur (comme les builtins de Python) - toutes deleguent vers un
    # opcode REX-SL deja existant, aucune modification de REX-SL.py.
    # -- appels qualifies de module (0.0.15) ----------------------------------

    def _call_module(self, alias, func_name, arg_specs):
        """Compile `alias.fn(args)` : resout le nom mangle via
        Emitter.resolve_module_func, puis compile comme un appel ordinaire
        vers cette fonction (qui est deja dans self.emitter.functions sous
        son nom mangle, ayant ete compilee normalement par REX_FuncStatement
        lors de l'inlining du module)."""
        mangled = self.emitter.resolve_module_func(alias, func_name)
        # Verifier que la fonction est bien connue sous son nom mangle
        if mangled not in self.emitter.functions:
            raise RexResolveError(
                f"module '{alias}' : la fonction '{func_name}' (nom interne "
                f"'{mangled}') n'a pas encore ete compilee - verifiez que "
                "l'import precede l'appel dans le fichier source"
            )
        return self._call(mangled, arg_specs)

    # -- appels via pointeur de fonction / funcref (0.0.15) -------------------

    def _call_funcref(self, var_name, arg_specs):
        """Compile `f(args)` quand `f` est une variable de type 'funcref'
        (pointeur de fonction, voir Emitter.funcrefs). L'appel est injecte
        en C brut via `scrc` car REX-SL n'a pas de notion de pointeur de
        fonction : on appelle directement `SL_<var_name>(args)` en C.

        La signature (types des arguments, type de retour) est celle de la
        fonction pointee au moment de la DECLARATION (var func f = myfunc;)
        ou de la derniere REASSIGNATION (f = otherfunc;). Les arguments sont
        evalues normalement (generate -> ref C via SL_<nom>), puis l'appel
        C est construit et emis via scrc, et le resultat est copie dans un
        temporaire REX-SL frais."""
        info = self.emitter.funcref_of(var_name)
        mangled_name = info[0]
        param_types   = info[1]
        param_names   = info[2]
        defaults      = info[3]
        return_type   = info[4]
        elem_type     = info[5]
        dict_val_type = info[6]

        if return_type is None:
            c_args = self._build_c_call_args(arg_specs, param_names, defaults)
            ptr_c = f"SL_{var_name}"
            call_stmt = f"{ptr_c}({', '.join(c_args)});"
            escaped = call_stmt.replace("\\", "\\\\").replace('"', '\\"')
            self.emitter.emit(f'scrc "{escaped}";')
            return NONE_REF, "none"

        # Construire les arguments C (meme logique que _build_c_call_args)
        c_args = self._build_c_call_args(arg_specs, param_names, defaults)

        # Nom C du pointeur de fonction : SL_<var_name> (declare par scrc a
        # la creation de la variable funcref, cf. Emitter.register_funcref)
        ptr_c = f"SL_{var_name}"
        call_expr = f"{ptr_c}({', '.join(c_args)})"

        temp = self.emitter.new_temp_name()
        if return_type in ("list", "tuple", "set", "dict"):
            emit_type = "dict" if return_type == "dict" else "list"
            self.emitter.declare_literal(temp, emit_type)
            self.emitter.types[temp] = return_type
            temp_c = f"SL_{temp}"
            free_fn = "rexsl_list_free" if emit_type == "list" else "rexsl_dict_free"
            code = (
                f"if ({temp_c}) {{ {free_fn}({temp_c}); }} "
                f"{temp_c} = {call_expr};"
            )
        else:
            self.emitter.declare_literal(temp, return_type, DEFAULT_VALUES[return_type])
            temp_c = f"SL_{temp}"
            code = f"{temp_c} = {call_expr};"

        escaped = code.replace("\\", "\\\\").replace('"', '\\"')
        self.emitter.emit(f'scrc "{escaped}";')
        self.emitter.types[temp] = return_type
        self._propagate_collection_type(temp, return_type, elem_type, dict_val_type)
        return temp, return_type

    BUILTIN_ARITY = {
        # -- builtins historiques (0.0.12) --
        "len": 1, "type": 1, "str": 1, "int": 1, "float": 1,
        # -- none natif (alpha 0.1.3, REX-SL 0.0.23) --
        "isnone": 1,   # isnone(x) -> bool : vrai si x est None/NULL
        "upper": 1, "lower": 1, "trim": 1, "reverse": 1,
        "charat": 2, "find": 2, "slice": 3, "replace": 3,
        # -- nouveaux builtins Python (alpha 0.1.1) --
        # Conversions / introspection
        "abs": 1, "bool": 1, "chr": 1, "hex": 1, "oct": 1, "bin": 1,
        "ord": 1, "repr": 1, "ascii": 1, "hash": 1, "id": 1,
        # Collections
        "list": 1, "tuple": 1, "set": 1, "dict": 0,
        "frozenset": 1, "bytes": 1, "bytearray": 1, "memoryview": 1,
        "sorted": 1, "reversed": 1, "enumerate": 1,
        # Maths / logique
        "round": -1,   # 1 ou 2 args
        "pow": -1,     # 2 ou 3 args (surcharge du ** existant)
        "divmod": 2, "sum": 1,
        "min": -1, "max": -1,   # 1+ args
        "all": 1, "any": 1,
        # I/O / eval
        "print": -1,   # alias de show()
        "input": -1,   # 0 ou 1 arg
        "format": -1,  # 1 ou 2 args
        # Objet / reflexion
        "callable": 1, "hasattr": 2, "getattr": -1, "setattr": 3, "delattr": 2,
        "isinstance": 2, "issubclass": 2,
        "dir": -1, "vars": -1, "globals": 0, "locals": 0,
        "iter": 1, "next": -1,
        "object": 0,
        "range": -1,   # 1, 2 ou 3 args (cf. REX_ForStatement, ici utilisable en expression)
        "zip": -1,     # N args
        "map": 2, "filter": 2,
        "eval": 1, "exec": 1, "compile": 3,
        "open": -1,    # 1 ou 2 args (delogue aux opcodes read/write REX-SL)
        "super": 0,
        "property": -1, "classmethod": 1, "staticmethod": 1,
        "complex": -1, "slice": -1,  # surchargent les existants
        "enumerate": 1,
        "breakpoint": 0,
        "help": -1,
    }

    def _call_builtin(self, name, arg_specs):
        """Compile un appel de fonction native Python vers REX-SL.

        Toutes les fonctions builtins Python sont implementees ici, soit en
        delegant vers un opcode REX-SL existant, soit via `scrc` (injection C
        brute), soit via une emulation REX-SL (boucles lbl/cdn/go).

        Fonctions avec arite variable (BUILTIN_ARITY == -1) : la validation
        du nombre d'arguments est effectuee cas par cas ci-dessous.
        Fonctions avec arite fixe  : validation generique en entete.
        """
        expected = self.BUILTIN_ARITY[name]
        nargs = len(arg_specs)

        # Validation arite fixe (expected >= 0)
        if expected >= 0 and nargs != expected:
            raise RexResolveError(
                f"{name}(): {expected} argument(s) attendu(s), {nargs} fourni(s)"
            )
        if any(spec[0] == "kwarg" for spec in arg_specs):
            raise RexResolveError(
                f"{name}() : les arguments nommes ne sont pas supportes pour les "
                "fonctions natives (uniquement pour les fonctions 'func' definies par vous)"
            )
        arg_nodes = [spec[1] for spec in arg_specs]
        args = [self.generate(n) for n in arg_nodes]
        emitter = self.emitter

        # ------------------------------------------------------------------ #
        #  BUILTINS HISTORIQUES (0.0.12)                                      #
        # ------------------------------------------------------------------ #

        # -- isnone(x) : teste si x est None/NULL (REX-SL 0.0.23 natif) --
        if name == "isnone":
            ref, vtype = args[0]
            # Scalaires non-pointeurs : jamais None -> resultat statique False
            if vtype in ("number", "float", "bool"):
                temp = emitter.new_temp_name()
                emitter.declare_literal(temp, "bool", "false")
                return temp, "bool"
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, "bool", "false")
            emitter.emit(f"isnone {temp} {ref};")
            return temp, "bool"

        if name == "len":
            ref, vtype = args[0]
            if vtype not in ("str", "list", "tuple", "set", "dict"):
                raise RexResolveError(
                    f"len() : type '{vtype}' non supporte (attendu 'str' ou une collection "
                    "list/tuple/set/dict)"
                )
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, "number")
            emitter.emit(f"len {temp} {ref};")
            return temp, "number"

        if name == "type":
            ref, _vtype = args[0]
            temp = emitter.new_temp_name()
            emitter.emit(f"type {temp} {ref};")
            emitter.types[temp] = "str"
            return temp, "str"

        if name == "str":
            ref, vtype = args[0]
            return self.to_str(ref, vtype), "str"

        if name in ("int", "float"):
            ref, vtype = args[0]
            target = "number" if name == "int" else "float"
            return self._convert(ref, vtype, target), target

        if name in ("upper", "lower", "trim"):
            ref, vtype = args[0]
            if vtype != "str":
                raise RexResolveError(f"{name}() : l'argument doit etre une 'str'")
            temp = emitter.new_temp_name()
            emitter.emit(f"{name} {temp} {ref};")
            emitter.types[temp] = "str"
            return temp, "str"

        if name == "charat":
            (ref, vtype), (idx_ref, idx_type) = args
            if vtype != "str" or idx_type != "number":
                raise RexResolveError("charat() : attend (str, number)")
            temp = emitter.new_temp_name()
            emitter.emit(f"charat {temp} {ref} {idx_ref};")
            emitter.types[temp] = "str"
            return temp, "str"

        if name == "find":
            (ref, vtype), (sub_ref, sub_type) = args
            if vtype != "str" or sub_type != "str":
                raise RexResolveError("find() : les deux arguments doivent etre des 'str'")
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, "number")
            emitter.emit(f"find {temp} {ref} {sub_ref};")
            return temp, "number"

        if name == "slice":
            # slice(s, debut, fin)  — 3 args (forme historique)
            # slice(start, stop[, step]) — 2 ou 3 args Python : non supporte
            #   comme valeur seule (objet slice), mais accepte ici en 3-args
            #   comme alias de la forme str existante.
            if nargs == 3:
                (ref, vtype), (start_ref, start_type), (end_ref, end_type) = args
                if vtype != "str" or start_type != "number" or end_type != "number":
                    raise RexResolveError("slice() : attend (str, number, number)")
                temp = emitter.new_temp_name()
                emitter.emit(f"slice {temp} {ref} {start_ref} {end_ref};")
                emitter.types[temp] = "str"
                return temp, "str"
            raise RexResolveError(
                "slice() : en REX, slice() attend exactement 3 arguments (str, debut, fin) "
                "— les objets slice Python ne sont pas supportes comme valeurs independantes"
            )

        if name == "replace":
            (ref, vtype), (old_ref, old_type), (new_ref, new_type) = args
            if vtype != "str" or old_type != "str" or new_type != "str":
                raise RexResolveError("replace() : les 3 arguments doivent etre des 'str'")
            temp = emitter.new_temp_name()
            emitter.emit(f"replace {temp} {ref} {old_ref} {new_ref};")
            emitter.types[temp] = "str"
            return temp, "str"

        if name == "reverse":
            ref, vtype = args[0]
            if vtype != "str":
                raise RexResolveError("reverse() : l'argument doit etre une 'str'")
            temp = emitter.new_temp_name()
            emitter.emit(f"reverse {temp} {ref};")
            emitter.types[temp] = "str"
            return temp, "str"

        # ------------------------------------------------------------------ #
        #  NOUVEAUX BUILTINS PYTHON (alpha 0.1.1)                             #
        # ------------------------------------------------------------------ #

        # --- abs(x) : valeur absolue — number ou float ---
        if name == "abs":
            ref, vtype = args[0]
            if vtype not in ("number", "float"):
                raise RexResolveError(
                    f"abs() : type '{vtype}' non supporte (attendu number ou float)"
                )
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, vtype)
            c_src = f"SL_{ref}"
            c_dst = f"SL_{temp}"
            fn = "abs" if vtype == "number" else "fabs"
            code = f"{c_dst} = {fn}({c_src});"
            escaped = code.replace("\\", "\\\\").replace('"', '\\"')
            emitter.emit(f'scrc "{escaped}";')
            return temp, vtype

        # --- bool(x) : conversion en booleen ---
        if name == "bool":
            ref, vtype = args[0]
            temp = emitter.new_temp_name()
            loop_id = emitter.new_loop_id()
            true_lbl = f"__rx_bool{loop_id}_t"
            end_lbl  = f"__rx_bool{loop_id}_e"
            emitter.declare_literal(temp, "bool", "false")
            if vtype == "bool":
                emitter.emit(f"cdn equal {ref} true;")
            elif vtype in ("number", "float"):
                zero = "0" if vtype == "number" else "0.0"
                emitter.emit(f"cdn not_equal {ref} {zero};")
            elif vtype == "str":
                emitter.emit(f'cdn not_equal {ref} "";')
            else:
                raise RexResolveError(
                    f"bool() : type '{vtype}' non supporte "
                    "(attendu number/float/str/bool)"
                )
            emitter.emit(f"go {true_lbl};")
            emitter.emit("cdn on;")
            emitter.emit(f"go {end_lbl};")
            emitter.emit(f"lbl {true_lbl};")
            emitter.emit(f"{temp} true;")
            emitter.emit(f"lbl {end_lbl};")
            return temp, "bool"

        # --- chr(n) : entier -> caractere Unicode ---
        if name == "chr":
            ref, vtype = args[0]
            if vtype != "number":
                raise RexResolveError("chr() : l'argument doit etre un 'number' (entier)")
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, "str", '""')
            c_dst = f"SL_{temp}"
            c_src = f"SL_{ref}"
            code = (
                f"{{ char __rx_chrbuf[5]; "
                f"unsigned int __rx_cp = (unsigned int)({c_src}); "
                f"if (__rx_cp < 0x80) {{ __rx_chrbuf[0]=(char)__rx_cp; __rx_chrbuf[1]=0; }} "
                f"else if (__rx_cp < 0x800) {{ "
                f"  __rx_chrbuf[0]=(char)(0xC0|(__rx_cp>>6)); "
                f"  __rx_chrbuf[1]=(char)(0x80|(__rx_cp&0x3F)); "
                f"  __rx_chrbuf[2]=0; }} "
                f"else if (__rx_cp < 0x10000) {{ "
                f"  __rx_chrbuf[0]=(char)(0xE0|(__rx_cp>>12)); "
                f"  __rx_chrbuf[1]=(char)(0x80|((__rx_cp>>6)&0x3F)); "
                f"  __rx_chrbuf[2]=(char)(0x80|(__rx_cp&0x3F)); "
                f"  __rx_chrbuf[3]=0; }} "
                f"else {{ "
                f"  __rx_chrbuf[0]=(char)(0xF0|(__rx_cp>>18)); "
                f"  __rx_chrbuf[1]=(char)(0x80|((__rx_cp>>12)&0x3F)); "
                f"  __rx_chrbuf[2]=(char)(0x80|((__rx_cp>>6)&0x3F)); "
                f"  __rx_chrbuf[3]=(char)(0x80|(__rx_cp&0x3F)); "
                f"  __rx_chrbuf[4]=0; }} "
                f"free({c_dst}); {c_dst} = strdup(__rx_chrbuf); }}"
            )
            escaped = code.replace("\\", "\\\\").replace('"', '\\"')
            emitter.emit(f'scrc "{escaped}";')
            return temp, "str"

        # --- ord(s) : caractere -> point de code Unicode ---
        if name == "ord":
            ref, vtype = args[0]
            if vtype != "str":
                raise RexResolveError("ord() : l'argument doit etre une 'str'")
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, "number")
            c_dst = f"SL_{temp}"
            c_src = f"SL_{ref}"
            code = (
                f"{{ unsigned char __rx_oc = (unsigned char)({c_src})[0]; "
                f"if (__rx_oc < 0x80) {{ {c_dst} = __rx_oc; }} "
                f"else if ((__rx_oc & 0xE0) == 0xC0) {{ "
                f"  {c_dst} = ((__rx_oc & 0x1F) << 6) | ((unsigned char)({c_src})[1] & 0x3F); }} "
                f"else if ((__rx_oc & 0xF0) == 0xE0) {{ "
                f"  {c_dst} = ((__rx_oc & 0x0F) << 12) | (((unsigned char)({c_src})[1] & 0x3F) << 6) | ((unsigned char)({c_src})[2] & 0x3F); }} "
                f"else {{ "
                f"  {c_dst} = ((__rx_oc & 0x07) << 18) | (((unsigned char)({c_src})[1] & 0x3F) << 12) | (((unsigned char)({c_src})[2] & 0x3F) << 6) | ((unsigned char)({c_src})[3] & 0x3F); }} }}"
            )
            escaped = code.replace("\\", "\\\\").replace('"', '\\"')
            emitter.emit(f'scrc "{escaped}";')
            return temp, "number"

        # --- hex(n) : entier -> chaine "0x..." ---
        if name == "hex":
            ref, vtype = args[0]
            if vtype != "number":
                raise RexResolveError("hex() : l'argument doit etre un 'number' (entier)")
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, "str", '""')
            c_dst = f"SL_{temp}"
            c_src = f"SL_{ref}"
            code = (
                f"{{ char __rx_hxbuf[32]; "
                f"if ({c_src} < 0) snprintf(__rx_hxbuf, 32, \"-0x%x\", (unsigned int)(-(int)({c_src}))); "
                f"else snprintf(__rx_hxbuf, 32, \"0x%x\", (unsigned int)({c_src})); "
                f"free({c_dst}); {c_dst} = strdup(__rx_hxbuf); }}"
            )
            escaped = code.replace("\\", "\\\\").replace('"', '\\"')
            emitter.emit(f'scrc "{escaped}";')
            return temp, "str"

        # --- oct(n) : entier -> chaine "0o..." ---
        if name == "oct":
            ref, vtype = args[0]
            if vtype != "number":
                raise RexResolveError("oct() : l'argument doit etre un 'number' (entier)")
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, "str", '""')
            c_dst = f"SL_{temp}"
            c_src = f"SL_{ref}"
            code = (
                f"{{ char __rx_ocbuf[32]; "
                f"if ({c_src} < 0) snprintf(__rx_ocbuf, 32, \"-0o%o\", (unsigned int)(-(int)({c_src}))); "
                f"else snprintf(__rx_ocbuf, 32, \"0o%o\", (unsigned int)({c_src})); "
                f"free({c_dst}); {c_dst} = strdup(__rx_ocbuf); }}"
            )
            escaped = code.replace("\\", "\\\\").replace('"', '\\"')
            emitter.emit(f'scrc "{escaped}";')
            return temp, "str"

        # --- bin(n) : entier -> chaine "0b..." ---
        if name == "bin":
            ref, vtype = args[0]
            if vtype != "number":
                raise RexResolveError("bin() : l'argument doit etre un 'number' (entier)")
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, "str", '""')
            c_dst = f"SL_{temp}"
            c_src = f"SL_{ref}"
            # Conversion manuelle bit par bit (pas de %b en C standard)
            code = (
                f"{{ long long __rx_bv = (long long)({c_src}); "
                f"char __rx_bnbuf[70]; int __rx_bpos = 68; "
                f"__rx_bnbuf[69] = 0; "
                f"int __rx_bneg = (__rx_bv < 0); "
                f"unsigned long long __rx_buv = __rx_bneg ? (unsigned long long)(-__rx_bv) : (unsigned long long)__rx_bv; "
                f"if (__rx_buv == 0) {{ __rx_bnbuf[__rx_bpos--] = '0'; }} "
                f"else {{ while (__rx_buv > 0) {{ __rx_bnbuf[__rx_bpos--] = '0' + (__rx_buv & 1); __rx_buv >>= 1; }} }} "
                f"__rx_bnbuf[__rx_bpos--] = 'b'; __rx_bnbuf[__rx_bpos--] = '0'; "
                f"if (__rx_bneg) __rx_bnbuf[__rx_bpos--] = '-'; "
                f"free({c_dst}); {c_dst} = strdup(&__rx_bnbuf[__rx_bpos+1]); }}"
            )
            escaped = code.replace("\\", "\\\\").replace('"', '\\"')
            emitter.emit(f'scrc "{escaped}";')
            return temp, "str"

        # --- repr(x) / ascii(x) : representation textuelle ---
        if name in ("repr", "ascii"):
            ref, vtype = args[0]
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, "str", '""')
            c_dst = f"SL_{temp}"
            if vtype == "str":
                c_src = f"SL_{ref}"
                if name == "repr":
                    # Encapsule dans guillemets simples Python : 'valeur'
                    code = (
                        f"{{ size_t __rx_rlen = strlen({c_src}) + 3; "
                        f"char* __rx_rbuf = (char*)malloc(__rx_rlen); "
                        f"snprintf(__rx_rbuf, __rx_rlen, \"'%s'\", {c_src}); "
                        f"free({c_dst}); {c_dst} = __rx_rbuf; }}"
                    )
                else:
                    # ascii() : meme chose + echappe les non-ASCII
                    code = (
                        f"{{ size_t __rx_rlen = strlen({c_src})*6 + 4; "
                        f"char* __rx_rbuf = (char*)malloc(__rx_rlen); "
                        f"char* __rx_rp = __rx_rbuf; *__rx_rp++ = '\\''; "
                        f"for (unsigned char* __rx_rs = (unsigned char*){c_src}; *__rx_rs; __rx_rs++) {{ "
                        f"  if (*__rx_rs >= 0x80) {{ __rx_rp += sprintf(__rx_rp, \"\\\\u%04x\", *__rx_rs); }} "
                        f"  else {{ *__rx_rp++ = *__rx_rs; }} }} "
                        f"*__rx_rp++ = '\\''; *__rx_rp = 0; "
                        f"free({c_dst}); {c_dst} = strdup(__rx_rbuf); free(__rx_rbuf); }}"
                    )
            elif vtype in ("number", "float"):
                # Copie en temp pour change, puis wrapping
                tmp2 = emitter.new_temp_name()
                if vtype == "number":
                    emitter.emit(f"add {tmp2} {ref} 0;")
                else:
                    emitter.emit(f"add {tmp2} {ref} 0.0;")
                emitter.types[tmp2] = vtype
                emitter.emit(f"change {tmp2} str;")
                emitter.types[tmp2] = "str"
                # repr(number) == str(number) en Python — on copie juste
                code = f"free({c_dst}); {c_dst} = strdup(SL_{tmp2});"
            elif vtype == "bool":
                loop_id = emitter.new_loop_id()
                tl = f"__rx_repr{loop_id}_t"
                el = f"__rx_repr{loop_id}_e"
                emitter.emit(f"cdn equal {ref} true;")
                emitter.emit(f"go {tl};")
                emitter.emit(f'add {temp} "False" "";')
                emitter.emit("cdn on;")
                emitter.emit(f"go {el};")
                emitter.emit(f"lbl {tl};")
                emitter.emit(f'add {temp} "True" "";')
                emitter.emit(f"lbl {el};")
                return temp, "str"
            else:
                raise RexResolveError(
                    f"{name}() : type '{vtype}' non supporte "
                    "(attendu number/float/str/bool)"
                )
            escaped = code.replace("\\", "\\\\").replace('"', '\\"')
            emitter.emit(f'scrc "{escaped}";')
            return temp, "str"

        # --- hash(x) : valeur de hachage (number) ---
        if name == "hash":
            ref, vtype = args[0]
            if vtype not in ("number", "float", "str", "bool"):
                raise RexResolveError(
                    f"hash() : type '{vtype}' non supporte (attendu number/float/str/bool)"
                )
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, "number")
            c_dst = f"SL_{temp}"
            c_src = f"SL_{ref}"
            if vtype == "str":
                # DJB2
                code = (
                    f"{{ unsigned long __rx_h = 5381; "
                    f"for (unsigned char* __rx_hp = (unsigned char*){c_src}; *__rx_hp; __rx_hp++) "
                    f"  __rx_h = ((__rx_h << 5) + __rx_h) + *__rx_hp; "
                    f"{c_dst} = (int)(__rx_h & 0x7FFFFFFF); }}"
                )
            elif vtype == "bool":
                code = f"{c_dst} = ({c_src}) ? 1 : 0;"
            else:
                code = f"{c_dst} = (int)({c_src});"
            escaped = code.replace("\\", "\\\\").replace('"', '\\"')
            emitter.emit(f'scrc "{escaped}";')
            return temp, "number"

        # --- id(x) : identifiant memoire (number) ---
        if name == "id":
            ref, vtype = args[0]
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, "number")
            c_dst = f"SL_{temp}"
            c_src = f"SL_{ref}"
            if vtype in ("list", "tuple", "set", "dict"):
                code = f"{c_dst} = (int)(size_t)({c_src});"
            else:
                code = f"{c_dst} = (int)(size_t)(&{c_src});"
            escaped = code.replace("\\", "\\\\").replace('"', '\\"')
            emitter.emit(f'scrc "{escaped}";')
            return temp, "number"

        # --- callable(x) : verifie si l'objet est appelable ---
        if name == "callable":
            ref, vtype = args[0]
            # En REX, seul le type "funcref" est appelable
            is_callable = (ref in emitter.funcrefs or vtype == "funcref")
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, "bool", "true" if is_callable else "false")
            return temp, "bool"

        # --- isinstance(obj, type_str) : verifie le type a l'execution ---
        if name == "isinstance":
            (ref, vtype), (cls_ref, cls_type) = args
            if cls_type != "str":
                raise RexResolveError(
                    "isinstance() : en REX, le deuxieme argument doit etre une "
                    "chaine litterale designant le type (ex: isinstance(x, \"number\"))"
                )
            # Delogue a l'opcode REX-SL `type` puis compare
            type_temp = emitter.new_temp_name()
            emitter.emit(f"type {type_temp} {ref};")
            emitter.types[type_temp] = "str"
            loop_id = emitter.new_loop_id()
            true_lbl = f"__rx_isa{loop_id}_t"
            end_lbl  = f"__rx_isa{loop_id}_e"
            result   = emitter.new_temp_name()
            emitter.declare_literal(result, "bool", "false")
            emitter.emit(f"cdn equal {type_temp} {cls_ref};")
            emitter.emit(f"go {true_lbl};")
            emitter.emit("cdn on;")
            emitter.emit(f"go {end_lbl};")
            emitter.emit(f"lbl {true_lbl};")
            emitter.emit(f"{result} true;")
            emitter.emit(f"lbl {end_lbl};")
            return result, "bool"

        # --- issubclass(cls, parent) : non pertinent sans systeme de classes —
        #     renvoie toujours false, avec avertissement compile ---
        if name == "issubclass":
            raise RexResolveError(
                "issubclass() : non supporte en REX (pas de systeme de classes). "
                "Utilisez isinstance(obj, \"type\") pour verifier le type d'une valeur."
            )

        # --- hasattr(obj, name) : verifie l'existence d'un attribut ---
        if name == "hasattr":
            raise RexResolveError(
                "hasattr() : non supporte en REX (pas d'attributs d'objet). "
                "Utilisez type(x) pour inspecter le type d'une valeur."
            )

        # --- getattr / setattr / delattr : non supportes ---
        if name in ("getattr", "setattr", "delattr"):
            raise RexResolveError(
                f"{name}() : non supporte en REX (pas d'attributs d'objet). "
                "Les proprietes et attributs Python n'ont pas d'equivalent en REX."
            )

        # --- dir(x) / vars(x) / globals() / locals() ---
        if name in ("dir", "vars", "globals", "locals"):
            raise RexResolveError(
                f"{name}() : non supporte en REX (pas de reflexion dynamique). "
                "Utilisez type(x) pour inspecter le type d'une valeur."
            )

        # --- round(x[, n]) : arrondi ---
        if name == "round":
            if nargs not in (1, 2):
                raise RexResolveError(f"round() : 1 ou 2 arguments attendus, {nargs} fourni(s)")
            ref, vtype = args[0]
            if vtype not in ("number", "float"):
                raise RexResolveError(
                    f"round() : type '{vtype}' non supporte (attendu number ou float)"
                )
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, "number" if nargs == 1 else "float")
            c_dst = f"SL_{temp}"
            c_src = f"SL_{ref}"
            if nargs == 1:
                code = f"{c_dst} = (int)round((double){c_src});"
                emitter.types[temp] = "number"
            else:
                nref, ntype = args[1]
                if ntype != "number":
                    raise RexResolveError("round() : le nombre de decimales doit etre un 'number'")
                c_n = f"SL_{nref}"
                code = (
                    f"{{ double __rx_rpow = pow(10.0, (double){c_n}); "
                    f"{c_dst} = round((double){c_src} * __rx_rpow) / __rx_rpow; }}"
                )
                emitter.types[temp] = "float"
            escaped = code.replace("\\", "\\\\").replace('"', '\\"')
            emitter.emit(f'scrc "{escaped}";')
            return temp, emitter.types[temp]

        # --- pow(base, exp[, mod]) : puissance (surcharge de **) ---
        if name == "pow":
            if nargs not in (2, 3):
                raise RexResolveError(f"pow() : 2 ou 3 arguments attendus, {nargs} fourni(s)")
            (base_ref, base_type), (exp_ref, exp_type) = args[0], args[1]
            if base_type not in ("number", "float") or exp_type not in ("number", "float"):
                raise RexResolveError("pow() : les arguments base et exposant doivent etre number ou float")
            # Delogue a l'opcode REX-SL `pow` existant (0.0.14)
            if nargs == 2:
                temp = emitter.new_temp_name()
                result_type = "float" if (base_type == "float" or exp_type == "float") else "number"
                emitter.emit(f"pow {temp} {base_ref} {exp_ref};")
                emitter.types[temp] = result_type
                return temp, result_type
            # pow(base, exp, mod) : (base**exp) % mod via scrc
            (mod_ref, mod_type) = args[2]
            if mod_type != "number":
                raise RexResolveError("pow() : le troisieme argument (mod) doit etre un 'number'")
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, "number")
            c_dst  = f"SL_{temp}"
            c_base = f"SL_{base_ref}"
            c_exp  = f"SL_{exp_ref}"
            c_mod  = f"SL_{mod_ref}"
            code   = f"{c_dst} = (int)(round(pow((double){c_base}, (double){c_exp}))) % {c_mod};"
            escaped = code.replace("\\", "\\\\").replace('"', '\\"')
            emitter.emit(f'scrc "{escaped}";')
            return temp, "number"

        # --- divmod(a, b) : (quotient, reste) -> list [q, r] ---
        if name == "divmod":
            (a_ref, a_type), (b_ref, b_type) = args
            if a_type not in ("number", "float") or b_type not in ("number", "float"):
                raise RexResolveError("divmod() : les deux arguments doivent etre number ou float")
            # Retourne une list [quotient, reste]
            q_temp = emitter.new_temp_name()
            r_temp = emitter.new_temp_name()
            result_type = "float" if (a_type == "float" or b_type == "float") else "number"
            emitter.declare_literal(q_temp, result_type)
            emitter.declare_literal(r_temp, result_type)
            c_q = f"SL_{q_temp}"; c_r = f"SL_{r_temp}"
            c_a = f"SL_{a_ref}";  c_b = f"SL_{b_ref}"
            if result_type == "number":
                code = f"{c_q} = {c_a} / {c_b}; {c_r} = {c_a} % {c_b};"
            else:
                code = f"{c_q} = floor((double){c_a} / (double){c_b}); {c_r} = fmod((double){c_a}, (double){c_b});"
            escaped = code.replace("\\", "\\\\").replace('"', '\\"')
            emitter.emit(f'scrc "{escaped}";')
            # Construit et retourne la list [q, r]
            list_temp = emitter.new_temp_name()
            emitter.declare_literal(list_temp, "list")
            emitter.emit(f"append {list_temp} {result_type} {q_temp};")
            emitter.emit(f"append {list_temp} {result_type} {r_temp};")
            emitter.types[list_temp] = "list"
            emitter.note_elem_type(list_temp, result_type)
            return list_temp, "list"

        # --- sum(iterable) : somme des elements d'une liste ---
        if name == "sum":
            ref, vtype = args[0]
            if vtype not in ("list", "tuple", "set"):
                raise RexResolveError(
                    f"sum() : type '{vtype}' non supporte (attendu list/tuple/set de number ou float)"
                )
            elem_type = emitter.get_elem_type(ref)
            if elem_type not in ("number", "float"):
                raise RexResolveError(
                    "sum() : la liste doit contenir des elements de type number ou float"
                )
            # Boucle REX-SL : for i in range(len(ref)): acc += ref[i]
            loop_id = emitter.new_loop_id()
            acc = emitter.new_temp_name()
            idx = emitter.new_temp_name()
            llen= emitter.new_temp_name()
            elem= emitter.new_temp_name()
            loop_start = f"__rx_sum{loop_id}_s"
            loop_end   = f"__rx_sum{loop_id}_e"
            emitter.declare_literal(acc,  elem_type, "0" if elem_type == "number" else "0.0")
            emitter.declare_literal(idx,  "number")
            emitter.declare_literal(llen, "number")
            emitter.declare_literal(elem, elem_type)
            emitter.emit(f"len {llen} {ref};")
            emitter.emit(f"lbl {loop_start};")
            emitter.emit(f"cdn less {idx} {llen};")
            emitter.emit(f"go {loop_end};")
            emitter.emit(f"get {ref} {elem_type} {elem} {idx};")
            emitter.emit(f"add {acc} {acc} {elem};")
            emitter.emit(f"add {idx} {idx} 1;")
            emitter.emit("cdn on;")
            emitter.emit(f"go {loop_start};")
            emitter.emit(f"lbl {loop_end};")
            return acc, elem_type

        # --- min(a, b, ...) ou min(iterable) : minimum ---
        # --- max(a, b, ...) ou max(iterable) : maximum ---
        if name in ("min", "max"):
            if nargs == 0:
                raise RexResolveError(f"{name}() : au moins 1 argument requis")
            op = "less" if name == "min" else "greater"
            if nargs == 1:
                # Forme iterable
                ref, vtype = args[0]
                if vtype not in ("list", "tuple", "set"):
                    raise RexResolveError(
                        f"{name}() avec 1 argument : attend une list/tuple/set"
                    )
                elem_type = emitter.get_elem_type(ref)
                if elem_type not in ("number", "float"):
                    raise RexResolveError(
                        f"{name}() : la liste doit contenir des elements de type number ou float"
                    )
                loop_id = emitter.new_loop_id()
                res  = emitter.new_temp_name()
                idx  = emitter.new_temp_name()
                llen = emitter.new_temp_name()
                elem = emitter.new_temp_name()
                ls = f"__rx_{name}{loop_id}_s"
                le = f"__rx_{name}{loop_id}_e"
                lk = f"__rx_{name}{loop_id}_k"
                emitter.declare_literal(res,  elem_type)
                emitter.declare_literal(idx,  "number")
                emitter.declare_literal(llen, "number")
                emitter.declare_literal(elem, elem_type)
                emitter.emit(f"len {llen} {ref};")
                emitter.emit(f"get {ref} {elem_type} {res} 0;")
                emitter.emit(f"add {idx} 0 1;")
                emitter.emit(f"lbl {ls};")
                emitter.emit(f"cdn less {idx} {llen};")
                emitter.emit(f"go {le};")
                emitter.emit(f"get {ref} {elem_type} {elem} {idx};")
                emitter.emit(f"cdn {op} {elem} {res};")
                emitter.emit(f"go {lk};")
                emitter.emit("cdn on;")
                emitter.emit(f"go {lk};")
                emitter.emit(f"lbl {lk};")
                # Si condition vraie, copier elem dans res
                lset = f"__rx_{name}{loop_id}_set"
                lnxt = f"__rx_{name}{loop_id}_nxt"
                emitter.emit(f"cdn {op} {elem} {res};")
                emitter.emit(f"go {lset};")
                emitter.emit("cdn on;")
                emitter.emit(f"go {lnxt};")
                emitter.emit(f"lbl {lset};")
                if elem_type == "number":
                    emitter.emit(f"add {res} {elem} 0;")
                else:
                    emitter.emit(f"add {res} {elem} 0.0;")
                emitter.emit(f"lbl {lnxt};")
                emitter.emit(f"add {idx} {idx} 1;")
                emitter.emit("cdn on;")
                emitter.emit(f"go {ls};")
                emitter.emit(f"lbl {le};")
                return res, elem_type
            else:
                # Forme multi-args
                vtypes = [a[1] for a in args]
                if not all(t in ("number", "float") for t in vtypes):
                    raise RexResolveError(
                        f"{name}() : tous les arguments doivent etre de type number ou float"
                    )
                result_type = "float" if any(t == "float" for t in vtypes) else "number"
                res = emitter.new_temp_name()
                zero = "0.0" if result_type == "float" else "0"
                emitter.emit(f"add {res} {args[0][0]} {zero};")
                emitter.types[res] = result_type
                loop_id = emitter.new_loop_id()
                for i, (aref, _) in enumerate(args[1:], 1):
                    lset = f"__rx_{name}{loop_id}_s{i}"
                    lnxt = f"__rx_{name}{loop_id}_n{i}"
                    emitter.emit(f"cdn {op} {aref} {res};")
                    emitter.emit(f"go {lset};")
                    emitter.emit("cdn on;")
                    emitter.emit(f"go {lnxt};")
                    emitter.emit(f"lbl {lset};")
                    emitter.emit(f"add {res} {aref} {zero};")
                    emitter.emit(f"lbl {lnxt};")
                return res, result_type

        # --- all(iterable) : True si tous les elements sont vrais ---
        # --- any(iterable) : True si au moins un element est vrai ---
        if name in ("all", "any"):
            ref, vtype = args[0]
            if vtype not in ("list", "tuple", "set"):
                raise RexResolveError(
                    f"{name}() : attend une list/tuple/set de bool"
                )
            elem_type = emitter.get_elem_type(ref)
            if elem_type != "bool":
                raise RexResolveError(
                    f"{name}() : la liste doit contenir des elements de type bool "
                    "(limitation REX : pas de coercion implicite vers bool)"
                )
            loop_id = emitter.new_loop_id()
            res  = emitter.new_temp_name()
            idx  = emitter.new_temp_name()
            llen = emitter.new_temp_name()
            elem = emitter.new_temp_name()
            ls = f"__rx_{name}{loop_id}_s"
            le = f"__rx_{name}{loop_id}_e"
            learly = f"__rx_{name}{loop_id}_early"
            init_val = "true" if name == "all" else "false"
            short_val = "false" if name == "all" else "true"
            cond_op = "equal"  # all: quitte si false ; any: quitte si true
            cond_val = "false" if name == "all" else "true"
            emitter.declare_literal(res,  "bool", init_val)
            emitter.declare_literal(idx,  "number")
            emitter.declare_literal(llen, "number")
            emitter.declare_literal(elem, "bool", "false")
            emitter.emit(f"len {llen} {ref};")
            emitter.emit(f"lbl {ls};")
            emitter.emit(f"cdn less {idx} {llen};")
            emitter.emit(f"go {le};")
            emitter.emit(f"get {ref} bool {elem} {idx};")
            emitter.emit(f"cdn {cond_op} {elem} {cond_val};")
            emitter.emit(f"go {learly};")
            emitter.emit("cdn on;")
            emitter.emit(f"add {idx} {idx} 1;")
            emitter.emit(f"go {ls};")
            emitter.emit(f"lbl {learly};")
            emitter.emit(f"{res} {short_val};")
            emitter.emit(f"lbl {le};")
            return res, "bool"

        # --- sorted(iterable) : tri d'une liste, retourne une nouvelle liste ---
        if name == "sorted":
            ref, vtype = args[0]
            if vtype not in ("list", "tuple", "set"):
                raise RexResolveError(
                    "sorted() : attend une list/tuple/set de number/float/str"
                )
            elem_type = emitter.get_elem_type(ref)
            if elem_type not in ("number", "float", "str"):
                raise RexResolveError(
                    "sorted() : la liste doit contenir des elements de type "
                    "number, float ou str"
                )
            # Copie la liste source, puis tri par insertion via scrc
            result = emitter.new_temp_name()
            emitter.declare_literal(result, "list")
            emitter.types[result] = "list"
            emitter.note_elem_type(result, elem_type)
            # Copie les elements
            loop_id = emitter.new_loop_id()
            idx  = emitter.new_temp_name()
            llen = emitter.new_temp_name()
            elem = emitter.new_temp_name()
            ls = f"__rx_srt{loop_id}_s"
            le = f"__rx_srt{loop_id}_e"
            emitter.declare_literal(idx,  "number")
            emitter.declare_literal(llen, "number")
            emitter.declare_literal(elem, elem_type)
            emitter.emit(f"len {llen} {ref};")
            emitter.emit(f"lbl {ls};")
            emitter.emit(f"cdn less {idx} {llen};")
            emitter.emit(f"go {le};")
            emitter.emit(f"get {ref} {elem_type} {elem} {idx};")
            emitter.emit(f"append {result} {elem_type} {elem};")
            emitter.emit(f"add {idx} {idx} 1;")
            emitter.emit("cdn on;")
            emitter.emit(f"go {ls};")
            emitter.emit(f"lbl {le};")
            # Tri par insertion via opcode REX-SL `sort`
            emitter.emit(f"sort {result};")
            return result, "list"

        # --- reversed(iterable) : iterable inverse (retourne une liste) ---
        if name == "reversed":
            ref, vtype = args[0]
            if vtype not in ("list", "tuple", "set"):
                raise RexResolveError(
                    "reversed() : attend une list/tuple/set"
                )
            elem_type = emitter.get_elem_type(ref)
            # Copie en sens inverse
            loop_id = emitter.new_loop_id()
            result = emitter.new_temp_name()
            llen   = emitter.new_temp_name()
            idx    = emitter.new_temp_name()
            elem   = emitter.new_temp_name()
            ls = f"__rx_rev{loop_id}_s"
            le = f"__rx_rev{loop_id}_e"
            emitter.declare_literal(result, "list")
            emitter.declare_literal(llen, "number")
            emitter.declare_literal(idx,  "number")
            emitter.declare_literal(elem, elem_type or "number")
            emitter.emit(f"len {llen} {ref};")
            emitter.emit(f"sub {idx} {llen} 1;")
            emitter.emit(f"lbl {ls};")
            emitter.emit(f"cdn greater_equal {idx} 0;")
            emitter.emit(f"go {le};")
            emitter.emit(f"get {ref} {elem_type or 'number'} {elem} {idx};")
            emitter.emit(f"append {result} {elem_type or 'number'} {elem};")
            emitter.emit(f"sub {idx} {idx} 1;")
            emitter.emit("cdn on;")
            emitter.emit(f"go {ls};")
            emitter.emit(f"lbl {le};")
            emitter.types[result] = "list"
            if elem_type:
                emitter.note_elem_type(result, elem_type)
            return result, "list"

        # --- enumerate(iterable) : retourne une list de pairs [i, val] ---
        #     Note : REX-SL ne supporte pas les tuples natifs, les pairs
        #     sont des listes de 2 elements (comme partout en REX).
        if name == "enumerate":
            ref, vtype = args[0]
            if vtype not in ("list", "tuple", "set"):
                raise RexResolveError(
                    "enumerate() : attend une list/tuple/set"
                )
            elem_type = emitter.get_elem_type(ref)
            raise RexResolveError(
                "enumerate() : utilisable uniquement dans la tete d'un 'for' "
                "(ex: 'for i, v in enumerate(liste):') - "
                "enumerate() n'est pas disponible comme valeur independante "
                "(limitation REX : pas de listes de listes heterogenes)"
            )

        # --- map(func, iterable) : non supporte comme valeur independante ---
        if name == "map":
            raise RexResolveError(
                "map() : non supporte comme expression independante en REX. "
                "Utilisez une list comprehension : [f(x) for x in liste]"
            )

        # --- filter(func, iterable) : non supporte comme valeur independante ---
        if name == "filter":
            raise RexResolveError(
                "filter() : non supporte comme expression independante en REX. "
                "Utilisez une list comprehension : [x for x in liste if cond(x)]"
            )

        # --- zip(*iterables) : non supporte comme valeur independante ---
        if name == "zip":
            raise RexResolveError(
                "zip() : non supporte comme expression independante en REX. "
                "Utilisez des boucles for avec un index commun."
            )

        # --- list(x) / tuple(x) / set(x) : conversion/copie de collection ---
        if name in ("list", "tuple", "set"):
            ref, vtype = args[0]
            if vtype not in ("list", "tuple", "set"):
                raise RexResolveError(
                    f"{name}() : attend une collection list/tuple/set comme argument "
                    "(limitation REX : pas de conversion depuis str ou dict)"
                )
            # Copie de la collection
            elem_type = emitter.get_elem_type(ref)
            loop_id = emitter.new_loop_id()
            result = emitter.new_temp_name()
            llen   = emitter.new_temp_name()
            idx    = emitter.new_temp_name()
            elem   = emitter.new_temp_name()
            ls = f"__rx_col{loop_id}_s"
            le = f"__rx_col{loop_id}_e"
            emitter.declare_literal(result, "list")
            emitter.declare_literal(llen, "number")
            emitter.declare_literal(idx,  "number")
            emitter.declare_literal(elem, elem_type or "number")
            emitter.emit(f"len {llen} {ref};")
            emitter.emit(f"lbl {ls};")
            emitter.emit(f"cdn less {idx} {llen};")
            emitter.emit(f"go {le};")
            emitter.emit(f"get {ref} {elem_type or 'number'} {elem} {idx};")
            emitter.emit(f"append {result} {elem_type or 'number'} {elem};")
            emitter.emit(f"add {idx} {idx} 1;")
            emitter.emit("cdn on;")
            emitter.emit(f"go {ls};")
            emitter.emit(f"lbl {le};")
            emitter.types[result] = "list"
            if elem_type:
                emitter.note_elem_type(result, elem_type)
            return result, "list"

        # --- dict() : cree un dictionnaire vide ---
        if name == "dict":
            if nargs != 0:
                raise RexResolveError(
                    "dict() : en REX, dict() sans argument cree un dict vide. "
                    "Pour initialiser avec des valeurs, utilisez un litteral : {\"cle\": val}"
                )
            result = emitter.new_temp_name()
            emitter.declare_literal(result, "dict")
            emitter.types[result] = "dict"
            return result, "dict"

        # --- frozenset(iterable) : alias de set() en REX (pas de type dedie) ---
        if name == "frozenset":
            # Meme implementation que list()/set() — represente en interne
            # comme une list (comme tous les set en REX)
            ref, vtype = args[0]
            if vtype not in ("list", "tuple", "set"):
                raise RexResolveError(
                    "frozenset() : attend une collection list/tuple/set comme argument"
                )
            elem_type = emitter.get_elem_type(ref)
            loop_id = emitter.new_loop_id()
            result = emitter.new_temp_name()
            llen   = emitter.new_temp_name()
            idx    = emitter.new_temp_name()
            elem   = emitter.new_temp_name()
            ls = f"__rx_frs{loop_id}_s"
            le = f"__rx_frs{loop_id}_e"
            emitter.declare_literal(result, "list")
            emitter.declare_literal(llen, "number")
            emitter.declare_literal(idx,  "number")
            emitter.declare_literal(elem, elem_type or "number")
            emitter.emit(f"len {llen} {ref};")
            emitter.emit(f"lbl {ls};")
            emitter.emit(f"cdn less {idx} {llen};")
            emitter.emit(f"go {le};")
            emitter.emit(f"get {ref} {elem_type or 'number'} {elem} {idx};")
            emitter.emit(f"append {result} {elem_type or 'number'} {elem};")
            emitter.emit(f"add {idx} {idx} 1;")
            emitter.emit("cdn on;")
            emitter.emit(f"go {ls};")
            emitter.emit(f"lbl {le};")
            emitter.types[result] = "list"
            if elem_type:
                emitter.note_elem_type(result, elem_type)
            return result, "list"

        # --- bytes() / bytearray() / memoryview() : non supportes ---
        if name in ("bytes", "bytearray", "memoryview"):
            raise RexResolveError(
                f"{name}() : non supporte en REX (pas de type bytes natif). "
                "Utilisez une list de number pour representer des octets."
            )

        # --- complex(real[, imag]) : non supporte ---
        if name == "complex":
            raise RexResolveError(
                "complex() : non supporte en REX (pas de type complexe natif). "
                "Utilisez deux variables float distinctes pour la partie reelle et imaginaire."
            )

        # --- format(value[, spec]) : formatage Python ---
        if name == "format":
            if nargs not in (1, 2):
                raise RexResolveError(f"format() : 1 ou 2 arguments attendus, {nargs} fourni(s)")
            ref, vtype = args[0]
            if nargs == 1:
                return self.to_str(ref, vtype), "str"
            spec_ref, spec_type = args[1]
            if spec_type != "str":
                raise RexResolveError("format() : la spec de format doit etre une 'str' litterale")
            # On tente d'extraire la spec litterale depuis l'AST
            spec_node = arg_nodes[1]
            if spec_node[0] == "lit" and isinstance(spec_node[1], str):
                return self._apply_fmt_spec(ref, vtype, spec_node[1])
            raise RexResolveError(
                "format() : la spec de format doit etre une chaine LITTERALE "
                "(ex: format(x, '.2f')) - les specs dynamiques (variables) ne sont "
                "pas supportees"
            )

        # --- print() : alias de show() ---
        if name == "print":
            # Delogue vers la logique show() deja existante dans REX_ShowStatement
            # Ici dans un contexte d'expression : compile show et retourne None
            show_args = []
            sep = " "; end = "\n"
            for spec in arg_specs:
                if spec[0] == "kwarg":
                    _, pname, node = spec
                    if pname == "sep":
                        if node[0] == "lit" and isinstance(node[1], str):
                            sep = node[1]
                    elif pname == "end":
                        if node[0] == "lit" and isinstance(node[1], str):
                            end = node[1]
                else:
                    show_args.append(spec[1])
            # Emet les showln/show via la logique existante
            if not show_args:
                emitter.emit(f'show "\\n";')
            else:
                parts_str = []
                for i, node in enumerate(show_args):
                    ref_s, vtype_s = self.generate(node)
                    s_ref = self.to_str(ref_s, vtype_s)
                    parts_str.append(s_ref)
                # Concatene avec sep
                if len(parts_str) == 1:
                    combined = parts_str[0]
                else:
                    combined = parts_str[0]
                    for s in parts_str[1:]:
                        sep_temp = emitter.new_temp_name()
                        sep_q = self._quote(sep)
                        emitter.emit(f"add {sep_temp} {combined} {sep_q};")
                        emitter.types[sep_temp] = "str"
                        nxt = emitter.new_temp_name()
                        emitter.emit(f"add {nxt} {sep_temp} {s};")
                        emitter.types[nxt] = "str"
                        combined = nxt
                if end == "\n":
                    emitter.emit(f"showln {combined};")
                else:
                    emitter.emit(f"show {combined};")
                    if end:
                        end_q = self._quote(end)
                        end_t = emitter.new_temp_name()
                        emitter.declare_literal(end_t, "str", end_q)
                        emitter.emit(f"show {end_t};")
            return NONE_REF, "none"

        # --- input([prompt]) : lecture clavier ---
        if name == "input":
            if nargs > 1:
                raise RexResolveError(f"input() : 0 ou 1 argument attendu, {nargs} fourni(s)")
            if nargs == 1:
                # Affiche le prompt d'abord (sans retour a la ligne)
                ref_p, vtype_p = args[0]
                s_ref = self.to_str(ref_p, vtype_p)
                emitter.emit(f"show {s_ref};")
            # Lit une ligne depuis stdin via l'opcode REX-SL natif 'input'
            # (evite le double-free que causait le scrc : declare_literal marque
            # la variable heap, puis le scrc faisait free+strdup, puis le GC de
            # REX-SL liberait une seconde fois -> munmap_chunk: invalid pointer)
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, "str", '""')
            emitter.emit(f"input {temp};")
            return temp, "str"

        # --- range(stop) / range(start,stop) / range(start,stop,step) ---
        #     comme EXPRESSION (retourne une list) — la forme `for x in range(...)`
        #     est deja geree optimalement par REX_ForStatement.
        if name == "range":
            if nargs not in (1, 2, 3):
                raise RexResolveError(f"range() : 1, 2 ou 3 arguments attendus, {nargs} fourni(s)")
            if nargs == 1:
                start_ref, start_type = "0", "number"
                stop_ref,  stop_type  = args[0]
                step_ref,  step_type  = "1", "number"
            elif nargs == 2:
                start_ref, start_type = args[0]
                stop_ref,  stop_type  = args[1]
                step_ref,  step_type  = "1", "number"
            else:
                start_ref, start_type = args[0]
                stop_ref,  stop_type  = args[1]
                step_ref,  step_type  = args[2]
            for n, t in (("start", start_type), ("stop", stop_type), ("step", step_type)):
                if t != "number":
                    raise RexResolveError(f"range() : l'argument '{n}' doit etre un 'number'")
            loop_id = emitter.new_loop_id()
            result = emitter.new_temp_name()
            cur    = emitter.new_temp_name()
            ls = f"__rx_rng{loop_id}_s"
            le = f"__rx_rng{loop_id}_e"
            emitter.declare_literal(result, "list")
            emitter.declare_literal(cur,    "number")
            emitter.emit(f"add {cur} {start_ref} 0;")
            emitter.emit(f"lbl {ls};")
            emitter.emit(f"cdn less {cur} {stop_ref};")
            emitter.emit(f"go {le};")
            emitter.emit(f"append {result} number {cur};")
            emitter.emit(f"add {cur} {cur} {step_ref};")
            emitter.emit("cdn on;")
            emitter.emit(f"go {ls};")
            emitter.emit(f"lbl {le};")
            emitter.types[result] = "list"
            emitter.note_elem_type(result, "number")
            return result, "list"

        # --- iter(iterable) : en REX, retourne la collection elle-meme ---
        if name == "iter":
            ref, vtype = args[0]
            if vtype not in ("list", "tuple", "set", "str"):
                raise RexResolveError(
                    f"iter() : type '{vtype}' non supporte (attendu list/tuple/set/str)"
                )
            # REX n'a pas d'objet iterateur : on retourne la valeur telle quelle
            return ref, vtype

        # --- next() : non supporte ---
        if name == "next":
            raise RexResolveError(
                "next() : non supporte en REX (pas d'objets iterateurs). "
                "Utilisez une boucle for ou un index direct."
            )

        # --- aiter() / anext() : non supportes (asynchrone) ---
        if name in ("aiter", "anext"):
            raise RexResolveError(
                f"{name}() : non supporte en REX (pas de support async/await)."
            )

        # --- object() : retourne une representation textuelle generique ---
        if name == "object":
            if nargs != 0:
                raise RexResolveError("object() : ne prend pas d'argument")
            temp = emitter.new_temp_name()
            emitter.declare_literal(temp, "str", '"<object>"')
            emitter.types[temp] = "str"
            return temp, "str"

        # --- super() : non supporte (pas de classes) ---
        if name == "super":
            raise RexResolveError(
                "super() : non supporte en REX (pas de systeme de classes). "
                "Utilisez des fonctions ordinaires."
            )

        # --- property() / classmethod() / staticmethod() : non supportes ---
        if name in ("property", "classmethod", "staticmethod"):
            raise RexResolveError(
                f"{name}() : non supporte en REX (pas de systeme de classes). "
                "Utilisez des fonctions ordinaires avec 'func'."
            )

        # --- eval(expr_str) : evalue une expression REX au runtime ---
        #     Non implementable sans interpreteur embarque.
        if name == "eval":
            raise RexResolveError(
                "eval() : non supporte en REX (pas d'interpreteur embarque). "
                "Les expressions doivent etre connues a la compilation."
            )

        # --- exec(code_str) : execute du code ---
        if name == "exec":
            raise RexResolveError(
                "exec() : non supporte en REX (pas d'interpreteur embarque). "
                "Le code doit etre compile statiquement."
            )

        # --- compile() : non supporte ---
        if name == "compile":
            raise RexResolveError(
                "compile() : non supporte en REX (pas d'interpreteur embarque). "
                "Tout code est compile statiquement."
            )

        # --- open() : delogue aux opcodes REX-SL read/write ---
        if name == "open":
            raise RexResolveError(
                "open() : utilisez directement read(path) / readlines(path) "
                "pour lire, et write(path, val) / writelines(path, liste) pour ecrire. "
                "REX ne supporte pas l'objet fichier Python (pas de mode append, "
                "pas de close() explicite)."
            )

        # --- breakpoint() : lance le debogueur ---
        if name == "breakpoint":
            # Insere un point d'arret C via scrc (fonctionne avec gdb/lldb)
            code = "raise(SIGTRAP);"
            escaped = code.replace("\\", "\\\\").replace('"', '\\"')
            emitter.emit(f'scrc "{escaped}";')
            return NONE_REF, "none"

        # --- help() : affiche une aide minimale ---
        if name == "help":
            if nargs == 0:
                msg = "Aide REX : consultez la documentation REX.py"
            else:
                ref_h, vtype_h = args[0]
                msg = None
            temp = emitter.new_temp_name()
            if msg is not None:
                emitter.declare_literal(temp, "str", self._quote(msg))
                emitter.emit(f"showln {temp};")
            else:
                # help(x) : affiche le type de x
                type_t = emitter.new_temp_name()
                emitter.emit(f"type {type_t} {ref_h};")
                emitter.types[type_t] = "str"
                prefix = emitter.new_temp_name()
                emitter.declare_literal(prefix, "str", '"Type REX : "')
                msg_t = emitter.new_temp_name()
                emitter.emit(f"add {msg_t} {prefix} {type_t};")
                emitter.types[msg_t] = "str"
                emitter.emit(f"showln {msg_t};")
                temp = NONE_REF
            return NONE_REF, "none"

        raise RexResolveError(f"fonction native non geree : {name}")

    def _slice(self, base_node, start_node, end_node):
        """Genere le code du slice postfixe `x[debut:fin]` a la syntaxe
        Python (voir ExprParser._parse_slice) : delegue au meme opcode
        REX-SL `slice` que le builtin `slice(s, a, b)` (0.0.12), donc
        seulement supporte sur une 'str' (limitation REX-SL : pas
        d'indexation generique sur 'list'). Bornes omises a la Python :
        `x[:b]` -> debut = 0, `x[a:]` / `x[:]` -> fin = len(x) (opcode
        `len`, lui aussi reserve aux 'str')."""
        ref, vtype = self.generate(base_node)
        if vtype != "str":
            raise RexResolveError(
                f"'[debut:fin]' non supporte sur le type '{vtype}' (limitation "
                "REX-SL : le slice n'est disponible que sur une 'str')"
            )

        if start_node is not None:
            start_ref, start_type = self.generate(start_node)
            if start_type != "number":
                raise RexResolveError("'[debut:fin]' : le debut doit etre un 'number'")
        else:
            start_ref = "0"

        if end_node is not None:
            end_ref, end_type = self.generate(end_node)
            if end_type != "number":
                raise RexResolveError("'[debut:fin]' : la fin doit etre un 'number'")
        else:
            end_ref = self.emitter.new_temp_name()
            self.emitter.declare_literal(end_ref, "number")
            self.emitter.emit(f"len {end_ref} {ref};")

        temp = self.emitter.new_temp_name()
        self.emitter.emit(f"slice {temp} {ref} {start_ref} {end_ref};")
        self.emitter.types[temp] = "str"
        return temp, "str"

    def _slice_step(self, base_node, start_node, end_node, step_node):
        """Genere le code du slice postfixe AVEC PAS `x[debut:fin:pas]`
        (0.0.14, syntaxe Python) : delegue au nouvel opcode REX-SL
        `slicestep`, uniquement sur 'str' (meme limitation que `slice`).
        Le pas doit etre un ENTIER LITTERAL connu a la compilation (meme
        contrainte que `range(a, b, pas)`, cf. REX_ForStatement._compile_range) :
        REX-SL n'a pas de branchement conditionnel exploitable ici pour
        choisir le sens de parcours a l'execution selon le signe d'un pas
        variable. Bornes omises a la Python : le defaut depend du signe du
        pas (`x[::-1]` -> inversion complete, `x[::2]` -> depuis le debut)."""
        ref, vtype = self.generate(base_node)
        if vtype != "str":
            raise RexResolveError(
                f"'[debut:fin:pas]' non supporte sur le type '{vtype}' (limitation "
                "REX-SL : le slice n'est disponible que sur une 'str')"
            )

        step_value = REX_ForStatement._literal_int_or_none(step_node)
        if step_value is None:
            raise RexResolveError(
                "'[debut:fin:pas]' : le pas doit etre un entier litteral connu a la "
                "compilation (limitation REX-SL, ex: x[::-1], pas x[::s])"
            )
        if step_value == 0:
            raise RexResolveError("'[debut:fin:pas]' : le pas ne peut pas etre 0")
        # Nombres negatifs : le tokenizer REX-SL lexe '-' et le chiffre separement
        # -> on passe toujours par un temporaire pour le pas (et pour end=-1).
        if step_value < 0:
            step_ref = self.emitter.new_temp_name()
            self.emitter.emit(f"sub {step_ref} 0 {-step_value};")
            self.emitter.types[step_ref] = "number"
        else:
            step_ref, _step_type = self._literal(step_value)

        if start_node is not None:
            start_ref, start_type = self.generate(start_node)
            if start_type != "number":
                raise RexResolveError("'[debut:fin:pas]' : le debut doit etre un 'number'")
        elif step_value > 0:
            start_ref = "0"
        else:
            start_ref = self.emitter.new_temp_name()
            self.emitter.declare_literal(start_ref, "number")
            self.emitter.emit(f"len {start_ref} {ref};")
            self.emitter.emit(f"sub {start_ref} {start_ref} 1;")

        if end_node is not None:
            end_ref, end_type = self.generate(end_node)
            if end_type != "number":
                raise RexResolveError("'[debut:fin:pas]' : la fin doit etre un 'number'")
        elif step_value > 0:
            end_ref = self.emitter.new_temp_name()
            self.emitter.declare_literal(end_ref, "number")
            self.emitter.emit(f"len {end_ref} {ref};")
        else:
            # sentinelle -1 : "jusqu'au debut de la chaine inclus" (le C ne
            # peut pas exprimer "avant l'indice 0" autrement en 'number').
            # On passe par un temporaire plutot que le litteral '-1' brut :
            # le tokenizer REX-SL ne reconnait pas les nombres negatifs (le
            # '-' est lexe comme 'unknown' separement du chiffre).
            end_ref = self.emitter.new_temp_name()
            self.emitter.emit(f"sub {end_ref} 0 1;")
            self.emitter.types[end_ref] = "number"

        temp = self.emitter.new_temp_name()
        self.emitter.emit(f"slicestep {temp} {ref} {start_ref} {end_ref} {step_ref};")
        self.emitter.types[temp] = "str"
        return temp, "str"

    def _index(self, base_node, key_node):
        """Genere le code de l'indexation generique postfixe `x[cle]` a la
        syntaxe Python (0.0.13, voir ExprParser._parse_bracket) :
            l[i]      -> list, index 'number', delegue a l'opcode etendu
                         REX-SL `get <liste> <type> <dest> <idx>;`
            d["cle"]  -> dict, cle 'str', meme opcode `get` (forme dict)
            s[i]      -> str, sucre pratique pour charat(s, i)
        Le TYPE de l'element/de la valeur doit etre CONNU A LA COMPILATION
        (liste/dict homogene, cf. Emitter.elem_types/dict_value_types,
        alimente par REX_CollectionLiteral.compile et REX_CallStatement
        pour 'append') : REX-SL n'a pas de type dynamique a l'execution,
        l'opcode `get` etendu a besoin d'un type hint explicite pour
        auto-declarer correctement le temporaire destination.
        """
        ref, vtype = self.generate(base_node)

        if vtype in ("list", "tuple", "set"):
            idx_ref, idx_type = self.generate(key_node)
            if idx_type != "number":
                raise RexResolveError("l'index d'une liste ('l[i]') doit etre un 'number'")
            elem_type = self.emitter.get_elem_type(ref)
            if elem_type is None:
                raise RexResolveError(
                    "indexation 'l[i]' impossible : type d'element inconnu ou "
                    "heterogene (la liste doit contenir des elements d'un seul "
                    "type number/float/str/bool, tous connus a la compilation)"
                )
            temp = self.emitter.new_temp_name()
            self.emitter.emit(f"get {ref} {elem_type} {temp} {idx_ref};")
            self.emitter.types[temp] = elem_type
            return temp, elem_type

        if vtype == "dict":
            key_ref, key_type = self.generate(key_node)
            if key_type != "str":
                raise RexResolveError('la cle d\'un dict ("d[\\"cle\\"]") doit etre une \'str\'')
            value_type = self.emitter.get_dict_value_type(ref)
            if value_type is None:
                raise RexResolveError(
                    "indexation 'd[\"cle\"]' impossible : type de valeur inconnu "
                    "ou heterogene (le dict doit avoir des valeurs d'un seul "
                    "type number/float/str/bool, toutes connues a la compilation)"
                )
            temp = self.emitter.new_temp_name()
            self.emitter.emit(f"get {ref} {value_type} {temp} {key_ref};")
            self.emitter.types[temp] = value_type
            return temp, value_type

        if vtype == "str":
            idx_ref, idx_type = self.generate(key_node)
            if idx_type != "number":
                raise RexResolveError("l'index d'une chaine ('s[i]') doit etre un 'number'")
            temp = self.emitter.new_temp_name()
            self.emitter.emit(f"charat {temp} {ref} {idx_ref};")
            self.emitter.types[temp] = "str"
            return temp, "str"

        raise RexResolveError(
            f"'[...]' (indexation) non supporte sur le type '{vtype}' "
            "(attendu : list/dict/str)"
        )

    def _convert(self, ref, from_type, to_type):
        """Convertit un operande deja evalue (`ref`, type `from_type`) vers
        `to_type`, pour les builtins str()/int()/float() - s'appuie sur
        to_str() pour '-> str', et sur l'opcode REX-SL 'change' (en place
        sur une COPIE temporaire, jamais sur `ref` lui-meme si c'est une
        variable utilisateur) pour les autres conversions."""
        if from_type == to_type:
            return ref
        if to_type == "str":
            return self.to_str(ref, from_type)
        if from_type == "number" and to_type == "float":
            temp = self.emitter.new_temp_name()
            self.emitter.emit(f"add {temp} {ref} 0.0;")
            self.emitter.types[temp] = "float"
            return temp
        if from_type in ("number", "float", "str") and to_type in ("number", "float"):
            temp, _ = self._copy_into_temp(ref, from_type)
            self.emitter.emit(f"change {temp} {to_type};")
            self.emitter.types[temp] = to_type
            return temp
        raise RexResolveError(
            f"conversion non supportee : '{from_type}' -> '{to_type}' "
            "(limitation REX-SL : number/float/str uniquement)"
        )

    def _call(self, name, arg_specs):
        """Compile un appel `nom(a, b, ...)` utilise DANS une expression
        vers REX-SL : soit une fonction native (0.0.12, voir BUILTIN_ARITY/
        _call_builtin - prioritaire, comme les builtins Python), soit
        `exec nom a b pname=c ...;` (une vraie fonction C, declaree au
        prealable par un bloc `func`), puis rapatrie immediatement `RX_ret`
        dans un temporaire dedie - indispensable car `RX_ret` est un
        registre global unique, qui serait ecrase par tout appel imbrique
        suivant avant d'etre lu.

        `arg_specs` est la liste ("pos", node) / ("kwarg", pname, node)
        produite par ExprParser._parse_call_args : la resolution complete
        des arguments (ordre positionnel/nomme, valeurs par defaut
        manquantes, verification de type parametre par parametre) est
        entierement deleguee a REX-SL (REX_SL_CODE.exec_call), deja
        capable de tout ceci nativement - aucune duplication ici.

        list/dict en type de RETOUR (0.0.13, parametres OK - simples
        pointeurs RexList*/RexDict* passes tels quels) reste hors de
        portee d'une expression : REX-SL n'offre aucune primitive de copie
        de collection, la seule valeur de retour recuperable ici est donc
        number/float/str/bool (cf. _copy_into_temp).

        0.0.14 : RX_ret est un registre C GLOBAL UNIQUE et MONOTYPE pour
        toute la duree du programme genere (fige par le premier `exec`
        rencontre qui retourne une valeur, cf. REX-SL.py REX_SL_CODE.
        exec_call / symbol_table["rx_ret_type"]) - un second appel, plus
        loin dans l'expression ou le programme, vers une fonction dont le
        type de retour DIFFERE de celui deja fige faisait donc planter la
        compilation REX-SL avec "RX_ret est deja de type ... cette
        fonction retourne ...", meme si chaque fonction est parfaitement
        valide individuellement. Emitter.rx_ret_type (miroir cote REX.py
        de ce meme suivi) permet de detecter ce conflit AVANT d'emettre
        `exec` : dans ce cas, on bascule sur _call_via_scrc, qui appelle
        FUNC_<name> directement en C (via `scrc`, injection brute deja
        exposee par REX-SL) dans un temporaire REX-SL frais et dedie,
        sans jamais toucher RX_ret."""
        if name in self.BUILTIN_ARITY:
            return self._call_builtin(name, arg_specs)
        info = self.emitter.functions.get(name)
        if info is None:
            raise RexResolveError(
                f"fonction inconnue : {name} (declarez-la avec 'func {name}(...):' avant de l'appeler)"
            )
        _param_types, _param_names, _defaults, return_type, _elem_type, _dict_value_type = info

        # Patch de signature pour les parametres non-annotes (type infere "number").
        # Au premier appel, on determine le type reel de chaque argument non-annote
        # et on patche la ligne `func ...` deja emise dans emitter.lines.
        # Apres le premier patch, l'entree dans pending_func_sigs est supprimee
        # pour que les appels suivants utilisent directement la signature patchee.
        pending = self.emitter.pending_func_sigs.get(name)
        if pending is not None:
            self._patch_untyped_func_sig(name, pending, arg_specs)
        else:
            # Signature deja stabilisee (ou jamais eu de parametre non-annote) :
            # verifier que cet appel reste coherent avec les types verrouilles.
            self._validate_call_arg_types(name, arg_specs)

        # Injecter les sentinelles bool __has_<x> pour les params = None
        arg_specs = self._inject_none_sentinels(name, arg_specs)

        if return_type is None:
            # 0.1.0 : comportement a la Python - une fonction sans 'return' explicite
            # "retourne" implicitement None. On execute quand meme l'appel (effets de
            # bord), sans jamais lire RX_ret (jamais ecrit par cette fonction).
            arg_str = self._build_exec_args(arg_specs)
            self.emitter.emit(f"exec {name}" + (" " + arg_str if arg_str else "") + ";")
            return NONE_REF, "none"
        # list/dict en retour : desormais supporte (0.0.14) via _copy_into_temp
        # qui assigne le pointeur C RexList*/RexDict* via scrc.

        if self.emitter.rx_ret_type is not None and self.emitter.rx_ret_type != return_type:
            temp_ref, temp_type = self._call_via_scrc(name, arg_specs, _param_names, _defaults, return_type)
            self._propagate_collection_type(temp_ref, return_type, _elem_type, _dict_value_type)
            return temp_ref, temp_type

        arg_str = self._build_exec_args(arg_specs)
        self.emitter.emit(f"exec {name}" + (" " + arg_str if arg_str else "") + ";")
        if self.emitter.rx_ret_type is None:
            self.emitter.rx_ret_type = return_type
        temp_ref, temp_type = self._copy_into_temp("RX_ret", return_type)
        self._propagate_collection_type(temp_ref, return_type, _elem_type, _dict_value_type)
        return temp_ref, temp_type

    def _patch_untyped_func_sig(self, name, pending, arg_specs):
        """Patche la ligne `func <name> ...;` deja emise dans emitter.lines
        pour remplacer le type par defaut "number" des parametres non-annotes
        par le type reel de l'argument fourni au premier appel.

        Appele depuis _call au premier appel d'une fonction dont au moins un
        parametre n'avait pas d'annotation de type explicite.

        Apres le patch, l'entree dans emitter.pending_func_sigs est supprimee
        et emitter.functions est mis a jour pour refleter les nouveaux types."""
        line_idx = pending["line_idx"]
        untyped_positions = pending["untyped_positions"]  # [(pos, pname), ...]
        expanded_params = pending["expanded_params"]
        return_type_func = pending["return_type"]

        # Resoudre les arguments positionnels et nommes pour connaitre leur type.
        # On utilise generate() (sans side effects sur le flux REX-SL, car on
        # inspecte juste le type) — mais generate() emet du code REX-SL.
        # Solution : on ne pre-evalue pas ici ; on reconstruit plutot la
        # signature depuis les types connus dans emitter.types / les litteraux.
        # Astuce : parcourir arg_specs en ordre positionnel pour matcher avec
        # expanded_params, en ignorant les kwargs pour l'instant.
        positional = [s for s in arg_specs if s[0] == "pos"]
        named = {s[1]: s[2] for s in arg_specs if s[0] == "kwarg"}

        # Construire le mapping pos -> type_arg pour les positions non-annotees,
        # via le helper partage _infer_literal_type (voir plus bas) plutot qu'une
        # fonction imbriquee, pour pouvoir reutiliser la meme logique lors de la
        # validation des appels suivants (cf. _validate_call_arg_types).
        untyped_pos_set = {pos for pos, _ in untyped_positions}
        new_types = {}  # pos -> type_reel
        still_unresolved = []  # (pos, pname) dont le type n'a pas pu etre devine cette fois
        for pos, pname in untyped_positions:
            # Chercher l'arg fourni pour ce parametre
            node = None
            if pos < len(positional):
                node = positional[pos][1]
            elif pname in named:
                node = named[pname]
            inferred = self._infer_literal_type(node) if node is not None else None
            if inferred in ("number", "float", "str", "bool"):
                new_types[pos] = inferred
            else:
                still_unresolved.append((pos, pname))

        if not new_types:
            # Impossible de deviner le type a CET appel (ex: argument fourni par
            # une expression non litterale : appel de fonction, index, etc.).
            # On NE supprime PAS le pending : on retente au prochain appel plutot
            # que de figer silencieusement le parametre sur son type par defaut
            # "number" pour le reste du programme, ce qui provoquerait une
            # coercion silencieuse (ex: une string passee ensuite dans un slot
            # reste type "number" -> tronquee/convertie a 0 sans aucune erreur).
            return

        # Reconstruire la ligne `func <name> <sig>;` avec les types patched
        new_expanded = list(expanded_params)
        for pos, new_type in new_types.items():
            entry = new_expanded[pos]
            new_expanded[pos] = (new_type,) + entry[1:]

        sig_parts = []
        for entry in new_expanded:
            vtype, pname2, default_lit = entry[0], entry[1], entry[2]
            piece = f"{vtype} {pname2}"
            if default_lit is not None and default_lit != "__NONE_DEFAULT__":
                piece += f" = {default_lit}"
            sig_parts.append(piece)
        sig = " ".join(sig_parts)
        new_header = f"func {name}" + (f" {sig}" if sig else "")
        if return_type_func is not None:
            new_header += f" -> {return_type_func}"
        self.emitter.lines[line_idx] = new_header + ";"

        # Mettre a jour emitter.functions avec les nouveaux types de parametres
        old_info = self.emitter.functions.get(name)
        if old_info is not None:
            old_ptypes, old_pnames, old_defaults, old_ret, old_elem, old_dval = old_info
            new_ptypes = list(old_ptypes)
            for pos, new_type in new_types.items():
                if pos < len(new_ptypes):
                    new_ptypes[pos] = new_type
            self.emitter.functions[name] = (
                new_ptypes, old_pnames, old_defaults, old_ret, old_elem, old_dval
            )

        # Correction retroactive du corps deja emis.
        # Le corps a ete compile avec l'ancien type (ex: "number") pour les params
        # non-annotes. Si le type reel est different (ex: "str"), les opcodes emis
        # pour convertir via _copy_into_temp + change sont incorrects :
        #   "add __rx_tN param 0;"  suppose param=number, mais param est maintenant str
        #   -> REX-SL leve "operande different : __rx_tN".
        # Fix : scanner le corps et corriger les couples add/change inconciliables.
        body_end = pending.get("body_end_idx")
        if body_end is not None:
            changed_params = {}
            for pos, pname2 in untyped_positions:
                if pos in new_types:
                    old_t = expanded_params[pos][0]
                    new_t = new_types[pos]
                    if old_t != new_t:
                        changed_params[pname2] = (old_t, new_t)

            if changed_params:
                import re as _re2
                lines = self.emitter.lines
                i = line_idx + 1
                while i < body_end:
                    line = lines[i]
                    for pname2, (old_t, new_t) in changed_params.items():
                        if new_t == "str" and old_t in ("number", "float"):
                            zero = "0" if old_t == "number" else "0.0"
                            m = _re2.match(
                                r'^add\s+(__rx_t\d+)\s+'
                                + _re2.escape(pname2)
                                + r'\s+' + _re2.escape(zero) + r'\s*;$',
                                line.strip()
                            )
                            if m:
                                temp_name = m.group(1)
                                # Remplacer la copie number par une copie str
                                lines[i] = line.replace(
                                    f"{pname2} {zero};", f'{pname2} "";'
                                )
                                # Supprimer le "change T str;" qui suit (devenu inutile)
                                if i + 1 < body_end:
                                    if lines[i + 1].strip() == f"change {temp_name} str;":
                                        lines[i + 1] = ""
                                break
                    i += 1

        # Verrouiller les types desormais connus pour ce nom de fonction, afin
        # que les appels suivants (une fois le pending retire) puissent etre
        # valides contre ces types au lieu de laisser passer silencieusement
        # un argument incompatible (cf. _validate_call_arg_types).
        if not hasattr(self.emitter, "locked_param_types"):
            self.emitter.locked_param_types = {}
        locked = self.emitter.locked_param_types.setdefault(name, {})
        locked.update(new_types)

        if still_unresolved:
            # Certaines positions restent non-annotees ET non-devinables a cet
            # appel (ex: argument = expression non litterale) : on retente aux
            # appels suivants au lieu d'abandonner definitivement.
            pending["untyped_positions"] = still_unresolved
        else:
            # Toutes les positions non-annotees sont maintenant resolues :
            # plus besoin de retenter, mais on garde locked_param_types pour
            # la validation des appels suivants.
            del self.emitter.pending_func_sigs[name]

    def _infer_literal_type(self, node):
        """Infere le type REX d'un noeud AST d'argument sans l'evaluer (pas
        d'emission de code). Utilise a la fois par _patch_untyped_func_sig
        (devine le type reel d'un parametre non-annote au premier appel
        exploitable) et par _validate_call_arg_types (verifie qu'un appel
        ulterieur ne fournit pas un type incompatible avec celui deja
        verrouille). Retourne None si le type ne peut pas etre devine sans
        evaluer l'expression (appel de fonction, indexation, etc.)."""
        if node is None:
            return None
        kind = node[0]
        if kind == "lit":
            val = node[1]
            if isinstance(val, bool):
                return "bool"
            if isinstance(val, int):
                return "number"
            if isinstance(val, float):
                return "float"
            if isinstance(val, str):
                return "str"
        if kind == "var":
            return self.emitter.types.get(node[1])
        if kind == "fstr":
            return "str"
        if kind == "binop":
            lt = self._infer_literal_type(node[2])
            rt = self._infer_literal_type(node[3])
            if lt == "str" or rt == "str":
                return "str"
            if lt == "float" or rt == "float":
                return "float"
            return lt
        return None

    def _validate_call_arg_types(self, name, arg_specs):
        """Pour une fonction dont au moins un parametre non-annote a deja ete
        verrouille sur un type reel (cf. emitter.locked_param_types, rempli
        par _patch_untyped_func_sig), verifie que CET appel ne fournit pas,
        pour ces positions, un argument dont le type est identifiable et
        DIFFERENT du type verrouille. Sans ce garde-fou, un appel ulterieur
        avec un type different du premier appel (ex: str alors que le
        premier appel avait fige le parametre sur "number") passait
        silencieusement, produisant du code C incorrect (ex: une string
        copiee dans une variable C 'number' -> valeur affichee "0" au lieu
        de la string attendue), sans le moindre message d'erreur."""
        locked = getattr(self.emitter, "locked_param_types", {}).get(name)
        if not locked:
            return
        info = self.emitter.functions.get(name)
        if info is None:
            return
        param_names = info[1]
        positional = [s for s in arg_specs if s[0] == "pos"]
        named = {s[1]: s[2] for s in arg_specs if s[0] == "kwarg"}
        for pos, expected_type in locked.items():
            node = None
            if pos < len(positional):
                node = positional[pos][1]
            elif pos < len(param_names) and param_names[pos] in named:
                node = named[param_names[pos]]
            if node is None:
                continue
            inferred = self._infer_literal_type(node)
            if inferred is not None and inferred != expected_type:
                pname = param_names[pos] if pos < len(param_names) else f"#{pos}"
                raise RexResolveError(
                    f"appel de '{name}' : le parametre '{pname}' (non-annote) a ete "
                    f"type '{expected_type}' d'apres un appel precedent, mais cet "
                    f"appel fournit un argument de type '{inferred}' - types "
                    "incompatibles pour un parametre sans annotation explicite "
                    f"(ajoutez une annotation de type a '{pname}' dans la "
                    "declaration de la fonction pour lever l'ambiguite)"
                )

    def _call_via_scrc(self, name, arg_specs, param_names, defaults, return_type):
        """Contournement du conflit de type sur RX_ret (voir _call) : appelle
        FUNC_<name> directement en C via `scrc "SL_temp = FUNC_name(args);"`
        plutot que par `exec` (qui ecrirait dans RX_ret, deja fige sur un
        autre type). Les arguments sont resolus nous-memes (positionnel/
        nomme + valeurs par defaut manquantes) exactement comme le ferait
        REX-SL.py REX_SL_CODE.exec_call, puisque REX-SL n'intervient plus
        du tout sur cet appel - puis convertis en expressions C : un
        argument LITTERAL est injecte directement (deja au format C, memes
        regles de guillemets que REX-SL/REX.py), toute autre expression
        (variable, temporaire, sous-calcul...) est d'abord evaluee
        normalement (self.generate, emet le REX-SL necessaire) puis
        referencee sous son nom C reel `SL_<nom>` (memes conventions que
        REX_IndexAssignStatement : une variable jamais passee par `change`
        garde toujours ce prefixe cote C).

        Le resultat est ecrit dans un temporaire REX-SL FRAIS (jamais
        RX_ret), declare au prealable via `var` (declare_literal) pour que
        REX-SL emette bien sa declaration C `SL_<temp>` - le `scrc` ne fait
        alors qu'assigner cette variable deja declaree.

        Cas 'str' : contrairement a RX_ret (initialise via rexsl_str_alloc,
        donc toujours heap), un temporaire frais UNIQUEMENT declare puis
        ecrit ici (jamais reassigne cote REX-SL) est detecte "assigne une
        seule fois" par REX-SL.py (voir symbol_table["const_vars"], passe
        d'auto-const en fin de compilation) et devient un simple `const
        char* ... = "";` (litteral, PAS heap) - lui appliquer `free()`
        avant l'ecraser (comme le fait exec_call pour RX_ret) ferait
        planter le programme genere (free() sur un pointeur non alloue).
        On se contente donc ici d'ecraser directement le pointeur, sans
        `free()` prealable."""
        c_args = self._build_c_call_args(arg_specs, param_names, defaults)
        call_expr = f"FUNC_{name}({', '.join(c_args)})"

        temp = self.emitter.new_temp_name()
        if return_type in ("list", "tuple", "set", "dict"):
            # Collection : declare via 'var list/dict' (rexsl_list_new/dict_new),
            # puis libere l'objet initial et reassigne le pointeur de retour
            # pour eviter le double-free (meme technique que _copy_into_temp).
            emit_type = "dict" if return_type == "dict" else "list"
            self.emitter.declare_literal(temp, emit_type)
            self.emitter.types[temp] = return_type
            temp_c = f"SL_{temp}"
            free_fn = "rexsl_list_free" if emit_type == "list" else "rexsl_dict_free"
            code = (
                f"if ({temp_c}) {{ {free_fn}({temp_c}); }} "
                f"{temp_c} = {call_expr};"
            )
        else:
            self.emitter.declare_literal(temp, return_type, DEFAULT_VALUES[return_type])
            temp_c = f"SL_{temp}"
            code = f"{temp_c} = {call_expr};"
        escaped = code.replace("\\", "\\\\").replace('"', '\\"')
        self.emitter.emit(f'scrc "{escaped}";')
        return temp, return_type

    def _build_c_call_args(self, arg_specs, param_names, defaults):
        """Resout `arg_specs` (positionnel/nomme, comme REX_SL_CODE.exec_call
        cote REX-SL) puis construit, DANS L'ORDRE DES PARAMETRES, la liste
        des expressions C correspondantes : litteral -> directement (deja
        au format C) ; variable/temporaire/sous-expression -> nom C reel
        `SL_<name>` (apres evaluation via self.generate, qui emet au
        besoin le REX-SL necessaire pour la calculer)."""
        positional = [spec for spec in arg_specs if spec[0] == "pos"]
        named = {}
        for spec in arg_specs:
            if spec[0] != "kwarg":
                continue
            _, pname, node = spec
            if pname not in param_names:
                raise RexResolveError(f"parametre nomme inconnu : {pname}")
            if pname in named:
                raise RexResolveError(f"argument nomme fourni plusieurs fois : {pname}")
            named[pname] = node

        if len(positional) > len(param_names):
            raise RexResolveError(
                f"trop d'arguments positionnels ({len(positional)} recus, "
                f"{len(param_names)} parametre(s))"
            )

        resolved = [None] * len(param_names)
        used = [False] * len(param_names)
        for idx, spec in enumerate(positional):
            resolved[idx] = spec[1]
            used[idx] = True
        for pname, node in named.items():
            idx = param_names.index(pname)
            if used[idx]:
                raise RexResolveError(
                    f"argument '{pname}' fourni a la fois positionnellement et par nom"
                )
            resolved[idx] = node
            used[idx] = True

        c_args = []
        for idx, pname in enumerate(param_names):
            node = resolved[idx]
            if node is None:
                if pname not in defaults:
                    raise RexResolveError(
                        f"argument manquant sans valeur par defaut : {pname}"
                    )
                c_args.append(defaults[pname])
                continue
            ref, vtype_arg = self.generate(node)
            if vtype_arg == "none":
                raise RexResolveError(f"argument '{pname}' : 'None' non supporte comme argument")
            if node[0] == "lit":
                c_args.append(ref)
            else:
                c_args.append(f"SL_{ref}")
        return c_args

    def _inject_none_sentinels(self, func_name, arg_specs):
        """Pour les fonctions ayant des parametres = None, transforme les
        arg_specs utilisateur (qui ne connaissent que les params visibles) en
        injectant les sentinelles bool __has_<x> au bon endroit.

        Exemple : func hello(number arg = None) -> signature REX-SL :
          bool __has_arg = false, number arg = 0
        Appel hello("e") avec arg_specs=[("pos", node_"e")] devient :
          [("pos", node_true), ("pos", node_"e")]
        Appel hello() reste vide -> REX-SL utilise les defaults (false, 0).
        """
        sentinel_map = getattr(self.emitter, "none_sentinel_map", {})
        sentinels = sentinel_map.get(func_name)
        if not sentinels:
            return arg_specs

        # Construire un mapping: real_param_name -> sentinel_name
        real_to_sentinel = {real: sent for sent, real in sentinels}
        # Noms visibles des parametres (sans sentinelles)
        all_param_names = self.emitter.functions[func_name][1]  # param_names complets
        # Noms "utilisateur" = tous les params sauf les sentinelles
        user_param_names = [p for p in all_param_names if not p.startswith("__has_")]

        # Separer les args positionnels et nommes
        positional = [s for s in arg_specs if s[0] == "pos"]
        named = {s[1]: s for s in arg_specs if s[0] == "kwarg"}

        # Construire le mapping complet utilisateur arg -> valeur fournie
        user_provided = {}
        for i, pos_spec in enumerate(positional):
            if i < len(user_param_names):
                user_provided[user_param_names[i]] = pos_spec
        user_provided.update({pname: spec for pname, spec in named.items()})

        # Reconstruire arg_specs dans l'ordre REX-SL (sentinel + real)
        new_specs = []
        for sent_name, real_name in sentinels:
            if real_name in user_provided:
                # Arg fourni -> sentinelle = true
                true_node = ("lit", True)
                new_specs.append(("kwarg", sent_name, true_node))
                spec = user_provided[real_name]
                if spec[0] == "pos":
                    new_specs.append(("kwarg", real_name, spec[1]))
                else:
                    new_specs.append(spec)
            # Si non fourni : REX-SL utilise les defaults (false, zero)

        # Ajouter les args pour les params normaux (sans sentinelle)
        normal_param_names = set(user_param_names) - set(real for _, real in sentinels)
        for pname in all_param_names:
            if pname.startswith("__has_"):
                continue
            if pname not in real_to_sentinel:
                # Parametre normal (sans sentinelle)
                if pname in user_provided:
                    spec = user_provided[pname]
                    if spec[0] == "pos":
                        new_specs.append(("kwarg", pname, spec[1]))
                    else:
                        new_specs.append(spec)
        return new_specs

    def _build_exec_args(self, arg_specs):
        pieces = []
        for spec in arg_specs:
            if spec[0] == "kwarg":
                _, pname, node = spec
                ref, vtype = self.generate(node)
                if vtype == "none":
                    raise RexResolveError(f"argument '{pname}' : 'None' non supporte comme argument")
                pieces.append(f"{pname}={ref}")
            else:
                _, node = spec
                ref, vtype = self.generate(node)
                if vtype == "none":
                    raise RexResolveError("'None' non supporte comme argument de fonction")
                pieces.append(ref)
        return " ".join(pieces)

    def _propagate_collection_type(self, temp_ref, return_type, elem_type, dict_value_type):
        """Propage le type d'element/de valeur connu d'une fonction retournant
        une list/dict vers le temporaire qui en porte le resultat, pour que les
        indexations ulterieures sur ce temporaire (, ) soient
        compilables sans information supplementaire."""
        if return_type in ("list", "tuple", "set") and elem_type is not None:
            self.emitter.note_elem_type(temp_ref, elem_type)
        elif return_type == "dict" and dict_value_type is not None:
            self.emitter.note_dict_value_type(temp_ref, dict_value_type)

    def _copy_into_temp(self, src_ref, vtype):
        """Copie `src_ref` (deja evalue, de type `vtype`) dans un nouveau
        temporaire, via l'opcode d'identite habituel (add .. 0/0.0/"") pour les
        scalaires, ou via un scrc d'assignation directe de pointeur pour les
        collections list/dict (0.0.14 : RX_ret est un RexList*/RexDict* qui peut
        etre passe directement sans copie profonde - on cree simplement un alias
        vers le meme objet C, ce qui est suffisant pour une lecture en expression)."""
        temp = self.emitter.new_temp_name()
        if vtype == "number":
            self.emitter.emit(f"add {temp} {src_ref} 0;")
        elif vtype == "float":
            self.emitter.emit(f"add {temp} {src_ref} 0.0;")
        elif vtype == "str":
            self.emitter.emit(f'add {temp} {src_ref} "";')
        elif vtype in ("list", "tuple", "set", "dict"):
            # list/dict : on declare le temporaire via 'var list/dict' (ce qui
            # emet rexsl_list_new()/rexsl_dict_new() et enregistre la variable
            # dans collection_vars pour les free() automatiques de REX-SL), puis
            # on reassigne le pointeur via scrc en liberant l'objet initial alloue
            # et en mettant la source a NULL pour eviter un double-free ulterieur.
            # Si src est RX_ret : RX_ret = NULL empeche le free implicite par le
            # code final de main() genere par REX-SL.
            emit_type = "dict" if vtype == "dict" else "list"
            self.emitter.declare_literal(temp, emit_type)
            self.emitter.types[temp] = vtype
            dest_c = f"SL_{temp}"
            free_fn = "rexsl_list_free" if emit_type == "list" else "rexsl_dict_free"
            if src_ref == "RX_ret":
                code = (
                    f"if ({dest_c}) {{ {free_fn}({dest_c}); }} "
                    f"{dest_c} = RX_ret; RX_ret = NULL;"
                )
            else:
                src_c = f"SL_{src_ref}"
                code = (
                    f"if ({dest_c}) {{ {free_fn}({dest_c}); }} "
                    f"{dest_c} = {src_c}; {src_c} = NULL;"
                )
            escaped = code.replace("\\", "\\\\").replace('"', '\\"')
            self.emitter.emit(f'scrc "{escaped}";')
            return temp, vtype
        else:
            raise RexResolveError(
                f"impossible de recuperer une valeur de retour de type '{vtype}' "
                "dans une expression (limitation REX-SL actuelle)"
            )
        self.emitter.types[temp] = vtype
        return temp, vtype

    # -- f-strings / conversion generique vers 'str' (0.0.11) ---------------

    # -- format specs supportes par _fstring (0.0.14) ------------------------
    # Formes Python acceptees -> format printf C :
    #   [<|>] [0] [largeur] [.precision] conv
    # conv : d (integer, number/float), f/e/g (flottant, number/float),
    #         s (chaine, str). Remplissage personnalise non supporte.
    _FMT_SPEC_RE = re.compile(
        r'^(?P<align>[<>^])?(?P<zero>0)?(?P<width>\d*)(?:\.(?P<prec>\d+))?(?P<conv>[dfseg])$'
    )
    # largeur du buffer snprintf pour les formats avec spec
    _FMT_BUF_SIZE = 128

    def _apply_fmt_spec(self, ref, vtype, spec):
        """Convertit `ref` (de type `vtype`) en `str` en appliquant la spec
        de format `spec` (chaine brute apres le ':' dans `{expr:spec}`).
        Retourne (temp_str_ref, "str") ou leve RexResolveError si la spec
        est invalide ou incompatible avec le type.
        Compile via un `scrc` injectant un snprintf C, sans modifier REX-SL.
        """
        m = ExprCodegen._FMT_SPEC_RE.match(spec.strip())
        if m is None:
            raise RexResolveError(
                f"f-string : spec de format '{spec}' non reconnue "
                "(formes supportees : d, f, g, s, .Nf, .Nd, Wd, Wf, Ws, 0Wd, </>/<)"
            )
        align  = m.group("align") or ""
        zero   = m.group("zero") or ""
        width  = m.group("width") or ""
        prec   = m.group("prec")
        conv   = m.group("conv")

        # Validation type REX <-> type de format
        if conv == "d":
            if vtype not in ("number", "float"):
                raise RexResolveError(
                    f"f-string ':{spec}' : format entier 'd' incompatible "
                    f"avec le type '{vtype}' (attendu number ou float)"
                )
            c_fmt_conv = "d"
        elif conv in ("f", "e", "g"):
            if vtype not in ("number", "float"):
                raise RexResolveError(
                    f"f-string ':{spec}' : format flottant '{conv}' incompatible "
                    f"avec le type '{vtype}' (attendu number ou float)"
                )
            c_fmt_conv = conv
        elif conv == "s":
            if vtype != "str":
                raise RexResolveError(
                    f"f-string ':{spec}' : format chaine 's' incompatible "
                    f"avec le type '{vtype}' (attendu str)"
                )
            c_fmt_conv = "s"
        else:
            raise RexResolveError(
                f"f-string : type de format '{conv}' non supporte"
            )

        # Construction du format C a la printf
        # Alignement : Python < -> -, > -> (rien ou 0), ^ non supporte
        if align == "^":
            raise RexResolveError(
                f"f-string ':{spec}' : alignement centre '^' non supporte "
                "(utilisez < pour gauche, > pour droite)"
            )
        c_flags = ""
        if align == "<":
            c_flags += "-"
        if zero and not align:
            c_flags += "0"

        c_fmt = "%" + c_flags + width
        if prec is not None:
            c_fmt += "." + prec
        c_fmt += c_fmt_conv

        # Le nom C de la variable source : les temporaires REX ont le
        # prefixe __rx_ -> nom C = SL___rx_t<N> ; les variables utilisateur
        # -> SL_<name>. Le nom REX-SL est identique au nom REX (depuis 0.0.23).
        emitter = self.emitter
        rexsl_ref = ref
        c_src = f"SL_{rexsl_ref}"

        # Pour float/double : cast explicite si type REX est number (int C)
        if conv in ("f", "e", "g", "d") and vtype == "number":
            c_src = f"(double)({c_src})" if conv in ("f", "e", "g") else c_src
        elif conv in ("f", "e", "g") and vtype == "float":
            c_src = f"(double)({c_src})"

        tmp = emitter.new_temp_name()
        buf_size = ExprCodegen._FMT_BUF_SIZE
        # On doit declarer le temporaire avant le scrc (pour que REX-SL le
        # connaisse comme variable str) puis le remplir via scrc+snprintf.
        emitter.declare_literal(tmp, "str", '""'  )
        rexsl_tmp = tmp
        c_dst = f"SL_{rexsl_tmp}"
        # Le scrc fait : alloue un buffer sur la pile, snprintf dedans,
        # puis reassigne SL_<tmp> (qui est un char* heap) via strdup.
        # On libere l'ancien contenu avant (SL_<tmp> a ete initialise a
        # strdup("") par var str -> il est sur le heap).
        escaped_fmt = c_fmt.replace('"', '\\"')
        c_code = (
            f'{{ char __rx_fmtbuf[{buf_size}]; '
            f'snprintf(__rx_fmtbuf, {buf_size}, "{escaped_fmt}", {c_src}); '
            f'free({c_dst}); {c_dst} = strdup(__rx_fmtbuf); }}'
        )
        escaped_c = c_code.replace("\\", "\\\\").replace('"', '\\\"'  )
        emitter.emit(f'scrc "{escaped_c}";'  )
        emitter.types[tmp] = "str"
        return tmp, "str"

    def _fstring(self, parts):
        """Genere la concatenation `str` correspondant aux `parts` d'une
        f-string (voir REX_Lexer._scan_fstring) : chaque morceau litteral
        devient un litteral `str` REX-SL, chaque `{expr}` est evalue puis
        converti en texte via `to_str` (sans spec) ou `_apply_fmt_spec`
        (avec spec `{expr:spec}`), le tout concatene via `add`.

        0.0.14 : support de `{expr:spec}` via le tuple ("tokens_fmt",
        sub_tokens, spec_str) produit par REX_Lexer._scan_fstring."""
        if not parts:
            return self._literal("")
        pieces = []
        for part in parts:
            kind = part[0]
            if kind == "str":
                pieces.append(self._literal(part[1]))
            elif kind == "tokens":
                expr_node = ExprParser(part[1]).parse()
                pieces.append((self.to_str_for_value_node(expr_node), "str"))
            elif kind == "tokens_fmt":
                _, sub_tokens, spec = part
                expr_node = ExprParser(sub_tokens).parse()
                ref, vtype = self.generate(expr_node)
                pieces.append(self._apply_fmt_spec(ref, vtype, spec))
            else:
                raise RexResolveError(f"f-string : type de morceau inconnu : {kind!r}")

        result_ref, _ = pieces[0]
        for nxt_ref, _ in pieces[1:]:
            temp = self.emitter.new_temp_name()
            self.emitter.emit(f"add {temp} {result_ref} {nxt_ref};")
            self.emitter.types[temp] = "str"
            result_ref = temp
        return result_ref, "str"

    def to_str(self, ref, vtype):
        """Convertit un operande deja evalue (`ref`, de type `vtype`) en
        texte (`str`), utilisable dans une concatenation - utilise par les
        f-strings ainsi que par `show(...)` (qui doit desormais accepter
        n'importe quelle combinaison de types, comme `print()`)."""
        if vtype == "none":
            return self._quote("None")
        if vtype == "str":
            return ref
        if vtype in ("number", "float"):
            temp, _ = self._copy_into_temp(ref, vtype)
            self.emitter.emit(f"change {temp} str;")
            self.emitter.types[temp] = "str"
            return temp
        if vtype == "bool":
            return self._bool_to_str(ref)
        if vtype in ("list", "tuple", "set", "dict"):
            # Depuis REX-SL 0.0.23 : show_list/show_dict/show_set/show_tuple
            # serialisent directement la collection vers stdout.
            # Pour to_str() (conversion en str pour concatenation f-string etc.),
            # on passe encore par list_str/dict_str qui retournent une str.
            temp = self.emitter.new_temp_name()
            instr = "dict_str" if vtype == "dict" else "list_str"
            self.emitter.emit(f"{instr} {temp} {ref};")
            self.emitter.types[temp] = "str"
            return temp
        raise RexResolveError(
            f"impossible de convertir une valeur de type '{vtype}' en texte "
            "(limitation REX-SL : number/float/str/bool uniquement)"
        )

    def _bool_to_str(self, ref):
        """Convertit un operande `bool` (`ref`, litteral ou variable) en
        `str` ("true"/"false"). L'opcode REX-SL `change` modifie la
        variable EN PLACE (meme nom) : on ne peut donc pas l'appliquer
        directement sur `ref` s'il s'agit d'une variable utilisateur (on
        la detruirait). On passe donc par un petit branchement cdn/go qui
        ecrit le litteral texte correspondant dans un temporaire `str`
        dedie, sans jamais toucher a `ref`."""
        emitter = self.emitter
        loop_id = emitter.new_loop_id()
        temp = emitter.new_temp_name()
        true_lbl = f"__rx_b2s{loop_id}_true"
        end_lbl = f"__rx_b2s{loop_id}_end"

        emitter.declare_literal(temp, "str", '""')
        emitter.emit(f"cdn equal {ref} true;")
        emitter.emit(f"go {true_lbl};")
        emitter.emit(f'{temp} "false";')
        emitter.emit("cdn on;")
        emitter.emit(f"go {end_lbl};")
        emitter.emit(f"lbl {true_lbl};")
        emitter.emit(f'{temp} "true";')
        emitter.emit(f"lbl {end_lbl};")
        return temp




# =============================================================================
# LITTERAUX DE COLLECTION : REX_CollectionLiteral + REX_FileReadExpr
# =============================================================================

class REX_CollectionLiteral:
    """Reconnait et compile les litteraux de collection a la syntaxe
    Python rencontres comme valeur d'un `var` :

        var l = [1, 2, 3]          -> list
        var t = (1, 2, 3)          -> tuple (t = (1,) pour un singleton)
        var s = {1, 2, 3}          -> set
        var d = {"a": 1, "b": 2}   -> dict

    REX-SL ne connait nativement que `list` et `dict` (voir REX-SL.py) :
    `tuple` et `set` sont donc representes EN INTERNE comme une `list`
    REX-SL (`var list ...;` + `append ...;`), la distinction `tuple`/`set`
    n'existant qu'au niveau REX (type suivi dans Emitter.types, utile pour
    des messages d'erreur coherents). Un `set` litteral est deduplique a
    la compilation pour ses elements litteraux (nombres/chaines/bool).
    """

    @staticmethod
    def detect(expr_tokens, explicit_type):
        """Retourne (kind, payload) si `expr_tokens` est un litteral de
        collection reconnu ('list'/'tuple'/'set'/'dict'), sinon None
        (auquel cas l'appelant retombe sur le parseur d'expression
        classique)."""
        if len(expr_tokens) != 1:
            return None
        tok = expr_tokens[0]

        if isinstance(tok, Group) and tok.kind == "[]":
            return "list", REX_CollectionLiteral._split_on_commas(tok.items)

        if isinstance(tok, Group) and tok.kind == "{}":
            items = tok.items
            if not items:
                return ("set" if explicit_type == "set" else "dict"), []
            has_colon = any(
                isinstance(t, Token) and t.type == "PUNCT" and t.value == ":"
                for t in items
            )
            if has_colon:
                return "dict", REX_CollectionLiteral._split_dict_pairs(items)
            return "set", REX_CollectionLiteral._split_on_commas(items)

        # `(...)` : deja represente comme une sous-liste "nue" par le lexer.
        if isinstance(tok, list):
            inner = tok
            if not inner:
                return "tuple", []  # `()`
            trailing_comma = (
                isinstance(inner[-1], Token)
                and inner[-1].type == "PUNCT"
                and inner[-1].value == ","
            )
            groups = REX_CollectionLiteral._split_on_commas(inner)
            if len(groups) > 1 or (len(groups) == 1 and trailing_comma):
                return "tuple", groups  # tuple (y compris singleton `(x,)`)
            return None  # simple parenthesage de priorite : pas une collection

        return None

    @staticmethod
    def compile(name, kind, payload, emitter, explicit=False):
        """Emet le code REX-SL pour un litteral de collection.

        `explicit` : True si le type a ete annote explicitement par l'utilisateur
        (ex: `var list l = [1,2,3]`). False si le type est infere (ex: `var l = [1,2,3]`
        ou une reaffectation `s = {1,2,3}` depuis un type different).

        Si `name` est DEJA dans emitter.types (reaffectation depuis un type
        different), on appelle d'abord retype_as_collection() pour vider
        l'ancienne entree, puis on emet une nouvelle declaration `var`."""
        already_declared = name in emitter.types
        if already_declared:
            # Retypage : autorise uniquement si l'ancien type n'etait pas explicite.
            emitter.retype_as_collection(name, kind)
            # Apres retype_as_collection, name n'est plus dans emitter.types :
            # declare_literal peut etre appele normalement ci-dessous.

        if kind == "dict":
            emitter.declare_literal(name, "dict", explicit=explicit)
            codegen = ExprCodegen(emitter)
            display_pairs = []
            all_literal = True
            for key_tokens, val_tokens in payload:
                key_node = ExprParser(key_tokens).parse()
                if key_node[0] != "lit" or not isinstance(key_node[1], str):
                    raise RexResolveError(
                        "les cles de dictionnaire doivent etre des chaines de caracteres "
                        "litterales (limitation REX-SL : 'set <dict> <cle> <val>;' exige "
                        "une cle string)"
                    )
                key_ref, _ = codegen._literal(key_node[1])
                val_node = ExprParser(val_tokens).parse()
                val_ref, val_type = codegen.generate(val_node)
                emitter.emit(f"set {name} {key_ref} {val_ref};")
                emitter.note_dict_value_type(name, val_type)
                if val_node[0] == "lit":
                    display_pairs.append((key_node[1], val_node[1]))
                else:
                    all_literal = False
            emitter.types[name] = "dict"
            if all_literal:
                emitter.collection_repr[name] = REX_CollectionLiteral._format_dict_repr(display_pairs)
            return

        # list / tuple / set -> tous representes comme une 'list' REX-SL.
        emitter.declare_literal(name, "list", explicit=explicit)
        codegen = ExprCodegen(emitter)
        seen_literals = set()
        display_values = []
        all_literal = True
        for elem_tokens in payload:
            if not elem_tokens:
                raise RexResolveError("element de collection vide")
            node = ExprParser(elem_tokens).parse()
            if kind == "set" and node[0] == "lit":
                if node[1] in seen_literals:
                    continue  # deduplication a la compilation (set litteral)
                seen_literals.add(node[1])
            ref, vtype = codegen.generate(node)
            if vtype not in ("number", "float", "str", "bool"):
                raise RexResolveError(
                    f"element de type '{vtype}' non supporte dans une collection "
                    "(limitation REX-SL : 'append' n'accepte que number/float/str/bool)"
                )
            emitter.emit(f"append {name} {ref};")
            emitter.note_elem_type(name, vtype)
            if node[0] == "lit":
                display_values.append(node[1])
            else:
                all_literal = False
        emitter.types[name] = kind
        if all_literal:
            emitter.collection_repr[name] = REX_CollectionLiteral._format_repr(kind, display_values)

    @staticmethod
    def _py_repr(value):
        """Rendu textuel a la Python d'un litteral REX (bool -> True/False,
        str -> entoure de quotes comme repr() Python, number/float -> tel
        quel) - utilise UNIQUEMENT pour l'affichage figé de show() sur une
        collection connue a la compilation (cf. Emitter.collection_repr)."""
        if isinstance(value, bool):
            return "true" if value else "false"
        return repr(value)

    @staticmethod
    def _format_repr(kind, values):
        """Formate `values` (elements deja dedupliques pour un 'set') a la
        syntaxe Python : [..] pour list, (..)/(x,)/() pour tuple, {..}
        pour set."""
        rendered = [REX_CollectionLiteral._py_repr(v) for v in values]
        if kind == "list":
            return "[" + ", ".join(rendered) + "]"
        if kind == "set":
            return "{" + ", ".join(rendered) + "}" if rendered else "set()"
        # tuple
        if not rendered:
            return "()"
        if len(rendered) == 1:
            return f"({rendered[0]},)"
        return "(" + ", ".join(rendered) + ")"

    @staticmethod
    def _format_dict_repr(pairs):
        """Formate une liste de (cle_str, valeur) a la syntaxe Python
        `{'cle': valeur, ...}` (cles toujours des 'str' litterales, cf.
        contrainte REX-SL sur 'set <dict> <cle> <val>;')."""
        rendered = [
            f"{REX_CollectionLiteral._py_repr(k)}: {REX_CollectionLiteral._py_repr(v)}"
            for k, v in pairs
        ]
        return "{" + ", ".join(rendered) + "}"

    @staticmethod
    def _split_on_commas(tokens):
        groups, current = [], []
        for t in tokens:
            if isinstance(t, Token) and t.type == "PUNCT" and t.value == ",":
                groups.append(current)
                current = []
            else:
                current.append(t)
        if current:
            groups.append(current)
        return groups

    @staticmethod
    def _split_dict_pairs(items):
        pairs = []
        for g in REX_CollectionLiteral._split_on_commas(items):
            colon_idx = next(
                (i for i, t in enumerate(g)
                 if isinstance(t, Token) and t.type == "PUNCT" and t.value == ":"),
                None,
            )
            if colon_idx is None:
                raise RexResolveError("entree de dictionnaire invalide (attendu 'cle: valeur')")
            key_tokens, val_tokens = g[:colon_idx], g[colon_idx + 1:]
            if not key_tokens or not val_tokens:
                raise RexResolveError("entree de dictionnaire invalide (cle ou valeur manquante)")
            pairs.append((key_tokens, val_tokens))
        return pairs


class REX_FileReadExpr:
    """Compile `read(<path>)` / `readlines(<path>)` utilises comme valeur
    d'un `var` (gestion de fichier a la Python, 0.0.11) :

        var contenu = read("data.txt")       # str : contenu ENTIER du fichier
        var lignes = readlines("data.txt")   # list : une entree par ligne

    Delegue directement aux opcodes REX-SL `read <path> <dest>;` /
    `readlines <dest> <path>;`, qui ECRIVENT dans une variable deja
    declaree - `name` est donc declaree ici (sans valeur initiale), puis
    l'opcode de lecture est emis juste apres."""

    FUNCS = {"read": "str", "readlines": "list"}

    @staticmethod
    def compile_into_var(func_name, arg_tokens, var_name, explicit_type, emitter):
        groups = REX_FileReadExpr._split_on_commas(arg_tokens)
        if len(groups) != 1 or not groups[0]:
            raise RexResolveError(
                f"'{func_name}' attend exactement un argument (chemin) : {func_name}(<path>)"
            )
        target_type = REX_FileReadExpr.FUNCS[func_name]
        if explicit_type is not None and explicit_type != target_type:
            raise RexResolveError(
                f"type declare '{explicit_type}' incompatible avec '{func_name}(...)' "
                f"(retourne toujours '{target_type}')"
            )
        if var_name in emitter.types:
            raise RexResolveError(f"variable deja declaree : {var_name}")

        codegen = ExprCodegen(emitter)
        path_ref, path_type = codegen.generate(ExprParser(groups[0]).parse())
        if path_type != "str":
            raise RexResolveError(f"'{func_name}' : le chemin doit etre de type 'str'")

        emitter.declare_literal(var_name, target_type, None, explicit=explicit_type is not None)
        dest = var_name
        if func_name == "read":
            emitter.emit(f"read {path_ref} {dest};")
        else:
            emitter.emit(f"readlines {dest} {path_ref};")

    @staticmethod
    def _split_on_commas(tokens):
        groups, current = [], []
        for t in tokens:
            if isinstance(t, Token) and t.type == "PUNCT" and t.value == ",":
                groups.append(current)
                current = []
            else:
                current.append(t)
        groups.append(current)
        return groups




# =============================================================================
# COMPREHENSION DE LISTE : REX_ListComprehension
# =============================================================================

class REX_ListComprehension:
    """0.0.14 : sucre syntaxique `[<expr> for <var> in <iterable> [if <cond>]]`
    reconnu comme valeur d'un `var` ou d'une reaffectation (aux memes
    points d'appel que REX_CollectionLiteral.detect, verifie EN PREMIER
    par l'appelant). Compile en `var list <nom> [];` + boucle + `append`,
    en reprenant les 4 strategies d'iteration de REX_ForStatement
    (range(), litteral deroule a la compilation, variable list/tuple/set
    au runtime via len()+get(), str au runtime via len()+charat()) - dupliquees
    ici plutot que reutilisees via resolver.compile_body(), le corps
    d'une comprehension n'etant pas une liste de _Line/_Block mais une
    simple expression (+ condition optionnelle) a evaluer et ajouter au
    resultat. Ni `break` ni `continue` n'ont de sens ici (pas de bloc
    utilisateur), donc pas de push_loop_labels/pop_loop_labels."""

    @staticmethod
    def detect(expr_tokens):
        """Retourne (items, for_idx) si `expr_tokens` est `[... for ...]`
        (un seul groupe `[...]` contenant un mot-cle 'for' de tete au
        niveau le plus haut), sinon None. Ne consomme rien : a appeler
        AVANT REX_CollectionLiteral.detect au point d'entree (sinon un
        `[x, y for z in w]` invalide serait mal interprete comme une
        liste litteraux a virgules)."""
        if len(expr_tokens) != 1:
            return None
        tok = expr_tokens[0]
        if not (isinstance(tok, Group) and tok.kind == "[]"):
            return None
        items = tok.items
        for i, t in enumerate(items):
            if isinstance(t, Token) and t.type == "KEYWORD" and t.value == "for":
                return items, i
        return None

    @staticmethod
    def compile_to_ref(items, for_idx, emitter):
        """Variante de `compile()` utilisable comme valeur au sein d'une
        expression generale (noeud "listcomp" produit par ExprParser quand
        une comprehension apparait ailleurs que directement comme valeur
        d'un `var`/reaffectation - ex: `show([i for i in range(10)])`,
        argument de fonction, f-string, ...). Alloue une variable REX
        temporaire fraiche (jamais en collision, cf. Emitter.new_temp_name),
        y compile la comprehension via `compile()`, puis retourne
        (ref, "list") comme n'importe quel autre operande deja evalue."""
        temp_name = emitter.new_temp_name()
        REX_ListComprehension.compile(temp_name, items, for_idx, emitter, explicit=False)
        return temp_name, "list"

    @staticmethod
    def compile(name, items, for_idx, emitter, explicit=False):
        expr_tokens = items[:for_idx]
        if not expr_tokens:
            raise RexResolveError(
                "comprehension de liste invalide : expression manquante avant 'for'"
            )
        rest = items[for_idx + 1:]
        if not rest or not (isinstance(rest[0], Token) and rest[0].type == "IDENT"):
            raise RexResolveError(
                "comprehension de liste invalide : nom de variable attendu apres 'for'"
            )
        var_name = rest[0].value
        if var_name.startswith("__rx_"):
            raise RexResolveError(f"nom de variable reserve au compilateur : {var_name}")
        idx = 1
        if idx >= len(rest) or not (
            isinstance(rest[idx], Token) and rest[idx].type == "KEYWORD" and rest[idx].value == "in"
        ):
            raise RexResolveError("comprehension de liste invalide : 'in' attendu apres la variable")
        idx += 1
        iterable_tokens = rest[idx:]
        cond_tokens = None
        for j, t in enumerate(iterable_tokens):
            if isinstance(t, Token) and t.type == "KEYWORD" and t.value == "if":
                cond_tokens = iterable_tokens[j + 1:]
                iterable_tokens = iterable_tokens[:j]
                break
        if not iterable_tokens:
            raise RexResolveError("comprehension de liste invalide : iterable manquant apres 'in'")
        if cond_tokens is not None and not cond_tokens:
            raise RexResolveError("comprehension de liste invalide : condition manquante apres 'if'")

        # variable resultat : liste vide au depart, type d'element decouvert
        # au premier append (comme pour un `var l = [];` suivi d'append()).
        already_declared = name in emitter.types
        if already_declared:
            emitter.retype_as_collection(name, "list")
        emitter.declare_literal(name, "list", explicit=explicit)
        result_ref = name

        def emit_body():
            if cond_tokens is not None:
                # Les comparaisons/and/or/not ne sont PAS des expressions au
                # sens ExprParser/ExprCodegen dans ce compilateur (seul
                # REX_IfStatement sait les compiler, via un arbre logique
                # cible sur des labels reels true_lbl/false_lbl - cf sa
                # docstring). On reutilise donc directement ce mecanisme au
                # lieu de tenter de produire une valeur bool intermediaire.
                append_lbl = f"__rx_lcif{emitter.new_loop_id()}_yes"
                skip_lbl = f"__rx_lcif{emitter.new_loop_id()}_no"
                REX_IfStatement._compile_cond_tree(cond_tokens, emitter, append_lbl, skip_lbl)
                emitter.emit(f"lbl {append_lbl};")
                REX_ListComprehension._emit_append(expr_tokens, result_ref, emitter)
                emitter.emit(f"lbl {skip_lbl};")
            else:
                REX_ListComprehension._emit_append(expr_tokens, result_ref, emitter)

        REX_ListComprehension._compile_loop(var_name, iterable_tokens, emit_body, emitter)

    @staticmethod
    def _emit_append(expr_tokens, result_ref, emitter):
        val_ref, val_type = ExprCodegen(emitter).generate(ExprParser(expr_tokens).parse())
        if val_type not in ("number", "float", "bool", "str"):
            raise RexResolveError(
                f"comprehension de liste : type '{val_type}' non stockable dans une liste "
                "(limitation REX-SL : number/float/bool/str uniquement)"
            )
        elem_type = emitter.get_elem_type(result_ref)
        if elem_type is not None and elem_type != val_type:
            raise RexResolveError(
                f"comprehension de liste : liste homogene de type '{elem_type}', valeur "
                f"incompatible de type '{val_type}'"
            )
        emitter.emit(f"append {result_ref} {val_ref};")
        emitter.note_elem_type(result_ref, val_type)
        emitter.collection_repr.pop(result_ref, None)

    @staticmethod
    def _compile_loop(var_name, iterable_tokens, emit_body, emitter):
        is_range = (
            len(iterable_tokens) == 2
            and isinstance(iterable_tokens[0], Token)
            and iterable_tokens[0].type == "IDENT"
            and iterable_tokens[0].value == "range"
            and isinstance(iterable_tokens[1], list)
        )
        if is_range:
            REX_ListComprehension._compile_range(var_name, iterable_tokens[1], emit_body, emitter)
            return

        collection = None
        if len(iterable_tokens) == 1:
            collection = REX_CollectionLiteral.detect(iterable_tokens, None)
        if collection is not None:
            _kind, payload = collection
            REX_ListComprehension._compile_unrolled(var_name, payload, emit_body, emitter)
            return

        probe_ref, probe_type = ExprCodegen(emitter).generate(ExprParser(iterable_tokens).parse())
        if probe_type in ("list", "tuple", "set"):
            REX_ListComprehension._compile_list_var(var_name, probe_ref, probe_type, emit_body, emitter)
            return
        if probe_type == "str":
            REX_ListComprehension._compile_str(var_name, probe_ref, emit_body, emitter)
            return
        raise RexResolveError(
            f"comprehension de liste : type '{probe_type}' non iterable (attendu range(), "
            "un litteral de collection, une variable list/tuple/set, ou une str)"
        )

    @staticmethod
    def _compile_range(var_name, range_args_tokens, emit_body, emitter):
        arg_groups = REX_ForStatement._split_on_commas(range_args_tokens)
        if len(arg_groups) == 1:
            start_tokens, stop_tokens, step_tokens = None, arg_groups[0], None
        elif len(arg_groups) == 2:
            start_tokens, stop_tokens, step_tokens = arg_groups[0], arg_groups[1], None
        elif len(arg_groups) == 3:
            start_tokens, stop_tokens, step_tokens = arg_groups[0], arg_groups[1], arg_groups[2]
        else:
            raise RexResolveError("range() attend 1, 2 ou 3 arguments (comme en Python)")
        if not stop_tokens or (start_tokens is not None and not start_tokens) or (
            step_tokens is not None and not step_tokens
        ):
            raise RexResolveError("argument vide dans range(...)")

        codegen = ExprCodegen(emitter)
        if start_tokens is not None:
            start_ref, start_type = codegen.generate(ExprParser(start_tokens).parse())
        else:
            start_ref, start_type = "0", "number"
        if start_type != "number":
            raise RexResolveError("range(): les bornes doivent etre de type 'number'")
        stop_ref, stop_type = codegen.generate(ExprParser(stop_tokens).parse())
        if stop_type != "number":
            raise RexResolveError("range(): les bornes doivent etre de type 'number'")
        if step_tokens is not None:
            step_node = ExprParser(step_tokens).parse()
            step_value = REX_ForStatement._literal_int_or_none(step_node)
            if step_value is None:
                raise RexResolveError(
                    "range(): le pas ('step') doit etre un entier litteral connu a la "
                    "compilation"
                )
            if step_value == 0:
                raise RexResolveError("range(): le pas ne peut pas etre 0")
            step_ref, step_type = codegen.generate(step_node)
        else:
            step_value = 1
            step_ref, step_type = "1", "number"

        loop_id = emitter.new_loop_id()
        start_lbl = f"__rx_lcr{loop_id}_start"
        body_lbl = f"__rx_lcr{loop_id}_body"
        step_lbl = f"__rx_lcr{loop_id}_step"
        end_lbl = f"__rx_lcr{loop_id}_end"
        limit = f"__rx_lcr{loop_id}_limit"
        step_var = f"__rx_lcr{loop_id}_stepv"

        if emitter.type_of_or_none(var_name) == "number" and not emitter.is_explicit_type(var_name):
            emitter.reassign(var_name, start_ref, "number")
        else:
            emitter.assign_computed(var_name, start_ref, start_type, "number")
        emitter.assign_computed(limit, stop_ref, stop_type, "number")
        emitter.assign_computed(step_var, step_ref, step_type, "number")

        cmp_op = "less" if step_value > 0 else "greater"
        var_ref = var_name

        emitter.emit(f"lbl {start_lbl};")
        emitter.emit(f"cdn {cmp_op} {var_ref} {limit};")
        emitter.emit(f"go {body_lbl};")
        emitter.emit("cdn on;")
        emitter.emit(f"go {end_lbl};")
        emitter.emit(f"lbl {body_lbl};")
        emit_body()
        emitter.emit(f"lbl {step_lbl};")
        emitter.emit(f"add {var_ref} {var_ref} {step_var};")
        emitter.emit("cdn on;")
        emitter.emit(f"go {start_lbl};")
        emitter.emit(f"lbl {end_lbl};")

    @staticmethod
    def _compile_unrolled(var_name, payload, emit_body, emitter):
        if not payload:
            return
        codegen = ExprCodegen(emitter)
        for elem_tokens in payload:
            if not elem_tokens:
                raise RexResolveError("element de collection vide dans une comprehension")
            ref, vtype = codegen.generate(ExprParser(elem_tokens).parse())
            if vtype not in ("number", "float", "str", "bool"):
                raise RexResolveError(
                    f"element de type '{vtype}' non supporte comme valeur de boucle "
                    "(limitation REX-SL : number/float/str/bool uniquement)"
                )
            emitter.assign_dynamic(var_name, ref, vtype)
            emit_body()

    @staticmethod
    def _compile_list_var(var_name, list_ref, list_type, emit_body, emitter):
        elem_type = emitter.get_elem_type(list_ref)
        if elem_type is None:
            raise RexResolveError(
                "comprehension sur une liste : type d'element inconnu ou heterogene "
                "(liste homogene de number/float/str/bool requise)"
            )
        loop_id = emitter.new_loop_id()
        start_lbl = f"__rx_lclst{loop_id}_start"
        body_lbl = f"__rx_lclst{loop_id}_body"
        step_lbl = f"__rx_lclst{loop_id}_step"
        end_lbl = f"__rx_lclst{loop_id}_end"
        len_var = f"__rx_lclst{loop_id}_len"
        idx_var = f"__rx_lclst{loop_id}_i"
        elem_var = f"__rx_lclst{loop_id}_e"

        emitter.declare_literal(len_var, "number")
        emitter.emit(f"len {len_var} {list_ref};")
        emitter.declare_literal(idx_var, "number", "0")
        emitter.declare_literal(elem_var, elem_type, DEFAULT_VALUES[elem_type])

        emitter.emit(f"lbl {start_lbl};")
        emitter.emit(f"cdn less {idx_var} {len_var};")
        emitter.emit(f"go {body_lbl};")
        emitter.emit("cdn on;")
        emitter.emit(f"go {end_lbl};")
        emitter.emit(f"lbl {body_lbl};")
        emitter.emit(f"get {list_ref} {elem_type} {elem_var} {idx_var};")
        emitter.assign_dynamic(var_name, elem_var, elem_type)
        emit_body()
        emitter.emit(f"lbl {step_lbl};")
        emitter.emit(f"add {idx_var} {idx_var} 1;")
        emitter.emit("cdn on;")
        emitter.emit(f"go {start_lbl};")
        emitter.emit(f"lbl {end_lbl};")

    @staticmethod
    def _compile_str(var_name, str_ref, emit_body, emitter):
        loop_id = emitter.new_loop_id()
        start_lbl = f"__rx_lcstr{loop_id}_start"
        body_lbl = f"__rx_lcstr{loop_id}_body"
        step_lbl = f"__rx_lcstr{loop_id}_step"
        end_lbl = f"__rx_lcstr{loop_id}_end"
        len_var = f"__rx_lcstr{loop_id}_len"
        idx_var = f"__rx_lcstr{loop_id}_i"
        char_var = f"__rx_lcstr{loop_id}_c"

        emitter.declare_literal(len_var, "number")
        emitter.emit(f"len {len_var} {str_ref};")
        emitter.declare_literal(idx_var, "number", "0")
        emitter.declare_literal(char_var, "str", '""')

        emitter.emit(f"lbl {start_lbl};")
        emitter.emit(f"cdn less {idx_var} {len_var};")
        emitter.emit(f"go {body_lbl};")
        emitter.emit("cdn on;")
        emitter.emit(f"go {end_lbl};")
        emitter.emit(f"lbl {body_lbl};")
        emitter.emit(f"charat {char_var} {str_ref} {idx_var};")
        emitter.assign_dynamic(var_name, char_var, "str")
        emit_body()
        emitter.emit(f"lbl {step_lbl};")
        emitter.emit(f"add {idx_var} {idx_var} 1;")
        emitter.emit("cdn on;")
        emitter.emit(f"go {start_lbl};")
        emitter.emit(f"lbl {end_lbl};")




# =============================================================================
# INSTRUCTIONS : déclarations et affectations
# =============================================================================

class REX_VarStatement:
    """Compile une instruction REX `var` vers une (ou plusieurs, pour les
    temporaires de calcul) declaration(s) REX-SL.

    Formes supportees :
        var x                 -> type "number" par defaut, valeur 0
        var x = expr            -> type infere depuis l'expression resolue
        var type x             -> type explicite, valeur par defaut du type
        var type x = expr      -> type explicite + valeur (expr resolue)

    ex: `var number x = 5` ; `var x = (2 + 3) * 4` ; `var y`.
    """

    keyword = "var"

    @staticmethod
    def compile(tokens, emitter):
        idx = 1  # tokens[0] == KEYWORD "var"
        explicit_type = None

        # `var <type> <name> ...` seulement si un IDENT suit immediatement
        # le nom de type (sinon "type" est en realite le nom de variable :
        # `var type = 5` reste valide, `type` devient alors l'identifiant).
        # 0.0.15 : `func` est un KEYWORD du lexer (pas un IDENT), donc on
        # l'accepte aussi comme annotation de type pour `var func f = myfunc;`.
        if (
            idx < len(tokens)
            and isinstance(tokens[idx], Token)
            and tokens[idx].type in ("IDENT", "KEYWORD")
            and tokens[idx].value in TYPE_NAMES
            and idx + 1 < len(tokens)
            and isinstance(tokens[idx + 1], Token)
            and tokens[idx + 1].type == "IDENT"
        ):
            explicit_type = tokens[idx].value
            idx += 1

        if idx >= len(tokens) or not (isinstance(tokens[idx], Token) and tokens[idx].type == "IDENT"):
            raise RexResolveError("declaration 'var' invalide : nom de variable attendu")
        name = tokens[idx].value
        idx += 1

        if name.startswith("__rx_"):
            # Reserve au compilateur : `__rx_t...` (temporaires, cf.
            # new_temp_name) et `__rx_col...` (alias internes generes par
            # Emitter.retype_as_collection lors d'un retypage de collection).
            raise RexResolveError(f"nom de variable reserve au compilateur : {name}")

        has_value = (
            idx < len(tokens)
            and isinstance(tokens[idx], Token)
            and tokens[idx].type == "OP"
            and tokens[idx].value == "="
        )

        if has_value:
            expr_tokens = tokens[idx + 1:]
            if not expr_tokens:
                raise RexResolveError(f"valeur manquante apres '=' pour la variable '{name}'")


            if REX_NoneSupport.is_none_tokens(expr_tokens):
                if explicit_type == "func":
                    raise RexResolveError("'var func' ne peut pas etre initialise a 'None'")
                REX_NoneSupport.declare(name, explicit_type, emitter)
                return
            
            # `var func f = myfunc;` (0.0.15) : declaration d'une variable
            # pointeur de fonction. L'expression droite doit etre un IDENT
            # simple correspondant a une fonction 'func' declaree par REX.
            if explicit_type == "func":
                REX_VarStatement._compile_funcref(name, expr_tokens, emitter)
                return

            # `var s = read(<path>)` / `var l = readlines(<path>)` (0.0.11) :
            # pseudo-appels reserves, geres a part car ils delegate directement
            # aux opcodes REX-SL `read`/`readlines` (qui ecrivent DANS la
            # variable cible), plutot que de passer par ExprCodegen._call
            # (reserve aux vraies fonctions REX declarees par 'func').
            if (
                len(expr_tokens) == 2
                and isinstance(expr_tokens[0], Token) and expr_tokens[0].type == "IDENT"
                and expr_tokens[0].value in REX_FileReadExpr.FUNCS
                and isinstance(expr_tokens[1], list)
            ):
                REX_FileReadExpr.compile_into_var(
                    expr_tokens[0].value, expr_tokens[1], name, explicit_type, emitter
                )
                return

            # comprehension de liste (0.0.14) : verifiee AVANT le litteral
            # de collection classique, sinon `[x for x in l]` serait
            # interprete a tort comme un litteral a un seul element.
            comprehension = REX_ListComprehension.detect(expr_tokens)
            if comprehension is not None:
                if explicit_type not in (None, "list"):
                    raise RexResolveError(
                        f"type declare '{explicit_type}' incompatible avec une comprehension "
                        "de liste (toujours de type 'list')"
                    )
                items, for_idx = comprehension
                REX_ListComprehension.compile(name, items, for_idx, emitter,
                                              explicit=explicit_type is not None)
                return

            collection = REX_CollectionLiteral.detect(expr_tokens, explicit_type)
            if collection is not None:
                kind, payload = collection
                if explicit_type is not None and explicit_type != kind:
                    raise RexResolveError(
                        f"type declare '{explicit_type}' incompatible avec la valeur litterale "
                        f"fournie (reconnue comme '{kind}')"
                    )
                # Le type est explicite si l'utilisateur a ecrit `var list l = [...]`
                # (explicit_type != None). Pour `var l = [...]`, le type est infere.
                REX_CollectionLiteral.compile(name, kind, payload, emitter,
                                              explicit=explicit_type is not None)
                return

            if explicit_type in ("list", "dict", "set", "tuple"):
                # On accepte un appel de fonction retournant une collection (0.0.14) :
                # le cas general (literal/calcul) est refuse plus bas si le type infere
                # ne correspond pas.
                node_test = ExprParser(expr_tokens).parse()
                if node_test[0] != "call":
                    raise RexResolveError(
                        f"le type '{explicit_type}' necessite soit aucune valeur, soit un litteral "
                        "de collection ([...], {...}, (a, b, ...)) ou un appel de fonction "
                        "retournant ce type de collection"
                    )

            node = ExprParser(expr_tokens).parse()
            codegen = ExprCodegen(emitter)

            if node[0] == "lit":
                # Cas simple : une valeur litterale peut etre ecrite
                # directement dans la declaration `var <type> <name> <val>;`
                # (pas besoin de passer par un calcul intermediaire).
                ref, inferred_type = codegen._literal(node[1])
                final_type = explicit_type or inferred_type
                if explicit_type and explicit_type != inferred_type:
                    if explicit_type == "float" and inferred_type == "number":
                        ref = repr(float(node[1]))  # promotion litterale directe
                    else:
                        raise RexResolveError(
                            f"type declare '{explicit_type}' incompatible avec la valeur "
                            f"de type '{inferred_type}' pour la variable '{name}'"
                        )
                # explicit=True ssi l'utilisateur a ecrit `var number x = 5`
                emitter.declare_literal(name, final_type, ref,
                                        explicit=explicit_type is not None)
            else:
                # Cas general (identifiant, moins unaire, calcul) : on
                # evalue l'expression puis on l'assigne a `name`.
                ref, inferred_type = codegen.generate(node)
                if inferred_type == "none":
                    if explicit_type is not None:
                        raise RexResolveError(
                            f"impossible d'assigner 'None' a la variable '{name}' de type explicite '{explicit_type}'"
                        )
                    REX_NoneSupport.declare(name, None, emitter)
                    return
                final_type = explicit_type or inferred_type
                if final_type in ("list", "tuple", "set", "dict"):
                    # Collection retournee par une fonction (0.0.14) : meme
                    # technique que _copy_into_temp -> declare via 'var list/dict'
                    # (rexsl_list_new()), puis libere l'objet initial et reassigne
                    # le pointeur via scrc pour eviter le double-free.
                    if explicit_type is not None and explicit_type != inferred_type:
                        raise RexResolveError(
                            f"type declare '{explicit_type}' incompatible avec la valeur "
                            f"de type '{inferred_type}' pour la variable '{name}'"
                        )
                    emit_type = "dict" if final_type == "dict" else "list"
                    emitter.declare_literal(name, emit_type,
                                            explicit=explicit_type is not None)
                    emitter.types[name] = final_type
                    dest_c = f"SL_{name}"
                    src_c = f"SL_{ref}"
                    free_fn = "rexsl_list_free" if emit_type == "list" else "rexsl_dict_free"
                    code = (
                        f"if ({dest_c}) {{ {free_fn}({dest_c}); }} "
                        f"{dest_c} = {src_c}; {src_c} = NULL;"
                    )
                    escaped = code.replace("\\", "\\\\").replace('"', '\\"')
                    emitter.emit(f'scrc "{escaped}";')
                    # Propager le type d'element si connu (depuis elem_types du temporaire)
                    src_elem = emitter.get_elem_type(ref)
                    src_dict_v = emitter.get_dict_value_type(ref)
                    if src_elem is not None:
                        emitter.note_elem_type(name, src_elem)
                    if src_dict_v is not None:
                        emitter.note_dict_value_type(name, src_dict_v)
                else:
                    # Cas scalaire : auto-declaration via opcode identite.
                    emitter.assign_computed(name, ref, inferred_type, final_type,
                                            explicit=explicit_type is not None)
        else:
            if idx != len(tokens):
                raise RexResolveError(
                    f"jetons inattendus apres la declaration de '{name}' : {tokens[idx:]!r}"
                )
            final_type = explicit_type or "number"
            # 0.1.3 : `var none x` (type explicite 'none', pas de valeur) -> `var none x;`
            if final_type == "none":
                emitter.declare_literal(name, "none", explicit=True)
                return
            # tuple/set n'existent pas nativement en REX-SL : representes
            # comme une 'list' vide, le type REX reel reste suivi a part.
            emit_type = "list" if final_type in ("set", "tuple") else final_type
            # `var x` sans valeur ni type explicite -> type par defaut "number", infere.
            # `var number x` -> type explicite.
            emitter.declare_literal(name, emit_type, DEFAULT_VALUES.get(emit_type),
                                    explicit=explicit_type is not None)
            if final_type != emit_type:
                emitter.types[name] = final_type


    @staticmethod
    def _compile_funcref(var_name, expr_tokens, emitter):
        """Compile `var func <var_name> = <func_name>;` (0.0.15).

        `expr_tokens` doit contenir exactement un IDENT correspondant a une
        fonction deja declaree (dans emitter.functions). Emet un `scrc`
        declarant un pointeur de fonction C du bon type :
            RetType (*SL_<var_name>)(params) = FUNC_<func_name>;
        puis enregistre la variable dans emitter.funcrefs."""
        if (
            len(expr_tokens) != 1
            or not (isinstance(expr_tokens[0], Token)
                    and expr_tokens[0].type == "IDENT")
        ):
            raise RexResolveError(
                "'var func' : la valeur doit etre le nom d'une fonction deja "
                "declaree (ex: var func f = myfunc;) - les expressions "
                "complexes ne sont pas supportees pour les pointeurs de fonction"
            )
        func_name = expr_tokens[0].value

        # Resoudre via le registre de fonctions (peut etre un nom mangle de module)
        info = emitter.functions.get(func_name)
        if info is None:
            raise RexResolveError(
                f"'var func {var_name} = {func_name};' : "
                f"fonction '{func_name}' inconnue - declarez-la avec "
                f"'func {func_name}(...):' avant de creer un pointeur vers elle"
            )
        param_types, param_names, defaults, return_type, elem_type, dict_val_type = info

        # Construire la signature C du type pointeur de fonction
        # Type de retour C
        _C_TYPES = {
            "number": "int", "float": "float", "bool": "bool",
            "str": "char*", "list": "RexList*", "dict": "RexDict*",
        }
        ret_c = _C_TYPES.get(return_type, "void") if return_type is not None else "void"
        # Types des parametres
        param_c_types = [_C_TYPES.get(t, "void*") for t in param_types]
        ptr_c_name = f"SL_{var_name}"
        # Note : le nom mangle REX-SL de la fonction cible est FUNC_<func_name>
        # (convention de nommage de REX-SL.py : toute fonction est emise sous
        # le nom C `FUNC_<nom_rexsl>` par func_begin/endfunc).
        c_decl = (
            f"{ret_c} (*{ptr_c_name})({', '.join(param_c_types) or 'void'}) "
            f"= FUNC_{func_name};"
        )
        emitter.register_funcref(
            var_name, func_name,
            (param_types, param_names, defaults, return_type, elem_type, dict_val_type),
            c_decl
        )


class REX_IndexAssignStatement:
    """Compile une affectation indexee a la Python `<nom>[<cle>] = <expr>;`
    (0.0.13) :
        d["cle"] = expr   -> dict, delegue directement a l'opcode REX-SL
                              deja existant `set <dict> <cle> <valeur>;`
        l[i] = expr        -> list/tuple/set, PAS d'opcode REX-SL dedie
                              (`list_set` n'existe pas cote REX-SL - seul
                              vrai manque identifie sur ce point) : on
                              ecrit directement dans le tableau C sous-
                              jacent via `scrc` (injection C brute, deja
                              exposee par REX-SL), en s'appuyant sur le
                              layout documente de RexList/RexValue.

                              Sur (in)securite du nom C genere : REX-SL
                              nomme la variable C `SL_<nom>` pour toute
                              variable qui n'a jamais ete retypee via
                              l'opcode `change` - et `change` refuse
                              explicitement les types list/dict (voir
                              REX-SL.py, REX_SL_CODE.change: "type non
                              convertible (list/dict)"), donc une liste
                              REX-SL declaree garde TOUJOURS le nom C
                              `SL_<nom>` (jamais de suffixe `_g<N>`) pour
                              toute sa duree de vie. Pour rester sur ce
                              terrain sûr avec l'index et la valeur aussi
                              (qui pourraient sinon referencer un
                              temporaire ayant transite par `change`), on
                              les recopie d'abord dans des temporaires
                              FRAIS via `_copy_into_temp` (jamais passes a
                              `change`), dont le nom C est donc lui aussi
                              garanti `SL_<temp>`.
    """

    @staticmethod
    def compile(tokens, emitter):
        name = tokens[0].value
        bracket = tokens[1]
        value_tokens = tokens[3:]
        if not value_tokens:
            raise RexResolveError(
                f"valeur manquante apres '=' pour l'affectation indexee de '{name}'"
            )
        items = list(bracket.items)
        if any(isinstance(t, Token) and t.type == "PUNCT" and t.value == ":" for t in items):
            raise RexResolveError(
                "affectation indexee : le slice '[debut:fin] = ...' n'est pas supporte"
            )
        if not items:
            raise RexResolveError("affectation indexee : index/cle manquant dans '[...]'")

        vtype = emitter.type_of(name)
        coll_ref = name
        codegen = ExprCodegen(emitter)
        key_node = ExprParser(items).parse()
        val_node = ExprParser(value_tokens).parse()
        val_ref, val_type = codegen.generate(val_node)

        if vtype == "dict":
            key_ref, key_type = codegen.generate(key_node)
            if key_type != "str":
                raise RexResolveError(
                    "affectation indexee sur un dict : la cle doit etre une 'str'"
                )
            if val_type not in ("number", "float", "bool", "str"):
                raise RexResolveError(
                    f"affectation indexee sur un dict : valeur de type '{val_type}' "
                    "non stockable (limitation REX-SL : number/float/bool/str uniquement)"
                )
            emitter.emit(f"set {coll_ref} {key_ref} {val_ref};")
            emitter.note_dict_value_type(coll_ref, val_type)
            emitter.collection_repr.pop(coll_ref, None)
            return

        if vtype in ("list", "tuple", "set"):
            idx_ref, idx_type = codegen.generate(key_node)
            if idx_type != "number":
                raise RexResolveError(
                    "affectation indexee sur une liste : l'index doit etre un 'number'"
                )
            if val_type not in ("number", "float", "bool", "str"):
                raise RexResolveError(
                    f"affectation indexee sur une liste : valeur de type '{val_type}' "
                    "non stockable (limitation REX-SL : number/float/bool/str uniquement)"
                )
            elem_type = emitter.get_elem_type(coll_ref)
            if elem_type is not None and elem_type != val_type:
                raise RexResolveError(
                    f"affectation indexee sur une liste homogene de type '{elem_type}' : "
                    f"valeur incompatible de type '{val_type}'"
                )
            idx_tmp, _ = codegen._copy_into_temp(idx_ref, "number")
            val_tmp, _ = codegen._copy_into_temp(val_ref, val_type)
            emitter.note_elem_type(coll_ref, val_type)
            emitter.collection_repr.pop(coll_ref, None)

            tag_field = {
                "number": ("REXSL_T_NUMBER", "as_number"),
                "float": ("REXSL_T_FLOAT", "as_float"),
                "bool": ("REXSL_T_BOOL", "as_bool"),
                "str": ("REXSL_T_STR", "as_str"),
            }
            tag, field = tag_field[val_type]
            list_c = f"SL_{coll_ref}"
            idx_c = f"SL_{idx_tmp}"
            val_c = f"strdup(SL_{val_tmp})" if val_type == "str" else f"SL_{val_tmp}"
            code = (
                f"{{ int __rx_i = (int)({idx_c}); "
                f'if (__rx_i < 0 || __rx_i >= {list_c}->count) {{ '
                f'fprintf(stderr, "[REX] erreur : index de liste hors limites : %d\\n", __rx_i); '
                f"exit(1); }} "
                f"{list_c}->items[__rx_i] = (RexValue){{ .type = {tag}, .value.{field} = {val_c} }}; }}"
            )
            escaped = code.replace("\\", "\\\\").replace('"', '\\"')
            emitter.emit(f'scrc "{escaped}";')
            return

        raise RexResolveError(
            f"affectation indexee '{name}[...] = ...' non supportee pour le type "
            f"'{vtype}' (attendu list/tuple/set/dict)"
        )


class REX_AssignStatement:
    """Compile une reaffectation `<nom> = <expr>;` (variable deja declaree
    par un `var` precedent) -> REX-SL `<nom> <operande>;`. Necessaire pour
    qu'un `repeat ... times` (ou tout code utilisant `go`) puisse
    reellement faire evoluer une variable d'un tour de boucle au suivant,
    la sortie `var` seule ne declarant qu'une fois.

    Depuis 0.0.8 : si la valeur droite est un LITTERAL DE COLLECTION et que
    le type actuel de la variable n'etait PAS declare explicitement, le
    retypage est autorise (ex: `var s = carre(i)` -> s est number-infere,
    puis `s = {1, 2, 3}` -> s devient set). Si le type etait explicite
    (`var number s = 0`), le changement de type est une erreur."""

    # 0.0.14 : operateurs de reaffectation composee -> opcode binaire REX-SL
    # correspondant (utilise pour reecrire `x op= expr` en `x = x op expr`
    # au niveau de l'AST, cf plus bas).
    COMPOUND_OPS = {
        "=": None,
        "+=": "add", "-=": "sub", "*=": "mul", "/=": "div", "%=": "mod",
    }

    @staticmethod
    def compile(tokens, emitter):
        name = tokens[0].value
        op_token = tokens[1].value
        opcode = REX_AssignStatement.COMPOUND_OPS[op_token]
        vtype = emitter.type_of(name)
        expr_tokens = tokens[2:]
        if not expr_tokens:
            raise RexResolveError(
                f"valeur manquante apres '{op_token}' pour la reaffectation de '{name}'"
            )

        if opcode is not None:
            # `x op= expr` : uniquement valable sur un scalaire deja declare
            # (number/float/str/bool) - une collection n'a pas de semantique
            # +=/-=/*=// / %= ici (utiliser append()/extend() pour les listes).
            if vtype in ("list", "dict", "set", "tuple", "funcref"):
                raise RexResolveError(
                    f"'{op_token}' invalide sur '{name}' (type '{vtype}') : "
                    "les operateurs composes ne s'appliquent qu'aux scalaires "
                    "(number/float/str/bool)"
                )
            node = ("binop", opcode, ("ident", name), ExprParser(expr_tokens).parse())
            codegen = ExprCodegen(emitter)
            ref, ref_type = codegen.generate(node)
            emitter.assign_dynamic(name, ref, ref_type)
            return
        
        if REX_NoneSupport.is_none_tokens(expr_tokens):
            REX_NoneSupport.assign(name, emitter)
            return

        # Reassignation d'une variable funcref `f = otherfunc;` (0.0.15)
        if vtype == "funcref":
            if (
                len(expr_tokens) != 1
                or not (isinstance(expr_tokens[0], Token)
                        and expr_tokens[0].type == "IDENT")
            ):
                raise RexResolveError(
                    f"reassignation de '{name}' (type 'func') : "
                    "seul un nom de fonction est accepte (ex: f = otherfunc;)"
                )
            new_func_name = expr_tokens[0].value
            new_info = emitter.functions.get(new_func_name)
            if new_info is None:
                raise RexResolveError(
                    f"reassignation '{name} = {new_func_name};' : "
                    f"fonction '{new_func_name}' inconnue"
                )
            param_types, param_names, defaults, return_type, elem_type, dict_val = new_info
            _C_TYPES = {
                "number": "int", "float": "float", "bool": "bool",
                "str": "char*", "list": "RexList*", "dict": "RexDict*",
            }
            ret_c = _C_TYPES.get(return_type, "void") if return_type is not None else "void"
            ptr_c = f"SL_{name}"
            c_assign = f"{ptr_c} = FUNC_{new_func_name};"
            emitter.reassign_funcref(
                name, new_func_name,
                (param_types, param_names, defaults, return_type, elem_type, dict_val),
                c_assign
            )
            return

        # Detecter d'abord une comprehension de liste (0.0.14), AVANT le
        # litteral de collection classique (meme raison que dans
        # REX_VarStatement : `[x for x in l]` ne doit pas etre lu comme un
        # litteral a un seul element).
        comprehension = REX_ListComprehension.detect(expr_tokens)
        if comprehension is not None:
            items, for_idx = comprehension
            REX_ListComprehension.compile(name, items, for_idx, emitter, explicit=False)
            return

        # Detecter d'abord un litteral de collection a droite.
        # On tente sans type hint (le type actuel de la variable sert de hint
        # si c'est deja une collection, sinon None pour laisser la detection libre).
        collection_hint = vtype if vtype in ("list", "dict", "set", "tuple") else None
        collection = REX_CollectionLiteral.detect(expr_tokens, collection_hint)
        if collection is not None:
            kind, payload = collection
            if vtype == kind or (vtype in ("list",) and kind in ("list", "tuple", "set")):
                # Meme famille de collection : reaffectation simple (pas de retypage).
                # On vide la liste et on la reconstruit (REX-SL ne permet pas de
                # reassigner une list directement -> on emet un nouveau var list,
                # en effacant d'abord l'ancienne entree du type tracker).
                emitter.retype_as_collection(name, kind)
                REX_CollectionLiteral.compile(name, kind, payload, emitter,
                                              explicit=False)
            else:
                # Retypage vers une collection d'un type different : autorise
                # uniquement si l'ancien type n'etait pas explicite. On doit
                # d'abord vider l'ancienne entree du type tracker (comme dans
                # la branche ci-dessus), sinon REX_CollectionLiteral.compile
                # (-> Emitter.declare_literal) considere `name` comme deja
                # declaree et leve a tort "variable deja declaree" - meme
                # dans le cas legitime d'un retypage autorise.
                emitter.retype_as_collection(name, kind)
                REX_CollectionLiteral.compile(name, kind, payload, emitter,
                                              explicit=False)
            return

        # Reaffectation scalaire : type identique -> reaffectation classique ;
        # type different sur une variable inferee -> retypage automatique a
        # la Python (0.0.12, cf. Emitter.assign_dynamic) ; type different sur
        # une variable explicite -> erreur (comme avant).
        node = ExprParser(expr_tokens).parse()
        codegen = ExprCodegen(emitter)
        ref, ref_type = codegen.generate(node)
        if ref_type == "none":
            REX_NoneSupport.assign(name, emitter)
            return
        emitter.assign_dynamic(name, ref, ref_type)


class REX_UnpackStatement:
    """0.0.14 : deballage de tuple a la Python `a, b = expr_a, expr_b;`
    (forme la plus courante) ou `a, b = f();` quand `f` retourne une liste.

    Formes supportees :
      - `a, b = expr1, expr2;`       : deux scalaires du meme type ou non
      - `a, b, c = e1, e2, e3;`      : N cibles = N valeurs (N >= 2)
      - `a, b = f();`                 : deballage d'une list retournee par
                                        une fonction (nombre de valeurs connu
                                        a la compilation uniquement si le type
                                        de retour est annote `-> list` ET que
                                        le literal a ete capture dans
                                        collection_repr ; sinon erreur explicite).

    Limitation : les cibles doivent etre des variables simples (pas
    d'indexation `a[i], b = ...` ni de deballage imbrique `(a, b), c = ...`).
    Chaque variable cible peut etre deja declaree (reaffectation dynamique
    via assign_dynamic) ou nouvelle (declaration inferee).

    Implementation : chaque valeur de droite est evaluee dans un temporaire
    AVANT toute affectation (semantique Python : `a, b = b, a` fonctionne
    correctement - les droites sont evaluees dans leur contexte courant,
    puis les affectations sont appliquees).
    """

    @staticmethod
    def detect(tokens):
        """Retourne True si `tokens` est de la forme :
            IDENT PUNCT(,) IDENT [PUNCT(,) IDENT ...] OP(=) ...
        avec au moins deux IDENT separees par des virgules avant le `=`.
        Criteres deliberement larges (verification complete dans compile)."""
        if len(tokens) < 4:
            return False
        if not (isinstance(tokens[0], Token) and tokens[0].type == "IDENT"):
            return False
        if not (isinstance(tokens[1], Token) and tokens[1].type == "PUNCT"
                and tokens[1].value == ","):
            return False
        # cherche le premier '=' au niveau de tete (pas dans un groupe)
        i = 1
        while i < len(tokens):
            t = tokens[i]
            if isinstance(t, Token) and t.type == "OP" and t.value == "=":
                break
            i += 1
        else:
            return False
        # il doit y avoir au moins un IDENT entre la premiere virgule et le '='
        # (= au moins deux cibles au total)
        return i >= 3

    @staticmethod
    def compile(tokens, emitter):
        # -- parse des cibles (avant le '=') ----------------------------------
        eq_idx = next(
            (i for i, t in enumerate(tokens)
             if isinstance(t, Token) and t.type == "OP" and t.value == "="),
            None,
        )
        if eq_idx is None:
            raise RexResolveError("deballage invalide : '=' manquant")
        lhs_tokens = tokens[:eq_idx]
        rhs_tokens = tokens[eq_idx + 1:]
        if not rhs_tokens:
            raise RexResolveError("deballage invalide : valeur(s) manquante(s) apres '='")

        targets = REX_UnpackStatement._parse_targets(lhs_tokens)

        # -- parse du cote droit ---------------------------------------------
        # Forme 1 : plusieurs expressions separees par des virgules
        #   a, b = expr1, expr2
        # Forme 2 : une seule expression (appel de fonction retournant une list)
        #   a, b = f()
        rhs_groups = REX_UnpackStatement._split_on_commas(rhs_tokens)

        if len(rhs_groups) == 1:
            # Forme 2 : expression unique -> doit retourner une list
            REX_UnpackStatement._compile_from_list(targets, rhs_groups[0], emitter)
        else:
            # Forme 1 : N expressions pour N cibles
            REX_UnpackStatement._compile_from_scalars(targets, rhs_groups, emitter)

    # -- helpers internes -----------------------------------------------------

    @staticmethod
    def _parse_targets(lhs_tokens):
        """Extrait la liste des noms cibles depuis les tokens avant '='.
        Attend IDENT [, IDENT]* avec au moins deux noms."""
        targets = []
        expect_ident = True
        for t in lhs_tokens:
            if expect_ident:
                if not (isinstance(t, Token) and t.type == "IDENT"):
                    raise RexResolveError(
                        f"deballage invalide : identifiant attendu comme cible, "
                        f"obtenu {t!r}"
                    )
                if t.value.startswith("__rx_"):
                    raise RexResolveError(
                        f"nom de variable reserve au compilateur : {t.value}"
                    )
                targets.append(t.value)
                expect_ident = False
            else:
                if not (isinstance(t, Token) and t.type == "PUNCT"
                        and t.value == ","):
                    raise RexResolveError(
                        f"deballage invalide : ',' attendu entre les cibles, "
                        f"obtenu {t!r}"
                    )
                expect_ident = True
        if expect_ident:
            raise RexResolveError(
                "deballage invalide : identifiant attendu apres la derniere virgule"
            )
        if len(targets) < 2:
            raise RexResolveError(
                "deballage invalide : au moins deux cibles requises"
            )
        return targets

    @staticmethod
    def _split_on_commas(tokens):
        """Decoupe `tokens` sur les virgules de niveau zero (pas dans
        un groupe). Retourne une liste de listes de tokens."""
        groups = []
        current = []
        for t in tokens:
            if isinstance(t, Token) and t.type == "PUNCT" and t.value == ",":
                groups.append(current)
                current = []
            else:
                current.append(t)
        groups.append(current)
        return groups

    @staticmethod
    def _compile_from_scalars(targets, rhs_groups, emitter):
        """Forme `a, b = e1, e2` : N expressions pour N cibles."""
        if len(rhs_groups) != len(targets):
            raise RexResolveError(
                f"deballage : {len(targets)} cibles mais {len(rhs_groups)} valeurs"
            )
        # Phase 1 : evaluer toutes les droites dans des temporaires
        temps = []
        codegen = ExprCodegen(emitter)
        for grp in rhs_groups:
            if not grp:
                raise RexResolveError(
                    "deballage invalide : expression vide dans la partie droite"
                )
            node = ExprParser(grp).parse()
            ref, vtype = codegen.generate(node)
            # copie dans un temporaire frais pour garantir la semantique Python
            # (evite que `a, b = b, a` lise la valeur deja modifiee de `a`)
            tmp = emitter.new_temp_name()
            if vtype == "number":
                emitter.emit(f"add {tmp} {ref} 0;")
            elif vtype == "float":
                emitter.emit(f"add {tmp} {ref} 0.0;")
            elif vtype == "str":
                emitter.emit(f'add {tmp} {ref} "";')
            elif vtype == "bool":
                # bool : pas d'add -> on stocke le ref directement
                # (le ref est deja un temporaire isole par ExprCodegen)
                tmp = ref
            else:
                raise RexResolveError(
                    f"deballage : type '{vtype}' non supportable comme valeur \
scalaire (uniquement number/float/str/bool)"
                )
            emitter.types[tmp] = vtype
            temps.append((tmp, vtype))

        # Phase 2 : affecter chaque temporaire a sa cible
        for name, (tmp, vtype) in zip(targets, temps):
            emitter.assign_dynamic(name, tmp, vtype)

    @staticmethod
    def _compile_from_list(targets, rhs_tokens, emitter):
        """Forme `a, b = f()` : deballage d'une liste retournee par une
        fonction. La liste doit etre connue a la compilation (collection_repr
        ou elem_type). On indexe via get <liste> <type> <dest> <i>."""
        if not rhs_tokens:
            raise RexResolveError(
                "deballage invalide : expression manquante apres '='"
            )
        codegen = ExprCodegen(emitter)
        node = ExprParser(rhs_tokens).parse()
        ref, vtype = codegen.generate(node)
        if vtype not in ("list", "tuple", "set"):
            raise RexResolveError(
                f"deballage depuis une expression unique : type '{vtype}' non \
supportable (attendu une list/tuple/set retournee par une fonction)"
            )
        rexsl_ref = ref
        elem_type = emitter.get_elem_type(rexsl_ref)
        if elem_type is None:
            raise RexResolveError(
                f"deballage '{', '.join(targets)} = <liste>' : type des elements inconnu "
                "(limitation : la liste doit avoir ete declaree avec des litteraux ou \
via append() pour que le compilateur connaisse le type element)"
            )
        n = len(targets)
        for i, name in enumerate(targets):
            tmp = emitter.new_temp_name()
            emitter.declare_literal(tmp, elem_type, DEFAULT_VALUES[elem_type])
            emitter.emit(f"get {rexsl_ref} {elem_type} {tmp} {i};")
            emitter.types[tmp] = elem_type
            emitter.assign_dynamic(name, tmp, elem_type)
        # avertissement si la liste contient probablement plus d'elements
        # qu'il y a de cibles (non bloquant, on ne connait pas la longueur
        # exacte a la compilation sauf si collection_repr est present)


class REX_ReturnStatement:
    """Compile `return <expr>;` -> REX-SL `return <operande>;` (uniquement
    valide a l'interieur du corps d'un `func`, cf. Emitter.note_return).
    L'operande peut etre un litteral ou une variable/temporaire : REX-SL
    accepte les deux indifferemment pour `return`."""

    keyword = "return"

    @staticmethod
    def compile(tokens, emitter):
        expr_tokens = tokens[1:]
        if not expr_tokens:
            raise RexResolveError("'return' necessite une valeur (return <expr>;)")
        node = ExprParser(expr_tokens).parse()
        # `return None;` -> `return none;` (REX-SL 0.0.23, void return) : supporte
        # nativement depuis alpha 0.1.3 via le type 'none' reel de REX-SL.
        if node[0] == "none":
            emitter.emit("return none;")
            emitter.note_return("none")
            return
        codegen = ExprCodegen(emitter)
        ref, vtype = codegen.generate(node)
        emitter.emit(f"return {ref};")
        # Pour list/dict retournes directement par nom, on propage les types
        # d'element/valeur connus (permet a l'appelant de faire f(...)[i]).
        elem_type = None
        dict_value_type = None
        if vtype == "list" and node[0] == "ident":
            elem_type = emitter.get_elem_type(node[1])
        if vtype == "dict" and node[0] == "ident":
            dict_value_type = emitter.get_dict_value_type(node[1])
        emitter.note_return(vtype, elem_type=elem_type, dict_value_type=dict_value_type)




# =============================================================================
# INSTRUCTIONS : sauts, labels, break, continue
# =============================================================================

class REX_LabelStatement:
    """Compile `label <name>;` -> REX-SL `lbl <name>;` (declare une cible
    de saut pour 'go')."""

    keyword = "label"

    @staticmethod
    def compile(tokens, emitter):
        idx = 1
        if idx >= len(tokens) or not (isinstance(tokens[idx], Token) and tokens[idx].type == "IDENT"):
            raise RexResolveError("'label' necessite un nom (label <name>;)")
        name = tokens[idx].value
        idx += 1
        if idx != len(tokens):
            raise RexResolveError(f"jetons inattendus apres 'label {name}' : {tokens[idx:]!r}")
        emitter.emit(f"lbl {name};")


class REX_GoStatement:
    """Compile `go <name>;` -> saut inconditionnel vers l'etiquette
    `<name>`. REX-SL ne saute que si sa derniere condition ('cdn') evaluee
    est vraie -> on force systematiquement `cdn on;` juste avant, ce qui
    donne un vrai goto inconditionnel du point de vue de REX."""

    keyword = "go"

    @staticmethod
    def compile(tokens, emitter):
        idx = 1
        if idx >= len(tokens) or not (isinstance(tokens[idx], Token) and tokens[idx].type == "IDENT"):
            raise RexResolveError("'go' necessite un nom d'etiquette (go <name>;)")
        name = tokens[idx].value
        idx += 1
        if idx != len(tokens):
            raise RexResolveError(f"jetons inattendus apres 'go {name}' : {tokens[idx:]!r}")
        emitter.emit("cdn on;")
        emitter.emit(f"go {name};")


class REX_BreakStatement:
    """Compile `break;` -> saut inconditionnel vers l'etiquette de fin de
    la boucle (while/for/repeat) la plus proche qui l'englobe."""

    keyword = "break"

    @staticmethod
    def compile(tokens, emitter):
        if len(tokens) != 1:
            raise RexResolveError("'break' ne prend aucun argument")
        end_lbl = emitter.current_loop_break()
        emitter.emit("cdn on;")
        emitter.emit(f"go {end_lbl};")


class REX_ContinueStatement:
    """Compile `continue;` -> saut inconditionnel vers l'etiquette de
    l'iteration suivante (reevaluation de la condition pour `while`,
    increment puis reevaluation pour `for`/`repeat`) de la boucle la plus
    proche qui l'englobe."""

    keyword = "continue"

    @staticmethod
    def compile(tokens, emitter):
        if len(tokens) != 1:
            raise RexResolveError("'continue' ne prend aucun argument")
        continue_lbl = emitter.current_loop_continue()
        emitter.emit("cdn on;")
        emitter.emit(f"go {continue_lbl};")




# =============================================================================
# INSTRUCTIONS : appel de fonction
# =============================================================================

class REX_CallStatement:
    """Compile un appel utilise comme instruction autonome (pas dans une
    expression), 0.0.13 - deux cas :
        append(l, x);   -> opcode dedie REX-SL `append <liste> <valeur>;`
                            (deja existant), avec suivi du type d'element
                            homogene (Emitter.note_elem_type) pour que
                            l'indexation generique `l[i]` reste possible
                            ensuite.
        f(a, b);         -> fonction utilisateur 'func' appelee sans
                            recuperer sa valeur de retour (celle-ci, si
                            elle existe, est simplement ignoree - `exec`
                            ecrit RX_ret de toute facon, on ne le lit pas).
    """

    @staticmethod
    def compile(tokens, emitter):
        name = tokens[0].value
        args = ExprParser._parse_call_args(tokens[1])

        if name == "append":
            REX_CallStatement._compile_append(args, emitter)
            return

        if name in ExprCodegen.BUILTIN_ARITY:
            raise RexResolveError(
                f"'{name}(...)' utilise comme instruction : les fonctions natives ne "
                "sont utilisables que dans une expression"
            )

        info = emitter.functions.get(name)
        if info is None:
            raise RexResolveError(
                f"fonction inconnue : {name} (declarez-la avec 'func {name}(...):' avant de l'appeler)"
            )
        codegen = ExprCodegen(emitter)
        # Patch de signature pour les parametres non-annotes (meme logique que _call)
        pending = emitter.pending_func_sigs.get(name)
        if pending is not None:
            codegen._patch_untyped_func_sig(name, pending, args)
        else:
            codegen._validate_call_arg_types(name, args)
        # Injecter les sentinelles bool pour les params = None
        args = codegen._inject_none_sentinels(name, args)
        arg_tokens_str = REX_CallStatement._build_exec_args(codegen, args)
        emitter.emit(f"exec {name}" + (" " + arg_tokens_str if arg_tokens_str else "") + ";")

    @staticmethod
    def _build_exec_args(codegen, args):
        """Evalue chaque argument (positionnel ou nomme) et construit la
        portion `<arg1> <pname>=<arg2> ...` de la ligne REX-SL `exec` -
        REX-SL (exec_call) se charge lui-meme de la resolution complete
        (ordre, valeurs par defaut manquantes, verification de type),
        aucune duplication de cette logique cote REX.py."""
        pieces = []
        for spec in args:
            if spec[0] == "kwarg":
                _, pname, node = spec
                ref, _vtype = codegen.generate(node)
                pieces.append(f"{pname}={ref}")
            else:
                _, node = spec
                ref, _vtype = codegen.generate(node)
                pieces.append(ref)
        return " ".join(pieces)

    @staticmethod
    def _compile_append(args, emitter):
        if len(args) != 2 or any(spec[0] == "kwarg" for spec in args):
            raise RexResolveError(
                "append() attend exactement 2 arguments positionnels : append(liste, valeur)"
            )
        list_node = args[0][1]
        val_node = args[1][1]
        if list_node[0] != "ident":
            raise RexResolveError(
                "append() : le premier argument doit etre le nom d'une variable liste"
            )
        name = list_node[1]
        vtype = emitter.type_of(name)
        if vtype not in ("list", "tuple", "set"):
            raise RexResolveError(f"append() : '{name}' n'est pas une liste (type '{vtype}')")
        coll_ref = name
        codegen = ExprCodegen(emitter)
        val_ref, val_type = codegen.generate(val_node)
        if val_type not in ("number", "float", "bool", "str"):
            raise RexResolveError(
                f"append() : type '{val_type}' non stockable dans une liste "
                "(limitation REX-SL : number/float/bool/str uniquement)"
            )
        elem_type = emitter.get_elem_type(coll_ref)
        if elem_type is not None and elem_type != val_type:
            raise RexResolveError(
                f"append() : liste homogene de type '{elem_type}', valeur incompatible "
                f"de type '{val_type}'"
            )
        emitter.emit(f"append {coll_ref} {val_ref};")
        emitter.note_elem_type(coll_ref, val_type)
        # une collection modifiee au runtime perd son "repr" fige (affichage show()).
        emitter.collection_repr.pop(coll_ref, None)




# =============================================================================
# INSTRUCTIONS : affichage et E/S fichier
# =============================================================================

class REX_ShowStatement:
    """Compile `show(...)` exactement comme `print(...)` en Python :

        show(x)                    -> une seule valeur, end="\\n" (defaut)
        show(a, b, c)                -> plusieurs valeurs, jointes par sep=" " (defaut)
        show(a, b, sep=", ")         -> separateur personnalise
        show(x, "")                  -> forme positionnelle historique (equiv. end="")
        show(x, end="")              -> pas de retour a la ligne
        show(x, end="...")           -> tout autre 'end'
        show(a, b, sep="-", end="!") -> combinable, comme print()

    Chaque valeur (et `sep`/`end` s'ils ne sont pas des chaines) est
    convertie en texte via ExprCodegen.to_str (limite a
    number/float/str/bool, seuls types affichables par REX-SL). Toutes les
    valeurs + separateurs sont concatenes EN UNE SEULE chaine avant d'etre
    emis via un unique `show`/`showln` REX-SL final (limitation REX-SL :
    show/showln n'acceptent qu'une seule valeur a la fois)."""

    keyword = "show"

    @staticmethod
    def compile(tokens, emitter):
        idx = 1
        if idx >= len(tokens) or not isinstance(tokens[idx], list):
            raise RexResolveError(
                "'show' necessite des parentheses : show(<expr>, ...) - comme print() en Python"
            )
        arg_tokens = tokens[idx]
        idx += 1
        if idx != len(tokens):
            raise RexResolveError(
                f"jetons inattendus apres 'show(...)' : {tokens[idx:]!r}"
            )

        groups = REX_ShowStatement._split_on_commas(arg_tokens)
        if not groups or not groups[0]:
            raise RexResolveError(
                "'show' necessite au moins une valeur a afficher : show(<expr>, ...)"
            )

        codegen = ExprCodegen(emitter)
        value_groups = []   # arguments positionnels (valeurs a afficher)
        sep_tokens = None   # None = defaut (" ")
        end_tokens = None   # None = defaut ("\n")

        for i, g in enumerate(groups):
            if not g:
                raise RexResolveError("argument vide dans 'show(...)'")
            kw = REX_ShowStatement._as_kwarg(g)
            if kw is not None:
                name, val_tokens = kw
                if name == "sep":
                    if sep_tokens is not None:
                        raise RexResolveError("'sep' fourni plusieurs fois dans 'show(...)'")
                    sep_tokens = val_tokens
                elif name == "end":
                    if end_tokens is not None:
                        raise RexResolveError("'end' fourni plusieurs fois dans 'show(...)'")
                    end_tokens = val_tokens
                else:
                    raise RexResolveError(
                        f"argument nomme inconnu dans 'show(...)' : '{name}' "
                        "(seuls 'sep' et 'end' sont acceptes, comme print())"
                    )
            else:
                if i == 1 and len(groups) == 2 and end_tokens is None and sep_tokens is None:
                    # Forme historique `show(x, "...")` : le 2e argument
                    # positionnel (sans virgule supplementaire) reste
                    # traite comme 'end', pour compatibilite retro (0.0.10).
                    end_tokens = g
                else:
                    value_groups.append(g)

        if not value_groups:
            raise RexResolveError(
                "'show' necessite au moins une valeur a afficher : show(<expr>, ...)"
            )

        # -- Chemin rapide : show(coll) seule avec end par defaut ("\n") ou "" --
        # On utilise show_list/show_dict/show_set/show_tuple (REX-SL 0.0.23)
        # directement, ce qui evite la conversion en str via list_str/dict_str.
        #
        # BUGFIX (double evaluation) : l'expression de l'UNIQUE argument est
        # generee (codegen.generate) une seule fois ci-dessous, que ce
        # chemin rapide s'applique ou non. Auparavant, quand la valeur
        # n'etait PAS une collection (donc que ce chemin rapide ne
        # s'appliquait pas), le code emis par cet appel a generate() etait
        # simplement abandonne (single_ref/single_vtype non reutilises), et
        # l'expression etait re-parsee ET regeneree une seconde fois plus
        # bas via `to_str_for_value_node(ExprParser(g).parse())` -> pour
        # tout `show(<expr_avec_effet_de_bord>)` (typiquement un appel de
        # fonction), l'expression - et donc l'appel de fonction - etait
        # executee DEUX FOIS a l'execution. Selon ce que fait la fonction
        # (ex: manipulation de listes de chaines), ce double appel pouvait
        # aussi provoquer une corruption memoire / un crash au lieu d'un
        # simple gaspillage de calcul. Desormais, le (ref, type) obtenu ici
        # est systematiquement reutilise plus bas au lieu d'etre regenere.
        value_refs = []
        if len(value_groups) == 1 and sep_tokens is None:
            single_node = ExprParser(value_groups[0]).parse()
            single_ref, single_vtype = codegen.generate(single_node)
            # Chemin rapide pour le type natif 'none' (REX-SL 0.0.23) :
            # show/showln acceptent directement le litteral 'none'.
            if single_vtype == "none":
                newline = True
                if end_tokens is not None:
                    end_node = ExprParser(end_tokens).parse()
                    if end_node[0] == "lit" and isinstance(end_node[1], str):
                        newline = end_node[1] == "\n"
                    else:
                        newline = None
                if newline is True:
                    emitter.emit("showln none;")
                    return
                if newline is False:
                    emitter.emit("show none;")
                    if end_tokens is not None:
                        end_node = ExprParser(end_tokens).parse()
                        if not (end_node[0] == "lit" and end_node[1] in ("", "\n")):
                            end_ref, end_type = codegen.generate(end_node)
                            emitter.emit(f"show {codegen.to_str(end_ref, end_type)};")
                    return
                # end dynamique : tombe dans le chemin general (to_str retourne "None")
            if single_vtype in ("list", "tuple", "set", "dict"):
                show_instr = {
                    "dict": "show_dict", "set": "show_set",
                    "tuple": "show_tuple", "list": "show_list",
                }.get(single_vtype, "show_list")
                # Determine si on affiche avec ou sans retour a la ligne
                newline = True
                if end_tokens is not None:
                    end_node = ExprParser(end_tokens).parse()
                    if end_node[0] == "lit" and isinstance(end_node[1], str):
                        newline = end_node[1] == "\n"
                    else:
                        # end dynamique : on passe par le chemin general
                        newline = None
                if newline is not None:
                    nl_arg = "" if newline else " nonl"
                    emitter.emit(f"{show_instr} {single_ref}{nl_arg};")
                    if not newline and end_tokens is not None:
                        end_node = ExprParser(end_tokens).parse()
                        if not (end_node[0] == "lit" and end_node[1] in ("", "\n")):
                            end_ref, end_type = codegen.generate(end_node)
                            emitter.emit(f"show {codegen.to_str(end_ref, end_type)};")
                    return
            # Pas une collection (ou 'end' dynamique) : reutilise le (ref, type)
            # deja genere ci-dessus au lieu de re-parser/regenerer l'expression.
            value_refs.append(
                REX_ShowStatement._to_str_reuse(codegen, single_ref, single_vtype, single_node)
            )
        else:
            # -- 1) construit la chaine finale a afficher (valeurs jointes par sep) --
            for g in value_groups:
                value_refs.append(codegen.to_str_for_value_node(ExprParser(g).parse()))

        if sep_tokens is None:
            sep_ref = '" "'
        else:
            sep_node = ExprParser(sep_tokens).parse()
            if sep_node[0] == "lit" and isinstance(sep_node[1], str):
                sep_ref = codegen._quote(sep_node[1])
            else:
                sref, stype = codegen.generate(sep_node)
                sep_ref = codegen.to_str(sref, stype)

        result_ref = value_refs[0]
        for nxt in value_refs[1:]:
            if sep_ref != '""':
                tmp = emitter.new_temp_name()
                emitter.emit(f"add {tmp} {result_ref} {sep_ref};")
                emitter.types[tmp] = "str"
                result_ref = tmp
            tmp2 = emitter.new_temp_name()
            emitter.emit(f"add {tmp2} {result_ref} {nxt};")
            emitter.types[tmp2] = "str"
            result_ref = tmp2

        # -- 2) affiche la chaine finale, selon 'end' --
        if end_tokens is None:
            emitter.emit(f"showln {result_ref};")
            return

        end_node = ExprParser(end_tokens).parse()
        if end_node[0] == "lit" and isinstance(end_node[1], str):
            if end_node[1] == "\n":
                emitter.emit(f"showln {result_ref};")
                return
            if end_node[1] == "":
                emitter.emit(f"show {result_ref};")
                return

        end_ref, end_type = codegen.generate(end_node)
        end_ref = codegen.to_str(end_ref, end_type)
        emitter.emit(f"show {result_ref};")
        emitter.emit(f"show {end_ref};")

    @staticmethod
    def _to_str_reuse(codegen, ref, vtype, node):
        """Equivalent de `ExprCodegen.to_str_for_value_node(node)` mais a
        partir d'un (ref, vtype) DEJA genere par un appel precedent a
        `codegen.generate(node)` - evite de regenerer (et donc, pour un
        appel de fonction, de RE-EXECUTER) la meme expression une seconde
        fois. Le type natif 'none' (REX-SL 0.0.23) donne toujours "None"."""
        if vtype == "none":
            return codegen._quote("None")
        return codegen.to_str(ref, vtype)

    @staticmethod
    def _as_kwarg(group):
        """Reconnait un argument nomme `nom=<expr>` en tete d'un groupe
        d'arguments deja separe sur les virgules. Retourne (nom, tokens)
        ou None si ce n'est pas un argument nomme."""
        if (
            len(group) >= 2
            and isinstance(group[0], Token) and group[0].type == "IDENT"
            and isinstance(group[1], Token) and group[1].type == "OP" and group[1].value == "="
        ):
            val_tokens = group[2:]
            if not val_tokens:
                raise RexResolveError(f"valeur manquante apres '{group[0].value}=' dans 'show(...)'")
            return group[0].value, val_tokens
        return None

    @staticmethod
    def _split_on_commas(tokens):
        groups, current = [], []
        for t in tokens:
            if isinstance(t, Token) and t.type == "PUNCT" and t.value == ",":
                groups.append(current)
                current = []
            else:
                current.append(t)
        groups.append(current)
        return groups

class REX_WriteStatement:
    """Compile `write(<path>, <valeur>);` (a la Python : ecriture de
    fichier) -> REX-SL `write <path> <valeur>;` (mode "w", ecrase le
    contenu existant, ecrit la representation texte de `<valeur>`)."""

    keyword = "write"

    @staticmethod
    def compile(tokens, emitter):
        idx = 1
        if idx >= len(tokens) or not isinstance(tokens[idx], list):
            raise RexResolveError("'write' necessite des parentheses : write(<path>, <valeur>)")
        arg_tokens = tokens[idx]
        idx += 1
        if idx != len(tokens):
            raise RexResolveError(f"jetons inattendus apres 'write(...)' : {tokens[idx:]!r}")

        groups = REX_ShowStatement._split_on_commas(arg_tokens)
        if len(groups) != 2 or not groups[0] or not groups[1]:
            raise RexResolveError("'write' attend exactement 2 arguments : write(<path>, <valeur>)")

        codegen = ExprCodegen(emitter)
        path_ref, path_type = codegen.generate(ExprParser(groups[0]).parse())
        if path_type != "str":
            raise RexResolveError("'write' : le chemin (1er argument) doit etre de type 'str'")

        value_ref, value_type = codegen.generate(ExprParser(groups[1]).parse())
        if value_type not in ("number", "float", "str", "bool"):
            raise RexResolveError(
                f"'write' ne peut pas ecrire une valeur de type '{value_type}' "
                "(limitation REX-SL : number/float/str/bool uniquement)"
            )
        emitter.emit(f"write {path_ref} {value_ref};")


class REX_WritelinesStatement:
    """Compile `writelines(<path>, <liste>);` -> REX-SL
    `writelines <path> <liste>;` (ecrit `<liste>` dans `<path>`, un
    element par ligne). `<liste>` doit etre le nom d'une variable liste
    (list/tuple/set) deja declaree - REX-SL attend directement une `list`,
    pas un litteral inline."""

    keyword = "writelines"

    @staticmethod
    def compile(tokens, emitter):
        idx = 1
        if idx >= len(tokens) or not isinstance(tokens[idx], list):
            raise RexResolveError("'writelines' necessite des parentheses : writelines(<path>, <liste>)")
        arg_tokens = tokens[idx]
        idx += 1
        if idx != len(tokens):
            raise RexResolveError(f"jetons inattendus apres 'writelines(...)' : {tokens[idx:]!r}")

        groups = REX_ShowStatement._split_on_commas(arg_tokens)
        if len(groups) != 2 or not groups[0] or not groups[1]:
            raise RexResolveError(
                "'writelines' attend exactement 2 arguments : writelines(<path>, <liste>)"
            )

        codegen = ExprCodegen(emitter)
        path_ref, path_type = codegen.generate(ExprParser(groups[0]).parse())
        if path_type != "str":
            raise RexResolveError("'writelines' : le chemin (1er argument) doit etre de type 'str'")

        if not (
            len(groups[1]) == 1
            and isinstance(groups[1][0], Token) and groups[1][0].type == "IDENT"
        ):
            raise RexResolveError(
                "'writelines' : le 2e argument doit etre le nom d'une variable liste "
                "deja declaree (pas un litteral inline)"
            )
        list_name = groups[1][0].value
        list_type = emitter.type_of(list_name)
        if list_type not in ("list", "tuple", "set"):
            raise RexResolveError(
                f"'writelines' : '{list_name}' doit etre une liste (type actuel : '{list_type}')"
            )
        emitter.emit(f"writelines {path_ref} {list_name};")


class REX_ImportStatement:
    """`import "chemin";` est entierement resolu et colle AVANT toute
    analyse lexicale (voir preprocess_imports) : si ce statement atteint
    quand meme le resolveur, c'est que sa syntaxe ne correspond pas a la
    forme reconnue par le preprocesseur - on renvoie une erreur explicite
    plutot que le message generique 'instruction non geree'."""

    keyword = "import"

    @staticmethod
    def compile(tokens, emitter):
        raise RexResolveError(
            "syntaxe 'import' invalide ou non geree a ce stade. Formes supportees :\n"
            "  import \"chemin/fichier.rex\";           -- import textuel classique\n"
            "  import \"chemin/fichier.rex\" as alias;  -- import avec espace de noms\n"
            "  import module;                          -- evo-import (sans guillemets) :\n"
            "                                             cherche module.rex puis executable module\n"
            "  import module as alias;                 -- idem avec alias\n"
            "Chaque import doit occuper une ligne entiere, disponible uniquement en mode "
            "fichier (-f/--file). Les imports sont resolus avant la compilation, aucun "
            "'import' ne devrait normalement atteindre le resolveur."
        )




# =============================================================================
# INSTRUCTIONS : fonctions (func / return)
# =============================================================================

class REX_FuncStatement:
    """Compile un bloc `func <nom>(<type> <arg> [= <defaut>], ...) [-> <type>]:`
    (syntaxe a la Python : parentheses + ':' + corps indente) vers une
    vraie fonction REX-SL (`func ... ; ... endfunc ...;`).

    0.0.13 : parametres list/dict acceptes (REX-SL les passe deja comme de
    simples pointeurs RexList*/RexDict*, aucune copie necessaire - seul le
    type de RETOUR list/dict reste hors de portee d'une expression, cf.
    ExprCodegen._call), valeurs par defaut (`y=5`) et type de retour
    explicite (`-> number`, necessaire pour qu'un appel recursif utilise
    DANS une expression fonctionne des le premier passage, cf.
    Emitter.enter_func_scope) - REX-SL (func_begin/exec_call) supporte deja
    nativement les deux, aucune modification de REX-SL.py necessaire ici.

    ex:
        func add(number a, number b = 10) -> number:
            return a + b
    """

    keyword = "func"

    @staticmethod
    def compile(header_tokens, body, emitter, resolver):
        idx = 1
        if idx >= len(header_tokens) or not (
            isinstance(header_tokens[idx], Token) and header_tokens[idx].type == "IDENT"
        ):
            raise RexResolveError(
                "declaration 'func' invalide : nom de fonction attendu (func nom(...):)"
            )
        name = header_tokens[idx].value
        idx += 1

        params = []
        if idx < len(header_tokens) and isinstance(header_tokens[idx], list):
            params = REX_FuncStatement._parse_params(header_tokens[idx])
            idx += 1

        return_type = None
        if (
            idx + 1 < len(header_tokens)
            and isinstance(header_tokens[idx], Token)
            and header_tokens[idx].type == "OP" and header_tokens[idx].value == "->"
        ):
            rt_tok = header_tokens[idx + 1]
            # 0.1.3 : 'none' accepte en plus des types scalaires/collections
            # (compile en `func f ... -> none;` REX-SL, fonction C void).
            # 'none' est un KEYWORD dans le lexer (pas un IDENT), donc on
            # l'accepte explicitement ici.
            is_none_ret = (
                isinstance(rt_tok, Token)
                and rt_tok.type == "KEYWORD"
                and rt_tok.value in REX_NoneSupport.LITERALS
            )
            is_scalar_ret = (
                isinstance(rt_tok, Token) and rt_tok.type == "IDENT"
                and rt_tok.value in ("number", "float", "bool", "str", "list", "dict")
            )
            if not (is_none_ret or is_scalar_ret):
                raise RexResolveError(
                    f"declaration 'func {name}' invalide : type de retour attendu apres '->' : {rt_tok!r}"
                )
            return_type = "none" if is_none_ret else rt_tok.value
            idx += 2

        if idx != len(header_tokens):
            raise RexResolveError(
                f"jetons inattendus dans l'entete de 'func {name}' : {header_tokens[idx:]!r}"
            )
        if not body:
            raise RexResolveError(f"le corps de 'func {name}' est vide")

        # Expansion des parametres = None : pour chaque parametre avec valeur par
        # defaut None, on insere un sentinelle bool __has_<nom> = false juste avant
        # le parametre reel. Cela permet d'emuler 'arg is None' / 'arg is not None'
        # a l'interieur du corps de la fonction (voir REX_IsNoneExpr / REX_IfStatement).
        none_default_params = set()  # noms des params ayant = None comme defaut
        expanded_params = []
        for entry in params:
            vtype, pname, default_lit, elem_hint = entry[0], entry[1], entry[2], entry[3]
            flags = entry[4:]
            if default_lit == "__NONE_DEFAULT__":
                none_default_params.add(pname)
                sentinel_name = f"__has_{pname}"
                # Sentinelle booleen : false = absent (None), true = fourni
                expanded_params.append(("bool", sentinel_name, "false", None, False, False))
                # Parametre reel : valeur par defaut "zero" du type (REX-SL exige
                # un default si le parametre est omissible a l'appel)
                zero_defaults = {"number": "0", "float": "0.0", "str": '""',
                                 "bool": "false", "list": None, "dict": None}
                real_default = zero_defaults.get(vtype)
                expanded_params.append((vtype, pname, real_default, elem_hint) + flags)
            else:
                expanded_params.append(entry)

        param_types = [t for t, n, d, e, *_ in expanded_params]
        param_names = [n for t, n, d, e, *_ in expanded_params]
        defaults = {n: d for t, n, d, e, *_ in expanded_params if d is not None}

        emitter.enter_func_scope(name, param_types, param_names, defaults,
                                 explicit_return_type=return_type)
        # Enregistrer les parametres = None pour que 'x is None' soit resolvable
        # dans le corps de la fonction (via emitter.none_default_params).
        if not hasattr(emitter, "none_default_params"):
            emitter.none_default_params = {}
        emitter.none_default_params[name] = none_default_params

        for vtype, pname, _default, elem_hint, *_flags in expanded_params:
            emitter.declare_param(pname, vtype)
            # Si le parametre est un 'list' avec annotation d'element (list[number],
            # list[str]...), on enregistre le type d'element immediatement pour que
            # les operations de la fonction (l[i], for x in l, ...) fonctionnent.
            if vtype == "list" and elem_hint is not None:
                emit_name = pname
                emitter.note_elem_type(emit_name, elem_hint)

        sig_parts = []
        for vtype, pname, default_lit, _elem_hint, *_flags in expanded_params:
            piece = f"{vtype} {pname}"
            if default_lit is not None:
                piece += f" = {default_lit}"
            sig_parts.append(piece)
        sig = " ".join(sig_parts)
        header = f"func {name}" + (f" {sig}" if sig else "")
        if return_type is not None:
            header += f" -> {return_type}"
        func_line_idx = len(emitter.lines)
        emitter.emit(header + ";")

        # Enregistrer les parametres non-annotes (explicit_type=False) pour
        # permettre le patch de la signature REX-SL lors du premier appel.
        # On collecte la position (index dans expanded_params) et le nom de
        # chaque parametre dont le type a ete infere (pas annote explicitement).
        untyped = []
        for pos, entry in enumerate(expanded_params):
            # Les sentinelles bool __has_<x> ont 6 elements (pas de explicit_type) ;
            # les params reels en ont 7, le 7eme etant explicit_type.
            if len(entry) >= 7 and not entry[6]:
                untyped.append((pos, entry[1]))  # (position_dans_sig, param_name)
        if untyped:
            emitter.pending_func_sigs[name] = {
                "line_idx": func_line_idx,
                "untyped_positions": untyped,
                "expanded_params": list(expanded_params),
                "return_type": return_type,
            }

        resolver.compile_body(body)

        # Si des params non-annotes existent, enregistrer l'indice de fin de corps
        # pour permettre la correction retroactive du corps dans _patch_untyped_func_sig.
        if untyped:
            emitter.pending_func_sigs[name]["body_end_idx"] = len(emitter.lines)

        emitter.emit(f"endfunc {name};")

        emitter.exit_func_scope()

    @staticmethod
    def _parse_params(arg_tokens):
        """Decoupe `<type1> <arg1> [= <defaut1>], <type2> <arg2>, ...`
        (contenu deja "nu" du `(...)`) sur les virgules de premier niveau,
        chaque segment devant etre `<type> <nom> [= <litteral>]`. Retourne
        une liste de (type, nom, defaut_litteral_rexsl_ou_None)."""
        if not arg_tokens:
            return []
        groups = []
        current = []
        for t in arg_tokens:
            if isinstance(t, Token) and t.type == "PUNCT" and t.value == ",":
                groups.append(current)
                current = []
            else:
                current.append(t)
        groups.append(current)

        params = []
        seen = set()
        args_param = None    # nom du *args, si present
        kwargs_param = None  # nom du **kwargs, si present
        ELEM_TYPES = ("number", "float", "bool", "str")
        for g in groups:
            if not g:
                raise RexResolveError("parametre vide dans la declaration de fonction")
            # Detection *args
            if (
                len(g) >= 1
                and isinstance(g[0], Token) and g[0].type == "OP" and g[0].value == "*"
                and len(g) >= 2
                and isinstance(g[1], Token) and g[1].type == "IDENT"
            ):
                if args_param is not None:
                    raise RexResolveError("un seul '*args' est autorise par fonction")
                if kwargs_param is not None:
                    raise RexResolveError("'*args' doit apparaitre avant '**kwargs'")
                args_param = g[1].value
                if args_param in seen:
                    raise RexResolveError(f"parametre duplique : {args_param}")
                seen.add(args_param)
                # *args est represente comme un parametre 'list' cote REX-SL
                params.append(("list", args_param, None, None))
                params[-1] = ("list", args_param, None, None, True, False)  # (type,nom,default,elem,is_args,is_kwargs)
                continue
            # Detection **kwargs
            if (
                len(g) >= 2
                and isinstance(g[0], Token) and g[0].type == "OP" and g[0].value == "**"
                and isinstance(g[1], Token) and g[1].type == "IDENT"
            ):
                if kwargs_param is not None:
                    raise RexResolveError("un seul '**kwargs' est autorise par fonction")
                kwargs_param = g[1].value
                if kwargs_param in seen:
                    raise RexResolveError(f"parametre duplique : {kwargs_param}")
                seen.add(kwargs_param)
                # **kwargs est represente comme un parametre 'dict' cote REX-SL
                params.append(("dict", kwargs_param, None, None, False, True))
                continue
            elem_type_hint = None
            if (
                len(g) >= 2
                and isinstance(g[0], Token) and g[0].type == "IDENT" and g[0].value == "list"
                and isinstance(g[1], Group) and g[1].kind == "[]"
            ):
                inner = list(g[1].items)
                if (
                    len(inner) == 1
                    and isinstance(inner[0], Token) and inner[0].type == "IDENT"
                    and inner[0].value in ELEM_TYPES
                ):
                    elem_type_hint = inner[0].value
                    g = [g[0]] + g[2:]  # retire le [elemtype] pour la suite
                else:
                    raise RexResolveError(
                        f"annotation 'list[...]' invalide (attendu : list[number], "
                        f"list[float], list[str] ou list[bool]) : {g[1]!r}"
                    )
            KNOWN_TYPES = ("number", "float", "bool", "str", "list", "dict")
            # Detecte si le premier token est un type connu -> syntaxe typee
            # sinon -> parametre non type.
            # Si non annote ET valeur par defaut = None, le type sera resolu
            # apres (voir ci-dessous) selon ce qui est passe a l'appel.
            explicit_type = True  # sera mis a False si le type n'est pas annote
            if (
                len(g) >= 2
                and isinstance(g[0], Token) and g[0].type == "IDENT"
                and g[0].value in KNOWN_TYPES
                and isinstance(g[1], Token) and g[1].type in ("IDENT", "KEYWORD")
            ):
                vtype, pname = g[0].value, g[1].value
                rest = g[2:]
            elif (
                len(g) >= 1
                and isinstance(g[0], Token) and g[0].type == "IDENT"
                and g[0].value not in KNOWN_TYPES
            ):
                vtype, pname = "number", g[0].value
                rest = g[1:]
                explicit_type = False
            else:
                raise RexResolveError(
                    f"parametre de fonction invalide (attendu : [type] nom [= defaut]) : {g!r}"
                )
            if elem_type_hint is not None and vtype != "list":
                raise RexResolveError(
                    f"annotation '[elemtype]' uniquement valide sur un parametre 'list' (pas '{vtype}')"
                )
            default_lit = None
            is_none_default = False
            if rest:
                if not (
                    len(rest) >= 2
                    and isinstance(rest[0], Token) and rest[0].type == "OP" and rest[0].value == "="
                ):
                    raise RexResolveError(
                        f"parametre '{pname}' invalide apres le nom (attendu '= <defaut>') : {g!r}"
                    )
                default_tokens = rest[1:]
                default_node = ExprParser(default_tokens).parse()
                # Valeur par defaut None : parametre optionnel (= None en Python)
                # Represente en interne par le marqueur "__NONE_DEFAULT__" et un
                # booleen sentinelle __has_<nom> cote REX-SL.
                if default_node[0] == "none":
                    is_none_default = True
                    default_lit = "__NONE_DEFAULT__"
                    # Sans annotation de type explicite, un param = None accepte
                    # n'importe quelle valeur scalaire -> on utilise str comme
                    # type universel (le plus flexible cote REX-SL).
                    if not explicit_type:
                        vtype = "str"
                elif default_node[0] != "lit":
                    raise RexResolveError(
                        f"parametre '{pname}' : la valeur par defaut doit etre un litteral "
                        "(number/float/str/bool/None), pas une expression"
                    )
                else:
                    default_ref, default_type = ExprCodegen(None)._literal(default_node[1])
                    if default_type == vtype:
                        default_lit = default_ref
                    elif vtype == "float" and default_type == "number":
                        default_lit = repr(float(default_node[1]))
                    else:
                        raise RexResolveError(
                            f"parametre '{pname}' : valeur par defaut de type '{default_type}' "
                            f"incompatible avec le type declare '{vtype}'"
                        )
            if pname in seen:
                raise RexResolveError(f"parametre duplique : {pname}")
            seen.add(pname)
            # 7-tuple : (type, nom, defaut_rexsl, elem_type_hint, is_args, is_kwargs, explicit_type)
            # default_lit == "__NONE_DEFAULT__" si le defaut est None (is_none_default).
            # explicit_type == False si le parametre n'a pas ete annote (type infere "number").
            params.append((vtype, pname, default_lit, elem_type_hint, False, False, explicit_type))
        return params




# =============================================================================
# INSTRUCTIONS : boucles (repeat, while, for)
# =============================================================================

class REX_RepeatStatement:
    """Compile un bloc `repeat <expr>:` (corps indente) en une veritable
    boucle REX-SL (compteur + lbl/cdn/go), executee `<expr>` fois au
    RUNTIME (le corps n'est jamais deroule/duplique a la compilation) :

        repeat 3:
            showln "hi"

    La forme historique `repeat <expr> times:` reste egalement acceptee
    (le mot-cle `times` final est simplement optionnel) :

        repeat 3 times:
            showln "hi"

    equivaut a :
        i = 0
        while i < <expr>:
            <corps>
            i += 1
    """

    keyword = "repeat"

    @staticmethod
    def compile(header_tokens, body, emitter, resolver):
        expr_tokens = header_tokens[1:]
        if (
            expr_tokens
            and isinstance(expr_tokens[-1], Token)
            and expr_tokens[-1].type == "KEYWORD"
            and expr_tokens[-1].value == "times"
        ):
            expr_tokens = expr_tokens[:-1]  # 'times' final optionnel, simple sucre syntaxique

        if not expr_tokens:
            raise RexResolveError("expression manquante apres 'repeat' (repeat <expr>: ou repeat <expr> times:)")
        if not body:
            raise RexResolveError("le corps de 'repeat' est vide")

        node = ExprParser(expr_tokens).parse()
        codegen = ExprCodegen(emitter)
        ref, vtype = codegen.generate(node)
        if vtype != "number":
            raise RexResolveError(
                f"'repeat ... times' attend un nombre entier (number), pas '{vtype}'"
            )

        loop_id = emitter.new_loop_id()
        counter = f"__rx_rep{loop_id}_i"
        limit = f"__rx_rep{loop_id}_n"
        lbl_start = f"__rx_rep{loop_id}_start"
        lbl_body = f"__rx_rep{loop_id}_body"
        lbl_end = f"__rx_rep{loop_id}_end"

        emitter.declare_literal(counter, "number", "0")
        # copie la borne dans sa propre variable : evite de re-evaluer
        # l'expression `<expr>` a chaque tour, et permet d'y stocker un
        # litteral ou une expression calculee indifferemment.
        emitter.assign_computed(limit, ref, vtype, "number")

        lbl_step = f"__rx_rep{loop_id}_step"

        emitter.emit(f"lbl {lbl_start};")
        emitter.emit(f"cdn less {counter} {limit};")
        emitter.emit(f"go {lbl_body};")
        emitter.emit("cdn on;")
        emitter.emit(f"go {lbl_end};")
        emitter.emit(f"lbl {lbl_body};")
        emitter.push_loop_labels(lbl_step, lbl_end)
        resolver.compile_body(body)
        emitter.pop_loop_labels()
        emitter.emit(f"lbl {lbl_step};")
        emitter.emit(f"add {counter} {counter} 1;")
        emitter.emit("cdn on;")
        emitter.emit(f"go {lbl_start};")
        emitter.emit(f"lbl {lbl_end};")


class REX_WhileStatement:
    """Compile un bloc `while <cond>:` (corps indente) en veritable
    boucle REX-SL (lbl/cdn/go), executee au RUNTIME (jamais deroulee a la
    compilation) :

        while a < 10:
            a += 1

    `<cond>` reutilise exactement le meme compilateur de conditions
    complexes que `if`/`elif` (and/or/not, parentheses de groupement) via
    REX_IfStatement._compile_cond_tree. `break`/`continue` sont geres via
    Emitter.push_loop_labels/pop_loop_labels ('continue' revient a la
    reevaluation de la condition, comme en Python : pas d'increment
    implicite propre a `while`)."""

    keyword = "while"

    @staticmethod
    def compile(header_tokens, body, emitter, resolver):
        cond_tokens = header_tokens[1:]
        if not cond_tokens:
            raise RexResolveError("condition manquante apres 'while' (while <cond>:)")
        if not body:
            raise RexResolveError("le corps de 'while' est vide")

        loop_id = emitter.new_loop_id()
        start_lbl = f"__rx_while{loop_id}_start"
        body_lbl = f"__rx_while{loop_id}_body"
        end_lbl = f"__rx_while{loop_id}_end"

        emitter.emit(f"lbl {start_lbl};")
        REX_IfStatement._compile_cond_tree(cond_tokens, emitter, body_lbl, end_lbl)
        emitter.emit(f"lbl {body_lbl};")
        emitter.push_loop_labels(start_lbl, end_lbl)
        resolver.compile_body(body)
        emitter.pop_loop_labels()
        emitter.emit("cdn on;")
        emitter.emit(f"go {start_lbl};")
        emitter.emit(f"lbl {end_lbl};")


class REX_ForStatement:
    """Compile les formes `for ... in ...:` (corps indente) en boucles
    REX-SL, TOUJOURS executees au RUNTIME/a la compilation reelle (jamais
    de simulation de resultat) :

        for i in range(5):                  # 0, 1, 2, 3, 4        (runtime)
            show(i)
        for c in "bonjour":                  # 'b','o','n','j','o','u','r' (runtime)
            show(c)
        for i, c in enumerate("abc"):        # (0,'a') (1,'b') (2,'c')     (runtime)
            show(i); show(c)
        for x in [1, 2, 3]:                  # deroule A LA COMPILATION
            show(x)                          # (litteral ecrit directement ici)
        for i, x in enumerate([10, 20, 30]): # idem, avec index
            show(i); show(x)

    Formes supportees pour la partie `in ...` :
      - `range(...)` (1 a 3 arguments comme en Python) : boucle compteur
        classique, jamais deroulee.
      - une expression de type `str` : boucle runtime caractere par
        caractere (via les opcodes REX-SL `len`/`charat`), jamais deroulee.
      - un LITTERAL de collection ecrit directement ici (`[..]`, `(..)`,
        `{..}`) : REX-SL n'exposant aucune primitive de longueur de liste
        pour une VARIABLE `list` (donc pas d'iteration directe sur une
        variable-liste), un litteral ecrit en toutes lettres est en
        revanche connu de REX a la compilation -> la boucle est deroulee
        (chaque tour du corps est emis autant de fois qu'il y a
        d'elements), `break`/`continue` restant geres normalement via des
        etiquettes partagees entre les tours deroules.
      - `enumerate(<l'une des deux formes ci-dessus>)` avec DEUX variables
        `for <index>, <valeur> in enumerate(...):` (pas de deballage de
        tuple general, uniquement cette forme).

    `break`/`continue` sont geres via Emitter.push_loop_labels/
    pop_loop_labels dans tous les cas."""

    keyword = "for"

    @staticmethod
    def compile(header_tokens, body, emitter, resolver):
        var_names, idx = REX_ForStatement._parse_target_vars(header_tokens, 1)

        if idx >= len(header_tokens) or not (
            isinstance(header_tokens[idx], Token)
            and header_tokens[idx].type == "KEYWORD"
            and header_tokens[idx].value == "in"
        ):
            raise RexResolveError(
                "boucle 'for' invalide : mot-cle 'in' attendu "
                "(for <nom> in ... :  /  for <i>, <v> in enumerate(...):)"
            )
        idx += 1
        remaining = header_tokens[idx:]
        if not remaining:
            raise RexResolveError("boucle 'for' invalide : iterable manquant apres 'in'")
        if not body:
            raise RexResolveError("le corps de 'for' est vide")

        is_range = (
            len(var_names) == 1
            and isinstance(remaining[0], Token)
            and remaining[0].type == "IDENT"
            and remaining[0].value == "range"
            and len(remaining) == 2
            and isinstance(remaining[1], list)
        )
        is_enumerate = (
            isinstance(remaining[0], Token)
            and remaining[0].type == "IDENT"
            and remaining[0].value == "enumerate"
            and len(remaining) == 2
            and isinstance(remaining[1], list)
        )

        if is_range:
            REX_ForStatement._compile_range(var_names[0], remaining[1], body, emitter, resolver)
            return

        if is_enumerate:
            if len(var_names) != 2:
                raise RexResolveError(
                    "'enumerate(...)' dans un 'for' necessite exactement deux variables "
                    "cibles : for <index>, <valeur> in enumerate(...):"
                )
            REX_ForStatement._compile_iterable(
                var_names, remaining[1], body, emitter, resolver, with_index=True
            )
            return

        if len(var_names) != 1:
            raise RexResolveError(
                "'for <a>, <b> in ...:' n'est supporte qu'avec 'enumerate(...)' du cote "
                "droit (pas de deballage de tuple general)"
            )
        REX_ForStatement._compile_iterable(
            var_names, remaining, body, emitter, resolver, with_index=False
        )

    @staticmethod
    def _parse_target_vars(header_tokens, idx):
        """Parse une ou deux variables cibles (`for a in ...` / `for a, b
        in ...`) a partir de `idx`, retourne (liste_de_noms, nouvel_idx)."""
        if idx >= len(header_tokens) or not (
            isinstance(header_tokens[idx], Token) and header_tokens[idx].type == "IDENT"
        ):
            raise RexResolveError(
                "boucle 'for' invalide : nom de variable attendu apres 'for'"
            )
        names = [header_tokens[idx].value]
        idx += 1
        if (
            idx < len(header_tokens)
            and isinstance(header_tokens[idx], Token)
            and header_tokens[idx].type == "PUNCT"
            and header_tokens[idx].value == ","
        ):
            idx += 1
            if idx >= len(header_tokens) or not (
                isinstance(header_tokens[idx], Token) and header_tokens[idx].type == "IDENT"
            ):
                raise RexResolveError(
                    "boucle 'for' invalide : nom de variable attendu apres ','"
                )
            names.append(header_tokens[idx].value)
            idx += 1
        for n in names:
            if n.startswith("__rx_"):
                raise RexResolveError(f"nom de variable reserve au compilateur : {n}")
        if len(set(names)) != len(names):
            raise RexResolveError("boucle 'for' invalide : variables cibles identiques")
        return names, idx

    @staticmethod
    def _compile_iterable(var_names, iterable_tokens, body, emitter, resolver, with_index):
        """Route vers le deroulement a la compilation (litteral de collection
        ecrit directement dans l'entete), vers la boucle runtime element par
        element sur une VARIABLE list/tuple/set (0.0.13, len()+get()
        desormais generiques cote REX-SL - cf _compile_list_var_iteration),
        ou vers la boucle runtime caractere-par-caractere (expression de
        type 'str')."""
        collection = None
        if len(iterable_tokens) == 1:
            collection = REX_CollectionLiteral.detect(iterable_tokens, None)
        if collection is not None:
            kind, payload = collection
            REX_ForStatement._compile_unrolled(var_names, payload, body, emitter, resolver, with_index)
            return

        # variable list/tuple/set (pas un litteral) : boucle RUNTIME via
        # len()+get() (0.0.13) plutot que le deroulement a la compilation
        # (impossible ici, la taille n'est pas connue statiquement).
        probe_codegen = ExprCodegen(emitter)
        probe_ref, probe_type = probe_codegen.generate(ExprParser(iterable_tokens).parse())
        if probe_type in ("list", "tuple", "set"):
            REX_ForStatement._compile_list_var_iteration(
                var_names, probe_ref, probe_type, body, emitter, resolver, with_index
            )
            return

        REX_ForStatement._compile_str_iteration(
            var_names, iterable_tokens, body, emitter, resolver, with_index
        )

    @staticmethod
    def _compile_list_var_iteration(var_names, list_ref, list_type, body, emitter, resolver, with_index):
        """Boucle RUNTIME element par element sur une VARIABLE list/tuple/
        set (0.0.13), via les opcodes REX-SL generiques `len`/`get` (le
        type d'element doit etre connu a la compilation - liste homogene,
        cf. Emitter.elem_types - exactement comme pour l'indexation
        generique `l[i]`, cf. ExprCodegen._index). Mirroir de
        _compile_str_iteration mais avec `get` au lieu de `charat`."""
        elem_type = emitter.get_elem_type(list_ref)
        if elem_type is None:
            raise RexResolveError(
                "boucle 'for ... in <liste>:' impossible : type d'element inconnu ou "
                "heterogene (la liste doit contenir des elements d'un seul type "
                "number/float/str/bool, tous connus a la compilation)"
            )

        value_name = var_names[-1]
        index_name = var_names[0] if with_index else None

        loop_id = emitter.new_loop_id()
        start_lbl = f"__rx_forlst{loop_id}_start"
        body_lbl = f"__rx_forlst{loop_id}_body"
        step_lbl = f"__rx_forlst{loop_id}_step"
        end_lbl = f"__rx_forlst{loop_id}_end"
        len_var = f"__rx_forlst{loop_id}_len"
        idx_var = f"__rx_forlst{loop_id}_i"
        elem_var = f"__rx_forlst{loop_id}_e"

        emitter.declare_literal(len_var, "number")
        emitter.emit(f"len {len_var} {list_ref};")
        emitter.declare_literal(idx_var, "number", "0")
        if elem_type == "str":
            # BUGFIX (double free / corruption memoire) : NE PAS pre-declarer
            # 'elem_var' ici via `var str elem_var "";`. REX-SL.py (list_get)
            # ne traite un `get <liste> str <dest> <idx>;` comme un pointeur
            # EMPRUNTE (non heap-tracke, proprietaire = la liste) QUE lorsque
            # 'dest' n'est pas deja declaree au moment ou ce 'get' est compile
            # (chemin d'auto-declaration, cf. REX_SL_CODE.list_get). Si
            # 'elem_var' est pre-declaree ici comme pour number/float/bool,
            # le 'get' emis plus bas dans la boucle tombe dans le chemin
            # "classique" (_collection_dest_field_or_decl) : simple
            # reaffectation de pointeur SANS liberer l'ancienne valeur et
            # SANS retirer 'elem_var' du heap-tracking. En fin de fonction,
            # 'elem_var' contient alors le pointeur EMPRUNTE du DERNIER
            # element de la liste, mais est quand meme libere comme s'il en
            # etait proprietaire -> corruption de la liste source, puis
            # double free/segfault quand celle-ci est liberee a son tour
            # (observe : "munmap_chunk(): invalid pointer"). En laissant le
            # premier (et unique) 'get' de la boucle auto-declarer 'elem_var',
            # on beneficie du chemin sur (non heap-tracke).
            emitter.types[elem_var] = elem_type
        else:
            emitter.declare_literal(elem_var, elem_type, DEFAULT_VALUES[elem_type])

        emitter.emit(f"lbl {start_lbl};")
        emitter.emit(f"cdn less {idx_var} {len_var};")
        emitter.emit(f"go {body_lbl};")
        emitter.emit("cdn on;")
        emitter.emit(f"go {end_lbl};")
        emitter.emit(f"lbl {body_lbl};")

        emitter.emit(f"get {list_ref} {elem_type} {elem_var} {idx_var};")
        emitter.assign_dynamic(value_name, elem_var, elem_type)
        if with_index:
            emitter.assign_dynamic(index_name, idx_var, "number")

        emitter.push_loop_labels(step_lbl, end_lbl)
        resolver.compile_body(body)
        emitter.pop_loop_labels()
        emitter.emit(f"lbl {step_lbl};")
        emitter.emit(f"add {idx_var} {idx_var} 1;")
        emitter.emit("cdn on;")
        emitter.emit(f"go {start_lbl};")
        emitter.emit(f"lbl {end_lbl};")

    @staticmethod
    def _compile_unrolled(var_names, payload, body, emitter, resolver, with_index):
        """Deroule `for [i,] v in <litteral>:` A LA COMPILATION : chaque
        element du litteral produit une copie du corps, precedee de
        l'affectation de la (des) variable(s) cible(s). `break`/`continue`
        restent geres via de vraies etiquettes REX-SL (continue saute a la
        fin du tour courant, break a la toute fin)."""
        if not payload:
            return  # collection vide : le corps ne s'execute jamais
        codegen = ExprCodegen(emitter)
        value_name = var_names[-1]
        index_name = var_names[0] if with_index else None
        loop_id = emitter.new_loop_id()
        end_lbl = f"__rx_forin{loop_id}_end"
        for i, elem_tokens in enumerate(payload):
            if not elem_tokens:
                raise RexResolveError("element de collection vide dans 'for ... in [...]:'")
            ref, vtype = codegen.generate(ExprParser(elem_tokens).parse())
            if vtype not in ("number", "float", "str", "bool"):
                raise RexResolveError(
                    f"element de type '{vtype}' non supporte comme valeur de boucle "
                    "(limitation REX-SL : number/float/str/bool uniquement)"
                )
            emitter.assign_dynamic(value_name, ref, vtype)
            if with_index:
                emitter.assign_dynamic(index_name, str(i), "number")
            cont_lbl = f"__rx_forin{loop_id}_c{i}"
            emitter.push_loop_labels(cont_lbl, end_lbl)
            resolver.compile_body(body)
            emitter.pop_loop_labels()
            emitter.emit(f"lbl {cont_lbl};")
        emitter.emit(f"lbl {end_lbl};")

    @staticmethod
    def _compile_str_iteration(var_names, iterable_tokens, body, emitter, resolver, with_index):
        """Boucle RUNTIME caractere par caractere sur une expression de type
        'str', via les opcodes REX-SL `len`/`charat` (jamais deroulee a la
        compilation - la longueur n'est connue qu'a l'execution)."""
        codegen = ExprCodegen(emitter)
        str_ref, str_type = codegen.generate(ExprParser(iterable_tokens).parse())
        if str_type != "str":
            raise RexResolveError(
                f"boucle 'for ... in <expr>:' : type '{str_type}' non iterable. Seules "
                "les chaines ('str', caractere par caractere) et les litteraux de "
                "collection ecrits directement dans l'entete (ex: for x in [1, 2, 3]:) "
                "le sont - REX-SL n'expose aucune primitive de longueur pour une "
                "VARIABLE de type liste/dict."
            )

        value_name = var_names[-1]
        index_name = var_names[0] if with_index else None

        loop_id = emitter.new_loop_id()
        start_lbl = f"__rx_forstr{loop_id}_start"
        body_lbl = f"__rx_forstr{loop_id}_body"
        step_lbl = f"__rx_forstr{loop_id}_step"
        end_lbl = f"__rx_forstr{loop_id}_end"
        len_var = f"__rx_forstr{loop_id}_len"
        idx_var = f"__rx_forstr{loop_id}_i"
        char_var = f"__rx_forstr{loop_id}_c"

        emitter.declare_literal(len_var, "number")
        emitter.emit(f"len {len_var} {str_ref};")
        emitter.declare_literal(idx_var, "number", "0")
        emitter.declare_literal(char_var, "str", '""')

        emitter.emit(f"lbl {start_lbl};")
        emitter.emit(f"cdn less {idx_var} {len_var};")
        emitter.emit(f"go {body_lbl};")
        emitter.emit("cdn on;")
        emitter.emit(f"go {end_lbl};")
        emitter.emit(f"lbl {body_lbl};")

        emitter.emit(f"charat {char_var} {str_ref} {idx_var};")
        emitter.assign_dynamic(value_name, char_var, "str")
        if with_index:
            emitter.assign_dynamic(index_name, idx_var, "number")

        emitter.push_loop_labels(step_lbl, end_lbl)
        resolver.compile_body(body)
        emitter.pop_loop_labels()
        emitter.emit(f"lbl {step_lbl};")
        emitter.emit(f"add {idx_var} {idx_var} 1;")
        emitter.emit("cdn on;")
        emitter.emit(f"go {start_lbl};")
        emitter.emit(f"lbl {end_lbl};")

    @staticmethod
    def _compile_range(var_name, range_args_tokens, body, emitter, resolver):
        """Compile `for <nom> in range(...):` (forme historique, 0.0.11) :
        veritable boucle REX-SL (compteur + lbl/cdn/go), jamais deroulee."""
        arg_groups = REX_ForStatement._split_on_commas(range_args_tokens)
        if len(arg_groups) == 1:
            start_tokens, stop_tokens, step_tokens = None, arg_groups[0], None
        elif len(arg_groups) == 2:
            start_tokens, stop_tokens, step_tokens = arg_groups[0], arg_groups[1], None
        elif len(arg_groups) == 3:
            start_tokens, stop_tokens, step_tokens = arg_groups[0], arg_groups[1], arg_groups[2]
        else:
            raise RexResolveError("range() attend 1, 2 ou 3 arguments (comme en Python)")
        if not stop_tokens or (start_tokens is not None and not start_tokens) or (
            step_tokens is not None and not step_tokens
        ):
            raise RexResolveError("argument vide dans range(...)")

        codegen = ExprCodegen(emitter)

        if start_tokens is not None:
            start_ref, start_type = codegen.generate(ExprParser(start_tokens).parse())
        else:
            start_ref, start_type = "0", "number"
        if start_type != "number":
            raise RexResolveError("range(): les bornes doivent etre de type 'number'")

        stop_ref, stop_type = codegen.generate(ExprParser(stop_tokens).parse())
        if stop_type != "number":
            raise RexResolveError("range(): les bornes doivent etre de type 'number'")

        if step_tokens is not None:
            step_node = ExprParser(step_tokens).parse()
            step_value = REX_ForStatement._literal_int_or_none(step_node)
            if step_value is None:
                raise RexResolveError(
                    "range(): le pas ('step') doit etre un entier litteral connu a la "
                    "compilation (limitation REX-SL, ex: range(a, b, -1), pas range(a, b, s))"
                )
            if step_value == 0:
                raise RexResolveError("range(): le pas ne peut pas etre 0")
            step_ref, step_type = codegen.generate(step_node)
        else:
            step_value = 1
            step_ref, step_type = "1", "number"

        loop_id = emitter.new_loop_id()
        start_lbl = f"__rx_for{loop_id}_start"
        body_lbl = f"__rx_for{loop_id}_body"
        step_lbl = f"__rx_for{loop_id}_step"
        end_lbl = f"__rx_for{loop_id}_end"
        limit = f"__rx_for{loop_id}_limit"
        step_var = f"__rx_for{loop_id}_stepv"

        # Variable de boucle : reassignee (pas redeclaree) si un 'for'
        # precedent a deja declare le meme nom en 'number' non explicite -
        # permet plusieurs 'for i in range(...)' successifs sur le meme nom.
        if emitter.type_of_or_none(var_name) == "number" and not emitter.is_explicit_type(var_name):
            emitter.reassign(var_name, start_ref, "number")
        else:
            emitter.assign_computed(var_name, start_ref, start_type, "number")
        emitter.assign_computed(limit, stop_ref, stop_type, "number")
        emitter.assign_computed(step_var, step_ref, step_type, "number")

        cmp_op = "less" if step_value > 0 else "greater"
        var_ref = var_name

        emitter.emit(f"lbl {start_lbl};")
        emitter.emit(f"cdn {cmp_op} {var_ref} {limit};")
        emitter.emit(f"go {body_lbl};")
        emitter.emit("cdn on;")
        emitter.emit(f"go {end_lbl};")
        emitter.emit(f"lbl {body_lbl};")
        emitter.push_loop_labels(step_lbl, end_lbl)
        resolver.compile_body(body)
        emitter.pop_loop_labels()
        emitter.emit(f"lbl {step_lbl};")
        emitter.emit(f"add {var_ref} {var_ref} {step_var};")
        emitter.emit("cdn on;")
        emitter.emit(f"go {start_lbl};")
        emitter.emit(f"lbl {end_lbl};")

    @staticmethod
    def _literal_int_or_none(node):
        """Retourne la valeur entiere si `node` est un litteral entier
        (eventuellement precede d'un moins unaire), sinon None."""
        if node[0] == "lit" and isinstance(node[1], int) and not isinstance(node[1], bool):
            return node[1]
        if node[0] == "neg":
            inner = REX_ForStatement._literal_int_or_none(node[1])
            if inner is not None:
                return -inner
        return None

    @staticmethod
    def _split_on_commas(tokens):
        groups, current = [], []
        for t in tokens:
            if isinstance(t, Token) and t.type == "PUNCT" and t.value == ",":
                groups.append(current)
                current = []
            else:
                current.append(t)
        groups.append(current)
        return groups




# =============================================================================
# INSTRUCTIONS : conditionnel (if / elif / else)
# =============================================================================

class REX_IfStatement:
    """Compile une chaine `if <cond>: / elif <cond>: / else:` (syntaxe a
    la Python, corps indentes) en veritable branchement REX-SL via
    lbl/cdn/go (aucune duplication de code, tout est evalue au runtime) :

        if a > b:
            <body1>
        elif a == b:
            <body2>
        else:
            <body3>

    Conditions complexes supportees (depuis 0.0.7) :
        if a > 3 and b < 10:   -> court-circuit AND (saute au 'next' si l'un est faux)
        if a == 0 or b == 0:   -> court-circuit OR (saute au 'body' si l'un est vrai)
        if not (a == b):       -> inversion de la condition
        if (a > 0) and (b > 0) or c == 1:  -> parentheses de groupement

    La precedence est : NOT > comparaison > AND > OR (comme Python).
    La compilation genere une sequence de cdn/go REX-SL pour chaque clause
    atomique, avec court-circuit logique."""

    COMPARATORS = {"==", "!=", "<", "<=", ">", ">="}
    # Mapping operateur comparaison -> opcode cdn REX-SL. Les noms utilises ici
    # DOIVENT correspondre exactement aux mots-cles reconnus par REX-SL.py
    # (cf. CDN_WORD_OPS : "equal"/"eq", "not_equal"/"different"/"neq"/"ne",
    # "greater"/"gt", "less"/"lt", "greater_equal"/"ge", "less_equal"/"le") -
    # "nequal", "lequal" et "gequal" n'existent PAS cote REX-SL et faisaient
    # echouer toute condition '!=', '<=' ou '>=' a la compilation REX-SL
    # avec "operateur de condition non gere".
    CDN_OPS = {
        "==": "equal",
        "!=": "not_equal",
        "<":  "less",
        "<=": "less_equal",
        ">":  "greater",
        ">=": "greater_equal",
    }
    # Inverses pour 'not'
    CDN_OPS_INVERTED = {
        "==": "not_equal",
        "!=": "equal",
        "<":  "greater_equal",
        "<=": "greater",
        ">":  "less_equal",
        ">=": "less",
    }

    @staticmethod
    def compile(chain, emitter, resolver):
        """`chain` est la liste (dans l'ordre) des _Block `if`/`elif`/
        (`else` en dernier, optionnel) qui forment une seule instruction
        conditionnelle."""
        if_id = emitter.new_loop_id()
        end_lbl = f"__rx_if{if_id}_end"
        last = len(chain) - 1

        for idx, block in enumerate(chain):
            head = block.tokens[0].value  # "if" / "elif" / "else"

            if head == "else":
                if idx != last:
                    raise RexResolveError("'else' doit etre le dernier bloc d'une chaine if/elif/else")
                resolver.compile_body(block.body)
                continue

            cond_tokens = block.tokens[1:]
            if not cond_tokens:
                raise RexResolveError(f"condition manquante apres '{head}'")

            body_lbl = f"__rx_if{if_id}_{idx}_body"
            next_lbl = end_lbl if idx == last else f"__rx_if{if_id}_{idx}_next"

            # Compile la condition complexe (and/or/not) en cdn/go REX-SL.
            # true_lbl/false_lbl sont les destinations REELLES (concretes) :
            # `body_lbl` est place immediatement apres, `next_lbl` ne l'est
            # pas (il faut donc explicitement y sauter dans le cas faux).
            REX_IfStatement._compile_cond_tree(cond_tokens, emitter, body_lbl, next_lbl)

            emitter.emit(f"lbl {body_lbl};")
            resolver.compile_body(block.body)
            emitter.emit("cdn on;")
            emitter.emit(f"go {end_lbl};")
            if idx != last:
                emitter.emit(f"lbl {next_lbl};")

        emitter.emit(f"lbl {end_lbl};")

    # ------------------------------------------------------------------
    # Compilateur de conditions complexes (and/or/not)
    # ------------------------------------------------------------------

    @staticmethod
    def _compile_cond_tree(tokens, emitter, true_lbl, false_lbl):
        """Parse et compile une condition (potentiellement composee de
        and/or/not) representee par `tokens`, avec destinations REELLES
        (concretes) `true_lbl`/`false_lbl` : a la fin de l'emission,
        l'execution DOIT avoir explicitement saute (via `go`) vers l'une
        des deux, jamais de fallthrough ambigu a ce niveau (voir _emit_logic
        pour la technique de court-circuit interne utilisee pour and/or)."""
        tree = REX_IfStatement._parse_logic_tree(tokens)
        REX_IfStatement._emit_logic(tree, emitter, true_lbl, false_lbl)

    # -- Parseur de l'arbre logique (OR < AND < NOT < atom) ------------

    @staticmethod
    def _parse_logic_tree(tokens):
        """Parse une sequence de tokens en arbre logique.
        Nœuds : ('or', [branches...]), ('and', [branches...]),
                ('not', subtree), ('atom', cond_tokens)."""
        return REX_IfStatement._parse_or(tokens)

    @staticmethod
    def _parse_or(tokens):
        """Niveau le plus faible : OR."""
        parts = REX_IfStatement._split_top_level(tokens, "or")
        if len(parts) == 1:
            return REX_IfStatement._parse_and(parts[0])
        branches = [REX_IfStatement._parse_and(p) for p in parts]
        return ("or", branches)

    @staticmethod
    def _parse_and(tokens):
        """Niveau intermediaire : AND."""
        parts = REX_IfStatement._split_top_level(tokens, "and")
        if len(parts) == 1:
            return REX_IfStatement._parse_not(parts[0])
        branches = [REX_IfStatement._parse_not(p) for p in parts]
        return ("and", branches)

    @staticmethod
    def _parse_not(tokens):
        """Niveau NOT."""
        if not tokens:
            raise RexResolveError("condition vide")
        first = tokens[0]
        if isinstance(first, Token) and first.type == "KEYWORD" and first.value == "not":
            rest = tokens[1:]
            if not rest:
                raise RexResolveError("'not' sans condition qui suit")
            return ("not", REX_IfStatement._parse_not(rest))
        return REX_IfStatement._parse_atom(tokens)

    @staticmethod
    def _parse_atom(tokens):
        """Niveau atomique : une seule comparaison ou expression bool,
        ou une sous-condition entre parentheses."""
        if not tokens:
            raise RexResolveError("condition atomique vide")
        # Sous-condition entre parentheses (sub-liste "nue" produite par le lexer)
        if len(tokens) == 1 and isinstance(tokens[0], list):
            return REX_IfStatement._parse_logic_tree(tokens[0])
        return ("atom", tokens)

    @staticmethod
    def _split_top_level(tokens, keyword):
        """Decoupe `tokens` sur les occurrences du mot-cle `keyword`
        (and/or) au niveau de profondeur 0 (les sous-listes/groupes
        representent des parentheses et sont opaque pour ce decoupage)."""
        parts, current = [], []
        for t in tokens:
            if (
                isinstance(t, Token)
                and t.type == "KEYWORD"
                and t.value == keyword
            ):
                if not current:
                    raise RexResolveError(
                        f"'{keyword}' sans operande gauche"
                    )
                parts.append(current)
                current = []
            else:
                current.append(t)
        if not current:
            raise RexResolveError(f"'{keyword}' sans operande droite")
        parts.append(current)
        return parts

    # -- Generateur de code REX-SL pour l'arbre logique ---------------
    #
    # Technique standard de compilation d'expressions booleennes par
    # court-circuit ("backpatching"/jumping code, cf. Aho & Ullman) :
    # chaque sous-arbre recoit une destination "vrai" (true_lbl) et une
    # destination "faux" (false_lbl), CHACUNE pouvant valoir soit un nom
    # d'etiquette REEL, soit le sentinel FALL (None) qui signifie "ne pas
    # emettre de saut pour ce cas, laisser l'execution continuer en
    # sequence" (utilise uniquement quand l'appelant garantit que le code
    # qui suit immediatement termine correctement ce cas - typiquement le
    # code de la branche and/or suivante). true_lbl et false_lbl ne
    # peuvent jamais valoir FALL tous les deux a la fois.
    #
    # Regles de propagation (true_lbl/false_lbl du parent -> des enfants) :
    #   B = B1 or B2   : B1.true = B.true : B1.false = FALL (continue B2)
    #                     B2.true = B.true : B2.false = B.false
    #   B = B1 and B2  : B1.true = FALL (continue B2) : B1.false = B.false
    #                     B2.true = B.true : B2.false = B.false
    #   B = not B1     : B1.true = B.false : B1.false = B.true (inversion)
    #   B = atome      : emet directement le(s) opcode(s) cdn/go necessaires
    #                     pour rejoindre B.true / B.false (cf. _emit_atom).

    @staticmethod
    def _emit_logic(tree, emitter, true_lbl, false_lbl):
        kind = tree[0]

        if kind == "or":
            branches = tree[1]
            # OR : la premiere branche vraie suffit (saut immediat vers
            # true_lbl) ; si elle est fausse, on continue (FALL) directement
            # dans le code de la branche suivante - aucune etiquette
            # intermediaire necessaire, l'ordre d'emission fait le travail.
            for branch in branches[:-1]:
                REX_IfStatement._emit_logic(branch, emitter, true_lbl, None)
            REX_IfStatement._emit_logic(branches[-1], emitter, true_lbl, false_lbl)

        elif kind == "and":
            branches = tree[1]
            # AND : la premiere branche fausse suffit (saut immediat vers
            # false_lbl) ; si elle est vraie, on continue (FALL) dans le
            # code de la branche suivante.
            for branch in branches[:-1]:
                REX_IfStatement._emit_logic(branch, emitter, None, false_lbl)
            REX_IfStatement._emit_logic(branches[-1], emitter, true_lbl, false_lbl)

        elif kind == "not":
            # NOT : inverse simplement les destinations vrai/faux pour le
            # sous-arbre - fonctionne uniformement, que true_lbl/false_lbl
            # soient concrets ou FALL (None), puisque c'est juste un echange.
            REX_IfStatement._emit_logic(tree[1], emitter, false_lbl, true_lbl)

        elif kind == "atom":
            REX_IfStatement._emit_atom(tree[1], emitter, true_lbl, false_lbl)

        else:
            raise RexResolveError(f"noeud logique inconnu : {kind!r}")

    @staticmethod
    def _emit_atom(cond_tokens, emitter, true_lbl, false_lbl):
        """Emet le(s) cdn/go REX-SL pour une condition atomique (une seule
        comparaison ou expression bool seule), en respectant le contrat
        FALL (None) decrit ci-dessus pour true_lbl/false_lbl :

          - false_lbl est FALL : on ne saute QUE si vrai (`cdn <op>; go true_lbl;`),
            le cas faux continue en sequence (pris en charge par l'appelant).
          - true_lbl est FALL  : symetrique, on ne saute QUE si faux, via
            l'operateur INVERSE (`cdn <inv_op>; go false_lbl;`).
          - aucun des deux n'est FALL : les deux cas doivent etre resolus
            explicitement ici (`cdn <op>; go true_lbl; cdn on; go false_lbl;`).
        """
        if true_lbl is None and false_lbl is None:
            raise RexResolveError(
                "erreur interne du compilateur : true_lbl et false_lbl ne peuvent pas "
                "etre FALL simultanement"
            )

        codegen = ExprCodegen(emitter)

        none_check = REX_IfStatement._split_none_check(cond_tokens)
        if none_check is not None:
            negate, target_tokens = none_check
            REX_IfStatement._emit_none_check(target_tokens, negate, emitter, true_lbl, false_lbl)
            return
        
        # `x in y` / `x not in y` (0.0.13) : detecte AVANT le comparateur
        # classique (==, !=, ...), delegue a l'opcode REX-SL deja existant
        # `in`/`notin <dest_bool> <valeur> <liste_ou_str>;` (contains_op),
        # puis reutilise exactement le meme branchement que le cas
        # "expression bool seule" ci-dessous (le resultat est un bool).
        membership = REX_IfStatement._split_membership(cond_tokens)
        if membership is not None:
            negate, val_tokens, coll_tokens = membership
            val_ref, _val_type = codegen.generate(ExprParser(val_tokens).parse())
            coll_ref, coll_type = codegen.generate(ExprParser(coll_tokens).parse())
            if coll_type not in ("str", "list", "tuple", "set"):
                raise RexResolveError(
                    f"'in'/'not in' : type '{coll_type}' non supporte a droite (attendu "
                    "'str' ou une collection list/tuple/set)"
                )
            temp = emitter.new_temp_name()
            opcode = "notin" if negate else "in"
            emitter.emit(f"{opcode} {temp} {val_ref} {coll_ref};")
            emitter.types[temp] = "bool"
            REX_IfStatement._emit_bool_ref(temp, emitter, true_lbl, false_lbl)
            return

        op, left_tokens, right_tokens = REX_IfStatement._split_comparator(cond_tokens)

        if op is None:
            # Expression bool seule : `if flag:`
            ref, vtype = codegen.generate(ExprParser(left_tokens).parse())
            if vtype == "none":
                REX_IfStatement._emit_static_bool(False, emitter, true_lbl, false_lbl)
                return
            if vtype != "bool":
                raise RexResolveError(
                    f"condition invalide : expression de type '{vtype}' (attendu 'bool', "
                    "ou une comparaison explicite : ==, !=, <, <=, >, >=, ou 'in'/'not in')"
                )
            REX_IfStatement._emit_bool_ref(ref, emitter, true_lbl, false_lbl)
            return

        l_ref, _lt = codegen.generate(ExprParser(left_tokens).parse())
        r_ref, _rt = codegen.generate(ExprParser(right_tokens).parse())

        if false_lbl is None:
            cdn_op = REX_IfStatement.CDN_OPS[op]
            emitter.emit(f"cdn {cdn_op} {l_ref} {r_ref};")
            emitter.emit(f"go {true_lbl};")
        elif true_lbl is None:
            cdn_op = REX_IfStatement.CDN_OPS_INVERTED[op]
            emitter.emit(f"cdn {cdn_op} {l_ref} {r_ref};")
            emitter.emit(f"go {false_lbl};")
        else:
            cdn_op = REX_IfStatement.CDN_OPS[op]
            emitter.emit(f"cdn {cdn_op} {l_ref} {r_ref};")
            emitter.emit(f"go {true_lbl};")
            emitter.emit("cdn on;")
            emitter.emit(f"go {false_lbl};")

    @staticmethod
    def _split_none_check(tokens):
        for i, t in enumerate(tokens):
            if isinstance(t, Token) and t.type == "KEYWORD" and t.value == "is":
                has_not = (
                    i + 1 < len(tokens)
                    and isinstance(tokens[i + 1], Token)
                    and tokens[i + 1].type == "KEYWORD" and tokens[i + 1].value == "not"
                )
                left = tokens[:i]
                right = tokens[i + 2:] if has_not else tokens[i + 1:]
                if REX_NoneSupport.is_none_tokens(right) and left:
                    return has_not, left
                if REX_NoneSupport.is_none_tokens(left) and right:
                    return has_not, right
                raise RexResolveError("'is'/'is not' n'est supporte qu'avec 'None'")
        for i, t in enumerate(tokens):
            if isinstance(t, Token) and t.type == "OP" and t.value in ("==", "!="):
                left, right = tokens[:i], tokens[i + 1:]
                if not left or not right:
                    continue
                if REX_NoneSupport.is_none_tokens(right):
                    return (t.value == "!="), left
                if REX_NoneSupport.is_none_tokens(left):
                    return (t.value == "!="), right
        return None

    @staticmethod
    def _emit_none_check(target_tokens, negate, emitter, true_lbl, false_lbl):
        """Compile un test `x is None` / `x is not None` / `x == None` /
        `x != None` via l'opcode REX-SL natif `isnone <dest_bool> <var>;`
        (REX-SL 0.0.23). Fonctionne pour le type 'none' reel ainsi que pour
        str/list/dict (pointeurs pouvant etre NULL). Pour les litteraux None
        et les scalaires non-pointeurs, le resultat est statique."""
        node = ExprParser(target_tokens).parse()
        codegen = ExprCodegen(emitter)

        if node[0] == "none":
            # Litteral None is-None -> toujours vrai
            cond_true = not negate
            REX_IfStatement._emit_static_bool(cond_true, emitter, true_lbl, false_lbl)
            return

        ref, vtype = codegen.generate(node)

        # Scalaires non-pointeurs (number/float/bool) : jamais None en REX-SL
        # SAUF si ce parametre a ete declare avec = None -> il a un sentinelle bool
        # __has_<nom> qui indique si la valeur a ete fournie par l'appelant.
        if vtype in ("number", "float", "bool"):
            # Detecter si le token evalue correspond a un parametre = None (sentinelle)
            param_name = None
            if node[0] == "ident":
                param_name = node[1]
            # Chercher dans les none_default_params de la fonction courante
            none_defaults = getattr(emitter, "none_default_params", {})
            current_func = getattr(emitter, "_current_func", None)
            func_name = current_func["name"] if current_func else None
            func_none_params = none_defaults.get(func_name, set()) if func_name else set()
            if param_name and param_name in func_none_params:
                # Utiliser la sentinelle __has_<param> : false = pas fourni = is None
                sentinel = f"__has_{param_name}"
                # is None  <=> __has_<nom> == false
                # is not None <=> __has_<nom> == true
                if negate:
                    # is not None -> __has_<nom> == true -> brancher sur true si true
                    REX_IfStatement._emit_bool_ref(sentinel, emitter, true_lbl, false_lbl)
                else:
                    # is None -> __has_<nom> == false -> brancher sur true si false
                    REX_IfStatement._emit_bool_ref(sentinel, emitter, false_lbl, true_lbl)
                return
            cond_true = negate  # not None -> True ; is None -> False
            REX_IfStatement._emit_static_bool(cond_true, emitter, true_lbl, false_lbl)
            return

        # Pointeurs (none, str, list, dict, tuple, set) : utilise isnone natif
        # SAUF si ce parametre a ete declare avec = None -> sentinelle __has_<nom>
        if node[0] == "ident":
            param_name = node[1]
            none_defaults = getattr(emitter, "none_default_params", {})
            current_func = getattr(emitter, "_current_func", None)
            func_name = current_func["name"] if current_func else None
            func_none_params = none_defaults.get(func_name, set()) if func_name else set()
            if param_name in func_none_params:
                sentinel = f"__has_{param_name}"
                if negate:
                    REX_IfStatement._emit_bool_ref(sentinel, emitter, true_lbl, false_lbl)
                else:
                    REX_IfStatement._emit_bool_ref(sentinel, emitter, false_lbl, true_lbl)
                return
        tmp = emitter.new_temp_name()
        emitter.declare_literal(tmp, "bool", "false")
        emitter.emit(f"isnone {tmp} {ref};")
        if negate:
            REX_IfStatement._emit_bool_ref(tmp, emitter, false_lbl, true_lbl)
        else:
            REX_IfStatement._emit_bool_ref(tmp, emitter, true_lbl, false_lbl)

    @staticmethod
    def _emit_static_bool(value, emitter, true_lbl, false_lbl):
        target = true_lbl if value else false_lbl
        if target is None:
            return
        emitter.emit("cdn on;")
        emitter.emit(f"go {target};")
        
    @staticmethod
    def _emit_bool_ref(ref, emitter, true_lbl, false_lbl):
        """Emet le branchement cdn/go pour un operande deja evalue de type
        'bool' (`ref`), en respectant le contrat FALL (None) - factorise
        entre le cas "expression bool seule" (`if flag:`) et le cas
        "in'/'not in'" (0.0.13, cf _emit_atom) qui produisent tous deux un
        simple operande bool a brancher."""
        if false_lbl is None:
            emitter.emit(f"cdn equal {ref} true;")
            emitter.emit(f"go {true_lbl};")
        elif true_lbl is None:
            emitter.emit(f"cdn not_equal {ref} true;")
            emitter.emit(f"go {false_lbl};")
        else:
            emitter.emit(f"cdn equal {ref} true;")
            emitter.emit(f"go {true_lbl};")
            emitter.emit("cdn on;")
            emitter.emit(f"go {false_lbl};")

    @staticmethod
    def _split_membership(tokens):
        """Cherche 'in' / 'not in' au niveau de profondeur 0 (0.0.13).
        Retourne (negate, left_tokens, right_tokens) ou None si absent.
        Note : le 'not' d'un 'not in' n'est PAS le 'not' prefixe unaire
        gere par _parse_not (celui-ci ne regarde que tokens[0]) - un 'not'
        au milieu des tokens, immediatement avant 'in', est donc bien
        encore disponible ici, au niveau atomique."""
        for i, t in enumerate(tokens):
            if isinstance(t, Token) and t.type == "KEYWORD" and t.value == "in":
                negate = (
                    i > 0
                    and isinstance(tokens[i - 1], Token)
                    and tokens[i - 1].type == "KEYWORD"
                    and tokens[i - 1].value == "not"
                )
                left = tokens[:i - 1] if negate else tokens[:i]
                right = tokens[i + 1:]
                if not left or not right:
                    raise RexResolveError("condition invalide autour de 'in'/'not in'")
                return negate, left, right
        return None

    @staticmethod
    def _split_comparator(tokens):
        """Cherche un operateur de comparaison au niveau de profondeur 0.
        Retourne (op, left_tokens, right_tokens) ou (None, tokens, None)."""
        for i, t in enumerate(tokens):
            if isinstance(t, Token) and t.type == "OP" and t.value in REX_IfStatement.COMPARATORS:
                left, right = tokens[:i], tokens[i + 1:]
                if not left or not right:
                    raise RexResolveError("condition invalide autour de l'operateur de comparaison")
                return t.value, left, right
        return None, tokens, None




# =============================================================================
# REX_ScrcStatement : injection C brute `scrc> "code C";`
# =============================================================================

class REX_ScrcStatement:
    """Instruction `scrc> "code C brut";` — injection directe de C dans le
    programme genere, via l'opcode REX-SL `scrc "..."`.

    Syntaxe REX :
        scrc> "int x = 42;";
        scrc> "printf(\\"hello\\n\\");";
        scrc> \"\"\"
            // bloc C multi-lignes
            for (int i = 0; i < 10; i++) {
                printf("%d\\n", i);
            }
        \"\"\";

    La valeur apres `scrc>` doit etre un UNIQUE litteral `str` (ou une chaine
    triple-quoted). Elle est passee telle quelle a l'opcode REX-SL `scrc` :
    REX-SL injecte son contenu verbatim dans le C genere. Les guillemets
    internes doivent etre echappes en \\\" comme dans REX-SL.

    Aucun typage ni verification semantique n'est effectue : `scrc>` est une
    trappe d'acces direct au C, a utiliser avec prudence (meme avertissements
    que scrc dans REX-SL)."""

    @staticmethod
    def compile(tokens, emitter):
        # tokens[0] est le token KEYWORD "scrc>"
        # tokens[1..] est le reste de la ligne : doit etre un seul STRING
        rest = tokens[1:]
        if not rest:
            raise RexResolveError(
                "scrc> : chaine C attendue apres 'scrc>' "
                "(ex: scrc> \"int x = 42;\";)"
            )
        if len(rest) != 1 or not isinstance(rest[0], Token) or rest[0].type != "STRING":
            raise RexResolveError(
                "scrc> : un unique litteral de chaine est attendu apres 'scrc>' "
                "(ex: scrc> \"code C\"; ou scrc> \"\"\"...\"\"\")"
            )
        c_code = rest[0].value
        # Echapper pour l'opcode REX-SL `scrc "..."` :
        #   - les backslashes d'abord (ordre important)
        #   - les guillemets doubles (delimiteurs de l'opcode REX-SL)
        #   - les sauts de ligne / tabulations litteraux (issus d'une chaine
        #     triple-quoted) : REX-SL attend une valeur sur UNE seule ligne.
        escaped = (
            c_code
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
        emitter.emit(f'scrc "{escaped}";')


# =============================================================================
# RESOLVEUR PRINCIPAL : _Line, _Block, REX_Resolver
# =============================================================================

class _Line:
    """Une ligne logique simple (pas de bloc) : liste de tokens deja
    debarrassee de NEWLINE/';' final."""

    __slots__ = ("tokens",)

    def __init__(self, tokens):
        self.tokens = tokens

    def __repr__(self):
        return f"Line({self.tokens!r})"


class _Block:
    """Une instruction a bloc (`<entete>:` suivi d'un corps indente), a la
    maniere de Python : `tokens` est l'entete (sans le ':' final), `body`
    la liste (recursive) de _Line/_Block du corps indente."""

    __slots__ = ("tokens", "body")

    def __init__(self, tokens, body):
        self.tokens = tokens
        self.body = body

    def __repr__(self):
        return f"Block({self.tokens!r}, body={self.body!r})"


class REX_Resolver:
    """Point d'entree du resolveur REX -> REX-SL.

    Reconstruit d'abord, a partir de la liste plate de tokens racine
    (NEWLINE/INDENT/DEDENT/';'), une structure d'instructions a la Python :
    chaque instruction est soit une ligne simple (_Line), soit une
    instruction a bloc (_Block) quand sa ligne d'entete se termine par ':'
    et qu'un corps indente suit (`func nom(...):`, `repeat n times:`, ...).
    Chaque instruction est ensuite deleguee au "statement compiler"
    correspondant a son mot-cle de tete, enregistre dans LINE_HANDLERS
    (lignes simples) ou BLOCK_HANDLERS (instructions a bloc). Ce sont ces
    deux dictionnaires qu'il faut completer pour rendre de nouvelles
    instructions REX disponibles (show, if, while, ...), sans rien changer
    au reste du moteur (lexer, ExprParser/ExprCodegen, Emitter).
    """

    LINE_HANDLERS = {
        "var": REX_VarStatement.compile,
        "return": REX_ReturnStatement.compile,
        "go": REX_GoStatement.compile,
        "label": REX_LabelStatement.compile,
        "show": REX_ShowStatement.compile,
        "break": REX_BreakStatement.compile,
        "continue": REX_ContinueStatement.compile,
        "write": REX_WriteStatement.compile,
        "writelines": REX_WritelinesStatement.compile,
        "import": REX_ImportStatement.compile,
        "scrc>": REX_ScrcStatement.compile,
    }

    BLOCK_HANDLERS = {
        "func": REX_FuncStatement.compile,
        "repeat": REX_RepeatStatement.compile,
        "while": REX_WhileStatement.compile,
        "for": REX_ForStatement.compile,
    }

    def __init__(self):
        self.emitter = Emitter()

    def compile(self, token_tree):
        statements, _ = self._parse_statement_list(token_tree, 0, stop_types=())
        self.compile_body(statements)
        return self.emitter.render()

    def compile_body(self, statements):
        """Compile une liste de _Line/_Block dans l'ordre (utilise aussi
        bien pour le programme racine que pour le corps indente d'un bloc
        comme `func`/`repeat`, appele par leurs statement compilers
        respectifs -> permet des blocs imbriques, ex. `repeat` dans
        `func`). Reconnait au passage les chaines `if`/`elif`*/`else`?
        (des _Block consecutifs de meme niveau) comme une seule
        instruction conditionnelle."""
        i, n = 0, len(statements)
        while i < n:
            stmt = statements[i]
            if self._is_block_kw(stmt, "if"):
                chain = [stmt]
                j = i + 1
                while j < n and self._is_block_kw(statements[j], ("elif", "else")):
                    chain.append(statements[j])
                    j += 1
                    if statements[j - 1].tokens[0].value == "else":
                        break
                REX_IfStatement.compile(chain, self.emitter, self)
                i = j
                continue
            if self._is_block_kw(stmt, ("elif", "else")):
                raise RexResolveError(
                    f"'{stmt.tokens[0].value}' sans 'if' correspondant juste avant"
                )
            self._compile_stmt(stmt)
            i += 1

    @staticmethod
    def _is_block_kw(stmt, keywords):
        if not isinstance(stmt, _Block) or not stmt.tokens:
            return False
        head = stmt.tokens[0]
        if not (isinstance(head, Token) and head.type == "KEYWORD"):
            return False
        if isinstance(keywords, str):
            return head.value == keywords
        return head.value in keywords

    def _compile_stmt(self, stmt):
        if isinstance(stmt, _Line):
            tokens = stmt.tokens
            if not tokens:
                return
            head = tokens[0]
            if isinstance(head, Token) and head.type == "KEYWORD" and head.value in self.LINE_HANDLERS:
                self.LINE_HANDLERS[head.value](tokens, self.emitter)
                return
            # reaffectation `<nom> = <expr>;` OU reaffectation composee
            # `<nom> += <expr>;` (et -=, *=, /=, %=, 0.0.14) : detectee
            # separement, car son nom de variable est un IDENT quelconque et
            # non un mot-cle fixe comme les autres instructions.
            if (
                isinstance(head, Token) and head.type == "IDENT"
                and len(tokens) >= 2
                and isinstance(tokens[1], Token) and tokens[1].type == "OP"
                and tokens[1].value in REX_AssignStatement.COMPOUND_OPS
            ):
                REX_AssignStatement.compile(tokens, self.emitter)
                return
            # deballage de tuple a la Python `a, b = expr;` (0.0.14) :
            # IDENT suivi d'une virgule et d'au moins un autre IDENT puis `=`.
            if REX_UnpackStatement.detect(tokens):
                REX_UnpackStatement.compile(tokens, self.emitter)
                return
            # affectation indexee a la Python `<nom>[<cle>] = <expr>;`
            # (0.0.13, cf REX_IndexAssignStatement) : IDENT suivi d'un
            # groupe '[...]' puis '='.
            if (
                isinstance(head, Token) and head.type == "IDENT"
                and len(tokens) >= 4
                and isinstance(tokens[1], Group) and tokens[1].kind == "[]"
                and isinstance(tokens[2], Token) and tokens[2].type == "OP" and tokens[2].value == "="
            ):
                REX_IndexAssignStatement.compile(tokens, self.emitter)
                return
            # appel utilise comme instruction autonome `nom(...);` (0.0.13,
            # cf REX_CallStatement) : IDENT suivi directement d'un
            # regroupement "nu" (parentheses), rien d'autre apres.
            if (
                isinstance(head, Token) and head.type == "IDENT"
                and len(tokens) == 2
                and isinstance(tokens[1], list)
            ):
                REX_CallStatement.compile(tokens, self.emitter)
                return
            # appel qualifie de module `alias.fn(args);` comme instruction
            # autonome (0.0.15) : IDENT '.' IDENT '(' args ')' -> 4 tokens
            # [IDENT, PUNCT('.'), IDENT, list].
            if (
                isinstance(head, Token) and head.type == "IDENT"
                and len(tokens) == 4
                and isinstance(tokens[1], Token) and tokens[1].type == "PUNCT"
                and tokens[1].value == "."
                and isinstance(tokens[2], Token) and tokens[2].type == "IDENT"
                and isinstance(tokens[3], list)
            ):
                alias = tokens[0].value
                fn_name = tokens[2].value
                # methode de liste `liste.append(val);` -> sucre syntaxique
                # pour `append(liste, val);` (0.0.23+).
                if fn_name == "append":
                    fake_list_tok = Token("IDENT", alias, head.line, head.col)
                    fake_name_tok = Token("IDENT", "append", tokens[2].line, tokens[2].col)
                    # On synthétise append(alias, val) : on emprunte le groupe
                    # d'args existant (tokens[3]) et on le prefixe du nom de
                    # liste. REX_CallStatement._compile_append attend exactement
                    # [("pos", list_node), ("pos", val_node)].
                    raw_args = ExprParser._parse_call_args(tokens[3])
                    if len(raw_args) != 1 or raw_args[0][0] == "kwarg":
                        raise RexResolveError(
                            "liste.append() attend exactement 1 argument positionnel : "
                            "liste.append(valeur)"
                        )
                    list_node = ("ident", alias)
                    full_args = [("pos", list_node), raw_args[0]]
                    REX_CallStatement._compile_append(full_args, self.emitter)
                    return
                mangled = self.emitter.resolve_module_func(alias, fn_name)
                if mangled not in self.emitter.functions:
                    raise RexResolveError(
                        f"module '{alias}' : fonction '{fn_name}' non encore compilee"
                    )
                # On synthetise des tokens equivalents a `mangled(args);`
                fake_ident = Token("IDENT", mangled, tokens[0].line, tokens[0].col)
                REX_CallStatement.compile([fake_ident, tokens[3]], self.emitter)
                return
            raise RexResolveError(
                f"instruction non geree par le resolveur (base modulable, pas encore "
                f"branchee) : {tokens!r}"
            )
        if isinstance(stmt, _Block):
            tokens = stmt.tokens
            if not tokens:
                raise RexResolveError("bloc sans mot-cle d'entete")
            head = tokens[0]
            if isinstance(head, Token) and head.type == "KEYWORD" and head.value in self.BLOCK_HANDLERS:
                self.BLOCK_HANDLERS[head.value](tokens, stmt.body, self.emitter, self)
                return
            raise RexResolveError(
                f"instruction a bloc non geree par le resolveur : {tokens!r}"
            )
        raise RexResolveError(f"instruction inconnue du resolveur : {stmt!r}")

    @staticmethod
    def _parse_statement_list(tokens, start, stop_types):
        """Reconstruit, a partir d'une portion de la liste plate de tokens
        racine (a partir de l'index `start`), la liste de _Line/_Block
        correspondante, en s'arretant des qu'un token dont le type figure
        dans `stop_types` est rencontre a ce niveau (ex: ("DEDENT",) pour
        le corps d'un bloc), ou a la fin des tokens (niveau racine).
        Retourne (liste_d_instructions, index_juste_apres_la_derniere)."""
        stmts = []
        i = start
        n = len(tokens)
        while i < n:
            tok = tokens[i]
            is_tok = isinstance(tok, Token)
            if is_tok and tok.type in stop_types:
                return stmts, i
            if is_tok and tok.type == "NEWLINE":
                i += 1
                continue
            if is_tok and tok.type == "PUNCT" and tok.value == ";":
                i += 1
                continue
            if is_tok and tok.type in ("INDENT", "DEDENT"):
                # INDENT hors contexte d'un bloc ouvert par ':', ou DEDENT
                # non attendu a ce niveau : indentation incoherente.
                raise RexResolveError(
                    "indentation inattendue (un bloc doit etre introduit par ':')"
                    if tok.type == "INDENT" else
                    "fin de bloc inattendue (DEDENT sans bloc ouvert correspondant)"
                )

            # collecte une ligne logique jusqu'a NEWLINE / ';' / INDENT-DEDENT
            line_tokens = []
            while i < n:
                t = tokens[i]
                if isinstance(t, Token) and t.type == "NEWLINE":
                    i += 1
                    break
                if isinstance(t, Token) and t.type == "PUNCT" and t.value == ";":
                    i += 1
                    break
                if isinstance(t, Token) and t.type in ("INDENT", "DEDENT"):
                    break
                line_tokens.append(t)
                i += 1

            if not line_tokens:
                continue

            last = line_tokens[-1]
            is_block_header = (
                isinstance(last, Token) and last.type == "PUNCT" and last.value == ":"
            )
            if is_block_header:
                header = line_tokens[:-1]
                if i >= n or not (isinstance(tokens[i], Token) and tokens[i].type == "INDENT"):
                    raise RexResolveError(
                        f"bloc indente attendu apres ':' : {header!r}"
                    )
                i += 1  # consomme l'INDENT
                body, i = REX_Resolver._parse_statement_list(tokens, i, stop_types=("DEDENT",))
                if i < n and isinstance(tokens[i], Token) and tokens[i].type == "DEDENT":
                    i += 1  # consomme le DEDENT correspondant
                stmts.append(_Block(header, body))
            else:
                stmts.append(_Line(line_tokens))

        return stmts, i




# =============================================================================
# UTILITAIRES DU RESOLVEUR
# =============================================================================

def _emit_evo_func_wrapper(emitter, fn_desc):
    """Genere directement les instructions REX-SL pour une fonction wrapper
    evo-import (appel d'un executable externe).

    Strategie :
      1. La fonction mangled (ex: __rx_mod_mymod_add) est declaree en REX-SL
         via func/endfunc.
      2. Le corps appelle l'executable via scrc+system() en construisant
         la ligne de commande avec les arguments passes en parametre.
      3. Le resultat (si non-none) est ecrit par l'executable dans un fichier
         temporaire /tmp/__rex_evo_<alias>_<fn>, lu par la fonction via
         l'opcode REX-SL 'read', converti au bon type et retourne.

    L'executable est responsable de :
      - Recevoir son label (nom de fonction) en argv[1]
      - Recevoir ses arguments en argv[2..N] (tous en texte)
      - Ecrire le resultat (texte) dans /tmp/__rex_evo_<alias>_<fn>
        avant de terminer.
    """
    fn_name   = fn_desc["name"]
    params    = fn_desc.get("params", [])   # [["type", "nom"], ...]
    ret_type  = fn_desc.get("return", "str")
    exe_path  = fn_desc["exe"]
    alias     = fn_desc["alias"]
    mangled   = f"__rx_mod_{alias}_{fn_name}"

    # Fichier temp utilise pour le retour
    tmp_file  = f"/tmp/__rex_evo_{alias}_{fn_name}"

    # Types C + formats printf pour construire la commande.
    # Tous les params sont declares 'str' (char*) cote REX-SL, donc SL_<n>
    # est toujours un char*.  Pour les types JSON number/float/bool, on passe
    # la valeur telle quelle via %s (l'appelant a deja converti en string).
    # On n'utilise plus atoi/atof ici car la variable est deja une string.
    _C_TYPE = {"number": "int", "float": "float", "bool": "bool", "str": "char*"}
    _C_FMT  = {"number": "%s", "float": "%s", "bool": "%s", "str": "%s"}
    _C_EXPR = {
        "number": lambda n: f"SL_{n}",
        "float":  lambda n: f"SL_{n}",
        "bool":   lambda n: f"SL_{n}",
        "str":    lambda n: f"SL_{n}",
    }

    # -- Signature REX-SL de la fonction --
    # Les params sont declares en 'str' dans la signature REX-SL, quel que soit
    # le type annote dans le JSON metafn.  Raison : les arguments transitent
    # toujours par argv[] (strings shell), donc l'appelant REX peut passer
    # n'importe quel type scalaire converti en str.  Le corps du wrapper se
    # charge de la conversion C (atoi/atof) avant de construire la commande
    # snprintf.  Sans ce choix, un param non-annote dans le module source
    # recoit le type provisoire "number" dans metafn, et un appel avec un
    # argument "str" provoque : "argument X attend number, recu str".
    rexsl_params = []
    for ptype, pname in params:
        rexsl_params.append(f"str {pname}")
    rexsl_ret = ret_type if ret_type != "none" else "none"

    param_str = " ".join(rexsl_params)
    ret_ann   = f" -> {rexsl_ret}" if rexsl_ret != "none" else ""
    emitter.emit(f"func {mangled} {param_str}{ret_ann};")

    # Enregistrer la fonction dans l'emitter pour que les appels
    # exec/ExprCodegen._call la reconnaissent.
    # Les types enregistres sont 'str' (correspondant a la signature emise).
    param_types  = ["str" for _ in params]
    param_names  = [p[1] for p in params]
    defaults_map = {}
    elem_type    = None
    dict_vtype   = None
    actual_ret   = ret_type if ret_type != "none" else None
    emitter.functions[mangled] = (
        param_types, param_names, defaults_map,
        actual_ret, elem_type, dict_vtype
    )

    # -- Corps : construction de la commande et appel via scrc --
    # Format : "<exe> <fn_name> [arg1 arg2 ...]"
    # Buffer de commande : 4096 octets (suffisant pour la plupart des usages)
    exe_esc = exe_path.replace("\\", "\\\\").replace('"', '\\"')
    tmp_esc = tmp_file.replace("\\", "\\\\").replace('"', '\\"')

    # Construction du snprintf pour assembler la commande avec les arguments
    fmt_parts  = [f'"{exe_esc} {fn_name}"']
    fmt_pieces = []   # morceaux du format printf
    arg_exprs  = []   # expressions C correspondantes

    for ptype, pname in params:
        fmt_pieces.append(_C_FMT.get(ptype, "%s"))
        arg_exprs.append(_C_EXPR.get(ptype, lambda n: f"SL_{n}")(pname))

    if fmt_pieces:
        fmt_str = " ".join(fmt_pieces)
        args_str = ", ".join(arg_exprs)
        cmd_build = (
            f'{{ char __rex_evo_cmd[4096]; '
            f'snprintf(__rex_evo_cmd, 4096, "{exe_esc} {fn_name} {fmt_str}", {args_str}); '
            f'system(__rex_evo_cmd); }}'
        )
    else:
        cmd_build = (
            f'system("{exe_esc} {fn_name}");'
        )

    escaped_cmd = cmd_build.replace("\\", "\\\\").replace('"', '\\"')
    emitter.emit(f'scrc "{escaped_cmd}";')

    # -- Lecture du resultat --
    if ret_type != "none":
        ret_tmp = "__rx_evo_ret"
        if ret_type == "str":
            emitter.emit(f'var str {ret_tmp} "";')
            emitter.emit(f'read "{tmp_esc}" {ret_tmp};')
            emitter.emit(f"return {ret_tmp};")
        elif ret_type in ("number", "float"):
            raw_tmp = "__rx_evo_raw"
            emitter.emit(f'var str {raw_tmp} "";')
            emitter.emit(f'read "{tmp_esc}" {raw_tmp};')
            emitter.emit(f'var {ret_type} {ret_tmp};')
            if ret_type == "number":
                conv_code = f'SL_{ret_tmp} = atoi(SL_{raw_tmp});'
            else:
                conv_code = f'SL_{ret_tmp} = (float)atof(SL_{raw_tmp});'
            conv_esc = conv_code.replace("\\", "\\\\").replace('"', '\\"')
            emitter.emit(f'scrc "{conv_esc}";')
            emitter.emit(f"return {ret_tmp};")
        elif ret_type == "bool":
            raw_tmp = "__rx_evo_raw"
            emitter.emit(f'var str {raw_tmp} "";')
            emitter.emit(f'read "{tmp_esc}" {raw_tmp};')
            emitter.emit(f'var bool {ret_tmp} false;')
            conv_code = f'SL_{ret_tmp} = (SL_{raw_tmp}[0] == \'t\' || SL_{raw_tmp}[0] == \'1\');'
            conv_esc = conv_code.replace("\\", "\\\\").replace('"', '\\"')
            emitter.emit(f'scrc "{conv_esc}";')
            emitter.emit(f"return {ret_tmp};")

    emitter.emit(f"endfunc {mangled};")


def resolve_to_rexsl(token_tree, source=None):
    """Fonction utilitaire : transpile un arbre de tokens REX (sortie de
    REX_Lexer.tokenize) en code source REX-SL (texte).

    0.0.15 : si `source` est fourni, pre-scanne les marqueurs speciaux
    `# __RX_MODULE_REG__ <alias> <json>` inseres par preprocess_imports
    pour les imports `as alias`, et enregistre les modules dans l'emitter
    AVANT de compiler le corps du programme (les fonctions de ces modules
    etant deja inline dans le source, elles seront compilees normalement
    par REX_FuncStatement ; le registre sert uniquement a valider/resoudre
    les appels qualifies `alias.fn(...)` rencontres apres)."""
    import json as _json
    import re as _re
    _MODULE_REG_RE = _re.compile(
        r'^#\s*__RX_MODULE_REG__\s+([A-Za-z_][A-Za-z0-9_]*)\s+(\{.*\})\s*$'
    )
    _EVO_FUNC_RE = _re.compile(
        r'^#\s*__RX_EVO_FUNC__\s+(\{.*\})\s*$'
    )
    resolver = REX_Resolver()
    if source is not None:
        for line in source.splitlines():
            m = _MODULE_REG_RE.match(line)
            if m:
                alias = m.group(1)
                try:
                    func_map = _json.loads(m.group(2))
                except Exception:
                    func_map = {}
                try:
                    resolver.emitter.register_module(alias, func_map)
                except RexResolveError:
                    pass  # doublon tolere (import dans un import)
            m2 = _EVO_FUNC_RE.match(line)
            if m2:
                try:
                    fn_desc = _json.loads(m2.group(1))
                    _emit_evo_func_wrapper(resolver.emitter, fn_desc)
                except Exception as e:
                    raise RexResolveError(f"evo-import: erreur generation wrapper : {e}")
    rexsl_source = resolver.compile(token_tree)

    # Garde-fou : avertir si une fonction termine la compilation avec un
    # parametre encore non-annote ET jamais type par un appel (emitter.
    # pending_func_sigs non vide). Concretement : ce parametre reste sur son
    # defaut "number", en silence. Sans consequence si ce fichier est importe
    # ailleurs via `import "fichier.rex";` (le vrai type sera resolu depuis
    # le site d'appel, dans le fichier qui fait l'import). MAIS si ce fichier
    # est compile seul (`REX -f ce_fichier.rex -c`) pour servir de module
    # 'evo-import' (executable appele via `import module;` quand aucun
    # module.rex n'est trouve a cote), ce type "number" par defaut sera
    # exporte tel quel dans metafn -- et tout argument string recu plus tard
    # via l'executable (argv[]) sera silencieusement converti par atoi() en 0.
    # D'ou l'avertissement explicite ici, au moment ou l'ambiguite existe
    # encore, plutot qu'un bug muet decouvert au runtime bien plus tard.
    pending = getattr(resolver.emitter, "pending_func_sigs", {})
    if pending:
        for fname, info in pending.items():
            if fname.startswith("__rx_"):
                continue  # fonction mangle d'un module importe, pas la source directe
            unresolved_names = [pname for _pos, pname in info.get("untyped_positions", [])]
            if not unresolved_names:
                continue
            print(
                f"[REX] avertissement : la fonction '{fname}' a le(s) parametre(s) "
                f"{', '.join(unresolved_names)!s} sans annotation de type, jamais "
                "resolue par un appel dans ce fichier -> reste sur le defaut "
                "'number'. Si ce fichier est compile seul et utilise via "
                "'import <nom>;' (evo-import, executable) depuis un autre "
                "programme, ce defaut sera exporte tel quel et tout argument "
                "string recu sera silencieusement converti a 0 par atoi(). "
                f"Annotez explicitement le type pour eviter ca : "
                f"'func {fname}(str {unresolved_names[0]}, ...)' par exemple.",
                file=sys.stderr,
            )
    return rexsl_source


def pretty_print_tokens(tree, indent=0):
    """Affiche une liste de tokens imbriquee de facon lisible."""
    pad = "  " * indent
    if isinstance(tree, list):
        print(f"{pad}[")
        for item in tree:
            pretty_print_tokens(item, indent + 1)
        print(f"{pad}]")
    elif isinstance(tree, Group):
        opening, closing = tree.kind[0], tree.kind[1]
        print(f"{pad}{opening}")
        for item in tree.items:
            pretty_print_tokens(item, indent + 1)
        print(f"{pad}{closing}")
    elif tree.type == "NEWLINE":
        print(f"{pad}NEWLINE          (l{tree.line})")
    elif tree.type == "INDENT":
        print(f"{pad}INDENT -> {tree.value}   (l{tree.line})")
    elif tree.type == "DEDENT":
        print(f"{pad}DEDENT -> {tree.value}   (l{tree.line})")
    else:
        print(f"{pad}{tree.type:<8} {tree.value!r}  (l{tree.line}:c{tree.col})")


# ---------------------------------------------------------------------------
# Chargement du code source
# ---------------------------------------------------------------------------



# =============================================================================
# PREPROCESSEUR : imports, lecture de fichier source
# =============================================================================

def _mangle_module_funcs(content, alias):
    """Transforme un contenu REX source importe avec `as <alias>` :
    chaque declaration `func <nom>(...):`  et chaque appel `<nom>(...)` qui
    correspond a une fonction declaree dans ce module est renomme vers
    `__rx_mod_<alias>_<nom>`. Retourne (contenu_mangle, func_map) ou
    func_map = {nom_original: nom_mangle}.

    Implementation : deux passes —
      1) detecter tous les noms de fonctions declares dans le module
         (regex _FUNC_DEF_RE sur les lignes a indentation zero) ;
      2) remplacer textuellement, dans tout le contenu, chaque occurrence
         du nom comme identificateur de fonction (flanquee de limites de
         mot \b) par son nom mangle. On utilise une regex word-boundary
         pour eviter de remplacer des prefixes de noms homonymes."""
    # Passe 1 : collecte des noms de fonctions
    func_names = []
    for line in content.splitlines():
        m = _FUNC_DEF_RE.match(line)
        if m:
            func_names.append(m.group(1))

    if not func_names:
        return content, {}

    # Passe 2 : renommage dans tout le contenu
    func_map = {}
    for fn in func_names:
        mangled = f"__rx_mod_{alias}_{fn}"
        func_map[fn] = mangled
        # Remplace le nom partout ou il apparait comme identificateur autonome
        # (definition func <nom> ET appels <nom>(...)) - \b assure qu'on ne
        # remplace pas un sous-mot (ex: "add" dans "added").
        content = re.sub(r'\b' + re.escape(fn) + r'\b', mangled, content)

    return content, func_map


def _strip_rex_header(content):
    """Retire la premiere ligne non vide d'un contenu REX si elle
    correspond a l'entete '# REX>' - utilise pour ne pas dupliquer/faire
    entrer en conflit l'entete d'un fichier importe avec celle du fichier
    principal (l'entete elle-meme reste de toute facon un simple
    commentaire pour le lexer, mais on prefere ne pas l'accumuler)."""
    lines = content.splitlines()
    first_idx = next((i for i, l in enumerate(lines) if l.strip() != ""), None)
    if first_idx is not None and HEADER_RE.match(lines[first_idx].strip()):
        lines = lines[:first_idx] + lines[first_idx + 1:]
    return "\n".join(lines)


def preprocess_imports(source, base_dir, _stack=None, _module_registry=None):
    """Preprocesseur d'`import` (0.0.11, etendu 0.0.15) : colle TEXTUELLEMENT
    le contenu de chaque fichier importe A LA PLACE de sa ligne `import "chemin";`
    (comme un `#include` C), AVANT toute analyse lexicale REX. Recursif et
    protege contre les imports circulaires via `_stack`.

    0.0.15 : forme `import "chemin.rex" as alias;` egalement reconnue —
    le contenu est inline identiquement, mais les noms de fonctions declares
    dans le module sont renommes vers `__rx_mod_<alias>_<nom>` (via
    _mangle_module_funcs) et enregistres dans `_module_registry` (dict
    {alias: func_map}), transmis au resolveur via le token special
    `# __RX_MODULE_REG__ <alias> <json>` insere en tete du bloc inline.
    Ce token est detecte par REX_Resolver.compile() et appelle
    emitter.register_module() avant de compiler les instructions normales.

    Chaque `import` doit occuper une ligne entiere a elle seule (pas
    d'indentation, pas d'autre instruction sur la meme ligne via ';') :
    toute autre forme n'est PAS reconnue ici et remonte telle quelle jusqu'au
    resolveur, qui la rejette explicitement (voir REX_ImportStatement)."""
    import json as _json

    if _stack is None:
        _stack = []
    if _module_registry is None:
        _module_registry = {}

    out_lines = []
    for line in source.splitlines():
        # Tenter d'abord la forme avec alias (plus specifique)
        m_as = IMPORT_LINE_AS_RE.match(line)
        m_plain = IMPORT_LINE_RE.match(line) if m_as is None else None

        # evo-import : import sans guillemets (a la Python)
        m_bare = None
        if m_as is None and m_plain is None:
            m_bare = IMPORT_BARE_RE.match(line)

        if m_as is None and m_plain is None and m_bare is None:
            out_lines.append(line)
            continue

        # -- traitement evo-import bare --
        if m_bare is not None:
            if m_bare.group("indent"):
                raise REXERROR(
                    f"'import' doit etre en debut de ligne (indentation non supportee) : {line!r}"
                )
            mod_name = m_bare.group("mod")
            alias = m_bare.group("alias") or mod_name.replace("/", "_").replace("\\", "_").replace(".", "_").replace("-", "_")

            # 1) Chercher module.rex (chemin relatif au fichier courant)
            #    On ne cherche QUE "mod_name.rex" (pas mod_name sans extension,
            #    qui serait un fichier sans .rex et causerait un faux positif si
            #    un executable du meme nom existe dans le dossier).
            rex_candidates = []
            if not mod_name.endswith(".rex"):
                rex_candidates.append(mod_name + ".rex")
            else:
                rex_candidates.append(mod_name)

            rex_found = None
            for cand in rex_candidates:
                p = cand if os.path.isabs(cand) else os.path.join(base_dir, cand)
                p = os.path.normpath(p)
                if os.path.isfile(p):
                    rex_found = p
                    break

            if rex_found is not None:
                # Traiter comme un import "chemin.rex" as alias classique
                # On simule la ligne avec guillemets et on relance
                rel = os.path.relpath(rex_found, base_dir)
                if alias == mod_name.replace("/", "_").replace("\\", "_").replace(".", "_").replace("-", "_"):
                    fake_line = f'import "{rel}" as {alias};'
                else:
                    fake_line = f'import "{rel}" as {alias};'
                # recurse sur la fausse ligne
                resolved_block = preprocess_imports(fake_line, base_dir, _stack, _module_registry)
                out_lines.extend(resolved_block.splitlines())
                if DEBUG:
                    print(f"[evo-import] '{mod_name}' -> rex '{rex_found}' (alias: {alias})")
                continue

            # 2) Chercher un executable dans base_dir UNIQUEMENT.
            #    On ne cherche PAS dans le PATH systeme pour un nom simple
            #    (ex: 'script' trouverait /usr/bin/script, une commande systeme).
            #    Pour cibler un exe hors du dossier courant, l'utilisateur doit
            #    passer un chemin explicite (ex: import ./tools/mon_exe).
            exe_candidates = [mod_name]
            if os.name == "nt":
                exe_candidates.append(mod_name + ".exe")
            exe_found = None
            for cand in exe_candidates:
                p = cand if os.path.isabs(cand) else os.path.join(base_dir, cand)
                p = os.path.normpath(p)
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    exe_found = p
                    break
            # Recherche PATH uniquement si le nom contient un separateur de chemin
            # (l'utilisateur a explicitement reference un sous-dossier/chemin).
            if exe_found is None and ("/" in mod_name or "\\" in mod_name):
                import shutil as _shutil
                found_in_path = _shutil.which(mod_name)
                if found_in_path:
                    exe_found = found_in_path

            if exe_found is None:
                raise REXERROR(
                    f"evo-import: module '{mod_name}' introuvable.\n"
                    f"  Cherche '{mod_name}.rex' dans : {base_dir}\n"
                    f"  Cherche executable '{mod_name}' dans : {base_dir}\n"
                    f"  Note : pour un import REX standard, utilisez : import \"{mod_name}.rex\";\n"
                    f"  Note : pour un exe hors dossier, utilisez un chemin : import ./dossier/{mod_name};"
                )

            # 3) Appeler l'executable avec 'metafn' pour obtenir les signatures
            import subprocess as _sp, json as _json
            try:
                result = _sp.run(
                    [exe_found, "metafn"],
                    capture_output=True, text=True, timeout=10
                )
                meta_json = result.stdout.strip()
                if not meta_json:
                    raise REXERROR(
                        f"evo-import: '{exe_found} metafn' n'a rien retourne sur stdout. "
                        f"L'executable doit ecrire un JSON de signatures quand appele avec 'metafn'."
                    )
                meta = _json.loads(meta_json)
            except _sp.TimeoutExpired:
                raise REXERROR(f"evo-import: '{exe_found} metafn' a depasse le delai de 10s")
            except _json.JSONDecodeError as e:
                raise REXERROR(
                    f"evo-import: '{exe_found} metafn' a retourne du JSON invalide : {e}\n"
                    f"Sortie brute : {meta_json[:200]!r}"
                )

            # Format attendu :
            # {"functions": [{"name": "add", "params": [["number","a"], ...], "return": "number"}, ...]}
            functions = meta.get("functions", [])
            if not functions:
                raise REXERROR(
                    f"evo-import: '{exe_found} metafn' : JSON valide mais 'functions' vide ou absent. "
                    f"Format attendu : {{\"functions\": [{{\"name\": \"fn\", \"params\": [[\"type\",\"nom\"],...], \"return\": \"type\"}}, ...]}}"
                )

            exe_escaped = exe_found.replace("\\", "/")

            # 4) Generer des marqueurs speciaux que resolve_to_rexsl transformera
            # en fonctions REX-SL directement (les wrappers appellent l'executable
            # via system() C et recuperent le resultat via un fichier temporaire).
            #
            # Format du marqueur :
            #   # __RX_EVO_FUNC__ <alias> <json_fn_descriptor>
            # json_fn_descriptor = {"name": ..., "params": [...], "return": ..., "exe": ...}
            #
            # resolve_to_rexsl lit ces marqueurs et appelle _emit_evo_func_wrapper()
            # dans l'emitter pour generer le code REX-SL correspondant.
            func_map = {fn["name"]: f"__rx_mod_{alias}_{fn['name']}" for fn in functions}
            wrapper_lines = [
                f"# --- debut evo-import: {mod_name} (executable) ---",
                f"# __RX_MODULE_REG__ {alias} {_json.dumps(func_map)}",
            ]
            for fn in functions:
                fn_desc = {
                    "name": fn["name"],
                    "params": fn.get("params", []),
                    "return": fn.get("return", "str"),
                    "exe": exe_found,
                    "alias": alias,
                }
                wrapper_lines.append(f"# __RX_EVO_FUNC__ {_json.dumps(fn_desc)}")
            wrapper_lines.append(f"# --- fin evo-import: {mod_name} (executable) ---")

            out_lines.extend(wrapper_lines)

            # Toujours signale (pas seulement en --debug) : 'import <mod>;' sans
            # guillemets est cense inliner <mod>.rex si ce fichier existe (import
            # source, types correctement inferes depuis les sites d'appel). Ici,
            # <mod>.rex n'a PAS ete trouve a cote du fichier compile, et on est
            # tombe sur un exécutable du meme nom a la place (pont shell/argv,
            # cf. REX-SL 'evo-import') - un mode beaucoup plus fragile (parametres
            # non-annotes de l'executable figes sur 'number' si jamais appeles a
            # l'interieur du module lui-meme). Avertir explicitement pour eviter
            # une confusion silencieuse entre les deux mode.
            print(
                f"[REX] avertissement : 'import {mod_name}' n'a pas trouve de "
                f"fichier '{mod_name}.rex' a cote de ce fichier -> utilise a la "
                f"place l'executable '{exe_found}' trouve sous ce nom (mode "
                "evo-import, pont via argv/atoi). Si tu voulais inliner ton "
                f"code source, verifie que '{mod_name}.rex' existe bien dans le "
                "meme dossier (et envisage de renommer/supprimer l'executable "
                "pour lever toute ambiguite).",
                file=sys.stderr,
            )
            if DEBUG:
                print(f"[evo-import] '{mod_name}' -> exe '{exe_found}' (alias: {alias}, {len(functions)} fonctions)")
            continue

        m = m_as if m_as is not None else m_plain
        if m.group("indent"):
            raise REXERROR(
                f"'import' doit etre en debut de ligne (indentation non supportee) : {line!r}"
            )

        rel_path = m.group("path")
        alias = m_as.group("alias") if m_as is not None else None
        import_path = rel_path if os.path.isabs(rel_path) else os.path.join(base_dir, rel_path)
        import_path = os.path.normpath(import_path)

        if not os.path.isfile(import_path):
            raise REXERROR(f"import: fichier introuvable : {rel_path} (resolu en {import_path})")
        if import_path in _stack:
            cycle = " -> ".join(_stack + [import_path])
            raise REXERROR(f"import: dependance circulaire detectee : {cycle}")

        with open(import_path, "r", encoding="utf-8") as f:
            imported_content = f.read()

        imported_lines = imported_content.splitlines()
        first_idx = next((i for i, l in enumerate(imported_lines) if l.strip() != ""), None)
        if first_idx is None or not HEADER_RE.match(imported_lines[first_idx].strip()):
            raise REXERROR(
                f"import: fichier REX invalide '{rel_path}' : header REX manquant en premiere "
                "ligne non vide (attendu: '# REX>')"
            )
        imported_content = _strip_rex_header(imported_content)

        # Import avec alias : mangler les noms de fonctions avant l'inlining
        func_map = {}
        if alias is not None:
            imported_content, func_map = _mangle_module_funcs(imported_content, alias)
            if alias in _module_registry:
                raise REXERROR(f"import: alias '{alias}' deja utilise dans ce fichier")
            _module_registry[alias] = func_map

        resolved = preprocess_imports(
            imported_content, os.path.dirname(import_path),
            _stack + [import_path], _module_registry
        )

        if DEBUG:
            mode = f"as {alias}" if alias else "inline"
            print(f"[import] '{rel_path}' ({mode}) -> colle (resolu: {import_path})")

        out_lines.append(f"# --- debut import: {rel_path} ---")
        # Pour les imports avec alias : injecter un marqueur special que le
        # resolveur lira pour enregistrer le module dans l'emitter.
        # Format : `# __RX_MODULE_REG__ <alias> <json_func_map>`
        # C'est un commentaire REX (# ...) : invisible au lexer, mais on
        # l'inspecte explicitement dans resolve_to_rexsl avant de lexer.
        if alias is not None:
            out_lines.append(
                f"# __RX_MODULE_REG__ {alias} {_json.dumps(func_map)}"
            )
        out_lines.extend(resolved.splitlines())
        out_lines.append(f"# --- fin import: {rel_path} ---")

    result = "\n".join(out_lines)
    if source.endswith("\n"):
        result += "\n"
    return result


def read_source_from_file(path):
    """Lit un fichier REX depuis le disque en verifiant la presence de
    l'entete obligatoire '# REX <version>' sur la premiere ligne non vide,
    puis resout et colle recursivement tout `import "chemin";` (voir
    preprocess_imports) avant de retourner le source pret pour le lexer."""
    if not os.path.isfile(path):
        raise REXERROR(f"fichier introuvable: {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()
    first_meaningful = next((l for l in lines if l.strip() != ""), "")
    match = HEADER_RE.match(first_meaningful.strip())
    if not match:
        raise REXERROR(
            "fichier REX invalide: header REX manquant en premiere ligne "
            "non vide (attendu: '# REX>')"
        )

    if DEBUG:
        print(f"[header] fichier REX valide (REX-SL cible: {REXSL_VERSION})")

    content = preprocess_imports(content, os.path.dirname(os.path.abspath(path)))

    return content


def compute_output_name(args):
    """Determine le nom de sortie (executable / .rexsl / .c) selon -O,
    ou a defaut selon -f (nom du fichier sans extension), ou 'rex_output'
    en mode -o."""
    if args.output:
        return args.output
    if args.file:
        base = os.path.basename(args.file)
        name, _ext = os.path.splitext(base)
        return name
    return "rex_output"



# =============================================================================
# POINT D'ENTREE PRINCIPAL
# =============================================================================

def main():
    global DEBUG

    parser = build_arg_parser()
    args = parser.parse_args()
    DEBUG = args.debug

    if DEBUG:
        print("===  REX  ===")
        print("(C) 2026 RECO4")

    if not args.oneline and not args.file:
        print("Pas de code fourni")
        sys.exit(1)

    if args.oneline and args.file:
        print("Erreur: utilisez soit -o soit -f, pas les deux en meme temps")
        sys.exit(1)

    try:
        if args.file:
            source = read_source_from_file(args.file)
        else:
            # Mode -o : instructions separees par ';' sur une seule ligne,
            # aucun header ni indentation n'est requis dans ce mode.
            source = args.oneline
    except REXERROR as e:
        print(f"Erreur: {e}")
        sys.exit(1)

    output_name = compute_output_name(args)
    if DEBUG:
        print(f"[config] fichier de sortie: {output_name}")
        print(
            f"[config] compile={args.compiler or args.run} run={args.run} "
            f"keep_c={args.keep_c} keep_rsl={args.keep_rsl}"
        )

    # -- Etape 1 : analyse lexicale -----------------------------------------
    try:
        lexer = REX_Lexer(source)
        tokens = lexer.tokenize()
    except REXERROR as e:
        print(f"Erreur lexicale: {e}")
        sys.exit(1)

    if DEBUG:
        print("[lexer] tokens generes:")
        pretty_print_tokens(tokens)

    # -- Etape 2 : resolution REX -> REX-SL ----------------------------------
    try:
        rexsl_source = resolve_to_rexsl(tokens, source=source)
    except REXERROR as e:
        print(f"Erreur de resolution: {e}")
        sys.exit(1)

    if DEBUG:
        print("[resolver] code REX-SL genere:")
        print(rexsl_source)

    rexsl_path = output_name + ".rexsl"
    try:
        with open(rexsl_path, "w", encoding="utf-8") as f:
            f.write(rexsl_source)
    except OSError as e:
        print(f"Erreur: impossible d'ecrire {rexsl_path}: {e}")
        sys.exit(1)

    if not (args.compiler or args.run):
        if not DEBUG:
            pretty_print_tokens(tokens)
        print(f"[REX] fichier REX-SL genere : {rexsl_path}")
        if not args.keep_rsl:
            print("(utilisez -s/--keep-rsl pour le conserver, sinon il ne "
                  "sera pas supprime car -c/-r n'a pas ete demande)")
        return

    # -- Etape 3 : REX-SL -> C -> executable (delegue a l'executable REX-SL) ----------
    
    # Résolution du chemin pour éviter le dossier /tmp de PyInstaller
    if getattr(sys, 'frozen', False):
        # Si le programme est compilé (ex: ./REX)
        base_dir = os.path.dirname(sys.executable)
    else:
        # Si le programme est exécuté comme un script classique (python REX.py)
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Compatibilité multiplateforme
    exe_name = "REX-SL.exe" if os.name == "nt" else "REX-SL"
    rexsl_exe = os.path.join(base_dir, exe_name)
    
    if not os.path.isfile(rexsl_exe):
        print(f"Erreur: executable {exe_name} introuvable a cote de REX ({rexsl_exe})")
        sys.exit(1)

    cmd = [rexsl_exe, "-f", rexsl_path, "-O", output_name, "-c"]
    if args.run:
        cmd.append("-r")
    if args.keep_c:
        cmd.append("-k")
    if DEBUG:
        cmd.append("--debug")

    if DEBUG:
        print(f"[main] appel REX-SL: {' '.join(cmd)}")

    result = subprocess.run(cmd)

    if not args.keep_rsl:
        try:
            os.remove(rexsl_path)
        except OSError:
            pass

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()