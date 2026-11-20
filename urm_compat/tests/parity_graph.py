"""
Story-graph rework: the working file gives what the pre-rework file gave.

    <a game's bundled python> -I parity_graph.py <that game folder>

check_graph.py proves single readers against frozen references. This file
proves the FEATURES: it loads tests/baseline/game_fixes_pre_graph.rpy and the
working game_fixes.rpy side by side, each in its own namespace with its own
x52URM stand-in, runs both over the same parsed scripts, and diffs what a
player would end up seeing:

  outline   _urmm_outline per menu (what each choice sets, per route)
  routes    _urmm_plan (starts and rejoin) and the _urmm_arms trees
  map       urm_map_build: every box (kind, title, sub, chips, marks, note,
            column, row), every line, every diamond, the "later" lines
  cards     _urmm_choice_view and _urmm_gate_view rows
  chain     _urm_chain steps and meta, from every If
  effects   _urm_flatten / _urm_reduce / _urm_effects per arm and menu item
  index     every table of the script index built over the script (since
            rework move 8), with three hand-made statements added
  contain   the label, choice and block each statement is in, as the map,
            the panel, the gallery switch and the skip rule ask it
  py        what the variable panel reads from each python statement
            (since rework move 9)
  skip      _urms_small_change and _urms_played_between for every dialogue
            line, under two records of what was seen, three ways a
            condition can come out and two limits (since rework move 6)

A step of the rework that moves a feature onto the graph must leave this
diff empty. WHITELIST names differences that are intended (a later, approved
behaviour fix); it is empty, and stays empty for every "move" step.

Still to be added by the step that ports it: urm_later_gate_rows.

Written to run on Python 2.7 and 3.
"""

from __future__ import print_function

import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import graph_harness as H          # noqa: E402
from graph_corpus import SCRIPTS   # noqa: E402

# (script, layer) pairs allowed to differ, each with the reason. Empty.
# (script, layer): why it may differ from the pre-rework file.
WHITELIST = {
    ("calls_and_hops", "cards"):
        "a check inside a choice is said in words on its card row (was code: 'has_key')",
    ("chapter_four", "cards"):
        "a check inside a choice is said in words on its card row (was code: 'carol_nerve >= 3')",
    # Idea 8 (design fix C7, 2026-11-20): a jump that cannot be followed is
    # said with one record and one wording, and nothing says it twice.
    # check_maze.py ("idea 8") holds the new behaviour.
    ("computed_targets", "cards"):
        "idea 8: a missing label says 'Goes somewhere decided while playing'; no second line",
    ("computed_targets", "effects"):
        "idea 8: a jump to a label that is not in the script is the one record, not 'jump x'",
    ("computed_targets", "outline"):
        "idea 8: a way that cannot be followed ends with the one record and no end text",
    # Idea 5 (design fix C4, 2026-11-20): a scene called twice is walked
    # twice; the way goes on to its real end. check_maze.py ("idea 5").
    ("twice_alone", "cards"):
        "idea 5: 'Ta visits +1 x2' and the way meets; was '+1' and 'Loops back to an earlier point'",
    ("twice_alone", "outline"):
        "idea 5: the second call is walked; was 'loops back to an earlier point'",
    # Idea 12 (design fix C11, 2026-11-20): a scene both ways call is a
    # visit, not the rejoin. check_maze.py ("idea 12").
    ("called_twice", "cards"):
        "idea 12: 'Visits +1 x2' / 'Visits +1'; was 'Changes nothing tracked' on both",
    ("called_twice", "outline"):
        "idea 12: each way shows the called scene's change; was nothing",
    ("called_twice", "plan"):
        "idea 12: the ways meet at t_done; was inside the scene they both call",
    # Idea 13 (design fix C12, 2026-11-20): options that jump back to the
    # hub's own label do not "meet" there - they are back at the menu.
    # check_maze.py ("idea 13").
    ("hub_with_set", "cards"):
        "idea 13: 'Back to this menu' under Kitchen and Garden; was nothing",
    ("hub_with_set", "outline"):
        "idea 13: the ways that jump back end 'back to this menu'; they 'met' at the hub's label",
    ("hub_with_set", "plan"):
        "idea 13: no rejoin - the hub's label only leads back into the menu",
    # Idea 13, the user's pick 2a (2026-11-20): a menu whose every option
    # has a test has one more way, "If none apply". check_maze.py
    # ("idea 13 (2a)"). On the file as it was before 2a the cards of this
    # script already differed from the pre-rework file in one thing, which
    # no other script of the corpus shows: what follows a choice inside a
    # choice is said once, not under each of its ways (a split closes at
    # its own rejoin - the map-rows work, older than idea 13).
    ("menu_all_tested", "cards"):
        "idea 13 (2a): one more row, 'If none apply'; and 'Mat out: 1' once, after the inner ways - was under each",
    ("menu_all_tested", "outline"):
        "idea 13 (2a): one more way through the inner menu, 'If none apply'",
    # Idea 2 (design fix C1, 2026-11-20): a jump ahead that cannot be
    # followed no longer empties the Path card. check_maze.py ("idea 2").
    ("lost_chains", "cards"):
        "idea 2: the gates found are shown, closed by 'Goes somewhere decided while playing'; was no card",
    ("lost_chains", "chain"):
        "idea 2: the chain returns its gates and a closing step; it raised",
    # Idea 3 (design fix C2, 2026-11-20): of two meeting points that tie,
    # the earlier in the script. check_maze.py ("idea 3").
    ("tied_rejoin", "cards"):
        "idea 3: the ways meet at tr_earlier, so A shows 'Tr l: 1'; they met at tr_later and B showed 'Tr e: 1'",
    ("tied_rejoin", "outline"):
        "idea 3: as the cards",
    ("tied_rejoin", "plan"):
        "idea 3: the earlier of the two tied labels; was the one found first",
    # The mirrored paths of Now and Then (_URMSG_FIX_MEET, 2026-11-20): ways
    # that share a scene one of them goes around meet BEHIND that scene.
    # check_maze.py ("mirrored paths").
    ("bypassed_scene", "cards"):
        "mirrored paths: 'Now.' and 'Say nothing.' show the talk's 'Bs talked: 1', 'Not today.' only its own "
        "scene; was nothing under the two and 'Bs done: 1' + 'Returns' under 'Not today.'",
    ("bypassed_scene", "outline"):
        "mirrored paths: as the cards",
    ("bypassed_scene", "plan"):
        "mirrored paths: the ways meet at bs_continue; was bs_talk, which 'Not today.' goes around",
}

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(2)

renpy = H.setup(sys.argv[1])
ast = renpy.ast

# The graph block first where the file has one: the pre-rework file has
# none, and from move 2 on the working file's cards read through it.
NEEDLES = ("class _URMSGraph", "def _urm_flatten", "def _urmm_walk",
           "class _URMIndex", "def _urms_small_change")


class Config(object):
    """Stands in for the store's config: the skip block reads two names."""

    skipping = "slow"

    def __init__(self):
        self.after_load_callbacks = []


def engine_patches():
    """What the skip block replaces in the engine when it loads."""

    return (renpy.ast.Say.__dict__["execute"],
            renpy.execution.Context.__dict__["seen_current"])


def restore(saved):
    renpy.ast.Say.execute = saved[0]
    renpy.execution.Context.seen_current = saved[1]


def load(path, text=None):
    """One side: its own namespace and x52URM stand-in."""

    x52 = H.make_x52()
    ns = H.bare_namespace(x52)
    ns["config"] = Config()
    whole = text if text is not None else H.urm_source.read(path)
    saved = engine_patches()
    try:
        for needle in NEEDLES:
            if needle == NEEDLES[0] and needle not in whole:
                continue
            body = H.chunk_with(path, needle, text)
            # The graph block, once it exists, is loaded first by whoever uses it.
            exec(compile(body, os.path.basename(path), "exec"), ns)
        # The panel's and the gallery's climbers, without the rest of their
        # blocks (the maze's and the skip rule's came with theirs).
        for needle, names in H.CLIMBERS[1:3]:
            body = H.chunk_with(path, needle, text)
            exec(compile(H.top_defs(body, names), os.path.basename(path), "exec"), ns)
    finally:
        # The skip block wraps Say.execute and Context.seen_current as it
        # loads; only its plain functions are called here.
        restore(saved)
    return ns, x52


def conditions_false(*a, **k):
    return False


def conditions_true(*a, **k):
    return True


def conditions_by_text(cond, *a, **k):
    n = sum(bytearray((u"%s" % (cond,)).encode("utf-8"))) % 3
    if n == 0:
        raise NameError("the test store has no such name")
    return n == 1


class Persistent(object):
    _seen_ever = None


def skip_decisions(ns, x52, nodes, run):
    """The two skip rules, asked about every dialogue line."""

    index = ns["_URMIndex"]()
    index.build(nodes)
    ns["_urmi_index"] = lambda: index
    says = [n for n in nodes if isinstance(n, ast.Say)]

    real_eval = renpy.python.py_eval
    real_persistent = getattr(renpy.game, "persistent", None)
    renpy.game.persistent = Persistent()
    try:
        for every in (2, 3):
            # Which lines count as read before: all but every 2nd / 3rd.
            renpy.game.persistent._seen_ever = dict(
                (n.name, True) for i, n in enumerate(says) if i % every)
            for fn in (conditions_false, conditions_true, conditions_by_text):
                renpy.python.py_eval = fn
                for say in says:
                    for limit in (1, 3):
                        x52.Var._urmsCache = None
                        run("skip", ns["_urms_small_change"], say.name, limit)
                        played = ns["_urms_run"]()
                        played.after_seen = True
                        played.unseen = 1
                        run("skip", ns["_urms_played_between"], say.name, limit)
    finally:
        renpy.python.py_eval = real_eval
        renpy.game.persistent = real_persistent


def plain(value, where, depth=0):
    if depth > 40:
        return "<deep>"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, ("".__class__, u"".__class__, bytes)):
        return value
    if isinstance(value, ast.Node):
        return ("node", where.get(id(value), "outside"))
    if isinstance(value, (list, tuple)):
        return [plain(v, where, depth + 1) for v in value]
    if isinstance(value, dict):
        return sorted(((where.get(k, k), plain(v, where, depth + 1))
                       for k, v in value.items()), key=repr)
    return "<%s>" % type(value).__name__


def box_row(b):
    return (b.kind, b.title, getattr(b, "sub", None),
            [tuple(c) for c in b.chips], list(getattr(b, "badges", ())),
            b.more, b.note, getattr(b, "note_tone", None),
            getattr(b, "col", None), b.row, b.x, b.y, b.w, b.h,
            bool(getattr(b, "diamond", False)), len(b.children))


def blocks_of(node):
    out = []
    for entry in (getattr(node, "entries", None) or []):
        out.append(entry[1])
    for item in (getattr(node, "items", None) or []):
        if item[2] is not None:
            out.append(item[2])
    return out


def observe(ns, x52, nodes):
    where = {}
    for i, node in enumerate(nodes):
        where[id(node)] = i
    out = {}

    def run(layer, fn, *args):
        kind, value = H.outcome(fn, *args)
        out.setdefault(layer, []).append((kind, plain(value, where)))

    ns["_urmm_st"].succ.clear()
    ns["_urmm_st"].cache.clear()
    reset = ns.get("_urmsg_reset")
    if reset is not None:
        reset()

    menus = [n for n in nodes if isinstance(n, ast.Menu)]
    ifs = [n for n in nodes if isinstance(n, ast.If)]

    for menu in menus:
        blocks = blocks_of(menu)
        items = [i for i in menu.items if i[2] is not None]
        run("outline", ns["_urmm_outline"], menu, blocks)
        kind, plan = H.outcome(ns["_urmm_plan"], menu, blocks)
        out.setdefault("plan", []).append((kind, plain(plan, where)))
        if kind == "ok" and plan is not None:
            kind, arms = H.outcome(ns["_urmm_arms"], menu, blocks, plan)
            out.setdefault("arms", []).append((kind, plain(arms, where)))
            if kind == "ok" and arms:
                run("cards", ns["_urmm_choice_view"], items, arms,
                    [True] * len(items), [])

        def the_map(m):
            view = ns["urm_map_build"](m, None)
            return (view.empty, [box_row(b) for b in view.boxes],
                    [tuple(bar) for bar in view.bars],
                    [tuple(d) for d in getattr(view, "diamonds", ())],
                    list(view.later), view.width, view.height)
        run("map", the_map, menu)

    for node in ifs:
        x52.PathDetection.target = node

        def chain():
            steps = ns["_urm_chain"]()
            return (steps, list(x52.Var._urmChainMeta))
        kind, value = H.outcome(chain)
        # A chain that cannot be followed raises; every caller catches any
        # exception and draws nothing. Since rework move 5b the class is
        # LookupError where the pre-rework file let URM's own exception
        # through, so THAT it raises is compared, not the class.
        out.setdefault("chain", []).append(
            (kind, "lost" if kind == "raised" else plain(value, where)))
        if kind == "ok":
            run("cards", ns["_urmm_gate_view"], value[0], lambda cond: None)
    x52.PathDetection.target = None

    for node in ifs + menus:
        for block in blocks_of(node):
            def effects(b):
                flat = ns["_urm_flatten"](b)
                return (flat, ns["_urm_reduce"](flat), ns["_urm_effects"](b))
            run("effects", effects, block)

    # A statement that cannot be read, through the cards: both files must
    # say "could not read this branch", not raise and not show nothing.
    class Broken(ast.If):
        def __init__(self):
            pass

        @property
        def entries(self):
            raise RuntimeError("broken entries")

    broken = [Broken()]
    BROKEN.append(broken)
    run("effects", ns["_urm_effects"], broken)
    run("cards", ns["_urmm_gate_view"], [("gate", "x", broken), ("else", None, broken)],
        lambda cond: None)

    skip_decisions(ns, x52, nodes, run)
    index_and_climbs(ns, nodes, where, run)

    return out


# Kept alive: a freed list's id may be handed to the next one.
BROKEN = []


def index_and_climbs(ns, nodes, where, run):
    """The script index over this script, and where it says each
    statement sits."""

    extra, links = ODD[id(nodes)]
    index = ns["_URMIndex"]()
    index.build(nodes + extra)
    for node, link in links:
        index.parent[id(node)] = link

    # RETIRED by idea 1 (a behaviour fix, 2026-11-20): "the label guessed
    # from a line number is the one the pre-rework index guessed" - it took
    # the nearest label above, even one nested in the scene before. The
    # pre-rework readers are handed the working file's guess, so "contain"
    # still compares every climb and when each reader falls back to the
    # line; the guess itself is held by check_panel.py.
    if ns is old_ns:
        live = new_ns["_URMIndex"]()
        live.build(nodes + extra)
        for node, link in links:
            live.parent[id(node)] = link
        index.label_at = live.label_at

    for i, node in enumerate(extra):
        where[id(node)] = "odd %d" % i

    tables = H.index_tables(index)
    for table in sorted(tables):
        run("index", lambda t: tables[t], table)

    for node in nodes:
        if isinstance(node, ast.Python):
            run("py", ns["_urmp_effects"], node.code.source)

    for node in nodes + extra:
        site = (getattr(node, "filename", "?"), getattr(node, "linenumber", 0), id(node))
        run("contain", ns["_urmm_label_of"], node, index)
        run("contain", index.where, site)
        run("contain", ns["_urmp_scene"], index, node, site[0], site[1])
        run("contain", ns["_urmg_in_init"], index, site)
        run("contain", ns["_urms_block"], index, node)


# id(statement list) -> the hand-made statements for it, the same objects
# for both files.
ODD = {}


def parse(source):
    """A corpus script with every statement named as the engine names it:
    the skip rules find the line the game is on by its name."""

    nodes = H.parse(source)
    assign = renpy.script.Script.assign_names
    assign = getattr(assign, "__func__", assign)      # Python 2: unbound
    assign(H.SCRIPT, H.LOADED[-1], "corpus")
    for node in nodes:
        if not isinstance(node, ast.Label):
            H.SCRIPT.labels[node.name] = node
    ODD[id(nodes)] = H.odd_nodes(nodes)
    KEPT.append(nodes)
    return nodes


KEPT = []


# Layers no longer compared with the pre-rework file, each because it was
# changed on purpose after the map was seen in a real game (FINDINGS.md,
# 2026-11-20). Their behaviour is pinned by check_maze.py instead. What IS
# still compared for the routes: "outline" - every different route through a
# menu with what it changes and how it ends - and "plan", the rejoin.
RETIRED = {
    "arms": "a split inside a way closes at its own rejoin: the raw tree has a new shape",
    "map": "the map is laid out again: boxes sized to their content, dots, tails, hover text",
}


def diff(a, b):
    """[(layer, index, left, right)] for the first difference per layer."""

    found = []
    for layer in sorted(set(a) | set(b)):
        left, right = a.get(layer, []), b.get(layer, [])
        if left == right:
            continue
        for i in range(max(len(left), len(right))):
            x = left[i] if i < len(left) else "<missing>"
            y = right[i] if i < len(right) else "<missing>"
            if x != y:
                found.append((layer, i, x, y))
                break
    return found


old_ns, old_x52 = load(H.BASELINE)
new_ns, new_x52 = load(H.GF)

failures = 0
total = 0
DEAD = {}
MAPS = [0, 0]

SKIP = [0, 0]

for name, source in SCRIPTS:
    nodes = parse(source)
    a = observe(old_ns, old_x52, nodes)
    b = observe(new_ns, new_x52, nodes)
    for kind, value in a.get("skip", []):
        SKIP[0] += 1
        SKIP[1] += (kind == "ok" and value is True)
    total += sum(len(rows) for rows in a.values())
    unexpected = [d for d in diff(a, b)
                  if (name, d[0]) not in WHITELIST and d[0] not in RETIRED]

    # A layer that only ever raises, or a map that never draws, compares
    # equal to itself and proves nothing: count what was really produced.
    for layer, rows in a.items():
        DEAD.setdefault(layer, [0, 0])
        DEAD[layer][0] += len(rows)
        DEAD[layer][1] += len([r for r in rows if r[0] == "raised"])
    maps = a.get("map", [])
    drawn = [r for r in maps if r[0] == "ok" and r[1][0] is None and r[1][1]]
    MAPS[0] += len(maps)
    MAPS[1] += len(drawn)
    if unexpected:
        failures += 1
        print("FAIL  %-18s differs from the pre-rework file" % name)
        for layer, i, x, y in unexpected[:3]:
            print("        %s #%d" % (layer, i))
            print("          before %r" % (x,))
            print("          now    %r" % (y,))
    else:
        print("pass  %-18s same as the pre-rework file" % name)

# The diff must be able to fail: alter one line of the working file's walker.
working = H.urm_source.read(H.GF)
NL = chr(10)
# Since rework move 3 that walker is the story graph's: a python statement
# with no jump in it is made to lead nowhere.
target = ("                edges.append((_URMSG_E_NEXT, nx, -1, None))" + NL
          + "                if nx is not None:" + NL
          + "                    flow.append(nx)" + NL)
if working.count(target) != 1:
    altered_ok = None
else:
    altered = working.replace(target, "                edges.append((_URMSG_E_NEXT, nx, -1, None))" + NL)
    alt_ns, alt_x52 = load(H.GF, altered)
    altered_ok = False
    for name, source in SCRIPTS[:3]:
        nodes = parse(source)
        if diff(observe(old_ns, old_x52, nodes), observe(alt_ns, alt_x52, nodes)):
            altered_ok = True

if altered_ok is None:
    # The walker has moved onto the graph; the self-test must move with it.
    failures += 1
    print("FAIL  the self-test found nothing to alter - update it for the port")
elif altered_ok:
    print("pass  the diff catches an altered walker")
else:
    failures += 1
    print("FAIL  an altered walker went unnoticed")

# The same for the skip decisions (move 6): a look-ahead that ignores jumps,
# calls and which arm of an if runs must change at least one of them.
target = "        return _urmsg_step_live(node, _urms_truth)" + NL
if working.count(target) != 1:
    failures += 1
    print("FAIL  the skip self-test found nothing to alter - update it for the port")
else:
    altered = working.replace(target, '        return getattr(node, "next", None)' + NL)
    alt_ns, alt_x52 = load(H.GF, altered)
    caught = False
    for name, source in SCRIPTS:
        nodes = parse(source)
        if "skip" in [d[0] for d in diff(observe(old_ns, old_x52, nodes),
                                         observe(alt_ns, alt_x52, nodes))]:
            caught = True
            break
    if caught:
        print("pass  the diff catches an altered skip look-ahead")
    else:
        failures += 1
        print("FAIL  an altered skip look-ahead went unnoticed")

# The same for the index and the climbs (move 8): a statement's blocks
# listed without the menu captions, and a climb that only looks one link up.
for what, layer, old_text, new_text in (
        ("a menu block linked without its caption", "index",
         '                out.append(("option", arm, item[0], item[2] or ()))',
         '                out.append(("option", arm, None, item[2] or ()))'),
        ("a panel that reads every assignment as a plain one", "py",
         "                        writes.append((name, op, ok, value))",
         '                        writes.append((name, "=", ok, value))'),
        ("a climb that stops at the nearest link", "contain",
         "        while cur is not None and n < limit:" + NL + "            n += 1" + NL
         + "            link = parents.get(id(cur))",
         "        while cur is not None and n < 1:" + NL + "            n += 1" + NL
         + "            link = parents.get(id(cur))")):
    if working.count(old_text) != 1:
        failures += 1
        print("FAIL  the self-test for %s found nothing to alter" % what)
        continue
    alt_ns, alt_x52 = load(H.GF, working.replace(old_text, new_text))
    caught = False
    for name, source in SCRIPTS:
        nodes = parse(source)
        if layer in [d[0] for d in diff(observe(old_ns, old_x52, nodes),
                                        observe(alt_ns, alt_x52, nodes))]:
            caught = True
            break
    if caught:
        print("pass  the diff catches %s" % what)
    else:
        failures += 1
        print("FAIL  %s went unnoticed" % what)

# A skip layer that never says "keep skipping" compares nothing useful.
if SKIP[1] == 0 or SKIP[1] == SKIP[0]:
    failures += 1
    print("FAIL  the skip decisions were all alike (%d of %d say skip)" % (SKIP[1], SKIP[0]))
else:
    print("pass  the skip decisions vary: %d of %d say keep skipping" % (SKIP[1], SKIP[0]))

for layer in sorted(DEAD):
    made, raised = DEAD[layer]
    if made and raised == made:
        failures += 1
        print("FAIL  the %s layer only ever raised (%d of %d): it compares nothing"
              % (layer, raised, made))
if MAPS[0] and MAPS[1] < MAPS[0] - 2:
    failures += 1
    print("FAIL  the map drew for only %d of %d menus" % (MAPS[1], MAPS[0]))
else:
    print("pass  the map really drew for %d of %d menus" % (MAPS[1], MAPS[0]))

print()
print("      per layer (made, raised): %s"
      % ", ".join("%s %d/%d" % (k, DEAD[k][0], DEAD[k][1]) for k in sorted(DEAD)))
print("      %d outputs compared over %d scripts; whitelist: %d entries"
      % (total, len(SCRIPTS), len(WHITELIST)))
print("all passed" if not failures else "%d FAILED" % failures)
sys.exit(1 if failures else 0)
