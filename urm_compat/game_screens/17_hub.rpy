# The MRM button, its menu and its settings window (17_hub in
# game_fixes). Drawn with the kit (16_kit); every entry and row comes from
# what the features registered in the doorway (01_urm_door).

# The button, and the menu while it is open. Shown on our layer at every
# interaction while the game runs (_urmh_show). It holds nothing of its
# own: a save keeps the scope of this screen, not of the one it uses.
screen urmh_button():
    if _urm_in_game():
        use urmh_button_in_game()

screen urmh_button_in_game():
    $ _urmhS = _urmh_state()
    # what a feature says now: asked at every draw, never kept (17_hub)
    $ _urmhG = _urm_status()
    for _urmhK, _urmhN in _urm_keys():
        key _urmhK action Function(urmh_key, _urmhN)
    key 'alt_K_u' action Function(urmh_toggle)
    if _urmhS.open:
        key 'game_menu' action Function(urmh_close)
        # a click or scroll anywhere else shuts the menu without moving dialogue
        use urmk_backdrop(Function(urmh_close))
        $ _urmhX, _urmhY, _urmhXa, _urmhYa = urmh_menu_place()
        frame:
            style 'urmk_frame'
            pos (_urmhX, _urmhY)
            anchor (_urmhXa, _urmhYa)
            use urmk_window(xa=0.0, width=URMH_MENU, pad=(0, 0)):
                button:
                    style 'urmk_button'
                    padding (urmk_px(8), urmk_px(8))
                    action NullAction()
                    vbox:
                        if _urmhG is not None and _urmhG.head:
                            use urmh_head(_urmhG)
                            use urmk_divider()
                        $ _urmhP = None
                        for _urmhE index _urmhE.name in _urmhS.entries:
                            if _urmhP is not None and _urmhE.group != _urmhP:
                                use urmk_divider()
                            $ _urmhP = _urmhE.group
                            $ _urmhF = (_urmhE.name in _urmhS.folded) if _urmhE.items is not None else None
                            use urmk_menu_row(_urmhE.words, _urmhE.icon, Function(urmh_pick, _urmhE.name), on=_urmhE.on, count=_urmhE.count, key_words=_urmhE.key_words, more=_urmhE.more, unfold=_urmhF)
                            if _urmhF:
                                for _urmhW, _urmhT, _urmhA in _urmhE.items:
                                    use urmk_menu_item(_urmhW, _urmhT, Function(urmh_step, _urmhA))
    $ _urmhW, _urmhH = urmh_button_size()
    $ _urmhR = urmh_room()
    $ _urmhT = urmk_room(_urmhR)[1]
    # the button, and room above it and at its right for the badge, kept
    # whether a badge shows or not; only the button takes the pointer
    use urmk_drag('urmh_button', keep='urmcHubPos', every_game=True, x=-URMH_GAP, y=URMH_GAP, size=URMH_BUTTON, room=_urmhR, handle=(0, _urmhT, _urmhW, _urmhH), clicked=Function(urmh_toggle), hovered=Function(urmh_point, True), unhovered=Function(urmh_point, False)):
        fixed:
            fit_first True
            frame:
                style 'urmk_frame'
                top_padding _urmhT
                right_padding urmk_room(_urmhR)[2]
                use urmk_button(URMH_CAPTION, None, urmh_kind(_urmhG), 'small', '\ue945')
            if _urmhG is not None:
                use urmh_badge(_urmhG)
            # the parts a feature hangs under the button: in its drag, so
            # they move with it (_urm_under); never in the badge's room
            $ _urmhU = urmh_under()
            if _urmhU:
                $ _urmhUX, _urmhUXo, _urmhUY, _urmhUYo, _urmhUXa, _urmhUYa = urmh_under_place()
                vbox:
                    pos (_urmhUX, _urmhUY)
                    xoffset _urmhUXo
                    yoffset _urmhUYo
                    anchor (_urmhUXa, _urmhUYa)
                    spacing urmk_px(URMH_UNDER_GAP)
                    for _urmhP in _urmhU:
                        use expression _urmhP.screen
    if _urmhG is not None and _urmhG.tip and _urmhS.pointed and not _urmhS.open:
        use urmh_tip(_urmhG.tip)

# The badge on the button's corner: the count, or the picture when there
# is none, on a pill in the tone's colour inside a dark ring that parts it
# from the button.
screen urmh_badge(status):
    $ _urmhF, _urmhI, _urmhH, _urmhR, _urmhN, _urmhP = urmh_badge_look(status)
    frame:
        style 'urmk_frame'
        xalign 1.0
        yalign 0.0
        background urmk_pill(urmk_colour('badge-rim'), _urmhH // 2)
        padding (_urmhR, _urmhR)
        frame:
            style 'urmk_frame'
            background urmk_pill(_urmhF, _urmhN // 2)
            ysize _urmhN
            xminimum _urmhN
            xpadding _urmhP
            if status.count is not None:
                add urmk_word(status.count, style='urmk_s_medium', color=_urmhI, align=(0.5, 0.5))
            else:
                add urmk_word(status.icon, style='urmk_icon', color=_urmhI, size=urmk_px(16 * urmk_look.text), align=(0.5, 0.5))

# What pointing at the button says, beside it toward the free side.
screen urmh_tip(words):
    $ _urmhX, _urmhY, _urmhA, _urmhM = urmh_tip_place()
    frame:
        style 'urmk_frame'
        pos (_urmhX, _urmhY)
        anchor (_urmhA, 0.5)
        xmaximum _urmhM
        use urmk_window('bubble', xa=0.0, pad=(12, 4)):
            add urmk_word(words, style='urmk_s')

# The head atop the menu, tinted in the tone: the picture, what the
# feature says, the tip under it, and its hide when it gives one.
screen urmh_head(status):
    $ _urmhC = urmh_tone(status)
    frame:
        style 'urmk_frame'
        background urmk_pill(urmk_chip_fill(_urmhC), urmk_px(URMK_ROW[2]))
        xfill True
        padding (urmk_px(URMK_ROW[1]), urmk_px(12))
        hbox:
            spacing urmk_px(16)
            add urmk_word(status.icon, style='urmk_icon', color=urmk_chip_ink(_urmhC))
            vbox:
                spacing urmk_px(8)
                vbox:
                    add urmk_word(status.head, style='urmk_m_medium', color=urmk_colour('ink'))
                    if status.tip:
                        add urmk_word(status.tip, style='urmk_s', color=urmk_colour('ink-muted'))
                if status.hide is not None:
                    use urmk_button(status.hide_words, Function(urmh_hide), 'plain', 'small')

# The settings window: in the middle, dragged by its title; the sections at
# the left, the rows of the one picked at the right. Each row: This game
# (with Clear while this game keeps its own value) and All games; a value
# the engine keeps for this game alone has This game only.
screen urmh_settings():
    modal True
    zorder 20
    $ _urmhS = _urmh_state()
    key 'game_menu' action Function(urmh_settings_close)
    use urmk_backdrop(Function(urmh_settings_close), urmk_colour('scrim'))
    $ _urmhPad = (32, 24)
    $ _urmhRight = URMH_WINDOW[0] - 2 * _urmhPad[0] - URMH_WINDOW[1] - 32
    $ _urmhCustom = _urm_section_screen(_urmhS.section)
    $ _urmhBadge = _urm_section_badge(_urmhS.section)
    use urmk_drag('urmh_settings', xa=0.5, ya=0.0, y=120, size=(URMH_WINDOW[0], 400), handle=(0, 0, 1.0, urmk_px(_urmhPad[1] + 48))):
        use urmk_window(xa=0.0, width=URMH_WINDOW[0], pad=(0, 0)):
            vbox:
                # Title bar sits outside any child shield button (no frame wrapper, so only one 1280px window in tree).
                null height urmk_px(_urmhPad[1])
                hbox:
                    null width urmk_px(_urmhPad[0])
                    fixed:
                        xsize urmk_px(URMH_WINDOW[0] - 2 * _urmhPad[0])
                        ysize urmk_px(48)
                        add urmk_word('MRM settings', style='urmk_l', yalign=0.5)
                        hbox:
                            xalign 1.0
                            yalign 0.5
                            spacing urmk_px(12)
                            if _urmhBadge:
                                frame:
                                    style 'urmk_frame'
                                    yalign 0.5
                                    use urmk_chip(_urmhBadge[0], _urmhBadge[1])
                            use urmk_button('', Function(urmh_settings_close), 'plain', 'big', '\ue5cd')
                    null width urmk_px(_urmhPad[0])
                if _urmhCustom:
                    # In Ren'Py 7.3 a button wrapping an input drops key events.
                    fixed:
                        ysize urmk_px(500)
                        button:
                            style 'urmk_button'
                            xfill True
                            yfill True
                            action NullAction()
                        frame:
                            style 'urmk_frame'
                            padding (urmk_px(_urmhPad[0]), urmk_px(32))
                            use urmh_settings_body(_urmhS.section, _urmhRight, _urmhCustom)
                else:
                    button:
                        style 'urmk_button'
                        xfill True
                        left_padding urmk_px(_urmhPad[0])
                        right_padding urmk_px(_urmhPad[0])
                        top_padding urmk_px(32)
                        bottom_padding urmk_px(_urmhPad[1])
                        action NullAction()
                        use urmh_settings_body(_urmhS.section, _urmhRight)

screen urmh_settings_body(section, width, custom=None):
    hbox:
        spacing urmk_px(32)
        vbox:
            xsize urmk_px(URMH_WINDOW[1])
            for _urmhC index _urmhC.name in _urm_sections():
                use urmk_tab(_urmhC.words, _urmhC.icon, Function(urmh_settings, _urmhC.name), _urmhC.name == section)
        if custom:
            use expression custom pass (width=width)
        else:
            vbox:
                xsize urmk_px(width)
                $ _urmhRows = urmh_rows(section)
                $ _urmhCol = urmh_column(_urmhRows)
                $ _urmhI = 0
                for _urmhRow index _urmhRow[0].name in _urmhRows:
                    $ _urmhR, _urmhV, _urmhWide = _urmhRow
                    if _urmhI:
                        use urmk_divider(0, 0)
                    $ _urmhI += 1
                    frame:
                        style 'urmk_frame'
                        xfill True
                        ypadding urmk_px(16)
                        if _urmhWide:
                            vbox:
                                spacing urmk_px(16)
                                use urmh_row_words(_urmhR)
                                use urmh_row_lines(_urmhV)
                        else:
                            side 'c r':
                                xfill True
                                spacing urmk_px(32)
                                use urmh_row_words(_urmhR)
                                use urmh_row_lines(_urmhV, _urmhCol)

screen urmh_row_words(row):
    vbox:
        add urmk_word(row.words, style='urmk_m_medium', color=urmk_colour('ink'))
        add urmk_word(row.about, style='urmk_s', color=urmk_colour('ink-muted'))

# width: the column the lines of a section's rows share, so that their
# labels and choices line up from row to row.
screen urmh_row_lines(view, width=None):
    vbox:
        spacing urmk_px(8)
        if width:
            xsize width
        hbox:
            spacing urmk_px(16)
            add urmk_word('This game', style='urmk_s', color=urmk_colour('ink-muted'), xsize=urmk_px(URMH_LABEL), yalign=0.5)
            if view.percent:
                use urmh_percent(view, view.value, False)
            else:
                use urmk_choices(urmh_line(view, False))
            if view.own and not view.game_only:
                use urmk_button('Clear', Function(_urm_row_clear, view.name), 'quiet', 'small')
        if not view.game_only:
            hbox:
                spacing urmk_px(16)
                add urmk_word('All games', style='urmk_s', color=urmk_colour('ink-muted'), xsize=urmk_px(URMH_LABEL), yalign=0.5)
                if view.percent:
                    use urmh_percent(view, view.shared, True)
                else:
                    use urmk_choices(urmh_line(view, True), held=view.own)

screen urmh_percent(view, value, all_games):
    $ _urmhHeld = all_games and view.own
    bar:
        id (view.name, all_games)
        style 'default'
        adjustment urmh_percent_adjustment(view.name, value, all_games)
        xysize (urmk_px(180), urmk_px(16))
        yalign 0.5
        left_bar Solid(urmk_colour('ink-muted' if _urmhHeld else 'accent'))
        right_bar Solid(urmk_colour('divider'))
        thumb Solid(urmk_colour('ink'), xysize=(urmk_px(6), urmk_px(16)))
        thumb_offset urmk_px(3)
    add urmk_word('%d%%' % value, style='urmk_s', xsize=urmk_px(44), yalign=0.5)
