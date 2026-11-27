# ---------------------------------------------------------------------------
# Branch-only parts: is this line shared, or here because of a check?
# ---------------------------------------------------------------------------
#
# The player's question (IDEAS.md, PRIORITY): "am I on the part everyone
# sees, or in a part that only plays because of a variable or a choice - and
# when am I back?" Three things are said on the URM+ button (the user's b,
# 2026-11-22: what a feature says, 01_urm_door and 17_hub draw it):
#
#   yellow, a badge with the lines left    in such a part; the menu's head:
#                                          "Only because Ch3bloody is yes"
#   green for one line, a check mark       the first shared line: "Back on
#                                          the shared part"
#   blue, a grey badge for one line        a check just passed over lines
#                                          others see: "Skipped a part -
#                                          needs Ch3bloody yes"
#
# How it knows. Guessing the way from one line to the next is wrong too
# often (fast skip, calls, two arms that both reach the next line), and the
# rollback log only has one entry per interaction. So every statement the
# game runs is noted as it runs, through config.statement_callbacks - which
# every statement class calls on every supported engine, If and Jump
# included. An If reports BEFORE it picks an arm, so the arm is read from
# the statement that reports next.
#
# At each line (a Say that waits, or a Menu) the statements noted since the
# line before are walked in order:
#   - an If or a Menu whose arm was taken opens a "frame": (the check, the
#     arm, the statement where that arm is back with the others);
#   - reaching a frame's rejoin statement closes it and everything opened
#     inside it;
#   - an If that passed over an arm with lines in it, without showing any
#     line itself, is a "skipped a part".
# No frame open = shared.
#
# The rejoin: when no arm of the check can leave (no jump, no return), it is
# simply the statement after the check. Otherwise it is searched for on the
# shared story graph - the first statement the arm taken and at least one
# other arm must both pass - without entering called labels (two arms that
# call the same scene do not meet inside it). No proven rejoin, no frame:
# a route that never comes back is not a detour, and unknown is never
# claimed.
#
# Rollback and loading. The state is ONE variable in the game's store,
# _urmb_state, made of plain tuples, strings and numbers - so rollback puts
# back the state of the line it returns to, a save carries it, and a save
# loads with or without URM+. Each new state is worked out only from the
# state before and the statements that ran since, so replaying those
# statements (rollback, roll-forward, load) gives the same answer again.
# Everything else here is a memo on a python_object that rollback ignores.
#
# When the statements noted do not connect to the line before (an old save,
# a jump made from a screen button, more than _URMB_REC_CAP statements in
# one go) nothing is carried over: frames are rebuilt from the checks whose
# indented arms contain the line, which the script index knows, and no
# "back" or "skipped" is said for that step.
#
# What is deliberately quiet: checks whose arms show no line; tests of the
# engine or the device (config.*, preferences.*, renpy.variant, True);
# menus with one option; parts longer than _URMB_ROUTE lines (a route, not
# a detour - tracked, never drawn); anything while skipping.
#
# Rules for this block: the same as the story graph's (no container
# displays, no comprehensions of them, classes on python_object).

init 999 python:

    import re as _urmb_re

    _URMB_REC_CAP = 2000     # statements noted between two lines
    _URMB_SCAN = 400         # statements read inside one check's arms
    _URMB_ROUTE = 40         # more lines than this: a route, not a detour
    _URMB_SEARCH = 4000      # statements searched for one rejoin
    _URMB_AHEAD = 400        # statements walked to count the lines left
    _URMB_MEMO = 4000        # checks remembered

    _urm_setting_add("urmcBranchChip", 2)
    # where players dropped the old chip: kept in their settings, read by
    # nothing since the chip is the button's badge (2026-11-22)
    _urm_setting_add("urmcBranchPos", None)

    # its row on the URM+ settings page (the registry, 01_urm_door)
    _urm_row_add("branch_chip", "story", "Branch notification",
                 "Says when the line on screen is there only because of a check or a choice you made.",
                 (("Branches and skipped parts", 2), ("Branches", 1), ("Off", 0)),
                 setting="urmcBranchChip", order=10)

    # (name of the line, frames, flash) or None. A frame is
    # (check name, arm, rejoin name, drawn, searched); flash is None,
    # ("back",) or ("skip", check name, arm). Plain data only: this is saved.
    _urmb_state = None

    _URMB_SYSTEM = _urmb_re.compile(
        r"^(?:not\s+)?(?:True|False|None|\d+|config\.[\w.]+"
        r"|_?preferences\.[\w.]+|_in_replay|main_menu|_menu"
        r"|renpy\.(?:variant|mobile|android|ios|emscripten|macintosh"
        r"|windows|linux)\b.*)$")
    _URMB_ASSIGN = _urmb_re.compile(
        r"^\s*([A-Za-z_][\w.]*)\s*(?://|[-+*/%])?=(?!=)")
    _URMB_NAME = _urmb_re.compile(r"[A-Za-z_][\w.]*")

    class _URMBState(python_object):
        __slots__ = ("rec", "over", "wrote", "gen", "info", "rejoin", "span",
                     "view", "closed", "tl", "level")

        def __init__(self):
            self.rec = python_list()
            self.over = False
            self.wrote = None
            self.gen = -1
            self.info = python_dict()
            self.rejoin = python_dict()
            self.span = python_dict()
            self.view = None
            self.closed = False
            self.level = 2

    class _URMBInfo(python_object):
        """What one If or Menu is made of, read once."""

        __slots__ = ("node", "menu", "arms", "heads", "says", "may", "lines",
                     "sets", "clean", "skip", "nxt", "has_else")

    _urmb_st = _URMBState()

    def _urmb_fresh():
        """Forget every memo when the script under the graph changed."""

        st = _urmb_st
        gen = _urmsg_gen()
        if st.gen != gen:
            st.gen = gen
            st.info.clear()
            st.rejoin.clear()
            st.span.clear()
            st.view = None

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _urmb_node(name):
        """The statement with this name, or None. Never raises, never calls
        the game's missing-label hook."""

        try:
            return renpy.game.script.namemap.get(name)
        except Exception:
            return None

    def _urmb_rep(node):
        """The first statement at or after `node` that reports itself when
        it runs: the story graph's answer (_urmsg_rep)."""

        return _urmsg_rep(node)

    def _urmb_is_line(node):
        """A statement the player reads and clicks past: a Say that waits,
        or a Menu. Transitions, pauses and screens are not lines."""

        k = _urmsg_kind(node)
        if k == _URMSG_K_MENU:
            return True
        if k == _URMSG_K_SAY:
            return bool(getattr(node, "interact", True))
        return False

    def _urmb_tl(language):
        """{id(statement in a translation block): (statement, identifier)}:
        the story graph's table (_urmsg_tl)."""

        return _urmsg_tl(language)

    def _urmb_canon(node):
        """The statement of the original script that a statement of a
        translation stands for; any other statement is itself. The story
        graph's one rule (_urmsg_default_twin, idea 14) - this block was
        the first to need it."""

        return _urmsg_default_twin(node)

    # ------------------------------------------------------------------
    # One check: its arms, and what they hold
    # ------------------------------------------------------------------

    def _urmb_scan(block):
        """
        (has lines, can leave, calls out, lines, names assigned) for one arm,
        nested blocks included. Past _URMB_SCAN statements it answers "can
        leave", which sends the rejoin to the search.
        """

        says = False
        leaves = False
        calls = False
        lines = 0
        sets = python_set()
        todo = python_list()
        if block:
            todo.extend(block)
        seen = 0

        while todo:
            if seen >= _URMB_SCAN:
                return (says, True, calls, lines, sets)
            seen += 1
            node = todo.pop()
            k = _urmsg_kind(node)

            if k == _URMSG_K_SAY:
                if getattr(node, "interact", True):
                    says = True
                    lines += 1
            elif k == _URMSG_K_MENU:
                says = True
                lines += 1
                for item in (getattr(node, "items", None) or ()):
                    if item[2]:
                        todo.extend(item[2])
            elif k == _URMSG_K_IF:
                for _cond, sub in (getattr(node, "entries", None) or ()):
                    if sub:
                        todo.extend(sub)
            elif k == _URMSG_K_WHILE or k == _URMSG_K_TRANS or k == _URMSG_K_LABEL:
                sub = getattr(node, "block", None)
                if sub:
                    todo.extend(sub)
            elif k == _URMSG_K_JUMP or k == _URMSG_K_RET:
                leaves = True
            elif k == _URMSG_K_CALL:
                calls = True
            elif k == _URMSG_K_PY:
                hop = _urmsg_hop(node)
                if hop:
                    if hop[0] == "jump":
                        leaves = True
                    else:
                        calls = True
                try:
                    source = node.code.source
                except Exception:
                    source = ""
                for raw in source.split("\n"):
                    m = _URMB_ASSIGN.match(raw)
                    if m:
                        sets.add(m.group(1))
            elif k == _URMSG_K_USER:
                if _urmsg_stmt_text(node):
                    calls = True

        return (says, leaves, calls, lines, sets)

    def _urmb_info(n):
        st = _urmb_st
        hit = st.info.get(id(n))
        if hit is not None and hit.node is n:
            return hit

        info = _URMBInfo()
        info.node = n
        info.menu = _urmsg_kind(n) == _URMSG_K_MENU
        fact = _urmsg_fact(n)

        arms = python_list()
        heads = python_list()
        says = python_list()
        may = python_list()
        lines = python_list()
        sets = python_list()
        clean = True
        system = not info.menu
        any_may = False

        # fact.arms: (index, test, typed by the author, block, start, caption)
        for arm in fact.arms:
            block = arm[3]
            arms.append((arm[1], block, arm[5], bool(arm[2])))
            head = python_set()
            if block:
                head.add(id(block[0]))
                first = _urmb_rep(block[0])
                if first is not None:
                    head.add(id(first))
            heads.append(head)
            found = _urmb_scan(block)
            says.append(found[0])
            may.append(found[0] or found[1] or found[2])
            lines.append(found[3])
            sets.append(found[4])
            if found[1]:
                clean = False
            if found[0] or found[1] or found[2]:
                any_may = True
            if not info.menu and arm[2]:
                if not _URMB_SYSTEM.match((u"%s" % (arm[1],)).strip()):
                    system = False

        info.arms = tuple(arms)
        info.heads = tuple(heads)
        info.says = tuple(says)
        info.may = tuple(may)
        info.lines = tuple(lines)
        info.sets = tuple(sets)
        info.clean = clean
        info.nxt = _urmb_rep(getattr(n, "next", None))
        info.has_else = bool(fact.has_else)
        # Not a check at all: a menu with one way through, a test of the
        # engine or device, an if whose arms show nothing and go nowhere.
        if info.menu:
            info.skip = len(arms) < 2
        else:
            info.skip = system or not any_may

        if len(st.info) >= _URMB_MEMO:
            st.info.clear()
        st.info[id(n)] = info
        return info

    def _urmb_arm(info, nx):
        """Which arm the statement that ran next belongs to: its number,
        -1 for "none, the check was passed over", None for cannot tell."""

        i = 0
        for head in info.heads:
            if id(nx) in head:
                return i
            i += 1
        if nx is info.nxt:
            return -1
        return None

    def _urmb_once(info, arm):
        """The arm changes a variable its own test reads: a once-only gate,
        whose test will not read the same way again."""

        if arm < 0 or not info.sets[arm]:
            return False
        for name in _URMB_NAME.findall(u"%s" % (info.arms[arm][0],)):
            if name in info.sets[arm]:
                return True
        return False

    # ------------------------------------------------------------------
    # Where an arm is back with the others
    # ------------------------------------------------------------------

    def _urmb_flow(node):
        """_urmsg_flow, except that a call comes straight back: the label
        it visits is not part of this stretch of the story."""

        k = _urmsg_kind(node)
        if k == _URMSG_K_CALL or k == _URMSG_K_PY:
            fact = _urmsg_fact(node)
            if k == _URMSG_K_CALL or fact.via == "call":
                nx = fact.nx
                return (nx,) if nx is not None else ()
        return _urmsg_flow(node)

    def _urmb_start(info, arm):
        if arm < 0:
            return info.nxt
        block = info.arms[arm][1]
        return _urmb_rep(block[0]) if block else info.nxt

    def _urmb_meeting(n, arm, info):
        """
        The first statement that the arm taken and at least one other arm
        must both pass, or None. Never a guess: a search cut short, or no
        statement that passes the must-pass test, is None.
        """

        starts = python_list()
        i = 0
        while i < len(info.arms):
            starts.append(_urmb_start(info, i))
            i += 1
        taken = arm
        if not info.menu and not info.has_else:
            if arm < 0:
                taken = len(starts)
            starts.append(info.nxt)
        if taken < 0 or taken >= len(starts) or len(starts) < 2:
            return None

        reach = python_list()
        for s in starts:
            if s is None:
                reach.append(python_dict())
                continue
            table, cut = _urmsg_reach(s, n, _URMB_SEARCH, True, _urmb_flow)
            if cut:
                return None
            reach.append(table)

        mine = reach[taken]
        ranked = python_list()
        for key in mine:
            dist, node = mine[key]
            if node is n:
                continue
            count = 1
            worst = dist
            j = 0
            for r in reach:
                if j != taken:
                    other = r.get(key)
                    if other is not None:
                        count += 1
                        if other[0] > worst:
                            worst = other[0]
                j += 1
            if count < 2:
                continue
            # File and line break ties, so every engine picks the same one.
            ranked.append((-count, worst, u"%s" % (getattr(node, "filename", "") or "",),
                           getattr(node, "linenumber", 0) or 0, node))

        if not ranked:
            return None

        ranked.sort(key=lambda r: r[:4])

        tried = 0
        for item in ranked:
            if tried >= _URMSG_CANDIDATES:
                break
            tried += 1
            x = item[4]
            regions = python_set()
            ok = True
            j = 0
            for s in starts:
                if s is not None and id(x) in reach[j]:
                    region = _urmsg_region(s, x, n, _URMB_SEARCH, _urmb_flow)
                    if region is None:
                        ok = False
                        break
                    regions |= region
                j += 1
            if ok and not _urmsg_meets(x, n, regions, _URMB_SEARCH, _urmb_flow):
                return _urmb_rep(x)

        return None

    def _urmb_rejoin(n, arm, info):
        """(the rejoin statement or None, whether it had to be searched for)"""

        st = _urmb_st
        key = (id(n), arm)
        hit = st.rejoin.get(key)
        if hit is not None and hit[0] is n:
            return hit[1], hit[2]

        if info.clean:
            found = info.nxt
            searched = False
        else:
            found = _urmb_meeting(n, arm, info)
            searched = True

        if len(st.rejoin) >= _URMB_MEMO:
            st.rejoin.clear()
        st.rejoin[key] = (n, found, searched)
        return found, searched

    def _urmb_span(n, arm, start, stop):
        """
        (ids of the statements the arm can be at before its rejoin, lines
        among them), or (None, None) when that runs past the cap. Called
        labels are entered: the line on screen may be inside one.
        """

        st = _urmb_st
        key = (id(n), arm)
        hit = st.span.get(key)
        if hit is not None and hit[0] is n:
            return hit[1], hit[2]

        ids = python_set()
        lines = 0
        if start is not None and start is not stop:
            ids.add(id(start))
            queue = python_list((start,))
            while queue:
                node = queue.pop()
                if _urmb_is_line(node):
                    lines += 1
                if node is n:
                    continue
                for nxt in _urmsg_flow(node):
                    if nxt is stop or id(nxt) in ids:
                        continue
                    ids.add(id(nxt))
                    if len(ids) >= _URMB_SEARCH:
                        queue = None
                        break
                    queue.append(nxt)
                if queue is None:
                    break
            if queue is None:
                ids = None
                lines = None

        if len(st.span) >= _URMB_MEMO:
            st.span.clear()
        st.span[key] = (n, ids, lines)
        return ids, lines

    def _urmb_frame(n, arm, info, rejoin, searched):
        """The frame for an arm just entered. drawn is False for a route:
        too long, or of unknown length."""

        lines = None
        if not searched and arm >= 0 and info.lines[arm] > 0:
            lines = info.lines[arm]
        else:
            lines = _urmb_span(n, arm, _urmb_start(info, arm), rejoin)[1]
        drawn = lines is not None and 0 < lines <= _URMB_ROUTE
        return (n.name, arm, rejoin.name, drawn, searched)

    # ------------------------------------------------------------------
    # From one line to the next
    # ------------------------------------------------------------------

    def _urmb_follows(a, b):
        """Whether b can be the statement that ran right after a."""

        k = _urmsg_kind(a)
        if k == _URMSG_K_PY or k == _URMSG_K_USER or k == _URMSG_K_RET:
            return True
        if k == _URMSG_K_JUMP or k == _URMSG_K_CALL:
            fact = _urmsg_fact(a)
            if fact.dyn or fact.target is None:
                return True
            return _urmb_rep(fact.target) is b
        if k == _URMSG_K_IF or k == _URMSG_K_MENU:
            return _urmb_arm(_urmb_info(a), b) is not None
        if k == _URMSG_K_WHILE:
            block = getattr(a, "block", None)
            if block and _urmb_rep(block[0]) is b:
                return True
        return _urmb_rep(getattr(a, "next", None)) is b

    def _urmb_bridge(prev, target):
        """
        The statements from prev up to (not including) target, when the
        script allows only one way there - after a load, the statements
        noted start part of the way along. None across any check.
        """

        out = python_list((prev,))
        node = prev
        steps = 0
        while steps < 200:
            steps += 1
            k = _urmsg_kind(node)
            if k in (_URMSG_K_IF, _URMSG_K_MENU, _URMSG_K_WHILE,
                     _URMSG_K_RET, _URMSG_K_USER):
                return None
            nxt = getattr(node, "next", None)
            if k == _URMSG_K_JUMP or k == _URMSG_K_CALL or k == _URMSG_K_PY:
                fact = _urmsg_fact(node)
                if fact.label is not None:
                    if fact.dyn or fact.target is None:
                        return None
                    nxt = fact.target
            nxt = _urmb_rep(nxt)
            if nxt is None:
                return None
            if nxt is target:
                return out
            out.append(nxt)
            node = nxt
        return None

    def _urmb_seed(node):
        """
        Frames for a line reached with nothing to go on, outermost first:
        one for each check whose indented arm contains it. Exact for arms
        written as indented lines; a branch reached by a jump is not found.
        """

        frames = python_list()
        try:
            index = globals().get("_urmi_index")
            index = index() if index is not None else None
            if index is None or getattr(index, "state", None) != "ready":
                return frames

            chain = python_list()
            cur = node
            for link in _urmsg_climb(index.parent, node, 64):
                if link[1] == "if" or link[1] == "option":
                    chain.append((link[0], cur))
                cur = link[0]

            i = len(chain) - 1
            while i >= 0:
                parent, child = chain[i]
                i -= 1
                info = _urmb_info(parent)
                if info.skip:
                    continue
                arm = None
                j = 0
                for _cond, block, _caption, _authored in info.arms:
                    for member in block or ():
                        if member is child:
                            arm = j
                            break
                    if arm is not None:
                        break
                    j += 1
                if arm is None:
                    continue
                rejoin, searched = _urmb_rejoin(parent, arm, info)
                if rejoin is None:
                    continue
                frames.append(_urmb_frame(parent, arm, info, rejoin, searched))
        except Exception:
            del frames[:]
        return frames

    def _urmb_has_lines(n, way, info):
        """Whether going this way through the check (an arm, or -1 for
        passing over it) shows a line before it is back with the others."""

        if way >= 0 and info.says[way]:
            return True
        if way >= 0 and not info.may[way]:
            return False
        rejoin, searched = _urmb_rejoin(n, way, info)
        if rejoin is None or (way < 0 and rejoin is info.nxt):
            return False
        lines = _urmb_span(n, way, _urmb_start(info, way), rejoin)[1]
        return bool(lines)

    def _urmb_check(stack, n, nx):
        """
        A check ran and nx ran next. Opens a frame on the stack when an arm
        with something in it was entered; returns ("skip", name, arm) when
        the check passed over an arm with lines and showed none itself.
        """

        info = _urmb_info(n)
        if info.skip:
            return None
        arm = _urmb_arm(info, nx)
        if arm is None or (info.menu and arm < 0):
            return None

        rejoin, searched = _urmb_rejoin(n, arm, info)

        silent = not _urmb_has_lines(n, arm, info)
        skipped = None
        if silent and not info.menu:
            i = 0
            last = len(info.arms)
            while i <= last:
                # The arms in order, then "passed over" when there is no else.
                way = i if i < last else -1
                if way < 0 and info.has_else:
                    break
                if way != arm and _urmb_has_lines(n, way, info):
                    if not _urmb_once(info, way):
                        skipped = ("skip", n.name, way)
                    break
                i += 1

        # Nothing to mark on a way that shows no line before the rejoin.
        if silent or rejoin is None or nx is rejoin:
            return skipped

        # The same check again (a loop): its earlier frame is over.
        name = n.name
        i = 0
        for frame in stack:
            if frame[0] == name:
                del stack[i:]
                break
            i += 1

        stack.append(_urmb_frame(n, arm, info, rejoin, searched))
        return None

    def _urmb_thaw(frames):
        """The saved frames as a list, or None when the script no longer
        has one of their statements (a save from another version)."""

        out = python_list()
        for frame in frames or ():
            if len(frame) != 5 or _urmb_node(frame[0]) is None or _urmb_node(frame[2]) is None:
                return None
            out.append(frame)
        return out

    def _urmb_advance(old, names, over, cur):
        """
        The state for the line `cur`: from the state of the line before
        (`old`) and the names of every statement that ran since. The same
        inputs always give the same state - that is what makes rollback,
        roll-forward and loading come out right.
        """

        _urmb_fresh()

        nodes = python_list()
        broken = bool(over)
        last = None
        for name in names:
            node = _urmb_node(name)
            if node is None:
                broken = True
                del nodes[:]
                last = None
                continue
            if _urmsg_kind(node) == _URMSG_K_TRANS or type(node).__name__ == "EndTranslate":
                continue
            node = _urmb_canon(node)
            if node is last:
                continue
            nodes.append(node)
            last = node

        prev = None
        frames = None
        if old is not None and not broken:
            try:
                prev = _urmb_node(old[0])
                frames = _urmb_thaw(old[1])
            except Exception:
                prev = None
                frames = None
            if prev is None or frames is None:
                prev = None
                frames = None

        # A statement can be noted after its own interaction began (a
        # window transition): the line before may head the list.
        if prev is not None:
            while nodes and nodes[0] is prev:
                del nodes[0]
            if not nodes and prev is cur:
                return old

        if not nodes or nodes[-1] is not cur:
            nodes.append(cur)

        # The longest run at the end where each statement follows the last.
        start = 0
        i = len(nodes) - 1
        while i > 0:
            if not _urmb_follows(nodes[i - 1], nodes[i]):
                start = i
                break
            i -= 1

        seq = python_list()
        joined = False
        if prev is not None and start == 0:
            if _urmb_follows(prev, nodes[0]):
                joined = True
                seq.append(prev)
            else:
                bridge = _urmb_bridge(prev, nodes[0])
                if bridge is not None:
                    joined = True
                    seq.extend(bridge)

        had = False
        if joined:
            stack = frames
            for frame in stack:
                if frame[3]:
                    had = True
        else:
            stack = _urmb_seed(nodes[start])

        first = len(seq)
        i = start
        while i < len(nodes):
            seq.append(nodes[i])
            i += 1

        skipped = None
        closed = False
        k = 0
        end = len(seq)
        while k < end:
            m = seq[k]

            # Reaching a rejoin ends its frame and everything inside it.
            name = m.name
            i = 0
            for frame in stack:
                if frame[2] == name:
                    for gone in stack[i:]:
                        if gone[3]:
                            closed = True
                    del stack[i:]
                    break
                i += 1

            if k + 1 < end:
                # A line in between: what was skipped before it is old news.
                if k >= first and _urmb_is_line(m):
                    skipped = None
                kind = _urmsg_kind(m)
                if kind == _URMSG_K_IF or kind == _URMSG_K_MENU:
                    got = _urmb_check(stack, m, seq[k + 1])
                    if got is not None:
                        skipped = got
            k += 1

        # A searched frame holds only while the line is somewhere its arm
        # can be: a jump away for good must not leave it open for ever.
        i = 0
        for frame in stack:
            if frame[4]:
                n = _urmb_node(frame[0])
                stop = _urmb_node(frame[2])
                ids = None
                if n is not None and stop is not None:
                    ids = _urmb_span(n, frame[1], _urmb_start(_urmb_info(n), frame[1]), stop)[0]
                if ids is not None and id(cur) not in ids:
                    del stack[i:]
                    break
            i += 1

        drawn = False
        for frame in stack:
            if frame[3]:
                drawn = True

        flash = None
        if not drawn:
            if joined and had and closed:
                flash = ("back",)
            elif skipped is not None:
                flash = skipped

        return (cur.name, tuple(stack), flash)

    # ------------------------------------------------------------------
    # The two hooks
    # ------------------------------------------------------------------

    def _urmb_record(name):
        """config.statement_callbacks: note the statement that is running."""

        try:
            st = _urmb_st
            ctx = renpy.game.context()
            if not ctx.rollback or ctx.init_phase:
                return
            # Only _urmb_interact writes the state, and it tells us what it
            # wrote. Anything else there means a rollback or a load put an
            # older state back: what was noted belongs to a future that no
            # longer happened.
            now = getattr(renpy.store, "_urmb_state", None)
            if now is not st.wrote:
                st.wrote = now
                del st.rec[:]
                st.over = False
            if len(st.rec) >= _URMB_REC_CAP:
                st.over = True
                return
            st.rec.append(ctx.current)
        except Exception:
            pass

    def _urmb_interact():
        """config.interact_callbacks: at a new line, work out its state."""

        st = _urmb_st
        if not st.rec and not st.over:
            return
        try:
            ctx = renpy.game.context()
            if not ctx.rollback or ctx.init_phase or ctx.current is None:
                return
            level = _urm_setting("urmcBranchChip")
            if level is None:
                level = 2
            st.level = level
            if not level:
                del st.rec[:]
                st.over = False
                return

            cur = _urmb_node(ctx.current)
            if cur is None or not _urmb_is_line(cur):
                return
            cur = _urmb_canon(cur)

            names = tuple(st.rec)
            over = st.over
            del st.rec[:]
            st.over = False

            old = getattr(renpy.store, "_urmb_state", None)
            new = _urmb_advance(old, names, over, cur)
            if new is not old:
                renpy.store._urmb_state = new
                st.wrote = new

            drawn = False
            for frame in new[1]:
                if frame[3]:
                    drawn = True
            if not drawn:
                st.closed = False
        except Exception:
            # Fail open: say nothing rather than something stale.
            try:
                del st.rec[:]
                st.over = False
                renpy.store._urmb_state = None
                st.wrote = None
            except Exception:
                pass

    def _urmb_forget():
        try:
            del _urmb_st.rec[:]
            _urmb_st.over = False
            _urmb_st.closed = False
            _urmb_st.view = None
        except Exception:
            pass

    try:
        if _urmb_record not in config.statement_callbacks:
            config.statement_callbacks.append(_urmb_record)
        if _urmb_interact not in config.interact_callbacks:
            config.interact_callbacks.append(_urmb_interact)
        if _urmb_forget not in config.after_load_callbacks:
            config.after_load_callbacks.append(_urmb_forget)
    except Exception as error:
        print("MRM: branch notification not hooked (%s)" % (error,))

    # ------------------------------------------------------------------
    # Words
    # ------------------------------------------------------------------

    def _urmb_only_test(info):
        """The one test the author typed in this if, or None when there is
        more than one (or none)."""

        only = None
        for cond, _block, _caption, authored in info.arms:
            if authored:
                if only is not None:
                    return None
                only = cond
        return only

    def _urmb_reason(info, arm):
        """The chip's words for being inside this arm."""

        if info.menu:
            caption = _URMM_TAG.sub(u"", u"%s" % (info.arms[arm][2] or u"",)).strip()
            if not caption:
                return "Because of your choice"
            return "You picked: %s" % _urm_clip(caption, 24)

        said = None
        if arm >= 0 and info.arms[arm][3]:
            said = _urmw_say(info.arms[arm][0], _urmb_once(info, arm))
        else:
            # The else arm, or passed over: the opposite of the one test.
            only = _urmb_only_test(info)
            if only is None:
                return "Only because no check passed"
            text = (u"%s" % (only,)).strip()
            if _urmw_dice(text):
                said = "by chance"
            else:
                flipped = _urmw_not(text)
                if flipped is not None:
                    said = _urmw_simple(flipped)

        if said == "by chance":
            return "Only by chance"
        if said is None:
            return "Only because of a check"
        return "Only because %s" % said

    # The goal words' own "needs" table (15_words), plus is and is not.
    _URMB_NEED = python_dict(_URM_GOAL_NEED)
    _URMB_NEED.update((("==", u""), ("!=", u"not ")))

    def _urmb_needs(cond):
        """'needs Ch3bloody yes' for the arm that was passed over, without
        the word needs; None when it cannot be said in words."""

        text = (u"%s" % (cond,)).strip()
        if "(" in text or " or " in text:
            return None
        pick = text
        parts = text.split(" and ")
        if len(parts) > 1:
            # Name the part that is not met; more than one, or none: say less.
            pick = None
            for part in parts:
                if _urm_truth(part) is False:
                    if pick is not None:
                        return None
                    pick = part
            if pick is None:
                return None
        m = _urmw_match(pick)
        if m is None:
            return None
        who = _urmm_pretty(m.group(2))
        if m.group(3):
            return "%s %s%s" % (who, _URMB_NEED[m.group(3)], _urmm_value(m.group(4)))
        return "%s %s" % (who, "false" if m.group(1) else "true")

    def _urmb_left(cur, stop):
        """Lines still to come before `stop` the way the game stands now,
        or None when that cannot be told (a menu, a return, a dice roll:
        _urm_truth never runs a test that calls a function)."""

        if cur is None or stop is None:
            return None
        count = 0
        steps = 0
        node = _urmsg_step_live(cur, _urm_truth)
        while node is not None and steps < _URMB_AHEAD:
            steps += 1
            if node is stop:
                return count
            if _urmb_is_line(node):
                count += 1
            node = _urmsg_step_live(node, _urm_truth)
        return None

    # ------------------------------------------------------------------
    # What the screen asks
    # ------------------------------------------------------------------

    def _urmb_view(state, closed, level):
        """(tone, words, lines left after this one or None, kind, closable)
        or None - pure. kind: "in" a part, "back" on its first shared
        line, "skip" past a skipped part."""

        top = None
        outer = None
        for frame in state[1]:
            if frame[3]:
                if outer is None:
                    outer = frame
                top = frame

        if top is not None:
            if closed:
                return None
            n = _urmb_node(top[0])
            if n is None:
                return None
            words = _urmb_reason(_urmb_info(n), top[1])
            left = _urmb_left(_urmb_node(state[0]), _urmb_node(outer[2]))
            return ("warn", words, left, "in", True)

        flash = state[2]
        if flash is None:
            return None
        if flash[0] == "back":
            return ("gain", "Back on the shared part", None, "back", False)
        if flash[0] == "skip" and level >= 2:
            words = "Skipped a part"
            n = _urmb_node(flash[1])
            if n is not None:
                info = _urmb_info(n)
                way = flash[2]
                needs = None
                if way >= 0 and info.arms[way][3]:
                    needs = _urmb_needs(info.arms[way][0])
                else:
                    only = _urmb_only_test(info)
                    flipped = _urmw_not(u"%s" % (only,)) if only is not None else None
                    if flipped is not None:
                        needs = _urmb_needs(flipped)
                if needs:
                    words += u"  \u00b7  needs %s" % needs
            return ("other", words, None, "skip", False)
        return None

    def urm_branch_view():
        """What to draw for the line on screen, or None for nothing."""

        try:
            st = _urmb_st
            if not st.level:
                return None
            if not _urm_in_game():
                return None
            if renpy.config.skipping:
                return None
            state = getattr(renpy.store, "_urmb_state", None)
            if state is None:
                return None
            hit = st.view
            if (hit is not None and hit[0] is state and hit[1] == st.closed
                    and hit[2] == st.level):
                return hit[3]
            _urmb_fresh()
            view = _urmb_view(state, st.closed, st.level)
            st.view = (state, st.closed, st.level, view)
            return view
        except BaseException:
            return None


    def urm_branch_close():
        """Hide: nothing said until the story is back on the shared part.
        A store name real saves hold (FINDINGS.md): it stays."""

        _urmb_st.closed = True
        renpy.restart_interaction()

    def urm_branch_dragged(drags, drop):
        """Did the old chip's drag: does nothing now. A store name real
        saves hold (FINDINGS.md): without it they would not load."""

        return None

    # ------------------------------------------------------------------
    # What the URM+ button says (the user's b, 2026-11-22)
    # ------------------------------------------------------------------

    # The badge's picture, from the kit's icon font: a split, as the corner
    # card's choices have (call_split; the route map has alt_route), a
    # check mark (check), a way around what was passed over (shortcut).
    _URMB_ICON = python_dict((("in", u"\ue0b6"), ("back", u"\ue5ca"), ("skip", u"\uf060")))
    _URMB_HIDE = u"Hide until the paths meet"

    def _urmb_says(view):
        """What the button says for urm_branch_view's `view`, as the
        doorway takes it (_urm_status_add): (tone, icon, count, tip, head,
        hide) or None - pure. In a part: yellow, the lines left counting the
        one on screen (the last shows 1), or the picture alone when that
        cannot be told; back: green with a check mark for that one line;
        skipped: the button stays blue, a grey badge for that one line."""

        if view is None:
            return None
        tone, words, left, kind, closable = view
        # the game's own words, drawn as text: a brace of theirs made safe
        words = (u"%s" % (words,)).replace(u"{", u"{{")
        icon = _URMB_ICON.get(kind, _URMB_ICON["in"])
        if kind == "in":
            if left is None:
                count, tip = None, u"The paths are still apart"
            elif left == 0:
                count, tip = u"1", u"Last line before the paths meet"
            else:
                count, tip = u"%d" % (left + 1), u"%d lines until the paths meet" % (left + 1)
            return ("warn", icon, count, tip, words,
                    (_URMB_HIDE, urm_branch_close) if closable else None)
        if kind == "back":
            return ("gain", icon, None, u"The paths meet on this line", words, None)
        return ("skip", icon, None, u"Others may see a part here", words, None)

    def _urmb_status():
        """The button asks at every draw: what the line on screen says."""

        return _urmb_says(urm_branch_view())

    _urm_status_add("branch", _urmb_status)
