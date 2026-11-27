screen urmu_settings(width):
    $ state = _urmu_state()
    vbox:
        xsize urmk_px(width)
        spacing urmk_px(16)
        add urmk_word('Updates', style='urmk_m_medium', color=urmk_colour('accent-ink'))
        use urmk_divider(0, 0)
        add urmk_word('Installed  ' + URMU_VERSION, style='urmk_s', color=urmk_colour('ink-muted'))
        if state.status == 'checking':
            add urmk_word('Checking for updates…', style='urmk_s', color=urmk_colour('ink-muted'))
        elif state.release:
            add urmk_word('Available  ' + state.release[0], style='urmk_m_medium')
            use urmk_button('Update MRM', Function(_urmu_review), 'main')
        elif state.status == 'offline':
            add urmk_word('Couldn’t check for updates.', style='urmk_s', color=urmk_tone_ink('warn'))
            hbox:
                spacing urmk_px(12)
                use urmk_button('Retry', Function(_urmu_check), 'main')
                use urmk_button('Release page', OpenURL(_urmu_page()))
        else:
            if state.status == 'checked':
                use urmk_chip('Up to date', 'gain')
            use urmk_button('Check for updates', Function(_urmu_check))

screen urmu_dialog():
    modal True
    zorder 30
    $ state = _urmu_state()
    if state.dialog and state.release:
        $ close = Function(_urmu_cancel)
        key 'game_menu' action close
        use urmk_backdrop(scrim=urmk_colour('scrim'))
        if state.dialog == 'notice':
            use urmk_window(width=500, ya=0.5, pad=(28, 24)):
                vbox:
                    spacing urmk_px(16)
                    add urmk_word('MRM update available', style='urmk_l')
                    add urmk_word('Version ' + state.release[0], style='urmk_m', color=urmk_colour('ink-muted'))
                    hbox:
                        spacing urmk_px(12)
                        use urmk_button('Update MRM', Function(_urmu_review), 'main')
                        use urmk_button('Later', close)
        else:
            use urmk_window(width=720, ya=0.5, pad=(28, 24)):
                vbox:
                    xsize urmk_px(664)
                    spacing urmk_px(12)
                    add urmk_word('Install MRM %s?' % state.release[0], style='urmk_l')
                    if state.dialog == 'confirm':
                        add urmk_word('Save your game before closing.', style='urmk_m', color=urmk_colour('ink-muted'))
                        hbox:
                            xalign 1.0
                            spacing urmk_px(12)
                            use urmk_button('Close & install', Function(_urmu_install), 'main')
                            use urmk_button('Cancel', close)
                    elif state.dialog == 'manual':
                        add urmk_word('In-game installation is available on Windows.', style='urmk_m', color=urmk_colour('ink-muted'))
                        hbox:
                            xalign 1.0
                            spacing urmk_px(12)
                            use urmk_button('Release page', OpenURL(_urmu_page()), 'main')
                            use urmk_button('Cancel', close)
                    elif state.dialog == 'failed':
                        add urmk_word('Couldn’t prepare the update.', style='urmk_m', color=urmk_tone_ink('warn'))
                        hbox:
                            xalign 1.0
                            spacing urmk_px(12)
                            use urmk_button('Retry', Function(_urmu_install), 'main')
                            use urmk_button('Release page', OpenURL(_urmu_page()))
                            use urmk_button('Cancel', close)
                    else:
                        add urmk_word('Preparing the update…', style='urmk_m', color=urmk_colour('ink-muted'))
                        if state.dialog == 'downloading':
                            hbox:
                                xalign 1.0
                                use urmk_button('Cancel', close)
