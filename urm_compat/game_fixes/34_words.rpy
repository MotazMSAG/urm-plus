    # ------------------------------------------------------------------
    # Notification cards, the map's way: words and chips, not code
    # ------------------------------------------------------------------
    #
    # The "Choices detected" and "Path detected" notifications, redrawn in
    # the style the user approved on the route map (UX.md, "The approved
    # look"): the real choice text instead of "1 always", changes as word
    # chips coloured by tone, deeper routes as "› Go left" rows, and one
    # short line per flag that matters later. Both can be closed until the
    # situation changes - they can sit over the game.
    #
    # A card is (icon, icon tone, number, title, dim, needs, rows):
    #   icon       a Material glyph, or ""; tone a urm_map_colour key
    #   dim        drawn muted - a choice you cannot pick, a gate that is
    #              skipped
    #   needs      a muted line under the title, or None
    #   rows       [(prefix or None, [(words, tone)], note or None)]

    _URMM_CARD_ROWS = 5

    _URMM_COND = _urmm_re.compile(
        r"^\s*(not\s+)?([A-Za-z_][\w.]*)\s*(?:(==|!=|>=|<=|>|<)\s*(.+?))?\s*$")

    # ---- a test in words: the one place every display takes them from

    def _urmw_match(text):
        """_URMM_COND on one plain test, or None for anything it would
        misread (a call, a second test hiding in the value)."""

        text = text.strip()
        if "(" in text or " and " in text or " or " in text:
            return None
        m = _URMM_COND.match(text)
        if not m or (m.group(1) and m.group(3)):
            return None
        if m.group(2) in ("True", "False", "None", "not"):
            return None
        return m

    def _urmw_simple(text, was=False):
        """'carol_love >= 3' -> 'Carol love is at least 3'; None if not plain."""

        m = _urmw_match(text)
        if m is None:
            return None
        who = _urmm_pretty(m.group(2))
        if m.group(3):
            said = _URMM_SAY_OP.get(m.group(3))
            if was:
                said = "was" + said[2:]
            return "%s %s %s" % (who, said, _urmm_value(m.group(4)))
        return "%s %s %s" % (who, "was" if was else "is", "off" if m.group(1) else "on")

    _URMW_FLIP = python_dict((
        ("==", "!="), ("!=", "=="), (">=", "<"), ("<", ">="),
        (">", "<="), ("<=", ">"),
    ))

    def _urmw_not(text):
        """The opposite of one plain test, as a test; None if not plain."""

        m = _urmw_match(text)
        if m is None:
            return None
        if m.group(3):
            return "%s %s %s" % (m.group(2), _URMW_FLIP[m.group(3)], m.group(4))
        return m.group(2) if m.group(1) else "not " + m.group(2)

    def _urmw_dice(text):
        return "renpy.random" in text or "random." in text

    def _urmw_say(cond, was=False):
        """
        A test in words: one plain test, two joined by "and", or the part of
        an "or" that holds now. "by chance" for dice. None when it cannot be
        said in words - never code on the chip.
        """

        text = (u"%s" % (cond,)).strip()
        if _urmw_dice(text):
            return "by chance"
        if "(" in text:
            return None
        if " or " in text:
            if " and " in text:
                return None
            for part in text.split(" or "):
                said = _urmw_simple(part, was)
                if said is None:
                    return None
                if _urm_truth(part) is True:
                    return said
            return None
        parts = text.split(" and ")
        if len(parts) > 2:
            return None
        said = None
        for part in parts:
            one = _urmw_simple(part, was)
            if one is None:
                return None
            said = one if said is None else said + " and " + one
        return said

    _URMW_NAME = _urmm_re.compile(r"[A-Za-z_][\w.]*")
    _URMW_QUOTED = _urmm_re.compile(r"""("[^"]*"|'[^']*')""")
    _URMW_NOT_NAMES = frozenset(("and", "or", "not", "in", "is", "True",
                                 "False", "None", "if", "else"))

    # ---- a way of a check: the one place every display titles it from
    #
    # The user's pick 3a (2026-11-20). The map titled the ways of a check
    # "Yes" / "Or" / "Otherwise" with the test in a grey line under it -
    # or with the script label the way jumps to, and "otherwise" in lower
    # case; the cards wrote "Only if <test>". Now, everywhere: the test in
    # plain words, then a chip for what the player has - green when the
    # test holds as things stand, amber when not - and "Otherwise" for the
    # last way. Never "Yes", never "Or", never a script's own name, never
    # code.

    _URMM_WAY_ELSE = "Otherwise"
    _URMM_WAY_UNSAID = "Only sometimes"     # a test that cannot be said in words

    def urm_way_words(cond):
        """
        (title, have, tone) for the way of a check that is taken when cond
        holds. have is "you: 2" - what the player has of the one thing the
        test asks about - or None when the test asks about more than one
        thing, or cannot be judged as the game stands (a name that does
        not exist yet, a call). tone is "gain" when the test holds now,
        "warn" when it does not.
        """

        text = (u"%s" % (cond,)).strip()
        title = _urmw_say(text) if text else None
        if not title:
            return _URMM_WAY_UNSAID, None, None
        title = title[:1].upper() + title[1:]

        m = _urmw_match(text)
        if m is None:
            return title, None, None
        known, now = _urmm_now(m.group(2))
        holds = _urm_truth(text)
        if not known or holds is None:
            return title, None, None
        if m.group(3):
            value = _urmm_value(_urmm_show(now))
        else:
            value = "on" if now else "off"
        return title, u"you: %s" % (value,), ("gain" if holds else "warn")

    _URMM_PICK_TIP = "The game picks the way"

    def urm_pick_tip(lines):
        """What a big diamond says when pointed at; lines: the hover text
        of a small diamond that would stand beside it, or None."""

        if lines:
            return _URMM_PICK_TIP + u"  \u00b7  " + lines
        return _URMM_PICK_TIP

    def urm_guard_tip(guards):
        """What stands behind a diamond in front of a chip: 'Only if Carol
        trust is at least 4'. Never code."""

        said = python_list()
        for guard in guards or ():
            for cond, wanted in (getattr(guard, "tests", None) or ()):
                text = (u"%s" % (cond,)).strip()
                if wanted:
                    one = _urmw_say(text)
                else:
                    flipped = _urmw_not(text)
                    one = _urmw_simple(flipped) if flipped is not None else None
                if one == "by chance":
                    return "Only by chance"
                if one is None:
                    return "Only sometimes: it depends on a check"
                if one not in said:
                    said.append(one)
        if not said:
            return "Only sometimes"
        return "Only if " + " and ".join(said[:3])

    def urm_mark_tip(marks):
        """What a lone diamond stands for, for all the checks of one box
        that only change lines: 'Lines change with Ch8strike, Naomiguilt'."""

        names = python_list()
        for mark in marks:
            for cond, _wanted in (getattr(mark, "tests", None) or ()):
                # Names only: what is inside quotes is a value, not a variable.
                for name in _URMW_NAME.findall(_URMW_QUOTED.sub(u" ", u"%s" % (cond,))):
                    if name in _URMW_NOT_NAMES or name.startswith("renpy."):
                        continue
                    pretty = _urmm_pretty(name)
                    if pretty not in names:
                        names.append(pretty)
        if not names:
            return "Some lines change with a check"
        if len(names) > 3:
            return "Lines change with " + ", ".join(names[:3]) + " and more"
        return "Lines change with " + ", ".join(names)

    def urm_cond_words(cond):
        """'carol_love >= 3' -> 'Carol love is at least 3'; else the code."""

        text = (u"%s" % (cond,)).strip()
        m = _URMM_COND.match(text)
        if m and not (m.group(1) and m.group(3)):
            who = _urmm_pretty(m.group(2))
            if m.group(3):
                return "%s %s %s" % (who, _URMM_SAY_OP.get(m.group(3)),
                                     _urmm_value(m.group(4)))
            return "%s is %s" % (who, "off" if m.group(1) else "on")
        return _urm_clip(text, 48)

    # The one wording for a jump or a call that cannot be followed (idea 8).
    _URMM_DYN_WORDS = "Goes somewhere decided while playing"

    def urm_any_chip(text):
        """urm_map_chip, plus the statements that move the story along."""

        t = text.strip()
        if t == _URMSG_DYN_JUMP or t == _URMSG_DYN_CALL:
            return (_URMM_DYN_WORDS, "other")
        if t.startswith("jump "):
            return ("Goes to %s" % t[5:], "other")
        if t.startswith("call screen "):
            return ("Shows a screen: %s" % _urm_clip(t[12:], 24), "other")
        if t.startswith("call "):
            return ("Plays %s" % t[5:], "other")
        if t == "return":
            return ("Returns", "other")
        return urm_map_chip(t)

    def _urmm_chips(records):
        chips = python_list()
        dyn_said = python_set()
        for guards, text, count in _urm_reduce(_urmm_real(records))[0]:
            # Gallery and achievement unlocks, not the story.
            if text.startswith("persistent."):
                continue
            if _urmm_dyn_again(dyn_said, guards, text):
                continue
            words, tone = urm_any_chip(text)
            if count > 1:
                words += "  x%d" % count
            if guards:
                words += " (sometimes)"
            chips.append((words, tone))
        return chips

    def _urmm_choice_rows(segment):
        """
        Rows for one choice, as (depth, prefix, chips, note): its own changes,
        then the choices inside it as an indented tree - the map's shape in
        text. Merging routes of different depth into one row made unreadable
        lines ("› Check out the noise. › Go to my right. / Be smarter…").
        """

        records, end = segment
        rows = python_list()
        chips = _urmm_chips(records)

        if end[0] != "fork":
            note = _urmm_end_text(end)
            if chips or not note:
                rows.append((0, None, chips, None if chips else "Changes nothing tracked"))
            if note:
                rows.append((0, None, python_list(), note[:1].upper() + note[1:]))
            return rows

        if chips:
            rows.append((0, None, chips, None))

        hidden = [0]

        def walk(seg, depth):
            for label, sub in seg[1][1]:
                if len(rows) >= _URMM_CARD_ROWS:
                    hidden[0] += 1
                    continue
                sub_records, sub_end = sub
                sub_chips = _urmm_chips(sub_records)
                if sub_end[0] == "fork":
                    note = None
                else:
                    note = _urmm_end_text(sub_end)
                    note = (note[:1].upper() + note[1:]) if note else (
                        None if sub_chips else "Changes nothing tracked")
                label = _urmm_arm_label(label)
                if label.startswith("if ") or label == "otherwise":
                    if label == "otherwise":
                        label = _URMM_WAY_ELSE
                    else:
                        # As on the map (urm_way_words): the test in plain
                        # words, then what the player has as the first chip.
                        label, words, tone = urm_way_words(label[3:])
                        if words:
                            sub_chips.insert(0, (words, tone))
                rows.append((depth, u"› " + _urm_clip(label, 44), sub_chips, note))
                if sub_end[0] == "fork":
                    walk(sub, depth + 1)

            # What follows once those ways have met again happens whichever
            # was taken: its changes belong to this level, under no label.
            after = seg[1][3] if len(seg[1]) > 3 else None
            if after is not None:
                after_chips = _urmm_chips(after[0])
                if after_chips and len(rows) < _URMM_CARD_ROWS:
                    rows.append((depth, None, after_chips, None))
                if after[1][0] == "fork":
                    walk(after, depth)

        walk(segment, 0)

        if hidden[0]:
            rows.append((0, None, python_list(),
                         "+%d more - open the map" % hidden[0]))
        return rows

    def urm_matters_line(name, op, literal, where):
        """'Carol nerve matters at ch04begin · needs 3, you have 1'."""

        line = "%s matters at %s" % (_urmm_pretty(name), where)
        if isinstance(literal, bool) or op not in (">=", ">", "<=", "<", "==", "!="):
            return line
        known, now = _urmm_now(name)
        value = _urmm_value(_urmm_show(literal))
        if op in ("==", "!="):
            line += u"  ·  checked for %s%s" % ("not " if op == "!=" else "", value)
            if known and now is not None:
                line += ", now %s" % _urmm_value(_urmm_show(now))
            return line
        need = python_dict(((">=", ""), (">", "over "), ("<=", "at most "),
                            ("<", "under ")))[op] + value
        line += u"  ·  needs %s" % need
        if known and now is not None and not isinstance(now, bool):
            line += ", you have %s" % _urmm_value(_urmm_show(now))
        return line

    def _urmm_choice_view(items, arms, open_flags, later_found):
        """(cards, footer) for a menu - pure, for tests."""

        cards = python_list()
        for n, (item, arm, is_open) in enumerate(zip(items, arms, open_flags)):
            cond = item[1]
            needs = None
            if not _urmsg_no_test(cond):
                needs = ("Needs: " if not is_open else "Only if: ") + urm_cond_words(cond)
            cards.append((
                "" if is_open else u"",
                "muted",
                "%d" % (n + 1),
                _URMM_TAG.sub(u"", u"%s" % (item[0] or u"")).strip(),
                not is_open,
                needs,
                _urmm_choice_rows(arm) if arm is not None else python_list(),
            ))

        footer = python_list()
        seen = python_set()
        for name, _t, where, op, lit in later_found:
            if name in seen:
                continue
            seen.add(name)
            footer.append(urm_matters_line(name, op, lit, where))
        return cards, footer[:3]

    def urm_choice_view():
        """("", cards, footer) for the menu on screen, or None."""

        try:
            choices = x52URM.Choices.currentChoices or []
            if not choices:
                return None
            routes = urm_maze_for(choices)
            menu = _urmm_current_menu()
            items = python_list()
            opens = python_list()
            for c in choices:
                tup = None
                try:
                    tup = c._m1_choices__choice
                except Exception:
                    pass
                if tup is None:
                    tup = (getattr(c, "text", "") or "?", getattr(c, "condition", None), None)
                items.append(tup)
                cond = getattr(c, "condition", None) or "True"
                opens.append(_urmsg_no_test(cond) or _urm_truth(cond) is True)
            arms = routes[0] if routes is not None else [None] * len(items)
            later = python_list()
            if routes is not None and routes[2] is not None:
                later = routes[3] if len(routes) > 3 else python_list()
            cards, footer = _urmm_choice_view(items, arms, opens, later)
            return ("", cards, footer)
        except BaseException:
            return None

    def _urmm_gate_view(steps, truth):
        """Cards for the gates ahead - pure; truth(cond) -> True/False/None."""

        cards = python_list()
        states = _urmsg_gate_states(steps, truth)
        at = 0

        for kind, cond, payload in steps:
            state, number = states[at]
            at += 1
            runs = state == "runs"
            if kind == "gate":
                if runs:
                    icon, tone, needs = u"", "gain", "Runs now"
                elif state == "unknown":
                    icon, tone, needs = u"", "muted", "Can't tell yet"
                else:
                    icon, tone, needs = u"", "muted", "Skipped"
                title = "If " + urm_cond_words(cond)
                records = _urmsg_arm_recs(payload)[0]
            else:
                icon, tone = ((u"", "gain") if runs else
                              (u"", "muted") if state == "unknown" else
                              (u"", "muted"))
                needs = "Runs now" if runs else None
                title = "Otherwise"
                records = (_urmsg_arm_recs(payload)[0] if kind == "else"
                           else python_list([((), payload)]))
            chips = _urmm_chips(records)
            rows = python_list([(0, None, chips, None if chips else "Changes nothing tracked")])
            cards.append((icon, tone, "%d" % number if kind == "gate" else "",
                          title, not runs, needs, rows))

        return cards

    def urm_path_view():
        """("", cards, []) for the gates ahead, or None."""

        try:
            steps = _urm_chain()
            if not steps:
                return None
            cards = _urmm_gate_view(steps, _urm_truth)
            return ("", cards[:_URM_MAX_GATES + 1], python_list())
        except BaseException:
            return None

    # ---- closing a notification until the situation changes

    def _urmm_note_key(kind):
        try:
            if kind == "choices":
                return tuple(id(_urm_choice_nodes(c))
                             for c in (x52URM.Choices.currentChoices or ()))
            detected = x52URM.PathDetection.nextIfStatement
            return tuple(id(n) for n in (detected or ())[:1])
        except Exception:
            return ()

    def urm_note_close(kind):
        try:
            _urmm_st.closed[kind] = _urmm_note_key(kind)
        except AttributeError:
            _urmm_st.closed = python_dict(((kind, _urmm_note_key(kind)),))
        renpy.restart_interaction()

    def urm_note_hidden(kind):
        closed = getattr(_urmm_st, "closed", None)
        if not closed or kind not in closed:
            return False
        key = _urmm_note_key(kind)
        return bool(key) and closed[kind] == key

