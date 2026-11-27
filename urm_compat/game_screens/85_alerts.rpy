# The alert banner, drawn with the kit (Glass edge: a window with an amber
# top edge, 32 px from the top). Not modal: a click on empty screen still
# moves the dialogue on, and it takes no keyboard focus of its own.

screen urmal_alert():
    zorder 1100
    default _urmalLeft = 15

    python:
        _urmalHead, _urmalRows, _urmalStopped, _urmalMarked = urmal_view()
        _urmalNames = _urmalMarked[:3]

    use urmk_window('window', edge='warn', y=32, width=960):
        vbox:
            xfill True
            fixed:
                ysize urmk_px(24)
                hbox:
                    yalign 0.5
                    spacing urmk_px(8)
                    text '' style 'urmk_icon' color urmk_tone_ink('warn') yalign 0.5
                    add urmk_word('MRM alert', style='urmk_s_medium', color=urmk_colour('ink-muted'), yalign=0.5)
                text ("Closes in %d s" % _urmalLeft) style 'urmk_s' color urmk_colour('ink-muted') xalign 1.0 yalign 0.5 substitute False
            null height urmk_px(8)
            text _urmalHead style 'urmk_l' substitute False
            for _urmalWhat, _urmalVerdict, _urmalTone in _urmalRows:
                null height urmk_px(8)
                hbox:
                    box_wrap True
                    spacing urmk_px(12)
                    text (_urmalWhat + u" –") style 'urmk_m' substitute False yalign 0.5
                    use urmk_chip(_urmalVerdict, _urmalTone)
            null height urmk_px(16)
            side 'c r':
                xfill True
                if _urmalStopped:
                    text "Skipping stopped." style 'urmk_m' color urmk_colour('ink-muted') yalign 0.5 substitute False
                else:
                    null
                # one row as drawn; each further name a row above it
                vbox:
                    spacing urmk_px(8)
                    for _urmalName in _urmalNames[:-1]:
                        hbox:
                            xalign 1.0
                            use urmk_button("Stop alerting for " + _urmi_safe(_urmalName), Function(urmal_stop, _urmalName), 'quiet')
                    hbox:
                        xalign 1.0
                        spacing urmk_px(8)
                        for _urmalName in _urmalNames[-1:]:
                            use urmk_button("Stop alerting for " + _urmi_safe(_urmalName), Function(urmal_stop, _urmalName), 'quiet')
                        use urmk_button("OK", Function(urmal_close), 'main')

    timer 1.0 repeat True action If(_urmalLeft > 1, SetScreenVariable('_urmalLeft', _urmalLeft - 1), Function(urmal_close))
