# Quick access (92_quick in game_fixes): a slim tray of icon buttons. The
# URM+ button draws it under itself, in its own drag (_urm_under, 17_hub),
# so it moves with the button. It holds nothing of its own: a save keeps
# the scope of the screen shown.
screen urmq_tray():
    $ _urmqB = urmq_buttons()
    $ _urmqH = urmq_height()
    $ _urmqE = max(1, urmk_px(1))
    fixed:
        fit_first True
        xoffset urmq_pill_offset(len(_urmqB))
        # a hairline edge around the tray's glass surface
        frame:
            style 'urmk_frame'
            foreground urmk_ring(urmk_colour('glass-rim'), _urmqH // 2, _urmqE)
            ysize _urmqH
            padding (_urmqE, _urmqE)
            frame:
                style 'urmk_frame'
                background urmk_pill(urmk_colour('glass'), _urmqH // 2 - _urmqE)
                yfill True
                padding (urmq_px('pad') - _urmqE, urmq_px('pad') - _urmqE)
                hbox:
                    spacing urmq_px('space')
                    for _urmqN, _urmqI, _urmqL, _urmqA, _urmqR in _urmqB:
                        use urmq_one(_urmqN, _urmqI, _urmqL, _urmqA, _urmqR)
        # a middle click on a button of the tray is taken here (92_quick),
        # inside fixed: after frame: so hovering adds no vbox child or gap
        if urmq_pointed():
            key 'mouseup_2' action Function(urmq_middle)
        $ _urmqT = urmq_tip()
        if _urmqT:
            $ _urmqTX, _urmqTA, _urmqTO = urmq_tip_side()
            frame:
                style 'urmk_frame'
                xpos _urmqTX
                xanchor _urmqTA
                xoffset _urmqTO
                yalign 0.5
                use urmk_window('bubble', xa=0.0, pad=(12, 4)):
                    # one line: the tray's box is narrower than its words
                    text _urmqT style 'urmk_s' substitute False layout 'nobreak'

# One button: a thin icon, muted; pointed at, a soft pill and brighter;
# lit (on), the icon in the accent with a short accent line under it. A
# right click runs `right` (it never opens the game's menu).
screen urmq_one(name, icon, lit, action, right):
    $ _urmqS = urmq_px('button')
    $ _urmqLW, _urmqLH = URMQ['lit']
    button:
        style 'urmk_button'
        xysize (_urmqS, _urmqS)
        hover_background urmk_pill(urmk_colour('hover'), _urmqS // 2)
        action action
        alternate right
        hovered Function(urmq_redraw)
        unhovered Function(urmq_redraw)
        text icon style 'urmk_icon' size urmq_px('icon') color urmk_colour('accent-ink' if lit else 'ink-muted') hover_color urmk_colour('accent-ink' if lit else 'ink') align (0.5, 0.5)
        if lit:
            frame:
                style 'urmk_frame'
                background urmk_pill(urmk_colour('accent-ink'), max(1, urmk_px(_urmqLH)) // 2)
                xysize (urmk_px(_urmqLW), max(1, urmk_px(_urmqLH)))
                xalign 0.5
                yalign 1.0
