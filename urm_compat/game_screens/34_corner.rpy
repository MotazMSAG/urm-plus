# The corner card: our own Choices and Path pop-ups (road step A4; the
# user's pick 1a "Corner card", 2a always open). 34_words in game_fixes
# hands over finished rows (urm_corner_view) and shows this screen on
# URM's layer at every interaction; no hook draws it. Drawn with the kit
# (16_kit): a glass card top right, one row per choice or way - a number
# where the player picks, a diamond where the game does - Take on the row
# pointed at (or tapped), the route map and close in the header. The card
# takes clicks on itself, so a click on it never moves the dialogue on.
#
# It moves by the grip at the left of its header (the user's pick 2a,
# 2026-11-22), like the URM+ button; while it stands elsewhere a faint
# outline marks its usual spot, and the next card is back there
# (urm_corner_spot). A choice has its title above the effect chips.
# The ways after it fold into "N ways after", open while that is
# pointed at (3a, urm_corner_fold).

screen urm_corner():
    # Under every other screen of ours and URM's on that layer: the route
    # map, the variable sheet, URM's windows and side panel.
    zorder -1
    default _urmcAt = None
    default _urmcOpen = None
    $ _urmcCards = urm_corner_view()
    $ _urmcText = urmk_px(_URMM_CORNER[0] - 2 * _URMM_CORNER[1] - 2 * _URMM_CORNER[2] - _URMM_CORNER[3] - _URMM_CORNER[5])
    $ _urmcEdge = urmk_px(_URMM_CORNER[4])
    if _urmcCards:
        $ _urmcKinds = tuple(_urmcC[0] for _urmcC in _urmcCards)
        $ _urmcSpot = urm_corner_spot(_urmcKinds)
        $ _urmcAbout = urm_corner_key(_urmcKinds)
        $ _urmcBeside = urm_corner_beside(_urmcKinds)
        if _urmcSpot is not None:
            # Its usual spot while it stands elsewhere: a faint dashed
            # outline of the size it had when it was dropped.
            fixed:
                xysize (_urmcSpot[2], _urmcSpot[3])
                xalign 1.0
                xoffset -_urmcEdge
                yoffset urmk_px(_URMM_CORNER[4] + URMH_BUTTON[1] + URMH_GAP) + urmh_under_px()
                fixed:
                    xysize (_urmcSpot[2], 2)
                    add Tile(urm_corner_dash(True))
                fixed:
                    xysize (_urmcSpot[2], 2)
                    yalign 1.0
                    add Tile(urm_corner_dash(True))
                fixed:
                    xysize (2, _urmcSpot[3])
                    add Tile(urm_corner_dash(False))
                fixed:
                    xysize (2, _urmcSpot[3])
                    xalign 1.0
                    add Tile(urm_corner_dash(False))
        # A new drag whenever its place or a fold changes: its place is then
        # always the one given here, worked out at its size of the moment;
        # and at every draw it is kept inside its room, header first
        # (urm_corner_keep_in): at the usual spot, under the URM+ button.
        for _urmcPlace index _urmcPlace in [urm_corner_place(_urmcAbout, _urmcSpot, _urmcOpen)]:
            drag:
                at urm_corner_keep_in(0 if _urmcSpot is not None else urmk_px(_URMM_CORNER[4] + URMH_BUTTON[1] + URMH_GAP) + urmh_under_px())
                drag_name urm_corner_drag_name(_urmcKinds)
                draggable _urmcAbout is not None
                droppable False
                focus_mask None
                drag_handle (0, 0, urmk_px(_URMM_CORNER[1] + _URMM_GRIP), urmk_px(16 + 40))
                dragged urm_corner_dropped
                if _urmcSpot is not None:
                    xalign _urmcSpot[0]
                    yalign _urmcSpot[1]
                else:
                    # below the URM+ button's own spot in the corner (17_hub)
                    xalign 1.0
                    xoffset -_urmcEdge
                    yoffset urmk_px(_URMM_CORNER[4] + URMH_BUTTON[1] + URMH_GAP) + urmh_under_px()
                vbox:
                    spacing urmk_px(16)
                    for _urmcCI index _urmcCI[0] in enumerate(_urmcCards):
                        $ _urmcI, (_urmcKind, _urmcTitle, _urmcFlavour, _urmcRows, _urmcFoot) = _urmcCI
                        $ _urmcMute = urm_corner_mute_key() if _urmcKind == 'paths' else None
                        button:
                            style 'urmk_button'
                            xalign 1.0
                            action NullAction()
                            # the top card's grip is the drag's, not this button's
                            focus_mask (None if _urmcI else urm_corner_grip_free())
                            use urmk_window('card', xa=1.0, width=_URMM_CORNER[0], pad=(_URMM_CORNER[1], 10)):
                                vbox:
                                    xfill True
                                    spacing 0
                                    fixed:
                                        ysize urmk_px(40)
                                        hbox:
                                            yalign 0.5
                                            spacing urmk_px(12)
                                            if not _urmcI and _urmcAbout is not None:
                                                add urmk_word('\ue945', style='urmk_icon', color=urmk_colour('ink-muted'), yalign=0.5)
                                            if _urmcKind == 'choices':
                                                add urmk_word('\ue0b6', style='urmk_icon', color=urmk_colour('ink'), yalign=0.5)
                                            else:
                                                add urm_corner_diamond(16, 'gain') yalign 0.5
                                            # The title opens the code behind the card (UX rule 2).
                                            button:
                                                style 'urmk_button'
                                                yalign 0.5
                                                action Function(urm_corner_open_code, _urmcKind)
                                                add urmk_word(_urmcTitle, style='urmk_m_medium', hover_color=urmk_colour('accent-ink'))
                                            if _urmcFlavour:
                                                add urmk_word('Flavour only', style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
                                        hbox:
                                            xalign 1.0
                                            yalign 0.5
                                            spacing urmk_px(4)
                                            if _urmcMute:
                                                fixed:
                                                    xysize (urmk_px(32), urmk_px(32))
                                                    button:
                                                        style 'urmk_button'
                                                        xfill True
                                                        yfill True
                                                        background urmk_back('quiet').image
                                                        hover_background urmk_back('quiet', hover=True).image
                                                        tooltip 'Mute this notification'
                                                        alt 'Mute this notification'
                                                        action Function(urm_corner_mute_ask, _urmcMute)
                                                        add urmk_word('\ue7f6', style='urmk_icon', color=urmk_colour('accent-ink'), align=(0.5, 0.5))
                                                    if GetTooltip('urm_corner'):
                                                        hbox:
                                                            xsize (urmk_text_width('Mute this notification', 'urmk_s') + 2 * urmk_px(12))
                                                            xpos 1.0
                                                            xanchor 1.0
                                                            ypos urmk_px(32)
                                                            use urmk_tip('urm_corner')
                                            if renpy.has_screen('urmnm_story'):
                                                use urmk_button('', Function(urm_corner_story), 'quiet', 'small', icon='\uf184')
                                            use urmk_button('', Function(urm_note_close, _urmcKind), 'quiet', 'small', icon='\ue5cd')
                                    null height urmk_px(8)
                                    for _urmcRI index _urmcRI[0] in enumerate(_urmcRows):
                                        $ _urmcN, (_urmcMark, _urmcLocked, _urmcWords, _urmcDim, _urmcTag, _urmcLines, _urmcLost, _urmcTake) = _urmcRI
                                        $ _urmcKey = (_urmcKind, _urmcN)
                                        $ _urmcFold = (_urmcAbout, _urmcKind, _urmcN)
                                        $ _urmcHere = _urmcAt == _urmcKey
                                        $ _urmcOpened = _urmcOpen == _urmcFold
                                        # Every row keeps room for Take beside its words, so
                                        # pointing at one never changes its size (Critic round 1).
                                        $ _urmcRoom = _urmcText
                                        if _urmcKind == 'choices':
                                            $ _urmcOwn, _urmcAfter, _urmcWays = urm_corner_fold(_urmcLines)
                                        elif not _urmcWords and _urmcLines:
                                            $ _urmcOwn, _urmcAfter, _urmcWays = _urmcLines[:1], _urmcLines[1:], 0
                                        else:
                                            $ _urmcOwn, _urmcAfter, _urmcWays = [], _urmcLines, 0
                                        $ _urmcHover = [SetScreenVariable('_urmcAt', _urmcKey), SetScreenVariable('_urmcOpen', _urmcFold if _urmcWays else None)]
                                        $ _urmcUnhover = [SetScreenVariable('_urmcAt', None), SetScreenVariable('_urmcOpen', None)]
                                        if _urmcN and not _urmcHere and _urmcAt != (_urmcKind, _urmcN - 1):
                                            add Solid(urmk_colour('divider'), xsize=urmk_px(_URMM_CORNER[0] - 2 * _URMM_CORNER[1]) - 2 * urmk_px(_URMM_CORNER[2]), ysize=1) xoffset urmk_px(_URMM_CORNER[2])
                                        else:
                                            null height (1 if _urmcN else 0)
                                        button:
                                            style 'urmk_button'
                                            xfill True
                                            background (urmk_back('plain').image if _urmcHere else None)
                                            foreground (Solid(urmk_colour('loss-ink'), xsize=urmk_px(3)) if _urmcLost else None)
                                            padding (urmk_px(_URMM_CORNER[2]), urmk_px(6 if _urmcKind != 'choices' else 4))
                                            # hovering a choice row expands its ways after; leaving collapses it
                                            hovered _urmcHover
                                            unhovered _urmcUnhover
                                            action SetScreenVariable('_urmcAt', _urmcKey)
                                            fixed:
                                                fit_first True
                                                hbox:
                                                    spacing urmk_px(8)
                                                    fixed:
                                                        xsize urmk_px(_URMM_CORNER[3] - 8)
                                                        ysize urmk_px(32)
                                                        if _urmcMark[0] == 'num':
                                                            add urmk_word(_urmcMark[1], style='urmk_m_medium', color=urmk_colour('ink-muted' if _urmcDim else 'accent-ink'), xalign=0.5, yalign=0.5)
                                                        elif _urmcMark[0] == 'diamond':
                                                            add urm_corner_diamond(16, _urmcMark[1] or 'gain') xalign 0.5 yalign 0.5
                                                        else:
                                                            add urm_corner_dot(_urmcMark[1]) xalign 0.5 yalign 0.5
                                                    vbox:
                                                        spacing urmk_px(8)
                                                        xmaximum _urmcRoom
                                                        if _urmcWords or _urmcLocked or (not _urmcOwn and (_urmcTag or _urmcWays)):
                                                            hbox:
                                                                box_wrap True
                                                                spacing urmk_px(8)
                                                                xmaximum _urmcRoom
                                                                if _urmcLocked:
                                                                    add urmk_word('\ue897', style='urmk_icon', size=urmk_px(20), color=urmk_colour('ink-muted'), yalign=0.5)
                                                                if _urmcWords:
                                                                    if _urmcKind == 'paths':
                                                                        add urm_corner_check_heading(_urmcWords, _urmcRoom, _urmcDim)
                                                                    else:
                                                                        add urmk_word(urm_map_esc(_urmcWords), style='urmk_m', color=urmk_colour('ink-muted' if _urmcDim else 'ink'), yalign=0.5)
                                                                if _urmcTag and (_urmcWords or not _urmcOwn):
                                                                    use urm_corner_row_tag(_urmcTag)
                                                                if _urmcWays and not _urmcOwn:
                                                                    use urm_corner_row_fold(_urmcWays, _urmcOpened, _urmcHover, _urmcUnhover)
                                                        if _urmcOwn:
                                                            hbox:
                                                                box_wrap True
                                                                spacing urmk_px(8)
                                                                xmaximum _urmcRoom
                                                                for _urmcLI index _urmcLI[0] in enumerate(_urmcOwn):
                                                                    $ _urmcDepth, _urmcPre, _urmcChips, _urmcNote = _urmcLI[1]
                                                                    use urm_corner_row_chips(_urmcChips, _urmcNote, _urmcBeside, _urmcHover, _urmcUnhover, _urmcRoom)
                                                                if _urmcTag and not _urmcWords:
                                                                    use urm_corner_row_tag(_urmcTag)
                                                                if _urmcWays:
                                                                    use urm_corner_row_fold(_urmcWays, _urmcOpened, _urmcHover, _urmcUnhover)
                                                        if _urmcKind != 'choices' or _urmcOpened:
                                                            for _urmcLI index _urmcLI[0] in enumerate(_urmcAfter):
                                                                $ _urmcDepth, _urmcPre, _urmcChips, _urmcNote = _urmcLI[1]
                                                                $ _urmcIndent = urmk_px(16 * _urmcDepth)
                                                                hbox:
                                                                    if _urmcIndent:
                                                                        null width _urmcIndent
                                                                    vbox:
                                                                        spacing urmk_px(8)
                                                                        xmaximum (_urmcRoom - _urmcIndent)
                                                                        if _urmcPre:
                                                                            add urmk_word(urm_map_esc(_urmcPre), style='urmk_s', color=urmk_colour('ink-muted'))
                                                                        if _urmcChips or _urmcNote:
                                                                            hbox:
                                                                                box_wrap True
                                                                                spacing urmk_px(8)
                                                                                xmaximum (_urmcRoom - _urmcIndent)
                                                                                use urm_corner_row_chips(_urmcChips, _urmcNote, _urmcBeside, _urmcHover, _urmcUnhover, _urmcRoom - _urmcIndent)
                                                # At the row's top-right edge on hover, without reserving a column.
                                                if _urmcHere and _urmcTake:
                                                    hbox:
                                                        xpos urmk_px(_URMM_CORNER[0] - 2 * _URMM_CORNER[1] - 2 * _URMM_CORNER[2])
                                                        xanchor 1.0
                                                        yalign 0.0
                                                        use urmk_button('Take', Function(urm_corner_take, _urmcKind, _urmcN), 'plain', 'small', hovered=[SetScreenVariable('_urmcAt', _urmcKey), SetScreenVariable('_urmcOpen', _urmcFold if _urmcWays else None)], unhovered=[SetScreenVariable('_urmcAt', None), SetScreenVariable('_urmcOpen', None)])
                                    for _urmcFI index _urmcFI[0] in enumerate(_urmcFoot):
                                        $ _urmcLine = _urmcFI[1]
                                        null height urmk_px(8)
                                        add urmk_word(urm_map_esc(_urmcLine), style='urmk_s', color=urmk_colour('ink-muted'), xmaximum=urmk_px(_URMM_CORNER[0] - 2 * _URMM_CORNER[1]))

# The wrapping box sees a joiner and its following pill as one child.
screen urm_corner_row_chips(chips, note, beside, on_hover, on_leave, room):
    for row index row[0] in enumerate(urm_corner_chip_groups(chips)):
        $ connector, chip = row[1]
        $ pill_room = room - (urmk_text_width(connector, 'urmk_s') + urmk_px(8) if connector else 0)
        $ words, tone, name = urm_corner_chip(chip, pill_room)
        hbox:
            spacing urmk_px(8)
            yalign 0.5
            if connector:
                add urmk_word(connector, style='urmk_s', color=urmk_colour('ink-muted'), yoffset=urmk_chip_pad())
            if name:
                button:
                    style 'urmk_button'
                    yalign 0.5
                    hovered on_hover
                    unhovered on_leave
                    action Function(urm_corner_open_value, name, beside)
                    fixed:
                        fit_first True
                        use urmk_chip(words, tone, room=pill_room)
                        add urmk_word('\u203a', style='urmk_s_medium', color='#0000', hover_color=urmk_colour('ink'), xalign=1.0, xoffset=-urmk_px(5), yalign=0.5)
            else:
                use urmk_chip(words, tone, room=pill_room)
    if note:
        add urmk_word(urm_map_esc(note), style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)

screen urm_corner_row_tag(tag):
    add urmk_word(tag[0], style='urmk_s_medium', color=(urmk_tone_ink(tag[1]) if tag[1] in URMK_TONES else urmk_colour(tag[1])), yalign=0.5)

screen urm_corner_row_fold(ways, opened, on_hover, on_leave):
    button:
        style 'urmk_button'
        yalign 0.5
        hovered on_hover
        unhovered on_leave
        action on_hover[1]
        add urmk_word(urm_corner_ways_words(ways), style='urmk_s', color=urmk_colour('ink' if opened else 'ink-muted'), hover_color=urmk_colour('ink'))

screen urm_corner_mute(notification, title, cue):
    modal True
    zorder 1050
    key 'K_ESCAPE' action Function(urm_corner_mute_close)
    key 'game_menu' action Function(urm_corner_mute_close)
    use urmk_backdrop(scrim=urmk_colour('scrim'))
    use urmk_window('window', xa=0.5, ya=0.5, width=460, pad=(24, 22)):
        vbox:
            xfill True
            spacing urmk_px(10)
            add urmk_word('Mute this notification?', style='urmk_l')
            add urmk_word('You can unmute it in Alerts & Mutes.', style='urmk_s', color=urmk_colour('ink-muted'))
            hbox:
                xalign 1.0
                spacing urmk_px(8)
                use urmk_button('No', Function(urm_corner_mute_close), 'plain', 'small')
                use urmk_button('Yes', Function(urm_corner_mute_close, notification, title, cue), 'main', 'small')
