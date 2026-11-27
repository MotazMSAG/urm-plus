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

    _urm_setting_add("urmcRollback", 500)

    class _URMRState(python_object):
        def __init__(self):
            self.game_hard = None
            self.game_length = None
            self.applied = None

    def _urmr_state():
        return _urm_kept("rollback", _URMRState)

    def _urmr_apply():
        st = _urmr_state()
        if st.game_hard is None:
            # Read on the first interaction, after every init block of the
            # game has had its say.
            st.game_hard = config.hard_rollback_limit
            st.game_length = config.rollback_length
        want = _urm_setting("urmcRollback")
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
            _urmr_check_skip_hold()
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
            renpy.notify("MRM: no choice in the rollback history to go back to")
            return False

        steps = 0
        for entry in entries[target:]:
            if getattr(entry, "hard_checkpoint", False):
                steps += 1
        if steps <= 0:
            steps = 1

        if steps > getattr(log, "rollback_limit", 0):
            renpy.notify("MRM: the game blocks going back that far")
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
        """Middle-click on a Skip button rolls back to the last choice."""

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
            if getattr(ev, "type", None) == _urmr_mouse_up and getattr(ev, "button", None) == 2:
                if _urmr_skip_focused():
                    urmr_back_to_choice()
                    raise _urmr_sys.modules["renpy.display.core"].IgnoreEvent()
            return None

    try:
        import pygame_sdl2 as _urmr_pygame
    except Exception:
        import pygame as _urmr_pygame
    _urmr_mouse_up = _urmr_pygame.MOUSEBUTTONUP
    _urmr_mouse_click_events = (_urmr_pygame.MOUSEBUTTONDOWN, _urmr_mouse_up)

    # ------------------------------------------------------------------
    # Resume a skip stopped at a check
    # ------------------------------------------------------------------
    #
    # Let Ren'Py complete an ordinary dialogue dismissal with skipping off,
    # then restore the mode held by the corner card for the next interaction.

    _urmr_say_event = renpy.display.behavior.SayBehavior.event

    def _urmr_resume_on_dismiss(self, ev, x, y, st):
        if ev.type not in _urmr_mouse_click_events or ev.button != 1 or config.skipping:
            return _urmr_say_event(self, ev, x, y, st)
        resume = _urm_skip_held()
        if not resume:
            return _urmr_say_event(self, ev, x, y, st)

        # An AFM timeout can also return True on a mouse event. The engine
        # calls allow_dismiss only on the manual path, after its focus,
        # rollback-side and AFM cancellation checks.
        previous = self.allow_dismiss
        dismissed = [False]

        def allow_dismiss():
            dismissed[0] = not previous or bool(previous())
            return dismissed[0]

        self.allow_dismiss = allow_dismiss
        try:
            result = _urmr_say_event(self, ev, x, y, st)
        finally:
            self.allow_dismiss = previous

        if result is True and dismissed[0] and _urm_skip_held() == resume:
            _urm_skip_forget()
            if not config.skipping and config.allow_skipping and renpy.store._skipping:
                config.skipping = resume
        return result

    renpy.display.behavior.SayBehavior.event = _urmr_resume_on_dismiss

    def _urmr_check_skip_hold():
        if not _urm_skip_held():
            return
        # A restarted skip belongs to the player now. Discard the old hold
        # so manually stopping again cannot restart it on a dialogue click.
        if config.skipping:
            _urm_skip_forget()
            return
        # Rolling back is the player stopping on purpose: a resume pending
        # from before must not restart the skip on the next click.
        try:
            log = renpy.game.log
            if renpy.game.after_rollback or (log is not None and log.in_rollback()):
                _urm_skip_forget()
                return
        except Exception:
            pass
        if isinstance(_urmsg_here(), renpy.ast.Menu):
            _urm_skip_forget()

    def _urmr_forget_resume():
        _urm_skip_forget()

    if _urmr_forget_resume not in config.after_load_callbacks:
        config.after_load_callbacks.append(_urmr_forget_resume)

    urmr_middle_click = _URMRMiddleClick()

    # ---- the Quick access action and settings page (the registry, 01_urm_door)

    _urm_entry_add("back_to_choice", "Back to last choice", u"\ue166", urmr_back_to_choice,
                   shown=lambda: False)
    _urm_row_add("rollback_length", "game", "Rollback length",
                 "How many steps back you can scroll. Longer costs memory and makes saves larger.",
                 (("Game default", 0), ("500", 500), ("2000", 2000)),
                 setting="urmcRollback", order=10)


