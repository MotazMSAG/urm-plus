    # ------------------------------------------------------------------
    # The variable sheet: what the user picked on 2026-11-19 (A, a ladder;
    # C, the story line behind a click) and on 2026-11-22 (c, our own sheet:
    # the ladder as a slider), worked out from what the panel already read -
    # nothing here reads the script again.
    #
    #   * rungs: one per value the game checks. A number's rung is coloured
    #     by reach (approved the same day): gain - playing can still get
    #     there with picks to spare; warn - only by taking every pick left
    #     that raises (or lowers) it; loss - no pick left gets there, only a
    #     change by hand. None when a write ahead cannot be read, so the
    #     window never colours on a guess (UX rule 21).
    #     The reach itself is a core fact (_urm_reach, 14_facts).
    #   * the story line: every place the story gives the value, played
    #     first, then "you are here", then what is still ahead. Story order
    #     across scenes is not knowable from the script, so within each part
    #     it is line order only.
    #   * one verdict, one count of lines (idea 11: the size of a place is
    #     _urmp_weight everywhere, a jump's target counted in).
    #
    # The screen draws these; the layout is the user's pick.
    # ------------------------------------------------------------------

    class _URMPRung(python_object):
        def __init__(self, words, value, sort):
            self.words = words            # "5 or more", "ON", '"flirt"'
            self.value = value            # what a click puts in the box, or _URMP_NOSET
            self.sort = sort              # the number, for a ladder
            self.title = None             # the first spoken line of its biggest place
            self.lines = 0                # how much that place plays
            self.holds = None             # True / False / None (not known) at the value now
            self.reach = None             # "gain" / "warn" / "loss" / None
            self.ahead = 0                # its places still ahead
            self.checks = python_list()   # its places, biggest first
            self.big = None               # the biggest place: title, Code, Replay

    class _URMPStep(python_object):
        def __init__(self, kind, words, chips, status):
            self.kind = kind              # "give" or "here"
            self.words = words            # '"Kiss her"', "The game itself", "you are here"
            self.chips = chips            # [(words, tone)]
            self.status = status          # "played", "picked", "here", "screen", "ahead"

    def _urmp_chip(w):
        """(words, tone) for what one write does, without the name: the
        window is about one value, so its chips read +1, ON, = "flirt"."""

        op, value = w.op, w.value
        ok = _urm_value_ok(w)
        if op in ("+=", "-=") and ok and _urm_isnum(value):
            delta = value if op == "+=" else -value
            if delta >= 0:
                return (u"+%s" % _urmi_show(delta), "gain")
            return (u"\u2212%s" % _urmi_show(-delta), "loss")
        if op == "=" and ok:
            if value is True:
                return (u"true", "set")
            if value is False:
                return (u"false", "set")
            return (u"= %s" % _urmp_plain(_urmi_show(value), 30), "set")
        return (u"changes", "other")

    def _urmp_holds(rows, name, now):
        """Whether the value now meets this rung's own part of the test."""

        if now is _URMP_UNK or not rows:
            return None
        _tree, mine, _others = _urmp_atoms(rows[0].cond, name)
        if not mine:
            return None
        found = True
        for atom in mine:
            got = _urmp_ev(atom, name, now)
            if got is False:
                return False
            if got is not True:
                found = None
        return found

    def _urmp_rung(words, value, sort, rows, name, now):
        g = _URMPRung(words, value, sort)
        rows = sorted(rows, key=lambda r: (_URMP_STATUS_RANK.get(r.status, 4), -r.weight))
        g.checks = rows
        g.ahead = len([r for r in rows if r.status in _URM_AHEAD])
        if rows:
            big = max(rows, key=lambda r: r.weight)
            g.big = big
            g.lines = big.weight
            if big.summary.first:
                g.title = big.summary.first
            elif big.kind == "option":
                g.title = u'the choice "%s" appears' % _urmp_plain(big.option, 60)
        g.holds = _urmp_holds(rows, name, now)
        return g

    def _urmp_window(p, name, now, mode, shown_rows, menus, menu_order, auto,
                     current_menu, seen, overwritten):
        """Fill p.win_*: the rungs, the story line, the verdict, the choice on screen."""

        ups, downs, unreadable = _urm_picks(menus, menu_order, auto, current_menu)

        # --- rungs
        rungs = python_list()
        if mode == "bool":
            on_value, off_value = (1, 0) if _urmp_isint(now) else (True, False)
            for side, words, value in (("on", u"true", on_value), ("off", u"false", off_value)):
                rows = [r for r in shown_rows if getattr(r, "side", None) == side]
                g = _urmp_rung(words, value, None, rows, name, now)
                g.holds = None if now is _URMP_UNK else bool(now) == (side == "on")
                rungs.append(g)
        elif mode in ("number", "value"):
            # One rung per requirement: "5 or more", "exactly 2", "flirt".
            # A threshold written against another value ("hard - 25") is
            # worked out with that value as it is now; its rung keeps the
            # number only.
            groups = python_dict()
            order = python_list()
            for r in shown_rows:
                words, value, sort = _urmp_requirement(r, name, now)
                words = words.split(u" (with ", 1)[0]
                if words not in groups:
                    groups[words] = (value, sort, python_list())
                    order.append(words)
                groups[words][2].append(r)
            if mode == "number":
                order.sort(key=lambda k: (groups[k][1] is None,
                                          groups[k][1] if groups[k][1] is not None else 0,
                                          0 if k.startswith("exactly") else 1, k))
            for words in order:
                value, sort, members = groups[words]
                g = _urmp_rung(words, value, sort, members, name, now)
                if mode == "number":
                    if g.holds:
                        g.reach = "gain"
                    elif g.holds is False and _urm_isnum(now) and _urm_isnum(g.value):
                        g.reach = _urm_reach(g.value - now, ups, downs, unreadable)
                rungs.append(g)
        p.win_rungs = rungs

        # --- the story line: who gives it
        played = python_list()
        ahead = python_list()
        for m in menu_order:
            g = menus[id(m)]
            on_screen = m is current_menu
            for w in g:
                step = _URMPStep("give", u'"%s"' % _urmp_plain(w.option, 50), [_urmp_chip(w)], "")
                if on_screen:
                    step.status = "screen"
                    ahead.append((0, w.file or "", w.line, step))
                elif w.status in _URM_AHEAD:
                    step.status = "ahead"
                    ahead.append((1, w.file or "", w.line, step))
                elif w.status in _URM_BEHIND:
                    if seen.picked(m, w.option) is not True:
                        continue
                    step.status = "picked"
                    played.append((w.file or "", w.line, step))
        for w in auto:
            step = _URMPStep("give", u"The game itself", [_urmp_chip(w)], "")
            if w.status in _URM_AHEAD:
                step.status = "ahead"
                ahead.append((1, w.file or "", w.line, step))
            elif w.status in _URM_BEHIND:
                step.status = "played"
                played.append((w.file or "", w.line, step))
        played.sort(key=lambda t: (t[0], t[1]))
        ahead.sort(key=lambda t: (t[0], t[1], t[2]))
        story = python_list(t[-1] for t in played)
        here = _URMPStep("here", u"you are here", python_list(), "here")
        here.now = now
        story.append(here)
        story.extend(t[-1] for t in ahead)
        p.win_story = story

        # --- the choice on screen
        p.win_now = python_list()
        if current_menu is not None:
            mine = menus.get(id(current_menu)) or ()
            for item in current_menu.items:
                label, cond, block = item[0], item[1], item[2]
                if block is None:
                    continue
                chips = [_urmp_chip(w) for w in mine if w.option == label]
                p.win_now.append((_urmp_plain(label, 50), chips))

        # --- one verdict
        ahead_rows = [r for r in shown_rows if r.status in _URM_AHEAD]
        behind = [r for r in shown_rows if r.status in _URM_BEHIND]
        if ahead_rows and overwritten:
            p.win_verdict = (u"Set again before it matters", "loss")
        elif ahead_rows:
            n = len(ahead_rows)
            p.win_verdict = (u"Still matters \u00b7 %d ahead" % n, "gain")
        elif behind and len(behind) == len(shown_rows):
            p.win_verdict = (u"Too late \u00b7 only on a replay", "warn")
        elif shown_rows:
            n = len(shown_rows)
            p.win_verdict = (u"Checked in %d place%s" % (n, "" if n == 1 else "s"), "other")
        else:
            p.win_verdict = (u"Does nothing in the story", "other")

    # ------------------------------------------------------------------
    # What the sheet calls (our own sheet, drawing c, picked 2026-11-22:
    # the ladder as a slider; game_screens/74_var_sheet.rpy). It takes a
    # name and asks these: each hands back plain values only (words,
    # numbers, tuples and lists of them), so a screen that keeps them
    # keeps none of our objects - a save holds a shown screen's scope, and
    # a save must load without URM+. What the player has picked or typed
    # lives in our memory (_urmp_bucket("ui")), never in a save.
    # ------------------------------------------------------------------

    _URMP_REACH_WORDS = python_dict((
        ("gain", u"Reachable by playing"),
        ("warn", u"Only with every pick left"),
        ("loss", u"Only by changing it here"),
    ))

    # The ladder, at 1080 lines: the knob, the room between two values to
    # scale and evenly spaced, the most whole numbers drawn to scale.
    URMI_LADDER = (40, 56, 64, 12)

    # Keys the open box lets through to the story (an older engine's Input
    # passes them): skip, rollback, roll forward. The sheet takes them.
    URMI_BOX_KEYS = ("K_TAB", "K_PAGEUP", "repeat_K_PAGEUP", "K_PAGEDOWN", "repeat_K_PAGEDOWN")

    def urmi_sheet_title(name):
        """The sheet's title: a variable's name or a flag's word, said
        plainly the same way (carol_love -> Carol love)."""

        rec = _urmfl_record(name)
        return _urmm_pretty(_urmi_safe(rec.word) if rec is not None else name)

    def urmi_kind(name, flag=False):
        """What the value is, for what the sheet offers: "flag", "bool",
        "int", "float", "text", "other" (a list, an object, None: shown,
        not set) or "unknown" (not there, or not readable)."""

        if flag:
            return "flag"
        now = _urmp_value(name)
        if now is _URMP_UNK:
            return "unknown"
        if isinstance(now, bool):
            return "bool"
        if _urm_isnum(now):
            return "float" if isinstance(now, float) else "int"
        if isinstance(now, _urmi_text):
            return "text"
        return "other"

    def urmi_value_words(value, kind=None):
        """A value as the sheet says it: true or false for booleans, a number
        as itself, words in quotes."""

        if value is _URMP_UNK:
            return u"?"
        if kind in ("flag", "bool") or isinstance(value, bool):
            return u"true" if value else u"false"
        if _urm_isnum(value):
            return _urm_number(value)
        return _urmp_plain(_urmi_show(value), 40)

    def urmi_now_words(name, flag=False):
        return urmi_value_words(_urmp_value(name), urmi_kind(name, flag))

    # ---- the sheet beside what asked for it (the user's 4a: a card's stat
    # chip opens it beside the card), through the doorway's value viewer

    URMI_SHEET_W = 560          # the sheet's maximum width at 1080 lines
    URMI_SHEET_EDGE = 16        # its gap to the screen's edge, and to what asked

    def urmi_sheet_place(beside, width, sheet, gap, off=None):
        """Left edge of the fitted panel, in pixels. Prefer left of the
        card, then right, then the usual bottom-right corner."""

        if beside:
            left, right = beside
            if left - gap - sheet >= gap:
                return left - gap - sheet
            if right + gap + sheet <= width - gap:
                return right + gap
        return max(gap, width - sheet - (gap if off is None else off))

    def urmi_sheet_room():
        """The available width inside the panel and its screen margins."""
        pad = urmk_px(URMI_SHEET_EDGE) * 2
        return max(1, min(urmk_px(URMI_SHEET_W), config.screen_width - pad) - pad)

    # Place after layout so the card's left/right choice and the popup's
    # bounds use the dimensions Ren'Py actually drew. Position forwards
    # render and events to its child as usual.
    try:
        _URMISheetPositionBase = renpy.display.layout.Position
    except AttributeError:
        _URMISheetPositionBase = python_object

    class _URMISheetPosition(_URMISheetPositionBase):
        def __init__(self, child, coordinates):
            super(_URMISheetPosition, self).__init__(child, style="urmk_frame")
            self.coordinates = coordinates

        def place(self, dest, x, y, width, height, surf, main=True):
            dx, dy = self.coordinates(width, height, surf.width, surf.height)
            pos = (x + dx, y + dy)
            if dest is not None:
                dest.blit(surf, pos, main, main)
            return pos

    def urmi_sheet_anchor(beside, off):
        gap = urmk_px(URMI_SHEET_EDGE)
        offset = None if off is None else urmk_px(off)

        def coordinates(width, height, w, h):
            return (urmi_sheet_place(beside, width, w, gap, offset), height - gap - h)

        return lambda child: _URMISheetPosition(child, coordinates)

    def urmi_sheet_popup(top, beside, off):
        def coordinates(width, height, w, h):
            gap = urmk_px(URMI_SHEET_EDGE)
            sw = config.screen_width
            left = urmi_sheet_place(beside, sw, width, gap, None if off is None else urmk_px(off))
            # Usually below the header. On a very short sheet, open above
            # it, leaving the same header icon available to close the menu.
            y = top if top + h <= height + gap else -h - urmk_px(4)
            return (max(gap - left, width - urmk_px(24) - w), y)

        return lambda child: _URMISheetPosition(child, coordinates)

    def urmi_sheet_header(title, page, room):
        icon, spacing = urmk_px(40), urmk_px(4)
        buttons = 6 * icon + 5 * spacing
        back = icon + urmk_px(8) if page else 0
        compact = room < buttons + urmk_px(48)
        title_room = max(1, room - back - (0 if compact else buttons + urmk_px(8)))
        # The bold kit style gives a conservative fit for the existing
        # medium-weight heading, including at larger text settings.
        w = urmk_text_width(title, "urmk_l") + back
        minimum = max(buttons, w) if compact else w + buttons + urmk_px(8)
        height = urmk_px(48)
        if compact:
            per_row = max(1, (room + spacing) // max(1, icon + spacing))
            rows = (6 + per_row - 1) // per_row
            height = max(icon, urmk_px(URMK_TEXT["l"][1] * urmk_look.text)) + urmk_px(8) + rows * icon
        return int(min(room, minimum)), compact, title_room, height

    def urmi_fit_line(words, room, style):
        """Keep a one-line label clear of the buttons beside it."""

        if urmk_text_width(words, style) <= room:
            return words
        lo, hi = 0, max(0, len(words) - 4)
        while lo < hi:
            n = (lo + hi + 1) // 2
            if urmk_text_width(urmi_cut(words, n + 3), style) <= room:
                lo = n
            else:
                hi = n - 1
        return urmi_cut(words, lo + 3)

    def urmi_ladder_width(rows):
        w = 0
        for _y, number, _tone, words, _muted, rung, _value, ahead in rows:
            one = max(urmk_px(32), urmk_text_width(number, "urmk_m_medium"))
            if ahead:
                one += urmk_px(20) + urmk_px(12)  # the rotated diamond
            if words:
                one += urmk_text_width(urmi_row_words(words), "urmk_m") + urmk_px(12)
            if rung is not None:
                one += urmk_text_width(u"\ue5cc", "urmk_icon") + urmk_px(8)
            w = max(w, one)
        return int(w + urmk_px(URMI_LADDER[0]) + urmk_px(8) + 2 * urmk_px(8))

    def urmi_sheet_beside(name, beside=None):
        """Show the sheet of `name` on our layer, beside (left, right)."""

        if renpy.has_screen("urmi_sheet_at"):
            urmi_sheet_reset(name)
            renpy.show_screen("urmi_sheet_at", name=name, beside=beside, _layer=_urmi_layer)

    _urm_value_viewer_add(urmi_sheet_beside)

    def urmi_sheet_reset(name):
        """A sheet opens on its first page, with nothing picked or typed."""

        ui = _urmp_bucket("ui")
        for key in (("rung", name), ("preview", name), ("more", name),
                    ("delete", name), ("box", name), ("box_error", name), ("set", name)):
            ui.pop(key, None)

    def urmi_rung(p, index):
        """The rung the sheet is turned to, or None."""

        if index is None or not (0 <= index < len(p.win_rungs)):
            return None
        return p.win_rungs[index]

    def urmi_open_page(name, index):
        """A rung's story line, or (None) back to the sheet's first page."""

        ui = _urmp_bucket("ui")
        ui[("rung", name)] = index
        ui.pop(("more", name), None)
        renpy.restart_interaction()

    # ---- the ladder

    def _urmp_whole(value):
        return _urm_isnum(value) and not isinstance(value, float)

    def _urmp_slots(p, now):
        """The values the knob stops at, lowest first, and whether they are
        drawn to scale. Every whole number from the bottom to the top when
        there are URMI_LADDER[3] or fewer; else only the values that mean
        something - each rung, the value now and the two ends - evenly
        spaced (money 0 to 10,000: the user's pick, 2026-11-22). The bottom
        is 0 or lower; the top a step above the highest rung or the value
        now, a quarter of the way again for a whole number."""

        vals = python_list(g.sort for g in p.win_rungs if _urm_isnum(g.sort))
        if _urm_isnum(now):
            vals.append(now)
        if p.mode != "number" or not vals:
            return python_list(), False
        lo = min(vals + [0])
        hi = max(vals)
        if all(_urmp_whole(v) for v in vals):
            hi = hi + max(1, (hi - lo) // 4)
            if hi - lo + 1 <= URMI_LADDER[3]:
                return python_list(range(lo, hi + 1)), True
        else:
            hi = hi + max(1, (hi - lo) / 4.0)
        found = python_list()
        for v in sorted(vals + [lo, hi]):
            if not found or v != found[-1]:
                found.append(v)
        return found, False

    def _urmp_slot_of(slots, value):
        """The slot a value sits at: its own, or the nearest below it (the
        lowest for a value under every slot)."""

        best = 0
        for i, v in enumerate(slots):
            if v <= value:
                best = i
        return best

    def urmi_preview(name):
        """The value the player is looking at before Set, or _URMP_UNK."""

        ui = _urmp_bucket("ui")
        if ("preview", name) not in ui:
            return _URMP_UNK
        return ui[("preview", name)]

    def urmi_preview_set(name, value):
        """Look at a value before setting it: the knob, a rung, a side."""

        ui = _urmp_bucket("ui")
        if value == _urmp_value(name) and type(value) is type(_urmp_value(name)):
            ui.pop(("preview", name), None)
        else:
            ui[("preview", name)] = value
        ui.pop(("box", name), None)
        ui.pop(("more", name), None)
        renpy.restart_interaction()

    def urmi_preview_clear(name):
        _urmp_bucket("ui").pop(("preview", name), None)
        renpy.restart_interaction()

    def urmi_ladder(name):
        """The ladder as the screen draws it: (height, rows, track, knob)
        at this game's size, or None when the value is no number on a
        ladder. rows: (y of its middle, the number, its tone or None, words,
        muted, the rung to open or None, the value) top to bottom; track:
        (top, bottom) of the line; knob: (y, from y, to y) - where it
        stands, and the lit stretch from the value now to it."""

        p = urm_panel(name)
        now = _urmp_value(name)
        slots, _scale = _urmp_slots(p, now)
        if len(slots) < 2 or not _urm_isnum(now):
            return None
        knob, scaled, even, _most = URMI_LADDER
        step = urmk_px(scaled if _scale else even)
        k = urmk_px(knob)
        n = len(slots)
        height = k + (n - 1) * step

        def y_of(i):
            return k // 2 + (n - 1 - i) * step

        at = python_dict()
        for i, g in enumerate(p.win_rungs):
            if _urm_isnum(g.sort):
                at.setdefault(_urmp_slot_of(slots, g.sort), python_list()).append(i)
        here = _urmp_slot_of(slots, now)
        rows = python_list()
        for i in range(n - 1, -1, -1):
            value = slots[i]
            rungs = at.get(i) or ()
            if rungs:
                gs = [p.win_rungs[j] for j in rungs]
                ahead = any(g.ahead for g in gs)
                tone = gs[0].reach if ahead else None
                words = u" \u00b7 ".join(urmi_rung_words(p, g) for g in gs)
                if i == here and slots[i] == now:
                    words += u" \u00b7 you are here"
                rows.append((y_of(i), _urm_number(value), tone, words, not ahead,
                             rungs[0], value, ahead))
            elif i == here and slots[i] == now:
                rows.append((y_of(i), _urm_number(value), None, u"you are here", True,
                             None, value, False))
            elif i in (0, n - 1):
                rows.append((y_of(i), _urm_number(value), None, u"", True, None, value, False))
        shown = urmi_preview(name)
        to = _urmp_slot_of(slots, shown) if _urm_isnum(shown) else here
        return (height, rows, (k // 2, height - k // 2), (y_of(to), y_of(here), y_of(to)))

    def urmi_rung_words(p, g):
        """What a rung of the ladder says: the first line of its biggest
        place, or what it asks; "exactly 2" or "4 or less" said in full, so
        it is never read as a step to climb to."""

        words = g.title or u""
        if p.mode == "number" and not g.words.endswith(u" or more"):
            return (g.words + u" \u00b7 " + words) if words else g.words
        return words or g.words

    _urmp_knob_kind = python_list()

    def _urmp_knob_class():
        """The ladder's knob, a bar's value: where it stands is the value
        looked at; a drag or a click on the bar looks at the slot nearest.
        Made anew at each draw, never kept by a screen (so no save holds
        one). The class is made when first asked for: the engine's BarValue
        is not there when a test reads the pieces alone."""

        if _urmp_knob_kind:
            return _urmp_knob_kind[0]

        class _URMPKnob(BarValue):
            def __init__(self, name, slots, index):
                self.name = name
                self.slots = tuple(slots)
                self.index = index

            def __eq__(self, other):
                return isinstance(other, _URMPKnob) and (self.name, self.slots) == (other.name, other.slots)

            def __ne__(self, other):
                return not self.__eq__(other)

            def __hash__(self):
                return hash((self.name, self.slots))

            def changed(self, value):
                i = int(round(value))
                if 0 <= i < len(self.slots) and self.slots[i] != urmi_preview(self.name):
                    urmi_preview_set(self.name, self.slots[i])

            def get_adjustment(self):
                return ui.adjustment(range=float(len(self.slots) - 1), value=float(self.index),
                                     step=1.0, page=0.0, changed=self.changed)

            def get_style(self):
                return "bar", "vbar"

        _urmp_knob_kind.append(_URMPKnob)
        return _URMPKnob

    def urmi_knob(name):
        """The knob of the ladder of `name` (a bar's value)."""

        p = urm_panel(name)
        now = _urmp_value(name)
        slots, _scale = _urmp_slots(p, now)
        shown = urmi_preview(name)
        return _urmp_knob_class()(name, slots, _urmp_slot_of(slots, shown if _urm_isnum(shown) else now))

    # ---- looking at a value before Set

    def _urmp_flips(p, name, now, value):
        """[(words, tone, rung)] for each rung with places still ahead whose
        answer the value flips: green "opens", red "closes"."""

        out = python_list()
        for i, g in enumerate(p.win_rungs):
            if not g.ahead:
                continue
            if p.mode == "bool":
                before = None if now is _URMP_UNK else bool(now) == (g.words == u"true")
                after = bool(value) == (g.words == u"true")
            else:
                before = _urmp_holds(g.checks, name, now)
                after = _urmp_holds(g.checks, name, value)
            what = _urmp_plain(urmi_rung_words(p, g), 44)
            if after is True and before is not True:
                out.append((u"opens " + what, "gain", i))
            elif after is False and before is True:
                out.append((u"closes " + what, "loss", i))
        return out

    def urmi_looking(name):
        """What the sheet says while the player looks at a value before Set:
        (its words, [(chip words, tone, rung)], the value), or None."""

        value = urmi_preview(name)
        if value is _URMP_UNK:
            return None
        p = urm_panel(name)
        chips = _urmp_flips(p, name, _urmp_value(name), value)
        if not chips:
            chips = python_list(((u"nothing ahead changes", "plain", None),))
        return (urmi_value_words(value, p.mode == "bool" and "bool" or None), chips, value)

    def urmi_sides(name):
        """A yes/no value's two sides, or a text value's values: [(words,
        how many places, lit, the rung, the value or None)], the side that
        holds now lit; looked at, the one looked at lit instead."""

        p = urm_panel(name)
        if p.mode not in ("bool", "value"):
            return python_list()
        looking = urmi_preview(name)
        out = python_list()
        for i, g in enumerate(p.win_rungs):
            value = g.value if g.value is not _URMP_NOSET else None
            if looking is not _URMP_UNK:
                lit = value is not None and value == looking and type(value) is type(looking)
                if p.mode == "bool":
                    lit = bool(looking) == (g.words == u"true")
            else:
                lit = bool(g.holds)
            n = len(g.checks)
            out.append((g.words, u"%d place%s" % (n, "" if n == 1 else "s"), lit, i, value))
        return out

    def urmi_settable(name, flag, value):
        """Whether Set can put this value in (a flag takes ON or OFF)."""

        kind = urmi_kind(name, flag)
        if value is None or value is _URMP_NOSET or value is _URMP_UNK:
            return False
        if kind in ("flag", "bool"):
            return value in (True, False, 0, 1)
        if kind in ("int", "float"):
            return _urm_isnum(value)
        if kind == "text":
            return isinstance(value, _urmi_text)
        return False

    # ---- setting it: our own, through the core's reading of a name

    def _urmp_place(name):
        """(what holds it, "a" or "i", attribute or key) for a name the
        sheet can set: a store name, an attribute or an item of what a name
        holds (mc.money, stats["love"]). None when it cannot be followed."""

        node = _urmp_parse(name)
        ast = _urmi_ast
        if isinstance(node, ast.Name):
            return (renpy.store, "a", node.id)
        if isinstance(node, ast.Attribute):
            owner = _urmp_ev(node.value)
            return None if owner is _URMP_UNK else (owner, "a", node.attr)
        if isinstance(node, ast.Subscript):
            owner = _urmp_ev(node.value)
            key = node.slice
            if type(key).__name__ == "Index":
                key = key.value
            key = _urmp_ev(key)
            if owner is _URMP_UNK or key is _URMP_UNK:
                return None
            return (owner, "i", key)
        return None

    def urmi_set(name, value):
        """Put a value in, as the game's own code would (so rollback has
        it). Words for what went wrong, or None."""

        place = _urmp_place(name)
        if place is None:
            return u"This value cannot be changed from here"
        owner, how, key = place
        old = _urmp_value(name)
        try:
            if how == "a":
                setattr(owner, key, value)
            else:
                owner[key] = value
        except Exception as error:
            return _urmp_plain(u"The game refused it: %s" % (error,), 100)
        # A save made at once has it; a frozen name holds it (the core).
        _urm_after_set(name)
        ui = _urmp_bucket("ui")
        for k in (("preview", name), ("box", name), ("box_error", name)):
            ui.pop(k, None)
        ui[("set", name)] = (old, value)
        renpy.restart_interaction()
        return None

    def urmi_snapped(name):
        """Words when the game put back a value the player set here (a value
        something keeps fixed comes back at the next line): never a quiet
        undo. None while the value set holds, and for good once the story
        moves it on to anything else."""

        ui = _urmp_bucket("ui")
        found = ui.get(("set", name))
        if found is None:
            return None
        old, new = found
        now = _urmp_value(name)
        if now == new and type(now) is type(new):
            return None
        if now == old and type(now) is type(old):
            return u"The game put this back to %s" % urmi_value_words(old)
        ui.pop(("set", name), None)
        return None

    def urmi_commit(name):
        """Set: the value looked at goes in."""

        value = urmi_preview(name)
        if value is _URMP_UNK:
            return
        urmi_set(name, value)

    def urmi_deletable(name, flag=False):
        return not flag and _urmp_place(name) is not None and urmi_kind(name) != "unknown"

    def urmi_delete(name):
        """Delete the variable from the game (More, asked twice)."""

        place = _urmp_place(name)
        if place is None:
            return
        owner, how, key = place
        try:
            if how == "a":
                delattr(owner, key)
            else:
                del owner[key]
        except Exception as error:
            print("MRM: could not delete %s (%s)" % (name, error))
        renpy.restart_interaction()

    # ---- the type-in box: a click on the value (Search's box, on the kit)

    def urmi_box(name):
        """The words typed into the sheet's box (an InputValue): Enter sets
        them, and is taken here, so it never reaches the story behind. One
        per name and run, kept in our memory, never by a screen. Its class
        is made when first asked for, as the knob's is."""

        found = _urmp_bucket("boxes").get(name)
        if found is not None:
            return found

        class _URMPBox(InputValue):
            default = True
            editable = True

            def __init__(self, name):
                self.name = name

            def get_text(self):
                return urmi_ui(("box", self.name)) or u""

            def set_text(self, words):
                ui = _urmp_bucket("ui")
                ui[("box", self.name)] = words
                ui.pop(("box_error", self.name), None)
                renpy.restart_interaction()

            def enter(self):
                urmi_box_enter(self.name)
                raise renpy.IgnoreEvent()

        found = _urmp_bucket("boxes")[name] = _URMPBox(name)
        return found

    def urmi_box_open(name):
        return urmi_ui(("box", name)) is not None

    def urmi_box_start(name, flag=False):
        """Open the box, filled with the value now (a number or words)."""

        kind = urmi_kind(name, flag)
        if kind not in ("int", "float", "text"):
            return
        now = _urmp_value(name)
        ui = _urmp_bucket("ui")
        ui[("box", name)] = _urm_number(now) if _urm_isnum(now) else u"%s" % (now,)
        for k in (("box_error", name), ("preview", name), ("more", name)):
            ui.pop(k, None)
        renpy.restart_interaction()

    def urmi_box_close(name):
        ui = _urmp_bucket("ui")
        ui.pop(("box", name), None)
        ui.pop(("box_error", name), None)
        renpy.restart_interaction()

    def urmi_box_step(name, delta):
        """- and +: the number in the box, one down or up."""

        text = urmi_ui(("box", name)) or u""
        try:
            number = float(text.strip())
        except Exception:
            number = 0
        number += delta
        _urmp_bucket("ui")[("box", name)] = _urm_number(number)
        renpy.restart_interaction()

    def urmi_box_fill(name, value):
        """A value the game checks for, into the box: never set."""

        _urmp_bucket("ui")[("box", name)] = _urm_number(value) if _urm_isnum(value) else u"%s" % (value,)
        renpy.restart_interaction()

    def urmi_box_enter(name):
        """Enter: the words typed go in, as a number for a number."""

        kind = urmi_kind(name)
        text = urmi_ui(("box", name)) or u""
        ui = _urmp_bucket("ui")
        value = text
        if kind in ("int", "float"):
            try:
                value = float(text.strip())
            except Exception:
                ui[("box_error", name)] = u"A number, please"
                renpy.restart_interaction()
                return
            if kind == "int" and value == int(value):
                value = int(value)
        error = urmi_set(name, value)
        if error:
            ui[("box_error", name)] = error
            renpy.restart_interaction()

    def urmi_box_checks(name):
        """The values the game checks for, as chips under the box: [(words,
        value)], lowest first."""

        p = urm_panel(name)
        out = python_list()
        for g in p.win_rungs:
            if g.value is _URMP_NOSET or g.value is None or isinstance(g.value, bool):
                continue
            out.append((urmi_value_words(g.value), g.value))
        return out

    # ---- the rest of the sheet

    def urmi_verdict(name):
        return urm_panel(name).win_verdict

    def urmi_choices(name):
        """The choice on screen: [(its number, its words, [(chip words,
        tone)])], what each choice does to this value with its name said
        plainly ("Carol love +1"), or "no change"."""

        p = urm_panel(name)
        title = urmi_sheet_title(name)
        out = python_list()
        for n, (words, chips) in enumerate(p.win_now):
            said = python_list()
            for w, tone in chips:
                said.append((u"%s %s" % (title, w), tone))
            out.append((u"%d" % (n + 1), words, said or python_list(((u"no change", "plain"),))))
        return out

    def urmi_reach_words(g):
        return _URMP_REACH_WORDS.get(g.reach)

    def urmi_needs_words(g):
        """The check at the end of a story line: "needs 5" for 5 or more."""

        words = g.words
        if words.endswith(u" or more"):
            words = words[:-len(u" or more")]
        return u"needs %s" % words

    def urmi_lines_words(n):
        """The one count of a place's size (idea 11), in words."""

        if n == 1:
            return u"1 line"
        return u"about %d lines" % n

    def urmi_page(name):
        """The story line page of the rung the sheet is turned to: (its
        words, its title, how much it plays, (reach words, tone) or None,
        [(status, words, [(chip words, tone)])], the check or None), or
        None."""

        p = urm_panel(name)
        g = urmi_rung(p, urmi_ui(("rung", name)))
        if g is None:
            return None
        reach = urmi_reach_words(g)
        steps = python_list()
        for st in p.win_story:
            if st.status == "here":
                steps.append(("here", urmi_value_words(st.now, p.mode == "bool" and "bool" or None), python_list()))
            else:
                steps.append((st.status, st.words, python_list(st.chips)))
        return (g.words, g.title, urmi_lines_words(g.lines) if g.lines else None,
                (reach, g.reach) if reach else None, steps,
                urmi_needs_words(g) if g.checks else None)

    # ---- the title bar's lists: our own (01_urm_door), with or without URM

    def urmi_lists(name, flag=False):
        """(remembered, ignored), each True or False; (None, None) for a
        flag, which the lists do not keep."""

        if flag:
            return (None, None)
        return (_urm_is_remembered(name), _urm_is_ignored(name, "path") and _urm_is_ignored(name, "code"))

    def urmi_freeze_view(name, flag=False):
        """(on, live, tip) of the title bar's Freeze: on while frozen; live
        when it can be frozen (a number, words or yes/no) or is frozen."""

        if flag:
            return (False, False, u"Freeze: for variables, not flags")
        if _urm_is_frozen(name):
            return (True, True, u"Unfreeze: kept at %s" % urmi_now_words(name))
        if _urm_can_freeze(name):
            return (False, True, u"Freeze at %s: the game cannot change it" % urmi_now_words(name))
        return (False, False, u"Freeze: numbers, words and true/false only")

    def urmi_freeze(name):
        """Freeze at what it holds now, or unfreeze."""

        if _urm_is_frozen(name):
            _urm_unfreeze(name)
        else:
            _urm_freeze(name)

    def urmi_remember(name):
        """Remember, under its own name, or Forget when it is remembered."""

        if _urm_is_remembered(name):
            _urm_forget(name)
        else:
            _urm_remember(name)

    def urmi_ignore(name):
        """Ignore for paths and the code view (the corner card skips its
        checks), or stop ignoring."""

        if urmi_lists(name)[1]:
            _urm_unignore(name)
        else:
            _urm_ignore(name)

    def urmi_cut(text, limit):
        """Words already made plain, cut to `limit` with "..." (never
        through an escaped brace)."""

        if len(text) <= limit:
            return text
        text = text[:limit - 3].rstrip()
        if (len(text) - len(text.rstrip(u"{"))) % 2:
            text = text[:-1]
        return text + u"..."

    def urmi_row_words(words):
        return urmi_cut(words, 42)

    def urmi_box_words(words):
        return urmi_cut(words, 16)

    def urmi_diamond(size, tone=None):
        """A rung with places still ahead: the diamond, as on the route map,
        in the colour of its reach; grey when the reach is not known (UX 9,
        21)."""

        colour = urmk_colour(tone + "-ink") if tone in ("gain", "warn", "loss") else urmk_colour("ink-muted")
        return Transform(Solid(colour, xysize=(size, size)), rotate=45)

    def urmi_halo():
        """The ring round the ladder's knob: the accent, faint."""

        return urmk_colour("accent")[:7] + "4d"

    # ---- Code and Replay for a rung: the script lines of its biggest place,
    # and the scene to replay (moved back from the first panel).

    def _urmp_stmt_code(node, indent, out, limit):
        ast = renpy.ast
        pad = "    " * indent
        if len(out) >= limit:
            return
        if isinstance(node, ast.Translate):
            for child in node.block or ():
                _urmp_stmt_code(child, indent, out, limit)
        elif isinstance(node, ast.Say):
            who = getattr(node, "who", None)
            what = (getattr(node, "what", "") or "").replace("\n", " ")
            if len(what) > 120:
                what = what[:117] + "..."
            out.append(u'%s%s"%s"' % (pad, (who + " ") if who else "", what))
        elif isinstance(node, (ast.Show, ast.Scene)) and getattr(node, "imspec", None):
            out.append(u"%s%s %s" % (pad, type(node).__name__.lower(), " ".join(node.imspec[0])))
        elif isinstance(node, ast.Python):
            source = getattr(getattr(node, "code", None), "source", "") or ""
            for line in source.split("\n")[:4]:
                out.append(u"%s$ %s" % (pad, line.strip()))
        elif isinstance(node, ast.Jump):
            out.append(u"%sjump %s" % (pad, node.target))
        elif isinstance(node, ast.Call):
            out.append(u"%scall %s" % (pad, node.label))
        elif isinstance(node, ast.If):
            for i, (cond, block) in enumerate(node.entries):
                if i == 0:
                    out.append(u"%sif %s:" % (pad, cond))
                elif cond.strip() == "True":
                    out.append(u"%selse:" % pad)
                else:
                    out.append(u"%selif %s:" % (pad, cond))
                for child in (block or ())[:3]:
                    _urmp_stmt_code(child, indent + 1, out, limit)
        elif isinstance(node, ast.Menu):
            out.append(u"%smenu:" % pad)
            for item in node.items:
                if item[2] is not None:
                    out.append(u'%s    "%s"%s:' % (pad, item[0], "" if item[1] in (None, "True") else " if " + item[1]))
        elif isinstance(node, ast.Return):
            out.append(u"%sreturn" % pad)

    def _urmp_code(r):
        out = python_list()
        if r.kind == "option":
            out.append(u"menu:")
            out.append(u'    "%s" if %s:' % (r.option, r.cond))
            for child in (r.block or ())[:14]:
                _urmp_stmt_code(child, 2, out, 18)
        elif r.kind == "loop":
            out.append(u"while %s:" % r.cond)
            for child in (r.block or ())[:12]:
                _urmp_stmt_code(child, 1, out, 16)
        else:
            out.append(u"if %s:" % r.cond)
            for child in (r.block or ())[:12]:
                _urmp_stmt_code(child, 1, out, 16)
            if r.other is not None:
                out.append(u"else:")
                for child in (r.other or ())[:6]:
                    _urmp_stmt_code(child, 1, out, 24)
            elif r.other_kind == "elif":
                out.append(u"elif ...")
        return u"\n".join(out)

    def urmi_rung_code(g):
        """The script lines of a rung's biggest place."""

        if g.big is None:
            return None
        return _urmp_code(g.big)

    def urmi_show_code(name, code):
        """Open Code above the sheet and keep its rung open underneath."""

        urmi_ui_set(("more", name), False)
        # The variable and flag dialogs both sit at 1060 on this layer.
        urmk_code_show(code, urmi_sheet_title(name), zorder=1061)

    def urmi_rung_replay(g):
        """A scene that can start without supplying label arguments."""

        if g.big is None:
            return None
        label = g.big.label
        target = _urmp_replay_target(label)
        return (label, target) if target is not None else None

    def _urmp_replay_target(label):
        if not isinstance(label, _urmi_text):
            return None
        # Match Ren'Py's single redirect without calling a missing-label hook.
        label = config.label_overrides.get(label, label)
        node = renpy.game.script.namemap.get(label)
        if not isinstance(node, renpy.ast.Label):
            return None
        signature = node.parameters
        if signature is None:
            return label
        params = signature.parameters
        # Older Ren'Py keeps (name, default) pairs.
        if not hasattr(params, "values"):
            required = any(default is None for _name, default in params)
        else:
            required = any(p.default is None and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
                           for p in params.values())
        return None if required else label

    def _urmp_replay():
        return _urm_kept("panel_replay", python_dict)

    def _urmp_replay_blocked():
        return getattr(renpy.store, "_in_replay", None) or _urmp_replay().get("running")

    def _urmp_replay_offer(label, cue):
        if not _urm_in_game() or _urmp_replay_blocked():
            return None
        target = _urmp_replay_target(label)
        if target is not None:
            words = cue if label == target else None
            return (label, target, words or u"The scene for this result")

    def _urmp_replay_open(offer):
        """Keep the captured scene while asking the player."""

        if not _urm_in_game() or _urmp_replay_blocked():
            return False
        label, target, cue = offer
        if _urmp_replay_target(label) != target:
            renpy.notify(u"This scene is unavailable. Try another scene.")
            return False
        _urmp_replay()["prompt"] = (renpy.game.context(), label, target, cue)
        renpy.show_screen("urmi_replay_confirm", _layer=_urmi_layer, _transient=True)
        return True

    def urmi_replay_offer(name, offer):
        if _urmp_replay_open(offer):
            urmi_ui_set(("more", name), False)

    _urm_replay_add(_urmp_replay_offer, _urmp_replay_open)

    def urmi_replay_prompt():
        prompt = _urmp_replay().get("prompt")
        if prompt and _urm_in_game() and prompt[0] is renpy.game.context():
            return prompt[3]
        return None

    def urmi_replay_cancel():
        _urmp_replay().pop("prompt", None)
        renpy.hide_screen("urmi_replay_confirm", layer=_urmi_layer)
        renpy.restart_interaction()

    def urmi_replay_start():
        if urmi_replay_prompt() is None or _urmp_replay_blocked():
            return
        prompt = _urmp_replay()["prompt"]
        _origin, label, target, _cue = prompt
        urmi_replay_cancel()
        if _urmp_replay_target(label) != target:
            renpy.notify(u"This scene is unavailable. Try another scene.")
            return

        replay = _urmp_replay()
        panel = _urmp_state()
        ui = _urmp_bucket("ui")
        # Child dialogue inherits this scope. A separate native replay starts
        # from clean stores, even when it asks for the same label.
        token = id(prompt)
        replay["running"] = token
        panel["ui"] = python_dict()
        try:
            renpy.call_replay(label, scope={"_urmi_replay_owner": token})
        finally:
            replay.pop("running", None)
            panel["ui"] = ui
            renpy.restart_interaction()

    def urmi_replay_active():
        token = _urmp_replay().get("running")
        return (token is not None and getattr(renpy.store, "_urmi_replay_owner", None) == token
                and bool(getattr(renpy.store, "_in_replay", None)))

    def _urmp_replay_interact():
        replay = _urmp_replay()
        prompt = replay.get("prompt")
        if prompt is not None and prompt[0] not in renpy.game.contexts:
            replay.pop("prompt", None)
        if (urmi_replay_active()
                and renpy.get_screen("urmi_replay_controls", layer=_urmi_layer) is None):
            renpy.show_screen("urmi_replay_controls", _layer=_urmi_layer)

    config.interact_callbacks.append(_urmp_replay_interact)

    def urmi_more_items(rung, delete):
        """What More holds besides Copy, as [(kind, what)]: with a rung open
        Code when it has a place to show; Replay when that place has an
        available scene; Delete when the value can be deleted."""

        items = python_list()
        if rung is not None:
            code = urmi_rung_code(rung)
            if code:
                items.append(("code", code))
            if not _urmp_replay_blocked():
                replay = urmi_rung_replay(rung)
                if replay:
                    requested, target = replay
                    cue = rung.title if requested == target else None
                    items.append(("replay", (requested, target, cue or u"The scene for this check")))
        if delete:
            items.append(("delete", None))
        return items
