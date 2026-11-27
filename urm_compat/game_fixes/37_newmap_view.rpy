# ---------------------------------------------------------------------------
# The new map, drawn (B2): the story line from the model's steps
# ---------------------------------------------------------------------------
#
# The user's picks (DECISIONS 2026-11-23, new map 1b(20), 3a): every split
# is one card listing its ways with chips. The line forks only for a way
# that stays 20 said lines or more longer than the shortest way to the
# meeting point, and for a way that ends the game or never meets again (in
# red); the lanes come back at the meeting point, a dot on the line (UX
# 17). Shorter ways stay on the line, with a muted "meet again after ~N
# lines". A check the game decides is titled per UX 25 and marked with the
# big diamond when it forks, the small one when it does not. A split whose
# ways are versions of one value is one block: "Plays in N versions", the
# current one lit with its test and length, the others folded under it.
#
# Everything here is plain data built once when the map opens (the model,
# 36, asked in the graph's twin); the screen (game_screens/37_newmap) only
# draws it. When the model cannot tell, nothing is said: no fork, no note,
# nothing lit or faded. The route map (30-34) is left as it is until the new
# map also has the overview, the bubbles and the footer (pick 5a).

init 999 python:

    _URMNM_FORK_LINES = 20      # the user's 1b(20)

    class _URMNMRowView(python_object):
        """One way on a card: words (the game's caption, or the test in
        plain words, "Otherwise" / "Then"); muted: the words are the map's,
        not the game's; have: (words, tone) of what the player has against
        its test, or None; chips: (words, tone) of what it changes; lit /
        faded; lines: "~N lines" on it before the ways meet, or None."""

        __slots__ = ("words", "muted", "have", "have_chips", "chips", "quiet_chips", "lost", "lit", "faded", "lines")

        def __init__(self, words, muted=False):
            self.words = words
            self.muted = muted
            self.have = None
            self.have_chips = ()
            self.chips = ()
            self.quiet_chips = ()
            self.lost = ()
            self.lit = False
            self.faded = False
            self.lines = None

    class _URMNMLaneView(python_object):
        """A way that leaves the line: words, lines ("~N lines" or None),
        cap: None (comes back at the meeting point), "end" (the game ends),
        "never" (never meets again); lit / faded as its row."""

        __slots__ = ("words", "lines", "cap", "lit", "faded", "at")

        def __init__(self, words, lines, cap, lit, faded, at=None):
            self.at = at
            self.words = words
            self.lines = lines
            self.cap = cap
            self.lit = lit
            self.faded = faded

    class _URMNMSceneView(python_object):
        """One scene a free-roam or sandbox place leads to."""

        __slots__ = ("words", "state", "need", "key", "tone", "lines")

        def __init__(self, words, state, need=None, key=None, tone="plain", lines=None):
            self.words = words
            self.state = state
            self.need = need
            self.key = key
            self.tone = tone
            self.lines = lines

    class _URMNMPlaceView(python_object):
        """One place inside a Free roam frame or Sandbox grid."""

        __slots__ = ("caption", "muted", "lines", "chips", "have_chips", "scenes",
                     "moves_story", "seen", "lit", "faded")

        def __init__(self, caption, muted=False):
            self.caption = caption
            self.muted = muted
            self.lines = None
            self.chips = ()
            self.have_chips = ()
            self.scenes = ()
            self.moves_story = False
            self.seen = False
            self.lit = False
            self.faded = False

    class _URMNMCardView(python_object):
        """One split as the screen draws it. title; mark: "big", "small" or
        None; rows: _URMNMRowView; versions: None, or (head, current row
        index or None) - the rows are then the versions; lanes:
        _URMNMLaneView; note: "meet again after ~N lines" or None; meet: a
        dot where the ways meet again; roam: True for a Free roam block."""

        __slots__ = ("title", "mark", "rows", "versions", "lanes", "note", "meet", "numbered",
                     "meet_line", "roam", "places", "exits", "short_checks")

        def __init__(self, title):
            self.title = title
            self.meet_line = None
            self.numbered = False
            self.mark = None
            self.rows = ()
            self.versions = None
            self.lanes = ()
            self.note = None
            self.meet = False
            self.roam = False
            self.places = ()
            self.exits = ()
            self.short_checks = ()

    class _URMNMViewState(python_object):
        def __init__(self):
            self.cards = None
            self.empty = None
            self.later = ()
            self.tip = None
            self.stretch_done = False
            self.mode = "story"
            self.sandbox = ()

    _urm_setting_add(u"urm_stretch_kind", u"auto")
    _urm_row_add("stretch_kind", "story", "Story mode",
                 "How Story line draws loops and hubs.",
                 (("Auto", u"auto"), ("Story", u"story"), ("Free roam", u"roam")),
                 setting=u"urm_stretch_kind", order=30)

    def _urmnm_view_st():
        return _urm_kept("newmap_view", _URMNMViewState)

    def urmnm_esc_text(text):
        """For text drawn with substitute False: only text tags need escaping."""
        return (u"%s" % (text,)).replace("{", "{{")

    def urmnm_font_px(size, floor=12):
        """Pixel font size with a readable floor on 800x600 games."""
        return max(floor, urmk_px_cut(size))

    def _urmnm_lines(n, cut):
        if n is None:
            return None
        if n == 0 and not cut:
            return None
        if cut:
            return u"%d+ line%s" % (n, u"" if n == 1 else u"s")
        return u"~%d line%s" % (n, u"" if n == 1 else u"s")

    def _urmnm_chip(change):
        """A change as (words, tone, name), or None when it cannot be said."""
        if change.name is None:
            return None
        if change.op is None or change.amount is None:
            words, tone = change.words, "other"
        else:
            amount = change.amount
            said = (u"%r" % (amount,)).lstrip(u"u") if isinstance(amount, (type(u""), type(""))) \
                else u"%s" % (amount,)
            op = u"=" if change.op == "=" or isinstance(amount, bool) else change.op + u"="
            words, tone = urm_map_chip(u"%s %s %s" % (change.name, op, said))
        if change.sometimes:
            words = u"%s (sometimes)" % (words,)
        return (words, tone, change.name)

    def urmnm_chip_parts(chip):
        """(words, tone, name) for one Story line chip; name is cleared to
        None when nothing can open its sheet."""
        name = chip[2] if len(chip) > 2 else None
        if name and not _urm_value_viewable():
            name = None
        return (chip[0], chip[1], name)

    def urmnm_open_value(name):
        """Open a chip's variable sheet over Story line, returning None."""
        _urm_value_view(name, None)
        return None

    def _urmnm_have_chips(gate, named=True):
        if not gate.told or gate.holds is None:
            return ()
        holds = gate.holds is gate.wanted
        expr = gate.test if gate.wanted else _urmw_not(gate.test)
        if expr is not None:
            chips = urm_need_chips(expr, holds=holds, named=named)
            if chips:
                return tuple(chips)
        if gate.have is not None:
            return ((gate.have, "gain" if holds else "loss", None),)
        return ()

    def _urmnm_have(gate, named=True):
        chips = _urmnm_have_chips(gate, named=named)
        return chips[0][:2] if chips else None

    _URMNM_OP_WORDS = python_dict((
        (">=", u"is at least"), (">", u"is over"),
        ("<=", u"is at most"), ("<", u"is under"),
        ("==", u"is"), ("!=", u"is not"),
    ))

    def _urmnm_index():
        try:
            idx = _urmi_index()
            return idx if getattr(idx, "state", None) == "ready" else None
        except Exception:
            return None

    def _urmnm_reach_dist(start, stop=None):
        if start is None:
            return python_dict(), False
        g = _urmsg_own()
        try:
            table, cut = _urmsg_reach(start, stop, _URMNM_SEARCH, False, _urmsg_flow_ways_in)
            return table, bool(cut)
        except Exception:
            return python_dict(), True
        finally:
            _urmsg_own_end(g)

    def _urmnm_place_name(index, site):
        try:
            label, _option, filename, line = index.where(site)
        except Exception:
            label, filename, line = None, site[0], site[1]
        if label:
            return _urmm_pretty(label)
        return u"%s:%s" % ((filename or u"?").split("/")[-1], line)

    def _urmnm_lit_word(lit):
        if isinstance(lit, bool):
            return u"true" if lit else u"false"
        if isinstance(lit, (type(u""), type(""))):
            return u"%s" % (lit,)
        return u"%s" % (lit,)

    def _urmnm_eval_cmp(val, op, lit, ups=0, downs=0):
        try:
            if op == "truthy":
                return bool(val) if ups == 0 and downs == 0 else None
            if op == "falsy":
                return (not val) if ups == 0 and downs == 0 else None
            num_val = isinstance(val, (int, float)) and not isinstance(val, bool)
            num_lit = isinstance(lit, (int, float)) and not isinstance(lit, bool)
            if not (num_val and num_lit):
                if ups == 0 and downs == 0:
                    if op == "==":
                        return val == lit
                    if op == "!=":
                        return val != lit
                return None
            if op == ">=":
                return (val + ups) >= lit
            if op == ">":
                return (val + ups) > lit
            if op == "<=":
                return (val - downs) <= lit
            if op == "<":
                return (val - downs) < lit
            if ups == 0 and downs == 0:
                if op == "==":
                    return val == lit
                if op == "!=":
                    return val != lit
        except Exception:
            return None
        return None

    _URMNM_AST_CMP = python_dict((
        ("GtE", ">="), ("Gt", ">"), ("LtE", "<="), ("Lt", "<"), ("Eq", "=="), ("NotEq", "!="),
    ))
    _URMNM_FLIP_OP = python_dict((
        (">=", "<="), (">", "<"), ("<=", ">="), ("<", ">"), ("==", "=="), ("!=", "!="),
    ))

    def _urmnm_const_val(node):
        kind = _urmsg_kind_of(node)
        if kind == "Constant":
            val = node.value
            return (True, val) if isinstance(val, (bool, int, float, type(u""), type(""))) else (False, None)
        if kind == "Num":
            return (True, node.n) if isinstance(node.n, (int, float)) else (False, None)
        if kind == "Str":
            return (True, node.s)
        if kind == "NameConstant":
            return (True, node.value) if node.value in (True, False) else (False, None)
        if kind == "UnaryOp" and _urmsg_kind_of(node.op) == "USub":
            ok, v = _urmnm_const_val(node.operand)
            if ok and isinstance(v, (int, float)) and not isinstance(v, bool):
                return (True, -v)
        return (False, None)

    def _urmnm_check_clauses(stmt):
        """For a simple `if` statement (no `elif`), extract a required list
        of `(name, op, lit)` conjunction clauses; None for `elif`, `or`,
        negated comparisons like `not (x >= 2)`, or complex expressions."""

        entries = getattr(stmt, "entries", None)
        if not entries:
            return None
        if len(entries) > 2 or (len(entries) == 2 and not _urmsg_is_else(entries[1][0])):
            return None
        cond = (u"%s" % (entries[0][0],)).strip()
        try:
            body = _urmsg_parse(cond, "eval").body
        except Exception:
            return None
        if _urmsg_kind_of(body) == "BoolOp":
            if _urmsg_kind_of(body.op) != "And":
                return None
            atoms = body.values
        else:
            atoms = (body,)
        clauses = python_list()
        for atom in atoms:
            ak = _urmsg_kind_of(atom)
            if ak == "Name":
                clauses.append((atom.id, "truthy", None))
            elif ak == "Attribute":
                name = _urmsg_version_name(atom)
                if not name:
                    return None
                clauses.append((name, "truthy", None))
            elif ak == "UnaryOp" and _urmsg_kind_of(atom.op) == "Not":
                name = _urmsg_version_name(atom.operand)
                if not name:
                    return None
                clauses.append((name, "falsy", None))
            elif ak == "Compare" and len(atom.ops) == 1 and len(atom.comparators) == 1:
                op = _URMNM_AST_CMP.get(_urmsg_kind_of(atom.ops[0]))
                if op is None:
                    return None
                lname = _urmsg_version_name(atom.left)
                rname = _urmsg_version_name(atom.comparators[0])
                if lname is not None:
                    ok, lit = _urmnm_const_val(atom.comparators[0])
                    if not ok:
                        return None
                    clauses.append((lname, op, lit))
                elif rname is not None:
                    ok, lit = _urmnm_const_val(atom.left)
                    if not ok:
                        return None
                    clauses.append((rname, _URMNM_FLIP_OP[op], lit))
                else:
                    return None
            else:
                return None
        return clauses if clauses else None

    def _urmnm_after_val(start_set, start_val, changes, name):
        is_set, val = start_set, start_val
        for ch in changes or ():
            if ch.name is None:
                return False, None
            if ch.name != name:
                continue
            if getattr(ch, "sometimes", False):
                return False, None
            if ch.op == "=" and ch.amount is not None:
                is_set, val = True, ch.amount
            elif ch.op in ("+", "-") and ch.amount is not None:
                if not is_set or not isinstance(val, (int, float)) or isinstance(val, bool):
                    return False, None
                if not isinstance(ch.amount, (int, float)) or isinstance(ch.amount, bool):
                    return False, None
                val = val + ch.amount if ch.op == "+" else val - ch.amount
            else:
                return False, None
        return is_set, val

    def _urmnm_lost_for(step, index=None):
        """Per-way lost scene labels for open choice options that make a
        reachable later check impossible while another open option can pass."""

        lost = python_list(python_list() for _w in step.ways)
        if step.kind != "choice" or not step.told or step.meet is None:
            return lost
        index = index if index is not None else _urmnm_index()
        if index is None:
            return lost
        open_idx = python_list(i for i, w in enumerate(step.ways)
                               if not w.faded and w.whole and w.changes is not None)
        if len(open_idx) < 2:
            return lost
        written = python_list()
        for i in open_idx:
            for ch in step.ways[i].changes or ():
                if (ch.name and not getattr(ch, "sometimes", False)
                        and ch.op in ("+", "-", "=") and ch.amount is not None
                        and ch.name not in written):
                    written.append(ch.name)
        if not written:
            return lost
        dist, cut = _urmnm_reach_dist(step.meet)
        if cut or not dist:
            return lost
        all_writes = getattr(index, "writes", None) or {}
        all_reads = getattr(index, "reads", None) or {}
        all_nodes = getattr(index, "nodes", None) or {}
        seen_sites = python_dict()
        for name in written:
            for r_site, _r_op, _r_lit in (all_reads.get(name) or ()):
                nid = r_site[2]
                if nid in dist and nid not in seen_sites:
                    seen_sites[nid] = r_site
        if not seen_sites:
            return lost
        written_set = frozenset(written)
        for nid, r_site in seen_sites.items():
            stmt = all_nodes.get(nid)
            if stmt is None:
                continue
            clauses = _urmnm_check_clauses(stmt)
            if not clauses or not any(c_name in written_set for c_name, _op, _lit in clauses):
                continue
            before_dist, before_cut = _urmnm_reach_dist(step.meet, stmt)
            if before_cut:
                continue
            overall = python_dict((i, True) for i in open_idx)
            uncertain_stmt = False
            for c_name, c_op, c_lit in clauses:
                ups, downs = 0, 0
                for w_site, w_op, w_val, _txt in (all_writes.get(c_name) or ()):
                    if w_site[2] not in before_dist or w_site[2] == nid:
                        continue
                    if w_op in ("+=", "-=") and isinstance(w_val, (int, float)) and not isinstance(w_val, bool):
                        delta = w_val if w_op == "+=" else -w_val
                        if delta > 0:
                            ups += delta
                        elif delta < 0:
                            downs += -delta
                    else:
                        uncertain_stmt = True
                        break
                if uncertain_stmt:
                    break
                start_set, start_val = _urm_now(c_name)
                for i in open_idx:
                    is_s, v_i = _urmnm_after_val(start_set, start_val, step.ways[i].changes, c_name)
                    res = _urmnm_eval_cmp(v_i, c_op, c_lit, ups, downs) if is_s else None
                    if res is False:
                        overall[i] = False
                    elif res is None and overall[i] is True:
                        overall[i] = None
            if uncertain_stmt:
                continue
            if any(overall[i] is True for i in open_idx):
                place = _urmnm_place_name(index, r_site)
                for i in open_idx:
                    if overall[i] is False and place not in lost[i]:
                        lost[i].append(place)
        return lost

    def urmnm_later(steps, index=None):
        """Goal rows for the footer: nearest reachable later check of each
        variable written across `steps`, up to 6 rows."""

        if not steps:
            return ()
        index = index if index is not None else _urmnm_index()
        if index is None:
            return ()
        names = python_list()
        for step in steps:
            if not step.told:
                continue
            for way in step.ways:
                for ch in (way.changes or ()):
                    if ch.name and ch.name not in names:
                        names.append(ch.name)
        if not names:
            return ()
        start = steps[0].meet if steps[0].meet is not None else steps[0].node
        dist, _cut = _urmnm_reach_dist(start)
        if not dist:
            return ()
        all_reads = getattr(index, "reads", None) or {}
        rows = python_list()
        for name in names:
            best = None
            for site, op, lit in (all_reads.get(name) or ()):
                d = dist.get(site[2])
                if d is None or (op not in _URMNM_OP_WORDS and op not in ("truthy", "falsy")):
                    continue
                if best is None or d < best[0]:
                    best = (d, site, op, lit)
            if best is None:
                continue
            _d, site, op, lit = best
            who = _urmm_pretty(name)
            where = _urmnm_place_name(index, site)
            if op == "truthy":
                cond_words = u"%s is true" % who
            elif op == "falsy":
                cond_words = u"%s is false" % who
            else:
                cond_words = u"%s %s %s" % (who, _URMNM_OP_WORDS[op], _urmnm_lit_word(lit))
            is_set, now = _urm_now(name)
            passes = _urmnm_eval_cmp(now, op, lit) if is_set else False
            tone = "gain" if passes is True else "loss"
            if op in (">=", ">", "<=", "<") and isinstance(lit, (int, float)) and not isinstance(lit, bool):
                have = urm_goal(name, op, lit)
                if not have:
                    have = u"%s/%s" % (_urm_number(now) if is_set and _urm_isnum(now) else u"?", _urm_number(lit))
            elif op in ("truthy", "falsy") or isinstance(lit, bool):
                have = (u"true" if now else u"false") if is_set else u"unset"
            else:
                have = _urmnm_lit_word(now) if is_set else u"unset"
            rows.append((u"At %s: %s" % (where, cond_words), have, tone, name))
            if len(rows) >= 6:
                break
        return tuple(rows)

    def urmnm_chip_tip(words, quiet=False, lost=False):
        if lost:
            return u"Picking this option closes that scene later"
        if quiet:
            return u"Never checked later in the script"
        if words and u"(sometimes)" in words:
            return u"Only happens under a check inside this path"
        return None

    def urmnm_set_tip(words=None):
        _urmnm_view_st().tip = words
        renpy.restart_interaction()
        return None

    def urmnm_tip_now():
        return getattr(_urmnm_view_st(), "tip", None)

    def urmnm_later_count():
        return len(getattr(_urmnm_view_st(), "later", ()) or ())

    def urmnm_later_rows():
        return tuple(getattr(_urmnm_view_st(), "later", ()) or ())

    def urmnm_overview_marks():
        cards = _urmnm_view_st().cards or ()
        out = python_list()
        for c in cards:
            if getattr(c, "roam", False):
                kind = "roam"
                bad = False
            else:
                kind = "versions" if c.versions is not None else ("check" if not c.numbered else "choice")
                bad = any(l.cap for l in c.lanes) or any(getattr(r, "lost", ()) for r in c.rows)
            out.append((kind, bool(bad)))
        return tuple(out)

    def urmnm_overview(st, at, xadj, size):
        """Compact horizontal timeline strip tracking viewport scroll."""

        try:
            mw, mh = size
            marks = urmnm_overview_marks()
            out = Fixed(xysize=(mw, mh))
            out.add(Solid(urmk_colour("surface"), xysize=(mw, mh)))
            pad = max(4, urmk_px_cut(6))
            mid = mh // 2
            line_h = max(1, urmk_px_cut(2))
            out.add(Solid(urmk_colour("graph-line"), xysize=(max(4, mw - 2 * pad), line_h), xpos=pad, ypos=mid - line_h // 2))
            dot = max(4, urmk_px_cut(6))
            out.add(Solid(urmk_colour("accent-ink"), xysize=(dot, dot), xpos=pad, ypos=mid - dot // 2))
            count = len(marks)
            if count:
                span = max(1, mw - 2 * pad - dot * 2)
                for idx, (kind, bad) in enumerate(marks):
                    cx = pad + dot + int((idx + 1) * span / float(count + 1))
                    colour = urmk_colour("warn-ink" if kind in ("check", "versions") else "ink-muted")
                    tick_w = max(3, urmk_px_cut(5))
                    tick_h = max(8, mh // 2)
                    out.add(Solid(colour, xysize=(tick_w, tick_h), xpos=cx - tick_w // 2, ypos=mid - tick_h // 2))
                    if bad:
                        out.add(Solid(urmk_colour("loss-ink"), xysize=(tick_w, max(3, urmk_px_cut(5))), xpos=cx - tick_w // 2, ypos=min(mh - 4, mid + tick_h // 2 - 2)))
            rng = float(getattr(xadj, "range", 0) or 0)
            page = float(getattr(xadj, "page", 0) or 0)
            val = float(getattr(xadj, "value", 0) or 0)
            total = rng + page
            if rng > 0 and total > 0:
                vw = max(10, int(mw * page / total))
                vx = min(mw - vw, max(0, int(mw * val / total)))
            else:
                vw, vx = mw, 0
            ink = urmk_colour("ink")
            out.add(Solid(ink, xysize=(vw, 2), xpos=vx, ypos=0))
            out.add(Solid(ink, xysize=(vw, 2), xpos=vx, ypos=mh - 2))
            out.add(Solid(ink, xysize=(2, mh), xpos=vx, ypos=0))
            out.add(Solid(ink, xysize=(2, mh), xpos=min(mw - 2, vx + vw - 2), ypos=0))
            return out, 0.1
        except Exception:
            return Null(), None

    def _urmnm_roam_context(step):
        """Return (is_roam, region_or_None) for `step` using core stretch info."""

        g = _urmsg_own()
        try:
            stretch = _urmsg_stretch(step.node)
            region = _urmsg_stretch_region(step.node) if stretch == "roam" else None
        except Exception:
            stretch = None
            region = None
        finally:
            _urmsg_own_end(g)
        is_room = getattr(step, "shape", None) in _URMNM_ROOMS
        if stretch == "roam" or (is_room and stretch != "story" and step.ways):
            return True, region
        return False, None

    def _urmnm_place_lines(start, origin, stop=None):
        if start is None:
            return None
        g = _urmsg_own()
        try:
            n, cut = _urmsg_said_to(start, origin, stop, _URMNM_WALK, _urmsg_flow_ways_in, python_dict())
            return _urmnm_lines(n, cut)
        except Exception:
            return None
        finally:
            _urmsg_own_end(g)

    def _urmnm_place_seen(choice_way, start):
        lbl = getattr(choice_way, "label", None) if choice_way is not None else None
        if not lbl and isinstance(start, renpy.ast.Label):
            lbl = getattr(start, "name", None)
        if not lbl:
            return False
        try:
            fn = getattr(renpy, "seen_label", None)
            return bool(fn(lbl)) if fn is not None else False
        except Exception:
            return False

    def _urmnm_place_reaches_exit(start, inside_ids, exit_from_ids, origin):
        if start is None or (not exit_from_ids and not inside_ids):
            return False
        g = _urmsg_own()
        try:
            seen = python_set()
            todo = python_list((start,))
            steps = 0
            while todo and steps < _URMNM_SEARCH:
                cur = todo.pop(0)
                cid = id(cur)
                if cid in seen:
                    continue
                seen.add(cid)
                steps += 1
                if cid in exit_from_ids or (inside_ids and cid not in inside_ids):
                    return True
                if cur is origin or (cur is not start and _urmsg_choice_in(cur) is not None):
                    continue
                for nxt in _urmsg_flow_ways_in(cur) or ():
                    if nxt is not None and id(nxt) not in seen:
                        todo.append(nxt)
            return False
        except Exception:
            return False
        finally:
            _urmsg_own_end(g)

    def _urmnm_scene_view(sc):
        """Convert a _URMNMScene (from urmnm_places) into a display-safe _URMNMSceneView."""

        gate = sc.way.gates[0] if sc.way and sc.way.gates else None
        gate_words = gate.words if gate and gate.words else None
        if sc.state == "open":
            return _URMNMSceneView(gate_words or u"Open scene", "open", u"open", None, "gain")
        if sc.state == "step":
            pretty = _urmm_pretty(sc.key) if sc.key else None
            if sc.need and pretty and not (sc.need.lower().startswith(pretty.lower())):
                need = u"needs %s (%s)" % (pretty, sc.need)
            elif sc.need:
                need = u"needs %s" % (sc.need,)
            else:
                need = u"needs %s" % (pretty or gate_words or u"requirement",)
            return _URMNMSceneView(gate_words or pretty or u"One step away", "step", need, sc.key, "warn")
        if sc.state == "locked":
            return _URMNMSceneView(gate_words or u"Locked scene", "locked", u"locked", sc.key, "loss")
        return _URMNMSceneView(gate_words or u"Scene", None, None, None, "plain")

    def urmnm_roam_view(step, exits=()):
        """Build a Free roam / Sandbox card view from a roam or room step."""

        card = _URMNMCardView(u"Free roam")
        card.roam = True
        card.numbered = False
        places_raw = urmnm_places(step)
        g = _urmsg_own()
        try:
            choice = _urmsg_choice_in(step.node)
        except Exception:
            choice = None
        finally:
            _urmsg_own_end(g)
        cways = choice.ways if choice is not None and len(choice.ways) == len(step.ways) else None
        inside_ids = python_set()
        exit_from_ids = python_set()
        if exits:
            inside_stmts, exit_pairs = exits
            for n in inside_stmts or ():
                inside_ids.add(id(n))
            for a, _b in exit_pairs or ():
                exit_from_ids.add(id(a))
        out_places = python_list()
        found_exits = python_list()
        for at, way in enumerate(step.ways):
            cap = _urm_player_text(way.caption) if way.caption else u"A place"
            pv = _URMNMPlaceView(cap, not way.caption)
            pv.lines = _urmnm_lines(way.said, way.said_cut) or _urmnm_place_lines(way.start, step.node)
            if step.told and way.changes:
                pv.chips = tuple(c for c in (_urmnm_chip(ch) for ch in way.changes
                                             if not (ch.op == "=" and ch.amount is None)) if c)
            for gate in way.gates:
                if not pv.have_chips:
                    pv.have_chips = _urmnm_have_chips(gate, named=True)
            pv.lit = way.lit
            pv.faded = way.faded
            cway = cways[at] if cways is not None else None
            pv.seen = _urmnm_place_seen(cway, way.start)
            if at < len(places_raw):
                pv.scenes = tuple(_urmnm_scene_view(sc) for sc in places_raw[at][1])
            pv.moves_story = _urmnm_place_reaches_exit(way.start, inside_ids, exit_from_ids, step.node)
            if pv.moves_story:
                found_exits.append(pv.caption)
            out_places.append(pv)
        card.places = tuple(out_places)
        card.exits = tuple(found_exits)
        card.meet = bool(found_exits)
        card.meet_line = _urmnm_first_line(exits[1][0][1]) if (found_exits and exits and exits[1]) else None
        return card

    def urmnm_roam_is_sandbox(cards, steps=()):
        """True when Story line is standing in a pure sandbox hub (one roam card, no story exits)."""

        return bool(len(cards) == 1 and getattr(cards[0], "roam", False)
                    and not getattr(cards[0], "exits", ())
                    and (not steps or len(steps) == 1))

    def urmnm_story_mode():
        return getattr(_urmnm_view_st(), "mode", "story") or "story"

    def urmnm_sandbox_count():
        return len(getattr(_urmnm_view_st(), "sandbox", ()) or ())

    def urmnm_sandbox_places():
        return tuple(getattr(_urmnm_view_st(), "sandbox", ()) or ())

    def urmnm_sandbox_rows(cols=3):
        places = urmnm_sandbox_places()
        return tuple(places[i:i + cols] for i in range(0, len(places), cols))

    def urmnm_roam_exit_y(places, header_px, row_px, default_y):
        for i, p in enumerate(places or ()):
            if getattr(p, "moves_story", False):
                return int(header_px + i * row_px)
        return int(default_y)

    def urmnm_roam_visible(places, opened, idx):
        if idx in opened or len(places) <= 6:
            return places
        return places[:6]

    def urmnm_roam_hidden_count(places, opened, idx):
        if idx in opened or len(places) <= 6:
            return 0
        return len(places) - 6

    def urmnm_story(steps, index=None):
        """The cards for a list of the model's steps (urmnm_model)."""

        cards = python_list()
        for step in steps:
            card = _urmnm_card(step, index=index)
            marks = python_list()
            for count, outcomes in step.short_checks:
                captions = python_list()
                for conditions in outcomes:
                    words = python_list()
                    for test, wanted in conditions:
                        gate = _URMNMGate(test, wanted, told=False)
                        _urmnm_gate_now(gate)
                        words.append(gate.words or u"the game's check")
                    if words:
                        captions.append(u" and ".join(words))
                marks.append((u"+%d" % count, count >= 10,
                              u" or ".join(captions) or u"The game checks which lines to show"))
            card.short_checks = tuple(marks)
            cards.append(card)
        return cards

    def _urmnm_card(step, index=None):
        if step.kind == "choice":
            is_roam, region = _urmnm_roam_context(step)
            if is_roam:
                return urmnm_roam_view(step, exits=region)
        game = step.kind != "choice"
        card = _URMNMCardView(u"You choose" if not game else
                              (u"The game picks the way" if step.kind == "pick"
                               else u"The game checks"))
        card.numbered = not game
        lost_by_way = _urmnm_lost_for(step, index=index) if not game else ()
        rows = python_list()
        for at, way in enumerate(step.ways):
            if game:
                gate = way.gates[0] if way.gates else None
                if way.tail is not None:
                    row = _URMNMRowView(u"Otherwise" if way.tail == "otherwise" else u"Then")
                elif gate is not None and gate.words:
                    row = _URMNMRowView(gate.words)
                    row.have_chips = _urmnm_have_chips(gate, named=False)
                    row.have = row.have_chips[0][:2] if row.have_chips else None
                else:
                    row = _URMNMRowView(u"When the game's own test holds", True)
            else:
                row = _URMNMRowView(_urm_player_text(way.caption) if way.caption else u"An option", not way.caption)
                for gate in way.gates:
                    if not row.have_chips:
                        row.have_chips = _urmnm_have_chips(gate, named=True)
                        row.have = row.have_chips[0][:2] if row.have_chips else None
            if step.told and way.changes:
                row.chips = tuple(c for c in (_urmnm_chip(ch) for ch in way.changes) if c)
            if step.told and getattr(way, "quiet", None):
                row.quiet_chips = tuple(c for c in (_urmnm_chip(ch) for ch in way.quiet) if c)
            if lost_by_way and at < len(lost_by_way) and lost_by_way[at]:
                row.lost = tuple(lost_by_way[at])
            # Lit marks the way the game takes; a choice's open options are
            # simply there (only a closed one is faded).
            row.lit, row.faded = way.lit and game, way.faded
            rows.append(row)
        if not rows:
            # A choice whose options cannot be read (DECISIONS 2026-11-23, 2a).
            rows.append(_URMNMRowView(u"You choose here, the options can't be read", True))
        card.rows = tuple(rows)
        if not step.told:
            # M3: captions only - no split, no note, nothing lit or faded.
            for row in card.rows:
                row.lit = row.faded = False
                row.chips = ()
            return card
        card.meet = step.meet is not None
        card.meet_line = _urmnm_first_line(step.meet)
        if game and (step.versions is not None or len(step.ways) >= 4):
            # Versions of one value, and any check of the game with four ways
            # or more (the user's rule, 2026-11-23): one block, yours shown.
            lit = python_list(i for i, way in enumerate(step.ways) if way.lit)
            current = lit[0] if len(lit) == 1 else None
            for i, way in enumerate(step.ways):
                card.rows[i].lines = _urmnm_lines(way.said, way.said_cut)
            card.versions = (u"Plays in %d versions" % len(step.ways), current)
            card.mark = "big"
            return card
        lanes, note = _urmnm_forks(step)
        card.lanes = tuple(_URMNMLaneView(card.rows[i].words, _urmnm_lines(w.said, w.said_cut),
                                          cap, w.lit and game, w.faded, i)
                           for i, w, cap in lanes)
        card.note = note
        if game:
            card.mark = "big" if card.lanes else "small"
        return card

    def _urmnm_forks(step):
        """([(index, way, cap)], note): the ways that leave the line - one
        that ends the game or never meets (cap "end" / "never"), and one
        that says 20 lines or more of its own before the meeting point -
        and the note for the ways that stay."""

        out = python_list()
        stay = python_list()
        for i, way in enumerate(step.ways):
            if way.end in ("end", "never"):
                out.append((i, way, way.end))
            elif way.end == "meet" and way.said is not None and way.said >= _URMNM_FORK_LINES:
                # 20 said lines or more of its own before the meeting: it
                # leaves the line (the user's rule, 2026-11-23; a floor that
                # already reaches 20 counts).
                out.append((i, way, None))
            elif way.end == "meet" and way.said is not None and not way.said_cut:
                # A way that stays whose count is only a floor leaves the gap
                # untold: it is not counted, so no note is said.
                stay.append((i, way))
        stay = python_list(way for _i, way in stay)
        note = None
        # The note speaks for the ways that stay on the line, only when every
        # way is accounted for and no lane comes back to say it instead.
        if (step.meet is not None and stay and len(stay) + len(out) == len(step.ways)
                and all(cap is not None for _i, _w, cap in out)):
            most = max(stay, key=lambda w: w.said)
            if most.said > 0:
                note = u"meet again after %s" % _urmnm_lines(most.said, False)
        return out, note

    # ---- open and close

    def urmnm_view():
        return _urmnm_view_st()

    def _urmnm_stretch_is_done():
        g = _urmsg_own()
        try:
            return bool(_urmsg_stretch_table().done)
        except Exception:
            return True
        finally:
            _urmsg_own_end(g)

    def urmnm_stretch_done():
        return bool(getattr(_urmnm_view_st(), "stretch_done", False))

    def urmnm_story_load(steps):
        """Populate view state from `steps` and return cards."""
        st = _urmnm_view_st()
        st.cards = urmnm_story(steps)
        st.later = urmnm_later(steps)
        if urmnm_roam_is_sandbox(st.cards, steps):
            st.mode = "sandbox"
            st.sandbox = st.cards[0].places
        else:
            st.mode = "story"
            st.sandbox = ()
        st.empty = None if st.cards else u"Nothing splits ahead"
        return st.cards

    def urmnm_stretch_tick():
        """Run one slice of the stretch pass (a frame's share, 6 ms); when
        it is done, rebuild the cards and redraw once. The worker calls it
        between frames (_urmnm_stretch_job), never the screen: a timer on the
        screen rebuilt the whole screen 20 times a second while the pass ran
        (the speed plan, FINDINGS "Where URM+ freezes")."""

        st = _urmnm_view_st()
        if getattr(st, "stretch_done", False):
            return None
        try:
            done = bool(_urmsg_stretch_step(0.006))
        except Exception as error:
            print("MRM: stretch pass failed (%s)" % (error,))
            st.stretch_done = True
            renpy.restart_interaction()
            return None
        if done:
            st.stretch_done = True
            if renpy.get_screen("urmnm_story", layer=_urmi_layer) is None:
                return None     # closed: the next open reads the cards
            _urmnm_story_read(keep=True)
            renpy.restart_interaction()
        return None

    _URMNM_READING = u"Reading the story ahead..."

    def _urmnm_story_failed():
        st = _urmnm_view_st()
        st.cards = python_list()
        st.later = ()
        st.mode = "story"
        st.sandbox = ()
        st.empty = u"The story line could not be read here."

    def _urmnm_story_read(keep=False):
        """Read the cards for the window: a frame's share now, the rest on
        the worker in slices (the walk ahead takes up to a second on a big
        game), the window saying it is reading till then; keep: the cards
        on show stay until the new ones are read (the speed plan: open at
        once, fill in; DECISIONS 2026-11-26 "Instant windows")."""

        import time
        st = _urmnm_view_st()
        _urm_work_cancel("story line")
        end = time.time() + _URM_WORK_SLICE
        try:
            steps = urmnm_model_steps()
            for said in steps:
                if isinstance(said, _URMSGDone):
                    urmnm_story_load(said.result)
                    return
                if time.time() >= end:
                    break
            else:
                urmnm_story_load(python_list())
                return
        except Exception as error:
            print("MRM: story line read failed (%s)" % (error,))
            _urmnm_story_failed()
            return
        if not keep:
            st.cards = python_list()
            st.later = ()
            st.mode = "story"
            st.sandbox = ()
            st.empty = _URMNM_READING
        _urm_work_slices("story line", lambda: _urmnm_story_job(steps), _urmnm_story_read_done, True)

    def _urmnm_story_job(steps):
        for said in steps:
            if isinstance(said, _URMSGDone):
                yield _URMWorkDone(said.result)
                return
            yield
        yield _URMWorkDone(python_list())

    def _urmnm_story_read_done(steps):
        if steps is None:
            _urmnm_story_failed()
        else:
            try:
                urmnm_story_load(steps)
            except Exception as error:
                print("MRM: story line read failed (%s)" % (error,))
                _urmnm_story_failed()
        renpy.restart_interaction()

    def _urmnm_stretch_job():
        """The worker's job while the pass is not done: a slice per step."""

        while not urmnm_stretch_done():
            urmnm_stretch_tick()
            yield
        yield _URMWorkDone()

    def urmnm_card_count():
        return len(_urmnm_view_st().cards or ())

    def urmnm_empty_text():
        return u"%s" % (_urmnm_view_st().empty or u"")

    def urmnm_has_caps():
        return bool(any(l.cap for c in (_urmnm_view_st().cards or ()) for l in c.lanes))

    def urmnm_legend_now(opened=()):
        return tuple(urmnm_legend(_urmnm_view_st().cards or (), opened))

    def urmnm_card_at(idx):
        cards = _urmnm_view_st().cards or ()
        if 0 <= idx < len(cards):
            return cards[idx]
        return None

    def urmnm_story_ready():
        return renpy.has_screen("urmnm_story")

    def urmnm_story_open():
        if not urmnm_story_ready():
            return
        st = _urmnm_view_st()
        st.tip = None
        st.stretch_done = _urmnm_stretch_is_done()
        if not st.stretch_done and _urm_work_state("story stretches") not in ("waiting", "running"):
            _urm_work_slices("story stretches", _urmnm_stretch_job)
        _urmnm_story_read()
        renpy.show_screen("urmnm_story", _layer=_urmi_layer)
        renpy.restart_interaction()

    def urmnm_story_close():
        if renpy.get_screen("urmnm_story", layer=_urmi_layer) is not None:
            renpy.hide_screen("urmnm_story", layer=_urmi_layer)
        _urm_work_cancel("story line")
        st = _urmnm_view_st()
        st.cards = None
        st.later = ()
        st.tip = None
        st.mode = "story"
        st.sandbox = ()
        renpy.restart_interaction()

    # Shown in the menu alongside Route map for side-by-side comparison.
    _URMNM_IN_MENU = True

    def _urmnm_in_menu():
        return _URMNM_IN_MENU and urmnm_story_ready()

    _urm_entry_add("story_line", "Story line", u"", urmnm_story_open,
                   shown=_urmnm_in_menu, key="alt_K_g", key_words="Alt+G",
                   group=1, order=11)

    # ---- its marks

    def urmnm_mark(size, kind):
        """A filled diamond: "big" (the game picks the way, amber) or
        "small" (only lines change, light grey)."""
        return Transform(Solid(urmk_colour("warn-ink" if kind == "big" else "ink-muted"), xysize=(size, size)),
                         rotate=45)

    def urmnm_short_mark(size):
        mark = Fixed(xysize=(size * 2, size * 2))
        inner = max(1, size - max(2, urmk_px_cut(4)))
        mark.add(Transform(Solid(urmk_colour("accent-ink"), xysize=(size, size)), rotate=45, align=(.5, .5)))
        mark.add(Transform(Solid(urmk_colour("surface"), xysize=(inner, inner)), rotate=45, align=(.5, .5)))
        return mark

    def urmnm_hold_short_mark():
        """The marker takes focus so its condition can be read."""
        return None

    def urmnm_short_tip_at():
        widget = renpy.display.focus.get_focused()
        action = getattr(widget, "action", None)
        return getattr(action, "callable", None) is urmnm_hold_short_mark

    def urmnm_others_words(n, other):
        """The fold under a version block: "2 other versions", "1 other
        version", or "3 versions" when none is lit."""
        return u"%d %sversion%s" % (n, u"other " if other else u"", u"" if n == 1 else u"s")

    def urmnm_fold_words(opened, n, other):
        """The block's fold link: what opens it, or "fold" while open."""
        return u"fold" if opened else urmnm_others_words(n, other)

    def urmnm_fold_icon(opened):
        return u"\ue5ce" if opened else u"\ue5cc"

    def urmnm_toggle(opened, at):
        return tuple(i for i in opened if i != at) if at in opened else tuple(opened) + (at,)

    def urmnm_legend(cards, opened=()):
        """The marks on screen, for the legend (UX 24): "big", "short",
        "faded" in that order; a folded version is not on screen."""
        found = python_list()
        if any(urmnm_check_split(c) for c in cards):
            found.append("big")
        if any(c.short_checks for c in cards):
            found.append("short")
        has_faded = any(
            r.faded for at, c in enumerate(cards) for i, r in enumerate(c.rows)
            if c.versions is None or at in opened or i == c.versions[1])
        if not has_faded:
            has_faded = any(p.faded for c in cards for p in getattr(c, "places", ()))
        if has_faded:
            found.append("faded")
        return found

    # A class of the store, made at load like every class of ours: a save
    # keeps the scope of the screen on show, and the block's ground is in it.
    class _URMNMDashed(renpy.display.core.Displayable):
        """A dashed edge drawn at whatever size it is given: the version
        block's ground."""

        def __init__(self, colour, width, dash, fill=None, **kwargs):
            super(_URMNMDashed, self).__init__(**kwargs)
            self.fill = fill
            self.colour = colour
            self.width = max(1, int(width))
            self.dash = max(2, int(dash))

        def render(self, w, h, st, at):
            w, h = int(w), int(h)
            rv = renpy.Render(w, h)
            t, d = self.width, self.dash
            if self.fill:
                rv.blit(renpy.render(Solid(self.fill), w, h, st, at), (0, 0))
            solid = Solid(self.colour)
            x = 0
            while x < w:
                n = min(d, w - x)
                piece = renpy.render(solid, n, t, st, at)
                rv.blit(piece, (x, 0))
                rv.blit(piece, (x, h - t))
                x += 2 * d
            y = 0
            while y < h:
                n = min(d, h - y)
                piece = renpy.render(solid, t, n, st, at)
                rv.blit(piece, (0, y))
                rv.blit(piece, (w - t, y))
                y += 2 * d
            return rv

    def urmnm_dashed():
        """The version block's ground (made once, kept in our memory)."""
        made = getattr(_urmnm_view_st(), "dashed", None)
        if made is None:
            made = _urmnm_view_st().dashed = _URMNMDashed(
                urmk_colour("set-ink"), urmk_px_cut(2), urmk_px_cut(6), urmk_colour("set-bg"))
        return made

    def urmnm_roam_ground():
        """The Free roam dashed frame ground (q2_free_roam panel b)."""
        made = getattr(_urmnm_view_st(), "roam_ground", None)
        if made is None:
            made = _urmnm_view_st().roam_ground = _URMNMDashed(
                urmk_colour("graph-line"), urmk_px_cut(2), urmk_px_cut(6), urmk_colour("surface"))
        return made

    # ---- the drawings' parts: a smooth line between two points, and where
    # a fork's lanes sit (research/newmap q1 panel b)

    class _URMNMCurve(renpy.display.core.Displayable):
        """A crisp anti-aliased Bezier curve from (x0, y0) to (x1, y1) inside a
        box of w x h, cached as an SDF PNG so every engine draws it smooth
        without segment gaps or endpoint blobs."""

        def __init__(self, w, h, x0, y0, x1, y1, colour, width, drop=False, **kwargs):
            super(_URMNMCurve, self).__init__(**kwargs)
            self.box = (int(w), int(h))
            self.ends = (x0, y0, x1, y1)
            self.colour = colour
            self.width = max(1, int(width))
            self.drop = bool(drop)

        def render(self, w, h, st, at):
            bw, bh = self.box
            rv = renpy.Render(bw, bh)
            if bw <= 0 or bh <= 0:
                return rv
            x0, y0, x1, y1 = self.ends
            if not self.drop and abs(y1 - y0) < 1:
                piece = renpy.render(Solid(self.colour), max(1, int(abs(x1 - x0))), self.width, st, at)
                rv.blit(piece, (int(min(x0, x1)), int(y0 - self.width // 2)))
                return rv
            cache = getattr(_urmnm_view_st(), "curves", None)
            if cache is None:
                cache = _urmnm_view_st().curves = python_dict()
            key = (bw, bh, int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1)),
                   self.colour, self.width, self.drop)
            img = cache.get(key)
            if img is None:
                img = _urmnm_curve_image(bw, bh, x0, y0, x1, y1, self.colour, self.width, self.drop, key)
                if len(cache) > 256:
                    cache.clear()
                cache[key] = img
            rv.blit(renpy.render(img, bw, bh, st, at), (0, 0))
            return rv

    def _urmnm_curve_image(bw, bh, x0, y0, x1, y1, colour, width, drop, key):
        import struct
        import zlib
        rgba = tuple(renpy.easy.color(colour))
        cr, cg, cb, ca = rgba
        half_w = width / 2.0
        # Match Solid(width) vertical rows [yc - width//2 .. yc - width//2 + width)
        odd_off = 0.5 if (width % 2 == 1) else 0.0
        yc0 = (int(y0) - width // 2) + half_w if not drop else max(half_w, float(y0))
        yc1 = (int(y1) - width // 2) + half_w
        if drop:
            cx0, cy0 = float(x0) + odd_off, yc1
            cx1, cy1 = float(x0) + odd_off, yc1
            sx0, sx1 = float(x0) + odd_off, float(x1)
        else:
            sx0, sx1 = float(x0), float(x1)
            cx0 = (sx0 + sx1) / 2.0
            cx1 = cx0
            cy0, cy1 = yc0, yc1
        pts = python_list()
        for k in range(49):
            s = k / 48.0
            om = 1.0 - s
            a, b, c, d = om * om * om, 3.0 * om * om * s, 3.0 * om * s * s, s * s * s
            pts.append((a * sx0 + b * cx0 + c * cx1 + d * sx1,
                        a * yc0 + b * cy0 + c * cy1 + d * yc1))
        segs = python_list()
        pad = half_w + 1.5
        for k in range(48):
            ax, ay = pts[k]
            bx, by = pts[k + 1]
            dx, dy = bx - ax, by - ay
            l2 = dx * dx + dy * dy
            if l2 <= 1e-6:
                continue
            segs.append((ax, ay, dx, dy, l2,
                         min(ax, bx) - pad, max(ax, bx) + pad,
                         min(ay, by) - pad, max(ay, by) + pad))
        zero_row = b"\x00" + (b"\x00\x00\x00\x00" * bw)
        rows = bytearray()
        y_lo = max(0, int(min(yc0, yc1) - pad - 1))
        y_hi = min(bh, int(max(yc0, yc1) + pad + 2))
        import math
        for j in range(bh):
            if j < y_lo or j >= y_hi:
                rows.extend(zero_row)
                continue
            py = j + 0.5
            active = python_list(s for s in segs if s[7] <= py <= s[8])
            if not active:
                rows.extend(zero_row)
                continue
            rows.append(0)
            for i in range(bw):
                px = i + 0.5
                best = 1e9
                for ax, ay, dx, dy, l2, x_a, x_b, _ya, _yb in active:
                    if px < x_a or px > x_b:
                        continue
                    t = ((px - ax) * dx + (py - ay) * dy) / l2
                    if t < 0.0:
                        t = 0.0
                    elif t > 1.0:
                        t = 1.0
                    rx = px - (ax + t * dx)
                    ry = py - (ay + t * dy)
                    d2 = rx * rx + ry * ry
                    if d2 < best:
                        best = d2
                if best >= pad * pad:
                    rows.extend((0, 0, 0, 0))
                else:
                    cov = min(1.0, max(0.0, half_w + 0.5 - math.sqrt(best)))
                    a_byte = int(round(ca * cov))
                    rows.extend((cr, cg, cb, a_byte))
        def chunk(kind, data):
            body = kind + data
            return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)
        png = (bytes(bytearray((137, 80, 78, 71, 13, 10, 26, 10)))
               + chunk(b"IHDR", struct.pack(">IIBBBBB", bw, bh, 8, 6, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(bytes(rows))) + chunk(b"IEND", b""))
        return renpy.display.im.Data(png, "urmnm_curve_%s.png" % (abs(hash(key)),))

    def urmnm_check_split(card):
        """A check the game decides whose ways stay apart: drawn as its
        labelled diamond and a box per way, no card (the user's shape
        rules, 2026-11-23)."""
        return (not card.numbered and card.versions is None and card.mark == "big"
                and any(lane.cap is None for lane in card.lanes))

    def urmnm_staying_rows(card):
        """The ways of a card that stay on the line (no lane of their own)."""
        taken = python_set(lane.at for lane in card.lanes)
        return python_list(row for at, row in enumerate(card.rows) if at not in taken)

    def urmnm_check_label(card):
        """What the diamond at a check's split says: its first test in plain
        words."""
        return card.rows[0].words if card.rows else u""

    def urmnm_lane_words(card, lane):
        """A lane box: its length; on a check, the way's test first."""
        lines = lane.lines or u"a long way"
        if card.numbered and lane.at is not None:
            return u"%d \u00b7 %s" % (lane.at + 1, lines)
        if card.numbered or not lane.words:
            return lines
        return u"%s \u00b7 %s" % (lane.words, lines)

    def _urmnm_first_line(node, steps=12):
        """The first line said at a meeting point, in the game's own words,
        quoted and cut short (the user's landmark box); None when it cannot
        be read straight on (a choice, a check or a jump comes first)."""
        at = node
        for _i in range(steps):
            if at is None:
                return None
            if isinstance(at, renpy.ast.Translate) and getattr(at, "block", None):
                # Older engines keep each said line inside its translation block.
                at = at.block[0]
            if isinstance(at, renpy.ast.Say):
                said = _urmp_plain(_urm_player_text(at.what), 48)
                return (u"\u201c%s\u201d" % said) if said else None
            if not isinstance(at, (renpy.ast.Label, renpy.ast.Pass)):
                return None
            at = getattr(at, "next", None)
        return None

    def urmnm_lane_chips(card, lane):
        """What a way that leaves the line gains or loses, on its curve's
        label (its row's chips)."""
        if lane.at is None or lane.at >= len(card.rows):
            return ()
        return card.rows[lane.at].chips

    def urmnm_fork_w(card, size):
        """The widest box on a card's lanes, as the engine sizes its words
        and chips, so a wide box never runs into the card (UX 22)."""
        pad = urmk_px_cut(24)
        stand_w = urmnm_text_w(u"as things stand", size) + pad
        widest = 0
        for lane in card.lanes:
            if lane.cap is not None and card.numbered:
                continue
            w = urmnm_text_w(urmnm_cap_words(card, lane) if lane.cap else urmnm_lane_words(card, lane), size) + pad
            if lane.cap is None:
                for chip in urmnm_lane_chips(card, lane):
                    w += urmnm_text_w(chip[0], size) + pad
                if lane.lit:
                    w += stand_w
            widest = max(widest, w)
        for row in urmnm_staying_rows(card):
            w = urmnm_text_w(row.words, size) + pad
            if row.lit:
                w += stand_w
            widest = max(widest, w)
        return widest

    def urmnm_fork_h(card, base_h, gap):
        """Vertical height for a card's fork box so 3+ lanes never clip."""
        back = [lane for lane in card.lanes if lane.cap is None or not card.numbered]
        tiers = (len(back) + 1) // 2
        if not tiers:
            return int(base_h)
        half = tiers * int(gap) + urmk_px_cut(36)
        needed = 2 * half
        return int(needed) if needed > int(base_h) else int(base_h)

    def urmnm_text_w(words, size):
        """The width the engine gives these words (UX 22: a size is asked)."""
        try:
            return int(Text(words, style="urmk_text", size=size, substitute=False).size()[0])
        except Exception:
            return int(len(words) * size * 0.55)

    def urmnm_card_ground(game):
        """A card's ground: a choice's plain; a split the game decides
        edged in the big diamond's amber (UX 12: it looks different)."""
        st = _urmnm_view_st()
        made = getattr(st, "grounds", None)
        if made is None:
            r = urmk_px_cut(10)
            made = st.grounds = (urmk_pill(urmk_colour("surface-2"), r),
                                 Fixed(urmk_pill(urmk_colour("surface-2"), r), urmk_ring(urmk_colour("warn-ink"), r, max(1, urmk_px_cut(2)))))
        return made[1 if game else 0]

    def urmnm_curve(w, h, x0, y0, x1, y1, colour, width, drop=False):
        return _URMNMCurve(w, h, x0, y0, x1, y1, colour, width, drop=drop)

    def urmnm_lane_rows(card, height, gap):
        """Where a card's fork puts each lane that comes back: (lane, y) with
        y its centre in a box `height` tall whose middle is the line; the
        ways that stay keep the middle, the lanes go above and below it in
        turn."""

        # A choice's ending ways drop under its card; the game's own fan out
        # here with the ways that come back.
        back = [lane for lane in card.lanes if lane.cap is None or not card.numbered]
        out = python_list()
        mid = height // 2
        for at, lane in enumerate(back):
            step = (at // 2 + 1) * gap
            out.append((lane, mid - step if at % 2 == 0 else mid + step))
        return out

    def urmnm_cap_words(card, lane):
        """A red drop's words, naming the way it is: "3 · game over" on a
        choice (its option's number), "Otherwise · game over" on a check."""
        # The reader cannot tell a loss from a good ending (12: "end" is any
        # `return` that ends the game): the words stay neutral.
        said = u"the game ends" if lane.cap == "end" else u"never meets again"
        if lane.at is None:
            return said
        if card.numbered:
            return u"%d \u00b7 %s" % (lane.at + 1, said)
        words = card.rows[lane.at].words if lane.at < len(card.rows) else None
        if not words:
            return said
        words = words if len(words) <= 28 else words[:27] + u"\u2026"
        return u"%s \u00b7 %s" % (words, said)
