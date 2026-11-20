# Keeps Ren'Py's hyperlink protocol dispatch alive.
#
# Ren'Py routes a link by looking its protocol up in config.hyperlink_handlers.
# Add-ons register their dialogs there - URM uses the "URMVarDialog" and
# "URMLabelDialog" protocols for its variable and label editors.
#
# A game that sets config.hyperlink_callback (commonly to open its Patreon or
# Discord link in a browser) makes renpy/common/00compat react by replacing the
# whole style.default.hyperlink_functions tuple with
# (config.hyperlink_styler, config.hyperlink_callback, config.hyperlink_focus).
# That discards Ren'Py's own hyperlink_function, the only thing that consults
# config.hyperlink_handlers, and every link in the game then goes to
# webbrowser.open() whatever its protocol - so clicking a variable in URM asks
# the OS to find an application for a "urmvardialog:" URL.
#
# _mc_dispatch below is Ren'Py's own routing logic with the game's callback
# kept as the fallback for anything that is not a registered protocol. It goes
# into both places the engine can consult on a click, and a per-interaction
# check puts it back if anything replaces it. Registered protocols reach their
# handler; the game's own links behave exactly as the game intended.
#
# The init priority is late so this sees the game's final configuration, and
# the per-interaction check makes the ordering not matter anyway.

init 1000 python:

    def _mc_split(target):

        if ":" not in target:
            default_protocol = getattr(
                config, "hyperlink_protocol", "call_in_new_context")
            target = default_protocol + ":" + target

        protocol, _, value = target.partition(":")

        return target, protocol, value

    def _mc_styler(target):
        return style.hyperlink_text

    def _mc_dispatch(target):

        target, protocol, value = _mc_split(target)

        handlers = getattr(config, "hyperlink_handlers", None) or { }

        if protocol in handlers:
            return handlers[protocol](value)

        # Kept on the function rather than in a store variable, so rollback
        # cannot take it away.
        fallback = getattr(_mc_dispatch, "stock_callback", None)

        if fallback is not None:
            return fallback(target)

        try:
            import webbrowser
            webbrowser.open(target)
        except Exception:
            pass

    _mc_dispatch.dispatches_protocols = True

    def _mc_sensitive(target):

        target, protocol, value = _mc_split(target)

        table = getattr(config, "hyperlink_sensitive", None) or { }

        if protocol not in table:
            return True

        return table[protocol](value)

    def _mc_install():

        existing = getattr(config, "hyperlink_callback", None)

        if existing is not None and not getattr(existing, "dispatches_protocols", False):
            _mc_dispatch.stock_callback = existing

        # Covers the case where 00compat copies this into the style tuple on a
        # later init pass.
        config.hyperlink_callback = _mc_dispatch

        # Ren'Py's tuple is (styler, clicked, focus, sensitive). Keep the
        # arity: text.py indexes 2 for focus and 3 for sensitive.
        style.default.hyperlink_functions = (
            _mc_styler, _mc_dispatch,
            getattr(config, "hyperlink_focus", None), _mc_sensitive)

        renpy.style.rebuild()

    def _mc_ensure():

        functions = style.default.hyperlink_functions

        if functions and len(functions) > 1 and functions[1] is _mc_dispatch:
            return

        _mc_install()

    if _mc_ensure not in config.interact_callbacks:
        config.interact_callbacks.append(_mc_ensure)
