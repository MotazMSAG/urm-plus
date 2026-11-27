# The code view (game_fixes/18_code_view; the user's pick 2b): a
# full-height panel at the right, 16 in from the edges, so the game stays in
# view. Its title with the wrap button and close; what the blue edge marks;
# the lines with their numbers on the code's solid ground; how to scroll and
# close. Draws only while the story runs.

screen urmk_code_view(code, title, marked=(), note=None):
    zorder 200
    default _urmkvWrap = False
    default _urmkvX = ui.adjustment()
    if _urm_in_game():
        $ _urmkvRows = urmk_code_rows(code, marked)
        $ _urmkvB = urmk_back('window')
        $ _urmkvW = urmk_px(URMK_CODE_WIDTH)
        $ _urmkvH = config.screen_height - 2 * urmk_px(16)
        $ _urmkvGut = urmk_px(48)
        $ _urmkvRoom = _urmkvW - 2 * urmk_px(16) - _urmkvGut - urmk_px(14) - urmk_px(24)
        $ _urmkvBar = urmk_px(6)
        $ _urmkvInk = URMK_CODE_COLOURS
        key 'K_ESCAPE' action Function(urmk_code_close)
        key 'game_menu' action Function(urmk_code_close)
        use urmk_backdrop(Function(urmk_code_close))
        frame:
            style 'urmk_frame'
            background _urmkvB.image
            xalign 1.0
            xoffset -urmk_px(16)
            yalign 0.5
            left_margin -_urmkvB.left
            right_margin -_urmkvB.right
            top_margin -_urmkvB.top
            bottom_margin -_urmkvB.bottom
            left_padding _urmkvB.left
            right_padding _urmkvB.right
            top_padding _urmkvB.top
            bottom_padding _urmkvB.bottom
            fixed:
                xysize (_urmkvW, _urmkvH)
                # the panel takes its own clicks: none reaches the game behind
                button:
                    style 'urmk_button'
                    xfill True
                    yfill True
                    action NullAction()
                side 't c b':
                    vbox:
                        hbox:
                            ysize urmk_px(64)
                            spacing urmk_px(12)
                            null width urmk_px(12)
                            add urmk_word('', style='urmk_icon', color=urmk_colour('accent-ink'), yalign=0.5)
                            add urmk_word(title, style='urmk_m_medium', yalign=0.5, xmaximum=_urmkvW - urmk_px(180))
                        if note:
                            hbox:
                                spacing urmk_px(8)
                                xoffset urmk_px(24)
                                frame:
                                    style 'urmk_frame'
                                    background urmk_pill(urmk_colour('accent-ink'), urmk_px(3))
                                    yalign 0.5
                                    null width urmk_px(14) height urmk_px(14)
                                add urmk_word(note, style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5, xmaximum=_urmkvW - urmk_px(80))
                            null height urmk_px(12)
                    frame:
                        style 'urmk_frame'
                        background urmk_pill(_urmkvInk['ground'], urmk_px(10))
                        xmargin urmk_px(16)
                        ypadding urmk_px(4)
                        viewport:
                            mousewheel True
                            draggable True
                            xadjustment _urmkvX
                            yadjustment urmk_code_adj
                            scrollbars ('vertical' if _urmkvWrap else 'both')
                            # both bars are the view's own: a game's
                            # horizontal bar can have no height (FINDINGS)
                            scrollbar_ysize _urmkvBar
                            scrollbar_base_bar urmk_pill(_urmkvInk['bar'], urmk_px(3))
                            scrollbar_thumb urmk_pill(_urmkvInk['thumb'], urmk_px(3))
                            scrollbar_thumb_offset 0
                            scrollbar_unscrollable 'hide'
                            vscrollbar_xsize _urmkvBar
                            vscrollbar_base_bar urmk_pill(_urmkvInk['bar'], urmk_px(3))
                            vscrollbar_thumb urmk_pill(_urmkvInk['thumb'], urmk_px(3))
                            vscrollbar_thumb_offset 0
                            vscrollbar_unscrollable 'hide'
                            side_spacing urmk_px(4)
                            use urmk_later('lines'):
                                vbox:
                                    for _urmkvItem index _urmkvItem[0] in _urmkvRows[:urmk_code_room()]:
                                        $ _urmkvN, _urmkvLine, _urmkvOn = _urmkvItem
                                        frame:
                                            style 'urmk_frame'
                                            background (urmk_code_mark() if _urmkvOn else None)
                                            xminimum (_urmkvGut + urmk_px(14) + _urmkvRoom)
                                            yminimum urmk_px(URMK_CODE_SIZE[1])
                                            hbox:
                                                add urmk_word(('%d' % _urmkvN), style='urmk_code', color=(urmk_colour('accent-ink') if _urmkvOn else _urmkvInk['gutter']), min_width=_urmkvGut, text_align=1.0)
                                                null width urmk_px(14)
                                                if _urmkvWrap:
                                                    add urmk_word(_urmkvLine, style='urmk_code', xmaximum=_urmkvRoom)
                                                else:
                                                    add urmk_word(_urmkvLine, style='urmk_code', layout='nobreak')
                    hbox:
                        ysize urmk_px(56)
                        spacing urmk_px(8)
                        null width urmk_px(16)
                        add urmk_word('', style='urmk_icon', color=urmk_colour('ink-muted'), yalign=0.5)
                        add urmk_word('Wheel scrolls', style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
                        if not _urmkvWrap:
                            null width urmk_px(8)
                            add urmk_word('', style='urmk_icon', color=urmk_colour('ink-muted'), yalign=0.5)
                            add urmk_word('Shift + wheel for long lines', style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
                # the title's buttons: wrap, close
                hbox:
                    xalign 1.0
                    xoffset -urmk_px(16)
                    yoffset urmk_px(12)
                    spacing urmk_px(4)
                    use urmk_button('', ToggleScreenVariable('_urmkvWrap'), ('plain' if _urmkvWrap else 'quiet'), 'small', icon='')
                    use urmk_button('', Function(urmk_code_close), 'quiet', 'small', icon='')
                # Esc or right-click closes, at the foot's right
                hbox:
                    xalign 1.0
                    yalign 1.0
                    xoffset -urmk_px(24)
                    yoffset -urmk_px(12)
                    spacing urmk_px(8)
                    use urmk_chip('Esc')
                    add urmk_word('or', style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
                    use urmk_chip('Right-click')
                    add urmk_word('closes', style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
        # Shift + wheel: sideways (last, so it comes before the viewport)
        if not _urmkvWrap:
            add _URMKCodeSide(_urmkvX)
