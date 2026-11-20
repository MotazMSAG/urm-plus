    # ------------------------------------------------------------------
    # Searches
    # ------------------------------------------------------------------

    def _urmsg_reach(start, origin, cap, pairs, flow=None):
        """
        Breadth-first from start. pairs True: {id: (distance, statement)},
        not searching through origin. pairs False: {id: distance}.
        Returns (table, cut) - cut when the cap stopped it.
        flow: another successor rule (default _urmsg_flow), for a search
        that must not enter called labels.
        """

        if flow is None:
            flow = _urmsg_flow
        seen = python_dict()

        if start is None:
            return seen, False

        seen[id(start)] = (0, start) if pairs else 0
        queue = python_list((start,))
        head = 0

        while head < len(queue) and len(seen) < cap:
            node = queue[head]
            head += 1
            dist = seen[id(node)][0] if pairs else seen[id(node)]
            if origin is not None and node is origin:
                continue
            for nxt in flow(node):
                if id(nxt) not in seen:
                    seen[id(nxt)] = (dist + 1, nxt) if pairs else dist + 1
                    queue.append(nxt)

        return seen, head < len(queue)

    def _urmsg_region(start, x, origin, cap, flow=None):
        """The ids start can reach without passing x; None when that runs on."""

        if flow is None:
            flow = _urmsg_flow
        seen = python_set()
        if start is None or start is x:
            return seen

        seen.add(id(start))
        queue = python_list((start,))

        while queue:
            node = queue.pop()
            if origin is not None and node is origin:
                continue
            for nxt in flow(node):
                if nxt is x or id(nxt) in seen:
                    continue
                seen.add(id(nxt))
                if len(seen) >= cap:
                    return None
                queue.append(nxt)

        return seen

    def _urmsg_meets(x, origin, regions, cap, flow=None):
        """True if something after x is also in the regions."""

        if not regions:
            return False
        if flow is None:
            flow = _urmsg_flow

        seen = python_set((id(x),))
        queue = python_list((x,))
        head = 0

        while head < len(queue) and len(seen) < cap:
            node = queue[head]
            head += 1
            if origin is not None and node is origin:
                continue
            for nxt in flow(node):
                if id(nxt) in seen:
                    continue
                if id(nxt) in regions:
                    return True
                seen.add(id(nxt))
                queue.append(nxt)

        return False

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

        nodes = python_dict()
        for table in tables:
            for key, (_dist, node) in table.items():
                nodes[key] = node

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
        while keys:
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
        a = 1
        while a < count:
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
        return closing

    _URMSG_MEET_SETS = 4       # sets of ways the shape is worked out for

    def _urmsg_can_meet(ranked, reach, origin, flow):
        """
        The candidates for the meeting point that can be one, in their
        order (_URMSG_FIX_MEET): each is asked of _urmsg_closing, worked
        out for the ways that reach it - once per set of ways, and only
        when a candidate of that set comes up. Candidates of a set past the
        first _URMSG_MEET_SETS are passed on as they are.
        """

        known = python_dict()
        for entry in ranked:
            key = id(entry[1])
            ways = python_list()
            n = 0
            for table in reach:
                if key in table:
                    ways.append(n)
                n += 1
            ways = tuple(ways)
            if ways not in known:
                if len(known) < _URMSG_MEET_SETS:
                    known[ways] = _urmsg_closing(
                        python_list(reach[i] for i in ways), origin, flow)
                else:
                    known[ways] = None
            closing = known[ways]
            if closing is None or key in closing:
                yield entry

    def _urmsg_meeting(starts, origin, after, cap=4000, flow=None):
        """The statement where the arms rejoin, or None. flow: another
        successor rule for every search in it (default _urmsg_flow)."""

        reach = python_list(_urmsg_reach(s, origin, cap, True, flow)[0] for s in starts)
        if len(reach) < 2:
            return after

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
            return None

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
            return None

        # The candidates looked at closely: the nearest ones - or, with
        # MEET, the nearest of those that can be a meeting point at all.
        # When none of them holds, the answer is as it always was: the
        # nearest statement the most ways share.
        tried = ranked
        if _URMSG_FIX_MEET:
            tried = nearest(_urmsg_can_meet(every, reach, origin, step))

        for _score, x in tried:
            regions = python_set()
            ok = True
            for start, r in zip(starts, reach):
                if id(x) not in r:
                    continue
                region = _urmsg_region(start, x, origin, cap, flow)
                if region is None:
                    ok = False
                    break
                regions |= region
            if ok and not _urmsg_meets(x, origin, regions, cap, flow):
                return x

        return ranked[0][1]

    def _urmsg_plan(origin, blocks, cap=4000, sites=()):
        """
        (arm start statements, rejoin statement or None), or None.

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

        g = _urmsg_graph()
        ids = python_list()
        for block in blocks:
            if block is None:
                return None
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
                return python_list(hit[2]), hit[3]

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
            rejoin = _urmsg_meeting(starts, origin, after, cap, _urmsg_flow_meet(sites))
        else:
            rejoin = _urmsg_meeting(starts, origin, after, cap)

        if g.skipped == skipped and _urmsg_st.g is g:
            if len(g.q) >= _URMSG_CAP_Q:
                g.q.clear()
            g.q[key] = (origin, tuple(blocks), tuple(starts), rejoin)

        return starts, rejoin

    def _urmsg_next_split(start, truth, limit=3000, flow=None):
        """
        The nearest menu at or ahead of start, and whether the search was
        cut short. An if is only pruned when truth(cond) is True or False.
        flow: another successor rule (default _urmsg_flow).
        """

        if start is None:
            return None, False
        if flow is None:
            flow = _urmsg_flow

        seen = python_set((id(start),))
        queue = python_list((start,))
        head = 0

        while head < len(queue) and head < limit:
            node = queue[head]
            head += 1
            k = _urmsg_kind(node)

            if k == _URMSG_K_MENU:
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
                     "calls", "met")

        def __init__(self, stop, origin, limit, keep, blocks=None):
            self.stop = stop
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

    def _urmsg_run(w, node, stack, seen):
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
        """

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

