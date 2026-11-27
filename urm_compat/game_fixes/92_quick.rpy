# ---------------------------------------------------------------------------
# Quick access: Auto, Skip and Skip unseen in a slim tray under the URM+ button
# ---------------------------------------------------------------------------
#
# The user's pick 1a (DECISIONS.md, Displays, 2026-11-23; drawings in
# research/quick-access), made sleek: turned on from the URM+ menu, a slim
# tray of three icon buttons hangs under the URM+ button. It is a part the
# button draws in its own drag (_urm_under_add, 01_urm_door; placed by
# 17_hub), so it moves with the button, never sits in the badge's room and
# hides while the URM+ menu is open; the choices card's usual spot moves
# down past it. Its own dark ground: it never takes the button's yellow,
# green or blue.
#
# Every button runs the engine's own action, which decides what can be done
# and what is lit, read at every draw:
# - Auto: auto-forward, at the speed the game's settings give. A game whose
#   speed is 0 ("never") would light Auto and never move on: turning it on
#   there sets the engine's usual starting speed for this game first.
# - Skip: a click skips as the game's Skip does; a right click skips to the
#   next choice and a middle click goes back to the last choice made, both
#   with no question asked. The middle click is the "back to the last
#   choice" step the URM+ menu has, asked for by name through the doorway.
# - Skip unseen: the engine's own "skip unseen text", for this game.
#
# Right and middle clicks on the tray's buttons are taken there (a right
# click by the button's alternate, a middle click by a key the tray holds
# only while one of its buttons is pointed at), so they never open the
# game's menu or hide its windows; anywhere else they reach the game as
# before. The buttons are not the engine's Skip action, so the quick bar's
# middle-click catcher (81_rollback) never acts on them: one action a click.
#
# Its options are on the settings tab "Quick access": the tray, and each of
# its buttons, This game and All games.

init 999 python:

    import sys as _urmq_sys

    _urm_setting_add("urmcQuick", False)
    _urm_setting_add("urmcQuickAuto", True)
    _urm_setting_add("urmcQuickSkip", True)
    _urm_setting_add("urmcQuickUnseen", True)
    _urm_setting_add("urmcQuickMenu", False)
    _urm_setting_add("urmcQuickStory", False)
    _urm_setting_add("urmcQuickSettings", False)

    # sizes at 1080 lines and text size Normal: the tray's padding, a
    # button's side, the space between buttons, an icon, the lit line's
    # width and height, the tip's gap to the tray
    URMQ = python_dict((("pad", 4), ("button", 36), ("space", 3), ("icon", 22),
                        ("lit", (14, 2)), ("tip", 8)))
    URMQ_AUTO_SPEED = 15        # the engine's usual starting auto speed (its slider's middle)


    def urmq_px(name):
        return urmk_px(URMQ[name] * urmk_look.text)

    # ---- what the buttons do: the engine's own actions

    def _urmq_auto_action():
        return Preference("auto-forward", "toggle")

    def urmq_auto():
        if not _preferences.afm_enable and not _preferences.afm_time:
            _preferences.afm_time = URMQ_AUTO_SPEED
        _urmq_auto_action()()
        renpy.restart_interaction()

    def urmq_skip(fast=False):
        """As the game's Skip (fast: to the next choice, never asked first),
        when the engine lets it run here."""
        action = Skip(fast=fast, confirm=False)
        if not renpy.is_sensitive(action):
            return
        if fast and config.skipping and config.skipping != "fast":
            # from a slow skip on to the next choice, where the engine's
            # Skip would only stop
            config.skipping = None
        action()

    def urmq_back():
        """Back to the last choice made: the URM+ menu's own step."""
        return _urm_open("back_to_choice")

    def urmq_unseen():
        Preference("skip", "toggle")()
        renpy.restart_interaction()

    def urmq_open(name):
        _urm_open(name)

    def urmq_middle():
        """A middle click on the tray: on Skip, back to the last choice; on
        any other button, nothing (it never hides the game's windows)."""
        if urmq_pointed() == "skip":
            urmq_back()

    # ---- what shows

    def urmq_on():
        return bool(_urm_setting("urmcQuick"))

    def urmq_buttons():
        """[(name, icon, lit, action, right click)] of the buttons the
        settings show, lit as the engine says now."""
        out = python_list()
        if _urm_setting("urmcQuickAuto"):
            out.append(("auto", u"",
                        bool(renpy.is_selected(_urmq_auto_action()) and _preferences.afm_time),
                        Function(urmq_auto), NullAction()))
        if _urm_setting("urmcQuickSkip"):
            out.append(("skip", u"",
                        bool(renpy.is_selected(Skip()) or renpy.is_selected(Skip(fast=True))),
                        Function(urmq_skip), Function(urmq_skip, True)))
        if _urm_setting("urmcQuickUnseen"):
            out.append(("unseen", u"", bool(_preferences.skip_unseen),
                        Function(urmq_unseen), NullAction()))
        if _urm_setting("urmcQuickMenu"):
            out.append(("menu", u"\ue5d2", False, Function(urmq_open, "menu"), NullAction()))
        if _urm_setting("urmcQuickStory"):
            out.append(("story_line", u"\ue922", False, Function(urmq_open, "story_line"), NullAction()))
        if _urm_setting("urmcQuickSettings"):
            out.append(("settings", u"\ue8b8", False, Function(urmq_open, "settings"), NullAction()))
        return out

    def urmq_shown():
        return urmq_on() and bool(urmq_buttons())

    def urmq_height():
        return 2 * urmq_px("pad") + urmq_px("button")

    def urmq_pill_offset(count):
        width = 2 * urmq_px("pad") + count * urmq_px("button") + (count - 1) * urmq_px("space")
        center = urmh_button_at()[0] + urmh_button_size()[0] // 2
        left = center - width // 2
        margin = urmk_px(URMH_GAP)
        return max(margin, min(config.screen_width - width - margin, left)) - left

    def urmq_pointed():
        """The tray's button the engine has in focus now ('auto', 'skip',
        'unseen'), or None. Asked of the engine at the moment, never kept:
        a button that stops being drawn under the mouse (the menu opened
        over it, the game's menu) never hears it was left."""
        try:
            focus = _urmq_sys.modules["renpy.display.focus"].get_focused()
        except Exception:
            return None
        action = getattr(focus, "action", None)
        fn = getattr(action, "callable", None)
        if fn is urmq_open:
            return action.args[0]
        return {urmq_auto: "auto", urmq_skip: "skip", urmq_unseen: "unseen"}.get(fn)

    def urmq_redraw():
        renpy.restart_interaction()

    def urmq_tip():
        """What the pointed button does, in words, or None."""
        name = urmq_pointed()
        if name == "auto":
            return ("Auto: on. Lines move on by themselves, at the game's own speed"
                    if _preferences.afm_enable and _preferences.afm_time else
                    "Auto: lines move on by themselves, at the game's own speed")
        if name == "skip":
            return "Skip. Right click: to the next choice. Middle click: back to the last choice"
        if name == "unseen":
            return ("Skip unseen text: on, in this game" if _preferences.skip_unseen
                    else "Skip unseen text: off, in this game")
        if name == "story_line":
            return "Story line"
        if name == "menu":
            return "Menu"
        if name == "settings":
            return "MRM settings"
        return None

    def urmq_tip_side():
        """The tip stands beside the tray toward the free side: (xpos,
        xanchor, xoffset) inside the tray's own box."""
        x, _y = urmh_button_at()
        w, _h = urmh_button_size()
        gap = urmq_px("tip")
        if x + w / 2.0 > config.screen_width / 2.0:
            return (0.0, 1.0, -gap)
        return (1.0, 0.0, gap)

    # ---- the URM+ menu, the part under the button and the settings page
    # (the registry, 01_urm_door)

    def urmq_flip():
        """The menu's switch: the value in effect flips, for all games (this
        game's own value, if it kept one, goes)."""
        value = not urmq_on()
        _urm_setting_set("urmcQuick", None)
        _urm_setting_set("urmcQuick", value, True)

    _urm_under_add("quick", "urmq_tray", urmq_shown, urmq_height)
    _urm_section_add("quick", "Quick access", u"", order=15)
    _urm_entry_add("quick", "Quick access", u"", urmq_flip, on=urmq_on, group=2, order=5)
    _urm_row_add("quick_tray", "quick", "Quick access buttons",
                 "Show your selected buttons under the MRM button.",
                 (("Shown", True), ("Hidden", False)), setting="urmcQuick", order=10)
    _urm_row_add("quick_auto", "quick", "Auto",
                 "Lines move on by themselves, at the speed the game's settings give.",
                 (("Shown", True), ("Hidden", False)), setting="urmcQuickAuto", order=20)
    _urm_row_add("quick_skip", "quick", "Skip",
                 "Right click: to the next choice. Middle click: back to the last choice.",
                 (("Shown", True), ("Hidden", False)), setting="urmcQuickSkip", order=30)
    _urm_row_add("quick_unseen", "quick", "Skip unseen text",
                 "Turns skipping text you have never read on or off, in this game.",
                 (("Shown", True), ("Hidden", False)), setting="urmcQuickUnseen", order=40)
    _urm_row_add("quick_story", "quick", "Story line",
                 "Opens Story line from the quick access tray.",
                 (("Shown", True), ("Hidden", False)), setting="urmcQuickStory", order=50)
    _urm_row_add("quick_menu", "quick", "Menu",
                 "Opens the full page.",
                 (("Shown", True), ("Hidden", False)), setting="urmcQuickMenu", order=45)
    _urm_row_add("quick_settings", "quick", "Settings",
                 "Opens MRM settings from the quick access tray.",
                 (("Shown", True), ("Hidden", False)), setting="urmcQuickSettings", order=60)
