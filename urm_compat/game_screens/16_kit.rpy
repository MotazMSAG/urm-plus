# The kit's parts (game_fixes/16_kit): every screen of ours draws with
# these. Sizes are at 1080 lines (urmk_px scales them); words take the
# kit's styles urmk_s, urmk_m (and their _medium), urmk_l, urmk_xl (bold)
# and urmk_icon.

# A window: a see-through panel with its edge light and shadow, what the
# `use` block holds inside it. kind: 'window', 'card' or 'bubble'; edge: a
# tone along the top edge (a banner). Placed by its panel, not its shadow:
# xa, ya are its xalign and yalign, x, y (at 1080 lines) moved from there;
# width at 1080 lines, or as wide as it holds; pad: the room inside, at
# the sides and at the top and bottom.
screen urmk_window(kind='window', edge=None, xa=0.5, ya=0.0, x=0, y=0, width=None, pad=(32, 24)):
    $ _urmkB = urmk_back(kind, edge)
    frame:
        style 'urmk_frame'
        background _urmkB.image
        left_margin -_urmkB.left
        right_margin -_urmkB.right
        top_margin -_urmkB.top
        bottom_margin -_urmkB.bottom
        left_padding _urmkB.left + urmk_px(pad[0])
        right_padding _urmkB.right + urmk_px(pad[0])
        top_padding _urmkB.top + urmk_px(pad[1])
        bottom_padding _urmkB.bottom + urmk_px(pad[1])
        xalign xa
        yalign ya
        xoffset urmk_px(x)
        yoffset urmk_px(y)
        xminimum (urmk_px(width) if width else 0)
        xmaximum (urmk_px(width) if width else None)
        transclude

# Frame first: what the `use` block holds is drawn one frame after the
# window it sits in was shown (game_fixes/16_kit, urmk_held); key names the
# part within its window. For a part whose room does not depend on what
# it holds, so the window keeps its size.
screen urmk_later(key):
    if urmk_held(key):
        timer 0.01 action Function(urmk_draw_now, key)
    else:
        transclude

# A chip: words on a soft pill in their tone's colours. mark: a sign in
# front of the words, for a shape as well as a colour.
screen urmk_chip(words, tone='plain', mark=None, room=None):
    frame:
        style 'urmk_frame'
        background urmk_chip_bg(tone)
        xmaximum room
        # One line of words makes it exactly the chip's height; words that
        # wrap in a narrow room make it taller, never spill (UX rule 18).
        yminimum urmk_px(URMK_CHIP[0])
        ypadding urmk_chip_pad()
        xpadding urmk_px(URMK_CHIP[1])
        hbox:
            yalign 0.5
            spacing urmk_px(8)
            if mark:
                add urmk_word(mark, style='urmk_s_medium', color=urmk_chip_ink(tone), yalign=0.5)
            if room is None:
                add urmk_word(words, style='urmk_s_medium', color=urmk_chip_ink(tone), yalign=0.5)
            else:
                add urmk_word(words, style='urmk_s_medium', color=urmk_chip_ink(tone), yalign=0.5, language='unicode', layout='greedy', xmaximum=max(1, room - 2 * urmk_px(URMK_CHIP[1])))

# A group's card (urmk_edged_back): an edge down its left side in its
# tone's colour, whole or dashed; what it holds is passed in.
screen urmk_edged(tone, dashed=False, width=None):
    frame:
        style 'urmk_frame'
        background urmk_edged_back(tone, dashed)
        xfill (width is None)
        xsize width
        left_padding urmk_px(4) + urmk_px(20)
        right_padding urmk_px(20)
        ypadding urmk_px(16)
        transclude

# A button: kind 'main' (the one main action), 'plain' or 'quiet'; size
# 'big' or 'small'; icon: a glyph of the icon font before the words, or
# alone when words is empty (then the button is square). Takes the mouse,
# the keyboard and a controller alike: pointed at and focused look the same.
screen urmk_button(words, action, kind='plain', size='big', icon=None, hovered=None, unhovered=None):
    $ _urmkH, _urmkP, _urmkT = URMK_BUTTON_SIZE[size]
    $ _urmkI, _urmkJ = URMK_BUTTON_INK[kind]
    button:
        style 'urmk_button'
        background urmk_back(kind).image
        hover_background urmk_back(kind, hover=True).image
        ysize urmk_px(_urmkH)
        xpadding (urmk_px(_urmkP) if words else 0)
        xminimum (0 if words else urmk_px(_urmkH))
        if hovered is not None:
            hovered hovered
        if unhovered is not None:
            unhovered unhovered
        action action
        hbox:
            align (0.5, 0.5)
            spacing urmk_px(8)
            if icon:
                add urmk_word(icon, style='urmk_icon', color=urmk_colour(_urmkI), hover_color=urmk_colour(_urmkJ), yalign=0.5)
            if words:
                add urmk_word(words, style=('urmk_%s_medium' % _urmkT), color=urmk_colour(_urmkI), hover_color=urmk_colour(_urmkJ), yalign=0.5)

# A switch, on or off: the look alone, for a menu row that takes the click.
screen urmk_switch(on):
    $ _urmkW, _urmkH, _urmkK, _urmkG = URMK_SWITCH
    frame:
        style 'urmk_frame'
        background urmk_pill(urmk_colour('accent' if on else 'plain-bg'), urmk_px(_urmkH) // 2)
        xysize (urmk_px(_urmkW), urmk_px(_urmkH))
        frame:
            style 'urmk_frame'
            background urmk_pill(urmk_colour('on-accent' if on else 'ink-muted'), urmk_px(_urmkK) // 2)
            xysize (urmk_px(_urmkK), urmk_px(_urmkK))
            xpos urmk_px(_urmkW - _urmkK - _urmkG if on else _urmkG)
            ypos urmk_px(_urmkG)

# A row of choices, one of them picked. items: (words, action, picked) in
# the order shown. held: the pick is not the one in effect (this game keeps
# its own value), so it is drawn quiet.
screen urmk_choices(items, held=False):
    $ _urmkH, _urmkI, _urmkC, _urmkP = URMK_CHOICES
    frame:
        style 'urmk_frame'
        background urmk_pill(urmk_colour('plain-bg'), urmk_px(_urmkH) // 2)
        ysize urmk_px(_urmkH)
        padding (urmk_px(_urmkI), urmk_px(_urmkI))
        hbox:
            spacing urmk_px(_urmkI)
            for _urmkItem index _urmkItem[0] in items:
                $ _urmkW, _urmkA, _urmkS = _urmkItem
                button:
                    style 'urmk_button'
                    ysize urmk_px(_urmkC)
                    xpadding urmk_px(_urmkP)
                    background (urmk_pill(urmk_colour('line' if held else 'accent'), urmk_px(_urmkC) // 2) if _urmkS else None)
                    hover_background urmk_pill(urmk_colour(('line' if held else 'accent') if _urmkS else 'hover'), urmk_px(_urmkC) // 2)
                    action _urmkA
                    add urmk_word(_urmkW, style='urmk_s_medium', color=urmk_colour((('ink' if held else 'on-accent') if _urmkS else 'ink-muted')), hover_color=urmk_colour((('ink' if held else 'on-accent') if _urmkS else 'ink')), align=(0.5, 0.5))

# A row of a menu: an icon and words at the left, and at the right what it
# says now: a key (key_words), a count (a chip), a switch (on: True or
# False) or, for a row that opens a further page, an arrow (more). unfold:
# the row folds rows out under it (urmk_menu_item), True while they show.
screen urmk_menu_row(words, icon, action, on=None, count=None, key_words=None, more=False, unfold=None):
    $ _urmkH, _urmkP, _urmkR = URMK_ROW
    button:
        style 'urmk_button'
        hover_background urmk_pill(urmk_colour('hover'), urmk_px(_urmkR))
        xfill True
        ysize urmk_px(_urmkH)
        xpadding urmk_px(_urmkP)
        action action
        fixed:
            xfill True
            yfill True
            hbox:
                yalign 0.5
                spacing urmk_px(16)
                add urmk_word(icon, style='urmk_icon', color=urmk_colour('ink'), yalign=0.5)
                add urmk_word(words, style='urmk_m_medium', color=urmk_colour('ink'), yalign=0.5)
            hbox:
                xalign 1.0
                yalign 0.5
                spacing urmk_px(8)
                if on is not None:
                    use urmk_switch(on)
                elif count is not None:
                    use urmk_chip(count)
                elif key_words:
                    add urmk_word(key_words, style='urmk_s', color=urmk_colour('ink-muted'), yalign=0.5)
                elif more:
                    add urmk_word('\ue5cc', style='urmk_icon', color=urmk_colour('ink-muted'), yalign=0.5)
                if unfold is not None:
                    add urmk_word(('\ue5ce' if unfold else '\ue5cf'), style='urmk_icon', color=urmk_colour('ink-muted'), yalign=0.5)

# A row a menu row folds out: words lined up with the menu row's words,
# and a quiet step at the right (the alerts' Stop).
screen urmk_menu_item(words, step, action):
    $ _urmkH, _urmkP, _urmkR = URMK_ROW
    fixed:
        xfill True
        ysize urmk_px(40)
        add urmk_word(words, style='urmk_m', color=urmk_colour('ink'), xpos=urmk_px(_urmkP + URMK_ICON + 16), yalign=0.5)
        hbox:
            xalign 1.0
            yalign 0.5
            use urmk_button(step, action, 'quiet', 'small')

# A section of a window's list at its left: an icon and words, the one
# picked on a raised ground, the others quiet.
screen urmk_tab(words, icon, action, picked=False):
    $ _urmkH, _urmkP, _urmkR = URMK_ROW
    button:
        style 'urmk_button'
        background (urmk_pill(urmk_colour('surface-2'), urmk_px(_urmkR)) if picked else None)
        hover_background urmk_pill(urmk_colour('surface-2' if picked else 'hover'), urmk_px(_urmkR))
        xfill True
        ysize urmk_px(_urmkH)
        xpadding urmk_px(_urmkP)
        action action
        hbox:
            yalign 0.5
            spacing urmk_px(16)
            add urmk_word(icon, style='urmk_icon', color=urmk_colour('ink' if picked else 'ink-muted'), yalign=0.5)
            add urmk_word(words, style=('urmk_m_medium' if picked else 'urmk_m'), color=urmk_colour('ink' if picked else 'ink-muted'), yalign=0.5)

# A line between rows or groups of a menu, x in from the sides and y off
# the rows above and below (at 1080 lines).
screen urmk_divider(x=16, y=8):
    frame:
        style 'urmk_frame'
        xfill True
        padding (urmk_px(x), urmk_px(y))
        frame:
            style 'urmk_frame'
            background urmk_pill(urmk_colour('divider'), 0)
            xfill True
            ysize max(1, urmk_px(1))

# A part the player drags: what the `use` block holds. Where the player
# drops it, it stays: kept in the setting `keep` (at all games' level with
# every_game) when given, else only while it is shown. Until it is dropped
# it sits at xa, ya, moved by x, y (at 1080 lines), as a window does; size:
# how big it is at most (at 1080 lines), to keep it on the screen. handle:
# the part that takes the drag, as the engine's drag_handle (None: all of
# it); clicked: what a click that does not move it does; hovered,
# unhovered: what pointing at it and away does. room: (left, top, right,
# bottom) at 1080 lines around the part, inside what the `use` block
# holds (a badge on its corner): x, y, size and the setting are the
# part's own, so the part sits where it would without room.
screen urmk_drag(name, keep=None, every_game=False, xa=1.0, ya=0.0, x=0, y=0, size=(48, 48), handle=None, clicked=None, room=None, hovered=None, unhovered=None):
    $ _urmkD = urmk_drag_at(keep, size, room) if keep else None
    $ _urmkR = urmk_room(room)
    drag:
        drag_name name
        draggable True
        droppable False
        focus_mask None
        if _urmkD:
            pos _urmkD
        else:
            xalign xa
            yalign ya
            xoffset urmk_px(x) - _urmkR[0] + int(round(xa * (_urmkR[0] + _urmkR[2])))
            yoffset urmk_px(y) - _urmkR[1] + int(round(ya * (_urmkR[1] + _urmkR[3])))
        if keep:
            dragged urmk_dragged(keep, every_game, room)
        if handle:
            drag_handle handle
        if clicked is not None:
            clicked clicked
        if hovered is not None:
            hovered hovered
        if unhovered is not None:
            unhovered unhovered
        transclude

# What a hovered part of the screen `of` is for (its tooltip), in a bubble
# placed by the screen beside what it describes, where it covers nothing
# (as the search sheet's expand icon has its name): for a button that shows
# only an icon. Nothing while nothing of `of` is pointed at. A tooltip is
# always words: the engine keeps one for every screen, and any screen may
# draw it as text (tests/check_rpy.py). A screen with one such button per
# row ends the row pointed at with it (it knows which by `hovered`).
screen urmk_tip(of):
    $ _urmkT = GetTooltip(of)
    if _urmkT:
        use urmk_window('bubble', xa=0.0, ya=0.5, pad=(12, 4)):
            add urmk_word(_urmkT, style='urmk_s')

# Click/scroll backdrop: absorbs outside rollback/rollforward keys and mousewheel,
# and closes the topmost URM+ window without advancing dialogue behind it.
screen urmk_backdrop(close=None, scrim=None):
    for _urmkSk in URMK_SCROLL_KEYS:
        key _urmkSk action NullAction()
    add _URMKWheelGuard()
    button:
        style 'urmk_button'
        xfill True
        yfill True
        if scrim:
            background urmk_pill(scrim, 0)
        action (close if close is not None else NullAction())

# The older displays' dialog (the Flags list; see game_fixes/16_kit): a
# window in the middle that the player drags by its title bar, its icon and
# title in the bar, a close button at the right, a veil over the game
# behind it. close: what the close button and Esc do. It takes the older
# displays' styles (style_prefix 'urmk_old'); the veil fades in and out
# (urmk_old_fade).
screen urmk_old_dialog(title, close, icon=None):
    style_prefix 'urmk_old'
    key 'K_ESCAPE' action close
    for _urmkSk in URMK_SCROLL_KEYS:
        key _urmkSk action NullAction()
    viewport:
        mousewheel True
        xfill True
        yfill True
        textbutton '' style 'urmk_old_overlay' xfill True yfill True action close at urmk_old_fade
    drag:
        draggable True
        drag_handle (0, 0, 1.0, urmk_px_cut(42))
        align ((0.5, 0.15) if renpy.variant('touch') else (0.5, 0.5))
        frame:
            style 'urmk_old_dialog'
            vbox:
                frame:
                    background None
                    ysize urmk_px_cut(40)
                    xpadding urmk_px_cut(4)
                    ypadding 0
                    hbox:
                        spacing urmk_px_cut(4)
                        yalign 0.5
                        if icon:
                            text icon style 'urmk_old_dialogIcon' yalign 0.5
                        frame:
                            style 'urmk_old_label'
                            yalign 0.5
                            text title style 'urmk_old_label_text' substitute False
                hbox:
                    style 'urmk_old_dialogButtons'
                    button:
                        style 'urmk_old_dialogCloseButton'
                        action close
                        text 'x' size urmk_px_cut(24) yalign 0.5 color URMK_OLD_COLOURS['closeInk']
                button:
                    style 'urmk_old_dialogContent'
                    key_events True
                    action NullAction()
                    has vbox
                    transclude
