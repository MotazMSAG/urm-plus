# ---------------------------------------------------------------------------
# What a branch tests, and what it changes - as cards
# ---------------------------------------------------------------------------
#
# URM's notification reports the first if-statement ahead of the cursor and
# stops there. When that statement has no else, not matching it does not mean
# "the other listed path" - control falls straight out of it into whatever
# comes next, which is often another if. So "1 options" can really be a chain
# of gates ending in a return, and none of that is on screen.
#
# Showing it was the easy half. The hard half was that earlier versions drew
# the effects as source code, and source code contains its own if/else - so a
# nested condition inside an effect looked exactly like the gate's own
# condition. No marker column fixes that, because the two things really are
# the same kind of text. Four changes make them different kinds of thing:
#
#   * the gate's condition is drawn bare - no leading "if", no trailing ":" -
#     so the token that caused the collision is never on screen twice;
#   * nested control flow is not drawn as code at all. A surviving test is
#     demoted to its own row reading "only if <cond>" under the statement it
#     guards;
#   * every row carries a 24px icon, and the icon fonts map only 0-9, _ and
#     a-z, so no colorize() output can ever put a glyph in that column;
#   * the screen draws a gate as a lighter band between two rules, with its
#     effects on a darker fill below. The rhythm never varies, which is why
#     the effect list here is guaranteed non-empty.
#
# Effects come from the arm's own AST, not from CodeView.nodesToCode: that
# drops every node after a Jump, shows nothing inside a While or a nested
# Menu, strips lines mentioning renpy./ui., and indents the first line of any
# block nested two deep by 4*(2n-1) spaces rather than 4*n.
#
# Only three reductions are applied, because only these three can be shown to
# be true (see _urm_reduce). Anything hidden is counted and reported as
# "+N more", never dropped silently.
#
# Nothing here raises: it all runs while the overlay is being drawn.

init 999 python:

    _URM_MAX_GATES = 4
    _URM_MAX_ROWS = 6
    _URM_MAX_TOTAL_ROWS = 12
    _URM_MAX_GUARD_CHARS = 18
    _URM_MAX_DEPTH = 3

    # Material Icons, from the font behind style_suffix 'icon'. That style is
    # `is x52URM_text` with no hover_font, so these do not change face when the
    # pointer enters the notification - unlike 'icon_button_text', which swaps
    # the Outlined face for the Solid one.
    _URM_ICON_LIVE = u""       # done (a tick; 'check' is U+E5CA)
    _URM_ICON_DEAD = u""       # close
    _URM_ICON_UNKNOWN = u""    # remove, a plain dash
    _URM_ICON_EFFECT = u""     # arrow_right_alt
    _URM_ICON_GUARD = u""      # subdirectory_arrow_right

    def _urm_colour(name):

        try:
            return getattr(x52URM.Theme.colors, name)
        except Exception:
            return None

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

    def _urm_signal(kind):
        """
        A colour for the live/dead mark that is readable on the card.

        successText and errorText are a fixed pale-background/dark-text pair
        meant for URM's message bars, so one half of each is unreadable on a
        given fill. Which half depends on the theme's actual colours, not on
        Theme.isDark: on Traffic light the "dark" flag and the real fills
        disagree, and the mark came out at 2.3:1. So both halves are measured
        against the fill the card really paints, and if neither clears 3:1 the
        mark falls back to the theme's own text colour, which by construction
        is readable there.
        """

        try:
            fill = _urm_colour("buttonBgHover")

            best = None
            ratio = 0.0

            for half in ("Bg", "Text"):
                candidate = _urm_hex(_urm_colour(kind + half))
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

    # Variables and labels in the cards are clickable, the same way they are
    # in URM's own code view: colorize wraps each one in an {a=URMVarDialog:}
    # or {a=URMLabelDialog:} hyperlink, and URM registers both protocols in
    # config.hyperlink_handlers when it loads (codeview.rpy:76-77).
    #
    # This works inside the notification's button because a Button hands an
    # event to its child before running its own action (behavior.py, Button
    # .event: `rv = super(Button, self).event(...)`, returning early if the
    # child claims it), and a Text carrying an {a=} tag registers a focus
    # rectangle per link (text.py, `rv.add_focus(self, hyperlink, ...)`) and
    # fires the handler itself on a click.
    #
    # Which rectangle wins where the button's and the link's overlap is
    # decided in focus_at_point, which lives in the compiled render module -
    # so if a future Ren'Py gives the button priority, clicking a variable
    # just opens the paths dialog, which is what the button does anyway.
    # Nothing breaks either way; set this to False to go back to plain text.
    _URM_CLICKABLE = True

    def _urm_colorize(code):
        """
        One statement, with URM's own syntax colouring.

        evaluateConditions stays off: it appends URM's "# X - Condition not
        met" comment, which belongs in the code dialog and not on a card whose
        icon already says the same thing. colorize() escapes braces itself, so
        nothing here may escape them again.

        colorize can leak its internal URMTKN placeholder when a tokenised
        name is followed by an open paren; that is worse than no colour, so it
        falls back to plain escaped text.
        """

        try:
            out = x52URM.CodeView.colorize(
                code, interactiveVariables=_URM_CLICKABLE,
                interactiveLabels=_URM_CLICKABLE,
                evaluateConditions=False)

            if out and "URMTKN" not in out:
                return out
        except Exception:
            pass

        return (code or "").replace("{", "{{")

    def _urm_words(text):
        """Our own prose: italic, so it never reads as the game's code."""

        return "{i}%s{/i}" % text.replace("{", "{{")

    def _urm_truth(expression):
        """
        Whether a condition holds right now, or None if that cannot be said.

        BaseException is caught, not Exception: this runs while the overlay is
        being built, and a game condition that calls sys.exit would otherwise
        surface as Ren'Py's exception screen rather than a quiet unknown.
        """

        try:
            return bool(eval(str(expression), renpy.store.__dict__))
        except BaseException:
            return None

    def _urm_clip(text, limit):

        if len(text) <= limit:
            return text

        # U+2026 is present in Roboto-Regular; U+2192 and the box-drawing
        # characters are not, which is why none of them appear in this file.
        return text[:limit - 1] + u"…"

    # ------------------------------------------------------------------
    # What an arm actually changes
    # ------------------------------------------------------------------

    # The four readers below are the shared story graph's (rework move 2):
    # one copy of "what a statement says" and "what an arm changes" for the
    # cards, the maze, the map and the branch tracker.

    def _urm_statement(node):
        """One AST node as one line of plain text, or None to ignore it."""

        return _urmsg_stmt_text(node)

    # Calls into Ren'Py that only change what is seen or heard, or how the
    # engine behaves - never the story. renpy.jump and renpy.call are not
    # here: they decide where the choice leads.
    _URM_NOISE_CALLS = _URMSG_NOISE

    def _urm_noise(line):
        """A python line that only touches presentation, not the story."""

        return _urmsg_noise(line)

    def _urm_idempotent(text):
        """
        Whether running this twice is the same as running it once.

        This is what decides when a duplicate may be dropped. A jump or a call
        leaves the block, and a plain assignment to a value overwrites. An
        augmented assignment or a bare function call does not: `love += 1`
        drawn once for code that runs it ten times is a false statement about
        the game, and that was the single most frequent falsehood in the first
        version of this file.
        """

        if text.startswith("jump ") or text.startswith("call ") or text == "return":
            return True

        head, sep, tail = text.partition("=")

        if not sep or tail.startswith("="):
            return False

        head = head.strip()

        if not head or not (head[0].isalpha() or head[0] == "_"):
            return False

        for ch in head:
            if not (ch.isalnum() or ch in "._"):
                return False

        return True

    def _urm_python_lines(node, dropped):
        """
        The assignments in a python block, without its own control flow.

        A `python:` block is stored verbatim, so its body can contain if/for/
        while/def lines. Those are counted (in dropped[0]) rather than shown:
        drawing them would put exactly the kind of text back on screen that
        this whole design removes.
        """

        lines, drop = _urmsg_py_lines(node)
        dropped[0] += drop
        return python_list(lines)

    def _urm_flatten(nodes, guards=(), depth=0, dropped=None):
        """
        An arm's nodes as (guards, text) records, innermost guard last.

        A nested if does not produce a line of code - it produces a guard on
        the records inside it, which the screen draws as its own "only if"
        row. That is what keeps a nested test from looking like a gate. When
        an if has an else and every arm does exactly the same thing under no
        deeper guard, the guards come off (the lift, _urmsg_lift).
        """

        return _urmsg_flat(nodes, guards, depth, dropped)

    def _urm_reduce(records):
        """
        L2 and L3, and an honest count of what they removed.

        Both only ever remove a row that another row already accounts for, and
        both are now limited to statements where that is actually true. A
        repeated `love += 1` is not a duplicate of itself - it is ten points of
        love - so repeats are collapsed into one row carrying a multiplier
        rather than silently thrown away.

        Returns (records, removed) where a record is (guards, text, count) and
        removed is how many rows were dropped outright, for the "+N more" tally.
        """

        plain = set(text for guards, text in records if not guards)

        removed = 0
        order = []
        index = {}

        for guards, text in records:

            # L2: a guarded copy of something that also happens unguarded,
            # and only when running it twice would change nothing.
            if guards and text in plain and _urm_idempotent(text):
                removed += 1
                continue

            key = (guards, text)

            if key in index:
                # L3: the same statement under the same guards. Idempotent
                # ones collapse; the rest keep a count, because the number of
                # times they run is the whole point of them.
                if _urm_idempotent(text):
                    removed += 1
                else:
                    index[key][2] += 1
                continue

            entry = [guards, text, 1]
            index[key] = entry
            order.append(entry)

        return [(g, t, n) for g, t, n in order], removed

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

    # ------------------------------------------------------------------
    # The chain of gates
    # ------------------------------------------------------------------

    def _urm_chain():
        """
        Every gate ahead of the cursor, in the order they are tested.

        The whole chain is collected before any card is built, so the summary
        can say how many gates there really are even when the card list is
        capped. The walk is the story graph's (_urmsg_chain, rework move 5)
        and so is each step (_urmsg_step_urm, move 5b: URM's nextNode, read
        from the same statement fields). A step URM's own code would raise
        on - a jump ahead that cannot be followed - no longer empties the
        card (idea 2): the gates found before it are returned, closed by
        the step that says where the chain stops.
        """

        steps = python_list()

        # Parallel to steps: (if-statement, arm index) for each, or (None, -1)
        # for the fall-through tail. Kept on URM's constant store, so the
        # force-a-path buttons can name the exact arm without walking again.
        meta = python_list()
        x52URM.Var._urmChainMeta = meta

        detected = x52URM.PathDetection.nextIfStatement

        if not detected:
            return steps

        detection = x52URM.PathDetection

        chain = _urmsg_chain(detected[0], detection.lookAheadLimit,
                             detection.nodeIsBlocking, _urmsg_step_urm,
                             _URM_MAX_GATES + 4)
        meta.extend(chain.meta)
        steps.extend(chain.steps)
        return steps

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

    def _urm_summary(gates, truncated, live, unknown):

        count = "%d+" % gates if truncated else "%d" % gates
        word = "gate" if gates == 1 and not truncated else "gates"

        if unknown:
            return "%s %s, cannot tell which" % (count, word)

        if live:
            return "%s %s, #%d runs" % (count, word, live)

        return "%s %s, none match" % (count, word)

    def urm_path_cards():

        try:
            steps = _urm_chain()

            if not steps:
                return ("", [])

            success = _urm_signal("success")
            error = _urm_signal("error")

            # The closing card - what happens when nothing matches - is the
            # one a reader needs most, so it gets a reserved slot rather than
            # being pushed off the end by the gates above it.
            closes = steps and steps[-1][0] in ("else", "tail")
            budget = _URM_MAX_GATES - (1 if closes else 0)

            cards = []
            number = 0
            gates = 0
            shown = 0
            live = 0
            unknown = False
            fired = False
            skipped = False

            for kind, cond, payload in steps:

                # Only a real test is a gate. The fall-through card is what
                # happens when none of them match, not one of them.
                if kind == "gate":
                    gates += 1

                    number += 1

                    truth = None if fired else _urm_truth(cond)

                    if truth is None and not fired:
                        unknown = True

                    if truth is True and not fired and not unknown:
                        fired = True
                        live = number
                        icon = _urm_tint(_URM_ICON_LIVE, success)
                    elif unknown and not fired:
                        icon = _URM_ICON_UNKNOWN
                    else:
                        icon = _urm_tint(_URM_ICON_DEAD, error)

                    if shown >= budget:
                        skipped = True
                        continue

                    shown += 1
                    cards.append((icon, "%d" % number,
                                  _urm_colorize(str(cond)),
                                  _urm_effects(payload)))

                elif kind == "else":
                    icon = _urm_fallback_icon(fired, unknown, success, error)
                    fired = True
                    cards.append((icon, "",
                                  _urm_words("nothing above matches"),
                                  _urm_effects(payload)))

                else:
                    icon = _urm_fallback_icon(fired, unknown, success, error)
                    cards.append((icon, "",
                                  _urm_words("nothing above matches"),
                                  [(_URM_ICON_EFFECT, _urm_colorize(payload))]))

            if not cards:
                return ("", [])

            return (_urm_summary(gates, skipped, live, unknown), cards)

        except BaseException:
            return ("", [])

    def _urm_choice_nodes(choice):
        """
        A choice's own AST block.

        URM keeps the (text, condition, block) tuple on a name-mangled
        attribute. It is the only private field this file touches, so it is
        guarded and falls back to the text URM already exposes.
        """

        try:
            return choice._m1_choices__choice[2]
        except Exception:
            return None

    def urm_choice_cards():

        try:
            error = _urm_signal("error")
            success = _urm_signal("success")

            cards = []
            available = 0

            choices = x52URM.Choices.currentChoices or []

            try:
                routes = urm_maze_for(choices)
            except BaseException:
                routes = None
            later = routes[2] if routes is not None else None
            routes = routes[0] if routes is not None else None

            for index, choice in enumerate(choices):

                condition = getattr(choice, "condition", None) or "True"
                open_now = _urmsg_no_test(condition) or (
                    _urm_truth(condition) is True)

                if open_now:
                    available += 1

                if len(cards) >= _URM_MAX_GATES:
                    continue

                if _urmsg_no_test(condition):
                    head = _urm_words("always")
                else:
                    head = _urm_colorize(str(condition))

                icon = (_urm_tint(_URM_ICON_LIVE, success) if open_now
                        else _urm_tint(_URM_ICON_DEAD, error))

                nodes = _urm_choice_nodes(choice)

                if nodes is None:
                    effects = [(_URM_ICON_EFFECT, _urm_colorize(line))
                               for line in (getattr(choice, "code", "")
                                            or "").split("\n")
                               if line.strip()][:_URM_MAX_ROWS]
                    if not effects:
                        effects = [(_URM_ICON_EFFECT,
                                    _urm_words("no tracked changes"))]
                else:
                    effects = None
                    if routes is not None and index < len(routes):
                        try:
                            effects = urm_maze_rows(routes[index]) or None
                        except BaseException:
                            effects = None
                    if effects is None:
                        effects = _urm_effects(nodes)
                    elif later is not None and index < len(later):
                        effects = python_list(effects) + python_list(later[index])

                cards.append((icon, "%d" % (index + 1), head, effects))

            if not cards:
                return ("", [])

            # The count is the menu's, not the card list's - URM prints its own
            # "[N] hidden" line directly above this and the two must agree.
            total = len(choices)
            word = "choice" if total == 1 else "choices"
            more = total - len(cards)
            extra = _urm_words(", %d not shown" % more) if more else ""

            return ("%d %s, %d open%s" % (total, word, available, extra), cards)

        except BaseException:
            return ("", [])


