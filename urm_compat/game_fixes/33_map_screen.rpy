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

        s = x52URM.scalePxInt
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
            s = x52URM.scalePxInt
            words, bx, by, bw, bh, room = urm_map_bubble_at(
                tip, view, xadj.value, yadj.value, shown)
            out = Fixed(xysize=shown)
            out.add(Solid(urm_map_colour("merge"), xysize=(bw, bh), xpos=bx, ypos=by))
            inner = Fixed(xysize=room, xpos=bx + s(_URMM_TIP_PAD[0]), ypos=by + s(_URMM_TIP_PAD[1]))
            inner.add(Text(urm_map_esc(words), style="x52URM_text", size=s(_URMM_TIP_SIZE),
                           color=urm_map_colour("inkOnPrimary"), substitute=False))
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
                        line = urm_map_later_line(name, op, lit, where)
                        if line not in seen:
                            seen.add(line)
                            view.later.append(line)
        except BaseException as error:
            view = _URMMView()
            view.empty = "The map could not be drawn here (%s)." % (error,)

        return view

    def urm_map_diamond(size, edge="gain", fill="screenSolid"):
        """A small outlined diamond, drawn - the icon fonts have none."""
        b = max(1, size // 7)
        return Transform(Fixed(
            Solid(urm_map_colour(edge), xysize=(size, size)),
            Solid(urm_map_colour(fill), xysize=(size - 2 * b, size - 2 * b), xpos=b, ypos=b),
            xysize=(size, size)), rotate=45)

    def urm_map_fade(faded):
        """What a row of chips is drawn through: faded when its check fails
        as the game stands. And a way's box: faded when the game will not
        take that way as things stand (_URMMBox.faded). Every row and box
        goes through one of the two, so the screen has one shape of each;
        made once, when first asked for."""

        made = getattr(_urmm_st, "fades", None)
        if made is None:
            made = _urmm_st.fades = (Transform(), Transform(alpha=0.4))
        return made[1 if faded else 0]

    # ---- the screen's side

    def urm_map_view():
        return getattr(_urmm_st, "view", None) or _URMMView()

    def urm_map_open(source=None):
        # source says which button asked (the quickmenu, a notification
        # header, the hotkey); the map is the same from all of them.
        _urmm_st.view = urm_map_build()
        try:
            layer = _urmi_layer
        except Exception:
            layer = "x52Overlay" if "x52Overlay" in config.layers else "overlay"
        renpy.show_screen("urm_route_map", _layer=layer)
        renpy.restart_interaction()

    def urm_map_close():
        for layer in python_list(config.layers) + python_list(getattr(config, "top_layers", ())):
            try:
                if renpy.get_screen("urm_route_map", layer=layer) is not None:
                    renpy.hide_screen("urm_route_map", layer=layer)
            except Exception:
                continue
        _urmm_st.view = None
        renpy.restart_interaction()

    def urm_map_colour(key):
        """Theme colours for the map, so it follows URM's theme."""

        try:
            t = x52URM.Theme
            c = t.colors
            table = python_dict((
                ("gain", t.primary),
                ("plain", t.colorAlpha(t.text, 0.3)),
                ("box", c.buttonBgHover),
                ("root", t.primary),
                ("merge", t.primary),
                ("ink", t.text),
                ("inkOnPrimary", t.background),
                ("muted", t.colorAlpha(t.text, 0.7)),
                ("gainBg", c.successBg), ("gainText", c.successText),
                # "You are in a part others may not see": amber, the one
                # tone URM's themes have no colour for.
                ("warnBg", "#fff4ce"), ("warnText", "#6b5a00"),
                ("lossBg", c.errorBg), ("lossText", c.errorText),
                ("setBg", t.secondary), ("setText", t.text),
                ("otherBg", c.buttonBg), ("otherText", t.text),
                ("screen", t.colorAlpha(t.background, 0.96)),
                ("screenSolid", t.background),
                ("pill", t.background), ("pillText", t.primary),
                ("bar", c.buttonBg),
            ))
            return table.get(key) or t.text
        except Exception:
            return "#888888"

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

    def _urmm_current_menu():
        try:
            node = _urmsg_here()
            if isinstance(node, renpy.ast.Menu):
                return node
        except BaseException:
            pass
        return None

    def urm_maze_for(choices):
        """The walked arms for the menu on screen, cached by menu."""

        blocks = [_urm_choice_nodes(c) for c in choices]
        if not blocks or any(b is None for b in blocks):
            return None

        # What was walked under another script is not this script's.
        gen = _urmsg_gen()
        if _urmm_st.gen != gen:
            _urmm_st.cache.clear()
            _urmm_st.gen = gen

        # The menu on screen is where the game is: its ways are walked with
        # the calls the game is inside (idea 7), and the answer is kept for
        # that menu reached through those calls.
        menu = _urmm_current_menu()
        frames = _urmsg_frames(_urmsg_live_stack()) if menu is not None else python_list()
        sites = _urmsg_sites(frames)

        key = tuple(id(b) for b in blocks) + tuple(id(s) for s in sites)
        hit = _urmm_st.cache.get(key)

        if hit is None:
            plan = _urmm_plan(menu, blocks, sites)
            if plan is None:
                return None
            met = python_list()
            arms = _urmm_arms(menu, blocks, plan, frames, met)
            if arms is None:
                return None
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
                    dist = _urmm_distances(hit[1], _urmm_st.cache.get(("after",) + key) or ())
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
                except BaseException:
                    pass

        return hit

