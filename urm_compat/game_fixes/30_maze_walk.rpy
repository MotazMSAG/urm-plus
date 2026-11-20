# ---------------------------------------------------------------------------
# Mazes, and where a choice's flags are checked later
# ---------------------------------------------------------------------------
#
# Used by urm_choice_cards above, at draw time. Its own block because it
# keeps a per-menu cache and reads the script index, so it is held to the
# untracked-containers rule (run_tests.py step 7d).

init 999 python:

    # ------------------------------------------------------------------
    # Mazes: follow a choice to where its effects really are
    # ------------------------------------------------------------------
    #
    # Many games write a menu as nothing but jumps - "Go left": jump left2 -
    # and set their flags at the label, sometimes two or three menus further
    # in. Reading the arm's own block then shows only "jump left2". So each
    # arm is walked the way the engine would run it: through jumps, calls and
    # returns, into nested menus and ifs, until the arms meet again.
    #
    # Where they meet is found first: every arm's reachable statements are
    # collected breadth-first, and the meeting point is the statement reached
    # by the most arms, nearest to the slowest of them. In a maze that is the
    # shared "done" label; for a plain menu it is simply the line after it,
    # which is what the old reading assumed. Everything an arm does before
    # that point is its effect, and a nested menu or if that leads to
    # different effects becomes one row per outcome.
    #
    # Purely static: nothing is run, and conditions are shown, not guessed.
    # Bounded (statements, paths, menu depth) and cached per menu, because
    # this is drawn every frame.

    _URMM_REACH = 4000     # statements searched per arm for the meeting point
    # Statements walked per menu, all ways together. It was 6000 when every
    # choice inside a way doubled the walk; now a split closes at its own
    # rejoin and each statement is read about once, so the budget buys
    # length, not width - and a long scene between two choices (a thousand
    # statements of pictures and lines) no longer ends the map.
    _URMM_STEPS = 24000
    _URMM_DEPTH = 4        # nested menus followed
    _URMM_LABEL_CHARS = 26

    import re as _urmm_re
    _URMM_PYJUMP = _urmm_re.compile(
        r"""^renpy\.(jump|call)\(\s*(?:label\s*=\s*)?["']([\w.]+)["']\s*\)$""")
    _URMM_TAG = _urmm_re.compile(r"\{[^{}]*\}")

    class _URMMState(python_object):
        def __init__(self):
            self.cache = python_dict()
            # The story graph's generation the cache was filled under: a
            # changed script empties it (rework move 7).
            self.gen = None
            # Unused since the successors moved to the shared story graph,
            # which remembers them; kept because tests clear it by name.
            self.succ = python_dict()
            # The map's text sizes: (text, size, room, bold) -> (w, h), for
            # one layout; and whether the engine can be asked for them
            # (None: not tried yet).
            self.sizes = python_dict()
            self.engine = None

    _urmm_st = _URMMState()

    # Where a statement leads, and where arms meet again: the shared story
    # graph's answers (rework move 3). The names and shapes callers use are
    # unchanged; the caps stay this block's.

    def _urmm_lookup(name):
        return _urmsg_lookup(name)

    def _urmm_pyjump(node):
        """('jump'|'call', label) for a python line that only does that."""

        return _urmsg_hop(node)

    def _urmm_after(node):
        """The statement that runs after this one, ignoring its inside."""

        return getattr(node, "next", None)

    def _urmm_successors(node):
        """Every statement control can reach next - for the meeting point."""

        return _urmsg_flow(node)

    def _urmm_reach(start, menu=None):
        """
        {id: (distance, node)} for what this arm can reach.

        The search does not go through the menu on screen: a wrong turn that
        leads back to it would otherwise reach every other choice's own
        statements, and the nearest of those would be taken as the meeting
        point - hiding that choice's effects entirely.
        """

        return _urmsg_reach(start, menu, _URMM_REACH, True)[0]

    _URMM_CANDIDATES = 12  # rejoin candidates checked exactly, nearest first

    def _urmm_region(start, x, menu):
        """The ids start can reach without passing x; None when that runs on."""

        return _urmsg_region(start, x, menu, _URMM_REACH)

    def _urmm_meets(x, menu, regions):
        """True if something after x is also in the regions."""

        return _urmsg_meets(x, menu, regions, _URMM_REACH)

    def _urmm_meeting(starts, menu, after):
        """The statement where the arms rejoin, or None."""

        return _urmsg_meeting(starts, menu, after, _URMM_REACH)

    def _urmm_pure(nodes, depth=0):
        """True if this block can only fall through - no jumps or menus."""

        return _urmsg_pure(nodes, depth)

    def _urmm_choice_label(item):

        text = _URMM_TAG.sub(u"", u"%s" % (item[0] or u"")).strip()

        cond = item[1]
        if not _urmsg_no_test(cond):
            text += u" (if %s)" % _urm_clip(u"%s" % cond, _URM_MAX_GUARD_CHARS)

        return text

    # Marks in a record list: a check, or a menu, that only changes some
    # lines; a custom statement with content inside. Never shown as text;
    # the map draws them as icons.
    _URMM_MARK_CHECK = _URMSG_MARK_CHECK
    _URMM_MARK_MENU = _URMSG_MARK_MENU
    _URMM_MARK_CODE = _URMSG_MARK_CODE

    # What the "?" of a custom statement with content inside says when the
    # mouse is on it (the user's pick 3b, 2026-11-20): a mark, no line of
    # text, the reason on demand.
    _URMM_CODE_TIP = "The game runs its own code here"

    def _urmm_real(records):
        return python_list(r for r in records if not r[1].startswith(u"\x00"))

    def _urmm_dyn_again(said, guards, text):
        """True when a box or a card row already says, behind the same
        checks, that the story goes somewhere decided while playing: a call
        and a jump that both cannot be followed have the same words, and
        they are said once. said is the caller's set for one box or row."""

        if text != _URMSG_DYN_JUMP and text != _URMSG_DYN_CALL:
            return False
        key = tuple(guards)
        if key in said:
            return True
        said.add(key)
        return False

    def _urmm_target_tag(block):
        """A mark plus the label when an if arm ends (or starts) by jumping
        somewhere, for its title; empty text otherwise."""

        return _urmsg_target_tag(block)

    # The labels of the way PAST a menu the game may pass without asking
    # (_urmsg_skip_why), in the user's words (picks 1a and 2a, 2026-11-20):
    #
    #   a menu with a `set`    _URMM_SKIP, followed by what it takes. Shown
    #       as "Otherwise" - the word for "none of the above" at a check
    #       with no else - with "When nothing is left to pick" under it.
    #   every option tested    _URMM_NONE, shown as "If none apply". The
    #       label carries the options' tests (a _URMSGNote, each wanted
    #       False), so whoever draws it can say whether that way is open
    #       as the game stands (_urmm_none_open).
    _URMM_SKIP = u"\x02"
    _URMM_SKIP_WHEN = u"When nothing is left to pick"
    _URMM_NONE = u"\x03"
    _URMM_NONE_WORDS = u"If none apply"

    def _urmm_arm_label(label):
        if label.startswith(_URMM_SKIP):
            return u"otherwise"
        if label.startswith(_URMM_NONE):
            return _URMM_NONE_WORDS
        return label.split(u"\x01")[0]

    def _urmm_skip_way(menu):
        """The label of the way past this menu, or None when the game
        always asks."""

        why = _urmsg_skip_why(menu)
        if why == "set":
            return _URMM_SKIP + _URMM_SKIP_WHEN
        if why == "tests":
            tests = python_list()
            for _i, cond, _authored, _block, _start, _text in _urmsg_arms(menu):
                tests.append((cond, False))
            return _URMSGNote(_URMM_NONE, tuple(tests))
        return None

    def _urmm_none_open(label):
        """
        Whether the way "If none apply" is open as the game stands: True
        only when every option's test is known to fail right now. False
        when at least one holds - and when that cannot be read (a test
        with a call in it, a name that does not exist yet). That is how
        the user's pick 2a was put: at full strength only when no option's
        test holds right now. It is the one place where "cannot be told"
        is drawn faded; a row of chips behind a check is not (UX.md rule
        21, _urmm_fill).
        """

        return _urmm_holds((label,)) is True

    def _urmm_way_tag(at, block):
        """_urmm_target_tag for a way of a check: where its arm jumps to.
        For a python jump made only sometimes, the label it jumps to."""

        if _urmsg_kind(at) == _URMSG_K_PY:
            label = _urmsg_fact(at).label
            return (u"\x01" + label) if label else u""
        return _urmm_target_tag(block)

    def _urmm_way_kind(is_if, label):
        """The kind of box a way of a split gets: a choice, or a branch
        (a check's way, and the way past a menu)."""

        if is_if or label.startswith((_URMM_SKIP, _URMM_NONE)):
            return "branch"
        return "choice"

    def _urmm_text_menu(node):
        """A menu whose every option only says something and carries on."""

        return _urmsg_text_menu(node)

    _URMM_CHAIN = 6        # splits followed one after another on one way
    _URMM_OUTCOMES = 24    # different routes listed for one choice

    def _urmm_cut(segment):
        """True if any way through this segment stopped at the budget."""

        end = segment[1]
        if end[0] == "limit":
            return True
        if end[0] != "fork":
            return False
        for _label, sub in end[1]:
            if _urmm_cut(sub):
                return True
        cont = end[3] if len(end) > 3 else None
        return cont is not None and _urmm_cut(cont)

    def _urmm_joins(segment):
        """True if some way through this segment reaches the rejoin it was
        walked towards."""

        end = segment[1]
        if end[0] == "meet":
            return True
        if end[0] != "fork":
            return False
        cont = end[3] if len(end) > 3 else None
        if cont is not None:
            return _urmm_joins(cont)
        for _label, sub in end[1]:
            if _urmm_joins(sub):
                return True
        return False

    def _urmm_walk_each(w, ways, stack, seen, extra=0):
        """
        Walk every way of one split - ways is (label, start, depth, chain) -
        and return (label, segment) for each.

        The budget of statements is SHARED OUT: each way may use its part
        of what is left (extra more parts are held back for what follows
        the split). Walked one after another on one budget, the first ways
        used all of it and the last were not read at all - on the map those
        were boxes saying only "Goes on off the map" (Now and Then, the menu
        at ch8beatingmenu: 5,917 of 6,000 statements went to earlier
        branches, and 6 of 7 such boxes had never been read). A way cut
        short by its part is read again with whatever the others left.
        """

        whole = w.limit
        out = python_list()
        used = python_list()
        n = 0
        for label, start, depth, chain in ways:
            parts = len(ways) - n + extra
            before = w.steps
            w.limit = w.steps + max(0, whole - w.steps) // max(1, parts)
            out.append((label, _urmm_walk(w, start, stack, seen, depth, chain)))
            used.append(w.steps - before)
            n += 1

        # Only when a second reading can get FURTHER than the first did: a
        # re-read on a few leftover statements would replace a way that was
        # read to the end of its part with one that barely starts.
        n = 0
        for label, start, depth, chain in ways:
            if _urmm_cut(out[n][1]):
                held = max(0, whole - w.steps) * extra // max(1, extra + 1)
                room = whole - held - w.steps
                if room > used[n]:
                    w.limit = whole - held
                    out[n] = (label, _urmm_walk(w, start, stack, seen, depth, chain))
            n += 1

        w.limit = whole
        return out

    def _urmm_idle(walked):
        """Every way through a split gives nothing and ends the same way:
        the split only changes lines."""

        first = None
        for _label, segment in walked:
            records, end = segment
            if end[0] not in ("meet", "here", "loop", "return", "later"):
                return False
            if _urmm_real(records):
                return False
            if first is None:
                first = end
            elif end != first:
                return False
        return first is not None

    def _urmm_fork(w, at, stack, seen, depth, chain):
        """
        What a split inside a walked way comes to: (records to add, end).

        A split CLOSES AT ITS OWN REJOIN. Its ways are walked only that far,
        and what follows is walked once, as the fork's fourth element:
            ("fork", [(label, segment), ...], "if" or "menu", after or None)
        Before, every way carried on separately to the rejoin of the menu
        on screen, so whatever followed a choice inside a choice was walked
        and drawn once per way: the map doubled at each one, and the budget
        ran out. A split whose ways only meet where the split around them
        meets has no rejoin of its own (after is None) and its ways carry
        on, as before.

        A split whose every way gives nothing, ends the same way and goes
        through the same door (the same jump, or none) is not a split to
        the player - only some lines differ: it adds a mark and the walk
        goes on. (Now and Then: six ways after "Give him another one.",
        each one line and a jump back to the menu, were six boxes.)
        """

        # A check: an if, or a python jump made only sometimes (idea 6).
        is_if = _urmsg_kind(at) != _URMSG_K_MENU
        ways = python_list()
        blocks = python_list()
        doors = python_set()       # where each way's block jumps to, if it does

        # The arms are the story graph's (rework move 7): (index, test,
        # authored, block, first statement, caption).
        arms = _urmsg_arms(at)

        if is_if:
            for _i, cond, authored, block, start, _text in arms:
                if authored:
                    label = u"if " + (u"%s" % (cond,))
                else:
                    label = u"otherwise"
                ways.append((label + _urmm_way_tag(at, block), start, depth, chain + 1))
                blocks.append(block or python_list())
                doors.add(_urmm_way_tag(at, block))
            if not _urmsg_has_else(at):
                ways.append((u"otherwise", _urmm_after(at), depth, chain + 1))
                blocks.append(python_list())
                doors.add(u"")
        else:
            if depth >= _URMM_DEPTH:
                return python_list(), ("more", len(arms))
            for _i, cond, _authored, block, start, text in arms:
                ways.append((_urmm_choice_label((text, cond)), start,
                             depth + 1, chain + 1))
                blocks.append(block)
                doors.add(_urmm_target_tag(block))
            skip = _urmm_skip_way(at)
            if skip is not None:
                # The way past the menu, when the game does not ask.
                ways.append((skip, _urmm_after(at), depth, chain + 1))
                blocks.append(python_list())
                doors.add(u"")

        if chain >= _URMM_CHAIN:
            return python_list(), ("ahead",)

        own = None
        try:
            plan = _urmm_plan(at, blocks, _urmsg_sites(stack))
            own = plan[1] if plan is not None else None
        except Exception:
            own = None
        if own is not None:
            if id(own) == w.stop or (w.outer is not None and id(own) in w.outer):
                own = None
            elif w.origin is not None and own is w.origin:
                own = None

        kept_stop = w.stop
        kept_outer = w.outer
        if own is not None:
            outer = python_set(kept_outer or ())
            if kept_stop is not None:
                outer.add(kept_stop)
            w.stop = id(own)
            w.outer = outer

        walked = _urmm_walk_each(w, ways, stack, seen, 1 if own is not None else 0)

        w.stop = kept_stop
        w.outer = kept_outer

        after = None
        if own is not None:
            joined = False
            for _label, segment in walked:
                if _urmm_joins(segment):
                    joined = True
                    break
            if joined:
                # From the stack the ways had when they met: they may have
                # left the called scene the split is in.
                after = _urmm_walk(w, own, w.met.get(id(own), stack), seen,
                                   depth, chain + 1)

        # Ways that jump to DIFFERENT scenes are a real split even when
        # nothing tracked changes: the player sees another scene.
        if len(doors) == 1 and _urmm_idle(walked):
            mark = _urmsg_check_mark(at) if is_if else _URMM_MARK_MENU
            added = python_list((((), mark),))
            if after is not None:
                added.extend(after[0])
                return added, after[1]
            return added, walked[0][1][1]

        return python_list(), ("fork", walked, "if" if is_if else "menu", after)

    def _urmm_walk(w, node, stack, seen, depth, chain=0):
        """
        One way from node to the meeting point, as a segment:
        (records, end) where end is one of
            ("meet",)  ("later",)  ("here",)  ("loop",)  ("return",)
            ("limit",)  ("dyn",)  ("ahead",)  ("more", n)
            ("fork", [(label, segment), ...], "if" or "menu", after or None)
        records are (guards, text) as _urm_flatten makes them. "later" is a
        way that skips its split's own rejoin and joins further on; "ahead"
        is where the map stops following (_URMM_CHAIN splits in a row);
        "dyn" is a jump that cannot be followed - its record, the last one,
        says so, and no end text says it a second time (idea 8).

        The walk itself is the story graph's (_urmsg_run), shared with the
        map's trunk walk; what happens at a split is _urmm_fork.
        """

        stack = python_list(stack)
        seen = python_set(seen)

        records, end, at = _urmsg_run(w, node, stack, seen)

        if end[0] != "split":
            return records, end

        added, end = _urmm_fork(w, at, stack, seen, depth, chain)
        records.extend(added)
        return records, end

    _URMM_ENDS = python_dict((
        ("meet", None),
        ("here", "back to this menu"),
        ("loop", "loops back to an earlier point"),
        ("return", "returns"),
        ("limit", "goes on further than URM+ follows"),
        ("ahead", "goes on further than URM+ follows"),
        ("later", "joins the others further on"),
        ("dyn", None),
    ))

    def _urmm_leaves(segment, labels, before, out):
        """
        Flatten a segment into (labels, records, end) outcomes: every
        different route through it. A route that reaches a split's own
        rejoin carries on through what follows that split. At most
        _URMM_OUTCOMES are listed.
        """

        records, end = segment
        records = python_list(before) + _urmm_real(records)

        if end[0] != "fork":
            out.append((tuple(labels), records, end))
            return

        after = end[3] if len(end) > 3 else None

        for label, sub in end[1]:
            if len(out) >= _URMM_OUTCOMES:
                return
            if after is None:
                _urmm_leaves(sub, python_list(labels) + [label], records, out)
                continue
            inner = python_list()
            _urmm_leaves(sub, python_list(labels) + [label], records, inner)
            for labs, recs, lend in inner:
                if len(out) >= _URMM_OUTCOMES:
                    return
                if lend[0] == "meet":
                    _urmm_leaves(after, python_list(labs), recs, out)
                else:
                    out.append((labs, recs, lend))

    def _urmm_end_text(end):

        if end[0] == "more":
            return "then %d more choices" % end[1]

        return _URMM_ENDS.get(end[0])

    def _urmm_route(arm):
        """
        Plain-text outline of one arm: (common, outcomes)
          common   - records every outcome shares (before the first fork)
          outcomes - [(["path label", ...], [record text, ...], end text)]
        One outcome with no labels means the arm never forks.
        """

        records, end = arm
        records = _urmm_real(records)

        if end[0] != "fork":
            return records, [((), [], _urmm_end_text(end))]

        leaves = python_list()
        _urmm_leaves(arm, [], [], leaves)

        common = records
        cut = len(records)
        outcomes = python_list()
        for labels, recs, lend in leaves:
            outcomes.append((tuple(_urmm_arm_label(l) for l in labels),
                             _urmm_real(recs[cut:]), _urmm_end_text(lend)))

        return common, outcomes

    def _urmm_plan(menu, blocks, sites=()):
        """(arm start statements, rejoin statement or None), or None.
        sites: see _urmsg_plan - only for a split reached from where the
        game is."""

        return _urmsg_plan(menu, blocks, _URMM_REACH, sites)

    def _urmm_arms(menu, blocks, plan=None, stack=(), met=None):
        """
        One walked segment per choice, or None if the menu can't be read.

        stack: the walk's stack at the split - the calls the game is inside
        (_urmsg_frames) when the split is reached from where the game is
        (idea 7); the plan must then have been made with its sites. met: a
        list that is given the stack the ways had at the rejoin, or None
        when no way reached it.
        """

        if plan is None:
            plan = _urmm_plan(menu, blocks, _urmsg_sites(stack))
        if plan is None:
            return None

        starts, stop = plan
        w = _URMSGWalk(id(stop) if stop is not None else None, menu,
                       _URMM_STEPS, _URMSG_KEEP_ARM)

        ways = python_list((None, start, 0, 0) for start in starts)
        out = python_list(segment for _label, segment in
                          _urmm_walk_each(w, ways, stack, ()))
        if met is not None:
            met.append(w.met.get(id(stop)) if stop is not None else None)
        return out

    # ------------------------------------------------------------------
    # Checked later: where the game finally tests what a choice set
    # ------------------------------------------------------------------
    #
    # A choice often only sets a flag, the paths rejoin, and the flag decides
    # something much later: `$ path = "left"` ... `if path == "left":`. The
    # two are linked by the variable, not by the path. URM+'s script index
    # already knows every place a variable is tested; for each variable a
    # choice sets, the card names the nearest of those that can run after
    # the rejoin (breadth-first from it). A test that cannot run after this
    # point - an earlier chapter, another route - is not "later" and is left
    # out. Only real tests count, not a variable being used in arithmetic.
    #
    # The index is built in the background as the game starts; until it is
    # ready these rows are simply absent, and they are not cached as absent.

    _URMM_LATER = 8000        # statements searched after the rejoin
    _URMM_LATER_ROWS = 2      # "checked later" rows per choice

    _URMM_ASSIGN = _urmm_re.compile(
        r"^([A-Za-z_][\w.]*)\s*(?:\*\*|//|[-+*/%|&^])?=(?!=)")

    def _urmm_names(segment, out=None):
        """Variables a walked arm assigns, in the order it first does."""

        if out is None:
            out = python_list()

        records, end = segment
        for _g, text in records:
            m = _URMM_ASSIGN.match(text)
            if m and m.group(1) not in out:
                out.append(m.group(1))

        if end[0] == "fork":
            for _label, sub in end[1]:
                _urmm_names(sub, out)
            if len(end) > 3 and end[3] is not None:
                _urmm_names(end[3], out)

        return out

    def _urmm_distances(start, sites=()):
        """{id: distance} for statements that can run after start. sites:
        where the calls the game is inside go back to, when start is
        reached from where the game is - a test after the called scene has
        returned is "later" too (idea 7)."""

        return _urmsg_reach(start, None, _URMM_LATER, False,
                            _urmsg_flow_from(sites))[0]

    def _urmm_show(value):
        try:
            return _urmi_show(value)
        except Exception:
            pass
        if isinstance(value, ("".__class__, u"".__class__)):
            return '"%s"' % value
        return "%r" % (value,)

    def _urmm_test_text(name, op, literal):
        """A recorded test as the code it stands for, or None to skip it."""

        if op == "truthy":
            return name
        if op == "falsy":
            return "not " + name
        if op == "mention":
            return None
        if op == "vs":
            return "%s vs %s" % (name, literal)
        if op in ("in", "not in"):
            return "%s %s %s" % (_urmm_show(literal), op, name)
        if literal is None:
            return None
        return "%s %s %s" % (name, op, _urmm_show(literal))

    def _urmm_later(stop, names, index, dist=None):
        """
        [(name, test text, where)] - the nearest later test of each name
        that has one, in the order the names were set. dist is
        _urmm_distances(stop), passed in when several choices share it.
        """

        if stop is None or not names:
            return python_list()

        if dist is None:
            dist = _urmm_distances(stop)
        out = python_list()

        for name in names:
            best = None
            for site, op, literal in (index.reads.get(name) or ()):
                d = dist.get(site[2])
                if d is None:
                    continue
                text = _urmm_test_text(name, op, literal)
                if text is None:
                    continue
                if best is None or d < best[0]:
                    best = (d, text, site, op, literal)
            if best is None:
                continue
            try:
                label, _option, filename, line = index.where(best[2])
            except Exception:
                label, filename, line = None, best[2][0], best[2][1]
            where = label or "%s:%s" % ((filename or "?").split("/")[-1], line)
            out.append((name, best[1], where, best[3], best[4]))

        return out

    def _urmm_later_rows(found):

        rows = python_list()
        for n, (_name, text, where, _op, _lit) in enumerate(found):
            if n >= _URMM_LATER_ROWS:
                rows.append((_URM_ICON_GUARD, _urm_words(
                    "+%d more checked later" % (len(found) - n))))
                break
            rows.append((_URM_ICON_GUARD,
                         _urm_words("checked later: ") + _urm_colorize(text)
                         + " " + _urm_words("(%s)" % where)))
        return rows

