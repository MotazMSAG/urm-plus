# The variable sheet, our own (drawing c, picked 2026-11-22: the ladder as
# a slider), on the kit (16_kit). It takes a name and a close action;
# what it draws it asks of the panel (74_var_window), as plain values. Ways
# in: URM's editor, for every way URM opens a value (ui_tweaks,
# urmi_var_frame), the Flags list's Details (83_flags), and anything that
# asks the doorway's value viewer (a card's stat chip: urmi_sheet_at, beside
# the card). The older off argument is still accepted for saved screens.

#
# It draws only while the story runs (_urm_in_game): a game's menus carry
# our layer with them, keys and all. Not modal (layout C: the game and its
# choice stay in view), but what lands on it is its own: a click on an
# empty spot and the wheel over it (a ground under the panel), the keys of
# the open box (Enter in the box itself). A click beside it plays on.
screen urmi_var_sheet(name, close, flag=False):
    if flag and _urm_in_game():
        use urmk_backdrop(If(urmi_box_open(name), Function(urmi_box_close, name), close))
    if _urm_in_game():
        use urmi_sheet_shown(name, close, flag)

# The sheet the doorway's value viewer opens (urmi_sheet_beside), the same
# sheet at `off`: its scope holds the value's name and a number alone, so a
# save may keep it.
screen urmi_sheet_at(name, off=None, beside=None):
    modal True
    zorder 1060
    if _urm_in_game():
        key 'mouseup_3' action If(urmi_box_open(name), Function(urmi_box_close, name), Function(renpy.hide_screen, 'urmi_sheet_at', layer=_urmi_layer))
        use urmk_backdrop(If(urmi_box_open(name), Function(urmi_box_close, name), Function(renpy.hide_screen, 'urmi_sheet_at', layer=_urmi_layer)))
        use urmi_sheet_shown(name, Function(renpy.hide_screen, 'urmi_sheet_at', layer=_urmi_layer), False, off, beside)

screen urmi_sheet_shown(name, close, flag, off=None, beside=None):
    $ _urmsKind = urmi_kind(name, flag)
    $ _urmsPage = urmi_page(name)
    $ _urmsTip = GetTooltip()
    $ _urmsTitle = urmi_sheet_title(name)
    $ _urmsRoom = urmi_sheet_room()
    $ _urmsHead, _urmsCompact, _urmsTitleRoom, _urmsBar = urmi_sheet_header(_urmsTitle, _urmsPage is not None, _urmsRoom)
    $ _urmsBelow = _urmsBar + urmk_px(32)

    key 'K_ESCAPE' action If(urmi_box_open(name), Function(urmi_box_close, name), close)
    if urmi_box_open(name):
        for _urmsKey index _urmsKey in URMI_BOX_KEYS:
            key _urmsKey action NullAction()
    on 'show' action Function(urmi_sheet_reset, name)

    fixed:
        fit_first True
        at urmi_sheet_anchor(beside, off)
        ymaximum (config.screen_height - urmk_px(URMI_SHEET_EDGE) * 2)
        button:
            style 'urmk_button'
            key_events True
            action NullAction()
            use urmk_window('window', xa=0.0, ya=0.0, x=0, y=0, pad=(URMI_SHEET_EDGE, URMI_SHEET_EDGE)):
                side 't c':
                    spacing urmk_px(16)
                    xmaximum _urmsRoom
                    use urmi_title_bar(name, close, flag, _urmsPage is not None, _urmsTitle, _urmsCompact, _urmsTitleRoom)
                    viewport:
                        mousewheel True
                        xfill False
                        yfill False
                        xminimum _urmsHead
                        if _urmsPage is None:
                            use urmi_sheet_body(name, flag, _urmsKind, _urmsRoom)
                        else:
                            use urmi_rung_page(name, _urmsPage)

        # What a title bar icon does, under the bar; More's list.
        if urmi_ui(('more', name)):
            vbox:
                at urmi_sheet_popup(_urmsBelow, beside, off)
                use urmi_more(name, close, flag)
        elif _urmsTip:
            vbox:
                at urmi_sheet_popup(_urmsBelow, beside, off)
                use urmk_window('bubble', xa=0.0, ya=0.0, pad=(12, 4)):
                    add urmk_word(_urmsTip, style='urmk_s')

# One icon of the title bar: on (lit), live (it does something) or greyed;
# lit in its own colour when it has one (Freeze: ice blue).
screen urmi_icon(icon, tip, action, on=False, live=True, lit='accent-ink'):
    button:
        style 'urmk_button'
        xysize (urmk_px(40), urmk_px(40))
        hover_background urmk_pill(urmk_colour('hover'), urmk_px(20))
        tooltip u'%s' % tip
        action action
        add urmk_word(icon, style='urmk_icon', color=urmk_colour(lit if on else ('ink' if live else 'disabled')), align=(0.5, 0.5))

# The title bar: the name said plainly; Remember, Freeze, Alert, Ignore,
# More, close (the user's order). On a rung's page, a back arrow first.
screen urmi_title_bar(name, close, flag, page, title, compact, room):
    if compact:
        vbox:
            spacing urmk_px(8)
            use urmi_title(name, page, title, room)
            use urmi_title_buttons(name, close, flag, compact)
    else:
        side 'c r':
            xfill True
            spacing urmk_px(8)
            ysize urmk_px(48)
            use urmi_title(name, page, title, room)
            use urmi_title_buttons(name, close, flag, compact)

screen urmi_title(name, page, title, room):
    hbox:
        yalign 0.5
        spacing urmk_px(8)
        if page:
            use urmi_icon(u'\ue5c4', u'Back', Function(urmi_open_page, name, None))
        add urmk_word(urmi_fit_line(title, room, 'urmk_l'), style='urmk_l', font=URMK_FONTS['medium'], yalign=0.5)

screen urmi_title_buttons(name, close, flag, compact):
    $ _urmsRem, _urmsIgn = urmi_lists(name, flag)
    hbox:
        yalign 0.5
        spacing urmk_px(4)
        box_wrap compact
        if _urmsRem is None:
            use urmi_icon(u'\ue83a', u'Remember: for variables, not flags', NullAction(), live=False)
        else:
            use urmi_icon((u'\ue838' if _urmsRem else u'\ue83a'), (u'Forget' if _urmsRem else u'Remember'), Function(urmi_remember, name), _urmsRem)
        $ _urmsFzOn, _urmsFzLive, _urmsFzTip = urmi_freeze_view(name, flag)
        use urmi_icon(u'\ueb3b', _urmsFzTip, (Function(urmi_freeze, name) if _urmsFzLive else NullAction()), _urmsFzOn, _urmsFzLive, 'frozen-on-glass')
        use urmi_icon((u'\ue7f7' if urmal_is(name) else u'\ue7f4'), (u'Stop alerting' if urmal_is(name) else u'Alert when the game checks this'), Function(urmal_toggle, name), urmal_is(name))
        if _urmsIgn is None:
            use urmi_icon(u'\ue14b', u'Ignore: for variables, not flags', NullAction(), live=False)
        else:
            use urmi_icon(u'\ue14b', (u'Stop ignoring' if _urmsIgn else u'Ignore on the corner card'), Function(urmi_ignore, name), _urmsIgn)
        use urmi_icon(u'\ue5d3', u'More', Function(urmi_ui_toggle, ('more', name)), urmi_ui(('more', name)))
        use urmi_icon(u'\ue5cd', u'Close', close)

# More: Copy the name; on a rung's page Code and Replay when available;
# Delete, asked again first.
screen urmi_more(name, close, flag):
    $ _urmsItems = urmi_more_items(urmi_rung(urm_panel(name), urmi_ui(('rung', name))), urmi_deletable(name, flag))
    $ _urmsMenuWidth = min(320, int(config.screen_width * 1080.0 / config.screen_height) - URMI_SHEET_EDGE * 2)
    use urmk_window('card', xa=0.0, ya=0.0, width=_urmsMenuWidth, pad=(8, 8)):
        vbox:
            if urmi_ui(('delete', name)):
                add urmk_word("Delete this variable from the game? The game may stop working where it uses it.", style='urmk_s', color=urmk_colour('ink'), xsize=urmk_px(_urmsMenuWidth - 32), xalign=0.5)
                null height urmk_px(16)
                hbox:
                    xalign 1.0
                    spacing urmk_px(8)
                    use urmk_button(u'Keep', Function(urmi_ui_set, ('delete', name), False), 'quiet', 'small')
                    use urmk_button(u'Delete', [Function(urmi_delete, name), close], 'plain', 'small')
            else:
                use urmk_menu_row(u'Copy name', u'\ue14d', [Function(urm_copy, name), Function(urmi_ui_set, ('more', name), False)])
                for _urmsItem index _urmsItem[0] in _urmsItems:
                    $ _urmsK, _urmsW = _urmsItem
                    if _urmsK == 'code':
                        use urmk_menu_row(u'Code', u'\ue86f', Function(urmi_show_code, name, _urmsW))
                    elif _urmsK == 'replay':
                        use urmk_menu_row(u'Replay this scene', u'\ue042', Function(urmi_replay_offer, name, _urmsW))
                    else:
                        use urmk_menu_row(u'Delete variable', u'\ue872', Function(urmi_ui_set, ('delete', name), True))

screen urmi_replay_confirm():
    modal True
    zorder 1061
    $ _urmsReplayPrompt = urmi_replay_prompt()
    if _urmsReplayPrompt:
        key 'K_ESCAPE' action Function(urmi_replay_cancel)
        key 'mouseup_3' action Function(urmi_replay_cancel)
        use urmk_backdrop(Function(urmi_replay_cancel), urmk_colour('scrim'))
        use urmk_window('card', xa=0.5, ya=0.5, width=456, pad=(0, 0)):
            button:
                style 'urmk_button'
                xpadding urmk_px(24)
                ypadding urmk_px(20)
                action NullAction()
                vbox:
                    spacing urmk_px(10)
                    xsize urmk_px(408)
                    add urmk_word(u'Replay this scene?', style='urmk_l', color=urmk_colour('ink'))
                    add urmk_word(_urmsReplayPrompt, style='urmk_m', color=urmk_colour('ink-muted'), xmaximum=urmk_px(408))
                    add urmk_word(u'End the replay to return here.', style='urmk_s', color=urmk_colour('ink-muted'))
                    null height urmk_px(4)
                    hbox:
                        xalign 1.0
                        spacing urmk_px(8)
                        use urmk_button(u'Cancel', Function(urmi_replay_cancel), 'plain', 'small')
                        use urmk_button(u'Replay', Function(urmi_replay_start), 'main', 'small')

screen urmi_replay_controls():
    zorder 1061
    if urmi_replay_active():
        use urmk_window('bubble', xa=1.0, ya=0.0, x=-16, y=16, pad=(0, 0)):
            button:
                style 'urmk_button'
                xpadding urmk_px(14)
                ypadding urmk_px(6)
                action NullAction()
                hbox:
                    spacing urmk_px(10)
                    add urmk_word(u'Replaying', style='urmk_m_medium', color=urmk_colour('accent-ink'), yalign=0.5)
                    use urmk_button(u'End replay', Function(renpy.end_replay), 'quiet', 'small')

# The sheet's first page: the value, the ladder (a number) or the sides (a
# yes/no or text value), Back and Set while looking, the choice on screen.
screen urmi_sheet_body(name, flag, kind, room):
    $ _urmsLook = urmi_looking(name)
    $ _urmsLadder = urmi_ladder(name)
    $ _urmsSides = urmi_sides(name)
    $ _urmsVerdict = urmi_verdict(name)
    $ _urmsMessage = urm_panel(name).message
    vbox:
        spacing urmk_px(24)

        if urmi_box_open(name):
            use urmi_box(name, kind, room)
        else:
            hbox:
                box_wrap True
                spacing urmk_px(16)
                box_wrap_spacing urmk_px(16)
                hbox:
                    spacing urmk_px(16)
                    use urmi_value_box(urmi_now_words(name, flag), Function(urmi_box_start, name, flag) if kind in ('int', 'float', 'text') else None, False)
                    if _urmsLook:
                        add urmk_word(u'\ue5c8', style='urmk_icon', color=urmk_colour('ink-muted'), yalign=0.5)
                        use urmi_value_box(_urmsLook[0], None, True)
                if _urmsLook:
                    for _urmsW, _urmsT, _urmsR in _urmsLook[1]:
                        if _urmsR is None:
                            use urmk_chip(_urmsW, _urmsT)
                        else:
                            button:
                                style 'urmk_button'
                                yalign 0.5
                                action Function(urmi_open_page, name, _urmsR)
                                use urmk_chip(_urmsW, _urmsT)
                elif _urmsVerdict:
                    use urmk_chip(_urmsVerdict[0], _urmsVerdict[1])

        if urmi_snapped(name):
            use urmk_chip(urmi_snapped(name), 'loss')

        if _urmsMessage:
            add urmk_word(_urmsMessage, style='urmk_s', color=urmk_colour('ink-muted'))
            if urm_panel(name).state == 'building':
                timer 0.5 repeat True action Function(renpy.restart_interaction)

        if _urmsLadder:
            use urmi_ladder(name, _urmsLadder, room)
        elif _urmsSides:
            hbox:
                box_wrap True
                spacing urmk_px(8)
                box_wrap_spacing urmk_px(8)
                for _urmsSide index _urmsSide[0] in _urmsSides:
                    $ _urmsW, _urmsN, _urmsLit, _urmsI, _urmsV = _urmsSide
                    button:
                        style 'urmk_button'
                        background urmk_pill(urmk_colour('accent' if _urmsLit else 'plain-bg'), urmk_px(14))
                        hover_background urmk_pill(urmk_colour('accent' if _urmsLit else 'hover'), urmk_px(14))
                        padding (urmk_px(16), urmk_px(8))
                        action (Function(urmi_preview_set, name, _urmsV) if urmi_settable(name, flag, _urmsV) else Function(urmi_open_page, name, _urmsI))
                        vbox:
                            add urmk_word(_urmsW, style='urmk_m_medium', color=urmk_colour('on-accent' if _urmsLit else 'ink'), xalign=0.5)
                            add urmk_word(_urmsN, style='urmk_s', color=urmk_colour('on-accent' if _urmsLit else 'ink-muted'), xalign=0.5)

        if _urmsLook:
            hbox:
                xalign 1.0
                spacing urmk_px(8)
                use urmk_button(u'Back to ' + urmi_now_words(name, flag), Function(urmi_preview_clear, name), 'plain', 'small')
                if flag:
                    use urmk_button(u'Set to ' + _urmsLook[0], [Function(urmfl_set, name, bool(_urmsLook[2])), Function(urmi_preview_clear, name)], 'main', 'small')
                elif urmi_settable(name, flag, _urmsLook[2]):
                    use urmk_button(u'Set to ' + _urmsLook[0], Function(urmi_commit, name), 'main', 'small')

        if urmi_choices(name):
            vbox:
                spacing urmk_px(8)
                add urmk_word(u'THE CHOICE ON SCREEN', style='urmk_s', color=urmk_colour('ink-muted'), kerning=1.5)
                for _urmsChItem index _urmsChItem[0] in urmi_choices(name):
                    $ _urmsN, _urmsW, _urmsC = _urmsChItem
                    hbox:
                        box_wrap True
                        spacing urmk_px(8)
                        add urmk_word((_urmsN + u' ' + _urmsW), style='urmk_m', color=urmk_colour('ink-muted'), yalign=0.5)
                        for _urmsCw, _urmsCt in _urmsC:
                            use urmk_chip(_urmsCw, _urmsCt)

# A value in a big box: now (a click types a new one) or the one looked at.
screen urmi_value_box(words, action, looking):
    button:
        style 'urmk_button'
        background urmk_pill(urmk_colour('accent' if looking else 'surface-2'), urmk_px(14))
        hover_background urmk_pill(urmk_colour('accent' if looking else 'line'), urmk_px(14))
        padding (urmk_px(2), urmk_px(2))
        yalign 0.5
        action action
        frame:
            style 'urmk_frame'
            background urmk_pill(urmk_colour('surface' if looking else 'surface-2'), urmk_px(12))
            xminimum urmk_px(84)
            ysize urmk_px(72)
            xpadding urmk_px(16)
            add urmk_word(urmi_box_words(words), style=('urmk_xl' if len(words) <= 6 else 'urmk_l'), color=urmk_colour('accent-ink' if looking else 'ink'), align=(0.5, 0.5))

# The type-in box (a click on the value): filled with it, - and + for a
# number, the values the game checks for as chips, Enter sets, Esc leaves.
screen urmi_box(name, kind, room):
    $ _urmsChecks = urmi_box_checks(name)
    vbox:
        spacing urmk_px(16)
        hbox:
            spacing urmk_px(8)
            frame:
                style 'urmk_frame'
                background urmk_pill(urmk_colour('accent'), urmk_px(14))
                xsize max(1, room - (urmk_px(112) if kind in ('int', 'float') else 0))
                ysize urmk_px(64)
                padding (urmk_px(2), urmk_px(2))
                frame:
                    style 'urmk_frame'
                    background urmk_pill(urmk_colour('surface'), urmk_px(12))
                    xfill True
                    yfill True
                    xpadding urmk_px(18)
                    input value urmi_box(name) style 'urmk_l' font URMK_FONTS['regular'] color urmk_colour('ink') yalign 0.5 pixel_width max(1, room - urmk_px(160)) allow (('0123456789-.' if kind in ('int', 'float') else None))
            if kind in ('int', 'float'):
                hbox:
                    yalign 0.5
                    spacing urmk_px(8)
                    use urmk_button('', Function(urmi_box_step, name, -1), 'plain', 'big', u'\ue15b')
                    use urmk_button('', Function(urmi_box_step, name, 1), 'plain', 'big', u'\ue145')
        if urmi_ui(('box_error', name)):
            add urmk_word(urmi_ui(('box_error', name)), style='urmk_s', color=urmk_tone_ink('loss'))
        if _urmsChecks:
            hbox:
                box_wrap True
                spacing urmk_px(8)
                box_wrap_spacing urmk_px(8)
                add urmk_word("The game checks for:", style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
                for _urmsW, _urmsV in _urmsChecks:
                    button:
                        style 'urmk_button'
                        action Function(urmi_box_fill, name, _urmsV)
                        use urmk_chip(_urmsW, 'plain')
        hbox:
            spacing urmk_px(16)
            use urmk_button(u'Set', Function(urmi_box_enter, name), 'main', 'small')
            use urmk_button(u'Cancel', Function(urmi_box_close, name), 'plain', 'small')

# The ladder (a number): the track, the stretch from the value now to the
# one looked at, a row at each value that means something (a rung: its
# number, a diamond for places still ahead in the colour of its reach, its
# words; you; the two ends), and the knob. The bar under it takes the drag
# and the clicks; a row's click looks at its value, its arrow opens the
# rung's story line.
screen urmi_ladder(name, ladder, room):
    $ _urmsH, _urmsRows, _urmsTrack, _urmsKnob = ladder
    $ _urmsK = urmk_px(URMI_LADDER[0])
    $ _urmsWidth = min(room, urmi_ladder_width(_urmsRows))
    fixed:
        xsize _urmsWidth
        ysize _urmsH
        frame:
            style 'urmk_frame'
            background urmk_pill(urmk_colour('line'), urmk_px(2))
            xpos (_urmsK // 2 - urmk_px(2))
            ypos _urmsTrack[0]
            xysize (urmk_px(4), _urmsTrack[1] - _urmsTrack[0])
        if _urmsKnob[1] != _urmsKnob[2]:
            frame:
                style 'urmk_frame'
                background urmk_pill(urmk_colour('accent-ink'), urmk_px(2))
                xpos (_urmsK // 2 - urmk_px(2))
                ypos min(_urmsKnob[1], _urmsKnob[2])
                xysize (urmk_px(4), abs(_urmsKnob[1] - _urmsKnob[2]))
        for _urmsRowItem index _urmsRowItem[0] in enumerate(_urmsRows):
            $ _urmsRI, (_urmsY, _urmsN, _urmsT, _urmsW, _urmsMuted, _urmsR, _urmsV, _urmsAhead) = _urmsRowItem
            $ _urmsNumW = max(urmk_px(32), urmk_text_width(_urmsN, 'urmk_m_medium'))
            $ _urmsWordsW = _urmsWidth - _urmsK - urmk_px(8) * 3 - _urmsNumW - urmk_px(12) - (urmk_px(32) if _urmsAhead else 0) - (urmk_text_width(u'\ue5cc', 'urmk_icon') + urmk_px(8) if _urmsR is not None else 0)
            button:
                style 'urmk_button'
                hover_background urmk_pill(urmk_colour('hover'), urmk_px(10))
                xpos (_urmsK + urmk_px(8))
                ypos _urmsY
                yanchor 0.5
                xsize (_urmsWidth - _urmsK - urmk_px(8))
                ysize urmk_px(40)
                xpadding urmk_px(8)
                action Function(urmi_preview_set, name, _urmsV)
                fixed:
                    xfill True
                    yfill True
                    hbox:
                        yalign 0.5
                        spacing urmk_px(12)
                        add urmk_word(_urmsN, style='urmk_m_medium', color=(urmk_tone_ink(_urmsT) if _urmsT in ('gain', 'warn', 'loss') else urmk_colour('ink')), min_width=urmk_px(32), text_align=1.0, yalign=0.5)
                        if _urmsAhead:
                            add urmi_diamond(urmk_px(14), _urmsT) yalign 0.5
                        if _urmsW:
                            add urmk_word(urmi_fit_line(urmi_row_words(_urmsW), _urmsWordsW, 'urmk_m'), style='urmk_m', color=urmk_colour('ink-muted' if _urmsMuted else 'ink'), yalign=0.5)
                    if _urmsR is not None:
                        button:
                            style 'urmk_button'
                            xalign 1.0
                            yalign 0.5
                            tooltip u'Its story line'
                            action Function(urmi_open_page, name, _urmsR)
                            add urmk_word(u'\ue5cc', style='urmk_icon', color=urmk_colour('ink-muted'), hover_color=urmk_colour('ink'))
        vbar:
            value urmi_knob(name)
            xpos 0
            ypos 0
            xysize (_urmsK, _urmsH)
            thumb Null(_urmsK, _urmsK)
            thumb_shadow None
            top_bar Null()
            bottom_bar Null()
            thumb_offset 0
            top_gutter 0
            bottom_gutter 0
            bar_invert False
            unscrollable None
        frame:
            style 'urmk_frame'
            background urmk_pill(urmi_halo(), _urmsK // 2)
            xpos 0
            ypos (_urmsKnob[0] - _urmsK // 2)
            xysize (_urmsK, _urmsK)
            frame:
                style 'urmk_frame'
                background urmk_pill(urmk_colour('accent'), (_urmsK - urmk_px(12)) // 2)
                align (0.5, 0.5)
                xysize (_urmsK - urmk_px(12), _urmsK - urmk_px(12))

# A rung's story line: who gives the value, you, the check (layout C).
screen urmi_rung_page(name, page):
    $ _urmsWords, _urmsTitle, _urmsLines, _urmsReach, _urmsSteps, _urmsNeeds = page
    vbox:
        spacing urmk_px(16)
        add urmk_word(_urmsWords, style='urmk_l', font=URMK_FONTS['medium'])
        if _urmsTitle:
            add urmk_word(_urmsTitle, style='urmk_m')
        if _urmsLines:
            add urmk_word(_urmsLines, style='urmk_s', color=urmk_colour('ink-muted'))
        if _urmsReach:
            use urmk_chip(_urmsReach[0], _urmsReach[1])
        vbox:
            spacing urmk_px(8)
            for _urmsStItem index _urmsStItem[0] in enumerate(_urmsSteps):
                $ _urmsSI, (_urmsSt, _urmsW, _urmsC) = _urmsStItem
                hbox:
                    box_wrap True
                    spacing urmk_px(8)
                    if _urmsSt == 'here':
                        add urmk_word(u'\ue55f', style='urmk_icon', color=urmk_colour('accent-ink'), yalign=0.5)
                        add urmk_word(u'you', style='urmk_m_medium', yalign=0.5)
                        use urmk_chip(_urmsW, 'plain')
                    elif _urmsSt in ('played', 'picked'):
                        add urmk_word(u'\ue061', style='urmk_icon', color=urmk_colour('ink-muted'), yalign=0.5)
                        add urmk_word(urmi_row_words(_urmsW), style='urmk_m', color=urmk_colour('ink-muted'), yalign=0.5)
                    else:
                        add urmk_word(u'\ue836', style='urmk_icon', color=urmk_colour('accent-ink'), yalign=0.5)
                        add urmk_word(urmi_row_words(_urmsW), style='urmk_m', yalign=0.5)
                    for _urmsCw, _urmsCt in _urmsC:
                        use urmk_chip(_urmsCw, _urmsCt)
            if _urmsNeeds:
                hbox:
                    spacing urmk_px(8)
                    add urmi_diamond(urmk_px(14), 'warn') yalign 0.5
                    add urmk_word(_urmsNeeds, style='urmk_m_medium', yalign=0.5)
