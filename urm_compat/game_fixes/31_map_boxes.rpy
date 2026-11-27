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

    def urm_map_esc(text):
        """For text drawn with substitute False: only text tags need escaping."""
        return (u"%s" % (text,)).replace("{", "{{")

    # ---- the map's look: our screen look (the user's pick 1a, 2026-11-22)

    _URMM_INK = python_dict((
        ("screen", "surface"), ("ink", "ink"), ("muted", "ink-muted"),
        ("line", "graph-line"), ("accent", "accent"), ("accent-ink", "accent-ink"),
        ("on-accent", "on-accent"), ("box", "surface"), ("game", "surface-2"),
        ("track", "track"), ("thumb", "thumb"), ("thumbHover", "thumb-hover"),
        ("pick", "warn-ink"), ("lines", "ink-muted"),
    ))
    def urm_map_ink(token):
        """The route map's colours from the shared palette."""
        return urmk_colour(_URMM_INK.get(token, token))

    def urm_map_later_parts(name, op, literal, where):
        """A later check as the map's footer shows it: (words, what the
        player has, its tone) - 'At ch04begin the game checks: Carol nerve
        is at least 3', 'you have 1, needs 3', 'warn'. The tone says how
        it stands now: met (gain), not met or not set yet (warn), not to be
        told (plain)."""

        who = _urmm_pretty(name)

        if op == "truthy":
            test = "%s is true" % who
        elif op == "falsy":
            test = "%s is false" % who
        elif op in ("in", "not in"):
            test = "%s %s %s" % (who, "has" if op == "in" else "lacks",
                                 _urmm_value(_urmm_show(literal)))
        elif op == "vs":
            test = "%s against %s" % (who, literal)
        else:
            test = "%s %s %s" % (who, _URMM_SAY_OP.get(op, op),
                                 _urmm_value(_urmm_show(literal)))

        known, now = _urm_now(name)
        if not known:
            have = "not set yet"
        elif now is True:
            have = "it is true"
        elif now is False:
            have = "it is false"
        else:
            have = (urm_goal(name, op, literal) if now is not None else None) or \
                "you have %s" % _urmm_value(_urmm_show(now))

        tone = "loss" if not known else _urmm_later_tone(now, op, literal)
        return ("At %s the game checks: %s" % (where, test), have, tone)

    _URMM_LATER_TESTS = python_dict((
        ("==", lambda a, b: a == b), ("!=", lambda a, b: a != b),
        (">=", lambda a, b: a >= b), (">", lambda a, b: a > b),
        ("<=", lambda a, b: a <= b), ("<", lambda a, b: a < b),
        ("in", lambda a, b: b in a), ("not in", lambda a, b: b not in a),
        ("truthy", lambda a, b: bool(a)), ("falsy", lambda a, b: not a),
    ))

    def _urmm_later_tone(now, op, literal):
        test = _URMM_LATER_TESTS.get(op)
        if test is None:
            return "plain"
        try:
            return "gain" if test(now, literal) else "loss"
        except Exception:
            return "plain"

    def urm_map_later_line(name, op, literal, where):
        """'At ch04begin the game checks: Carol nerve is at least 3 · you
        have 1, needs 3' - a number test says it as a goal (urm_goal)."""

        words, have, _tone = urm_map_later_parts(name, op, literal, where)
        return "%s  ·  %s" % (words, have)

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
            self.later_rows = python_list()   # (words, have, tone) for each later line

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
        never run - a call can do anything - and counts as cannot be said
        (_urm_truth, the one answer every display gives).
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
                now = _urm_truth(cond)
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
        changes_said = python_set()
        for guards, text, count in _urm_reduce(python_list(records))[0]:
            if text == _URMM_MARK_CHECK:
                continue
            if _urmm_dyn_again(dyn_said, guards, text):
                continue
            if text == _URMM_MARK_MENU:
                if ("menu", None) not in box.badges:
                    box.badges.append(("menu", None))
                continue
            if text.startswith("persistent."):
                continue
            chip = None if text == _URMM_MARK_CODE else urm_any_chip(text)
            if text == _URMM_MARK_CODE or chip == _URMM_CODE_CHIP:
                # One "?" however many such statements the stretch holds,
                # and lines of the game's own code whose writes cannot be
                # told (34_words).
                if ("code", _URMM_CODE_TIP) not in box.badges:
                    box.badges.append(("code", _URMM_CODE_TIP))
                continue
            if chip is None:
                continue            # it changes nothing of the story
            words, tone = chip
            if _urmm_says_no_amount(chip):
                # What a line changes, with no amount: said once behind
                # the same checks (each check keeps its own diamond).
                said = (words, tuple(guards))
                if said in changes_said:
                    continue
                changes_said.add(said)
            elif count > 1:
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

