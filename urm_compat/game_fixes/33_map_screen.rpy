    # ---- the hover text: a bubble beside the mark pointed at (pick 1b)
    #
    # It stood in the header, centred, where the legend is: on the user's
    # screen it had 240 px and needed up to 568. Now it is where the eye
    # is - beside the mark - and the header holds no hover text at all.

    _URMM_TIP_SIZE = 17
    _URMM_TIP_ROOM = 260      # its words run this wide before they break: a bubble as wide as a box
    _URMM_TIP_PAD = (10, 6)
    _URMM_TIP_GAP = 6         # between the mark's square and the bubble
    _URMM_TIP_EDGE = 20       # kept free at the edges of the map in view
    _URMM_TIP_OFF = 120       # how far it may stand off its mark to cover no box
    _URMM_TIP_STEP = 12

    def urm_map_bubble_place(mark, size, shown, edge, gap, boxes=(), off=0, step=12):
        """
        Where a bubble this large goes for a mark, both in the coordinates
        of the part of the map in view: (x, y) of its top left corner.

        BESIDE the mark, at one of six places, tried in this order: at its
        right, level with it; at its left; under it, running right; under
        it, running left; over it, running right; over it, running left. A
        place counts only when the bubble is wholly in view there (edge
        free all round; along the mark it is moved as far as that takes).
        The first place where the bubble covers nothing of what the boxes
        say wins. When there is none, the bubble stands OFF its mark, a
        step at a time and at most `off`, away from it at each of the six
        places, until one is free; and when none is, it goes where it
        covers the least (the nearest of those).

        Why: seen on the real maps, a bubble that always went to the right
        lay on the title of the way a big diamond leads to, and on the
        very chips the diamond in front of a row stands for; and a big
        diamond is hemmed in by boxes 28 px away on both sides, so the
        least covering place touching it still lay on half a title.

        It never covers the mark it explains - and so never the mouse
        either, which is on the mark. The header and its legend are above
        the map in view, out of its reach.

        boxes: (x, y, width, height) of what should stay readable.
        """

        mx, my, mw, mh = mark
        bw, bh = size
        vw, vh = shown

        def within(value, lo, hi):
            return lo if (value < lo or hi < lo) else (hi if value > hi else value)

        lo_x, hi_x = edge, vw - edge - bw
        lo_y, hi_y = edge, vh - edge - bh
        level = within(my + mh // 2 - bh // 2, lo_y, hi_y)
        runs_right = within(mx, lo_x, hi_x)
        runs_left = within(mx + mw - bw, lo_x, hi_x)

        best = None
        least = None
        away = 0
        while away <= off:
            # (A mark half out of view: the bubble still starts inside it.)
            right = max(mx + mw + gap + away, lo_x)
            left = min(mx - gap - bw - away, hi_x)
            below = max(my + mh + gap + away, lo_y)
            above = min(my - gap - bh - away, hi_y)
            places = python_list()
            if right <= hi_x:
                places.append((right, level))
            if left >= lo_x:
                places.append((left, level))
            if below <= hi_y and lo_x <= hi_x:
                places.append((runs_right, below))
                places.append((runs_left, below))
            if above >= lo_y and lo_x <= hi_x:
                places.append((runs_right, above))
                places.append((runs_left, above))

            for x, y in places:
                covered = 0
                for ox, oy, ow, oh in boxes:
                    wide = min(x + bw, ox + ow) - max(x, ox)
                    high = min(y + bh, oy + oh) - max(y, oy)
                    if wide > 0 and high > 0:
                        covered += wide * high
                if not covered:
                    return x, y
                if least is None or covered < least:
                    best = (x, y)
                    least = covered
            away += max(1, step)

        if best is not None:
            return best
        # What is in view is smaller than the bubble and its mark: the
        # side with more room, running out of view rather than over the
        # mark.
        if vw - (mx + mw) >= mx:
            return mx + mw + gap, level
        return mx - gap - bw, level

    def urm_map_bubble_at(tip, view, xscroll, yscroll, shown):
        """(words, x, y, width, height, room for the words) of the bubble
        for a spot (words, x, y, w, h in the map's own coordinates), in the
        coordinates of the part of the map in view."""

        s = urmk_px_cut
        words, x, y, w, h = tip
        vw, vh = shown
        top = (max(view.height, vh) - view.height) // 2
        dx = int(xscroll)
        dy = top - int(yscroll)
        tw, th = _urmm_text(words, _URMM_TIP_SIZE, s, s(_URMM_TIP_ROOM))
        bw = tw + 2 * s(_URMM_TIP_PAD[0])
        bh = th + 2 * s(_URMM_TIP_PAD[1])
        # What the boxes in view SAY: a box without the room left free
        # round its content.
        px = s(_URMM_BOX_PAD)
        py = s(_URMM_BOX_EDGE)
        boxes = python_list()
        for box in view.boxes:
            if box.dot:
                continue
            ox = box.x - dx
            oy = box.y + dy
            if ox + box.w <= 0 or ox >= vw or oy + box.h <= 0 or oy >= vh:
                continue
            boxes.append((ox + px, oy + py, box.w - 2 * px, box.h - 2 * py))
        bx, by = urm_map_bubble_place(
            (x - dx, y + dy, w, h), (bw, bh), shown,
            s(_URMM_TIP_EDGE), s(_URMM_TIP_GAP), boxes,
            s(_URMM_TIP_OFF), s(_URMM_TIP_STEP))
        return words, bx, by, bw, bh, (tw, th)

    def urm_map_bubble(st, at, tip, view, xadj, yadj, shown):
        """
        The bubble itself, over the part of the map in view. A
        DynamicDisplayable body, like the overview: it follows the mark
        while the map is dragged or scrolled under the mouse, without the
        screen being rebuilt.
        """

        try:
            s = urmk_px_cut
            words, bx, by, bw, bh, room = urm_map_bubble_at(
                tip, view, xadj.value, yadj.value, shown)
            out = Fixed(xysize=shown)
            back = urmk_back("bubble")
            out.add(Fixed(back.image, xpos=bx - back.left, ypos=by - back.top,
                          xysize=(bw + back.left + back.right, bh + back.top + back.bottom)))
            inner = Fixed(xysize=room, xpos=bx + s(_URMM_TIP_PAD[0]), ypos=by + s(_URMM_TIP_PAD[1]))
            inner.add(Text(urm_map_esc(words), style="urmk_text", size=s(_URMM_TIP_SIZE),
                           color=urm_map_ink("ink"), substitute=False))
            out.add(inner)
            return out, 0.1
        except Exception:
            return Null(), None

    def urm_map_build(menu=None, index=None):
        """The map from where the game is - or from menu, for tests."""

        view = _URMMView()

        try:
            if index is None:
                try:
                    index = _urmi_index()
                except Exception:
                    index = None

            here = menu if menu is not None else _urmm_here()
            # The calls the game is inside - only when the map starts where
            # the game is (idea 7).
            live = _urmsg_live_stack() if menu is None else ()
            # Empty only when the map would draw no split: the stretch ahead
            # is the one _urmm_build walks, and it ends at a menu or at a
            # check that sends the story different ways (idea 9, C8).
            if here is None or _urmm_stretch(here, stack=_urmsg_frames(live))[1] is None:
                view.empty = "No choice or check ahead yet."
                return view

            stop = _urmm_build(here, view, index, live)

            if index is not None and getattr(index, "state", None) == "ready" and stop is not None:
                frames = _urmsg_frames(live)
                fork = here if isinstance(here, renpy.ast.Menu) else _urmm_next_menu(
                    here, sites=_urmsg_sites(frames))
                split = _urmm_split(fork, frames) if fork is not None else None
                if split is not None:
                    names = python_list()
                    for _l, a in split[1]:
                        _urmm_names(a, names)
                    dist = _urmm_distances(split[2], _urmsg_sites(split[3]))
                    seen = python_set()
                    for name, _t, where, op, lit in _urmm_later(split[2], names, index, dist):
                        parts = urm_map_later_parts(name, op, lit, where)
                        line = "%s  ·  %s" % parts[:2]
                        if line not in seen:
                            seen.add(line)
                            view.later.append(line)
                            view.later_rows.append(parts)
        except BaseException as error:
            view = _URMMView()
            view.empty = "The map could not be drawn here (%s)." % (error,)

        return view

    def urm_map_later_view(view):
        """The footer's rows: (words, what the player has, its tone)."""

        rows = getattr(view, "later_rows", None)
        if rows and len(rows) == len(view.later):
            return rows
        return [(line, None, "plain") for line in view.later]

    def urm_map_mark(size, colour):
        """A filled diamond: 'pick' (the game picks the way) or 'lines'
        (only lines change)."""

        return Transform(Solid(urm_map_ink(colour), xysize=(size, size)), rotate=45)

    # ---- the screen's side

    def urm_map_view():
        return getattr(_urmm_st, "view", None) or _URMMView()

    def urm_map_ready():
        """Whether the route map can open: its screen is ours
        (game/urmplus.rpa)."""
        return renpy.has_screen("urm_route_map")

    def urm_map_open(source=None):
        # source says which button asked (the quickmenu, a notification
        # header, the hotkey); the map is the same from all of them. It
        # opens on our layer.
        if not urm_map_ready():
            return
        _urmm_st.view = urm_map_build()
        renpy.show_screen("urm_route_map", _layer=_urmi_layer)
        renpy.restart_interaction()

    def urm_map_close():
        if renpy.get_screen("urm_route_map", layer=_urmi_layer) is not None:
            renpy.hide_screen("urm_route_map", layer=_urmi_layer)
        _urmm_st.view = None
        renpy.restart_interaction()

    def _urmm_outline(menu, blocks):
        """
        A plain-text form of the whole analysis, for tests and for the cards:
        one (common_texts, [(path, texts, end)]) per choice.
        """

        out = python_list()
        for arm in (_urmm_arms(menu, blocks) or ()):
            common, outcomes = _urmm_route(arm)
            out.append((
                [t for _g, t in common],
                [(" > ".join(labels), [t for _g, t in recs], end)
                 for labels, recs, end in outcomes]))
        return out

    def urm_maze_rows(segment):
        """
        Rows for one choice card. Records before the first fork are drawn as
        before; each different outcome after it is one row, its path in
        italics and its changes in code colours. Paths with identical
        outcomes share a row.
        """

        common, outcomes = _urmm_route(segment)

        if len(outcomes) == 1 and not outcomes[0][0]:
            rows = _urm_effects_records(common)
            note = outcomes[0][2]
            if note:
                if len(rows) == 1 and rows[0][1] == _urm_words("no tracked changes"):
                    rows = python_list()
                rows.append((_URM_ICON_GUARD, _urm_words(note)))
            return rows

        rows = python_list(_urm_effects_records(common, allow_empty=True))

        groups = python_list()
        index = python_dict()
        for labels, recs, note in outcomes:
            texts = tuple((g, t, n) for g, t, n in _urm_reduce(recs)[0])
            key = (texts, note)
            if key in index:
                groups[index[key]][0].append(labels)
            else:
                index[key] = len(groups)
                groups.append(([labels], texts, note))

        room = _URM_MAX_ROWS - len(rows)
        if len(groups) > room:
            room -= 1

        for n, (paths, texts, note) in enumerate(groups):
            if n >= room:
                rows.append((_URM_ICON_GUARD, _urm_words(
                    "+%d more outcomes" % (len(groups) - n))))
                break

            head = _urm_words(" / ".join(
                u" › ".join(_urm_clip(x, _URMM_LABEL_CHARS) for x in p)
                if p else "straight on"
                for p in paths) + ":") + " "
            if texts:
                body = ", ".join(_urmm_piece(g, t, c) for g, t, c in texts)
            else:
                body = _urm_words("no tracked changes")
            if note:
                body += " " + _urm_words("(%s)" % note)
            rows.append((_URM_ICON_GUARD, head + body))

        return rows

    def _urmm_piece(guards, text, count):
        """One change inside an outcome row, keeping its guards and count."""

        out = _urm_colorize(text)
        if count > 1:
            out += _urm_words("  x%d" % count)
        for guard in guards:
            if guard == "otherwise":
                out += " " + _urm_words("(otherwise)")
            else:
                out += " " + _urm_words("(only if ") + _urm_colorize(
                    guard[len("only if "):]) + _urm_words(")")
        return out

    def _urm_effects_records(records, allow_empty=False):
        """_urm_effects for records already walked rather than a block."""

        out = _urm_effects_from(records)
        if allow_empty and len(out) == 1 and out[0][1] == _urm_words("no tracked changes"):
            return python_list()
        return out

    def urm_maze_for(choices, menu=None):
        """The walked arms for the menu on screen, cached by menu. menu: a
        Menu statement a few lines ahead instead (_urmm_ahead), reached
        through the calls the game is inside now."""

        # The choice the worker is walking ahead came before its walk ended
        # (the player clicked on fast): that walk is finished now, from where
        # it is, and its answer is taken from the memory below.
        if (menu is None and _urm_menu_here() is getattr(_urmm_st, "ahead", None)
                and _urm_work_state("corner card ahead") in ("waiting", "running")):
            _urm_work_finish("corner card ahead")
        return _urmsg_drain(_urmm_maze_steps(choices, menu))

    def _urmm_maze_steps(choices, menu=None):
        """urm_maze_for in steps: the worker walks the choice ahead with it
        (_urmm_ahead_steps), no step long on a frame."""

        blocks = [_urm_choice_nodes(c) for c in choices]
        if not blocks or any(b is None for b in blocks):
            yield _URMSGDone(None)
            return

        # What was walked under another script is not this script's.
        gen = _urmsg_gen()
        if _urmm_st.gen != gen:
            _urmm_st.cache.clear()
            _urmm_st.gen = gen

        # The menu on screen is where the game is: its ways are walked with
        # the calls the game is inside (idea 7), and the answer is kept for
        # that menu reached through those calls.
        if menu is None:
            menu = _urm_menu_here()
        frames = _urmsg_frames(_urmsg_live_stack()) if menu is not None else python_list()
        sites = _urmsg_sites(frames)

        key = tuple(id(b) for b in blocks) + tuple(id(s) for s in sites)
        hit = _urmm_st.cache.get(key)

        if hit is None:
            plan = None
            for _said in _urmsg_plan_steps(menu, blocks, _URMM_REACH, sites):
                if isinstance(_said, _URMSGDone):
                    plan = _said.result
                    break
                yield _said
            if plan is None:
                yield _URMSGDone(None)
                return
            met = python_list()
            arms = None
            for _said in _urmm_arms_steps(menu, blocks, plan, frames, met):
                if isinstance(_said, _URMSGDone):
                    arms = _said.result
                    break
                yield _said
            if arms is None:
                yield _URMSGDone(None)
                return
            # the walk may have paused: what another reader kept meanwhile
            # under this key is as good, and is kept
            if _urmm_st.cache.get(key) is not None:
                hit = _urmm_st.cache[key]
        if hit is None:
            if len(_urmm_st.cache) > 64:
                _urmm_st.cache.clear()
            hit = python_list([arms, plan[1], None])
            _urmm_st.cache[key] = hit
            # Where the calls still go back to once the ways have met: the
            # search for later tests follows a `return` there.
            _urmm_st.cache[("after",) + key] = _urmsg_sites(
                met[0] if met and met[0] is not None else frames)

        # The later tests need the script index; computed once it is ready.
        # Only a complete answer is remembered: while the index is not ready,
        # or when reading it failed, the entry stays [arms, rejoin, None] and
        # the next call tries again.
        if hit[2] is None:
            try:
                index = _urmi_index()
            except Exception:
                index = None
            if index is not None and index.state == "ready":
                try:
                    dist, cut, ahead = _urmm_reach_later(
                        hit[1], _urmm_st.cache.get(("after",) + key) or ())
                    names = python_list()
                    for arm in hit[0]:
                        _urmm_names(arm, names)
                    found = _urmm_later(hit[1], names, index, dist)
                    rows = python_list(
                        _urmm_later_rows(_urmm_later(
                            hit[1], _urmm_names(arm), index, dist))
                        for arm in hit[0])
                    hit[2] = rows
                    hit.append(found)
                    # What can run later, for urm_choice_costs - none when
                    # the search was cut short: a check further on would
                    # read as never made.
                    hit.append(None if cut else dist)
                    hit.append(None if cut else _urmm_code_reads(ahead))
                except BaseException:
                    pass

        yield _URMSGDone(hit)

    # ---- ahead of the player (the speed plan, step 6): the menu a few lines
    # on is walked while its lines are read, so the corner card finds it
    # ready when the menu comes (it was walked when the menu came: up to
    # 1.3 s on Being a DIK, FINDINGS "Where URM+ freezes").

    _URMM_AHEAD = 40         # statements looked through for the next menu

    def _urmm_next_menu_ahead(node):
        """The Menu statement a straight run of lines from node leads to,
        or None: stops at a jump, a call, a return, a check or a menu's
        end, where the way on is not the next line or the calls change."""

        steps = 0
        while node is not None and steps < _URMM_AHEAD:
            kind = _urmsg_kind(node)
            if kind == _URMSG_K_MENU:
                return node
            if kind >= _URMSG_K_RET or kind == _URMSG_K_USER:
                return None     # a return, jump, call, check, loop, python or a game's own
                                # statement (either may jump): not a straight run
            node = getattr(node, "next", None)
            steps += 1
        return None

    def _urmm_ahead_steps(menu):
        """The worker's walk of the choice ahead: urm_maze_for in steps."""

        for said in _urmm_maze_steps(_urm_choices_of(menu), menu):
            if isinstance(said, _URMSGDone):
                break
            yield said
        yield _URMWorkDone()

    def _urmm_ahead_interact():
        """config.interact_callbacks: hand the worker the next menu's walk."""

        try:
            if not _urm_in_game() or not _urm_setting("showChoicesNotification"):
                return
            here = _urmsg_here()
            if here is None or _urmsg_kind(here) == _URMSG_K_MENU:
                return
            menu = _urmm_next_menu_ahead(getattr(here, "next", None))
            if menu is None or getattr(_urmm_st, "ahead", None) is menu:
                return
            _urmm_st.ahead = menu
            _urm_work_slices("corner card ahead", lambda: _urmm_ahead_steps(menu))
        except Exception:
            pass

    try:
        if _urmm_ahead_interact not in config.interact_callbacks:
            config.interact_callbacks.append(_urmm_ahead_interact)
    except Exception as error:
        print("MRM: the corner card is not worked out ahead (%s)" % (error,))

