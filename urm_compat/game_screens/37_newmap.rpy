# The new map's story line (game_fixes/37_newmap_view builds what it
# draws), drawn as the user's picked drawings show it (research/newmap:
# q1 panel b, q3 panel a): left to right from "YOU ARE HERE", one card per
# split on the line, its options numbered with their chips; "meet again
# after ~N lines" above a card whose ways stay on the line; a way that stays
# apart 20 lines or more leaves on a smooth line to a small box with its
# length and comes back at a dot; a way that ends the game drops in red
# under its card; the amber diamond on the line before a split the game
# decides; versions as one dashed purple block.

screen urmnm_story():
    modal True
    zorder 300

    default _urmnmOpen = ()

    python:
        _urmnmMode = urmnm_story_mode()
        _urmnmCount = urmnm_card_count()
        _urmnmSbCount = urmnm_sandbox_count()
        _urmnmEmpty = urmnm_empty_text()
        _urmnmLaterCount = urmnm_later_count()
        _urmnmHead = urmk_px_cut(70)
        _urmnmFoot = (urmk_px_cut(48) + urmk_px_cut(30) * min(6, _urmnmLaterCount)) if _urmnmLaterCount else 0
        _urmnmViewH = config.screen_height - _urmnmHead - _urmnmFoot
        _urmnmInk = urmk_colour('ink')
        _urmnmMuted = urmk_colour('ink-muted')
        _urmnmMedium = URMK_FONTS['medium']
        _urmnmCaps = urmnm_has_caps()
        _urmnmRow = urmk_px_cut(78) if _urmnmCaps else urmk_px_cut(40)
        _urmnmForkW = urmk_px_cut(300)
        _urmnmForkH = urmk_px_cut(190)
        _urmnmLegend = urmnm_legend_now(_urmnmOpen)

    key 'K_ESCAPE' action Function(urmnm_story_close)
    key 'mouseup_3' action Function(urmnm_story_close)
    for _urmnmSk in URMK_SCROLL_KEYS:
        key _urmnmSk action NullAction()

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
            ysize _urmnmHead
            padding (urmk_px_cut(24), urmk_px_cut(8))
            fixed:
                hbox:
                    yalign .5
                    spacing urmk_px_cut(14)
                    add urmk_word(u'', style='urmk_icon', size=urmk_px_cut(32), color=urmk_colour('accent-ink'), yalign=0.5)
                    add urmk_word(('Sandbox' if _urmnmMode == 'sandbox' else 'Story line'), style='urmk_text', font=_urmnmMedium, size=urmnm_font_px(28, 20), color=_urmnmInk, yalign=0.5)
                hbox:
                    xalign 1.0
                    yalign .5
                    spacing urmk_px_cut(8)
                    if 'big' in _urmnmLegend:
                        add urmnm_mark(urmk_px_cut(14), 'big') yalign .5
                        add urmk_word('the game picks the way', style='urmk_text', size=urmnm_font_px(16, 13), color=_urmnmMuted, yalign=0.5)
                        null width urmk_px_cut(8)
                    if 'small' in _urmnmLegend:
                        add urmnm_mark(urmk_px_cut(9), 'small') yalign .5
                        add urmk_word('only lines change', style='urmk_text', size=urmnm_font_px(16, 13), color=_urmnmMuted, yalign=0.5)
                        null width urmk_px_cut(8)
                    if 'short' in _urmnmLegend:
                        add urmnm_short_mark(urmk_px_cut(9)) yalign .5
                        add urmk_word('extra dialogue', style='urmk_text', size=urmnm_font_px(16, 13), color=_urmnmMuted, yalign=0.5)
                        null width urmk_px_cut(8)
                    if 'faded' in _urmnmLegend:
                        frame:
                            style 'urmk_frame'
                            yalign .5
                            background urm_chip_bg('plain', faded=True)
                            padding (urmk_px_cut(8), urmk_px_cut(2))
                            add urmk_word('faded', style='urmk_text', size=urmnm_font_px(16, 13), color=urmk_colour('disabled'))
                        add urmk_word('not as things stand', style='urmk_text', size=urmnm_font_px(16, 13), color=_urmnmMuted, yalign=0.5)
                        null width urmk_px_cut(8)
                    use urmk_button('', Function(urmnm_story_close), 'plain', 'small', icon=u'')

        if _urmnmMode == 'sandbox' and _urmnmSbCount:
            use urmnm_sandbox_view(_urmnmViewH)
        elif not _urmnmCount:
            frame:
                style 'urmk_frame'
                xfill True
                ysize _urmnmViewH
                add urmk_word(urmnm_esc_text(_urmnmEmpty), style='urmk_text', align=(0.5, 0.4), size=urmnm_font_px(24, 18), color=_urmnmInk)
        else:
            use urmnm_viewport(_urmnmCount, _urmnmOpen, _urmnmRow, _urmnmForkW, _urmnmForkH, _urmnmViewH)
            if _urmnmLaterCount:
                frame:
                    style 'urmk_frame'
                    xfill True
                    ysize _urmnmFoot
                    background urmk_pill(urmk_colour('surface'), urmk_px_cut(14))
                    padding (urmk_px_cut(24), urmk_px_cut(8))
                    vbox:
                        spacing urmk_px_cut(4)
                        hbox:
                            spacing urmk_px_cut(10)
                            add urmk_word(u'', style='urmk_icon', size=urmnm_font_px(20, 14), color=_urmnmMuted, yalign=0.5)
                            add urmk_word('What these choices decide later', style='urmk_text', font=_urmnmMedium, size=urmnm_font_px(20, 14), color=_urmnmInk, yalign=0.5)
                        for _urmnmLItem index _urmnmLItem[0] in urmnm_later_rows():
                            $ _urmnmLw, _urmnmLh, _urmnmLt, _urmnmLn = _urmnmLItem
                            hbox:
                                spacing urmk_px_cut(10)
                                ysize urmk_px_cut(26)
                                add urmk_word(u'', style='urmk_icon', size=urmnm_font_px(18, 13), color=_urmnmMuted, yalign=0.5)
                                add urmk_word(urmnm_esc_text(_urmnmLw), style='urmk_text', size=urmnm_font_px(18, 13), color=_urmnmInk, yalign=0.5)
                                if _urmnmLh:
                                    $ _urmnmCw, _urmnmCt, _urmnmCn = urmnm_chip_parts((_urmnmLh, _urmnmLt, _urmnmLn))
                                    use urmnm_chip(_urmnmCw, _urmnmCt, _urmnmCn)

    $ _urmnmHover = GetTooltip('urmnm_story')
    if _urmnmHover and urmnm_short_tip_at():
        $ _urmnmSize = urmnm_font_px(16, 13)
        $ _urmnmPad = urmk_px_cut(12)
        $ _urmnmMargin = urmk_px_cut(16)
        $ _urmnmWords = urmnm_esc_text(_urmnmHover)
        $ _urmnmTipW = min(urmnm_text_w(_urmnmWords, _urmnmSize) + 2 * _urmnmPad, urmk_px_cut(430), config.screen_width - 2 * _urmnmMargin)
        $ _urmnmMx, _urmnmMy = renpy.get_mouse_pos()
        $ _urmnmTipX = max(_urmnmMargin, min(_urmnmMx + _urmnmMargin, config.screen_width - _urmnmTipW - _urmnmMargin))
        $ _urmnmClearance = urmk_px_cut(76)
        $ _urmnmAbove = _urmnmMy >= _urmnmHead + _urmnmClearance + urmk_px_cut(110)
        frame:
            style 'urmk_frame'
            xpos _urmnmTipX
            ypos (_urmnmMy - _urmnmClearance if _urmnmAbove else _urmnmMy + _urmnmClearance)
            yanchor (1.0 if _urmnmAbove else 0.0)
            xsize _urmnmTipW
            padding (_urmnmPad, urmk_px_cut(6))
            background urmk_pill(urmk_colour('surface-2'), urmk_px_cut(8))
            add urmk_word(_urmnmWords, style='urmk_text', size=_urmnmSize, color=_urmnmInk)

screen urmnm_viewport(count, opened, row_h, fork_w, fork_h, view_h):
    default _urmnmXadj = ui.adjustment()
    $ _urmnmTip = urmnm_tip_now()
    $ _urmnmMedium = URMK_FONTS['medium']
    fixed:
        xfill True
        ysize view_h
        viewport:
            xfill True
            ysize view_h
            mousewheel 'horizontal'
            draggable True
            scrollbars 'horizontal'
            scrollbar_ysize urmk_px_cut(6)
            scrollbar_base_bar urmk_pill(urmk_colour('track'), urmk_px_cut(3))
            scrollbar_thumb urmk_pill(urmk_colour('thumb'), urmk_px_cut(3))
            scrollbar_hover_thumb urmk_pill(urmk_colour('thumb-hover'), urmk_px_cut(3))
            scrollbar_unscrollable 'hide'
            xadjustment _urmnmXadj
            vbox:
                ysize view_h - urmk_px_cut(12)
                hbox:
                    yalign .45
                    spacing 0
                    null width urmk_px_cut(40)
                    frame:
                        style 'urmk_frame'
                        yalign .5
                        background urmk_pill(urmk_colour('accent'), urmk_px_cut(10))
                        padding (urmk_px_cut(14), urmk_px_cut(8))
                        add urmk_word('YOU ARE HERE', style='urmk_text', font=_urmnmMedium, size=urmnm_font_px(18, 14), color=urmk_colour('on-accent'))
                    for _urmnmI index _urmnmI in range(count):
                        use urmnm_step_slot(_urmnmI, count, opened, row_h, fork_w, fork_h)
                    null width urmk_px_cut(60)
        if count >= 2:
            frame:
                style 'urmk_frame'
                xalign 1.0
                yalign 1.0
                xoffset -urmk_px_cut(24)
                yoffset -urmk_px_cut(24)
                background urmk_pill(urmk_colour('surface'), urmk_px_cut(10))
                padding (urmk_px_cut(8), urmk_px_cut(8))
                add DynamicDisplayable(urmnm_overview, _urmnmXadj, (urmk_px_cut(220), urmk_px_cut(38)))
        if _urmnmTip:
            frame:
                style 'urmk_frame'
                xalign 0.0
                yalign 1.0
                xoffset urmk_px_cut(24)
                yoffset -urmk_px_cut(24)
                background urmk_back('inset').image
                padding (urmk_px_cut(14), urmk_px_cut(8))
                add urmk_word(urmnm_esc_text(_urmnmTip), style='urmk_text', size=urmnm_font_px(16, 13), color=urmk_colour('ink'))

screen urmnm_step_slot(idx, total, opened, row_h, fork_w, fork_h):
    $ _urmnmK = urmnm_card_at(idx)
    $ _urmnmS = urmk_px_cut
    $ _urmnmInk = urmk_colour('ink')
    $ _urmnmMuted = urmk_colour('ink-muted')
    $ _urmnmMedium = URMK_FONTS['medium']
    $ _urmnmLine = urmk_colour('graph-line')
    $ _urmnmRed = urmk_colour('loss-ink')
    $ _urmnmBar = max(2, _urmnmS(3))
    if _urmnmK is not None and getattr(_urmnmK, 'roam', False):
        use urmnm_roam_card(_urmnmK, idx, opened, total)
    elif _urmnmK is not None:
        $ _urmnmSplit = urmnm_check_split(_urmnmK)
        $ _urmnmFh = urmnm_fork_h(_urmnmK, fork_h, _urmnmS(56))
        $ _urmnmCw = _urmnmS(100)
        $ _urmnmBack = urmnm_lane_rows(_urmnmK, _urmnmFh, _urmnmS(56))
        $ _urmnmFw = max(fork_w + (_urmnmS(180) if _urmnmSplit else 0), urmnm_fork_w(_urmnmK, urmnm_font_px(16, 13)) + 2 * _urmnmCw + _urmnmS(40))
        $ _urmnmHome = [l for l, _y in _urmnmBack if l.cap is None]
        $ _urmnmCaps = [l for l in _urmnmK.lanes if l.cap] if _urmnmK.numbered else []
        $ _urmnmSlotH = max(row_h, len(_urmnmCaps) * _urmnmS(40) + _urmnmS(16)) if _urmnmCaps else row_h
        hbox:
            yalign .5
            spacing 0
            # the line into the card, and its diamond
            use urmnm_connector(idx, _urmnmK.short_checks)
            if _urmnmSplit:
                # A check the game decides whose ways stay apart: no card,
                # the diamond on the line says what it checks, a box per way.
                $ _urmnmLab = urmnm_check_label(_urmnmK)
                $ _urmnmLw = max(_urmnmS(40), urmnm_text_w(_urmnmLab, urmnm_font_px(16, 13)) + _urmnmS(8))
                fixed:
                    yalign .5
                    xysize (_urmnmLw, _urmnmS(110))
                    add Solid(_urmnmLine, xysize=(_urmnmLw, _urmnmBar)) ypos _urmnmS(55) yanchor .5
                    add urmnm_mark(_urmnmS(24), 'big') xalign .5 ypos _urmnmS(55) yanchor .5
                    add urmk_word(urmnm_esc_text(_urmnmLab), style='urmk_text', size=urmnm_font_px(16, 13), color=urmk_tone_ink('warn'), xalign=0.5, ypos=_urmnmS(34), yanchor=1.0)
            vbox:
                if _urmnmSplit:
                    null
                yalign .5
                # Keep top spacer matched to bottom drop room so card centers on main line.
                frame:
                    style 'urmk_frame'
                    ysize _urmnmSlotH
                    padding (0, 0, 0, _urmnmS(8))
                    if _urmnmSplit:
                        null
                    elif _urmnmK.note:
                        add urmk_word(_urmnmK.note, style='urmk_text', size=urmnm_font_px(16, 13), color=_urmnmMuted, yalign=1.0)
                    else:
                        null
                if _urmnmSplit:
                    null
                elif _urmnmK.versions is not None:
                    use urmnm_versions(_urmnmK, idx, opened)
                else:
                    frame:
                        style 'urmk_frame'
                        background urmnm_card_ground(not _urmnmK.numbered)
                        padding (_urmnmS(16), _urmnmS(12))
                        vbox:
                            spacing _urmnmS(6)
                            add urmk_word(_urmnmK.title, style='urmk_text', font=_urmnmMedium, size=urmnm_font_px(19, 15), color=_urmnmInk)
                            for _urmnmRItem index _urmnmRItem[0] in enumerate(_urmnmK.rows):
                                $ _urmnmN, _urmnmR = _urmnmRItem
                                use urmnm_row(_urmnmR, (_urmnmN + 1) if _urmnmK.numbered else None)
                # A choice's way that ends drops under its card cleanly in stacked rows.
                fixed:
                    xysize (_urmnmS(260) if _urmnmCaps else 0, _urmnmSlotH)
                    for _urmnmJ, _urmnmL in enumerate(_urmnmCaps):
                        $ _urmnmCy = _urmnmS(22) + _urmnmJ * _urmnmS(40)
                        add urmnm_curve(_urmnmS(52), _urmnmSlotH, 0, 0, _urmnmS(48), _urmnmCy, _urmnmRed, _urmnmBar, True) xpos _urmnmS(24)
                        frame:
                            style 'urmk_frame'
                            xpos _urmnmS(72)
                            ypos _urmnmCy
                            yanchor .5
                            background urmk_pill(urmk_colour('surface-2'), _urmnmS(8))
                            padding (_urmnmS(10), _urmnmS(4))
                            add urmk_word(urmnm_esc_text(urmnm_cap_words(_urmnmK, _urmnmL)), style='urmk_text', size=urmnm_font_px(16, 13), color=urmk_colour('disabled') if _urmnmL.faded else _urmnmInk)
            if _urmnmBack:
                fixed:
                    yalign .5
                    xysize (_urmnmFw, _urmnmFh)
                    if urmnm_staying_rows(_urmnmK):
                        add Solid(_urmnmLine, xysize=(_urmnmFw, _urmnmBar)) ypos (_urmnmFh // 2 - _urmnmBar // 2)
                    if _urmnmSplit and urmnm_staying_rows(_urmnmK):
                        # with no card, the ways that stay on the line are named on it
                        # one box for all of them, a row each, so they never overlap
                        frame:
                            style 'urmk_frame'
                            xpos _urmnmFw // 2
                            ypos _urmnmFh // 2
                            anchor (.5, .5)
                            background urmk_pill(urmk_colour('surface-2'), _urmnmS(8))
                            padding (_urmnmS(10), _urmnmS(4))
                            vbox:
                                spacing _urmnmS(2)
                                for _urmnmR in urmnm_staying_rows(_urmnmK):
                                    hbox:
                                        spacing _urmnmS(6)
                                        add urmk_word(urmnm_esc_text(_urmnmR.words), style='urmk_text', size=urmnm_font_px(16, 13), color=urmk_colour('disabled' if _urmnmR.faded else 'ink'), yalign=0.5)
                                        if _urmnmR.lit:
                                            add urmk_word('as things stand', style='urmk_text', italic=True, size=urmnm_font_px(14, 12), color=_urmnmMuted, yalign=0.5)
                    for _urmnmL, _urmnmY in _urmnmBack:
                        $ _urmnmPx = (_urmnmFw // 2) if _urmnmL.cap is None else _urmnmCw
                        $ _urmnmAx = .5 if _urmnmL.cap is None else 0.0
                        add urmnm_curve(_urmnmCw, _urmnmFh, 0, _urmnmFh // 2, _urmnmCw, _urmnmY, (_urmnmRed if _urmnmL.cap else _urmnmLine), _urmnmBar)
                        if _urmnmL.cap is None:
                            add urmnm_curve(_urmnmCw, _urmnmFh, 0, _urmnmY, _urmnmCw, _urmnmFh // 2, _urmnmLine, _urmnmBar) xpos _urmnmFw - _urmnmCw
                            # Overlap joins by 2px on each end so curved strokes leave zero gap
                            add Solid(_urmnmLine, xysize=(max(2, _urmnmFw - 2 * _urmnmCw + 4), _urmnmBar)) xpos _urmnmCw - 2 ypos (_urmnmY - _urmnmBar // 2)
                        frame:
                            style 'urmk_frame'
                            xpos _urmnmPx
                            ypos _urmnmY
                            xanchor _urmnmAx
                            yanchor .5
                            background urmk_pill(urmk_colour('row-on' if _urmnmL.lit else 'surface-2'), _urmnmS(8))
                            padding (_urmnmS(10), _urmnmS(4))
                            if _urmnmL.cap:
                                add urmk_word(urmnm_esc_text(urmnm_cap_words(_urmnmK, _urmnmL)), style='urmk_text', size=urmnm_font_px(16, 13), color=urmk_colour('disabled') if _urmnmL.faded else _urmnmInk)
                            else:
                                hbox:
                                    spacing _urmnmS(6)
                                    add urmk_word(urmnm_esc_text(urmnm_lane_words(_urmnmK, _urmnmL)), style='urmk_text', size=urmnm_font_px(16, 13), color=urmk_colour('disabled') if _urmnmL.faded else _urmnmInk, yalign=0.5)
                                    for _urmnmCh in urmnm_lane_chips(_urmnmK, _urmnmL):
                                        $ _urmnmCw2, _urmnmCt, _urmnmCn = urmnm_chip_parts(_urmnmCh)
                                        use urmnm_chip(_urmnmCw2, _urmnmCt, _urmnmCn, faded=_urmnmL.faded)
                                    if _urmnmL.lit:
                                        add urmk_word('as things stand', style='urmk_text', italic=True, size=urmnm_font_px(14, 12), color=_urmnmMuted, yalign=0.5)
                    if idx == total - 1 and not _urmnmHome and urmnm_staying_rows(_urmnmK):
                        fixed:
                            xysize (_urmnmS(10), _urmnmS(10))
                            xpos _urmnmFw - _urmnmS(5)
                            ypos _urmnmFh // 2
                            anchor (.5, .5)
                            add urmk_pill(_urmnmLine, _urmnmS(5))
            if _urmnmHome or (_urmnmK.versions is not None and _urmnmK.meet):
                if not _urmnmHome:
                    add Solid(_urmnmLine, xysize=(_urmnmS(48), _urmnmBar)) yalign .5
                # where the ways meet again: a landmark box, the game's
                # first line there quoted; the line goes on from its right
                frame:
                    style 'urmk_frame'
                    yalign .5
                    background urmk_pill(urmk_colour('surface-2'), _urmnmS(10))
                    padding (_urmnmS(14), _urmnmS(8))
                    vbox:
                        spacing _urmnmS(2)
                        add urmk_word('Ways meet again', style='urmk_text', font=_urmnmMedium, size=urmnm_font_px(16, 13), color=_urmnmInk)
                        if _urmnmK.meet_line:
                            add urmk_word(_urmnmK.meet_line, style='urmk_text', italic=True, size=urmnm_font_px(15, 12), color=_urmnmMuted)

screen urmnm_connector(idx, marks):
    $ _urmnmS = urmk_px_cut
    $ _urmnmGap = _urmnmS(52)
    $ _urmnmWidth = max(_urmnmS(64), (len(marks) + 1) * _urmnmGap)
    fixed:
        yalign .5
        xysize (_urmnmWidth, _urmnmS(46 if marks else 30))
        add Solid(urmk_colour('graph-line'), xysize=(_urmnmWidth, max(2, _urmnmS(3)))) yalign .5
        for _urmnmI index _urmnmI in range(len(marks)):
            $ _urmnmCount, _urmnmLarge, _urmnmTip = marks[_urmnmI]
            $ _urmnmToken = ('short_check', idx, _urmnmI)
            $ _urmnmX = (_urmnmI + 1) * _urmnmGap
            $ _urmnmSize = _urmnmS(13 if _urmnmLarge else 9)
            button:
                id _urmnmToken
                style 'urmk_button'
                xpos _urmnmX
                xanchor .5
                yalign .5
                xysize (_urmnmGap, _urmnmS(46))
                action Function(urmnm_hold_short_mark)
                tooltip u'{}'.format(_urmnmTip)
                fixed:
                    add urmnm_short_mark(_urmnmSize) align (.5, .5)
                    add urmk_word(_urmnmCount, style='urmk_text', size=urmnm_font_px(16, 13), color=urmk_colour('ink-muted'), xalign=.5)

screen urmnm_row(r, n):
    $ _urmnmS = urmk_px_cut
    $ _urmnmLost = getattr(r, 'lost', ())
    hbox:
        spacing _urmnmS(8)
        if _urmnmLost:
            add Solid(urmk_colour('loss-ink'), xysize=(max(2, _urmnmS(3)), _urmnmS(24))) yalign .5
        if n is not None:
            add urmk_word(str(n), style='urmk_text', size=urmnm_font_px(18, 14), color=urmk_colour('disabled' if r.faded else 'accent-ink'), yalign=0.5)
        add urmk_word(urmnm_esc_text(r.words), style='urmk_text', italic=r.muted, size=urmnm_font_px(18, 14), color=urmk_colour('disabled' if r.faded else ('ink-muted' if r.muted else 'ink')), yalign=0.5)
        for _urmnmCh in (r.have_chips if getattr(r, 'have_chips', None) else ((r.have,) if r.have else ())):
            $ _urmnmCw, _urmnmCt, _urmnmCn = urmnm_chip_parts(_urmnmCh)
            use urmnm_chip(_urmnmCw, _urmnmCt, _urmnmCn, faded=r.faded)
        for _urmnmCh in r.chips:
            $ _urmnmCw, _urmnmCt, _urmnmCn = urmnm_chip_parts(_urmnmCh)
            use urmnm_chip(_urmnmCw, _urmnmCt, _urmnmCn, urmnm_chip_tip(_urmnmCw), faded=r.faded)
        for _urmnmCh in getattr(r, 'quiet_chips', ()):
            $ _urmnmCw, _urmnmCt, _urmnmCn = urmnm_chip_parts(_urmnmCh)
            frame:
                style 'urmk_frame'
                yalign .5
                use urmnm_chip(_urmnmCw, _urmnmCt, _urmnmCn, urmnm_chip_tip(_urmnmCw, quiet=True), faded=True)
        for _urmnmPlace in _urmnmLost:
            $ _urmnmLw = u"You lose %s" % _urmnmPlace
            use urmnm_chip(_urmnmLw, 'loss', None, urmnm_chip_tip(_urmnmLw, lost=True), faded=r.faded)
        if r.lines:
            add urmk_word(r.lines, style='urmk_text', size=urmnm_font_px(15, 12), color=urmk_colour('ink-muted'), yalign=0.5)
        if r.lit:
            add urmk_word('as things stand', style='urmk_text', italic=True, size=urmnm_font_px(14, 12), color=urmk_colour('ink-muted'), yalign=0.5)

screen urmnm_chip(words, tone, name=None, tip=None, faded=False):
    $ _urmnmS = urmk_px_cut
    $ _urmnmChipGround = urm_chip_bg(tone, faded=faded)
    $ _urmnmChipInk = urm_chip_ink(tone, faded=faded)
    if name:
        button:
            style 'urmk_button'
            yalign .5
            if tip:
                hovered Function(urmnm_set_tip, tip)
                unhovered Function(urmnm_set_tip, None)
            action Function(urmnm_open_value, name)
            fixed:
                fit_first True
                frame:
                    style 'urmk_frame'
                    background _urmnmChipGround
                    padding (_urmnmS(8), _urmnmS(2))
                    add urmk_word(urmnm_esc_text(words), style='urmk_text', size=urmnm_font_px(16, 13), color=_urmnmChipInk)
                add urmk_word(u'\u203a', style='urmk_text', size=urmnm_font_px(16, 13), color='#0000', hover_color=urmk_colour('ink'), xalign=1.0, xoffset=-_urmnmS(4), yalign=0.5)
    elif tip:
        button:
            style 'urmk_button'
            yalign .5
            hovered Function(urmnm_set_tip, tip)
            unhovered Function(urmnm_set_tip, None)
            action NullAction()
            frame:
                style 'urmk_frame'
                background _urmnmChipGround
                padding (_urmnmS(8), _urmnmS(2))
                add urmk_word(urmnm_esc_text(words), style='urmk_text', size=urmnm_font_px(16, 13), color=_urmnmChipInk)
    else:
        frame:
            style 'urmk_frame'
            yalign .5
            background _urmnmChipGround
            padding (_urmnmS(8), _urmnmS(2))
            add urmk_word(urmnm_esc_text(words), style='urmk_text', size=urmnm_font_px(16, 13), color=_urmnmChipInk)

screen urmnm_versions(k, idx, opened):
    $ _urmnmS = urmk_px_cut
    $ _urmnmCur = k.versions[1]
    $ _urmnmShow = range(len(k.rows)) if idx in opened else ([_urmnmCur] if _urmnmCur is not None else [])
    frame:
        style 'urmk_frame'
        background urmnm_dashed()
        padding (_urmnmS(16), _urmnmS(12))
        vbox:
            spacing _urmnmS(6)
            hbox:
                spacing _urmnmS(6)
                add urmk_word(k.versions[0], style='urmk_text', font=URMK_FONTS['medium'], size=urmnm_font_px(19, 15), color=urmk_colour('set-ink'), yalign=1.0)
                if _urmnmCur is not None and idx not in opened:
                    add urmk_word('· the game picks by your route', style='urmk_text', size=urmnm_font_px(15, 12), color=urmk_colour('ink-muted'), yalign=1.0)
            if _urmnmCur is None and idx not in opened:
                add urmk_word('not decided yet', style='urmk_text', size=urmnm_font_px(16, 13), color=urmk_colour('ink-muted'))
            for _urmnmJ index _urmnmJ in _urmnmShow:
                $ _urmnmR = k.rows[_urmnmJ]
                hbox:
                    spacing _urmnmS(12)
                    add urmk_word(urmnm_esc_text(_urmnmR.words), style='urmk_text', font=(URMK_FONTS['medium'] if _urmnmR.lit else URMK_FONTS['regular']), size=urmnm_font_px(18, 14), color=urmk_colour('disabled' if _urmnmR.faded else 'ink'), min_width=_urmnmS(300), yalign=0.5)
                    add urmk_word((_urmnmR.lines or ''), style='urmk_text', size=urmnm_font_px(15, 12), color=urmk_colour('ink-muted'), min_width=_urmnmS(90), yalign=0.5)
                    if _urmnmR.lit:
                        use urmnm_chip('you: true', 'gain')
                        add urmk_word('as things stand', style='urmk_text', italic=True, size=urmnm_font_px(14, 12), color=urmk_colour('ink-muted'), yalign=0.5)
                    elif _urmnmR.faded:
                        use urmnm_chip('you: false', 'loss', faded=True)
            button:
                style 'urmk_button'
                action SetScreenVariable('_urmnmOpen', urmnm_toggle(opened, idx))
                hbox:
                    spacing _urmnmS(4)
                    add urmk_word(urmnm_fold_words(idx in opened, len(k.rows) - (0 if _urmnmCur is None else 1), _urmnmCur is not None), style='urmk_text', size=urmnm_font_px(16, 13), color=urmk_colour('accent-ink'), yalign=0.5)
                    add urmk_word(urmnm_fold_icon(idx in opened), style='urmk_icon', size=urmnm_font_px(20, 15), color=urmk_colour('accent-ink'), yalign=0.5)

# Wave 5.3 Free roam frame (q2_free_roam panel b) on the Story line.
screen urmnm_roam_card(k, idx, opened, total):
    $ _urmnmS = urmk_px_cut
    $ _urmnmInk = urmk_colour('ink')
    $ _urmnmMuted = urmk_colour('ink-muted')
    $ _urmnmAcc = urmk_colour('accent-ink')
    $ _urmnmMedium = URMK_FONTS['medium']
    $ _urmnmLine = urmk_colour('graph-line')
    $ _urmnmBar = max(2, _urmnmS(3))
    $ _urmnmPlaces = urmnm_roam_visible(k.places, opened, idx)
    $ _urmnmMore = urmnm_roam_hidden_count(k.places, opened, idx)
    hbox:
        yalign .5
        spacing 0
        use urmnm_connector(idx, k.short_checks)
        frame:
            style 'urmk_frame'
            yalign .5
            background urmnm_roam_ground()
            padding (_urmnmS(18), _urmnmS(14))
            vbox:
                spacing _urmnmS(10)
                hbox:
                    spacing _urmnmS(10)
                    add urmk_word('Free roam', style='urmk_text', font=_urmnmMedium, size=urmnm_font_px(19, 15), color=_urmnmInk, yalign=0.5)
                    add urmk_word('go anywhere, in any order, come back any time', style='urmk_text', size=urmnm_font_px(14, 12), color=_urmnmMuted, yalign=0.5)
                for _urmnmP in _urmnmPlaces:
                    hbox:
                        spacing _urmnmS(8)
                        add Solid(_urmnmAcc if _urmnmP.moves_story else _urmnmLine, xysize=(_urmnmS(16), _urmnmBar)) yalign .5
                        frame:
                            style 'urmk_frame'
                            background urmk_pill(urmk_colour('surface-2'), _urmnmS(8))
                            padding (_urmnmS(10), _urmnmS(4))
                            hbox:
                                spacing _urmnmS(8)
                                add urmk_word(urmnm_esc_text(_urmnmP.caption), style='urmk_text', font=_urmnmMedium, size=urmnm_font_px(16, 13), color=urmk_colour('disabled') if _urmnmP.faded else _urmnmInk, yalign=0.5)
                                if _urmnmP.lines:
                                    add urmk_word(_urmnmP.lines, style='urmk_text', size=urmnm_font_px(14, 12), color=_urmnmMuted, yalign=0.5)
                        for _urmnmCh in _urmnmP.chips:
                            $ _urmnmCw, _urmnmCt, _urmnmCn = urmnm_chip_parts(_urmnmCh)
                            use urmnm_chip(_urmnmCw, _urmnmCt, _urmnmCn, faded=_urmnmP.faded)
                        for _urmnmSc in _urmnmP.scenes:
                            if _urmnmSc.need:
                                use urmnm_chip(_urmnmSc.need, _urmnmSc.tone, (_urmnmSc.key if _urmnmSc.key and _urmnmSc.state == 'step' else None), faded=_urmnmP.faded)
                        if _urmnmP.seen:
                            use urmnm_chip(u'\u2713 seen', 'plain', faded=_urmnmP.faded)
                        if _urmnmP.moves_story:
                            frame:
                                style 'urmk_frame'
                                yalign .5
                                background urmk_pill(urmk_colour('row-on'), _urmnmS(8))
                                padding (_urmnmS(8), _urmnmS(2))
                                add urmk_word('moves the story on', style='urmk_text', size=urmnm_font_px(14, 12), color=_urmnmAcc)
                if len(k.places) > 6:
                    button:
                        style 'urmk_button'
                        action SetScreenVariable('_urmnmOpen', urmnm_toggle(opened, idx))
                        add urmk_word(('fold places' if idx in opened else ('+%d places' % _urmnmMore)), style='urmk_text', size=urmnm_font_px(15, 12), color=_urmnmAcc)
        if k.exits:
            $ _urmnmFhR = max(_urmnmS(100), len(_urmnmPlaces) * _urmnmS(42) + _urmnmS(56))
            $ _urmnmExitY = _urmnmFhR // 2
            $ _urmnmY0 = urmnm_roam_exit_y(_urmnmPlaces, _urmnmS(64), _urmnmS(40), _urmnmExitY)
            fixed:
                yalign .5
                xysize (_urmnmS(220), _urmnmFhR)
                add urmnm_curve(_urmnmS(110), _urmnmFhR, 0, _urmnmY0, _urmnmS(110), _urmnmExitY, _urmnmAcc, _urmnmBar)
                add Solid(_urmnmAcc, xysize=(_urmnmS(112), _urmnmBar)) xpos _urmnmS(108) ypos (_urmnmExitY - _urmnmBar // 2)
                if idx == total - 1:
                    frame:
                        style 'urmk_frame'
                        xpos _urmnmS(140)
                        ypos _urmnmExitY
                        yanchor .5
                        background urmk_pill(urmk_colour('surface-2'), _urmnmS(8))
                        padding (_urmnmS(10), _urmnmS(4))
                        add urmk_word('story goes on', style='urmk_text', font=_urmnmMedium, size=urmnm_font_px(15, 12), color=_urmnmInk)

# Wave 5.3 Sandbox view by place (q4_sandbox panel a).
screen urmnm_sandbox_view(view_h):
    $ _urmnmS = urmk_px_cut
    $ _urmnmInk = urmk_colour('ink')
    $ _urmnmMuted = urmk_colour('ink-muted')
    $ _urmnmMedium = URMK_FONTS['medium']
    viewport:
        xfill True
        ysize view_h
        mousewheel True
        draggable True
        scrollbars 'vertical'
        vscrollbar_xsize urmk_px_cut(6)
        vscrollbar_base_bar urmk_pill(urmk_colour('track'), urmk_px_cut(3))
        vscrollbar_thumb urmk_pill(urmk_colour('thumb'), urmk_px_cut(3))
        vscrollbar_hover_thumb urmk_pill(urmk_colour('thumb-hover'), urmk_px_cut(3))
        vscrollbar_unscrollable 'hide'
        vbox:
            xoffset _urmnmS(24)
            spacing _urmnmS(16)
            null height _urmnmS(16)
            for _urmnmRowP in urmnm_sandbox_rows(3):
                hbox:
                    spacing _urmnmS(16)
                    for _urmnmP in _urmnmRowP:
                        frame:
                            style 'urmk_frame'
                            background urmk_pill(urmk_colour('surface-2'), _urmnmS(10))
                            padding (_urmnmS(16), _urmnmS(12))
                            xsize _urmnmS(360)
                            vbox:
                                spacing _urmnmS(6)
                                hbox:
                                    spacing _urmnmS(8)
                                    add urmk_word(urmnm_esc_text(_urmnmP.caption), style='urmk_text', font=_urmnmMedium, size=urmnm_font_px(18, 14), color=_urmnmInk, yalign=0.5)
                                    if _urmnmP.lines:
                                        add urmk_word(_urmnmP.lines, style='urmk_text', size=urmnm_font_px(14, 12), color=_urmnmMuted, yalign=0.5)
                                for _urmnmSc in _urmnmP.scenes:
                                    hbox:
                                        spacing _urmnmS(8)
                                        if _urmnmSc.need:
                                            use urmnm_chip(_urmnmSc.need, _urmnmSc.tone, (_urmnmSc.key if _urmnmSc.key and _urmnmSc.state == 'step' else None), faded=_urmnmP.faded)
                                        add urmk_word(urmnm_esc_text(_urmnmSc.words), style='urmk_text', size=urmnm_font_px(15, 12), color=(_urmnmMuted if _urmnmSc.state == 'locked' else _urmnmInk), yalign=0.5)
                                if not _urmnmP.scenes:
                                    add urmk_word('Visit anytime', style='urmk_text', italic=True, size=urmnm_font_px(15, 12), color=_urmnmMuted)
            null height _urmnmS(16)
