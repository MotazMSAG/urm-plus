"""Exercise _urmtb_update through normal say screens and draw each layout."""
# run_tests: props
# prop_probe: standalone

import sys

import prop_probes

PROBE_CODE = u'''
screen _tb_fixture(who, what):
    window:
        id "window"
        xysize (900, 170)
        xalign 0.5
        yalign 1.0
        background Solid("#20232a")
        if who is not None:
            window:
                id "namebox"
                background None
                text who id "who"
        text what id "what" yoffset 48
    add Null(20, 20) xalign 0.0

screen _tb_fixture_reversed(who, what):
    window:
        id "window"
        vbox:
            text what id "what"
            if who is not None:
                window:
                    id "namebox"
                    background None
                    text who id "who"

screen _tb_fixture_separate(who, what, second_background=False):
    window:
        style "say_window"
        background Transform(Solid("#20232a"), alpha=0.75)
        xysize (900, 170)
        align (0.5, 1.0)
    if who:
        text who id "who" pos (240, 565)
    text what id "what" pos (240, 610)
    add Solid("#fe6c19", xysize=(20, 20)) pos (18, 250)
    if second_background:
        window:
            style "say_window"
            background Solid("#41454d")
            xysize (30, 30)
            pos (1000, 640)

screen _tb_phone(who, what):
    window:
        id "window"
        xysize (480, 600)
        xalign 1.0
        yalign 0.5
        background Solid("#454854")
        text what id "what"

init 1999 python:
    def _tb_begin(who, what, screen="say", **kwargs):
        tag, _what, layer = renpy.character.show_display_say(who, what, screen=screen, **kwargs)
        sd = renpy.display.screen.get_screen(tag, layer)
        sd.update()
        return sd

    def _tb_redraw(sd):
        renpy.display.screen.updated_screens.discard(sd)
        sd.update()
        renpy.display.render.invalidate(sd)
        renpy.display.render.process_redraws()

    def _tb_render(sd, picture=None):
        import os
        import pygame_sdl2 as pygame
        width, height = config.screen_width, config.screen_height
        root = renpy.display.layout.Fixed()
        scene = os.environ.get("URMTB_TEST_SCENE")
        if picture and scene:
            with open(scene, "rb") as file:
                root.add(im.Scale(im.Data(file.read(), "urmtb_test_scene.png"), width, height))
        else:
            root.add(Solid("#e6d4aa", xysize=(width, height)))
        root.add(sd)
        root.visit_all(lambda d: d.per_interact())
        result = renpy.display.render.render_screen(root, width, height)
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        renpy.display.swdraw.draw(surf, None, result, 0, 0, True)
        if picture:
            pygame.image.save(surf, picture)
        return surf

    def _tb_bars(check, pic):
        import pygame_sdl2 as pygame
        ds = renpy.display.screen
        focus = renpy.display.focus
        tag = "urmh_settings"
        section = _urmh_state().section
        _urmh_state().section = "look"
        settings = ds.ScreenDisplayable(ds.get_screen_variant(tag), tag, "screens", scope={"_kwargs": {}})

        def bar():
            return settings.widgets[("textbox_opacity", True)]

        def event(kind, x):
            active = bar()
            ev = pygame.event.Event(kind, {"button": 1, "mod": 0})
            try:
                active.event(ev, x, active.height // 2, 0)
            except renpy.display.core.IgnoreEvent:
                pass
            _tb_redraw(settings)
            _tb_render(settings)
            focus.before_interact([settings])

        try:
            settings.update()
            _tb_render(settings, pic("textbox_settings"))
            focus.before_interact([settings])
            focus.set_focused(bar(), None, settings)
            event(pygame.MOUSEBUTTONDOWN, bar().width)
            grabbed = focus.get_grab() is bar()
            event(pygame.MOUSEMOTION, bar().width // 2)
            middle = _urm_row_view("textbox_opacity").shared
            check("a held drag follows the slider through a redraw",
                  grabbed and focus.get_grab() is bar() and 45 <= middle <= 55, repr(middle))
            event(pygame.MOUSEMOTION, 0)
            check("the drag reaches zero", _urm_row_view("textbox_opacity").shared == 0)
            event(pygame.MOUSEBUTTONUP, bar().width)
            check("the drag reaches 100 and releases",
                  _urm_row_view("textbox_opacity").shared == 100 and focus.get_grab() is None)
        finally:
            focus.set_grab(None)
            focus.set_focused(None, None, None)
            _urmh_state().section = section
            _urm_setting_set("urmcTextboxOpacity", None, True)

    def _tb_probe_body(lines, check, pic):
        config.screen_width, config.screen_height = 1280, 720
        renpy.game.context().init_phase = False
        text = "The last train left an hour ago. So who turned on the light?"
        dlg = _tb_begin("Mara", text)
        check("defaults to the game's own screen", _urm_setting("urmcTextboxStyle") == "game"
              and dlg.widgets["window"] is dlg.child.children[0])
        own = _tb_render(dlg, pic("textbox_own"))
        check("game background starts fully opaque", tuple(own.get_at((400, 700)))[:3] == (32, 35, 42))
        _urm_row_pick("textbox_opacity", 45)
        _tb_redraw(dlg)
        half = _tb_render(dlg)
        dim = tuple(half.get_at((400, 700)))[:3]
        check("game background opacity blends into the scene",
              all(a < b < c for a, b, c in zip((32, 35, 42), dim, (230, 212, 170))), repr(dim))
        _urm_row_pick("textbox_opacity", 0)
        _tb_redraw(dlg)
        clear = _tb_render(dlg)
        scene = tuple(clear.get_at((20, 700)))
        check("zero opacity clears the background", tuple(clear.get_at((400, 700))) == scene)
        check("zero opacity leaves the dialogue visible",
              any(tuple(clear.get_at((x, y))) != scene
                  for x in range(200, 420) for y in range(598, 643)))
        _urm_row_clear("textbox_opacity")
        _tb_redraw(dlg)
        restored = _tb_render(dlg)
        check("clear returns to the inherited game opacity",
              tuple(restored.get_at((400, 700))) == tuple(own.get_at((400, 700))))
        style_view = _urm_row_view("textbox_style")
        check("settings offer both picked styles", [a for a, b in style_view.options] ==
              ["Game's own", "Glass strip", "Subtitles"])
        bar_view = _urm_row_view("textbox_opacity")
        check("settings expose an adjustable percentage", bar_view.percent and bar_view.value == 100)
        bar = urmh_percent_adjustment("textbox_opacity", bar_view.value, False)
        bar.change(37)
        check("adjusting the slider updates the setting", bar.range == 100
              and _urm_row_view("textbox_opacity").value == 37)
        _urm_row_clear("textbox_opacity")
        _tb_bars(check, pic)

        for mode in ("glass", "subtitles"):
            _urm_row_pick("textbox_style", mode)
            _tb_redraw(dlg)
            what, who = dlg.widgets["what"], dlg.widgets["who"]
            check(mode + " uses the game's real speaker and dialogue widgets",
                  dlg.child.children[0].child.children == [who, what]
                  and what is renpy.display.screen.get_widget("say", "what", dlg.layer))
            old_window = dlg.child.children[0]
            dlg.update()
            check(mode + " is built once per screen update", old_window is dlg.child.children[0])
            check(mode + " preserves independent game widgets", len(dlg.child.children) == 2)
            _tb_render(dlg, pic("textbox_" + mode))
            faded = _tb_begin(None, text + " " + text + " " + text)
            check(mode + " fits multiple narrator lines", faded.child.children[0].child.children ==
                  [faded.widgets["what"]])
            _tb_render(faded, pic("textbox_" + mode + "_narrator"))
            dlg = _tb_begin("Mara", text)
        phone = _tb_begin("Mara", "This is a phone message.", screen="_tb_phone")
        check("custom dialogue screen keeps its own window", phone.child.children[0] is phone.widgets["window"])
        _urm_row_pick("textbox_style", "game")
        _tb_redraw(dlg)
        check("switching back restores the native window on the same line",
              dlg.child.children[0] is dlg.widgets["window"]
              and not hasattr(dlg.widgets["what"], "_urmtb_original_style")
              and dlg.widgets["what"].style.yoffset == 48)
        _urm_row_clear("textbox_style")
        renpy.hide_screen("say", layer=dlg.layer)
        renpy.hide_screen("_tb_phone", layer=phone.layer)

    def _tb_probe(lines, check, pic):
        import copy
        ds = renpy.display.screen
        sizes = (config.screen_width, config.screen_height)
        ctx = renpy.game.context()
        init_phase = ctx.init_phase
        key = ("say", config.variants[0])
        original = ds.screens.get(key)
        try:
            def bind(fixture):
                screen = copy.copy(ds.get_screen_variant(fixture))
                screen.name = ("say",)
                ds.screens[key] = screen

            bind("_tb_fixture")
            _tb_probe_body(lines, check, pic)
            bind("_tb_fixture_reversed")
            _urm_row_pick("textbox_style", "glass")
            reversed_sd = _tb_begin("Mara", "The game orders dialogue before the name.")
            check("reversed widget order still uses the picked layout",
                  reversed_sd.child.children[0].child.children ==
                  [reversed_sd.widgets["who"], reversed_sd.widgets["what"]])
            bind("_tb_fixture_separate")
            _tb_probe_separate(check, pic)
        finally:
            _urm_row_clear("textbox_style")
            _urm_row_clear("textbox_opacity")
            renpy.hide_screen("say", layer=config.say_layer)
            renpy.hide_screen("_tb_phone", layer=config.say_layer)
            if original is None:
                ds.screens.pop(key, None)
            else:
                ds.screens[key] = original
            config.screen_width, config.screen_height = sizes
            ctx.init_phase = init_phase

    def _tb_probe_separate(check, pic):
        _urm_row_pick("textbox_style", "game")
        text = "The last train left an hour ago. So who turned on the light?"
        dlg = _tb_begin("Mara", text)
        sample = (400, 680)
        side = (25, 260)
        native = _tb_render(dlg, pic("textbox_separate_game"))
        own = tuple(native.get_at(sample))[:3]
        scene = tuple(native.get_at((20, 700)))[:3]
        side_colour = tuple(native.get_at(side))[:3]
        check("separate game draws side art",
              all(abs(a - b) <= 1 for a, b in zip(side_colour, (254, 108, 25))), repr(side_colour))
        pixels = {}
        for percent in (50, 0, 100):
            _urm_row_pick("textbox_opacity", percent)
            _tb_redraw(dlg)
            surf = _tb_render(dlg)
            pixels[percent] = tuple(surf.get_at(sample))[:3]
            check("separate background opacity preserves the line", dlg.widgets["what"].style.xpos == 240)
        check("separate game background at 50% blends into the scene",
              all(a < b < c for a, b, c in zip(own, pixels[50], scene)), repr(pixels[50]))
        # The software renderer can round a transparent blit by one.
        check("separate game background at 0% reveals the scene",
              all(abs(a - b) <= 1 for a, b in zip(pixels[0], scene)), repr(pixels[0]))
        check("separate game background at 100% restores its own opacity", pixels[100] == own)
        for mode in ("glass", "subtitles"):
            _urm_row_pick("textbox_style", mode)
            _tb_redraw(dlg)
            root = dlg.child
            words, speaker = (dlg.widgets[key] for key in ("what", "who"))
            surf = _tb_render(dlg, pic("textbox_separate_" + mode))
            check("separate " + mode + " uses the original text and leaves side art in place",
                  len(root.children) == 2 and tuple(surf.get_at(side))[:3] == side_colour
                  and getattr(root.children[0].child, "children", None) == [speaker, words]
                  and words is renpy.display.screen.get_widget("say", "what", dlg.layer))
        narrator_sd = _tb_begin(None, text)
        check("separate narration uses the original dialogue widget",
              len(narrator_sd.child.children) == 2 and
              getattr(narrator_sd.child.children[0].child, "children", None) == [narrator_sd.widgets["what"]])
        _urm_row_pick("textbox_style", "game")
        _tb_redraw(dlg)
        check("switching back restores the separate text and background",
              dlg.child.children[1:3] == [dlg.widgets["who"], dlg.widgets["what"]]
              and dlg.widgets["what"].style.xpos == 240
              and tuple(_tb_render(dlg).get_at(sample))[:3] == own)

        _urm_row_pick("textbox_style", "glass")
        _urm_row_pick("textbox_opacity", 0)
        ambiguous = _tb_begin("Mara", text, second_background=True)
        pixel = tuple(_tb_render(ambiguous).get_at(sample))[:3]
        check("two unidentified backgrounds leave the custom layout alone",
              len(ambiguous.child.children) == 5 and ambiguous.child.children[2] is ambiguous.widgets["what"]
              and pixel == own, repr((len(ambiguous.child.children), pixel, own)))
'''

PROBE_ENTRY = "_tb_probe"
PROBE_PIC_ENV = "URMTB_PICTURES"
PROBE_TAG_ENV = "URMTB_TAG"
PROBE_MIN_ENGINES = 2

if __name__ == "__main__":
    sys.exit(prop_probes.main_single(__file__, sys.argv))
