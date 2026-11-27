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

    _URM_MAX_TOTAL_ROWS = 12
    _URM_MAX_DEPTH = 3

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
