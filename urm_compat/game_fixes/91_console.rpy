# ---------------------------------------------------------------------------
# The Ren'Py console, from the URM+ menu
# ---------------------------------------------------------------------------
#
# URM opened the engine's console (shift+O) in builds that have it switched
# off; a player without URM lost that. The engine keeps its console object
# only in a developer build or with config.console set (00console: the
# object is made at init 1701 in those cases, else it stays None, and
# _console.enter() then does nothing). The menu entry makes the object when it
# is missing and opens the console. Nothing is kept: no state of ours,
# nothing in the game's store, nothing in a save. An engine with no console
# module leaves the entry out of the menu.
#
# It does not call the engine's enter(): in a context that rolls back, enter()
# starts the console and then rolls back with current_label="_console",
# which raises one of the engine's own control exceptions for its loop to
# take (renpy.game.CONTROL_EXCEPTIONS). The menu's doorway (_urm_open) catches
# every exception of an entry, so the rollback was swallowed half done: the
# menu closed, the dialogue box went, and no console came (the user's report,
# 2026-11-24). What enter() does in a context with no rollback is what is
# done here: start the console, run the engine's console label in a context
# of its own, and come back when it is closed.

init 999 python:

    def _urmcn_module():
        """The engine's console module, or None when this engine has none."""
        mod = getattr(renpy.store, "_console", None)
        if mod is None or not hasattr(mod, "DebugConsole"):
            return None
        return mod

    def urmcn_open():
        """Open the console, making the engine's console object first when
        the build left it out."""
        mod = _urmcn_module()
        if mod is None:
            raise Exception("this engine has no console")
        if getattr(mod, "console", None) is None:
            mod.console = mod.DebugConsole()
        mod.console.start()
        renpy.call_in_new_context("_console")

    _urm_entry_add("console", "Console", u"", urmcn_open, key="alt_K_o", key_words="Alt+O",
                   shown=lambda: _urmcn_module() is not None, group=1, order=70)
