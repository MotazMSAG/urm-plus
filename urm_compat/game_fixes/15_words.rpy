    # ------------------------------------------------------------------
    # Words and tones: text, colours and icons; a branch's rows
    # ------------------------------------------------------------------

    _URM_MAX_ROWS = 6
    _URM_MAX_GUARD_CHARS = 18

    # Material Icons, from the font behind style_suffix 'icon'. That style is
    # `is x52URM_text` with no hover_font, so these do not change face when the
    # pointer enters the notification - unlike 'icon_button_text', which swaps
    # the Outlined face for the Solid one.
    _URM_ICON_LIVE = u""       # done (a tick; 'check' is U+E5CA)
    _URM_ICON_DEAD = u""       # close
    _URM_ICON_UNKNOWN = u""    # remove, a plain dash
    _URM_ICON_EFFECT = u""     # arrow_right_alt
    _URM_ICON_GUARD = u""      # subdirectory_arrow_right

    # Ren'Py 7 runs on Python 2, where a theme colour may be a unicode rather
    # than a str. Checking against str alone would reject every colour there
    # and quietly drop the markers back to plain text.
    # Inside a Ren'Py 7 store, `str` is Ren'Py's compat str - unicode - but
    # Python 2's parser hands back string literals as byte strings. So text
    # types come from the real builtins, never from the store's names.
    try:
        import __builtin__ as _urm_builtins
        _URM_TEXT = (_urm_builtins.str, _urm_builtins.unicode)
    except ImportError:
        _URM_TEXT = (str,)

    def _urm_hex(value):
        """
        A colour only if it really is one.

        ThemeProvider.__getattr__ has no final else, so a name it does not
        know comes back as None rather than raising. "{color=None}" would be
        drawn literally, so anything that is not a hex string is refused here.
        """

        if isinstance(value, _URM_TEXT) and value.startswith("#"):
            return value

        return None

    def _urm_rgb(value):

        value = _urm_hex(value)

        if not value:
            return None

        digits = value[1:]

        if len(digits) in (3, 4):
            digits = "".join(c + c for c in digits)

        if len(digits) < 6:
            return None

        try:
            return tuple(int(digits[i:i + 2], 16) for i in (0, 2, 4))
        except Exception:
            return None

    def _urm_luminance(rgb):

        channels = []

        for raw in rgb:
            c = raw / 255.0
            channels.append(c / 12.92 if c <= 0.03928
                            else ((c + 0.055) / 1.055) ** 2.4)

        return (0.2126 * channels[0] + 0.7152 * channels[1]
                + 0.0722 * channels[2])

    def _urm_contrast(one, two):
        """WCAG contrast, or 0.0 when either colour cannot be read."""

        a = _urm_rgb(one)
        b = _urm_rgb(two)

        if a is None or b is None:
            return 0.0

        la = _urm_luminance(a)
        lb = _urm_luminance(b)

        if la < lb:
            la, lb = lb, la

        return (la + 0.05) / (lb + 0.05)

    # kind ("success", "error") -> the tone of its colours in the kit's
    # table of the older displays (16_kit, URMK_OLD_COLOURS)
    _URM_SIGNAL_TONE = python_dict((("success", "gain"), ("error", "loss")))

    def _urm_signal(kind):
        """
        A colour for the live/dead mark that is readable on the card, or
        None (then the mark takes the words' colour).

        A tone's ground and words colours are a pale-ground/dark-words pair
        meant for a message bar, so one half of each is unreadable on a
        given fill. Both halves are measured against the fill the card
        really paints (its "box"), and the one that clears 3:1 is taken.
        """

        try:
            fill = URMK_OLD_COLOURS["box"]
            tone = _URM_SIGNAL_TONE.get(kind, kind)

            best = None
            ratio = 0.0

            for half in ("Bg", "Text"):
                candidate = _urm_hex(URMK_OLD_COLOURS.get(tone + half))
                if candidate is None:
                    continue
                score = _urm_contrast(candidate, fill)
                if score > ratio:
                    best, ratio = candidate, score

            if best is not None and ratio >= 3.0:
                return best
        except Exception:
            pass

        return None

    def _urm_tint(text, colour):

        if colour:
            return "{color=%s}%s{/color}" % (colour, text)

        return text

    def _urm_colorize(code):
        """Show source as literal text in the older cards and route map."""
        return (code or u"").replace(u"{", u"{{")

    def _urm_words(text):
        """Our own prose: italic, so it never reads as the game's code."""

        return "{i}%s{/i}" % text.replace("{", "{{")

    def _urm_clip(text, limit):

        if len(text) <= limit:
            return text

        # U+2026 is present in Roboto-Regular; U+2192 and the box-drawing
        # characters are not, which is why none of them appear in this file.
        return text[:limit - 1] + u"…"

    def _urm_effects(nodes):
        """
        The rows for one arm: guaranteed non-empty, and never half a record.

        A record is its statement row plus one row per guard. Those are drawn
        together or not at all - a guard row stranded from its statement, or a
        statement whose guard row fell off the bottom, would promote a
        conditional change to an unconditional one. The overflow row is
        budgeted for before the loop rather than squeezed in afterwards, so
        the count it reports is never short.
        """

        # The arm's records are the story graph's, read once per block and
        # remembered (rework move 7): this runs on every redraw.
        try:
            flat, dropped = _urmsg_arm_recs(nodes)
        except BaseException:
            return _urm_effects_from(None)

        return _urm_effects_from(flat, dropped)

    def _urm_effects_from(flat, dropped=0):
        """_urm_effects for records already collected; None means it broke."""

        broke = False

        try:
            if flat is None:
                raise ValueError
            records, removed = _urm_reduce(flat)
        except BaseException:
            records, removed, broke = [], 0, True

        hidden = dropped + removed

        # Reserve the overflow row up front if anything might not fit.
        room = _URM_MAX_ROWS
        if hidden or sum(1 + len(g) for g, _t, _n in records) > room:
            room -= 1

        rows = []

        for index, (guards, text, count) in enumerate(records):

            needed = 1 + len(guards)

            if len(rows) + needed > room:
                hidden += sum(1 + len(g) for g, _t, _n in records[index:])
                break

            body = _urm_colorize(text)

            if count > 1:
                body += _urm_words("  x%d" % count)

            rows.append((_URM_ICON_EFFECT, body))

            for guard in guards:
                if guard == "otherwise":
                    rows.append((_URM_ICON_GUARD, _urm_words("otherwise")))
                else:
                    rows.append((
                        _URM_ICON_GUARD,
                        _urm_words("only if ")
                        + _urm_colorize(guard[len("only if "):]),
                    ))

        if hidden:
            rows.append((_URM_ICON_GUARD, _urm_words("+%d more" % hidden)))

        if not rows:
            if broke:
                # An internal failure must not look like a branch that simply
                # changes nothing - that is a confident lie.
                rows.append((_URM_ICON_GUARD,
                             _urm_words("could not read this branch")))
            else:
                # Honest: most branches in a real game are dialogue only, and
                # dialogue changes nothing URM tracks.
                rows.append((_URM_ICON_EFFECT,
                             _urm_words("no tracked changes")))

        return rows

    def _urm_fallback_icon(fired, unknown, success, error):
        """
        The mark on the "nothing above matches" card.

        It only runs if every gate above it missed - so if we could not
        evaluate one of those gates, we cannot claim this one runs either.
        """

        if fired:
            return _urm_tint(_URM_ICON_DEAD, error)

        if unknown:
            return _URM_ICON_UNKNOWN

        return _urm_tint(_URM_ICON_LIVE, success)


    # ---- a number test as a goal (UX rule 8): what the player has, what it needs
    #
    # The one goal wording, "you have 1, needs 3", for every display that
    # says one: the route map, the choice cards, the alert (the user's pick,
    # 2026-11-22). What the player has comes from the one reader, _urm_now.

    _URM_GOAL_NEED = python_dict(((">=", u""), (">", u"over "), ("<=", u"at most "), ("<", u"under ")))

    def _urm_number(value):
        if isinstance(value, float) and value == int(value):
            value = int(value)
        return u"%s" % (value,)

    def urm_goal(name, op, literal):
        """'1/3' (or '1 (over 3)') for a test of name against literal with
        >=, >, <= or <; 'needs 3' alone when what name holds now cannot be
        said (not set yet, None, on or off); None for any other test."""

        if op not in _URM_GOAL_NEED or literal is None or isinstance(literal, bool):
            return None
        known, now = _urm_now(name)
        if not known or now is None or isinstance(now, bool) or not _urm_isnum(now):
            return u"needs %s%s" % (_URM_GOAL_NEED[op], _urm_number(literal))
        if op == ">=":
            return u"%s/%s" % (_urm_number(now), _urm_number(literal))
        return u"%s (%s%s)" % (_urm_number(now), _URM_GOAL_NEED[op], _urm_number(literal))

    def urm_goal_words(test):
        """urm_goal for a test written as code (elena_love >= 3) of one name
        against a number, when the name holds a number now; None for any
        other test or value."""

        import re
        m = re.match(r"^\s*([A-Za-z_][\w.]*)\s*(>=|>|<=|<)\s*(-?\d+(?:\.\d+)?)\s*$", test or "")
        if m is None:
            return None
        known, now = _urm_now(m.group(1))
        if not known or not _urm_isnum(now):
            return None
        literal = float(m.group(3)) if "." in m.group(3) else int(m.group(3))
        return urm_goal(m.group(1), m.group(2), literal)
