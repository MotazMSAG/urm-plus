"""
Unit-checks "is this line shared, or here because of a check?" against real
Ren'Py AST.

    <a game's bundled python> -I check_branch.py <that game folder>

Scripts are parsed with the engine's own parser and then PLAYED by a small
interpreter that reports every statement in the order it runs - what
config.statement_callbacks gives the tracker in a game. At each line the
tracker is handed the statements that ran since the line before, exactly as
_urmb_interact does, and what the chip would say is compared with what is
true.

The player's two cases come first (IDEAS.md, PRIORITY):
    hello / how are you / [check x: True] / I'm fine, what about you? /
    [remerge] / I'm fine also!
and the same with x False, where nothing extra plays.
"""

from __future__ import print_function

import io
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import urm_source  # noqa  (the add-on's code, joined from its pieces)

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(2)

base = os.path.abspath(sys.argv[1])
os.chdir(base)
sys.path.insert(0, base)

import renpy  # noqa

renpy.import_all()
renpy.config.basedir = base
renpy.config.gamedir = os.path.join(base, "game")


class FakeScript(object):
    record_pycode = False
    all_pycode = []
    serial = 0

    def __init__(self):
        self.labels = {}
        self.namemap = {}
        self.all_stmts = []

    def lookup(self, name):
        return self.namemap[name]

    def __getattr__(self, name):
        return None


SCRIPT = FakeScript()
renpy.game.script = SCRIPT
renpy.game.log = type("L", (), {"mutated": {}})()
if not renpy.game.contexts:
    renpy.game.contexts = [type("C", (), {"init_phase": True})()]


def children(node):
    for block in ([getattr(node, "block", None)]
                  + [b for _c, b in (getattr(node, "entries", None) or [])]
                  + [i[2] for i in (getattr(node, "items", None) or [])]):
        for n in (block or []):
            yield n


def every(nodes):
    for n in nodes:
        yield n
        for m in every(list(children(n))):
            yield m


class Colors(object):
    def __getattr__(self, name):
        return None


class Theme(object):
    colors = Colors()
    isDark = True


class CodeView(object):
    @staticmethod
    def colorize(code, **kw):
        return code.replace("{", "{{")


class SettingsClass(object):
    defaultValues = {}


class X52URM(object):
    Theme = Theme()
    CodeView = CodeView()
    SettingsClass = SettingsClass

    @staticmethod
    def scalePxInt(n):
        return n


ns = {"x52URM": X52URM(), "renpy": renpy, "config": renpy.config,
      "__name__": "urm_helpers",
      "python_object": object, "python_list": list, "python_dict": dict,
      "python_set": set}

# The story graph, the card helpers (truth, clip), the maze block (words),
# then the block under test.
for needle in ("class _URMSGraph", "def _urm_flatten", "def _urmm_walk",
               "def _urmb_advance"):
    exec(compile(urm_source.block(needle), "game_fixes.rpy", "exec"), ns)

# The block hooks itself in when it loads; here the test drives it instead.
for hook in (renpy.config.statement_callbacks, renpy.config.interact_callbacks,
             getattr(renpy.config, "after_load_callbacks", [])):
    for name in ("_urmb_record", "_urmb_interact", "_urmb_forget"):
        if ns[name] in hook:
            hook.remove(ns[name])

advance = ns["_urmb_advance"]
view_of = ns["_urmb_view"]
is_line = ns["_urmb_is_line"]

LOADED = []
STORE = renpy.store.__dict__


def load(script):
    """Parse a whole script; give every statement a name, as a game has."""

    path = os.path.join(base, "_urm_check_branch.rpy")
    io.open(path, "w", encoding="utf-8").write(textwrap.dedent(script))
    try:
        block = renpy.parser.parse(path)
    finally:
        os.remove(path)

    renpy.ast.chain_block(block, None)
    LOADED.append(block)
    ns["_urmsg_reset"]()
    ns["_urmb_st"].gen = -1
    SCRIPT.labels = {}
    SCRIPT.namemap = {}
    serial = 0
    for n in every(block):
        serial += 1
        if isinstance(n, renpy.ast.Label):
            SCRIPT.labels[n.name] = n
        elif getattr(n, "name", None) is None:
            n.name = ("check_branch.rpy", len(LOADED), serial)
        SCRIPT.namemap[n.name] = n
    return block


def play(label, picks=()):
    """Yield every statement in the order the game would run it."""

    picks = list(picks)
    node = SCRIPT.labels[label]
    returns = []
    steps = 0
    ast = renpy.ast
    while node is not None and steps < 5000:
        steps += 1
        kind = type(node).__name__
        if kind == "Translate":
            node = node.block[0] if node.block else node.next
            continue
        if kind == "EndTranslate":
            node = node.next
            continue

        yield node

        if isinstance(node, ast.Menu):
            blocks = [i[2] for i in node.items if i[2] is not None]
            node = blocks[picks.pop(0)][0]
        elif isinstance(node, ast.If):
            for cond, block in node.entries:
                if eval(str(cond), STORE):
                    node = block[0]
                    break
            else:
                node = node.next
        elif isinstance(node, ast.While):
            node = node.block[0] if eval(str(node.condition), STORE) else node.next
        elif isinstance(node, ast.Jump):
            node = SCRIPT.labels[node.target]
        elif isinstance(node, ast.Call):
            returns.append(node.next)
            node = SCRIPT.labels[node.label]
        elif isinstance(node, ast.Return):
            node = returns.pop() if returns else None
        elif isinstance(node, ast.Python):
            exec(node.code.source, STORE)
            node = node.next
        else:
            node = node.next


def said(node):
    if isinstance(node, renpy.ast.Menu):
        return "<menu>"
    return node.what


def chip(state):
    v = view_of(state, False, 2)
    if v is None:
        return "-"
    return v[1] + (" | " + v[2] if v[2] else "")


def run(label, picks=(), keep=None):
    """[(line, chip)] for every line shown; keep collects (state, names, line)."""

    state = None
    pending = []
    shown = []
    for node in play(label, picks):
        pending.append(node.name)
        if is_line(node):
            before = state
            state = advance(state, tuple(pending), False, node)
            if keep is not None:
                keep.append((before, tuple(pending), node, state))
            pending = []
            shown.append((said(node), chip(state)))
    return shown


failures = 0


def expect(name, got, want):
    global failures
    if got == want:
        print("pass  %s" % name)
    else:
        failures += 1
        print("FAIL  %s" % name)
        print("        got  %r" % (got,))
        print("        want %r" % (want,))


def setv(**values):
    for k, v in values.items():
        STORE[k] = v


DOT = u"  ·  "

# ---------------------------------------------------------------------------
# The player's two cases
# ---------------------------------------------------------------------------

load("""
label c1:
    "hello"
    "how are you"
    if x:
        "I'm fine, what about you?"
    "I'm fine also!"
    return
""")

setv(x=True)
kept = []
expect("case 1 (x True): the extra line is marked, the next one says back",
       run("c1", keep=kept),
       [("hello", "-"), ("how are you", "-"),
        ("I'm fine, what about you?", "Only because X is on | last line"),
        ("I'm fine also!", "Back on the shared part")])

# Rollback, roll-forward and load re-run the statements since the line
# before against that line's state: the answer must be the same again.
again = [advance(before, names, False, node) for before, names, node, _s in kept]
expect("the same state and statements give the same state (rollback, load)",
       again, [s for _b, _n, _x, s in kept])

setv(x=False)
expect("case 2 (x False): nothing extra plays, and it says a part was skipped",
       run("c1"),
       [("hello", "-"), ("how are you", "-"),
        ("I'm fine also!", "Skipped a part" + DOT + "needs X on")])

# Fast skip: no interaction until the last line, so the tracker gets every
# statement in one go. Nothing was seen in the branch, so no "back".
setv(x=True)
trace = [n for n in play("c1")]          # label, hello, how, if, fine, also
state = advance(None, (trace[0].name, trace[1].name), False, trace[1])
state = advance(state, tuple(n.name for n in trace[2:6]), False, trace[5])
expect("fast skip over a branch: no chip, and no false 'skipped'",
       (said(trace[5]), chip(state)), ("I'm fine also!", "-"))

# ---------------------------------------------------------------------------
# A check inside a check
# ---------------------------------------------------------------------------

load("""
label nest:
    "start"
    if a:
        "a1"
        if b:
            "b1"
        "a2"
    "end"
    return
""")

setv(a=True, b=True)
expect("nested: the inner reason while inside it, the count runs to the outer rejoin",
       run("nest"),
       [("start", "-"), ("a1", "Only because A is on | 2 more"),
        ("b1", "Only because B is on | 1 more"),
        ("a2", "Only because A is on | last line"),
        ("end", "Back on the shared part")])

setv(a=True, b=False)
expect("nested: a part skipped INSIDE a branch is not announced",
       run("nest"),
       [("start", "-"), ("a1", "Only because A is on | 1 more"),
        ("a2", "Only because A is on | last line"),
        ("end", "Back on the shared part")])

# ---------------------------------------------------------------------------
# A branch written as a jump to another label that jumps back
# ---------------------------------------------------------------------------

load("""
label j:
    "start"
    if x:
        jump j_extra
label j_back:
    "shared"
    return
label j_extra:
    "extra line"
    jump j_back
""")

setv(x=True)
expect("jump-based branch: marked in the other label, back at the label it returns to",
       run("j"),
       [("start", "-"), ("extra line", "Only because X is on | last line"),
        ("shared", "Back on the shared part")])

setv(x=False)
expect("jump-based branch not taken: the part behind the jump was skipped",
       run("j"),
       [("start", "-"), ("shared", "Skipped a part" + DOT + "needs X on")])

# The guard shape: the check jumps AWAY, the lines after it are the branch.
load("""
label g:
    "start"
    if not x:
        jump g_join
    "only with x"
label g_join:
    "joined"
    return
""")

setv(x=True)
expect("guard: the lines after a check that jumps away are branch-only",
       run("g"),
       [("start", "-"), ("only with x", "Only because X is on | last line"),
        ("joined", "Back on the shared part")])

setv(x=False)
expect("guard taken: the lines it jumped over were skipped",
       run("g"),
       [("start", "-"), ("joined", "Skipped a part" + DOT + "needs X on")])

# ---------------------------------------------------------------------------
# Parts that exist because of a choice
# ---------------------------------------------------------------------------

load("""
label m:
    "q"
    menu:
        "{i}Tease{/i} her":
            "t1"
            "t2"
        "Leave":
            "l1"
    "after"
    return
""")

expect("menu: the part is there because of the choice, then back",
       run("m", picks=[0]),
       [("q", "-"), ("<menu>", "-"),
        ("t1", "You picked: Tease her | 1 more"),
        ("t2", "You picked: Tease her | last line"),
        ("after", "Back on the shared part")])

# A hub menu that returns to itself: no way through it rejoins the others
# before the menu comes round again, so nothing is claimed.
load("""
label hub:
    menu:
        "Look around":
            "You look."
            jump hub
        "Go":
            "You go."
    "end"
    return
""")

expect("hub menu: neither the loop option nor the exit is a 'detour'",
       run("hub", picks=[0, 1]),
       [("<menu>", "-"), ("You look.", "-"), ("<menu>", "-"),
        ("You go.", "-"), ("end", "-")])

# ---------------------------------------------------------------------------
# Quiet: nothing is said about these
# ---------------------------------------------------------------------------

load("""
label quiet:
    "a"
    if x:
        $ y = 1
    "b"
    if config.developer:
        "dev line"
    "c"
    if True:
        "always"
    "d"
    menu:
        "Only way":
            "one"
    "e"
    return
""")

setv(x=True)
expect("no chip for a check with no lines, an engine test, 'if True', a one-option menu",
       run("quiet", picks=[0]),
       [("a", "-"), ("b", "-"), ("c", "-"), ("always", "-"), ("d", "-"),
        ("<menu>", "-"), ("one", "-"), ("e", "-")])

# A once-only gate: the arm changes the variable it tested.
load("""
label once:
    "a"
    if not met:
        $ met = True
        "Nice to meet you."
    "b"
    return
""")

setv(met=False)
expect("once-only gate: the reason is in the past tense",
       run("once"),
       [("a", "-"), ("Nice to meet you.", "Only because Met was off | last line"),
        ("b", "Back on the shared part")])
expect("once-only gate, second time through: not a 'skipped part'",
       run("once"), [("a", "-"), ("b", "-")])

# A route, not a detour: too long to be worth a chip all the way.
long_arm = "\n".join('        "line %d"' % i for i in range(45))
load("""
label route:
    "start"
    if x:
%s
    "end"
    return
""" % long_arm)

setv(x=True)
shown = run("route")
expect("a 45-line part is a route: tracked, never drawn, no 'back' after it",
       sorted(set(c for _l, c in shown)), ["-"])

# ---------------------------------------------------------------------------
# Words
# ---------------------------------------------------------------------------

load("""
label words:
    "start"
    if a and b:
        "both"
    if points >= 3:
        "enough"
    else:
        "not enough"
    if helper(1):
        "code"
    if tone == "yes":
        "yes"
    elif tone == "no":
        "no"
    else:
        "neither"
    "end"
    return
""")

setv(a=True, b=True, points=1, helper=lambda n: True, tone="maybe")
expect("words: two tests, the else of one test, a function call, the else of a chain",
       run("words"),
       [("start", "-"),
        ("both", "Only because A is on and B is on | last line"),
        ("not enough", "Only because Points is under 3 | last line"),
        ("code", "Only because of a check | last line"),
        ("neither", "Only because no check passed | last line"),
        ("end", "Back on the shared part")])

# ---------------------------------------------------------------------------
# Both arms visit the same called scene
# ---------------------------------------------------------------------------

load("""
label s:
    "start"
    if x:
        call s_scene
        "x extra"
    else:
        call s_scene
    "end"
    return
label s_scene:
    "in the scene"
    return
""")

setv(x=True)
expect("a scene both arms call is not taken for the place they meet",
       run("s"),
       [("start", "-"), ("in the scene", "Only because X is on"),
        ("x extra", "Only because X is on | last line"),
        ("end", "Back on the shared part")])

# ---------------------------------------------------------------------------
# Nothing to go on: an old save, or a jump made from a screen button
# ---------------------------------------------------------------------------

block = load("""
label cold:
    "start"
    if x:
        "inside"
        "inside 2"
    "end"
    return
""")

inside = [n for n in every(block) if getattr(n, "what", None) == "inside"][0]
state = advance(None, (inside.name,), False, inside)
expect("no history and no script index: nothing is claimed",
       chip(state), "-")


class FakeIndex(object):
    state = "ready"

    def __init__(self, nodes):
        self.parent = {}
        ast = renpy.ast
        for node in nodes:
            if isinstance(node, ast.If):
                for cond, blk in node.entries:
                    for child in blk or ():
                        self.parent[id(child)] = (node, "if", cond)
            elif isinstance(node, ast.Menu):
                for item in node.items:
                    for child in item[2] or ():
                        self.parent[id(child)] = (node, "option", item[0])
            else:
                for child in getattr(node, "block", None) or ():
                    self.parent[id(child)] = (node, "block", None)


index = FakeIndex(list(every(block)))
ns["_urmi_index"] = lambda: index
setv(x=True)
state = advance(None, (inside.name,), False, inside)
expect("no history, script index ready: the indented arm around the line is found",
       chip(state), "Only because X is on | 1 more")

# A statement name the script no longer has (a save from another version).
state = advance((("gone.rpy", 1, 1), (), None), (inside.name,), False, inside)
expect("a state naming a statement that no longer exists is dropped, not trusted",
       chip(state), "Only because X is on | 1 more")
del ns["_urmi_index"]

# ---------------------------------------------------------------------------
# What goes into a save
# ---------------------------------------------------------------------------

import pickle

setv(a=True, b=True)
load("""
label nest2:
    "start"
    if a:
        "a1"
        if b:
            "b1"
        "a2"
    "end"
    return
""")
kept = []
run("nest2", keep=kept)
blob = pickle.dumps([s for _b, _n, _x, s in kept], 2)
expect("the saved state is plain data: no URM class is needed to load it",
       b"URM" in blob or b"urm" in blob, False)

print()
if failures:
    print("%d FAILED" % failures)
    sys.exit(1)
print("all passed")
