# ---------------------------------------------------------------------------
# Longer rollback, and back to the last choice with a middle click on Skip
# ---------------------------------------------------------------------------
#
# Ren'Py lets the player roll back 100 steps (config.hard_rollback_limit) out
# of a history of about 128 recorded statements (config.rollback_length) -
# a cautious default from when memory was scarce. The setting raises both,
# 500 steps by default; a game that already asks for more keeps its own. The
# cost is memory and save size: every save carries the history.
#
# Middle-clicking a Skip button rolls back to the last choice the player
# made. Right-click on Skip already skips forward to the next choice (Ren'Py's
# fast skip), so the middle button is its mirror. Middle-click everywhere else
# keeps its usual job of hiding the text window: the catcher only acts while
# the button under the mouse is a Skip button.
#
# Finding the choice: Ren'Py takes a checkpoint after each interaction and
# stores what the interaction returned on that history entry. A menu returns
# the option picked - a number, or the value a python menu or a screen
# returned - where dialogue returns True. So the newest entry holding such a
# value is the last choice, and rolling back the number of checkpoints up to
# and including it lands on that menu with its options open again.
#
# The game's own rollback blocks are respected: if one stands between here
# and the choice, nothing happens and a notification says why.

init 999 python:

    import sys as _urmr_sys

    try:
        x52URM.SettingsClass.defaultValues.setdefault("urmcRollback", 500)
    except Exception as error:
        print("URM+: rollback setting not registered (%s)" % (error,))

    class _URMRState(python_object):
        def __init__(self):
            self.game_hard = None
            self.game_length = None
            self.applied = None
            self.resume = None             # the skip path detection stopped

    def _urmr_state():
        holder = x52URM.Var
        st = getattr(holder, "_urmrState", None)
        if st is None:
            st = _URMRState()
            holder._urmrState = st
        return st

    def _urmr_apply():
        st = _urmr_state()
        if st.game_hard is None:
            # Read on the first interaction, after every init block of the
            # game has had its say.
            st.game_hard = config.hard_rollback_limit
            st.game_length = config.rollback_length
        try:
            want = x52URM.Settings.get("urmcRollback")
        except Exception:
            want = 500
        if want is None:
            want = 500
        if want == st.applied:
            return
        st.applied = want
        if want:
            config.hard_rollback_limit = max(st.game_hard, want)
            config.rollback_length = max(st.game_length, want + want // 2)
        else:
            config.hard_rollback_limit = st.game_hard
            config.rollback_length = st.game_length

    def _urmr_interact():
        try:
            _urmr_apply()
        except Exception:
            pass
        try:
            _urmr_forget_resume_at_menu()
        except Exception:
            pass

    if _urmr_interact not in config.interact_callbacks:
        config.interact_callbacks.append(_urmr_interact)


    def _urmr_is_choice(entry):
        value = getattr(entry, "forward", None)
        if value is None or isinstance(value, bool):
            return False
        try:
            return isinstance(value, (int, float) + _urmi_text)
        except Exception:
            return isinstance(value, (int, float, str))

    def urmr_back_to_choice():
        """Roll back to the last choice made. False when there is none within reach."""

        try:
            log = renpy.game.log
            entries = log.log
        except Exception:
            return False

        target = None
        for i in range(len(entries) - 1, -1, -1):
            entry = entries[i]
            if entry is log.current:
                # The statement on screen has not been answered yet.
                continue
            if _urmr_is_choice(entry):
                target = i
                break

        if target is None:
            renpy.notify("URM: no choice in the rollback history to go back to")
            return False

        steps = 0
        for entry in entries[target:]:
            if getattr(entry, "hard_checkpoint", False):
                steps += 1
        if steps <= 0:
            steps = 1

        if steps > getattr(log, "rollback_limit", 0):
            renpy.notify("URM: the game blocks going back that far")
            return False

        renpy.rollback(checkpoints=steps)
        return True

    def _urmr_skip_focused():
        try:
            focus = _urmr_sys.modules["renpy.display.focus"].get_focused()
        except Exception:
            return False
        action = getattr(focus, "action", None)
        if isinstance(action, (python_list, tuple)):
            actions = action
        else:
            actions = (action,)
        for item in actions:
            if type(item).__name__ == "Skip":
                return True
        return False

    class _URMRMiddleClick(renpy.Displayable):
        """
        Two mouse jobs, from the top layer so nothing below sees them first:

        * a middle click on a Skip button rolls back to the last choice
        * after URM stopped a skip on path detection, the next left click on
          empty space resumes that skip (see _urmr_cancel_skipping)
        """

        # The quick menu's screen lands in saves, and this with it. Saved as
        # a plain Null, so a save never needs URM+ to load: a save made with
        # the old pickling said "store._URMRMiddleClick" and failed to load
        # wherever URM+ was missing (Freeloading Family, 2026-11-17). The
        # screen builds a fresh one after loading anyway.
        def __reduce__(self):
            return (renpy.display.layout.Null, ())

        def render(self, width, height, st, at):
            return renpy.Render(0, 0)

        def event(self, ev, x, y, st):
            kind = getattr(ev, "type", None)
            button = getattr(ev, "button", None)
            if kind == _urmr_mouse_up and button == 1:
                state = _urmr_state()
                if state.resume and not config.skipping and _urmr_empty_click():
                    config.skipping = state.resume
                    state.resume = None
                    renpy.restart_interaction()
                    # Taken, not passed on: the dialogue's own click handler
                    # stops skipping when it sees a click while skipping.
                    raise _urmr_sys.modules["renpy.display.core"].IgnoreEvent()
            elif kind == _urmr_mouse_up and button == 2:
                if _urmr_skip_focused():
                    urmr_back_to_choice()
                    raise _urmr_sys.modules["renpy.display.core"].IgnoreEvent()
            return None

    try:
        import pygame_sdl2 as _urmr_pygame
    except Exception:
        import pygame as _urmr_pygame
    _urmr_mouse_up = _urmr_pygame.MOUSEBUTTONUP

    def _urmr_empty_click():
        """No button under the mouse: the click is one that advances dialogue."""

        try:
            focus = _urmr_sys.modules["renpy.display.focus"].get_focused()
        except Exception:
            return False
        return focus is None or type(focus).__name__ == "SayBehavior"


    # ------------------------------------------------------------------
    # Resume a skip that path detection stopped
    # ------------------------------------------------------------------
    #
    # With "Stop skipping on path detection" on, URM cancels the skip the
    # moment a path card appears (watchpanel.rpy.x52:310-311, CancelSkipping
    # in utils.rpy:121). Clicking on then only advances one line at a time.
    # The skip URM cancelled - slow, or fast to the next choice - is
    # remembered here, and the next left click on empty space picks it up
    # again. A click on a button does not, a choice menu forgets it (Ren'Py
    # stops skipping there anyway), and so do rolling back - the player
    # stopping on purpose - and loading a save.

    def _urmr_cancel_skipping_wrap(original):
        def cancel(self, *args, **kwargs):
            if config.skipping:
                _urmr_state().resume = config.skipping
            return original(self, *args, **kwargs)
        cancel._urmr_original = original
        return cancel

    try:
        _urmr_cancel = x52URM.CancelSkipping.__call__
        if not hasattr(_urmr_cancel, "_urmr_original"):
            x52URM.CancelSkipping.__call__ = _urmr_cancel_skipping_wrap(_urmr_cancel)
    except Exception as error:
        print("URM+: skipping will not resume after path detection (%s)" % (error,))

    def _urmr_forget_resume_at_menu():
        state = _urmr_state()
        if not state.resume:
            return
        # Rolling back is the player stopping on purpose: a resume pending
        # from before must not restart the skip on the next click.
        try:
            log = renpy.game.log
            if renpy.game.after_rollback or (log is not None and log.in_rollback()):
                state.resume = None
                return
        except Exception:
            pass
        if isinstance(_urmsg_here(), renpy.ast.Menu):
            state.resume = None

    def _urmr_forget_resume():
        _urmr_state().resume = None

    if _urmr_forget_resume not in config.after_load_callbacks:
        config.after_load_callbacks.append(_urmr_forget_resume)

    urmr_middle_click = _URMRMiddleClick()


