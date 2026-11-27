# ---------------------------------------------------------------------------
# The MRM button: its menu and its settings window
# ---------------------------------------------------------------------------
#
# One button of ours on the game (the user's picks 1a, 2a, rows c and
# alerts a, 2026-11-22; DECISIONS.md, Displays; drawings in
# research/hub_button): it sits top right until the player drags it, and
# stays where it is dropped, in every game. A click, or Alt+U, opens a menu
# toward the free side of the screen; Settings opens a window in the middle,
# dragged by its title, a section list at the left and the rows at the
# right, each row with This game (and Clear) and All games.
#
# Everything the menu and the window show comes from what the features
# registered in the doorway (01_urm_door): this piece and its screens name
# no feature, so it sits in the words layer beside the kit it draws with.
# The closed button calls one thing a feature registered: what it says
# (_urm_status), asked each time the button is drawn and never kept, so
# that its colour, the badge on its corner, its tip and the head atop its
# menu are those of the line on screen (the user's b, 2026-11-22). Only the
# used screen and Python hold it: the screen shown keeps plain values,
# since a save keeps that screen's scope. The button always keeps room for
# the badge, so it never moves when one comes or goes. The keys are read
# from the registrations alone; the entries are worked out when the menu
# opens and again after a switch is flipped, each in try/except
# (_urm_entries). Its screens are shown on our layer at every interaction
# while the game runs, as the chip is, and only when our screens are there
# (renpy.has_screen). A game's menus and H carry every layer into a context
# of their own: there the button, its menu and its keys draw nothing
# (_urm_in_game).

init 999 python:

    class _URMHState(python_object):
        def __init__(self):
            self.open = False               # the menu is open
            self.entries = python_list()    # what it shows, worked out when it opened
            self.folded = python_set()      # entries whose rows are folded out
            self.section = None             # the settings window's section; None: closed
            self.size = None                # (text scale, the button's width, height)
            self.pointed = False            # the button is pointed at: its tip shows

    def _urmh_state():
        return _urm_kept("hub", _URMHState)

    # Where the player dropped the button, for every game (the job's own call,
    # DECISIONS.md), and the text size of every window of ours.
    _urm_setting_add("urmcHubPos", None)
    _urm_setting_add("urmcTextSize", 1.0)

    URMH_LARGE = 1.25           # the text scale of "Large"
    URMH_GAP = 16               # the button's spot from the corner, and the menu's gap to it
    URMH_CAPTION = "MRM"
    URMH_MENU = 400             # the menu's width
    URMH_WINDOW = (1280, 240)   # the settings window's width, its section list's
    URMH_LABEL = 96             # "This game", "All games": their column
    URMH_BUTTON = (128, 40)     # the button's size at most, to keep it on the screen
    URMH_WORDS = 360            # a row's words need this much beside its choices
    # the badge on the button's corner, at text size Normal: its height, how
    # far it reaches past the button's top and right edge (the room the
    # button keeps), the dark ring around it, its words' padding
    URMH_BADGE = (28, 12, 2, 6)
    URMH_TIP_GAP = 8            # the tip's gap to the button
    URMH_UNDER_GAP = 8          # the gap between the button and a part under it

    _urm_section_add("skipping", "Skipping", u"\ue01f", order=10)
    _urm_section_add("story", "Story help", u"\uf184", order=20)
    _urm_section_add("game", "Game", u"\uea28", order=30)
    _urm_section_add("look", "Look", u"\ue262", order=40)

    _urm_entry_add("settings", "Settings", u"\ue8b8", lambda: urmh_settings(), more=True,
                   group=9)
    _urm_row_add("text_size", "look", "Text size", "The size of the words in every MRM window.",
                 (("Normal", 1.0), ("Large", URMH_LARGE)), setting="urmcTextSize", order=20)

    # ---- the text size: the kit's one scale

    def _urmh_text_size(restyle=True):
        try:
            scale = float(_urm_setting("urmcTextSize") or 1.0)
        except Exception:
            scale = 1.0
        if scale != urmk_look.text:
            urmk_look.text = scale
            urmk_restyle()
            if restyle:
                renpy.style.rebuild()

    _urmh_text_size(False)
    _urm_setting_watch("urmcTextSize", _urmh_text_size)

    # ---- the menu

    def urmh_open():
        st = _urmh_state()
        st.entries = _urm_entries()
        st.folded = python_set()
        st.open = True
        renpy.restart_interaction()

    def urmh_close():
        st = _urmh_state()
        st.open = False
        st.entries = python_list()
        renpy.restart_interaction()

    def urmh_toggle():
        if _urmh_state().open:
            urmh_close()
        else:
            urmh_open()

    def urmh_pick(name):
        """An entry of the menu was picked: a switch flips and the menu
        stays; an entry with rows folds them out or in; any other closes
        the menu and opens what it names."""
        st = _urmh_state()
        entry = [e for e in st.entries if e.name == name]
        if entry and entry[0].items is not None:
            if name in st.folded:
                st.folded.discard(name)
            else:
                st.folded.add(name)
            renpy.restart_interaction()
        elif entry and entry[0].on is not None:
            _urm_open(name)
            st.entries = _urm_entries()
            renpy.restart_interaction()
        else:
            urmh_close()
            _urm_open(name)

    def urmh_step(action):
        """A step on a folded-out row (an alert's Stop): done, the menu
        stays and says what is left."""
        try:
            action()
        except _urm_control_exceptions():
            raise
        except Exception as error:
            print("MRM: a step of the menu failed (%s)" % (error,))
        st = _urmh_state()
        st.entries = _urm_entries()
        renpy.restart_interaction()

    def urmh_key(name):
        """A key an entry registered: as picked from the menu, the menu shut."""
        if _urmh_state().open:
            urmh_close()
        _urm_open(name)

    def urmh_button_size():
        """The button's width and height, on this screen, at this text size."""
        st = _urmh_state()
        if st.size is None or st.size[0] != urmk_look.text:
            h, pad, _t = URMK_BUTTON_SIZE["small"]
            try:
                words = urmk_text_width(URMH_CAPTION)
            except Exception:
                words = urmk_px(44)
            st.size = (urmk_look.text, int(urmk_px(pad) * 2 + urmk_px(URMK_ICON) + urmk_px(8) + words),
                       urmk_px(h))
        return st.size[1], st.size[2]

    def urmh_room():
        """The room the button keeps above it and at its right for the
        badge, at 1080 lines: (left, top, right, bottom), as a drag's."""
        r = URMH_BADGE[1] * urmk_look.text
        return (0, r, r, 0)

    def urmh_button_at():
        """Where the button is: its top left, in pixels."""
        w, h = urmh_button_size()
        room = urmh_room()
        at = urmk_drag_at("urmcHubPos", URMH_BUTTON, room)
        if at is None:
            return (config.screen_width - urmk_px(URMH_GAP) - w, urmk_px(URMH_GAP))
        return (at[0], at[1] + urmk_room(room)[1])

    # ---- the parts a feature hangs under the button (_urm_under)

    def urmh_under():
        """The parts under the button that show now; none while the menu is
        open, which opens where they stand."""
        if _urmh_state().open:
            return python_list()
        return _urm_under()

    def urmh_under_place():
        """Where the parts under the button stand in its drag, beside the
        room it keeps for the badge: (xpos, xoffset, ypos, yoffset,
        xanchor, yanchor), the pos as a fraction of the button with that
        room, so it holds for the button as drawn. Centred horizontally on
        the button as drawn; above the badge's room while the button is in
        the bottom half. Read from where the button was dropped, so a part
        follows it live while it is dragged and keeps that edge."""
        x, y = urmh_button_at()
        w, h = urmh_button_size()
        _l, top, room_right, _b = urmk_room(urmh_room())
        gap = urmk_px(URMH_UNDER_GAP)
        below = y + h / 2.0 <= config.screen_height / 2.0
        # centred on the button as drawn, subtracting half the badge room
        return (0.5, -(room_right // 2),
                1.0 if below else 0.0, gap if below else -gap,
                0.5, 0.0 if below else 1.0)

    def urmh_under_px():
        """How much further down the corner's usual spot under the button
        starts while parts show under it, in pixels (the choices card
        stands there, 34_corner). When the URM+ button was dragged away
        from the corner, it no longer occupies the corner spot."""
        if urmk_drag_at("urmcHubPos", URMH_BUTTON) is not None:
            return 0
        return sum(urmk_px(URMH_UNDER_GAP) + part.height for part in _urm_under())

    # ---- what a feature says on the button (_urm_status)

    def urmh_kind(status):
        """The button's ground: yellow, green or the main blue."""
        tone = status.tone if status is not None else None
        return tone if tone in ("warn", "gain") else "main"

    def urmh_tone(status):
        """The tone of the badge and of the menu's head."""
        return status.tone if status.tone in ("warn", "gain") else "ignored"

    def urmh_badge_look(status):
        """(its colour, its words' colour, height, ring, inner height,
        padding) in pixels at this text size."""
        tone = urmh_tone(status)
        fill, ink = ((URMK_COLOURS[tone + "-accent"], URMK_COLOURS["on-tone"]) if tone != "ignored"
                     else (URMK_COLOURS["badge-muted"], URMK_COLOURS["badge-muted-ink"]))
        high = urmk_px(URMH_BADGE[0] * urmk_look.text)
        ring = max(1, urmk_px(URMH_BADGE[2]))
        return fill, ink, high, ring, high - 2 * ring, urmk_px(URMH_BADGE[3] * urmk_look.text)

    def urmh_point(on):
        st = _urmh_state()
        if st.pointed != on:
            st.pointed = on
            renpy.restart_interaction()

    def urmh_hide():
        """The head's hide: what the feature gives for it now; the menu shuts."""
        status = _urm_status()
        urmh_close()
        if status is not None and status.hide is not None:
            try:
                status.hide()
            except _urm_control_exceptions():
                raise
            except Exception as error:
                print("MRM: hide failed (%s)" % (error,))

    def urmh_tip_place():
        """The tip beside the button, toward the free side, its middle at
        the button's: (x, y, xanchor, the width it has)."""
        x, y = urmh_button_at()
        w, h = urmh_button_size()
        gap = urmk_px(URMH_TIP_GAP)
        mid = int(y + h / 2)
        if x + w / 2.0 > config.screen_width / 2.0:
            return (int(x - gap), mid, 1.0, int(x - 2 * gap))
        right = int(x + w + urmk_room(urmh_room())[2] + gap)
        return (right, mid, 0.0, int(config.screen_width - right - gap))

    def urmh_menu_place():
        """The menu opens toward the free side of the button: (x, y,
        xanchor, yanchor), its corner at the button's."""
        x, y = urmh_button_at()
        w, h = urmh_button_size()
        gap = urmk_px(URMH_GAP)
        right = x + w / 2.0 > config.screen_width / 2.0
        below = y + h / 2.0 <= config.screen_height / 2.0
        return (int(x + w) if right else int(x), int(y + h + gap) if below else int(y - gap),
                1.0 if right else 0.0, 0.0 if below else 1.0)

    # ---- the settings window

    def urmh_settings(section=None):
        sections = _urm_sections()
        if not sections or not renpy.has_screen("urmh_settings"):
            return
        st = _urmh_state()
        st.section = section or sections[0].name
        _urm_section_open(st.section)
        if renpy.get_screen("urmh_settings", layer=_urmi_layer) is None:
            renpy.show_screen("urmh_settings", _layer=_urmi_layer)
        renpy.restart_interaction()

    def urmh_settings_close():
        _urmh_state().section = None
        if renpy.get_screen("urmh_settings", layer=_urmi_layer) is not None:
            renpy.hide_screen("urmh_settings", layer=_urmi_layer)
        renpy.restart_interaction()

    def urmh_rows(section):
        """[(row, its view, wide)] of a section, a row that cannot be worked
        out left out (the doorway says so). wide: its choices do not fit
        beside its words, so they go under them."""
        out = python_list()
        room = urmk_px(URMH_WINDOW[0] - 2 * 32 - URMH_WINDOW[1] - 32)
        for row in _urm_rows(section):
            view = _urm_row_view(row.name)
            if view is None:
                continue
            out.append((row, view, urmh_choices_width(view) > room - urmk_px(URMH_WORDS)))
        return out

    def urmh_column(rows):
        """The width the lines of a section's rows beside their words
        share, so that they line up."""
        found = [urmh_choices_width(view) for _r, view, wide in rows if not wide]
        return max(found) if found else None

    def urmh_choices_width(view):
        """How wide a row's lines are: the label, the choices, Clear."""
        if view.percent:
            return urmk_px(URMH_LABEL + 336)
        try:
            words = sum(urmk_text_width(w, "urmk_s_medium") for w, _v in view.options)
        except Exception:
            words = sum(len(w) for w, _v in view.options) * urmk_px(9)
        inset, _c, pad = URMK_CHOICES[1], URMK_CHOICES[2], URMK_CHOICES[3]
        n = len(view.options)
        return (urmk_px(URMH_LABEL) + words + n * 2 * urmk_px(pad) + (n + 1) * urmk_px(inset)
                + urmk_px(16) + urmk_px(80))

    def urmh_line(view, all_games):
        """The choices of one line of a row: (words, action, picked)."""
        have = view.shared if all_games else view.game
        return [(words, Function(_urm_row_pick, view.name, value, all_games), have == value)
                for words, value in view.options]

    def urmh_percent_adjustment(name, value, all_games):
        def changed(new):
            _urm_row_pick(name, new, all_games)
        return ui.adjustment(range=100, value=value, step=1, changed=changed)

    # ---- shown at every interaction while the game runs

    def _urmh_show():
        try:
            if not _urm_in_game() or not renpy.has_screen("urmh_button"):
                return
            if renpy.get_screen("urmh_button", layer=_urmi_layer) is None:
                renpy.show_screen("urmh_button", _layer=_urmi_layer)
        except Exception:
            pass

    if _urmh_show not in config.interact_callbacks:
        config.interact_callbacks.append(_urmh_show)
