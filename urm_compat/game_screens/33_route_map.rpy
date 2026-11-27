# The route map: the full-screen map of a choice (see 33_map_screen
# in game_fixes, which lays it out). Opened by urm_map_open, on our layer.
# Our screen look (the user's pick 1a, 2026-11-22): today's tree left to
# right on the map's glass surface, boxes as rounded panels, "you are here"
# and where the ways join again in the accent, the game's own picks raised
# a step, lines in the kit's line colour, the overview in the corner, and a
# footer of what the choices decide later as goals with tone chips. Its
# sizes are the layout's (32_map_layout), so what is drawn is what was
# measured.

screen urm_route_map():
    modal True
    zorder 300

    default _urmmTip = None
    default _urmmXadj = ui.adjustment()
    default _urmmYadj = ui.adjustment()

    python:
        _urmmV = urm_map_view()
        _urmmS = urmk_px_cut
        _urmmHead = _urmmS(70)
        _urmmFoot = (_urmmS(48) + _urmmS(30) * len(_urmmV.later[:6])) if _urmmV.later else 0
        _urmmViewH = config.screen_height - _urmmHead - _urmmFoot
        _urmmInk = urm_map_ink('ink')
        _urmmMuted = urm_map_ink('muted')
        _urmmMedium = URMK_FONTS['medium']
        _urmmTotalH = max(_urmmV.height, _urmmViewH)
        _urmmHereY = _urmmV.here[1] + (_urmmTotalH - _urmmV.height) // 2
        _urmmYinit = (max(0.0, min(1.0, float(_urmmHereY - _urmmViewH // 2) / (_urmmTotalH - _urmmViewH)))
                      if _urmmTotalH > _urmmViewH else 0.0)
        _urmmBig = _urmmV.width > config.screen_width or _urmmV.height > _urmmViewH
        _urmmBar = _urmmS(6)

    key 'K_ESCAPE' action Function(urm_map_close)
    key 'mouseup_3' action Function(urm_map_close)
    for _urmmSk in URMK_SCROLL_KEYS:
        key _urmmSk action NullAction()

    button:
        style 'urmk_button'
        xfill True
        yfill True
        background urmk_pill(urmk_colour('glass'), 0)
        action NullAction()

    vbox:
        spacing 0
        xfill True
        frame:
            style 'urmk_frame'
            xfill True
            ysize _urmmHead
            padding (_urmmS(24), _urmmS(8))
            fixed:
                hbox:
                    yalign .5
                    spacing _urmmS(14)
                    text '' style 'urmk_icon' size _urmmS(32) color urm_map_ink('accent-ink') yalign .5
                    text 'Route map' style 'urmk_text' font _urmmMedium size _urmmS(28) color _urmmInk yalign .5
                hbox:
                    xalign 1.0
                    yalign .5
                    spacing _urmmS(8)
                    for _urmmKey, _urmmWords in (('gain', 'you gain'), ('loss', 'you lose'), ('set', 'sets something')):
                        frame:
                            style 'urmk_frame'
                            yalign .5
                            background urm_chip_bg(_urmmKey)
                            padding (_urmmS(8), _urmmS(2))
                            text _urmmWords style 'urmk_text' size _urmmS(16) color urm_chip_ink(_urmmKey)
                    null width _urmmS(8)
                    add urm_map_mark(_urmmS(14), 'pick') yalign .5
                    text 'the game picks the way' style 'urmk_text' size _urmmS(16) color _urmmMuted yalign .5
                    null width _urmmS(8)
                    add urm_map_mark(_urmmS(9), 'lines') yalign .5
                    text 'only lines change (point at one)' style 'urmk_text' size _urmmS(16) color _urmmMuted yalign .5
                    null width _urmmS(8)
                    frame:
                        style 'urmk_frame'
                        yalign .5
                        background urm_chip_bg('plain', faded=True)
                        padding (_urmmS(8), _urmmS(2))
                        text 'faded' style 'urmk_text' size _urmmS(16) color urm_chip_ink('plain', faded=True)
                    text 'not as things stand' style 'urmk_text' size _urmmS(16) color _urmmMuted yalign .5
                    null width _urmmS(16)
                    use urmk_button('', Function(urm_map_close), 'plain', 'small', icon='')

        if _urmmV.empty:
            frame:
                style 'urmk_frame'
                xfill True
                ysize _urmmViewH
                text urm_map_esc(_urmmV.empty) style 'urmk_text' align (.5, .4) size _urmmS(24) color _urmmInk substitute False
        else:
            fixed:
                xfill True
                ysize _urmmViewH
                viewport:
                    xfill True
                    ysize _urmmViewH
                    mousewheel 'horizontal'
                    draggable True
                    scrollbars 'both'
                    # Both bars are the map's own: a game's sideways bar
                    # can have no height, and one with none took the whole
                    # map (DECISIONS.md 2026-11-21, 1a).
                    scrollbar_ysize _urmmBar
                    scrollbar_base_bar urmk_pill(urm_map_ink('track'), _urmmS(3))
                    scrollbar_thumb urmk_pill(urm_map_ink('thumb'), _urmmS(3))
                    scrollbar_hover_thumb urmk_pill(urm_map_ink('thumbHover'), _urmmS(3))
                    scrollbar_thumb_offset 0
                    scrollbar_unscrollable 'hide'
                    vscrollbar_xsize _urmmBar
                    vscrollbar_base_bar urmk_pill(urm_map_ink('track'), _urmmS(3))
                    vscrollbar_thumb urmk_pill(urm_map_ink('thumb'), _urmmS(3))
                    vscrollbar_hover_thumb urmk_pill(urm_map_ink('thumbHover'), _urmmS(3))
                    vscrollbar_thumb_offset 0
                    vscrollbar_unscrollable 'hide'
                    xadjustment _urmmXadj
                    yadjustment _urmmYadj
                    yinitial _urmmYinit
                    fixed:
                        xysize (max(_urmmV.width, config.screen_width), _urmmTotalH)
                        fixed:
                            xysize (_urmmV.width, _urmmV.height)
                            yalign .5
                            for _urmmX, _urmmY, _urmmW, _urmmH, _urmmT in _urmmV.bars:
                                add Solid(urm_map_ink('line'), xminimum=_urmmW, xmaximum=_urmmW, yminimum=_urmmH, ymaximum=_urmmH) xpos _urmmX ypos _urmmY
                            for _urmmDx, _urmmDy, _urmmDtip in _urmmV.picks:
                                button:
                                    style 'urmk_button'
                                    xysize (_urmmS(32), _urmmS(32))
                                    pos (_urmmDx, _urmmDy)
                                    anchor (.5, .5)
                                    hovered SetScreenVariable('_urmmTip', (_urmmDtip, _urmmDx - _urmmS(16), _urmmDy - _urmmS(16), _urmmS(32), _urmmS(32)))
                                    unhovered SetScreenVariable('_urmmTip', None)
                                    action NullAction()
                                    add urm_map_mark(_urmmS(20), 'screen') align (.5, .5)
                                    add urm_map_mark(_urmmS(14), 'pick') align (.5, .5)
                            for _urmmDx, _urmmDy, _urmmDtip in _urmmV.marks:
                                button:
                                    style 'urmk_button'
                                    xysize (_urmmS(24), _urmmS(24))
                                    pos (_urmmDx, _urmmDy)
                                    anchor (.5, .5)
                                    hovered SetScreenVariable('_urmmTip', (_urmmDtip, _urmmDx - _urmmS(12), _urmmDy - _urmmS(12), _urmmS(24), _urmmS(24)))
                                    unhovered SetScreenVariable('_urmmTip', None)
                                    action NullAction()
                                    add urm_map_mark(_urmmS(14), 'screen') align (.5, .5)
                                    add urm_map_mark(_urmmS(9), 'lines') align (.5, .5)
                            for _urmmDx, _urmmDy, _urmmDtip in _urmmV.codes:
                                button:
                                    style 'urmk_button'
                                    background urm_map_ink('screen')
                                    hover_background urm_map_ink('screen')
                                    xysize (_urmmS(18), _urmmS(24))
                                    pos (_urmmDx, _urmmDy)
                                    anchor (.5, .5)
                                    hovered SetScreenVariable('_urmmTip', (_urmmDtip, _urmmDx - _urmmS(9), _urmmDy - _urmmS(12), _urmmS(18), _urmmS(24)))
                                    unhovered SetScreenVariable('_urmmTip', None)
                                    action NullAction()
                                    text '?' style 'urmk_text' font _urmmMedium size _urmmS(17) color urm_map_ink('lines') align (.5, .5)
                            for _urmmB in _urmmV.boxes:
                                if not _urmmB.dot:
                                    $ _urmmLoud = _urmmB.kind in ('here', 'merge')
                                    $ _urmmFill = urm_map_ink('accent') if _urmmLoud else urm_map_ink('game' if _urmmB.kind == 'branch' else 'box')
                                    $ _urmmWords = urmk_colour('disabled') if _urmmB.faded else (urm_map_ink('on-accent') if _urmmLoud else _urmmInk)
                                    $ _urmmSoft = urmk_colour('disabled') if _urmmB.faded else (urm_map_ink('on-accent') if _urmmLoud else _urmmMuted)
                                    $ _urmmHeard = getattr(_urmmB, 'heard', None) if _urmmB.kind == 'here' else None
                                    frame:
                                        style 'urmk_frame'
                                        xpos _urmmB.x
                                        ypos _urmmB.y
                                        xsize _urmmB.w
                                        ysize _urmmB.h
                                        background urmk_pill(_urmmFill, _urmmS(14))
                                        padding (_urmmS(14), _urmmS(8))
                                        vbox:
                                            spacing _urmmS(5)
                                            if _urmmB.kind == 'here':
                                                hbox:
                                                    spacing _urmmS(4)
                                                    text '' style 'urmk_icon' size _urmmS(16) color _urmmWords yalign .5
                                                    text 'YOU ARE HERE' style 'urmk_text' font _urmmMedium size _urmmS(14) color _urmmWords yalign .5
                                            if _urmmHeard:
                                                text urm_map_esc(_urmmHeard) style 'urmk_text' italic True size _urmmS(19) color _urmmWords substitute False
                                            elif _urmmB.title and _urmmB.have and _urmmB.have_beside:
                                                hbox:
                                                    spacing _urmmS(6)
                                                    text urm_map_esc(_urmmB.title) style 'urmk_text' size _urmmS(19) font (_urmmMedium if _urmmLoud else URMK_FONTS['regular']) color _urmmWords yalign .5 substitute False
                                                    frame:
                                                        style 'urmk_frame'
                                                        yalign .5
                                                        background urm_chip_bg(_urmmB.have[1], _urmmLoud, _urmmB.faded)
                                                        padding (_urmmS(8), _urmmS(2))
                                                        text urm_map_esc(_urmmB.have[0]) style 'urmk_text' size _urmmS(16) color urm_chip_ink(_urmmB.have[1], _urmmLoud, _urmmB.faded) substitute False
                                            elif _urmmB.title:
                                                text urm_map_esc(_urmmB.title) style 'urmk_text' size _urmmS(19) font (_urmmMedium if _urmmLoud else URMK_FONTS['regular']) color _urmmWords substitute False
                                                if _urmmB.have:
                                                    frame:
                                                        style 'urmk_frame'
                                                        background urm_chip_bg(_urmmB.have[1], _urmmLoud, _urmmB.faded)
                                                        padding (_urmmS(8), _urmmS(2))
                                                        text urm_map_esc(_urmmB.have[0]) style 'urmk_text' size _urmmS(16) color urm_chip_ink(_urmmB.have[1], _urmmLoud, _urmmB.faded) substitute False
                                            if _urmmB.sub:
                                                text urm_map_esc(_urmmB.sub) style 'urmk_text' italic True size _urmmS(15) color _urmmSoft substitute False
                                            if _urmmB.draw:
                                                vbox:
                                                    spacing _urmmS(4)
                                                    for _urmmRl, _urmmRtip, _urmmRf, _urmmRh, _urmmRc in _urmmB.draw:
                                                        hbox:
                                                            ysize _urmmRh
                                                            spacing _urmmS(6)
                                                            if _urmmRl == 'check':
                                                                button:
                                                                    style 'urmk_button'
                                                                    xysize (_urmmS(24), _urmmS(24))
                                                                    yalign .5
                                                                    hovered SetScreenVariable('_urmmTip', _urmmRtip)
                                                                    unhovered SetScreenVariable('_urmmTip', None)
                                                                    action NullAction()
                                                                    add urm_map_mark(_urmmS(9), 'lines') align (.5, .5)
                                                            elif _urmmRl:
                                                                null width _urmmS(24)
                                                            for _urmmCk, _urmmCw, _urmmCt in _urmmRc:
                                                                if _urmmCk == 'chip':
                                                                    frame:
                                                                        style 'urmk_frame'
                                                                        yalign .5
                                                                        background urm_chip_bg(_urmmCt, _urmmLoud, _urmmRf or _urmmB.faded)
                                                                        padding (_urmmS(8), _urmmS(2))
                                                                        text urm_map_esc(_urmmCw) style 'urmk_text' size _urmmS(16) color urm_chip_ink(_urmmCt, _urmmLoud, _urmmRf or _urmmB.faded) substitute False
                                                                elif _urmmCk == 'menu':
                                                                    text '' style 'urmk_icon' size _urmmS(18) color (urmk_colour('disabled') if _urmmRf else _urmmSoft) yalign .5
                                                                elif _urmmCk == 'check':
                                                                    button:
                                                                        style 'urmk_button'
                                                                        xysize (_urmmS(24), _urmmS(24))
                                                                        yalign .5
                                                                        hovered SetScreenVariable('_urmmTip', _urmmCw)
                                                                        unhovered SetScreenVariable('_urmmTip', None)
                                                                        action NullAction()
                                                                        add urm_map_mark(_urmmS(9), 'lines') align (.5, .5)
                                                                elif _urmmCk == 'code':
                                                                    button:
                                                                        style 'urmk_button'
                                                                        xysize (_urmmS(24), _urmmS(24))
                                                                        yalign .5
                                                                        hovered SetScreenVariable('_urmmTip', _urmmCw)
                                                                        unhovered SetScreenVariable('_urmmTip', None)
                                                                        action NullAction()
                                                                        text '?' style 'urmk_text' font _urmmMedium size _urmmS(17) color urm_map_ink('lines') align (.5, .5)
                                                                else:
                                                                    text _urmmCw style 'urmk_text' size _urmmS(15) color (urmk_colour('disabled') if _urmmRf else _urmmSoft) yalign .5
                                            if _urmmB.note:
                                                if _urmmB.note_tone:
                                                    frame:
                                                        style 'urmk_frame'
                                                        background urm_chip_bg(_urmmB.note_tone, _urmmLoud, _urmmB.faded)
                                                        padding (_urmmS(8), _urmmS(2))
                                                        text urm_map_esc(_urmmB.note) style 'urmk_text' font _urmmMedium size _urmmS(16) color urm_chip_ink(_urmmB.note_tone, _urmmLoud, _urmmB.faded) substitute False
                                                else:
                                                    text urm_map_esc(_urmmB.note) style 'urmk_text' italic True size _urmmS(15) color _urmmSoft substitute False
                if _urmmBig:
                    frame:
                        style 'urmk_frame'
                        xalign 1.0
                        yalign 1.0
                        xoffset -_urmmS(28)
                        yoffset -_urmmS(28)
                        background urmk_pill(urm_map_ink('box'), _urmmS(10))
                        padding (_urmmS(8), _urmmS(8))
                        add DynamicDisplayable(urm_map_overview, _urmmV, _urmmXadj, _urmmYadj, (config.screen_width, _urmmViewH), (_urmmS(240), _urmmS(140)))
                if _urmmTip:
                    add DynamicDisplayable(urm_map_bubble, _urmmTip, _urmmV, _urmmXadj, _urmmYadj, (config.screen_width, _urmmViewH))

            if _urmmV.later:
                frame:
                    style 'urmk_frame'
                    xfill True
                    ysize _urmmFoot
                    background urmk_pill(urm_map_ink('box'), _urmmS(14))
                    padding (_urmmS(24), _urmmS(8))
                    vbox:
                        spacing _urmmS(4)
                        hbox:
                            spacing _urmmS(10)
                            text '' style 'urmk_icon' size _urmmS(20) color _urmmMuted yalign .5
                            text 'What these choices decide later' style 'urmk_text' font _urmmMedium size _urmmS(20) color _urmmInk yalign .5
                        for _urmmLw, _urmmLh, _urmmLt in urm_map_later_view(_urmmV)[:6]:
                            hbox:
                                spacing _urmmS(10)
                                ysize _urmmS(26)
                                text '' style 'urmk_icon' size _urmmS(18) color _urmmMuted yalign .5
                                text urm_map_esc(_urmmLw) style 'urmk_text' size _urmmS(18) color _urmmInk yalign .5 substitute False
                                if _urmmLh:
                                    frame:
                                        style 'urmk_frame'
                                        yalign .5
                                        background urm_chip_bg(_urmmLt)
                                        padding (_urmmS(8), _urmmS(1))
                                        text urm_map_esc(_urmmLh) style 'urmk_text' size _urmmS(16) color urm_chip_ink(_urmmLt) substitute False
