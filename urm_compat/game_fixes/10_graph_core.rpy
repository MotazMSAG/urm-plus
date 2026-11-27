# The shared story graph - see research/story_graph and FINDINGS.md (2026-11-19).
init 999 python:

    # One reader of the game's script for every feature: what runs after a
    # statement, where the story splits, where it meets again, what sits in
    # what, what a python line assigns. Before it each feature (cards, maze,
    # map, path chain, skip, index, panel) walked the script with its own
    # rules, so a traversal bug was fixed in one and not the others. They
    # moved onto this block one at a time (rework moves 1 to 9), each move
    # proven against the frozen pre-rework readers (tests/check_graph.py,
    # tests/parity_graph.py, the installer probe).
    #
    # EVERY FEATURE THAT READS THE SCRIPT NOW READS IT THROUGH THIS BLOCK.
    # For the features that existed before it, it is a port, not a
    # redesign: every function answers as the code it replaced, bugs
    # included, and raises where that code raised. Behaviour fixes are
    # separate, approved steps.
    # Two known, deliberate differences: label targets used for the edge
    # table are remembered until the script changes (the maze reader already
    # remembered them per statement), and the one remembered lookup catches
    # every exception class where two of the old readers let
    # KeyboardInterrupt and SystemExit through.
    #
    # Rules for this block (enforced by tests/run_tests.py):
    #   - It only defines names. It touches nothing in the engine, the store
    #     or URM when it loads, so tests can load it with nothing else.
    #   - No square-bracket or curly-bracket containers and no comprehensions
    #     of them, anywhere: inside a game the engine turns each into an
    #     object that rollback tracks. Use python_list, python_dict,
    #     python_set and tuples. No counting helper that returns a tracked
    #     sequence either: loops count with while.
    #   - Every class derives from python_object.
    #   - Plain ASCII, Python 2.7 and 3.
    #
    # Nothing is built ahead of time: facts are worked out when asked for
    # and remembered. Statements and block lists are keyed by id() with the
    # object kept alongside and checked on every hit.

    import re as _urmsg_re

    # Kinds. Every kind below _URMSG_K_RET has exactly one successor: .next
    _URMSG_K_PLAIN = 0
    _URMSG_K_SAY = 1
    _URMSG_K_TRANS = 2
    _URMSG_K_LABEL = 3
    _URMSG_K_USER = 4
    _URMSG_K_RET = 5
    _URMSG_K_PY = 6
    _URMSG_K_JUMP = 7
    _URMSG_K_CALL = 8
    _URMSG_K_IF = 9
    _URMSG_K_MENU = 10
    _URMSG_K_WHILE = 11

    # Edges: (type, target or None, arm index or -1, data). Types up to
    # _URMSG_E_EXIT are flow; DYN, MISS and SKIP are facts, never followed.
    _URMSG_E_NEXT = 0
    _URMSG_E_JUMP = 1
    _URMSG_E_CALL = 2
    _URMSG_E_RETSITE = 3
    _URMSG_E_ARM = 4
    _URMSG_E_FALL = 5
    _URMSG_E_ITEM = 6
    _URMSG_E_BODY = 7
    _URMSG_E_EXIT = 8
    _URMSG_E_DYN = 9
    _URMSG_E_MISS = 10
    _URMSG_E_SKIP = 11

    _URMSG_CANDIDATES = 12

    _URMSG_CAP_FACTS = 50000
    _URMSG_CAP_LABELS = 20000
    _URMSG_CAP_PY = 20000
    _URMSG_CAP_Q = 256
    _URMSG_CAP_RETURN = 4000      # statements read to see whether a call comes back

    _URMSG_PYJUMP = _urmsg_re.compile(
        r"""^renpy\.(jump|call)\(\s*(?:label\s*=\s*)?["']([\w.]+)["']\s*\)$""")

    # "URM's own next-statement rule raises here."
    _URMSG_LOST = python_object()

    # The one record for a jump that cannot be followed, and for a call that
    # cannot be entered: the target is worked out while the game runs, or it
    # is not in the script (idea 8, design fix C7). Every reader writes
    # these two texts and every display says them with the same words
    # (urm_any_chip): "Goes somewhere decided while playing".
    _URMSG_DYN_JUMP = "jump to a computed label"
    _URMSG_DYN_CALL = "call a computed label"

    # Behaviour fixes that changed what a walk or a search answers, each
    # behind one switch that is True in a game and never changed there. The
    # parity tests (check_graph.py, parity_graph.py, the installer probe)
    # turn a switch off to prove that, the fix aside, everything still
    # answers as the frozen pre-rework readers do; check_maze.py holds what
    # each fix does.
    #   FRAMES (idea 5, C4): a statement met again is a loop only when it is
    #   met again INSIDE THE SAME CALL. A scene called twice is walked twice.
    _URMSG_FIX_FRAMES = True
    #   VISIT (idea 12, C11): for the search for where ways meet again, a
    #   called scene is a visit - the search steps over a call that comes
    #   back, so a scene several ways call is not taken for the rejoin.
    _URMSG_FIX_VISIT = True
    #   SKIP (idea 13, C12): a menu with a `set` is passed without asking
    #   once its captions are used up, and a menu whose every option has a
    #   test when none of them holds: each has a way out past it, which the
    #   searches follow and the walks offer as one more way (_urmsg_skip).
    #   A menu with no option at all is passed by every walk. A statement
    #   from which the story runs straight back into the split is not
    #   where its ways "meet again": they are back at the split. And a
    #   custom statement with content inside leaves a mark where the walk
    #   passes it (_urmsg_closed).
    _URMSG_FIX_SKIP = True
    #   HOP (idea 6, C5): a python statement that jumps on an indented line
    #   - inside an if, a loop, a try - only jumps SOMETIMES. It is a check
    #   with two ways (the jump, and carrying on), and the statement's own
    #   lines count: before, such a statement was read as "always jumps"
    #   and whatever else it does was lost.
    _URMSG_FIX_HOP = True
    #   TIES (idea 3, C2): two candidates for the place where ways meet
    #   that are reached by as many ways and are as far off are told apart
    #   by where they stand in the script - the earlier one wins. Before,
    #   the order of a dict decided: on Python 2 that is the order of
    #   memory addresses, so the same menu could meet in different places
    #   from one start of the game to the next.
    _URMSG_FIX_TIES = True
    #   MEET (the mirrored paths of Now and Then, 2026-11-20): the search
    #   for where ways meet again only LOOKED AT the dozen nearest
    #   statements the ways share, and answered with the nearest of them
    #   when none held. Where the ways share a long scene that some way
    #   goes around (a scene one option of each way jumps into, another
    #   option skips), all twelve stood inside that scene, the real meeting
    #   point behind it was never looked at, and the scene's first
    #   statement was the answer. Everything behind the real meeting point
    #   was then walked, and drawn, once per way. Now the statements that
    #   CAN be where ways meet are told from the shape of the story first
    #   (_urmsg_closing), and only those are looked at.
    _URMSG_FIX_MEET = True
    #   FUNCS (a game told in phone texts, the user's pick c, 2026-11-21):
    #   a python line that does nothing but call one of the game's own
    #   functions (`$ text_message(phone, "Ann", _("Hi"))`, one text) was
    #   read as a change and drawn as code. Now the function is read from
    #   the script and followed (_urmsg_call_quiet): the line is not said
    #   when nothing it changes is read by a test of the story. Every other
    #   line is read as before.
    _URMSG_FIX_FUNCS = True

    class _URMSGState(python_object):
        __slots__ = ("g", "kinds", "classes", "passes", "pass_classes")

        def __init__(self):
            self.g = None
            self.kinds = python_dict()
            self.classes = None
            self.passes = python_dict()
            self.pass_classes = None

    class _URMSGraph(python_object):
        __slots__ = ("gen", "script", "count", "over", "facts", "labels",
                     "py", "q", "skipped", "arms", "rets", "tl", "fns", "defs",
                     "checked", "trees", "fdefs", "effects", "methods", "checked_why",
                     "lines", "twin", "base", "choices", "screens", "homes",
                     "stretch")

        def __init__(self, gen):
            self.gen = gen
            self.script = None
            self.count = 0
            self.over = 0
            self.facts = python_dict()
            self.labels = python_dict()
            self.py = python_dict()
            self.q = python_dict()
            self.skipped = 0
            self.arms = python_dict()
            # Whether a call of a label comes back (_urmsg_returns):
            # id(label) -> (label, True, False or None).
            self.rets = python_dict()
            # The statements of one language's translation blocks
            # (_urmsg_tl): (language, {id: (statement, identifier)}).
            self.tl = None
            # A line that only calls a game function: whether it is said
            # (_urmsg_call_quiet), by its text; where the script's python
            # blocks stand (_urmsg_defs): file -> [(first line, source)];
            # every path a test of the story reads (_urmsg_checked).
            self.fns = python_dict()
            self.defs = None
            self.checked = None
            # The same, remembered: a block's source parsed; a function's
            # def (by id of its code); what a call of it changes, by what
            # it is handed (_urmsg_fn_effects).
            self.trees = python_dict()
            self.fdefs = python_dict()
            self.effects = python_dict()
            # The name of every method a class of the script defines.
            self.methods = None
            # Why the tests could not all be followed (_urmsg_checked).
            self.checked_why = None
            # What a story line writes, by its text (_urmsg_line_effects).
            self.lines = python_dict()
            # The map rework's readers (12, "The player's ways"): the twin
            # they run in (its own memories, _urmsg_own), and on a twin the
            # graph it was made from; a choice of any shape by statement;
            # a screen's choice by name; the block each statement sits in.
            self.twin = None
            self.base = None
            self.choices = python_dict()
            self.screens = python_dict()
            self.homes = None
            # The stretch table (12, "Free roam and the kind of a stretch").
            self.stretch = None

    class _URMSGFact(python_object):
        __slots__ = ("node", "k", "nx", "label", "dyn", "target", "via",
                     "arms", "has_else", "e", "flow", "quiet", "pure",
                     "text_only", "flat", "skip", "flow_skip")

        def __init__(self, node, k):
            self.node = node
            self.k = k
            self.nx = getattr(node, "next", None)
            self.label = None
            self.dyn = False
            self.target = None
            self.via = None
            self.arms = ()
            self.has_else = False
            self.e = ()
            self.flow = ()
            self.quiet = None
            self.pure = None
            self.text_only = None
            self.flat = None
            # True for a statement the story may also PASS: a menu with a
            # `set` (not asked once its captions are used up) and a python
            # statement whose jump is made only sometimes; and its flow
            # with the way past it.
            self.skip = None
            self.flow_skip = ()

    class _URMSGPy(python_object):
        __slots__ = ("hop", "hop_indented", "hop_cond", "lines", "drop")

        def __init__(self):
            self.hop = None
            self.hop_indented = False
            # The test the jump stands under, when it can be read: the jump
            # is one level inside a plain `if <test>:` at the top of the
            # statement. None for anything else (an else, a loop, deeper).
            self.hop_cond = None
            self.lines = None
            self.drop = None

    class _URMSGChain(python_object):
        __slots__ = ("steps", "meta", "ways", "live", "lost", "cut")

        def __init__(self):
            self.steps = python_list()
            self.meta = python_list()
            # Parallel to steps: what each way does to the next (12,
            # _urmsg_gate_read).
            self.ways = python_list()
            self.live = False
            self.lost = False
            self.cut = False

    _urmsg_st = _URMSGState()
    _urmsg_st.g = _URMSGraph(0)

    # ------------------------------------------------------------------
    # The graph object and its freshness
    # ------------------------------------------------------------------

    def _urmsg_stamp():
        """(script object, statement count, label override count)."""

        script = None
        count = 0
        over = 0
        try:
            script = renpy.game.script
            count = len(getattr(script, "all_stmts", None) or ())
        except BaseException:
            pass
        try:
            over = len(getattr(renpy.config, "label_overrides", None) or ())
        except BaseException:
            pass
        return script, count, over

    def _urmsg_graph():
        """The current graph; a new one when the script under it changed."""

        st = _urmsg_st
        g = st.g
        script, count, over = _urmsg_stamp()
        if g.script is None and g.gen == 0 and not g.facts and not g.labels and not g.arms:
            g.script, g.count, g.over = script, count, over
            return g
        if g.script is not script or g.count != count or g.over != over:
            g = _URMSGraph(g.gen + 1)
            g.script, g.count, g.over = script, count, over
            st.g = g
        return g

    def _urmsg_reset():
        """Forget everything remembered (tests reuse one script object)."""

        st = _urmsg_st
        g = _URMSGraph(st.g.gen + 1)
        g.script, g.count, g.over = _urmsg_stamp()
        st.g = g
        return g

    def _urmsg_gen():
        return _urmsg_graph().gen

    # ------------------------------------------------------------------
    # Labels: the one lookup
    # ------------------------------------------------------------------

    def _urmsg_resolve(name):
        """
        (statement or None, settled). settled is False when the lookup
        failed in a way that may not repeat, so nothing was remembered.
        A label that truly does not exist is remembered as a miss.
        """

        g = _urmsg_graph()

        try:
            hit = g.labels.get(name, g)
        except BaseException:
            hit = None
            g = None

        if g is not None:
            if hit is False:
                return None, True
            if hit is not g:
                return hit, True

        try:
            node = renpy.game.script.lookup(name)
        except BaseException as error:
            se = getattr(getattr(renpy, "script", None), "ScriptError", None)
            is_miss = isinstance(error, se) if isinstance(se, type) else (type(error).__name__ == "ScriptError")
            if g is not None and is_miss:
                if len(g.labels) >= _URMSG_CAP_LABELS:
                    g.labels.clear()
                g.labels[name] = False
                return None, True
            if g is not None:
                g.skipped += 1
            return None, False

        if node is None:
            if g is not None:
                g.skipped += 1
            return None, False

        if g is not None:
            if len(g.labels) >= _URMSG_CAP_LABELS:
                g.labels.clear()
            g.labels[name] = node

        return node, True

    def _urmsg_lookup(name):
        return _urmsg_resolve(name)[0]

    def _urmsg_here():
        """The statement the game is on, or None. Asked of the engine every
        time: a statement's own name never goes through the label memory."""

        try:
            return renpy.game.script.lookup(renpy.game.context().current)
        except Exception:
            return None

    def _urmsg_live_stack():
        """
        The statements the game goes back to from the calls it is inside
        right now, innermost first; _URMSG_LOST in place of one that cannot
        be found, and nothing below that one. () outside any call.

        A walk or a search that starts where the game is must know these
        (idea 7, design fix C6): without them a `return` ahead, inside a
        called scene, read as the end of the story. Nothing that starts
        anywhere else may use them.
        """

        try:
            names = tuple(renpy.game.context().return_stack or ())
        except Exception:
            return ()

        out = python_list()
        n = len(names)
        while n > 0:
            n -= 1
            node = _urmsg_lookup_now(names[n])
            if node is None:
                out.append(_URMSG_LOST)
                break
            out.append(node)
        return tuple(out)

    def _urmsg_frames(sites):
        """A walk's stack to start with, for a walk that starts where the
        game is: one frame per call the game is inside (sites as
        _urmsg_live_stack gives them). Their numbers are below zero, so no
        call the walk enters itself shares one."""

        stack = python_list()
        n = len(sites)
        while n > 0:
            n -= 1
            stack.append((sites[n], -(n + 1), 0))
        return stack

    def _urmsg_sites(stack):
        """The statements a walk's stack returns to, innermost first: out of
        the calls the game is inside (_urmsg_frames) and out of the calls
        the walk entered itself. A search that starts at a split inside
        those calls is told them, and follows a `return` there - so ways
        that leave a called scene meet in the scene that called it."""

        out = python_list()
        n = len(stack)
        while n > 0:
            n -= 1
            frame = stack[n]
            if frame[0] is not None and frame[0] is not _URMSG_LOST:
                out.append(frame[0])
        return tuple(out)

    def _urmsg_returns(target, depth=0):
        """
        Whether a call of this label comes back: True when a `return` can be
        reached from it, False when every way through it was read and none
        returns (a label that is called but only ever jumps on), None when
        that could not be told. Calls inside it are visits too. Remembered
        per label until the script changes.
        """

        g = _urmsg_graph()
        hit = g.rets.get(id(target))
        if hit is not None and hit[0] is target:
            return hit[1]
        if depth > 12:
            return None

        skipped = g.skipped
        # While it is being read: a label that calls itself comes back if
        # anything in it does.
        if len(g.rets) >= _URMSG_CAP_LABELS:
            g.rets.clear()
        g.rets[id(target)] = (target, True)

        seen = python_set((id(target),))
        queue = python_list((target,))
        head = 0
        answer = False

        while head < len(queue):
            if len(seen) >= _URMSG_CAP_RETURN:
                answer = None
                break
            node = queue[head]
            head += 1
            if _urmsg_kind(node) == _URMSG_K_RET:
                answer = True
                break
            for nxt in _urmsg_flow_visit(node, depth + 1):
                if id(nxt) not in seen:
                    seen.add(id(nxt))
                    queue.append(nxt)

        if g.skipped == skipped and _urmsg_st.g is g:
            g.rets[id(target)] = (target, answer)
        else:
            g.rets.pop(id(target), None)
        return answer

    def _urmsg_flow_visit(node, depth=0):
        """
        _urmsg_flow for the search for where ways meet again: a called
        scene is a VISIT (idea 12). A call that comes back leads to the
        statement after it and not into the scene; a call that never comes
        back leads into its label, as a jump does; one that cannot be told
        leads both ways, as _urmsg_flow says for every call.
        """

        k = _urmsg_kind(node)
        if k == _URMSG_K_CALL or k == _URMSG_K_PY:
            fact = _urmsg_fact(node)
            if (k == _URMSG_K_CALL or fact.via == "call") and fact.target is not None:
                back = _urmsg_returns(fact.target, depth)
                if back is True:
                    return (fact.nx,) if fact.nx is not None else ()
                if back is False:
                    return (fact.target,)
        return _urmsg_flow(node)

    def _urmsg_flow_meet(sites):
        """The successor rule of the search for a rejoin: calls are visits
        (when that fix is on), and a `return` leads to where the calls
        around the split go back to (sites, see _urmsg_sites)."""

        step = _urmsg_flow_visit if _URMSG_FIX_VISIT else _urmsg_flow
        if not sites:
            return step

        def flow(node):
            if _urmsg_kind(node) == _URMSG_K_RET:
                return sites
            return step(node)

        return flow

    def _urmsg_flow_from(sites):
        """The successor rule for a search that starts inside calls the game
        is in: _urmsg_flow, and a `return` leads to where those calls go
        back to. With no such call it IS _urmsg_flow."""

        if not sites:
            return _urmsg_flow

        def flow(node):
            if _urmsg_kind(node) == _URMSG_K_RET:
                return sites
            return _urmsg_flow(node)

        return flow

    def _urmsg_lookup_now(name):
        """The label as the engine resolves it this instant, never from memory.
        The step functions use this: the readers they port ask every time, so
        an override or a label added mid-game is seen at once."""

        try:
            return renpy.game.script.lookup(name)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Kinds and facts
    # ------------------------------------------------------------------

    def _urmsg_kind(node):
        """Which of the twelve kinds a statement is, by its class."""

        st = _urmsg_st
        cls = type(node)
        kind = st.kinds.get(cls)
        if kind is not None:
            return kind

        classes = st.classes
        if classes is None:
            found = python_list()
            for name, k in (("Jump", _URMSG_K_JUMP), ("Call", _URMSG_K_CALL),
                            ("Return", _URMSG_K_RET), ("If", _URMSG_K_IF),
                            ("Menu", _URMSG_K_MENU), ("While", _URMSG_K_WHILE),
                            ("Python", _URMSG_K_PY), ("Label", _URMSG_K_LABEL),
                            ("Translate", _URMSG_K_TRANS), ("Say", _URMSG_K_SAY),
                            ("UserStatement", _URMSG_K_USER)):
                found_cls = getattr(renpy.ast, name, None)
                if found_cls is not None:
                    found.append((found_cls, k))
            classes = tuple(found)
            st.classes = classes

        kind = _URMSG_K_PLAIN
        for found_cls, k in classes:
            if isinstance(node, found_cls):
                kind = k
                break

        st.kinds[cls] = kind
        return kind

    def _urmsg_is_else(cond):
        """True for the arm Ren'Py adds for `else:` - a plain "True" string,
        where a test the author typed is a PyExpr."""

        try:
            return not isinstance(cond, renpy.ast.PyExpr)
        except Exception:
            return False

    def _urmsg_no_test(cond):
        """True when a menu option or an arm tests nothing: no condition, or
        one whose text is exactly `True` - whoever wrote it. The one rule for
        "is this conditional" (idea 4); `_urmsg_is_else` stays the way to
        tell an `else:` from a written `if True:`."""

        if cond is None:
            return True
        try:
            return (u"%s" % (cond,)).strip() in (u"", u"True")
        except Exception:
            return False

    def _urmsg_py(source):
        """What a python statement's source says about where it goes."""

        g = _urmsg_graph()
        hit = g.py.get(source)
        if hit is not None:
            return hit

        py = _URMSGPy()
        top = None       # the last line at the top level of the statement
        inner = None     # the indentation of the first line under it

        for raw in source.split("\n"):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            lead = raw[:len(raw) - len(raw.lstrip())]
            m = _URMSG_PYJUMP.match(line)
            if m:
                py.hop = (m.group(1), m.group(2))
                py.hop_indented = raw[:1] in (" ", "\t")
                if (py.hop_indented and top is not None
                        and (inner is None or lead == inner)
                        and top.startswith("if ") and top.endswith(":")):
                    py.hop_cond = top[3:-1].strip() or None
                break
            if not lead:
                top = line
                inner = None
            elif inner is None:
                inner = lead

        if len(g.py) >= _URMSG_CAP_PY:
            g.py.clear()
        g.py[source] = py
        return py

    def _urmsg_hop(node):
        """(verb, label) for a python statement that jumps or calls, or None."""

        try:
            return _urmsg_py(node.code.source).hop
        except Exception:
            return None

    def _urmsg_fact(node):
        """
        The facts of a statement that can send the story somewhere other
        than its .next: Jump, Call, If, Menu, While, and every Python
        statement. None for the rest.
        """

        k = _urmsg_kind(node)
        if k < _URMSG_K_PY:
            return None

        g = _urmsg_graph()
        hit = g.facts.get(id(node))
        if hit is not None and hit.node is node:
            return hit

        fact = _URMSGFact(node, k)
        nx = fact.nx
        settled = True
        edges = python_list()
        flow = python_list()

        if k == _URMSG_K_JUMP or k == _URMSG_K_CALL:
            label = node.target if k == _URMSG_K_JUMP else node.label
            fact.label = label
            fact.dyn = bool(getattr(node, "expression", False))
            if fact.dyn:
                edges.append((_URMSG_E_DYN, None, -1, label))
            else:
                target, settled = _urmsg_resolve(label)
                fact.target = target
                if target is not None:
                    edges.append((_URMSG_E_JUMP if k == _URMSG_K_JUMP
                                  else _URMSG_E_CALL, target, -1, None))
                    flow.append(target)
                else:
                    edges.append((_URMSG_E_MISS, None, -1, label))
            if k == _URMSG_K_CALL:
                edges.append((_URMSG_E_RETSITE, nx, -1, None))
                if nx is not None:
                    flow.append(nx)

        elif k == _URMSG_K_MENU:
            arms = python_list()
            index = 0
            has_set = getattr(node, "set", None) is not None
            all_cond = True
            for item in (getattr(node, "items", None) or ()):
                block = item[2]
                if block is not None:
                    start = block[0] if block else nx
                    arms.append((index, item[1], None, block, start, item[0]))
                    edges.append((_URMSG_E_ITEM, start, index, item[1]))
                    if start is not None:
                        flow.append(start)
                    if _urmsg_no_test(item[1]):
                        all_cond = False
                index += 1
            fact.arms = tuple(arms)
            edges.append((_URMSG_E_SKIP, nx, -1, (has_set, all_cond)))
            # Why the game may pass this menu without asking: it has no
            # option at all; it has a `set` (its captions get used up); or
            # every option has a test (none of them may hold).
            if not arms:
                fact.skip = "empty"
            elif has_set:
                fact.skip = "set"
            elif all_cond:
                fact.skip = "tests"

        elif k == _URMSG_K_IF:
            arms = python_list()
            index = 0
            for cond, block in (getattr(node, "entries", None) or ()):
                authored = not _urmsg_is_else(cond)
                start = block[0] if block else nx
                arms.append((index, cond, authored, block, start, None))
                edges.append((_URMSG_E_ARM, start, index, cond))
                if start is not None:
                    flow.append(start)
                if not authored:
                    fact.has_else = True
                index += 1
            fact.arms = tuple(arms)
            if not fact.has_else:
                edges.append((_URMSG_E_FALL, nx, -1, None))
                if nx is not None:
                    flow.append(nx)

        elif k == _URMSG_K_WHILE:
            block = getattr(node, "block", None)
            if block:
                edges.append((_URMSG_E_BODY, block[0], -1, None))
                if block[0] is not None:
                    flow.append(block[0])
            edges.append((_URMSG_E_EXIT, nx, -1, None))
            if nx is not None:
                flow.append(nx)

        else:
            hop = _urmsg_hop(node)
            if hop:
                fact.via, fact.label = hop
                target, settled = _urmsg_resolve(hop[1])
                fact.target = target
                if target is not None:
                    edges.append((_URMSG_E_JUMP if hop[0] == "jump"
                                  else _URMSG_E_CALL, target, -1, None))
                    flow.append(target)
                else:
                    edges.append((_URMSG_E_MISS, None, -1, hop[1]))
                if hop[0] == "call":
                    edges.append((_URMSG_E_RETSITE, nx, -1, None))
                    if nx is not None:
                        flow.append(nx)
                elif target is not None:
                    py = _urmsg_py(node.code.source)
                    if py.hop_indented:
                        # A jump made only sometimes (idea 6): the story
                        # may also pass this statement, and for the walks
                        # it is a check with one arm - the jump.
                        fact.skip = True
                        fact.arms = ((0, py.hop_cond or u"", True, (target,),
                                      target, None),)
            else:
                edges.append((_URMSG_E_NEXT, nx, -1, None))
                if nx is not None:
                    flow.append(nx)

        fact.e = tuple(edges)
        fact.flow = tuple(flow)
        if fact.skip is not None:
            if nx is not None and nx not in flow:
                flow.append(nx)
            fact.flow_skip = tuple(flow)

        if settled:
            if len(g.facts) >= _URMSG_CAP_FACTS:
                g.facts.clear()
            g.facts[id(node)] = fact

        return fact

    def _urmsg_unfollowed(node):
        """
        _URMSG_DYN_JUMP or _URMSG_DYN_CALL for a jump, a call or a python
        line that jumps or calls, when where it goes cannot be followed: the
        target is computed, or no such label is in the script. None for
        every other statement. The one test behind the one wording (idea 8):
        the walks, the records of a block and the gate chain all ask it.
        """

        k = _urmsg_kind(node)
        if k != _URMSG_K_JUMP and k != _URMSG_K_CALL and k != _URMSG_K_PY:
            return None
        fact = _urmsg_fact(node)
        if fact.label is None and not fact.dyn:
            return None
        if not fact.dyn and fact.target is not None:
            return None
        if k == _URMSG_K_CALL or fact.via == "call":
            return _URMSG_DYN_CALL
        return _URMSG_DYN_JUMP

    def _urmsg_arms(node):
        fact = _urmsg_fact(node)
        return fact.arms if fact is not None else ()

    def _urmsg_has_else(node):
        fact = _urmsg_fact(node)
        return bool(fact is not None and fact.has_else)

    def _urmsg_flow(node):
        """Every statement control can reach next, in a fixed order."""

        k = _urmsg_kind(node)
        if k < _URMSG_K_RET:
            nx = getattr(node, "next", None)
            return (nx,) if nx is not None else ()
        if k == _URMSG_K_RET:
            return ()
        fact = _urmsg_fact(node)
        if fact.skip is not None:
            if (_URMSG_FIX_SKIP if fact.k == _URMSG_K_MENU else _URMSG_FIX_HOP):
                return fact.flow_skip
        return fact.flow

    def _urmsg_hop_some(node):
        """True for a python statement whose jump is made only sometimes
        (idea 6): for the walks it is a check, with the jump as its one arm
        (_urmsg_arms) and carrying on as "otherwise"."""

        if not _URMSG_FIX_HOP or _urmsg_kind(node) != _URMSG_K_PY:
            return False
        return _urmsg_fact(node).skip is not None

    def _urmsg_skip_why(node):
        """
        Why the game may pass a menu WITHOUT ASKING (idea 13), or None for
        a menu it always asks. The engine shows no menu when it has no
        option to offer and carries on with the statement after it.

        "set"    the menu has a `set`: a caption that was chosen is not
                 offered again, so once all are used up nothing is left to
                 pick. In a hub - every option jumps back to the menu -
                 that is the only way out.
        "tests"  every option has a test: when none of them holds there is
                 nothing to offer. Whether that can happen is not in the
                 script ("Kiss" if love >= 3, "Wave" if love < 3 never is),
                 so the way past such a menu is always there, and whoever
                 draws it says whether it is open as the game stands (the
                 user's pick 2a, 2026-11-20).

        A menu with a `set` whose options all have tests is "set": nothing
        left to pick covers both. None for a menu with no option at all
        (the walk passes that one without a word).
        """

        if not _URMSG_FIX_SKIP or _urmsg_kind(node) != _URMSG_K_MENU:
            return None
        why = _urmsg_fact(node).skip
        return why if why in ("set", "tests") else None

    def _urmsg_skip(node):
        """True for a menu the game may pass without asking - it has a way
        past it, which the searches follow and the walks offer as one more
        way of the split (_urmsg_skip_why says which kind)."""

        return _urmsg_skip_why(node) is not None

    def _urmsg_closed(node):
        """
        True for a custom statement WITH CONTENT INSIDE: a statement the
        game registered itself (renpy.register_statement) that has a block
        under it - lines only its own code reads (.block), script
        (.code_block), or statements it had the engine parse for it
        (.subparses). What is in there, and whether it runs, is decided by
        the game's own code; every reader here passes the statement as one
        statement, and the walks leave a mark saying so (_URMSG_MARK_CODE).
        False for a custom statement on one line (`play music ...`).
        """

        if _urmsg_kind(node) != _URMSG_K_USER:
            return False
        try:
            if getattr(node, "block", None) or getattr(node, "code_block", None):
                return True
            for sub in getattr(node, "subparses", None) or ():
                if getattr(sub, "block", None):
                    return True
        except Exception:
            pass
        return False

    def _urmsg_closed_in(nodes, depth=0):
        """True when a block holds a custom statement with content inside,
        itself or in an if inside it (as deep as _urmsg_flat reads)."""

        if depth > _URMSG_MAX_DEPTH:
            return False
        for node in (nodes or ()):
            k = _urmsg_kind(node)
            if k == _URMSG_K_USER:
                if _urmsg_closed(node):
                    return True
            elif k == _URMSG_K_IF:
                for _cond, block in (getattr(node, "entries", None) or ()):
                    if _urmsg_closed_in(block, depth + 1):
                        return True
        return False

    # ------------------------------------------------------------------
    # What a statement says, and whether an if is quiet
    # ------------------------------------------------------------------

    def _urmsg_stmt_text(node):
        """One statement as one line of plain text, or None to ignore it."""

        k = _urmsg_kind(node)

        if k == _URMSG_K_JUMP:
            return _urmsg_unfollowed(node) or "jump %s" % node.target

        if k == _URMSG_K_CALL:
            return _urmsg_unfollowed(node) or "call %s" % node.label

        if k == _URMSG_K_RET:
            return "return"

        if k == _URMSG_K_USER:
            try:
                head = node.parsed[0][0]
            except Exception:
                head = None
            if head == "call":
                return node.line.strip()

        return None

    def _urmsg_quiet_if(node, depth=0):
        """An if whose arms only change pictures, sound or values."""

        ast = renpy.ast
        if depth > 4:
            return False
        for _cond, block in node.entries:
            for child in block or ():
                if isinstance(child, (ast.Say, ast.Menu, ast.Jump, ast.Call, ast.Return)):
                    return False
                if isinstance(child, ast.If) and not _urmsg_quiet_if(child, depth + 1):
                    return False
                if isinstance(child, ast.Translate):
                    return False
        return True

    # Statements a dialogue line can sit next to without leaving its passage.
    _URMSG_PASSES = ("If", "Translate", "EndTranslate", "Show", "Scene",
                     "Hide", "With", "Python", "Pass", "UserStatement",
                     "ShowLayer", "Camera")

    def _urmsg_passes(node):
        """True for a statement the skip look-back may step over: it shows
        no line and offers no choice. Answered once per statement class."""

        st = _urmsg_st
        cls = type(node)
        hit = st.passes.get(cls)
        if hit is not None:
            return hit

        classes = st.pass_classes
        if classes is None:
            found = python_list()
            for name in _URMSG_PASSES:
                found_cls = getattr(renpy.ast, name, None)
                if found_cls is not None:
                    found.append(found_cls)
            classes = tuple(found)
            st.pass_classes = classes

        hit = isinstance(node, classes)
        st.passes[cls] = hit
        return hit

    def _urmsg_blocks_urm(node):
        """Whether the reader stops at this interaction or pause."""
        if getattr(node, "interact", False):
            return True
        if _urmsg_kind(node) != _URMSG_K_USER:
            return False
        user_statement = getattr(node, "get_code", None)
        return callable(user_statement) and user_statement() == "pause"

    # ------------------------------------------------------------------
    # Two ways of taking one step
    # ------------------------------------------------------------------

    def _urmsg_step_urm(node):
        """
        The next statement for the look-ahead reader. Follow a jump or call
        to its target, or return _URMSG_LOST if a lookup fails.
        """

        k = _urmsg_kind(node)

        if k == _URMSG_K_CALL:
            label = getattr(node, "label", None)
            if label:
                try:
                    return renpy.game.script.lookup(label)
                except Exception:
                    return _URMSG_LOST
            return None

        if k == _URMSG_K_JUMP:
            if getattr(node, "expression", False):
                predict = getattr(node, "predict", None)
                if predict is None or not callable(predict):
                    return None
                try:
                    found = predict()
                except Exception:
                    return _URMSG_LOST
                if len(found) > 0 and isinstance(found[0], renpy.ast.Node):
                    return found[0]
                return None
            try:
                return renpy.game.script.lookup(node.target)
            except Exception:
                return _URMSG_LOST

        return getattr(node, "next", None)

    def _urmsg_step_live(node, truth):
        """
        The statement that runs after this one as the game stands now, or
        None where that cannot be told. truth(cond) gives True, False or
        None for "cannot tell".
        """

        k = _urmsg_kind(node)

        if k == _URMSG_K_TRANS:
            return node.block[0] if node.block else node.next

        if k == _URMSG_K_JUMP:
            if getattr(node, "expression", False):
                return None
            return _urmsg_lookup_now(node.target)

        if k == _URMSG_K_CALL:
            if getattr(node, "expression", False):
                return None
            return _urmsg_lookup_now(node.label)

        if k == _URMSG_K_MENU or k == _URMSG_K_RET or k == _URMSG_K_WHILE:
            return None

        if k == _URMSG_K_IF:
            fact = _urmsg_fact(node)
            if fact.quiet is None:
                fact.quiet = _urmsg_quiet_if(node)
            if fact.quiet:
                return node.next
            for cond, block in node.entries:
                taken = truth(cond)
                if taken is None:
                    return None
                if taken:
                    return block[0] if block else node.next
            return node.next

        if k == _URMSG_K_LABEL:
            return node.block[0] if getattr(node, "block", None) else node.next

        return getattr(node, "next", None)

