# Flags: choices a game keeps as words in a collection. The list is
# opened from the Flags button beside Search and the URM+ menu; a flag's
# Details open the variable sheet on our layer (urmfl_details). This
# screen's scope holds the flag's name alone: a save may keep it.

screen urmfl_flag_dialog(name):
    modal True
    zorder 1060
    use urmi_var_sheet(name, Function(renpy.hide_screen, 'urmfl_flag_dialog', layer=_urmi_layer), True)

# The Flags list, in the older displays' dialog (urmk_old_dialog) on our
# layer: urmfl_open shows it, urmfl_close hides it. The filter box's words
# are the kit's (urmk_old_input), never the screen's, so no save holds them.
screen urmfl_flags():
    style_prefix 'urmk_old'
    default _urmflTip = None    # the flag whose bell is pointed at: its row ends in the hint

    on "show" action urmk_old_input('flags').Enable()

    python:
        _urmflRows, _urmflMatched = urmfl_rows(urmk_old_input('flags').get_text(), URMFL_ROWS.room())

    use urmk_old_dialog('Flags', Function(urmfl_close), u'\ue153'):
        vbox xsize urmk_px_cut(1100)
        add urmk_word("Choices this game keeps as words in a collection instead of variables. Switch one, or open it to see what it does.", style='urmk_old_description')
        null height urmk_px_cut(8)
        hbox:
            spacing urmk_px_cut(6)
            add urmk_word(u'\ue8b6', style='urmk_old_icon', yalign=0.5)
            button:
                xminimum urmk_px_cut(500)
                key_events True
                action urmk_old_input('flags').Enable()
                input value urmk_old_input('flags')
            add urmk_word((u"%d found" % _urmflMatched + (u" (first 200 shown)" if _urmflMatched > 200 else u"")), style='urmk_old_description', yalign=0.5)
        null height urmk_px_cut(8)
        viewport:
            ymaximum urmk_px_cut(560)
            yadjustment URMFL_ROWS.adj
            mousewheel True
            draggable True
            scrollbars "vertical"
            vbox:
                spacing urmk_px_cut(4)
                for _urmflItem index _urmflItem[0] in _urmflRows:
                    $ _urmflName, _urmflWord, _urmflState, _urmflInfo = _urmflItem
                    hbox:
                        spacing urmk_px_cut(10)
                        textbutton ("true" if _urmflState else "false") xminimum urmk_px_cut(70) text_size urmk_px_cut(17) substitute False action Function(urmfl_set, _urmflName, not _urmflState)
                        textbutton "Details" text_size urmk_px_cut(17) substitute False action Function(urmfl_details, _urmflName)
                        textbutton (u'\ue7f4' if urmal_is(_urmflName) else u'\ue7f6') style 'urmk_old_icon_button' selected urmal_is(_urmflName) tooltip 'Alert when the game checks this' hovered SetScreenVariable('_urmflTip', _urmflName) unhovered SetScreenVariable('_urmflTip', None) action Function(urmal_toggle, _urmflName)
                        add urmk_word(_urmflWord, style='urmk_old_text', size=urmk_px_cut(19), yalign=0.5)
                        add urmk_word(_urmflInfo, style='urmk_old_text', size=urmk_px_cut(16), color=urmk_colour('ink-muted'), yalign=0.5)
                        if _urmflTip == _urmflName:
                            use urmk_tip('urmfl_flags')
