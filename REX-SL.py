#
#* REX-SL compiler (python)
#* > V : beta 0.0.23
#* > R-ECO : 4.0.0
#* copyright (c) 2026 R-ECO4
# 0.0.23 : gestion python-like de None :
#          - nouveau type 'none' : var none x; declare un pointeur void* SL_x = NULL.
#          - litteral 'none' utilisable partout ou une valeur est attendue (show, cdn,
#            reaffectation, isnone). Tokenise comme ("none", None) par le lexer.
#          - show/showln : affiche "None" (comme Python) pour un litteral ou une
#            variable de type none.
#          - cdn == / != : comparaison none vs none, ou variable none vs none,
#            generee comme (ptr == NULL) / (ptr != NULL) en C.
#          - nouvel opcode 'isnone <dest_bool> <var>;' : teste si une variable de
#            type quelconque est none (NULL). Utile apres un retour de fonction
#            pouvant renvoyer none.
#          - reaffectation : 'x none;' remet un pointeur none a NULL (interdit
#            sur les types scalaires non-pointer : number/float/bool).
#          - type : retourne "none" pour une variable de type none.
#          - func -> none : type de retour explicite 'func f -> none;' genere void.
#          - return sans valeur : 'return none;' emis comme 'return;' dans un func void.

#
# 0.0.1  : basic lexer
# 0.0.2  : compilateur system
# 0.0.3  : calcul implementation total and show
# 0.0.4  : var implementation et gc
# 0.0.5  : stdbool.h + debug massif partout
# 0.0.6  : --debug (leger) et --stylish (colore, colorama) remplacent le mode debug fixe
# 0.0.7  : sub/mul/div/mod + fix bool (var/show) + fix add (resolution de type sur ident)
# 0.0.8  : condition system
# 0.0.9  : evo import
# 0.0.10 : run (import dynamique RUNTIME) + labels exposes via argv[1]
# 0.0.11 : scrc (injection C brute) + type (typeof en string) + list/dict
#          (append/get/pop/set) + input/write/read (I/O bas niveau)
#          -> passage en BETA
# 0.0.12 : gestion avancee des strings : len/tostr/tonum/tofloat/charat/slice/
#          find/upper/lower/trim + fix troncature silencieuse sur input (str)
# 0.0.13 : gestion avancee des strings suite : replace, reverse 
#          gestion supplementaire pour liste : split, join, readlines, splitlines
#          ajout de la shared memory avec shared_memory, share, save, del
# 0.0.14 : amelioration de la shared memory sans limites, GC aussi , si pas de supression alors
#          le compilateur demande confirmation si ya pas le flag --force-shm-nogc, si non alors un GC
#          est automatiquement mis en place.
#          mis en place des popall, pushall qui pousse toute les variables dans un liste temporaire
#          qui ne commence pas par SL mais par RXS_ et son scope
#          pushall pousse toute les variables sur RXS ce qui permet de redefinir les variables 
#          des variables peuvent etre forwarde par forward *arg qui copiera la valeur dans des 
#          nouvelles variables, un return peut aussi etre fait via return var qui copiera la valeur
#          dans le scope inférieur avec le nom RX_ret
#          ainsi des la 0.0.14 les fonction sont possible via func qui ne fait rien dautre qu'un 
#          pushall et un forward arg et un return et popall
# 0.0.15 : ajout de change <var> <type> (conversion generique number/float/bool/str),
#          remplace et supprime tostr/tonum/tofloat.
#          fix : reaffectation (<nom> <valeur>;) apres un change ciblait l'ancienne
#          generation de la variable (use-after-free potentiel) -> corrige.
#          fix : double free possible sur une string heap convertie via change puis
#          jamais retouchee jusqu'a la fin du programme -> corrige (_heap_unmark).
# 0.0.16 : patch de bugs et amelioration du systeme de fonction
# 0.0.17 : ajout de garde-fous dans main() (CLI) pour eviter les crashs bruts :
#          fichier source manquant/dossier/permissions/encodage invalide,
#          code -o/--oneline vide, lexer/compilateur proteges par un filet
#          Exception generique (en plus de REX_SL), RecursionError sur
#          programme trop imbrique, input() du GC shm protege contre stdin
#          non interactif (EOFError), nom de sortie (-O) vide/invalide,
#          protection contre l'ecrasement du fichier source par le .c genere,
#          verification de la presence de gcc avant de l'invoquer, nettoyage
#          du .c intermediaire securise (ne plante plus si deja absent),
#          erreurs d'execution de l'executable final (-r) gerees proprement,
#          Ctrl+C intercepte proprement en sortie de programme.
# 0.0.18 : (changelog perime, voir 0.0.20 ci-dessus pour le statut reel corrige)
#          1. FAIT : len generique, accepte list (->count) et str (strlen), dispatch
#             retro-compatible (len_of()).
#          2. FAIT : list_count, opcode dedie, alias explicite de len sur une list.
#          3. PARTIEL : _collection_dest_field_or_decl() existe (auto-declaration
#             d'une destination scalaire depuis un RexValue boxe) mais list_get/
#             list_pop/dict_get l'appellent PAS encore -- ils utilisent toujours
#             _collection_dest_field() qui exige une destination pre-declaree.
#             Pas de get/set/list_get comme sous-expression composee reutilisable
#             ailleurs pour l'instant. Reste a faire : brancher la variante
#             auto-declarante dans list_get/list_pop/dict_get (+ syntaxe etendue
#             'get <coll> <type> <dest> <idx>').
#          4. FAIT (ce patch) : operateurs in / notin, nouveaux opcodes 'in' et
#             'notin' (REX_SL_CODE.contains_op) :
#             'in <dest_bool> <val> <list>'  -> rexsl_list_contains (type ET valeur).
#             'in <dest_bool> <val> <str>'   -> rexsl_str_find(...) != -1.
#             'notin' = negation. Destination bool auto-declaree si absente, sinon
#             doit deja etre bool. Teste : membre present/absent dans list (number/
#             str), sous-chaine presente/absente, destination pre-declaree reutilisee
#             sur plusieurs tests -- tous corrects, compile et s'execute (gcc).
#          5. PAS FAIT : func_begin/return_stmt/exec_call n'acceptent toujours que
#             les 4 types scalaires (number/float/bool/str) pour parametres/retour ;
#             list/dict provoquent une erreur de type. A faire.
#          6. PAS FAIT : func_begin(param_pairs) attend une liste positionnelle
#             stricte (type, nom) ; aucune valeur par defaut, aucun support de
#             'nom=valeur' cote exec_call. A faire.
#          7. PAS FAIT : confirme bloquant. compile() appelle _detect_recursive_call()
#             sur symbol_table["call_graph"] et leve une REX_SL (erreur de compilation,
#             pas juste un warning) des qu'un cycle direct/indirect existe entre
#             func/exec -- la recursion est donc explicitement rejetee, avec le
#             commentaire "aucune protection de pile" comme raison. A faire : retirer
#             ce garde-fou (ou le rendre non bloquant) ET verifier que chaque appel
#             recursif genere obtient bien des variables C locales par appel (pile C
#             native) sans alias sur des heap_vars/collections partages entre appels
#             imbriques -- pas encore audite.
#          Prochain patch : item 3 (brancher l'auto-declaration dans list_get/
#          list_pop/dict_get), puis 5/6/7 dans l'ordre.
# 0.0.19 : les 7 limitations demandees par REX.py sont desormais TOUTES implementees
#          et verifiees par compilation+execution reelle (gcc, + gcc -fsanitize=address,
#          undefined sur plusieurs programmes de test couvrant les 7 points). Le
#          changelog 0.0.19 ci-dessous annoncait 5/6/7 comme non faits alors que le
#          code les avait deja (func_begin/exec_call/return_stmt geraient deja
#          list/dict, defaults, args nommes, et la recursion n'etait deja plus
#          bloquante) -- seul le changelog etait perime. Ce qui a reellement ete
#          corrige dans ce patch (bugs trouves en compilant/executant des programmes
#          de test de bout en bout, pas juste en relisant le code) :
#          1/2. len/list_count : list_count n'avait AUCUN cas dans le dispatch de
#             _compile_line -- opcode mort, corrige (case "list_count" ajoute).
#          3. get/pop syntaxe etendue (auto-declaration) : deux bugs corriges --
#             (a) le pre-scan de const-inference marque const toute variable ecrite
#             une seule fois, y compris une destination tout juste auto-declaree par
#             'get' ; les checks const de list_get/list_pop/dict_get/dict_get_hinted/
#             _collection_dest_field_or_decl rejetaient donc leur propre
#             auto-declaration ("modification interdite, constante") -- corrige en
#             ne bloquant que si la variable etait DEJA declaree avant cet appel.
#             (b) la declaration typee generee etait entouree d'un bloc '{ ... }',
#             donc la variable disparaissait juste apres la ligne 'get' -- corrige
#             (plus d'accolades, temporaire RexValue nomme par destination pour
#             eviter les collisions entre plusieurs 'get' auto-declarants dans le
#             meme scope).
#          4. in/notin : inchange, deja correct.
#          5. list/dict en parametre/retour de func : le code (func_begin/endfunc/
#             exec_call/return_stmt) gerait deja list/dict par pointeur (pas de
#             copie, pas de double free au retour), mais plusieurs bugs bloquaient
#             son usage reel : RX_ret de type list/dict faisait planter compile()
#             (KeyError, "list"/"dict" absents du type map C de sa declaration) ;
#             et append/get/pop/set ne reconnaissaient une collection QUE si elle
#             etait dans symbol_table["var"] (registre SL), donc impossible de
#             faire 'get' directement sur un RX_ret list/dict -- nouveau helper
#             _collection_kind() qui resout via le bon registre (SL ou RX),
#             branche partout ou une collection est acceptee en operande.
#          6. defaults/args nommes : inchange, deja correct (verifie avec
#             exec fact; puis exec fact n=6; sur la meme fonction).
#          7. recursion : deja non bloquante (warning), mais deux bugs C annexes
#             la rendaient non compilable en pratique des qu'un 'func' recursif
#             utilisait cdn/go et/ou retournait une str : (a) __rexsl_cond declaree
#             APRES les FUNC_<n> qui l'utilisent -- deplacee avant, comme RX_ret ;
#             (b) le temporaire de retour str '__rexsl_ret_tmp' avait un nom FIXE :
#             une fonction avec plusieurs 'return' str (ex: cas de base + cas
#             recursif) generait deux declarations C du meme nom dans la meme
#             portee -- corrige avec un compteur global (__rexsl_ret_tmp_<n>).
#          Bug annexe (independant des 7 points, trouve via gcc -fsanitize) : les
#          etiquettes 'lbl' declarees a l'interieur d'un 'func' etaient enregistrees
#          comme points d'entree top-level du programme (dispatch argv[1]),
#          generant des 'goto LBL_x;' invalides dans main() -- corrige (etiquettes
#          internes a un func desormais exclues de ce registre, + detection propre
#          des doublons de lbl DANS un meme func, avant ne remontait qu'une erreur
#          gcc brute "duplicate label").
#          BUG CONNU (structurel, hors perimetre des 7 points, trouve via
#          gcc -fsanitize=address) : dans un 'func' dont le corps utilise
#          cdn/go pour sauter par-dessus la declaration d'une variable str/
#          list/dict locale avant d'atteindre un 'return' (ex: 'cdn ...; go
#          base; var str r; ...; lbl base; return "";'), endfunc/return_stmt
#          liberaient quand meme cette variable a la fin (le tracking
#          heap_vars n'etait pas sensible au chemin de controle reellement
#          emprunte) -> free() d'un pointeur non initialise, double-free/UB
#          confirme par AddressSanitizer. CORRIGE EN 0.0.21, voir ci-dessous.
# 0.0.20 : correctif du bug free()-sur-pointeur-non-initialise documente en
#          0.0.19 (cdn/go sautant une declaration str/list/dict avant un
#          return dans un 'func'). Principe : hissage ('hoist') a NULL en
#          tete de bloc (func/endfunc, ou main()) de toute variable str/
#          list/dict dont c'est la premiere declaration heap-trackee, et
#          passage de tous les free() de fin de bloc en conditionnel +
#          idempotent (if (x) { free(x); x = NULL; }).
#          Modifie : symbol_table (nouvelles piles heap_str_decls et
#          collection_hoist, synchronisees avec heap_vars/collection_vars
#          dans func_begin/endfunc) ; nouveaux helpers _can_hoist(),
#          _hoisted_decl_lines(), _conditional_free_lines() ; var() (str
#          longue, list, dict), _assign_heap_str(), list_get/dict_get_hinted
#          (auto-declaration avec hint str), add()/sub()/mul() (branches
#          concat/remove_all/repeat auto-declarantes) : declaration inline
#          remplacee par une simple affectation quand _can_hoist() est vrai ;
#          endfunc()/return_stmt()/assemblage final de main() : free()
#          rendus conditionnels via _conditional_free_lines.
#          Repro confirme sous gcc -fsanitize=address,undefined : crash
#          avant patch ("attempting free on address which was not
#          malloc()-ed"), exit 0 apres patch. Non-regression verifiee sous
#          ASan/UBSan sur concatenation str auto-declarante dans un func et
#          list/dict via 'get <coll> <type> <dest> <idx>'.
#          Perimetre volontairement exclu : le mecanisme legacy pushall/
#          popall/forward (emission de code directe, sans buffer differe
#          -> hoisting structurellement impossible sans refonte plus
#          lourde ; _can_hoist() y retombe sur l'ancien comportement
#          inline, donc pas de regression, juste pas de correctif la).
#          LIMITE RESIDUELLE (corrigee en 0.0.22) : si c'est la ligne de
#          *promotion* pile->tas d'une variable DEJA declaree en str courte
#          (buffer pile), et non sa declaration d'origine, qui est sautee
#          par un 'go', le pointeur reste non-NULL (il pointe encore vers le
#          buffer pile) et le free conditionnel la liberait quand meme a
#          tort. Corrige en 0.0.22 : var() hoiste desormais TOUTES les str
#          (courtes y compris) a NULL en tete de bloc quand _can_hoist()
#          est vrai, de sorte qu'aucune variable str ne demarre jamais sur
#          la pile dans un contexte ou elle pourrait etre promue par la suite.
# 0.0.22 : correctif du bug residuel free()-sur-pointeur-pile documente en
#          0.0.20/0.0.21. Dans var(), branche str courte
#          (len < STACK_STR_THRESHOLD), si _can_hoist() est vrai, on utilise
#          desormais rexsl_str_alloc + hissage a NULL (comme pour les str
#          longues) au lieu du buffer pile char[]. Consequence : toute variable
#          str dans un func ou dans main() commence sa vie a NULL -> le free()
#          conditionnel de _conditional_free_lines est sans danger meme si un
#          add/sub/mul de promotion est saute par un 'go'. Le buffer pile
#          n'est conserve que dans les scopes pushall/popall manuels
#          (_can_hoist() = False), ou le code est emis en flux continu et le
#          hoisting est de toute facon impossible.

r"""
# REX-SL Compiler — Documentation

> **Version** : beta 0.0.22
> **R-ECO** : 4.0.0
> © 2026 R-ECO4

---

## Sommaire

- [Bases](#bases)
- [Variables](#variables)
- [Affichage](#affichage)
- [Calcul](#calcul)
- [Types](#types)
- [Strings avancées](#strings-avancées)
- [Split / Join](#split--join)
- [Mémoire partagée](#mémoire-partagée-inter-processus-posix-shm)
- [Fonctions](#fonctions)
  - [Scopes manuels (pushall / popall / forward / return)](#scopes-manuels-pushall--popall--forward--return)
  - [Fonctions C réelles (func / endfunc / exec)](#fonctions-c-réelles-func--endfunc--exec)
- [Collections](#collections)
- [Entrées / Sorties bas niveau](#entrées--sorties-bas-niveau)
- [Injection C brute](#injection-c-brute)
- [Conditions](#conditions)
- [Modules](#modules)
- [CLI / Compilateur (robustesse)](#cli--compilateur-robustesse)
- [Erreurs connues / limitations](#erreurs-connues--limitations)

---

## Bases

REX-SL est la dernière étape avant transpilation vers C du langage REX. La syntaxe est de type assembleur, avec aucune ou très peu d'abstractions.

### Syntaxe

Chaque **opcode** (nom d'une instruction) est composé d'un mot-clé et de paramètres. L'opcode est conclu par un `;`.

---

## Variables

### Déclaration

```
var <type> <name> [valeur];
```

Déclare une variable et la marque dans le registre `$VAR` (SL, local).
`<type>` accepte : `number`, `float`, `bool`, `str`, `list`, `dict`, `none`. `list`, `dict` et `none` ne prennent pas de valeur initiale (ou `none` comme valeur explicite pour `none`).
Une variable ne peut être déclarée qu'une seule fois (erreur si `<name>` existe déjà).

### Chargement (réaffectation)

```
<name> <value>;
```

Change la valeur de la variable `<name>` (déjà déclarée) par `<value>`. Le type de `<value>` doit correspondre exactement au type de `<name>`.

### Lecture

Simplement `<name>` là où une valeur est attendue (`show`, `add`, `cdn`, etc.)

---

## Affichage

| Instruction | Effet |
|---|---|
| `showln <value>;` | affiche `<value>` et retourne à la ligne |
| `show <value>;` | affiche `<value>` sans retour à la ligne |

---

## Calcul

| Instruction | Comportement |
|---|---|
| `add <dest> <a> <b>;` | `number+number` → addition, float mixé → promotion float, `str+str` → concaténation (malloc/realloc, libéré automatiquement en fin de programme) |
| `sub <dest> <a> <b>;` | `number-number` → soustraction, `str-str` → supprime toutes les occurrences de `<b>` dans `<a>` (équivalent `.replace(b, "")`) |
| `mul <dest> <a> <b>;` | `number*number` → multiplication, `str*number` (ou `number*str`) → répète la string `<b>` fois |
| `div <dest> <a> <b>;` | division protégée contre le zéro (erreur compile-time si connu, check runtime sinon) |
| `mod <dest> <a> <b>;` | modulo entier uniquement (non géré sur les float) |

---

## Types

### Typeof

```
type <dest> <op>;
```

Écrit dans `<dest>` (variable `str` déjà déclarée) le nom du type REX-SL de `<op>` : `"number"`, `"float"`, `"bool"`, `"str"`, `"list"`, `"dict"` ou `"none"`.

### None (valeur absente, Python-like)

| Instruction | Effet |
|---|---|
| `var none <name>;` | déclare un pointeur opaque initialisé à `NULL` (équivalent de `x = None` en Python) |
| `showln none;` / `show none;` | affiche `None` (comme Python) |
| `cdn == <var> none;` | teste si `<var>` est `None` (comparaison contre `NULL`) — seuls `==` et `!=` sont autorisés |
| `isnone <dest_bool> <var>;` | écrit `true` dans `<dest>` si `<var>` est `NULL`/`None`, `false` sinon. Fonctionne aussi sur les types pointeurs (`str`, `list`, `dict`). Toujours `false` sur les scalaires (`number`/`float`/`bool`) |
| `<name> none;` | réaffecte une variable de type `none` à `NULL` (idempotent) |
| `func f -> none;` | déclare une fonction de type de retour `void` (aucune valeur renvoyée) |
| `return none;` | sortie anticipée d'une fonction `void` (libre la mémoire heap locale puis émet `return;`) |

---

## Strings avancées

| Instruction | Effet |
|---|---|
| `len <dest_number> <str>;` | écrit dans `<dest>` (number déjà déclarée) le nombre de caractères de `<str>` |
| `charat <dest_str> <str> <idx>;` | écrit dans `<dest>` le caractère de `<str>` à l'index `<idx>` (1 caractère). Index hors limites → **erreur fatale à l'exécution** |
| `slice <dest_str> <str> <start> <end>;` | écrit dans `<dest>` la sous-chaîne `[start, end)` de `<str>`. Bornes clampées silencieusement (pas d'erreur fatale) |
| `find <dest_number> <str> <substr>;` | index de la première occurrence de `<substr>` dans `<str>`, ou `-1` si absente |
| `upper <dest_str> <str>;` | copie `<str>` en majuscules dans `<dest>` |
| `lower <dest_str> <str>;` | copie `<str>` en minuscules dans `<dest>` |
| `trim <dest_str> <str>;` | copie `<str>` dans `<dest>` en retirant les espaces/tabulations/retours à la ligne en début et fin |
| `replace <dest> <str> <old> <new>;` | remplace toutes les occurrences de `<old>` par `<new>` (substitution, contrairement à `sub` qui supprime) |
| `reverse <dest> <str>;` | inverse l'ordre des caractères de `<str>` |

> **Note mémoire** : `charat`/`slice`/`upper`/`lower`/`trim`/`replace`/`reverse` allouent toujours `<dest>` sur le tas (GC automatique en fin de programme, même mécanisme que `add` en mode concaténation).

## Conversion de type (change)

| Instruction | Effet |
|---|---|
| `change <var> <type>;` | convertit `<var>` (deja declaree) vers `<type>` (`number`/`float`/`bool`/`str`). Erreur si `<var>` est `list`/`dict`, si `<type>` est déjà son type courant, ou si `<var>` est une variable RX_ (registre importe, lecture seule) |

### Règles de conversion

| De \ Vers | number | float | bool | str |
|---|---|---|---|---|
| number | — | cast | `!= 0` | `%d` |
| float | cast (troncature) | — | `!= 0` | `%g` |
| bool | 0/1 | 0.0/1.0 | — | `"true"`/`"false"` |
| str | `atoi` (0 si non numerique) | `atof` (0 si non numerique) | premier caractere `t`/`1` | — |

> **Note interne** : `change` ne modifie pas la variable C existante (impossible en C) mais en génère une nouvelle sous le même nom REX-SL (mécanisme de génération interne, transparent pour l'utilisateur). L'ancienne valeur, si allouée sur le tas, est libérée immédiatement — aucune fuite ni double libération.

---

## Split / Join

| Instruction | Effet |
|---|---|
| `split <dest_list> <str> <delim>;` | découpe `<str>` selon `<delim>` et ajoute chaque morceau (str) à `<dest_list>` (liste déjà déclarée) |
| `join <dest_str> <list> <delim>;` | concatène tous les éléments de `<list>` (convertis en texte selon leur type) séparés par `<delim>` |
| `readlines <dest_list> <path>;` | raccourci de `read` + `split "\n"` : lit `<path>` et découpe son contenu ligne par ligne |
| `writelines <path> <list>;` | raccourci de `join "\n"` + `write` : écrit `<list>` dans `<path>`, un élément par ligne |

---

## Mémoire partagée (inter-processus, POSIX shm)

| Instruction | Effet |
|---|---|
| `shared_memory <name>;` | active la mémoire partagée pour ce programme. **DOIT être la toute première instruction du fichier.** `<name>` identifie le segment (`/dev/shm/rexsl_<name>`), partagé entre tous les exécutables REX-SL utilisant le même `<name>` |
| `share <source> <name>;` | publie la variable primitive `<source>` (`number`/`float`/`bool`/`str`) sous la clé `<name>` dans la mémoire partagée (protégé par sémaphore) |
| `save <dest> <name>;` | récupère la valeur associée à `<name>` et l'écrit dans `<dest>` (variable déjà déclarée, même type attendu). Erreur fatale si `<name>` est inconnue |
| `save <dest>;` (sans nom) | si `<dest>` est une liste → remplie avec TOUS les noms de clés actuellement partagées ; si `<dest>` est un dictionnaire → rempli avec TOUTES les paires clé/valeur partagées |
| `del <name>;` | supprime la clé `<name>` de la mémoire partagée |

### Capacité et cycle de vie

Le segment **grandit automatiquement** (`ftruncate`/`mremap` internes, protégés par sémaphore) : plus de limite fixe sur le nombre d'entrées ni sur la longueur des clés/valeurs.

Le compilateur trace les clés publiées (`share`) et supprimées (`del`) **dans ce module**, à condition que le nom soit un littéral connu à la compilation (une clé passée via une variable n'est pas traçable et n'entre pas dans ce bilan).

S'il reste des clés jamais nettoyées à la fin du programme :

- **sans** `--force-shm-nogc` → le compilateur demande une confirmation interactive avant de continuer ;
- **avec** `--force-shm-nogc` → un **GC automatique** (`atexit`) est inséré silencieusement pour les supprimer en fin de programme.

---

## Fonctions

REX-SL propose désormais **deux mécanismes de fonctions**, indépendants l'un de l'autre :

1. les **scopes manuels** (`pushall`/`popall`/`forward`/`return`), inchangés depuis la 0.0.14 — un simple bloc C `{ ... }` avec sauvegarde/restauration de variables, sans notion de fonction C réelle ;
2. les **fonctions C réelles** (`func`/`endfunc`/`exec`), nouveau système qui **remplace l'ancien sucre syntaxique** `func = lbl + pushall` de la 0.0.14. `func` ne fait plus un simple `lbl` + `pushall` : il ouvre désormais une véritable fonction C, compilée séparément et déclarée en prototype avant `main()`.

Les deux systèmes peuvent cohabiter dans le même programme, mais **ne se mélangent pas dans le même bloc** : un `func` ne s'appuie plus sur `pushall`/`forward` en interne.

### Scopes manuels (pushall / popall / forward / return)

| Instruction | Effet |
|---|---|
| `pushall;` | ouvre un nouveau scope C réel (`{ ... }`). Sauvegarde une copie de chaque variable primitive du scope courant sous `RXS_<profondeur>_<nom>`, ce qui permet au code suivant de redéclarer librement les mêmes noms sans collision. Les `list`/`dict` ne sont pas transmissibles par ce mécanisme |
| `popall;` | ferme le scope ouvert par le dernier `pushall` (libère aussi la mémoire heap allouée à l'intérieur de ce scope) |
| `forward <arg1> [arg2 ...];` | copie chaque `<argN>` (lu dans le scope parent sauvegardé par `pushall`) vers une nouvelle variable de même nom dans le scope courant. Les `str` sont dupliquées sur le tas (jamais un alias de pointeur). Au moins un argument est requis ; chaque argument doit exister dans le scope parent et ne pas déjà être déclaré dans le scope courant |
| `return <var>;` | **en dehors d'un `func`** : copie `<var>` (scope courant) vers le scope inférieur sous le nom fixe `RX_ret` (comportement historique, inchangé) |

### Exemple (scopes manuels)

```
lbl add_one;
pushall;
    forward n;
    add n n 1;
    return n;
popall;

# ailleurs :
var number x 5;
go add_one;
showln RX_ret;
```

> ⚠️ `RX_ret` est déclaré **une seule fois, globalement**, typé sur le type du **premier** `return` rencontré dans le programme (que ce `return` provienne d'un scope manuel ou de la valeur de retour d'un `exec`, voir plus bas). Deux sources renvoyant des types différents provoquent une erreur de compilation.

---

### Fonctions C réelles (func / endfunc / exec)

Nouveau système : `func` déclare une **vraie fonction C**, compilée à part et insérée (prototype + corps) avant `main()`. Ses paramètres deviennent des variables locales C typées de la fonction générée, **isolées de l'appelant** — aucune collision de nom possible, contrairement à l'ancien `pushall`/`RXS_`.

| Instruction | Effet |
|---|---|
| `func <name> [<type1> <arg1> <type2> <arg2> ...];` | ouvre la déclaration de la fonction `<name>` avec ses paramètres typés (`number`/`float`/`bool`/`str`). Aucune valeur initiale possible pour les paramètres. Ne peut pas être imbriqué (un `func` doit être fermé par `endfunc` avant d'en ouvrir un autre). Le nom ne peut être déclaré qu'une seule fois |
| `endfunc <name>;` | ferme la fonction ouverte par le `func <name>` correspondant, assemble sa signature C et son corps, et restaure l'espace de noms de l'appelant. Le type de retour est déduit automatiquement du **premier** `return` rencontré dans le corps (fonction `void` si aucun `return`) |
| `exec <name> <val1> [val2 ...];` | appelle la fonction C `FUNC_<name>` avec ces arguments (nombre et types doivent correspondre exactement aux paramètres déclarés par `func`). Si la fonction retourne une valeur, celle-ci est copiée dans `RX_ret` (mêmes règles de typage global que le `return` des scopes manuels) |
| `return <var>;` | **à l'intérieur d'un `func`** : `return` C réel — libère automatiquement toute la mémoire heap allouée localement dans la fonction avant de renvoyer `<var>` (les `str` sont copiées sur le tas pour que l'appelant possède sa propre copie, le buffer local disparaissant à la sortie de la fonction) |

### Exemple (fonctions C réelles)

```
func add_one number n;
    add n n 1;
    return n;
endfunc add_one;

# ailleurs :
var number x 5;
exec add_one x;
showln RX_ret;
```

### Points d'attention

- Un même programme peut mélanger les deux systèmes (des `func`/`exec` et des `lbl`/`pushall` séparés), mais **`RX_ret` reste unique et global** : la première source de retour rencontrée (qu'il s'agisse d'un `exec` de fonction C réelle ou d'un `return` en scope manuel) fixe définitivement son type.
- Une fonction `func` sans aucun `return` dans son corps est compilée en `void` ; un `exec` vers cette fonction ne touche pas `RX_ret`.
- `list`/`dict` ne sont pas des types de paramètres ou de retour valides pour `func`/`return`/`exec`.
- Une déclaration `func` non refermée par `endfunc` avant la fin du fichier est une erreur de compilation.

---

## Collections

### Déclaration

```
var list <name>;
var dict <name>;
```

### Listes

| Instruction | Effet |
|---|---|
| `append <list> <value>;` | ajoute `<value>` en fin de liste |
| `get <list> <dest> <idx>;` | copie l'élément à l'index `<idx>` dans `<dest>` (variable primitive déjà déclarée, même type que la valeur stockée) |
| `pop <list>;` | retire et jette le dernier élément |
| `pop <list> <dest>;` | retire le dernier élément et le copie dans `<dest>` |
| `pop <list> <dest> <idx>;` | retire l'élément à l'index `<idx>` et le copie dans `<dest>` |

### Dictionnaires

| Instruction | Effet |
|---|---|
| `set <dict> <key> <value>;` | associe `<value>` à la clé `<key>` (string obligatoire), écrase si la clé existe déjà |
| `get <dict> <dest> <key>;` | copie la valeur associée à `<key>` dans `<dest>` |

### Appartenance (`in` / `notin`)

| Instruction | Effet |
|---|---|
| `in <dest_bool> <valeur> <list>;` | `<dest_bool>` = vrai si `<valeur>` est présente dans `<list>` (comparaison type ET valeur, élément par élément) |
| `notin <dest_bool> <valeur> <list>;` | négation de `in` |
| `in <dest_bool> <valeur_str> <str>;` | `<dest_bool>` = vrai si `<valeur_str>` est une sous-chaîne de `<str>` (réutilise `find`/`rexsl_str_find`) |
| `notin <dest_bool> <valeur_str> <str>;` | négation de `in` sur une string |

`<dest_bool>` est auto-déclarée (type `bool`) si elle n'existe pas encore ; si elle existe déjà, elle doit être de type `bool`.

> Listes et dictionnaires sont automatiquement libérés (`rexsl_list_free`/`rexsl_dict_free`) en fin de programme, au même titre que les strings du tas (GC rudimentaire).

---

## Entrées / Sorties bas niveau

| Instruction | Effet |
|---|---|
| `input <dest>;` | lit une ligne sur stdin dans `<dest>` (déjà déclarée). `number`/`float` lisent via `scanf`, `bool` lit `t`/`1` en premier caractère, `str` lit via `fgets` (buffer 1024) et retire le retour à la ligne — une variable `str` est toujours promue sur le tas après un `input` |
| `write <path> <value>;` | ouvre `<path>` en écriture (mode `"w"`, écrase le contenu existant) et écrit `<value>` convertie en texte |
| `read <path> <dest>;` | lit le contenu ENTIER de `<path>` dans `<dest>` (str déjà déclarée). Toujours alloué sur le tas |

---

## Injection C brute

```
scrc <code>;
```

Injecte le contenu de `<code>` (string littérale) **tel quel** comme code C brut, sans aucune vérification de syntaxe ni de sens. À partir de cette ligne, on sort du cadre protégé de REX-SL.

> ⚠️ Si `<code>` contient un `;`, celui-ci doit être correctement géré par le lexer (split quote-aware) pour ne pas être interprété comme fin d'opcode REX-SL. Il est de la responsabilité de l'auteur d'écrire du C syntaxiquement valide (y compris le `;` final des instructions C, non ajouté automatiquement).

---

## Conditions

| Instruction | Effet |
|---|---|
| `lbl <name> [<type1> <arg1> ...];` | déclare une étiquette à laquelle on peut sauter avec `go`, ou vers laquelle un autre module peut dispatcher via `run <path> <lbl>`. Ne peut être déclarée qu'une seule fois |
| `cdn <op> <a> <b>;` | évalue `<a> <op> <b>` et mémorise le résultat (une seule condition "courante" à la fois). `<op>` accepte les symboles (`==`, `!=`, `>`, `<`, `>=`, `<=`) et les mots-clés équivalents (`equal`/`eq`, `not_equal`/`neq`/`ne`/`different`, `greater`/`gt`, `less`/`lt`, `greater_equal`/`ge`, `less_equal`/`le`). Les strings sont comparées avec `strcmp`, les nombres/bool directement |
| `cdn on;` | force la condition courante à vraie, pour un saut garanti avec `go` |
| `go <name>;` | saute à l'étiquette `<name>` SI la dernière condition évaluée (`cdn`) est vraie |

---

## Modules

| Instruction | Effet |
|---|---|
| `run <path>;` | exécute au **runtime** l'exécutable REX-SL situé à `<path>` (déjà compilé), depuis son début. Résolution via `system()` : `<path>` peut pointer vers un binaire différent sans jamais recompiler le programme appelant |
| `run <path> <lbl>;` | idem, mais demande au module cible de sauter directement à son étiquette `<lbl>`. Côté module cible : chaque `lbl` déclaré devient une cible d'entrée valide (lancement avec le nom de l'étiquette en `argv[1]`) |

---

## CLI / Compilateur (robustesse)

Depuis la 0.0.17, `main()` (le point d'entree CLI) est protege par une serie de
garde-fous afin qu'une erreur d'environnement ou d'utilisation ne produise plus
un traceback Python brut, mais un message `[REX-SL] erreur : ...` exploitable
sur `stderr` (et un code de sortie non nul).

| Situation | Comportement |
|---|---|
| `-f <file>` inexistant, dossier, illisible (permissions) ou mal encode | erreur claire via `parser.error(...)`, sortie immediate |
| `-f <file>` vide ou sans header `# REX-SL>` | erreur claire (comportement deja existant, desormais plus robuste sur le vide via `.strip()`) |
| `-o ""` (code en ligne vide) | erreur claire au lieu de compiler du vide |
| Exception inattendue pendant le **lexing** ou la **compilation** (bug interne, pas seulement `REX_SL`) | interceptee et rapportee proprement ; le traceback complet n'est re-leve qu'en mode `--debug`/`--stylish` |
| Programme source trop imbrique (deborde la pile Python du compilateur) | `RecursionError` intercepte et rapporte comme une limite de complexite, pas un crash |
| Confirmation interactive du GC shm orphelin (`input()`) lancee avec stdin non interactif (script, CI, pipe) | `EOFError` intercepte, comportement par defaut = pas de GC (comme une reponse vide) |
| `-O <output>` vide, `.` ou `..` | erreur claire, aucun fichier n'est genere |
| `-O <output>` pointant (par erreur) vers le meme chemin que le fichier source `-f` | erreur claire, empeche d'ecraser le source avec le `.c` genere |
| Ecriture du `.c` intermediaire impossible (disque plein, permissions, chemin invalide) | erreur claire, sortie immediate |
| `gcc` absent du `PATH` | detecte **avant** l'appel `subprocess.run` (`shutil.which`), message d'installation suggere |
| `gcc` present mais inexecutable, ou tout autre echec de lancement du process | erreur claire au lieu d'un `OSError` brut |
| Suppression du `.c` intermediaire (nettoyage normal ou apres echec gcc) | ne plante plus si le fichier a deja disparu ou est verrouille ; le nettoyage est centralise (`_cleanup_c_file`) et systematique meme en cas d'echec de compilation C |
| Execution de l'executable final (`-r`) : permission refusee, binaire introuvable/casse | erreur claire au lieu d'un crash ; le code de retour non nul de l'executable est desormais signale sur `stderr` |
| `Ctrl+C` en cours d'execution | intercepte proprement (code de sortie `130`), pas de traceback |
| Tout autre bug non anticipe remontant jusqu'au point d'entree | filet de securite final : message `[REX-SL] erreur interne inattendue : ...`, sortie avec code `1` |

> **Note** : ces garde-fous concernent uniquement la robustesse du **compilateur
> Python lui-meme** (CLI, I/O disque, appel a `gcc`, execution du binaire). Ils
> ne changent rien a la semantique du langage REX-SL ni aux erreurs `REX_SL`
> deja levees pendant la compilation (variable inconnue, type incompatible,
> etc.), qui restent rapportees exactement comme avant.

---

## Erreurs connues / limitations

- Comportement de `run <path> <lbl>;` en présence de `RX_ret`/`pushall` non initialisés au moment du saut `goto` (le dispatch d'entrée via `argv[1]` saute directement à l'étiquette, donc toute initialisation précédente — y compris celle de `RX_ret` — est court-circuitée). C'est cohérent avec le comportement déjà existant avant la 0.0.14, donc pas une régression, mais reste une source de bugs silencieux si un scope accède à `RX_ret` avant qu'un `return`/`exec` n'ait eu lieu dans le flot d'exécution réel.
- Robustesse de la marque de suppression dans `rexsl_shm_del` (clé mise à zéro plutôt que compaction réelle du buffer) : fonctionnelle mais laisse les entrées "mortes" occuper de la place jusqu'à la fin du programme.
- Les fonctions C réelles (`func`/`endfunc`/`exec`) et les scopes manuels (`pushall`/`popall`/`forward`) partagent la même variable globale `RX_ret` : mélanger les deux styles dans un même programme reste possible mais impose que toutes les sources de retour soient du même type REX-SL.
- Un `func` ne peut pas être imbriqué dans un autre `func` ; il n'existe pas non plus de mécanisme de récursion vérifié statiquement (un `exec` d'une fonction vers elle-même compile, mais aucune protection de pile n'est ajoutée par REX-SL).
- Depuis le correctif 0.0.21 (hissage à `NULL` en tête de bloc + `free()` conditionnel), le cas où `cdn`/`go` saute la *déclaration* d'une variable `str`/`list`/`dict` locale dans un `func` avant un `return` est corrigé et vérifié sous AddressSanitizer. Reste ouvert : si c'est la ligne de *promotion* pile→tas d'une variable **déjà déclarée** en `str` courte (buffer pile) — pas sa déclaration d'origine — qui est sautée, le pointeur libéré n'est pas `NULL` et le `free()` conditionnel la libère quand même à tort (nécessiterait un flag runtime par variable, non implémenté).
- Le hissage introduit par le correctif 0.0.21 ne s'applique pas au mécanisme legacy `pushall`/`popall`/`forward` (émission de code directe, sans buffer différé) : ce système reste donc exposé au même type de bug s'il est combiné avec `cdn`/`go` sautant une déclaration heap-trackée, contrairement aux blocs `func`/`endfunc` et à `main()`.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time

# colorama est optionnel : s'il n'est pas installe, le mode --stylish
# fonctionnera quand meme mais sans les couleurs dans le terminal.
try:
    from colorama import init as _colorama_init, Fore, Style
    _colorama_init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False

# ============================================================
#  DEBUG SYSTEM
# ============================================================
#
#  MODE = "off"      -> aucun log
#  MODE = "debug"    -> logs "haut niveau" seulement (etapes importantes)
#  MODE = "stylish"  -> logs complets (haut niveau + trace detaillee) EN COULEUR
#
# ------------------------------------------------------------

MODE = "off"          # mode de debug courant, change par les arguments CLI (--debug / --stylish)
INDENT_LEVEL = 0       # niveau d'indentation courant des logs (augmente/diminue avec log_enter/log_exit)

# une couleur par "famille" de tag (le prefixe avant le point), pour s'y retrouver visuellement
TAG_FAMILY_COLORS = {
    "LEXER": "CYAN",
    "CODE": "YELLOW",
    "COMPILER": "MAGENTA",
    "MAIN": "GREEN",
    "ARGPARSE": "BLUE",
    "ERROR": "RED",
}

# registre global des symboles connus par le compilateur.
# "var"     -> variables locales SL (nom -> type "number"/"float"/"bool"/"str"), compilees en SL_<nom>
# "rx_var"  -> variables/symboles externes RX (importes), compiles tels quels (RX_<nom>), pas de prefixe SL_
# "heap_vars" -> noms C (deja prefixes) alloues dynamiquement, a liberer (free) en fin de programme

symbol_table = {
    "var": {}, "rx_var": {},
    "heap_vars": [set()],   # pile de scopes: heap_vars[0] = scope racine, [-1] = scope courant
    "rexfn": [], "labels": [],
    # pile de scopes (comme heap_vars) : [(c_name, "list"|"dict"), ...] par scope.
    # collection_vars[0] = scope racine (main), libere en fin de programme ;
    # un nouveau scope est empile a func_begin et libere/depile a endfunc, pour
    # que 'var list ...;'/'var dict ...;' declares DANS une fonction soient
    # liberes a la sortie de CETTE fonction plutot que de polluer l'epilogue
    # global de main() avec un nom C hors de portee (voir §5 des extensions).
    "collection_vars": [[]],
    # pile de scopes (comme heap_vars) : noms C dont la PREMIERE declaration est
    # heap-tracked (str longue via 'var', ou destination auto-declaree par
    # add/sub/mul/get/_assign_heap_str). Sert a hisser ("hoist") ces declarations
    # a NULL en tete du bloc englobant (func/main) plutot que de les declarer
    # inline au point d'origine -- voir _heap_mark/le bug connu documente en
    # tete de fichier (double free si cdn/go saute par-dessus la declaration).
    # NOTE : les 'str' courtes (buffer pile, voir var()) et les variables
    # PROMUES pile->tas par une reaffectation/operation ulterieure (add/sub sur
    # une variable deja declaree, reaffectation directe) ne sont PAS couvertes
    # par ce hoisting -- seule la toute premiere declaration heap est hissee.
    # Un saut qui evite la ligne de PROMOTION (mais atteint bien la declaration
    # initiale) etait un residu de bug non couvert ici -- corrige en 0.0.22
    # (var() hoiste toutes les str a NULL quand _can_hoist(), voir changelog).
    "heap_str_decls": [set()],
    # pile de scopes (comme heap_str_decls) : sous-ensemble des NOMS presents dans
    # collection_vars dont la declaration ('var list'/'var dict') a ete hissee a
    # NULL (voir _can_hoist()). Une collection declaree DANS un scope 'pushall'
    # manuel reste dans collection_vars (pour etre liberee normalement) mais PAS
    # dans ce registre, pour ne pas generer une seconde declaration hissee en
    # plus de sa declaration inline existante.
    "collection_hoist": [set()],
}

symbol_table["var_gen"] = {}        # nom -> generation courante (0 = declaration initiale)
symbol_table["var_gen_stack"] = []  # sauvegarde/restauration scoping via pushall/popall
symbol_table["shm_enabled"] = False
symbol_table["shm_name"] = None
symbol_table["shm_shared_keys"] = []    # cles publiees (litteraux connus) via share() dans ce module
symbol_table["shm_deleted_keys"] = []   # cles supprimees (litteraux connus) via del() dans ce module
symbol_table["scope_stack"] = []        # pile de dict {nom: type} sauvegardes par pushall
symbol_table["scope_depth"] = 0
symbol_table["rx_ret_declared"] = False
symbol_table["rx_ret_type"] = None
symbol_table["functions"] = {}        # name -> [(type, argname), ...]
symbol_table["current_func"] = None   # nom de la func en cours de compilation (None hors func)
symbol_table["exec_counter"] = {}     # name -> compteur pour labels AFTER_EXEC uniques
symbol_table["call_graph"] = {}       # name -> {noms appelés via exec} pour détecter récursion
symbol_table["labeled_params"] = {}   # pour lbl paramétrés (dispatch run) : name -> [(type,arg)]
symbol_table["func_local_labels"] = {}  # nom de func -> set des etiquettes 'lbl' declarees dans son corps (dedup)
symbol_table["ret_tmp_counter"] = 0    # compteur global pour nommer de facon unique les temporaires
                                        # __rexsl_ret_tmp_<n> generes par 'return' (str) -- une fonction
                                        # (ou le top-level) peut contenir plusieurs 'return' str atteints
                                        # par des chemins de controle differents (cdn/go, recursion) et
                                        # emis dans la MEME portee C : un nom fixe provoquait une
                                        # redefinition C des qu'un 2e 'return' str existait dans la meme
                                        # fonction/le meme main().
symbol_table["function_bodies"] = {}      # name -> lignes C du corps, en cours de compilation
symbol_table["func_ctx_stack"] = []       # sauvegarde (var, var_gen, heap_vars) de l'appelant a func_begin
symbol_table["func_order"] = []           # ordre de declaration, pour generer prototypes+corps
symbol_table["compiled_functions_c"] = [] # texte C final de chaque fonction (rempli a endfunc)
symbol_table["const_vars"] = set()   # noms bruts (sans prefixe SL_) marques constants
                                       # -> soit explicitement (const ...;), soit auto-detectes


def _heap_mark(name):
    """Marque <name> comme heap-alloue dans le scope courant."""
    symbol_table["heap_vars"][-1].add(name)


def _heap_is(name):
    """Vrai si <name> est heap-alloue dans un scope quelconque actuellement ouvert."""
    return any(name in scope for scope in symbol_table["heap_vars"])


def _heap_unmark(name):
    """Retire <name> du suivi heap (utilise apres un free explicite hors GC final)."""
    for scope in symbol_table["heap_vars"]:
        scope.discard(name)


def _can_hoist():
    """Vrai si le point de compilation courant assemble son bloc C englobant en
    UNE fois a la fin (func...endfunc, ou main() en tete de programme), ce qui
    permet de hisser les declarations heap a NULL en tete de ce bloc (voir
    _hoisted_decl_lines). Faux a l'interieur d'un scope 'pushall' manuel (legacy,
    voir doc 'Scopes manuels'), dont le code C est emis en flux continu au fil
    de la compilation : il n'y a alors pas de point unique ou revenir inserer
    une declaration hissee avant les lignes deja emises pour ce scope. Dans ce
    cas on retombe sur l'ancien comportement (declaration inline, non hissee)."""
    return symbol_table["current_func"] is not None or symbol_table["scope_depth"] == 0


def _hoisted_decl_lines(str_decl_names, collections):
    """Genere les lignes C 'TYPE nom = NULL;' a placer en tete d'un bloc (func
    ou main) pour chaque variable str/list/dict dont la PREMIERE declaration a
    ete hissee (voir symbol_table['heap_str_decls'] / 'collection_vars').
    Hisser la declaration a NULL, puis ne l'assigner que plus loin (au point
    d'origine, converti en simple affectation) rend le free() de fin de bloc
    sans danger meme si un 'cdn ... ; go ...;' saute par-dessus ce point
    d'origine : le pointeur vaut alors NULL au lieu d'une valeur indeterminee,
    voir _conditional_free_lines() -- c'est le correctif du bug documente en
    tete de fichier (double free / free() sur pointeur non initialise)."""
    lines = [f"char* {name} = NULL;" for name in sorted(str_decl_names)]
    c_type_by_kind = {"list": "RexList*", "dict": "RexDict*", "set": "RexList*", "tuple": "RexList*"}
    for coll_name, coll_kind in collections:
        lines.append(f"{c_type_by_kind[coll_kind]} {coll_name} = NULL;")
    return lines


def _conditional_free_lines(heap_names, collections):
    """Genere des lignes 'if (nom) { free(nom); nom = NULL; }' (ou
    rexsl_list_free/rexsl_dict_free pour les collections) au lieu d'un
    free(nom) inconditionnel. Complement de _hoisted_decl_lines() : protege
    contre le free() d'un pointeur non initialise si la declaration d'origine
    a ete sautee par un 'go' (le hoisting garantit NULL dans ce cas), et rend
    le free idempotent (remise a NULL) au cas ou plusieurs epilogues du meme
    scope seraient traverses. Ne resout PAS le cas plus etroit ou c'est la
    ligne de PROMOTION pile->tas d'une variable deja declaree (pas sa
    declaration initiale) qui est sautee -- residu documente, voir endfunc()."""
    lines = [f"if ({name}) {{ free({name}); {name} = NULL; }}" for name in heap_names]
    for coll_name, coll_kind in collections:
        if coll_kind in ("list", "set", "tuple"):
            free_fn = "rexsl_list_free"
        else:
            free_fn = "rexsl_dict_free"
        lines.append(f"if ({coll_name}) {{ {free_fn}({coll_name}); {coll_name} = NULL; }}")
    return lines


def _detect_recursive_call(call_graph):
    """Detecte tout cycle (recursion directe ou indirecte) dans le graphe
    d'appels exec entre func (symbol_table["call_graph"] : name -> {noms
    appeles}). REX-SL genere de vraies fonctions C sans aucune protection de
    pile (voir limitations connues), donc toute recursion doit etre refusee
    a la compilation plutot que de risquer un stack overflow a l'execution.
    Retourne le premier cycle trouve (liste de noms, ferme sur lui-meme) ou
    None si le graphe est acyclique."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {name: WHITE for name in call_graph}
    path = []

    def dfs(node):
        color[node] = GRAY
        path.append(node)
        for neighbor in call_graph.get(node, ()):
            neighbor_color = color.get(neighbor, WHITE)
            if neighbor_color == GRAY:
                cycle_start = path.index(neighbor)
                return path[cycle_start:] + [neighbor]
            if neighbor_color == WHITE:
                result = dfs(neighbor)
                if result:
                    return result
        path.pop()
        color[node] = BLACK
        return None

    for node in list(call_graph):
        if color[node] == WHITE:
            cycle = dfs(node)
            if cycle:
                return cycle
    return None


def _split_func_signature(remaining):
    """Decoupe les tokens situes apres 'func <nom>' en (param_specs, explicit_ret_token).
    param_specs   : liste de (type_tok, name_tok, default_tok_ou_None), un triplet par parametre.
    explicit_ret  : token de type ident (ou None) si la signature se termine par '-> <type>'.
    Syntaxe geree : func <nom> [<type> <arg> [= <defaut>]]... [-> <type_retour>];
    Partagee entre le pre-pass de compile() (prototypes en avant), le dispatch
    'func' de _compile_line, et _scan_assignment_counts, pour n'avoir qu'un seul
    endroit a maintenir. Leve REX_SL si la structure est invalide."""
    explicit_ret = None
    if len(remaining) >= 2 and remaining[-2] == ("op", "->"):
        ret_tok = remaining[-1]
        # Le type de retour peut etre un ident ("number", "str"...) OU le token none
        explicit_ret = ret_tok
        remaining = remaining[:-2]

    param_specs = []
    i = 0
    while i < len(remaining):
        if i + 1 >= len(remaining):
            raise REX_SL(f"func: parametres incomplets : {remaining}")
        type_tok, name_tok = remaining[i], remaining[i + 1]
        i += 2
        default_tok = None
        if i < len(remaining) and remaining[i] == ("op", "="):
            if i + 1 >= len(remaining):
                raise REX_SL(f"func: valeur par defaut manquante apres '=' : {remaining}")
            default_tok = remaining[i + 1]
            i += 2
        param_specs.append((type_tok, name_tok, default_tok))
    return param_specs, explicit_ret


# seuil (en nombre de caracteres) en dessous duquel une string litterale est
# stockee dans un buffer fixe sur la pile plutot que sur le tas. Au-dela, la
# variable est allouee dynamiquement via rexsl_str_alloc et enregistree dans
# symbol_table["heap_vars"] pour etre liberee (free) automatiquement en fin
# de programme -- c'est le "GC" (tres rudimentaire) de REX-SL.
STACK_STR_THRESHOLD = 64

# ------------------------------------------------------------
#  CONDITION SYSTEM (cdn / lbl / go)
# ------------------------------------------------------------
# cdn <op> <a> <b>; evalue une condition et la stocke dans REXSL_COND_VAR (une seule
# condition "courante" a la fois, ecrasee a chaque nouveau cdn -- pas de pile de conditions).
# cdn on;           force la condition courante a vraie (saut inconditionnel).
# lbl <nom>;        declare une etiquette C (LBL_<nom>) a laquelle sauter.
# go <nom>;         saute a l'etiquette <nom> SI la derniere condition evaluee est vraie.
#
# <op> peut etre un symbole (==, !=, >, <, >=, <=), deja tokenise tel quel par le lexer,
# ou un mot-cle (equal, not_equal, greater, less, greater_equal, less_equal, + alias courts).
REXSL_COND_VAR = "__rexsl_cond"

CDN_WORD_OPS = {
    "equal": "==", "eq": "==",
    "not_equal": "!=", "different": "!=", "neq": "!=", "ne": "!=",
    "greater": ">", "gt": ">",
    "less": "<", "lt": "<",
    "greater_equal": ">=", "ge": ">=",
    "less_equal": "<=", "le": "<=",
}
CDN_SYMBOL_OPS = {"==", "!=", ">", "<", ">=", "<="}


def _get_tag_color(tag):
    """Retourne le nom de couleur colorama associe a la famille du tag (partie avant le premier '.')."""
    family = tag.split(".")[0].upper()
    return TAG_FAMILY_COLORS.get(family, "WHITE")


def _colorize(text, color_name):
    """Applique une couleur colorama au texte si on est en mode 'stylish' et que colorama est dispo."""
    if MODE != "stylish" or not HAS_COLORAMA:
        return text
    color_code = getattr(Fore, color_name, "")  # type: ignore
    return f"{color_code}{text}{Style.RESET_ALL}"  # type: ignore


def log(tag, message, *args, verbose=False):
    """
    Log de debug generique.
    - verbose=False -> visible en mode 'debug' ET 'stylish' (les etapes importantes)
    - verbose=True  -> visible seulement en mode 'stylish' (trace tres detaillee)
    """
    if MODE == "off":
        return
    if verbose and MODE != "stylish":
        return

    formatted_message = message % args if args else message
    timestamp = time.strftime("%H:%M:%S")
    indent_prefix = "  " * INDENT_LEVEL
    tag_label = f"[TRACE][{tag}]" if verbose else f"[{tag}]"

    if MODE == "stylish":
        line = (
            _colorize(f"[{timestamp}]", "WHITE")
            + _colorize(tag_label, _get_tag_color(tag))
            + f"{indent_prefix} {formatted_message}"
        )
    else:
        line = f"[{timestamp}]{tag_label}{indent_prefix} {formatted_message}"

    print(line, file=sys.stderr)


def log_enter(tag, message, *args, verbose=False):
    """A appeler au debut d'une fonction : log + augmente l'indentation des logs suivants."""
    global INDENT_LEVEL
    log(tag, ">>> ENTER " + message, *args, verbose=verbose)
    INDENT_LEVEL += 1


def log_exit(tag, message, *args, verbose=False):
    """A appeler a la fin d'une fonction : diminue l'indentation puis log."""
    global INDENT_LEVEL
    INDENT_LEVEL = max(0, INDENT_LEVEL - 1)
    log(tag, "<<< EXIT " + message, *args, verbose=verbose)


def log_separator(tag, title=""):
    """Affiche une ligne de separation (et un titre optionnel) pour delimiter les grandes phases."""
    separator_line = "-" * 50
    log(tag, separator_line)
    if title:
        log(tag, "== %s ==", title)
        log(tag, separator_line)


def _escape_c_string(value):
    """
    Echappe une chaine Python pour qu'elle soit inseree sans risque a
    l'interieur d'un litteral C entre guillemets (ex: printf("...")).
    L'ordre compte : le backslash doit etre echappe EN PREMIER, sinon on
    echapperait aussi les backslashes qu'on vient d'ajouter pour les autres
    caracteres.
    """
    if not isinstance(value, str):
        return value
    return (
        value.replace("\\", "\\\\")   # backslash d'abord
             .replace('"', '\\"')      # guillemets
             .replace("\n", "\\n")
             .replace("\t", "\\t")
             .replace("\r", "\\r")
    )
    
def _scan_assignment_counts(tokenized_lines):
    """Pre-scan heuristique (globale, ne distingue pas les scopes func/pushall
    entre eux) : compte pour chaque nom brut de variable SL le nombre de fois
    ou elle est ECRITE (declaration incluse). Une variable dont le compteur
    vaut 1 n'est jamais modifiee apres sa creation -> elle devient candidate
    a la constantification automatique."""
    counts = {}

    def bump(tok):
        if tok and tok[0] == "ident" and not tok[1].startswith("RX_"):
            counts[tok[1]] = counts.get(tok[1], 0) + 1

    # instruction -> index du token destination
    DEST_INDEX = {
        "var": 2, "add": 1, "sub": 1, "mul": 1, "div": 1, "mod": 1, "pow": 1,
        "change": 1, "charat": 1, "slice": 1, "upper": 1, "lower": 1,
        "trim": 1, "replace": 1, "reverse": 1, "join": 1, "type": 1,
        "input": 1, "read": 2, "len": 1, "find": 1, "save": 1,
        "in": 1, "notin": 1, "list_count": 1, "slicestep": 1,
        "isnone": 1,  # isnone <dest_bool> <var>
    }

    for tokens in tokenized_lines:
        if not tokens or tokens[0][0] != "ident":
            continue
        name = tokens[0][1]

        if name in DEST_INDEX:
            idx = DEST_INDEX[name]
            if idx < len(tokens):
                bump(tokens[idx])
        elif name == "get" and len(tokens) == 4:
            bump(tokens[2])
        elif name == "get" and len(tokens) == 5:
            # forme etendue : get <coll> <type> <dest> <idx/cle> -- destination en position 3
            bump(tokens[3])
        elif name == "pop" and len(tokens) >= 3:
            bump(tokens[2])
        elif name == "func" and len(tokens) >= 2:
            try:
                param_specs, _explicit_ret = _split_func_signature(tokens[2:])
            except REX_SL:
                param_specs = []
            for _type_tok, name_tok, _default_tok in param_specs:
                bump(name_tok)
        elif name not in (
            "showln", "show", "shared_memory", "share", "del",
            "pushall", "popall", "forward", "return", "endfunc", "exec",
            "lbl", "go", "cdn", "run", "scrc", "append", "set", "write",
            "split", "readlines", "writelines", "const",
        ):
            if len(tokens) == 2:   # reaffectation classique : <nom> <valeur>;
                bump(tokens[0])

    return counts
    
class REX_SL(Exception):
    """Exception levee pour toute erreur propre au langage REX-SL (syntaxe, type, variable inconnue...)."""
    pass


class REX_SL_LEXER:
    """
    Transforme le code source REX-SL (texte brut) en une liste de lignes de tokens.
    Chaque ligne correspond a un opcode (separe par ';') et contient une liste de
    tuples (type_de_token, valeur), par exemple ("ident", "show") ou ("number", 42).
    """

    def __init__(self, source_code):
        log_enter("LEXER.__init__", "source_code=%r", source_code)
        self.source_code = source_code
        self.tokens = self.tokenize_all_lines()
        log("LEXER.__init__", "tokens finaux (lignes=%d) : %r", len(self.tokens), self.tokens)
        log_exit("LEXER.__init__", "source_code=%r", source_code)

    def _is_identifier_start(self, char):
        """Un identifiant peut commencer par une lettre ou un underscore."""
        result = char.isalpha() or char == "_"
        log("LEXER._is_identifier_start", "char=%r -> %r", char, result, verbose=True)
        return result

    def _is_identifier_part(self, char):
        """Apres le premier caractere, un identifiant accepte lettres, chiffres et underscore."""
        result = char.isalnum() or char == "_"
        log("LEXER._is_identifier_part", "char=%r -> %r", char, result, verbose=True)
        return result

    def _tokenize_opcode(self, opcode_text):
        """Decoupe le texte d'un seul opcode (une instruction) en une liste de tokens."""
        log_enter("LEXER._tokenize_opcode", "opcode_text=%r", opcode_text, verbose=True)
        tokens = []
        pos = 0
        length = len(opcode_text)

        while pos < length:
            char = opcode_text[pos]
            log("LEXER._tokenize_opcode", "position pos=%d, caractere courant=%r", pos, char, verbose=True)

            # espaces / tabulations / retours a la ligne -> on ignore
            if char in (" ", "\t", "\n"):
                log("LEXER._tokenize_opcode", "espace/tab/nl ignore a pos=%d", pos, verbose=True)
                pos += 1
                continue

            # commentaire : '#' -> on ignore tout jusqu'a la fin de la ligne
            if char == "#":
                cursor = pos
                while cursor < length and opcode_text[cursor] != "\n":
                    cursor += 1
                log("LEXER._tokenize_opcode", "commentaire ignore (pos=%d -> %d) : %r",
                    pos, cursor, opcode_text[pos:cursor], verbose=True)
                pos = cursor
                continue

            # string : "..." ou '...'
            if char in ('"', "'"):
                quote_char = char
                cursor = pos + 1
                buffer = ""
                log("LEXER._tokenize_opcode", "debut de string detecte, quote=%r a pos=%d",
                    quote_char, pos, verbose=True)
                while cursor < length and opcode_text[cursor] != quote_char:
                    current_char = opcode_text[cursor]

                    # backslash -> sequence d'echappement : on interprete le caractere suivant
                    if current_char == "\\" and cursor + 1 < length:
                        next_char = opcode_text[cursor + 1]
                        escape_map = {
                            "n": "\n",
                            "t": "\t",
                            "r": "\r",
                            "\\": "\\",
                            '"': '"',
                            "'": "'",
                            "0": "\0",
                        }
                        if next_char in escape_map:
                            buffer += escape_map[next_char]
                            log("LEXER._tokenize_opcode", "  echappement \\%s -> %r (cursor=%d)",
                                next_char, escape_map[next_char], cursor, verbose=True)
                            cursor += 2
                            continue
                        else:
                            # backslash suivi d'un caractere inconnu -> on le garde tel quel
                            log("LEXER._tokenize_opcode", "  echappement inconnu \\%s, backslash conserve (cursor=%d)",
                                next_char, cursor, verbose=True)
                            buffer += current_char
                            cursor += 1
                            continue

                    buffer += current_char
                    log("LEXER._tokenize_opcode", "  accumulation string buffer=%r (cursor=%d)",
                        buffer, cursor, verbose=True)
                    cursor += 1

                if cursor >= length:
                    log("LEXER._tokenize_opcode", "string non terminee (guillemet manquant) : %r", buffer)
                    log_exit("LEXER._tokenize_opcode", "ERREUR", verbose=True)
                    raise REX_SL(f"string non terminee : {buffer!r}")

                tokens.append(("str", buffer))
                log("LEXER._tokenize_opcode", "token STR cree -> %r", ("str", buffer), verbose=True)
                pos = cursor + 1  # on saute le guillemet fermant
                continue

            # operateurs de comparaison (pour "cdn") : ==, !=, >=, <=, >, <
            if char in ("=", "!", ">", "<"):
                has_next = pos + 1 < length
                next_char = opcode_text[pos + 1] if has_next else ""

                if char == "=" and next_char == "=":
                    tokens.append(("op", "=="))
                    log("LEXER._tokenize_opcode", "operateur == detecte a pos=%d", pos, verbose=True)
                    pos += 2
                    continue
                if char == "!" and next_char == "=":
                    tokens.append(("op", "!="))
                    log("LEXER._tokenize_opcode", "operateur != detecte a pos=%d", pos, verbose=True)
                    pos += 2
                    continue
                if char == ">":
                    op_value = ">=" if next_char == "=" else ">"
                    tokens.append(("op", op_value))
                    log("LEXER._tokenize_opcode", "operateur %s detecte a pos=%d", op_value, pos, verbose=True)
                    pos += 2 if next_char == "=" else 1
                    continue
                if char == "<":
                    op_value = "<=" if next_char == "=" else "<"
                    tokens.append(("op", op_value))
                    log("LEXER._tokenize_opcode", "operateur %s detecte a pos=%d", op_value, pos, verbose=True)
                    pos += 2 if next_char == "=" else 1
                    continue
                # '=' seul (ou '!' seul) n'a pas de sens dans REX-SL -> laisse tomber en "unknown"
                if char == "=":
                    tokens.append(("op", "="))
                    log("LEXER._tokenize_opcode", "operateur = (seul) detecte a pos=%d", pos, verbose=True)
                    pos += 1
                    continue

            # fleche '->' : uniquement utilisee pour annoter le type de retour explicite
            # d'une declaration 'func' (voir func_begin) : func <n> ... -> <type>;
            if char == "-" and pos + 1 < length and opcode_text[pos + 1] == ">":
                tokens.append(("op", "->"))
                log("LEXER._tokenize_opcode", "operateur -> detecte a pos=%d", pos, verbose=True)
                pos += 2
                continue

            # litteral negatif : '-' suivi immediatement d'un chiffre (pas d'espace)
            # -> on tokenise directement comme number/float negatif au lieu de forcer
            # REX.py a emuler le unaire moins via des contorsions d'expression.
            # Condition : le '-' est en debut de token-list (premier token) OU le
            # precedent token est un operateur/instruction (pas un ident/nombre) --
            # simple heuristique : si le dernier token est un ident ou number/float,
            # c'est probablement un operateur binaire, pas un signe => on laisse passer
            # comme "unknown '-'".  Dans tous les autres cas on le consomme comme signe.
            if char == "-" and pos + 1 < length and opcode_text[pos + 1].isdigit():
                # heuristique : precedent token ident/number/float => operateur binaire
                if tokens and tokens[-1][0] in ("ident", "number", "float", "bool"):
                    pass  # laisse tomber sur "unknown" ci-dessous
                else:
                    cursor = pos + 1  # saute le '-'
                    buffer = "-"
                    is_float = False
                    while cursor < length and (opcode_text[cursor].isdigit() or opcode_text[cursor] == "."):
                        if opcode_text[cursor] == ".":
                            if is_float:
                                break
                            is_float = True
                        buffer += opcode_text[cursor]
                        cursor += 1
                    if is_float:
                        tokens.append(("float", float(buffer)))
                        log("LEXER._tokenize_opcode", "token FLOAT NEGATIF cree -> %r", tokens[-1], verbose=True)
                    else:
                        tokens.append(("number", int(buffer)))
                        log("LEXER._tokenize_opcode", "token NUMBER NEGATIF cree -> %r", tokens[-1], verbose=True)
                    pos = cursor
                    continue

            # nombre / flottant : chiffres avec un point decimal optionnel
            if char.isdigit():
                cursor = pos
                buffer = ""
                is_float = False
                log("LEXER._tokenize_opcode", "debut de nombre detecte a pos=%d", pos, verbose=True)
                while cursor < length and (opcode_text[cursor].isdigit() or opcode_text[cursor] == "."):
                    if opcode_text[cursor] == ".":
                        if is_float:  # deuxieme point -> on arrete le nombre ici
                            log("LEXER._tokenize_opcode", "  deuxieme point rencontre, arret du nombre",
                                verbose=True)
                            break
                        is_float = True
                        log("LEXER._tokenize_opcode", "  point decimal detecte, is_float=True", verbose=True)
                    buffer += opcode_text[cursor]
                    log("LEXER._tokenize_opcode", "  accumulation nombre buffer=%r (cursor=%d)",
                        buffer, cursor, verbose=True)
                    cursor += 1

                if is_float:
                    tokens.append(("float", float(buffer)))
                    log("LEXER._tokenize_opcode", "token FLOAT cree -> %r", tokens[-1], verbose=True)
                else:
                    tokens.append(("number", int(buffer)))
                    log("LEXER._tokenize_opcode", "token NUMBER cree -> %r", tokens[-1], verbose=True)
                pos = cursor
                continue

            # identifiant / booleen : commence par une lettre ou un underscore
            if self._is_identifier_start(char):
                cursor = pos
                buffer = ""
                log("LEXER._tokenize_opcode", "debut d'identifiant detecte a pos=%d", pos, verbose=True)
                while cursor < length and self._is_identifier_part(opcode_text[cursor]):
                    buffer += opcode_text[cursor]
                    log("LEXER._tokenize_opcode", "  accumulation ident buffer=%r (cursor=%d)",
                        buffer, cursor, verbose=True)
                    cursor += 1

                if buffer in ("true", "false"):
                    tokens.append(("bool", buffer == "true"))
                    log("LEXER._tokenize_opcode", "token BOOL cree -> %r", tokens[-1], verbose=True)
                elif buffer == "none":
                    tokens.append(("none", None))
                    log("LEXER._tokenize_opcode", "token NONE cree -> %r", tokens[-1], verbose=True)
                else:
                    tokens.append(("ident", buffer))
                    log("LEXER._tokenize_opcode", "token IDENT cree -> %r", tokens[-1], verbose=True)
                pos = cursor
                continue

            # caractere non reconnu : on le garde tel quel, un par un
            tokens.append(("unknown", char))
            log("LEXER._tokenize_opcode", "token UNKNOWN cree -> %r", tokens[-1], verbose=True)
            pos += 1

        log("LEXER._tokenize_opcode", "resultat pour opcode_text=%r -> %r", opcode_text, tokens)
        log_exit("LEXER._tokenize_opcode", "opcode_text=%r", opcode_text, verbose=True)
        return tokens

    def tokenize_all_lines(self):
        log_enter("LEXER.tokenize_all_lines", "self.source_code=%r", self.source_code, verbose=True)

        raw_opcodes = []
        opcode_lines = []   # numero de ligne source (1-indexe) associe a chaque entree de raw_opcodes
        buffer = ""
        in_string = False
        quote_char = None
        pos = 0
        length = len(self.source_code)
        current_line = 1   # numero de la ligne du caractere en cours de traitement

        while pos < length:
            char = self.source_code[pos]

            # suivi du numero de ligne : incremente pour CHAQUE '\n' rencontre,
            # que ce soit dans une string, un commentaire ou du code -- utilise
            # ensuite pour situer les erreurs de compilation dans le fichier
            # source (cf. self.opcode_lines).
            if char == "\n":
                current_line += 1

            if in_string:
                buffer += char
                # backslash -> on avale aussi le caractere suivant sans l'analyser
                # (evite qu'un \" a l'interieur de la string ne soit pris pour
                # la fermeture, exactement le meme escaping que _tokenize_opcode)
                if char == "\\" and pos + 1 < length:
                    buffer += self.source_code[pos + 1]
                    pos += 2
                    continue
                if char == quote_char:
                    in_string = False
                pos += 1
                continue

            # commentaire '#' (hors string) : on recopie tel quel jusqu'a la fin
            # de la ligne SANS interpreter les guillemets/apostrophes qu'il
            # contient (ce ne sont pas des delimiteurs de string du code REX-SL)
            # ni un eventuel ';' (qui ne doit pas decouper une instruction s'il
            # n'est que du texte de commentaire). Le contenu reste dans buffer,
            # il sera de toute facon ignore plus tard par _tokenize_opcode.
            if char == "#":
                cursor = pos
                while cursor < length and self.source_code[cursor] != "\n":
                    buffer += self.source_code[cursor]
                    cursor += 1
                pos = cursor
                continue

            if char in ('"', "'"):
                in_string = True
                quote_char = char
                buffer += char
                pos += 1
                continue

            if char == ";":
                raw_opcodes.append(buffer)
                opcode_lines.append(current_line)
                buffer = ""
                pos += 1
                continue

            buffer += char
            pos += 1

        if buffer.strip():
            raw_opcodes.append(buffer)
            opcode_lines.append(current_line)

        log("LEXER.tokenize_all_lines", "split quote-aware -> %d parties : %r",
            len(raw_opcodes), raw_opcodes, verbose=True)

        # expose les numeros de ligne pour que le compilateur puisse les
        # rattacher aux erreurs REX_SL (voir REX_SL_COMPILER.compile()).
        self.opcode_lines = opcode_lines

        tokenized_lines = []
        for index, opcode_text in enumerate(raw_opcodes):
            log("LEXER.tokenize_all_lines", "traitement partie #%d (ligne %d) : %r",
                index, opcode_lines[index], opcode_text, verbose=True)
            try:
                tokenized_lines.append(self._tokenize_opcode(opcode_text))
            except REX_SL as e:
                # on enrichit l'erreur lexicale avec le numero de ligne source
                # avant de la laisser remonter, plutot que de forcer
                # l'utilisateur a chercher a l'aveugle dans son fichier.
                raise REX_SL(f"ligne {opcode_lines[index]} : {e}") from None

        log("LEXER.tokenize_all_lines", "lignes de tokens finales : %r", tokenized_lines, verbose=True)
        log_exit("LEXER.tokenize_all_lines", "self.source_code=%r", self.source_code, verbose=True)
        return tokenized_lines


class REX_SL_RXFN:
    @staticmethod
    def resolve():
        # macro presente inconditionnellement : garde-fou generique contre les
        # echecs d'allocation (malloc/realloc renvoyant NULL) -> message clair
        # + exit(1) au lieu d'un segfault silencieux au premier dereferencement.
        ret = """
#define REXSL_CHECK_ALLOC(ptr) do { \\
    if ((ptr) == NULL) { \\
        fprintf(stderr, "[REX-SL] erreur fatale : allocation memoire echouee\\n"); \\
        exit(1); \\
    } \\
} while (0)
"""
        if symbol_table["shm_enabled"]:
            ret += """
#define REXSL_SHM_KEY_MAX 4096
#define REXSL_SHM_VAL_MAX 65536

typedef struct {
    size_t total_size;   // taille totale actuelle du mapping, partagee entre process
    size_t used;         // octets utilises (a partir de la fin du header)
} RexShmHeader;

static RexShmHeader* __rexsl_shm_hdr = NULL;
static char* __rexsl_shm_data = NULL;
static size_t __rexsl_shm_local_size = 0;
static int __rexsl_shm_fd = -1;
static sem_t* __rexsl_shm_sem = NULL;

#define REXSL_SHM_INITIAL_SIZE 65536

void rexsl_shm_remap(size_t new_size) {
    if (__rexsl_shm_hdr != NULL) munmap(__rexsl_shm_hdr, __rexsl_shm_local_size);
    __rexsl_shm_hdr = mmap(NULL, new_size, PROT_READ | PROT_WRITE, MAP_SHARED, __rexsl_shm_fd, 0);
    if (__rexsl_shm_hdr == MAP_FAILED) { fprintf(stderr, "[REX-SL] erreur : mmap shm a echoue\\n"); exit(1); }
    __rexsl_shm_data = (char*)__rexsl_shm_hdr + sizeof(RexShmHeader);
    __rexsl_shm_local_size = new_size;
}

void rexsl_shm_sync(void) {
    if (__rexsl_shm_hdr->total_size != __rexsl_shm_local_size) {
        rexsl_shm_remap(__rexsl_shm_hdr->total_size);
    }
}

void rexsl_shm_init(const char* name) {
    char shm_path[128], sem_path[128];
    snprintf(shm_path, sizeof(shm_path), "/rexsl_%s", name);
    snprintf(sem_path, sizeof(sem_path), "/rexsl_sem_%s", name);

    int is_new = (shm_open(shm_path, O_RDWR, 0666) < 0);
    __rexsl_shm_fd = shm_open(shm_path, O_CREAT | O_RDWR, 0666);
    if (__rexsl_shm_fd < 0) { fprintf(stderr, "[REX-SL] erreur : shm_open a echoue\\n"); exit(1); }
    __rexsl_shm_sem = sem_open(sem_path, O_CREAT, 0666, 1);
    if (__rexsl_shm_sem == SEM_FAILED) { fprintf(stderr, "[REX-SL] erreur : sem_open shm a echoue\\n"); exit(1); }

    sem_wait(__rexsl_shm_sem);
    if (is_new) {
        if (ftruncate(__rexsl_shm_fd, REXSL_SHM_INITIAL_SIZE) != 0) { fprintf(stderr, "[REX-SL] erreur : ftruncate shm a echoue\\n"); exit(1); }
    }
    rexsl_shm_remap(REXSL_SHM_INITIAL_SIZE);
    if (is_new) {
        __rexsl_shm_hdr->total_size = REXSL_SHM_INITIAL_SIZE; __rexsl_shm_hdr->used = 0;
    } else {
        rexsl_shm_sync();
    }
    sem_post(__rexsl_shm_sem);
}

// format d'une entree dans __rexsl_shm_data (taille variable) :
// [uint32 key_len][key bytes][int32 type][uint32 val_len][val bytes]
// type: 0=number 1=float 2=bool 3=str ; val_len = sizeof(int)/sizeof(float)/sizeof(bool)/strlen+1

void rexsl_shm_grow(size_t needed) {
    size_t new_total = __rexsl_shm_hdr->total_size;
    while (new_total - sizeof(RexShmHeader) - __rexsl_shm_hdr->used < needed) new_total *= 2;
    if (ftruncate(__rexsl_shm_fd, (long)new_total) != 0) { fprintf(stderr, "[REX-SL] erreur : ftruncate (grow) shm a echoue\\n"); exit(1); }
    __rexsl_shm_hdr->total_size = new_total;
    rexsl_shm_remap(new_total);
}

char* rexsl_shm_find(const char* key) {
    rexsl_shm_sync();
    char* cursor = __rexsl_shm_data;
    char* end = __rexsl_shm_data + __rexsl_shm_hdr->used;
    uint32_t klen = (uint32_t)strlen(key);
    while (cursor < end) {
        uint32_t entry_klen; memcpy(&entry_klen, cursor, 4);
        char* entry_key = cursor + 4;
        int32_t type; memcpy(&type, entry_key + entry_klen, 4);
        uint32_t vlen; memcpy(&vlen, entry_key + entry_klen + 4, 4);
        char* val_ptr = entry_key + entry_klen + 8;
        if (entry_klen == klen && strncmp(entry_key, key, klen) == 0) return cursor;
        cursor = val_ptr + vlen;
    }
    return NULL;
}

void rexsl_shm_write_value(char* entry, int32_t type, uint32_t vlen, const void* val) {
    uint32_t klen; memcpy(&klen, entry, 4);
    memcpy(entry + 4 + klen, &type, 4);
    memcpy(entry + 4 + klen + 4, &vlen, 4);
    memcpy(entry + 4 + klen + 8, val, vlen);
}

char* rexsl_shm_find_or_create(const char* key, int32_t type, uint32_t vlen) {
    char* existing = rexsl_shm_find(key);
    if (existing) {
        uint32_t old_klen; memcpy(&old_klen, existing, 4);
        int32_t old_vlen_off = 4 + old_klen + 4;
        uint32_t old_vlen; memcpy(&old_vlen, existing + old_vlen_off - 4, 4);
        if (old_vlen == vlen) return existing;  // meme taille -> reutilise en place
        // taille differente (typiquement une str plus longue/plus courte) : on append
        // une nouvelle entree et on laisse l'ancienne "morte" (simplification 0.0.14 ;
        // recupere par le GC final comme le reste)
    }
    uint32_t klen = (uint32_t)strlen(key);
    size_t needed = 4 + klen + 4 + 4 + vlen;
    if (__rexsl_shm_hdr->total_size - sizeof(RexShmHeader) - __rexsl_shm_hdr->used < needed) {
        rexsl_shm_grow(needed);
    }
    char* entry = __rexsl_shm_data + __rexsl_shm_hdr->used;
    memcpy(entry, &klen, 4);
    memcpy(entry + 4, key, klen);
    __rexsl_shm_hdr->used += needed;
    return entry;
}

void rexsl_shm_del(const char* key) {
    sem_wait(__rexsl_shm_sem);
    char* entry = rexsl_shm_find(key);
    if (entry != NULL) {
        uint32_t klen; memcpy(&klen, entry, 4);
        memcpy(entry, &klen, 4);  // no-op garde ; l'entree "morte" reste dans le buffer
        // marquage simple : cle videe (klen=0 impossible normalement -> on ecrase la cle par des nuls)
        memset(entry + 4, 0, klen);
    }
    sem_post(__rexsl_shm_sem);
}

void* rexsl_shm_value_ptr(char* entry, uint32_t* out_vlen) {
    uint32_t klen; memcpy(&klen, entry, 4);
    int32_t type; memcpy(&type, entry + 4 + klen, 4);
    uint32_t vlen; memcpy(&vlen, entry + 4 + klen + 4, 4);
    if (out_vlen) *out_vlen = vlen;
    return entry + 4 + klen + 8;
}
"""
        if "rexsl_str_remove_all" in symbol_table["rexfn"]:
            ret += """
char* rexsl_str_remove_all(const char* src, const char* pattern) {
    size_t pattern_len = strlen(pattern);
    char* result = malloc(strlen(src) + 1);
    REXSL_CHECK_ALLOC(result);
    char* out = result;
    if (pattern_len == 0) {
        strcpy(result, src);
        return result;
    }
    while (*src) {
        if (strncmp(src, pattern, pattern_len) == 0) {
            src += pattern_len;
        } else {
            *out++ = *src++;
        }
    }
    *out = '\\0';
    return result;
}"""
        if "rexsl_str_repeat" in symbol_table["rexfn"]:
            ret += """
char* rexsl_str_repeat(const char* src, int count) {
    if (count < 0) count = 0;
    size_t len = strlen(src);
    char* result = malloc(len * (size_t)count + 1);
    REXSL_CHECK_ALLOC(result);
    result[0] = '\\0';
    for (int i = 0; i < count; i++) {
        strcat(result, src);
    }
    return result;
}"""
        if "rexsl_str_alloc" in symbol_table["rexfn"]:
            ret += """
char* rexsl_str_alloc(const char* value) {
    size_t len = strlen(value) + 1;
    char* result = malloc(len);
    REXSL_CHECK_ALLOC(result);
    memcpy(result, value, len);
    return result;
}"""
        if "rexsl_collections" in symbol_table["rexfn"]:
            ret += """
typedef enum { REXSL_T_NUMBER, REXSL_T_FLOAT, REXSL_T_BOOL, REXSL_T_STR } RexType;

typedef struct {
    RexType type;
    union {
        int as_number;
        float as_float;
        bool as_bool;
        char* as_str;
    } value;
} RexValue;

typedef struct {
    RexValue* items;
    int count;
    int capacity;
} RexList;

typedef struct {
    char* key;
    RexValue value;
} RexDictEntry;

typedef struct {
    RexDictEntry* entries;
    int count;
    int capacity;
} RexDict;

RexList* rexsl_list_new(void) {
    RexList* list = malloc(sizeof(RexList));
    REXSL_CHECK_ALLOC(list);
    list->items = NULL;
    list->count = 0;
    list->capacity = 0;
    return list;
}

void rexsl_list_append(RexList* list, RexValue value) {
    if (list->count >= list->capacity) {
        list->capacity = list->capacity == 0 ? 8 : list->capacity * 2;
        list->items = realloc(list->items, sizeof(RexValue) * (size_t)list->capacity);
        REXSL_CHECK_ALLOC(list->items);
    }
    list->items[list->count++] = value;
}

RexValue rexsl_list_get(RexList* list, int idx) {
    if (idx < 0 || idx >= list->count) {
        fprintf(stderr, "[REX-SL] erreur : index de liste hors limites : %d\\n", idx);
        exit(1);
    }
    return list->items[idx];
}

RexValue rexsl_list_pop(RexList* list, int idx) {
    if (list->count == 0) {
        fprintf(stderr, "[REX-SL] erreur : pop sur une liste vide\\n");
        exit(1);
    }
    if (idx < 0) idx = list->count - 1;
    if (idx >= list->count) {
        fprintf(stderr, "[REX-SL] erreur : index de liste hors limites : %d\\n", idx);
        exit(1);
    }
    RexValue result = list->items[idx];
    for (int i = idx; i < list->count - 1; i++) {
        list->items[i] = list->items[i + 1];
    }
    list->count--;
    return result;
}

void rexsl_list_free(RexList* list) {
    free(list->items);
    free(list);
}

RexDict* rexsl_dict_new(void) {
    RexDict* dict = malloc(sizeof(RexDict));
    REXSL_CHECK_ALLOC(dict);
    dict->entries = NULL;
    dict->count = 0;
    dict->capacity = 0;
    return dict;
}

void rexsl_dict_set(RexDict* dict, const char* key, RexValue value) {
    for (int i = 0; i < dict->count; i++) {
        if (strcmp(dict->entries[i].key, key) == 0) {
            dict->entries[i].value = value;
            return;
        }
    }
    if (dict->count >= dict->capacity) {
        dict->capacity = dict->capacity == 0 ? 8 : dict->capacity * 2;
        dict->entries = realloc(dict->entries, sizeof(RexDictEntry) * (size_t)dict->capacity);
        REXSL_CHECK_ALLOC(dict->entries);
    }
    size_t __rexsl_klen = strlen(key) + 1;
    dict->entries[dict->count].key = malloc(__rexsl_klen);
    REXSL_CHECK_ALLOC(dict->entries[dict->count].key);
    memcpy(dict->entries[dict->count].key, key, __rexsl_klen);
    dict->entries[dict->count].value = value;
    dict->count++;
}

RexValue rexsl_dict_get(RexDict* dict, const char* key) {
    for (int i = 0; i < dict->count; i++) {
        if (strcmp(dict->entries[i].key, key) == 0) {
            return dict->entries[i].value;
        }
    }
    fprintf(stderr, "[REX-SL] erreur : cle inconnue dans le dictionnaire : %s\\n", key);
    exit(1);
}

void rexsl_dict_free(RexDict* dict) {
    for (int i = 0; i < dict->count; i++) {
        free(dict->entries[i].key);
    }
    free(dict->entries);
    free(dict);
}
"""
        if "rexsl_collections_str" in symbol_table["rexfn"]:
            ret += """
char* rexsl_value_repr(RexValue v) {
    char buf[64];
    switch (v.type) {
        case REXSL_T_NUMBER:
            snprintf(buf, sizeof(buf), "%d", v.value.as_number);
            return rexsl_str_alloc(buf);
        case REXSL_T_FLOAT:
            snprintf(buf, sizeof(buf), "%g", v.value.as_float);
            return rexsl_str_alloc(buf);
        case REXSL_T_BOOL:
            return rexsl_str_alloc(v.value.as_bool ? "True" : "False");
        case REXSL_T_STR: {
            size_t len = strlen(v.value.as_str);
            char* out = malloc(len + 3);
            REXSL_CHECK_ALLOC(out);
            out[0] = '\\'';
            memcpy(out + 1, v.value.as_str, len);
            out[len + 1] = '\\'';
            out[len + 2] = '\\0';
            return out;
        }
    }
    return rexsl_str_alloc("");
}

char* rexsl_list_to_str(RexList* list) {
    char* result = malloc(3);
    REXSL_CHECK_ALLOC(result);
    strcpy(result, "[");
    for (int i = 0; i < list->count; i++) {
        char* piece = rexsl_value_repr(list->items[i]);
        size_t need = strlen(result) + strlen(piece) + 4;
        result = realloc(result, need);
        REXSL_CHECK_ALLOC(result);
        if (i > 0) strcat(result, ", ");
        strcat(result, piece);
        free(piece);
    }
    strcat(result, "]");
    return result;
}

char* rexsl_dict_to_str(RexDict* dict) {
    char* result = malloc(3);
    REXSL_CHECK_ALLOC(result);
    strcpy(result, "{");
    for (int i = 0; i < dict->count; i++) {
        char* vpiece = rexsl_value_repr(dict->entries[i].value);
        size_t need = strlen(result) + strlen(dict->entries[i].key) + strlen(vpiece) + 8;
        result = realloc(result, need);
        REXSL_CHECK_ALLOC(result);
        if (i > 0) strcat(result, ", ");
        strcat(result, "'");
        strcat(result, dict->entries[i].key);
        strcat(result, "': ");
        strcat(result, vpiece);
        free(vpiece);
    }
    strcat(result, "}");
    return result;
}"""
        if "rexsl_list_contains" in symbol_table["rexfn"]:
            ret += """
bool rexsl_list_contains(RexList* list, RexValue needle) {
    for (int i = 0; i < list->count; i++) {
        RexValue v = list->items[i];
        if (v.type != needle.type) continue;
        switch (v.type) {
            case REXSL_T_NUMBER: if (v.value.as_number == needle.value.as_number) return true; break;
            case REXSL_T_FLOAT:  if (v.value.as_float  == needle.value.as_float)  return true; break;
            case REXSL_T_BOOL:   if (v.value.as_bool   == needle.value.as_bool)   return true; break;
            case REXSL_T_STR:    if (strcmp(v.value.as_str, needle.value.as_str) == 0) return true; break;
        }
    }
    return false;
}"""
        if "rexsl_show_list" in symbol_table["rexfn"]:
            ret += """
void rexsl_show_list(RexList* list, int newline) {
    printf("[");
    for (int i = 0; i < list->count; i++) {
        RexValue v = list->items[i];
        if (i > 0) printf(", ");
        switch (v.type) {
            case REXSL_T_NUMBER: printf("%d", v.value.as_number); break;
            case REXSL_T_FLOAT:  printf("%g", v.value.as_float); break;
            case REXSL_T_BOOL:   printf("%s", v.value.as_bool ? "true" : "false"); break;
            case REXSL_T_STR:    printf("'%s'", v.value.as_str); break;
        }
    }
    printf("]");
    if (newline) printf("\\n");
}"""
        if "rexsl_show_dict" in symbol_table["rexfn"]:
            ret += """
void rexsl_show_dict(RexDict* dict, int newline) {
    printf("{");
    for (int i = 0; i < dict->count; i++) {
        if (i > 0) printf(", ");
        printf("'%s': ", dict->entries[i].key);
        RexValue v = dict->entries[i].value;
        switch (v.type) {
            case REXSL_T_NUMBER: printf("%d", v.value.as_number); break;
            case REXSL_T_FLOAT:  printf("%g", v.value.as_float); break;
            case REXSL_T_BOOL:   printf("%s", v.value.as_bool ? "true" : "false"); break;
            case REXSL_T_STR:    printf("'%s'", v.value.as_str); break;
        }
    }
    printf("}");
    if (newline) printf("\\n");
}"""
        if "rexsl_show_set" in symbol_table["rexfn"]:
            ret += """
void rexsl_show_set(RexList* s, int newline) {
    printf("{");
    for (int i = 0; i < s->count; i++) {
        RexValue v = s->items[i];
        if (i > 0) printf(", ");
        switch (v.type) {
            case REXSL_T_NUMBER: printf("%d", v.value.as_number); break;
            case REXSL_T_FLOAT:  printf("%g", v.value.as_float); break;
            case REXSL_T_BOOL:   printf("%s", v.value.as_bool ? "true" : "false"); break;
            case REXSL_T_STR:    printf("'%s'", v.value.as_str); break;
        }
    }
    printf("}");
    if (newline) printf("\\n");
}"""
        if "rexsl_show_tuple" in symbol_table["rexfn"]:
            ret += """
void rexsl_show_tuple(RexList* t, int newline) {
    printf("(");
    for (int i = 0; i < t->count; i++) {
        RexValue v = t->items[i];
        if (i > 0) printf(", ");
        switch (v.type) {
            case REXSL_T_NUMBER: printf("%d", v.value.as_number); break;
            case REXSL_T_FLOAT:  printf("%g", v.value.as_float); break;
            case REXSL_T_BOOL:   printf("%s", v.value.as_bool ? "true" : "false"); break;
            case REXSL_T_STR:    printf("'%s'", v.value.as_str); break;
        }
    }
    if (t->count == 1) printf(",");
    printf(")");
    if (newline) printf("\\n");
}"""
        if "rexsl_set_add" in symbol_table["rexfn"]:
            ret += """
void rexsl_set_add(RexList* s, RexValue v) {
    /* n'insere que si l'element n'est pas deja present (semantique set) */
    for (int i = 0; i < s->count; i++) {
        RexValue e = s->items[i];
        if (e.type != v.type) continue;
        switch (e.type) {
            case REXSL_T_NUMBER: if (e.value.as_number == v.value.as_number) return; break;
            case REXSL_T_FLOAT:  if (e.value.as_float  == v.value.as_float)  return; break;
            case REXSL_T_BOOL:   if (e.value.as_bool   == v.value.as_bool)   return; break;
            case REXSL_T_STR:    if (strcmp(e.value.as_str, v.value.as_str) == 0) return; break;
        }
    }
    rexsl_list_append(s, v);
}"""
        if "rexsl_str_charat" in symbol_table["rexfn"]:
            ret += """
char* rexsl_str_charat(const char* src, int idx) {
    int len = (int)strlen(src);
    if (idx < 0 || idx >= len) {
        fprintf(stderr, "[REX-SL] erreur : index hors limites (charat) : %d\\n", idx);
        exit(1);
    }
    char* result = malloc(2);
    REXSL_CHECK_ALLOC(result);
    result[0] = src[idx];
    result[1] = '\\0';
    return result;
}"""
        if "rexsl_str_slice" in symbol_table["rexfn"]:
            ret += """
char* rexsl_str_slice(const char* src, int start, int end) {
    int len = (int)strlen(src);
    if (start < 0) start = 0;
    if (end > len) end = len;
    if (start > end) start = end;
    int slice_len = end - start;
    char* result = malloc((size_t)slice_len + 1);
    REXSL_CHECK_ALLOC(result);
    memcpy(result, src + start, (size_t)slice_len);
    result[slice_len] = '\\0';
    return result;
}"""
        if "rexsl_str_slice_step" in symbol_table["rexfn"]:
            # 0.0.14 : slice avec pas (x[a:b:c]). `end` == -1 est une
            # sentinelle signifiant "jusqu'au debut de la chaine inclus"
            # (utilisee quand le pas est negatif et la fin omise, cf.
            # ExprCodegen._slice_step) - la valeur -1 elle-meme n'est donc
            # jamais un indice de fin "normal" ici (bornes toujours clampees
            # comme pour rexsl_str_slice, pas d'erreur fatale).
            ret += """
char* rexsl_str_slice_step(const char* src, int start, int end, int step) {
    int len = (int)strlen(src);
    int count = 0, i;
    if (step > 0) {
        if (start < 0) start = 0;
        if (start > len) start = len;
        if (end > len) end = len;
        if (end < start) end = start;
        for (i = start; i < end; i += step) count++;
    } else {
        if (start >= len) start = len - 1;
        if (start < -1) start = -1;
        if (end < -1) end = -1;
        if (end > start) end = start;
        for (i = start; i > end; i += step) count++;
    }
    char* result = malloc((size_t)count + 1);
    REXSL_CHECK_ALLOC(result);
    int j = 0;
    if (step > 0) {
        for (i = start; i < end; i += step) result[j++] = src[i];
    } else {
        for (i = start; i > end; i += step) result[j++] = src[i];
    }
    result[j] = '\\0';
    return result;
}"""
        if "rexsl_str_find" in symbol_table["rexfn"]:
            ret += """
int rexsl_str_find(const char* src, const char* substr) {
    const char* found = strstr(src, substr);
    if (found == NULL) return -1;
    return (int)(found - src);
}"""
        if "rexsl_str_upper" in symbol_table["rexfn"]:
            ret += """
char* rexsl_str_upper(const char* src) {
    size_t len = strlen(src);
    char* result = malloc(len + 1);
    REXSL_CHECK_ALLOC(result);
    for (size_t i = 0; i < len; i++) result[i] = (char)toupper((unsigned char)src[i]);
    result[len] = '\\0';
    return result;
}"""
        if "rexsl_str_lower" in symbol_table["rexfn"]:
            ret += """
char* rexsl_str_lower(const char* src) {
    size_t len = strlen(src);
    char* result = malloc(len + 1);
    REXSL_CHECK_ALLOC(result);
    for (size_t i = 0; i < len; i++) result[i] = (char)tolower((unsigned char)src[i]);
    result[len] = '\\0';
    return result;
}"""
        if "rexsl_str_trim" in symbol_table["rexfn"]:
            ret += """
char* rexsl_str_trim(const char* src) {
    size_t len = strlen(src);
    size_t start = 0;
    while (start < len && isspace((unsigned char)src[start])) start++;
    size_t end = len;
    while (end > start && isspace((unsigned char)src[end - 1])) end--;
    size_t out_len = end - start;
    char* result = malloc(out_len + 1);
    REXSL_CHECK_ALLOC(result);
    memcpy(result, src + start, out_len);
    result[out_len] = '\\0';
    return result;
}"""
        if "rexsl_str_replace_all" in symbol_table["rexfn"]:
            ret += """
char* rexsl_str_replace_all(const char* src, const char* old_s, const char* new_s) {
    size_t old_len = strlen(old_s);
    size_t new_len = strlen(new_s);
    size_t src_len = strlen(src);
    size_t cap = src_len + 1;
    char* result = malloc(cap);
    REXSL_CHECK_ALLOC(result);
    size_t out_len = 0;
    if (old_len == 0) { strcpy(result, src); return result; }
    while (*src) {
        if (strncmp(src, old_s, old_len) == 0) {
            while (out_len + new_len + 1 > cap) { cap *= 2; result = realloc(result, cap); REXSL_CHECK_ALLOC(result); }
            memcpy(result + out_len, new_s, new_len);
            out_len += new_len;
            src += old_len;
        } else {
            while (out_len + 1 + 1 > cap) { cap *= 2; result = realloc(result, cap); REXSL_CHECK_ALLOC(result); }
            result[out_len++] = *src++;
        }
    }
    result[out_len] = '\\0';
    return result;
}"""
        if "rexsl_str_reverse" in symbol_table["rexfn"]:
            ret += """
char* rexsl_str_reverse(const char* src) {
    size_t len = strlen(src);
    char* result = malloc(len + 1);
    REXSL_CHECK_ALLOC(result);
    for (size_t i = 0; i < len; i++) result[i] = src[len - 1 - i];
    result[len] = '\\0';
    return result;
}"""
        if "rexsl_str_split" in symbol_table["rexfn"]:
            ret += """
void rexsl_str_split(RexList* dest, const char* src, const char* delim) {
    size_t delim_len = strlen(delim);
    if (delim_len == 0) {
        char* copy = malloc(strlen(src) + 1);
        REXSL_CHECK_ALLOC(copy);
        strcpy(copy, src);
        rexsl_list_append(dest, (RexValue){ .type = REXSL_T_STR, .value.as_str = copy });
        return;
    }
    const char* start = src;
    const char* found;
    while ((found = strstr(start, delim)) != NULL) {
        size_t piece_len = (size_t)(found - start);
        char* piece = malloc(piece_len + 1);
        REXSL_CHECK_ALLOC(piece);
        memcpy(piece, start, piece_len);
        piece[piece_len] = '\\0';
        rexsl_list_append(dest, (RexValue){ .type = REXSL_T_STR, .value.as_str = piece });
        start = found + delim_len;
    }
    char* last = malloc(strlen(start) + 1);
    REXSL_CHECK_ALLOC(last);
    strcpy(last, start);
    rexsl_list_append(dest, (RexValue){ .type = REXSL_T_STR, .value.as_str = last });
}"""
        if "rexsl_list_join" in symbol_table["rexfn"]:
            ret += """
char* rexsl_list_join(RexList* list, const char* delim) {
    size_t delim_len = strlen(delim);
    size_t cap = 64, out_len = 0;
    char* result = malloc(cap);
    REXSL_CHECK_ALLOC(result);
    result[0] = '\\0';
    char piece[256];
    for (int i = 0; i < list->count; i++) {
        RexValue v = list->items[i];
        switch (v.type) {
            case REXSL_T_NUMBER: snprintf(piece, sizeof(piece), "%d", v.value.as_number); break;
            case REXSL_T_FLOAT:  snprintf(piece, sizeof(piece), "%g", v.value.as_float); break;
            case REXSL_T_BOOL:   snprintf(piece, sizeof(piece), "%s", v.value.as_bool ? "true" : "false"); break;
            case REXSL_T_STR:    snprintf(piece, sizeof(piece), "%s", v.value.as_str); break;
        }
        size_t piece_len = strlen(piece);
        size_t sep_len = (i < list->count - 1) ? delim_len : 0;
        while (out_len + piece_len + sep_len + 1 > cap) { cap *= 2; result = realloc(result, cap); REXSL_CHECK_ALLOC(result); }
        memcpy(result + out_len, piece, piece_len); out_len += piece_len;
        if (sep_len) { memcpy(result + out_len, delim, sep_len); out_len += sep_len; }
    }
    result[out_len] = '\\0';
    return result;
}"""
        
        return ret


class REX_SL_CODE:
    """Regroupe les generateurs de code C pour chaque instruction (show, var, ...)."""

    @staticmethod
    def _is_rx(name):
        """Un nom qui commence par RX_ reference le registre externe RX (importe), pas le registre SL local."""
        return name.startswith("RX_")

    @staticmethod
    def _registry_for(name):
        """Retourne le registre symbol_table correspondant au nom : rx_var pour RX_, var (SL) sinon."""
        return symbol_table["rx_var"] if REX_SL_CODE._is_rx(name) else symbol_table["var"]

    @staticmethod
    def _registry_label(name):
        return "RX" if REX_SL_CODE._is_rx(name) else "SL"

    @staticmethod
    def _collection_kind(name):
        """Retourne 'list'/'dict'/None pour <name>, en resolvant via le bon registre
        (rx_var pour RX_, var/SL sinon) -- necessaire pour que list/dict retournes par
        une fonction (RX_ret) soient utilisables directement comme collection source
        par append/get/pop/set/len/in/notin, pas seulement les variables SL locales."""
        registry = REX_SL_CODE._registry_for(name)
        kind = registry.get(name)
        return kind if kind in ("list", "dict", "set", "tuple") else None

    @staticmethod
    def _c_name(name):
        if REX_SL_CODE._is_rx(name):
            return name
        gen = symbol_table["var_gen"].get(name, 0)
        return f"SL_{name}" if gen == 0 else f"SL_{name}_g{gen}"

    @staticmethod
    def _operand_type(token):
        """Retourne le type REX-SL reel d'un operande, en resolvant les idents via le bon registre (SL ou RX).
        Le token ("none", None) retourne directement "none"."""
        token_type, token_value = token
        if token_type == "none":
            return "none"
        if token_type == "ident":
            registry = REX_SL_CODE._registry_for(token_value)
            if token_value not in registry:
                raise REX_SL(f"variable {REX_SL_CODE._registry_label(token_value)} inconnue : {token_value}")
            return registry[token_value]
        return token_type

    @staticmethod
    def _operand_expr(token):
        """Retourne l'expression C d'un operande (litteral echappe/formate, ou nom de variable SL_/RX_).
        Le token ("none", None) retourne "NULL" (pointeur nul C)."""
        token_type, token_value = token
        if token_type == "none":
            return "NULL"
        if token_type == "ident":
            return REX_SL_CODE._c_name(token_value)
        if token_type == "str":
            return f'"{_escape_c_string(token_value)}"'
        if token_type == "bool":
            return "true" if token_value else "false"
        return str(token_value)
    
    @staticmethod
    def func_begin(name_token, param_specs, explicit_ret_token=None):
        """func <name> [<type> <arg> [= <defaut>]]... [-> <type_retour>]; ouvre une
        VRAIE fonction C compilee a part et inseree avant main(). Chaque parametre
        devient une variable locale C typee de la fonction generee, isolee de
        l'appelant (aucune collision de nom possible, contrairement a l'ancien
        pushall/RXS_).

        param_specs : liste de (type_tok, name_tok, default_tok_ou_None) -- voir
        _split_func_signature(). Un parametre avec valeur par defaut peut etre
        omis a l'appel (exec), voir exec_call().

        explicit_ret_token : token de type ident portant le type de retour, si la
        signature se termine par '-> <type>'. Permet de connaitre le type de
        retour de la fonction DES sa declaration plutot qu'a la premiere
        instruction 'return' rencontree dans son corps -- necessaire pour que
        les appels 'exec' recursifs (directs OU indirects/mutuels) generent le
        bon code des le premier appel, meme si celui-ci precede textuellement le
        'return' de base dans le corps de la fonction. Sans annotation explicite,
        un appel recursif/en-avant vers une fonction dont le type de retour n'est
        pas encore connu au moment de l'appel est traite comme un appel void
        (valeur de retour ignoree) -- limitation documentee, contournable en
        annotant la fonction."""
        log_enter("CODE.func_begin", "name_token=%r param_specs=%r explicit_ret_token=%r",
                  name_token, param_specs, explicit_ret_token)
        if name_token[0] != "ident":
            raise REX_SL(f"func: nom de fonction non gere : {name_token}")
        name = name_token[1]
        if symbol_table["current_func"] is not None:
            raise REX_SL(f"func: declaration imbriquee non geree (deja dans {symbol_table['current_func']})")

        existing = symbol_table["functions"].get(name)
        if existing is not None and not existing.get("_forward_only", False):
            raise REX_SL(f"func: fonction deja declaree : {name}")

        params = []
        defaults = {}
        seen = set()
        for type_tok, name_tok, default_tok in param_specs:
            if type_tok[0] != "ident" or type_tok[1] not in ("number", "float", "bool", "str", "list", "dict", "set", "tuple"):
                raise REX_SL(f"func: type de parametre non gere : {type_tok}")
            if name_tok[0] != "ident":
                raise REX_SL(f"func: nom de parametre non gere : {name_tok}")
            argname = name_tok[1]
            if argname in seen:
                raise REX_SL(f"func: parametre duplique : {argname}")
            seen.add(argname)
            ptype = type_tok[1]
            params.append((ptype, argname))
            if default_tok is not None:
                if ptype in ("list", "dict", "set", "tuple"):
                    raise REX_SL(
                        f"func: valeur par defaut non supportee pour un parametre {ptype} : {argname}"
                    )
                if default_tok[0] != ptype:
                    raise REX_SL(
                        f"func: valeur par defaut de type incompatible pour {argname} : "
                        f"attendu {ptype}, recu {default_tok[0]}"
                    )
                defaults[argname] = default_tok

        if explicit_ret_token is not None:
            if explicit_ret_token[0] not in ("ident", "none"):
                raise REX_SL(f"func: type de retour explicite invalide : {explicit_ret_token}")
            if explicit_ret_token[0] == "none":
                ret_type = "none"   # void
            elif explicit_ret_token[1] not in (
                "number", "float", "bool", "str", "list", "dict", "set", "tuple", "none"
            ):
                raise REX_SL(f"func: type de retour explicite invalide : {explicit_ret_token}")
            else:
                ret_type = explicit_ret_token[1]
        else:
            ret_type = None

        if existing is not None:
            # signature deja enregistree par le pre-pass (prototype en avant, voir
            # compile()) -- on verifie la coherence puis on finalise l'entree.
            if existing["params"] != params:
                raise REX_SL(
                    f"func {name}: signature incoherente avec sa pre-declaration "
                    f"(utilisee par un appel 'exec' avant sa definition)"
                )
            if existing.get("ret_type") is not None and ret_type is not None and existing["ret_type"] != ret_type:
                raise REX_SL(
                    f"func {name}: type de retour incoherent avec sa pre-declaration : "
                    f"{existing['ret_type']} vs {ret_type}"
                )
            if ret_type is None:
                ret_type = existing.get("ret_type")
            existing.update({"params": params, "defaults": defaults, "ret_type": ret_type, "_forward_only": False})
        else:
            symbol_table["functions"][name] = {
                "params": params, "defaults": defaults, "ret_type": ret_type, "_forward_only": False,
            }
            symbol_table["func_order"].append(name)

        symbol_table["function_bodies"][name] = []
        symbol_table["current_func"] = name

        # sauvegarde le contexte SL de l'appelant, puis espace de noms neuf
        symbol_table["func_ctx_stack"].append((
            symbol_table["var"], symbol_table["var_gen"], symbol_table["heap_vars"],
            symbol_table["collection_vars"], symbol_table["heap_str_decls"],
            symbol_table["collection_hoist"],
        ))
        symbol_table["var"] = {}
        symbol_table["var_gen"] = {}
        symbol_table["heap_vars"] = [set()]
        symbol_table["collection_vars"] = [[]]
        symbol_table["heap_str_decls"] = [set()]
        symbol_table["collection_hoist"] = [set()]

        for ptype, pname in params:
            symbol_table["var"][pname] = ptype

        log_exit("CODE.func_begin", "-> None (rien emis dans main)")
        return None

    @staticmethod
    def endfunc(name_token):
        """endfunc <name>; ferme la fonction, genere son texte C complet
        (signature + corps + free des heap_vars residuels) et restaure le
        contexte de l'appelant."""
        log_enter("CODE.endfunc", "name_token=%r", name_token)
        if name_token[0] != "ident":
            raise REX_SL(f"endfunc: nom non gere : {name_token}")
        name = name_token[1]
        if symbol_table["current_func"] != name:
            raise REX_SL(
                f"endfunc {name}: ne correspond pas au func actuellement ouvert "
                f"({symbol_table['current_func']!r})"
            )

        # collections (list/dict) declarees localement (var list/dict ...;) dans cette
        # fonction : liberees ici aussi (pile dediee, distincte de heap_vars car elles
        # utilisent rexsl_list_free/rexsl_dict_free et non free() -- voir §5). Comme pour
        # heap_vars, ce code n'est atteint que sur le chemin qui tombe en fin de fonction
        # sans avoir deja 'return'e (chaque 'return' libere lui-meme les collections
        # locales autres que celle qu'il renvoie, voir return_stmt) : pas de double free
        # a l'execution, meme si la collection renvoyee reste listee ici (code mort apres
        # le 'return' correspondant).
        #
        # BUG CONNU CORRIGE ICI (voir tete de fichier, changelog) : trailing_free_lines
        # etait auparavant une liste de free(v) inconditionnels sur symbol_table
        # ["heap_vars"][-1], qui contient un nom C des l'instant ou sa declaration a ete
        # COMPILEE -- meme si un 'cdn ...; go ...;' saute cette declaration a l'EXECUTION
        # (ex: 'cdn on; go base; var str r; ...; lbl base; return "";'). Le pointeur
        # restait alors non initialise et free() dessus est un double-free/UB (confirme
        # par AddressSanitizer). Correctif : chaque variable dont la PREMIERE declaration
        # est heap-tracked (symbol_table["heap_str_decls"][-1] pour les str, 
        # symbol_table["collection_vars"][-1] pour les list/dict) est desormais hissee a
        # NULL en tete de la fonction generee (_hoisted_decl_lines), et son point de
        # declaration d'origine (var()/_assign_heap_str()/add()/sub()/mul()/get) n'emet
        # plus qu'une simple affectation. Le free() de fin de fonction devient conditionnel
        # (_conditional_free_lines) : si le 'go' a saute la declaration, le pointeur est
        # toujours NULL a ce point et rien n'est libere.
        # LIMITE residuelle (non couverte par ce correctif) : si c'est la ligne de
        # PROMOTION pile->tas d'une variable DEJA declaree en 'str' courte (buffer sur la
        # pile, voir var()) qui est sautee par un 'go' -- alors que sa declaration
        # d'origine, elle, a bien ete executee -- symbol_table["heap_vars"] la considere
        # heap des la compilation (marquage inconditionnel, non sensible au chemin
        # reellement emprunte non plus) alors qu'a l'execution son pointeur pointe encore
        # vers le buffer pile (non-NULL) : le free() conditionnel ci-dessous la libererait
        # quand meme a tort. Une correction complete de ce cas necessiterait un flag
        # booleen runtime distinct par variable (pas seulement un test de nullite du
        # pointeur), hors perimetre de ce patch.
        trailing_free_lines = _conditional_free_lines(
            symbol_table["heap_vars"][-1], symbol_table["collection_vars"][-1]
        )
        trailing_frees = "\n    ".join(trailing_free_lines)

        hoisted_colls = [
            (n, k) for n, k in symbol_table["collection_vars"][-1]
            if n in symbol_table["collection_hoist"][-1]
        ]
        hoist_lines = _hoisted_decl_lines(symbol_table["heap_str_decls"][-1], hoisted_colls)
        hoisted_decls = ("    " + "\n    ".join(hoist_lines) + "\n") if hoist_lines else ""

        finfo = symbol_table["functions"][name]
        body_lines = symbol_table["function_bodies"].pop(name)
        ret_type = finfo["ret_type"]
        c_type_by_kind = {"number": "int", "float": "float", "bool": "bool", "str": "char*",
                          "list": "RexList*", "dict": "RexDict*",
                          "set": "RexList*", "tuple": "RexList*",
                          "none": "void",   # func -> none;  = fonction void
                          None: "void"}
        c_ret_type = c_type_by_kind[ret_type]
        param_decl = ", ".join(
            f"{c_type_by_kind[t]} SL_{n}" for t, n in finfo["params"]
        ) or "void"

        body = "\n    ".join(body_lines)
        full_fn = f"{c_ret_type} FUNC_{name}({param_decl}) {{\n{hoisted_decls}    {body}\n"
        if trailing_frees:
            full_fn += f"    {trailing_frees}\n"
        full_fn += "}\n"
        symbol_table["compiled_functions_c"].append(full_fn)

        (outer_var, outer_var_gen, outer_heap, outer_coll, outer_str_decls,
         outer_coll_hoist) = symbol_table["func_ctx_stack"].pop()
        symbol_table["var"] = outer_var
        symbol_table["var_gen"] = outer_var_gen
        symbol_table["heap_vars"] = outer_heap
        symbol_table["collection_vars"] = outer_coll
        symbol_table["heap_str_decls"] = outer_str_decls
        symbol_table["collection_hoist"] = outer_coll_hoist
        symbol_table["current_func"] = None

        log_exit("CODE.endfunc", "-> None (fonction assemblee)")
        return None

    @staticmethod
    def exec_call(name_token, arg_specs):
        """exec <name> <arg1> ...; appel C reel de FUNC_<name>. Remplit RX_ret si
        la fonction retourne quelque chose (meme contrainte qu'avant : une seule
        signature de retour partagee par RX_ret dans tout le programme).

        arg_specs : liste de tuples produite par le dispatch 'exec' de
        _compile_line, chaque element etant soit ("pos", None, operand) pour un
        argument positionnel classique, soit ("named", pname, operand) pour un
        argument nomme (syntaxe 'exec f a=1 b=2;'). Les parametres declares avec
        une valeur par defaut (voir func_begin/_split_func_signature) peuvent
        etre omis a l'appel."""
        log_enter("CODE.exec_call", "name_token=%r arg_specs=%r", name_token, arg_specs)
        if name_token[0] != "ident":
            raise REX_SL(f"exec: nom de fonction non gere : {name_token}")
        name = name_token[1]
        if name not in symbol_table["functions"]:
            raise REX_SL(f"exec: fonction inconnue : {name}")

        # trace l'arete caller -> callee dans le graphe d'appels. Ce graphe n'est
        # plus utilise pour BLOQUER la recursion (voir compile() : la generation
        # C emet des prototypes en avant pour toutes les fonctions, donc la
        # recursion directe ou indirecte fonctionne nativement via la pile C) --
        # il sert uniquement a emettre un avertissement informatif en fin de
        # compilation, voir _detect_recursive_call().
        if symbol_table["current_func"] is not None:
            caller = symbol_table["current_func"]
            symbol_table["call_graph"].setdefault(caller, set()).add(name)

        finfo = symbol_table["functions"][name]
        params = finfo["params"]                # [(ptype, pname), ...] dans l'ordre de declaration
        defaults = finfo.get("defaults", {})     # pname -> token litteral par defaut
        param_names = [pname for _, pname in params]

        positional = [spec for spec in arg_specs if spec[0] == "pos"]
        named = {}
        for spec in arg_specs:
            if spec[0] != "named":
                continue
            pname = spec[1]
            if pname not in param_names:
                raise REX_SL(f"exec {name}: parametre nomme inconnu : {pname}")
            if pname in named:
                raise REX_SL(f"exec {name}: argument nomme fourni plusieurs fois : {pname}")
            named[pname] = spec[2]

        if len(positional) > len(params):
            raise REX_SL(
                f"exec {name}: trop d'arguments positionnels "
                f"({len(positional)} recus, {len(params)} parametre(s))"
            )

        resolved = [None] * len(params)
        used = [False] * len(params)
        for idx, spec in enumerate(positional):
            resolved[idx] = spec[2]
            used[idx] = True
        for pname, operand in named.items():
            idx = param_names.index(pname)
            if used[idx]:
                raise REX_SL(
                    f"exec {name}: argument '{pname}' fourni a la fois positionnellement et par nom"
                )
            resolved[idx] = operand
            used[idx] = True
        for idx, (ptype, pname) in enumerate(params):
            if resolved[idx] is None:
                if pname in defaults:
                    resolved[idx] = defaults[pname]
                else:
                    raise REX_SL(
                        f"exec {name}: argument manquant sans valeur par defaut : {pname}"
                    )

        arg_exprs = []
        for (ptype, pname), operand in zip(params, resolved):
            atype = REX_SL_CODE._operand_type(operand)
            if atype != ptype:
                raise REX_SL(f"exec {name}: argument {pname} attend {ptype}, recu {atype}")
            arg_exprs.append(REX_SL_CODE._operand_expr(operand))

        call_expr = f"FUNC_{name}({', '.join(arg_exprs)})"

        if finfo["ret_type"] is None or finfo["ret_type"] == "none":
            # void ou non encore connu -> appel sans capture de valeur de retour
            c_line = f"{call_expr};"
            log_exit("CODE.exec_call", "-> %r", c_line)
            return c_line

        ret_type = finfo["ret_type"]
        if not symbol_table["rx_ret_declared"]:
            symbol_table["rx_ret_declared"] = True
            symbol_table["rx_ret_type"] = ret_type
            symbol_table["rx_var"]["RX_ret"] = ret_type
        elif symbol_table["rx_ret_type"] != ret_type:
            raise REX_SL(
                f"exec {name}: RX_ret est deja de type {symbol_table['rx_ret_type']}, "
                f"cette fonction retourne {ret_type}"
            )

        if ret_type == "str":
            c_line = f"free(RX_ret);\n    RX_ret = {call_expr};"
        else:
            c_line = f"RX_ret = {call_expr};"

        log_exit("CODE.exec_call", "-> %r", c_line)
        return c_line
    
    @staticmethod
    def change(destination, target_type_token):
        log_enter("CODE.change", "destination=%r target_type_token=%r", destination, target_type_token)

        dest_type, dest_raw_name = destination
        if dest_type != "ident" or dest_raw_name not in symbol_table["var"]:
            raise REX_SL(f"change: variable inconnue ou non declaree : {destination}")
        if REX_SL_CODE._is_rx(dest_raw_name):
            raise REX_SL(f"change: destination RX_ en lecture seule (registre importe) : {dest_raw_name}")
        if dest_raw_name in symbol_table["const_vars"]:
            raise REX_SL(f"change: modification interdite, {dest_raw_name} est une constante")

        current_type = symbol_table["var"][dest_raw_name]
        if current_type in ("list", "dict"):
            raise REX_SL(f"change: type non convertible (list/dict) : {dest_raw_name}")

        if target_type_token[0] != "ident" or target_type_token[1] not in ("number", "float", "bool", "str"):
            raise REX_SL(f"change: type cible non gere : {target_type_token}")
        target_type = target_type_token[1]

        if target_type == current_type:
            raise REX_SL(f"change: {dest_raw_name} est deja de type {target_type}")

        old_c_name = REX_SL_CODE._c_name(dest_raw_name)
        was_heap = _heap_is(old_c_name)

        symbol_table["var_gen"][dest_raw_name] = symbol_table["var_gen"].get(dest_raw_name, 0) + 1
        new_c_name = REX_SL_CODE._c_name(dest_raw_name)

        lines = []

        if target_type == "str":
            fmt, conv_expr = {
                "number": ("%d", old_c_name),
                "float": ("%g", old_c_name),
                "bool": ("%s", f'({old_c_name} ? "true" : "false")'),
            }[current_type]
            lines.append(f'char {new_c_name}_buf[{STACK_STR_THRESHOLD}];')
            lines.append(f'snprintf({new_c_name}_buf, {STACK_STR_THRESHOLD}, "{fmt}", {conv_expr});')
            lines.append(f'char* {new_c_name} = {new_c_name}_buf;')

        elif current_type == "str":
            if target_type == "number":
                lines.append(f'int {new_c_name} = atoi({old_c_name});')
            elif target_type == "float":
                lines.append(f'float {new_c_name} = (float)atof({old_c_name});')
            else:  # bool
                lines.append(f"bool {new_c_name} = ({old_c_name}[0] == 't' || {old_c_name}[0] == '1');")

        else:
            c_type = {"number": "int", "float": "float", "bool": "bool"}[target_type]
            if target_type == "bool":
                expr = f'({old_c_name} != 0)'
            elif current_type == "bool":
                expr = f'({old_c_name} ? 1 : 0)'
            else:
                expr = old_c_name
            lines.append(f'{c_type} {new_c_name} = {expr};')

        if was_heap:
            lines.append(f'free({old_c_name});')
            _heap_unmark(old_c_name)   # <-- CRITIQUE, voir §7 (double free)

        symbol_table["var"][dest_raw_name] = target_type

        c_line = "\n    ".join(lines)
        log_exit("CODE.change", "-> %r", c_line)
        return c_line

    @staticmethod
    def retype(var_token, new_type_token, new_value_token):
        """retype <var> <nouveau_type> [<valeur>];
        Redecrare une variable existante avec un nouveau type (ecrase l'entree
        dans la table des symboles sans interdire le redeclarage -- c'est le but
        de cet opcode).  L'ancienne valeur est liberee si necessaire (heap str /
        collections).  Le generateur de generation (var_gen) est incremente pour
        que _c_name() produise un NOM C DISTINCT de l'ancienne variable, evitant
        tout conflit de declaration dans le meme bloc C.
        
        Gain principal : REX.py n'a plus besoin de sa couche _aliases /
        rexsl_name() / retype_as_collection() / assign_dynamic() pour contourner
        l'absence de redeclaration cote REX-SL."""
        log_enter("CODE.retype", "var_token=%r new_type_token=%r new_value_token=%r",
                  var_token, new_type_token, new_value_token)

        if var_token[0] != "ident":
            raise REX_SL(f"retype: nom de variable attendu : {var_token}")
        raw_name = var_token[1]
        if REX_SL_CODE._is_rx(raw_name):
            raise REX_SL(f"retype: registre RX_ en lecture seule : {raw_name}")
        if raw_name in symbol_table["const_vars"]:
            raise REX_SL(f"retype: modification interdite, {raw_name} est une constante")
        if raw_name not in symbol_table["var"]:
            raise REX_SL(f"retype: variable inconnue : {raw_name} (utiliser var pour la premiere declaration)")

        if new_type_token[0] != "ident" or new_type_token[1] not in (
            "number", "float", "bool", "str", "list", "dict", "set", "tuple"
        ):
            raise REX_SL(f"retype: type cible invalide : {new_type_token}")
        new_type = new_type_token[1]

        # verifie coherence valeur initiale / nouveau type (scalaires uniquement)
        if new_value_token is not None and new_type not in ("list", "dict", "set", "tuple"):
            if new_value_token[0] != new_type:
                raise REX_SL(
                    f"retype: valeur initiale de type {new_value_token[0]} "
                    f"incompatible avec le nouveau type {new_type}"
                )
        if new_value_token is not None and new_type in ("list", "dict", "set", "tuple"):
            raise REX_SL(f"retype: les collections (list/dict/set/tuple) ne prennent pas de valeur initiale")

        old_type = symbol_table["var"][raw_name]
        old_c_name = REX_SL_CODE._c_name(raw_name)

        lines = []

        # liberation de l'ancienne valeur si necessaire
        if old_type == "str" and _heap_is(old_c_name):
            lines.append(f"free({old_c_name});")
            _heap_unmark(old_c_name)
        elif old_type == "list":
            # cherche si cette collection est trackee
            for coll_name, coll_kind in symbol_table["collection_vars"][-1]:
                if coll_name == old_c_name and coll_kind == "list":
                    lines.append(f"if ({old_c_name}) {{ rexsl_list_free({old_c_name}); {old_c_name} = NULL; }}")
                    symbol_table["collection_vars"][-1] = [
                        (n, k) for n, k in symbol_table["collection_vars"][-1]
                        if not (n == old_c_name and k == "list")
                    ]
                    break
        elif old_type == "dict":
            for coll_name, coll_kind in symbol_table["collection_vars"][-1]:
                if coll_name == old_c_name and coll_kind == "dict":
                    lines.append(f"if ({old_c_name}) {{ rexsl_dict_free({old_c_name}); {old_c_name} = NULL; }}")
                    symbol_table["collection_vars"][-1] = [
                        (n, k) for n, k in symbol_table["collection_vars"][-1]
                        if not (n == old_c_name and k == "dict")
                    ]
                    break
        elif old_type == "set":
            for coll_name, coll_kind in symbol_table["collection_vars"][-1]:
                if coll_name == old_c_name and coll_kind == "set":
                    lines.append(f"if ({old_c_name}) {{ rexsl_list_free({old_c_name}); {old_c_name} = NULL; }}")
                    symbol_table["collection_vars"][-1] = [
                        (n, k) for n, k in symbol_table["collection_vars"][-1]
                        if not (n == old_c_name and k == "set")
                    ]
                    break
        elif old_type == "tuple":
            for coll_name, coll_kind in symbol_table["collection_vars"][-1]:
                if coll_name == old_c_name and coll_kind == "tuple":
                    lines.append(f"if ({old_c_name}) {{ rexsl_list_free({old_c_name}); {old_c_name} = NULL; }}")
                    symbol_table["collection_vars"][-1] = [
                        (n, k) for n, k in symbol_table["collection_vars"][-1]
                        if not (n == old_c_name and k == "tuple")
                    ]
                    break

        # incremente la generation -> nouveau nom C distinct dans le meme bloc
        symbol_table["var_gen"][raw_name] = symbol_table["var_gen"].get(raw_name, 0) + 1
        new_c_name = REX_SL_CODE._c_name(raw_name)

        # declaration de la nouvelle variable
        symbol_table["var"][raw_name] = new_type

        if new_type == "number":
            val = str(new_value_token[1]) if new_value_token else "0"
            lines.append(f"int {new_c_name} = {val};")
        elif new_type == "float":
            val = str(new_value_token[1]) if new_value_token else "0.0f"
            lines.append(f"float {new_c_name} = {val};")
        elif new_type == "bool":
            val = ("true" if new_value_token[1] else "false") if new_value_token else "false"
            lines.append(f"bool {new_c_name} = {val};")
        elif new_type == "str":
            raw_val = new_value_token[1] if new_value_token else ""
            escaped = _escape_c_string(raw_val)
            symbol_table["rexfn"].append("rexsl_str_alloc")
            _heap_mark(new_c_name)
            if _can_hoist():
                symbol_table["heap_str_decls"][-1].add(new_c_name)
                lines.append(f'{new_c_name} = rexsl_str_alloc("{escaped}");')
            else:
                lines.append(f'char* {new_c_name} = rexsl_str_alloc("{escaped}");')
        elif new_type == "list":
            symbol_table["rexfn"].append("rexsl_collections")
            symbol_table["collection_vars"][-1].append((new_c_name, "list"))
            if _can_hoist():
                symbol_table["collection_hoist"][-1].add(new_c_name)
                lines.append(f"{new_c_name} = rexsl_list_new();")
            else:
                lines.append(f"RexList* {new_c_name} = rexsl_list_new();")
        elif new_type == "dict":
            symbol_table["rexfn"].append("rexsl_collections")
            symbol_table["collection_vars"][-1].append((new_c_name, "dict"))
            if _can_hoist():
                symbol_table["collection_hoist"][-1].add(new_c_name)
                lines.append(f"{new_c_name} = rexsl_dict_new();")
            else:
                lines.append(f"RexDict* {new_c_name} = rexsl_dict_new();")
        elif new_type == "set":
            symbol_table["rexfn"].append("rexsl_collections")
            symbol_table["collection_vars"][-1].append((new_c_name, "set"))
            if _can_hoist():
                symbol_table["collection_hoist"][-1].add(new_c_name)
                lines.append(f"{new_c_name} = rexsl_list_new();")
            else:
                lines.append(f"RexList* {new_c_name} = rexsl_list_new();")
        elif new_type == "tuple":
            symbol_table["rexfn"].append("rexsl_collections")
            symbol_table["collection_vars"][-1].append((new_c_name, "tuple"))
            if _can_hoist():
                symbol_table["collection_hoist"][-1].add(new_c_name)
                lines.append(f"{new_c_name} = rexsl_list_new();")
            else:
                lines.append(f"RexList* {new_c_name} = rexsl_list_new();")

        c_line = "\n    ".join(lines)
        log_exit("CODE.retype", "-> %r", c_line)
        return c_line

    @staticmethod
    def pushall():
        """pushall; ouvre un scope C reel + sauvegarde une copie de chaque variable
        courante sous RXS_<profondeur>_<nom>, lisible depuis le scope enfant."""
        log_enter("CODE.pushall", "vars_courantes=%r", symbol_table["var"])
        symbol_table["scope_stack"].append(dict(symbol_table["var"]))
        symbol_table["scope_depth"] += 1
        symbol_table["heap_vars"].append(set())
        depth = symbol_table["scope_depth"]

        c_type_by_kind = {"number": "int", "float": "float", "bool": "bool", "str": "char*"}
        lines = ["{"]
        for name, kind in symbol_table["var"].items():
            if kind in ("list", "dict"):
                continue  # non transmissibles via forward pour l'instant
            c_name = REX_SL_CODE._c_name(name)
            c_type = c_type_by_kind[kind]
            lines.append(f"    {c_type} RXS_{depth}_{name} = {c_name};")

        symbol_table["var"] = {}
        symbol_table["var_gen_stack"].append(dict(symbol_table["var_gen"]))
        symbol_table["var_gen"] = {}

        c_line = "\n    ".join(lines)
        log_exit("CODE.pushall", "-> %r", c_line)
        return c_line

    @staticmethod
    def popall():
        """popall; ferme le scope ouvert par le dernier pushall, libere sa memoire heap."""
        log_enter("CODE.popall", "popall")
        if not symbol_table["scope_stack"]:
            log_exit("CODE.popall", "ERREUR")
            raise REX_SL("popall sans pushall correspondant")

        lines = [f"free({name});" for name in symbol_table["heap_vars"][-1]]
        symbol_table["heap_vars"].pop()
        symbol_table["var"] = symbol_table["scope_stack"].pop()
        symbol_table["var_gen"] = symbol_table["var_gen_stack"].pop()
        symbol_table["scope_depth"] -= 1
        lines.append("}")

        c_line = "\n    ".join(lines)
        log_exit("CODE.popall", "-> %r", c_line)
        return c_line

    @staticmethod
    def forward(name_tokens):
        """forward arg1 [arg2 ...]; copie chaque variable depuis le scope parent
        (RXS_<depth>_<nom>) vers une nouvelle variable de meme nom dans le scope
        courant. Les str sont dupliquees sur le tas (jamais un alias de pointeur)."""
        log_enter("CODE.forward", "name_tokens=%r", name_tokens)
        if not name_tokens:
            log_exit("CODE.forward", "ERREUR")
            raise REX_SL("forward attend au moins un argument")
        if not symbol_table["scope_stack"]:
            log_exit("CODE.forward", "ERREUR")
            raise REX_SL("forward sans pushall correspondant")

        parent_vars = symbol_table["scope_stack"][-1]
        depth = symbol_table["scope_depth"]
        lines = []
        for token in name_tokens:
            if token[0] != "ident":
                log_exit("CODE.forward", "ERREUR")
                raise REX_SL(f"forward: argument non gere : {token}")
            arg_name = token[1]
            if arg_name not in parent_vars:
                log_exit("CODE.forward", "ERREUR")
                raise REX_SL(f"forward: variable inconnue dans le scope parent : {arg_name}")
            if arg_name in symbol_table["var"]:
                log_exit("CODE.forward", "ERREUR")
                raise REX_SL(f"forward: variable deja declaree dans ce scope : {arg_name}")

            arg_kind = parent_vars[arg_name]
            symbol_table["var"][arg_name] = arg_kind
            src = f"RXS_{depth}_{arg_name}"

            if arg_kind == "str":
                symbol_table["rexfn"].append("rexsl_str_alloc")
                _heap_mark(REX_SL_CODE._c_name(arg_name))
                lines.append(f"char* SL_{arg_name} = rexsl_str_alloc({src});")
            elif arg_kind in ("number", "float", "bool"):
                c_type = {"number": "int", "float": "float", "bool": "bool"}[arg_kind]
                lines.append(f"{c_type} SL_{arg_name} = {src};")
            else:
                log_exit("CODE.forward", "ERREUR")
                raise REX_SL(f"forward: type non transmissible : {arg_kind}")

        c_line = "\n    ".join(lines)
        log_exit("CODE.forward", "-> %r", c_line)
        return c_line

    @staticmethod
    def return_stmt(var_operand):
        """return var; A l'interieur d'un func/endfunc : return C reel (avec free
        des heap_vars locaux). En dehors (ancien mode pushall/popall manuel) :
        copie vers RX_ret, comportement inchange."""
        log_enter("CODE.return_stmt", "var_operand=%r", var_operand)
        op_type = REX_SL_CODE._operand_type(var_operand)

        # 'return none;' dans un func void -> simple 'return;' C
        if op_type == "none" and symbol_table["current_func"] is not None:
            fname = symbol_table["current_func"]
            finfo = symbol_table["functions"][fname]
            if finfo["ret_type"] not in (None, "none"):
                log_exit("CODE.return_stmt", "ERREUR")
                raise REX_SL(
                    f"return none: incompatible avec le type de retour {finfo['ret_type']} de {fname}"
                )
            finfo["ret_type"] = "none"
            # libere la memoire heap locale avant de retourner
            free_lines = _conditional_free_lines(
                symbol_table["heap_vars"][-1], symbol_table["collection_vars"][-1]
            )
            lines = free_lines + ["return;"]
            c_line = "\n    ".join(lines)
            log_exit("CODE.return_stmt", "-> %r (return void)", c_line)
            return c_line

        if op_type not in ("number", "float", "bool", "str", "list", "dict"):
            log_exit("CODE.return_stmt", "ERREUR")
            raise REX_SL(f"return: type non gere : {var_operand}")
        expr = REX_SL_CODE._operand_expr(var_operand)

        if symbol_table["current_func"] is not None:
            fname = symbol_table["current_func"]
            finfo = symbol_table["functions"][fname]
            if finfo["ret_type"] is None:
                finfo["ret_type"] = op_type
            elif finfo["ret_type"] != op_type:
                log_exit("CODE.return_stmt", "ERREUR")
                raise REX_SL(
                    f"return: type incoherent dans {fname} : deja {finfo['ret_type']}, "
                    f"recoit {op_type}"
                )

            # libere toute la memoire heap allouee localement dans CETTE fonction
            # EXCEPTION : si on retourne un list/dict local, NE PAS le liberer ici
            # (il appartient maintenant a l'appelant via le pointeur retourne)
            ret_c_name = REX_SL_CODE._c_name(var_operand[1]) if var_operand[0] == "ident" else None
            if op_type in ("list", "dict", "set", "tuple") and ret_c_name:
                free_set = symbol_table["heap_vars"][-1] - {ret_c_name}
            else:
                free_set = symbol_table["heap_vars"][-1]
            # meme logique pour les collections (list/dict/set/tuple) locales : toutes liberees
            # a ce point de retour SAUF celle qu'on renvoie elle-meme (le pointeur
            # est transmis a l'appelant, qui en devient responsable).
            colls_to_free = [
                (coll_name, coll_kind)
                for coll_name, coll_kind in symbol_table["collection_vars"][-1]
                if not (op_type in ("list", "dict", "set", "tuple") and coll_name == ret_c_name)
            ]
            free_lines = _conditional_free_lines(free_set, colls_to_free)

            if op_type == "str":
                # copie fraiche sur le tas : le buffer local va disparaitre a la
                # sortie de la fonction, l'appelant doit posseder sa propre copie.
                # IMPORTANT : la copie doit se faire AVANT les free() ci-dessous,
                # sinon expr (qui peut etre directement le nom d'une variable
                # locale presente dans heap_vars[-1], p.ex. une str retournee
                # telle quelle, un slice, une concatenation stockee dans un
                # temporaire heap...) peut deja avoir ete liberee au moment de
                # rexsl_str_alloc(expr) -> use-after-free. On capture donc la
                # valeur dans une variable temporaire d'abord, on libere ensuite,
                # puis on retourne la temporaire.
                symbol_table["rexfn"].append("rexsl_str_alloc")
                symbol_table["ret_tmp_counter"] += 1
                ret_tmp = f"__rexsl_ret_tmp_{symbol_table['ret_tmp_counter']}"
                lines = [f"char* {ret_tmp} = rexsl_str_alloc({expr});"]
                lines += free_lines
                lines += [f"return {ret_tmp};"]
            elif op_type in ("list", "dict"):
                # list/dict : retour par pointeur. On ne copie PAS la structure
                # (passage par reference : l'appelant recoit le meme pointeur).
                # Les variables heap locales autres que la collection retournee
                # sont liberees ; la collection elle-meme est transmise a l'appelant.
                lines = free_lines + [f"return {expr};"]
            else:
                lines = free_lines + [f"return {expr};"]

            c_line = "\n    ".join(lines)
        else:
            if not symbol_table["rx_ret_declared"]:
                symbol_table["rx_ret_declared"] = True
                symbol_table["rx_ret_type"] = op_type
                symbol_table["rx_var"]["RX_ret"] = op_type
            elif symbol_table["rx_ret_type"] != op_type:
                log_exit("CODE.return_stmt", "ERREUR")
                raise REX_SL(
                    f"return: type incoherent, RX_ret est {symbol_table['rx_ret_type']} "
                    f"mais {var_operand} est {op_type}"
                )
            if op_type == "str":
                # meme risque de use-after-free que dans la branche func : si expr
                # reference RX_ret lui-meme (ex: return RX_ret, ou une expression
                # qui le reutilise), il ne faut pas le liberer avant de l'avoir lu.
                symbol_table["rexfn"].append("rexsl_str_alloc")
                symbol_table["ret_tmp_counter"] += 1
                ret_tmp = f"__rexsl_ret_tmp_{symbol_table['ret_tmp_counter']}"
                c_line = (
                    f"char* {ret_tmp} = rexsl_str_alloc(" + expr + ");\n"
                    "    free(RX_ret);\n"
                    f"    RX_ret = {ret_tmp};"
                )
            else:
                c_line = f"RX_ret = {expr};"

        log_exit("CODE.return_stmt", "-> %r", c_line)
        return c_line
    
    @staticmethod
    def share(source_operand, name_operand):
        log_enter("CODE.share", "source_operand=%r name_operand=%r", source_operand, name_operand)
        if not symbol_table["shm_enabled"]:
            raise REX_SL("share: shared_memory non activee (declare-la en premiere ligne)")
        if REX_SL_CODE._operand_type(name_operand) != "str":
            raise REX_SL(f"share: name doit etre une string : {name_operand}")
        src_type = REX_SL_CODE._operand_type(source_operand)
        if src_type not in ("number", "float", "bool", "str"):
            log_exit("CODE.share", "ERREUR")
            raise REX_SL(f"share: type non partageable : {source_operand}")

        name_e = REX_SL_CODE._operand_expr(name_operand)
        if name_operand[0] == "str":
            symbol_table["shm_shared_keys"].append(name_operand[1])
        src_e = REX_SL_CODE._operand_expr(source_operand)
        type_tag = {"number": 0, "float": 1, "bool": 2, "str": 3}[src_type]

        if src_type == "str":
            vlen_expr = f"(uint32_t)(strlen({src_e}) + 1)"
            val_ptr = src_e
            tmp_decl = ""
        else:
            c_type = {"number": "int", "float": "float", "bool": "bool"}[src_type]
            vlen_expr = f"sizeof({c_type})"
            tmp_decl = f"{c_type} __rexsl_share_tmp = {src_e};\n        "
            val_ptr = "&__rexsl_share_tmp"

        c_line = (
            '{\n'
            '        sem_wait(__rexsl_shm_sem);\n'
            f'        {tmp_decl}char* entry = rexsl_shm_find_or_create({name_e}, {type_tag}, {vlen_expr});\n'
            f'        rexsl_shm_write_value(entry, {type_tag}, {vlen_expr}, {val_ptr});\n'
            '        sem_post(__rexsl_shm_sem);\n'
            '    }'
        )
        log_exit("CODE.share", "-> %r", c_line)
        return c_line

    @staticmethod
    def save_named(destination, name_operand):
        log_enter("CODE.save_named", "destination=%r name_operand=%r", destination, name_operand)
        if not symbol_table["shm_enabled"]:
            raise REX_SL("save: shared_memory non activee")
        dest_type, dest_raw_name = destination
        if dest_type != "ident" or dest_raw_name not in symbol_table["var"]:
            raise REX_SL(f"save: destination doit etre une variable deja declaree : {destination}")
        if dest_raw_name in symbol_table["const_vars"]:
            log_exit("CODE.save_named", "ERREUR")
            raise REX_SL(f"save: modification interdite, {dest_raw_name} est une constante")
        dest_kind = symbol_table["var"][dest_raw_name]
        if dest_kind not in ("number", "float", "bool", "str"):
            log_exit("CODE.save_named", "ERREUR")
            raise REX_SL(f"save: type de destination non gere : {dest_kind}")
        if REX_SL_CODE._operand_type(name_operand) != "str":
            raise REX_SL(f"save: name doit etre une string : {name_operand}")

        dest_name = REX_SL_CODE._c_name(dest_raw_name)
        name_e = REX_SL_CODE._operand_expr(name_operand)

        if dest_kind == "str":
            symbol_table["rexfn"].append("rexsl_str_alloc")
            free_old = f'free({dest_name}); ' if _heap_is(dest_name) else ""
            if not _heap_is(dest_name):
                _heap_mark(dest_name)
            assign = (
                'uint32_t __vlen; void* __vptr = rexsl_shm_value_ptr(entry, &__vlen);\n'
                f'        {free_old}{dest_name} = malloc(__vlen); REXSL_CHECK_ALLOC({dest_name}); '
                f'memcpy({dest_name}, __vptr, __vlen);'
            )
        else:
            c_type = {"number": "int", "float": "float", "bool": "bool"}[dest_kind]
            assign = (
                'uint32_t __vlen; void* __vptr = rexsl_shm_value_ptr(entry, &__vlen);\n'
                f'        memcpy(&{dest_name}, __vptr, sizeof({c_type}));'
            )

        c_line = (
            '{\n'
            '        sem_wait(__rexsl_shm_sem);\n        rexsl_shm_sync();\n'
            f'        char* entry = rexsl_shm_find({name_e});\n'
            f'        if (entry == NULL) {{ sem_post(__rexsl_shm_sem); fprintf(stderr, "[REX-SL] erreur : cle inconnue en memoire partagee : %s\\n", {name_e}); exit(1); }}\n'
            f'        {assign}\n'
            '        sem_post(__rexsl_shm_sem);\n'
            '    }'
        )
        log_exit("CODE.save_named", "-> %r", c_line)
        return c_line

    @staticmethod
    def save_all(destination):
        log_enter("CODE.save_all", "destination=%r", destination)
        if not symbol_table["shm_enabled"]:
            raise REX_SL("save: shared_memory non activee")
        dest_type, dest_raw_name = destination
        if dest_type != "ident" or dest_raw_name not in symbol_table["var"]:
            raise REX_SL(f"save: destination doit etre une variable deja declaree : {destination}")
        dest_kind = symbol_table["var"][dest_raw_name]
        dest_c = REX_SL_CODE._c_name(dest_raw_name)

        walk_start = (
            'char* __rexsl_cur = __rexsl_shm_data;\n'
            '        char* __rexsl_end = __rexsl_shm_data + __rexsl_shm_hdr->used;\n'
            '        while (__rexsl_cur < __rexsl_end) {\n'
            '            uint32_t __k_klen; memcpy(&__k_klen, __rexsl_cur, 4);\n'
            '            char* __k_key = __rexsl_cur + 4;\n'
            '            int32_t __k_type; memcpy(&__k_type, __k_key + __k_klen, 4);\n'
            '            uint32_t __k_vlen; memcpy(&__k_vlen, __k_key + __k_klen + 4, 4);\n'
            '            char* __k_val = __k_key + __k_klen + 8;\n'
            '            if (__k_klen == 0 || __k_key[0] == \'\\0\') { __rexsl_cur = __k_val + __k_vlen; continue; }\n'
        )
        walk_end = '            __rexsl_cur = __k_val + __k_vlen;\n        }\n'

        if dest_kind == "list":
            c_line = (
                '{\n        sem_wait(__rexsl_shm_sem);\n        rexsl_shm_sync();\n'
                f'        {walk_start}'
                '            char* __key_copy = malloc((size_t)__k_klen + 1);\n'
                '            REXSL_CHECK_ALLOC(__key_copy);\n'
                '            memcpy(__key_copy, __k_key, __k_klen); __key_copy[__k_klen] = \'\\0\';\n'
                f'            rexsl_list_append({dest_c}, (RexValue){{ .type = REXSL_T_STR, .value.as_str = __key_copy }});\n'
                f'        {walk_end}'
                '        sem_post(__rexsl_shm_sem);\n    }'
            )
        elif dest_kind == "dict":
            c_line = (
                '{\n        sem_wait(__rexsl_shm_sem);\n        rexsl_shm_sync();\n'
                f'        {walk_start}'
                '            char* __key_copy = malloc((size_t)__k_klen + 1);\n'
                '            REXSL_CHECK_ALLOC(__key_copy);\n'
                '            memcpy(__key_copy, __k_key, __k_klen); __key_copy[__k_klen] = \'\\0\';\n'
                '            RexValue __v;\n'
                '            switch (__k_type) {\n'
                '                case 0: { int __n; memcpy(&__n, __k_val, sizeof(int)); __v = (RexValue){ .type = REXSL_T_NUMBER, .value.as_number = __n }; } break;\n'
                '                case 1: { float __f; memcpy(&__f, __k_val, sizeof(float)); __v = (RexValue){ .type = REXSL_T_FLOAT, .value.as_float = __f }; } break;\n'
                '                case 2: { bool __b; memcpy(&__b, __k_val, sizeof(bool)); __v = (RexValue){ .type = REXSL_T_BOOL, .value.as_bool = __b }; } break;\n'
                '                default: { char* __s = malloc(__k_vlen); REXSL_CHECK_ALLOC(__s); memcpy(__s, __k_val, __k_vlen); __v = (RexValue){ .type = REXSL_T_STR, .value.as_str = __s }; } break;\n'
                '            }\n'
                f'            rexsl_dict_set({dest_c}, __key_copy, __v);\n            free(__key_copy);\n'
                f'        {walk_end}'
                '        sem_post(__rexsl_shm_sem);\n    }'
            )
        else:
            log_exit("CODE.save_all", "ERREUR")
            raise REX_SL(f"save: sans <name>, destination doit etre list ou dict : {dest_kind}")

        log_exit("CODE.save_all", "-> %r", c_line)
        return c_line
    
    @staticmethod
    def shm_del(name_operand):
        log_enter("CODE.shm_del", "name_operand=%r", name_operand)
        if not symbol_table["shm_enabled"]:
            raise REX_SL("del: shared_memory non activee")
        if REX_SL_CODE._operand_type(name_operand) != "str":
            raise REX_SL(f"del: name doit etre une string : {name_operand}")
        name_e = REX_SL_CODE._operand_expr(name_operand)
        if name_operand[0] == "str":
            symbol_table["shm_deleted_keys"].append(name_operand[1])
        c_line = f"rexsl_shm_del({name_e});"
        log_exit("CODE.shm_del", "-> %r", c_line)
        return c_line
    
    @staticmethod
    def split(list_dest, str_operand, delim_operand):
        log_enter("CODE.split", "list_dest=%r str=%r delim=%r", list_dest, str_operand, delim_operand)
        dest_type, dest_raw_name = list_dest
        if dest_type != "ident" or symbol_table["var"].get(dest_raw_name) != "list":
            log_exit("CODE.split", "ERREUR")
            raise REX_SL(f"split: destination doit etre une liste deja declaree : {list_dest}")
        if REX_SL_CODE._operand_type(str_operand) != "str" or REX_SL_CODE._operand_type(delim_operand) != "str":
            log_exit("CODE.split", "ERREUR")
            raise REX_SL(f"split: str/delim doivent etre des string : {str_operand}, {delim_operand}")
        symbol_table["rexfn"].append("rexsl_str_split")
        list_c = REX_SL_CODE._c_name(dest_raw_name)
        str_e = REX_SL_CODE._operand_expr(str_operand)
        delim_e = REX_SL_CODE._operand_expr(delim_operand)
        c_line = f"rexsl_str_split({list_c}, {str_e}, {delim_e});"
        log_exit("CODE.split", "-> %r", c_line)
        return c_line


    @staticmethod
    def list_str(destination, list_operand):
        log_enter("CODE.list_str", "destination=%r list=%r", destination, list_operand)
        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            raise REX_SL(f"destination non gere : {destination[1]}")
        list_type, list_name = list_operand
        if list_type != "ident" or symbol_table["var"].get(list_name) != "list":
            log_exit("CODE.list_str", "ERREUR")
            raise REX_SL(f"list_str: operande doit etre une liste declaree : {list_operand}")
        symbol_table["rexfn"].append("rexsl_collections")
        symbol_table["rexfn"].append("rexsl_str_alloc")
        symbol_table["rexfn"].append("rexsl_collections_str")
        list_c = REX_SL_CODE._c_name(list_name)
        c_line = REX_SL_CODE._assign_heap_str(dest_raw_name, f"rexsl_list_to_str({list_c})")
        log_exit("CODE.list_str", "-> %r", c_line)
        return c_line

    @staticmethod
    def dict_str(destination, dict_operand):
        log_enter("CODE.dict_str", "destination=%r dict=%r", destination, dict_operand)
        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            raise REX_SL(f"destination non gere : {destination[1]}")
        dict_type, dict_name = dict_operand
        if dict_type != "ident" or symbol_table["var"].get(dict_name) != "dict":
            log_exit("CODE.dict_str", "ERREUR")
            raise REX_SL(f"dict_str: operande doit etre un dict declare : {dict_operand}")
        symbol_table["rexfn"].append("rexsl_collections")
        symbol_table["rexfn"].append("rexsl_str_alloc")
        symbol_table["rexfn"].append("rexsl_collections_str")
        dict_c = REX_SL_CODE._c_name(dict_name)
        c_line = REX_SL_CODE._assign_heap_str(dest_raw_name, f"rexsl_dict_to_str({dict_c})")
        log_exit("CODE.dict_str", "-> %r", c_line)
        return c_line

    @staticmethod
    def join(destination, list_operand, delim_operand):
        log_enter("CODE.join", "destination=%r list=%r delim=%r", destination, list_operand, delim_operand)
        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            raise REX_SL(f"destination non gere : {destination[1]}")
        list_type, list_name = list_operand
        if list_type != "ident" or symbol_table["var"].get(list_name) != "list":
            log_exit("CODE.join", "ERREUR")
            raise REX_SL(f"join: operande doit etre une liste declaree : {list_operand}")
        if REX_SL_CODE._operand_type(delim_operand) != "str":
            log_exit("CODE.join", "ERREUR")
            raise REX_SL(f"join: delim doit etre une string : {delim_operand}")
        symbol_table["rexfn"].append("rexsl_list_join")
        list_c = REX_SL_CODE._c_name(list_name)
        delim_e = REX_SL_CODE._operand_expr(delim_operand)
        c_line = REX_SL_CODE._assign_heap_str(dest_raw_name, f"rexsl_list_join({list_c}, {delim_e})")
        log_exit("CODE.join", "-> %r", c_line)
        return c_line

    @staticmethod
    def readlines(list_dest, path_operand):
        log_enter("CODE.readlines", "list_dest=%r path_operand=%r", list_dest, path_operand)
        dest_type, dest_raw_name = list_dest
        if dest_type != "ident" or symbol_table["var"].get(dest_raw_name) != "list":
            log_exit("CODE.readlines", "ERREUR")
            raise REX_SL(f"readlines: destination doit etre une liste deja declaree : {list_dest}")
        if REX_SL_CODE._operand_type(path_operand) != "str":
            log_exit("CODE.readlines", "ERREUR")
            raise REX_SL(f"readlines: chemin doit etre une string : {path_operand}")
        symbol_table["rexfn"].append("rexsl_str_split")
        path_e = REX_SL_CODE._operand_expr(path_operand)
        list_c = REX_SL_CODE._c_name(dest_raw_name)
        c_line = (
            '{\n'
            f'        FILE* __rexsl_fp = fopen({path_e}, "rb");\n'
            f'        if (__rexsl_fp == NULL) {{ fprintf(stderr, "[REX-SL] erreur : impossible d\'ouvrir %s en lecture\\n", {path_e}); exit(1); }}\n'
            '        fseek(__rexsl_fp, 0, SEEK_END);\n'
            '        long __rexsl_size = ftell(__rexsl_fp);\n'
            f'        if (__rexsl_size < 0) {{ fclose(__rexsl_fp); fprintf(stderr, "[REX-SL] erreur : ftell a echoue sur %s\\n", {path_e}); exit(1); }}\n'
            '        fseek(__rexsl_fp, 0, SEEK_SET);\n'
            '        char* __rexsl_content = malloc((size_t)__rexsl_size + 1);\n'
            '        REXSL_CHECK_ALLOC(__rexsl_content);\n'
            '        fread(__rexsl_content, 1, (size_t)__rexsl_size, __rexsl_fp);\n'
            '        __rexsl_content[__rexsl_size] = \'\\0\';\n'
            '        fclose(__rexsl_fp);\n'
            f'        rexsl_str_split({list_c}, __rexsl_content, "\\n");\n'
            '        free(__rexsl_content);\n'
            '    }'
        )
        log_exit("CODE.readlines", "-> %r", c_line)
        return c_line

    @staticmethod
    def writelines(path_operand, list_operand):
        log_enter("CODE.writelines", "path_operand=%r list_operand=%r", path_operand, list_operand)
        if REX_SL_CODE._operand_type(path_operand) != "str":
            log_exit("CODE.writelines", "ERREUR")
            raise REX_SL(f"writelines: chemin doit etre une string : {path_operand}")
        list_type, list_name = list_operand
        if list_type != "ident" or symbol_table["var"].get(list_name) != "list":
            log_exit("CODE.writelines", "ERREUR")
            raise REX_SL(f"writelines: operande doit etre une liste declaree : {list_operand}")
        symbol_table["rexfn"].append("rexsl_list_join")
        path_e = REX_SL_CODE._operand_expr(path_operand)
        list_c = REX_SL_CODE._c_name(list_name)
        c_line = (
            '{\n'
            f'        char* __rexsl_joined = rexsl_list_join({list_c}, "\\n");\n'
            f'        FILE* __rexsl_fp = fopen({path_e}, "w");\n'
            f'        if (__rexsl_fp == NULL) {{ fprintf(stderr, "[REX-SL] erreur : impossible d\'ouvrir %s en ecriture\\n", {path_e}); exit(1); }}\n'
            '        fprintf(__rexsl_fp, "%s", __rexsl_joined);\n'
            '        fclose(__rexsl_fp);\n'
            '        free(__rexsl_joined);\n'
            '    }'
        )
        log_exit("CODE.writelines", "-> %r", c_line)
        return c_line
    
    @staticmethod
    def scrc(code_token):
        """scrc <str>; injecte le contenu de la string TEL QUEL comme code C brut, sans
        aucune verification. On sort du cadre protege de REX-SL a partir de la : aucune
        garantie de compilation ou de sens n'est plus donnee au-dela de cette ligne.
        ATTENTION : le lexer coupe le source sur ';' AVANT tokenisation -> une string
        scrc contenant un ';' sera tronquee au niveau REX-SL (limitation existante du
        lexer, non corrigee ici)."""
        log_enter("CODE.scrc", "code_token=%r", code_token)
        if code_token[0] != "str":
            log_exit("CODE.scrc", "ERREUR")
            raise REX_SL(f"scrc attend une string litterale de code C : {code_token}")
        c_line = code_token[1]
        log("CODE.scrc", "code C brut injecte : %r", c_line)
        log_exit("CODE.scrc", "-> %r", c_line)
        return c_line

    @staticmethod
    def type_of(destination, operand):
        """type <dest> <op>; ecrit dans <dest> (string) le nom du type REX-SL de <op>
        ('number'/'float'/'bool'/'str'/'list'/'dict'). Reutilise la meme strategie de
        stockage stack/heap que les strings normales (voir CODE.var / reaffectation)."""
        log_enter("CODE.type_of", "destination=%r operand=%r", destination, operand)

        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            log_exit("CODE.type_of", "ERREUR")
            raise REX_SL(f"destination non gere : {destination[1]}")
        if REX_SL_CODE._is_rx(dest_raw_name):
            log_exit("CODE.type_of", "ERREUR")
            raise REX_SL(f"destination RX_ en lecture seule (registre importe) : {dest_raw_name}")

        is_declaration = dest_raw_name not in symbol_table["var"]
        if not is_declaration and dest_raw_name in symbol_table["const_vars"]:
            log_exit("CODE.type_of", "ERREUR")
            raise REX_SL(f"type: modification interdite, {dest_raw_name} est une constante")
        dest_name = REX_SL_CODE._c_name(dest_raw_name)
        type_name = REX_SL_CODE._operand_type(operand)  # peut valoir "none"
        escaped = _escape_c_string(type_name)

        if is_declaration:
            c_line = (
                f'char {dest_name}_buf[{STACK_STR_THRESHOLD}] = "{escaped}";\n'
                f'    char* {dest_name} = {dest_name}_buf;'
            )
            symbol_table["var"][dest_raw_name] = "str"
        elif _heap_is(dest_name) :
            # heap -> jamais de retour sur la pile (meme regle que partout ailleurs) :
            # on libere puis on repointe vers un litteral C statique (jamais free()).
            c_line = f'free({dest_name});\n    {dest_name} = "{escaped}";'
            _heap_unmark(dest_name)
        else:
            c_line = f'strcpy({dest_name}, "{escaped}");'

        log("CODE.type_of", "ligne C generee : %r", c_line)
        log_exit("CODE.type_of", "-> %r", c_line)
        return c_line

    @staticmethod
    def isnone(destination, operand):
        """isnone <dest_bool> <var>; -> teste si <var> (de type none ou pointeur) est NULL.
        <dest_bool> doit etre de type bool (deja declaree ou declaree a la volee).
        Genere : bool SL_dest = (SL_var == NULL);
        Fonctionne sur tout type stocke comme pointeur (none, str heap, list, dict).
        Sur un type scalaire (number/float/bool) toujours faux (jamais NULL en C)."""
        log_enter("CODE.isnone", "destination=%r operand=%r", destination, operand)
        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            log_exit("CODE.isnone", "ERREUR")
            raise REX_SL(f"isnone: destination doit etre un identifiant : {destination}")
        if REX_SL_CODE._is_rx(dest_raw_name):
            log_exit("CODE.isnone", "ERREUR")
            raise REX_SL(f"isnone: destination RX_ en lecture seule : {dest_raw_name}")
        if dest_raw_name in symbol_table["const_vars"]:
            log_exit("CODE.isnone", "ERREUR")
            raise REX_SL(f"isnone: modification interdite, {dest_raw_name} est une constante")

        op_type = REX_SL_CODE._operand_type(operand)
        is_declaration = dest_raw_name not in symbol_table["var"]

        # verifier que la destination est ou sera un bool
        if not is_declaration and symbol_table["var"].get(dest_raw_name) != "bool":
            log_exit("CODE.isnone", "ERREUR")
            raise REX_SL(f"isnone: destination doit etre de type bool : {destination}")

        dest_c = REX_SL_CODE._c_name(dest_raw_name)

        # types "pointer" : on compare directement contre NULL
        POINTER_TYPES = ("none", "str", "list", "dict", "set", "tuple")
        if op_type in POINTER_TYPES:
            if op_type == "none":
                # une variable none est TOUJOURS NULL -> toujours true
                expr = "true"
            else:
                op_expr = REX_SL_CODE._operand_expr(operand)
                expr = f"({op_expr} == NULL)"
        else:
            # scalaires (number/float/bool) -> jamais NULL en C -> toujours false
            expr = "false"

        if is_declaration:
            symbol_table["var"][dest_raw_name] = "bool"
            c_line = f"bool {dest_c} = {expr};"
        else:
            c_line = f"{dest_c} = {expr};"

        log_exit("CODE.isnone", "-> %r", c_line)
        return c_line

    @staticmethod
    def _box_expr(operand):
        """Construit l'expression C RexValue (compound literal) correspondant a un operande."""
        op_type = REX_SL_CODE._operand_type(operand)
        expr = REX_SL_CODE._operand_expr(operand)
        field_by_type = {
            "number": ("REXSL_T_NUMBER", "as_number"),
            "float": ("REXSL_T_FLOAT", "as_float"),
            "bool": ("REXSL_T_BOOL", "as_bool"),
            "str": ("REXSL_T_STR", "as_str"),
        }
        if op_type not in field_by_type:
            raise REX_SL(f"type non stockable dans une liste/dictionnaire : {op_type}")
        tag, field = field_by_type[op_type]
        return f"(RexValue){{ .type = {tag}, .value.{field} = {expr} }}"

    @staticmethod
    def list_append(list_operand, value_operand):
        log_enter("CODE.list_append", "list_operand=%r value_operand=%r", list_operand, value_operand)
        list_type, list_name = list_operand
        coll_kind = REX_SL_CODE._collection_kind(list_name) if list_type == "ident" else None
        if coll_kind not in ("list", "set", "tuple"):
            log_exit("CODE.list_append", "ERREUR")
            raise REX_SL(f"append attend une liste, un set ou un tuple declare : {list_operand}")
        c_name = REX_SL_CODE._c_name(list_name)
        boxed = REX_SL_CODE._box_expr(value_operand)
        symbol_table["rexfn"].append("rexsl_collections")
        if coll_kind == "set":
            # rexsl_set_add garantit l'unicite (pas de doublon)
            symbol_table["rexfn"].append("rexsl_set_add")
            c_line = f"rexsl_set_add({c_name}, {boxed});"
        else:
            # list et tuple utilisent rexsl_list_append (tuple : immuable en theorie,
            # la garantie est laissee a REX.py ; cote C on peut toujours appeler append
            # lors de la construction initiale du tuple)
            c_line = f"rexsl_list_append({c_name}, {boxed});"
        log_exit("CODE.list_append", "-> %r", c_line)
        return c_line

    @staticmethod
    def _collection_dest_field(destination):
        """Verifie que <destination> est une variable primitive deja declaree et
        retourne (nom C, champ RexValue correspondant).
        Retro-compatible : leve REX_SL si la variable n'est pas encore declaree
        (utiliser _collection_dest_field_or_decl pour l'auto-declaration)."""
        dest_type, dest_raw_name = destination
        if dest_type != "ident" or dest_raw_name not in symbol_table["var"]:
            raise REX_SL(f"destination doit etre une variable deja declaree : {destination}")
        dest_kind = symbol_table["var"][dest_raw_name]
        field_by_type = {"number": "as_number", "float": "as_float", "bool": "as_bool", "str": "as_str"}
        if dest_kind not in field_by_type:
            raise REX_SL(f"type de destination non gere : {dest_kind}")
        return REX_SL_CODE._c_name(dest_raw_name), field_by_type[dest_kind]

    @staticmethod
    def _collection_dest_field_or_decl(destination, rexval_expr):
        """Variante etendue de _collection_dest_field :
        - Si la destination est deja declaree comme variable scalaire -> comportement identique
          a _collection_dest_field (assign directe, aucune declaration supplementaire).
        - Si la destination n'est PAS encore declaree -> on declare automatiquement une nouvelle
          variable locale C de type deduit du RexValue boxe au runtime.
          Retourne (pre_code, assign_code) :
            pre_code   : code C a emettre AVANT l'assignation (peut etre vide "")
            assign_code: code C realisant l'assignation effective.
        Le type REX-SL de la variable est enregistre dans symbol_table["var"] si auto-declare.
        Note : quand la destination n'est pas encore declaree, le type n'est pas connu a la
        compilation (il depend du RexValue runtime) -> on genere un bloc avec switch sur .type
        qui declare la variable dans le scope englobant via un pointeur union."""
        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            raise REX_SL(f"destination doit etre un identifiant : {destination}")

        if dest_raw_name in symbol_table["var"] and dest_raw_name in symbol_table["const_vars"]:
            raise REX_SL(f"get: modification interdite, {dest_raw_name} est une constante")

        field_by_type = {"number": "as_number", "float": "as_float", "bool": "as_bool", "str": "as_str"}

        if dest_raw_name in symbol_table["var"]:
            # Variable deja declaree : assignation directe (comportement classique)
            dest_kind = symbol_table["var"][dest_raw_name]
            if dest_kind not in field_by_type:
                raise REX_SL(f"type de destination non gere : {dest_kind}")
            dest_c = REX_SL_CODE._c_name(dest_raw_name)
            field = field_by_type[dest_kind]
            tag_by_kind = {"number": "REXSL_T_NUMBER", "float": "REXSL_T_FLOAT",
                           "bool": "REXSL_T_BOOL", "str": "REXSL_T_STR"}
            pre = (
                f'RexValue __rexsl_gv = {rexval_expr};\n'
                f'    if (__rexsl_gv.type != {tag_by_kind[dest_kind]}) {{'
                f' fprintf(stderr, "[REX-SL] erreur : type incompatible dans get\\n"); exit(1); }}'
            )
            assign = f'{dest_c} = __rexsl_gv.value.{field};'
            return pre, assign
        else:
            # Variable pas encore declaree : on infere le type depuis le RexValue au runtime.
            # On declare la variable via un type "souple" : on utilise un union C local
            # mais le type REX-SL enregistre sera "auto" (non connu statiquement).
            # Pour permettre un usage compile-time correct dans les opcodes suivants,
            # on exige que le type soit fourni via la syntaxe etendue de get :
            #   get <list> <type> <dest> <idx>
            # Si on arrive ici sans type connu, on genere une erreur explicite invitant
            # a pre-declarer la variable.
            raise REX_SL(
                f"get/pop: la destination '{dest_raw_name}' n'est pas encore declaree. "
                f"Soit declarez-la d'abord via 'var <type> {dest_raw_name};', "
                f"soit utilisez la syntaxe etendue 'get <collection> <type> <dest> <idx>;' "
                f"pour auto-declarer avec type explicite."
            )

    @staticmethod
    def list_get(list_operand, destination, idx_operand, hint_type=None):
        """get <list> <dest> <idx>;              -- destination deja declaree (comportement classique)
           get <list> <type> <dest> <idx>;       -- auto-declaration de <dest> avec le type explicite.
        hint_type : token de type optionnel fourni par la syntaxe etendue (5 tokens)."""
        log_enter("CODE.list_get", "list_operand=%r destination=%r idx_operand=%r hint_type=%r",
                  list_operand, destination, idx_operand, hint_type)
        list_type, list_name = list_operand
        if list_type != "ident" or REX_SL_CODE._collection_kind(list_name) not in ("list", "set", "tuple"):
            log_exit("CODE.list_get", "ERREUR")
            raise REX_SL(f"get attend une liste, un set ou un tuple declare : {list_operand}")
        if (destination[0] == "ident" and destination[1] in symbol_table["var"]
                and destination[1] in symbol_table["const_vars"]):
            log_exit("CODE.list_get", "ERREUR")
            raise REX_SL(f"get: modification interdite, {destination[1]} est une constante")
        if idx_operand[0] == "number" and idx_operand[1] < 0:
            log_exit("CODE.list_get", "ERREUR")
            raise REX_SL(f"get: index negatif connu a la compilation : {idx_operand[1]}")

        symbol_table["rexfn"].append("rexsl_collections")
        list_c_name = REX_SL_CODE._c_name(list_name)
        idx_expr = REX_SL_CODE._operand_expr(idx_operand)
        dest_raw = destination[1]
        rexval_expr = f"rexsl_list_get({list_c_name}, {idx_expr})"

        # syntaxe etendue : hint_type fourni -> auto-declaration si besoin
        if hint_type is not None and dest_raw not in symbol_table["var"]:
            if hint_type[0] != "ident" or hint_type[1] not in ("number", "float", "bool", "str"):
                raise REX_SL(f"get: type hint invalide : {hint_type}")
            kind = hint_type[1]
            symbol_table["var"][dest_raw] = kind
            c_type_map = {"number": "int", "float": "float", "bool": "bool", "str": "char*"}
            field_map = {"number": "as_number", "float": "as_float", "bool": "as_bool", "str": "as_str"}
            tag_map = {"number": "REXSL_T_NUMBER", "float": "REXSL_T_FLOAT",
                       "bool": "REXSL_T_BOOL", "str": "REXSL_T_STR"}
            dest_c = REX_SL_CODE._c_name(dest_raw)
            field = field_map[kind]
            # pas d'accolades englobantes : la variable typee declaree ici doit rester
            # visible dans la portee du bloc appelant (voir §3, bug de portee corrige --
            # un '{ ... }' autour de la declaration la faisait disparaitre a la sortie du
            # bloc). Le temporaire RexValue est nomme d'apres la destination pour eviter
            # toute collision si plusieurs 'get' auto-declarants coexistent dans le meme
            # scope C (chacun genere son propre __rexsl_gv_<dest>).
            gv_tmp = f"__rexsl_gv_{dest_c}"
            if kind == "str":
                # BUGFIX (double-free) : as_str ici est un pointeur EMPRUNTE a la
                # RexValue interne de la liste (litteral C si l'element vient d'un
                # literal, ou memoire dont la liste reste proprietaire sinon) --
                # ce n'est jamais une allocation dont <dest_c> devient proprietaire.
                # Ne PAS _heap_mark() ce temporaire (sinon double free / free() sur
                # un pointeur non malloc()-e a la fin du bloc). On garde neanmoins
                # le hoist a NULL en tete de bloc (coherence avec le hoisting
                # general, evite toute lecture d'un pointeur indetermine si un
                # 'go' saute par-dessus cette ligne), simplement exclu de heap_vars.
                if _can_hoist():
                    symbol_table["heap_str_decls"][-1].add(dest_c)
                    decl_prefix = ""
                else:
                    decl_prefix = f"{c_type_map[kind]} "
            else:
                decl_prefix = f"{c_type_map[kind]} "
            c_line = (
                f'RexValue {gv_tmp} = {rexval_expr};\n'
                f'    if ({gv_tmp}.type != {tag_map[kind]}) {{'
                f' fprintf(stderr, "[REX-SL] erreur : type incompatible dans get (liste)\\n"); exit(1); }}\n'
                f'    {decl_prefix}{dest_c} = {gv_tmp}.value.{field};'
            )
            log_exit("CODE.list_get", "-> %r (auto-decl %s, non heap-tracke)", c_line, kind)
            return c_line

        # comportement classique : appel a _collection_dest_field_or_decl
        pre, assign = REX_SL_CODE._collection_dest_field_or_decl(destination, rexval_expr)
        c_line = f'{{ {pre}\n    {assign} }}'
        log_exit("CODE.list_get", "-> %r", c_line)
        return c_line

    @staticmethod
    def list_pop(list_operand, destination=None, idx_operand=None):
        log_enter("CODE.list_pop", "list_operand=%r destination=%r idx_operand=%r",
                  list_operand, destination, idx_operand)
        list_type, list_name = list_operand
        if list_type != "ident" or REX_SL_CODE._collection_kind(list_name) not in ("list", "set", "tuple"):
            log_exit("CODE.list_pop", "ERREUR")
            raise REX_SL(f"pop attend une liste, un set ou un tuple declare : {list_operand}")
        if idx_operand and idx_operand[0] == "number" and idx_operand[1] < 0:
            log_exit("CODE.list_pop", "ERREUR")
            raise REX_SL(f"pop: index negatif connu a la compilation : {idx_operand[1]}")
        list_c_name = REX_SL_CODE._c_name(list_name)
        idx_expr = REX_SL_CODE._operand_expr(idx_operand) if idx_operand else "-1"

        if destination is None:
            c_line = f"rexsl_list_pop({list_c_name}, {idx_expr});"
            log_exit("CODE.list_pop", "-> %r", c_line)
            return c_line

        if (destination[0] == "ident" and destination[1] in symbol_table["var"]
                and destination[1] in symbol_table["const_vars"]):
            log_exit("CODE.list_pop", "ERREUR")
            raise REX_SL(f"pop: modification interdite, {destination[1]} est une constante")

        rexval_expr = f"rexsl_list_pop({list_c_name}, {idx_expr})"
        pre, assign = REX_SL_CODE._collection_dest_field_or_decl(destination, rexval_expr)
        c_line = f'{{ {pre}\n    {assign} }}'
        log_exit("CODE.list_pop", "-> %r", c_line)
        return c_line

    @staticmethod
    def dict_set(dict_operand, key_operand, value_operand):
        log_enter("CODE.dict_set", "dict_operand=%r key_operand=%r value_operand=%r",
                  dict_operand, key_operand, value_operand)
        dict_type, dict_name = dict_operand
        if dict_type != "ident" or REX_SL_CODE._collection_kind(dict_name) != "dict":
            log_exit("CODE.dict_set", "ERREUR")
            raise REX_SL(f"set attend un dictionnaire declare (var dict ...) : {dict_operand}")
        if REX_SL_CODE._operand_type(key_operand) != "str":
            log_exit("CODE.dict_set", "ERREUR")
            raise REX_SL(f"set: la cle d'un dictionnaire doit etre une string : {key_operand}")
        dict_c_name = REX_SL_CODE._c_name(dict_name)
        key_expr = REX_SL_CODE._operand_expr(key_operand)
        boxed = REX_SL_CODE._box_expr(value_operand)
        c_line = f"rexsl_dict_set({dict_c_name}, {key_expr}, {boxed});"
        log_exit("CODE.dict_set", "-> %r", c_line)
        return c_line

    @staticmethod
    def dict_get(dict_operand, destination, key_operand):
        log_enter("CODE.dict_get", "dict_operand=%r destination=%r key_operand=%r",
                  dict_operand, destination, key_operand)
        dict_type, dict_name = dict_operand
        if dict_type != "ident" or REX_SL_CODE._collection_kind(dict_name) != "dict":
            log_exit("CODE.dict_get", "ERREUR")
            raise REX_SL(f"get attend un dictionnaire declare (var dict ...) : {dict_operand}")
        if REX_SL_CODE._operand_type(key_operand) != "str":
            log_exit("CODE.dict_get", "ERREUR")
            raise REX_SL(f"get: la cle d'un dictionnaire doit etre une string : {key_operand}")
        if (destination[0] == "ident" and destination[1] in symbol_table["var"]
                and destination[1] in symbol_table["const_vars"]):
            log_exit("CODE.dict_get", "ERREUR")
            raise REX_SL(f"get: modification interdite, {destination[1]} est une constante")
        dict_c_name = REX_SL_CODE._c_name(dict_name)
        key_expr = REX_SL_CODE._operand_expr(key_operand)
        rexval_expr = f"rexsl_dict_get({dict_c_name}, {key_expr})"
        pre, assign = REX_SL_CODE._collection_dest_field_or_decl(destination, rexval_expr)
        c_line = f'{{ {pre}\n    {assign} }}'
        log_exit("CODE.dict_get", "-> %r", c_line)
        return c_line

    @staticmethod
    def dict_get_hinted(dict_operand, destination, key_operand, hint_type):
        """get <dict> <type> <dest> <cle>; -- forme etendue (5 tokens) de dict_get :
        auto-declare <dest> avec le type explicite fourni si elle n'existe pas
        encore, sinon delegue au comportement classique de dict_get."""
        log_enter("CODE.dict_get_hinted", "dict_operand=%r destination=%r key_operand=%r hint_type=%r",
                  dict_operand, destination, key_operand, hint_type)
        dict_type, dict_name = dict_operand
        if dict_type != "ident" or REX_SL_CODE._collection_kind(dict_name) != "dict":
            log_exit("CODE.dict_get_hinted", "ERREUR")
            raise REX_SL(f"get attend un dictionnaire declare (var dict ...) : {dict_operand}")
        if REX_SL_CODE._operand_type(key_operand) != "str":
            log_exit("CODE.dict_get_hinted", "ERREUR")
            raise REX_SL(f"get: la cle d'un dictionnaire doit etre une string : {key_operand}")
        if destination[0] != "ident":
            log_exit("CODE.dict_get_hinted", "ERREUR")
            raise REX_SL(f"get: destination invalide : {destination}")
        dest_raw = destination[1]
        if dest_raw in symbol_table["var"] and dest_raw in symbol_table["const_vars"]:
            log_exit("CODE.dict_get_hinted", "ERREUR")
            raise REX_SL(f"get: modification interdite, {dest_raw} est une constante")

        dict_c_name = REX_SL_CODE._c_name(dict_name)
        key_expr = REX_SL_CODE._operand_expr(key_operand)
        rexval_expr = f"rexsl_dict_get({dict_c_name}, {key_expr})"

        if dest_raw not in symbol_table["var"]:
            if hint_type[0] != "ident" or hint_type[1] not in ("number", "float", "bool", "str"):
                log_exit("CODE.dict_get_hinted", "ERREUR")
                raise REX_SL(f"get: type hint invalide : {hint_type}")
            kind = hint_type[1]
            symbol_table["var"][dest_raw] = kind
            c_type_map = {"number": "int", "float": "float", "bool": "bool", "str": "char*"}
            field_map = {"number": "as_number", "float": "as_float", "bool": "as_bool", "str": "as_str"}
            tag_map = {"number": "REXSL_T_NUMBER", "float": "REXSL_T_FLOAT",
                       "bool": "REXSL_T_BOOL", "str": "REXSL_T_STR"}
            dest_c = REX_SL_CODE._c_name(dest_raw)
            field = field_map[kind]
            # meme correction de portee que list_get (voir §3) : pas d'accolades
            # englobantes, temporaire nomme d'apres la destination.
            gv_tmp = f"__rexsl_gv_{dest_c}"
            if kind == "str":
                # BUGFIX (double-free) : meme raisonnement que list_get -- as_str
                # est ici un pointeur emprunte a la RexValue stockee dans le dict
                # (rexsl_dict_set() copie la struct RexValue telle quelle ; si sa
                # valeur venait d'un literal C, as_str pointe vers ce literal ;
                # sinon la memoire reste sous la propriete du dict). <dest_c> n'en
                # est jamais proprietaire -> pas de _heap_mark ici (evite le
                # double free / free() sur pointeur non malloc()-e observe avec
                # les temporaires generes par REX.py, ex. SL___rx_t92..t95, en fin
                # de main() apres rexsl_dict_free(SL_d)). Le hoist a NULL reste en
                # place pour la coherence generale du hoisting, juste exclu de
                # heap_vars (donc jamais free()).
                if _can_hoist():
                    symbol_table["heap_str_decls"][-1].add(dest_c)
                    decl_prefix = ""
                else:
                    decl_prefix = f"{c_type_map[kind]} "
            else:
                decl_prefix = f"{c_type_map[kind]} "
            c_line = (
                f'RexValue {gv_tmp} = {rexval_expr};\n'
                f'    if ({gv_tmp}.type != {tag_map[kind]}) {{'
                f' fprintf(stderr, "[REX-SL] erreur : type incompatible dans get (dict)\\n"); exit(1); }}\n'
                f'    {decl_prefix}{dest_c} = {gv_tmp}.value.{field};'
            )
            log_exit("CODE.dict_get_hinted", "-> %r (auto-decl %s, non heap-tracke)", c_line, kind)
            return c_line

        # destination deja declaree : comportement classique (delegue a dict_get)
        result = REX_SL_CODE.dict_get(dict_operand, destination, key_operand)
        log_exit("CODE.dict_get_hinted", "-> %r", result)
        return result

    @staticmethod
    def _assign_heap_str(dest_raw_name, c_expr):
        """Affecte une expression C retournant un char* malloc'e a <dest_raw_name>,
        en liberant l'ancienne valeur si necessaire (declaration, promotion
        stack->heap, ou reaffectation heap->heap)."""
        if REX_SL_CODE._is_rx(dest_raw_name):
            raise REX_SL(f"destination RX_ en lecture seule (registre importe) : {dest_raw_name}")
        is_declaration = dest_raw_name not in symbol_table["var"]
        if not is_declaration and dest_raw_name in symbol_table["const_vars"]:
            raise REX_SL(f"modification interdite : {dest_raw_name} est une constante")
        dest_name = REX_SL_CODE._c_name(dest_raw_name)
        was_heap = _heap_is(dest_name)

        if is_declaration:
            if _can_hoist():
                symbol_table["heap_str_decls"][-1].add(dest_name)
                c_line = f'{dest_name} = {c_expr};'
            else:
                c_line = f'char* {dest_name} = {c_expr};'
            symbol_table["var"][dest_raw_name] = "str"
        elif was_heap:
            c_line = f'free({dest_name});\n    {dest_name} = {c_expr};'
        else:
            c_line = f'{dest_name} = {c_expr};'

        _heap_mark(dest_name)
        return c_line

    @staticmethod
    def input_line(destination):
        """input <dest>; lit une ligne sur stdin dans <dest> (deja declaree)."""
        log_enter("CODE.input_line", "destination=%r", destination)
        dest_type, dest_raw_name = destination
        if dest_type != "ident" or dest_raw_name not in symbol_table["var"]:
            log_exit("CODE.input_line", "ERREUR")
            raise REX_SL(f"input: destination doit etre une variable deja declaree : {destination}")
        if dest_raw_name in symbol_table["const_vars"]:
            log_exit("CODE.input_line", "ERREUR")
            raise REX_SL(f"input: modification interdite, {dest_raw_name} est une constante")
        dest_kind = symbol_table["var"][dest_raw_name]
        dest_name = REX_SL_CODE._c_name(dest_raw_name)

        if dest_kind == "str":
            symbol_table["rexfn"].append("rexsl_str_alloc")
            was_heap = _heap_is(dest_name)
            free_old = f'free({dest_name});\n        ' if was_heap else ""
            _heap_mark(dest_name)
            c_line = (
                '{\n'
                '        char __rexsl_input_buf[1024] = {0};\n'
                '        if (fgets(__rexsl_input_buf, sizeof(__rexsl_input_buf), stdin)) {\n'
                '            __rexsl_input_buf[strcspn(__rexsl_input_buf, "\\n")] = \'\\0\';\n'
                '        }\n'
                f'        {free_old}{dest_name} = rexsl_str_alloc(__rexsl_input_buf);\n'
                '    }'
            )
        elif dest_kind == "number":
            c_line = (
                f'if (scanf("%d", &{dest_name}) != 1) {{ {dest_name} = 0; }}\n'
                '    { int __rexsl_c; while ((__rexsl_c = getchar()) != \'\\n\' && __rexsl_c != EOF); }'
            )
        elif dest_kind == "float":
            c_line = (
                f'if (scanf("%f", &{dest_name}) != 1) {{ {dest_name} = 0; }}\n'
                '    { int __rexsl_c; while ((__rexsl_c = getchar()) != \'\\n\' && __rexsl_c != EOF); }'
            )
        elif dest_kind == "bool":
            c_line = (
                '{ char __rexsl_buf[8] = {0}; if (fgets(__rexsl_buf, sizeof(__rexsl_buf), stdin)) {\n'
                f'        {dest_name} = (__rexsl_buf[0] == \'t\' || __rexsl_buf[0] == \'1\');\n'
                '    } }'
            )
        else:
            log_exit("CODE.input_line", "ERREUR")
            raise REX_SL(f"input: type de destination non gere : {dest_kind}")

        log_exit("CODE.input_line", "-> %r", c_line)
        return c_line

    @staticmethod
    def write_file(path_operand, value_operand):
        """write <path> <valeur>; ouvre <path> en ecriture (mode "w", ecrase) et y
        ecrit <valeur> convertie en texte."""
        log_enter("CODE.write_file", "path_operand=%r value_operand=%r", path_operand, value_operand)
        if REX_SL_CODE._operand_type(path_operand) != "str":
            log_exit("CODE.write_file", "ERREUR")
            raise REX_SL(f"write: le chemin doit etre une string : {path_operand}")
        path_expr = REX_SL_CODE._operand_expr(path_operand)

        value_type = REX_SL_CODE._operand_type(value_operand)
        value_expr = REX_SL_CODE._operand_expr(value_operand)
        format_by_type = {"number": "%d", "float": "%g", "str": "%s"}

        if value_type == "bool":
            value_expr = f'({value_expr} ? "true" : "false")'
            value_type = "str"
        if value_type not in format_by_type:
            log_exit("CODE.write_file", "ERREUR")
            raise REX_SL(f"write: type non gere : {value_operand}")

        c_line = (
            '{\n'
            f'        FILE* __rexsl_fp = fopen({path_expr}, "w");\n'
            f'        if (__rexsl_fp == NULL) {{ fprintf(stderr, "[REX-SL] erreur : impossible d\'ouvrir %s en ecriture\\n", {path_expr}); exit(1); }}\n'
            f'        fprintf(__rexsl_fp, "{format_by_type[value_type]}", {value_expr});\n'
            '        fclose(__rexsl_fp);\n'
            '    }'
        )
        log_exit("CODE.write_file", "-> %r", c_line)
        return c_line

    @staticmethod
    def read_file(path_operand, destination):
        """read <path> <dest>; lit le contenu ENTIER du fichier <path> dans <dest>
        (str deja declaree). Toujours alloue sur le tas (fread) et promeut <dest>
        vers heap_vars si besoin (transfert stack -> heap uniquement, jamais l'inverse)."""
        log_enter("CODE.read_file", "path_operand=%r destination=%r", path_operand, destination)
        if REX_SL_CODE._operand_type(path_operand) != "str":
            log_exit("CODE.read_file", "ERREUR")
            raise REX_SL(f"read: le chemin doit etre une string : {path_operand}")
        path_expr = REX_SL_CODE._operand_expr(path_operand)

        dest_type, dest_raw_name = destination
        if dest_type != "ident" or symbol_table["var"].get(dest_raw_name) != "str":
            log_exit("CODE.read_file", "ERREUR")
            raise REX_SL(f"read: destination doit etre une variable str deja declaree : {destination}")
        if dest_raw_name in symbol_table["const_vars"]:
            log_exit("CODE.read_file", "ERREUR")
            raise REX_SL(f"read: modification interdite, {dest_raw_name} est une constante")

        dest_name = REX_SL_CODE._c_name(dest_raw_name)
        was_heap = _heap_is(dest_name)
        _heap_mark(dest_name)
        free_old = f'free({dest_name});\n        ' if was_heap else ""

        c_line = (
            '{\n'
            f'        FILE* __rexsl_fp = fopen({path_expr}, "rb");\n'
            f'        if (__rexsl_fp == NULL) {{ fprintf(stderr, "[REX-SL] erreur : impossible d\'ouvrir %s en lecture\\n", {path_expr}); exit(1); }}\n'
            '        fseek(__rexsl_fp, 0, SEEK_END);\n'
            '        long __rexsl_size = ftell(__rexsl_fp);\n'
            f'        if (__rexsl_size < 0) {{ fclose(__rexsl_fp); fprintf(stderr, "[REX-SL] erreur : ftell a echoue sur %s\\n", {path_expr}); exit(1); }}\n'
            '        fseek(__rexsl_fp, 0, SEEK_SET);\n'
            '        char* __rexsl_content = malloc((size_t)__rexsl_size + 1);\n'
            '        REXSL_CHECK_ALLOC(__rexsl_content);\n'
            '        fread(__rexsl_content, 1, (size_t)__rexsl_size, __rexsl_fp);\n'
            '        __rexsl_content[__rexsl_size] = \'\\0\';\n'
            '        fclose(__rexsl_fp);\n'
            f'        {free_old}{dest_name} = __rexsl_content;\n'
            '    }'
        )
        log_exit("CODE.read_file", "-> %r", c_line)
        return c_line

    @staticmethod
    def show(value_token, line_ending):
        """
        Genere la ligne C correspondant a un show/showln.
        value_token : tuple (type, valeur) du token affiche, ex ("number", 42)
        line_ending : "\\n" pour showln, "" pour show
        """
        log_enter("CODE.show", "value_token=%r line_ending=%r", value_token, line_ending)
        token_type, token_value = value_token

        if token_type == "none":
            # litteral none -> affiche "None" comme Python
            c_line = f'printf("%s{line_ending}", "None");'
            log("CODE.show", "type=none -> ligne C generee : %r", c_line)

        elif token_type == "str":
            escaped_value = _escape_c_string(token_value)
            # IMPORTANT : la valeur ne doit jamais servir de FORMAT a printf
            # (sinon un show "%s%s%s"; provoquerait un format-string bug/crash).
            # On la passe donc comme argument via %s, jamais comme format brut.
            c_line = f'printf("%s{line_ending}", "{escaped_value}");'
            log("CODE.show", "type=str -> ligne C generee (echappee) : %r", c_line)

        elif token_type == "number":
            c_line = f'printf("%d{line_ending}", {token_value});'
            log("CODE.show", "type=number -> ligne C generee : %r", c_line)

        elif token_type == "float":
            # %g supprime les zeros inutiles (3.14 au lieu de 3.140000)
            c_line = f'printf("%g{line_ending}", {token_value});'
            log("CODE.show", "type=float -> ligne C generee (%%g) : %r", c_line)

        elif token_type == "bool":
            # traduction de la valeur python True/False vers le litteral C true/false
            c_bool_literal = "true" if token_value else "false"
            log("CODE.show", "type=bool -> valeur python=%r convertie en litteral C=%r",
                token_value, c_bool_literal, verbose=True)
            c_line = f'printf("%s{line_ending}", {c_bool_literal} ? "true" : "false");'
            log("CODE.show", "type=bool -> ligne C generee : %r", c_line)
            
        elif token_type == "ident":
            registry = REX_SL_CODE._registry_for(token_value)
            if token_value not in registry:
                log("CODE.show", "type=ident -> variable inconnue -> exception REX_SL")
                log_exit("CODE.show", "ERREUR")
                raise REX_SL(f"variable {REX_SL_CODE._registry_label(token_value)} inconnue : {token_value}")
            variable_type = registry[token_value]
            c_name = REX_SL_CODE._c_name(token_value)

            if variable_type == "none":
                # variable none -> toujours NULL -> affiche "None"
                c_line = f'printf("%s{line_ending}", "None");'
            elif variable_type == "number":
                c_line = f'printf("%d{line_ending}", {c_name});'
            elif variable_type == "float":
                c_line = f'printf("%g{line_ending}", {c_name});'
            elif variable_type == "bool":
                c_line = f'printf("%s{line_ending}", {c_name} ? "true" : "false");'
            elif variable_type == "list":
                # opcode natif rexsl_show_list : elimine la boucle d'impression manuelle
                newline_flag = "1" if line_ending else "0"
                symbol_table["rexfn"].append("rexsl_collections")
                symbol_table["rexfn"].append("rexsl_show_list")
                c_line = f'rexsl_show_list({c_name}, {newline_flag});'
            elif variable_type == "dict":
                newline_flag = "1" if line_ending else "0"
                symbol_table["rexfn"].append("rexsl_collections")
                symbol_table["rexfn"].append("rexsl_show_dict")
                c_line = f'rexsl_show_dict({c_name}, {newline_flag});'
            elif variable_type == "set":
                newline_flag = "1" if line_ending else "0"
                symbol_table["rexfn"].append("rexsl_collections")
                symbol_table["rexfn"].append("rexsl_show_set")
                c_line = f'rexsl_show_set({c_name}, {newline_flag});'
            elif variable_type == "tuple":
                newline_flag = "1" if line_ending else "0"
                symbol_table["rexfn"].append("rexsl_collections")
                symbol_table["rexfn"].append("rexsl_show_tuple")
                c_line = f'rexsl_show_tuple({c_name}, {newline_flag});'
            else:
                c_line = f'printf("%s{line_ending}", {c_name});'
            log("CODE.show", "type=ident -> ligne C generee : %r", c_line)
            
        else:
            log("CODE.show", "type non gere -> exception REX_SL")
            log_exit("CODE.show", "ERREUR")
            raise REX_SL(f"show non gere : {value_token}")

        log_exit("CODE.show", "-> %r", c_line)
        return c_line

    @staticmethod
    def add(destination, operand_a, operand_b):
        log_enter("CODE.add", "destination=%r operand_a=%r operand_b=%r",
                destination, operand_a, operand_b)

        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            log_exit("CODE.add", "ERREUR")
            raise REX_SL(f"destination non gere : {destination[1]}")
        if REX_SL_CODE._is_rx(dest_raw_name):
            log_exit("CODE.add", "ERREUR")
            raise REX_SL(f"destination RX_ en lecture seule (registre importe) : {dest_raw_name}")

        dest_name = REX_SL_CODE._c_name(dest_raw_name)
        is_declaration = dest_raw_name not in symbol_table["var"]
        if not is_declaration and dest_raw_name in symbol_table["const_vars"]:
            log_exit("CODE.add", "ERREUR")
            raise REX_SL(f"modification interdite : {dest_raw_name} est une constante")
        type_a = REX_SL_CODE._operand_type(operand_a)
        type_b = REX_SL_CODE._operand_type(operand_b)

        if type_a == "bool" or type_b == "bool":
            log_exit("CODE.add", "ERREUR")
            raise REX_SL(f"operande bool non gere : {destination[1]}")

        operation = "concat" if type_a == "str" else "classic"

        valid_b_types = ("number", "float") if operation == "classic" else ("str",)
        if type_b not in valid_b_types:
            log_exit("CODE.add", "ERREUR")
            raise REX_SL(f"operande different : {destination[1]}")

        if operation == "concat":
            expr_a = REX_SL_CODE._operand_expr(operand_a)
            expr_b = REX_SL_CODE._operand_expr(operand_b)
            if is_declaration:
                if _can_hoist():
                    symbol_table["heap_str_decls"][-1].add(dest_name)
                    decl_prefix = ""
                else:
                    decl_prefix = "char* "
                c_line = (
                    f'{decl_prefix}{dest_name} = malloc(strlen({expr_a}) + strlen({expr_b}) + 1);\n'
                    f'    REXSL_CHECK_ALLOC({dest_name});\n'
                    f'    strcpy({dest_name}, {expr_a});\n'
                    f'    strcat({dest_name}, {expr_b});'
                )
                symbol_table["var"][dest_raw_name] = "str"
            else:
                # dest deja declaree : on ne peut PAS supposer qu'elle contient deja
                # operand_a, et son buffer courant peut etre sur la pile (jamais
                # malloc'e) -> realloc() dessus est un comportement indefini.
                # On reconstruit toujours une nouvelle chaine fraiche sur le tas.
                was_heap = _heap_is(dest_name)
                free_old = f'free({dest_name});\n    ' if was_heap else ""
                c_line = (
                    f'{free_old}{dest_name} = malloc(strlen({expr_a}) + strlen({expr_b}) + 1);\n'
                    f'    REXSL_CHECK_ALLOC({dest_name});\n'
                    f'    strcpy({dest_name}, {expr_a});\n'
                    f'    strcat({dest_name}, {expr_b});'
                )
            _heap_mark(dest_name)

        else:
            is_float_result = "float" in (type_a, type_b)
            c_type = "float" if is_float_result else "int"
            var_kind = "float" if is_float_result else "number"
            expr_a = REX_SL_CODE._operand_expr(operand_a)
            expr_b = REX_SL_CODE._operand_expr(operand_b)
            if is_declaration:
                c_line = f"{c_type} {dest_name} = {expr_a} + {expr_b};"
                symbol_table["var"][dest_raw_name] = var_kind
            else:
                c_line = f"{dest_name} = {expr_a} + {expr_b};"

        log("CODE.add", "ligne C generee : %r", c_line)
        log_exit("CODE.add", "-> %r", c_line)
        return c_line

    @staticmethod
    def sub(destination, operand_a, operand_b):
        log_enter("CODE.sub", "destination=%r operand_a=%r operand_b=%r",
                destination, operand_a, operand_b)

        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            log_exit("CODE.sub", "ERREUR")
            raise REX_SL(f"destination non gere : {destination[1]}")
        if REX_SL_CODE._is_rx(dest_raw_name):
            log_exit("CODE.sub", "ERREUR")
            raise REX_SL(f"destination RX_ en lecture seule (registre importe) : {dest_raw_name}")

        dest_name = REX_SL_CODE._c_name(dest_raw_name)
        is_declaration = dest_raw_name not in symbol_table["var"]
        if not is_declaration and dest_raw_name in symbol_table["const_vars"]:
            log_exit("CODE.sub", "ERREUR")
            raise REX_SL(f"modification interdite : {dest_raw_name} est une constante")
        type_a = REX_SL_CODE._operand_type(operand_a)
        type_b = REX_SL_CODE._operand_type(operand_b)

        if type_a == "bool" or type_b == "bool":
            log_exit("CODE.sub", "ERREUR")
            raise REX_SL(f"operande bool non gere : {destination[1]}")

        if type_a == "str":
            # sub sur des strings = "remove all" (equivalent de .replace(pattern, ""))
            if type_b != "str":
                log_exit("CODE.sub", "ERREUR")
                raise REX_SL(f"operande different : {destination[1]}")

            expr_a = REX_SL_CODE._operand_expr(operand_a)
            expr_b = REX_SL_CODE._operand_expr(operand_b)
            symbol_table["rexfn"].append("rexsl_str_remove_all")

            if is_declaration:
                if _can_hoist():
                    symbol_table["heap_str_decls"][-1].add(dest_name)
                    c_line = f"{dest_name} = rexsl_str_remove_all({expr_a}, {expr_b});"
                else:
                    c_line = f"char* {dest_name} = rexsl_str_remove_all({expr_a}, {expr_b});"
                symbol_table["var"][dest_raw_name] = "str"
            else:
                # meme piege que add() : dest_name peut deja contenir une valeur
                # (stack ou heap) qui n'a rien a voir avec operand_a -> il faut
                # TOUJOURS repartir de expr_a, jamais de l'ancienne valeur de dest.
                was_heap = _heap_is(dest_name)
                free_old = f'free({dest_name});\n    ' if was_heap else ""
                c_line = f"{free_old}{dest_name} = rexsl_str_remove_all({expr_a}, {expr_b});"
            _heap_mark(dest_name)

        else:
            if type_b == "str":
                log_exit("CODE.sub", "ERREUR")
                raise REX_SL(f"operande different : {destination[1]}")

            is_float_result = "float" in (type_a, type_b)
            c_type = "float" if is_float_result else "int"
            var_kind = "float" if is_float_result else "number"
            expr_a = REX_SL_CODE._operand_expr(operand_a)
            expr_b = REX_SL_CODE._operand_expr(operand_b)

            if is_declaration:
                c_line = f"{c_type} {dest_name} = {expr_a} - {expr_b};"
                symbol_table["var"][dest_raw_name] = var_kind
            else:
                c_line = f"{dest_name} = {expr_a} - {expr_b};"

        log("CODE.sub", "ligne C generee : %r", c_line)
        log_exit("CODE.sub", "-> %r", c_line)
        return c_line

    @staticmethod
    def mul(destination, operand_a, operand_b):
        log_enter("CODE.mul", "destination=%r operand_a=%r operand_b=%r",
                destination, operand_a, operand_b)

        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            log_exit("CODE.mul", "ERREUR")
            raise REX_SL(f"destination non gere : {destination[1]}")
        if REX_SL_CODE._is_rx(dest_raw_name):
            log_exit("CODE.mul", "ERREUR")
            raise REX_SL(f"destination RX_ en lecture seule (registre importe) : {dest_raw_name}")

        dest_name = REX_SL_CODE._c_name(dest_raw_name)
        is_declaration = dest_raw_name not in symbol_table["var"]
        if not is_declaration and dest_raw_name in symbol_table["const_vars"]:
            log_exit("CODE.mul", "ERREUR")
            raise REX_SL(f"modification interdite : {dest_raw_name} est une constante")
        type_a = REX_SL_CODE._operand_type(operand_a)
        type_b = REX_SL_CODE._operand_type(operand_b)

        if type_a == "bool" or type_b == "bool":
            log_exit("CODE.mul", "ERREUR")
            raise REX_SL(f"operande bool non gere : {destination[1]}")

        # ---- cas repetition : str * number (dans les deux ordres) ----
        if type_a == "str" and type_b == "number":
            str_operand, count_operand = operand_a, operand_b
        elif type_b == "str" and type_a == "number":
            str_operand, count_operand = operand_b, operand_a
        elif type_a == "str" or type_b == "str":
            # str * float ou str * str -> pas de sens
            log_exit("CODE.mul", "ERREUR")
            raise REX_SL(f"multiplication non geree sur ce type : {destination[1]}")
        else:
            str_operand = None
            count_operand = 0, 0

        if str_operand is not None:
            if count_operand[0] == "number" and count_operand[1] < 0:
                log_exit("CODE.mul", "ERREUR")
                raise REX_SL(f"repetition negative non geree : {destination[1]}")

            if str_operand[0] == "str" and count_operand[0] == "number":
                # les deux connus a la compilation -> repetition faite en Python, zero malloc
                repeated = str_operand[1] * count_operand[1]
                escaped = _escape_c_string(repeated)
                if is_declaration:
                    c_line = f'char* {dest_name} = "{escaped}";'
                    symbol_table["var"][dest_raw_name] = "str"
                elif _heap_is(dest_name):
                    # variable existante allouee dynamiquement -> on libere avant de reassigner
                    c_line = f'free({dest_name});\n    {dest_name} = "{escaped}";'
                    _heap_unmark(dest_name)
                else:
                    c_line = f'{dest_name} = "{escaped}";'
            else:
                # au moins un operande vient d'une variable -> repetition faite a l'execution
                symbol_table["rexfn"].append("rexsl_str_repeat")
                expr_str = REX_SL_CODE._operand_expr(str_operand)
                expr_count = REX_SL_CODE._operand_expr(count_operand)
                if is_declaration:
                    if _can_hoist():
                        symbol_table["heap_str_decls"][-1].add(dest_name)
                        c_line = f'{dest_name} = rexsl_str_repeat({expr_str}, {expr_count});'
                    else:
                        c_line = f'char* {dest_name} = rexsl_str_repeat({expr_str}, {expr_count});'
                    symbol_table["var"][dest_raw_name] = "str"
                else:
                    c_line = f'{dest_name} = rexsl_str_repeat({expr_str}, {expr_count});'
                _heap_mark(dest_name)

        # ---- cas classique : number/float * number/float ----
        else:
            is_float_result = "float" in (type_a, type_b)
            c_type = "float" if is_float_result else "int"
            var_kind = "float" if is_float_result else "number"
            expr_a = REX_SL_CODE._operand_expr(operand_a)
            expr_b = REX_SL_CODE._operand_expr(operand_b)

            if is_declaration:
                c_line = f"{c_type} {dest_name} = {expr_a} * {expr_b};"
                symbol_table["var"][dest_raw_name] = var_kind
            else:
                c_line = f"{dest_name} = {expr_a} * {expr_b};"

        log("CODE.mul", "ligne C generee : %r", c_line)
        log_exit("CODE.mul", "-> %r", c_line)
        return c_line

    @staticmethod
    def pow_op(destination, operand_a, operand_b):
        """pow <dest> <base> <exposant>; (0.0.14) - number/float uniquement
        (pas de sens pour str/bool), meme structure que mul() cote
        validation. Utilise pow() de <math.h> (cf. c_source, include ajoute
        inconditionnellement) et gcc -lm (cf. gcc_cmd)."""
        log_enter("CODE.pow_op", "destination=%r operand_a=%r operand_b=%r",
                destination, operand_a, operand_b)

        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            log_exit("CODE.pow_op", "ERREUR")
            raise REX_SL(f"destination non gere : {destination[1]}")
        if REX_SL_CODE._is_rx(dest_raw_name):
            log_exit("CODE.pow_op", "ERREUR")
            raise REX_SL(f"destination RX_ en lecture seule (registre importe) : {dest_raw_name}")

        dest_name = REX_SL_CODE._c_name(dest_raw_name)
        is_declaration = dest_raw_name not in symbol_table["var"]
        if not is_declaration and dest_raw_name in symbol_table["const_vars"]:
            log_exit("CODE.pow_op", "ERREUR")
            raise REX_SL(f"modification interdite : {dest_raw_name} est une constante")
        type_a = REX_SL_CODE._operand_type(operand_a)
        type_b = REX_SL_CODE._operand_type(operand_b)

        if type_a not in ("number", "float") or type_b not in ("number", "float"):
            log_exit("CODE.pow_op", "ERREUR")
            raise REX_SL(f"pow: operandes doivent etre number/float : {destination[1]}")

        is_float_result = "float" in (type_a, type_b)
        c_type = "float" if is_float_result else "int"
        var_kind = "float" if is_float_result else "number"
        expr_a = REX_SL_CODE._operand_expr(operand_a)
        expr_b = REX_SL_CODE._operand_expr(operand_b)
        pow_expr = f"({c_type})pow((double)({expr_a}), (double)({expr_b}))"

        if is_declaration:
            c_line = f"{c_type} {dest_name} = {pow_expr};"
            symbol_table["var"][dest_raw_name] = var_kind
        else:
            c_line = f"{dest_name} = {pow_expr};"

        log("CODE.pow_op", "ligne C generee : %r", c_line)
        log_exit("CODE.pow_op", "-> %r", c_line)
        return c_line

    @staticmethod
    def _div_mod(op_name, c_operator, destination, operand_a, operand_b):
        """Logique commune a div et mod : meme structure, meme protection division par zero."""
        log_enter(f"CODE.{op_name}", "destination=%r operand_a=%r operand_b=%r",
                destination, operand_a, operand_b)

        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            log_exit(f"CODE.{op_name}", "ERREUR")
            raise REX_SL(f"destination non gere : {destination[1]}")
        if REX_SL_CODE._is_rx(dest_raw_name):
            log_exit(f"CODE.{op_name}", "ERREUR")
            raise REX_SL(f"destination RX_ en lecture seule (registre importe) : {dest_raw_name}")

        dest_name = REX_SL_CODE._c_name(dest_raw_name)
        is_declaration = dest_raw_name not in symbol_table["var"]
        if not is_declaration and dest_raw_name in symbol_table["const_vars"]:
            log_exit(f"CODE.{op_name}", "ERREUR")
            raise REX_SL(f"modification interdite : {dest_raw_name} est une constante")
        type_a = REX_SL_CODE._operand_type(operand_a)
        type_b = REX_SL_CODE._operand_type(operand_b)

        if type_a in ("bool", "str") or type_b in ("bool", "str"):
            log_exit(f"CODE.{op_name}", "ERREUR")
            raise REX_SL(f"{op_name} non gere sur ce type : {destination[1]}")

        # division/modulo par zero connu a la compilation -> erreur immediate
        if operand_b[0] in ("number", "float") and operand_b[1] == 0:
            log_exit(f"CODE.{op_name}", "ERREUR")
            raise REX_SL(f"division par zero : {destination[1]}")

        is_float_result = "float" in (type_a, type_b)
        if op_name == "mod" and is_float_result:
            log_exit(f"CODE.{op_name}", "ERREUR")
            raise REX_SL(f"modulo non gere sur les float : {destination[1]}")

        c_type = "float" if is_float_result else "int"
        var_kind = "float" if is_float_result else "number"
        expr_a = REX_SL_CODE._operand_expr(operand_a)
        expr_b = REX_SL_CODE._operand_expr(operand_b)

        lines = []
        # si le diviseur est une variable (valeur inconnue a la compilation), on ajoute
        # un garde-fou runtime pour eviter le crash / UB en cas de division par zero
        if operand_b[0] == "ident":
            lines.append(
                f'if (({expr_b}) == 0) {{ fprintf(stderr, "[REX-SL] erreur : '
                f'division par zero\\n"); exit(1); }}'
            )

        if is_declaration:
            lines.append(f"{c_type} {dest_name} = {expr_a} {c_operator} {expr_b};")
            symbol_table["var"][dest_raw_name] = var_kind
        else:
            lines.append(f"{dest_name} = {expr_a} {c_operator} {expr_b};")

        c_line = "\n    ".join(lines)
        log(f"CODE.{op_name}", "ligne C generee : %r", c_line)
        log_exit(f"CODE.{op_name}", "-> %r", c_line)
        return c_line

    @staticmethod
    def div(destination, operand_a, operand_b):
        return REX_SL_CODE._div_mod("div", "/", destination, operand_a, operand_b)

    @staticmethod
    def mod(destination, operand_a, operand_b):
        return REX_SL_CODE._div_mod("mod", "%", destination, operand_a, operand_b)

    @staticmethod
    def var(var_type, var_name, initial_value_token):
        log_enter("CODE.var", "var_type=%r var_name=%r initial_value_token=%r",
                var_type, var_name, initial_value_token)

        if REX_SL_CODE._is_rx(var_name):
            log_exit("CODE.var", "ERREUR")
            raise REX_SL(f"nom reserve au registre RX (importe), declaration via var impossible : {var_name}")

        raw_name = var_name                       # <-- AJOUT : nom brut avant conversion SL_
        is_const = raw_name in symbol_table["const_vars"]   # <-- AJOUT
        var_name = REX_SL_CODE._c_name(var_name)

        if initial_value_token and var_type != initial_value_token[0]:
            log_exit("CODE.var", "ERREUR")
            raise REX_SL(
                f"variable {var_name} de type {var_type} et valeur {initial_value_token[1]} "
                f"de type {initial_value_token[0]}"
            )

        if var_type == "bool":
            if initial_value_token:
                bool_literal = "true" if initial_value_token[1] else "false"
            else:
                bool_literal = "true"
            qualifier = "const bool" if is_const else "bool"
            c_line = f"{qualifier} {var_name} = {bool_literal};"
            log_exit("CODE.var", "-> %r", c_line)
            return c_line

        # valeur par defaut si aucune valeur initiale n'est fournie
        if initial_value_token:
            default_value = initial_value_token[1]
        else:
            default_value = "0"

        if var_type == "number":
            qualifier = "const int" if is_const else "int"
            c_line = f"{qualifier} {var_name} = {default_value};"

        elif var_type == "float":
            qualifier = "const float" if is_const else "float"
            c_line = f"{qualifier} {var_name} = {default_value};"

        elif var_type == "str":
            raw_value = default_value if initial_value_token else ""
            escaped_value = _escape_c_string(raw_value)

            if is_const:
                # constante -> jamais de malloc, jamais de free, meme si longue
                c_line = f'const char* {var_name} = "{escaped_value}";'
                log("CODE.var", "str %r constante -> litteral direct (pas de heap)", var_name)
            elif len(raw_value) < STACK_STR_THRESHOLD:
                if _can_hoist():
                    # Hissage a NULL en tete de bloc, meme pour les str courtes.
                    # Cela couvre le cas residuel documente (promotion pile->tas
                    # d'une variable deja declaree sautee par un 'go') : si le
                    # 'add'/'sub'/'mul' de promotion est saute, le pointeur vaut
                    # NULL (et non l'adresse du buffer pile) -> le free()
                    # conditionnel de fin de bloc est sans danger.
                    symbol_table["rexfn"].append("rexsl_str_alloc")
                    _heap_mark(var_name)
                    symbol_table["heap_str_decls"][-1].add(var_name)
                    c_line = f'{var_name} = rexsl_str_alloc("{escaped_value}");'
                else:
                    c_line = (
                        f'char {var_name}_buf[{STACK_STR_THRESHOLD}] = "{escaped_value}";\n'
                        f'    char* {var_name} = {var_name}_buf;'
                    )
            else:
                symbol_table["rexfn"].append("rexsl_str_alloc")
                _heap_mark(var_name)
                if _can_hoist():
                    symbol_table["heap_str_decls"][-1].add(var_name)
                    c_line = f'{var_name} = rexsl_str_alloc("{escaped_value}");'
                else:
                    c_line = f'char* {var_name} = rexsl_str_alloc("{escaped_value}");'
        elif var_type == "list":
            if initial_value_token:
                log_exit("CODE.var", "ERREUR")
                raise REX_SL(f"list ne prend pas de valeur initiale : {var_name}")
            symbol_table["rexfn"].append("rexsl_collections")
            symbol_table["collection_vars"][-1].append((var_name, "list"))
            if _can_hoist():
                symbol_table["collection_hoist"][-1].add(var_name)
                c_line = f"{var_name} = rexsl_list_new();"
            else:
                c_line = f"RexList* {var_name} = rexsl_list_new();"

        elif var_type == "dict":
            if initial_value_token:
                log_exit("CODE.var", "ERREUR")
                raise REX_SL(f"dict ne prend pas de valeur initiale : {var_name}")
            symbol_table["rexfn"].append("rexsl_collections")
            symbol_table["collection_vars"][-1].append((var_name, "dict"))
            if _can_hoist():
                symbol_table["collection_hoist"][-1].add(var_name)
                c_line = f"{var_name} = rexsl_dict_new();"
            else:
                c_line = f"RexDict* {var_name} = rexsl_dict_new();"

        elif var_type == "set":
            # set = ensemble non ordonne sans doublons, stocke comme RexList* cote C
            # (rexsl_set_add() garantit l'unicite a l'insertion).
            if initial_value_token:
                log_exit("CODE.var", "ERREUR")
                raise REX_SL(f"set ne prend pas de valeur initiale : {var_name}")
            symbol_table["rexfn"].append("rexsl_collections")
            symbol_table["collection_vars"][-1].append((var_name, "set"))
            if _can_hoist():
                symbol_table["collection_hoist"][-1].add(var_name)
                c_line = f"{var_name} = rexsl_list_new();"
            else:
                c_line = f"RexList* {var_name} = rexsl_list_new();"

        elif var_type == "tuple":
            # tuple = sequence immuable, stockee comme RexList* (pas de garde-fou
            # d'immuabilite cote C pour l'instant, semantique garantie par REX.py).
            if initial_value_token:
                log_exit("CODE.var", "ERREUR")
                raise REX_SL(f"tuple ne prend pas de valeur initiale : {var_name}")
            symbol_table["rexfn"].append("rexsl_collections")
            symbol_table["collection_vars"][-1].append((var_name, "tuple"))
            if _can_hoist():
                symbol_table["collection_hoist"][-1].add(var_name)
                c_line = f"{var_name} = rexsl_list_new();"
            else:
                c_line = f"RexList* {var_name} = rexsl_list_new();"

        elif var_type == "none":
            # none : pointeur void* opaque, toujours NULL. Pas de valeur initiale.
            if initial_value_token and initial_value_token[0] != "none":
                log_exit("CODE.var", "ERREUR")
                raise REX_SL(f"none ne prend que 'none' comme valeur initiale (ou rien) : {var_name}")
            c_line = f"void* {var_name} = NULL;"

        else:
            log_exit("CODE.var", "ERREUR")
            raise REX_SL(f"type de variable non gere : {var_type}")

        log("CODE.var", "ligne C generee : %r", c_line)
        log_exit("CODE.var", "-> %r", c_line)
        return c_line

    @staticmethod
    def _resolve_cdn_operator(op_token):
        """Resout un token operateur de 'cdn' (symbole deja tokenise, ou mot-cle) vers l'operateur C."""
        op_type, op_value = op_token
        if op_type == "op" and op_value in CDN_SYMBOL_OPS:
            return op_value
        if op_type == "ident" and op_value.lower() in CDN_WORD_OPS:
            return CDN_WORD_OPS[op_value.lower()]
        raise REX_SL(f"operateur de condition non gere : {op_value}")

    @staticmethod
    def cdn_on():
        """cdn on; -> force la condition courante a vraie (permet un saut inconditionnel via go)."""
        log("CODE.cdn_on", "condition forcee a true (saut inconditionnel)")
        c_line = f"{REXSL_COND_VAR} = true;"
        return c_line

    @staticmethod
    def cdn(op_token, operand_a, operand_b):
        """
        cdn <op> <a> <b>; evalue une condition et la stocke dans REXSL_COND_VAR pour un
        'go' ulterieur. Les strings n'etant pas comparables directement en C (char*),
        elles passent par strcmp(...) <op> 0 -- ce qui marche uniformement pour les 6
        operateurs (==, !=, >, <, >=, <=). Les autres types (number/float/bool) sont
        compares directement, bool etant naturellement compatible int en C.
        """
        log_enter("CODE.cdn", "op_token=%r operand_a=%r operand_b=%r", op_token, operand_a, operand_b)

        c_operator = REX_SL_CODE._resolve_cdn_operator(op_token)
        type_a = REX_SL_CODE._operand_type(operand_a)
        type_b = REX_SL_CODE._operand_type(operand_b)
        expr_a = REX_SL_CODE._operand_expr(operand_a)
        expr_b = REX_SL_CODE._operand_expr(operand_b)

        if type_a == "none" or type_b == "none":
            # Comparaison impliquant none : seuls == et != ont un sens (is/is not)
            if c_operator not in ("==", "!="):
                log_exit("CODE.cdn", "ERREUR")
                raise REX_SL(
                    f"cdn: seuls == et != sont autorises avec none "
                    f"(operateur recu : {c_operator})"
                )
            if type_a != "none" and type_b != "none":
                # cas impossible (les deux seraient non-none), mais garde-fou
                log_exit("CODE.cdn", "ERREUR")
                raise REX_SL(f"cdn: comparaison none incoherente : {operand_a} / {operand_b}")
            # On compare le cote non-none contre NULL, ou none contre none
            if type_a == "none" and type_b == "none":
                # none == none -> toujours vrai ; none != none -> toujours faux
                bool_lit = "true" if c_operator == "==" else "false"
                c_line = f"{REXSL_COND_VAR} = {bool_lit};"
            else:
                # variable (ptr) == none ou none == variable
                ptr_expr = expr_a if type_b == "none" else expr_b
                c_line = f"{REXSL_COND_VAR} = ({ptr_expr} {c_operator} NULL);"
            log("CODE.cdn", "comparaison none -> pointeur : %r", c_line)
        elif type_a == "str" or type_b == "str":
            if type_a != "str" or type_b != "str":
                log_exit("CODE.cdn", "ERREUR")
                raise REX_SL(f"comparaison de types differents : {operand_a} / {operand_b}")
            c_line = f"{REXSL_COND_VAR} = (strcmp({expr_a}, {expr_b}) {c_operator} 0);"
            log("CODE.cdn", "comparaison str -> strcmp : %r", c_line)
        else:
            c_line = f"{REXSL_COND_VAR} = ({expr_a} {c_operator} {expr_b});"
            log("CODE.cdn", "comparaison numerique/bool : %r", c_line)

        log_exit("CODE.cdn", "-> %r", c_line)
        return c_line

    @staticmethod
    def lbl(label_name):
        """lbl <nom>; -> declare une etiquette C (LBL_<nom>) a laquelle 'go' peut sauter."""
        c_line = f"LBL_{label_name}: ;"
        log("CODE.lbl", "ligne C generee : %r", c_line)
        return c_line

    @staticmethod
    def go(label_name):
        """go <nom>; -> saute a LBL_<nom> SI la derniere condition evaluee (cdn) est vraie."""
        c_line = f"if ({REXSL_COND_VAR}) goto LBL_{label_name};"
        log("CODE.go", "ligne C generee : %r", c_line)
        return c_line

    @staticmethod
    def run(path_token, label_token=None, arg_operands=None):
        """
        run <path>;                     -> execute au runtime, depuis le debut.
        run <path> <lbl>;                -> saute directement a <lbl>.
        run <path> <lbl> <v1> <v2> ...;  -> idem + transmet des valeurs via argv
                                             (pas de memoire partagee entre process :
                                             tout passe par des chaines de texte).
        """
        log_enter("CODE.run", "path_token=%r label_token=%r arg_operands=%r",
                   path_token, label_token, arg_operands)
        arg_operands = arg_operands or []

        if path_token[0] != "str":
            log_exit("CODE.run", "ERREUR")
            raise REX_SL(f"chemin de module non gere (attendu une string) : {path_token}")
        if arg_operands and label_token is None:
            log_exit("CODE.run", "ERREUR")
            raise REX_SL("run: des arguments ont ete fournis sans etiquette cible")

        escaped_path = _escape_c_string(path_token[1])

        if label_token is None:
            c_line = f'fflush(stdout); system("{escaped_path}");'
            log_exit("CODE.run", "-> %r", c_line)
            return c_line

        if label_token[0] != "ident":
            log_exit("CODE.run", "ERREUR")
            raise REX_SL(f"etiquette de module non geree : {label_token}")
        escaped_label = _escape_c_string(label_token[1])

        if not arg_operands:
            c_line = (
                "{\n"
                "    char __rexsl_run_cmd[1024];\n"
                f'    snprintf(__rexsl_run_cmd, sizeof(__rexsl_run_cmd), "%s %s", "{escaped_path}", "{escaped_label}");\n'
                "    fflush(stdout);\n"
                "    system(__rexsl_run_cmd);\n"
                "    }"
            )
            log_exit("CODE.run", "-> %r (sans args)", c_line)
            return c_line

        arg_fmt_parts = []
        arg_exprs = []
        for operand in arg_operands:
            op_type = REX_SL_CODE._operand_type(operand)
            expr = REX_SL_CODE._operand_expr(operand)
            if op_type == "number":
                arg_fmt_parts.append("%d")
                arg_exprs.append(expr)
            elif op_type == "float":
                arg_fmt_parts.append("%g")
                arg_exprs.append(expr)
            elif op_type == "bool":
                arg_fmt_parts.append("%s")
                arg_exprs.append(f'({expr} ? "true" : "false")')
            elif op_type == "str":
                # quoting minimal (protege les espaces) -- PAS une defense anti-injection
                arg_fmt_parts.append('\\"%s\\"')
                arg_exprs.append(expr)
            else:
                log_exit("CODE.run", "ERREUR")
                raise REX_SL(f"run: type d'argument non gere : {operand}")

        fmt_string = "%s %s " + " ".join(arg_fmt_parts)
        all_args = ", ".join([f'"{escaped_path}"', f'"{escaped_label}"'] + arg_exprs)
        c_line = (
            "{\n"
            "    char __rexsl_run_cmd[1024];\n"
            f'    snprintf(__rexsl_run_cmd, sizeof(__rexsl_run_cmd), "{fmt_string}", {all_args});\n'
            "    fflush(stdout);\n"
            "    system(__rexsl_run_cmd);\n"
            "    }"
        )
        log_exit("CODE.run", "-> %r (avec args)", c_line)
        return c_line
    
    @staticmethod
    def len_of(destination, operand):
        """len <dest_number> <str_ou_list>;
        - str  : ecrit (int)strlen(str) dans <dest> (number deja declaree ou declaree a la volee).
        - list : ecrit list->count dans <dest> (meme regles).
        Retrocompatible : le cas str est identique a avant."""
        log_enter("CODE.len_of", "destination=%r operand=%r", destination, operand)

        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            log_exit("CODE.len_of", "ERREUR")
            raise REX_SL(f"len: destination doit etre un identifiant : {destination}")
        if dest_raw_name in symbol_table["const_vars"]:
            log_exit("CODE.len_of", "ERREUR")
            raise REX_SL(f"len: modification interdite, {dest_raw_name} est une constante")

        # La destination peut ne pas encore exister -> on la declare comme number
        is_declaration = dest_raw_name not in symbol_table["var"]
        if not is_declaration and symbol_table["var"].get(dest_raw_name) != "number":
            log_exit("CODE.len_of", "ERREUR")
            raise REX_SL(f"len: destination doit etre de type number : {destination}")

        op_type = REX_SL_CODE._operand_type(operand)
        dest_name = REX_SL_CODE._c_name(dest_raw_name)

        if op_type == "str":
            str_expr = REX_SL_CODE._operand_expr(operand)
            if is_declaration:
                symbol_table["var"][dest_raw_name] = "number"
                c_line = f"int {dest_name} = (int)strlen({str_expr});"
            else:
                c_line = f"{dest_name} = (int)strlen({str_expr});"

        elif op_type in ("list", "dict", "set", "tuple"):
            # list/set/tuple -> RexList*->count ; dict -> RexDict*->count
            # Le champ count est expose de facon identique dans les deux structs.
            coll_type, coll_name = operand
            if coll_type != "ident":
                log_exit("CODE.len_of", "ERREUR")
                raise REX_SL(f"len: operande {op_type} doit etre un identifiant : {operand}")
            symbol_table["rexfn"].append("rexsl_collections")
            coll_c = REX_SL_CODE._c_name(coll_name)
            if is_declaration:
                symbol_table["var"][dest_raw_name] = "number"
                c_line = f"int {dest_name} = {coll_c}->count;"
            else:
                c_line = f"{dest_name} = {coll_c}->count;"

        else:
            log_exit("CODE.len_of", "ERREUR")
            raise REX_SL(
                f"len: operande doit etre une string ou une collection "
                f"(list/dict) : {operand} (type={op_type})"
            )

        log_exit("CODE.len_of", "-> %r", c_line)
        return c_line

    @staticmethod
    def list_count(destination, list_operand):
        """list_count <dest_number> <list>; primitive explicite retournant list->count.
        Alias semantique de 'len' sur une list ; utile quand REX.py veut etre explicite."""
        log_enter("CODE.list_count", "destination=%r list_operand=%r", destination, list_operand)
        # Delegue simplement a len_of qui gere desormais les deux cas.
        result = REX_SL_CODE.len_of(destination, list_operand)
        log_exit("CODE.list_count", "-> %r", result)
        return result

    @staticmethod
    def charat(destination, str_operand, idx_operand):
        """charat <dest_str> <str> <idx>; 1 caractere, index verifie au runtime (erreur fatale si hors bornes)."""
        log_enter("CODE.charat", "destination=%r str_operand=%r idx_operand=%r",
                  destination, str_operand, idx_operand)
        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            log_exit("CODE.charat", "ERREUR")
            raise REX_SL(f"destination non gere : {destination[1]}")
        if REX_SL_CODE._operand_type(str_operand) != "str":
            log_exit("CODE.charat", "ERREUR")
            raise REX_SL(f"charat: operande doit etre une string : {str_operand}")
        if REX_SL_CODE._operand_type(idx_operand) != "number":
            log_exit("CODE.charat", "ERREUR")
            raise REX_SL(f"charat: index doit etre un number : {idx_operand}")
        if idx_operand[0] == "number" and idx_operand[1] < 0:
            log_exit("CODE.charat", "ERREUR")
            raise REX_SL(f"charat: index negatif connu a la compilation : {idx_operand[1]}")
        symbol_table["rexfn"].append("rexsl_str_charat")
        str_expr = REX_SL_CODE._operand_expr(str_operand)
        idx_expr = REX_SL_CODE._operand_expr(idx_operand)
        c_line = REX_SL_CODE._assign_heap_str(dest_raw_name, f"rexsl_str_charat({str_expr}, {idx_expr})")
        log_exit("CODE.charat", "-> %r", c_line)
        return c_line

    @staticmethod
    def slice(destination, str_operand, start_operand, end_operand):
        """slice <dest_str> <str> <start> <end>; sous-chaine [start,end), bornes clampees (pas d'erreur fatale)."""
        log_enter("CODE.slice", "destination=%r str_operand=%r start=%r end=%r",
                  destination, str_operand, start_operand, end_operand)
        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            log_exit("CODE.slice", "ERREUR")
            raise REX_SL(f"destination non gere : {destination[1]}")
        if REX_SL_CODE._operand_type(str_operand) != "str":
            log_exit("CODE.slice", "ERREUR")
            raise REX_SL(f"slice: operande doit etre une string : {str_operand}")
        if REX_SL_CODE._operand_type(start_operand) != "number" or REX_SL_CODE._operand_type(end_operand) != "number":
            log_exit("CODE.slice", "ERREUR")
            raise REX_SL(f"slice: start/end doivent etre des number : {start_operand}, {end_operand}")
        if start_operand[0] == "number" and end_operand[0] == "number" and start_operand[1] > end_operand[1]:
            log_exit("CODE.slice", "ERREUR")
            raise REX_SL(
                f"slice: start ({start_operand[1]}) > end ({end_operand[1]}) connu a la compilation"
            )
        symbol_table["rexfn"].append("rexsl_str_slice")
        str_expr = REX_SL_CODE._operand_expr(str_operand)
        start_expr = REX_SL_CODE._operand_expr(start_operand)
        end_expr = REX_SL_CODE._operand_expr(end_operand)
        c_line = REX_SL_CODE._assign_heap_str(
            dest_raw_name, f"rexsl_str_slice({str_expr}, {start_expr}, {end_expr})"
        )
        log_exit("CODE.slice", "-> %r", c_line)
        return c_line

    @staticmethod
    def slice_step(destination, str_operand, start_operand, end_operand, step_operand):
        """slicestep <dest_str> <str> <start> <end> <pas>; (0.0.14) - meme
        principe que slice() mais avec un pas, `end` == -1 (litteral)
        signifiant "jusqu'au debut inclus" pour un pas negatif (cf.
        ExprCodegen._slice_step cote REX.py, seul point d'emission de
        cet opcode). Le pas doit etre un litteral non nul (verifie a la
        compilation cote REX.py deja, revalide ici par securite)."""
        log_enter("CODE.slice_step", "destination=%r str_operand=%r start=%r end=%r step=%r",
                  destination, str_operand, start_operand, end_operand, step_operand)
        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            log_exit("CODE.slice_step", "ERREUR")
            raise REX_SL(f"destination non gere : {destination[1]}")
        if REX_SL_CODE._operand_type(str_operand) != "str":
            log_exit("CODE.slice_step", "ERREUR")
            raise REX_SL(f"slicestep: operande doit etre une string : {str_operand}")
        if (
            REX_SL_CODE._operand_type(start_operand) != "number"
            or REX_SL_CODE._operand_type(end_operand) != "number"
            or REX_SL_CODE._operand_type(step_operand) != "number"
        ):
            log_exit("CODE.slice_step", "ERREUR")
            raise REX_SL(
                f"slicestep: start/end/pas doivent etre des number : "
                f"{start_operand}, {end_operand}, {step_operand}"
            )
        if step_operand[0] == "number" and step_operand[1] == 0:
            log_exit("CODE.slice_step", "ERREUR")
            raise REX_SL("slicestep: le pas ne peut pas etre 0")
        symbol_table["rexfn"].append("rexsl_str_slice_step")
        str_expr = REX_SL_CODE._operand_expr(str_operand)
        start_expr = REX_SL_CODE._operand_expr(start_operand)
        end_expr = REX_SL_CODE._operand_expr(end_operand)
        step_expr = REX_SL_CODE._operand_expr(step_operand)
        c_line = REX_SL_CODE._assign_heap_str(
            dest_raw_name,
            f"rexsl_str_slice_step({str_expr}, {start_expr}, {end_expr}, {step_expr})"
        )
        log_exit("CODE.slice_step", "-> %r", c_line)
        return c_line

    @staticmethod
    def find(destination, str_operand, substr_operand):
        """find <dest_number> <str> <substr>; index de la 1ere occurrence, -1 si absente."""
        log_enter("CODE.find", "destination=%r str_operand=%r substr_operand=%r",
                  destination, str_operand, substr_operand)
        dest_type, dest_raw_name = destination
        if dest_type != "ident" or symbol_table["var"].get(dest_raw_name) != "number":
            log_exit("CODE.find", "ERREUR")
            raise REX_SL(f"find: destination doit etre une variable number deja declaree : {destination}")
        if dest_raw_name in symbol_table["const_vars"]:
            log_exit("CODE.find", "ERREUR")
            raise REX_SL(f"find: modification interdite, {dest_raw_name} est une constante")
        if REX_SL_CODE._operand_type(str_operand) != "str" or REX_SL_CODE._operand_type(substr_operand) != "str":
            log_exit("CODE.find", "ERREUR")
            raise REX_SL(f"find: operandes doivent etre des string : {str_operand}, {substr_operand}")
        symbol_table["rexfn"].append("rexsl_str_find")
        dest_name = REX_SL_CODE._c_name(dest_raw_name)
        str_expr = REX_SL_CODE._operand_expr(str_operand)
        substr_expr = REX_SL_CODE._operand_expr(substr_operand)
        c_line = f"{dest_name} = rexsl_str_find({str_expr}, {substr_expr});"
        log_exit("CODE.find", "-> %r", c_line)
        return c_line

    @staticmethod
    def contains_op(destination, negate, value_operand, collection_operand):
        """in <dest_bool> <valeur> <liste_ou_str>; / notin <dest_bool> <valeur> <liste_ou_str>;
        - list : comparaison element par element selon le type stocke dans le RexValue
          (rexsl_list_contains, meme type ET meme valeur requis).
        - str  : test de sous-chaine, reutilise rexsl_str_find (!= -1).
        Destination bool auto-declaree si absente ; sinon doit deja etre bool (comme len_of)."""
        log_enter("CODE.contains_op", "destination=%r negate=%r value_operand=%r collection_operand=%r",
                  destination, negate, value_operand, collection_operand)

        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            log_exit("CODE.contains_op", "ERREUR")
            raise REX_SL(f"in/notin: destination doit etre un identifiant : {destination}")
        if REX_SL_CODE._is_rx(dest_raw_name):
            log_exit("CODE.contains_op", "ERREUR")
            raise REX_SL(f"destination RX_ en lecture seule (registre importe) : {dest_raw_name}")

        is_declaration = dest_raw_name not in symbol_table["var"]
        if not is_declaration and dest_raw_name in symbol_table["const_vars"]:
            log_exit("CODE.contains_op", "ERREUR")
            raise REX_SL(f"in/notin: modification interdite, {dest_raw_name} est une constante")
        if not is_declaration and symbol_table["var"].get(dest_raw_name) != "bool":
            log_exit("CODE.contains_op", "ERREUR")
            raise REX_SL(f"in/notin: destination doit etre de type bool : {destination}")

        dest_name = REX_SL_CODE._c_name(dest_raw_name)
        coll_type = REX_SL_CODE._operand_type(collection_operand)

        if coll_type == "str":
            if REX_SL_CODE._operand_type(value_operand) != "str":
                log_exit("CODE.contains_op", "ERREUR")
                raise REX_SL(f"in/notin: recherche dans une str exige une valeur str : {value_operand}")
            symbol_table["rexfn"].append("rexsl_str_find")
            str_expr = REX_SL_CODE._operand_expr(collection_operand)
            substr_expr = REX_SL_CODE._operand_expr(value_operand)
            test_expr = f"(rexsl_str_find({str_expr}, {substr_expr}) != -1)"

        elif coll_type in ("list", "set", "tuple"):
            list_type, list_name = collection_operand
            if list_type != "ident":
                log_exit("CODE.contains_op", "ERREUR")
                raise REX_SL(f"in/notin: operande list/set/tuple doit etre un identifiant : {collection_operand}")
            symbol_table["rexfn"].append("rexsl_collections")
            symbol_table["rexfn"].append("rexsl_list_contains")
            list_c = REX_SL_CODE._c_name(list_name)
            boxed = REX_SL_CODE._box_expr(value_operand)
            test_expr = f"rexsl_list_contains({list_c}, {boxed})"

        else:
            log_exit("CODE.contains_op", "ERREUR")
            raise REX_SL(f"in/notin: operande doit etre une list, set, tuple ou str : {collection_operand} (type={coll_type})")

        if negate:
            test_expr = f"!({test_expr})"

        if is_declaration:
            c_line = f"bool {dest_name} = {test_expr};"
            symbol_table["var"][dest_raw_name] = "bool"
        else:
            c_line = f"{dest_name} = {test_expr};"

        log_exit("CODE.contains_op", "-> %r", c_line)
        return c_line

    @staticmethod
    def upper(destination, str_operand):
        log_enter("CODE.upper", "destination=%r str_operand=%r", destination, str_operand)
        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            log_exit("CODE.upper", "ERREUR")
            raise REX_SL(f"destination non gere : {destination[1]}")
        if REX_SL_CODE._operand_type(str_operand) != "str":
            log_exit("CODE.upper", "ERREUR")
            raise REX_SL(f"upper: operande doit etre une string : {str_operand}")
        symbol_table["rexfn"].append("rexsl_str_upper")
        str_expr = REX_SL_CODE._operand_expr(str_operand)
        c_line = REX_SL_CODE._assign_heap_str(dest_raw_name, f"rexsl_str_upper({str_expr})")
        log_exit("CODE.upper", "-> %r", c_line)
        return c_line

    @staticmethod
    def lower(destination, str_operand):
        log_enter("CODE.lower", "destination=%r str_operand=%r", destination, str_operand)
        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            log_exit("CODE.lower", "ERREUR")
            raise REX_SL(f"destination non gere : {destination[1]}")
        if REX_SL_CODE._operand_type(str_operand) != "str":
            log_exit("CODE.lower", "ERREUR")
            raise REX_SL(f"lower: operande doit etre une string : {str_operand}")
        symbol_table["rexfn"].append("rexsl_str_lower")
        str_expr = REX_SL_CODE._operand_expr(str_operand)
        c_line = REX_SL_CODE._assign_heap_str(dest_raw_name, f"rexsl_str_lower({str_expr})")
        log_exit("CODE.lower", "-> %r", c_line)
        return c_line

    @staticmethod
    def trim(destination, str_operand):
        log_enter("CODE.trim", "destination=%r str_operand=%r", destination, str_operand)
        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            log_exit("CODE.trim", "ERREUR")
            raise REX_SL(f"destination non gere : {destination[1]}")
        if REX_SL_CODE._operand_type(str_operand) != "str":
            log_exit("CODE.trim", "ERREUR")
            raise REX_SL(f"trim: operande doit etre une string : {str_operand}")
        symbol_table["rexfn"].append("rexsl_str_trim")
        str_expr = REX_SL_CODE._operand_expr(str_operand)
        c_line = REX_SL_CODE._assign_heap_str(dest_raw_name, f"rexsl_str_trim({str_expr})")
        log_exit("CODE.trim", "-> %r", c_line)
        return c_line
    
    @staticmethod
    def replace(destination, str_operand, old_operand, new_operand):
        log_enter("CODE.replace", "destination=%r str=%r old=%r new=%r",
                  destination, str_operand, old_operand, new_operand)
        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            raise REX_SL(f"destination non gere : {destination[1]}")
        for op, label in ((str_operand, "str"), (old_operand, "old"), (new_operand, "new")):
            if REX_SL_CODE._operand_type(op) != "str":
                log_exit("CODE.replace", "ERREUR")
                raise REX_SL(f"replace: {label} doit etre une string : {op}")
        symbol_table["rexfn"].append("rexsl_str_replace_all")
        str_e = REX_SL_CODE._operand_expr(str_operand)
        old_e = REX_SL_CODE._operand_expr(old_operand)
        new_e = REX_SL_CODE._operand_expr(new_operand)
        c_line = REX_SL_CODE._assign_heap_str(
            dest_raw_name, f"rexsl_str_replace_all({str_e}, {old_e}, {new_e})"
        )
        log_exit("CODE.replace", "-> %r", c_line)
        return c_line

    @staticmethod
    def reverse(destination, str_operand):
        log_enter("CODE.reverse", "destination=%r str_operand=%r", destination, str_operand)
        dest_type, dest_raw_name = destination
        if dest_type != "ident":
            raise REX_SL(f"destination non gere : {destination[1]}")
        if REX_SL_CODE._operand_type(str_operand) != "str":
            log_exit("CODE.reverse", "ERREUR")
            raise REX_SL(f"reverse: operande doit etre une string : {str_operand}")
        symbol_table["rexfn"].append("rexsl_str_reverse")
        str_e = REX_SL_CODE._operand_expr(str_operand)
        c_line = REX_SL_CODE._assign_heap_str(dest_raw_name, f"rexsl_str_reverse({str_e})")
        log_exit("CODE.reverse", "-> %r", c_line)
        return c_line


class REX_SL_COMPILER:
    """
    Transforme les lignes de tokens (issues du lexer) en code C.
    Instructions gerees pour l'instant :
        show / showln <valeur>   -> printf(...)
        var <type> <nom> [valeur] -> declaration de variable C
        <nom> <valeur>            -> reaffectation d'une variable existante
    """

    def __init__(self, tokenized_lines, opcode_lines=None):
        log("COMPILER.__init__", "tokenized_lines=%r", tokenized_lines, verbose=True)
        self.tokenized_lines = tokenized_lines  # liste de listes de tokens, une entree par instruction
        # numero de ligne source (1-indexe) pour chaque entree de tokenized_lines,
        # utilise pour situer les erreurs REX_SL dans le fichier de l'utilisateur.
        # optionnel : si absent (ou trop court), on retombe sur l'index d'opcode.
        self.opcode_lines = opcode_lines or []

    def _line_for(self, index):
        """Retourne le numero de ligne source pour l'opcode #index, ou None si inconnu."""
        if 0 <= index < len(self.opcode_lines):
            return self.opcode_lines[index]
        return None

    def _compile_line(self, tokens):
        """Compile une seule ligne de tokens (une instruction) en une ligne de code C."""
        log_enter("COMPILER._compile_line", "tokens=%r", tokens, verbose=True)

        if not tokens:
            log("COMPILER._compile_line", "ligne vide, on renvoie None", verbose=True)
            log_exit("COMPILER._compile_line", "tokens=%r", tokens, verbose=True)
            return None

        instruction_type, instruction_name = tokens[0]
        log("COMPILER._compile_line", "premier token : type=%r value=%r",
            instruction_type, instruction_name, verbose=True)

        if instruction_type != "ident":
            log("COMPILER._compile_line", "erreur : premier token n'est pas un ident")
            log_exit("COMPILER._compile_line", "ERREUR")
            raise REX_SL(f"instruction non ident : {tokens}")

        match instruction_name:
            
            case "shared_memory":
                if len(tokens) != 2 or tokens[1][0] != "str":
                    raise REX_SL(f"instruction shared_memory non gere : {tokens}")
                if symbol_table["shm_enabled"]:
                    raise REX_SL("shared_memory deja declaree")
                symbol_table["shm_enabled"] = True
                symbol_table["shm_name"] = tokens[1][1]
                log_exit("COMPILER._compile_line", "-> shm activee : %r", tokens[1][1], verbose=True)
                return None  # pas de ligne C ici, juste un flag ; l'init reelle est generee dans compile()
            
            case "change":
                if len(tokens) != 3:
                    raise REX_SL(f"instruction change non gere : {tokens}")
                result = REX_SL_CODE.change(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result
            
            case "showln":  # affichage avec retour a la ligne sur stdout
                log("COMPILER._compile_line", "instruction reconnue : showln", verbose=True)
                result = REX_SL_CODE.show(tokens[1], "\\n")
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result
            
            case "const":  # const <type> <nom> <valeur> ; -> constante explicite, jamais modifiable
                if len(tokens) != 4:
                    raise REX_SL(f"instruction const non gere : {tokens}")
                var_type = tokens[1][1]
                if var_type not in ("number", "float", "bool", "str"):
                    raise REX_SL(f"type de constante non gere : {var_type}")
                if tokens[2][0] != "ident":
                    raise REX_SL(f"nom de constante non gere : {tokens[2][1]}")
                var_name = tokens[2][1]
                if var_name.startswith("RX_"):
                    raise REX_SL(f"nom reserve au registre RX (importe) : {var_name}")
                if var_name in symbol_table["var"]:
                    raise REX_SL(f"variable deja declaree : {var_name}")
                symbol_table["var"][var_name] = var_type
                symbol_table["const_vars"].add(var_name)
                result = REX_SL_CODE.var(var_type, var_name, tokens[3])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "show":  # affichage sans retour a la ligne sur stdout
                log("COMPILER._compile_line", "instruction reconnue : show", verbose=True)
                result = REX_SL_CODE.show(tokens[1], "")
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result
            
            case "share":
                if len(tokens) != 3:
                    raise REX_SL(f"instruction share non gere : {tokens}")
                result = REX_SL_CODE.share(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result
            
            case "pushall":
                if len(tokens) != 1:
                    raise REX_SL(f"instruction pushall non gere : {tokens}")
                result = REX_SL_CODE.pushall()
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "popall":
                if len(tokens) != 1:
                    raise REX_SL(f"instruction popall non gere : {tokens}")
                result = REX_SL_CODE.popall()
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "forward":
                if len(tokens) < 2:
                    raise REX_SL(f"instruction forward non gere (au moins 1 argument attendu) : {tokens}")
                result = REX_SL_CODE.forward(tokens[1:])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "return":
                if len(tokens) != 2:
                    raise REX_SL(f"instruction return non gere : {tokens}")
                result = REX_SL_CODE.return_stmt(tokens[1])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "func":
                # func <nom> [<type> <arg> [= <defaut>]]... [-> <type_retour>];
                if len(tokens) < 2 or tokens[1][0] != "ident":
                    raise REX_SL(f"instruction func non gere : {tokens}")
                param_specs, explicit_ret = _split_func_signature(tokens[2:])
                result = REX_SL_CODE.func_begin(tokens[1], param_specs, explicit_ret_token=explicit_ret)
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "endfunc":
                if len(tokens) != 2 or tokens[1][0] != "ident":
                    raise REX_SL(f"instruction endfunc non gere : {tokens}")
                result = REX_SL_CODE.endfunc(tokens[1])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "exec":
                # exec <nom> [<arg> | <param>=<arg>]...;
                # Chaque argument est soit positionnel (un operande brut), soit
                # nomme (identifiant de parametre '=' operande) -- voir exec_call.
                if len(tokens) < 2 or tokens[1][0] != "ident":
                    raise REX_SL(f"instruction exec non gere : {tokens}")
                raw_args = tokens[2:]
                arg_specs = []
                i = 0
                while i < len(raw_args):
                    tok = raw_args[i]
                    if (tok[0] == "ident" and i + 1 < len(raw_args) and raw_args[i + 1] == ("op", "=")
                            and i + 2 < len(raw_args)):
                        arg_specs.append(("named", tok[1], raw_args[i + 2]))
                        i += 3
                    else:
                        arg_specs.append(("pos", None, tok))
                        i += 1
                result = REX_SL_CODE.exec_call(tokens[1], arg_specs)
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "save":
                if len(tokens) == 3:
                    result = REX_SL_CODE.save_named(tokens[1], tokens[2])
                elif len(tokens) == 2:
                    result = REX_SL_CODE.save_all(tokens[1])
                else:
                    raise REX_SL(f"instruction save non gere : {tokens}")
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "del":
                if len(tokens) != 2:
                    raise REX_SL(f"instruction del non gere : {tokens}")
                result = REX_SL_CODE.shm_del(tokens[1])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result
            
            case "replace":
                if len(tokens) != 5:
                    raise REX_SL(f"instruction replace non gere : {tokens}")
                result = REX_SL_CODE.replace(tokens[1], tokens[2], tokens[3], tokens[4])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "reverse":
                if len(tokens) != 3:
                    raise REX_SL(f"instruction reverse non gere : {tokens}")
                result = REX_SL_CODE.reverse(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "retype":
                # retype <var> <nouveau_type> [<valeur>];
                # Redecrare une variable existante avec un nouveau type.
                # Syntaxe : 2 ou 3 tokens apres le mot-cle.
                if len(tokens) not in (3, 4):
                    raise REX_SL(f"instruction retype non gere (2 ou 3 arguments attendus) : {tokens}")
                new_value_tok = tokens[3] if len(tokens) == 4 else None
                result = REX_SL_CODE.retype(tokens[1], tokens[2], new_value_tok)
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "show_list":  # show_list <list>; | show_list <list> <newline>;
                if len(tokens) not in (2, 3):
                    raise REX_SL(f"instruction show_list non gere : {tokens}")
                coll_tok = tokens[1]
                newline = True  # par defaut avec retour a la ligne
                if len(tokens) == 3:
                    if tokens[2] == ("ident", "nonl"):
                        newline = False
                    else:
                        raise REX_SL(f"show_list: second argument attendu 'nonl' : {tokens[2]}")
                coll_name = coll_tok[1] if coll_tok[0] == "ident" else None
                if not coll_name or REX_SL_CODE._collection_kind(coll_name) != "list":
                    raise REX_SL(f"show_list: operande doit etre une liste declaree : {coll_tok}")
                c_name = REX_SL_CODE._c_name(coll_name)
                symbol_table["rexfn"].append("rexsl_collections")
                symbol_table["rexfn"].append("rexsl_show_list")
                result = f'rexsl_show_list({c_name}, {"1" if newline else "0"});'
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "show_dict":
                if len(tokens) not in (2, 3):
                    raise REX_SL(f"instruction show_dict non gere : {tokens}")
                coll_tok = tokens[1]
                newline = True
                if len(tokens) == 3:
                    if tokens[2] == ("ident", "nonl"):
                        newline = False
                    else:
                        raise REX_SL(f"show_dict: second argument attendu 'nonl' : {tokens[2]}")
                coll_name = coll_tok[1] if coll_tok[0] == "ident" else None
                if not coll_name or REX_SL_CODE._collection_kind(coll_name) != "dict":
                    raise REX_SL(f"show_dict: operande doit etre un dict declare : {coll_tok}")
                c_name = REX_SL_CODE._c_name(coll_name)
                symbol_table["rexfn"].append("rexsl_collections")
                symbol_table["rexfn"].append("rexsl_show_dict")
                result = f'rexsl_show_dict({c_name}, {"1" if newline else "0"});'
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "show_set":
                if len(tokens) not in (2, 3):
                    raise REX_SL(f"instruction show_set non gere : {tokens}")
                coll_tok = tokens[1]
                newline = True
                if len(tokens) == 3:
                    if tokens[2] == ("ident", "nonl"):
                        newline = False
                    else:
                        raise REX_SL(f"show_set: second argument attendu 'nonl' : {tokens[2]}")
                coll_name = coll_tok[1] if coll_tok[0] == "ident" else None
                if not coll_name or REX_SL_CODE._collection_kind(coll_name) != "set":
                    raise REX_SL(f"show_set: operande doit etre un set declare : {coll_tok}")
                c_name = REX_SL_CODE._c_name(coll_name)
                symbol_table["rexfn"].append("rexsl_collections")
                symbol_table["rexfn"].append("rexsl_show_set")
                result = f'rexsl_show_set({c_name}, {"1" if newline else "0"});'
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "show_tuple":
                if len(tokens) not in (2, 3):
                    raise REX_SL(f"instruction show_tuple non gere : {tokens}")
                coll_tok = tokens[1]
                newline = True
                if len(tokens) == 3:
                    if tokens[2] == ("ident", "nonl"):
                        newline = False
                    else:
                        raise REX_SL(f"show_tuple: second argument attendu 'nonl' : {tokens[2]}")
                coll_name = coll_tok[1] if coll_tok[0] == "ident" else None
                if not coll_name or REX_SL_CODE._collection_kind(coll_name) != "tuple":
                    raise REX_SL(f"show_tuple: operande doit etre un tuple declare : {coll_tok}")
                c_name = REX_SL_CODE._c_name(coll_name)
                symbol_table["rexfn"].append("rexsl_collections")
                symbol_table["rexfn"].append("rexsl_show_tuple")
                result = f'rexsl_show_tuple({c_name}, {"1" if newline else "0"});'
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "var":  # declaration de variable : var <type> <nom> [valeur]
                if len(tokens) != 3 and len(tokens) != 4:
                    log("COMPILER._compile_line", "instruction var non gere : %r", tokens)
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction var non gere : {tokens}")

                # tokens[1] peut etre ("ident", "number") ou ("none", None)
                var_type = tokens[1][0] if tokens[1][0] == "none" else tokens[1][1]
                if var_type not in ("number", "float", "bool", "str", "list", "dict", "set", "tuple", "none"):
                    log("COMPILER._compile_line", "type de variable non gere : %r", var_type)
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"type de variable non gere : {var_type}")

                var_name = tokens[2][1]
                if tokens[2][0] != "ident":
                    log("COMPILER._compile_line", "nom de variable non gere : %r", var_name)
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"nom de variable non gere : {var_name}")

                if var_name.startswith("RX_"):
                    log("COMPILER._compile_line", "nom reserve au registre RX (importe) : %r", var_name)
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"nom reserve au registre RX (importe), declaration via var impossible : {var_name}")

                # on enregistre la variable dans le registre des symboles (SL, local)
                if var_name in symbol_table["var"]:
                    log("COMPILER._compile_line", "variable deja declaree : %r", var_name)
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"variable deja declaree : {var_name}")

                symbol_table["var"][var_name] = var_type
                initial_value_token = tokens[3] if len(tokens) == 4 else None

                result = REX_SL_CODE.var(var_type, var_name, initial_value_token)
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "add":  # addition de 2 nombres ou de 2 strings dans une variable
                if len(tokens) != 4:
                    log("COMPILER._compile_line", "instruction add non gere : %r", tokens)
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction add non gere : {tokens}")

                result = REX_SL_CODE.add(tokens[1], tokens[2], tokens[3])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result
            
            case "mul":
                if len(tokens) != 4:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction mul non gere : {tokens}")
                result = REX_SL_CODE.mul(tokens[1], tokens[2], tokens[3])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "sub":
                if len(tokens) != 4:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction sub non gere : {tokens}")
                result = REX_SL_CODE.sub(tokens[1], tokens[2], tokens[3])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result
            
            case "div":
                if len(tokens) != 4:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction div non gere : {tokens}")
                result = REX_SL_CODE.div(tokens[1], tokens[2], tokens[3])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "mod":
                if len(tokens) != 4:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction mod non gere : {tokens}")
                result = REX_SL_CODE.mod(tokens[1], tokens[2], tokens[3])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "pow":  # exposant (0.0.14) : pow <dest> <base> <exposant>;
                if len(tokens) != 4:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction pow non gere : {tokens}")
                result = REX_SL_CODE.pow_op(tokens[1], tokens[2], tokens[3])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result
            
            case "list_str":
                if len(tokens) != 3:
                    raise REX_SL(f"instruction list_str non gere : {tokens}")
                result = REX_SL_CODE.list_str(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "dict_str":
                if len(tokens) != 3:
                    raise REX_SL(f"instruction dict_str non gere : {tokens}")
                result = REX_SL_CODE.dict_str(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "lbl":  # lbl <nom> [<type1> <arg1> <type2> <arg2> ...];
                if len(tokens) < 2 or tokens[1][0] != "ident":
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction lbl non gere : {tokens}")

                label_name = tokens[1][1]
                # les etiquettes declarees a l'interieur d'un 'func' sont locales a la
                # fonction C generee (portee via goto interne, voir go/lbl) et ne doivent
                # PAS etre enregistrees dans symbol_table["labels"] : ce registre sert
                # uniquement au dispatch d'entree de main() via argv[1] ('run <path> <lbl>;'),
                # qui ne peut cibler qu'une etiquette top-level (hors de toute fonction) --
                # un goto C ne peut de toute facon pas traverser une frontiere de fonction
                # (verifie separement par le pre-pass de compile()). Les enregistrer ici
                # generait un 'goto LBL_x;' invalide dans main() vers un label qui n'existe
                # que dans FUNC_<n>, en plus d'exposer une etiquette interne a une fonction
                # comme point d'entree externe du programme.
                if symbol_table["current_func"] is None:
                    if label_name in symbol_table["labels"]:
                        log_exit("COMPILER._compile_line", "ERREUR")
                        raise REX_SL(f"etiquette deja declaree : {label_name}")
                    symbol_table["labels"].append(label_name)
                else:
                    fname = symbol_table["current_func"]
                    local_labels = symbol_table["func_local_labels"].setdefault(fname, set())
                    if label_name in local_labels:
                        log_exit("COMPILER._compile_line", "ERREUR")
                        raise REX_SL(f"etiquette deja declaree dans {fname} : {label_name}")
                    local_labels.add(label_name)

                remaining = tokens[2:]
                if remaining:
                    if symbol_table["current_func"] is not None:
                        raise REX_SL(
                            f"lbl: parametres d'entree ('lbl {label_name} <type> <arg> ...') "
                            f"non geres a l'interieur d'un 'func' -- reserves aux etiquettes "
                            f"top-level ciblees via 'run <path> <lbl> ...;'"
                        )
                    if len(remaining) % 2 != 0:
                        log_exit("COMPILER._compile_line", "ERREUR")
                        raise REX_SL(f"instruction lbl non gere (parametres incomplets) : {tokens}")
                    params = []
                    for i in range(0, len(remaining), 2):
                        type_tok, name_tok = remaining[i], remaining[i + 1]
                        if type_tok[0] != "ident" or type_tok[1] not in ("number", "float", "bool", "str"):
                            raise REX_SL(f"lbl: type de parametre non gere : {type_tok}")
                        if name_tok[0] != "ident":
                            raise REX_SL(f"lbl: nom de parametre non gere : {name_tok}")
                        argname = name_tok[1]
                        if argname in symbol_table["var"]:
                            raise REX_SL(f"lbl: parametre {argname} entre en collision avec une variable existante")
                        symbol_table["var"][argname] = type_tok[1]
                        params.append((type_tok[1], argname))
                    symbol_table["labeled_params"][label_name] = params

                result = REX_SL_CODE.lbl(label_name)
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result
            
            case "go":  # saut conditionnel vers une etiquette : go <nom>
                if len(tokens) != 2 or tokens[1][0] != "ident":
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction go non gere : {tokens}")
                result = REX_SL_CODE.go(tokens[1][1])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "cdn":  # evaluation de condition : cdn <op> <a> <b>  ou  cdn on
                if len(tokens) == 2 and tokens[1] == ("ident", "on"):
                    result = REX_SL_CODE.cdn_on()
                    log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                    return result
                if len(tokens) != 4:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction cdn non gere : {tokens}")
                result = REX_SL_CODE.cdn(tokens[1], tokens[2], tokens[3])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "run":  # run <path>; | run <path> <lbl>; | run <path> <lbl> <v1> <v2> ...;
                if len(tokens) < 2:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction run non gere : {tokens}")
                path_token = tokens[1]
                label_token = tokens[2] if len(tokens) >= 3 else None
                arg_tokens = tokens[3:] if len(tokens) >= 3 else []
                result = REX_SL_CODE.run(path_token, label_token, arg_tokens)
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result
            
            case "scrc":  # scrc <code_c> ; -> injection C brute
                if len(tokens) != 2:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction scrc non gere : {tokens}")
                result = REX_SL_CODE.scrc(tokens[1])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "type":  # type <dest> <op> ; -> nom du type de <op> dans <dest> (str)
                if len(tokens) != 3:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction type non gere : {tokens}")
                result = REX_SL_CODE.type_of(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "append":  # append <list> <valeur> ;
                if len(tokens) != 3:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction append non gere : {tokens}")
                result = REX_SL_CODE.list_append(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "get":
                # Deux formes :
                #   get <coll> <dest> <idx_ou_cle> ;         -- 4 tokens, destination pre-declaree
                #   get <coll> <type> <dest> <idx_ou_cle> ;  -- 5 tokens, auto-declaration avec type hint
                if len(tokens) not in (4, 5):
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction get non gere : {tokens}")
                collection_token = tokens[1]
                collection_kind = (
                    REX_SL_CODE._collection_kind(collection_token[1])
                    if collection_token[0] == "ident" else None
                )
                if collection_kind is None:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"get: collection inconnue : {collection_token}")
                if len(tokens) == 5:
                    # forme etendue : tokens[2]=type_hint, tokens[3]=dest, tokens[4]=idx/cle
                    hint_tok, dest_tok, key_tok = tokens[2], tokens[3], tokens[4]
                    if collection_kind == "list":
                        result = REX_SL_CODE.list_get(collection_token, dest_tok, key_tok, hint_type=hint_tok)
                    elif collection_kind == "dict":
                        # dict_get avec hint : on pre-declare si besoin, comme list
                        result = REX_SL_CODE.dict_get_hinted(collection_token, dest_tok, key_tok, hint_tok)
                    else:
                        raise REX_SL(f"get: type non gere : {collection_kind}")
                else:
                    dest_tok, key_tok = tokens[2], tokens[3]
                    if collection_kind == "list":
                        result = REX_SL_CODE.list_get(collection_token, dest_tok, key_tok)
                    elif collection_kind == "dict":
                        result = REX_SL_CODE.dict_get(collection_token, dest_tok, key_tok)
                    else:
                        log_exit("COMPILER._compile_line", "ERREUR")
                        raise REX_SL(f"get: type non gere (attendu list/dict) : {collection_kind}")
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "pop":  # pop <list> ; | pop <list> <dest> ; | pop <list> <dest> <idx> ;
                if len(tokens) not in (2, 3, 4):
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction pop non gere : {tokens}")
                dest_token = tokens[2] if len(tokens) >= 3 else None
                idx_token = tokens[3] if len(tokens) == 4 else None
                result = REX_SL_CODE.list_pop(tokens[1], dest_token, idx_token)
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "set":  # set <dict> <cle> <valeur> ;
                if len(tokens) != 4:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction set non gere : {tokens}")
                result = REX_SL_CODE.dict_set(tokens[1], tokens[2], tokens[3])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "input":  # input <dest> ;
                if len(tokens) != 2:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction input non gere : {tokens}")
                result = REX_SL_CODE.input_line(tokens[1])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "write":  # write <path> <valeur> ;
                if len(tokens) != 3:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction write non gere : {tokens}")
                result = REX_SL_CODE.write_file(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "read":  # read <path> <dest> ;
                if len(tokens) != 3:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction read non gere : {tokens}")
                result = REX_SL_CODE.read_file(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result
            
            case "len":
                if len(tokens) != 3:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction len non gere : {tokens}")
                result = REX_SL_CODE.len_of(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "list_count":  # list_count <dest_number> <list> ;
                if len(tokens) != 3:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction list_count non gere : {tokens}")
                result = REX_SL_CODE.list_count(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "in":  # in <dest_bool> <valeur> <liste_ou_str> ;
                if len(tokens) != 4:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction in non gere : {tokens}")
                result = REX_SL_CODE.contains_op(tokens[1], False, tokens[2], tokens[3])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "notin":  # notin <dest_bool> <valeur> <liste_ou_str> ;
                if len(tokens) != 4:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction notin non gere : {tokens}")
                result = REX_SL_CODE.contains_op(tokens[1], True, tokens[2], tokens[3])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "isnone":  # isnone <dest_bool> <var> ;
                if len(tokens) != 3:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction isnone non gere : {tokens}")
                result = REX_SL_CODE.isnone(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "charat":
                if len(tokens) != 4:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction charat non gere : {tokens}")
                result = REX_SL_CODE.charat(tokens[1], tokens[2], tokens[3])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "slice":
                if len(tokens) != 5:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction slice non gere : {tokens}")
                result = REX_SL_CODE.slice(tokens[1], tokens[2], tokens[3], tokens[4])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "slicestep":  # slice avec pas (0.0.14) : slicestep <dest> <str> <start> <end> <pas>;
                if len(tokens) != 6:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction slicestep non gere : {tokens}")
                result = REX_SL_CODE.slice_step(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "find":
                if len(tokens) != 4:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction find non gere : {tokens}")
                result = REX_SL_CODE.find(tokens[1], tokens[2], tokens[3])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "upper":
                if len(tokens) != 3:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction upper non gere : {tokens}")
                result = REX_SL_CODE.upper(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "lower":
                if len(tokens) != 3:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction lower non gere : {tokens}")
                result = REX_SL_CODE.lower(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "trim":
                if len(tokens) != 3:
                    log_exit("COMPILER._compile_line", "ERREUR")
                    raise REX_SL(f"instruction trim non gere : {tokens}")
                result = REX_SL_CODE.trim(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result
            
            case "split":
                if len(tokens) != 4:
                    raise REX_SL(f"instruction split non gere : {tokens}")
                result = REX_SL_CODE.split(tokens[1], tokens[2], tokens[3])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "join":
                if len(tokens) != 4:
                    raise REX_SL(f"instruction join non gere : {tokens}")
                result = REX_SL_CODE.join(tokens[1], tokens[2], tokens[3])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "readlines":
                if len(tokens) != 3:
                    raise REX_SL(f"instruction readlines non gere : {tokens}")
                result = REX_SL_CODE.readlines(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case "writelines":
                if len(tokens) != 3:
                    raise REX_SL(f"instruction writelines non gere : {tokens}")
                result = REX_SL_CODE.writelines(tokens[1], tokens[2])
                log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                return result

            case _:
                # pas un mot-cle connu : on tente une reaffectation de variable existante
                # syntaxe : <nom_variable> <nouvelle_valeur>
                if tokens[0][0] == "ident":
                    raw_name = tokens[0][1]

                    if raw_name.startswith("RX_"):
                        log("COMPILER._compile_line", "ecriture RX_ interdite (registre importe) : %r", raw_name)
                        log_exit("COMPILER._compile_line", "ERREUR")
                        raise REX_SL(f"destination RX_ en lecture seule (registre importe) : {raw_name}")

                    if raw_name in symbol_table["const_vars"]:
                        log("COMPILER._compile_line", "reaffectation interdite (constante) : %r", raw_name)
                        log_exit("COMPILER._compile_line", "ERREUR")
                        raise REX_SL(f"reaffectation interdite : {raw_name} est une constante")

                    if raw_name not in symbol_table["var"]:
                        log("COMPILER._compile_line", "variable non gere : %r", raw_name)
                        log_exit("COMPILER._compile_line", "ERREUR")
                        raise REX_SL(f"variable non gere : {raw_name}")

                    var_type = symbol_table["var"][raw_name]
                    var_name = REX_SL_CODE._c_name(raw_name)
                    new_value_token = tokens[1]
                    if new_value_token[0] != var_type:
                        log("COMPILER._compile_line", "type de variable non identique : %r", var_type)
                        log_exit("COMPILER._compile_line", "ERREUR")
                        raise REX_SL(f"type de variable non identique : {var_type}")

                    if var_type == "none":
                        # reassigner none a NULL (idempotent mais explicite)
                        result = f"{var_name} = NULL;"
                    elif var_type == "str":
                        # la reaffectation depend de la strategie de stockage choisie
                        # a la declaration (voir REX_SL_CODE.var), avec un transfert
                        # possible dans un seul sens :
                        #  - variable deja sur le tas (heap_vars) -> on y reste TOUJOURS,
                        #    meme si la nouvelle valeur est courte (pas de retour sur la
                        #    pile) : on libere l'ancienne valeur puis on realloue la nouvelle.
                        #  - variable sur la pile (buffer fixe) :
                        #      - nouvelle valeur qui tient dans le buffer -> simple strcpy,
                        #        la variable reste sur la pile.
                        #      - nouvelle valeur trop grande pour le buffer -> promotion :
                        #        le pointeur est repointe vers une allocation sur le tas
                        #        (rexsl_str_alloc) et la variable est enregistree dans le
                        #        GC (heap_vars) pour etre liberee en fin de programme.
                        new_raw_value = new_value_token[1]
                        escaped_new_value = _escape_c_string(new_raw_value)

                        if _heap_is(var_name):
                            symbol_table["rexfn"].append("rexsl_str_alloc")
                            result = (
                                f'free({var_name});\n'
                                f'    {var_name} = rexsl_str_alloc("{escaped_new_value}");'
                            )
                            log("COMPILER._compile_line",
                                "reaffectation str heap %r -> heap (free + rexsl_str_alloc, "
                                "pas de retour sur la pile)", var_name, verbose=True)
                        elif len(new_raw_value) >= STACK_STR_THRESHOLD:
                            symbol_table["rexfn"].append("rexsl_str_alloc")
                            _heap_mark(var_name)
                            result = f'{var_name} = rexsl_str_alloc("{escaped_new_value}");'
                            log("COMPILER._compile_line",
                                "reaffectation str stack %r -> heap (promotion, valeur "
                                "trop grande pour le buffer : %d >= %d)",
                                var_name, len(new_raw_value), STACK_STR_THRESHOLD, verbose=True)
                        else:
                            result = f'strcpy({var_name}, "{escaped_new_value}");'
                            log("COMPILER._compile_line",
                                "reaffectation str stack %r -> stack (strcpy)", var_name,
                                verbose=True)
                    elif var_type == "bool":
                        bool_literal = "true" if new_value_token[1] else "false"
                        result = f"{var_name} = {bool_literal};"
                    else:
                        result = f"{var_name} = {new_value_token[1]};"

                    log_exit("COMPILER._compile_line", "-> %r", result, verbose=True)
                    return result

        log("COMPILER._compile_line", "instruction inconnue : %r", instruction_name)
        log_exit("COMPILER._compile_line", "ERREUR")
        raise REX_SL(f"instruction non reconnue : {tokens}")

    def compile(self):
        """Compile toutes les lignes de tokens et assemble le fichier C final."""
        log_enter("COMPILER.compile", "nb_lignes=%d", len(self.tokenized_lines))
        c_instructions = []
        for index, tokens in enumerate(self.tokenized_lines):
            if tokens and tokens[0] == ("ident", "shared_memory") and index != 0:
                line_no = self._line_for(index)
                where = f"ligne {line_no} : " if line_no is not None else ""
                raise REX_SL(f"{where}shared_memory doit etre la premiere instruction du programme")

        # --- pre-validation des labels : un 'go' vers une etiquette jamais
        # declaree (faute de frappe...) doit etre une erreur REX-SL claire,
        # plutot qu'un 'goto' C non resolu qui plante gcc avec un message
        # incomprehensible pour un utilisateur du langage.
        # Verifie EGALEMENT que 'go' cible une etiquette declaree dans la MEME
        # fonction (ou toutes deux hors de tout 'func') : un goto C ne peut pas
        # traverser une frontiere de fonction -- sans ce garde-fou, un 'lbl'/'go'
        # mal place a l'interieur d'un 'func' (voir §7, controle de flot dans une
        # fonction recursive) ne serait detecte qu'a la compilation gcc, avec un
        # message peu clair. ---
        declared_labels = set()
        label_owner = {}          # nom d'etiquette -> nom de func l'englobant (None si top-level)
        go_references = []        # [(nom_etiquette, index_ligne, func_englobant_du_go)]
        scan_current_func = None
        for index, tokens in enumerate(self.tokenized_lines):
            if tokens and tokens[0] == ("ident", "func") and len(tokens) >= 2 and tokens[1][0] == "ident":
                scan_current_func = tokens[1][1]
            elif tokens and tokens[0] == ("ident", "endfunc"):
                scan_current_func = None
            if tokens and tokens[0] == ("ident", "lbl") and len(tokens) >= 2 and tokens[1][0] == "ident":
                declared_labels.add(tokens[1][1])
                label_owner[tokens[1][1]] = scan_current_func
            if tokens and tokens[0] == ("ident", "go") and len(tokens) == 2 and tokens[1][0] == "ident":
                go_references.append((tokens[1][1], index, scan_current_func))

        for label_name, index, go_owner in go_references:
            line_no = self._line_for(index)
            where = f"ligne {line_no}" if line_no is not None else f"ligne d'opcode #{index}"
            if label_name not in declared_labels:
                raise REX_SL(
                    f"go: etiquette inconnue '{label_name}' ({where}) "
                    f"-- verifie qu'elle est bien declaree via 'lbl {label_name};'"
                )
            if label_owner.get(label_name) != go_owner:
                raise REX_SL(
                    f"go: l'etiquette '{label_name}' ({where}) n'est pas declaree dans la meme "
                    f"fonction que ce 'go' -- un saut ('goto' C) ne peut pas traverser une "
                    f"frontiere de fonction ('func'/'endfunc')"
                )

        # --- pre-pass des signatures 'func' : rend le PROTOTYPE (params + type de
        # retour explicite eventuel) de chaque fonction visible AVANT que son corps
        # ne soit compile, pour que 'exec' puisse cibler une fonction pas encore
        # atteinte dans le fichier -- necessaire a la recursion indirecte/mutuelle
        # entre deux 'func' (A appelle B, B est declaree plus loin dans le fichier).
        # Le corps reste compile a sa place naturelle par func_begin/endfunc ; ce
        # pre-scan ne fait qu'enregistrer le prototype plus tot. Toute signature
        # malformee est simplement ignoree ici : l'erreur precise sera levee au bon
        # endroit par func_begin lors du passage de compilation normal. ---
        for tokens in self.tokenized_lines:
            if not (tokens and tokens[0] == ("ident", "func") and len(tokens) >= 2 and tokens[1][0] == "ident"):
                continue
            fname = tokens[1][1]
            if fname in symbol_table["functions"]:
                continue
            try:
                param_specs, explicit_ret = _split_func_signature(tokens[2:])
                params = []
                seen = set()
                for type_tok, name_tok, _default_tok in param_specs:
                    if (type_tok[0] != "ident"
                            or type_tok[1] not in ("number", "float", "bool", "str", "list", "dict", "set", "tuple")
                            or name_tok[0] != "ident" or name_tok[1] in seen):
                        raise REX_SL("signature malformee")
                    seen.add(name_tok[1])
                    params.append((type_tok[1], name_tok[1]))
                if explicit_ret is not None:
                    if explicit_ret[0] != "ident" or explicit_ret[1] not in (
                        "number", "float", "bool", "str", "list", "dict", "set", "tuple"
                    ):
                        raise REX_SL("type de retour malforme")
                    ret_type = explicit_ret[1]
                else:
                    ret_type = None
            except REX_SL:
                continue
            symbol_table["functions"][fname] = {
                "params": params, "defaults": {}, "ret_type": ret_type, "_forward_only": True,
            }
            symbol_table["func_order"].append(fname)

        for index, tokens in enumerate(self.tokenized_lines):
            log("COMPILER.compile", "compilation ligne #%d : %r", index, tokens, verbose=True)
            try:
                c_line = self._compile_line(tokens)
            except REX_SL as e:
                # on rattache le numero de ligne source (quand on l'a) au message
                # d'erreur, sans toucher aux ~50 points d'appel de "raise REX_SL"
                # eparpilles dans REX_SL_CODE : un seul endroit a maintenir.
                line_no = self._line_for(index)
                if line_no is not None:
                    raise REX_SL(f"ligne {line_no} : {e}") from None
                raise
            if c_line:
                if symbol_table["current_func"] is not None:
                    symbol_table["function_bodies"][symbol_table["current_func"]].append(c_line)
                    log("COMPILER.compile", "ligne #%d -> corps de %r", index,
                        symbol_table["current_func"], verbose=True)
                else:
                    c_instructions.append(c_line)
                    log("COMPILER.compile", "ligne #%d compilee -> %r", index, c_line, verbose=True)
            else:
                log("COMPILER.compile", "ligne #%d ignoree (vide/None)", index, verbose=True)

        if symbol_table["current_func"] is not None:
            raise REX_SL(f"func {symbol_table['current_func']} sans endfunc correspondant")

        # NOTE (§7) : la recursion directe ou indirecte entre 'func' est desormais
        # SUPPORTEE -- REX-SL genere de vraies fonctions C (avec prototypes emis en
        # avant, voir plus bas) et s'appuie donc nativement sur la pile d'appel C
        # pour la recursion, sans simulation par label/goto. Ce n'est plus une
        # erreur de compilation ; on se contente d'un avertissement informatif
        # (pas de protection contre un stack overflow a l'execution en cas de
        # profondeur excessive -- responsabilite de l'auteur du programme).
        cycle = _detect_recursive_call(symbol_table["call_graph"])
        if cycle:
            sys.stderr.write(
                "[REX-SL] avertissement : recursion (directe ou indirecte) detectee entre "
                f"fonctions func/exec : {' -> '.join(cycle)}. Chaque appel recursif obtient "
                "des variables C locales independantes (pile d'appel C native), aucun etat "
                "global partage n'est corrompu par les appels imbriques. Si le type de retour "
                "d'une fonction recursive n'est pas encore connu au moment d'un appel "
                "recursif/en-avant (le 'return' de base suit textuellement l'appel), "
                "annotez-la explicitement : func <nom> ... -> <type>;\n"
            )

        log("COMPILER.compile", "corps C complet (%d lignes)", len(c_instructions))

        c_source = "#include <stdio.h>\n#include <stdbool.h>\n#include <string.h>\n#include <stdlib.h>\n#include <ctype.h>\n#include <math.h>\n"
        if symbol_table["shm_enabled"]:
            c_source += "#include <sys/mman.h>\n#include <fcntl.h>\n#include <semaphore.h>\n#include <unistd.h>\n#include <stdint.h>\n"
        c_source += "\n"
        c_source += REX_SL_RXFN.resolve()

        # RX_ret doit etre une variable C GLOBALE (et non locale a main()) : les
        # fonctions 'func' compilees (FUNC_<n>) sont des fonctions C independantes,
        # emises AVANT main(), et un 'exec' effectue DANS le corps d'une fonction
        # (appel recursif ou appel a une autre fonction dont la valeur de retour
        # est utilisee) genere du code qui ecrit dans RX_ret -- ce code doit donc
        # pouvoir la referencer depuis n'importe quelle fonction, pas seulement
        # depuis main(). La declarer localement dans main() (comme avant) rendait
        # tout 'exec ... ;' avec valeur de retour utilise a l'interieur d'un 'func'
        # non compilable (RX_ret non declaree dans la portee de FUNC_<n>) -- corrige
        # ici en la promouvant en variable globale, initialisee au debut de main().
        if symbol_table["rx_ret_declared"]:
            c_type = {"number": "int", "float": "float", "bool": "bool", "str": "char*",
                      "list": "RexList*", "dict": "RexDict*",
                      "set": "RexList*", "tuple": "RexList*"}[symbol_table["rx_ret_type"]]
            c_source += f"{c_type} RX_ret;\n"

        # __rexsl_cond (drapeau de condition pour cdn/go) doit egalement etre declare
        # AVANT les fonctions FUNC_<n> : comme RX_ret ci-dessus, une fonction 'func' peut
        # contenir 'cdn'/'go' (controle de flot interne, y compris dans un appel recursif)
        # et referencer cette variable -- la declarer plus loin (juste avant main(), comme
        # avant ce correctif) rendait tout usage de cdn/go a l'interieur d'un 'func' non
        # compilable (identifiant non declare au moment ou gcc rencontre FUNC_<n>).
        c_source += f"static bool {REXSL_COND_VAR} = false;\n"

        c_type_by_kind = {"number": "int", "float": "float", "bool": "bool", "str": "char*",
                          "list": "RexList*", "dict": "RexDict*",
                          "set": "RexList*", "tuple": "RexList*", None: "void", "none": "void"}
        if symbol_table["func_order"]:
            for fname in symbol_table["func_order"]:
                finfo = symbol_table["functions"][fname]
                ret_c = c_type_by_kind[finfo["ret_type"]]
                params_c = ", ".join(
                    f"{c_type_by_kind[t]} SL_{n}" for t, n in finfo["params"]
                ) or "void"
                c_source += f"{ret_c} FUNC_{fname}({params_c});\n"
            c_source += "\n" + "\n".join(symbol_table["compiled_functions_c"]) + "\n"

        # ------------------------------------------------------------
        # WRAPPERS EVO (pour le dispatch argv[] -> FUNC_<name>)
        # ------------------------------------------------------------
        # Chaque fonction exportee recoit un wrapper _evo_wrap_<name>(char** argv, int argc)
        # qui convertit les argv[2..] en types C attendus par FUNC_<name>, l'appelle,
        # et imprime le resultat sur stdout.  Ces wrappers sont appeles depuis main()
        # quand argv[1] == nom de la fonction, et sont separes de FUNC_ pour ne pas
        # modifier la signature de celle-ci (qui peut etre int/float/bool, pas char*).
        exported_fns = [
            fname for fname in symbol_table["func_order"]
            if not fname.startswith("__rx_")
        ]
        _c_conv = {
            "number": lambda i: f"(argc > {i}) ? atoi(argv[{i}]) : 0",
            "float":  lambda i: f"(argc > {i}) ? (float)atof(argv[{i}]) : 0.0f",
            "bool":   lambda i: f"(argc > {i}) && (argv[{i}][0] == 't' || argv[{i}][0] == '1')",
            "str":    lambda i: f"(argc > {i}) ? argv[{i}] : \"\"",
        }
        if exported_fns:
            for fname in exported_fns:
                finfo = symbol_table["functions"][fname]
                params = finfo["params"]
                ret_type = finfo["ret_type"]
                ret_c = c_type_by_kind[ret_type]
                c_source += f"static void _evo_wrap_{fname}(int argc, char** argv) {{\n"
                for i, (ptype, pname) in enumerate(params):
                    argv_i = i + 2
                    ctype = c_type_by_kind.get(ptype, "char*")
                    conv = _c_conv.get(ptype, lambda j: f"(argc > {j}) ? argv[{j}] : \"\"")(argv_i)
                    c_source += f"    {ctype} _a{i} = {conv};\n"
                call_args = ", ".join(f"_a{i}" for i in range(len(params)))
                if ret_type in (None, "none"):
                    c_source += f"    FUNC_{fname}({call_args});\n"
                elif ret_type == "str":
                    c_source += f"    char* _r = FUNC_{fname}({call_args});\n"
                    c_source += '    if (_r) printf("%s\\n", _r);\n'
                elif ret_type == "number":
                    c_source += f"    printf(\"%d\\n\", FUNC_{fname}({call_args}));\n"
                elif ret_type == "float":
                    c_source += f"    printf(\"%g\\n\", FUNC_{fname}({call_args}));\n"
                elif ret_type == "bool":
                    c_source += f"    printf(\"%s\\n\", FUNC_{fname}({call_args}) ? \"true\" : \"false\");\n"
                else:
                    c_source += f"    FUNC_{fname}({call_args});\n"
                c_source += "}\n"
        
        c_source += "\nint main(int argc, char** argv) {\n"
        # Meme correctif qu'endfunc() (voir §bug connu, tete de fichier) : les
        # variables str/list/dict de premiere-declaration heap au niveau
        # top-level (hors de tout 'func') sont hissees a NULL ici, en tete de
        # main(), pour rester sures si un 'cdn ...; go ...;' ou le dispatch
        # d'entree ('run <path> <lbl>;', voir plus bas) saute par-dessus leur
        # declaration d'origine.
        _main_hoisted_colls = [
            (n, k) for n, k in symbol_table["collection_vars"][0]
            if n in symbol_table["collection_hoist"][0]
        ]
        for _hoist_line in _hoisted_decl_lines(symbol_table["heap_str_decls"][0], _main_hoisted_colls):
            c_source += f"    {_hoist_line}\n"
        if symbol_table["rx_ret_declared"]:
            default_val = "0"
            if symbol_table["rx_ret_type"] == "str":
                symbol_table["rexfn"].append("rexsl_str_alloc")
                c_source += f'    RX_ret = rexsl_str_alloc("");\n'
            else:
                c_source += f"    RX_ret = {default_val};\n"
                
        if symbol_table["shm_enabled"]:
            escaped_shm_name = _escape_c_string(symbol_table["shm_name"])
            c_source += f'    rexsl_shm_init("{escaped_shm_name}");\n'


        c_default = {"number": "0", "float": "0", "bool": "false"}
        for _label_name, _params in symbol_table["labeled_params"].items():
            for ptype, pname in _params:
                c_name = f"SL_{pname}"
                if ptype == "str":
                    c_source += f'    char* {c_name} = "";\n'
                else:
                    c_type = {"number": "int", "float": "float", "bool": "bool"}[ptype]
                    c_source += f"    {c_type} {c_name} = {c_default[ptype]};\n"
                    
        # ------------------------------------------------------------
        # HANDLER METAFN (pour 'evo-import' depuis un autre module REX)
        # ------------------------------------------------------------
        # Si ce programme est lance avec argv[1] == "metafn", il affiche sur stdout
        # un JSON decrivant toutes les fonctions exportees, puis quitte.
        # Format : {"functions": [{"name": "f", "params": [["str","x"]], "return": "none"}, ...]}
        # Seules les fonctions publiques (ne commencant pas par __rx_) sont exposees.
        exported_fns = [
            fname for fname in symbol_table["func_order"]
            if not fname.startswith("__rx_")
        ]
        if exported_fns:
            log("COMPILER.compile", "generation du handler metafn pour %d fonction(s) : %r",
                len(exported_fns), exported_fns)
            c_source += '    if (argc > 1 && strcmp(argv[1], "metafn") == 0) {\n'
            c_source += '        int _mfn_first = 1;\n'
            c_source += '        printf("{\\"functions\\": [");\n'
            for fname in exported_fns:
                finfo = symbol_table["functions"][fname]
                ret_json = "none" if finfo["ret_type"] in (None, "none") else finfo["ret_type"]
                escaped_fname = _escape_c_string(fname)
                escaped_ret   = _escape_c_string(ret_json)
                # Construire la partie params en JSON pur (guillemets normaux),
                # puis echapper les guillemets une seule fois pour les mettre
                # dans un litteral C (printf("...")).
                params = finfo["params"]
                if params:
                    parts = []
                    for ptype, pname in params:
                        # _escape_c_string protege contre les chars speciaux dans
                        # les noms, mais on travaille encore en JSON brut ici.
                        safe_pt = _escape_c_string(ptype)
                        safe_pn = _escape_c_string(pname)
                        parts.append(f'["{safe_pt}","{safe_pn}"]')
                    params_json = ",".join(parts)
                    entry = (
                        f'{{"name":"{escaped_fname}",'
                        f'"params":[{params_json}],'
                        f'"return":"{escaped_ret}"}}'
                    )
                else:
                    entry = (
                        f'{{"name":"{escaped_fname}",'
                        f'"params":[],'
                        f'"return":"{escaped_ret}"}}'
                    )
                # Echapper les guillemets pour le litteral C (une seule passe)
                escaped_entry = entry.replace('"', '\\"')
                c_source += f'        if (_mfn_first) {{ printf("{escaped_entry}"); _mfn_first = 0; }}\n'
                c_source += f'        else {{ printf(",{escaped_entry}"); }}\n'
            c_source += '        printf("]}\\n");\n'
            c_source += '        return 0;\n'
            c_source += '    }\n'
        else:
            # Pas de fonctions exportees : repondre quand meme a metafn avec une liste vide
            c_source += '    if (argc > 1 && strcmp(argv[1], "metafn") == 0) {\n'
            c_source += '        printf("{\\"functions\\": []}\\n");\n'
            c_source += '        return 0;\n'
            c_source += '    }\n'

        # ------------------------------------------------------------
        # DISPATCH DE FONCTIONS (pour 'evo-import' : ./module funcname arg1 arg2 ...)
        # ------------------------------------------------------------
        # Delegue aux wrappers _evo_wrap_<name> generes avant main(),
        # qui se chargent de la conversion argv[] -> types C corrects.
        if exported_fns:
            c_source += "    if (argc > 1) {\n"
            for fname in exported_fns:
                escaped_fname = _escape_c_string(fname)
                c_source += f'        if (strcmp(argv[1], "{escaped_fname}") == 0) {{\n'
                c_source += f'            _evo_wrap_{fname}(argc, argv);\n'
                c_source += '            return 0;\n'
                c_source += '        }\n'
            c_source += "    }\n"

        # DISPATCH D'ENTREE DYNAMIQUE (pour 'run <path> <lbl>;' venant d'un autre module)
        # ------------------------------------------------------------
        # Si ce programme est lance avec un argument (argv[1]), on considere que c'est
        # le nom d'une etiquette locale et on saute directement dessus au lieu de partir
        # du debut de main(). C'est ce qui permet a un AUTRE module de dire "run moi lbl;"
        # et d'atterrir precisement a cette etiquette -- la resolution se fait au runtime
        # (fork/exec via system(), voir REX_SL_CODE.run), pas a la compilation.
        
        if symbol_table["labels"]:
            log("COMPILER.compile", "generation du dispatch d'entree pour %d etiquette(s) : %r",
                len(symbol_table["labels"]), symbol_table["labels"])
            c_source += "    if (argc > 1) {\n"
            for label_name in symbol_table["labels"]:
                escaped_label = _escape_c_string(label_name)
                params = symbol_table["labeled_params"].get(label_name, [])
                c_source += f'        if (strcmp(argv[1], "{escaped_label}") == 0) {{\n'
                for i, (ptype, pname) in enumerate(params):
                    argv_index = i + 2  # argv[0]=exe, argv[1]=label, argv[2..]=args
                    c_name = f"SL_{pname}"
                    if ptype == "number":
                        c_source += f'            {c_name} = atoi(argv[{argv_index}]);\n'
                    elif ptype == "float":
                        c_source += f'            {c_name} = (float)atof(argv[{argv_index}]);\n'
                    elif ptype == "bool":
                        c_source += (
                            f"            {c_name} = (argv[{argv_index}][0] == 't' "
                            f"|| argv[{argv_index}][0] == '1');\n"
                        )
                    else:  # str : pointeur direct dans argv, jamais libere (pas heap-tracke)
                        c_source += f'            {c_name} = argv[{argv_index}];\n'
                c_source += f"            goto LBL_{label_name};\n"
                c_source += "        }\n"
            c_source += '        fprintf(stderr, "[REX-SL] erreur : etiquette inconnue : %s\\n", argv[1]);\n'
            c_source += "        exit(1);\n"
            c_source += "    }\n"
        else:
            log("COMPILER.compile", "aucune etiquette declaree -> pas de dispatch d'entree genere")

        for instruction in c_instructions:
            c_source += f"    {instruction}\n"
            
        if symbol_table["scope_depth"] != 0:
            raise REX_SL(f"pushall sans popall correspondant ({symbol_table['scope_depth']} scope(s) ouvert(s))")

        for _free_line in _conditional_free_lines(symbol_table["heap_vars"][0], symbol_table["collection_vars"][0]):
            c_source += f"    {_free_line}\n"
    
        c_source += "\n    printf(\"\\n\");\n    return 0;\n}\n"

        log("COMPILER.compile", "code C final genere :\n%s", c_source, verbose=True)
        log("COMPILER.compile", "variables enregistrees : %r", symbol_table["var"], verbose=True)
        log_exit("COMPILER.compile", "nb_lignes=%d", len(self.tokenized_lines))
        return c_source


def build_arg_parser():
    """Construit le parseur d'arguments en ligne de commande du compilateur."""
    parser = argparse.ArgumentParser(
        prog="rex_sl",
        description="REX-SL compiler",
    )
    parser.add_argument(
        "-o", "--oneline",
        metavar="CODE",
        help="code REX-SL a traiter (sur une seule ligne, instructions separees par ;)",
    )
    parser.add_argument(
        "-f", "--file",
        metavar="FILE",
        help="fichier REX-SL a traiter (necessite le header REX-SL)",
    )
    parser.add_argument(
        "-O", "--output",
        metavar="OUTPUT_FILE",
        dest="output",
        help="nom du fichier executable (et du .c intermediaire) genere. "
             "Par defaut : meme nom que le script source passe via -f/--file "
             "(sans son extension), ou 'rex_sl_output' en mode -o/--oneline.",
    )
    parser.add_argument(
        "-c", "--compiler",
        action="store_true",
        help="compile le code REX-SL en C puis en executable",
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
        "--force-shm-nogc",
        action="store_true",
        dest="force_shm_nogc",
        help="desactive la confirmation interactive si des cles shm ne sont jamais "
            "supprimees, et insere directement un GC automatique",
    )

    # --debug et --stylish sont mutuellement exclusifs : un seul mode de debug a la fois
    debug_group = parser.add_mutually_exclusive_group()
    debug_group.add_argument(
        "--debug",
        action="store_true",
        help="affiche quelques informations de debug (etapes principales, sans le detail)",
    )
    debug_group.add_argument(
        "--stylish",
        action="store_true",
        help="affiche un debug complet et colore (colorama) avec toute la trace detaillee",
    )
    return parser


def main():
    global MODE

    parser = build_arg_parser()
    args = parser.parse_args()

    # choix du mode de debug en fonction des arguments CLI
    if args.stylish:
        MODE = "stylish"
        if not HAS_COLORAMA:
            print("[REX-SL] colorama n'est pas installe, --stylish s'affichera sans couleur "
                  "(pip install colorama)", file=sys.stderr)
    elif args.debug:
        MODE = "debug"
    else:
        MODE = "off"

    log_separator("MAIN", "DEMARRAGE REX-SL COMPILER")
    log("MAIN", "arguments parses : %r", args)

    if not args.oneline and not args.file:
        parser.error("aucun code fourni, utilise -o/--oneline ou -f/--file \"...\"")

    # recuperation du code source, soit directement en ligne de commande, soit depuis un fichier
    if args.oneline:
        source_code = args.oneline
        if not source_code.strip():
            parser.error("le code fourni via -o/--oneline est vide")
    else:
        # garde-fou : le fichier peut ne pas exister, ne pas etre lisible,
        # etre un dossier, ou contenir un encodage invalide -> on evite un
        # traceback brut et on donne un message exploitable
        if not os.path.exists(args.file):
            parser.error(f"le fichier {args.file} n'existe pas")
        if os.path.isdir(args.file):
            parser.error(f"{args.file} est un dossier, pas un fichier")
        try:
            with open(args.file, encoding="utf-8") as f:
                source_code = f.read()
        except PermissionError:
            parser.error(f"permission refusee pour lire {args.file}")
        except UnicodeDecodeError as e:
            parser.error(f"encodage invalide dans {args.file} (utf-8 attendu) : {e}")
        except OSError as e:
            parser.error(f"impossible de lire {args.file} : {e}")

        if not source_code.strip():
            parser.error(f"fichier {args.file} est vide")
        if not source_code.startswith("# REX-SL>"):
            parser.error(f"pas de header REX-SL dans {args.file}")

    log("MAIN", "code REX-SL fourni :\n%s", source_code)

    log_separator("MAIN", "PHASE LEXER")
    try:
        lexer = REX_SL_LEXER(source_code)
    except REX_SL as e:
        log("ERROR", "exception REX_SL attrapee pendant le lexing : %s", e)
        print(f"[REX-SL] erreur lexicale : {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # garde-fou generique : un bug interne du lexer ne doit pas produire
        # un traceback Python brut cote utilisateur final
        log("ERROR", "exception inattendue pendant le lexing : %r", e)
        print(f"[REX-SL] erreur interne inattendue pendant le lexing : {e}", file=sys.stderr)
        if MODE != "off":
            raise
        sys.exit(1)
    log("MAIN", "lexer termine, tokens=%r", lexer.tokens)

    if not lexer.tokens:
        print("[REX-SL] attention : aucun token produit (code source vide ou entierement "
              "commente), rien a faire", file=sys.stderr)
        log_separator("MAIN", "FIN (aucun token)")
        return

    # -r implique -c : pas de sens de "run" sans compiler avant
    should_compile = args.compiler or args.run
    log("MAIN", "should_compile=%r (compiler=%r, run=%r)", should_compile, args.compiler, args.run)

    if not should_compile:
        # sans -c ni -r, on se contente d'afficher les tokens bruts (mode debug/inspection)
        log("MAIN", "mode affichage brut des tokens (pas de compilation)")
        for line in lexer.tokens:
            print(line)
        log_separator("MAIN", "FIN (mode tokens)")
        return

    log_separator("MAIN", "PHASE COMPILATION PYTHON -> C")
    try:
        assignment_counts = _scan_assignment_counts(lexer.tokens)
        symbol_table["const_vars"] = {name for name, c in assignment_counts.items() if c == 1}
        log("MAIN", "variables auto-const detectees : %r", symbol_table["const_vars"])
        compiler = REX_SL_COMPILER(lexer.tokens, getattr(lexer, "opcode_lines", None))
        c_source = compiler.compile()
    except REX_SL as e:
        log("ERROR", "exception REX_SL attrapee : %s", e)
        print(f"[REX-SL] erreur de compilation : {e}", file=sys.stderr)
        sys.exit(1)
    except RecursionError:
        # garde-fou : un programme REX-SL pathologique (deeply nested func/exec,
        # boucle de compilation) peut faire deborder la pile Python du compilateur
        # lui-meme, bien avant meme d'atteindre la detection de recursion REX-SL
        log("ERROR", "RecursionError pendant la compilation (programme trop profond/complexe)")
        print("[REX-SL] erreur : le programme source est trop complexe/imbrique pour etre "
              "compile (limite de recursion Python atteinte)", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # garde-fou generique : tout bug non anticipe dans le compilateur ne doit
        # jamais remonter comme un traceback Python brut a l'utilisateur final
        log("ERROR", "exception inattendue pendant la compilation : %r", e)
        print(f"[REX-SL] erreur interne inattendue pendant la compilation : {e}", file=sys.stderr)
        if MODE != "off":
            raise
        sys.exit(1)

    if symbol_table["shm_enabled"]:
        orphan_keys = sorted(set(symbol_table["shm_shared_keys"]) - set(symbol_table["shm_deleted_keys"]))
        if orphan_keys:
            def _insert_shm_gc(c_source, orphan_keys):
                gc_calls = "\n".join(f'    rexsl_shm_del("{_escape_c_string(k)}");' for k in orphan_keys)
                gc_fn = f"\nvoid rexsl_shm_gc_atexit(void) {{\n{gc_calls}\n}}\n"
                c_source = c_source.replace(
                    f'rexsl_shm_init("{_escape_c_string(symbol_table["shm_name"])}");',
                    f'rexsl_shm_init("{_escape_c_string(symbol_table["shm_name"])}");\n    atexit(rexsl_shm_gc_atexit);',
                )
                c_source = c_source.replace("int main(int argc, char** argv) {", gc_fn + "\nint main(int argc, char** argv) {")
                return c_source

            if not args.force_shm_nogc:
                print(f"[REX-SL] attention : {len(orphan_keys)} cle(s) shm jamais supprimee(s) : "
                    f"{', '.join(orphan_keys)}", file=sys.stderr)
                # garde-fou : input() leve EOFError si stdin n'est pas interactif
                # (script, pipe, CI...) -> on ne doit pas planter, on part sur le
                # comportement par defaut (pas de GC) comme pour une reponse vide
                try:
                    answer = input("Implementer un GC automatique pour ces cles ? [y/N] ")
                except EOFError:
                    log("MAIN", "stdin non interactif, reponse par defaut (N) pour le GC shm")
                    answer = "n"
                if answer.strip().lower() == "y":
                    c_source = _insert_shm_gc(c_source, orphan_keys)
                # sinon : on continue simplement sans GC, pas de sys.exit(1)
            else:
                c_source = _insert_shm_gc(c_source, orphan_keys)

    # ------------------------------------------------------------
    # NOM DU FICHIER DE SORTIE : par defaut, meme nom que le script
    # source (-f), sans extension ; 'rex_sl_output' en mode -o/--oneline ;
    # ecrase dans tous les cas si -O/--output est fourni.
    # ------------------------------------------------------------
    if args.output:
        executable_path = args.output
    elif args.file:
        executable_path = os.path.splitext(os.path.basename(args.file))[0]
    else:
        executable_path = "rex_sl_output"

    # garde-fou : un nom de sortie vide/invalide (ex: -O "" ou -O ".") ne doit
    # pas produire un fichier illisible plus tard ni ecraser le dossier courant
    if not executable_path.strip() or executable_path in (".", ".."):
        parser.error(f"nom de sortie invalide : {executable_path!r}")

    c_file_path = executable_path + ".c"
    log("MAIN", "c_file_path=%r executable_path=%r", c_file_path, executable_path)

    # garde-fou : eviter d'ecraser le fichier source REX-SL lui-meme si -O
    # pointe (par erreur) vers le meme chemin que le .c genere
    if args.file and os.path.abspath(c_file_path) == os.path.abspath(args.file):
        parser.error(f"le fichier C genere ({c_file_path}) ecraserait le fichier "
                      f"source {args.file}, choisis un autre -O/--output")

    try:
        with open(c_file_path, "w") as f:
            f.write(c_source)
    except OSError as e:
        log("ERROR", "impossible d'ecrire le fichier C genere : %r", e)
        print(f"[REX-SL] erreur : impossible d'ecrire {c_file_path} : {e}", file=sys.stderr)
        sys.exit(1)
    log("MAIN", "fichier C ecrit sur disque : %s", c_file_path)

    def _cleanup_c_file():
        """Supprime le .c intermediaire, sans planter si deja absent/verrouille."""
        if args.keep_c:
            log("MAIN", "fichier C conserve (--keep-c) : %s", c_file_path)
            return
        try:
            os.remove(c_file_path)
            log("MAIN", "fichier C supprime : %s", c_file_path)
        except OSError as e:
            log("ERROR", "impossible de supprimer le fichier C intermediaire : %r", e)
            print(f"[REX-SL] attention : impossible de supprimer {c_file_path} : {e}",
                  file=sys.stderr)

    log_separator("MAIN", "PHASE COMPILATION C (gcc)")

    # garde-fou : verifier que gcc est bien installe/accessible avant de lancer
    # subprocess.run, plutot que de laisser remonter un FileNotFoundError brut
    if shutil.which("gcc") is None:
        log("ERROR", "gcc introuvable dans le PATH")
        print("[REX-SL] erreur : gcc est introuvable. Installe un compilateur C "
              "(ex: apt install gcc) ou verifie ton PATH.", file=sys.stderr)
        _cleanup_c_file()
        sys.exit(1)

    gcc_cmd = ["gcc", c_file_path, "-o", executable_path, "-lm"]
    if symbol_table["shm_enabled"]:
        gcc_cmd += ["-lrt", "-pthread"]
    log("MAIN", "commande executee : %s", " ".join(gcc_cmd))
    try:
        gcc_result = subprocess.run(gcc_cmd)
    except OSError as e:
        # garde-fou : gcc present dans le PATH mais inexecutable (permissions,
        # binaire casse...), ou toute autre erreur au lancement du process
        log("ERROR", "echec du lancement de gcc : %r", e)
        print(f"[REX-SL] erreur : impossible de lancer gcc : {e}", file=sys.stderr)
        _cleanup_c_file()
        sys.exit(1)
    log("MAIN", "gcc termine avec returncode=%d", gcc_result.returncode)

    if gcc_result.returncode != 0:
        log("ERROR", "echec de la compilation C, nettoyage puis sortie")
        print("[REX-SL] erreur : la compilation C a echoue", file=sys.stderr)
        _cleanup_c_file()
        sys.exit(1)

    _cleanup_c_file()

    if args.run:
        log_separator("MAIN", "PHASE EXECUTION DE L'EXECUTABLE")
        abs_executable_path = os.path.abspath(executable_path)
        log("MAIN", "lancement de : %s", abs_executable_path)
        try:
            run_result = subprocess.run([abs_executable_path])
            log("MAIN", "execution terminee avec returncode=%d", run_result.returncode)
            if run_result.returncode != 0:
                print(f"[REX-SL] attention : l'executable s'est termine avec le code "
                      f"{run_result.returncode}", file=sys.stderr)
        except PermissionError:
            log("ERROR", "permission refusee pour executer %s", abs_executable_path)
            print(f"[REX-SL] erreur : permission refusee pour executer {abs_executable_path}",
                  file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            log("ERROR", "impossible d'executer %s : %r", abs_executable_path, e)
            print(f"[REX-SL] erreur : impossible d'executer {abs_executable_path} : {e}",
                  file=sys.stderr)
            sys.exit(1)

    log_separator("MAIN", "FIN NORMALE DU PROGRAMME")
    
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # garde-fou : Ctrl+C ne doit pas afficher un traceback, juste sortir proprement
        print("\n[REX-SL] interrompu par l'utilisateur", file=sys.stderr)
        sys.exit(130)
    except SystemExit:
        # laisse passer les sys.exit()/parser.error() deja geres plus haut
        raise
    except Exception as e:
        # dernier filet de securite : tout ce qui n'a pas ete attrape plus haut
        # (bug reellement imprevu) sort proprement plutot qu'en traceback brut
        print(f"[REX-SL] erreur interne inattendue : {e}", file=sys.stderr)
        sys.exit(1)