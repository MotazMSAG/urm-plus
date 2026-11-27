# Dialogue appearance. Work from the screen the game already built, so
# Character and Ren'Py still own the current line and its text widget.
init 999 python:

    _urm_setting_add("urmcTextboxStyle", "game")
    _urm_setting_add("urmcTextboxOpacity", 100)

    def _urmtb_glass():
        radius = max(3, urmk_px(18))
        size = radius * 2 + 4
        box = (0, 0, size, size)

        def pixel(x, y):
            distance = _urmk_distance(x + 0.5, y + 0.5, box, radius)
            coverage = _urmk_cover(distance)
            edge = coverage - _urmk_cover(distance + 1)
            light = 0.42 if y < radius else 0.26
            r, g, b, a = _urmk_lay((255, 255, 255, 255), edge * light,
                                   32.0 / 255 * 0.82 * coverage,
                                   35.0 / 255 * 0.82 * coverage,
                                   42.0 / 255 * 0.82 * coverage, 0.82 * coverage)
            return (int(255 * r / a), int(255 * g / a), int(255 * b / a), int(255 * a)) if a else (0, 0, 0, 0)

        picture = im.Data(_urmk_png(size, size, pixel, True), "urmtb_glass.png")
        return Frame(picture, radius + 1, radius + 1)

    def _urmtb_fade():
        height = max(3, urmk_px(160))

        def pixel(_x, y):
            fraction = float(y) / (height - 1)
            if fraction < 0.70:
                alpha = 173 * fraction / 0.70
            else:
                alpha = 173 + 28 * (fraction - 0.70) / 0.30
            return (16, 17, 22, int(alpha))

        picture = im.Data(_urmk_png(2, height, pixel), "urmtb_fade.png")
        return Frame(picture, 0, 0)

    _URMTB_BACKS = python_dict((("glass", _urmtb_glass()), ("subtitles", _urmtb_fade())))

    def _urmtb_font(weight):
        group = FontGroup()
        group.add(URMK_FONTS[weight], 0x20, 0x7e)
        group.add("DejaVuSans.ttf", None, None)
        return group

    _URMTB_FONTS = (_urmtb_font("medium"), _urmtb_font("bold"))

    def _urmtb_alpha(background, opacity):
        if background is None or opacity == 0:
            return None
        if opacity == 100:
            return background
        return Transform(background, alpha=opacity / 100.0)

    def _urmtb_style(widget, key, properties=None):
        # Screen language can hand the same widget back on the next
        # interaction. Keep its style so a change of setting is reversible.
        saved = getattr(widget, "_urmtb_original_style", None)
        if saved is not None and saved[0] == key:
            return
        if saved is None:
            original = widget.style
        else:
            original = saved[1]
        if properties is None:
            if saved is None:
                return
            widget.style = original
            del widget._urmtb_original_style
        else:
            changed = original.copy()
            changed.set_prefix(widget.style.prefix)
            changed.add_properties(properties)
            widget.style = changed
            widget._urmtb_original_style = (key, original)
        if isinstance(widget, renpy.text.text.Text):
            widget.kill_layout()
        renpy.display.render.invalidate(widget)

    def _urmtb_only_words(node, words, name):
        """Return the word widget identities in a plain say window. A custom
        layout can contain buttons, transforms, images or other text."""
        if node is words:
            return (id(words),)
        if name is not None and node is name:
            return (id(name),)
        layout = renpy.display.layout
        if type(node) is layout.Window:
            return _urmtb_only_words(node.get_child(), words, name)
        if type(node) is not layout.MultiBox:
            return ()
        found = ()
        for child in node.children:
            leaves = _urmtb_only_words(child, words, name)
            if not leaves:
                return ()
            found += leaves
        return found

    def _urmtb_separate_window(root, words, name):
        # Some say screens put the background and the two identified text
        # widgets next to one another. Find only an unambiguous say window.
        if words not in root.children or (name is not None and name not in root.children):
            return None
        layout = renpy.display.layout
        found = None
        for item in root.children:
            if type(item) is not layout.Window:
                continue
            saved = getattr(item, "_urmtb_original_style", None)
            style = saved[1] if saved else item.style
            if style.name != ("say_window",) and style.parent != ("say_window",):
                continue
            child = item.get_child()
            if child is None or (type(child) is layout.MultiBox and not child.children):
                if found is not None:
                    return None
                found = item
        return found

    def _urmtb_caption(visual, opacity, words, name, name_colour):
        layout = renpy.display.layout
        glass = visual == "glass"
        align = 0.0 if glass else 0.5
        for widget, size, colour, kit_font in ((words, 45, "#f2f3f5", _URMTB_FONTS[0]),
                                               (name, 34, name_colour, _URMTB_FONTS[1])):
            if widget is not None:
                saved = getattr(widget, "_urmtb_original_style", None)
                font = (saved[1] if saved else widget.style).font
                if font == "DejaVuSans.ttf" and not getattr(_preferences, "font_transform", None):
                    font = kit_font
                _urmtb_style(widget, (visual, size, colour, config.screen_height, font),
                             dict(xalign=align, yalign=0.0, xoffset=0, yoffset=0,
                                  xminimum=0, xmaximum=None, yminimum=0, ymaximum=None,
                                  xfill=False, yfill=False, text_align=align,
                                  size=urmk_px(size), color=colour, font=font,
                                  outlines=[(urmk_px(2), "#0f1013b0", 0, urmk_px(1))]))
        contents = layout.MultiBox(layout="vertical", spacing=urmk_px(6), xfill=True)
        if name is not None:
            contents.add(name)
        contents.add(words)
        return layout.Window(
            contents, style="default", xalign=0.5, yanchor=1.0,
            ypos=0.93 if glass else 1.0, xfill=True, yfill=False,
            xmaximum=int(config.screen_width * (0.84 if glass else 1.0)),
            left_padding=urmk_px(45) if glass else int(config.screen_width * 0.06),
            right_padding=urmk_px(45) if glass else int(config.screen_width * 0.06),
            top_padding=urmk_px(25 if glass else 104),
            bottom_padding=urmk_px(30) if glass else int(config.screen_height * 0.11),
            background=_urmtb_alpha(_URMTB_BACKS[visual], opacity))

    def _urmtb_apply(sd, visual, opacity):
        root = sd.child
        window = sd.widgets.get("window")
        words = sd.widgets.get("what")
        name = sd.widgets.get("who")
        layout = renpy.display.layout
        if not isinstance(words, renpy.text.text.Text):
            return
        text_name = isinstance(name, renpy.text.text.Text) if sd.scope.get("who") else name is None
        separate = None
        if window is None and text_name:
            separate = window = _urmtb_separate_window(root, words, name)
        if type(window) is not layout.Window:
            return
        if (visual in _URMTB_BACKS and window in root.children and text_name
                and (separate is not None or sorted(_urmtb_only_words(window.get_child(), words, name)) ==
                     (sorted((id(name), id(words))) if name is not None else [id(words)]))):
            colour = sd.widget_properties.get("who", {}).get("color", "#f5d5b6")
            caption = _urmtb_caption(visual, opacity, words, name, colour)
            root.children[root.children.index(window)] = caption
            if separate is not None:
                for i in range(len(root.children) - 1, -1, -1):
                    if root.children[i] is words or root.children[i] is name:
                        del root.children[i]
                        del root.start_times[i]
                        del root.anim_times[i]
            root.child = root.children[-1]
            return

        _urmtb_style(words, None)
        if isinstance(name, renpy.text.text.Text):
            _urmtb_style(name, None)
        if opacity == 100:
            _urmtb_style(window, None)
        else:
            saved = getattr(window, "_urmtb_original_style", None)
            original = saved[1] if saved else window.style
            _urmtb_style(window, opacity, dict(background=_urmtb_alpha(original.background, opacity)))

    _urmtb_update_original = renpy.display.screen.ScreenDisplayable.update

    def _urmtb_update(sd):
        if sd.screen_name != ("say",) or not sd.transient:
            return _urmtb_update_original(sd)
        old_child = sd.child
        result = _urmtb_update_original(sd)
        if sd.child is not old_child:
            _urmtb_apply(sd, _urm_setting("urmcTextboxStyle"), _urm_setting("urmcTextboxOpacity"))
        return result

    renpy.display.screen.ScreenDisplayable.update = _urmtb_update

    _urm_row_add("textbox_style", "look", "Dialogue style", "How ordinary dialogue appears.",
                 (("Game's own", "game"), ("Glass strip", "glass"), ("Subtitles", "subtitles")),
                 setting="urmcTextboxStyle", order=20)
    _urm_row_add("textbox_opacity", "look", "Background opacity", "How solid the dialogue background is.",
                 (), setting="urmcTextboxOpacity", percent=True, order=30)
