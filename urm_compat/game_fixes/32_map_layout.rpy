    # ---- rows: this file decides them, the screen draws exactly those
    #
    # The screen used to wrap a box's chips itself, while the height of the
    # box was guessed here as two chips a row. The two disagreed and a chip
    # was drawn below its box (seen in Now and Then, 2026-11-20). Now a
    # box's rows are made here, each with its height, and the screen draws
    # them as given: the box is as tall as its rows by addition.
    #
    # How wide and high a text is drawn is asked of the engine - the way
    # URM itself sizes its texts (Text(...).size()) - with the style and
    # size the screen uses, so the font, URM's scaling and the player's
    # text-size setting are all in the answer. Only when the engine cannot
    # be asked is it counted from the characters, each class at the width
    # of its widest letter in the wider of the two fonts URM can be seen in
    # (Roboto, DejaVu Sans). Numbers are pixels before URM's scaling; the
    # screen uses the same ones.

    _URMM_BOX_W = 280         # a box
    _URMM_BOX_PAD = 14        # ... the room left free at each side
    _URMM_BOX_EDGE = 8        # ... and above and below
    _URMM_PART_GAP = 5        # between a box's title, rows and note
    _URMM_ROW_H = 26          # a row of chips, at least
    _URMM_ROW_GAP = 4
    _URMM_LEAD_W = 24         # the diamond in front of a row
    _URMM_CELL_GAP = 6
    _URMM_CHIP_PAD = (8, 2)   # around a chip's words

    _URMM_THIN = frozenset(u" .,:;'|!()[]/-ijlrtfIJ")
    _URMM_BROAD = frozenset(u"mwMW@%+=<>#^~")

    def _urmm_count(text, size, bold):
        """A text's width counted from its characters, at most; pixels
        before scaling."""

        n = 0
        for ch in text:
            if ch in _URMM_THIN:
                n += 64
            elif ch in _URMM_BROAD:
                n += 160
            elif ch > u"~":
                n += 170
            elif ch.isupper():
                n += 126
            else:
                n += 102
        # n is in tenths of a pixel at size 16; bold runs a tenth wider.
        return n * size * (11 if bold else 10) // 1600 + 1

    def _urmm_text(text, size, s, room=None, bold=False):
        """
        (width, height) in screen pixels of a text as the map's screen draws
        it at this size, broken to fit a room this wide (None: one line).
        """

        text = u"%s" % (text,)
        key = (text, size, room, bold)
        hit = _urmm_st.sizes.get(key)
        if hit is not None:
            return hit

        out = None
        if _urmm_st.engine is not False:
            try:
                w, h = renpy.text.text.Text(
                    urm_map_esc(text), style="x52URM_text", size=s(size),
                    bold=bold, substitute=False).size(room or 100000, 100000)
                out = (int(w + 0.999), int(h + 0.999))
                _urmm_st.engine = True
            except Exception:
                # No style, no font, an engine without Text.size: count,
                # and do not ask again.
                _urmm_st.engine = False

        if out is None:
            line = s(size * 12 // 10 + 1)
            wide = s(_urmm_count(text, size, bold))
            if room is None or wide <= room:
                out = (wide, line)
            else:
                # broken between words; a word longer than a line is broken
                # wherever it must be
                lines = 1
                used = 0
                gap = s(_urmm_count(u" ", size, bold))
                for word in text.split():
                    w = s(_urmm_count(word, size, bold))
                    if used and used + gap + w > room:
                        lines += 1
                        used = 0
                    if w > room:
                        lines += w // room
                        used = w % room
                    else:
                        used += (gap if used else 0) + w
                out = (room, lines * line)

        _urmm_st.sizes[key] = out
        return out

    def _urmm_wrap(rows, cells, lead, tip, faded, s, wide=None):
        """
        Cells [kind, words, tone, width, height] into as many rows as they
        need. Only the first row of a check carries its diamond; the rows
        that carry on are set in under it ("under"). wide: a list that is
        given, per row made, how wide each of its cells is.
        """

        room = s(_URMM_BOX_W) - 2 * s(_URMM_BOX_PAD)
        if lead:
            room -= s(_URMM_LEAD_W) + s(_URMM_CELL_GAP)
        gap = s(_URMM_CELL_GAP)
        line = python_list()
        widths = python_list()
        used = 0
        high = s(_URMM_ROW_H)
        for kind, words, tone, w, h in cells:
            if line and used + gap + w > room:
                rows.append((lead, tip, faded, high, tuple(line)))
                if wide is not None:
                    wide.append(tuple(widths))
                lead = lead and "under"
                line = python_list()
                widths = python_list()
                used = 0
                high = s(_URMM_ROW_H)
            if not line and w > room and kind == "chip":
                # Too long for a row even alone: its words run over several
                # lines, and the row is as high as that makes it.
                pad = s(_URMM_CHIP_PAD[0])
                w, h = _urmm_text(words, 16, s, max(1, room - 2 * pad))
                w += 2 * pad
                h += 2 * s(_URMM_CHIP_PAD[1])
            used += (gap if line else 0) + w
            high = max(high, h)
            line.append((kind, words, tone))
            widths.append(w)
        if line:
            rows.append((lead, tip, faded, high, tuple(line)))
            if wide is not None:
                wide.append(tuple(widths))

    def _urmm_rows(box, s):
        """
        A box's rows, top to bottom: what happens whatever the checks say;
        then one row per check - ONE diamond, then everything that check
        gives; then what stands alone (the icon of a menu that only changes
        lines, the lone diamond, "+N more"). With no check in the box the
        last group simply follows the chips.

        A row is (lead, tip, faded, height, cells): lead is "check" (a
        diamond that says tip), "under" (room left where the diamond of the
        row above is) or None; a cell is ("chip", words, tone), ("menu",
        None, None), ("check", tip, None), ("code", tip, None) - the "?" of
        a custom statement, where the lone diamond stands and as large -
        or ("more", words, None).
        """

        rows = python_list()
        wide = python_list()

        def chip(words, tone):
            w, h = _urmm_chip_size(words, s)
            return ("chip", words, tone, w, h)

        alone = python_list()
        for kind, _tip in box.badges:
            if kind == "menu":
                alone.append(("menu", None, None, s(20), s(20)))
        for mark in _URMM_MARKS:
            for kind, tip in box.badges:
                if kind == mark:
                    alone.append((kind, tip, None, s(_URMM_LEAD_W), s(_URMM_LEAD_W)))
        if box.more:
            words = "+%d more" % box.more
            w, h = _urmm_text(words, 15, s)
            alone.append(("more", words, None, w, h))

        free = python_list()
        checked = python_list()
        for key, tip, faded, chips in box.sets:
            cells = python_list(chip(words, tone) for words, tone in chips)
            if key:
                checked.append((tip, faded, cells))
            else:
                free.extend(cells)

        if not checked:
            free.extend(alone)
            alone = ()
        _urmm_wrap(rows, free, None, None, False, s, wide)
        for tip, faded, cells in checked:
            _urmm_wrap(rows, cells, "check", tip, faded, s, wide)
        _urmm_wrap(rows, alone, None, None, False, s, wide)
        box.rows = rows
        box.wide = wide

    def _urmm_chip_size(words, s):
        """(width, height) of a chip with these words."""

        w, h = _urmm_text(words, 16, s)
        return w + 2 * s(_URMM_CHIP_PAD[0]), h + 2 * s(_URMM_CHIP_PAD[1])

    def _urmm_box_parts(box, s):
        """
        A box's parts as the screen stacks them, top to bottom: (what, how
        high). The screen's frame and its column use the same numbers.

        What the player has (box.have, pick 3a) is a chip AFTER the title:
        on the title's line when both fit there, under it when not - said
        here (box.have_beside), drawn so by the screen.
        """

        room = s(_URMM_BOX_W) - 2 * s(_URMM_BOX_PAD)
        loud = box.kind in ("here", "merge")
        parts = python_list()
        if box.kind == "here":
            parts.append(("pill", _urmm_text(u"you are here", 14, s, None, True)[1] + 2 * s(1)))
        if box.title:
            high = _urmm_text(box.title, 19, s, room, loud)[1]
            if box.have:
                cw, ch = _urmm_chip_size(box.have[0], s)
                one = _urmm_text(box.title, 19, s, None, loud)
                box.have_beside = one[0] + s(_URMM_CELL_GAP) + cw <= room
                if box.have_beside:
                    parts.append(("title", max(one[1], ch)))
                else:
                    parts.append(("title", high))
                    parts.append(("have", ch))
            else:
                parts.append(("title", high))
        if box.sub:
            parts.append(("sub", _urmm_text(box.sub, 15, s, room)[1]))
        if box.rows:
            high = s(_URMM_ROW_GAP) * (len(box.rows) - 1)
            for row in box.rows:
                high += row[3]
            parts.append(("rows", high))
        if box.note and box.note_tone:
            parts.append(("note", _urmm_text(box.note, 16, s, None, True)[1] + 2 * s(_URMM_CHIP_PAD[1])))
        elif box.note:
            parts.append(("note", _urmm_text(box.note, 15, s, room)[1]))
        return parts

    def _urmm_box_h(box, s):
        """How high a box is: its parts, added up."""

        parts = _urmm_box_parts(box, s)
        high = 2 * s(_URMM_BOX_EDGE) + s(_URMM_PART_GAP) * max(0, len(parts) - 1)
        for _what, part in parts:
            high += part
        return high

    def _urmm_draw_rows(box, s):
        """
        A placed box's rows for the screen, with the PLACE of every mark
        that can be pointed at: a row is (lead, spot, faded, height,
        cells), a cell ("chip", words, tone), ("menu", None, None),
        ("more", words, None) or ("check" / "code", spot, None). A spot is
        (words, x, y, width, height) - what the mark says and the square
        it stands in, in the map's own coordinates. The hover text is
        drawn beside that square (the user's pick 1b), so the place is
        worked out here, from the numbers the screen lays the box out
        with, and not looked up on the screen.
        """

        mark = s(_URMM_LEAD_W)
        gap = s(_URMM_CELL_GAP)
        y = box.y + s(_URMM_BOX_EDGE)
        for what, high in _urmm_box_parts(box, s):
            if what == "rows":
                break
            y += high + s(_URMM_PART_GAP)

        out = python_list()
        n = 0
        for lead, tip, faded, high, cells in box.rows:
            x = box.x + s(_URMM_BOX_PAD)
            at = y + (high - mark) // 2
            spot = None
            if lead:
                if lead == "check":
                    spot = (tip, x, at, mark, mark)
                x += mark + gap
            drawn = python_list()
            i = 0
            for kind, words, tone in cells:
                if kind in _URMM_MARKS:
                    drawn.append((kind, (words, x, at, mark, mark), tone))
                else:
                    drawn.append((kind, words, tone))
                x += box.wide[n][i] + gap
                i += 1
            out.append((lead, spot, faded, high, tuple(drawn)))
            y += high + s(_URMM_ROW_GAP)
            n += 1
        return out

    def _urmm_point(box):
        """
        True when this is not a box but a point on the line: paths meeting,
        or a scene the story passes into, with nothing to say - no chip, no
        icon, no word about how it ends. A check that only changes lines
        does not earn a box either; its small diamond rides on the line.
        Neither does a custom statement with content inside: its "?" rides
        there too (_URMM_MARKS).
        """

        return (box.kind in ("merge", "block") and not box.note
                and _urmm_only_check(box))

    def _urmm_note(box, end):
        """How a way ends, on its last box. A way the map stops following
        gets a tail (drawn), not words; a way that meets needs neither."""

        if end[0] == "more":
            box.note, box.note_tone = "%d more choices" % end[1], None
        elif end[0] in ("limit", "ahead", "dyn"):
            # "dyn": the chip in the box says that where it goes is decided
            # while playing; the tail, that the map stops here.
            box.tail = True
        elif end[0] != "meet":
            box.note, box.note_tone = _URMM_LEAF_NOTES.get(end[0], (None, None))

    def _urmm_merge(records):
        """The point where ways meet again. With nothing to say it is a dot
        on the track, not a box - decided once everything is hung on it
        (_urmm_point), since how the story ends there is something to say."""

        merge = _URMMBox("merge", "Paths meet again", 0)
        _urmm_fill(merge, records)
        return merge

    def _urmm_grow(box, end):
        """Hang on a box what follows it: the ways of a split, then the
        point where they meet and what follows that; or how it ends."""

        if end[0] != "fork":
            box.end = end[0]
            _urmm_note(box, end)
            return

        box.diamond = (end[2] if len(end) > 2 else "menu") == "if"
        n = 0
        for label, segment in end[1]:
            child = _urmm_subtree(_urmm_way_kind(box.diamond, label),
                                  label, segment, n == 0)
            box.children.append(child)
            box.gain = box.gain or child.gain
            n += 1

        after = end[3] if len(end) > 3 else None
        if after is not None:
            merge = _urmm_merge(after[0])
            box.after = merge
            _urmm_grow(merge, after[1])
            box.gain = box.gain or merge.gain

    def _urmm_subtree(kind, label, segment, first):
        """A choice or a branch as a box, with everything that follows it."""

        faded = False
        have = None
        if kind == "branch":
            # The way past a menu whose every option has a test: faded
            # until no option is open as the game stands.
            none = label.startswith(_URMM_NONE)
            if none:
                faded = not _urmm_none_open(label)
            # (What follows the mark is the label the way jumps to. It was
            # the box's title; a script's own names are not shown.)
            label = label.split(u"\x01")[0]
            if none:
                title, sub = _URMM_NONE_WORDS, None
            elif label.startswith(_URMM_SKIP):
                title, sub = "Otherwise", (label[len(_URMM_SKIP):] or None)
            elif label == "otherwise":
                title, sub = _URMM_WAY_ELSE, None
            else:
                # The test in plain words and what the player has: the one
                # rule for a way of a check (urm_way_words, pick 3a).
                title, words, tone = urm_way_words(label[3:])
                sub = None
                if words:
                    have = (words, tone)
        else:
            title, sub = label, None

        box = _URMMBox(kind, title, 0)
        box.sub = sub
        box.have = have
        box.faded = faded
        records, end = segment
        _urmm_fill(box, records)
        _urmm_grow(box, end)
        return box

    def _urmm_exits(box):
        """The last boxes of the ways that reach the rejoin they were walked
        towards - the ones a merge after this box is joined to."""

        out = python_list()
        if box.after is not None:
            out.extend(_urmm_exits(box.after))
        elif box.children:
            for child in box.children:
                out.extend(_urmm_exits(child))
        elif box.end == "meet":
            out.append(box)
        return out

    def _urmm_stretch(start, budget=_URMM_STRETCH, stack=None):
        """
        From start to the next real split: ([(label or None, records)],
        split node or None, how it ended). Called labels do not start a
        block; only labels the story passes into do. The walk is the story
        graph's, in its trunk form (rework move 4).

        stack: the walk's stack at start, changed in place - the caller
        then holds the stack at the split. Given only on the map's own
        line, which starts where the game is (idea 7).
        """

        if stack is None:
            stack = python_list()
        blocks = python_list((python_list((None, python_list())),))
        w = _URMSGWalk(None, None, budget, _URMSG_KEEP_TRUNK, blocks)
        _records, end, at = _urmsg_run(w, start, stack, python_set())
        if end[0] == "split":
            return blocks, at, None
        return blocks, None, end[0]

    def _urmm_split(fork, stack=()):
        """
        (kind, [(label, segment)], rejoin, stack at the rejoin) for a menu
        or a splitting if. stack: the walk's stack at the split (see
        _urmm_arms); the fourth element is the stack the ways had when they
        met, or the split's own when none says.
        """

        # The arms are the story graph's (rework move 7): (index, test,
        # authored, block, first statement, caption).
        blocks = python_list()
        labels = python_list()
        sites = _urmsg_sites(stack)
        met = python_list()

        def at_rejoin():
            if met and met[0] is not None:
                return met[0]
            return tuple(stack)

        if isinstance(fork, renpy.ast.Menu):
            for _i, cond, _authored, block, _start, text in _urmsg_arms(fork):
                labels.append(_urmm_choice_label((text, cond)))
                blocks.append(block)
            skip = _urmm_skip_way(fork)
            if skip is not None:
                labels.append(skip)
                blocks.append(python_list())
            plan = _urmm_plan(fork, blocks, sites)
            arms = _urmm_arms(fork, blocks, plan, stack, met) if plan else None
            if not arms:
                return None
            return "menu", python_list(zip(labels, arms)), plan[1], at_rejoin()

        for _i, cond, authored, block, _start, _text in _urmsg_arms(fork):
            if authored:
                labels.append(u"if " + (u"%s" % cond) + _urmm_way_tag(fork, block))
            else:
                labels.append(u"otherwise" + _urmm_way_tag(fork, block))
            blocks.append(block or python_list())
        if not _urmsg_has_else(fork):
            labels.append(u"otherwise")
            blocks.append(python_list())
        plan = _urmm_plan(fork, blocks, sites)
        arms = _urmm_arms(fork, blocks, plan, stack, met) if plan else None
        if not arms:
            return None
        return "if", python_list(zip(labels, arms)), plan[1], at_rejoin()

    def _urmm_label_of(node, index):
        """
        The label the node is in, as the map words it: the story graph's
        one rule (_urmsg_label_of - up the node's own containers, the line
        only when they reach no label), or None when there is no answer.
        Now and Then's menu at script.rpy:1806 is in ch03begin, not in the
        play_movie2 nested above it.
        """
        try:
            label = _urmsg_label_of(index, node)
            if label:
                return u"%s" % label
        except Exception:
            pass
        return None

    def _urmm_build(here, view, index, live=()):
        """
        Hang the whole map on its first box and lay it out; returns the
        first rejoin.

        live: the calls the game is inside (_urmsg_live_stack), when here
        is where the game is. The map's own line carries the walk's stack
        from stretch to split to stretch, so a `return` out of a called
        scene leads back into the scene that called it, and "Ending" is
        only said where the story really ends (idea 7).

        The trunk: "you are here", the stretch to the next split, its ways
        (each a box with whatever follows hung on it - _urmm_subtree), the
        point where they meet, the next stretch - _URMM_STAGES times. A
        scene the story passes into is a box only for what happens in it,
        and has no title: its name is the author's, it tells the player
        nothing. With nothing in it, it is not drawn at all.
        """

        def chain(last, blocks):
            for _name, records in blocks:
                box = _URMMBox("block", "", 0)
                _urmm_fill(box, records)
                if not (box.chips or box.badges or box.more):
                    continue
                if (_urmm_only_check(box) and last.kind in ("merge", "block")
                        and _urmm_only_check(last)):
                    # Checks that only change lines, one scene after the
                    # other: one diamond on the line says them all (and
                    # one "?" every custom statement with content).
                    _urmm_take_marks(last, box)
                    continue
                last.after = box
                last = box
            return last

        stack = _urmsg_frames(live)
        blocks, fork, end = _urmm_stretch(here, stack=stack)
        first = _URMMBox("here", _urmm_label_of(here, index) or blocks[0][0] or "Here", 0)
        _urmm_fill(first, blocks[0][1])
        last = chain(first, blocks[1:])

        first_stop = None
        for stage in range(_URMM_STAGES):
            if fork is None:
                if end:
                    last.end = end
                    _urmm_note(last, (end,))
                break
            split = _urmm_split(fork, stack)
            if split is None:
                break
            kind, arms, stop = split[0], split[1], split[2]
            if stage == 0:
                first_stop = stop
            last.diamond = kind == "if"
            joined = False
            n = 0
            for label, arm in arms:
                child = _urmm_subtree(_urmm_way_kind(kind == "if", label), label, arm, n == 0)
                last.children.append(child)
                last.gain = last.gain or child.gain
                joined = joined or bool(_urmm_exits(child))
                n += 1

            if not joined or stop is None:
                break

            stack = python_list(split[3])
            blocks, fork, end = _urmm_stretch(stop, stack=stack)
            merge = _urmm_merge(blocks[0][1])
            merge.sub = blocks[0][0]
            last.after = merge
            last = chain(merge, blocks[1:])
            if stage == _URMM_STAGES - 1 and fork is not None:
                last.tail = True

        _urmm_place(view, first)
        return first_stop

    def _urmm_place(view, root):
        """
        Give every box its place. Each box is as tall as what is in it, each
        way takes only the room it and what hangs on it need, and what
        follows a split sits to the right of all its ways.
        """

        s = x52URM.scalePxInt
        W, GAP, MARGIN, T, ROW = s(_URMM_BOX_W), s(56), s(24), max(2, s(4)), s(12)
        DOT = s(18)
        MARK = s(_URMM_LEAD_W)
        DASH = s(8)

        # Sizes asked of the engine are kept for this layout only: the
        # font, URM's scale or the player's text size may have changed.
        _urmm_st.sizes.clear()

        def measure(b):
            b.dot = _urmm_point(b)
            b.pick = None
            if b.dot:
                # A point on the line. Where paths meet, the lines that
                # join say so: there is no mark for it (the user's pick 2b;
                # a ring stood here). On the line: the small diamond of a
                # check that only changes lines, and after it the "?" of a
                # custom statement with content inside.
                b.sub = None
                b.ring = False
                b.tip = None
                b.ask = None
                for kind, words in b.badges:
                    if kind == "check":
                        b.tip = words
                    elif kind == "code":
                        b.ask = words
                # Never two diamonds side by side: where a check sends the
                # story different ways right after this point, its big
                # diamond is the one mark, and says what the small one said.
                if b.tip and b.children and b.diamond:
                    b.pick = b.tip
                    b.tip = None
                on_line = (1 if b.tip else 0) + (1 if b.ask else 0)
                b.w = MARK * on_line
                b.h = DOT
            else:
                _urmm_rows(b, s)
                b.w = W
                b.h = _urmm_box_h(b, s)
            kw = 0
            kh = 0
            for c in b.children:
                measure(c)
                kw = max(kw, c.tw)
                kh += c.th
            if b.children:
                kh += ROW * (len(b.children) - 1)
            b.kh = kh
            b.ow = b.w + (GAP + kw if b.children else 0) + (GAP if b.tail else 0)
            if b.after is not None:
                measure(b.after)
                b.tw = b.ow + GAP + b.after.tw
                b.th = max(b.h, kh, b.after.th)
            else:
                b.tw = b.ow
                b.th = max(b.h, kh)

        placed = python_list()

        def place(b, x, y, h, col):
            b.x = x
            b.y = y + (h - b.h) // 2
            b.col = col
            b.row = b.y
            placed.append(b)
            if b.children:
                cy = y + (h - b.kh) // 2
                for c in b.children:
                    place(c, x + b.w + GAP, cy, c.th, col + 1)
                    cy += c.th + ROW
            if b.after is not None:
                place(b.after, x + b.ow + GAP, y, h, col + 1)

        measure(root)
        place(root, MARGIN, MARGIN, root.th, 0)

        def mid(b):
            return b.y + b.h // 2

        def tone(b):
            return "gain" if b.gain else "plain"

        bars = python_list()
        diamonds = python_list()
        picks = python_list()
        marks = python_list()
        codes = python_list()

        for b in placed:
            if b.dot:
                # The line runs on through a point; its marks stand on it.
                if b.w:
                    bars.append((b.x, mid(b) - T // 2, b.w, T, tone(b)))
                x = b.x + b.w - MARK // 2
                if b.ask:
                    codes.append((x, mid(b), b.ask))
                    x -= MARK
                if b.tip:
                    marks.append((x, mid(b), b.tip))

            if b.children:
                xs = b.x + b.w
                xm = xs + GAP // 2
                mids = python_list(mid(c) for c in b.children)
                mids.append(mid(b))
                bars.append((xs, mid(b) - T // 2, xm - xs, T, tone(b)))
                lo, hi = min(mids), max(mids)
                bars.append((xm - T // 2, lo - T // 2, T, hi - lo + T, tone(b)))
                for c in b.children:
                    bars.append((xm, mid(c) - T // 2, c.x - xm, T, tone(c)))
                if b.diamond:
                    diamonds.append((xm, mid(b)))
                    picks.append((xm, mid(b), urm_pick_tip(b.pick)))

            if b.after is not None:
                a = b.after
                if b.children:
                    # every way that reaches the rejoin runs into it
                    ends = python_list()
                    for c in b.children:
                        ends.extend(_urmm_exits(c))
                    xm = a.x - GAP // 2
                    mids = python_list(mid(e) for e in ends)
                    mids.append(mid(a))
                    for e in ends:
                        bars.append((e.x + e.w, mid(e) - T // 2, xm - e.x - e.w, T, tone(e)))
                    bars.append((xm - T // 2, min(mids) - T // 2, T,
                                 max(mids) - min(mids) + T, tone(a)))
                    bars.append((xm, mid(a) - T // 2, a.x - xm, T, tone(a)))
                else:
                    bars.append((b.x + b.w, mid(b) - T // 2, a.x - b.x - b.w, T, tone(a)))

            if b.tail:
                # the map stops following here: three dashes, no words
                x = b.x + b.w + DASH // 2
                for _n in (0, 1, 2):
                    bars.append((x, mid(b) - T // 2, DASH, T, "plain"))
                    x += DASH * 2

        # The map's boxes and the points where paths meet. A scene that is
        # only a mark on the line is neither.
        for b in placed:
            b.draw = python_list() if b.dot else _urmm_draw_rows(b, s)
        view.boxes = python_list(b for b in placed if not (b.dot and b.kind == "block"))
        view.bars = bars
        view.diamonds = diamonds
        view.picks = picks
        view.dots = python_list()
        view.marks = marks
        view.codes = codes
        view.here = (root.x + root.w // 2, mid(root))
        view.width = MARGIN * 2 + root.tw
        view.height = MARGIN * 2 + root.th
        view.mini = None

    def urm_map_overview(st, at, view, xadj, yadj, shown, size):
        """
        The small overview in the corner: every box of the map, and a frame
        around the part on screen. A DynamicDisplayable body - the frame
        follows the drag without the screen being rebuilt.
        """

        try:
            shown_w, shown_h = shown
            mw, mh = size
            total_w = max(view.width, shown_w)
            total_h = max(view.height, shown_h)
            k = min(float(mw) / total_w, float(mh) / total_h)
            mw, mh = int(total_w * k), int(total_h * k)

            if view.mini is None or view.mini[0] != (k, mw, mh):
                base = Fixed(xysize=(mw, mh))
                base.add(Solid(urm_map_colour("screenSolid"), xysize=(mw, mh)))
                top = (total_h - view.height) // 2
                for b in view.boxes:
                    colour = urm_map_colour("root" if b.kind in ("here", "merge") else "muted")
                    base.add(Solid(colour,
                                   xysize=(max(2, int(b.w * k)), max(2, int(b.h * k))),
                                   xpos=int(b.x * k), ypos=int((b.y + top) * k)))
                view.mini = ((k, mw, mh), base)

            out = Fixed(xysize=(mw, mh))
            out.add(view.mini[1])
            x = int(xadj.value * k)
            y = int(yadj.value * k)
            w = max(4, int(shown_w * k))
            h = max(4, int(shown_h * k))
            ink = urm_map_colour("ink")
            out.add(Solid(ink, xysize=(w, 2), xpos=x, ypos=y))
            out.add(Solid(ink, xysize=(w, 2), xpos=x, ypos=min(mh - 2, y + h - 2)))
            out.add(Solid(ink, xysize=(2, h), xpos=x, ypos=y))
            out.add(Solid(ink, xysize=(2, h), xpos=min(mw - 2, x + w - 2), ypos=y))
            return out, 0.1
        except Exception:
            return Null(), None

