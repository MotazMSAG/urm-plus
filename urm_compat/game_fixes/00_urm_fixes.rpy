# ---------------------------------------------------------------------------
# A game whose config.font_transforms is not a table
# ---------------------------------------------------------------------------
#
# My Femdom Wife 0.7 (Ren'Py 8.3.7), modules/utils/main.rpyc:89, init 0:
#     config.font_transforms = ["smooth"]
# The engine only looks in that table once the player picks a font override,
# so the game itself runs. URM's FontsHandler (compiled, init 999, and its
# file loads before this one) indexes the table by name:
# "TypeError: list indices must be integers or slices, not str" - and the
# game did not start.
#
# URM's code is compiled, and at its own priority it runs before anything
# here. So this one block runs a priority earlier: while URM's FontsHandler
# runs, an empty table stands in for a value that is not one - there is
# nothing in it to wrap, and URM starts. The first thing the block below
# does is put the game's own object back, untouched. A real table is never
# touched here: URM wraps its entries as it always did.
#
# (87_font, URM+'s own "Game font", writes to the same table: it is offered
# only where the table is one.)

init 998 python:

    # (the game's own value, the stand-in) while URM starts; else empty.
    _urm_font_hold = python_list()

    def _urm_fonts_open():
        if not hasattr(renpy.config, "font_transforms"):
            return
        own = renpy.config.font_transforms
        if isinstance(own, python_dict):
            return
        stand_in = python_dict()
        _urm_font_hold.append((own, stand_in))
        renpy.config.font_transforms = stand_in
        print("URM+: config.font_transforms is a %s in this game, not a table. "
              "URM starts without it; the game keeps its own." % (type(own).__name__,))

    def _urm_fonts_close():
        while _urm_font_hold:
            own, stand_in = _urm_font_hold.pop()
            # Still the stand-in: the game's own goes back. Anything else
            # was put there by the game since, and stays.
            if renpy.config.font_transforms is stand_in:
                renpy.config.font_transforms = own

    _urm_fonts_open()


# Small compatibility fixes for URM, applied inside URM's own archive.
#
# Both of these are guarded: on a game that does not have the problem they do
# nothing at all. They run at a late init priority so they see the game's
# final state, and before screens are prepared.


init 999 python:

    # URM's own init 999 statements have run: the game's font table goes
    # back (see the block above).
    _urm_fonts_close()


    # ------------------------------------------------------------------
    # A game that defines its own EndReplay
    # ------------------------------------------------------------------
    #
    # Ren'Py's EndReplay is a screen action class taking an optional `confirm`
    # argument, and URM's watchpanel uses it as `action EndReplay(False)`.
    #
    # Some games define a plain zero-argument helper of the same name in the
    # store, which replaces Ren'Py's. URM's screen then fails to prepare with
    # "EndReplay() takes 0 positional arguments but 1 was given", and the game
    # will not start with URM installed.
    #
    # The shim makes the name work for both callers: no argument keeps doing
    # whatever the game's helper did, an argument gives back a real action.

    if not isinstance(EndReplay, type) and not getattr(EndReplay, "urm_shim", False):

        _urm_game_end_replay = EndReplay

        class _URMEndReplay(Action, DictEquality):
            """
            Stands in for Ren'Py's EndReplay action.
            """

            def __init__(self, confirm=True):
                self.confirm = confirm

            def __call__(self):
                renpy.end_replay()

        def EndReplay(confirm=None):
            if confirm is None:
                return _urm_game_end_replay()

            return _URMEndReplay(confirm)

        EndReplay.urm_shim = True


    # ------------------------------------------------------------------
    # A game that redirects every hyperlink
    # ------------------------------------------------------------------
    #
    # Ren'Py routes a link by looking its protocol up in
    # config.hyperlink_handlers; URM registers its variable and label editors
    # as the "URMVarDialog" and "URMLabelDialog" protocols.
    #
    # A game that sets config.hyperlink_callback - commonly to open its Patreon
    # or Discord link in a browser - makes renpy/common/00compat replace the
    # whole style.default.hyperlink_functions tuple with
    # (config.hyperlink_styler, config.hyperlink_callback,
    # config.hyperlink_focus). That discards Ren'Py's own hyperlink_function,
    # the only thing that consults config.hyperlink_handlers, so every link in
    # the game goes to webbrowser.open() whatever its protocol - and clicking a
    # variable in URM asks the OS to find an application for a "urmvardialog:"
    # link.
    #
    # Only games that set that callback are affected, so this leaves everything
    # alone unless one has. Running at init means the style tuple is set before
    # styles are built, so no rebuild is needed; and the translation system
    # snapshots styles after init, so changing the language keeps this too.

    _urm_game_hyperlink_callback = getattr(config, "hyperlink_callback", None)

    # Bracketed, not a backslash continuation: Ren'Py's lexer does not join a
    # backslash followed by CRLF, so a file saved with Windows line endings
    # would orphan the next line and fail to parse.
    if (_urm_game_hyperlink_callback is not None
            and not getattr(_urm_game_hyperlink_callback, "urm_shim", False)):

        def _urm_split(target):

            if ":" not in target:
                default_protocol = getattr(
                    config, "hyperlink_protocol", "call_in_new_context")
                target = default_protocol + ":" + target

            protocol, _, value = target.partition(":")

            return target, protocol, value

        def _urm_styler(target):
            return style.hyperlink_text

        def _urm_dispatch(target):

            target, protocol, value = _urm_split(target)

            handlers = getattr(config, "hyperlink_handlers", None) or { }

            if protocol in handlers:
                return handlers[protocol](value)

            return _urm_game_hyperlink_callback(target)

        _urm_dispatch.urm_shim = True

        def _urm_sensitive(target):

            target, protocol, value = _urm_split(target)

            table = getattr(config, "hyperlink_sensitive", None) or { }

            if protocol not in table:
                return True

            return table[protocol](value)

        # Covers 00compat copying this into the style tuple on a later pass.
        config.hyperlink_callback = _urm_dispatch

        # Ren'Py's tuple is (styler, clicked, focus, sensitive). Keep the
        # arity: text.py indexes 2 for focus and 3 for sensitive.
        style.default.hyperlink_functions = (
            _urm_styler, _urm_dispatch,
            getattr(config, "hyperlink_focus", None), _urm_sensitive)

