"""
Story-graph rework: the frozen references are sound, and (from M0b) the
shared graph answers exactly as they do.

    <a game's bundled python> -I check_graph.py <that game folder>

Why this exists: the rework moves every feature that reads the game's script
onto one shared reader (research/story_graph/final_design.json). Each move
must change nothing a player sees. The yardstick is tests/baseline/
graph_refs.rpy - today's readers, frozen under _urmref* names by
make_graph_refs.py. This file proves the yardstick itself:

  (a) the committed reference file is the one that was pinned
  (b) it regenerates from the baseline byte for byte
  (c) it is ASCII, LF-only, with no trailing backslash
  (d) it runs on its own: exec'd with nothing but renpy, an x52URM stand-in
      and the four python_* names, no call over the corpus hits a NameError
  (e) on every statement, menu, label and If of the corpus each reference
      gives what the still-live original gives - or raises the same way

Written to run on Python 2.7 and 3.
"""

from __future__ import print_function

import hashlib
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import graph_harness as H          # noqa: E402
from graph_corpus import SCRIPTS   # noqa: E402

# sha256 of tests/baseline/graph_refs.rpy. Changes only with a deliberate
# re-freeze (see make_graph_refs.py).
PIN = "d2a5abc17a183f3d2eb14a2734dce7e7f9989698aa6243dcf35b79023936d45e"

# sha256 of tests/baseline/graph_refs_m8.rpy, the references of moves 8 and
# 9 (make_graph_refs.py --m8).
PIN_M8 = "a42405416174acb7e6c51609304e54dc88021b6c8814162e060dfca04e1c0b97"

# sha256 of tests/baseline/game_fixes_pre_graph.rpy, the "before" side of
# parity_graph.py. Without it the baseline and the working file could be
# edited together and the parity diff would stay empty.
BASELINE_PIN = "6560991f842cb536bc1ee23219128fac34bc825c2a12921eec1d7883e7c8eaf6"

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(2)

renpy = H.setup(sys.argv[1])
ast = renpy.ast

# One more script, for this file only: the statements a dialogue line can
# sit next to (show, scene, hide, with, pass), which the shared corpus has
# none of. The skip look-back's test (move 6) is compared on it.
EXTRA = [("skip_passage", u'''
label sp:
    scene bg room
    show eileen happy
    "One."
    with dissolve
    hide eileen
    pass
    $ seen_it = True
    if seen_it:
        show eileen sad
    "Two."
    menu:
        "Stay":
            "Three."
        "Go":
            jump sp_out
    while seen_it:
        $ seen_it = False
    call sp_out
    return

label sp_out:
    "Four."
    return
''')]
ALL = list(SCRIPTS) + EXTRA

failures = 0


def ok(name, good, detail=""):
    global failures
    if good:
        print("pass  %s" % name)
    else:
        failures += 1
        print("FAIL  %s" % name)
        if detail:
            print("        %s" % (detail,))


# ----------------------------------------------------------- (a) (b) (c)

with io.open(H.REFS, "rb") as f:
    raw = f.read()

ok("(a) graph_refs.rpy is the pinned file",
   hashlib.sha256(raw).hexdigest() == PIN, hashlib.sha256(raw).hexdigest())

with io.open(H.BASELINE, "rb") as f:
    base_raw = f.read()
ok("(a) the pre-rework baseline is the pinned file",
   hashlib.sha256(base_raw).hexdigest() == BASELINE_PIN,
   hashlib.sha256(base_raw).hexdigest())

regen = subprocess.call([sys.executable, os.path.join(HERE, "make_graph_refs.py"), "--check"],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
ok("(b) it regenerates from the baseline byte for byte", regen == 0)

text = raw.decode("ascii", "replace")
ok("(c) ASCII, LF only, no trailing backslash",
   all(b < 128 for b in bytearray(raw)) and b"\r" not in raw
   and not any(line.rstrip().endswith("\\") for line in text.split("\n")))


# ------------------------------------------------------------ the two sides

class Side(object):
    """One implementation of the readers, by naming scheme."""

    def __init__(self, ns, names):
        self.ns = ns
        self.names = names

    def __call__(self, logical):
        return self.ns[self.names[logical]]

    def reset(self):
        state = self.ns[self.names["state"]]
        state.succ.clear()
        graph_reset = self.ns.get("_urmsg_reset")
        if graph_reset is not None:
            graph_reset()
        cache = getattr(state, "cache", None)
        if cache is not None:
            cache.clear()


def scheme(maze, cards, skip, const):
    return {
        "succ": maze + "successors", "pyjump": maze + "pyjump",
        "pure": maze + "pure", "text_menu": maze + "text_menu",
        "target_tag": maze + "target_tag", "plan": maze + "plan",
        "reach": maze + "reach", "distances": maze + "distances",
        "next_menu": maze + "next_menu", "arms": maze + "arms",
        "stretch": maze + "stretch", "state": maze + "st",
        "stmt": cards + "statement", "pylines": cards + "python_lines",
        "flatten": cards + "flatten", "truth": cards + "truth",
        "chain": cards + "chain",
        "next": skip + "next", "quiet_if": skip + "quiet_if",
        "says_in": skip + "says_in", "passes": skip + "passes",
    }


LIVE = scheme("_urmm_", "_urm_", "_urms_", "_URM")
REF = scheme("_urmrefm_", "_urmref_", "_urmrefs_", "_URMREF")


def load_live(ns):
    """Today's readers from the working file, by needle."""

    for needle in ("class _URMSGraph", "def _urm_flatten", "def _urmm_walk"):
        exec(compile(H.chunk_with(H.GF, needle), "game_fixes.rpy", "exec"), ns)
    # Every comparison in this file is with the frozen readers: the
    # behaviour fixes are switched off for it (H.fixes_off).
    H.fixes_off(ns)

    # The skip chunk patches the engine at its top level, so its four
    # readers are taken by name instead of exec'ing the chunk.
    skip = H.top_defs(H.chunk_with(H.GF, "def _urms_next"),
                      ["_urms_lookup", "_urms_truth", "_urms_next", "_urms_passes",
                       "_urms_quiet_if", "_urms_says_in"])
    exec(compile(skip, "game_fixes.rpy:skip", "exec"), ns)


# ------------------------------------------------------------- normalising

class Norm(object):
    """Turns results into plain comparable data: a statement becomes its
    position in the script, so two sides must name the very same node."""

    def __init__(self, nodes):
        self.where = {}
        for i, node in enumerate(nodes):
            self.where[id(node)] = i

    def __call__(self, value, depth=0):
        if depth > 40:
            return "<too deep>"
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, ("".__class__, u"".__class__, bytes)):
            return value
        if isinstance(value, ast.Node):
            return ("node", self.where.get(id(value), "outside"))
        if isinstance(value, (list, tuple)):
            return [self(v, depth + 1) for v in value]
        if isinstance(value, (set, frozenset)):
            return sorted(self(v, depth + 1) for v in value)
        if isinstance(value, dict):
            out = []
            for k, v in value.items():
                out.append((self.where.get(k, k), self(v, depth + 1)))
            return sorted(out, key=repr)
        return "<%s>" % type(value).__name__


def raising(*a, **k):
    raise NameError("the test store has no such name")


def text_number(cond):
    return sum(bytearray((u"%s" % (cond,)).encode("utf-8"))) % 3


def by_text(cond, *a, **k):
    """Stands in for the engine's evaluator: the answer depends on the
    condition's own text, so a second or third arm is the one taken, some
    conditions are false and some cannot be evaluated."""
    n = text_number(cond)
    if n == 0:
        raise NameError("the test store has no such name")
    return n == 1


def by_text_shifted(cond, *a, **k):
    n = (text_number(cond) + 1) % 3
    if n == 0:
        raise NameError("the test store has no such name")
    return n == 1


# (name, evaluator). An evaluator returns a value or raises.
TRUTHS = (("always false", lambda *a, **k: False),
          ("always true", lambda *a, **k: True),
          ("always raises", raising),
          ("by its text", by_text),
          ("by its text, shifted", by_text_shifted))


def as_truth(fn):
    """An evaluator as a truth function: True, False, or None for unknown."""
    def truth(cond, *a, **k):
        try:
            return bool(fn(cond))
        except Exception:
            return None
    return truth


def written_true(nodes, depth=0):
    """
    RETIRED by idea 4 (design fix C3, 2026-11-20): a block that holds a
    written `if True:`. Such an arm tests nothing, so the working file no
    longer puts an "only if True" guard on what is in it; the frozen readers
    still do. The flat-record comparisons skip exactly these blocks (every
    other comparison on them stays), and check_maze.py's "if True:" cases
    hold the new behaviour.
    """

    for n in (nodes or ()):
        if isinstance(n, ast.If):
            for cond, block in n.entries:
                if isinstance(cond, ast.PyExpr) and (u"%s" % (cond,)).strip() == u"True":
                    return True
                if depth < 12 and written_true(block, depth + 1):
                    return True
    return False


def blocks_of(node):
    out = []
    for entry in (getattr(node, "entries", None) or []):
        out.append(entry[1])
    for item in (getattr(node, "items", None) or []):
        if item[2] is not None:
            out.append(item[2])
    return out


def observe(side, x52, nodes):
    """Everything one side says about one script, as {layer: [results]}."""

    norm = Norm(nodes)
    out = {}

    def run(layer, fn, *args):
        kind, value = H.outcome(fn, *args)
        out.setdefault(layer, []).append((kind, norm(value)))

    side.reset()

    menus = [n for n in nodes if isinstance(n, ast.Menu)]
    ifs = [n for n in nodes if isinstance(n, ast.If)]
    labels = [n for n in nodes if isinstance(n, ast.Label)]
    pythons = [n for n in nodes if isinstance(n, ast.Python)]

    for node in nodes:
        run("flow", side("succ"), node)
        if not H.idea8_static(node):
            run("text", side("stmt"), node)
        run("passes", side("passes"), node)

    real_eval = renpy.python.py_eval
    try:
        for _name, fn in TRUTHS:
            renpy.python.py_eval = fn
            for node in nodes:
                run("live", side("next"), node)
    finally:
        renpy.python.py_eval = real_eval

    for node in pythons:
        dropped = [0]
        run("lex", side("pylines"), node, dropped)
        out.setdefault("lex", []).append(("dropped", dropped[0]))
        run("lex", side("pyjump"), node)

    for node in ifs + menus:
        if isinstance(node, ast.If):
            dropped = [0]
            if not written_true([node]) and not H.idea8_block([node]):
                run("lex", lambda n, d: side("flatten")([n], dropped=d), node, dropped)
            out.setdefault("lex", []).append(("dropped", dropped[0]))
            run("lex", lambda n: side("pure")([n], 0), node)
            run("lex", side("quiet_if"), node)
        else:
            run("lex", side("text_menu"), node)
        for block in blocks_of(node):
            dropped = [0]
            if not written_true(block) and not H.idea8_block(block):
                run("lex", lambda b, d: side("flatten")(b, dropped=d), block, dropped)
            out.setdefault("lex", []).append(("dropped", dropped[0]))
            run("lex", side("pure"), block)
            run("lex", side("target_tag"), block)
            run("lex", side("says_in"), block)

    real_truth = side.ns[side.names["truth"]]
    try:
        for _name, fn in TRUTHS:
            side.ns[side.names["truth"]] = as_truth(fn)
            for node in labels:
                run("search", side("next_menu"), node)
    finally:
        side.ns[side.names["truth"]] = real_truth

    for menu in menus:
        blocks = blocks_of(menu)
        kind, plan = H.outcome(side("plan"), menu, blocks)
        out.setdefault("search", []).append((kind, norm(plan)))
        if kind != "ok" or plan is None:
            continue
        starts, stop = plan
        for start in starts:
            run("search", side("reach"), start, menu)
        run("search", side("distances"), stop)
        # The arm walk is not compared here any more: since 2026-11-20 a
        # split inside a way closes at its own rejoin and the budget is
        # shared out (FINDINGS.md), so the live walk differs from the
        # frozen one on purpose. check_maze.py holds the cases for the new
        # behaviour; the graph's own run is still compared with the frozen
        # walk below (stitch_arms).

    # Idea 8: a stretch on which the working file meets a jump or a call it
    # cannot follow is not compared (H.idea8_walk) - asked of the working
    # file's own walk, whichever side is being observed.
    working = side.ns.get("_urmm_stretch")
    for node in labels:
        if working is not None and H.idea8_walk(H.outcome(working, node)[1]):
            continue
        run("run", side("stretch"), node)

    for node in ifs:
        x52.PathDetection.target = node
        if side.names is LIVE:
            def chain():
                steps = side("chain")()
                return (steps, list(x52.Var._urmChainMeta))
            run("chain", chain)
        else:
            run("chain", side("chain"), node)
        # Since rework move 5b the live chain steps with the graph's own
        # step, which reports "lost" where URM's nextNode raised; the chain
        # then raises LookupError, not what URM raised. Every caller catches
        # any exception and draws nothing, so what must match is THAT it
        # raises at the same If, not the class.
        # RETIRED by idea 2 (design fix C1, 2026-11-20): where URM's step
        # is lost the frozen chain raises and the card was empty; the live
        # chain now returns the gates it found, closed by the step that
        # says where it stops (check_maze.py, "idea 2"). A lost chain is
        # compared as lost, whatever it now shows - the graph's chain is
        # asked whether it was.
        if side.names is LIVE and out["chain"][-1][0] == "ok":
            asked = side.ns["_urmsg_chain"](
                node, x52.PathDetection.lookAheadLimit, x52.PathDetection.nodeIsBlocking,
                side.ns["_urmsg_step_urm"], side.ns["_URM_MAX_GATES"] + 4)
            if asked.lost:
                out["chain"][-1] = ("raised", "lost")
        if out["chain"][-1][0] == "raised":
            out["chain"][-1] = ("raised", "lost")
        else:
            out["chain"][-1] = H.idea8_tail(out["chain"][-1])
    x52.PathDetection.target = None

    return out


def first_difference(a, b):
    for layer in sorted(set(a) | set(b)):
        left, right = a.get(layer, []), b.get(layer, [])
        if left == right:
            continue
        for i in range(max(len(left), len(right))):
            x = left[i] if i < len(left) else "<missing>"
            y = right[i] if i < len(right) else "<missing>"
            if x != y:
                return "%s #%d: %r  !=  %r" % (layer, i, x, y)
    return None


# -------------------------------------------------------------------- (d)

bare = H.bare_namespace()
exec(compile(H.refs_body(), "graph_refs.rpy", "exec"), bare)
ok("(d) the references exec with nothing else in scope",
   "_urmrefm_walk" in bare and "_urmref_chain" in bare and "_urmrefs_next" in bare)

name_errors = []
counts = {}
for name, source in ALL:
    nodes = H.parse(source)
    seen = observe(Side(bare, REF), bare["x52URM"], nodes)
    for layer, rows in seen.items():
        counts[layer] = counts.get(layer, 0) + len(rows)
        for row in rows:
            if row[0] == "raised" and row[1] in ("NameError", "UnboundLocalError"):
                name_errors.append("%s/%s" % (name, layer))

ok("(d) running every reference over the corpus needs no outside name",
   not name_errors, sorted(set(name_errors))[:6])


# -------------------------------------------------------------------- (e)

x52 = H.make_x52()
both = H.bare_namespace(x52)
load_live(both)
exec(compile(H.refs_body(), "graph_refs.rpy", "exec"), both)

live, ref = Side(both, LIVE), Side(both, REF)
total = 0
raised = 0

for name, source in ALL:
    nodes = H.parse(source)
    a = observe(live, x52, nodes)
    b = observe(ref, x52, nodes)
    for rows in a.values():
        total += len(rows)
        raised += len([r for r in rows if r[0] == "raised"])
    ok("(e) %-18s references = live code  (%d statements)" % (name, len(nodes)),
       a == b, first_difference(a, b))

print()
print("      %d comparisons over %d scripts, %d of them 'both raise the same way'"
      % (total, len(ALL), raised))
print("      per layer: %s" % ", ".join("%s %d" % (k, counts[k]) for k in sorted(counts)))

# The comparison must be able to fail: change one reference and look again.
NL = chr(10)
GENERAL = "    else:" + NL + "        out.append(_urmrefm_after(node))" + NL
intact = H.refs_body()
broken = intact.replace(GENERAL, "    else:" + NL + "        out.append(None)" + NL, 1)
if broken == intact:
    raise SystemExit("FAIL  the self-test found nothing to alter")
probe = H.bare_namespace(H.make_x52())
load_live(probe)
exec(compile(broken, "graph_refs.rpy (altered)", "exec"), probe)
caught = False
for name, source in SCRIPTS[:3]:
    nodes = H.parse(source)
    if observe(Side(probe, LIVE), probe["x52URM"], nodes) != \
            observe(Side(probe, REF), probe["x52URM"], nodes):
        caught = True
ok("the comparison catches an altered reference", caught)

# Move 5b: the live chain's step is the graph's. Break that step in two ways
# (a call that is not followed into its label; a missing label that is not
# "lost") and the chain comparison must notice each.
def chain_caught(altered):
    real = both["_urmsg_step_urm"]
    both["_urmsg_step_urm"] = altered
    try:
        for _name, source in SCRIPTS:
            nodes = H.parse(source)
            if observe(live, x52, nodes).get("chain") != observe(ref, x52, nodes).get("chain"):
                return True
        return False
    finally:
        both["_urmsg_step_urm"] = real


def step_not_into_calls(node):
    if isinstance(node, ast.Call):
        return node.next
    return real_step_urm(node)


def step_never_lost(node):
    found = real_step_urm(node)
    return None if found is both["_URMSG_LOST"] else found


real_step_urm = both["_urmsg_step_urm"]
ok("M5b: the chain comparison catches a step that does not follow a call",
   chain_caught(step_not_into_calls))
ok("M5b: the chain comparison catches a step that is never lost",
   chain_caught(step_never_lost))


# ====================================================================
# M0b - the shared graph answers exactly as the frozen references do
# ====================================================================

graph_ns = H.bare_namespace(H.make_x52())
exec(compile(H.chunk_with(H.GF, "class _URMSGraph"), "game_fixes.rpy:graph", "exec"), graph_ns)
ok("the graph block loads with nothing else in scope",
   "_urmsg_flow" in graph_ns and "_urmsg_chain" in graph_ns)

# Both in one namespace for the comparison (names never collide).
gx52 = H.make_x52()
g = H.bare_namespace(gx52)
exec(compile(H.chunk_with(H.GF, "class _URMSGraph"), "game_fixes.rpy:graph", "exec"), g)
FIXES = H.fixes_off(g)
exec(compile(H.refs_body(), "graph_refs.rpy", "exec"), g)

LOST = g["_URMSG_LOST"]


def py_truth(cond):
    """What the skip look-ahead does with a condition: the engine's
    evaluator, None when it raises, truthiness otherwise."""
    try:
        taken = renpy.python.py_eval(cond)
    except Exception:
        return None
    return bool(taken)


def urm_step(node):
    """URM's nextNode as a step: an exception is LOST."""
    try:
        return gx52.PathDetection.nextNode(node)
    except Exception:
        return LOST


def graph_chain(first, step, blocks=None):
    c = g["_urmsg_chain"](first, gx52.PathDetection.lookAheadLimit,
                          blocks or gx52.PathDetection.nodeIsBlocking, step)
    if c.lost:
        raise LookupError("lost")
    return (c.steps, c.meta)


def stitch_walk(w, node, stack, seen, depth):
    """The maze's arm walk rebuilt on _urmsg_run: what the maze block will
    keep for itself (fork recursion, arm labels, the menu depth cap)."""

    stack = list(stack)
    seen = set(seen)
    records, end, at = g["_urmsg_run"](w, node, stack, seen)
    if end[0] != "split":
        return records, end

    if isinstance(at, ast.If):
        arms = []
        exhaustive = False
        for cond, block in (getattr(at, "entries", None) or []):
            if not g["_urmsg_is_else"](cond):
                label = "if " + g["_urmsg_clip"](str(cond), 18)
            else:
                label = "otherwise"
                exhaustive = True
            start = block[0] if block else at.next
            arms.append((label + g["_urmsg_target_tag"](block), start))
        if not exhaustive:
            arms.append(("otherwise", at.next))
        return records, ("fork", [(label, stitch_walk(w, start, stack, seen, depth))
                                  for label, start in arms], "if")

    items = [i for i in (getattr(at, "items", None) or []) if i[2] is not None]
    if depth >= g["_URMREFM_DEPTH"]:
        return records, ("more", len(items))
    return records, ("fork", [(g["_urmrefm_choice_label"](i),
                               stitch_walk(w, i[2][0] if i[2] else at.next, stack, seen, depth + 1))
                              for i in items], "menu")


def stitch_arms(menu, blocks, plan):
    starts, stop = plan
    w = g["_URMSGWalk"](id(stop) if stop is not None else None, menu,
                        g["_URMREFM_STEPS"], g["_URMSG_KEEP_ARM"])
    return [stitch_walk(w, start, (), (), 0) for start in starts]


def stitch_stretch(start):
    """The map's trunk walk rebuilt on _urmsg_run."""

    blocks = [[None, []]]
    w = g["_URMSGWalk"](None, None, g["_URMREFM_STRETCH"], g["_URMSG_KEEP_TRUNK"], blocks)
    _records, end, at = g["_urmsg_run"](w, start, [], set())
    if end[0] == "split":
        return blocks, at, None
    return blocks, None, end[0]


def compare_graph(nodes, caps=None):
    """{layer: [(reference, graph)]} - only the pairs that differ."""

    norm = Norm(nodes)
    bad = {}
    done = [0]

    def same(layer, what, ref, new):
        done[0] += 1
        if ref != new:
            bad.setdefault(layer, []).append("%s: %r != %r" % (what, ref, new))

    def got(fn, *args):
        kind, value = H.outcome(fn, *args)
        return (kind, norm(value))

    g["_urmrefm_st"].succ.clear()
    g["_urmsg_reset"]()

    reach_cap = (caps or {}).get("reach", 4000)
    later_cap = (caps or {}).get("later", 8000)
    if caps:
        g["_URMREFM_REACH"] = reach_cap
        g["_URMREFM_LATER"] = later_cap

    menus = [n for n in nodes if isinstance(n, ast.Menu)]
    ifs = [n for n in nodes if isinstance(n, ast.If)]
    labels = [n for n in nodes if isinstance(n, ast.Label)]
    pythons = [n for n in nodes if isinstance(n, ast.Python)]

    def urm_plain(node):
        try:
            return gx52.PathDetection.nextNode(node)
        except Exception:
            return "LOST"

    def graph_plain(node):
        found = g["_urmsg_step_urm"](node)
        return "LOST" if found is LOST else found

    for i, node in enumerate(nodes):
        same("flow", i, got(g["_urmrefm_successors"], node), got(g["_urmsg_flow"], node))
        if not H.idea8_static(node):
            same("text", i, got(g["_urmref_statement"], node), got(g["_urmsg_stmt_text"], node))
        same("urm step", i, got(urm_plain, node), got(graph_plain, node))
        same("blocking", i, got(gx52.PathDetection.nodeIsBlocking, node),
             got(g["_urmsg_blocks_urm"], node))
        same("passes", i, got(g["_urmrefs_passes"], node), got(g["_urmsg_passes"], node))

    real_eval = renpy.python.py_eval
    try:
        for name, fn in TRUTHS:
            renpy.python.py_eval = fn
            for i, node in enumerate(nodes):
                same("live", "%s %d" % (name, i), got(g["_urmrefs_next"], node),
                     got(g["_urmsg_step_live"], node, py_truth))
    finally:
        renpy.python.py_eval = real_eval

    for node in pythons:
        same("lex", "hop", got(g["_urmrefm_pyjump"], node), got(g["_urmsg_hop"], node))
    for node in ifs:
        same("lex", "quiet", got(g["_urmrefs_quiet_if"], node), got(g["_urmsg_quiet_if"], node))

    # ---- M1: what a block does
    def ref_lines(node):
        dropped = [0]
        return (g["_urmref_python_lines"](node, dropped), dropped[0])

    def ref_flat(block):
        dropped = [0]
        return (g["_urmref_flatten"](block, dropped=dropped), dropped[0])

    def new_flat(block):
        dropped = [0]
        return (g["_urmsg_flat"](block, (), 0, dropped), dropped[0])

    for node in pythons:
        same("lex", "python lines", got(ref_lines, node), got(g["_urmsg_py_lines"], node))
    for node in ifs + menus:
        if isinstance(node, ast.If):
            if not written_true([node]) and not H.idea8_block([node]):
                same("lex", "flat if", got(ref_flat, [node]), got(new_flat, [node]))
            same("lex", "pure if", got(lambda n: g["_urmrefm_pure"]([n], 0), node),
                 got(lambda n: g["_urmsg_pure"]((n,), 0), node))
        else:
            same("lex", "text menu", got(g["_urmrefm_text_menu"], node),
                 got(g["_urmsg_text_menu"], node))
        for block in blocks_of(node):
            if written_true(block) or H.idea8_block(block):
                ref = got(new_flat, block)
            else:
                ref = got(ref_flat, block)
            same("lex", "flat arm", ref, got(new_flat, block))
            # The remembered form answers the same, asked twice.
            same("lex", "arm records", ref, got(g["_urmsg_arm_recs"], block))
            same("lex", "arm records again", ref, got(g["_urmsg_arm_recs"], block))
            same("lex", "pure arm", got(g["_urmrefm_pure"], block), got(g["_urmsg_pure"], block))
            same("lex", "tag", got(g["_urmrefm_target_tag"], block),
                 got(g["_urmsg_target_tag"], block))
            same("lex", "says", got(g["_urmrefs_says_in"], block), got(g["_urmsg_says_in"], block))

    # ---- M1: the run both walkers share, stitched back into each of them
    for menu in menus:
        blocks = blocks_of(menu)
        kind, plan = H.outcome(g["_urmrefm_plan"], menu, blocks)
        if kind != "ok" or plan is None:
            continue
        new_arms = got(stitch_arms, menu, blocks, plan)
        if not H.idea8_walk(new_arms[1]):
            same("run", "arms", got(g["_urmrefm_arms"], menu, blocks, plan), new_arms)
    for node in labels:
        new_stretch = got(stitch_stretch, node)
        if not H.idea8_walk(new_stretch[1]):
            same("run", "stretch", got(g["_urmrefm_stretch"], node), new_stretch)

    real_truth = g["_urmref_truth"]
    try:
        for name, fn in TRUTHS:
            truth = as_truth(fn)
            g["_urmref_truth"] = truth
            for node in labels:
                same("search", "next split " + name,
                     got(g["_urmrefm_next_menu"], node),
                     got(lambda n: g["_urmsg_next_split"](n, truth)[0], node))
    finally:
        g["_urmref_truth"] = real_truth

    for menu in menus:
        blocks = blocks_of(menu)
        ref_plan = got(g["_urmrefm_plan"], menu, blocks)
        new_plan = got(lambda m, b: g["_urmsg_plan"](m, b, reach_cap), menu, blocks)
        same("search", "plan", ref_plan, new_plan)
        # Move 7: the plan is remembered. Asked again it must still be the
        # reference's answer, and so must the same split asked about with
        # its arms the other way round (a memo that ignored the block lists
        # would hand back the first answer).
        same("search", "plan again", ref_plan,
             got(lambda m, b: g["_urmsg_plan"](m, b, reach_cap), menu, blocks))
        turned = blocks[::-1]
        same("search", "plan, arms turned round",
             got(g["_urmrefm_plan"], menu, turned),
             got(lambda m, b: g["_urmsg_plan"](m, b, reach_cap), menu, turned))
        if ref_plan[0] != "ok" or ref_plan[1] is None:
            continue
        starts, stop = g["_urmrefm_plan"](menu, blocks)
        for start in starts:
            same("search", "reach", got(g["_urmrefm_reach"], start, menu),
                 got(lambda s, m: g["_urmsg_reach"](s, m, reach_cap, True)[0], start, menu))
        same("search", "distances", got(g["_urmrefm_distances"], stop),
             got(lambda s: g["_urmsg_reach"](s, None, later_cap, False)[0], stop))

    def lost(result):
        # The reference raises whatever URM's step raised; the graph reports
        # "lost" and its adapter raises. The feature's guard catches any
        # exception, so what must match is THAT it raises, not the class.
        # Idea 8: the text of a closing step that cannot be followed is not
        # compared (H.idea8_tail).
        return ("raised", "lost") if result[0] == "raised" else H.idea8_tail(result)

    for node in ifs:
        ref = lost(got(g["_urmref_chain"], node))
        same("chain", "URM's step", ref, lost(got(graph_chain, node, urm_step)))
        same("chain", "graph's step", ref, lost(got(graph_chain, node, g["_urmsg_step_urm"])))
        same("chain", "graph's step and blocking test", ref,
             lost(got(graph_chain, node, g["_urmsg_step_urm"], g["_urmsg_blocks_urm"])))

    if caps:
        g["_URMREFM_REACH"] = 4000
        g["_URMREFM_LATER"] = 8000

    return bad, done[0]


graph_total = 0
for name, source in ALL:
    nodes = H.parse(source)
    bad, n = compare_graph(nodes)
    graph_total += n
    detail = ""
    for layer in sorted(bad):
        detail = "%s: %s" % (layer, bad[layer][0])
        break
    ok("graph = references on %-18s" % name, not bad, detail)

# The same again with the caps squeezed, so every search hits its limit.
squeezed = 0
squeezed_bad = []
for name, source in SCRIPTS:
    nodes = H.parse(source)
    for cap in (2, 5, 9):
        bad, n = compare_graph(nodes, {"reach": cap, "later": cap})
        squeezed += n
        if bad:
            squeezed_bad.append("%s cap %d: %s" % (name, cap, sorted(bad)[0]))
ok("graph = references with every search cut short (caps 2, 5, 9)",
   not squeezed_bad, squeezed_bad[:3])

short = 0
short_bad = []
for name, source in SCRIPTS:
    nodes = H.parse(source)
    for limit in (1, 2, 3):
        gx52.PathDetection.lookAheadLimit = limit
        try:
            bad, n = compare_graph(nodes)
        finally:
            gx52.PathDetection.lookAheadLimit = 20
        short += n
        if bad:
            short_bad.append("%s limit %d: %s" % (name, limit, sorted(bad)[0]))
ok("graph = references with URM's look-ahead cut to 1, 2 and 3",
   not short_bad, short_bad[:3])

print()
print("      %d graph-vs-reference comparisons, %d more with squeezed caps, %d with a short look-ahead"
      % (graph_total, squeezed, short))

# The graph comparison must be able to fail too: break one graph function.
real_flow = g["_urmsg_flow"]


def broken_flow(node):
    found = real_flow(node)
    return found[:-1] if isinstance(node, ast.If) and found else found


g["_urmsg_flow"] = broken_flow
try:
    caught_graph = False
    for name, source in SCRIPTS[:3]:
        if compare_graph(H.parse(source))[0]:
            caught_graph = True
finally:
    g["_urmsg_flow"] = real_flow
ok("the comparison catches an altered graph function", caught_graph)

# The same for M1: each alteration below must be caught in its own layer.
#   - the arm walk dropping the records only it keeps (the keep-set)
#   - the trunk walk keeping them
#   - a python line wrongly treated as presentation
#   - the lift taking guards off when it must not
def caught_in(layer, name, value):
    real = g[name]
    g[name] = value
    try:
        for _name, source in SCRIPTS:
            if layer in compare_graph(H.parse(source))[0]:
                return True
        return False
    finally:
        g[name] = real


ok("M1: the comparison catches an arm walk that drops its own records",
   caught_in("run", "_URMSG_KEEP_ARM", frozenset()))
ok("M1: the comparison catches a trunk walk that keeps the arm's records",
   caught_in("run", "_URMSG_KEEP_TRUNK", frozenset((0, 1, 2, 3))))
ok("M1: the comparison catches a python line wrongly dropped as presentation",
   caught_in("lex", "_urmsg_noise", lambda line: True))
ok("M1: the comparison catches a lift that drops guards it must keep",
   caught_in("lex", "_urmsg_lift",
             lambda arms, guards: [(guards, t) for _g, rows, _a in arms for _x, t in rows]))

# Each behaviour fix: switched on, the comparison must differ in the layer
# and on the script the fix is about - so the switch is the fix, and the
# comparisons above were made without it.
ok("the behaviour-fix switches are found and off for the comparisons",
   FIXES == sorted(FIXES) and "_URMSG_FIX_FRAMES" in FIXES and not any(g[n] for n in FIXES),
   FIXES)


def fix_changes(switch, script, layer):
    source = [s for n, s in ALL if n == script][0]
    g[switch] = True
    try:
        return layer in compare_graph(H.parse(source))[0]
    finally:
        g[switch] = False


ok("idea 5: with FRAMES on, a scene called twice is walked differently from the frozen walk",
   fix_changes("_URMSG_FIX_FRAMES", "twice_alone", "run"))
ok("idea 12: with VISIT on, the rejoin of ways that call one scene differs from the frozen search",
   fix_changes("_URMSG_FIX_VISIT", "called_twice", "search"))
ok("idea 13: with SKIP on, a menu with a set leads on past itself, which the frozen flow does not",
   fix_changes("_URMSG_FIX_SKIP", "hub_with_set", "flow"))
ok("idea 13 (2a): with SKIP on, a menu whose every option has a test leads on past itself as well",
   fix_changes("_URMSG_FIX_SKIP", "menu_all_tested", "flow"))
ok("idea 6: with HOP on, a python jump made only sometimes also leads on, which the frozen flow does not",
   fix_changes("_URMSG_FIX_HOP", "python_hops", "flow"))
ok("idea 3: with TIES on, two meeting points that tie are told apart by their place in the script",
   fix_changes("_URMSG_FIX_TIES", "tied_rejoin", "search"))
ok("mirrored paths: with MEET on, ways that share a scene one of them goes around meet behind it, "
   "which the frozen search does not find",
   fix_changes("_URMSG_FIX_MEET", "bypassed_scene", "search"))

# The same for move 6, the skip look-ahead's readers.
#   - the graph's "a line can sit next to this" without the show statement
#   - the live look-ahead treating a condition it cannot evaluate as false
#   - the live look-ahead stepping into a quiet if as if it had lines
def passes_without_show():
    state = g["_urmsg_st"]
    real = g["_URMSG_PASSES"]
    g["_URMSG_PASSES"] = tuple(n for n in real if n != "Show")
    state.pass_classes = None
    state.passes.clear()
    try:
        for _name, source in ALL:
            if "passes" in compare_graph(H.parse(source))[0]:
                return True
        return False
    finally:
        g["_URMSG_PASSES"] = real
        state.pass_classes = None
        state.passes.clear()


def live_caught(name, value, layer):
    real = both[name]
    both[name] = value
    try:
        for _name, source in ALL:
            nodes = H.parse(source)
            if observe(live, x52, nodes).get(layer) != observe(ref, x52, nodes).get(layer):
                return True
        return False
    finally:
        both[name] = real


def truth_unknown_is_false(cond):
    try:
        return bool(renpy.python.py_eval(cond))
    except Exception:
        return False


ok("M6: the comparison catches a look-back that stops at a show statement",
   passes_without_show())
ok("M6: the live comparison catches a wrapper that reads 'show' as leaving the passage",
   live_caught("_urms_passes", lambda node: not isinstance(node, ast.Show)
               and both["_urmsg_passes"](node), "passes"))
ok("M6: the live comparison catches a look-ahead that takes 'cannot tell' for false",
   live_caught("_urms_truth", truth_unknown_is_false, "live"))
ok("M6: the live comparison catches a look-ahead that enters every if",
   live_caught("_urmsg_quiet_if", lambda node, depth=0: False, "live"))

# The same for move 7: a plan memo that does not look at the block lists.
# The graph block is loaded again with that one change, and its plan put in
# place of the real one.
graph_text = H.chunk_with(H.GF, "class _URMSGraph")
KEY = 'key = ("plan", id(origin) if origin is not None else 0, tuple(ids), cap)'
PIN = "if block and kept[i] is not block:"
if graph_text.count(KEY) != 1 or graph_text.count(PIN) != 1:
    ok("M7: the plan-memo self-test found its two lines to alter", False)
else:
    alt = H.bare_namespace(gx52)
    exec(compile(graph_text.replace(KEY, 'key = ("plan", id(origin) if origin is not None else 0, cap)')
                 .replace(PIN, "if False:"),
                 "game_fixes.rpy:graph (altered)", "exec"), alt)
    ok("M7: the comparison catches a plan memo that ignores the block lists",
       caught_in("search", "_urmsg_plan", alt["_urmsg_plan"]))

# ---- move 7: the statement the game is on, and the plan memo

nodes = H.parse(dict(SCRIPTS)["plain_menu"])
g["_urmsg_reset"]()
ctx = renpy.game.contexts[-1]
real_context = renpy.game.context
renpy.game.context = lambda *a, **k: ctx
try:
    H.SCRIPT.labels[("here", 1, 2)] = nodes[3]
    ctx.current = ("here", 1, 2)
    at = g["_urmsg_here"]()
    ctx.current = ("nowhere", 1, 2)
    gone = g["_urmsg_here"]()
    remembered = ("nowhere", 1, 2) in g["_urmsg_st"].g.labels \
        or ("here", 1, 2) in g["_urmsg_st"].g.labels
    del ctx.current
    none = g["_urmsg_here"]()
finally:
    renpy.game.context = real_context
ok("the statement the game is on: found, None when it is not in the script, "
   "None with no position - and never through the label memory",
   at is nodes[3] and gone is None and none is None and not remembered,
   (at, gone, none, remembered))

nodes = H.parse(dict(SCRIPTS)["now_and_then"])
g["_urmsg_reset"]()
menu = [n for n in nodes if isinstance(n, ast.Menu)][0]
blocks = blocks_of(menu)
searches = [0]
real_meeting = g["_urmsg_meeting"]


def counted_meeting(*a, **k):
    searches[0] += 1
    return real_meeting(*a, **k)


g["_urmsg_meeting"] = counted_meeting
try:
    first = g["_urmsg_plan"](menu, blocks)
    first[0].append("scribble")
    second = g["_urmsg_plan"](menu, list(blocks))
    other_cap = g["_urmsg_plan"](menu, blocks, 7)
    g["_urmsg_reset"]()
    after_reset = g["_urmsg_plan"](menu, blocks)
finally:
    g["_urmsg_meeting"] = real_meeting
ok("the plan of a split is searched once, handed out as a fresh list, and "
   "searched again for another cap or another script",
   searches[0] == 3 and second[1] is first[1] and second[0] == first[0][:-1]
   and second[0] is not first[0] and after_reset[1] is first[1],
   (searches[0], len(first[0]), len(second[0])))

# A plan found while a label could not be looked up is not remembered.
nodes = H.parse(dict(SCRIPTS)["computed_targets"])
real_miss = H.SCRIPT.miss
try:
    H.SCRIPT.miss = KeyError
    g["_urmsg_reset"]()
    kept = 0
    asked = 0
    for menu in [n for n in nodes if isinstance(n, ast.Menu)]:
        before = g["_urmsg_st"].g.skipped
        g["_urmsg_plan"](menu, blocks_of(menu))
        if g["_urmsg_st"].g.skipped != before:
            asked += 1
            kept += len(g["_urmsg_st"].g.q)
            g["_urmsg_st"].g.q.clear()
    ok("a plan found while a lookup failed some other way is not remembered",
       asked > 0 and kept == 0, (asked, kept))
finally:
    H.SCRIPT.miss = real_miss
g["_urmsg_reset"]()

# ====================================================================
# M8 - what sits in what: the index's links and the climbs up them
# ====================================================================

with io.open(H.REFS_M8, "rb") as f:
    raw8 = f.read()
ok("M8 (a) graph_refs_m8.rpy is the pinned file",
   hashlib.sha256(raw8).hexdigest() == PIN_M8, hashlib.sha256(raw8).hexdigest())
regen8 = subprocess.call([sys.executable, os.path.join(HERE, "make_graph_refs.py"),
                          "--m8", "--check"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
ok("M8 (b) it regenerates from the baseline byte for byte", regen8 == 0)
# (It keeps the two backslash continuations of the index code it copies: the
# live index block has the same lines and loads on every engine.)
ok("M8 (c) ASCII, LF only", all(b < 128 for b in bytearray(raw8)) and b"\r" not in raw8)

# The live index and the live climbers next to the frozen ones.
m8 = H.bare_namespace(H.make_x52())
exec(compile(H.chunk_with(H.GF, "class _URMSGraph"), "game_fixes.rpy:graph", "exec"), m8)
exec(compile(H.chunk_with(H.GF, "class _URMIndex"), "game_fixes.rpy:index", "exec"), m8)
for needle, names in H.CLIMBERS:
    exec(compile(H.top_defs(H.chunk_with(H.GF, needle), names), "game_fixes.rpy:climbers", "exec"), m8)
exec(compile(H.refs_m8_body(), "graph_refs_m8.rpy", "exec"), m8)

# One more script for the index: a game that keeps choices as words in a
# collection, read and written through its own helper functions.
FLAGS = [("flag_helpers", u'''
init python:
    def true(o):
        if o in mc_choices:
            return True

    def option(i):
        global mc_choices
        mc_choices.add(i)

default mc_choices = set()
default seen_kim = False
define easy = True

label fh:
    "Well?"
    menu:
        "Accept" if not seen_kim:
            $ option("kim_accept")
            $ points += 2
        "Refuse":
            $ option("kim_refuse")
            $ a, b = 1, 2
            $ option(last_pick)
    if points > hard:
        "Hard."
    if true("kim_accept") and points >= 2:
        "Yours."
    elif "kim_refuse" in mc_choices:
        "No."
    while points < 3:
        $ points += 1
    $ diary.append("met kim")
    return
'''),

    # Move 9: python text of every shape the two readers tell apart.
    ("python_lines", u'''
init python:
    def helper(a):
        local_only = a
        return a

    class Thing(object):
        inside_class = 1

default bag = []

label pl:
    python:
        x = 1
        x = 2
        love += 3
        a, b = 1, 2
        (c, [d, e]) = (1, [2, 3])
        store.flag = True
        stats["str"] = 5
        girl.love -= 1
        rows[3] = None
        k = m = 7
        setflag("met", who)
        girl.note("hello", 3, mood)
        bag.append("key")
        bag.append("rope", "torch")
        bag.add(item)
        get_bag().append("lost")
        pockets[0].remove("coin")
        bag.discard()
        if x > 1:
            y = 2
            bag.discard("key")
            for i in others:
                z += 1
        f = lambda q: q
        def inner():
            hidden = 1
        total = x + y
        nothing = None
        neg = -4
    $ broken = = 1
    $ renpy.pause(1)
    $ love += 1
    $ girl.gift("rose")
    return
''')]


def build_both(nodes):
    """(frozen index, live index) over the same statements."""

    extra, links = H.odd_nodes(nodes)
    made = []
    for cls in (m8["_URMREF8Index"], m8["_URMIndex"]):
        index = cls()
        index.build(nodes + extra)
        for node, link in links:
            index.parent[id(node)] = link
        made.append(index)
    return made[0], made[1], nodes + extra


def compare_m8(nodes):
    """{what: first difference} between the frozen and the live side."""

    ref_index, new_index, every_node = build_both(nodes)
    # RETIRED by idea 1 (a behaviour fix, 2026-11-20): "the label guessed
    # from a line number is the one the frozen index guessed". The frozen
    # index took the nearest label above, even one nested in the scene
    # before; the live one does not, on purpose. So the frozen readers are
    # handed the live guess: what is still compared below is every climb and
    # when each reader falls back to the line. The guess itself is held by
    # check_panel.py ("which scene a line is in").
    ref_index.label_at = new_index.label_at
    norm = Norm(every_node)
    bad = {}
    done = [0]

    def same(layer, what, a, b):
        done[0] += 1
        if a != b and layer not in bad:
            bad[layer] = "%s: %r != %r" % (what, a, b)

    def got(fn, *args):
        kind, value = H.outcome(fn, *args)
        return (kind, norm(value))

    a, b = H.index_tables(ref_index), H.index_tables(new_index)
    for table in sorted(a):
        same("index", table, norm(a[table]), norm(b[table]))

    # Move 9: what the panel reads from a python line, the frozen reader
    # against the live one. Each keeps its own cache; both start empty.
    m8["x52URM"].Var._urmpState = None
    m8["x52URM"].Var._urmref8pState = None
    for i, node in enumerate(every_node):
        if isinstance(node, ast.Python):
            source = node.code.source
            same("py", "effects %d" % i, got(m8["_urmref8p_effects"], source),
                 got(m8["_urmp_effects"], source))
            same("py", "effects again %d" % i, got(m8["_urmref8p_effects"], source),
                 got(m8["_urmp_effects"], source))

    for i, node in enumerate(every_node):
        site = (getattr(node, "filename", "?"), getattr(node, "linenumber", 0), id(node))
        same("contain", "label_of %d" % i, got(m8["_urmref8m_label_of"], node, ref_index),
             got(m8["_urmm_label_of"], node, new_index))
        same("contain", "where %d" % i, got(ref_index.where, site), got(new_index.where, site))
        same("contain", "scene %d" % i, got(m8["_urmref8p_scene"], ref_index, node, site[0], site[1]),
             got(m8["_urmp_scene"], new_index, node, site[0], site[1]))
        same("contain", "in_init %d" % i, got(m8["_urmref8g_in_init"], ref_index, site),
             got(m8["_urmg_in_init"], new_index, site))
        same("contain", "block %d" % i, got(m8["_urmref8s_block"], ref_index, node),
             got(m8["_urms_block"], new_index, node))

    counts = dict((t, len(a[t])) for t in a)
    return bad, done[0], counts


m8_total = 0
m8_sizes = {}
for name, source in ALL + FLAGS:
    bad, n, counts = compare_m8(H.parse(source))
    m8_total += n
    for table, size in counts.items():
        m8_sizes[table] = m8_sizes.get(table, 0) + size
    detail = ""
    for layer in sorted(bad):
        detail = "%s: %s" % (layer, bad[layer])
        break
    ok("M8: index and climbs = references on %-18s" % name, not bad, detail)

empty = sorted(t for t in ("reads", "writes", "rivals", "tokens", "calls", "callreads",
                           "callnames", "declared", "helpers", "flags", "labels",
                           "label_lines", "parent", "prev", "prev_many")
               if not m8_sizes.get(t))
ok("M8: every index table had something in it to compare", not empty, empty)
print()
print("      %d index-and-climb comparisons; entries per table: %s"
      % (m8_total, ", ".join("%s %d" % (t, m8_sizes[t]) for t in sorted(m8_sizes))))


# Each of these breaks one of the four structure functions and must be
# caught - in the index tables or in the climbs.
def m8_caught(name, value, layer):
    real = m8[name]
    m8[name] = value
    try:
        for _name, source in ALL + FLAGS:
            if layer in compare_m8(H.parse(source))[0]:
                return True
        return False
    finally:
        m8[name] = real


real_children = m8["_urmsg_children"]
real_conds = m8["_urmsg_conds"]
real_climb = m8["_urmsg_climb"]

ok("M8: caught - a menu's blocks linked without their caption",
   m8_caught("_urmsg_children",
             lambda node: tuple((k, a, None if k == "option" else e, m)
                                for k, a, e, m in real_children(node)), "index"))


def children_keep_everything(node):
    if isinstance(node, (ast.If, ast.Menu, ast.Label, ast.While)):
        return real_children(node)
    return (("block", -1, None, tuple(getattr(node, "block", None) or ())),)


ok("M8: caught - a block's lexer tuples linked as if they were statements",
   m8_caught("_urmsg_children", children_keep_everything, "index"))
ok("M8: caught - the last test of an if or menu not recorded",
   m8_caught("_urmsg_conds", lambda node: real_conds(node)[:-1]
             if isinstance(node, (ast.If, ast.Menu)) else real_conds(node), "index"))
ok("M8: caught - a while's test not recorded",
   m8_caught("_urmsg_conds", lambda node: () if isinstance(node, ast.While)
             else real_conds(node), "index"))
ok("M8: caught - a climb that stops at the nearest link",
   m8_caught("_urmsg_climb", lambda parents, node, limit=200: real_climb(parents, node, 1),
             "contain"))
ok("M8: caught - a line in a translation block not placed where the block is",
   m8_caught("_urmsg_block_link", lambda parents, node: parents.get(id(node)), "contain"))

# The index calls two of them from its own thread: they, and everything
# they call, must touch no graph state. Read from the block's own text.
import ast as pyast

graph_tree = pyast.parse(H.chunk_with(H.GF, "class _URMSGraph"))
graph_defs = dict((n.name, n) for n in graph_tree.body if isinstance(n, pyast.FunctionDef))
STATEFUL = set(["_urmsg_st", "_urmsg_graph", "_urmsg_kind", "_urmsg_fact", "_urmsg_resolve",
                "_urmsg_lookup", "_urmsg_py", "_urmsg_reset", "_urmsg_gen"])


def names_reached(root, seen=None):
    seen = set() if seen is None else seen
    for node in pyast.walk(graph_defs[root]):
        if isinstance(node, pyast.Name) and node.id not in seen:
            seen.add(node.id)
            if node.id in graph_defs:
                names_reached(node.id, seen)
    return seen


# The same for move 9, the one parse of a python line. Each alteration is
# of the parse (or of the panel's ordering of it) and must show in the
# index tables or in the panel's reading.
real_parse = m8["_urmsg_py_parse"]


def parse_altered(change):
    def parse(source):
        parsed, events = real_parse(source)
        return parsed, tuple(change(events))
    return parse


ok("M9: caught - events handed over first statement first (the index's lists are in visiting order)",
   m8_caught("_urmsg_py_parse", parse_altered(lambda events: events[::-1]), "index"))
ok("M9: caught - only the first argument of coll.append(...) kept",
   m8_caught("_urmsg_py_parse",
             parse_altered(lambda events: [e[:8] + (e[8][:1],) if e[0] == "c" else e for e in events]),
             "index"))
ok("M9: caught - names unpacked from a tuple given to the panel as plain assignments",
   m8_caught("_urmsg_py_parse",
             parse_altered(lambda events: [e[:7] + (False,) if e[0] == "w" else e for e in events]),
             "py"))
ok("M9: caught - the panel reading a python block last line first",
   m8_caught("_urmsg_py_top", lambda events: [e for e in events if e[1] == 0], "py"))

SKIP = "        if isinstance(cur, _urmsg_py_skip):"
if graph_text.count(SKIP) != 1:
    ok("M9: the def-body self-test found its line to alter", False)
else:
    alt9 = H.bare_namespace(gx52)
    exec(compile(graph_text.replace(SKIP, "        if False:"),
                 "game_fixes.rpy:graph (altered)", "exec"), alt9)
    ok("M9: caught - the body of a def read as the story's own assignments",
       m8_caught("_urmsg_py_parse", alt9["_urmsg_py_parse"], "index"))

PURE = ["_urmsg_children", "_urmsg_conds", "_urmsg_py_parse", "_urmsg_py_top"]
impure = [(root, sorted(names_reached(root) & STATEFUL)) for root in PURE
          if root not in graph_defs or names_reached(root) & STATEFUL]
ok("M8: what the index calls from its thread touches no graph state", not impure, impure)
ok("M8: and that check can fail (the successor rule does touch it)",
   bool(names_reached("_urmsg_flow") & STATEFUL))

# ---- every part of a fact, not just its successors

E = dict((k, g[k]) for k in g if k.startswith("_URMSG_E_"))
facts_bad = []
facts_seen = 0
for name, source in SCRIPTS:
    nodes = H.parse(source)
    g["_urmsg_reset"]()
    for node in nodes:
        fact = g["_urmsg_fact"](node)
        if fact is None:
            continue
        facts_seen += 1
        where = "%s:%s" % (name, type(node).__name__)
        flow = tuple(e[1] for e in fact.e
                     if e[0] <= E["_URMSG_E_EXIT"] and e[1] is not None)
        if flow != fact.flow:
            facts_bad.append(where + " flow is not its flow edges")
        if g["_urmsg_arms"](node) is not fact.arms or \
                g["_urmsg_has_else"](node) != fact.has_else:
            facts_bad.append(where + " arms/has_else helpers disagree with the fact")
        if isinstance(node, ast.If):
            if len(fact.arms) != len(node.entries):
                facts_bad.append(where + " arm count")
            for i, (cond, block) in enumerate(node.entries):
                arm = fact.arms[i]
                start = block[0] if block else node.next
                if not (arm[0] == i and arm[1] is cond
                        and arm[2] == g["_urmref_is_condition"](cond)
                        and arm[3] is block and arm[4] is start and arm[5] is None):
                    facts_bad.append(where + " arm %d" % i)
            has_else = any(not g["_urmref_is_condition"](c) for c, _b in node.entries)
            fall = [e for e in fact.e if e[0] == E["_URMSG_E_FALL"]]
            if fact.has_else != has_else or (len(fall) == 1) != (not has_else):
                facts_bad.append(where + " else / fall-through")
            if fall and fall[0][1] is not node.next:
                facts_bad.append(where + " fall-through target")
        elif isinstance(node, ast.Menu):
            with_block = [(i, item) for i, item in enumerate(node.items) if item[2] is not None]
            if len(fact.arms) != len(with_block):
                facts_bad.append(where + " item count")
            for arm, (i, item) in zip(fact.arms, with_block):
                start = item[2][0] if item[2] else node.next
                if not (arm[0] == i and arm[1] is item[1] and arm[3] is item[2]
                        and arm[4] is start and arm[5] is item[0]):
                    facts_bad.append(where + " item %d" % i)
            skip = fact.e[-1]
            if skip[0] != E["_URMSG_E_SKIP"] or skip[1] is not node.next:
                facts_bad.append(where + " skip edge")
        elif isinstance(node, ast.Call) or fact.via == "call":
            ret = [e for e in fact.e if e[0] == E["_URMSG_E_RETSITE"]]
            if len(ret) != 1 or ret[0][1] is not node.next:
                facts_bad.append(where + " return site")
        if isinstance(node, (ast.Jump, ast.Call)):
            label = node.target if isinstance(node, ast.Jump) else node.label
            if fact.label != label or fact.dyn != bool(node.expression):
                facts_bad.append(where + " label / computed")
            if not fact.dyn and fact.target is not H.SCRIPT.labels.get(label):
                facts_bad.append(where + " target")
ok("every part of every fact matches the statement (%d facts)" % facts_seen,
   not facts_bad, facts_bad[:4])

# ---- the chain's flags

nodes = H.parse(dict(SCRIPTS)["eight_ifs"])
g["_urmsg_reset"]()
first_if = [n for n in nodes if isinstance(n, ast.If)][0]
c = g["_urmsg_chain"](first_if, 20, gx52.PathDetection.nodeIsBlocking, g["_urmsg_step_urm"])
ok("a chain of more than 8 ifs is cut, and says so",
   c.cut and not c.lost and len(c.steps) == 8 and len(c.meta) == 8)

nodes = H.parse(dict(SCRIPTS)["lost_chains"])
g["_urmsg_reset"]()
ifs_here = [n for n in nodes if isinstance(n, ast.If)]
c_missing = g["_urmsg_chain"](ifs_here[0], 20, gx52.PathDetection.nodeIsBlocking, g["_urmsg_step_urm"])
c_computed = g["_urmsg_chain"](ifs_here[1], 20, gx52.PathDetection.nodeIsBlocking, g["_urmsg_step_urm"])
ok("a chain that runs into a missing label is lost; one that meets a "
   "computed jump is marked live",
   c_missing.lost and not c_missing.live and c_computed.live and not c_computed.cut,
   (c_missing.lost, c_missing.live, c_computed.live, c_computed.lost))

# ---- freshness: a new script object means a new graph
nodes = H.parse(dict(SCRIPTS)["plain_menu"])
g["_urmsg_reset"]()
g["_urmsg_flow"](nodes[1])
old_gen = g["_urmsg_gen"]()
had_facts = len(g["_urmsg_st"].g.facts)
real_script = renpy.game.script
try:
    other = H.FakeScript()
    other.labels = real_script.labels
    other.miss = real_script.miss
    renpy.game.script = other
    fresh_gen = g["_urmsg_gen"]()
    fresh_facts = len(g["_urmsg_st"].g.facts)
finally:
    renpy.game.script = real_script
ok("a different script object makes a new, empty graph",
   had_facts > 0 and fresh_gen == old_gen + 1 and fresh_facts == 0,
   (had_facts, old_gen, fresh_gen, fresh_facts))

# A label that resolves differently later: the step functions see it at
# once (they ask the engine every time, as the readers they port do).
nodes = H.parse(dict(SCRIPTS)["loop_back"])
g["_urmsg_reset"]()
jump = [n for n in nodes if isinstance(n, ast.Jump) and n.target == "out"][0]
before = g["_urmsg_step_live"](jump, py_truth)
H.SCRIPT.labels["out"] = H.SCRIPT.labels["hall"]
after = g["_urmsg_step_live"](jump, py_truth)
after_urm = g["_urmsg_step_urm"](jump)
ok("the step functions never answer from a remembered label",
   before is not after and after is H.SCRIPT.labels["hall"] and after_urm is after)

# ---- things only the graph has

nodes = H.parse(dict(SCRIPTS)["computed_targets"])
g["_urmsg_reset"]()
missing = [n for n in nodes if isinstance(n, ast.Jump)
           and not n.expression and n.target == "ct_missing_label"][0]
fact = g["_urmsg_fact"](missing)
ok("a jump to a label that does not exist is a MISS edge, remembered",
   fact.e == ((g["_URMSG_E_MISS"], None, -1, "ct_missing_label"),)
   and g["_urmsg_st"].g.labels.get("ct_missing_label") is False
   and g["_urmsg_flow"](missing) == ())

dyn = [n for n in nodes if isinstance(n, ast.Jump) and n.expression][0]
ok("a computed jump is a DYN edge and never a successor",
   g["_urmsg_fact"](dyn).e[0][0] == g["_URMSG_E_DYN"] and g["_urmsg_flow"](dyn) == ())

# A lookup that fails for another reason is not remembered as a miss.
real_miss = H.SCRIPT.miss
try:
    H.SCRIPT.miss = KeyError
    g["_urmsg_reset"]()
    before = g["_urmsg_st"].g.skipped
    again = g["_urmsg_resolve"]("ct_missing_label")
    ok("a lookup failing some other way is not remembered",
       again == (None, False) and "ct_missing_label" not in g["_urmsg_st"].g.labels
       and g["_urmsg_st"].g.skipped == before + 1)
finally:
    H.SCRIPT.miss = real_miss

nodes = H.parse(dict(SCRIPTS)["hub_with_set"])
g["_urmsg_reset"]()
hub = [n for n in nodes if isinstance(n, ast.Menu)][0]
fact = g["_urmsg_fact"](hub)
skip = fact.e[-1]
ok("a menu's own next is a SKIP edge with its data, not a successor",
   skip[0] == g["_URMSG_E_SKIP"] and skip[1] is hub.next and skip[3] == (True, False)
   and hub.next not in g["_urmsg_flow"](hub) and len(fact.arms) == 3)

ok("the fact is remembered and handed back",
   g["_urmsg_fact"](hub) is fact and g["_urmsg_st"].g.facts[id(hub)] is fact)

# Memo tables hold only untracked containers.
graph = g["_urmsg_st"].g
g["_urmsg_plan"](hub, blocks_of(hub))
plain_tables = all(type(t) is dict for t in (graph.facts, graph.labels, graph.py, graph.q)) \
    and len(graph.q) == 1 \
    and all(type(k) is tuple and type(v) is tuple and type(v[1]) is tuple and type(v[2]) is tuple
            for k, v in graph.q.items())
plain_fields = all(type(f.e) is tuple and type(f.flow) is tuple and type(f.arms) is tuple
                   for f in graph.facts.values())
ok("memo tables are plain dicts of tuples", plain_tables and plain_fields)

# A new script on the same script object: the reset makes answers right.
first = H.parse(dict(SCRIPTS)["plain_menu"])
g["_urmsg_reset"]()
a = [g["_urmsg_flow"](n) for n in first]
second = H.parse(dict(SCRIPTS)["loop_back"])
gen = g["_urmsg_gen"]()
g["_urmsg_reset"]()
jump = [n for n in second if isinstance(n, ast.Jump) and n.target == "hall"][0]
ok("after a reset, a new script gets its own answers",
   g["_urmsg_gen"]() == gen + 1 and g["_urmsg_flow"](jump) == (H.SCRIPT.labels["hall"],))

# The gate-state machine, on fixed vectors.
states = g["_urmsg_gate_states"]
steps3 = [("gate", "a", None), ("gate", "b", None), ("else", None, None)]
ok("gate states: the first true gate runs, the rest are dead",
   states(steps3, lambda c: c == "b") == [("dead", 1), ("runs", 2), ("dead", 0)])
ok("gate states: an unknown gate makes everything after it unknown",
   states(steps3, lambda c: None) == [("unknown", 1), ("unknown", 2), ("unknown", 0)])
ok("gate states: nothing true means the else runs",
   states(steps3, lambda c: False) == [("dead", 1), ("dead", 2), ("runs", 0)])
asked = []
states(steps3, lambda c: asked.append(c) or True)
ok("gate states: truth is not asked once a gate has fired", asked == ["a"])

# Fault injection: a statement whose arms cannot be read.
class Broken(ast.If):
    def __init__(self):
        pass

    @property
    def entries(self):
        raise RuntimeError("broken entries")


broken_if = Broken()
kinds = set()
for fn in (lambda: g["_urmsg_fact"](broken_if), lambda: g["_urmsg_flow"](broken_if)):
    kinds.add(H.outcome(fn))
ok("a statement that cannot be read raises, as the readers it replaces do",
   kinds == set([("raised", "RuntimeError")]), kinds)

print()
print("all passed" if not failures else "%d FAILED" % failures)
sys.exit(1 if failures else 0)
