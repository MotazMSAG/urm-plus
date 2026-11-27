# ---------------------------------------------------------------------------
# The new map's model (B1): one list of steps, read from the player's ways
# ---------------------------------------------------------------------------
#
# What the new map will draw, as data - nothing here draws, and today's map
# (30-34) is left as it is. The steps follow the story from a statement:
# the next place it splits, where its ways meet again, the next split from
# there, and so on. A split is a choice of any shape the core reads (12,
# "The player's ways": a menu, a called screen, a room, a menu a function
# shows, a route the code picks) or a check that sends the story different
# ways (the gate chain, _urmsg_chain - separate if-statements kept apart).
#
# Every reader asked runs in the graph's twin (_urmsg_own), and what is
# worked out here is kept in our own memory: asking the model never changes
# what today's map is told (FINDINGS.md 2026-11-23, "Does this call come
# back depends on what was asked first"). It is asked only while a screen is
# drawn or a test asks: never from the script index's thread.
#
# When it cannot tell, it says nothing: a choice whose ways cannot be told
# apart gives its captions only - no meeting point, no changes, nothing lit
# or faded; a check with a test that cannot be told now lights nothing; a
# room, a jump through a name, a screen the game does not have end the list.

init 999 python:

    import re as _urmnm_re

    _URMNM_STEPS = 4         # steps in one list
    _URMNM_SEARCH = 3000     # statements searched for the next split
    _URMNM_WALK = 4000       # statements walked along one way, or searched for the meeting
    _URMNM_IFS = 8           # separate if-statements one check may hold

    # Shapes where the player picks the way in a place: a room. Whether the
    # stretch around one is the story or free roam is not told yet (map
    # rework Batch 2), so the list ends at a room (the plan check, must 5).
    _URMNM_ROOMS = ("ui", "shown")

    class _URMNMGate(python_object):
        """
        A test a way stands behind. words: the test in plain words, or None
        when it cannot be said so (never code). have: what the player has
        against it, "you have 1, needs 3", or None. holds: True, False or
        None (cannot be told now: a call, a value the screen itself
        decides, a value written on the way to the test).
        """

        __slots__ = ("test", "wanted", "words", "have", "holds", "told")

        def __init__(self, test, wanted=True, told=True):
            self.test = test
            self.wanted = wanted
            self.told = told
            self.words = None
            self.have = None
            self.holds = None

    class _URMNMChange(python_object):
        """
        What a way changes before the ways meet. name: the store name, words:
        the name said plainly; op "+", "-", "=" or None (written some other
        way); amount: the literal written, or None. tone: "gain", "loss",
        "set" or "other". read: True when a test of the story reads it,
        None when that cannot be told (never False: those are left out).
        sometimes: it happens only under a check inside the way.
        """

        __slots__ = ("name", "words", "op", "amount", "tone", "read", "sometimes")

        def __init__(self, name, op, amount, read, sometimes):
            self.name = name
            self.words = _urmm_pretty(name) if name else None
            self.op = op
            self.amount = amount
            self.read = read
            self.sometimes = sometimes
            neg = isinstance(amount, (int, float)) and not isinstance(amount, bool) and amount < 0
            if op == "+":
                self.tone = "loss" if neg else "gain"
            elif op == "-":
                self.tone = "gain" if neg else "loss"
            elif op == "=":
                self.tone = "set"
            else:
                self.tone = "other"

    class _URMNMWay(python_object):
        """
        One way of a step. caption: the game's own words for it, or None.
        gates: _URMNMGate it stands behind. changes: _URMNMChange list, or
        None when not told (the step's ways are not told apart, or a line on
        it cannot be read). whole: the changes run to the meeting point (no
        split or loss on the way). tail: "otherwise" or "then" for the last
        way of a check that tests nothing (UX rule 25), else None. lit /
        faded: this way is open (offered, or taken by the game) / closed, as
        things stand; both False when it cannot be told. end, said,
        said_cut: where it goes after the split and the fewest said lines
        on it before the meeting point (12, _URMSGApartWay); None when the
        step's ways are not told apart.
        """

        __slots__ = ("caption", "gates", "changes", "quiet", "whole", "tail", "lit",
                     "faded", "start", "end", "said", "said_cut")

        def __init__(self, caption=None, gates=(), tail=None):
            self.caption = caption
            self.gates = tuple(gates)
            self.changes = None
            self.quiet = ()
            self.whole = False
            self.tail = tail
            self.lit = False
            self.faded = False
            self.start = None
            self.end = None
            self.said = None
            self.said_cut = False

    class _URMNMStep(python_object):
        """
        One split. kind: "choice" (the player picks), "pick" (the code
        picks a route), "check" (the game's tests pick). shape: the
        choice's shape (12, _URMSGChoice) or "check". chain: "one" (one
        if/elif, the first that holds is taken) or "apart" (each way stands
        on its own test; more than one can be open). told: the ways can be
        told apart - only then is there a meeting point and changes. whole:
        no way is missing. meet: the statement where the ways meet again,
        or None (not told, not found, or a way that does not get there
        cannot be told). flavour: True when no change on any way is read
        later, None when that cannot be told. versions: the ways are
        versions of one value (12, _URMSGVersions), or None; which one
        holds now is the lit way.
        """

        __slots__ = ("kind", "shape", "node", "chain", "told", "whole", "ways",
                     "meet", "flavour", "states", "versions", "short_checks")

        def __init__(self, kind, shape, node, chain):
            self.kind = kind
            self.shape = shape
            self.node = node
            self.chain = chain
            self.told = False
            self.whole = True
            self.ways = ()
            self.meet = None
            self.flavour = None
            self.states = None
            self.versions = None
            self.short_checks = ()

    class _URMNMState(python_object):
        def __init__(self):
            # id(start) -> (start, graph, steps): the steps as the script
            # says them, kept until the script changes. What holds now is
            # worked out again at every ask.
            self.steps = python_dict()
            # id(if-statement) -> (it, its gate chain): the checks in a row
            # that start at it (_urmsg_chain).
            self.chains = python_dict()
            self.graph = None

    def _urmnm_st():
        return _urm_kept("newmap", _URMNMState)

    # ---- the list

    def urmnm_model(start=None, steps=_URMNM_STEPS):
        """
        The new map's steps from start (default: the statement the game is
        on), at most `steps` of them, as things stand now. [] when there is
        no split ahead that can be read.
        """

        g0 = _urmsg_own()
        try:
            return _urmsg_drain(_urmnm_model_steps(start, steps))
        finally:
            _urmsg_own_end(g0)

    def urmnm_model_steps(start=None, steps=_URMNM_STEPS):
        """urmnm_model in steps, for the worker (a generator ending with
        _URMSGDone(steps)): the twin is in place only while a step runs."""

        return _urmsg_owned_steps(_urmnm_model_steps(start, steps))

    def _urmnm_model_steps(start, steps):
        node = start if start is not None else _urmsg_here()
        if node is None:
            yield _URMSGDone(python_list())
            return
        # Where the game is, the calls it is inside are known: a
        # `return` ahead leads back into them, and with none a `return`
        # ends the game. From any other statement neither is known.
        around = ((), False)
        if start is None:
            live = _urmsg_live_stack()
            if all(site is not _URMSG_LOST for site in live):
                around = (tuple(live), not live)
        out = python_list()
        for said in _urmnm_steps_steps(node, steps, around):
            if isinstance(said, _URMSGDone):
                out = said.result
                break
            yield said
        for step in out:
            _urmnm_now(step)
        yield _URMSGDone(out)

    def _urmnm_steps_steps(start, limit, around=((), False)):
        """The steps from start, at most limit, in steps (the twin in
        place while each runs: _urmnm_model_steps)."""

        st = _urmnm_st()
        g = _urmsg_graph()
        if st.graph is not g:
            st.steps.clear()
            st.chains.clear()
            st.graph = g
        sites = tuple(around[0])
        key = (id(start), limit, tuple(id(site) for site in sites), around[1])
        hit = st.steps.get(key)
        if hit is not None and hit[0] is start and all(a is b for a, b in zip(hit[2], sites)):
            yield _URMSGDone(hit[1])
            return
        out = python_list()
        node = start
        while node is not None and len(out) < limit:
            at, _cut = _urmsg_next_split_in(node, _urmnm_no_truth, _URMNM_SEARCH,
                                            _urmsg_flow_ways_in, _urmnm_is_split)
            if at is None:
                break
            if around != ((), False) and _urmnm_enters_call(node, at):
                # The search may have gone into a called scene on its way:
                # a `return` there goes back to its caller.
                around = ((), False)
            pending = python_list()
            if node is not at:
                for pause in _urmnm_short_steps(node, at, pending):
                    yield pause
            step, split = _urmnm_step(at, around)
            if step is None:
                break
            if split is not None:
                for said in _urmnm_split_steps(*split):
                    yield said
            step.short_checks = tuple(pending)
            out.append(step)
            if step.shape in _URMNM_ROOMS or not step.told:
                break
            node = step.meet
            if any(node is site for site in around[0]):
                # Out of a call the game is in: what is around is not known.
                around = ((), False)
        if len(st.steps) >= 64:
            st.steps.clear()
        st.steps[key] = (start, out, sites)
        yield _URMSGDone(out)

    def _urmnm_short_steps(node, card, found):
        """Read short checks for the connector into the already chosen card.

        The card search must stay independent. Advancing past a short check
        can skip a full card in another arm of its enclosing condition.
        """
        seen = python_set()
        while node is not None and node is not card:
            short = python_list()
            reached = python_list()
            at, _cut = _urmsg_next_split_in(
                node, _urmnm_no_truth, _URMNM_SEARCH, _urmsg_flow_ways_in,
                lambda n: _urmnm_connector_check(n, card, short, reached))
            if not short or id(at) in seen:
                return
            seen.add(id(at))
            found.extend(short)
            # If the selected card belongs to an arm we just read, its
            # enclosing check's continuation is already past that card.
            if reached:
                return
            node = at.next
            yield None

    def _urmnm_no_truth(cond):
        return None

    def _urmnm_enters_call(node, at):
        """True when the story from node to the split at may go into a
        called scene first: a call (or a choice's way that calls) whose
        `return` is not known to come back, so that the search stepped into
        it, or a call through a name; and when that cannot be read whole."""

        table, cut = _urmsg_reach(node, at, _URMNM_SEARCH, True, _urmsg_flow_ways_in)
        if cut:
            return True
        for _d, one in table.values():
            if one is at:
                continue
            if _urmsg_unfollowed(one) == _URMSG_DYN_CALL:
                return True
            k = _urmsg_kind(one)
            if k == _URMSG_K_CALL or k == _URMSG_K_PY:
                fact = _urmsg_fact(one)
                if ((k == _URMSG_K_CALL or fact.via == "call") and fact.target is not None
                        and _urmsg_returns(fact.target) is not True):
                    return True
            choice = _urmsg_choice_in(one)
            if choice is not None and any(
                    way.go == "visit" and way.target is not None
                    and _urmsg_returns(way.target) is not True for way in choice.ways):
                return True
        return False

    def _urmnm_is_split(node, short=None, outer=()):
        """A choice of any shape, or a check that sends the story different
        ways: an if-statement that may leave, or one that only changes lines
        but starts a row of separate checks one of which may (the first way
        of the row is where the game starts picking), or one that only
        changes lines but tells a scene in versions of one value, or whose
        ways say 20 lines more one than another (_urmnm_lines_apart).
        The main story walk also stops to collect short checks in `short`."""

        if _urmsg_choice_in(node) is not None:
            return True
        if _urmsg_kind(node) != _URMSG_K_IF:
            return False
        if not _urmsg_pure((node,), 0):
            return True
        chain = _urmnm_chain(node)
        if any(fact[1] is not False for fact, (kind, _c, _b) in zip(chain.ways, chain.steps)
               if kind != "tail"):
            return True
        return _urmnm_lines_apart(node, short, outer)

    def _urmnm_connector_check(node, card, short, reached, outer=()):
        if node is card:
            reached.append(node)
            return True
        own = python_list()
        if _urmnm_is_split(node, own, outer) and not own:
            return True
        if _urmsg_kind(node) != _URMSG_K_IF:
            return False

        short.extend(own)
        entries = getattr(node, "entries", None) or ()
        for i, (_cond, block) in enumerate(entries):
            conditions = outer + _urmnm_arm_conditions(entries, i)
            for stmt in block or ():
                if stmt is card:
                    reached.append(stmt)
                    break
                if _urmsg_kind(stmt) != _URMSG_K_IF:
                    if _urmsg_choice_in(stmt) is not None:
                        break
                    continue
                inner = python_list()
                boundary = python_list()
                split = _urmnm_connector_check(stmt, card, inner, boundary, conditions)
                short.extend(inner)
                reached.extend(boundary)
                if boundary or (split and not inner):
                    break
        return bool(short or reached)

    # The user's 1b(20): a check the game decides forks the line when its
    # ways differ by this many said lines or more (DECISIONS 2026-11-23).
    _URMNM_APART_LINES = 20

    def _urmnm_arm_conditions(entries, i):
        earlier = tuple((cond, False) for cond, _block in entries[:i])
        if i < len(entries) and not _urmsg_is_else(entries[i][0]):
            return earlier + ((entries[i][0], True),)
        return earlier

    def _urmnm_lines_apart(node, short, outer):
        """For one if/elif that only changes lines: True when its ways are
        versions of one value (12, _urmsg_versions), or when one way says
        20 lines or more than another (fewest lines, exact for the shorter;
        no else counts as a way of no lines)."""

        entries = getattr(node, "entries", None) or ()
        if not entries:
            return False
        has_else = _urmsg_is_else(entries[-1][0])
        tests = python_list(() if _urmsg_is_else(cond) else ((cond, True),)
                            for cond, _b in entries)
        if not has_else:
            tests.append(())
        if _urmsg_versions(node, tests) is not None:
            return True
        counts = python_list()
        for _cond, block in entries:
            counts.append(_urmsg_said_to(block[0] if block else node.next, node, node.next,
                                         _URMNM_WALK, _urmsg_flow, python_dict()))
        if not has_else:
            counts.append((0, False))
        exact = python_list(n for n, floor in counts if n is not None and not floor)
        if not exact:
            return False
        least = min(exact)
        if any(n is not None and n - least >= _URMNM_APART_LINES for n, _f in counts):
            return True
        if short is None or len(exact) != len(counts) or max(exact) - least < 5:
            return False
        outcomes = python_dict()
        for i, (count, _floor) in enumerate(counts):
            extra = count - least
            if extra >= 5:
                outcomes.setdefault(extra, python_list()).append(
                    outer + _urmnm_arm_conditions(entries, i))
        short.extend((extra, tuple(outcomes[extra])) for extra in sorted(outcomes))
        return True

    def _urmnm_chain(node):
        st = _urmnm_st()
        hit = st.chains.get(id(node))
        if hit is not None and hit[0] is node:
            return hit[1]
        chain = _urmsg_chain(node, _URMNM_SEARCH, _urmsg_blocks_urm, _urmsg_step_urm,
                             _URMNM_IFS)
        if len(st.chains) >= 512:
            st.chains.clear()
        st.chains[id(node)] = (node, chain)
        return chain

    def _urmnm_step(node, around=((), False)):
        """(step, split): the step at node, and the arguments of its
        _urmnm_split still to run (the caller runs it, in steps); (None,
        None) when there is none."""

        if _urmsg_kind(node) == _URMSG_K_IF:
            return _urmnm_check(node, around)
        choice = _urmsg_choice_in(node)
        if choice is None:
            return None, None
        if choice.shape == "screen" and choice.screen and _urmsg_screen_find(choice.screen) is None:
            # A screen the game does not have: nobody picks anything there
            # (Him's `call screen gameplay`). No step, and nothing past it.
            return None, None
        step =_URMNMStep("pick" if choice.shape == "code" else "choice", choice.shape, node,
                          "one" if choice.shape == "code" else "apart")
        step.whole = choice.whole
        ways = python_list()
        starts = python_list()
        told = choice.whole and len(choice.ways) > 1
        # What the code writes before it tests (`score = a + b`, then `if
        # score > 3`): a test that reads it is not asked now - the value now
        # is not the value there.
        written = _urmnm_before_writes(node) if step.kind == "pick" else frozenset()
        for way in choice.ways:
            gates = python_list(_URMNMGate(test, wanted, _urmnm_told(test, way.inside, written))
                                for test, wanted in way.tests)
            one = _URMNMWay(way.caption, gates)
            if step.kind == "pick" and all(not wanted for _t, wanted in way.tests):
                one.tail = "otherwise"
            one.start = _urmsg_way_start(choice, way)
            # A way the player picks that comes back to where the choice was
            # (a function's menu, a scene visited) goes its own way only
            # through the check that reads what it hands on: without that
            # arm it is not told. (An arm of a route picked in code that
            # does not jump simply carries on after the block.)
            if one.start is None or (way.go in ("back", "visit") and way.arm is None
                                     and step.kind == "choice"):
                told = False
            starts.append(one.start)
            ways.append(one)
        if told and len(python_set(id(s) for s in starts)) < 2:
            told = False
        step.ways = tuple(ways)
        if step.kind == "pick":
            step.versions = _urmsg_versions(node, python_list(way.tests for way in choice.ways),
                                            choice.whole)
        return step, (step, node, choice.after, starts, told, around)

    def _urmnm_before_writes(node):
        """The keys a python block writes before its first if-statement at
        the top (where a route picked in code is tested); _URMSG_ALL when
        that cannot be told."""

        try:
            source = node.code.source
            tree = _urmsg_tree(source)
            at = None
            for top in tree.body:
                if _urmsg_kind_of(top) == "If":
                    at = top.lineno
                    break
            if at is None:
                return frozenset((_URMSG_ALL,))
            before = u"\n".join(source.splitlines()[:at - 1]).strip()
            if not before:
                return frozenset()
            paths = _urmsg_line_writes(before)
        except Exception:
            paths = None
        return frozenset(_urmsg_keys_of(paths))

    def _urmnm_told(test, inside, written):
        if test is None or inside:
            return False
        if not written:
            return True
        if _URMSG_ALL in written:
            return False
        return not (_urmsg_test_keys(test) & written)

    def _urmnm_check(node, around=((), False)):
        chain = _urmnm_chain(node)
        if not chain.steps:
            return None, None
        facts = python_list(chain.ways)
        steps = python_list(chain.steps)
        metas = python_list(chain.meta)
        if steps[-1][0] == "gate" and not (chain.lost or chain.cut):
            # The checks end with no else and nothing said after them: the
            # story still falls through. The chain keeps such a way only
            # when a line follows it (it was made for the corner card).
            steps.append(("tail", None, u""))
            metas.append((None, -1))
            facts.append((facts[-1][0] + 1, None, frozenset(), frozenset(), frozenset()))
        groups = python_set(fact[0] for fact in facts if any(
            f is fact for f, s in zip(facts, steps) if s[0] != "tail"))
        step = _URMNMStep("check", "check", node, "apart" if len(groups) > 1 else "one")
        step.states = (steps, facts)
        ways = python_list()
        starts = python_list()
        last = None
        for at, ((kind, cond, block), (stmt, _arm)) in enumerate(zip(steps, metas)):
            if kind == "gate":
                one = _URMNMWay(None, (_URMNMGate(cond),))
            else:
                one = _URMNMWay(None, (), _urmnm_tail(kind, facts, at))
            if stmt is not None:
                last = stmt
                one.start = block[0] if block else stmt.next
            else:
                one.start = last.next if last is not None else None
            starts.append(one.start)
            ways.append(one)
        step.ways = tuple(ways)
        told = not (chain.lost or chain.cut) and all(s is not None for s in starts)
        if step.chain == "one":
            step.versions = _urmsg_versions(
                node, python_list(((cond, True),) if kind == "gate" else ()
                                  for kind, cond, _b in steps),
                not (chain.lost or chain.cut))
        return step, (step, node, last.next if last is not None else None, starts, told, around)

    def _urmnm_tail(kind, facts, at):
        """The last way of a check: "otherwise" after one if/elif or when
        every way of the check before it leaves; "then" when the story also
        gets there after a way of it that carries on (UX rule 25)."""

        if kind != "tail" or at >= len(facts):
            return "otherwise"
        if any(leaves is not True for _g, leaves, _b, _w, _r in facts[:at]):
            return "then"
        return "otherwise"

    def _urmnm_split_steps(step, node, after, starts, told, around=((), False)):
        """Where the ways go after the split (12, _urmsg_apart: the meeting
        point, kept only when two or more ways reach it and every other way
        is told), and what each changes on its way there. In steps, the
        twin in place (_urmnm_model_steps)."""

        step.told = told
        if not told:
            return
        apart = None
        for said in _urmsg_apart_steps(starts, node, after, _URMNM_WALK, around[0], around[1]):
            if isinstance(said, _URMSGDone):
                apart = said.result
                break
            yield said
        step.meet = apart.meet
        for way, fact in zip(step.ways, apart.ways):
            way.end, way.said, way.said_cut = fact.end, fact.said, fact.said_cut
        checked = _urmsg_checked()
        flavour = True if step.meet is not None else None
        for way in step.ways:
            way.changes, way.quiet, way.whole = _urmnm_changes(way, node, step.meet, checked)
            if way.changes is None or not way.whole:
                flavour = None
            elif flavour is not None and any(c.read is not False for c in way.changes):
                if any(c.read is True for c in way.changes):
                    flavour = False
                elif flavour is True:
                    flavour = None
        step.flavour = flavour

    _URMNM_SET = _urmnm_re.compile(r"^\s*([A-Za-z_][\w.]*)\s*(\+=|-=|=)(?!=)\s*(.+?)\s*$")

    def _urmnm_changes(way, origin, meet, checked):
        """(changes or None, quiet, whole): what the way writes from its start
        to the meeting point that a test of the story may read, plus quiet
        writes (read is False) kept separately so flavour stays unchanged."""

        w = _URMSGWalk(id(meet) if meet is not None else None, origin, _URMNM_WALK,
                       _URMSG_KEEP_ARM, None, True)
        records, end, _at = _urmsg_run(w, way.start, python_list(), python_set())
        out = python_list()
        quiet = python_list()
        for guards, text in records:
            keys = None
            paths = _urmsg_line_effects(text)
            if paths is None:
                return None, (), False
            for path in paths:
                if keys is None:
                    keys = python_set()
                keys.update(_urmsg_keys(path))
            if not keys:
                continue
            read = _urmnm_read(keys, checked)
            m = _URMNM_SET.match(u"%s" % (text,))
            if read is False:
                if m is not None:
                    op = {"+=": "+", "-=": "-", "=": "="}[m.group(2)]
                    quiet.append(_URMNMChange(m.group(1), op, _urmnm_amount(m.group(3)), False,
                                              bool(guards)))
                continue
            if m is not None:
                op = {"+=": "+", "-=": "-", "=": "="}[m.group(2)]
                out.append(_URMNMChange(m.group(1), op, _urmnm_amount(m.group(3)), read,
                                        bool(guards)))
            else:
                out.append(_URMNMChange(None, None, None, read, bool(guards)))
        return out, tuple(quiet), end[0] in ("meet", "return")

    def _urmnm_read(keys, checked):
        if checked is None or checked == _URMSG_ANY or _URMSG_ALL in keys:
            return None
        for key in keys:
            if key in checked:
                return True
        return False

    def _urmnm_amount(text):
        try:
            import ast
            value = ast.literal_eval(text)
        except Exception:
            return None
        if isinstance(value, (type(u""), type(""))):
            # A label's name kept in a value (Being a DIK's events): a
            # script name, never said.
            return None if _urmsg_lookup(value) is not None else value
        if isinstance(value, (bool, int, float)):
            return value
        return None

    # ---- as things stand now

    def _urmnm_now(step):
        """What holds now: each gate's words, what the player has and
        whether it holds; which ways are open (lit) or closed (faded).
        Nothing is lit or faded when one way cannot be told."""

        for way in step.ways:
            way.lit = way.faded = False
        if step.kind == "check":
            states = _urmsg_gate_read(step.states[0], _urm_truth, step.states[1])
            for way, (state, _number, told) in zip(step.ways, states):
                for gate in way.gates:
                    gate.told = told
                    _urmnm_gate_now(gate)
            if any(state == "unknown" for state, _n, _t in states):
                return
            for way, (state, _number, _told) in zip(step.ways, states):
                way.lit = state == "runs"
                way.faded = state == "dead"
            return
        opens = python_list()
        for way in step.ways:
            is_open = True
            for gate in way.gates:
                _urmnm_gate_now(gate)
                if gate.holds is None:
                    is_open = None
                elif gate.holds is not gate.wanted and is_open is not None:
                    is_open = False
            opens.append(is_open)
        if not step.told or any(o is None for o in opens):
            return
        for way, is_open in zip(step.ways, opens):
            way.lit = is_open is True
            way.faded = is_open is False

    def _urmnm_gate_now(gate):
        test = gate.test
        if test is None:
            gate.words = gate.have = gate.holds = None
            return
        text = (u"%s" % (test,)).strip()
        # A test of a label's name is said as nothing (35, _urmw_simple).
        if gate.wanted:
            gate.words = _urmw_say(text, flags=True)
        else:
            flipped = _urmw_not(text)
            gate.words = _urmw_simple(flipped) if flipped is not None else None
        if not gate.told:
            gate.have = gate.holds = None
            return
        gate.have = urm_goal_words(text)
        holds = _urm_truth(text)
        gate.holds = holds if holds in (True, False) else None

    # ---- by place: what each place starts, open now or one step away
    #
    # The user's 4a (sandbox by place, open now in green, one step away with
    # what it needs) and map rework 5 (gates read honestly, keyed by the
    # value they test). Nothing is drawn.

    class _URMNMScene(python_object):
        """
        A scene a place starts: way, the check's way (_URMNMWay: its gate's
        words, lit / faded as things stand); state "open" (the game takes it
        now), "step" (one test of one value short), "locked" (two or more
        short) or None (cannot tell: a test that cannot be told now, one
        that reads what the place or the lines after it write, a way the
        game passes for an earlier one). key: the value the one unmet test
        reads; need: what it still needs in words, or None.
        """

        __slots__ = ("way", "state", "key", "need")

        def __init__(self, way):
            self.way = way
            self.state = None
            self.key = None
            self.need = None

    def urmnm_places(step):
        """
        For a step where the player picks (a room, a screen, a menu): one
        (place, scenes) per way - place: the step's _URMNMWay; scenes: the
        ways of the first check the place leads to (_URMNMScene), () when
        it leads to none that can be read. [] for any other step. Asked
        while a screen is drawn or a test asks, in the graph's twin.
        """

        g0 = _urmsg_own()
        try:
            out = python_list()
            if step.kind != "choice":
                return out
            choice = _urmsg_choice_in(step.node)
            if choice is None or len(choice.ways) != len(step.ways):
                return out
            for place, way in zip(step.ways, choice.ways):
                sets = python_set()
                for name, _value in way.sets or ():
                    sets.add(u"%s" % (name,))
                out.append((place, _urmnm_scenes(place.start, frozenset(sets))))
            return out
        finally:
            _urmsg_own_end(g0)

    def _urmnm_scenes(start, sets):
        """The scenes the first check after start leads to, as things stand.
        sets: the names the place itself writes (its button's action)."""

        if start is None:
            return ()
        at, _cut = _urmsg_next_split_in(start, _urmnm_no_truth, _URMNM_SEARCH,
                                        _urmsg_flow_ways_in, _urmnm_is_split)
        if at is None or _urmsg_kind(at) != _URMSG_K_IF:
            return ()
        # The chain is told where the story comes from, so a test of what the
        # lines from the place to the check write is not asked now.
        chain = _urmsg_chain(at, _URMNM_SEARCH, _urmnm_waits, _urmsg_step_urm,
                             _URMNM_IFS, start)
        # A hub's checks lead back to the hub and on to the same checks: the
        # chain is read up to the first if-statement it meets again (what
        # comes before it does not hang on what comes after).
        steps = python_list()
        ways = python_list()
        seen = python_list()
        group = None
        for one, way, (node, _arm) in zip(chain.steps, chain.ways, chain.meta):
            if node is not None and way[0] != group:
                if any(node is other for other in seen):
                    break
                seen.append(node)
                group = way[0]
            steps.append(one)
            ways.append(way)
        if not steps:
            return ()
        states = _urmsg_gate_read(steps, _urm_truth, ways)
        out = python_list()
        for at, ((kind, cond, _block), (state, _number, told)) in enumerate(zip(steps, states)):
            if kind != "gate":
                continue
            if told and sets & frozenset(_urmsg_test_keys(cond)):
                told = False
            one = _URMNMWay(None, (_URMNMGate(cond, True, told),))
            _urmnm_gate_now(one.gates[0])
            one.lit = state == "runs" and told
            one.faded = state == "dead" and told
            scene = _URMNMScene(one)
            if told and state == "runs":
                scene.state = "open"
            elif told and state == "dead" and _urm_truth(cond) is False and _urmnm_runs_if(
                    steps, ways, at):
                got = _urm_one_step(((cond, True),))
                if got is not None and got[0] != "open":
                    scene.state = got[0]
                    if got[0] == "step":
                        scene.key = got[1]
                        scene.need = _urmnm_need(got[2])
            out.append(scene)
        return tuple(out)

    def _urmnm_runs_if(steps, ways, at):
        """True when the game would take way `at` of the chain if its own
        test held, everything else as things stand: the one reader that
        knows reach and closing (_urmsg_gate_read) is asked again with that
        test held. Only then is the way short of its own test - not when an
        earlier way is taken, the story jumps away first, or a test before
        it cannot be told ("Only the gate reader knows whether a check is
        reached", FINDINGS)."""

        def truth(cond):
            return True if cond is steps[at][1] else _urm_truth(cond)

        states = _urmsg_gate_read(steps, truth, ways)
        return at < len(states) and states[at][0] == "runs"

    def _urmnm_waits(node):
        """The chain's stop for a place's checks: a line that waits, or a
        statement where the player picks (back at the hub)."""

        return _urmsg_blocks_urm(node) or _urmsg_choice_in(node) is not None

    def _urmnm_need(unmet):
        """What a way still needs, in words: "you have 1, needs 3", or the
        test it lacks said plainly (a test that must not hold: its
        opposite); None when it cannot be said."""

        test, wanted = unmet
        text = (u"%s" % (test,)).strip()
        if wanted:
            return urm_goal_words(text) or _urmw_say(text, flags=True)
        flipped = _urmw_not(text)
        return _urmw_simple(flipped) if flipped is not None else None
