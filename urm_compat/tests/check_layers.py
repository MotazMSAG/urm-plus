"""
The layers of the add-on: a piece uses names only from its own group or
from a group below it.

    python tests/check_layers.py            check the pieces
    python tests/check_layers.py --record   write baseline/layer_links.txt
                                            from what the pieces do now

The add-on is meant to be a stack: the hooks at the bottom, then the story
graph, then the script index, then the features on top. A layer uses only
the layers below it, and a feature never uses another feature. GROUPS below
says which piece is in which layer.

What counts as a use: a name a piece reads (or writes through `global`) in
its code that another piece defines at block level (a def, a class, an
assignment) - also when it keeps a stand-in of that name itself, since the
other piece's definition replaces it while the game loads. Names that only
appear in comments or strings do not count, and a function's own local
names are not mixed up with another piece's.

The links that go the wrong way today are listed in baseline/layer_links.txt,
one line per pair of pieces. The check fails on
  - a wrong-way link that is not in that list (a new one: move the name to
    a lower layer instead), and
  - a listed link that is gone (good news: take it out of the list, so the
    list only ever shrinks).

The URM+ menu and settings window (piece and screens 17_hub, HUB) reach
the features only through what they registered in the doorway: they name
no feature's function, class or screen anywhere, not even in a string.

The pieces are read through urm_source.py (URM_CHECK_SOURCE may name
another folder of pieces, to prove the check can fail). Static: nothing is
run. Python 2.7 and 3.
"""

from __future__ import print_function

import ast
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import urm_source  # noqa

LINKS = os.path.join(HERE, "baseline", "layer_links.txt")

# The layers. (group, rank, piece numbers). A piece may use names from its
# own group or from a group of LOWER rank. Every feature has the same rank,
# so a feature using another feature is a wrong-way link.
FEATURE = 9
GROUPS = (
    ("core.hooks", 0, ("00", "01", "02")),
    ("core.graph", 1, ("10", "11", "12")),
    ("core.index", 2, ("60",)),
    ("core.now", 3, ("13", "61")),
    ("core.facts", 4, ("14", "72")),
    ("core.words", 5, ("15", "16", "17", "18", "35", "73")),
    ("cards", FEATURE, ("20",)),
    ("map", FEATURE, ("30", "31", "32", "33", "34")),
    ("chip", FEATURE, ("40",)),
    ("search", FEATURE, ("50",)),
    ("extras", FEATURE, ("55",)),
    ("codeview", FEATURE, ("56",)),
    ("panel", FEATURE, ("70", "71", "74")),
    ("gallery", FEATURE, ("80",)),
    ("rollback", FEATURE, ("81",)),
    ("force", FEATURE, ("82",)),
    ("flags", FEATURE, ("83",)),
    ("skip", FEATURE, ("84",)),
    ("alerts", FEATURE, ("85",)),
    ("percent", FEATURE, ("86",)),
    ("font", FEATURE, ("87",)),
    ("pins", FEATURE, ("88",)),
    ("saves", FEATURE, ("89",)),
)

GROUP_OF = dict((number, (group, rank))
                for group, rank, numbers in GROUPS for number in numbers)
# A new feature needs no line in GROUPS: a piece number it does not list is a
# feature layer named by its file name (game_fixes/91_notes.rpy and
# 92_notes_view.rpy: the layer "notes"; found_layer). These names are taken:
# a listed layer, a core layer's word ("words" for core.words), tools.
RESERVED = (set(g for g, _r, _n in GROUPS) | set(g.split(".", 1)[-1] for g, _r, _n in GROUPS)
            | set(["tools"]))

FUNCS = tuple(getattr(ast, n) for n in ("FunctionDef", "AsyncFunctionDef")
              if hasattr(ast, n))
COMPS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
NEW_SCOPE = FUNCS + COMPS + (ast.ClassDef, ast.Lambda)


class LayerError(Exception):
    pass


# ------------------------------------------------------------ the blocks

def blocks(folder):
    """[(code at column 0, joined line of its first line, piece of each
    joined line)] for every init python block of the joined source."""

    if not os.path.isdir(folder):
        raise LayerError("%s is not a folder of pieces: the layers are "
                         "per piece." % folder)

    piece_of = {}
    for name, first, count, _continues in urm_source.layout(folder):
        for line in range(first, first + count):
            piece_of[line] = name[:-len(".rpy")]

    lines = urm_source.read(folder).split(u"\n")
    heads = [n for n, line in enumerate(lines)
             if line in (urm_source.HEADER, urm_source.EARLY)]
    out = []
    for head in heads:
        end = head + 1
        while end < len(lines):
            line = lines[end]
            if line and not line.startswith((u" ", u"#")):
                break
            end += 1
        code = u"\n".join(line[4:] if line.startswith(u"    ") else line
                          for line in lines[head + 1:end])
        # Joined lines count from 1; the code's line 1 is the one after
        # the header.
        out.append((code, head + 2, piece_of))
    return out


def parse(code, first, piece_of):
    try:
        return ast.parse(code)
    except SyntaxError as e:
        line = first + (e.lineno or 1) - 1
        raise LayerError("the block at joined line %d does not parse "
                         "(%s line %s): %s"
                         % (first - 1, piece_of.get(line, "?"), line, e))


# ------------------------------------------------------------ the names

def arg_names(args):
    out = set()
    for field in ("posonlyargs", "args", "kwonlyargs"):
        for a in getattr(args, field, None) or ():
            out.add(getattr(a, "arg", None) or getattr(a, "id", None))
    for field in ("vararg", "kwarg"):
        a = getattr(args, field, None)
        if a is not None:
            out.add(a if isinstance(a, str) else getattr(a, "arg", None))
    out.discard(None)
    return out


def bound(body):
    """(names a scope binds, names it declares global), not looking into
    the scopes nested in it."""

    names, glob = set(), set()
    todo = list(body)
    while todo:
        node = todo.pop()
        if isinstance(node, FUNCS + (ast.ClassDef,)):
            names.add(node.name)
            continue
        if isinstance(node, (ast.Lambda,) + COMPS):
            continue
        if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load):
            names.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.Global):
            glob.update(node.names)
        elif isinstance(node, getattr(ast, "Nonlocal", ())):
            names.update(node.names)
        elif isinstance(node, ast.ExceptHandler) and isinstance(node.name, str):
            names.add(node.name)
        todo.extend(ast.iter_child_nodes(node))
    return names - glob, glob


def defines(tree, first, piece_of, out):
    """Block-level definitions: {name: set of pieces}. Imports are left
    out: a module two pieces import is nobody's layer."""

    todo = list(tree.body)
    while todo:
        node = todo.pop()
        piece = piece_of[first + node.lineno - 1] if hasattr(node, "lineno") else None
        if isinstance(node, FUNCS + (ast.ClassDef,)):
            out.setdefault(node.name, set()).add(piece)
            continue
        if isinstance(node, (ast.Lambda,) + COMPS):
            continue
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            out.setdefault(node.id, set()).add(piece)
        todo.extend(ast.iter_child_nodes(node))


def uses(node, scopes, first, piece_of, out):
    """[(piece, name, at load)] every name the code reads, or writes through
    `global`, that is not one of its own local names; "at load" when the
    code runs while the game loads (outside every function). `scopes` is
    the enclosing scopes, innermost last: (kind, names)."""

    def visible(name):
        return any(name in names for _kind, names in scopes)

    def inner(local, kind="func"):
        # A function nested in a class does not see the class's names.
        return [s for s in scopes if s[0] != "class"] + [(kind, local)]

    if isinstance(node, FUNCS):
        for d in node.decorator_list:
            uses(d, scopes, first, piece_of, out)
        for d in list(node.args.defaults) + [k for k in getattr(node.args, "kw_defaults", ()) if k]:
            uses(d, scopes, first, piece_of, out)
        local, _glob = bound(node.body)
        local |= arg_names(node.args)
        for child in node.body:
            uses(child, inner(local), first, piece_of, out)
        return

    if isinstance(node, ast.ClassDef):
        for d in node.decorator_list + node.bases + [k.value for k in getattr(node, "keywords", ())]:
            uses(d, scopes, first, piece_of, out)
        local, _glob = bound(node.body)
        for child in node.body:
            uses(child, scopes + [("class", local)], first, piece_of, out)
        return

    if isinstance(node, ast.Lambda):
        for d in list(node.args.defaults) + [k for k in getattr(node.args, "kw_defaults", ()) if k]:
            uses(d, scopes, first, piece_of, out)
        uses(node.body, inner(arg_names(node.args)), first, piece_of, out)
        return

    if isinstance(node, COMPS):
        local = set()
        for gen in node.generators:
            for n in ast.walk(gen.target):
                if isinstance(n, ast.Name):
                    local.add(n.id)
        for child in ast.iter_child_nodes(node):
            uses(child, inner(local, "comp"), first, piece_of, out)
        return

    if isinstance(node, ast.Name) and not visible(node.id):
        # Reading a name, or writing one inside a function (only possible
        # through `global`: every other write is in the function's locals).
        # A write at block level is a definition, not a use.
        at_load = not any(kind == "func" for kind, _names in scopes)
        if isinstance(node.ctx, ast.Load) or not at_load:
            out.append((piece_of[first + node.lineno - 1], node.id, at_load))

    for child in ast.iter_child_nodes(node):
        uses(child, scopes, first, piece_of, out)


# ------------------------------------------------------------ the links

def found_layer(name, pieces=None):
    """The layer of a piece number GROUPS does not list: a feature, named
    by the first word after the number in the file name of the piece of
    that number (a screen file follows its piece's number; with no piece of
    that number, its own name)."""

    if pieces is None:
        folder = urm_source.PIECES
        pieces = os.listdir(folder) if os.path.isdir(folder) else []
    same = sorted(p for p in pieces if p[:2] == name[:2] and p.endswith(".rpy"))
    found = re.match(r"^\d\d_([a-z0-9]+)", same[0] if same else name)
    if not found:
        raise LayerError("%s is in no layer: name it NN_word.rpy, the word its feature's "
                         "layer" % name)
    word = found.group(1)
    if word in RESERVED:
        raise LayerError("%s is in no listed layer, and its found layer %r is a taken name "
                         "(a listed layer, a core layer's word, tools): name the file after "
                         "its own feature, or, for a core piece, add its number to GROUPS "
                         "in tests/check_layers.py" % (name, word))
    return word, FEATURE


def group(piece):
    """(layer, rank) of a piece, or of a screen file (screens/NN_name)."""

    name = piece[len(SCREEN_TAG):] if piece.startswith(SCREEN_TAG) else piece
    return GROUP_OF.get(name[:2]) or found_layer(name)


def all_groups():
    """{number: layer} of every listed number and every piece and screen
    file found."""

    out = dict((n, g) for n, (g, _r) in GROUP_OF.items())
    folders = (urm_source.PIECES, urm_source.SCREENS)
    names = [n for f in folders if os.path.isdir(f) for n in os.listdir(f)
             if urm_source.NAME.match(n)]
    pieces = os.listdir(folders[0]) if os.path.isdir(folders[0]) else []
    for name in names:
        if name[:2] not in out:
            out[name[:2]] = found_layer(name, pieces)[0]
    return out


def layer_names():
    """Every layer: the listed ones in their order, then the found ones."""

    listed = [g for g, _r, _n in GROUPS]
    return listed + sorted(set(all_groups().values()) - set(listed))


def wrong_way(user, owner):
    """Why `user` may not use `owner`, or None when it may."""

    (ug, ur), (og, orank) = group(user), group(owner)
    if ug == og or orank < ur:
        return None
    if ur == FEATURE and orank == FEATURE:
        return ("%s is the feature %s and %s the feature %s: a feature "
                "never uses another feature" % (user, ug, owner, og))
    return ("%s is in %s (layer %d) and %s in %s (layer %d): a piece "
            "uses only its own group or a lower layer"
            % (user, ug, ur, owner, og, orank))


def links(folder=None):
    """({(user, owner, name)} of every wrong-way link, {name: pieces} of
    names more than one piece defines)."""

    folder = folder or urm_source.working()
    trees = [(parse(code, first, piece_of), first, piece_of)
             for code, first, piece_of in blocks(folder)]

    owners = {}
    for tree, first, piece_of in trees:
        defines(tree, first, piece_of, owners)

    found = []
    for tree, first, piece_of in trees:
        for node in tree.body:
            uses(node, [], first, piece_of, found)

    pieces = set(p for _t, _f, piece_of in trees for p in piece_of.values())
    for piece in pieces:
        group(piece)

    # A name two pieces define: the later definition replaces the earlier
    # while the game loads (pieces load in the order of their names). So a
    # function that keeps a stand-in of a name a LATER piece defines calls
    # that later piece when it runs; a piece whose own definition comes last
    # calls itself. Code that runs while the game loads (outside functions)
    # sees the definition in effect at that moment: its own piece's, or the
    # last one loaded before it.
    out = set()
    for user, name, at_load in found:
        where = owners.get(name, ())
        if at_load:
            if user in where:
                continue
            earlier = [p for p in where if p < user]
            targets = [max(earlier)] if earlier else list(where)
        else:
            targets = [p for p in where
                       if p != user and not (user in where and p < user)]
        for owner in targets:
            if wrong_way(user, owner):
                out.add((user, owner, name))

    # Our screen files (game_screens/): a screen file is in the layer of
    # the piece with its number. What it uses: every name in its code (not
    # in a comment or a string, not after a dot) that a piece defines, or
    # that is another file's screen. Screens run when drawn, never while
    # the game loads.
    screens = screen_names()
    for user, words in screen_uses():
        for name in words:
            where = set(owners.get(name, ())) | set(
                f for f, defined in screens.items() if name in defined)
            for owner in where - set([user]):
                if wrong_way(user, owner):
                    out.add((user, owner, name))

    shared = dict((n, p) for n, p in owners.items() if len(p) > 1)
    return out, shared


# The URM+ menu: what it shows comes from the registry in the doorway, so
# its piece and its screens name no feature, not even in a string.
HUB = "17"
COMMENT = re.compile(r"(^|\s)#[^'\"\n]*$", re.M)


def hub_names(folder=None):
    """[(file, name)]: a feature's name in the menu's piece or screens."""

    folder = folder or urm_source.working()
    owners = {}
    for code, first, piece_of in blocks(folder):
        defines(parse(code, first, piece_of), first, piece_of, owners)
    features = set(n for n, where in owners.items()
                   if any(group(p)[1] == FEATURE for p in where))
    for f, defined in screen_names().items():
        if group(f)[1] == FEATURE:
            features |= defined
    texts = [(name, data.decode("utf-8")) for name, data in urm_source.pieces(folder)
             if name.startswith(HUB + "_")]
    texts += [(SCREEN_TAG + name[:-len(".rpy")], text) for name, text in screen_texts_raw()
              if name.startswith(HUB + "_")]
    out = []
    for name, text in texts:
        for word in sorted(set(WORD.findall(COMMENT.sub(u"", text))) & features):
            out.append((name, word))
    return out


def screen_texts_raw():
    return [(name, data.decode("utf-8")) for name, data in urm_source.screen_files()]


# A screen file's name in the links: screens/NN_name.
SCREEN_TAG = "screens/"
STRING = re.compile(r"'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"")
WORD = re.compile(r"(?<![\w.])[A-Za-z_][A-Za-z0-9_]*")


def screen_texts():
    return [(SCREEN_TAG + name[:-len(".rpy")], data.decode("utf-8"))
            for name, data in urm_source.screen_files()]


def screen_names():
    """{screen file: set of the screens it defines}."""

    return dict((f, set(re.findall(r"^screen ([A-Za-z0-9_]+)", text, re.M)))
                for f, text in screen_texts())


def screen_uses():
    """[(screen file, set of words its code uses)]."""

    out = []
    for f, text in screen_texts():
        code = u"\n".join(l for l in text.split(u"\n")
                          if not l.lstrip().startswith(u"#"))
        out.append((f, set(WORD.findall(STRING.sub(u"''", code)))))
    return out


def by_pair(found):
    pairs = {}
    for user, owner, name in found:
        pairs.setdefault((user, owner), set()).add(name)
    return pairs


def read_list(path=LINKS):
    """{(user, owner, name)} from layer_links.txt."""

    if not os.path.exists(path):
        raise LayerError("%s is missing: python tests/check_layers.py "
                         "--record writes it." % path)
    out = set()
    with io.open(path, encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith(u"#"):
                continue
            try:
                pair, names = line.split(u":", 1)
                user, owner = [p.strip() for p in pair.split(u"->")]
            except ValueError:
                raise LayerError("%s line %d is not \"<piece> -> <piece>: "
                                 "name, name\": %s" % (path, number, line))
            for name in names.split(u","):
                if name.strip():
                    out.add((str(user), str(owner), str(name.strip())))
    return out


def write_list(found, path=LINKS):
    lines = [
        u"# Wrong-way links between the layers that exist today (see",
        u"# tests/check_layers.py). This list may only shrink: a new link",
        u"# fails the unit suite, and so does a link here that is gone.",
        u"# Written by: python tests/check_layers.py --record",
        u"",
    ]
    for (user, owner), names in sorted(by_pair(found).items()):
        lines.append(u"%s -> %s: %s" % (user, owner, u", ".join(sorted(names))))
    with io.open(path, "w", encoding="utf-8", newline=u"\n") as f:
        f.write(u"\n".join(lines) + u"\n")


def main(argv):
    try:
        found, _shared = links()
        if len(argv) > 1 and argv[1] == "--record":
            write_list(found)
            print("Wrote %s: %d links in %d pairs"
                  % (LINKS, len(found), len(by_pair(found))))
            return 0
        if len(argv) > 1:
            print(__doc__)
            return 2
        listed = read_list()
    except (LayerError, urm_source.SourceError) as e:
        print("FAIL  %s" % e)
        return 1

    bad = 0
    for user, owner, name in sorted(found - listed):
        bad += 1
        print("FAIL  %s uses %s from %s. %s. Move %s to a lower layer, or "
              "do without it." % (user, name, owner, wrong_way(user, owner), name))
    for user, owner, name in sorted(listed - found):
        bad += 1
        print("FAIL  %s no longer uses %s from %s: remove it from "
              "layer_links.txt." % (user, name, owner))
    try:
        named = hub_names()
    except (LayerError, urm_source.SourceError) as e:
        named = [("the URM+ menu", "unreadable: %s" % e)]
    for where, name in named:
        bad += 1
        print("FAIL  %s names the feature's %s: the URM+ menu reaches a feature only "
              "through what it registered in the doorway." % (where, name))
    if bad:
        return 1
    print("pass  the URM+ menu names no feature, not even in a string")
    print("pass  %d known wrong-way links in %d pairs, no new ones"
          % (len(found), len(by_pair(found))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
