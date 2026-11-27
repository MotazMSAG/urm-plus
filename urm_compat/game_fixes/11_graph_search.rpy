    # ------------------------------------------------------------------
    # Searches
    # ------------------------------------------------------------------

    # The searches of a split's meeting point can each run for a long time on
    # a big game (seconds for one choice on Being a DIK): each is also a
    # generator of steps (`*_steps`) that pauses every _URMSG_STEP_NODES
    # statements and ends by yielding _URMSGDone(answer), so the worker
    # can run it between frames (the choice ahead, 33_map_screen). The old
    # names run the steps to the end: the same answer, at once.

    _URMSG_STEP_NODES = 256

    class _URMSGDone(python_object):
        """What a generator of steps yields last: its answer."""

        def __init__(self, result=None):
            self.result = result

    def _urmsg_drain(steps):
        """The answer a generator of steps ends with."""

        for said in steps:
            if isinstance(said, _URMSGDone):
                return said.result
        return None

    def _urmsg_reach(start, origin, cap, pairs, flow=None):
        """
        Breadth-first from start. pairs True: {id: (distance, statement)},
        not searching through origin. pairs False: {id: distance}.
        Returns (table, cut) - cut when the cap stopped it.
        flow: another successor rule (default _urmsg_flow), for a search
        that must not enter called labels.
        """

        return _urmsg_drain(_urmsg_reach_steps(start, origin, cap, pairs, flow))

    def _urmsg_reach_steps(start, origin, cap, pairs, flow=None):
        if flow is None:
            flow = _urmsg_flow
        seen = python_dict()

        if start is None:
            yield _URMSGDone((seen, False))
            return

        seen[id(start)] = (0, start) if pairs else 0
        queue = python_list((start,))
        head = 0

        while head < len(queue) and len(seen) < cap:
            if not head % _URMSG_STEP_NODES:
                yield None
            node = queue[head]
            head += 1
            dist = seen[id(node)][0] if pairs else seen[id(node)]
            if origin is not None and node is origin:
                continue
            for nxt in flow(node):
                if id(nxt) not in seen:
                    seen[id(nxt)] = (dist + 1, nxt) if pairs else dist + 1
                    queue.append(nxt)

        yield _URMSGDone((seen, head < len(queue)))

    def _urmsg_region(start, x, origin, cap, flow=None):
        """The ids start can reach without passing x; None when that runs on."""

        return _urmsg_drain(_urmsg_region_steps(start, x, origin, cap, flow))

    def _urmsg_region_steps(start, x, origin, cap, flow=None):
        if flow is None:
            flow = _urmsg_flow
        seen = python_set()
        if start is None or start is x:
            yield _URMSGDone(seen)
            return

        seen.add(id(start))
        queue = python_list((start,))
        n = 0

        while queue:
            n += 1
            if not n % _URMSG_STEP_NODES:
                yield None
            node = queue.pop()
            if origin is not None and node is origin:
                continue
            for nxt in flow(node):
                if nxt is x or id(nxt) in seen:
                    continue
                seen.add(id(nxt))
                if len(seen) >= cap:
                    yield _URMSGDone(None)
                    return
                queue.append(nxt)

        yield _URMSGDone(seen)

    def _urmsg_meets(x, origin, regions, cap, flow=None):
        """True if something after x is also in the regions."""

        return _urmsg_drain(_urmsg_meets_steps(x, origin, regions, cap, flow))

    def _urmsg_meets_steps(x, origin, regions, cap, flow=None):
        if not regions:
            yield _URMSGDone(False)
            return
        if flow is None:
            flow = _urmsg_flow

        seen = python_set((id(x),))
        queue = python_list((x,))
        head = 0

        while head < len(queue) and len(seen) < cap:
            if not head % _URMSG_STEP_NODES:
                yield None
            node = queue[head]
            head += 1
            if origin is not None and node is origin:
                continue
            for nxt in flow(node):
                if id(nxt) in seen:
                    continue
                if id(nxt) in regions:
                    yield _URMSGDone(True)
                    return
                seen.add(id(nxt))
                queue.append(nxt)

        yield _URMSGDone(False)

    def _urmsg_leads_back(x, origin, flow, limit=400):
        """True when the story runs from x straight back into the split it
        came from - no other way to go on the way. Such a statement (the
        hub's own label, in front of its menu) is reached by every option
        that jumps back, but nothing meets there: the ways are back at the
        split, and say so."""

        node = x
        n = 0
        while n < limit:
            n += 1
            nexts = flow(node)
            if len(nexts) != 1:
                return False
            node = nexts[0]
            if node is origin:
                return True
        return False

    def _urmsg_place(node):
        """Where a statement stands in the script: (file, line)."""

        return (getattr(node, "filename", None) or "",
                getattr(node, "linenumber", None) or 0)

    def _urmsg_closing(tables, origin, flow):
        """
        The statements that CLOSE what comes after them, among the ones in
        these reach tables (_urmsg_reach with pairs, one per way): the ids
        of every statement x such that nothing the story can get to from x
        can also be got to from one of the ways' starts without passing x.
        Only such a statement can be where the ways meet again - the test
        _urmsg_meeting makes of one candidate at a time, answered here for
        every statement at once.

        How: the statements of the tables are a graph (an edge where the
        story can step, none out of the split itself, none to a statement
        outside the tables). x closes what comes after it when x DOMINATES
        everything reachable from x - every way there from the starts
        passes x. With the dominator tree (Cooper, Harvey and Kennedy's
        iteration) that is: no step leaves the part of the tree under x,
        other than back to x itself. One pass up the tree finds, for every
        x, the step out of its part that reaches highest.

        What lies beyond the tables is not seen here, so this can say yes
        to a statement the full test then refuses; it is never the other
        way round within the tables. The full test still decides.
        """

        return _urmsg_drain(_urmsg_closing_steps(tables, origin, flow))

    def _urmsg_closing_steps(tables, origin, flow):
        nodes = python_dict()
        for table in tables:
            for key, (_dist, node) in table.items():
                nodes[key] = node
        yield None

        # 0 stands for a start in front of every way.
        first = python_list()
        for table in tables:
            for key, (dist, _node) in table.items():
                if dist == 0 and key not in first:
                    first.append(key)
        succ = python_dict()
        succ[0] = first

        def out(key):
            got = succ.get(key)
            if got is None:
                got = python_list()
                node = nodes[key]
                if not (origin is not None and node is origin):
                    for nxt in flow(node):
                        if id(nxt) in nodes and id(nxt) not in got:
                            got.append(id(nxt))
                succ[key] = got
            return got

        # Depth-first, without recursion: the order the statements are
        # left in, reversed, numbers them so that every statement comes
        # after the one that dominates it.
        seen = python_set((0,))
        post = python_list()
        keys = python_list((0,))
        places = python_list((0,))
        n = 0
        while keys:
            n += 1
            if not n % _URMSG_STEP_NODES:
                yield None
            nexts = out(keys[-1])
            i = places[-1]
            if i < len(nexts):
                places[-1] = i + 1
                nxt = nexts[i]
                if nxt not in seen:
                    seen.add(nxt)
                    keys.append(nxt)
                    places.append(0)
            else:
                post.append(keys.pop())
                places.pop()

        post.reverse()
        count = len(post)
        number = python_dict()
        n = 0
        for key in post:
            number[key] = n
            n += 1

        steps = python_list()        # by number: the numbers it steps to
        preds = python_list()
        for _key in post:
            steps.append(python_list())
            preds.append(python_list())
        for key in post:
            a = number[key]
            for nxt in succ[key]:
                b = number[nxt]
                steps[a].append(b)
                preds[b].append(a)

        idom = python_list((-1,)) * count
        idom[0] = 0
        changed = True
        while changed:
            changed = False
            b = 0
            while b < count - 1:
                b += 1
                if not b % _URMSG_STEP_NODES:
                    yield None
                new = -1
                for p in preds[b]:
                    if idom[p] == -1:
                        continue
                    if new == -1:
                        new = p
                        continue
                    a = p
                    while a != new:
                        while a > new:
                            a = idom[a]
                        while new > a:
                            new = idom[new]
                if idom[b] != new:
                    idom[b] = new
                    changed = True

        # Where each statement stands in the tree: how deep, and the run of
        # numbers its part of the tree takes when the tree is written out
        # parent first (so "a is above b" is one comparison).
        depth = python_list((0,)) * count
        size = python_list((1,)) * count
        b = 1
        while b < count:
            depth[b] = depth[idom[b]] + 1
            b += 1
        b = count - 1
        while b > 0:
            size[idom[b]] += size[b]
            b -= 1
        at = python_list((0,)) * count
        free = python_list((1,)) * count
        b = 1
        while b < count:
            up = idom[b]
            at[b] = free[up]
            free[up] += size[b]
            free[b] = at[b] + 1
            b += 1

        # A step a -> b leaves the part of the tree under every statement
        # above a that is deeper than b's own dominator (b itself aside,
        # when b is above a: a step back to x does not leave x's part).
        high = python_list((count + 1,)) * count
        yield None
        a = 1
        while a < count:
            if not a % _URMSG_STEP_NODES:
                yield None
            best = high[a]
            for b in steps[a]:
                if at[b] <= at[a] < at[b] + size[b]:
                    reach = depth[b] + 1
                else:
                    reach = depth[b]
                if reach < best:
                    best = reach
            high[a] = best
            a += 1
        b = count - 1
        while b > 0:
            up = idom[b]
            if high[b] < high[up]:
                high[up] = high[b]
            b -= 1

        closing = python_set()
        for key in post:
            b = number[key]
            if b and high[b] > depth[b]:
                closing.add(key)
        yield _URMSGDone(closing)

    _URMSG_MEET_SETS = 4       # sets of ways the shape is worked out for

    def _urmsg_meeting(starts, origin, after, cap=4000, flow=None, ways=False):
        """The statement where the arms rejoin, or None. flow: another
        successor rule for every search in it (default _urmsg_flow).
        ways: the searches run in the twin, with _urmsg_flow_ways when no
        flow is given (12, "The player's ways")."""

        if ways and _urmsg_graph().base is None:
            g = _urmsg_own()
            try:
                return _urmsg_meeting(starts, origin, after, cap,
                                      flow or _urmsg_flow_ways_in, True)
            finally:
                _urmsg_own_end(g)
        return _urmsg_drain(_urmsg_meeting_steps(starts, origin, after, cap, flow, ways))

    def _urmsg_meeting_steps(starts, origin, after, cap=4000, flow=None, ways=False):
        """_urmsg_meeting in steps. A read in the twin (ways) never pauses:
        the twin is in place only while it runs (_urmsg_own), and a pause
        would leave it in place for whatever runs next."""

        if ways and _urmsg_graph().base is None:
            yield _URMSGDone(_urmsg_meeting(starts, origin, after, cap, flow, True))
            return
        if ways and flow is None:
            flow = _urmsg_flow_ways_in

        reach = python_list()
        for s in starts:
            for said in _urmsg_reach_steps(s, origin, cap, True, flow):
                if isinstance(said, _URMSGDone):
                    reach.append(said.result[0])
                    break
                yield said
        if len(reach) < 2:
            yield _URMSGDone(after)
            return

        counts = python_dict()
        for r in reach:
            for key, (dist, node) in r.items():
                c = counts.get(key)
                if c is None:
                    counts[key] = python_list((1, dist, node))
                else:
                    c[0] += 1
                    if dist > c[1]:
                        c[1] = dist

        ranked = python_list()
        for key, (count, worst, node) in counts.items():
            if count < 2 or (origin is not None and node is origin):
                continue
            ranked.append(((-count, worst), node))

        if not ranked:
            yield _URMSGDone(None)
            return

        if _URMSG_FIX_TIES:
            ranked.sort(key=lambda r: (r[0], _urmsg_place(r[1])))
        else:
            ranked.sort(key=lambda r: r[0])

        step = flow if flow is not None else _urmsg_flow

        def nearest(entries):
            """The first _URMSG_CANDIDATES of these. Idea 13: candidates
            that only lead straight back into the split are left out (at
            most 64 are looked at that way)."""

            kept = python_list()
            looked = 0
            for entry in entries:
                if _URMSG_FIX_SKIP and origin is not None and looked < 64:
                    looked += 1
                    if _urmsg_leads_back(entry[1], origin, step):
                        continue
                kept.append(entry)
                if len(kept) >= _URMSG_CANDIDATES:
                    break
            return kept

        every = ranked
        ranked = nearest(every)
        if not ranked:
            yield _URMSGDone(None)
            return

        # The candidates looked at closely: the nearest ones - or, with
        # MEET, the nearest of those that can be a meeting point at all.
        # When none of them holds, the answer is as it always was: the
        # nearest statement the most ways share. (The closings, worked out
        # in steps, in the order the candidates come.)
        tried = ranked
        if _URMSG_FIX_MEET:
            # the nearest of the candidates that can close: each closing in steps
            known = python_dict()
            tried = python_list()
            looked = 0
            for entry in every:
                key = id(entry[1])
                ways_in = tuple(i for i, table in enumerate(reach) if key in table)
                if ways_in not in known:
                    if len(known) < _URMSG_MEET_SETS:
                        for said in _urmsg_closing_steps(
                                python_list(reach[i] for i in ways_in), origin, step):
                            if isinstance(said, _URMSGDone):
                                known[ways_in] = said.result
                                break
                            yield said
                    else:
                        known[ways_in] = None
                closing = known[ways_in]
                if not (closing is None or key in closing):
                    continue
                if _URMSG_FIX_SKIP and origin is not None and looked < 64:
                    looked += 1
                    if _urmsg_leads_back(entry[1], origin, step):
                        continue
                tried.append(entry)
                if len(tried) >= _URMSG_CANDIDATES:
                    break

        for _score, x in tried:
            regions = python_set()
            ok = True
            for start, r in zip(starts, reach):
                if id(x) not in r:
                    continue
                region = None
                for said in _urmsg_region_steps(start, x, origin, cap, flow):
                    if isinstance(said, _URMSGDone):
                        region = said.result
                        break
                    yield said
                if region is None:
                    ok = False
                    break
                regions |= region
            if ok:
                meets = False
                for said in _urmsg_meets_steps(x, origin, regions, cap, flow):
                    if isinstance(said, _URMSGDone):
                        meets = said.result
                        break
                    yield said
                if not meets:
                    yield _URMSGDone(x)
                    return

        yield _URMSGDone(ranked[0][1])

    def _urmsg_plan(origin, blocks, cap=4000, sites=(), ways=False):
        """
        (arm start statements, rejoin statement or None), or None.

        ways: for a choice of any shape, its ways in place of blocks
        (_urmsg_plan_ways, 12).

        sites: for a split met by a walk that started where the game is,
        the statements the calls the game is inside go back to
        (_urmsg_sites): arms that leave a called scene by `return` then
        meet in the scene that called it.

        Remembered per split until the script changes: the notification,
        the map and every way that walks through a split ask for the same
        rejoin, and finding it is the dearest search here. The split and
        its block lists are kept with the answer and checked on a hit; an
        answer found while a label could not be looked up is not kept.
        """

        if ways:
            return _urmsg_plan_ways(origin, cap, sites)
        return _urmsg_drain(_urmsg_plan_steps(origin, blocks, cap, sites))

    def _urmsg_plan_steps(origin, blocks, cap=4000, sites=()):
        """_urmsg_plan (blocks, not ways) in steps; ends with its answer."""

        g = _urmsg_graph()
        ids = python_list()
        for block in blocks:
            if block is None:
                yield _URMSGDone(None)
                return
            ids.append(id(block) if block else 0)
        key = ("plan", id(origin) if origin is not None else 0, tuple(ids), cap)
        if sites:
            # The answer is for this split reached through these calls.
            marks = python_list()
            for site in sites:
                marks.append(id(site))
            key = key + (tuple(marks),)

        hit = g.q.get(key)
        if hit is not None and hit[0] is origin:
            kept = hit[1]
            same = True
            i = 0
            for block in blocks:
                if block and kept[i] is not block:
                    same = False
                    break
                i += 1
            if same:
                yield _URMSGDone((python_list(hit[2]), hit[3]))
                return

        skipped = g.skipped

        after = getattr(origin, "next", None) if origin is not None else None
        if after is None:
            for block in blocks:
                if block and not isinstance(block[-1], (
                        renpy.ast.Jump, renpy.ast.Return)):
                    after = getattr(block[-1], "next", None)
                    if after is not None:
                        break

        starts = python_list()
        for block in blocks:
            starts.append(block[0] if block else after)

        if sites or _URMSG_FIX_VISIT:
            meeting = _urmsg_meeting_steps(starts, origin, after, cap, _urmsg_flow_meet(sites))
        else:
            meeting = _urmsg_meeting_steps(starts, origin, after, cap)
        rejoin = None
        for said in meeting:
            if isinstance(said, _URMSGDone):
                rejoin = said.result
                break
            yield said

        if g.skipped == skipped and _urmsg_st.g is g:
            if len(g.q) >= _URMSG_CAP_Q:
                g.q.clear()
            g.q[key] = (origin, tuple(blocks), tuple(starts), rejoin)

        yield _URMSGDone((starts, rejoin))

    def _urmsg_next_split(start, truth, limit=3000, flow=None, ways=False):
        """
        The nearest menu at or ahead of start, and whether the search was
        cut short. An if is only pruned when truth(cond) is True or False.
        flow: another successor rule (default _urmsg_flow). ways: the
        nearest choice of any shape (_urmsg_next_choice, 12).
        """

        if ways:
            return _urmsg_next_choice(start, truth, limit)
        return _urmsg_next_split_in(start, truth, limit, flow or _urmsg_flow, None)

    def _urmsg_next_split_in(start, truth, limit, flow, pick):
        """_urmsg_next_split's search; pick(node) True for a choice (None:
        a menu)."""

        if start is None:
            return None, False

        seen = python_set((id(start),))
        queue = python_list((start,))
        head = 0

        while head < len(queue) and head < limit:
            node = queue[head]
            head += 1
            k = _urmsg_kind(node)

            if (k == _URMSG_K_MENU) if pick is None else pick(node):
                return node, False

            if k == _URMSG_K_IF:
                nexts = python_list()
                taken = False
                nx = getattr(node, "next", None)
                for cond, block in (getattr(node, "entries", None) or ()):
                    target = block[0] if block else nx
                    t = True if _urmsg_is_else(cond) else truth(cond)
                    if t is False:
                        continue
                    nexts.append(target)
                    if t is True:
                        taken = True
                        break
                if not taken:
                    nexts.append(nx)
            else:
                nexts = flow(node)

            for nxt in nexts:
                if nxt is not None and id(nxt) not in seen:
                    seen.add(id(nxt))
                    queue.append(nxt)

        return None, head < len(queue)

    # ------------------------------------------------------------------
    # What a block of statements does, and the run two walkers share (M1)
    # ------------------------------------------------------------------
    #
    # Ports of the card readers (python lines, flatten with its lift), the
    # maze's lexical tests (pure, text-only menu, target tag) and the skip
    # look-ahead's "dialogue in this block"; then _urmsg_run, the one body
    # behind the maze's arm walk and the map's trunk walk. The two differed
    # in exactly four records the arm walk keeps and the trunk walk drops
    # (the keep-sets below), in the trunk starting a new block at each label
    # it passes into, and in what they do at a split - which stays with the
    # caller.

    _URMSG_MAX_GUARD_CHARS = 18
    _URMSG_MAX_DEPTH = 3

    _URMSG_NOISE = (
        "renpy.sound.", "renpy.music.", "renpy.play", "renpy.pause",
        "renpy.show", "renpy.hide", "renpy.scene", "renpy.with_statement",
        "renpy.transition", "renpy.notify", "renpy.restart_interaction",
        "renpy.free_memory", "renpy.block_rollback", "renpy.fix_rollback",
        "renpy.checkpoint", "renpy.save_persistent", "renpy.force_autosave",
        "renpy.take_screenshot", "renpy.start_predict", "renpy.stop_predict",
        "renpy.cache_pin", "renpy.cache_unpin", "renpy.display.",
        "renpy.exports.", "renpy.vibrate", "renpy.set_mouse_pos",
        "renpy.end_replay", "renpy.say", "renpy.log", "renpy.predict",
        "config.", "preferences.", "_preferences.", "store._window",
        "_window", "print(",
    )

    # Marks in a record list: a check, or a menu, that only changes lines;
    # and a custom statement with content inside (_urmsg_closed), which is
    # passed as one statement - what it holds is not read.
    _URMSG_MARK_CHECK = u"\x00check"
    _URMSG_MARK_MENU = u"\x00menu"
    _URMSG_MARK_CODE = u"\x00code"

    # Records only the arm walk keeps. A jump or a call that cannot be
    # followed used to be three more of these; it is now said by every walk
    # (idea 8), so the two walks differ in this one record alone.
    _URMSG_FX_WHILE = 0
    _URMSG_KEEP_ARM = frozenset((0,))
    _URMSG_KEEP_TRUNK = frozenset(())

    _URMSG_ASSIGN = _urmsg_re.compile(
        r"^([A-Za-z_][\w.]*)\s*(?:\*\*|//|[-+*/%|&^])?=(?!=)")

    _urmsg_text = u"".__class__

    class _URMSGNote(_urmsg_text):
        """
        A guard or a mark inside a record. Everything that reads records
        sees plain text (it compares and hashes as its text). A display that
        wants to say WHICH test stands behind it - the map, when the mouse
        is on a diamond - reads .tests: a tuple of (test, wanted), wanted
        True (must hold), False (must not hold) or None (only looked at).
        The guard text alone cannot say it: it is clipped to 18 characters.
        .before holds the tests that come first in the same if and must
        fail for this one to be reached at all (an elif): not said in words,
        but needed to tell whether the guard holds as the game stands.
        """

        def __new__(cls, text, tests=(), before=()):
            self = _urmsg_text.__new__(cls, text)
            self.tests = tests
            self.before = before
            return self

    class _URMSGArm(python_object):
        """What one block list holds, each part worked out when asked."""

        __slots__ = ("block", "recs", "drop", "pure", "says", "tag")

        def __init__(self, block):
            self.block = block
            self.recs = None
            self.drop = 0
            self.pure = None
            self.says = None
            self.tag = None

    class _URMSGWalk(python_object):
        """One walk: stop = id of the rejoin or None; origin = the menu on
        screen or None; steps is shared by every fork; blocks is None for an
        arm walk, or the trunk walk's list of [label, records]."""

        __slots__ = ("stop", "origin", "steps", "limit", "keep", "blocks", "outer",
                     "calls", "met", "ways", "shown", "live")

        def __init__(self, stop, origin, limit, keep, blocks=None, ways=False, shown=None):
            self.stop = stop
            # True: a choice of any shape is a split, and a jump through a
            # name ends the walk (12, "The player's ways"; opt-in).
            self.ways = ways
            # With ways: the game's screens on show where the walk starts
            # (_urmsg_live_shown() for a walk from where the game is), None
            # when that is not known; live: the ones on show where the last
            # run stopped (_urmsg_on_show), None when not known.
            self.shown = shown
            self.live = None
            self.origin = origin
            self.steps = 0
            # Calls entered so far, by every fork of this walk: each call
            # gets the next number as the name of its frame (_urmsg_call).
            self.calls = 0
            # The stack a way had when it reached a rejoin, by the rejoin's
            # id (the first way to get there): what follows the rejoin is
            # walked from THAT stack. Ways that leave a called scene meet in
            # the scene that called it, one call further out than the split.
            self.met = python_dict()
            self.limit = limit
            self.keep = keep
            self.blocks = blocks
            # ids of the rejoins of the splits AROUND the one whose arms are
            # being walked: reaching one of those ends the walk as "later".
            self.outer = None

    def _urmsg_clip(text, limit):
        if len(text) <= limit:
            return text
        return text[:limit - 1] + u"\u2026"

    def _urmsg_noise(line):
        """A python line that only touches presentation, not the story."""

        text = line.strip()
        if text.startswith(("renpy.jump", "renpy.call")):
            return False
        return text.startswith(_URMSG_NOISE)

    # ---- A line that only calls one of the game's own functions
    # (_URMSG_FIX_FUNCS). A game can tell its story through such calls - a
    # phone text each. The function is read from the script, never run,
    # and followed into the game's functions it calls in turn: the line is
    # not said when nothing it changes is read by a test of the story (an
    # if, a while, a menu option's condition, an if in the story's python).
    # Anything else stays as it was: a call of something the script does
    # not define, a change that cannot be told, a change a test reads.

    import ast as _urmsg_pyast
    import inspect as _urmsg_inspect
    import types as _urmsg_types
    import warnings as _urmsg_warnings
    try:
        import builtins as _urmsg_builtins_mod
    except ImportError:
        import __builtin__ as _urmsg_builtins_mod

    # Methods of lists, dicts and sets that change what they are called on.
    _URMSG_CHANGERS = frozenset((
        "append", "extend", "insert", "remove", "pop", "popitem", "clear",
        "add", "discard", "update", "setdefault", "sort", "reverse"))
    # Builtin string/dict/set read-only methods: never change their receiver.
    _URMSG_PURE_METHODS = frozenset((
        "strip", "lstrip", "rstrip", "lower", "upper", "title", "capitalize",
        "casefold", "swapcase", "split", "rsplit", "splitlines", "join",
        "replace", "startswith", "endswith", "find", "rfind", "index",
        "rindex", "count", "format", "isdigit", "isalpha", "isalnum",
        "isspace", "islower", "isupper", "isnumeric", "isdecimal", "encode",
        "decode", "get", "keys", "values", "items", "copy", "union",
        "intersection", "difference", "symmetric_difference", "issubset",
        "issuperset", "isdisjoint"))
    # Builtin container/text types whose store-default values match these pure
    # methods (subclasses include Ren'Py RevertableDict/List/Set).
    _URMSG_BUILTIN_TYPES = (
        _urmsg_text, bytes, type(""), python_dict, python_set, frozenset,
        python_list, tuple)
    # Calls that can change anything at all.
    _URMSG_SETTERS = frozenset(("setattr", "delattr", "exec", "execfile",
                                "eval", "globals", "vars", "locals"))
    # Not the story: the engine, and galleries and achievements (the
    # displays leave out `persistent.` lines as well).
    _URMSG_NOT_STORY = frozenset(("renpy", "persistent"))
    # The engine's calls that send the story elsewhere, or wait for the
    # player on a screen that may set values: what follows cannot be told.
    _URMSG_MOVES = frozenset((
        "jump", "call", "call_in_new_context", "invoke_in_new_context",
        "jump_out_of_context", "call_screen", "return_statement"))
    # Methods with which a class answers any name: reading or setting
    # anything of it may run the game's code.
    _URMSG_ANY_NAME = frozenset((
        "__getattr__", "__getattribute__", "__getitem__", "__setattr__",
        "__setitem__", "__delattr__", "__delitem__"))
    # How deep the game's functions are followed.
    _URMSG_FN_DEPTH = 3

    # What an expression stands for (_urmsg_path_of): a path - a tuple of
    # names, the store's name first - or one of these two.
    _URMSG_NEW = u"\x00new"     # a value made right there
    _URMSG_ITEM = u"\x00item"   # in a path: an item of the container before
    _URMSG_ANY = u"\x00any"     # cannot be told
    _URMSG_MADE = frozenset((
        "List", "Tuple", "Dict", "Set", "ListComp", "SetComp", "DictComp",
        "GeneratorExp", "Str", "Num", "Bytes", "NameConstant", "Constant",
        "JoinedStr", "BinOp", "UnaryOp", "Compare", "BoolOp"))
    _URMSG_SCOPES = ("FunctionDef", "AsyncFunctionDef", "ClassDef", "Lambda")

    def _urmsg_tree(source):
        """A python block's source, parsed once per script."""

        g = _urmsg_graph()
        tree = g.trees.get(source)
        if tree is None:
            try:
                tree = _urmsg_parse(source)
            except Exception:
                tree = False
            g.trees[source] = tree
        return tree or None

    def _urmsg_parse(source, mode="exec"):
        """The game's own python, parsed - quietly: a newer Python warns
        about old escapes in it, which are the game's business."""

        with _urmsg_warnings.catch_warnings():
            _urmsg_warnings.simplefilter("ignore")
            return _urmsg_pyast.parse(source, mode=mode)

    def _urmsg_kind_of(node):
        return type(node).__name__

    def _urmsg_inside(body):
        """Every parsed node of a body, without the functions, classes and
        lambdas defined in it (they run only when called)."""

        out = python_list()
        todo = python_list(body)
        while todo:
            node = todo.pop()
            out.append(node)
            for child in _urmsg_pyast.iter_child_nodes(node):
                if _urmsg_kind_of(child) not in _URMSG_SCOPES:
                    todo.append(child)
        return out

    def _urmsg_path_of(node, env):
        """What an expression stands for: a path (a part of a container is
        the container), _URMSG_NEW, or _URMSG_ANY. env holds a function's
        own names."""

        tail = python_list()
        while True:
            kind = _urmsg_kind_of(node)
            if kind == "Attribute":
                tail.append(node.attr)
                node = node.value
            elif kind == "Subscript":
                # A part of a container is the container; a field of a
                # part keeps its name, behind a mark no object has.
                if tail:
                    tail.append(_URMSG_ITEM)
                node = node.value
            else:
                break
        if kind == "Name":
            if node.id in env:
                base = env[node.id]
                if not isinstance(base, tuple):
                    return base
            elif node.id in ("True", "False", "None"):
                return _URMSG_NEW
            else:
                base = (node.id,)
            tail.reverse()
            path = base + tuple(tail)
            # The store itself, however it is reached: store.x, renpy.store.x.
            if path[:2] == ("renpy", "store") and len(path) > 2:
                path = path[2:]
            elif path[0] == "store" and len(path) > 1:
                path = path[1:]
            return path
        if kind in _URMSG_MADE:
            return _URMSG_NEW
        if kind == "Call" and _urmsg_called(node.func, env)[0] == "other":
            return _URMSG_NEW
        return _URMSG_ANY

    def _urmsg_static_get(obj, name):
        """obj.name, read without running any of the game's code (no
        __getattr__, no property): the object's own dict, then its
        classes'. None when it is not there."""

        try:
            own = python_object.__getattribute__(obj, "__dict__")
        except TypeError:
            # Python 2's old-style instances and classes.
            own = getattr(obj, "__dict__", None)
        except Exception:
            own = None
        try:
            if own is not None and name in own:
                return own[name]
        except Exception:
            return None

        if isinstance(obj, (type, getattr(_urmsg_types, "ClassType", type))):
            klass = obj
        else:
            try:
                klass = python_object.__getattribute__(obj, "__class__")
            except TypeError:
                klass = obj.__class__
            except Exception:
                return None
        try:
            for one in _urmsg_inspect.getmro(klass):
                found = one.__dict__
                if name in found:
                    return found[name]
        except Exception:
            pass
        return None

    def _urmsg_obj_at(path):
        """The object a path names in the game's store, or None."""

        try:
            obj = vars(renpy.store).get(path[0])
        except Exception:
            return None
        for part in path[1:]:
            if obj is None:
                return None
            obj = _urmsg_static_get(obj, part)
        return obj

    def _urmsg_file(name):
        return (u"%s" % (name,)).replace(u"\\", u"/")

    def _urmsg_defs():
        """file -> [(the line its source starts at, source)] for every
        python block of the script that defines something; once per
        script."""

        g = _urmsg_graph()
        if g.defs is None:
            defs = python_dict()
            for node in (getattr(renpy.game.script, "all_stmts", None) or ()):
                code = getattr(node, "code", None)
                source = getattr(code, "source", None)
                if not source or u"def " not in source:
                    continue
                where = getattr(code, "location", None) or ()
                name = getattr(code, "filename", None) or (where[0] if where else None)
                line = getattr(code, "linenumber", None) or (where[1] if len(where) > 1 else None)
                if name is None or line is None or _urmsg_engine_file(name):
                    continue
                defs.setdefault(_urmsg_file(name), python_list()).append((line, source))
            g.defs = defs
        return g.defs

    def _urmsg_classes():
        """What the script's classes define: (every method's defs by name,
        the getters of every property by name - None for one that cannot
        be read -, the name of every property that can be set, the names
        of the methods with which a class answers any name)."""

        g = _urmsg_graph()
        if g.methods is None:
            methods = python_dict()
            getters = python_dict()
            setters = python_set()
            magic = python_set()
            for blocks in _urmsg_defs().values():
                for _line, source in blocks:
                    if u"class " not in source:
                        continue
                    tree = _urmsg_tree(source)
                    for node in (_urmsg_pyast.walk(tree) if tree is not None else ()):
                        if _urmsg_kind_of(node) != "ClassDef":
                            continue
                        for item in node.body:
                            kind = _urmsg_kind_of(item)
                            if kind in ("FunctionDef", "AsyncFunctionDef"):
                                methods.setdefault(item.name, python_list()).append(item)
                                if item.name in _URMSG_ANY_NAME:
                                    magic.add(item.name)
                                for deco in item.decorator_list:
                                    if _urmsg_kind_of(deco) == "Name" and deco.id == "property":
                                        getters.setdefault(item.name, python_list()).append(item)
                                    elif _urmsg_kind_of(deco) == "Attribute":
                                        if deco.attr == "getter":
                                            getters.setdefault(item.name, python_list()).append(item)
                                        elif deco.attr in ("setter", "deleter"):
                                            setters.add(item.name)
                            elif kind == "Assign" and _urmsg_kind_of(item.value) == "Call":
                                # name = property(...): what it reads cannot be told.
                                if _urmsg_kind_of(item.value.func) == "Name" and item.value.func.id == "property":
                                    for target in item.targets:
                                        if _urmsg_kind_of(target) == "Name":
                                            getters.setdefault(target.id, python_list()).append(None)
                                            setters.add(target.id)
            g.methods = (methods, getters, frozenset(setters), frozenset(magic))
        return g.methods

    def _urmsg_def_of(fn):
        """A game function's def, parsed from the script's own source: the
        one of its name nearest the line the engine compiled it at. None
        when it is not found."""

        code = fn.__code__
        g = _urmsg_graph()
        hit = g.fdefs.get(id(code))
        if hit is not None and hit[0] is code:
            return hit[1]
        found = _urmsg_def_find(code)
        g.fdefs[id(code)] = (code, found)
        return found

    def _urmsg_def_find(code):
        defs = _urmsg_defs()
        name = _urmsg_file(code.co_filename)
        blocks = defs.get(name)
        if blocks is None:
            base = name.rsplit(u"/", 1)[-1]
            blocks = python_list()
            for key, found in defs.items():
                if key.rsplit(u"/", 1)[-1] == base:
                    blocks.extend(found)

        best = None
        for start, source in blocks:
            if (u"def " + code.co_name) not in source:
                continue
            tree = _urmsg_tree(source)
            if tree is None:
                continue
            for node in _urmsg_pyast.walk(tree):
                if _urmsg_kind_of(node) not in ("FunctionDef", "AsyncFunctionDef"):
                    continue
                if node.name != code.co_name:
                    continue
                # A decorated def: some engines number it from the decorator.
                gap = abs(start + node.lineno - 1 - code.co_firstlineno)
                for deco in node.decorator_list:
                    gap = min(gap, abs(start + deco.lineno - 1 - code.co_firstlineno))
                if best is None or gap < best[0]:
                    best = (gap, node)
        if best is None or best[0] > 2:
            return None
        return best[1]

    def _urmsg_engine_file(name):
        """True for a script file that is not the game's: the engine's own
        the URM+ archive, and scripts from old URM installs."""

        name = _urmsg_file(name).lower()
        return (name.startswith((u"renpy/", u"urmplus/")) or u"/renpy/common/" in name
                or u"/urmplus/" in name or u"0x52" in name or u"_urmfix" in name
                or u"urm_compat" in name)

    def _urmsg_game_fn(obj):
        """The function, when obj is one the game's script defines (not
        the engine's, not URM's, not a library's); else None."""

        if isinstance(obj, (staticmethod, classmethod, _urmsg_types.MethodType)):
            obj = getattr(obj, "__func__", None)
        if not isinstance(obj, _urmsg_types.FunctionType):
            return None
        if getattr(obj, "__module__", None) != "store":
            return None
        if _urmsg_engine_file(obj.__code__.co_filename):
            return None
        return obj

    def _urmsg_called(func, env):
        """What a call calls: ("fn", function, receiver path or None) for a
        function of the game's script; ("write", path) for a method that may
        change what it is called on; ("other",) for what changes nothing of
        the story (the engine, a builtin, a class, a value made right
        there); ("methods", defs, name, receiver written or None) for a
        method of the script's classes on an object that cannot be told -
        every method of that name; ("missing",) for a name the store does not have; ("any",)
        when it cannot be told."""

        kind = _urmsg_kind_of(func)
        if kind == "Name":
            if func.id in env:
                return ("other",) if env[func.id] == _URMSG_NEW else ("any",)
            try:
                store = vars(renpy.store)
            except Exception:
                return ("any",)
            if func.id not in store:
                # A builtin; or a name the store does not have, which a
                # running story could not call either.
                return ("other",) if hasattr(_urmsg_builtins_mod, func.id) else ("missing",)
            obj = store.get(func.id)
            fn = _urmsg_game_fn(obj)
            if fn is not None:
                return ("fn", fn, None)
            if (isinstance(obj, _urmsg_types.FunctionType)
                    and getattr(obj, "__module__", None) == "store"
                    and not _urmsg_engine_file(obj.__code__.co_filename)):
                return ("any",)
            return ("other",)

        if kind != "Attribute":
            return ("any",)
        receiver = _urmsg_path_of(func.value, env)
        if receiver == _URMSG_NEW:
            return ("other",)
        if not isinstance(receiver, tuple):
            # Called on what cannot be told: a method no class of the
            # script defines (a text's split, a match's group) is not the
            # game's code.
            if func.attr in _URMSG_CHANGERS:
                # It may be a list's own method changing a list no name says.
                return ("any",)
            if func.attr in _urmsg_classes()[0]:
                return ("methods", tuple(_urmsg_classes()[0][func.attr]), func.attr, None)
            return ("other",)
        if receiver[0] in _URMSG_NOT_STORY:
            if receiver[0] == "persistent" and func.attr in _URMSG_CHANGERS:
                return ("write", receiver)
            return ("other",)
        obj = _urmsg_obj_at(receiver)
        method = _urmsg_static_get(obj, func.attr) if obj is not None else None
        fn = _urmsg_game_fn(method)
        if fn is not None:
            # Called on an instance, the method gets it as its first name.
            bound = not isinstance(method, staticmethod) and not isinstance(
                obj, (type, getattr(_urmsg_types, "ClassType", type), _urmsg_types.ModuleType))
            return ("fn", fn, receiver if bound else None)
        if isinstance(obj, _urmsg_types.ModuleType) and method is not None:
            return ("other",)
        if method is None and func.attr in _urmsg_classes()[0]:
            # A method of the script's classes, on what does not have it as
            # the map is built (an item, a name set later): every method of
            # that name, on an object that cannot be told - and, for a name
            # lists, sets and dicts have too, a change to the receiver.
            return ("methods", tuple(_urmsg_classes()[0][func.attr]), func.attr,
                    receiver if func.attr in _URMSG_CHANGERS else None)
        # A list's method that changes it, or an unknown/builtin method not
        # defined by any game class: read-only builtins leave receiver alone.
        if ((method is None or isinstance(obj, _URMSG_BUILTIN_TYPES))
                and func.attr in _URMSG_PURE_METHODS):
            return ("other",)
        return ("write", receiver)

    def _urmsg_bind(fdef, pos, named):
        """A function's own names, bound to what the call hands it."""

        a = fdef.args
        env = python_dict()
        params = python_list(getattr(a, "posonlyargs", None) or ()) + python_list(a.args)
        for i, param in enumerate(params):
            name = getattr(param, "arg", None) or getattr(param, "id", None)
            if name is None:
                continue
            if i < len(pos):
                env[name] = pos[i]
            else:
                env[name] = named.get(name, _URMSG_NEW)
        for param in (getattr(a, "kwonlyargs", None) or ()):
            env[param.arg] = named.get(param.arg, _URMSG_NEW)
        for extra in (a.vararg, a.kwarg):
            if extra is not None:
                env[getattr(extra, "arg", extra)] = _URMSG_ANY
        return env

    def _urmsg_args(call, env, receiver=None):
        """(positional, named) of a call, as paths."""

        pos = python_list()
        if receiver is not None:
            pos.append(receiver)
        for arg in call.args:
            if _urmsg_kind_of(arg) == "Starred":
                pos.append(_URMSG_ANY)
            else:
                pos.append(_urmsg_path_of(arg, env))
        named = python_dict()
        for kw in (call.keywords or ()):
            if kw.arg is not None:
                named[kw.arg] = _urmsg_path_of(kw.value, env)
        return pos, named

    def _urmsg_local_env(nodes, env, declared):
        """env with the function's own names added: a name bound once, or
        always to the same thing, stands for that; any other, _URMSG_ANY."""

        binds = python_dict()
        for node in nodes:
            kind = _urmsg_kind_of(node)
            if kind == "Assign":
                for target in node.targets:
                    if _urmsg_kind_of(target) == "Name":
                        binds.setdefault(target.id, python_list()).append(node.value)
                    else:
                        for sub in _urmsg_pyast.walk(target):
                            if _urmsg_kind_of(sub) == "Name" and isinstance(sub.ctx, _urmsg_pyast.Store):
                                binds.setdefault(sub.id, python_list()).append(None)
            elif kind == "AnnAssign" and node.value is not None and _urmsg_kind_of(node.target) == "Name":
                binds.setdefault(node.target.id, python_list()).append(node.value)
            elif kind in ("For", "AsyncFor", "comprehension", "withitem", "With", "NamedExpr"):
                target = getattr(node, "target", None) or getattr(node, "optional_vars", None)
                if target is None and kind == "With":
                    target = getattr(node, "optional_vars", None)
                for sub in (_urmsg_pyast.walk(target) if target is not None else ()):
                    if _urmsg_kind_of(sub) == "Name":
                        binds.setdefault(sub.id, python_list()).append(None)
            elif kind in ("Import", "ImportFrom"):
                for alias in node.names:
                    name = (alias.asname or alias.name).split(".")[0]
                    if name in ("store", "renpy") or alias.name in ("store", "renpy.store"):
                        # The store and the engine: `store.x`, `renpy.store.x`
                        # stay paths into them.
                        continue
                    binds.setdefault(name, python_list()).append(_URMSG_NEW)
            elif kind == "ExceptHandler" and isinstance(getattr(node, "name", None), _urmsg_text):
                binds.setdefault(node.name, python_list()).append(_URMSG_NEW)

        out = python_dict(env)
        for _round in (0, 1):
            for name, values in binds.items():
                if name in declared:
                    continue
                said = python_list()
                for value in values:
                    if value is None:
                        said.append(_URMSG_ANY)
                    elif value is _URMSG_NEW:
                        said.append(_URMSG_NEW)
                    else:
                        said.append(_urmsg_path_of(value, out))
                if name in env:
                    said.append(env[name])
                first = said[0]
                out[name] = first if all(one == first for one in said) else _URMSG_ANY
        return out

    def _urmsg_fn_effects(fn, pos, named, depth, seen, writes):
        """Add to writes every path a call of a game function changes,
        following the game's functions it calls. False when that cannot be
        told."""

        fdef = _urmsg_def_of(fn)
        if fdef is None:
            return False
        return _urmsg_def_effects(fdef, pos, named, depth, seen, writes)

    def _urmsg_def_effects(fdef, pos, named, depth, seen, writes):
        if depth > _URMSG_FN_DEPTH:
            return False
        key = (id(fdef), tuple(pos), frozenset(named.items()))
        if key in seen:
            return True
        seen.add(key)
        g = _urmsg_graph()
        hit = g.effects.get((key, depth))
        if hit is not None:
            writes.extend(hit[1])
            return hit[0]
        mine = python_list()
        ok = _urmsg_fn_walk(fdef, pos, named, depth, seen, mine)
        g.effects[(key, depth)] = (ok, tuple(mine))
        writes.extend(mine)
        return ok

    def _urmsg_fn_walk(fdef, pos, named, depth, seen, writes):
        nodes = _urmsg_inside(fdef.body)
        declared = python_set()
        for node in nodes:
            kind = _urmsg_kind_of(node)
            if kind in ("Global", "Nonlocal"):
                declared.update(node.names)
            elif kind == "Exec":
                return False
        env = _urmsg_local_env(nodes, _urmsg_bind(fdef, pos, named), declared)
        for name in declared:
            env.pop(name, None)
        return _urmsg_nodes_effects(nodes, env, declared, depth, seen, writes)

    def _urmsg_nodes_effects(nodes, env, declared, depth, seen, writes):
        """Add to writes every path a body's nodes (_urmsg_inside) change,
        its own names in env, the store's names in declared - persistent's
        and the engine's too (_urmsg_line_both leaves them out of what the
        story changes). False when that cannot be told."""

        def write(target, inplace=False):
            kind = _urmsg_kind_of(target)
            if kind in ("Tuple", "List"):
                return all(write(one) for one in target.elts)
            if kind == "Starred":
                return write(target.value)
            if kind == "Name":
                if target.id in declared:
                    writes.append((target.id,))
                    return True
                # A name of its own; `x += ...` may change what it stands for.
                path = env.get(target.id, _URMSG_NEW) if inplace else _URMSG_NEW
            elif kind in ("Attribute", "Subscript"):
                if kind == "Attribute" and target.attr in _urmsg_classes()[2]:
                    # A property that can be set: what it changes is its own code.
                    return False
                path = _urmsg_path_of(target, env)
                if path == _URMSG_ANY and kind == "Attribute":
                    # Whatever it is, what changes is this attribute.
                    writes.append((_URMSG_ANY, target.attr))
                    return True
            else:
                return False
            if path == _URMSG_ANY:
                return False
            if isinstance(path, tuple):
                writes.append(path)
            return True

        for node in nodes:
            kind = _urmsg_kind_of(node)
            if kind in ("Assign", "Delete"):
                if not all(write(target) for target in node.targets):
                    return False
            elif kind == "AugAssign":
                if not write(node.target, True):
                    return False
            elif kind == "AnnAssign" and node.value is not None:
                if not write(node.target):
                    return False
            elif kind in ("For", "AsyncFor", "withitem", "With"):
                # A loop's name, a with's name: set too.
                target = getattr(node, "target", None) or getattr(node, "optional_vars", None)
                if target is not None and not write(target):
                    return False
            elif kind == "Call":
                func = node.func
                if _urmsg_kind_of(func) == "Name" and func.id in _URMSG_SETTERS:
                    return False
                if (_urmsg_kind_of(func) == "Attribute" and func.attr in _URMSG_MOVES
                        and _urmsg_path_of(func.value, env) == ("renpy",)):
                    return False
                called = _urmsg_called(func, env)
                if called[0] in ("any", "missing"):
                    return False
                if called[0] == "write":
                    writes.append(called[1])
                elif called[0] == "fn":
                    inner_pos, inner_named = _urmsg_args(node, env, called[2])
                    if not _urmsg_fn_effects(called[1], inner_pos, inner_named,
                                             depth + 1, seen, writes):
                        return False
                elif called[0] == "methods":
                    if called[3] is not None:
                        writes.append(called[3])
                    inner_pos, inner_named = _urmsg_args(node, env, _URMSG_ANY)
                    for fdef in called[1]:
                        if not _urmsg_def_effects(fdef, inner_pos, inner_named,
                                                  depth + 1, seen, writes):
                            return False
        return True

    # Changes and tests are matched by name, not by object - an object is
    # reached by too many ways to be told: ("g", name) for a name of the
    # store, ("a", name) for an attribute, of whatever object.

    def _urmsg_keys(path):
        """The names a written path touches: a name of the store, or the
        attribute written."""

        if len(path) == 1:
            return (("g", path[0]),)
        return (("a", path[-1]),)

    class _URMSGReads(python_object):
        """What the story's tests read, being gathered: out (keys), seen
        (what was followed already), worked ([(keys, expression, env,
        names)] - values the story works out, read when a test reads them),
        blind (True once something a test may read cannot be told - then
        any change may be read)."""

        __slots__ = ("out", "seen", "worked", "blind", "why")

        def __init__(self):
            self.out = python_set()
            self.seen = python_set()
            self.worked = python_list()
            self.blind = False
            # The first thing that could not be told, for a probe to say.
            self.why = None

    def _urmsg_blind(r, why):
        r.blind = True
        if r.why is None:
            r.why = why

    def _urmsg_values(nodes, declared, env, call=None, fdef=None, caller=None, bound=False):
        """A function's own names -> [(an expression that gives it a value,
        the env and names to read that expression in)]. A name it was
        handed whose value cannot be told is read at the call: what the
        caller's expression reads (caller = (env, names))."""

        values = python_dict()

        def add(name, value, where_env=None, where_names=None):
            if name in declared or value is None:
                return
            values.setdefault(name, python_list()).append(
                (value, env if where_env is None else where_env,
                 values if where_names is None else where_names))

        for node in nodes:
            kind = _urmsg_kind_of(node)
            if kind in ("Assign", "AnnAssign", "AugAssign", "NamedExpr"):
                targets = node.targets if kind == "Assign" else (node.target,)
                for target in targets:
                    for sub in _urmsg_pyast.walk(target):
                        if _urmsg_kind_of(sub) == "Name":
                            add(sub.id, getattr(node, "value", None))
            elif kind in ("For", "AsyncFor", "comprehension"):
                for sub in _urmsg_pyast.walk(node.target):
                    if _urmsg_kind_of(sub) == "Name":
                        add(sub.id, node.iter)
            elif kind == "withitem" and node.optional_vars is not None:
                for sub in _urmsg_pyast.walk(node.optional_vars):
                    if _urmsg_kind_of(sub) == "Name":
                        add(sub.id, node.context_expr)
            elif kind == "With" and getattr(node, "optional_vars", None) is not None:
                for sub in _urmsg_pyast.walk(node.optional_vars):
                    if _urmsg_kind_of(sub) == "Name":
                        add(sub.id, node.context_expr)

        if call is not None and fdef is not None and caller is not None:
            a = fdef.args
            params = python_list(getattr(a, "posonlyargs", None) or ()) + python_list(a.args)
            handed = python_list(call.args)
            if bound:
                params = params[1:]
            for param, arg in zip(params, handed):
                name = getattr(param, "arg", None) or getattr(param, "id", None)
                if name is not None and not isinstance(env.get(name), tuple):
                    add(name, arg, caller[0], caller[1])
            for kw in (call.keywords or ()):
                if kw.arg is not None and not isinstance(env.get(kw.arg), tuple):
                    add(kw.arg, kw.value, caller[0], caller[1])
        return values

    def _urmsg_read_called(func, env):
        """_urmsg_called, for what a call reads: a method named as a list's
        own (update, add) on an object that cannot be told is the game's
        methods of that name, or a list's own, which reads only what it is
        handed - not "cannot tell", as it is for what a call changes."""

        called = _urmsg_called(func, env)
        if (called[0] == "any" and _urmsg_kind_of(func) == "Attribute"
                and func.attr in _URMSG_CHANGERS
                and not isinstance(_urmsg_path_of(func.value, env), tuple)):
            defs = _urmsg_classes()[0].get(func.attr)
            return ("methods", tuple(defs), func.attr, None) if defs else ("other",)
        return called

    def _urmsg_in_store(node, parts, env, names):
        """When an expression - node, then parts - reaches into the store
        itself (store.x, renpy.store.x, a name bound to the store): the path
        inside it, () for the store itself. None for anything else."""

        tail = python_list()
        while _urmsg_kind_of(node) == "Attribute":
            tail.append(node.attr)
            node = node.value
        if _urmsg_kind_of(node) != "Name":
            return None
        if node.id in env:
            base = env[node.id]
            if not isinstance(base, tuple):
                return None
        elif node.id in names:
            return None
        else:
            base = (node.id,)
        tail.reverse()
        path = base + tuple(tail) + tuple(parts)
        if path[:2] == ("renpy", "store"):
            return path[2:]
        if path[:1] == ("store",):
            return path[1:]
        return None

    # A game function, method or class used as a value - handed to a
    # screen's button (action Function(check), action MyAction()), kept to
    # be called later - runs when the player acts: what it reads is read,
    # as a call of it would be. A class: every method of the game's in it
    # (the engine asks an action's own methods too); an object: when its
    # class is called (__call__).

    class _URMSGNoArgs(python_object):
        """A call that hands nothing: how a function handed on is read."""

        __slots__ = ()
        args = ()
        keywords = ()

    _urmsg_no_args = _URMSGNoArgs()

    def _urmsg_handed_reads(node, env, names, depth, r, inside=None):
        """What a name or an attribute used as a value reads when it runs
        (inside: its path in the store, for store.x)."""

        obj = None
        called = None
        if inside:
            obj = _urmsg_obj_at(inside)
            fn = _urmsg_game_fn(obj)
            if fn is not None:
                called = ("fn", fn, None)
        else:
            called = _urmsg_read_called(node, env)
            if called[0] not in ("fn", "methods"):
                called = None
                if _urmsg_kind_of(node) == "Name":
                    if node.id in env or node.id in names:
                        return
                    try:
                        obj = vars(renpy.store).get(node.id)
                    except Exception:
                        obj = None
                else:
                    path = _urmsg_path_of(node, env)
                    if isinstance(path, tuple) and path[0] not in _URMSG_NOT_STORY:
                        obj = _urmsg_obj_at(path)
        if called is not None:
            _urmsg_fn_reads(called, _urmsg_no_args, env, names, depth, r, True)
        elif obj is not None:
            _urmsg_class_reads(obj, depth, r)

    def _urmsg_class_reads(obj, depth, r):
        """Every game method of a class of the game's, or of the class of an
        object that can be called."""

        classes = (type, getattr(_urmsg_types, "ClassType", type))
        if isinstance(obj, classes):
            klass = obj
        else:
            try:
                klass = python_object.__getattribute__(obj, "__class__")
            except TypeError:
                # Python 2's old-style instances.
                klass = getattr(obj, "__class__", None)
            except Exception:
                return
            if klass is None or _urmsg_game_fn(_urmsg_static_get(klass, "__call__")) is None:
                return
        key = ("class", id(klass))
        if key in r.seen:
            return
        r.seen.add(key)
        try:
            mro = _urmsg_inspect.getmro(klass)
        except Exception:
            return
        for one in mro:
            try:
                values = python_list(one.__dict__.values())
            except Exception:
                continue
            for value in values:
                if isinstance(value, property):
                    value = value.fget
                fn = _urmsg_game_fn(value)
                if fn is not None:
                    receiver = None if isinstance(value, (staticmethod, classmethod)) else _URMSG_ANY
                    _urmsg_fn_reads(("fn", fn, receiver), _urmsg_no_args, python_dict(),
                                    python_dict(), depth, r, True)

    def _urmsg_reads_of(node, env, names, depth, r):
        """Add to r.out every name an expression reads, through the game's
        functions it calls, the properties it reads and the values of a
        function's own names."""

        kind = _urmsg_kind_of(node)
        if kind in ("Attribute", "Subscript"):
            getters = _urmsg_classes()[1]
            root = node
            parts = python_list()
            while _urmsg_kind_of(root) in ("Attribute", "Subscript"):
                if _urmsg_kind_of(root) == "Subscript":
                    _urmsg_reads_of(root.slice, env, names, depth, r)
                    parts.append(_URMSG_ITEM)
                else:
                    r.out.add(("a", root.attr))
                    parts.append(root.attr)
                    for getter in (getters.get(root.attr) or ()):
                        if getter is None:
                            _urmsg_blind(r, u"a property that cannot be read: %s" % (root.attr,))
                        elif ("getter", id(getter)) not in r.seen:
                            r.seen.add(("getter", id(getter)))
                            _urmsg_body_reads(getter, python_dict(), python_dict(), depth + 1, r, True)
                root = root.value
            parts.reverse()
            inside = _urmsg_in_store(root, parts, env, names)
            if inside is not None:
                # store.x, renpy.store.x: the store's name x, as a write of
                # x is keyed. The store itself, read whole: anything.
                if inside and inside[0] != _URMSG_ITEM:
                    r.out.add(("g", inside[0]))
                    if kind == "Attribute":
                        _urmsg_handed_reads(node, env, names, depth, r, inside)
                else:
                    _urmsg_blind(r, u"the store read whole")
                return
            if kind == "Attribute":
                _urmsg_handed_reads(node, env, names, depth, r)
            _urmsg_reads_of(root, env, names, depth, r)
            return
        if kind == "Name":
            if node.id in names:
                for value, where_env, where_names in names[node.id]:
                    key = ("value", id(value))
                    if key not in r.seen:
                        r.seen.add(key)
                        _urmsg_reads_of(value, where_env, where_names, depth, r)
            if node.id in env:
                path = env[node.id]
                if isinstance(path, tuple) and path[0] not in _URMSG_NOT_STORY:
                    r.out.add(("g", path[0]))
                    for part in path[1:]:
                        r.out.add(("a", part))
            elif node.id == "store" and node.id not in names:
                # The store handed on whole (vars(store), f(store)): what is
                # read of it cannot be told.
                _urmsg_blind(r, u"the store read whole")
            elif (node.id not in names and node.id not in ("True", "False", "None")
                  and node.id not in _URMSG_NOT_STORY):
                r.out.add(("g", node.id))
                _urmsg_handed_reads(node, env, names, depth, r)
            return
        if kind == "Call":
            func = node.func
            args = python_list(node.args)
            if _urmsg_kind_of(func) == "Name" and func.id in _URMSG_SETTERS and func.id not in env:
                # eval, globals(), vars(): reads what cannot be told.
                _urmsg_blind(r, u"a test through %s" % (func.id,))
            if (_urmsg_kind_of(func) == "Name" and func.id in ("getattr", "hasattr")
                    and func.id not in env):
                # An attribute read by its name: a written name, or anything;
                # of the store itself, the store's name.
                attr = args[1] if len(args) > 1 else None
                text = getattr(attr, "s", None) if attr is not None else None
                if text is None and _urmsg_kind_of(attr) == "Constant":
                    text = attr.value
                if isinstance(text, (_urmsg_text, type(""))):
                    r.out.add(("a", text))
                    if args and _urmsg_in_store(args[0], (), env, names) == ():
                        r.out.add(("g", text))
                        args = args[1:]
                else:
                    _urmsg_blind(r, u"getattr with a worked-out name")
            called = _urmsg_read_called(func, env)
            if called[0] in ("fn", "methods"):
                _urmsg_fn_reads(called, node, env, names, depth, r, True)
            elif called[0] == "any":
                _urmsg_blind(r, u"a call that cannot be told: %s" % (_urmsg_pyast.dump(func)[:80],))
            elif _urmsg_kind_of(func) == "Attribute":
                _urmsg_reads_of(func.value, env, names, depth, r)
            if called[0] == "other" and _urmsg_kind_of(func) in ("Name", "Attribute"):
                # A class of the game's made here (action MyAction()): what
                # its methods read when the engine runs them.
                _urmsg_handed_reads(func, env, names, depth, r)
            for arg in args:
                _urmsg_reads_of(arg, env, names, depth, r)
            for kw in (node.keywords or ()):
                _urmsg_reads_of(kw.value, env, names, depth, r)
            return
        if kind == "Lambda":
            # A rule handed to max(), sorted(), filter(): what it reads.
            _urmsg_reads_of(node.body, env, names, depth, r)
            return
        if kind in _URMSG_SCOPES:
            return
        for child in _urmsg_pyast.iter_child_nodes(node):
            _urmsg_reads_of(child, env, names, depth, r)

    def _urmsg_target_keys(target, env):
        """The keys an assignment target sets, or None when it cannot be
        told."""

        kind = _urmsg_kind_of(target)
        if kind in ("Tuple", "List"):
            out = python_list()
            for one in target.elts:
                keys = _urmsg_target_keys(one, env)
                if keys is None:
                    return None
                out.extend(keys)
            return out
        if kind == "Starred":
            return _urmsg_target_keys(target.value, env)
        path = _urmsg_path_of(target, env)
        if kind == "Attribute" and not isinstance(path, tuple):
            # Whatever it is, what is set is this attribute.
            return (("a", target.attr),)
        if isinstance(path, tuple):
            return _urmsg_keys(path)
        return None if path == _URMSG_ANY else ()

    def _urmsg_body_reads(fdef, env, names, depth, r, whole, declared=()):
        """What a function body reads. whole: its value is used, so all it
        reads; else only its tests, the tests of the game functions it
        calls, and the values it works out (r.worked)."""

        nodes = _urmsg_inside(fdef.body)
        for sub in nodes:
            kind = _urmsg_kind_of(sub)
            if kind in ("If", "While", "IfExp", "Assert"):
                _urmsg_reads_of(sub.test, env, names, depth, r)
            elif kind in ("Assign", "AnnAssign", "AugAssign") and getattr(sub, "value", None) is not None:
                if whole:
                    _urmsg_reads_of(sub.value, env, names, depth, r)
                    if kind == "AugAssign":
                        _urmsg_reads_of(sub.target, env, names, depth, r)
                else:
                    targets = sub.targets if kind == "Assign" else (sub.target,)
                    for target in targets:
                        if _urmsg_kind_of(target) == "Name" and target.id not in declared:
                            continue
                        keys = _urmsg_target_keys(target, env)
                        if keys is None:
                            # Set where it cannot be told: a test may read
                            # it, so what it is worked out from is read.
                            _urmsg_reads_of(sub.value, env, names, depth, r)
                        elif keys:
                            r.worked.append((keys, sub.value, env, names))
            elif whole and kind in ("Return", "Expr", "Yield") and getattr(sub, "value", None) is not None:
                _urmsg_reads_of(sub.value, env, names, depth, r)
            elif not whole and kind == "Call":
                inside = _urmsg_read_called(sub.func, env)
                if inside[0] in ("fn", "methods"):
                    _urmsg_fn_reads(inside, sub, env, names, depth, r, False)
                elif inside[0] == "any":
                    _urmsg_blind(r, u"a call that cannot be told: %s" % (_urmsg_pyast.dump(sub.func)[:80],))

    def _urmsg_fn_reads(called, call, env, names, depth, r, whole):
        """What a call of a game function reads (_urmsg_body_reads)."""

        if called[0] == "methods":
            for fdef in called[1]:
                _urmsg_def_reads(fdef, called[2], call, env, names, depth, r, whole, _URMSG_ANY)
            return
        fdef = _urmsg_def_of(called[1])
        if fdef is None:
            _urmsg_blind(r, u"no def found: %s" % (called[1].__name__,))
            return
        _urmsg_def_reads(fdef, called[1].__name__, call, env, names, depth, r, whole, called[2])

    def _urmsg_def_reads(fdef, name, call, env, names, depth, r, whole, receiver):
        pos, named = _urmsg_args(call, env, receiver)
        key = ("fn", id(fdef), tuple(pos), frozenset(named.items()), whole)
        if key in r.seen:
            # Read already, at whatever depth: methods of one name that
            # lead back to each other are not "too deep".
            return
        if depth >= _URMSG_FN_DEPTH:
            _urmsg_blind(r, u"too deep: %s" % (name,))
            return
        r.seen.add(key)

        nodes = _urmsg_inside(fdef.body)
        declared = python_set()
        for sub in nodes:
            if _urmsg_kind_of(sub) in ("Global", "Nonlocal"):
                declared.update(sub.names)
        inner = _urmsg_local_env(nodes, _urmsg_bind(fdef, pos, named), declared)
        for name in declared:
            inner.pop(name, None)
        own = _urmsg_values(nodes, declared, inner, call, fdef, (env, names),
                            receiver is not None)
        _urmsg_body_reads(fdef, inner, own, depth + 1, r, whole, declared)

    # The screen language: what a game's screens read. A story value a
    # screen tests (`if love >= 3: textbutton ...`), makes a button
    # sensitive with, hands an action or a used screen, is read as a test
    # of the story is: every expression of a screen is read, as the player
    # acts on what a screen shows. (Text shown with [name] in it is not a
    # test.) A screen statement of a kind not known here cannot be told.
    _URMSG_SL_KINDS = frozenset((
        "SLScreen", "SLBlock", "SLDisplayable", "SLIf", "SLShowIf", "SLFor",
        "SLPython", "SLPass", "SLDefault", "SLUse", "SLCustomUse",
        "SLTransclude", "SLBreak", "SLContinue"))
    _URMSG_SL_SCREEN = ("modal", "zorder", "variant", "predict", "sensitive",
                        "layer", "roll_forward")
    _URMSG_WORD = _urmsg_re.compile(r"^[A-Za-z_]\w*$")

    def _urmsg_sl_walk(screen, visit):
        """
        The one walk over a screen's tree (the new screen language): every
        node, last child first, each handed to visit(node, kind, tests,
        loop) - tests the screen ifs above it, as ((test, holds), ...), an
        if's earlier arms not holding; loop True inside a `for`. When visit
        answers False, nothing under that node is walked. A used screen's
        own block (a `use` with content) is walked after its children.
        """

        todo = python_list(((screen, (), False),))
        while todo:
            node, tests, loop = todo.pop()
            kind = _urmsg_kind_of(node)
            if not visit(node, kind, tests, loop):
                continue
            before = tests
            for cond, block in (getattr(node, "entries", None) or ()):
                if block is not None:
                    todo.append((block, before + ((cond, True),) if cond is not None else before,
                                 loop))
                if cond is not None:
                    before = before + ((cond, False),)
            inner = loop or kind == "SLFor"
            for child in (getattr(node, "children", None) or ()):
                todo.append((child, tests, inner))
            block = getattr(node, "block", None)
            if block is not None and kind in ("SLUse", "SLCustomUse"):
                todo.append((block, tests, loop))

    def _urmsg_screen_reads(screen, r):
        """Add to r.out every name a screen's expressions read; a step (a
        yield) every _URMSG_CHECKED_STEP expressions: a phone screen of a
        big game is 0.2 s of reading (the whole-game read runs it between
        frames)."""

        exprs = python_list()
        code = python_list()
        if _urmsg_kind_of(screen) != "SLScreen":
            # The old screen language: the screen is python.
            source = getattr(getattr(screen, "code", None), "source", None)
            if source:
                code.append(source)
            else:
                _urmsg_blind(r, u"a screen that cannot be read: %s" % (_urmsg_kind_of(screen),))
                return
        else:
            for name in _URMSG_SL_SCREEN:
                exprs.append(getattr(screen, name, None))
            params = getattr(getattr(screen, "parameters", None), "parameters", None) or ()
            if hasattr(params, "values"):
                # 8.x: a mapping of name to parameter.
                params = python_list(params.values())
            for one in params:
                exprs.append(one[1] if isinstance(one, tuple) else getattr(one, "default", None))
            def visit(node, kind, _tests, _loop):
                if kind not in _URMSG_SL_KINDS:
                    _urmsg_blind(r, u"a screen statement that cannot be read: %s" % (kind,))
                    return False
                for _name, value in (getattr(node, "keyword", None) or ()):
                    exprs.append(value)
                exprs.extend(getattr(node, "positional", None) or ())
                for cond, _block in (getattr(node, "entries", None) or ()):
                    exprs.append(cond)
                if kind == "SLFor":
                    exprs.append(node.expression)
                    exprs.append(getattr(node, "index_expression", None))
                elif kind == "SLDefault":
                    exprs.append(node.expression)
                elif kind == "SLPython":
                    source = getattr(node.code, "source", None)
                    if source is None:
                        _urmsg_blind(r, u"screen python that cannot be read")
                    else:
                        code.append(source)
                elif kind == "SLUse":
                    target = getattr(node, "target", None)
                    if target is not None and not _URMSG_WORD.match(u"%s" % (target,)):
                        # use expression ...: a worked-out screen.
                        exprs.append(target)
                    for _name, value in (getattr(getattr(node, "args", None), "arguments", None) or ()):
                        exprs.append(value)
                    exprs.append(getattr(node, "id", None))
                return True

            _urmsg_sl_walk(screen, visit)

        empty = python_dict()
        for at, expr in enumerate(exprs):
            if not (at + 1) % _URMSG_CHECKED_STEP:
                yield
            if expr is None:
                continue
            try:
                tree = _urmsg_parse(u"%s" % (expr,), "eval")
            except Exception:
                _urmsg_blind(r, u"a screen expression that does not parse: %s" % (expr,))
                continue
            _urmsg_reads_of(tree.body, empty, empty, 0, r)
        for source in code:
            yield
            tree = _urmsg_tree(source)
            if tree is None:
                _urmsg_blind(r, u"screen python that does not parse")
                continue
            for one in tree.body:
                _urmsg_reads_of(one, empty, empty, 0, r)

    def _urmsg_checked():
        """Every name the story's tests read: an if, a while, a menu
        option's condition, a jump or call to a worked-out label, a test in
        the story's python and in the game functions it calls, what a value
        worked out before a test was worked out from - through the game's
        functions and properties. Once per script; None when the script
        cannot be read; _URMSG_ANY when something a test reads cannot be
        told (then any change may be read).

        One read for both memories (the graph's twin asks its base): the
        worker reads it between frames as the game starts
        (_urmsg_checked_steps), and a display that asks before then
        finishes it at once."""

        g = _urmsg_graph()
        home = g.base if g.base is not None else g
        if home.checked is None:
            for _step in _urmsg_checked_steps(home):
                pass
        return home.checked

    _URMSG_CHECKED_STEP = 64     # statements read between two pauses

    def _urmsg_checked_steps(home=None):
        """_urmsg_checked's read, pausing (a yield) every
        _URMSG_CHECKED_STEP statements, after every screen and every value
        followed back; a float yielded is how far it is. Keeps its answer
        in `home` (the base graph). The story's python blocks it parses are
        its own, dropped when it ends: kept, they were 0.8 M objects on
        Being a DIK that every garbage collection walked (FINDINGS)."""

        if home is None:
            g = _urmsg_graph()
            home = g.base if g.base is not None else g
        if home.checked is None:
            stmts = getattr(renpy.game.script, "all_stmts", None)
            if not stmts:
                return
            parsed = python_dict()
            r = _URMSGReads()
            empty = python_dict()
            setup = python_set()
            if _urmsg_classes()[3]:
                _urmsg_blind(r, u"a class answers any name: %s" % (next(iter(_urmsg_classes()[3])),))
            for node in stmts:
                if _urmsg_kind_of(node) == "Init":
                    todo = python_list(getattr(node, "block", None) or ())
                    while todo:
                        one = todo.pop()
                        setup.add(id(one))
                        for _cond, inner in (getattr(one, "entries", None) or ()):
                            todo.extend(inner or ())
                        todo.extend(getattr(one, "block", None) or ())

            total = float(len(stmts))
            for at, node in enumerate(stmts):
                if not at % _URMSG_CHECKED_STEP:
                    yield at / total
                if _urmsg_engine_file(getattr(node, "filename", u"") or u""):
                    continue
                kind = _urmsg_kind_of(node)
                if kind == "Screen":
                    # Defined at init, read while playing.
                    for _step in _urmsg_screen_reads(getattr(node, "screen", None), r):
                        yield at / total
                    yield at / total
                    continue
                if id(node) in setup:
                    continue
                tests = python_list()
                if kind == "If":
                    tests.extend(cond for cond, _block in node.entries)
                elif kind == "While":
                    tests.append(node.condition)
                elif kind == "Menu":
                    tests.extend(item[1] for item in node.items)
                elif kind == "Jump" and getattr(node, "expression", False):
                    tests.append(node.target)
                elif kind == "Call" and getattr(node, "expression", False):
                    tests.append(node.label)
                elif kind == "Python":
                    source = getattr(getattr(node, "code", None), "source", None) or u""
                    tree = parsed.get(source)
                    if tree is None:
                        try:
                            tree = _urmsg_parse(source)
                        except Exception:
                            tree = False
                        parsed[source] = tree
                    if not tree:
                        continue
                    # The story's own python, read as a function's body
                    # whose names are all the store's.
                    _urmsg_body_reads(tree, empty, empty, 0, r, False,
                                      _urmsg_always_declared)
                    continue
                for cond in tests:
                    if _urmsg_no_test(cond):
                        continue
                    try:
                        tree = _urmsg_parse(u"%s" % (cond,), "eval")
                    except Exception:
                        _urmsg_blind(r, u"a test that does not parse: %s" % (cond,))
                        continue
                    _urmsg_reads_of(tree.body, empty, empty, 0, r)

            # A value worked out and then read by a test: what it was worked
            # out from is read too.
            used = python_set()
            grew = True
            while grew:
                grew = False
                for i, (keys, value, where_env, where_names) in enumerate(r.worked):
                    if i in used:
                        continue
                    if any(key in r.out for key in keys):
                        used.add(i)
                        grew = True
                        _urmsg_reads_of(value, where_env, where_names, 0, r)
                        yield 1.0
            if home.checked is None:
                home.checked = _URMSG_ANY if r.blind else frozenset(r.out)
                home.checked_why = r.why

    def _urmsg_checked_ahead():
        """The worker's job: the whole-game read, between frames, once the
        game is up."""

        g = _urmsg_graph()
        home = g.base if g.base is not None else g
        for said in _urmsg_checked_steps(home):
            yield said
        yield _URMWorkDone(home.checked)

    try:
        _urm_work_slices("whole-game read", _urmsg_checked_ahead)
    except Exception as error:
        print("MRM: the whole-game read waits for its first display (%s)" % (error,))

    class _URMSGEveryName(python_object):
        """Stands for "every name is declared": at the story's level, a
        name set is the store's."""

        __slots__ = ()

        def __contains__(self, name):
            return True

    _urmsg_always_declared = _URMSGEveryName()

    def _urmsg_call_quiet(line):
        """True when a python line only calls one of the game's own
        functions and nothing that call changes is read by a test of the
        story: the line is not said (_URMSG_FIX_FUNCS). Remembered per
        line."""

        if u"(" not in line or _URMSG_ASSIGN.match(line):
            return False
        g = _urmsg_graph()
        hit = g.fns.get(line)
        if hit is not None:
            return hit
        hit = False
        try:
            body = _urmsg_parse(line).body
            call = body[0].value if len(body) == 1 and _urmsg_kind_of(body[0]) == "Expr" else None
            if (call is not None and _urmsg_kind_of(call) == "Call"
                    and _urmsg_called(call.func, python_dict())[0] == "fn"):
                checked = _urmsg_checked()
                writes = _urmsg_line_effects(line)
                if checked is not None and checked != _URMSG_ANY and writes is not None:
                    hit = not any(key in checked for wrote in writes
                                  for key in _urmsg_keys(wrote))
        except Exception:
            hit = False
        g.fns[line] = hit
        return hit

    # ---- What a story line writes: the one reader for every display that
    # says what a line changes. A line is a record's text as the walks give
    # it: the story's python (_urmsg_py_lines), a jump, a call, a return
    # (_urmsg_stmt_text), a mark. Read as _urmsg_fn_walk reads a function,
    # every name set being the store's.

    # The engine's calls the walks follow as they follow a jump or a call
    # statement (_urmsg_unfollowed): on a story line they write nothing.
    _URMSG_WALKED = frozenset(("jump", "call", "return_statement", "jump_out_of_context"))
    _URMSG_LABEL_LINE = _urmsg_re.compile(r"^(?:jump|call)\s+[\w.]+$")

    def _urmsg_line_effects(line):
        """
        What a story line writes, as a frozenset of paths (_urmsg_path_of:
        the store's name first; a path that starts with _URMSG_ANY is an
        attribute of an object that cannot be told - its last name is what
        changes). Key them with _urmsg_keys to hold them against
        _urmsg_checked().

        Empty for a line that writes nothing of the story: a jump, a call
        of a label (the walks follow it and give its lines), a return, a
        check or a menu that only changes lines, persistent.

        None when that cannot be told - never "writes nothing": a jump or a
        call that cannot be followed, a custom statement with content
        inside, `call screen` and renpy.call_screen (the player sets values
        on a screen), renpy.call_in_new_context, setattr, exec, a call of
        what the script does not define, a game function that cannot be
        followed, a line that does not parse.

        Remembered per line until the script changes.
        """

        return _urmsg_line_both(line)[1]

    def _urmsg_line_writes(line):
        """
        Every path a line writes, the engine's and persistent's too - what
        a later test may then read differently (the gate chain's way facts,
        12): a game lets the player enter a name before the later check reads it. None when that cannot be told.
        """

        return _urmsg_line_both(line)[0]

    def _urmsg_line_both(line):
        """(writes, effects) of a line, remembered per line until the
        script changes."""

        if not isinstance(line, (_urmsg_text, type(""))):
            return None, None
        g = _urmsg_graph()
        try:
            return g.lines[line]
        except KeyError:
            pass
        writes = _urmsg_line_read(line)
        if writes is None:
            hit = (None, None)
        else:
            hit = (writes, frozenset(path for path in writes if path[0] not in _URMSG_NOT_STORY))
        g.lines[line] = hit
        return hit

    def _urmsg_line_read(line):
        if line == _URMSG_MARK_CHECK or line == _URMSG_MARK_MENU:
            return frozenset()
        if line.startswith(u"\x00") or line == _URMSG_DYN_JUMP or line == _URMSG_DYN_CALL:
            return None
        text = line.strip()
        if text == "return" or _URMSG_LABEL_LINE.match(text):
            return frozenset()
        tree = _urmsg_tree(text)
        if tree is None:
            return None
        nodes = _urmsg_inside(tree.body)
        for node in nodes:
            if _urmsg_kind_of(node) == "Exec":
                return None
        if len(tree.body) == 1 and _urmsg_kind_of(tree.body[0]) == "Expr":
            call = tree.body[0].value
            func = getattr(call, "func", None)
            if (_urmsg_kind_of(call) == "Call" and _urmsg_kind_of(func) == "Attribute"
                    and func.attr in _URMSG_WALKED
                    and _urmsg_path_of(func.value, python_dict()) == ("renpy",)):
                # renpy.jump("x"): what it is handed may still change things.
                nodes = python_list(one for one in nodes if one is not call)
        writes = python_list()
        if not _urmsg_nodes_effects(nodes, python_dict(), _urmsg_always_declared,
                                    0, python_set(), writes):
            return None
        return frozenset(path for path in writes if path)

    def _urmsg_py_lines(node):
        """
        (lines, dropped) for a python statement: its top-level lines that
        change the story, and how many lines of its own control flow were
        left out. Remembered per source text.
        """

        try:
            source = node.code.source
        except Exception:
            return (), 0

        source = source or ""
        py = _urmsg_py(source)
        if py.lines is None:
            out = python_list()
            drop = 0
            for line in source.split("\n"):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if line[:1] in (" ", "\t") or stripped.endswith(":"):
                    drop += 1
                    continue
                if _urmsg_noise(stripped):
                    continue
                if _URMSG_FIX_FUNCS and _urmsg_call_quiet(stripped):
                    continue
                out.append(stripped)
            py.lines = tuple(out)
            py.drop = drop
        return py.lines, py.drop

    def _urmsg_lift(arms, guards):
        """When an if has an else and every arm does exactly the same thing
        under no deeper guard, that thing is unconditional."""

        exhaustive = False
        for _guard, _rows, authored in arms:
            if not authored:
                exhaustive = True

        if exhaustive and arms:
            keys = python_list()
            for arm_guard, rows, _authored in arms:
                own = tuple(guards)
                if arm_guard is not None:
                    own = own + (arm_guard,)
                deeper = False
                for g, _t in rows:
                    if tuple(g) != own:
                        deeper = True
                        break
                if deeper:
                    keys = python_list()
                    break
                keys.append(tuple(text for _g, text in rows))

            if keys and keys[0]:
                same = True
                for key in keys:
                    if key != keys[0]:
                        same = False
                        break
                if same:
                    return python_list((guards, text) for text in keys[0])

        out = python_list()
        for _guard, rows, _authored in arms:
            out.extend(rows)
        return out

    def _urmsg_flat(nodes, guards=(), depth=0, dropped=None):
        """A block's statements as (guards, text) records, innermost guard
        last. dropped is a one-item list counting what was left out."""

        if dropped is None:
            dropped = python_list((0,))

        records = python_list()

        for node in (nodes or ()):
            k = _urmsg_kind(node)

            if k == _URMSG_K_IF:
                if depth >= _URMSG_MAX_DEPTH:
                    dropped[0] += 1
                    continue
                arms = python_list()
                earlier = python_list()
                for cond, inner in (getattr(node, "entries", None) or ()):
                    authored = not _urmsg_is_else(cond)
                    if authored and _urmsg_no_test(cond):
                        # Written `if True:` - it tests nothing, so what is
                        # in it stands under no guard of its own, and the
                        # arms after it can never run (idea 4).
                        earlier.append((cond, False))
                        arms.append((None,
                                     _urmsg_flat(inner, guards, depth + 1, dropped),
                                     False))
                        continue
                    if authored:
                        guard = _URMSGNote(
                            "only if " + _urmsg_clip(str(cond), _URMSG_MAX_GUARD_CHARS),
                            ((cond, True),), tuple(earlier))
                        earlier.append((cond, False))
                    else:
                        guard = _URMSGNote("otherwise", tuple(earlier))
                    arms.append((guard,
                                 _urmsg_flat(inner, guards + (guard,), depth + 1, dropped),
                                 authored))
                records.extend(_urmsg_lift(arms, guards))
                continue

            if k == _URMSG_K_PY:
                # A python line that jumps where it cannot be followed is
                # said the way every such jump is (idea 8), not as code.
                dyn = _urmsg_unfollowed(node)
                if dyn is not None:
                    records.append((guards, dyn))
                    continue
                lines, drop = _urmsg_py_lines(node)
                dropped[0] += drop
                for line in lines:
                    records.append((guards, line))
                continue

            text = _urmsg_stmt_text(node)
            if text is not None:
                records.append((guards, text))

        return records

    def _urmsg_arm(block):
        """The _URMSGArm of a block list, remembered by the list itself."""

        g = _urmsg_graph()
        hit = g.arms.get(id(block))
        if hit is not None and hit.block is block:
            return hit
        arm = _URMSGArm(block)
        if len(g.arms) >= _URMSG_CAP_FACTS:
            g.arms.clear()
        g.arms[id(block)] = arm
        return arm

    def _urmsg_arm_recs(block):
        """(records of a block as a tuple, how many statements were left out)"""

        arm = _urmsg_arm(block)
        if arm.recs is None:
            dropped = python_list((0,))
            arm.recs = tuple(_urmsg_flat(block, (), 0, dropped))
            arm.drop = dropped[0]
        return arm.recs, arm.drop

    def _urmsg_pure(nodes, depth=0):
        """True if this block can only fall through - no jumps or menus."""

        if depth > _URMSG_MAX_DEPTH:
            return False

        for node in (nodes or ()):
            k = _urmsg_kind(node)
            if k in (_URMSG_K_JUMP, _URMSG_K_CALL, _URMSG_K_RET,
                     _URMSG_K_MENU, _URMSG_K_WHILE):
                return False
            if k == _URMSG_K_PY and _urmsg_hop(node):
                return False
            if k == _URMSG_K_IF:
                for _c, block in (getattr(node, "entries", None) or ()):
                    if not _urmsg_pure(block, depth + 1):
                        return False
            if k == _URMSG_K_LABEL and getattr(node, "block", None):
                return False

        return True

    def _urmsg_text_menu(node):
        """A menu whose every option only says something and carries on."""

        try:
            found = False
            for item in node.items:
                if item[2] is not None:
                    found = True
            if not found:
                return False
            for item in node.items:
                if item[2] is None:
                    continue
                if not _urmsg_pure(item[2]) or _urmsg_flat(item[2]):
                    return False
                if not _urmsg_no_test(item[1]):
                    return False
            return True
        except Exception:
            return False

    def _urmsg_says_in(block, depth=0):
        """Every dialogue line directly in a block (and in ifs inside it)."""

        out = python_list()
        if depth > 4:
            return out
        for child in block or ():
            k = _urmsg_kind(child)
            if k == _URMSG_K_SAY:
                out.append(child)
            elif k == _URMSG_K_TRANS:
                for inner in child.block or ():
                    if _urmsg_kind(inner) == _URMSG_K_SAY:
                        out.append(inner)
            elif k == _URMSG_K_IF:
                for _c, sub in child.entries:
                    out.extend(_urmsg_says_in(sub, depth + 1))
        return out

    def _urmsg_target_tag(block):
        """A mark plus the label when an if arm ends (or starts) by jumping
        somewhere, for its title; empty text otherwise."""

        try:
            for node in (block[-1], block[0]):
                if _urmsg_kind(node) == _URMSG_K_JUMP and not getattr(node, "expression", False):
                    return u"\x01" + node.target
        except Exception:
            pass
        return u""

    def _urmsg_assign(text):
        """The name a record's text assigns to, or None."""

        m = _URMSG_ASSIGN.match(text)
        return m.group(1) if m else None

    def _urmsg_check_mark(node):
        """The mark for an if that only changes lines, carrying its tests."""

        tests = python_list()
        for cond, _block in (getattr(node, "entries", None) or ()):
            if not _urmsg_is_else(cond):
                tests.append((cond, None))
        return _URMSGNote(_URMSG_MARK_CHECK, tuple(tests))

    def _urmsg_call(w, stack, back, target):
        """
        Enter a called label: push the frame (statement it returns to, the
        frame's number, the label called) on the stack. False when that
        label is already being called further down the stack - the call
        would never return, which is a real loop.

        The frame's number is what tells a second call of a scene from a
        loop (idea 5): the walk remembers a statement together with the
        frame it was met in, so a statement is "met again" only inside one
        and the same call. Before, the second call of a scene found its
        statements already met and the way ended as "loops back".
        """

        if not _URMSG_FIX_FRAMES:
            stack.append((back, 0, 0))
            return True

        mark = id(target)
        for frame in stack:
            if frame[2] == mark:
                return False
        w.calls += 1
        stack.append((back, w.calls, mark))
        return True

    def _urmsg_run(w, node, stack, seen, shown=None):
        """
        Walk from node until the story ends, meets, loops, runs out of
        budget, goes where it cannot be followed or SPLITS. Returns
        (records, end, at): end is ("return",), ("meet",), ("later",),
        ("here",), ("loop",), ("limit",), ("dyn",) or ("split",) with `at`
        the If or Menu that splits. stack and seen are the caller's and are
        changed in place. A trunk walk (w.blocks set) writes its records
        into the last block and starts a block at each label it passes into.

        stack holds the frames of the calls the walk is inside
        (_urmsg_call); seen holds each statement met, by its id in the
        outermost frame and by (id, frame number) inside a call. "loop" is a
        statement met again in the same frame, or a label called while it is
        already being called.

        A jump that cannot be followed ends the walk as ("dyn",) and a call
        that cannot be entered is stepped over; either way the walk SAYS so
        with the one record for it (_URMSG_DYN_JUMP, _URMSG_DYN_CALL),
        whoever walks (idea 8).

        With ways, the run also keeps the screens on show (w.live, read
        with _urmsg_on_show): from `shown` (_urmsg_walk_shown of the run
        that reached this one's start; None: the walk's own start), plus
        every screen shown on the way, minus every one hidden.
        """

        if w.ways and _urmsg_graph().base is None:
            g = _urmsg_own()
            try:
                return _urmsg_run(w, node, stack, seen, shown)
            finally:
                _urmsg_own_end(g)

        if w.ways:
            if shown is None:
                shown = w.shown
            w.live = (python_list(shown) if shown is not None and shown is not _URMSG_NOT_SHOWN
                      else None)

        records = python_list()
        blocks = w.blocks
        keep = w.keep
        frames = _URMSG_FIX_FRAMES

        while True:

            if node is None:
                if stack:
                    node = stack.pop()[0]
                    continue
                return records, ("return",), None

            if node is _URMSG_LOST:
                # Back out of a call the game is inside, to a statement that
                # could not be found: said as every jump that cannot be
                # followed is (idea 8) - never as the end of the story.
                (records if blocks is None else blocks[-1][1]).append(
                    ((), _URMSG_DYN_JUMP))
                return records, ("dyn",), None

            if id(node) == w.stop:
                if w.stop not in w.met:
                    w.met[w.stop] = tuple(stack)
                return records, ("meet",), node

            if w.outer is not None and id(node) in w.outer:
                return records, ("later",), node

            if w.origin is not None and node is w.origin:
                return records, ("here",), node

            met = id(node)
            if frames and stack:
                met = (met, stack[-1][1])
            if met in seen:
                return records, ("loop",), node

            w.steps += 1
            if w.steps > w.limit:
                return records, ("limit",), node

            seen.add(met)

            k = _urmsg_kind(node)
            nx = getattr(node, "next", None)
            out = records if blocks is None else blocks[-1][1]

            if w.ways and (k == _URMSG_K_USER or k == _URMSG_K_PY or k == _URMSG_K_WHILE):
                if w.live is not None and k != _URMSG_K_WHILE:
                    _urmsg_live_step(w, node, k)
                if _urmsg_name_jump(node):
                    out.append(((), _URMSG_DYN_JUMP))
                    return records, ("dyn",), node
                if _urmsg_choice_in(node) is not None:
                    return records, ("split",), node

            if k == _URMSG_K_LABEL and blocks is not None and not stack:
                if blocks[-1][0] is None and not blocks[-1][1]:
                    blocks[-1][0] = node.name
                else:
                    blocks.append(python_list((node.name, python_list())))
                node = nx
                continue

            if k == _URMSG_K_JUMP:
                target = None
                if not getattr(node, "expression", False):
                    target = _urmsg_lookup(node.target)
                if target is None:
                    out.append(((), _URMSG_DYN_JUMP))
                    return records, ("dyn",), node
                node = target
                continue

            if k == _URMSG_K_CALL:
                target = None
                if not getattr(node, "expression", False):
                    target = _urmsg_lookup(node.label)
                if target is None:
                    out.append(((), _URMSG_DYN_CALL))
                    node = nx
                    continue
                if not _urmsg_call(w, stack, nx, target):
                    return records, ("loop",), target
                node = target
                continue

            if k == _URMSG_K_RET:
                if stack:
                    node = stack.pop()[0]
                    continue
                return records, ("return",), node

            if k == _URMSG_K_PY:
                hop = _urmsg_hop(node)
                if hop:
                    some = False
                    if _URMSG_FIX_HOP:
                        # What the statement does besides jumping (idea 6).
                        for line in _urmsg_py_lines(node)[0]:
                            if not _URMSG_PYJUMP.match(line):
                                out.append(((), line))
                        some = hop[0] == "jump" and _urmsg_py(node.code.source).hop_indented
                    target = _urmsg_lookup(hop[1])
                    if target is None:
                        if hop[0] == "call":
                            out.append(((), _URMSG_DYN_CALL))
                            node = nx
                            continue
                        if some:
                            # Sometimes it goes where it cannot be followed;
                            # otherwise the story carries on here.
                            cond = _urmsg_py(node.code.source).hop_cond
                            out.append(((_URMSGNote(
                                u"only if " + _urmsg_clip(cond or u"\u2026", _URMSG_MAX_GUARD_CHARS),
                                ((cond, True),) if cond else ()),), _URMSG_DYN_JUMP))
                            node = nx
                            continue
                        out.append(((), _URMSG_DYN_JUMP))
                        return records, ("dyn",), node
                    if some:
                        return records, ("split",), node
                    if hop[0] == "call" and not _urmsg_call(w, stack, nx, target):
                        return records, ("loop",), target
                    node = target
                    continue
                for line in _urmsg_py_lines(node)[0]:
                    out.append(((), line))
                node = nx
                continue

            if k == _URMSG_K_IF:
                if _urmsg_pure((node,), 0):
                    flat = _urmsg_flat((node,))
                    if flat:
                        out.extend(flat)
                    else:
                        out.append(((), _urmsg_check_mark(node)))
                    if _URMSG_FIX_SKIP and _urmsg_closed_in((node,)):
                        out.append(((), _URMSG_MARK_CODE))
                    node = nx
                    continue
                return records, ("split",), node

            if k == _URMSG_K_MENU:
                if _urmsg_text_menu(node):
                    out.append(((), _URMSG_MARK_MENU))
                    node = nx
                    continue
                if _URMSG_FIX_SKIP and not _urmsg_arms(node):
                    # No option to choose at all: the game never asks.
                    # (It was a split with no way through it - the end of
                    # everything that follows.)
                    node = nx
                    continue
                return records, ("split",), node

            if k == _URMSG_K_WHILE:
                if _URMSG_FX_WHILE in keep:
                    out.append(((), "while %s: ..." % _urmsg_clip(
                        str(getattr(node, "condition", "")), _URMSG_MAX_GUARD_CHARS)))
                node = nx
                continue

            if k == _URMSG_K_USER and _URMSG_FIX_SKIP and _urmsg_closed(node):
                # A custom statement with content inside is passed as one
                # statement; the mark says that something here is not read.
                out.append(((), _URMSG_MARK_CODE))

            text = _urmsg_stmt_text(node)
            if text is not None:
                out.append(((), text))
            node = nx

