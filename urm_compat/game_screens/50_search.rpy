# Our own Search page (game_fixes/50_search, the page block), drawn with
# the kit (Glass edge): the quick sheet on the right edge (Alt+F) and the
# full page it opens. The user's picks: research/search3_q.png and
# search3_f1.png. Screens hold plain words and names only (urmcp_*_rows):
# a game object in a screen's scope would go into a save.

# A pill: a filter, its count only when it has results.
screen urmcp_pill(words, pill, count=None):
    $ _urmcpOn = urmcp_state_pill() == pill
    button:
        style 'urmk_button'
        background urmcp_ground('pill-on' if _urmcpOn else 'pill')
        hover_background urmcp_ground('pill-on' if _urmcpOn else 'pill', True)
        ysize urmk_px(40)
        xpadding urmk_px(16)
        action Function(urmcp_pill, pill)
        hbox:
            yalign 0.5
            spacing urmk_px(8)
            add urmk_word(words, style='urmk_s_medium', color=urmk_colour('on-accent' if _urmcpOn else 'ink'), yalign=0.5)
            if count:
                add urmk_word(('%d' % count), style='urmk_s', color=urmk_colour('on-accent' if _urmcpOn else 'ink-muted'), yalign=0.5)

# A wide button of the kit's grounds: the full page's menu and its DO list.
# on False: drawn greyed, nothing happens (it waits for the shared layer).
screen urmcp_wide(words, action, kind='plain', on=True):
    button:
        style 'urmk_button'
        background urmk_back(kind).image
        hover_background urmk_back(kind, hover=True).image
        xfill True
        ysize urmk_px(48)
        xpadding urmk_px(24)
        action (action if on else None)
        insensitive_background urmk_back('plain').image
        add urmk_word(words, style='urmk_m', color=urmk_colour(('on-accent' if kind == 'main' else 'ink') if on else 'disabled'), yalign=0.5)

# A button with its key beside its words: Set to 500 [Enter], Cancel [Esc].
screen urmcp_keyed(words, key, action, kind='plain'):
    button:
        style 'urmk_button'
        background urmk_back(kind).image
        hover_background urmk_back(kind, hover=True).image
        ysize urmk_px(48)
        xpadding urmk_px(16)
        action action
        hbox:
            yalign 0.5
            spacing urmk_px(12)
            add urmk_word(words, style='urmk_m_medium', color=urmk_colour('on-accent' if kind == 'main' else 'ink'), yalign=0.5)
            frame:
                style 'urmk_frame'
                background urmcp_ground('key-on' if kind == 'main' else 'key')
                ysize urmk_px(32)
                xpadding urmk_px(10)
                add urmk_word(key, style='urmk_s_medium', color=urmk_colour('on-accent' if kind == 'main' else 'ink-muted'), yalign=0.5)

# The full page from the quick sheet: the expand icon (Material's
# open_in_full: two arrows out from the middle, to the corners), what it
# does said beside it while pointed at.
screen urmcp_expand():
    $ _urmcpTip = GetTooltip()
    hbox:
        spacing urmk_px(8)
        if _urmcpTip:
            use urmk_window('bubble', xa=0.0, ya=0.5, pad=(12, 4)):
                add urmk_word(_urmcpTip, style='urmk_s', yalign=0.5)
        button:
            style 'urmk_button'
            background urmk_back('main').image
            hover_background urmk_back('main', hover=True).image
            xysize (urmk_px(48), urmk_px(48))
            action Function(urmcp_full)
            tooltip u'Open full page'
            add urmk_word(u'\uf1ce', style='urmk_icon', color=urmk_colour('on-accent'), align=(0.5, 0.5))

# A yes/no value: one click flips it.
screen urmcp_switch(on, action):
    button:
        style 'urmk_button'
        action action
        use urmk_switch(on)

# The box a value is changed in, as drawn (2a): filled with the value, -
# and + for a number, the values the game checks for as chips (only here),
# Set (Enter) and Cancel (Esc).
screen urmcp_edit(path, kind, width):
    $ _urmcpChecks = urmcp_checks(path)
    vbox:
        spacing urmk_px(16)
        xsize width
        hbox:
            spacing urmk_px(8)
            frame:
                style 'urmk_frame'
                background urmcp_ground('field-on')
                xsize (width - (urmk_px(112) if kind in ('int', 'float') else 0))
                ysize urmk_px(64)
                padding (urmk_px(2), urmk_px(2))
                frame:
                    style 'urmk_frame'
                    background urmcp_ground('field')
                    xfill True
                    yfill True
                    xpadding urmk_px(18)
                    input value urmcp_edit_box style 'urmk_l' font URMK_FONTS['regular'] color urmk_colour('ink') yalign 0.5 pixel_width (width - urmk_px(160)) allow (('0123456789-.' if kind in ('int', 'float') else None))
            if kind in ('int', 'float'):
                hbox:
                    yalign 0.5
                    spacing urmk_px(8)
                    use urmk_button('', Function(urmcp_step, -1), 'plain', 'big', u'\ue15b')
                    use urmk_button('', Function(urmcp_step, 1), 'plain', 'big', u'\ue145')
        if urmcp_edit_error():
            add urmk_word(urmcp_edit_error(), style='urmk_s', color=urmk_tone_ink('loss'))
        if _urmcpChecks:
            hbox:
                box_wrap True
                spacing urmk_px(8)
                add urmk_word("The game checks for:", style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
                for _urmcpItem index _urmcpItem[0] in _urmcpChecks:
                    $ _urmcpW, _urmcpV, _urmcpT = _urmcpItem
                    button:
                        style 'urmk_button'
                        action Function(urmcp_fill, _urmcpV)
                        use urmk_chip(_urmcpW, _urmcpT)
        hbox:
            spacing urmk_px(16)
            use urmcp_keyed(urmcp_set_words(path), u'Enter', Function(urmcp_commit), 'main')
            use urmcp_keyed(u'Cancel', u'Esc', Function(urmcp_close), 'plain')

# A box to type in, in the look of the edit box.
screen urmcp_new_field(box, width):
    frame:
        style 'urmk_frame'
        background urmcp_ground('field-on')
        xsize width
        ysize urmk_px(64)
        padding (urmk_px(2), urmk_px(2))
        frame:
            style 'urmk_frame'
            background urmcp_ground('field')
            xfill True
            yfill True
            xpadding urmk_px(18)
            input value box style 'urmk_l' font URMK_FONTS['regular'] color urmk_colour('ink') yalign 0.5 pixel_width (width - urmk_px(40))

# The form of a new variable: its name, its value (what it will be said
# under the box), Create (Enter) and Cancel (Esc).
screen urmcp_new(width):
    frame:
        style 'urmk_frame'
        background urmk_back('plain').image
        xsize width
        xpadding urmk_px(24)
        ypadding urmk_px(16)
        vbox:
            spacing urmk_px(12)
            add urmk_word("New variable", style='urmk_m_medium')
            add urmk_word("Name", style='urmk_s', color=urmk_colour('ink-muted'))
            use urmcp_new_field(urmcp_new_name_box, width - urmk_px(48))
            add urmk_word("Value", style='urmk_s', color=urmk_colour('ink-muted'))
            use urmcp_new_field(urmcp_new_text_box, width - urmk_px(48))
            add urmk_word(urmcp_new_words(), style='urmk_s', color=urmk_colour('ink-muted'))
            if urmcp_new_error():
                add urmk_word(urmcp_new_error(), style='urmk_s', color=urmk_tone_ink('loss'))
            hbox:
                spacing urmk_px(16)
                use urmcp_keyed(u'Create', u'Enter', Function(urmcp_new_commit), 'main')
                use urmcp_keyed(u'Cancel', u'Esc', Function(urmcp_close), 'plain')

# Delete a variable: the button, then one question in red words with
# Delete and Keep it. Drawn only for a name that may go (urmcp_can_delete).
# wide: the full page's DO list button.
screen urmcp_delete(path, width, wide=False):
    if urmcp_can_delete(path):
        if urmcp_deleting() == path:
            vbox:
                spacing urmk_px(12)
                add urmk_word(urmcp_delete_words(path), style='urmk_s', color=urmk_tone_ink('loss'), xmaximum=width)
                hbox:
                    spacing urmk_px(12)
                    use urmk_button(u'Delete', Function(urmcp_delete_yes), 'plain', 'small', u'')
                    use urmk_button(u'Keep it', Function(urmcp_delete_no), 'quiet', 'small')
        elif wide:
            use urmcp_wide(u'Delete variable', Function(urmcp_delete, path), 'plain')
        else:
            use urmk_button(u'Delete variable', Function(urmcp_delete, path), 'quiet', 'small', u'')

# The value of a row: a box to click (a number or words), a switch, or
# what a list or an object holds.
screen urmcp_value(path, kind, words, width):
    if kind == 'bool':
        hbox:
            spacing urmk_px(8)
            if urmcp_undo_for(path):
                use urmk_button(u'Undo', Function(urmcp_undo), 'quiet', 'small')
            use urmcp_switch((words == 'true'), Function(urmcp_switch, path))
    elif kind in ('int', 'float', 'text', 'none'):
        button:
            style 'urmk_button'
            background urmcp_ground('value')
            hover_background urmcp_ground('value', True)
            ysize urmk_px(40)
            xpadding urmk_px(12)
            action Function(urmcp_edit, path)
            add urmk_word(urmcp_fit(words, 'urmk_m_medium', width), style='urmk_m_medium', color=urmk_colour('ink-muted' if kind == 'none' else ('frozen-value' if urmcp_frozen(path) else 'ink')), yalign=0.5)
    elif kind in ('dict', 'object'):
        add urmk_word(urmcp_fit(words, 'urmk_s', width), style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
    else:
        add urmk_word(urmcp_fit(words, 'urmk_s', width), style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)

# A name: its owners small and muted before it (mc > money).
screen urmcp_name(owners, name, width, fold=None):
    hbox:
        yalign 0.5
        spacing urmk_px(8)
        if fold is not None:
            add urmk_word((u'\ue5cf' if fold else u'\ue5cc'), style='urmk_icon', color=urmk_colour('ink-muted'), yalign=0.5)
        if owners:
            add urmk_word(urmcp_fit(owners + u' \u203a', 'urmk_s', width // 3), style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
        add urmk_word(urmcp_fit(name, 'urmk_m', width - (width // 3 if owners else 0) - (urmk_px(32) if fold is not None else 0)), style='urmk_m', yalign=0.5)

# One variable on the quick sheet: the name with its note under it, the
# value at the right. Selected: where the story checks it; editing: the box.
screen urmcp_sheet_var(row, width):
    $ _urmcpPath, _urmcpOwners, _urmcpName, _urmcpKind, _urmcpWords, _urmcpNote, _urmcpFold = row
    $ _urmcpEditing = urmcp_editing() == _urmcpPath
    button:
        style 'urmk_button'
        background urmk_back('plain').image
        hover_background urmk_back('plain', hover=not _urmcpEditing).image
        xsize width
        xpadding urmk_px(24)
        ypadding urmk_px(16)
        action (Function(urmcp_fold, _urmcpPath) if _urmcpFold is not None else Function(urmcp_select, _urmcpPath))
        if _urmcpEditing:
            vbox:
                spacing urmk_px(16)
                side 'c r':
                    xfill True
                    use urmcp_name(_urmcpOwners, _urmcpName, width - urmk_px(200))
                    add urmk_word("editing", style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
                use urmcp_edit(_urmcpPath, _urmcpKind, width - urmk_px(48))
        else:
            $ _urmcpNameW = width - urmk_px(262)
            $ _urmcpValW = urmk_px(170)
            vbox:
                spacing urmk_px(8)
                side 'c r':
                    xfill True
                    vbox:
                        spacing urmk_px(8)
                        button:
                            style 'urmk_button'
                            hover_background urmk_pill(urmk_colour('hover'), urmk_px(8))
                            xpadding urmk_px(6)
                            ypadding urmk_px(2)
                            action (Function(urmcp_fold, _urmcpPath) if _urmcpFold is not None else (Function(urmcp_open_sheet, _urmcpPath) if urmcp_can_sheet() else Function(urmcp_select, _urmcpPath)))
                            if _urmcpFold is None and not _urmcpOwners:
                                add urmk_word(urmcp_fit(_urmcpName, 'urmk_m', _urmcpNameW), style='urmk_m', yalign=0.5)
                            else:
                                hbox:
                                    yalign 0.5
                                    spacing urmk_px(8)
                                    if _urmcpFold is not None:
                                        add urmk_word((u'\ue5cf' if _urmcpFold else u'\ue5cc'), style='urmk_icon', color=urmk_colour('ink-muted'), yalign=0.5)
                                    if _urmcpOwners:
                                        add urmk_word(urmcp_fit(_urmcpOwners + u' \u203a', 'urmk_s', _urmcpNameW // 3), style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
                                    add urmk_word(urmcp_fit(_urmcpName, 'urmk_m', _urmcpNameW - (_urmcpNameW // 3 if _urmcpOwners else 0) - (urmk_px(32) if _urmcpFold is not None else 0)), style='urmk_m', yalign=0.5)
                        if _urmcpNote:
                            frame:
                                style 'urmk_frame'
                                background urmk_chip_bg(_urmcpNote[1])
                                yminimum urmk_px(URMK_CHIP[0])
                                ypadding urmk_chip_pad()
                                xpadding urmk_px(URMK_CHIP[1])
                                add urmk_word(_urmcpNote[0], style='urmk_s_medium', color=urmk_chip_ink(_urmcpNote[1]), yalign=0.5)
                    if _urmcpKind == 'bool':
                        hbox:
                            yalign 0.5
                            use urmcp_value(_urmcpPath, _urmcpKind, _urmcpWords, _urmcpValW)
                    elif _urmcpKind in ('int', 'float', 'text', 'none'):
                        button:
                            style 'urmk_button'
                            background urmcp_ground('value')
                            hover_background urmcp_ground('value', True)
                            ysize urmk_px(40)
                            xpadding urmk_px(12)
                            yalign 0.5
                            action Function(urmcp_edit, _urmcpPath)
                            add urmk_word(urmcp_fit(_urmcpWords, 'urmk_m_medium', _urmcpValW), style='urmk_m_medium', color=urmk_colour('ink-muted' if _urmcpKind == 'none' else ('frozen-value' if urmcp_frozen(_urmcpPath) else 'ink')), yalign=0.5)
                    else:
                        add urmk_word(urmcp_fit(_urmcpWords, 'urmk_s', _urmcpValW), style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
                if urmcp_selected() == _urmcpPath:
                    $ _urmcpAbout = urmcp_about(_urmcpPath)
                    if _urmcpAbout:
                        add urmk_word(_urmcpAbout, style='urmk_s', color=urmk_colour('ink-muted'))
                    use urmcp_delete(_urmcpPath, width - urmk_px(48))

# A line, a choice, a label or a flag on the quick sheet.
screen urmcp_sheet_text(key, words, note, width, quoted=True):
    button:
        style 'urmk_button'
        background urmk_back('plain').image
        hover_background urmk_back('plain', hover=True).image
        xsize width
        xpadding urmk_px(24)
        ypadding urmk_px(16)
        action Function(urmcp_select, key)
        vbox:
            spacing urmk_px(4)
            add urmk_word(urmcp_fit((u'\u201c%s\u201d' % words) if quoted else words, 'urmk_m', width - urmk_px(48)), style='urmk_m')
            add urmk_word(note, style='urmk_s', color=urmk_colour('ink-muted'))
    if quoted and urmcp_selected() == key:
        use urmcp_replay_action(key)

screen urmcp_replay_action(key):
    $ _urmcpReplay = urmcp_replay_offer(key)
    if _urmcpReplay:
        use urmk_menu_row(u'Replay this scene', u'\ue042', Function(_urm_replay_open, _urmcpReplay))

# The engine's names: one folded group, last.
screen urmcp_engine_row(width, count):
    button:
        style 'urmk_button'
        background None
        hover_background urmk_back('quiet', hover=True).image
        xsize width
        xpadding urmk_px(24)
        ysize urmk_px(56)
        action Function(urmcp_engine_fold)
        side 'c r':
            yalign 0.5
            xfill True
            hbox:
                spacing urmk_px(8)
                add urmk_word((u'\ue5cf' if urmcp_engine_open() else u'\ue5cc'), style='urmk_icon', color=urmk_colour('ink-muted'), yalign=0.5)
                add urmk_word("Engine and game internals", style='urmk_m', yalign=0.5)
                add urmk_word(('(%d)' % count), style='urmk_m', color=urmk_colour('ink-muted'), yalign=0.5)
            if not urmcp_engine_open():
                add urmk_word(urmcp_fit(u'e.g. ' + urmcp_engine_hint(), 'urmk_s', width // 3), style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
            else:
                null

# "Changed since": which moment, and a mark of your own.
screen urmcp_since():
    hbox:
        box_wrap True
        spacing urmk_px(8)
        add urmk_word("Since", style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
        use urmk_choices([(_urmcpW, Function(urmcp_since, _urmcpK), urmcp_state_since() == _urmcpK)
                          for _urmcpK, _urmcpW, _urmcpThere in urmcp_since_words()])
        use urmk_button(u'Mark now', Function(urmcp_mark), 'quiet', 'small')

# The rows of the quick sheet for the pill picked.
screen urmcp_sheet_rows(width):
    $ _urmcpPill = urmcp_state_pill()
    $ _urmcpCounts = urmcp_counts()
    vbox:
        spacing urmk_px(16)
        if urmcp_creating():
            use urmcp_new(width)
        if _urmcpPill == 'changed':
            use urmcp_since()
            for _urmcpRow index _urmcpRow[0] in urmcp_var_rows('changed'):
                use urmcp_sheet_var(_urmcpRow, width)
            if not _urmcpCounts.get('changed') and not urmcp_reading():
                add urmk_word(urmcp_empty_words(), style='urmk_s', color=urmk_colour('ink-muted'))
        else:
            if _urmcpPill in ('all', 'vars'):
                for _urmcpRow index _urmcpRow[0] in urmcp_var_rows('vars'):
                    use urmcp_sheet_var(_urmcpRow, width)
            if _urmcpPill in ('all', 'flags'):
                for _urmcpItem index _urmcpItem[0] in urmcp_flag_rows():
                    $ _urmcpKey, _urmcpWords, _urmcpNote = _urmcpItem
                    use urmcp_sheet_text(_urmcpKey, _urmcpWords, u'Flag \u00b7 ' + _urmcpNote, width, False)
            if _urmcpPill in ('all', 'choices'):
                for _urmcpItem index _urmcpItem[0] in urmcp_line_rows('choices'):
                    $ _urmcpKey, _urmcpWords, _urmcpNote = _urmcpItem
                    use urmcp_sheet_text(_urmcpKey, _urmcpWords, _urmcpNote, width)
            if _urmcpPill in ('all', 'lines'):
                for _urmcpItem index _urmcpItem[0] in urmcp_line_rows('lines'):
                    $ _urmcpKey, _urmcpWords, _urmcpNote = _urmcpItem
                    use urmcp_sheet_text(_urmcpKey, _urmcpWords, _urmcpNote, width)
            if _urmcpPill == 'labels':
                for _urmcpItem index _urmcpItem[0] in urmcp_label_rows():
                    $ _urmcpKey, _urmcpWords, _urmcpNote = _urmcpItem
                    use urmcp_sheet_text(_urmcpKey, _urmcpWords, _urmcpNote, width, False)
            if _urmcpPill in ('all', 'vars') and _urmcpCounts.get('engine'):
                use urmcp_engine_row(width, _urmcpCounts['engine'])
            if _urmcpPill == 'engine' or (_urmcpPill in ('all', 'vars') and urmcp_engine_open()):
                for _urmcpRow index _urmcpRow[0] in urmcp_var_rows('engine'):
                    use urmcp_sheet_var(_urmcpRow, width)
            if urmcp_nothing():
                add urmk_word(urmcp_empty_words(), style='urmk_s', color=urmk_colour('ink-muted'))

# The search box: the query, and how many were found.
screen urmcp_field(width):
    frame:
        style 'urmk_frame'
        background urmk_back('plain').image
        xsize width
        ysize urmk_px(72)
        xpadding urmk_px(24)
        side 'l c r':
            yalign 0.5
            xfill True
            add urmk_word(u'\ue8b6', style='urmk_icon', size=urmk_px(32), color=urmk_colour('ink-muted'), yalign=0.5)
            frame:
                style 'urmk_frame'
                xpadding urmk_px(16)
                yalign 0.5
                if urmcp_editing() is None and not urmcp_creating():
                    input value urmcp_query_box style 'urmk_l' font URMK_FONTS['regular'] color urmk_colour('ink') pixel_width (width - urmk_px(240))
                else:
                    add urmk_word(urmcp_fit(urmcp_state_query(), 'urmk_l', width - urmk_px(240)), style='urmk_l', font=URMK_FONTS['regular'])
            if not urmcp_state_empty():
                add urmk_word((u'Searching\u2026' if urmcp_reading() else u'%d found' % urmcp_found()), style='urmk_m', color=urmk_colour('ink-muted'), yalign=0.5)
            else:
                null

# The quick sheet (search3_q): a slim sheet on the right edge.
screen urmcp_sheet():
    modal True
    zorder 1050
    key 'K_ESCAPE' action Function(urmcp_close)
    key 'alt_K_f' action Function(urmcp_toggle)
    # its catalog or overflow search runs silently via _URMKWorkerPump (0 ms screen eval)
    if urmcp_pumping():
        add urmk_worker_pump(urmcp_pumping)
    $ _urmcpW = urmk_px(720)
    $ _urmcpIn = _urmcpW - urmk_px(32)
    $ _urmcpCounts = urmcp_counts()
    # a click beside the sheet closes it; scrolling outside never rolls dialogue
    use urmk_backdrop(Function(urmcp_close))
    # clicks and scrolling inside the sheet (gaps, header, footer) stay inside it
    viewport:
        mousewheel True
        xalign 1.0
        xoffset -urmk_px(16)
        yalign 0.5
        xysize (_urmcpW, config.screen_height - urmk_px(32))
        button:
            style 'urmk_button'
            xfill True
            yfill True
            action NullAction()
    use urmk_window('window', xa=1.0, ya=0.5, x=-16, width=720, pad=(16, 16)):
        side 't c b':
            ysize (config.screen_height - urmk_px(80))
            spacing urmk_px(16)
            vbox:
                spacing urmk_px(16)
                use urmcp_field(_urmcpIn)
                hbox:
                    box_wrap True
                    spacing urmk_px(8)
                    box_wrap_spacing urmk_px(8)
                    use urmcp_pill(u'Everything', 'all')
                    use urmcp_pill(u'Variables', 'vars', _urmcpCounts.get('vars'))
                    use urmcp_pill(u'Lines', 'lines', _urmcpCounts.get('lines'))
                    use urmcp_pill(u'Choices', 'choices', _urmcpCounts.get('choices'))
                    use urmcp_pill(u'Flags', 'flags', _urmcpCounts.get('flags'))
                    use urmcp_pill(u'Changed', 'changed', _urmcpCounts.get('changed'))
                    if urmcp_more() or urmcp_state_pill() in ('labels', 'engine'):
                        use urmcp_pill(u'Labels', 'labels', _urmcpCounts.get('labels'))
                        use urmcp_pill(u'Engine', 'engine', _urmcpCounts.get('engine'))
                    else:
                        button:
                            style 'urmk_button'
                            background urmcp_ground('pill')
                            hover_background urmcp_ground('pill', True)
                            ysize urmk_px(40)
                            xpadding urmk_px(16)
                            action Function(urmcp_show_more)
                            add urmk_word(u'\ue5d3', style='urmk_icon', color=urmk_colour('ink'), yalign=0.5)
                    use urmk_button(u'New variable', Function(urmcp_new_open), 'quiet', 'small', u'\ue145')
            viewport:
                id 'urmcp_sheet_rows'
                yadjustment urmcp_rows_adj
                mousewheel True
                draggable True
                xsize _urmcpIn
                if urmcp_reading():
                    use urmk_later('rows'):
                        use urmcp_sheet_rows(_urmcpIn)
                else:
                    use urmcp_sheet_rows(_urmcpIn)
            side 'c r':
                xfill True
                spacing urmk_px(16)
                add urmk_word("Typos forgiven. Use \u201cquotes\u201d for exact only.", style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
                use urmcp_expand()

# One row of the full page: name, value, what it matters for, in one line.
screen urmcp_page_var(row, cols):
    $ _urmcpPath, _urmcpOwners, _urmcpName, _urmcpKind, _urmcpWords, _urmcpNote, _urmcpFold = row
    $ _urmcpEditing = urmcp_editing() == _urmcpPath
    $ _urmcpOn = urmcp_selected() == _urmcpPath
    button:
        style 'urmk_button'
        background (urmk_back('plain').image if (_urmcpOn or _urmcpEditing) else None)
        hover_background (urmk_back('plain').image if (_urmcpOn or _urmcpEditing) else urmk_back('quiet', hover=True).image)
        xsize cols[3]
        xpadding urmk_px(24)
        yminimum urmk_px(64)
        action (Function(urmcp_fold, _urmcpPath) if _urmcpFold is not None else Function(urmcp_select, _urmcpPath))
        if _urmcpEditing:
            vbox:
                spacing urmk_px(16)
                null height urmk_px(4)
                use urmcp_name(_urmcpOwners, _urmcpName, cols[0])
                use urmcp_edit(_urmcpPath, _urmcpKind, cols[3] - urmk_px(48))
        else:
            hbox:
                yalign 0.5
                fixed:
                    xsize cols[0]
                    ysize urmk_px(64)
                    button:
                        style 'urmk_button'
                        yalign 0.5
                        hover_background urmk_pill(urmk_colour('hover'), urmk_px(8))
                        xpadding urmk_px(6)
                        ypadding urmk_px(2)
                        action (Function(urmcp_fold, _urmcpPath) if _urmcpFold is not None else (Function(urmcp_open_sheet, _urmcpPath) if urmcp_can_sheet() else Function(urmcp_select, _urmcpPath)))
                        use urmcp_name(_urmcpOwners, _urmcpName, cols[0] - urmk_px(28), _urmcpFold)
                fixed:
                    xsize cols[1]
                    ysize urmk_px(64)
                    hbox:
                        yalign 0.5
                        use urmcp_value(_urmcpPath, _urmcpKind, _urmcpWords, cols[1] - urmk_px(40))
                fixed:
                    xsize cols[2]
                    ysize urmk_px(64)
                    if _urmcpNote:
                        hbox:
                            yalign 0.5
                            use urmk_chip(urmcp_fit(_urmcpNote[0], 'urmk_s_medium', cols[2] - urmk_px(40)), _urmcpNote[1])

# A line, a choice, a label or a flag on the full page.
screen urmcp_page_text(key, words, note, cols, quoted=True):
    $ _urmcpOn = urmcp_selected() == key
    button:
        style 'urmk_button'
        background (urmk_back('plain').image if _urmcpOn else None)
        hover_background (urmk_back('plain').image if _urmcpOn else urmk_back('quiet', hover=True).image)
        xsize cols[3]
        xpadding urmk_px(24)
        ysize urmk_px(64)
        action Function(urmcp_select, key)
        hbox:
            yalign 0.5
            fixed:
                xsize (cols[0] + cols[1])
                ysize urmk_px(64)
                add urmk_word(urmcp_fit((u'\u201c%s\u201d' % words) if quoted else words, 'urmk_m', cols[0] + cols[1] - urmk_px(24)), style='urmk_m', yalign=0.5)
            fixed:
                xsize cols[2]
                ysize urmk_px(64)
                add urmk_word(urmcp_fit(note, 'urmk_s', cols[2] - urmk_px(16)), style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)

screen urmcp_page_rows(cols):
    $ _urmcpPill = urmcp_state_pill()
    $ _urmcpCounts = urmcp_counts()
    vbox:
        spacing urmk_px(4)
        if urmcp_creating():
            use urmcp_new(cols[3])
        if _urmcpPill == 'changed':
            for _urmcpRow index _urmcpRow[0] in urmcp_var_rows('changed'):
                use urmcp_page_var(_urmcpRow, cols)
        else:
            if _urmcpPill in ('all', 'vars'):
                for _urmcpRow index _urmcpRow[0] in urmcp_var_rows('vars'):
                    use urmcp_page_var(_urmcpRow, cols)
            if _urmcpPill in ('all', 'flags'):
                for _urmcpItem index _urmcpItem[0] in urmcp_flag_rows():
                    $ _urmcpKey, _urmcpWords, _urmcpNote = _urmcpItem
                    use urmcp_page_text(_urmcpKey, _urmcpWords, u'Flag \u00b7 ' + _urmcpNote, cols, False)
            if _urmcpPill in ('all', 'choices'):
                for _urmcpItem index _urmcpItem[0] in urmcp_line_rows('choices'):
                    $ _urmcpKey, _urmcpWords, _urmcpNote = _urmcpItem
                    use urmcp_page_text(_urmcpKey, _urmcpWords, _urmcpNote, cols)
            if _urmcpPill in ('all', 'lines'):
                for _urmcpItem index _urmcpItem[0] in urmcp_line_rows('lines'):
                    $ _urmcpKey, _urmcpWords, _urmcpNote = _urmcpItem
                    use urmcp_page_text(_urmcpKey, _urmcpWords, _urmcpNote, cols)
            if _urmcpPill == 'labels':
                for _urmcpItem index _urmcpItem[0] in urmcp_label_rows():
                    $ _urmcpKey, _urmcpWords, _urmcpNote = _urmcpItem
                    use urmcp_page_text(_urmcpKey, _urmcpWords, _urmcpNote, cols, False)
            if _urmcpPill in ('all', 'vars') and _urmcpCounts.get('engine'):
                use urmcp_engine_row(cols[3], _urmcpCounts['engine'])
            if _urmcpPill == 'engine' or (_urmcpPill in ('all', 'vars') and urmcp_engine_open()):
                for _urmcpRow index _urmcpRow[0] in urmcp_var_rows('engine'):
                    use urmcp_page_var(_urmcpRow, cols)
        if urmcp_nothing():
            add urmk_word(urmcp_empty_words(), style='urmk_s', color=urmk_colour('ink-muted'), xoffset=urmk_px(24))

# The Remembered page (the user's 3b, drawn as B2): three groups, each a
# card with its own edge (Frozen ice blue, Watching violet, Ignored for
# paths grey and dashed), tint, icon, count and a line on what it means. A
# row: the name, its value as a chip (a click edits it, as on Find: the
# same box, the same switch), and Unfreeze, Freeze or Stop ignoring.

# The value of a row on the Remembered page: the chip in its group's
# colours; it opens the same box (or flips the same switch) as on Find.
screen urmcp_kept_value(path, kind, words, frozen, dim, width):
    $ _urmcpInk = 'frozen-value' if frozen else ('ignored-dim' if dim else 'ink')
    hbox:
        spacing urmk_px(8)
        yalign 0.5
        if kind == 'bool' and urmcp_undo_for(path):
            use urmk_button(u'Undo', Function(urmcp_undo), 'quiet', 'small')
        button:
            style 'urmk_button'
            background (urmk_pill(urmk_colour('frozen-bg'), urmk_px(8)) if frozen else urmcp_ground('value'))
            hover_background (urmk_pill(_urmcp_veil('frozen-bg'), urmk_px(8)) if frozen else urmcp_ground('value', True))
            ysize urmk_px(40)
            xpadding urmk_px(12)
            action (Function(urmcp_switch, path) if kind == 'bool' else (Function(urmcp_edit, path) if kind in ('int', 'float', 'text', 'none') else Function(urmcp_select, path)))
            add urmk_word(urmcp_fit(words, 'urmk_m_medium', width), style='urmk_m_medium', color=urmk_colour(_urmcpInk), yalign=0.5)

# A row's button: Unfreeze filled ice blue, Freeze outlined, Stop ignoring
# grey; Freeze greyed for what cannot be frozen.
screen urmcp_kept_button(group, path, frozen, can):
    if group == 'ignored':
        button:
            style 'urmk_button'
            background urmk_pill(urmk_colour('ignored-bg'), urmk_px(20))
            hover_background urmk_pill(_urmcp_veil('ignored-bg'), urmk_px(20))
            ysize urmk_px(40)
            xpadding urmk_px(16)
            action Function(urmcp_unignore, path)
            add urmk_word(u'Stop ignoring', style='urmk_s_medium', color=urmk_colour('ignored-button'), yalign=0.5)
    else:
        button:
            style 'urmk_button'
            background (urmk_pill(urmk_colour('frozen-ink'), urmk_px(20)) if frozen else urmk_ring(urmk_colour('frozen-line'), urmk_px(20), max(1, urmk_px(1))))
            hover_background (urmk_pill(_urmcp_veil('frozen-ink'), urmk_px(20)) if frozen else urmk_pill(urmk_colour('frozen-bg'), urmk_px(20)))
            ysize urmk_px(40)
            xpadding urmk_px(16)
            action (Function(urmcp_freeze, path) if (frozen or can) else None)
            insensitive_background urmk_pill(urmk_colour('surface-2'), urmk_px(20))
            hbox:
                spacing urmk_px(8)
                yalign 0.5
                add urmk_word(u'\ueb3b', style='urmk_icon', size=urmk_px(20), color=urmk_colour('frozen-on' if frozen else ('frozen-on-glass' if can else 'disabled')), yalign=0.5)
                add urmk_word((u'Unfreeze' if frozen else u'Freeze'), style='urmk_s_medium', color=urmk_colour('frozen-on' if frozen else ('frozen-on-glass' if can else 'disabled')), yalign=0.5)

screen urmcp_kept_row(group, row, width):
    $ _urmcpPath, _urmcpOwners, _urmcpName, _urmcpKind, _urmcpWords, _urmcpFrozen, _urmcpCan = row
    $ _urmcpOn = urmcp_selected() == _urmcpPath
    $ _urmcpDim = group == 'ignored'
    if urmcp_editing() == _urmcpPath:
        frame:
            style 'urmk_frame'
            background urmk_pill(urmk_colour('row-on'), urmk_px(10))
            xsize width
            xpadding urmk_px(16)
            ypadding urmk_px(12)
            vbox:
                spacing urmk_px(16)
                use urmcp_name(_urmcpOwners, _urmcpName, width - urmk_px(32))
                use urmcp_edit(_urmcpPath, _urmcpKind, width - urmk_px(32))
    else:
        fixed:
            xsize width
            ysize urmk_px(60)
            button:
                style 'urmk_button'
                background (urmk_pill(urmk_colour('row-on'), urmk_px(10)) if _urmcpOn else None)
                hover_background urmk_pill(urmk_colour('row-on'), urmk_px(10))
                xfill True
                yfill True
                action Function(urmcp_select, _urmcpPath)
            hbox:
                xpos urmk_px(16)
                yalign 0.5
                spacing urmk_px(16)
                fixed:
                    xsize int(width * 0.42)
                    ysize urmk_px(60)
                    button:
                        style 'urmk_button'
                        yalign 0.5
                        hover_background urmk_pill(urmk_colour('hover'), urmk_px(8))
                        xpadding urmk_px(6)
                        ypadding urmk_px(2)
                        action (Function(urmcp_open_sheet, _urmcpPath) if urmcp_can_sheet() else Function(urmcp_select, _urmcpPath))
                        hbox:
                            yalign 0.5
                            spacing urmk_px(8)
                            if _urmcpOwners:
                                add urmk_word(urmcp_fit(_urmcpOwners + u' >', 'urmk_s', int(width * 0.14)), style='urmk_s', color=urmk_colour('ink-faint'), yalign=0.5)
                            add urmk_word(urmcp_fit(_urmcpName, 'urmk_m', int(width * 0.42) - (int(width * 0.14) if _urmcpOwners else 0) - urmk_px(12)), style='urmk_m', color=urmk_colour('ignored-dim' if _urmcpDim else 'ink'), yalign=0.5)
                use urmcp_kept_value(_urmcpPath, _urmcpKind, _urmcpWords, _urmcpFrozen, _urmcpDim, int(width * 0.22))
            hbox:
                xalign 1.0
                yalign 0.5
                xoffset -urmk_px(12)
                use urmcp_kept_button(group, _urmcpPath, _urmcpFrozen, _urmcpCan)

screen urmcp_kept(width):
    vbox:
        spacing urmk_px(20)
        for _urmcpGrp index _urmcpGrp[0] in urmcp_kept_groups():
            $ _urmcpKey, _urmcpTitle, _urmcpIcon, _urmcpTone, _urmcpDashed, _urmcpLine, _urmcpRows = _urmcpGrp
            use urmk_edged(_urmcpTone, _urmcpDashed, width):
                vbox:
                    spacing urmk_px(12)
                    hbox:
                        spacing urmk_px(12)
                        add urmk_word(_urmcpIcon, style='urmk_icon', color=urmk_tone_ink(_urmcpTone), yalign=0.5)
                        add urmk_word(_urmcpTitle, style='urmk_s_medium', color=urmk_tone_ink(_urmcpTone), kerning=urmk_px(1), yalign=0.5)
                        use urmk_chip(u'%d' % len(_urmcpRows), _urmcpTone)
                        add urmk_word(_urmcpLine, style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
                    if _urmcpRows:
                        vbox:
                            spacing urmk_px(4)
                            for _urmcpRow index _urmcpRow[0] in _urmcpRows:
                                use urmcp_kept_row(_urmcpKey, _urmcpRow, width - urmk_px(4) - urmk_px(40))
                    else:
                        add urmk_word((u'Nothing frozen yet: Freeze on a value keeps it where it is.' if _urmcpKey == 'frozen' else (u'Nothing remembered yet: Remember on a value puts it here.' if _urmcpKey == 'watch' else u'Nothing ignored.')), style='urmk_s', color=urmk_colour('ink-faint'))

# The detail panel: the selected row in words, and what can be done.
screen urmcp_detail(width):
    $ _urmcpSel = urmcp_selected()
    vbox:
        xsize width
        spacing urmk_px(16)
        add urmk_word("SELECTED", style='urmk_s_medium', color=urmk_colour('ink-muted'))
        if _urmcpSel is None:
            add urmk_word("Pick a row to see where the story checks it.", style='urmk_m', color=urmk_colour('ink-muted'))
        elif urmcp_is_var(_urmcpSel):
            $ _urmcpKind, _urmcpWords = urmcp_value(_urmcpSel)
            add urmk_word(urmcp_fit(urmcp_title(_urmcpSel), 'urmk_l', width), style='urmk_l')
            $ _urmcpFrozenWords = urmcp_frozen_words(_urmcpSel)
            if _urmcpKind in ('int', 'float', 'text', 'none', 'bool', 'list'):
                frame:
                    style 'urmk_frame'
                    background (urmk_pill(urmk_colour('frozen-bg'), urmk_px(8)) if _urmcpFrozenWords else urmcp_ground('value'))
                    xpadding urmk_px(24)
                    ypadding urmk_px(8)
                    add urmk_word(urmcp_fit(_urmcpWords, 'urmk_xl', width - urmk_px(48)), style='urmk_xl', color=urmk_colour('frozen-value' if _urmcpFrozenWords else 'ink'))
            if _urmcpFrozenWords:
                hbox:
                    spacing urmk_px(8)
                    add urmk_word(u'\ueb3b', style='urmk_icon', color=urmk_tone_ink('frozen'))
                    add urmk_word(_urmcpFrozenWords, style='urmk_m', color=urmk_colour('ink-muted'), xmaximum=width - urmk_px(32))
            else:
                $ _urmcpAbout = urmcp_about(_urmcpSel)
                if _urmcpAbout:
                    add urmk_word(_urmcpAbout, style='urmk_m', color=urmk_colour('ink-muted'))
            null height urmk_px(8)
            add urmk_word("DO", style='urmk_s_medium', color=urmk_colour('ink-muted'))
            if _urmcpKind == 'bool':
                use urmcp_wide(u'Set %s' % (u'false' if _urmcpWords == 'true' else u'true'), Function(urmcp_switch, _urmcpSel), 'main')
            else:
                use urmcp_wide(u'Set value', Function(urmcp_edit, _urmcpSel), 'main', _urmcpKind in ('int', 'float', 'text', 'none'))
            use urmcp_wide((u'Forget' if _urm_is_remembered(_urmcpSel) else u'Remember'), Function(urmcp_remember, _urmcpSel), 'plain')
            if urmcp_state_tab() != 'remembered':
                $ _urmcpFz, _urmcpFzOn = urmcp_freeze_words(_urmcpSel)
                use urmcp_wide(_urmcpFz, Function(urmcp_freeze, _urmcpSel), 'plain', _urmcpFzOn)
            use urmcp_delete(_urmcpSel, width, True)
        else:
            $ _urmcpWords, _urmcpNote = urmcp_other(_urmcpSel)
            add urmk_word(_urmcpWords, style='urmk_l')
            add urmk_word(_urmcpNote, style='urmk_m', color=urmk_colour('ink-muted'))
            use urmcp_replay_action(_urmcpSel)

# The full page (search3_f1): the URM+ menu, the search, the detail panel.
screen urmcp_alert_subtab(words, tab, count):
    $ _urmcpActive = urmcp_alert_tab() == tab
    button:
        style 'urmk_button'
        background urmk_back('plain' if _urmcpActive else 'quiet').image
        hover_background urmk_back('plain', hover=True).image
        ysize urmk_px(40)
        xpadding urmk_px(16)
        action Function(urmcp_select_alert_tab, tab)
        hbox:
            yalign 0.5
            spacing urmk_px(8)
            add urmk_word(words, style='urmk_s_medium', color=urmk_colour('accent-ink' if _urmcpActive else 'ink'), yalign=0.5)
            if count:
                add urmk_word('%d' % count, style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)

screen urmcp_notice_row(width, words, action_words, action, cue=None):
    frame:
        style 'urmk_frame'
        background urmk_back('plain').image
        xsize width
        xpadding urmk_px(24)
        ypadding urmk_px(12)
        side 'c r':
            xfill True
            spacing urmk_px(8)
            vbox:
                yalign 0.5
                spacing urmk_px(2)
                add urmk_word(words, style='urmk_m')
                if cue:
                    add urmk_word(cue, style='urmk_s', color=urmk_colour('ink-muted'))
            use urmk_button(action_words, action, 'quiet', 'small')

screen urmcp_page():
    modal True
    zorder 1050
    key 'K_ESCAPE' action Function(urmcp_close)
    key 'alt_K_f' action Function(urmcp_toggle)
    # its catalog or overflow search runs silently via _URMKWorkerPump (0 ms screen eval)
    if urmcp_pumping():
        add urmk_worker_pump(urmcp_pumping)
    $ _urmcpW = config.screen_width - urmk_px(64)
    $ _urmcpH = config.screen_height - urmk_px(64)
    $ _urmcpL = urmk_px(300)
    $ _urmcpNoticePage = urmcp_state_tab() == 'alerts'
    $ _urmcpR = 0 if _urmcpNoticePage else urmk_px(460)
    $ _urmcpM = _urmcpW - _urmcpL - _urmcpR
    $ _urmcpIn = _urmcpM - urmk_px(80)
    $ _urmcpCols = (int(_urmcpIn * 0.46), urmk_px(190), _urmcpIn - int(_urmcpIn * 0.46) - urmk_px(190), _urmcpIn)
    $ _urmcpCounts = urmcp_counts()
    use urmk_backdrop(Function(urmcp_close), urmk_colour('scrim'))
    # Sibling shield covers the page panel without wrapping input widgets (7.3.5 Button drops key_events).
    viewport:
        mousewheel True
        align (0.5, 0.5)
        xysize (_urmcpW, _urmcpH)
        button:
            style 'urmk_button'
            xfill True
            yfill True
            action NullAction()
    use urmk_window('window', xa=0.5, ya=0.5, width=(config.screen_width - urmk_px(64)) * 1080.0 / config.screen_height, pad=(0, 0)):
        hbox:
            ysize _urmcpH
            # the menu
            frame:
                style 'urmk_frame'
                xsize _urmcpL
                yfill True
                xpadding urmk_px(24)
                ypadding urmk_px(32)
                fixed:
                    xfill True
                    yfill True
                    vbox:
                        xfill True
                        spacing urmk_px(8)
                        add urmk_word("Menu", style='urmk_l', xoffset=urmk_px(24))
                        null height urmk_px(24)
                        use urmcp_wide(u'Find', Function(urmcp_tab, 'find'), 'plain' if urmcp_state_tab() == 'find' else 'quiet')
                        use urmcp_wide(u'Remembered', Function(urmcp_tab, 'remembered'), 'plain' if urmcp_state_tab() == 'remembered' else 'quiet')
                        use urmcp_wide(u'Changes', Function(urmcp_tab, 'changes'), 'plain' if urmcp_state_tab() == 'changes' else 'quiet')
                        use urmcp_wide(u'Scenes & goals', Function(urmcp_open_map), 'quiet', urmcp_can_map())
                        use urmcp_wide(u'Flags', Function(urmcp_go, 'flags'), 'quiet', urmcp_can_open('flags'))
                        use urmcp_wide(u'Alerts & Mutes', Function(urmcp_tab, 'alerts'), 'plain' if _urmcpNoticePage else 'quiet')
                    vbox:
                        xfill True
                        yalign 1.0
                        use urmcp_wide(u'Settings', Function(urmcp_go, 'settings'), 'quiet', urmcp_can_open('settings'))
            # the search
            frame:
                style 'urmk_frame'
                background Solid(urmk_colour('surface-tint'))
                xsize _urmcpM
                yfill True
                xpadding urmk_px(40)
                ypadding urmk_px(32)
                if urmcp_state_tab() == 'remembered':
                    vbox:
                        spacing urmk_px(24)
                        vbox:
                            spacing urmk_px(4)
                            add urmk_word("Remembered", style='urmk_l')
                            add urmk_word("Values you keep an eye on.", style='urmk_s', color=urmk_colour('ink-faint'))
                        viewport:
                            id 'urmcp_kept_rows'
                            mousewheel True
                            draggable True
                            yfill True
                            xsize _urmcpIn
                            use urmcp_kept(_urmcpIn)
                elif _urmcpNoticePage:
                    $ _urmcpAlerts = urmcp_alert_rows()
                    $ _urmcpMutes = urmcp_mute_rows()
                    $ _urmcpNoticeW = min(_urmcpIn, urmk_px(760))
                    vbox:
                        spacing urmk_px(24)
                        side 'c r':
                            xfill True
                            add urmk_word("Alerts & Mutes", style='urmk_l', yalign=0.5)
                            use urmk_button('', Function(urmcp_close), 'quiet', 'small', u'\ue5cd')
                        hbox:
                            spacing urmk_px(8)
                            use urmcp_alert_subtab('Alerts', 'alerts', len(_urmcpAlerts))
                            use urmcp_alert_subtab('Mutes', 'mutes', len(_urmcpMutes))
                        viewport:
                            id 'urmcp_alert_rows'
                            mousewheel True
                            draggable True
                            yfill True
                            xsize _urmcpNoticeW
                            yadjustment urmcp_alert_adj
                            if urmcp_alert_tab() == 'mutes':
                                if _urmcpMutes:
                                    vbox:
                                        spacing urmk_px(8)
                                        for _urmcpMute index _urmcpMute[0] in _urmcpMutes[:urmcp_alert_room()]:
                                            $ _urmcpKey, _urmcpWords, _urmcpCue = _urmcpMute
                                            use urmcp_notice_row(_urmcpNoticeW, _urmcpWords, 'Unmute', Function(urmcp_mute_remove, _urmcpKey), _urmcpCue)
                                else:
                                    add urmk_word("No muted notifications for this game.", style='urmk_s', color=urmk_colour('ink-muted'))
                            elif _urmcpAlerts:
                                vbox:
                                    spacing urmk_px(12)
                                    add urmk_word("Stop skipping when the game checks one of these.", style='urmk_s', color=urmk_colour('ink-muted'))
                                    for _urmcpAlert index _urmcpAlert[0] in _urmcpAlerts[:urmcp_alert_room()]:
                                        $ _urmcpAw, _urmcpAs = _urmcpAlert
                                        use urmcp_notice_row(_urmcpNoticeW, _urmcpAw, _urmcpAs, Function(urmcp_alert_stop, _urmcpAw))
                            else:
                                add urmk_word("No alerts set. Open a variable or flag and click the bell to alert when the game checks it.", style='urmk_s', color=urmk_colour('ink-muted'))
                else:
                    vbox:
                        spacing urmk_px(24)
                        use urmcp_field(_urmcpIn)
                        if urmcp_state_tab() == 'changes':
                            use urmcp_since()
                        else:
                            hbox:
                                box_wrap True
                                spacing urmk_px(8)
                                box_wrap_spacing urmk_px(8)
                                use urmcp_pill(u'Everything', 'all')
                                use urmcp_pill(u'Variables', 'vars', _urmcpCounts.get('vars'))
                                use urmcp_pill(u'Lines', 'lines', _urmcpCounts.get('lines'))
                                use urmcp_pill(u'Choices', 'choices', _urmcpCounts.get('choices'))
                                use urmcp_pill(u'Flags', 'flags', _urmcpCounts.get('flags'))
                                use urmcp_pill(u'Labels', 'labels', _urmcpCounts.get('labels'))
                                use urmcp_pill(u'Changed', 'changed', _urmcpCounts.get('changed'))
                                use urmcp_pill(u'Engine', 'engine', _urmcpCounts.get('engine'))
                                use urmk_button(u'New variable', Function(urmcp_new_open), 'quiet', 'small', u'')
                            if urmcp_state_pill() == 'changed':
                                use urmcp_since()
                        hbox:
                            xoffset urmk_px(24)
                            frame:
                                style 'urmk_frame'
                                xsize _urmcpCols[0]
                                add urmk_word("Name", style='urmk_s_medium', color=urmk_colour('ink-muted'))
                            frame:
                                style 'urmk_frame'
                                xsize _urmcpCols[1]
                                add urmk_word("Value", style='urmk_s_medium', color=urmk_colour('ink-muted'))
                            frame:
                                style 'urmk_frame'
                                xsize _urmcpCols[2]
                                add urmk_word("Matters", style='urmk_s_medium', color=urmk_colour('ink-muted'))
                        viewport:
                            id 'urmcp_page_rows'
                            yadjustment urmcp_rows_adj
                            mousewheel True
                            draggable True
                            yfill True
                            xsize _urmcpIn
                            if urmcp_reading():
                                use urmk_later('rows'):
                                    use urmcp_page_rows(_urmcpCols)
                            else:
                                use urmcp_page_rows(_urmcpCols)
            # the detail panel
            if not _urmcpNoticePage:
                frame:
                    style 'urmk_frame'
                    xsize _urmcpR
                    yfill True
                    xpadding urmk_px(32)
                    ypadding urmk_px(32)
                    side 't c':
                        side 'c r':
                            xfill True
                            null
                            use urmk_button('', Function(urmcp_close), 'quiet', 'small', u'\ue5cd')
                        use urmcp_detail(_urmcpR - urmk_px(64))
