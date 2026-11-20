    # ------------------------------------------------------------------
    # The route map: the whole split, full screen, until the paths meet
    # ------------------------------------------------------------------
    #
    # Opened from the quickmenu. It draws the same walk the cards use as a
    # left-to-right subway map: "You are here", one box per choice (nested
    # menus and ifs branch further right), and a single "Paths meet again"
    # box that every rejoining route runs into. Each box says what that step
    # gives you in plain words ("Carol love +1"), not code - see UX.md.
    # Under the map: what the flags these routes set decide later, with the
    # value you have now.
    #
    # Everything here is plain data (boxes, bars, lines of text); the screen
    # only draws it. Built once when opened, never per frame.

    try:
        x52URM.SettingsClass.defaultValues.setdefault("urmcBtnRouteMap", True)
    except Exception as error:
        print("URM+: route map setting not registered (%s)" % (error,))

    _URMM_HUMAN = _urmm_re.compile(
        r"^([A-Za-z_][\w.]*)\s*(\+=|-=|\*=|/=|=)\s*(.+)$")
    _URMM_NUMBER = _urmm_re.compile(r"^-?\d+(\.\d+)?$")

    def urm_map_esc(text):
        """For text drawn with substitute False: only text tags need escaping."""
        return (u"%s" % (text,)).replace("{", "{{")

    def _urmm_pretty(name):
        """carol_love -> Carol love; persistent.seen_end -> Seen end."""

        if name.startswith("persistent."):
            name = name[len("persistent."):]
        if name.startswith("store."):
            name = name[len("store."):]
        text = name.replace("_", " ").replace(".", " ").strip()
        return text[:1].upper() + text[1:]

    def _urmm_value(text):
        """A literal as a player would say it: "yes" -> yes, True -> on."""

        text = text.strip()
        if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
            return text[1:-1]
        if text == "True":
            return "on"
        if text == "False":
            return "off"
        if text == "None":
            return "cleared"
        return text

    def urm_map_chip(text):
        """
        One change as (words, tone). tone is gain, loss, set or other, and
        decides the chip's colour - so "better or worse" reads without
        reading.
        """

        m = _URMM_HUMAN.match(text.strip())
        if not m:
            return (_urm_clip(text.strip(), 40), "other")

        name, op, value = m.group(1), m.group(2), m.group(3).strip()
        who = _urmm_pretty(name)
        number = _URMM_NUMBER.match(value) is not None
        negative = number and value.startswith("-")

        if op == "+=":
            if number:
                return ("%s %s%s" % (who, "" if negative else "+", value),
                        "loss" if negative else "gain")
            return ("%s + %s" % (who, _urm_clip(value, 16)), "other")

        if op == "-=":
            if number:
                return ("%s %s" % (who, value[1:] if negative else "-" + value),
                        "gain" if negative else "loss")
            return ("%s - %s" % (who, _urm_clip(value, 16)), "other")

        if op in ("*=", "/="):
            return ("%s %s%s" % (who, "x" if op == "*=" else "/",
                                 _urm_clip(value, 12)), "other")

        said = _urmm_value(value)
        if value == "True":
            return ("%s: on" % who, "gain")
        if value == "False":
            return ("%s: off" % who, "loss")
        return ("%s: %s" % (who, _urm_clip(said, 20)), "set")

    def _urmm_now(name):
        """The variable's value right now, or a marker when it has none."""

        try:
            obj = renpy.store
            parts = name.split(".")
            if parts[0] == "persistent":
                obj = persistent
                parts = parts[1:]
            for part in parts:
                obj = getattr(obj, part)
            return True, obj
        except BaseException:
            return False, None

    _URMM_SAY_OP = python_dict((
        ("==", "is"), ("!=", "is not"), (">=", "is at least"),
        (">", "is over"), ("<=", "is at most"), ("<", "is under"),
    ))

    def urm_map_later_line(name, op, literal, where):
        """'At ch04begin the game checks: Carol nerve is at least 3 · you have 1'."""

        who = _urmm_pretty(name)

        if op == "truthy":
            test = "%s is on" % who
        elif op == "falsy":
            test = "%s is off" % who
        elif op in ("in", "not in"):
            test = "%s %s %s" % (who, "has" if op == "in" else "lacks",
                                 _urmm_value(_urmm_show(literal)))
        elif op == "vs":
            test = "%s against %s" % (who, literal)
        else:
            test = "%s %s %s" % (who, _URMM_SAY_OP.get(op, op),
                                 _urmm_value(_urmm_show(literal)))

        known, now = _urmm_now(name)
        if not known:
            have = "not set yet"
        elif now is True:
            have = "it is on"
        elif now is False:
            have = "it is off"
        else:
            have = "you have %s" % _urmm_value(_urmm_show(now))
            try:
                if op in (">=", ">") and not isinstance(now, bool):
                    gap = literal - now + (1 if op == ">" else 0)
                    if gap > 0:
                        have += " (%s short)" % gap
            except Exception:
                pass

        return "At %s the game checks: %s  ·  %s" % (where, test, have)

    # ---- finding the menu to draw

    def _urmm_next_menu(start, limit=3000, sites=()):
        """
        The nearest menu at or ahead of start. An if is only pruned when its
        condition can be judged now; otherwise every arm is searched.
        sites: see _urmm_distances.
        """

        return _urmsg_next_split(start, _urm_truth, limit,
                                 _urmsg_flow_from(sites))[0]

    def _urmm_here():
        try:
            return _urmsg_here()
        except BaseException:
            return None

    # ---- layout
    #
    # The map runs on past each place the paths meet: the blocks after it
    # (one per label the story passes through), then the next real split, and
    # so on for a few splits - the screen is dragged to see further. "You are
    # here" is the block holding the line the game is on.
    #
    # Three ways a check is drawn (UX.md rules 12-13):
    #   - it sends routes different ways: a diamond on the track, branches
    #     after it named for where they go;
    #   - it only changes some lines: a diamond inside its block, no words;
    #   - it gives something without splitting (points added later for an
    #     earlier choice): a diamond in front of that chip.
    # A menu whose options only change some lines gets a list icon instead
    # of a split; a menu that splits is the split, never also a label.

    _URMM_STAGES = 4          # splits drawn, the first one included
    _URMM_STRETCH = 3000      # statements walked between two splits
    _URMM_MAP_BOXES = 160

    class _URMMBox(python_object):
        def __init__(self, kind, title, col):
            self.kind = kind          # here, choice, branch, merge, block
            self.title = title
            self.sub = None           # a muted line under the title
            self.col = col
            self.chips = python_list()    # (words, tone, after a check, tip)
            # ("menu", None), ("check", tip) - the lone diamond - and
            # ("code", tip) - the "?" of a custom statement with content.
            self.badges = python_list()
            # Drawn faded: a way the game will not take as things stand
            # ("If none apply" while an option is open).
            self.faded = False
            # The chips again, by the check they stand behind: [key, tip,
            # faded, [(words, tone)]], the unguarded ones first.
            self.sets = python_list()
            self.checks = python_list()   # the marks behind the lone diamond
            # What the screen draws, row by row (_urmm_rows): (lead, tip,
            # faded, height, cells).
            self.rows = python_list()
            self.more = 0
            self.note = None
            self.note_tone = None     # a chip tone, or None for plain text
            self.end = None
            self.children = python_list()
            self.diamond = False      # a check splits right after this box
            self.row = 0.0
            self.gain = False
            self.x = self.y = self.w = self.h = 0
            self.after = None         # the box that follows on the same line
            # Not a box but a point on the line (_urmm_point): a merge with
            # nothing to say, a scene that holds only a check.
            self.dot = False
            # (.ring: a ring where paths met. Gone with the user's pick 2b -
            # lines that join already say it. Always False; kept so that the
            # screen of the build before still draws.)
            self.ring = False
            # ... and the check that sends the story different ways right
            # after it: the hover text of the small diamond that would stand
            # beside the big one. There is ONE mark there, the big one.
            self.pick = None
            # What the player has, for a way of a check: (words, tone) -
            # "you: 2", green ("gain") when the way's test holds as things
            # stand, amber ("warn") when not. beside: drawn on the title's
            # line (it fits there), else under it.
            self.have = None
            self.have_beside = False
            # How wide each cell of each row is (a tuple per row), and the
            # rows again for the screen, with the PLACE of every mark that
            # can be pointed at (_urmm_draw_rows).
            self.wide = python_list()
            self.draw = python_list()
            self.tip = None           # ... with a small check diamond after it
            self.ask = None           # ... and a "?" (a custom statement)
            self.tail = False         # the map stops following here
            self.tw = self.th = 0     # room taken with everything hung on it
            self.ow = self.kh = 0

    class _URMMView(python_object):
        def __init__(self):
            self.empty = None
            self.summary = ""
            self.boxes = python_list()
            self.bars = python_list()     # (x, y, w, h, tone)
            self.diamonds = python_list() # (centre x, centre y)
            # Rings where paths meet: (centre x, centre y, tone, None). The
            # fourth place held the tip of a diamond drawn beside the ring
            # until those moved onto the line (marks); it stays so that the
            # screen of the build before still draws with this file.
            self.dots = python_list()
            # Every big diamond with what it says when pointed at: (x, y,
            # tip). .diamonds holds the same places without the words, for
            # the screen of the build before.
            self.picks = python_list()
            self.marks = python_list()    # small check diamonds on a line: (x, y, tip)
            # The "?" of a custom statement with content inside, on a line:
            # (x, y, tip). A list of its own, so that the screen of the
            # build before - which knows nothing of it - still draws.
            self.codes = python_list()
            self.here = (0, 0)            # centre of "you are here"
            self.mini = None              # the overview, drawn once
            self.width = 0
            self.height = 0
            self.later = python_list()

    _URMM_MAP_CHIPS = 6

    _URMM_LEAF_NOTES = python_dict((
        ("here", ("Back to this choice", None)),
        ("loop", ("Loops back", None)),
        ("return", ("Ending", "loss")),
        ("later", ("Joins further on", None)),
    ))

    def _urmm_holds(guards):
        """
        Whether the checks in front of a row hold as the game stands: True,
        False, or None when that cannot be said. A test with a call in it is
        never run - a call can do anything - and counts as cannot be said.
        An elif is reached only when the tests before it fail (.before); an
        "otherwise" carries exactly those. One test known to fail settles
        it, whatever the others are.
        """

        sure = True
        for guard in guards or ():
            tests = (tuple(getattr(guard, "tests", None) or ())
                     + tuple(getattr(guard, "before", None) or ()))
            for cond, wanted in tests:
                if wanted is None:
                    continue
                text = u"%s" % (cond,)
                if "(" in text:
                    sure = False
                    continue
                now = _urm_truth(text)
                if now is None:
                    sure = False
                elif now != bool(wanted):
                    return False
        return True if sure else None

    def _urmm_check_badge(box):
        """The one lone diamond of a box, for every check in it that only
        changes lines."""

        kept = python_list(b for b in box.badges if b[0] != "check")
        if box.checks:
            kept.append(("check", urm_mark_tip(box.checks)))
        box.badges = kept

    # The badges that are marks: they stand alone after the chips, and with
    # nothing else in the box they ride on the line instead (_urmm_point).
    _URMM_MARKS = ("check", "code")

    def _urmm_only_check(box):
        """True when a box holds no chip and no icon - at most marks: the
        lone diamond, the "?" of a custom statement."""

        if box.chips or box.more:
            return False
        for kind, _tip in box.badges:
            if kind not in _URMM_MARKS:
                return False
        return True

    def _urmm_take_marks(last, box):
        """Marks one scene after the other become one of each kind on the
        box before: the checks behind one diamond, one "?"."""

        last.checks.extend(box.checks)
        _urmm_check_badge(last)
        for badge in box.badges:
            if badge[0] != "check" and badge not in last.badges:
                last.badges.append(badge)

    def _urmm_fill(box, records):
        """
        Put a stretch's changes in a box. A chip is (words, tone, guarded,
        tip). Chips that stand behind the same check are also kept together
        (box.sets), with what that check is in words and whether it fails
        as the game stands now: the map draws one diamond per check, not
        one per chip. A badge is (kind, tip).
        """

        # Every mark, not what _urm_reduce leaves of them: it folds repeats
        # of the same text into one, and all marks have the same text.
        for _guards, text in records:
            if text == _URMM_MARK_CHECK:
                box.checks.append(text)

        dyn_said = python_set()
        for guards, text, count in _urm_reduce(python_list(records))[0]:
            if text == _URMM_MARK_CHECK:
                continue
            if _urmm_dyn_again(dyn_said, guards, text):
                continue
            if text == _URMM_MARK_MENU:
                if ("menu", None) not in box.badges:
                    box.badges.append(("menu", None))
                continue
            if text == _URMM_MARK_CODE:
                # One "?" however many such statements the stretch holds.
                if ("code", _URMM_CODE_TIP) not in box.badges:
                    box.badges.append(("code", _URMM_CODE_TIP))
                continue
            if text.startswith("persistent."):
                continue
            words, tone = urm_any_chip(text)
            if count > 1:
                words += "  x%d" % count
            # A jump that cannot be followed is always said, never "+1 more".
            if (len(box.chips) >= _URMM_MAP_CHIPS
                    and text != _URMSG_DYN_JUMP and text != _URMSG_DYN_CALL):
                box.more += 1
                continue
            tip = urm_guard_tip(guards) if guards else None
            box.chips.append((words, tone, bool(guards), tip))

            # The same check is the same tests - never the same guard text,
            # which is clipped.
            key = tuple((u"%s" % (g,), getattr(g, "tests", None), getattr(g, "before", None))
                        for g in guards)
            held = None
            for one in box.sets:
                if one[0] == key:
                    held = one
                    break
            if held is None:
                faded = bool(guards) and _urmm_holds(guards) is False
                if faded:
                    tip += u"  \u00b7  not as things stand"
                held = python_list((key, tip, faded, python_list()))
                if key:
                    box.sets.append(held)
                else:
                    box.sets.insert(0, held)
            held[3].append((words, tone))

        # One diamond for every check here that only changes lines, drawn
        # AFTER the chips: in front of one it read as that chip's check.
        _urmm_check_badge(box)
        box.gain = box.gain or any(c[1] == "gain" for c in box.chips)

