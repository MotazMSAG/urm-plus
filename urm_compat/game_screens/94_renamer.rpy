screen urmrn_settings(width):
    $ _urmrnSt = urmrn_state()
    $ _urmrnGap = 24
    $ _urmrnList = 316
    $ _urmrnForm = width - _urmrnList - _urmrnGap
    $ _urmrnSample = urmrn_preview()
    $ _urmrnIssue = urmrn_problem()
    $ _urmrnChoices = urmrn_candidates()
    hbox:
        spacing urmk_px(_urmrnGap)
        vbox:
            xsize urmk_px(_urmrnForm)
            spacing urmk_px(9)
            use urmrn_field('Character', _urmrnSt, 'source', _urmrnForm)
            if not _urmrnSt.editing and _urmrnChoices and _urmrnSt.source not in _urmrnChoices:
                hbox:
                    spacing urmk_px(6)
                    for _urmrnName index _urmrnName in _urmrnChoices[:3]:
                        use urmk_button(_urmrn_esc(_urmrnName), Function(urmrn_edit, _urmrnName), 'plain', 'small')
            use urmrn_field('New name', _urmrnSt, 'target', _urmrnForm)
            null height urmk_px(9)
            add urmk_word('Preview', style='urmk_m_medium', size=urmk_px(25 * urmk_look.text), color=urmk_colour('ink'))
            if _urmrnSample:
                use urmrn_example('Speaker', _urmrnSample, _urmrnForm, 'accent-ink')
                use urmrn_example('Dialogue', u'%s left a light on.' % _urmrnSample, _urmrnForm)
                use urmrn_example('Choice', u'Ask %s about the light' % _urmrnSample, _urmrnForm)
            else:
                add urmk_word('Enter a new name to preview it.', style='urmk_s', color=urmk_colour('ink-muted'))
            if _urmrnIssue:
                add urmk_word(_urmrnIssue, style='urmk_s', color=urmk_tone_ink('warn'))
            use urmk_divider(0, 0)
            hbox:
                xalign 1.0
                spacing urmk_px(8)
                use urmk_button('Cancel', Function(urmrn_cancel), 'plain', 'small')
                use urmk_button('Rename', Function(urmrn_put) if _urmrnIssue is None else None, 'main', 'small')
        vbox:
            xsize urmk_px(_urmrnList)
            spacing urmk_px(12)
            add urmk_word('Renamed in this game', style='urmk_m_medium', size=urmk_px(23 * urmk_look.text), color=urmk_colour('ink'))
            $ _urmrnRows = urmrn_list()
            if _urmrnRows:
                $ _urmrnStart = _urmrnSt.page * URMRN_PAGE
                for _urmrnPair index _urmrnPair[0] in _urmrnRows[_urmrnStart:_urmrnStart + URMRN_PAGE]:
                    $ _urmrnOld, _urmrnNew = _urmrnPair
                    use urmk_window('card', xa=0.0, width=_urmrnList, pad=(10, 8)):
                        vbox:
                            spacing urmk_px(4)
                            add urmk_word(_urmrn_esc(u'%s to %s' % (_urmrnOld, _urmrnNew)), style='urmk_s', size=urmk_px(21 * urmk_look.text), color=urmk_colour('ink'))
                            hbox:
                                spacing urmk_px(4)
                                use urmk_button('Edit', Function(urmrn_edit, _urmrnOld, _urmrnNew), 'plain', 'small')
                                use urmk_button('Restore', Function(urmrn_restore, _urmrnOld), 'quiet', 'small')
                if len(_urmrnRows) > URMRN_PAGE:
                    hbox:
                        spacing urmk_px(4)
                        use urmk_button('Previous', Function(urmrn_page, -1) if _urmrnStart else None, 'quiet', 'small')
                        use urmk_button('Next', Function(urmrn_page, 1) if _urmrnStart + URMRN_PAGE < len(_urmrnRows) else None, 'quiet', 'small')
            else:
                add urmk_word('No names changed yet', style='urmk_s', color=urmk_colour('ink-muted'))

screen urmrn_example(label, words, width, tone='ink'):
    $ _urmrnSize = urmk_px(23 * urmk_look.text)
    hbox:
        spacing urmk_px(12)
        fixed:
            xysize (urmk_px(128), _urmrnSize + urmk_px(7))
            add urmk_word(label, style='urmk_s', size=_urmrnSize, color=urmk_colour('ink-muted'))
        add urmk_word(_urmrn_esc(words), style='urmk_s', size=_urmrnSize, color=urmk_colour(tone), xmaximum=urmk_px(width - 140))

screen urmrn_field(label, state, name, width):
    $ _urmrnValue = FieldInputValue(state, name, default=(name == 'source'), returnable=False)
    vbox:
        spacing urmk_px(5)
        add urmk_word(label, style='urmk_s', size=urmk_px(20 * urmk_look.text), color=urmk_colour('ink-muted'))
        frame:
            style 'urmk_frame'
            xsize urmk_px(width)
            ysize urmk_px(45)
            background urmk_pill(urmk_colour('surface'), urmk_px(7))
            padding (urmk_px(10), urmk_px(5))
            fixed:
                button:
                    style 'urmk_button'
                    xfill True
                    yfill True
                    action _urmrnValue.Enable()
                input id name value _urmrnValue length 56 style 'urmk_m' size urmk_px(23 * urmk_look.text) color urmk_colour('ink') pixel_width urmk_px(width - 25) yalign .5
