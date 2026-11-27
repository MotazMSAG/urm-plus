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
        known, now = _urm_now(m.group(2))
        holds = _urm_truth(text)
        if not known or holds is None:
            return title, None, None
        chip = urm_need_chip(text, holds=holds, named=False)
        if chip is not None:
            return title, chip[0], chip[1]
        if m.group(3):
            value = _urmm_value(_urmm_show(now))
        else:
            value = "true" if now else "false"
        return title, u"you: %s" % (value,), ("gain" if holds else "loss")

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
            return "%s is %s" % (who, "false" if m.group(1) else "true")
        return _urm_clip(text, 48)

    # The one wording for a jump or a call that cannot be followed (idea 8).
    _URMM_DYN_WORDS = "Goes somewhere decided while playing"

    def urm_any_chip(text, omit_grouped=False, with_value=False):
        """urm_map_chip, plus the statements that move the story along; a
        line neither can say is said by what it changes (_urmm_code_chip):
        _URMM_CODE_CHIP when that cannot be told, None when it changes
        nothing of the story (no chip)."""

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
        if t.startswith("while ") and t.endswith(": ..."):
            # The story's own loop (the walk's record) is not a line that
            # writes: it stays as it was (IDEAS, "The story's loop in words").
            return urm_map_chip(t)
        chip = _urmm_call_chip(t, with_value=with_value)
        if chip is not None:
            return chip
        if not _URMM_HUMAN.match(t):
            return _urmm_code_chip(t, omit_grouped)
        return urm_map_chip(t, with_value=with_value)

    # A line of the game's own code that no pattern above can say
    # (Neuvau's increaseStatBalances(lst=1, sub=1, dom=1, exp=1), 2026-11-22)
    # is never shown as code (UX rules 2, 4): it is said by what it changes,
    # as the one reader of what a line writes tells (_urmsg_line_effects,
    # 11), with the names the other chips use. Never an amount: that would
    # be a guess. When what it writes cannot be told, the map's "?" for the
    # game's own code says it (a badge on the map, these words on a card).
    _URMM_CHANGES = u" changes"
    _URMM_CHANGE = u" change"
    _URMM_CODE_CHIP = (_URMM_CODE_TIP, "other")

    def _urmm_code_chip(text, omit_grouped=False):
        """("Victor stats changes", "other") for a line of code: the things
        it writes, in words; _URMM_CODE_CHIP when what it writes cannot be
        told; None when it writes nothing of the story."""

        paths = _urmsg_line_effects(text)
        if paths is None:
            return _URMM_CODE_CHIP
        said = python_list()
        for path in sorted(paths, key=lambda p: python_list(u"%s" % (x,) for x in p)):
            names = python_list(p for p in path if isinstance(p, (str, u"".__class__))
                                and not p.startswith(u"\x00"))
            if not names:
                continue
            if path[0] == _URMSG_ANY:
                words = _urmm_pretty(names[-1])     # whose cannot be told
            else:
                words = _urmm_path_words(u".".join(names))
            if words and words not in said:
                said.append(words)
        if not said or (omit_grouped and len(said) > 1):
            return None
        return (u", ".join(said) + (_URMM_CHANGES if len(said) == 1 else _URMM_CHANGE), "other")

    def _urmm_says_no_amount(chip):
        """A chip that says no amount - what a line changes, an unread
        variable (name only), or the game's own code - so saying it twice
        adds nothing."""

        return (chip == _URMM_CODE_CHIP or chip[1] == "ignored"
                or chip[0].endswith((_URMM_CHANGES, _URMM_CHANGE)))

    def _urmm_chip_name(text):
        """The value a record's change is about, as the one namer says it
        (_urmsg_name: what Search, Remembered and Freeze call it), for the
        user's 4a: a stat chip opens its sheet. A line that sets one target
        (_URMM_HUMAN) names that target - d["k"], a.b[0].c; else, or where
        its key is not a literal, the one place the walk says it writes,
        up to its first item - a part of a container is the container
        (nv_balance for a game function that raises one of its stats).
        None for two places, nothing, or what cannot be told. Only parsed:
        nothing of the game runs."""

        t = (u"%s" % (text,)).strip()
        try:
            paths = _urmsg_line_effects(t)
        except Exception:
            return None
        if not paths or len(paths) != 1:
            return None
        path = tuple(tuple(paths)[0])
        if not path or path[0] is _URMSG_ANY:
            return None
        m = _URMM_HUMAN.match(t)
        if m is not None:
            try:
                name = _urmsg_name(_urmsg_ast.parse(m.group(1).strip(), mode="eval").body)
            except Exception:
                name = None
            if name:
                return name
        parts = python_list()
        for step in path:
            if step == _URMSG_ITEM:
                break
            if not isinstance(step, (str, type(u""))):
                return None
            parts.append(step)
        return u".".join(parts) or None

    def _urmm_unchecked_chip(text, omit_grouped=False):
        """(name, 'ignored') for a variable change no story test reads:
        shows the name dimmed without its value or delta, or None when the
        line writes nothing of the story."""

        t = text.strip()
        m = _URMM_HUMAN.match(t)
        if m is not None:
            name = m.group(1)
            return (_urmm_path_words(name) if "[" in name else _urmm_pretty(name), "ignored")
        paths = _urmsg_line_effects(t)
        if not paths:
            return None
        said = python_list()
        for path in sorted(paths, key=lambda p: python_list(u"%s" % (x,) for x in p)):
            names = python_list(p for p in path if isinstance(p, (str, u"".__class__))
                                and not p.startswith(u"\x00"))
            if not names:
                continue
            words = (_urmm_pretty(names[-1]) if path[0] == _URMSG_ANY
                     else _urmm_path_words(u".".join(names)))
            if words and words not in said:
                said.append(words)
        if not said or (omit_grouped and len(said) > 1):
            return None
        return (u", ".join(said), "ignored")

    def _urmm_chips(records, checked=None, named=False, common=()):
        """Chips for a stretch's changes. checked (_urmsg_checked): a
        change no test of the story reads shows dimmed with its variable
        name only (no value or value change); one that cannot be told is
        kept.
        A chip that says no amount is said once behind the same checks,
        and not at all behind checks when it also always happens (Neuvau
        calls increaseStatBalances with other arguments, behind other
        checks); the game's own code is said once."""

        found = python_list()
        dyn_said = python_set()
        for guards, text, count in _urm_reduce(_urmm_real(records))[0]:
            # Gallery and achievement unlocks, not the story.
            if text.startswith("persistent."):
                continue
            if _urmm_dyn_again(dyn_said, guards, text):
                continue
            omit_grouped = not guards and text in common
            if checked is not None and _urmm_read_later(_urmm_record_keys(text), checked) is False:
                chip = _urmm_unchecked_chip(text, omit_grouped)
            else:
                chip = urm_any_chip(text, omit_grouped, with_value=named)
            if chip is not None:
                found.append((guards, chip, count, text))
        always = python_set(c for g, c, _n, _t in found if not g and _urmm_says_no_amount(c))
        said = python_list()
        chips = python_list()
        for guards, chip, count, text in found:
            words, tone = chip[:2]
            if _urmm_says_no_amount(chip):
                if guards and chip in always:
                    continue
                key = (chip, () if chip == _URMM_CODE_CHIP else tuple(guards))
                if key in said:
                    continue
                said.append(key)
            elif count > 1:
                words += "  x%d" % count
            if guards:
                words += " (sometimes)"
            # named (the corner card): the value the chip is about, or None
            chips.append(((words, tone, _urmm_chip_name(text)) + chip[2:]) if named else (words, tone))
        return chips

    def _urmm_choice_rows(segment, checked=None, named=False, common=()):
        """
        Rows for one choice, as (depth, prefix, chips, note): its own changes,
        then the choices inside it as an indented tree - the map's shape in
        text. Merging routes of different depth into one row made unreadable
        lines ("› Check out the noise. › Go to my right. / Be smarter…").
        """

        records, end = segment
        rows = python_list()
        chips = _urmm_chips(records, checked, named, common)

        # Pick B: changes no test reads are left out, without a word in
        # their place - "Changes nothing tracked" only when there are none.
        left_out = not chips and (checked is not None or common) and bool(_urmm_chips(records))

        if end[0] != "fork":
            note = _urmm_end_text(end)
            if chips or not (note or left_out):
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
                sub_chips = _urmm_chips(sub_records, checked, named)
                sub_left = (not sub_chips and checked is not None
                            and bool(_urmm_chips(sub_records)))
                if sub_end[0] == "fork":
                    note = None
                else:
                    note = _urmm_end_text(sub_end)
                    note = (note[:1].upper() + note[1:]) if note else (
                        None if sub_chips or sub_left else "Changes nothing tracked")
                label = _urmm_arm_label(label)
                if label.startswith("if ") or label == "otherwise":
                    if label == "otherwise":
                        label = _URMM_WAY_ELSE
                    elif named:
                        cond = label[3:]
                        sub_chips[:0] = _urmm_corner_conditions(cond, _urm_truth(cond))
                        label = "Only if"
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
                after_chips = _urmm_chips(after[0], checked, named)
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
        """'Carol nerve matters at ch04begin · you have 1, needs 3' - a
        number test says it as a goal (urm_goal)."""

        line = "%s matters at %s" % (_urmm_pretty(name), where)
        if isinstance(literal, bool) or op not in (">=", ">", "<=", "<", "==", "!="):
            return line
        if op in ("==", "!="):
            known, now = _urm_now(name)
            line += u"  ·  checked for %s%s" % ("not " if op == "!=" else "",
                                                 _urmm_value(_urmm_show(literal)))
            if known and now is not None:
                line += ", now %s" % _urmm_value(_urmm_show(now))
            return line
        goal = urm_goal(name, op, literal)
        return line + u"  ·  " + goal if goal else line

    # ---- what a walked line changes, as the story graph keys it
    #
    # The keys of _urmsg_keys - ("g", a store name) or ("a", an attribute
    # written) - so a change can be held against _urmsg_checked(): every
    # name a test of the story reads, in the whole game, through the game's
    # functions too. A change whose key no test reads is not read later.

    def _urmm_record_keys(text):
        """The keys a walked record changes - _urmsg_line_effects, the one
        reader of what a story line writes (11), keyed by _urmsg_keys: an
        empty set for a line that writes nothing of the story, None when
        that cannot be told."""

        paths = _urmsg_line_effects(text)
        if paths is None:
            return None
        keys = python_set()
        for path in paths:
            keys.update(_urmsg_keys(path))
        return keys

    def _urmm_read_later(keys, checked):
        """True / False / None: does a test of the story read one of these
        keys (None: cannot be told)."""

        if keys is None or checked is None or checked == _URMSG_ANY:
            return None
        for key in keys:
            if key in checked:
                return True
        return False

    def _urmm_call_chip(text, with_value=False):
        """
        (words, tone) for a line that calls one of the game's functions with
        a word and a number - mod_victor('affinity', -4) (Heavenly Vows) -
        when everything it changes belongs to one object of the store: that
        object's name (its own, when it has one), the word, the number.
        None for any other call.
        """

        try:
            body = _urmsg_parse(text.strip()).body
        except Exception:
            return None
        if len(body) != 1 or _urmsg_kind_of(body[0]) != "Expr":
            return None
        call = body[0].value
        if _urmsg_kind_of(call) != "Call" or getattr(call, "keywords", None):
            return None
        words = python_list()
        numbers = python_list()
        for arg in call.args:
            try:
                value = _urm_ast.literal_eval(arg)
            except Exception:
                return None
            if isinstance(value, (str, u"".__class__)):
                words.append(value)
            elif _urm_isnum(value):
                numbers.append(value)
            else:
                return None
        if len(words) != 1 or len(numbers) != 1:
            return None
        writes = _urmsg_line_effects(text)
        if not writes:
            return None
        bases = python_set(path[0] for path in writes)
        if len(bases) != 1:
            return None
        base = bases.pop()
        if not isinstance(base, (str, u"".__class__)) or base.startswith(u"\x00"):
            return None
        adds = _urmm_adds(call)
        if adds is None:
            return None
        sign, shape = adds
        number = numbers[0] * sign
        if shape == "field":
            # victor.stats[stat] += value: Victor affinity -4
            word = _urmm_pretty(words[0])
            said = u"%s %s" % (_urmm_path_words(base), word[:1].lower() + word[1:])
        else:
            # points[who] += n: Elena points +2
            said = u"%s %s" % (_urmm_pretty(words[0]), _urmm_pretty(base).lower())
        return _urmw_value_chip(said, " ", u"%s%s" % ("+" if number > 0 else "", number),
                                "gain" if number > 0 else "loss" if number < 0 else "other", with_value)

    def _urmm_adds(call):
        """(1, shape) when the called function does container[word_param]
        += number_param and nothing else, (-1, shape) for -=, None
        otherwise - so a chip's sign and colour are what the call does, not
        a guess. shape: "field" for an object's container (victor.stats),
        "dict" for a container of the store (points)."""

        called = _urmsg_called(call.func, python_dict())
        if called[0] != "fn" or called[2] is not None:
            return None
        fdef = _urmsg_def_of(called[1])
        if fdef is None:
            return None
        params = python_list()
        for arg in fdef.args.args:
            params.append(getattr(arg, "arg", None) or getattr(arg, "id", None))
        if len(params) != len(call.args):
            return None
        word_param = number_param = None
        for param, arg in zip(params, call.args):
            value = _urm_ast.literal_eval(arg)
            if isinstance(value, (str, u"".__class__)):
                word_param = param
            else:
                number_param = param
        body = python_list()
        for n in fdef.body:
            kind = _urmsg_kind_of(n)
            if kind == "Global":
                continue
            if kind == "Expr":
                value = n.value
                if _urmsg_kind_of(value) in ("Str", "Constant") and isinstance(
                        getattr(value, "s", getattr(value, "value", None)), (str, u"".__class__)):
                    continue        # its docstring
                if (_urmsg_kind_of(value) == "Call"
                        and _urmsg_called(value.func, python_dict())[0] == "other"):
                    continue        # renpy.notify(...): changes nothing of the story
            body.append(n)
        if len(body) != 1 or _urmsg_kind_of(body[0]) != "AugAssign":
            return None
        node = body[0]
        if (_urmsg_kind_of(node.value) != "Name" or node.value.id != number_param
                or _urmsg_kind_of(node.target) != "Subscript"):
            return None
        key = node.target.slice
        if _urmsg_kind_of(key) == "Index":
            key = key.value
        if _urmsg_kind_of(key) != "Name" or key.id != word_param:
            return None
        holder = node.target.value
        shape = ("dict" if _urmsg_kind_of(holder) == "Name" else
                 "field" if _urmsg_kind_of(holder) == "Attribute"
                 and _urmsg_kind_of(holder.value) == "Name" else None)
        if shape is None:
            return None
        if _urmsg_kind_of(node.op) == "Add":
            return 1, shape
        if _urmsg_kind_of(node.op) == "Sub":
            return -1, shape
        return None

    # ---- what a choice costs (idea 15, pick C, 2026-11-21; idea 20 B)
    #
    # For the menu on screen, each choice: does anything it changes get
    # read later, and which later checks does picking it close for good -
    # the check could still pass after another choice here that can be
    # picked, and after this one no pick left gets there (_urm_picks,
    # _urm_reach: 14_facts). The player's question "what does this point
    # do?": nothing (faded), or it costs a scene. Never on a guess (UX rule
    # 21): a change that cannot be tied to a name (a list or dict, a call,
    # the game's own code), a write made only sometimes, a later search cut
    # short, a test that is not the whole condition or one part of an
    # `and` - each gives no answer, so nothing fades and nothing is claimed.

    _URMM_WAYS = 24             # ways through one choice weighed at most
    _URMM_UNREAD = object()     # a value that cannot be worked out
    _URMM_UNSET = object()      # a variable the game has not set yet

    class _URMMWrite(python_object):
        """A write ahead, in the shape _urm_picks reads (14_facts)."""

        def __init__(self, op, value, node):
            self.op = op
            self.value = value
            self.node = node
            self.menu = None
            self.option = None
            self.status = "later"

    def _urmm_ways(segment):
        """
        The records - (guards, text) - along each way through a walked
        choice to where the ways meet again; None when a way ends elsewhere,
        is cut short, or there are more than _URMM_WAYS.
        """

        records, end = segment
        here = python_list(records)
        if end[0] == "meet":
            return python_list([here])
        if end[0] != "fork":
            return None
        after = end[3] if len(end) > 3 else None
        tails = _urmm_ways(after) if after is not None else python_list([python_list()])
        if tails is None:
            return None
        out = python_list()
        for _label, sub in end[1]:
            # With a rejoin of its own, a way ends there ("meet") and what
            # follows is `after`; without one it runs on to the menu's.
            ways = _urmm_ways(sub)
            if ways is None:
                return None
            for way in ways:
                for tail in tails:
                    out.append(here + way + tail)
                    if len(out) > _URMM_WAYS:
                        return None
        return out

    def _urmm_name_of(node):
        """The name the index files a write target by - a.b.c, store.
        dropped - or None for anything else (a list or dict item)."""

        parts = python_list()
        while isinstance(node, _urm_ast.Attribute):
            parts.insert(0, node.attr)
            node = node.value
        if not isinstance(node, _urm_ast.Name):
            return None
        if node.id != "store":
            parts.insert(0, node.id)
        return u".".join(parts) or None

    def _urmm_write_of(text):
        """
        (name, op, literal or _URMM_UNREAD) for a statement that is one
        plain or augmented assignment to one name; "" for a record that
        writes nothing (a mark for lines that change, story text kept in a
        value); None for one that may write anything - two assignments on
        a line, a = b = 0, a list or dict item, a call, the game's own code.
        """

        if not isinstance(text, (str, u"".__class__)):
            return None
        if text.startswith(u"\x00"):
            return None if text == _URMM_MARK_CODE else ""
        if _URMM_SAYS.match(text):
            return ""
        try:
            body = _urm_ast.parse(text.strip()).body
        except Exception:
            return None
        if len(body) != 1:
            return None
        statement = body[0]
        if isinstance(statement, _urm_ast.Assign) and len(statement.targets) == 1:
            target, op = statement.targets[0], "="
        elif isinstance(statement, _urm_ast.AugAssign):
            target = statement.target
            op = ("+=" if isinstance(statement.op, _urm_ast.Add) else
                  "-=" if isinstance(statement.op, _urm_ast.Sub) else "other")
        else:
            return None
        name = _urmm_name_of(target)
        if name is None:
            return None
        if _urmm_reads_in(statement.value):
            return None         # computed from other values, or a call
        return name, op, _urmm_literal_node(statement.value)

    def _urmm_reads_in(node):
        for sub in _urm_ast.walk(node):
            if isinstance(sub, (_urm_ast.Name, _urm_ast.Call, _urm_ast.Attribute)):
                if isinstance(sub, _urm_ast.Name) and sub.id in ("True", "False", "None"):
                    continue
                return True
        return False

    def _urmm_value_after(way, name, start):
        """What `name` holds after one way, from what it held before."""

        value = start
        for guards, text in way:
            write = _urmm_write_of(text)
            if write == "":
                continue
            if write is None or (guards and write[0] == name):
                return _URMM_UNREAD
            wname, op, lit = write
            if wname != name:
                continue
            if lit is _URMM_UNREAD:
                return _URMM_UNREAD
            if op == "=":
                value = lit
            elif op in ("+=", "-=") and _urm_isnum(lit) and _urm_isnum(value):
                value = value + lit if op == "+=" else value - lit
            else:
                return _URMM_UNREAD
        return value

    _URMM_COMPARE = python_list()
    for _urmm_pair in (("GtE", ">="), ("Gt", ">"), ("LtE", "<="), ("Lt", "<"),
                       ("Eq", "=="), ("NotEq", "!=")):
        if hasattr(_urm_ast, _urmm_pair[0]):
            _URMM_COMPARE.append((getattr(_urm_ast, _urmm_pair[0]), _urmm_pair[1]))

    def _urmm_test_part(part):
        """(name, op, literal) for one simple test, or None."""

        name = _urmm_name_of(part)
        if name is not None:
            return (name, "truthy", None)
        if isinstance(part, _urm_ast.UnaryOp) and isinstance(part.op, _urm_ast.Not):
            name = _urmm_name_of(part.operand)
            return (name, "falsy", None) if name is not None else None
        if not isinstance(part, _urm_ast.Compare) or len(part.ops) != 1:
            return None
        name = _urmm_name_of(part.left)
        if name is not None:
            for kind, op in _URMM_COMPARE:
                if isinstance(part.ops[0], kind):
                    lit = _urmm_literal_node(part.comparators[0])
                    return None if lit is _URMM_UNREAD else (name, op, lit)
            return None
        name = _urmm_name_of(part.comparators[0])
        if name is not None and isinstance(part.ops[0], (_urm_ast.In, _urm_ast.NotIn)):
            lit = _urmm_literal_node(part.left)
            if lit is not _URMM_UNREAD:
                return (name, "in" if isinstance(part.ops[0], _urm_ast.In) else "not in", lit)
        return None

    def _urmm_tests_of(cond):
        """
        [(name, op, literal)] for a condition that is one simple test, or
        an `and` of simple tests - the shapes whose outcome follows from
        each part. None for any other (an `or`, a `not` around a
        comparison, a sum, a call).
        """

        try:
            body = _urm_ast.parse(u"%s" % (cond,), mode="eval").body
        except Exception:
            return None
        parts = (body.values if isinstance(body, _urm_ast.BoolOp)
                 and isinstance(body.op, _urm_ast.And) else [body])
        tests = python_list()
        for part in parts:
            test = _urmm_test_part(part)
            if test is None:
                return None
            tests.append(test)
        return tests

    def _urmm_literal_node(node):
        try:
            return _urm_ast.literal_eval(node)
        except Exception:
            return _URMM_UNREAD

    _URMM_PLAIN_STATEMENTS = frozenset((u"play", u"queue", u"stop", u"pause",
                                        u"window", u"voice", u"nvl"))

    def _urmm_code_reads(statements):
        """
        (names the game reads in its python lines ahead, and unsure):
        unsure when one of those lines or a test ahead calls something,
        whose reads cannot be known, or cannot be read; when a jump or call
        ahead goes where the game works out while playing (the search
        cannot follow it - the names in its expression are read); and at a
        custom statement, which may hold anything - a screen's code - but
        for the engine's own sound, pause, window and voice statements,
        which play what they are given and decide nothing. A plain write
        of a name is not a read of it. What a test reads is the index's.
        """

        names = python_set()
        unsure = False
        for node in statements:
            kind = _urmsg_kind(node)
            texts = python_list()
            if kind == _URMSG_K_PY:
                texts.append((getattr(getattr(node, "code", None), "source", None), "exec"))
            elif kind in (_URMSG_K_JUMP, _URMSG_K_CALL):
                if getattr(node, "expression", False):
                    unsure = True
                    texts.append((getattr(node, "target", None)
                                  or getattr(node, "label", None), "eval-read"))
            elif kind == _URMSG_K_USER:
                word = (u"%s" % (getattr(node, "line", u"") or u"")).split()[:1]
                if not word or word[0] not in _URMM_PLAIN_STATEMENTS:
                    unsure = True
            elif kind in (_URMSG_K_IF, _URMSG_K_WHILE):
                for cond, _block in (getattr(node, "entries", None)
                                     or [(getattr(node, "condition", None), None)]):
                    texts.append((cond, "eval"))
            elif kind == _URMSG_K_MENU:
                for item in node.items:
                    texts.append((item[1], "eval"))
            for text, mode in texts:
                if text is None:
                    continue
                try:
                    tree = _urm_ast.parse(u"%s" % (text,), mode="exec" if mode == "exec" else "eval")
                except Exception:
                    unsure = True
                    continue
                for sub in _urm_ast.walk(tree):
                    if isinstance(sub, _urm_ast.Call):
                        unsure = True
                    elif mode != "eval" and isinstance(sub, (_urm_ast.Name, _urm_ast.Attribute)) and isinstance(
                            getattr(sub, "ctx", None), _urm_ast.Load):
                        name = _urmm_name_of(sub)
                        if name is not None:
                            names.add(name)
                            if u"." in name:
                                names.add(name.split(u".")[0])
        return names, unsure

    def _urmm_test_holds(value, op, lit):
        if op == "truthy":
            return bool(value)
        if op == "falsy":
            return not value
        if op == "in":
            return lit in value
        if op == "not in":
            return lit not in value
        if op == ">=":
            return value >= lit
        if op == ">":
            return value > lit
        if op == "<=":
            return value <= lit
        if op == "<":
            return value < lit
        if op == "==":
            return value == lit
        return value != lit

    def _urmm_can_pass(value, op, lit, ahead, picks):
        """True / False / None: can a test still pass from this value, with
        the picks and writes ahead."""

        if value is _URMM_UNREAD or value is _URMM_UNSET:
            return None
        try:
            if _urmm_test_holds(value, op, lit):
                return True
        except Exception:
            return None
        if op in (">=", "<=", ">", "<") and _urm_isnum(value) and _urm_isnum(lit):
            if op in (">", "<") and not (isinstance(lit, int) and isinstance(value, int)):
                return None
            target = lit + (1 if op == ">" else -1 if op == "<" else 0)
            reach = _urm_reach(target - value, *picks)
            return None if reach is None else reach != "loss"
        unknown = False
        for w in ahead:
            if w.op != "=" or not _urm_value_ok(w):
                unknown = True
                continue
            try:
                if _urmm_test_holds(w.value, op, lit):
                    return True
            except Exception:
                unknown = True
        return None if unknown else False

    def _urmm_ahead(index, name, dist):
        """The writes of `name` that can run later, and _urm_picks of them."""

        ahead = python_list()
        menus = python_dict()
        order = python_list()
        auto = python_list()
        done = python_set()
        for site, op, value, _text in index.writes.get(name) or ():
            if dist.get(site[2]) is None:
                continue
            key = (site[2], op, repr(value))
            if key in done:
                continue
            done.add(key)
            node = index.nodes.get(site[2])
            w = _URMMWrite(op, value, node)
            for parent, kind, extra in _urmsg_climb(index.parent, node):
                if kind == "option":
                    w.menu = parent
                    w.option = extra
                    break
                if kind == "label":
                    break
            ahead.append(w)
            if w.menu is None:
                auto.append(w)
            else:
                group = menus.get(id(w.menu))
                if group is None:
                    group = menus[id(w.menu)] = python_list()
                    order.append(w.menu)
                group.append(w)
        return ahead, _urm_picks(menus, order, auto, None)

    def _urmm_check_of(node):
        """([(name, op, literal)], place) for a later check that decides
        what the player sees, or None. place: the first line it lets the
        player see, or the choice it opens. Only an if's first test (a
        later one also needs the ones before it to fail) and a choice's own
        condition; the test a whole simple test or an `and` of them."""

        try:
            kind = _urmsg_kind(node)
            if kind == _URMSG_K_IF and node.entries:
                cond, block = node.entries[0]
                tests = _urmm_tests_of(cond) if cond else None
                if tests is None:
                    return None
                for say in _urmsg_says_in(block):
                    text = _urmp_plain(getattr(say, "what", "") or "", 48)
                    if text:
                        return tests, u'"%s"' % text
                return tests, u"a later scene"
            if kind == _URMSG_K_MENU:
                for item in node.items:
                    tests = _urmm_tests_of(item[1]) if item[1] else None
                    if tests is not None:
                        return tests, u'the choice "%s"' % _urm_clip(
                            _URMM_TAG.sub(u"", u"%s" % (item[0] or u"")).strip(), 40)
        except Exception:
            pass
        return None

    def urm_choice_costs(arms, index, dist, opens=None, code=None, checked=None):
        """
        [(matters, [places it loses], sure, known)] per choice, or None
        without an index. known: every way through the choice was followed
        to where the ways meet, and every change in it is held against
        `checked` (_urmsg_checked: every name a test of the story reads) -
        a menu whose choices are all known and none matters is flavour.
        matters: something it changes is read by a test, or it loses a
        check. sure: known, and every later check of what the choices
        change was worked out for every choice, so this one can be faded
        alone (dist: what can run later, None when that search was cut;
        code: _urmm_code_reads of it). opens: whether each choice can be
        picked; a locked one keeps nothing open and is said to lose nothing.
        """

        if not arms or index is None:
            return None
        usable = checked is not None and checked != _URMSG_ANY
        if opens is None:
            opens = python_list(True for _a in arms)
        code_names, doubt = code if code is not None and dist is not None else (python_set(), True)
        ways = python_list(_urmm_ways(arm) for arm in arms)
        held = python_list()        # known, matters by the whole game's tests
        for way_list in ways:
            read = False if usable and way_list is not None else None
            for way in way_list or ():
                for _guards, text in way:
                    later = _urmm_read_later(_urmm_record_keys(text), checked)
                    if later is None:
                        read = None
                    elif later and read is not None:
                        read = True
                if read is None:
                    break
            held.append(read)
        written = python_list()
        names = python_list()
        known = python_list()
        for way_list in ways:
            mine = python_set()
            ok = way_list is not None
            for way in way_list or ():
                for _guards, text in way:
                    write = _urmm_write_of(text)
                    if write is None:
                        ok = False
                    elif write:
                        mine.add(write[0])
                        if write[0] not in names:
                            names.append(write[0])
            written.append(mine)
            known.append(ok)
        matters = python_list(False for _a in arms)
        lost = python_list(python_list() for _a in arms)
        if not all(known):
            doubt = True        # one choice unknown: no other is sure

        sites = python_list()
        for name in (names if dist is not None else ()):
            read = name in code_names
            if read:
                doubt = True    # read in the game's code: not worked out
            for site, _op, _lit in index.reads.get(name) or ():
                if dist.get(site[2]) is not None:
                    read = True
                    if site[2] not in sites:
                        sites.append(site[2])
            if read:
                for i in range(len(arms)):
                    if name in written[i]:
                        matters[i] = True

        facts = python_dict()       # name -> (start, ahead, picks)

        def can_pass(way, name, op, lit):
            if name not in facts:
                is_set, now = _urm_now(name)
                ahead, picks = _urmm_ahead(index, name, dist)
                facts[name] = (now if is_set else _URMM_UNSET, ahead, picks)
            start, ahead, picks = facts[name]
            return _urmm_can_pass(_urmm_value_after(way, name, start), op, lit, ahead, picks)

        for nid in sites:
            check = _urmm_check_of(index.nodes.get(nid))
            if check is None:
                doubt = True
                continue
            tests, place = check
            per = python_list()
            for i in range(len(arms)):
                if not ways[i]:
                    per.append(None)
                    continue
                found = python_list()
                for way in ways[i]:
                    parts = python_list(can_pass(way, n, op, lit) for n, op, lit in tests)
                    found.append(False if False in parts else
                                 True if all(p is True for p in parts) else None)
                if True in found:
                    per.append(True)
                elif all(f is False for f in found):
                    per.append(False)
                else:
                    per.append(None)
            if None in per:
                doubt = True
            if not any(can is True and opens[i] for i, can in enumerate(per)):
                continue
            for i, can in enumerate(per):
                if can is False and opens[i] and place not in lost[i]:
                    lost[i].append(place)

        return python_list((bool(held[i]) or matters[i] or bool(lost[i]), lost[i],
                            known[i] and not doubt and held[i] is not None,
                            held[i] is not None)
                           for i in range(len(arms)))

    _URMM_FLAVOUR = "Flavour only"

    def _urmm_choice_title(text):
        """Substitute [var] placeholders in choice text and strip text tags."""
        raw = u"%s" % (text or u"")
        if u"[" in raw:
            try:
                raw = renpy.substitute(raw)
            except Exception:
                pass
        return _urm_player_text(_URMM_TAG.sub(u"", raw).strip())

    def _urmm_common_changes(arms):
        """Unguarded source records made equally often in every choice.
        Compare the original records because distinct expressions can write
        the same names. The compact card hides only their grouped fallback."""

        if len(arms) < 2:
            return ()
        common = None
        for arm in arms:
            if arm is None:
                return ()
            counts = python_dict()
            for guards, text in arm[0]:
                if not guards and (common is None or text in common):
                    counts[text] = counts.get(text, 0) + 1
            common = counts if common is None else python_dict(
                (text, count) for text, count in counts.items() if common.get(text) == count)
            if not common:
                return ()
        return common

    def _urmm_choice_view(items, arms, open_flags, later_found, costs=None, checked=None, named=False):
        """(cards, footer) for a menu - pure, for tests. costs: what
        urm_choice_costs says, or None; checked: _urmsg_checked, or None."""

        if costs and all(known and not matters for matters, _lost, _sure, known in costs):
            # Idea 20 B: a menu where nothing matters shrinks to one line.
            return python_list([(u"", "muted", u"", _URMM_FLAVOUR, True, None,
                                 python_list())]), python_list()

        common = _urmm_common_changes(arms) if named and len(items) == len(arms) else ()
        cards = python_list()
        for n, (item, arm, is_open) in enumerate(zip(items, arms, open_flags)):
            # Idea 20 B: a choice whose changes the game never checks, and
            # that closes nothing, is faded.
            flavour = bool(costs) and costs[n][2] and not costs[n][0]
            cond = item[1]
            needs = None
            if not _urmsg_no_test(cond):
                needs = ("Needs: " if not is_open else "Only if: ") + urm_cond_words(cond)
            cards.append((
                "" if is_open else u"",
                "muted",
                "%d" % (n + 1),
                _urmm_choice_title(item[0]),
                not is_open or flavour,
                needs,
                _urmm_choice_rows(arm, checked, named, common) if arm is not None else python_list(),
            ))

        footer = python_list()
        seen = python_set()
        for name, _t, where, op, lit in later_found:
            if name in seen:
                continue
            seen.add(name)
            footer.append(urm_matters_line(name, op, lit, where))
        return cards, footer[:3]

    def urm_choice_view(named=False):
        """("", cards, footer) for the menu on screen, or None. named: each
        chip says the value it is about (the corner card)."""

        try:
            choices = _urm_choices_here()
            if not choices:
                return None
            routes = urm_maze_for(choices)
            items = python_list()
            opens = python_list()
            for _i, text, cond, block in choices:
                items.append((text, cond, block))
                cond = cond or "True"
                opens.append(_urmsg_no_test(cond) or _urm_truth(cond) is True)
            arms = routes[0] if routes is not None else [None] * len(items)
            later = python_list()
            costs = None
            checked = _urmsg_checked()
            if routes is not None and routes[2] is not None:
                later = routes[3] if len(routes) > 3 else python_list()
                if len(routes) > 4:
                    costs = urm_choice_costs(arms, _urmi_index(), routes[4], opens,
                                             routes[5] if len(routes) > 5 else None,
                                             checked)
            cards, footer = _urmm_choice_view(items, arms, opens, later, costs, checked, named)
            # Idea 15 C: per card, the later scenes picking it closes for
            # good - beside the cards, whose shape the other views share.
            lost = python_list(python_list(c[1]) if costs and is_open and len(cards) == len(costs)
                               else python_list() for c, is_open in zip(costs or (), opens))
            return ("", cards, footer, lost)
        except BaseException:
            return None

    def _urmm_gate_view(steps, truth, ways=None, named=False):
        """Cards for the gates ahead - pure; truth(cond) -> True/False/None;
        ways: the chain's way facts (_urmsg_gate_read)."""

        cards = python_list()
        states = _urmsg_gate_read(steps, truth, ways)
        at = 0

        for kind, cond, payload in steps:
            state, number, _told = states[at]
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
            chips = _urmm_chips(records, named=named)
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
            ways = python_list(getattr(_URMMemory, "chain_ways", None) or ())
            cards = _urmm_gate_view(steps, _urm_truth, ways if len(ways) == len(steps) else None)
            return ("", cards[:_URM_MAX_GATES + 1], python_list())
        except BaseException:
            return None

    # ---- closing a notification until the situation changes

    def _urmm_note_key(kind):
        try:
            if kind == "choices":
                return tuple(id(c[3]) for c in _urm_choices_here())
            gate = _urm_gate_ahead()
            return (id(gate),) if gate is not None else ()
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

    # ---- the corner card (the user's pick 1a, 2026-11-22: "Corner card")
    #
    # Our own Path and Choices pop-ups (road step A4), drawn by
    # game_screens/34_corner.rpy: a glass card top right, one row per
    # choice or way, a number where the player picks and a diamond where
    # the game picks, Take on the row pointed at, the route map and close
    # in its header; always open (2a). This hands the screen finished,
    # plain data - words, tones, numbers - and never a statement: the
    # screen's variables go into saves. Take asks again when clicked.
    #
    # A card is (kind, title, flavour, rows, foot):
    #   kind     "choices" or "paths" (what urm_note_close and Take take)
    #   flavour  a menu where nothing matters (idea 20 B): said once, by
    #            the title
    #   rows     (mark, locked, text, dim, tag, lines, lost, take)
    #     mark   ("num", "2") for a choice, ("diamond", None) for a test the
    #            game makes, ("dot", tone) for "Otherwise"
    #     locked a choice the player cannot pick now (a lock before it)
    #     tag    (words, tone) after the text - "HAPPENS NOW" - or None
    #     lines  [(depth, prefix, chips, note)]: chips [(words, tone)]
    #     lost   picking it closes a later scene for good (a red edge)
    #     take   Take is offered on it (not on the way that happens anyway)
    #   foot     muted lines: what the menu's flags decide later

    _urm_setting_add("showChoicesNotification", True)
    _urm_setting_add("showPathsNotification", True)
    _urm_setting_add("stopSkippingOnPathDetection", False)

    # their rows on the URM+ settings page (the registry, 01_urm_door); URM's
    # options page shows the same values, through the door
    _urm_row_add("corner_choices", "story", "Choices card",
                 "Shows the choices on screen in the corner: what each one does, and Take.",
                 (("On", True), ("Off", False)), setting="showChoicesNotification", order=20)
    _urm_row_add("corner_paths", "story", "Path card",
                 "Shows the ways the game will pick between next, in the corner.",
                 (("On", True), ("Off", False)), setting="showPathsNotification", order=21)
    _urm_row_add("stop_at_check", "skipping", "Stop skipping at a check",
                 "Skipping stops when the game is about to pick a way by a check.",
                 (("On", True), ("Off", False)), setting="stopSkippingOnPathDetection", order=40)
    # How far the reader the card shows looks ahead (13_now keeps it).
    _urm_row_add("look_ahead", "skipping", "Path look-ahead",
                 "How far ahead to look for the next choice. Raise it if a long scene hides one.",
                 (("20", 20), ("50", 50), ("100", 100), ("200", 200)), setting="urmcLookAhead",
                 order=50)

    _URMM_NOW = "HAPPENS NOW"
    # The card's sizes at 1080 lines: width, the card's room at the sides,
    # a row's room at the sides, the mark's column, the gap to the screen's
    # edge, the room kept for Take beside a row's words. The rest is the
    # kit's.
    _URMM_CORNER = (460, 12, 8, 28, 16, 0)
    _URMM_TAKEN = "TAKEN"
    _URMM_UNSURE = "CAN'T TELL YET"

    def _urmm_corner_conditions(cond, holds, fallback=True):
        """Need chips in the exact logical order, or a neutral grouped check."""

        if holds is not None:
            chips = urm_need_chips(cond, holds=holds, joiners=True, with_value=True)
            if chips:
                return chips
        if not fallback:
            return ()
        words = _urmw_corner_fallback((u"%s" % (cond,)).strip())
        tone = "gain" if holds is True else ("loss" if holds is False else "plain")
        return [(words, tone)]

    def _urmm_goal_chip(cond, holds, named=False, key=False):
        """(words, tone) saying what a test needs via urm_need_chip - '2/3'
        or 'Rae love 2/3', 'Orphan' or 'Nadia alive: no' - green when it
        holds, red when not; or None."""

        text = (u"%s" % (cond,)).strip()
        chip = urm_need_chip(text, holds=holds, named=named)
        if chip is None:
            return None
        if key:
            # the value its test reads (the user's 4a)
            m = _urmw_match(text)
            return (chip[0], chip[1], m.group(2) if m is not None else None)
        return chip

    def _urmm_strip_no_track(raw_lines):
        """Drop standalone 'Changes nothing tracked' lines; on sub-way
        lines with a prefix, clear only the note so the row stays."""

        out = python_list()
        for d, pre, chips, note in raw_lines:
            if not chips and note == u"Changes nothing tracked":
                if pre:
                    out.append((d, pre, chips, None))
            else:
                out.append((d, pre, chips, note))
        return out

    def _urmm_corner_chip_key(chip):
        if len(chip) > 2 and chip[2]:
            return u"%s" % (chip[2],)
        w = u"%s" % (chip[0],)
        for sep in (u": ", u" +", u" -", u" x", u" /"):
            if sep in w:
                return w.split(sep, 1)[0].strip().lower()
        return w.strip().lower()

    def _urmm_corner_clean_lines(raw_lines):
        """Clean and group Choices-card rows (3b): drop code-plumbing chips,
        'Changes nothing tracked', and '+N more - open the map'; on top-level
        rows deduplicate by variable (preferring unconditional over (sometimes))
        and sort deltas before sets."""

        out = python_list()
        for d, pre, chips, note in raw_lines:
            kept_chips = python_list(c for c in chips if c[0] != _URMM_CODE_CHIP[0])
            clean_note = note
            if clean_note and (clean_note == u"Changes nothing tracked"
                               or (clean_note.startswith(u"+") and u"more - open the map" in clean_note)):
                clean_note = None
            if not kept_chips and not clean_note and not pre:
                continue
            if d == 0 and pre is None and kept_chips:
                best = python_dict()
                for c in kept_chips:
                    k = _urmm_corner_chip_key(c)
                    rank = (0 if c[1] == "ignored" else 1, 0 if u"(sometimes)" in c[0] else 1)
                    prev = best.get(k)
                    if prev is None or rank > prev[0]:
                        best[k] = (rank, c)
                tone_order = {"gain": 0, "loss": 0, "set": 1, "other": 2, "ignored": 3}
                kept_chips = python_list(
                    v[1] for _k, v in sorted(best.items(), key=lambda kv: (tone_order.get(kv[1][1][1], 2), kv[0])))
            out.append((d, pre, kept_chips, clean_note))
        return out

    def _urmm_corner_footer(footer):
        """Strip raw script label names from corner-card footer lines."""
        out = python_list()
        for line in footer:
            if u" matters at " in line:
                head, rest = line.split(u" matters at ", 1)
                idx = rest.find(u"  \u00b7  ")
                suffix = rest[idx:] if idx != -1 else u""
                out.append(head + u" matters later" + suffix)
            else:
                out.append(line)
        return out

    def _urmm_corner_choices(choices, view):
        """The choices card for the menu on screen - pure, for tests.
        choices: _urm_choices_here(); view: urm_choice_view()."""

        _blank, cards, footer, lost = view
        # Idea 20 B: a menu where nothing matters is one "Flavour only"
        # card in the view; here every choice keeps its row (and its Take).
        flavour = (len(cards) == 1 and cards[0][3] == _URMM_FLAVOUR and cards[0][2] == u"")
        rows = python_list()
        for n, (_i, text, cond, _block) in enumerate(choices):
            cond = cond or "True"
            no_test = _urmsg_no_test(cond)
            truth = None if no_test else _urm_truth(cond)
            is_open = no_test or truth is True
            card = None if flavour or n >= len(cards) else cards[n]
            lines = python_list()
            if not no_test:
                lines.append((0, None, _urmm_corner_conditions(cond, truth), None))
            if card is not None:
                lines.extend(_urmm_corner_clean_lines(card[6]))
            places = lost[n] if n < len(lost) else ()
            if places:
                lines.append((0, None, python_list((u"You lose %s" % p, "loss") for p in places), None))
            title = _urmm_choice_title(text) or u"?"
            dim = (not is_open) or flavour or (card is not None and card[4])
            rows.append((("num", u"%d" % (n + 1)), not is_open, title, dim, None, lines,
                         bool(places), True))
        return ("choices", u"Choices", flavour, rows, _urmm_corner_footer(footer))

    # The row after the last check, when the story also gets there after a
    # way of it that carries on (the checks are separate if-statements).
    _URMM_WAY_THEN = "Then"
    _URMM_SCENE_NOTES = (u"Goes to ", u"Goes somewhere", u"Plays ", u"Returns", u"Ends the scene", u"Ends the game", u"Loops back")

    def _urmm_corner_ways(steps, cards, taken, ways=None, told=None):
        """The Active Path corner card - pure, for tests. Title is
        'Active Path (Scene)' when a way changes scene, else
        'Active Path (Dialogue)'; no 'HAPPENS NOW' or 'Changes nothing
        tracked'; readable conditions render as green/red chips with
        'and'/'or' joiners."""

        is_scene = bool(ways and any(w[1] is True for w in ways))
        rows = python_list()
        for at, ((kind, cond, _payload), card) in enumerate(zip(steps, cards)):
            _icon, _tone, _num, _title, _dim, needs, card_lines = card
            lines = _urmm_strip_no_track(card_lines)
            if not is_scene:
                for _d, _p, c_list, note in lines:
                    if (note and note.startswith(_URMM_SCENE_NOTES)) or any(
                        c[0].startswith(_URMM_SCENE_NOTES) for c in c_list
                    ):
                        is_scene = True
                        break
            dim = False
            if taken is not None:
                tag = (_URMM_TAKEN, "accent-ink") if at == taken else None
                dim = at != taken
            elif needs == "Can't tell yet":
                tag = (_URMM_UNSURE, "ink-muted")
            else:
                tag = None
            happens = (at == taken) if taken is not None else (needs == "Runs now")
            tone_mark = "gain" if (happens and not dim) else "ink-muted"
            if kind == "gate":
                can_read = (told is None or told[at])
                holds = _urm_truth(cond) if can_read else None
                chips = _urmm_corner_conditions(cond, holds, fallback=False)
                if chips:
                    title = u""
                    lines.insert(0, (0, None, chips, None))
                else:
                    title = _urmw_corner_fallback((u"%s" % (cond,)).strip())
                mark = ("diamond", tone_mark)
            else:
                title = _URMM_WAY_ELSE
                if kind == "tail" and ways is not None and at < len(ways):
                    last = python_list(w[1] for w in ways[:at] if w[0] == ways[at][0] - 1)
                    if not all(leaves is True for leaves in last):
                        title = _URMM_WAY_THEN
                mark = ("dot", tone_mark)
            rows.append((mark, False, title, dim, tag, lines, False, not happens))
        card_title = u"Active Path (Scene)" if is_scene else u"Active Path (Dialogue)"
        return ("paths", card_title, False, rows, python_list())

    def _urmm_taken_step(meta):
        """Which step of the chain a pending Take sends the game down, or
        None when no Take waits on it: the step whose arm is taken, or the
        tail when what waits is only checks falling through. meta: the
        chain's (if-statement, arm) per step, (None, -1) for the tail."""

        through = False
        for at, (node, arm) in enumerate(meta):
            if node is None:
                return at if through else None
            wants = _urm_taken(node)
            if wants == arm:
                return at
            if wants == -1:
                through = True
        return None

    def _urmm_path_key(chain):
        """The ordered source locations and exact conditions of the checks."""

        if chain.cut:
            return None
        seen = python_set()
        gates = python_list()
        for node, _arm in chain.meta:
            if node is None or id(node) in seen:
                continue
            seen.add(id(node))
            filename = (getattr(node, "filename", None) or u"").replace("\\", "/")
            line = getattr(node, "linenumber", 0)
            if _urm_os.path.isabs(filename):
                base = config.basedir.replace("\\", "/").rstrip("/") + "/"
                if not filename.lower().startswith(base.lower()):
                    return None
                filename = filename[len(base):]
            if not filename or filename.startswith(("<", "../")) or not line:
                return None
            tests = tuple(_urm_plain_words(cond) for cond, _block in node.entries
                          if not _urmsg_is_else(cond))
            if not tests:
                return None
            gates.append((filename, line, tests))
        return tuple(gates) if gates else None

    def _urmm_path_notice(gate, ignored, mutes):
        """One chain per interaction, shared by stop skipping and the card."""

        if gate is None:
            return None
        here = _urmsg_here()
        cached = getattr(_urmm_st, "path_notice", None)
        if cached is None or cached[0] is not here or cached[1] is not gate:
            chain = _urm_read_chain(gate)
            if chain is None or not chain.steps:
                return None
            cached = (here, gate, chain, _urmm_path_key(chain))
            _urmm_st.path_notice = cached
        chain, key = cached[2:]
        if _urm_chain_ignored(chain, ignored) or (key and mutes and _urm_path_is_muted(key, mutes)):
            return None
        return chain, key

    def urm_corner_mute_key():
        # The screen gets only plain values. It has just drawn this chain.
        notice = getattr(_urmm_st, "path_notice", None)
        return notice[3] if notice is not None else None

    _URMM_MUTE_COMPARE = python_dict((
        ("Eq", "=="), ("NotEq", "!="), ("GtE", ">="),
        ("Gt", ">"), ("LtE", "<="), ("Lt", "<"),
    ))

    def _urmm_mute_location(value):
        return isinstance(value, _urmsg_texts) and (
            value.lower().endswith((".rpy", ".rpyc")) or _urmw_names_label(repr(value)))

    def _urmm_mute_operand(node):
        name = _urmsg_name(node)
        if name is not None:
            return _urmm_pretty(name)
        known, value = _urmsg_literal(node)
        if not known:
            return None
        if isinstance(value, _urmsg_texts):
            return u"\u201c%s\u201d" % value
        return _urmm_value(u"%s" % value)

    def _urmm_mute_words(node):
        """Say the parsed condition, with no value read from the game."""

        kind = _urmsg_kind_of(node)
        if kind == "BoolOp":
            parts = python_list()
            for child in node.values:
                words = _urmm_mute_words(child)
                if words is None:
                    return None
                parts.append(u"(%s)" % words if _urmsg_kind_of(child) == "BoolOp" else words)
            return (u" and " if _urmsg_kind_of(node.op) == "And" else u" or ").join(parts)
        if kind == "UnaryOp" and _urmsg_kind_of(node.op) == "Not":
            name = _urmsg_name(node.operand)
            if name is not None:
                return u"%s is false" % _urmm_pretty(name)
            words = _urmm_mute_words(node.operand)
            return u"not (%s)" % words if words is not None else None
        if kind == "Compare" and len(node.ops) == 1:
            op = _URMM_MUTE_COMPARE.get(_urmsg_kind_of(node.ops[0]))
            left, right = _urmm_mute_operand(node.left), _urmm_mute_operand(node.comparators[0])
            if op and left is not None and right is not None:
                return u"%s %s %s" % (left, _URMM_SAY_OP[op], right)
        name = _urmsg_name(node)
        if name is not None:
            return u"%s is true" % _urmm_pretty(name)
        return None

    def _urmm_mute_condition(condition):
        text = condition.strip()
        try:
            node = _urmsg_parse(text, "eval").body
            for child in _urmsg_pyast.walk(node):
                known, value = _urmsg_literal(child)
                if known and _urmm_mute_location(value):
                    return u"Check about a script location"
            words = _urmm_mute_words(node)
            if words is not None:
                return words
        except (SyntaxError, ValueError, RuntimeError):
            pass
        return text

    def _urmm_mute_title(key):
        gates = (u" \u00b7 Otherwise if ".join(_urmm_mute_condition(cond) for cond in tests)
                 for _filename, _line, tests in key)
        title = u" \u00b7 Then checks ".join(gates)
        title = title.replace(u"\r", u"\\r").replace(u"\n", u"\\n").replace(u"\t", u"\\t")
        return urm_map_esc(_urm_clip(title, 280))

    def urm_corner_mute_ask(key):
        """Capture the notification as it was when the bell was pressed."""

        title = _urmm_mute_title(key)
        here = _urmsg_here()
        if isinstance(here, renpy.ast.Translate) and getattr(here, "block", None):
            here = here.block[0]
        cue = None
        if isinstance(here, renpy.ast.Say):
            said = _urmp_plain(_urm_player_text(here.what), 64)
            if said and "[" not in said:
                cue = u"\u201c%s\u201d" % said
        renpy.show_screen("urm_corner_mute", key, title, cue, _layer=_urmi_layer)
        renpy.restart_interaction()

    def urm_corner_mute_close(key=None, title=None, cue=None):
        renpy.hide_screen("urm_corner_mute", layer=_urmi_layer)
        if key is not None:
            _urm_path_mute(key, title, cue)
        renpy.restart_interaction()

    def urm_corner_view():
        """The cards to draw now, [] when there is nothing to say."""

        out = python_list()
        try:
            if not _urm_in_game():
                return out
        except Exception:
            return out
        try:
            if _urm_setting("showChoicesNotification") and not urm_note_hidden("choices"):
                choices = _urm_choices_here()
                view = urm_choice_view(named=True) if choices else None
                if view is not None:
                    out.append(_urmm_corner_choices(choices, view))
        except BaseException:
            pass
        try:
            if _urm_setting("showPathsNotification") and not urm_note_hidden("paths"):
                notice = _urmm_path_notice(_urm_gate_ahead(), _urm_ignored_names("path"),
                                           _urm_path_mutes())
                if notice is not None:
                    chain, _key = notice
                    steps, meta, ways = chain.steps, chain.meta, chain.ways
                    _URMMemory.chain_meta, _URMMemory.chain_ways = meta, ways
                    told = python_list(t for _s, _n, t in _urmsg_gate_read(steps, _urm_truth, ways))
                    cards = _urmm_gate_view(steps, _urm_truth, ways, named=True)[:_URM_MAX_GATES + 1]
                    out.append(_urmm_corner_ways(steps[:len(cards)], cards,
                                                 _urmm_taken_step(meta), ways, told))
        except BaseException:
            pass
        return out

    # ---- a choice on one line (the user's pick 3a, 2026-11-22): its title,
    # then what it does itself; the ways after it fold into "N ways after",
    # which opens while it is pointed at. The rows keep their shape (the
    # gate draws the card from stubbed rows); the screen folds them here.

    def urm_corner_fold(lines):
        """(own, after, n) of a choice's lines - pure, for tests. own: what
        goes on the choice's line - every line at its own level with no way
        before it that says something (its test, its own changes, what it
        closes for good, the changes after its ways meet again, its note);
        after: the rest, in order, from its first "›" way on (a note after
        the ways - "+2 more" - goes with them); n: the ways right after it."""

        own = python_list()
        after = python_list()
        ways = False
        for line in lines:
            depth, prefix, chips, note = line
            if prefix:
                ways = True
            if not prefix and not depth and (not ways or chips):
                own.append(line)
            else:
                after.append(line)
        n = sum(1 for depth, prefix, _c, _n in after if prefix and not depth)
        return own, after, n

    def urm_corner_ways_words(n):
        return u"· 1 way after ›" if n == 1 else u"· %d ways after ›" % n

    # ---- moving the card (the user's pick 2a, 2026-11-22): by its grip,
    # like the URM+ button; while it stands elsewhere a faint outline marks
    # its usual spot; the next card is back there. Where it was dropped is
    # kept with the map's state (closed cards are kept there too: never in
    # a save), keyed by the cards on screen and their situation, and
    # forgotten at the first interaction where that changes, so a new menu
    # or a new check ahead - or the same menu reached again - finds the
    # usual spot. Cards shown together move together.
    #
    # The spot is kept as a share of the room left beside the cards (an
    # align): whatever their size when drawn, they stay on the screen, top
    # first, and a fold opened near the bottom grows upwards. The screen
    # draws a new drag whenever the spot or the fold changes
    # (urm_corner_place), so its place is always the one it is given: a
    # drag the screen draws again keeps the place it had otherwise.

    def _urmm_corner_key(kinds):
        """The cards on screen and what each is about; None when one of
        them cannot be told (then the cards do not move)."""

        key = python_list()
        for kind in kinds:
            about = _urmm_note_key(kind)
            if not about:
                return None
            key.append((kind, about))
        return tuple(key) if key else None

    def _urmm_corner_share(x, y, w, h, width, height):
        """(xalign, yalign) of a drop at x, y of a part w x h - pure, for
        tests: its share of the room beside it, 0 to 1; 0 where it has no
        room (taller than the screen: its top at the top)."""

        def share(at, room):
            return 0.0 if room <= 0 else max(0.0, min(1.0, float(at) / room))

        return (share(x, int(width) - int(w)), share(y, int(height) - int(h)))

    def _urmm_corner_spot(moved, key):
        """(xalign, yalign, w, h, drop) of the cards while `key` is what is
        on screen, or None: the usual spot - pure, for tests. w, h: their
        size when dropped (the outline's); drop: which drop it is."""

        if not moved or key is None or moved[0] != key:
            return None
        return tuple(moved[1:])

    def _urmm_corner_forget(moved, now):
        """The kept drop, or None once one of its cards is about something
        else - pure, for tests; now(kind): what that card is about now."""

        if not moved:
            return None
        for kind, about in moved[0]:
            if now(kind) != about:
                return None
        return moved

    def urm_corner_spot(kinds):
        """Where the cards stand now: (xalign, yalign, w, h, drop), or None
        for the usual spot."""

        try:
            return _urmm_corner_spot(getattr(_urmm_st, "moved", None), _urmm_corner_key(kinds))
        except Exception:
            return None

    def urm_corner_key(kinds):
        """What the cards on screen are about (plain values), or None: they
        do not move, and nothing is kept for them."""

        try:
            return _urmm_corner_key(kinds)
        except Exception:
            return None

    def urm_corner_place(about, spot, folded):
        """What the screen draws a new drag for: what the cards are about
        (urm_corner_key), their spot, which choice is unfolded. Plain
        values only (it is in the screen's scope, so in a save)."""

        return (about, spot, folded)

    class _URMMKeepIn(renpy.display.core.Displayable):
        """The cards' drag, kept inside the screen at every draw, at its
        size of the moment, header first, whatever made it grow (a fold, a
        longer menu). The engine never does: an align or a drag's place
        has no limit, and a drag is held in only while it is dragged
        (Critic round 1). Its room is the room of the spot it stands in:
        from `top` down - at the usual spot, under the URM+ button, which
        stands over every screen in that corner (Critic round 2); a card
        taller than its room runs off the bottom, its header in place. The
        screen puts it on the drag (`at urm_corner_keep_in(top)`)."""

        def __init__(self, child, top=0, **properties):
            super(_URMMKeepIn, self).__init__(**properties)
            self.child = child
            self.top = top

        def render(self, width, height, st, at):
            d = self.child
            cr = renpy.display.render.render(d, width, height, st, at)
            cw, ch = cr.get_size()
            x, y = getattr(d, "x", None), getattr(d, "y", None)
            nx = max(0, min(int(x or 0), int(width - cw)))
            # While the player holds it, its room is the whole screen: the
            # room of the spot it left counts again only once it is
            # dropped (Critic round 3).
            held = renpy.display.focus.get_grab() is d and bool(getattr(d, "drag_moved", False))
            ny = max(0 if held else self.top, min(int(y or 0), int(height - ch)))
            if x is not None and (nx, ny) != (x, y):
                # the drag's own idea of its place, so its events and its
                # next draw agree with where it is shown
                d.x = d.last_x = d.target_x = nx
                d.y = d.last_y = d.target_y = ny
            rv = renpy.display.render.Render(width, height)
            rv.blit(cr, (nx, ny))
            return rv

        def event(self, ev, x, y, st):
            d = self.child
            return d.event(ev, x - (getattr(d, "x", None) or 0), y - (getattr(d, "y", None) or 0), st)

        def visit(self):
            return [self.child]

    class _URMMKeepAt(object):
        """What the screen's `at` takes: one per top, the same object at
        every draw (the screen keeps its wrapper while it is the same)."""

        def __init__(self, top):
            self.top = top

        def __call__(self, d):
            return _URMMKeepIn(d, self.top)

    def urm_corner_keep_in(top):
        """The `at` for the cards' drag: kept in from `top` down - the
        usual top at the usual spot, 0 once the player moved them."""

        top = int(top)
        found = _urmm_dash.get(("keep", top))
        if found is None:
            found = _urmm_dash[("keep", top)] = _URMMKeepAt(top)
        return found

    _URMM_UNBROKEN = _urmm_re.compile(r"\S+")
    _URMM_WORD_PARTS = _urmm_re.compile(r"[^_.:/-]*[_.:/-]|[^_.:/-]+")

    def _urmm_corner_wrap(words, room, font=None, style_name="urmk_s_medium"):
        """Give an overwide token real break points without dropping letters."""

        short = max(1, room // max(1, getattr(style, style_name).size))
        if len(words) <= short:
            return urm_map_esc(words)

        def fits(text):
            if len(text) <= short:
                return True
            escaped = urm_map_esc(text)
            if font is not None:
                escaped = u"{font=%s}%s{/font}" % (font, escaped)
            return urmk_text_width(escaped, style_name) <= room

        def wrap(match):
            word = match.group(0)
            if fits(word):
                return word
            lines = python_list()
            line = u""
            for part in _URMM_WORD_PARTS.findall(word):
                if fits(line + part):
                    line += part
                    continue
                if line:
                    lines.append(line)
                while not fits(part):
                    lo, hi = 1, len(part)
                    while lo + 1 < hi:
                        middle = (lo + hi) // 2
                        if fits(part[:middle]):
                            lo = middle
                        else:
                            hi = middle
                    lines.append(part[:lo])
                    part = part[lo:]
                line = part
            lines.append(line)
            return u"\n".join(lines)

        return urm_map_esc(_URMM_UNBROKEN.sub(wrap, words))

    def urm_corner_check_heading(words, room, dim):
        return urmk_word(_urmm_corner_wrap(words, room, style_name="urmk_m"), style="urmk_m",
                         color=urmk_colour("ink-muted" if dim else "ink"), yalign=0.5,
                         xmaximum=room, language="unicode", layout="greedy")

    def urm_corner_chip(chip, room):
        """(words, tone, name) of a chip on the card: name, the value it is
        about when something can show values (the doorway's viewer), else
        None (not clickable). A chip without one is (words, tone)."""

        name = chip[2] if len(chip) > 2 else None
        if name and not _urm_value_viewable():
            name = None
        words = u"%s" % (chip[0],)
        text_room = room - 2 * urmk_px(URMK_CHIP[1])
        if len(chip) > 3:
            start, end = chip[3]
            font = URMK_FONTS["bold"]
            words = u"%s{font=%s}%s{/font}%s" % (_urmm_corner_wrap(words[:start], text_room), font,
                                                  _urmm_corner_wrap(words[start:end], text_room, font),
                                                  _urmm_corner_wrap(words[end:], text_room))
        else:
            words = _urmm_corner_wrap(words, text_room)
        return words, chip[1], name

    def urm_corner_chip_groups(chips):
        """Attach each logical connector to the chip that follows it."""

        out = python_list()
        joiner = None
        for chip in chips:
            if chip[1] == "join":
                joiner = chip[0]
            else:
                out.append((joiner, chip))
                joiner = None
        return out

    def urm_corner_story():
        # A screen Function action must return None to keep dialogue open.
        _urm_open("story_line")

    def urm_corner_open_value(name, beside):
        """A stat chip's click: the value's sheet beside the cards, through
        the doorway. Always None: a click that hands the engine anything
        else ends the interaction - at a menu it would take a choice
        (plan check, must 1)."""

        _urm_value_view(name, beside)
        return None

    def urm_corner_beside(kinds):
        """(left, right) in pixels of the cards where they stand now: what
        a chip's sheet opens beside."""

        width = config.screen_width
        spot = urm_corner_spot(kinds)
        if spot is not None:
            fx, _fy, w, _h = spot[:4]
            left = int(round(fx * max(0, width - w)))
            return (left, left + int(w))
        right = width - urmk_px(_URMM_CORNER[4])
        return (right - urmk_px(_URMM_CORNER[0]), right)

    def urm_corner_drag_name(kinds):
        """The drag's name says which cards it holds, so the drop needs no
        object of its own (a drag's callback can end up in a save)."""

        return u"urm_corner " + u" ".join(kinds)

    def urm_corner_dropped(drags, drop=None):
        """The drag's `dragged`: keep where the cards were dropped."""

        try:
            d = drags[0]
            kinds = (u"%s" % (d.drag_name,)).split()[1:]
            key = _urmm_corner_key(kinds)
            old = getattr(_urmm_st, "moved", None)
            if key is None:
                _urmm_st.moved = None
            else:
                fx, fy = _urmm_corner_share(d.x, d.y, d.w, d.h,
                                            config.screen_width, config.screen_height)
                _urmm_st.moved = (key, fx, fy, int(d.w), int(d.h), (old[5] + 1) if old else 1)
            renpy.restart_interaction()
        except Exception as error:
            print("MRM: the card's spot was not kept (%s)" % (error,))
        return None

    def _urmm_corner_moved_check():
        """At every interaction: forget the drop once the cards are about
        something else (or gone)."""

        moved = getattr(_urmm_st, "moved", None)
        if moved and _urmm_corner_forget(moved, _urmm_note_key) is None:
            _urmm_st.moved = None

    def urm_corner_grip_free():
        """The card's focus mask: the whole card but its grip, so the grip
        is the drag's (a button's focus beats the drag it sits in). A
        picture, not a function: the engine asks a function about points
        far outside the button too (it would take every click on the
        screen); a picture is asked only inside it."""

        g = urmk_px(_URMM_CORNER[1] + _URMM_GRIP)
        h = urmk_px(16 + 40)
        found = _urmm_dash.get(("grip", g, h))
        if found is None:
            found = _urmm_dash[("grip", g, h)] = Fixed(Solid("#000", xpos=g), Solid("#000", ypos=h))
        return found

    _URMM_GRIP = 32          # the grip's column, at 1080 lines

    _urmm_dash = python_dict()

    def urm_corner_dash(across):
        """One dash and its gap of the outline at the usual spot: across
        (a top or bottom edge) or down, 2 pixels thick, made once."""

        n = max(2, urmk_px(8))
        key = (across, n)
        found = _urmm_dash.get(key)
        if found is None:
            r, g, b = tuple(renpy.easy.color(urmk_colour("ink-muted")))[:3]

            def at(i, j):
                on = (i if across else j) < n
                return (r, g, b, 150 if on else 0)

            w, h = (2 * n, 2) if across else (2, 2 * n)
            found = _urmm_dash[key] = im.Data(_urmk_png(w, h, at),
                                              "urm_corner_dash_%d_%d.png" % (int(across), n))
        return found

    def _urmm_take_spec(meta, at, ways=None):
        """What Take on step `at` of the chain remembers: an earlier
        if-statement that could keep the game from getting there (a way of
        it leaves, or may) falls through (-1), then that step's arm; for
        the tail (no if-statement), only those. An earlier one whose every
        way carries on runs as the game decides: the checks are separate
        if-statements (ways: the chain's way facts; without them every
        earlier one falls through)."""

        node, arm = meta[at]
        spec = python_list()
        for earlier, _arm in meta[:at]:
            if earlier is None or earlier is node or (earlier, -1) in spec:
                continue
            if ways is not None and all(
                    ways[i][1] is False for i, (other, _a) in enumerate(meta) if other is earlier):
                continue
            spec.append((earlier, -1))
        if node is not None:
            spec.append((node, arm))
        return spec

    def urm_corner_take(kind, at):
        """Take on row `at` of a card: a choice now; a way when the game
        gets there. Asked again from where the game is, at the click."""

        if kind == "choices":
            choices = _urm_choices_here()
            if at >= len(choices):
                renpy.notify("MRM: that choice is no longer on screen")
                return None
            return _urm_take_choice(choices[at][0])
        steps = _urm_chain()
        meta = python_list(getattr(_URMMemory, "chain_meta", None) or ())
        if at >= len(meta) or len(meta) != len(steps):
            renpy.notify("MRM: that way is no longer ahead")
            return None
        ways = python_list(getattr(_URMMemory, "chain_ways", None) or ())
        _urm_take_way(_urmm_take_spec(meta, at, ways if len(ways) == len(meta) else None))
        return None

    # ---- the code behind a card, one click away (UX rule 2): the card's
    # title opens the URM+ Code view with the relevant lines marked.

    _URMM_CODE_DEPTH = 4

    def _urmm_code_lines(nodes, indent, out, depth=0, mark=None):
        """The statements of a block as lines of code, nested as written.
        mark: (ids, spans): the lines of a statement whose id is in ids go
        into spans as (first, end)."""

        for node in (nodes or ()):
            first = len(out)
            _urmm_code_one(node, indent, out, depth, mark)
            if mark is not None and id(node) in mark[0] and len(out) > first:
                mark[1].append((first, len(out)))

    def _urmm_code_one(node, indent, out, depth, mark):
        pad = u"    " * indent
        k = _urmsg_kind(node)
        if k == _URMSG_K_IF:
            if depth >= _URMM_CODE_DEPTH:
                out.append(pad + u"if ...:")
                return
            for n, (cond, inner) in enumerate(getattr(node, "entries", None) or ()):
                if _urmsg_is_else(cond):
                    out.append(pad + u"else:")
                else:
                    out.append(pad + (u"if " if n == 0 else u"elif ") + u"%s:" % (cond,))
                _urmm_code_lines(inner, indent + 1, out, depth + 1, mark)
            return
        if k == _URMSG_K_MENU:
            out.append(pad + u"menu:")
            if depth < _URMM_CODE_DEPTH:
                for item in (getattr(node, "items", None) or ()):
                    _urmm_code_choice(item, indent + 1, out, depth + 1, mark)
            return
        if k == _URMSG_K_TRANS:
            _urmm_code_lines(getattr(node, "block", None), indent, out, depth, mark)
            return
        if k == _URMSG_K_PY:
            lines, _drop = _urmsg_py_lines(node)
            for line in lines:
                out.append(pad + u"$ " + line)
            return
        if k == _URMSG_K_JUMP or k == _URMSG_K_CALL:
            out.append(pad + u"%s %s%s" % ("jump" if k == _URMSG_K_JUMP else "call",
                                           "expression " if getattr(node, "expression", False) else "",
                                           node.target if k == _URMSG_K_JUMP else node.label))
            return
        what = getattr(node, "what", None)
        if what is not None and k != _URMSG_K_USER:
            who = getattr(node, "who", None)
            out.append(pad + (u"%s " % who if who else u"") + u'"%s"' % _urm_clip(u"%s" % what, 60))
            return
        text = _urmsg_stmt_text(node)
        if text is not None:
            out.append(pad + text)

    def _urmm_code_choice(item, indent, out, depth, mark=None):
        text, cond = item[0], item[1]
        block = item[2] if len(item) > 2 else None
        head = u'"%s"' % (text,)
        if cond and not _urmsg_no_test(cond):
            head += u" if %s" % (cond,)
        out.append(u"    " * indent + head + (u":" if block else u""))
        if block:
            _urmm_code_lines(block, indent + 1, out, depth, mark)

    def urm_corner_code(kind):
        """The code of the menu on screen, or of the checks ahead, as text."""

        out = python_list()
        if kind == "choices":
            menu = _urm_menu_here()
            if menu is not None:
                out.append(u"menu:")
                for item in (getattr(menu, "items", None) or ()):
                    _urmm_code_choice(item, 1, out, 1)
        else:
            gate = _urm_gate_ahead()
            meta = getattr(_URMMemory, "chain_meta", None) or ()
            seen = python_list()
            for node, _arm in meta:
                if node is not None and node not in seen:
                    seen.append(node)
            if gate is not None and not seen:
                seen.append(gate)
            for node in seen:
                _urmm_code_lines([node], 0, out)
        return u"\n".join(out)

    _URMM_SCENE_LINES = 300   # a longer scene shows this many lines around the marked ones

    def _urmm_corner_nodes(kind):
        """The statements a card is about: the menu on screen, or the
        checks ahead."""

        if kind == "choices":
            menu = _urm_menu_here()
            return python_list([menu]) if menu is not None else python_list()
        seen = python_list()
        for node, _arm in (getattr(_URMMemory, "chain_meta", None) or ()):
            if node is not None and node not in seen:
                seen.append(node)
        gate = _urm_gate_ahead()
        if gate is not None and not seen:
            seen.append(gate)
        return seen

    def urm_corner_scene(kind):
        """The scene around a card's statements: (code, marked) with marked
        the (first, end) lines that are the card's own, or None when the
        scene cannot be told (no label holds them, or a marked statement
        does not show in it): then the card's own code is all there is."""

        nodes = _urmm_corner_nodes(kind)
        index = _urmi_index()
        if not nodes or index is None:
            return None
        labels = python_set()
        for node in nodes:
            try:
                labels.add(_urmsg_label_of(index, node))
            except Exception:
                return None
        if len(labels) != 1 or None in labels:
            return None
        name = labels.pop()
        try:
            label = renpy.game.script.lookup(name)
        except Exception:
            return None
        out = python_list([u"label %s:" % (name,)])
        mark = (python_set(id(n) for n in nodes), python_list())
        _urmm_code_lines(getattr(label, "block", None), 1, out, 0, mark)
        if len(mark[1]) != len(nodes):
            return None
        spans = sorted(mark[1])
        if len(out) > _URMM_SCENE_LINES:
            middle = (spans[0][0] + spans[-1][1]) // 2
            first = max(0, min(middle - _URMM_SCENE_LINES // 2, len(out) - _URMM_SCENE_LINES))
            first = min(first, spans[0][0])
            end = max(first + _URMM_SCENE_LINES, spans[-1][1])
            out = out[first:end]
            spans = [(a - first, b - first) for a, b in spans]
        return (u"\n".join(out), spans)

    def urm_corner_open_code(kind):
        """The card's title: the scene around it in the code view
        (18_code_view), its own lines marked; its own code alone where the
        scene cannot be told."""

        title = u"The choices' code" if kind == "choices" else u"The checks' code"
        scene = urm_corner_scene(kind)
        if scene is None:
            urmk_code_show(urm_corner_code(kind), title)
        else:
            note = (u"Blue edge: the choices on screen now. The scene around them for context."
                    if kind == "choices" else
                    u"Blue edge: the checks ahead. The scene around them for context.")
            urmk_code_show(scene[0], title, scene[1], note)

    # ---- the card is on screen whenever the game is (URM's layer, like
    # the index's progress line)

    def _urmm_corner_interact():
        _urmm_st.path_notice = None
        try:
            if not renpy.has_screen("urm_corner"):
                return
            if not _urm_in_game():
                return
            if renpy.get_screen("urm_corner", layer=_urmi_layer) is None:
                renpy.show_screen("urm_corner", _layer=_urmi_layer)
            _urmm_corner_moved_check()
            _urmm_stop_at_check()
        except Exception:
            pass

    # ---- stop skipping on a check ahead (URM's own setting, "Stop skipping
    # on path detection", now ours through the door): when a check comes
    # into view that was not in view at the interaction before, as URM's
    # pop-up did when it slid in - the same reader as the card, and only
    # where the card would say so (on, not closed, the side panel shut).

    def _urmm_stop_at_check():
        was = getattr(_urmm_st, "check_in_view", None)
        _urmm_st.check_in_view = None
        if not _urm_setting("stopSkippingOnPathDetection") or not _urm_setting("showPathsNotification"):
            return
        gate = _urm_gate_ahead()
        if gate is None or urm_note_hidden("paths"):
            return
        ignored, mutes = _urm_ignored_names("path"), _urm_path_mutes()
        if (ignored or mutes) and _urmm_path_notice(gate, ignored, mutes) is None:
            return
        key = id(gate)
        _urmm_st.check_in_view = key
        if key != was:
            _urm_stop_skipping()  # held: the next empty click resumes it (13_now)

    try:
        if _urmm_corner_interact not in config.interact_callbacks:
            config.interact_callbacks.append(_urmm_corner_interact)
    except Exception as error:
        print("MRM: the corner card is not shown (%s)" % (error,))

    def urm_corner_diamond(size, tone="gain"):
        """The mark of a way the game picks: a diamond in `tone` (green by
        default), `size` at 1080 lines from corner to corner, made once."""

        n = max(4, urmk_px(size))
        colour_key = (tone + "-ink") if tone in URMK_TONES else tone
        key = ("diamond", n, colour_key)
        found = urmk_look.made.get(key)
        if found is None:
            colour = tuple(renpy.easy.color(urmk_colour(colour_key)))
            half = n / 2.0

            def at(i, j):
                d = abs(i + 0.5 - half) + abs(j + 0.5 - half)
                cover = min(1.0, max(0.0, half - d + 0.5))
                return (colour[0], colour[1], colour[2], int(round(colour[3] * cover)))

            found = im.Data(_urmk_png(n, n, at), "urm_corner_diamond_%d_%s.png" % (n, colour_key))
            urmk_look.made[key] = found
        return found

    def urm_corner_dot(tone):
        """The mark of "Otherwise": a round dot, 10 at 1080 lines, in a
        tone's ink ("ink-muted" or a tone), drawn as a picture, made once."""

        colour = urmk_colour(tone + "-ink") if tone in URMK_TONES else urmk_colour(tone)
        n = max(4, urmk_px(10))
        key = ("dot", n, colour)
        found = urmk_look.made.get(key)
        if found is None:
            rgba = tuple(renpy.easy.color(colour))
            half = n / 2.0

            def at(i, j):
                d = ((i + 0.5 - half) ** 2 + (j + 0.5 - half) ** 2) ** 0.5
                cover = min(1.0, max(0.0, half - d + 0.5))
                return (rgba[0], rgba[1], rgba[2], int(round(rgba[3] * cover)))

            found = im.Data(_urmk_png(n, n, at), "urm_corner_dot_%d_%s.png" % (n, colour.lstrip("#")))
            urmk_look.made[key] = found
        return found
