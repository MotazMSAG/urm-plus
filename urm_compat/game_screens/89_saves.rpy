# Our own save page (game_fixes/89_saves): a band across the bottom, the
# user's pick c2. Sizes at 1080 lines (urmk_px); the band is as wide as
# the screen less 16 at each side, 540 high.

screen urmsv_page():
    modal True
    zorder 1050
    # A modal screen still lets keys reach the engine's own keymap below
    # every screen: while the page is open the story does not move. Esc and
    # a right click (the game menu's keys) step back or close the page.
    key 'game_menu' action Function(urmsv_escape)
    for _urmsvK in URMSV_HELD_KEYS:
        key _urmsvK action NullAction()
    $ _urmsvS = urmsv_state_now()
    if not _urmsvS.shot:
        # one frame with nothing of ours on it: the picture the saves get
        timer 0.05 action Function(urmsv_shoot)
    else:
        $ _urmsvW = config.screen_width - urmk_px(32)
        $ _urmsvH = urmk_px(540)
        $ _urmsvP = urmk_px(276)
        $ _urmsvPX = _urmsvW - urmk_px(32) - _urmsvP
        $ _urmsvA = _urmsvPX - urmk_px(32)
        $ _urmsvTop = config.screen_height - urmk_px(16) - _urmsvH
        # a click or scroll above the band closes the latest save popup or the page
        viewport:
            mousewheel True
            xfill True
            yfill True
            button:
                style 'urmk_button'
                xfill True
                yfill True
                action Function(urmsv_escape)
        use urmk_window('window', xa=0.5, ya=1.0, y=-16, width=_urmsvW * 1080.0 / config.screen_height, pad=(0, 0)):
            fixed:
                xysize (_urmsvW, _urmsvH)
                button:
                    style 'urmk_button'
                    xfill True
                    yfill True
                    action NullAction()
                if _urmsvS.mode == 'save':
                    add urmsv_outline('accent-ink')
                use urmsv_header(_urmsvS)
                if _urmsvS.view == 'timeline':
                    use urmsv_timeline(_urmsvS, _urmsvA)
                else:
                    use urmsv_pages(_urmsvS, _urmsvA)
                # the line between the saves and the resume save
                frame:
                    style 'urmk_frame'
                    background urmk_pill(urmk_colour('divider'), 0)
                    pos (_urmsvPX - urmk_px(20), urmk_px(140))
                    xysize (max(1, urmk_px(2)), urmk_px(376))
                use urmsv_resume_card(_urmsvPX, _urmsvP)
        if _urmsvS.focus and not (_urmsvS.ask or _urmsvS.naming):
            use urmsv_bubble(_urmsvS, _urmsvTop)
        if _urmsvS.leaving:
            timer 0.6 action Function(urmsv_bubble_gone)
        if _urmsvS.gear:
            use urmsv_gear(_urmsvTop)
        if _urmsvS.ask:
            use urmsv_ask(_urmsvS, _urmsvTop)
        if _urmsvS.naming:
            use urmsv_naming(_urmsvS, _urmsvTop)

# The top row: Save | Load, what a click does, where the player was last,
# Timeline | Pages, the settings and close.
screen urmsv_header(st):
    $ _urmsvN = urmsv_newest()
    $ _urmsvHint, _urmsvLast = urmsv_header_words()
    hbox:
        pos (urmk_px(32), urmk_px(24))
        ysize urmk_px(48)
        spacing urmk_px(16)
        use urmk_choices([(u'Save', Function(urmsv_set_mode, 'save'), st.mode == 'save'),
                          (u'Load', Function(urmsv_set_mode, 'load'), st.mode == 'load')])
        if _urmsvHint:
            text _urmsvHint style 'urmk_s' color urmk_colour(urmsv_hint_tone()) yalign 0.5 substitute False
        if _urmsvN is not None and _urmsvLast:
            frame:
                style 'urmk_frame'
                background urmk_pill(urmk_colour('divider'), 0)
                xysize (max(1, urmk_px(2)), urmk_px(24))
                yalign 0.5
            text u'You were last at' style 'urmk_s' color urmk_colour('ink-muted') yalign 0.5
            text _urmsvLast style 'urmk_m_medium' yalign 0.5 substitute False
            text (u'\u00b7 ' + urmsv_when(_urmsvN)) style 'urmk_s' color urmk_colour('ink-muted') yalign 0.5 substitute False
    hbox:
        xalign 1.0
        xoffset -urmk_px(24)
        ypos urmk_px(24)
        ysize urmk_px(48)
        spacing urmk_px(8)
        frame:
            style 'urmk_frame'
            yalign 0.5
            use urmk_choices([(u'Timeline', Function(urmsv_set_view, 'timeline'), st.view == 'timeline'),
                              (u'Pages', Function(urmsv_set_view, 'pages'), st.view == 'pages')])
        use urmk_button(u'', ToggleField(st, 'gear'), 'plain', 'big', u'\ue8b8')
        use urmk_button(u'', Function(urmsv_close), 'plain', 'big', u'\ue5cd')

# A pill of a strip: a filter, a page; on: picked; count after the words.
screen urmsv_pill(words, action, on=False, count=None, edit=None):
    button:
        style 'urmk_button'
        background urmk_pill(urmk_colour('accent' if on else 'plain-bg'), urmk_px(20))
        hover_background urmk_pill(urmk_colour('accent' if on else 'surface-2'), urmk_px(20))
        ysize urmk_px(40)
        xpadding urmk_px(16)
        action action
        hbox:
            yalign 0.5
            spacing urmk_px(8)
            text words style 'urmk_s_medium' color urmk_colour('on-accent' if on else 'plain-ink') yalign 0.5 substitute False
            if count is not None:
                text ('%d' % count) style 'urmk_s_medium' color urmk_colour('on-accent' if on else 'ink-muted') yalign 0.5
            if edit:
                text u'\ue3c9' style 'urmk_icon' size urmk_px(20) color urmk_colour('on-accent' if on else 'plain-ink') yalign 0.5

# A box to type in (the save's name, a page number, a page's name).
screen urmsv_field(value, width, height=56):
    frame:
        style 'urmk_frame'
        background urmk_pill(urmk_colour('surface'), urmk_px(10))
        foreground urmsv_outline('accent-ink', 10)
        xysize (width, urmk_px(height))
        xpadding urmk_px(16)
        input:
            value value
            style 'urmk_m'
            caret urmsv_caret()
            yalign 0.5
            pixel_width width - urmk_px(32)

# Go to page: a box for a number.
screen urmsv_goto(st):
    hbox:
        spacing urmk_px(8)
        yalign 0.5
        text u'Go to page' style 'urmk_s' color urmk_colour('ink-muted') yalign 0.5
        if st.editing == 'goto':
            use urmsv_field(urmsv_goto_box, urmk_px(72), 40)
        else:
            button:
                style 'urmk_button'
                background urmk_pill(urmk_colour('surface'), urmk_px(10))
                hover_background urmk_pill(urmk_colour('surface-2'), urmk_px(10))
                xysize (urmk_px(72), urmk_px(40))
                action Function(urmsv_edit, 'goto')

# ---- the timeline

screen urmsv_timeline(st, area):
    $ _urmsvI, _urmsvEarlier, _urmsvLater = urmsv_timeline(area)
    # the strip: All, Quick, Auto, then the pages
    hbox:
        pos (urmk_px(32), urmk_px(88))
        spacing urmk_px(8)
        $ _urmsvPills, _urmsvMore = urmsv_pills_shown(area)
        if st.pill_from:
            use urmk_button(u'', Function(urmsv_pills_step, -1), 'quiet', 'small', u'\ue5cb')
        for _urmsvWd, _urmsvC, _urmsvK in _urmsvPills:
            use urmsv_pill(_urmsvWd, Function(urmsv_set_pill, _urmsvK), st.pill == _urmsvK, _urmsvC)
            if _urmsvK == 'auto':
                frame:
                    style 'urmk_frame'
                    background urmk_pill(urmk_colour('divider'), 0)
                    xysize (max(1, urmk_px(2)), urmk_px(24))
                    yalign 0.5
        if _urmsvMore:
            use urmk_button(u'', Function(urmsv_pills_step, 1), 'quiet', 'small', u'\ue5cc')
        use urmsv_goto(st)
    hbox:
        xpos area
        xanchor 1.0
        ypos urmk_px(96)
        spacing urmk_px(8)
        add urmsv_ring_dot(16) yalign 0.5
        text u'auto' style 'urmk_s' color urmk_colour('ink-muted') yalign 0.5
        null width urmk_px(4)
        add urmsv_diamond(12) yalign 0.5
        text u'quick' style 'urmk_s' color urmk_colour('ink-muted') yalign 0.5
        null width urmk_px(4)
        frame:
            style 'urmk_frame'
            background urmk_back('plain').image
            xysize (urmk_px(22), urmk_px(16))
            yalign 0.5
        text u'on a page' style 'urmk_s' color urmk_colour('ink-muted') yalign 0.5
    # the line
    frame:
        style 'urmk_frame'
        background urmk_pill(urmk_colour('line'), 0)
        pos (0, urmk_px(420))
        xysize (area, max(1, urmk_px(2)))
    for _urmsvKd, _urmsvX, _urmsvR in _urmsvI:
        if _urmsvKd == 'day':
            frame:
                style 'urmk_frame'
                background urmk_pill(urmk_colour('divider'), 0)
                pos (_urmsvX, urmk_px(140))
                xysize (max(1, urmk_px(2)), urmk_px(300))
            text _urmsvR.upper() style 'urmk_s_medium' color urmk_colour('ink-muted') pos (_urmsvX + urmk_px(12), urmk_px(140)) substitute False
        elif _urmsvKd == 'card':
            use urmsv_card(st, _urmsvR, _urmsvX)
        else:
            use urmsv_dot(st, _urmsvR, _urmsvX)
    if not _urmsvI:
        text urmsv_none_words() style 'urmk_m' color urmk_colour('ink-muted') pos (urmk_px(32), urmk_px(260)) substitute False
    if _urmsvEarlier:
        add urmsv_fade(urmk_px(220), urmk_px(400)) pos (0, urmk_px(132))
        frame:
            style 'urmk_frame'
            pos (urmk_px(24), urmk_px(256))
            use urmk_button(u'Earlier', Function(urmsv_earlier), 'plain', 'small', u'\ue5cb')
    if _urmsvLater:
        frame:
            style 'urmk_frame'
            pos (area - urmk_px(24), urmk_px(450))
            xanchor 1.0
            use urmk_button(u'Later', Function(urmsv_later), 'plain', 'small', u'\ue5cc')
    if st.mode == 'save' and st.pill == 'all':
        # where Save now saves, at the right end of the line
        $ _urmsvSX = area - urmk_px(224 + 8)
        frame:
            style 'urmk_frame'
            background urmk_pill('#7ab0ff1a', urmk_px(14))
            foreground urmsv_outline('accent-ink', 14, True)
            pos (_urmsvSX, urmk_px(196))
            xysize (urmk_px(224), urmk_px(176))
            vbox:
                align (0.5, 0.5)
                spacing urmk_px(12)
                frame:
                    style 'urmk_frame'
                    xalign 0.5
                    use urmk_button(u'Save now', Function(urmsv_save_now), 'main', 'big', u'\ue145')
                text urmsv_next_words() style 'urmk_s' color urmk_colour('ink-muted') xalign 0.5 substitute False
        add urmsv_dashes(urmk_px(48)) pos (_urmsvSX + urmk_px(112) - 1, urmk_px(372))

# A save on a page, as a card on the line.
screen urmsv_card(st, r, x):
    $ _urmsvOn = st.focus == r.slot
    $ _urmsvNew = urmsv_newest_card()
    button:
        style 'urmk_button'
        background urmk_back('plain', hover=_urmsvOn).image
        hover_background urmk_back('plain', hover=True).image
        foreground (urmsv_outline('accent-ink', 14) if _urmsvOn and st.mode == 'save' else None)
        pos (x, urmk_px(196))
        xysize (urmk_px(184), urmk_px(176))
        padding (urmk_px(12), urmk_px(12))
        action Function(urmsv_click, r.slot)
        hovered Function(urmsv_hover, r.slot)
        unhovered Function(urmsv_unhover, r.slot)
        vbox:
            spacing urmk_px(8)
            fixed:
                xysize (urmk_px(160), urmk_px(90))
                add urmsv_thumb(r.slot, urmk_px(160), urmk_px(90))
                if _urmsvOn:
                    add urmsv_veil(urmk_px(160), urmk_px(90))
                    frame:
                        style 'urmk_frame'
                        align (0.5, 0.5)
                        use urmsv_over(st.mode)
            text urmsv_fit(urmsv_title(r), 'urmk_s_medium', urmk_px(160)) style 'urmk_s_medium' substitute False
            hbox:
                spacing urmk_px(8)
                text (urmsv_clock(r.when) + u' \u00b7 ' + urmsv_place(r)) style 'urmk_s' color urmk_colour('ink-muted') substitute False yalign 0.5
    frame:
        style 'urmk_frame'
        background urmk_pill(urmk_colour('line'), 0)
        pos (x + urmk_px(92) - 1, urmk_px(372))
        xysize (max(1, urmk_px(2)), urmk_px(48))
    add urmsv_node(12) pos (x + urmk_px(92) - urmk_px(6), urmk_px(415))
    if _urmsvNew is r:
        frame:
            style 'urmk_frame'
            pos (x + urmk_px(184) - urmk_px(8), urmk_px(196) - urmk_px(12))
            xanchor 1.0
            use urmk_chip(u'Newest', 'set')

# What a click on a card does, on its picture.
screen urmsv_over(mode):
    if mode == 'save':
        frame:
            style 'urmk_frame'
            background urmk_pill(urmk_colour('accent'), urmk_px(16))
            ysize urmk_px(32)
            xpadding urmk_px(16)
            text u'Save over' style 'urmk_s_medium' color urmk_colour('on-accent') yalign 0.5
    else:
        frame:
            style 'urmk_frame'
            background urmk_pill(urmk_colour('surface-2'), urmk_px(16))
            ysize urmk_px(32)
            xpadding urmk_px(16)
            hbox:
                yalign 0.5
                spacing urmk_px(4)
                text u'\ue037' style 'urmk_icon' size urmk_px(20) yalign 0.5
                text u'Load' style 'urmk_s_medium' yalign 0.5

# An auto or quick save: a mark on the line and its time.
screen urmsv_dot(st, r, x):
    $ _urmsvOn = st.focus == r.slot
    button:
        style 'urmk_button'
        pos (x, urmk_px(400))
        xysize (urmk_px(56), urmk_px(72))
        action Function(urmsv_click, r.slot)
        hovered Function(urmsv_hover, r.slot)
        unhovered Function(urmsv_unhover, r.slot)
        fixed:
            if r.kind == 'auto':
                add urmsv_ring_dot(24 if _urmsvOn else 20) align (0.5, 0.0) yoffset urmk_px(11 if not _urmsvOn else 9)
            else:
                add urmsv_diamond(18 if _urmsvOn else 14) align (0.5, 0.0) yoffset urmk_px(13 if not _urmsvOn else 11)
            text urmsv_clock(r.when) style 'urmk_s' color urmk_colour('ink' if _urmsvOn else 'ink-muted') xalign 0.5 ypos urmk_px(40)

# ---- pages: the engine's page strip and the page's 3 x 3 slots

screen urmsv_pages(st, area):
    $ _urmsvPage = urmsv_page()
    $ _urmsvStrip = urmsv_strip_layout(area)
    hbox:
        pos (urmk_px(32), urmk_px(88))
        spacing urmk_px(8)
        use urmk_button(u'', Function(urmsv_go, 1), 'quiet', 'small', u'\ue5dc')
        use urmk_button(u'', Function(urmsv_go, urmsv_prev_page()), 'quiet', 'small', u'\ue5cb')
    # Pages and slots are drags of one group: a save dragged from a slot
    # drops on a slot or a page. A drag takes the click itself, so what
    # it holds only draws.
    draggroup:
        xysize (area, urmk_px(516))
        for _urmsvKey, _urmsvPX, _urmsvPW, _urmsvWd, _urmsvOn in _urmsvStrip:
            drag:
                drag_name urmsv_drag_name('page', _urmsvKey)
                draggable False
                droppable True
                pos (_urmsvPX, urmk_px(88))
                clicked Function(urmsv_page_pill, _urmsvKey)
                use urmsv_pill_face(_urmsvWd, _urmsvOn, None, _urmsvOn and str(_urmsvKey).isdigit())
        for _urmsvN, _urmsvR in urmsv_slots():
            $ _urmsvX, _urmsvY, _urmsvTW = urmsv_tile_box(_urmsvN, area)
            $ _urmsvSlot = '%s-%d' % (_urmsvPage, _urmsvN)
            drag:
                drag_name urmsv_drag_name('slot', _urmsvSlot)
                draggable (_urmsvR is not None and not st.carry)
                droppable True
                drag_raise True
                dropped urmsv_dropped
                pos (_urmsvX, _urmsvY)
                clicked Function(urmsv_click, _urmsvSlot)
                hovered Function(urmsv_hover, _urmsvSlot if _urmsvR is not None else ('empty', _urmsvSlot))
                unhovered Function(urmsv_unhover)
                use urmsv_tile(st, _urmsvN, _urmsvR, _urmsvSlot, _urmsvTW)
    if st.editing == 'page':
        # the shown page's name, typed into the engine's own page name
        for _urmsvKey, _urmsvPX, _urmsvPW, _urmsvWd, _urmsvOn in _urmsvStrip:
            if _urmsvOn:
                frame:
                    style 'urmk_frame'
                    pos (_urmsvPX, urmk_px(88))
                    use urmsv_field(urmsv_page_box(), max(_urmsvPW, urmk_px(240)), 40)
    $ _urmsvEnd = (_urmsvStrip[-1][1] + _urmsvStrip[-1][2] + urmk_px(8)) if _urmsvStrip else urmk_px(400)
    hbox:
        pos (_urmsvEnd, urmk_px(88))
        spacing urmk_px(8)
        use urmk_button(u'', Function(urmsv_go, urmsv_next_page()), 'quiet', 'small', u'\ue5cc')
        use urmsv_goto(st)

# A pill as it looks, for a drag that takes the click itself.
screen urmsv_pill_face(words, on=False, count=None, edit=False):
    frame:
        style 'urmk_frame'
        background urmk_pill(urmk_colour('accent' if on else 'plain-bg'), urmk_px(20))
        ysize urmk_px(40)
        xpadding urmk_px(16)
        hbox:
            yalign 0.5
            spacing urmk_px(8)
            text words style 'urmk_s_medium' color urmk_colour('on-accent' if on else 'plain-ink') yalign 0.5 substitute False
            if edit:
                text u'\ue3c9' style 'urmk_icon' size urmk_px(20) color urmk_colour('on-accent' if on else 'plain-ink') yalign 0.5

# One slot of the page.
screen urmsv_tile(st, n, r, slot, width):
    $ _urmsvOn = st.focus == slot or st.focus == ('empty', slot)
    $ _urmsvTH = urmsv_tile_h()
    if r is not None:
        frame:
            style 'urmk_frame'
            background urmk_back('plain', hover=_urmsvOn).image
            foreground (urmsv_outline('accent-ink', 14) if _urmsvOn and st.mode == 'save' else None)
            xysize (width, _urmsvTH)
            padding (urmk_px(11), urmk_px(11))
            hbox:
                spacing urmk_px(16)
                add urmsv_thumb(slot, (_urmsvTH - urmk_px(22)) * 16 // 9, _urmsvTH - urmk_px(22))
                vbox:
                    hbox:
                        spacing urmk_px(8)
                        text ('%d' % n) style 'urmk_s_medium' color urmk_colour('ink-muted') yalign 0.5
                        text urmsv_fit(urmsv_title(r), 'urmk_m_medium', width - (_urmsvTH - urmk_px(22)) * 16 // 9 - urmk_px(80)) style 'urmk_m_medium' substitute False yalign 0.5
                    text urmsv_when(r) style 'urmk_s' color urmk_colour('ink-muted') substitute False
                    if urmsv_newest_card() is r:
                        null height urmk_px(4)
                        use urmk_chip(u'Newest', 'set')
    else:
        $ _urmsvLive = _urmsvOn and st.mode == 'save' or (_urmsvOn and st.carry)
        frame:
            style 'urmk_frame'
            background (urmk_pill('#7ab0ff1f', urmk_px(14)) if _urmsvLive else None)
            foreground urmsv_outline('accent-ink' if _urmsvLive else 'line', 14, True)
            xysize (width, _urmsvTH)
            padding (urmk_px(11), urmk_px(11))
            hbox:
                yalign 0.5
                spacing urmk_px(16)
                text ('%d' % n) style 'urmk_s_medium' color urmk_colour('ink' if _urmsvLive else 'ink-muted') yalign 0.5
                if _urmsvLive and not st.carry:
                    frame:
                        style 'urmk_frame'
                        background urmk_back('main').image
                        ysize urmk_px(40)
                        xpadding urmk_px(16)
                        hbox:
                            yalign 0.5
                            spacing urmk_px(8)
                            text u'\ue145' style 'urmk_icon' color urmk_colour('on-accent') yalign 0.5
                            text u'Save here' style 'urmk_s_medium' color urmk_colour('on-accent') yalign 0.5
                elif st.carry:
                    text (u'Put it here' if _urmsvOn else u'Empty') style 'urmk_s' color urmk_colour('ink' if _urmsvOn else 'ink-muted') yalign 0.5
                else:
                    text (u'Empty \u00b7 click to save here' if st.mode == 'save' else u'Empty') style 'urmk_s' color urmk_colour('ink-muted') yalign 0.5

# ---- the resume save, at the right

screen urmsv_resume_card(x, width):
    $ _urmsvT = urmsv_resume()
    frame:
        style 'urmk_frame'
        background urmk_back('plain').image
        pos (x, urmk_px(140))
        xysize (width, urmk_px(376))
        padding (urmk_px(16), urmk_px(16))
        vbox:
            spacing urmk_px(12)
            hbox:
                spacing urmk_px(8)
                xfill True
                text u'\uf10d' style 'urmk_icon' yalign 0.5
                text u'Resume next start' style 'urmk_s_medium' yalign 0.5
            if _urmsvT:
                add urmsv_thumb(urmsv_resume_slot(), width - urmk_px(32), (width - urmk_px(32)) * 9 // 16)
                use urmk_chip(u'Set \u00b7 ' + urmsv_day_clock(_urmsvT), 'gain')
                text u'The next start of the game opens here, past the title screen, once.' style 'urmk_s' color urmk_colour('ink-muted')
            else:
                frame:
                    style 'urmk_frame'
                    background urmk_pill(urmk_colour('plain-bg'), urmk_px(8))
                    xysize (width - urmk_px(32), (width - urmk_px(32)) * 9 // 16)
                use urmk_chip(u'Not set', 'plain')
                text u'Set it, and the next start of the game opens here, past the title screen.' style 'urmk_s' color urmk_colour('ink-muted')
            hbox:
                spacing urmk_px(8)
                if not urmsv_no_game():
                    use urmk_button(u'Set to now', Function(urmsv_resume_set), 'plain', 'small', u'\ue5d5')
                if _urmsvT:
                    use urmk_button(u'', Function(urmsv_resume_clear), 'plain', 'small', u'\ue872')

# ---- bubbles above the band

# The save pointed at: its picture big, when it was made, where it sits,
# and move, copy, delete.
screen urmsv_bubble(st, top):
    $ _urmsvR = urmsv_focus_row()
    if _urmsvR is not None:
        $ _urmsvX = urmsv_bubble_x(urmk_px(480))
        # pointed at, the bubble stays (its height as the kit lays it out)
        mousearea:
            area (_urmsvX, top - urmk_px(12 + 424), urmk_px(480), urmk_px(424))
            hovered Function(urmsv_bubble_kept)
            unhovered Function(urmsv_unhover)
        use urmk_window('bubble', xa=0.0, ya=1.0, x=urmsv_at1080(_urmsvX), y=urmsv_above(top), width=480, pad=(16, 16)):
                vbox:
                    spacing urmk_px(12)
                    add urmsv_thumb(_urmsvR.slot, urmk_px(448), urmk_px(252))
                    vbox:
                        text urmsv_title(_urmsvR) style 'urmk_m_medium' substitute False
                        hbox:
                            xfill True
                            text urmsv_long_when(_urmsvR) style 'urmk_s' color urmk_colour('ink-muted') substitute False yalign 0.5
                            frame:
                                style 'urmk_frame'
                                xalign 1.0
                                use urmk_chip(urmsv_where(_urmsvR), 'plain')
                    hbox:
                        xfill True
                        spacing urmk_px(8)
                        text (u'Click it to load it (asks first)' if st.mode == 'load' else u'Click it to save over it (asks first)') style 'urmk_s' color urmk_colour('ink-muted') yalign 0.5
                        hbox:
                            xalign 1.0
                            spacing urmk_px(8)
                            use urmk_button(u'', Function(urmsv_pick_up, _urmsvR.slot, False), 'plain', 'small', u'\ue675')
                            use urmk_button(u'', Function(urmsv_pick_up, _urmsvR.slot, True), 'plain', 'small', u'\ue14d')
                            use urmk_button(u'', Function(urmsv_delete, _urmsvR.slot), 'plain', 'small', u'\ue872')

# The four settings, as switches.
screen urmsv_gear(top):
    button:
        style 'urmk_button'
        xfill True
        yfill True
        action SetField(urmsv_state_now(), 'gear', False)
    use urmk_window('bubble', xa=1.0, ya=1.0, x=-40, y=urmsv_above(top), width=440, pad=(16, 16)):
            vbox:
                spacing urmk_px(4)
                text u'Save page settings' style 'urmk_m_medium'
                null height urmk_px(8)
                for _urmsvN, _urmsvWd, _urmsvAb in URMSV_SETTING_WORDS:
                    button:
                        style 'urmk_button'
                        hover_background urmk_pill(urmk_colour('hover'), urmk_px(10))
                        xfill True
                        ysize urmk_px(56)
                        xpadding urmk_px(8)
                        action Function(urmsv_flip, _urmsvN)
                        fixed:
                            xfill True
                            yfill True
                            vbox:
                                yalign 0.5
                                text _urmsvWd style 'urmk_s_medium'
                                text _urmsvAb style 'urmk_s' color urmk_colour('ink-muted')
                            frame:
                                style 'urmk_frame'
                                align (1.0, 0.5)
                                use urmk_switch(bool(_urm_setting(_urmsvN)))

# Load, save over, delete, replace: asked first.
screen urmsv_ask(st, top):
    button:
        style 'urmk_button'
        xfill True
        yfill True
        action Function(urmsv_no)
    use urmk_window('bubble', xa=0.5, ya=1.0, y=urmsv_above(top), width=520, pad=(24, 24)):
            vbox:
                spacing urmk_px(8)
                text st.ask[0] style 'urmk_m_medium' substitute False
                text st.ask[1] style 'urmk_s' color urmk_colour('ink-muted') substitute False
                null height urmk_px(8)
                hbox:
                    xalign 1.0
                    spacing urmk_px(8)
                    use urmk_button(u'Cancel', Function(urmsv_no), 'plain', 'small')
                    use urmk_button(st.ask[2], Function(urmsv_yes), 'main', 'small')

# A name for the save.
screen urmsv_naming(st, top):
    button:
        style 'urmk_button'
        xfill True
        yfill True
        action SetField(st, 'naming', None)
    use urmk_window('bubble', xa=0.5, ya=1.0, y=urmsv_above(top), width=520, pad=(24, 24)):
            vbox:
                spacing urmk_px(12)
                text u'Name this save' style 'urmk_m_medium'
                use urmsv_field(urmsv_name_box, urmk_px(472))
                hbox:
                    xfill True
                    text u'Enter saves \u00b7 Esc stops' style 'urmk_s' color urmk_colour('ink-muted') yalign 0.5
                    hbox:
                        xalign 1.0
                        spacing urmk_px(8)
                        use urmk_button(u'Cancel', SetField(st, 'naming', None), 'plain', 'small')
                        use urmk_button(u'Save', Function(urmsv_name_done), 'main', 'small', u'\ue161')
