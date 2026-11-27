"""
Checks the screen kit (16_kit) and the screens drawn with it, in each
prop's own engine.

    python check_kit.py <props folder> [--record] [--pictures <folder>]

Each prop's engine is started read-only, with its `lint` command replaced,
on a base folder of its own (a temporary folder: nothing is written to the
prop), as check_pins.py does. That folder's game/ holds the kit's block as
the add-on joins it (urm_source), our screen files of the kit and of the
screens drawn with it (game_screens), the fonts the kit names (our
Roboto and icon fonts from urm_compat/fonts), and a sheet of every part:
chips in
each tone, every button, a card, a bubble, the alert banner with words of
its own. The engine lays them out and draws them (its software renderer).

What is checked:
  - every part is centred: a chip's and a button's words (and an icon) in
    the middle of the part, within half a pixel by the engine's own layout;
    an icon and a capital word by their ink within a pixel; the banner in
    the middle of the screen; the banner's panel is the drawn one (960 wide
    at 1080 lines, 32 from the top);
  - the soft grey surface transmits 40 to 45 percent of the scene. Its
    opaque foreground is readable over black, the darkest scene;
  - nothing moved by accident: the box of every part on the sheet and in
    the banner is compared with tests/baseline/kit_layout.txt, one list per
    engine version. A change you meant: run with --record and look at the
    pictures before committing the new list.

--pictures writes, per engine, the banner over a bright and over a dark
scene (made here, no game's art) and the parts sheet, 1920x1080 PNGs.

The Flags dialog keeps its control sizes and takes the glass palette.
The legacy gallery button and code helpers still use the compatibility
palette. LOOK draws the Flags dialog and checks the old input and veil
behavior.

A protected engine ignores loose script files: it is listed and skipped.
Every other prop must pass.
"""

from __future__ import print_function

import glob
import io
import os
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(TOOLKIT, "single"))

import urm_source  # noqa  (the add-on's code, joined from its pieces)

BASELINE = os.path.join(HERE, "baseline", "kit_layout.txt")
SCREEN_FILES = ("16_kit.rpy", "17_hub.rpy", "18_code_view.rpy", "85_alerts.rpy")

SHEET = u'''
init -1 python:
    # A game made at 1920x1080, as most are (a prop has no gui: 800x600).
    config.screen_width, config.screen_height = 1920, 1080
    def _probe_notl(tag, argument, contents):
        return contents
    config.custom_text_tags["urm_notl"] = _probe_notl

screen probe_parts():
    vbox:
        pos (64, 64)
        spacing 24
        hbox:
            spacing 8
            for _t in URMK_TONES:
                use urmk_chip("Elena love +1", _t)
        hbox:
            spacing 8
            use urmk_button("OK", NullAction(), "main")
            use urmk_button("Close", NullAction(), "plain")
            use urmk_button("Stop alerting", NullAction(), "quiet")
            use urmk_button("", NullAction(), "plain", "small", "\\ue5cd")
            use urmk_button("Change", NullAction(), "main", "small")
            use urmk_button("Copy", NullAction(), "plain", "small", "\\ue14d")
        hbox:
            spacing 32
            use urmk_window("card", xa=0.0, width=336, pad=(16, 16)):
                vbox:
                    spacing 8
                    text "Stay at the party." style "urmk_m"
                    use urmk_chip("Mark trust +1", "gain")
            use urmk_window("bubble", xa=0.0, width=352, pad=(16, 16)):
                text "The game picks this way." style "urmk_s"
            use urmk_window("window", xa=0.0, width=416, pad=(32, 24)):
                vbox:
                    text "Elena love" style "urmk_l"
                    text "48 1" style "urmk_xl"

# The parts of the URM+ menu and settings page, the menu laid out as the
# drawing (research/hub_button, drawing A), and the button that drags.
screen probe_menu_parts():
    hbox:
        pos (64, 64)
        spacing 48
        use urmk_window(xa=0.0, width=400, pad=(8, 8)):
            vbox:
                use urmk_menu_row("Route map", "\\uf184", NullAction(), key_words="Alt+G")
                use urmk_menu_row("Flags", "\\ue153", NullAction(), count="12")
                use urmk_menu_row("Alerts", "\\ue7f4", NullAction(), count="2 on", unfold=True)
                use urmk_menu_item("Elena love", "Stop", NullAction())
                use urmk_menu_item("Took the key", "Stop", NullAction())
                use urmk_divider()
                use urmk_menu_row("Skip unseen text", "\\ue01f", NullAction(), on=False)
                use urmk_menu_row("Gallery: unlock all", "\\ue413", NullAction(), on=True)
                use urmk_menu_row("Back to last choice", "\\ue166", NullAction())
                use urmk_divider()
                use urmk_menu_row("Settings", "\\ue8b8", NullAction(), more=True)
        use urmk_window(xa=0.0, width=720, pad=(32, 24)):
            vbox:
                spacing 24
                hbox:
                    spacing 16
                    use urmk_switch(False)
                    use urmk_switch(True)
                use urmk_choices([("Off", NullAction(), False), ("1 line", NullAction(), False),
                                  ("2 lines", NullAction(), False), ("3 lines", NullAction(), True)])
                hbox:
                    spacing 16
                    use urmk_choices([("Skip them", NullAction(), True), ("Stop on them", NullAction(), False)], held=True)
                    use urmk_button("Clear", NullAction(), "quiet", "small")
    use urmk_drag("probe_button", keep="probe_pos", every_game=True, x=-16, y=16, size=(160, 48)):
        use urmk_button("MRM", None, "main", "small", "\\ue945")

# A chip in a room narrower than its words (the corner card's column on
# Neuvau, 2026-11-22): its words wrap, and the chip must hold both lines.
screen probe_narrow_chip():
    hbox:
        pos (64, 64)
        box_wrap True
        spacing 8
        xmaximum urmk_px(240)
        use urmk_chip("Ch1 maureen bj cum: on (sometimes) after the club", "gain")
        use urmk_chip("Lust +1", "gain")

init 1999 python:
    # The doorway is the real one (its block is loaded): where a dragged
    # part was dropped is kept there. The URM+ menu shows what features
    # registered: stand-ins here, as drawing A has them.
    _urmi_layer = "screens"
    _urm_in_game = lambda: True       # the probe stands where the story runs
    _urm_setting_add("probe_pos", None)
    _urm_entry_add("route_map", "Route map", u"\\uf184", lambda: None, key="alt_K_g",
                   key_words="Alt+G", group=1, order=10)
    _urm_entry_add("flags", "Flags", u"\\ue153", lambda: None, count=lambda: u"12", group=1, order=20)
    _urm_entry_add("alerts", "Alerts", u"\\ue7f4", None, count=lambda: u"2 on",
                   items=lambda: [(u"Elena love", u"Stop", lambda: None),
                                  (u"Took the key", u"Stop", lambda: None)], group=1, order=30)
    _urm_entry_add("skip_unseen", "Skip unseen text", u"\\ue01f", lambda: None,
                   on=lambda: False, group=2, order=10)
    _urm_entry_add("gallery_all", "Gallery: unlock all", u"\\ue413", lambda: None,
                   on=lambda: True, group=2, order=20)
    _urm_entry_add("back", "Back to last choice", u"\\ue166", lambda: None, group=2, order=30)
    # a feature whose count fails: left out, the menu still draws
    _urm_entry_add("broken", "Broken", u"\\ue153", lambda: None, count=lambda: 1 // 0, group=1, order=40)
    _urm_setting_add("probeTypos", 3)
    _urm_setting_add("probeStrict", False)
    _urm_setting_add("probeAhead", 20)
    probe_engine = {"unseen": False}
    _urm_row_add("typos", "skipping", "Skip past small changes",
                 "When an update rewords lines you have read, skipping carries on.",
                 (("Off", 0), ("1 line", 1), ("2 lines", 2), ("3 lines", 3)), setting="probeTypos", order=10)
    _urm_row_add("strict", "skipping", "Replies to new choices",
                 "A short reply to a choice you have not picked before.",
                 (("Skip them", False), ("Stop on them", True)), setting="probeStrict", order=20)
    _urm_row_add("unseen", "skipping", "Skip unseen text", "Skipping runs through text you have never read.",
                 (("On", True), ("Off", False)), get=lambda: probe_engine["unseen"],
                 put=lambda v: probe_engine.__setitem__("unseen", v), order=30)
    _urm_row_add("ahead", "skipping", "Path look-ahead",
                 "How far ahead to look for the next choice. Raise it if a long scene hides one.",
                 (("20", 20), ("50", 50), ("100", 100), ("200", 200)), setting="probeAhead", order=40)
    _urm_row_add("branch", "story", "Branch notification",
                 "Says when the line on screen is there only because of a check or a choice you made.",
                 (("Branches and skipped parts", 2), ("Branches", 1), ("Off", 0)), setting="probeAhead", order=10)

    import os

    # the banner's words: a menu that tests a marked name (or three, with
    # long names); a number test (row 1) says goal words, any other test
    # (row 2) a verdict, as 85_alerts draws them
    probe_names = [u"Elena love"]

    def urmal_view():
        return (u"Elena love checked in Chapter 4",
                [(u'The choice "Walk her home" needs it', u"you have 1, needs 3", "loss"),
                 (u"Elena knows the secret", u"passes: what it gates plays now", "gain")],
                True, probe_names)

    def urmal_close():
        pass

    def urmal_stop(name):
        pass

    def _urmi_safe(text):
        return text

    def _probe_png(w, h, colour_at):
        import struct, zlib
        rows = bytearray()
        for j in range(h):
            rows.append(0)
            for i in range(w):
                rows.extend(colour_at(i, j))

        def chunk(kind, data):
            body = kind + data
            return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)

        return (bytes(bytearray((137, 80, 78, 71, 13, 10, 26, 10)))
                + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(bytes(rows))) + chunk(b"IEND", b""))

    def _probe_bright(i, j):
        # a sunny sky over pale sand, white clouds, hard bright edges: the
        # worst a see-through panel meets
        sky = j < 160
        r, g, b = ((150 + j // 2, 205 + j // 6, 255) if sky else (250, 236 - (j - 160) // 4, 200))
        if ((i - 140) ** 2) / 3600.0 + ((j - 50) ** 2) / 700.0 < 1 or ((i - 330) ** 2) / 5000.0 + ((j - 40) ** 2) / 500.0 < 1:
            r, g, b = 255, 255, 255
        if 200 < i < 260 and 120 < j < 200:
            r, g, b = 255, 120, 60
        if (i // 12 + j // 12) % 2 and j > 210:
            r, g, b = 255, 250, 235
        return (min(255, r), min(255, g), min(255, b), 255)

    def _probe_dark(i, j):
        # night: deep blue to black, a few lit windows
        r, g, b = 10, 14, max(0, 50 - j // 6)
        if 300 < i < 420 and 120 < j < 260 and (i // 8) % 3 == 0 and (j // 10) % 2 == 0:
            r, g, b = 255, 210, 120
        return (r, g, b, 255)

    probe_bright = Transform(im.Data(_probe_png(480, 270, _probe_bright), "probe_bright.png"), zoom=4)
    probe_white = Transform(im.Data(_probe_png(4, 4, lambda i, j: (255, 255, 255, 255)), "probe_white.png"), zoom=480)
    probe_black = Transform(im.Data(_probe_png(4, 4, lambda i, j: (0, 0, 0, 255)), "probe_black.png"), zoom=480)
    probe_slate = Transform(im.Data(_probe_png(4, 4, lambda i, j: (32, 34, 39, 255)), "probe_slate.png"), zoom=480)
    probe_dark = Transform(im.Data(_probe_png(480, 270, _probe_dark), "probe_dark.png"), zoom=4)

    def _probe_lint():
        lines = []

        def check(name, ok, detail=""):
            lines.append("%s  %s%s" % ("pass" if ok else "FAIL", name,
                                       ("  " + detail) if detail else ""))

        try:
            renpy.style.rebuild()
            renpy.display.screen.prepare_screens()
            config.developer = False
            __import__("renpy.display.swdraw")
            import pygame_sdl2 as pygame
            # The engine's own software renderer, without a window: the
            # displayables take its path ("sw": a Frame is cut and scaled as
            # pictures), and swdraw draws the frame. Drawing the hardware
            # path's frame with swdraw instead leaves a Frame's corners wrong.
            class _ProbeDraw(object):
                draw_per_virt = 1.0
                draw_to_virt = renpy.display.render.IDENTITY
                virt_to_draw = renpy.display.render.IDENTITY
                info = {"renderer": "sw", "models": False}

                def mutated_surface(self, surf):
                    pass

                def load_texture(self, surf, *args, **kwargs):
                    return surf.copy()

                def ready_one_texture(self):
                    return False

                def render_to_texture(self, what, alpha):
                    w, h = what.get_size()
                    surf = pygame.Surface((max(1, int(w)), max(1, int(h))), pygame.SRCALPHA)
                    surf.fill((0, 0, 0, 0))
                    renpy.display.swdraw.draw(surf, None, what, 0, 0, True)
                    return surf

                def __getattr__(self, name):
                    raise AttributeError("probe draw: " + name)
            renpy.display.draw = _ProbeDraw()
            W, H = config.screen_width, config.screen_height

            def screen(name, under=None):
                """The screen laid out and rendered as one frame, over a
                scene when given: (the root's render, its displayable)."""
                root = renpy.display.layout.Fixed()
                if under is not None:
                    root.add(under)
                sd = renpy.display.screen.ScreenDisplayable(
                    renpy.display.screen.get_screen_variant(name), name, "screens",
                    scope={"_kwargs": {}})
                sd.update()
                sd.visit_all(lambda d: d.per_interact())
                root.add(sd)
                return renpy.display.render.render_screen(root, W, H), root

            def parts(rv):
                """[(kind, words, x, y, w, h)]: every window, button and
                text the render holds, in drawing order, by the engine's
                own layout."""
                out = []
                seen = set()

                def walk(r, x, y):
                    for d in getattr(r, "render_of", ()) or ():
                        if id(d) in seen:
                            continue
                        kind = None
                        if isinstance(d, renpy.display.behavior.Button):
                            kind = "button"
                        elif isinstance(d, renpy.display.layout.Window):
                            kind = "window"
                        elif isinstance(d, renpy.text.text.Text):
                            kind = "text"
                        if kind:
                            seen.add(id(d))
                            words = u"".join(t for t in d.text if isinstance(t, (type(u""), type("")))) if kind == "text" else u""
                            out.append((kind, words, x, y, r.width, r.height))
                    for c in r.children:
                        if isinstance(c[0], renpy.display.render.Render):
                            walk(c[0], x + c[1], y + c[2])

                walk(rv, 0, 0)
                return out

            def picture(rv, path=None):
                surf = pygame.Surface((W, H), pygame.SRCALPHA)
                surf.fill((0, 0, 0, 0))
                renpy.display.swdraw.draw(surf, None, rv, 0, 0, True)
                if path:
                    # saved solid: every picture is drawn over a solid scene,
                    # and the alpha the drawing leaves is not what is seen
                    # (pixel by pixel: slow, so only with --pictures)
                    import struct, zlib
                    rows = bytearray()
                    for j in range(H):
                        rows.append(0)
                        for i in range(W):
                            c = surf.get_at((i, j))
                            rows.extend((c[0], c[1], c[2]))

                    def chunk(kind, data):
                        body = kind + data
                        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)

                    with open(path, "wb") as fh:
                        fh.write(bytes(bytearray((137, 80, 78, 71, 13, 10, 26, 10)))
                                 + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
                                 + chunk(b"IDAT", zlib.compress(bytes(rows))) + chunk(b"IEND", b""))
                return surf

            def inside(a, b):
                return (a[2] >= b[2] - 0.5 and a[3] >= b[3] - 0.5 and a[2] + a[4] <= b[2] + b[4] + 0.5
                        and a[3] + a[5] <= b[3] + b[5] + 0.5)

            def centre(a):
                return (a[2] + a[4] / 2.0, a[3] + a[5] / 2.0)

            # ---- the parts sheet
            rv, _root = screen("probe_parts")
            sheet = parts(rv)
            chip_h = urmk_px(URMK_CHIP[0])
            off = []
            for w in [p for p in sheet if p[0] in ("window", "button")]:
                if w[0] == "window" and abs(w[5] - chip_h) > 0.5:
                    continue                    # a panel, not a chip
                inner = [p for p in sheet if p[0] == "text" and inside(p, w)]
                if not inner:
                    off.append("%s %r: nothing inside" % (w[0], w[1]))
                    continue
                xs = [p[2] for p in inner] + [p[2] + p[4] for p in inner]
                ys = [p[3] for p in inner] + [p[3] + p[5] for p in inner]
                cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
                wx, wy = centre(w)
                if abs(cx - wx) > 0.5 or abs(cy - wy) > 0.5:
                    off.append("%s holding %r off by %+.1f, %+.1f" % (w[0], inner[-1][1], cx - wx, cy - wy))
            check("every chip's and button's words sit in its middle", not off, "; ".join(off))

            # a chip whose words wrap holds both lines, apart from the next
            # chip; a chip of one line is the chip's height, as it was - at
            # every screen height, and in the large text where its line
            # still fits (Neuvau's corner card, 2026-11-22)
            bad = []
            for height in (480, 600, 720, 768, 800, 900, 1017, 1080, 1200, 1440, 2160):   # HEIGHTS
                for scale in (1.0, URMH_LARGE):
                    config.screen_width, config.screen_height = int(round(height * 16 / 9.0)), height
                    urmk_look.text = scale
                    urmk_restyle()
                    renpy.style.rebuild()
                    root_ = renpy.display.layout.Fixed()
                    sd_ = renpy.display.screen.ScreenDisplayable(
                        renpy.display.screen.get_screen_variant("probe_narrow_chip"), "probe_narrow_chip",
                        "screens", scope={"_kwargs": {}})
                    sd_.update()
                    root_.add(sd_)
                    narrow = parts(renpy.display.render.render_screen(root_, config.screen_width, height))
                    chips_ = [p for p in narrow if p[0] == "window"]
                    words_ = [p for p in narrow if p[0] == "text"]
                    held = [t[1] for t in words_ if not [c for c in chips_ if inside(t, c)]]
                    overlap = [a[2:] for i, a in enumerate(chips_) for b in chips_[i + 1:]
                               if a[2] < b[2] + b[4] and b[2] < a[2] + a[4]
                               and a[3] < b[3] + b[5] and b[3] < a[3] + a[5]]
                    line = urmk_px(URMK_TEXT["s"][1] * scale)
                    one = max(urmk_px(URMK_CHIP[0]), line)
                    if (len(chips_) != 2 or held or overlap or chips_[0][5] <= one + 0.5
                            or abs(chips_[1][5] - one) > 0.5):
                        bad.append("%d lines, text x%s: chips %r; words outside %r; overlapping %r"
                                   % (height, scale, [c[2:] for c in chips_], held, overlap))
            config.screen_width, config.screen_height = W, H
            urmk_look.text = 1.0
            urmk_restyle()
            renpy.style.rebuild()
            check("a chip whose words wrap holds both lines, apart from the next chip; "
                  "one line is the chip's height, at every screen height",
                  not bad, "; ".join(bad[:3]))

            # the ink: an icon alone, and a capital word, centred by what is drawn
            def ink_off(part, colour):
                surf = picture(rv)
                want = tuple(renpy.easy.color(colour))[:3]
                x0, y0, w, h = [int(round(v)) for v in part[2:]]
                pts = []
                for py in range(y0, y0 + h):
                    for px in range(x0, x0 + w):
                        r, g, b, a = surf.get_at((px, py))
                        if max(abs(r - want[0]), abs(g - want[1]), abs(b - want[2])) < 48:
                            pts.append((px, py))
                if not pts:
                    return None
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                cx = (min(xs) + max(xs) + 1) / 2.0
                cy = (min(ys) + max(ys) + 1) / 2.0
                return cx - (part[2] + part[4] / 2.0), cy - (part[3] + part[5] / 2.0)

            buttons = [p for p in sheet if p[0] == "button"]
            ok_button = buttons[0]
            icon_button = [b for b in buttons if abs(b[4] - b[5]) < 0.5][0]
            worst = []
            for what, part, colour in (("OK", ok_button, URMK_COLOURS["on-accent"]),
                                       ("the close icon", icon_button, URMK_COLOURS["ink"])):
                got = ink_off(part, colour)
                if got is None or max(abs(got[0]), abs(got[1])) > 1.0:
                    worst.append("%s off by %s" % (what, "nothing drawn" if got is None else "%+.1f, %+.1f" % got))
            check("an icon and a capital word are centred by their ink", not worst, "; ".join(worst))

            # The focus veil remains visible on pale glass. The standalone
            # accent button keeps its existing weaker hover.
            mid = urmk_back("quiet", hover=True).image.image.load()
            got = mid.get_at((mid.get_width() // 2, mid.get_height() // 2))
            check("a quiet button pointed at shows the glass focus veil",
                  tuple(got) == (255, 255, 255, 72), "%r" % (tuple(got),))

            # ---- the banner
            rv, _root = screen("urmal_alert")
            banner = parts(rv)
            panel = [p for p in banner if p[0] == "window"][0]
            check("the banner is the drawn one: 960 wide, 32 from the top",
                  abs(panel[4] - urmk_px(960)) < 0.5 and abs(panel[3] - urmk_px(32)) < 0.5,
                  "%r" % (panel[2:],))
            check("the banner is in the middle of the screen", abs(centre(panel)[0] - W / 2.0) <= 0.5,
                  "%+.1f" % (centre(panel)[0] - W / 2.0))
            # A bare part of the panel over white and black measures how
            # much of the scene gets through the glass.
            px_, py_ = int(panel[2] + panel[4] - 6), int(panel[3] + panel[5] / 2.0)
            seen = []
            for under in (probe_white, probe_black):
                seen.append(picture(screen("urmal_alert", under)[0]).get_at((px_, py_)))
            transmission = [(seen[0][c] - seen[1][c]) / 255.0 for c in range(3)]
            check("the alert's glass transmits 40 to 45 percent of the scene",
                  all(.40 <= a <= .45 for a in transmission), str(transmission))

            def luminance(rgb):
                channels = [c / 255.0 for c in rgb[:3]]
                linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
                return sum(v * weight for v, weight in zip(linear, (.2126, .7152, .0722)))

            def contrast(one, two):
                low, high = sorted((luminance(one), luminance(two)))
                return (high + .05) / (low + .05)

            darkest = seen[1]
            direct = [(key, urmk_colour(key)) for key in ("ink", "ink-muted", "ink-faint", "accent-ink")]
            direct.extend((tone, urmk_tone_ink(tone)) for tone in URMK_TONES)
            ratios = [(name, contrast(renpy.easy.color(ink), darkest)) for name, ink in direct]
            check("text and tone ink read on glass over black at 4.5:1",
                  all(ratio >= 4.5 for name, ratio in ratios),
                  repr([(name, round(ratio, 2)) for name, ratio in ratios]))
            chip_issues = []
            for tone in URMK_TONES:
                for faded in (False, True):
                    ink = renpy.easy.color(urmk_chip_ink(tone, faded))
                    fill = renpy.easy.color(urmk_chip_fill(tone, faded))
                    ratio = contrast(ink, fill)
                    if ink[3] != 255 or fill[3] != 255 or ratio < 4.5:
                        chip_issues.append((tone, faded, ink, fill, ratio))
            check("normal and faded chips stay opaque and read at 4.5:1", not chip_issues, repr(chip_issues))
            overview = renpy.easy.color(urmk_colour("overview-accent"))
            neighbours = [renpy.easy.color(urmk_colour(key)) for key in ("surface", "ink-muted")]
            ratios = [contrast(overview, neighbour) for neighbour in neighbours]
            check("the overview's blue marks distinguish both the panel and ordinary marks at 3:1",
                  all(ratio >= 3.0 for ratio in ratios), repr([round(ratio, 2) for ratio in ratios]))

            # three long names: every part still inside the panel
            store.probe_names = [u"Elena love with a long name", u"Mark trust with a long name",
                                 u"Took the key in Chapter 2"]
            rv3, _root = screen("urmal_alert")
            three = parts(rv3)
            panel3 = [p for p in three if p[0] == "window"][0]
            out3 = [p[1] or p[0] for p in three if p is not panel3 and not inside(p, panel3)]
            check("with three names every part stays inside the banner", not out3, repr(out3[:3]))
            store.probe_names = [u"Elena love"]

            # ---- the URM+ menu's parts
            rv, _root = screen("probe_menu_parts")
            menu = parts(rv)
            near = lambda a, b: abs(a - b) <= 0.5
            frames = [p for p in menu if p[0] == "window"]
            sw = urmk_px(URMK_SWITCH[0])
            tracks = [p for p in frames if near(p[4], sw) and near(p[5], urmk_px(URMK_SWITCH[1]))]
            knobs = [p for p in frames if near(p[4], urmk_px(URMK_SWITCH[2])) and near(p[5], urmk_px(URMK_SWITCH[2]))]
            gap = urmk_px(URMK_SWITCH[3])
            spots = [(k[2] - t[2], k[3] - t[3]) for t in tracks for k in knobs if inside(k, t)]
            check("a switch is the drawn one: 48 by 28, its knob 4 in, at the left when off, the right when on",
                  len(tracks) >= 2 and spots[:2] == [(gap, gap), (sw - urmk_px(URMK_SWITCH[2]) - gap, gap)]
                  if len(spots) >= 2 else False, "%r %r" % ([t[2:] for t in tracks], spots))
            rows_ = [p for p in menu if p[0] == "button" and near(p[5], urmk_px(URMK_ROW[0]))]
            off = []
            for row in rows_:
                inner = [p for p in menu if p[0] in ("text", "window") and p is not row and inside(p, row)
                         and not near(p[5], urmk_px(URMK_SWITCH[2]))]
                said = [p[1] for p in inner if p[0] == "text"][1:2] or [""]
                for p in inner:
                    if not near(p[3] + p[5] / 2.0, row[3] + row[5] / 2.0):
                        off.append("%r in the row of %r off by %+.1f" % (p[1] or p[0], said[0],
                                                                       p[3] + p[5] / 2.0 - row[3] - row[5] / 2.0))
            check("a menu row is 48 high and 384 wide in a 400 menu, all it holds in its middle",
                  len(rows_) == 7 and all(near(r[4], urmk_px(400 - 16)) for r in rows_) and not off,
                  "%d rows, widths %r; %s" % (len(rows_), sorted(set(round(r[4], 1) for r in rows_)), "; ".join(off[:3])))
            choices = [p for p in menu if p[0] == "button" and near(p[5], urmk_px(URMK_CHOICES[2]))]
            off = []
            for b in choices:
                inner = [p for p in menu if p[0] == "text" and inside(p, b)]
                if not inner or not (near(centre(inner[0])[0], centre(b)[0]) and near(centre(inner[0])[1], centre(b)[1])):
                    off.append(repr(inner[0][1] if inner else "nothing"))
            grounds = [p for p in frames if near(p[5], urmk_px(URMK_CHOICES[0]))]
            check("a row of choices is 40 high, each choice 32, its words in its middle",
                  len(grounds) == 2 and len(choices) == 6 and not off, "%d grounds, %d choices; %s" % (len(grounds), len(choices), off))
            # a line: one pixel, 16 in from the sides and 8 off the rows,
            # so its part is the menu's width and 17 high
            lines_ = [p for p in frames if near(p[5], max(1, urmk_px(1)) + 2 * urmk_px(8))]
            check("a line between groups is one pixel with 8 above and below, 16 in from each side",
                  len(lines_) == 2 and all(near(l[4], urmk_px(400 - 16)) for l in lines_), "%r" % ([l[2:] for l in lines_],))
            panel_ = [p for p in frames if near(p[4], urmk_px(400))][0]
            inner_x = panel_[2] + urmk_px(8)
            folded = [p for p in menu if p[0] == "text" and p[1] in (u"Elena love", u"Took the key")]
            stops = [p for p in menu if p[0] == "button" and [t for t in menu if t[0] == "text" and t[1] == u"Stop" and inside(t, p)]]
            check("a row folded out: its words in line with the rows' words (56 in), a quiet Stop at the right",
                  len(folded) == 2 and all(near(f[2], inner_x + urmk_px(56)) for f in folded) and len(stops) == 2
                  and all(near(s[2] + s[4], inner_x + urmk_px(400 - 16)) for s in stops)
                  and near(stops[1][3] - stops[0][3], urmk_px(40)),
                  "%r %r" % ([f[2:] for f in folded], [s[2:] for s in stops]))

            def dragged_button(found):
                return [p for p in found if p[0] == "button"
                        and [t for t in found if t[0] == "text" and t[1] == u"MRM" and inside(t, p)]]

            button = dragged_button(menu)
            check("a dragged part sits where it is put until it is dropped: 16 from the top right",
                  len(button) == 1 and near(button[0][2] + button[0][4], W - urmk_px(16)) and near(button[0][3], urmk_px(16)),
                  "%r" % ([b[2:] for b in button],))

            class _Dropped(object):
                x, y = W // 4, H // 2

            urmk_dragged("probe_pos", True)([_Dropped()], None)
            button = dragged_button(parts(screen("probe_menu_parts")[0]))
            kept_at = _urm_setting_at("probe_pos", True)
            check("where it is dropped it stays, kept as a fraction of the screen at the level asked",
                  tuple(kept_at or ()) == (0.25, 0.5) and _urm_setting_at("probe_pos", False) is None
                  and len(button) == 1 and near(button[0][2], W // 4) and near(button[0][3], H // 2),
                  "%r %r" % (kept_at, [b[2:] for b in button]))
            _urm_setting_set("probe_pos", (0.99, 0.99), True)
            button = dragged_button(parts(screen("probe_menu_parts")[0]))
            check("a part dropped by the far edge, then the window shrunk, stays on the screen",
                  len(button) == 1 and button[0][2] <= W - urmk_px(160) + 0.5 and button[0][3] <= H - urmk_px(48) + 0.5,
                  "%r" % ([b[2:] for b in button],))
            _urm_setting_set("probe_pos", None, True)

            # ---- the URM+ menu and settings window (17_hub), from what the
            # stand-ins registered
            hub = _urmh_state()

            def hub_menu(folded=()):
                hub.open, hub.entries, hub.folded = True, _urm_entries(), set(folded)
                return parts(screen("urmh_button")[0])

            def panel_of(found):
                # the menu's place and its panel: one box, so one of them
                return sorted(set(p[2:] for p in found if p[0] == "window" and near(p[4], urmk_px(URMH_MENU))))

            bw, bh = urmh_button_size()
            menu1 = hub_menu()
            pan = panel_of(menu1)
            words = [p[1] for p in menu1 if p[0] == "text"]
            check("the menu opens under the button at its spot, toward the free side: 400 wide, right edge with the button's, 16 below it",
                  len(pan) == 1 and near(pan[0][0] + pan[0][2], W - urmk_px(16)) and near(pan[0][1], urmk_px(16) + bh + urmk_px(16))
                  and all(w in words for w in (u"Route map", u"Flags", u"Alerts", u"Skip unseen text", u"Gallery: unlock all",
                                                u"Back to last choice", u"Settings", u"Alt+G", u"12", u"2 on"))
                  and u"Broken" not in words,
                  "%r %r" % (pan, words[:14]))
            menu_folded = hub_menu(("alerts",))
            check("picking Alerts folds its names out under it, each with Stop",
                  [p[1] for p in menu_folded if p[0] == "text" and p[1] in (u"Elena love", u"Took the key", u"Stop")]
                  .count(u"Stop") == 2, "")
            _urm_setting_set("urmcHubPos", (0.02, 0.9), True)
            menu2 = hub_menu()
            pan, at = panel_of(menu2), urmh_button_at()
            check("the button dropped bottom left: the menu opens above it, toward the right",
                  len(pan) == 1 and near(pan[0][0], at[0]) and near(pan[0][1] + pan[0][3], at[1] - urmk_px(16)),
                  "%r %r" % (pan, at))
            _urm_setting_set("urmcHubPos", None, True)
            hub.open, hub.entries = False, []
            closed = parts(screen("urmh_button")[0])
            check("closed, only the button shows", [p[1] for p in closed if p[0] == "text"] == [u"\\ue945", u"MRM"],
                  repr([p[1] for p in closed if p[0] == "text"]))

            _urm_setting_set("probeStrict", True)
            _urm_setting_set("probeTypos", 3, True)
            hub.section = "skipping"
            page = parts(screen("urmh_settings")[0])
            win = [p for p in page if p[0] == "window" and near(p[4], urmk_px(URMH_WINDOW[0]))]
            pw = [p[1] for p in page if p[0] == "text"]
            check("the settings window: 1280 wide in the middle, 120 from the top, its sections at the left",
                  len(win) == 1 and near(win[0][2] + win[0][4] / 2.0, W / 2.0) and near(win[0][3], urmk_px(120))
                  and all(w in pw for w in (u"MRM settings", u"Skipping", u"Story help")),
                  "%r %r" % ([p[2:] for p in win], pw[:8]))
            check("each row has This game and All games, the game-only row This game alone, Clear where this game keeps its own",
                  pw.count(u"This game") == 4 and pw.count(u"All games") == 3 and pw.count(u"Clear") == 1,
                  "%d %d %d" % (pw.count(u"This game"), pw.count(u"All games"), pw.count(u"Clear")))
            hub.section = "story"
            story = [p for p in parts(screen("urmh_settings")[0]) if p[0] == "text"]
            check("a row whose choices do not fit beside its words has them under its words",
                  [p[3] for p in story if p[1] == u"This game"][0] > [p[3] for p in story if p[1] == u"Branch notification"][0] + urmk_px(40),
                  "")
            hub.section = "skipping"

            # the Text size row: Large scales every window's words, Normal
            # puts them back
            normal = style.urmk_m.size
            _urm_setting_set("urmcTextSize", URMH_LARGE)
            large = (urmk_look.text, style.urmk_m.size)
            _urm_setting_set("urmcTextSize", None)
            check("Text size Large makes the words 1.25 times as big, Normal puts them back",
                  large == (URMH_LARGE, urmk_px(20 * URMH_LARGE)) and (urmk_look.text, style.urmk_m.size) == (1.0, normal),
                  "%r %r" % (large, (urmk_look.text, style.urmk_m.size)))

            # ---- the code view's lines (18_code_view): the game's own code,
            # braces and all, comes out as it is and raises nothing (a text
            # tag is read even where nothing is substituted)
            ts = renpy.text.textsupport
            bad = []
            for code in (u"$ d = {'a': 1}", u'"{i}Hi{/i} [mc]"', u"{", u"{{", u"# 100%",
                         u"$ s = \\"it's\\" + 'a \\\\'b' + '{'", u"if elena_love >= 2 and not met: # {b}",
                         u"jump p0_c6_left"):
                try:
                    words = urmk_code_words(code)
                    shown = Text(words, substitute=False)
                    renpy.display.render.render(shown, 1000, 200, 0, 0)
                    got = u"".join(t for k, t in ts.tokenize(words) if k == ts.TEXT)
                    if got != code:
                        bad.append("%r drawn as %r" % (code, got))
                except Exception:
                    import traceback
                    bad.append("%r raised %s" % (code, traceback.format_exc().strip().splitlines()[-1]))
            check("the code view draws the game's code as it is, braces too", not bad, "; ".join(bad))

            # ---- _URMKWord & width cache (16_kit):
            # _URMKWord must NOT cache Render objects across frames (GL textures
            # get freed/recycled); urmk_text_width caches plain int widths.
            w1 = urmk_word(u"Cache probe 10", style="urmk_m", color=urmk_colour("ink"))
            is_text = isinstance(w1, renpy.text.text.Text) and u"".join(w1.text) == u"Cache probe 10" and not getattr(w1, "substitute", True)
            r1 = renpy.display.render.render(w1, 400, 100, 0, 0)
            renpy.display.render.free_memory()
            w2 = urmk_word(u"Cache probe 10", style="urmk_m", color=urmk_colour("ink"))
            r2 = renpy.display.render.render(w2, 400, 100, 0, 0)
            fresh_render = (r1 is not r2) and ("renders" not in _urmk_word_cache())
            check("urmk_word is Text(substitute=False) and produces fresh Renders after free_memory",
                  is_text and fresh_render,
                  repr((is_text, fresh_render)))
            _wm1 = urmk_text_width(u"Sample width", "urmk_s_medium")
            _wm2 = urmk_text_width(u"Sample width", "urmk_s_medium")
            urmk_look.text = URMH_LARGE
            urmk_restyle()
            _wm_big = urmk_text_width(u"Sample width", "urmk_s_medium")
            urmk_look.text = 1.0
            urmk_restyle()
            check("urmk_text_width caches widths and invalidates on text scale change",
                  _wm1 == _wm2 and _wm_big > _wm1,
                  repr((_wm1, _wm2, _wm_big)))

            _pump_ticks = [2]
            def _pump_tick():
                _pump_ticks[0] -= 1
            _orig_tick = globals().get("_urm_work_tick")
            globals()["_urm_work_tick"] = _pump_tick
            try:
                _pump = urmk_worker_pump(lambda: _pump_ticks[0] > 0)
                renpy.display.render.render(_pump, 100, 100, 0, 0)
                _after_one = _pump_ticks[0]
                _pump.render(100, 100, 0, 0)
                _after_two = _pump_ticks[0]
            finally:
                if _orig_tick is not None:
                    globals()["_urm_work_tick"] = _orig_tick
            check("urmk_worker_pump steps _urm_work_tick per render while busy",
                  (_after_one, _after_two) == (1, 0),
                  repr((_after_one, _after_two)))

            _old_fm = style.default.focus_mask
            _fm_ok = False
            _fm_err = ""
            try:
                style.default.focus_mask = True
                renpy.style.rebuild()
                screen("urmh_button")
                _fm_ok = True
            except Exception as _err:
                _fm_err = repr(_err)
            finally:
                style.default.focus_mask = _old_fm
                renpy.style.rebuild()
            check("urmk_drag ignores style.default.focus_mask = True without subsurface error",
                  _fm_ok, _fm_err)

            # ---- frame first (16_kit, urmk_later): while the game runs, a
            # window just shown holds its part back for one frame; shown
            # again over itself (its cache handed on) it stays drawn; a
            # window opened anew holds it back again; a picture taken
            # headless gets the whole window
            class _KitShown(object):
                def __init__(self, cache):
                    self.cache = cache
            was_live, was_current, was_restart = _urmk_live, renpy.current_screen, renpy.restart_interaction
            try:
                renpy.restart_interaction = lambda: None
                store._urmk_live = lambda: True
                first = _KitShown({})
                renpy.current_screen = lambda: first
                held = [urmk_held("rows")]
                urmk_draw_now("rows")
                held += [urmk_held("rows"), urmk_held("other")]
                again = _KitShown(first.cache)
                renpy.current_screen = lambda: again
                held.append(urmk_held("rows"))
                anew = _KitShown({})
                renpy.current_screen = lambda: anew
                held.append(urmk_held("rows"))
                store._urmk_live = lambda: False
                held.append(urmk_held("rows"))
            finally:
                store._urmk_live, renpy.current_screen, renpy.restart_interaction = was_live, was_current, was_restart
            check("frame first: a part held back one frame, drawn after, kept when shown again, "
                  "held again in a window opened anew, never in a headless picture",
                  held == [True, False, True, False, True, False], repr(held))

            # ---- a list built as far as it is scrolled (16_kit, _URMKRows):
            # the Flags list and the code view's lines
            was_restart = renpy.restart_interaction
            try:
                renpy.restart_interaction = lambda: None
                rows = _URMKRows("kit check", 40, 100)
                grown = [rows.room()]
                rows.adj.range, rows.adj.page = 1000, 300
                rows.scrolled(100)
                grown.append(rows.room())
                for value in (500, 700, 900):
                    rows.scrolled(value)
                    grown.append(rows.room())
                rows.top()
                grown += [rows.room(), rows.adj.value]
            finally:
                renpy.restart_interaction = was_restart
            check("a list builds its first rows, more near its end up to its most, from its first again when opened",
                  grown == [40, 40, 80, 120, 120, 40, 0], repr(grown))
            check("the code view's lines are such a list", urmk_code_adj is URMK_CODE_ROWS.adj
                  and urmk_code_room() == URMK_CODE_ROOM, repr(urmk_code_room()))

            # ---- what a feature says on the button (_urm_status, the
            # user's b): the button in its tone, a badge on its corner, the
            # tip beside it toward the free side, a head atop the menu. A
            # stand-in feature, which learns the line on screen in its own
            # interact callback, added after the hub's as a feature's is.
            def G(n):
                return u"%c" % n

            probe_line = {"next": None, "at": None, "hidden": False}
            probe_hid = []
            PAPART = (u"Hide until the paths meet", lambda: (probe_hid.append(probe_line["at"]),
                                                            probe_line.__setitem__("hidden", True)))
            PSAYS = {
                "blue": None,
                "yellow 14": ("warn", G(0xe0b6), u"14", u"14 lines until the paths meet",
                              u"You picked: Stay for dinner", PAPART),
                "yellow 1": ("warn", G(0xe0b6), u"1", u"1 line until the paths meet",
                             u"You picked: Stay for dinner", PAPART),
                "yellow, count unknown": ("warn", G(0xe0b6), None, u"The paths are still apart",
                                          u"You picked: Stay for dinner", PAPART),
                "green": ("gain", G(0xe5ca), None, u"The paths meet on this line",
                          u"You picked: Stay for dinner", None),
                "grey": ("skip", G(0xe01f), None, u"A part was skipped", None, None),
            }

            def probe_says():
                if probe_line["hidden"]:
                    return None
                return PSAYS.get(probe_line["at"])

            def probe_feature_interact():
                probe_line["at"] = probe_line["next"]

            _urm_status_add("probe", probe_says)
            config.interact_callbacks.append(probe_feature_interact)

            def drawn():
                rv_ = screen("urmh_button", probe_bright)[0]
                return parts(rv_), rv_

            def hub_parts(open_=False, pointed=False):
                hub.open, hub.pointed = open_, pointed
                hub.entries, hub.folded = (_urm_entries() if open_ else []), set()
                return drawn()

            def hub_found(found):
                """(the button, the badge, the tip's bubble, the menu's
                panel), each (kind, words, x, y, w, h) or None."""
                words = [p for p in found if p[0] == "text"]
                label = [p for p in words if p[1] == u"MRM"]
                button = sorted((p for p in found if p[0] == "button" and label and inside(label[0], p)),
                                key=lambda p: p[4] * p[5])
                now = _urm_status()
                look = urmh_badge_look(now) if now is not None else None
                mark = [p for p in words if now and p[1] == (now.count if now.count is not None else now.icon)]
                badge = [p for p in found if p[0] == "window" and look and near(p[5], look[2])
                         and [m for m in mark if inside(m, p)]]
                pan = [p for p in found if p[0] == "window" and near(p[4], urmk_px(URMH_MENU))]
                tip = _urm_status().tip if _urm_status() is not None else None
                tipw = [p for p in words if tip and p[1] == tip]
                bubble = [p for p in found if p[0] == "window" and tipw and inside(tipw[0], p)
                          and p[4] < W / 2 and not near(p[4], urmk_px(URMH_MENU))]
                return ((button or [None])[0], (badge or [None])[0], (bubble or [None])[-1],
                        (pan or [None])[0])

            def on_screen(part):
                return part is None or (part[2] >= -0.5 and part[3] >= -0.5 and part[2] + part[4] <= W + 0.5
                                        and part[3] + part[5] <= H + 0.5)

            def apart(a, b):
                return (a is None or b is None or a[2] + a[4] <= b[2] + 0.5 or b[2] + b[4] <= a[2] + 0.5
                        or a[3] + a[5] <= b[3] + 0.5 or b[3] + b[5] <= a[3] + 0.5)

            def colour_at(rv_, x, y):
                return tuple(picture(rv_).get_at((int(x), int(y))))[:3]

            def like(got, token):
                want = tuple(renpy.easy.color(URMK_COLOURS.get(token, token)))[:3]
                return max(abs(got[i] - want[i]) for i in range(3)) <= 8

            GROUND = {"blue": "accent", "yellow 14": "warn-accent", "yellow 1": "warn-accent",
                      "yellow, count unknown": "warn-accent", "green": "gain-accent", "grey": "accent"}
            BADGE = {"yellow 14": "warn-accent", "yellow 1": "warn-accent", "yellow, count unknown": "warn-accent",
                     "green": "gain-accent", "grey": "badge-muted"}
            hub_states = []
            bad = []
            for scale in (1.0, URMH_LARGE):
                _urm_setting_set("urmcTextSize", scale)
                for corner in (None, (0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)):
                    _urm_setting_set("urmcHubPos", corner, True)
                    blue_at = None
                    for state in ("blue", "yellow 14", "yellow 1", "yellow, count unknown", "green", "grey"):
                        probe_line["at"], probe_line["hidden"] = state, False
                        where = "text x%s, %s, %s" % (scale, corner or "where it starts", state)
                        found, rv_ = hub_parts(pointed=True)
                        button, badge, bubble, _p = hub_found(found)
                        if button is None:
                            bad.append("%s: no button" % where)
                            continue
                        if state == "blue":
                            blue_at = button[2:4]
                        elif button[2:4] != blue_at:
                            bad.append("%s: the button moved from %r to %r" % (where, blue_at, button[2:4]))
                        if not all(on_screen(p) for p in (button, badge, bubble)):
                            bad.append("%s: off the screen: %r" % (where, [p and p[2:] for p in (button, badge, bubble)]))
                        said = PSAYS[state]
                        words = [p[1] for p in found if p[0] == "text"]
                        if said is None:
                            if badge is not None or bubble is not None or words != [G(0xe945), u"MRM"]:
                                bad.append("%s: more than the button: %r" % (where, words))
                        else:
                            shown = said[2] if said[2] is not None else said[1]
                            if badge is None or shown not in words:
                                bad.append("%s: no badge showing %r: %r" % (where, shown, words))
                            elif not (badge[2] + badge[4] > button[2] + button[4] and badge[3] < button[3]
                                      and badge[2] < button[2] + button[4] and badge[3] + badge[5] > button[3]):
                                bad.append("%s: the badge is not on the button's corner: %r %r" % (where, badge[2:], button[2:]))
                            if bubble is None or not apart(bubble, button) or not apart(bubble, badge):
                                bad.append("%s: the tip is missing or covers the button: %r" % (where, bubble and bubble[2:]))
                        if scale == 1.0 and corner is None:
                            ground = colour_at(rv_, button[2] + urmk_px(12), button[3] + button[5] / 2.0)
                            if not like(ground, GROUND[state]):
                                bad.append("%s: the button is %r, not %s" % (where, ground, GROUND[state]))
                            if state in BADGE:
                                look = urmh_badge_look(_urm_status())
                                fill = colour_at(rv_, badge[2] + look[3] + urmk_px(3), badge[3] + badge[5] / 2.0)
                                if not like(fill, BADGE[state]):
                                    bad.append("%s: the badge is %r, not %s" % (where, fill, BADGE[state]))
                            hub_states.append((state, found, rv_))
                        found, rv_ = hub_parts(open_=True)
                        button, badge, _b, pan = hub_found(found)
                        if pan is None or not apart(pan, badge) or not apart(pan, button) or not on_screen(pan):
                            bad.append("%s: the menu covers the badge or leaves the screen: %r %r" % (where, pan and pan[2:], badge and badge[2:]))
                        if said is not None and said[4]:
                            words = [p for p in found if p[0] == "text"]
                            head = [p for p in words if p[1] == said[4]]
                            first = [p for p in words if p[1] == u"Route map"]
                            hide = [p for p in words if said[5] and p[1] == said[5][0]]
                            if (not head or not first or head[0][3] >= first[0][3] or bool(said[5]) != bool(hide)
                                    or said[3] not in [p[1] for p in words]):
                                bad.append("%s: the menu's head is not atop it: %r" % (where, [p[1] for p in words][:6]))
                        if scale == 1.0 and corner is None and state == "yellow 14":
                            hub_states.append(("menu", found, rv_))
            _urm_setting_set("urmcHubPos", None, True)
            _urm_setting_set("urmcTextSize", None)
            check("the button says what a feature says: in its tone, a badge on its corner, the tip beside it, "
                  "the head atop the menu; in every corner and text size it stays put and on the screen, "
                  "the menu clear of the badge",
                  not bad, "; ".join(bad[:4]))

            # The line on screen: the feature learns it in its callback,
            # after the hub's; the button shows it on that same line - green
            # exactly where the paths meet, again after a rollback onto it,
            # blue on the next; the menu's head says what is true now; Hide
            # turns the button blue on its line.
            def ground_of(found, rv_):
                button = hub_found(found)[0]
                return colour_at(rv_, button[2] + urmk_px(12), button[3] + button[5] / 2.0)

            def play(state):
                """A new line: every interact callback in its order, then
                the button drawn as it is (the menu as it was opened)."""
                probe_line["next"] = state
                for cb in list(config.interact_callbacks):
                    try:
                        cb()
                    except Exception:
                        pass
                found, rv_ = drawn()
                return found, ground_of(found, rv_)

            hub.open, hub.pointed, hub.entries = False, False, []
            probe_line["hidden"] = False
            seen = []
            for state, want in (("yellow 14", "warn-accent"), ("green", "gain-accent"), (None, "accent"),
                                ("green", "gain-accent"), ("yellow 1", "warn-accent")):
                found, ground = play(state)
                seen.append((state, like(ground, want)))
            urmh_open()
            found, ground = play("green")
            head = [p[1] for p in found if p[0] == "text" and p[1] == u"The paths meet on this line"]
            seen.append(("the menu opened a line before: its head says this line", bool(head) and like(ground, "gain-accent")))
            found, ground = play("yellow 14")
            urmh_hide()
            found, rv_ = drawn()
            seen.append(("Hide: blue on its line, the menu shut", like(ground_of(found, rv_), "accent")
                         and not hub.open and probe_hid == ["yellow 14"]
                         and [p[1] for p in found if p[0] == "text"] == [G(0xe945), u"MRM"]))
            check("green on the line where the paths meet and after a rollback onto it, blue on the next; "
                  "the menu's head says the line now; Hide turns the button blue on its line",
                  all(ok for _s, ok in seen), "%r" % ([s for s, ok in seen if not ok],))
            del config.interact_callbacks[config.interact_callbacks.index(probe_feature_interact)]
            _urm_offers().statuses.pop("probe", None)
            hub.open, hub.pointed, hub.entries = False, False, []

            # the button's size the hub works out is the one drawn
            found = parts(screen("urmh_button")[0])
            button = hub_found(found)[0]
            check("the button's size worked out is the size drawn",
                  button is not None and near(button[4], urmh_button_size()[0]) and near(button[5], urmh_button_size()[1]),
                  "%r %r" % (button and button[4:], urmh_button_size()))

            # ---- nothing moved by accident
            got = []
            for where, found in (("sheet", sheet), ("banner", banner), ("menu parts", menu),
                                 ("menu", menu1), ("menu moved", menu2), ("settings", page)) + tuple(
                    ("status " + s, f) for s, f, _r in hub_states):
                for kind, words, x, y, w, h in found:
                    got.append("%s %s %r %.1f %.1f %.1f %.1f" % (where, kind, words, x, y, w, h))
            with open(os.path.join(config.basedir, "probe_layout.txt"), "w") as fh:
                fh.write("\\n".join(got) + "\\n")

            pictures = os.environ.get("URMK_PICTURES")
            if pictures:
                tag = renpy.version_only.replace(".", "_")
                for name, under in (("bright", probe_bright), ("dark", probe_dark)):
                    rv, _root = screen("urmal_alert", under)
                    picture(rv, os.path.join(pictures, "banner_%s_%s.png" % (name, tag)))
                rv, _root = screen("probe_parts", probe_slate)
                picture(rv, os.path.join(pictures, "parts_%s.png" % tag))
                rv, _root = screen("probe_menu_parts", probe_bright)
                picture(rv, os.path.join(pictures, "menu_parts_%s.png" % tag))
                hub.open, hub.entries, hub.folded = True, _urm_entries(), set()
                picture(screen("urmh_button", probe_bright)[0], os.path.join(pictures, "hub_menu_%s.png" % tag))
                hub.folded = set(("alerts",))
                picture(screen("urmh_button", probe_bright)[0], os.path.join(pictures, "hub_alerts_%s.png" % tag))
                _urm_setting_set("urmcHubPos", (0.02, 0.6), True)
                hub.folded = set()
                picture(screen("urmh_button", probe_bright)[0], os.path.join(pictures, "hub_moved_%s.png" % tag))
                _urm_setting_set("urmcHubPos", None, True)
                hub.open = False
                picture(screen("urmh_settings", probe_bright)[0], os.path.join(pictures, "hub_settings_%s.png" % tag))
                for state, _f, rv_ in hub_states:
                    picture(rv_, os.path.join(pictures, "hub_status_%s_%s.png" % (state.replace(",", "").replace(" ", "_"), tag)))
        except Exception:
            import traceback
            lines.append("FAIL  " + traceback.format_exc())
        probe_look(check)
        with open(os.path.join(config.basedir, "probe_out.txt"), "w") as fh:
            fh.write(renpy.version_only + "\\n" + "\\n".join(lines) + "\\n")
        os._exit(0)

    renpy.arguments.commands["lint"] = _probe_lint
'''


# What URM gives for each colour of the kit's table of the older displays
# (URMK_OLD_COLOURS): t is URM's theme, c its colours. warnBg and warnText
# are our own (URM's themes have no amber).
LOOK = u'''
init -1 python:
    config.screen_width, config.screen_height = 1920, 1080

init 1500 python:
    # no caret: it blinks with the clock, not with the style
    probe_input = urmk_old_input("probe")
    probe_input.words = u"elena"
    probe_input.editable = False

    def probe_look(check):
        import pygame_sdl2 as pygame
        renpy.style.rebuild()
        renpy.display.screen.prepare_screens()
        config.developer = False
        __import__("renpy.display.swdraw")

        class _ProbeDraw(object):
            draw_per_virt = 1.0
            draw_to_virt = renpy.display.render.IDENTITY
            virt_to_draw = renpy.display.render.IDENTITY
            info = {"renderer": "sw", "models": False}

            def mutated_surface(self, surf):
                pass

            def load_texture(self, surf, *args, **kwargs):
                return surf.copy()

            def ready_one_texture(self):
                return False

            def render_to_texture(self, what, alpha):
                w, h = what.get_size()
                surf = pygame.Surface((max(1, int(w)), max(1, int(h))), pygame.SRCALPHA)
                surf.fill((0, 0, 0, 0))
                renpy.display.swdraw.draw(surf, None, what, 0, 0, True)
                return surf

            def solid_texture(self, w, h, colour):
                # as the engine's software renderer makes one (a Solid)
                surf = pygame.Surface((int(w) + 4, int(h) + 4), pygame.SRCALPHA)
                surf.fill(colour)
                return surf.subsurface((2, 2, int(w), int(h)))

            def __getattr__(self, name):
                raise AttributeError("probe draw: " + name)

        renpy.display.draw = _ProbeDraw()
        W, H = config.screen_width, config.screen_height

        def drawn(name, kwargs, hover):
            root = renpy.display.layout.Fixed()
            sd = renpy.display.screen.ScreenDisplayable(
                renpy.display.screen.get_screen_variant(name), name, "screens",
                scope={"_kwargs": kwargs})
            sd.update()
            sd.visit_all(lambda d: d.per_interact())
            if hover:
                sd.visit_all(lambda d: d.set_style_prefix("hover_", True)
                             if isinstance(d, renpy.display.behavior.Button) else None)
            root.add(sd)
            # a second after it was shown: a veil has faded in
            rv = renpy.display.render.render(root, W, H, 1.0, 1.0)
            surf = pygame.Surface((W, H), pygame.SRCALPHA)
            surf.fill((0, 0, 0, 0))
            renpy.display.swdraw.draw(surf, None, rv, 0, 0, True)
            return surf

        idle = drawn("probe_dialog_ours", {}, False)
        hover = drawn("probe_dialog_ours", {}, True)
        check("the Flags dialog draws and the close button responds to hover",
              idle.get_at((W // 2, H // 2))[3] > 0
              and any(idle.get_at((x, y)) != hover.get_at((x, y))
                      for x in range(0, W, 4) for y in range(0, H, 4)))

        # The filter box: Enter stays in it (the dialogue behind must not
        # move on, as with URM's box), and it starts empty when asked.
        box = urmk_old_input("probe_box")
        box.set_text(u"kim")
        try:
            box.enter()
            kept = False
        except renpy.IgnoreEvent:
            kept = True
        check("Enter in an older display's box goes no further; the box starts empty when asked",
              kept and urmk_old_input("probe_box") is box and box.get_text() == u"kim"
              and urmk_old_input("probe_box", fresh=True).get_text() == u"",
              "kept %r, words %r" % (kept, box.get_text()))

        # The veil behind the dialog: in over 0.3 s, out over 0.3 s, as
        # URM's (alpha 0 to 1 when shown, back to 0 when hidden).
        class _Veil(object):
            alpha = 1.0
            hide_request = False
            hide_response = True
        veil = _Veil()
        seen = []
        for st in (0.0, 0.15, 0.3):
            seen.append((urmk_old_fade.function(veil, st, st), round(veil.alpha, 3)))
        veil.hide_request = True
        for st in (2.0, 2.15, 2.3):
            veil.hide_response = True
            seen.append((urmk_old_fade.function(veil, st, st), round(veil.alpha, 3), veil.hide_response))
        check("the veil fades in over 0.3 s, and out over 0.3 s before it goes",
              seen == [(0, 0.0), (0, 0.5), (None, 1.0), (0, 1.0, False), (0, 0.5, False), (None, 0.0, True)],
              repr(seen))

screen probe_dialog_ours():
    style_prefix 'urmk_old'
    use urmk_old_dialog('Flags', NullAction(), u'\\ue153'):
        vbox xsize 600
        text "Inside the dialog" style_suffix 'description'
'''


def kit_block():
    """The kit's blocks (its own, the older displays' look, a list built as scrolled) as the
    joined add-on has them, after the worker (02_worker) the kit hands its
    painting to (the doorway, zz_door, comes first)."""

    out = u""
    for needle in ("def _urm_work_tick", "def urmk_restyle", "def _urmk_old_restyle", "class _URMKRows"):
        code = urm_source.block(needle)
        out += u"init 999 python:\n" + u"".join(
            (u"    " + line if line.strip() else line) for line in code.splitlines(True))
    return out


def block_file(needle):
    """One block of the joined add-on as a file of its own: the doorway
    (01_urm_door), the URM+ menu (17_hub)."""

    code = urm_source.block(needle)
    return u"init 999 python:\n" + u"".join(
        (u"    " + line if line.strip() else line) for line in code.splitlines(True))


def screens(names=SCREEN_FILES):
    files = dict(urm_source.screen_files())
    return u"\n".join(files[name].decode("utf-8") for name in names)


def fonts():
    """Our fonts (urm_compat/fonts: Roboto and the icon fonts) where our
    archive puts them."""

    found = {}
    folder = os.path.join(TOOLKIT, "fonts")
    for name in os.listdir(folder):
        with open(os.path.join(folder, name), "rb") as f:
            found["urmplus/fonts/" + name] = f.read()
    return found


def engine(prop):
    """(python, flags, launcher, env) the way the gate starts this prop."""

    exes = glob.glob(os.path.join(prop, "*.exe"))
    starts = [e[:-4] + ".py" for e in exes if os.path.exists(e[:-4] + ".py")]
    pythons = sorted(glob.glob(os.path.join(prop, "lib", "*x86_64*", "python.exe")))
    pythons += sorted(glob.glob(os.path.join(prop, "lib", "*", "python.exe")))
    if not starts or not pythons:
        return None
    py = pythons[0]
    flags = ["-I"] if "py3" in os.path.basename(os.path.dirname(py)) else ["-s"]
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    libs = glob.glob(os.path.join(prop, "lib", "pythonlib*"))
    if libs:
        flags = ["-O"] + flags          # a .pyo-only library
        env["PYTHONPATH"] = libs[0] + os.pathsep + os.path.dirname(py)
    return py, flags, starts[0], env


def run(prop, files, pictures):
    """('pass' | 'skip' | the failure, the engine's version, the lines the
    probe wrote, the layout it measured)."""

    found = engine(prop)
    if found is None:
        return "no engine", "", [], []
    py, flags, start, env = found
    base = tempfile.mkdtemp(prefix="urm_kit_")
    try:
        game = os.path.join(base, "game")
        home = os.path.join(base, "_home")
        os.makedirs(game)
        os.makedirs(os.path.join(home, "persistent"))
        os.makedirs(os.path.join(home, "RenPy"))
        for name, data in files.items():
            path = os.path.join(game, *name.split("/"))
            if not os.path.isdir(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            with open(path, "wb") as f:
                f.write(data)
        env.update(RENPY_PATH_TO_SAVES=home, APPDATA=home,
                   RENPY_MULTIPERSISTENT=os.path.join(home, "persistent"))
        if pictures:
            env["URMK_PICTURES"] = pictures
        try:
            result = subprocess.run([py] + flags + ["-B", start, base, "lint"], cwd=base, env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            said = result.stdout.decode("utf-8", "replace")
        except subprocess.TimeoutExpired:
            return "the engine did not finish in 180 s", "", [], []
        out = os.path.join(base, "probe_out.txt")
        if os.path.exists(out):
            with io.open(out, encoding="utf-8", errors="replace") as f:
                lines = [l for l in f.read().splitlines() if l.strip()]
            version, lines = lines[0], lines[1:]
            layout = []
            measured = os.path.join(base, "probe_layout.txt")
            if os.path.exists(measured):
                with io.open(measured, encoding="utf-8", errors="replace") as f:
                    layout = [l for l in f.read().splitlines() if l.strip()]
            bad = [l for l in lines if not l.startswith("pass")]
            return ("pass" if lines and not bad else "failed"), version, lines, layout
        trace = os.path.join(base, "traceback.txt")
        compiled = glob.glob(os.path.join(game, "*.rpyc"))
        if not os.path.exists(trace) and not compiled:
            return "skip", "", [], []      # an engine that ignores loose script files
        if os.path.exists(trace):
            with io.open(trace, encoding="utf-8", errors="replace") as f:
                said = f.read()
        return "the engine stopped", "", said.strip().splitlines()[-12:], []
    finally:
        shutil.rmtree(base, ignore_errors=True)


def read_baseline():
    """{engine version: [layout lines]}"""

    found = {}
    if os.path.exists(BASELINE):
        with io.open(BASELINE, encoding="utf-8") as f:
            version = None
            for line in f.read().splitlines():
                if line.startswith("engine "):
                    version = line[len("engine "):]
                    found[version] = []
                elif line.strip() and not line.startswith("#") and version:
                    found[version].append(line)
    return found


def write_baseline(found):
    with io.open(BASELINE, "w", encoding="utf-8", newline="\n") as f:
        f.write(u"# The box of every part on the kit's sheet and in the banner, per\n"
                u"# engine version, as the engine lays them out (check_kit.py).\n"
                u"# Written by check_kit.py --record; never by hand.\n")
        for version in sorted(found):
            f.write(u"engine %s\n" % version)
            for line in found[version]:
                f.write(line + u"\n")


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    record = "--record" in argv
    pictures = None
    if "--pictures" in argv:
        pictures = os.path.abspath(argv[argv.index("--pictures") + 1])
        args.remove(argv[argv.index("--pictures") + 1])
        if not os.path.isdir(pictures):
            os.makedirs(pictures)
    if not args:
        print(__doc__)
        return 2
    props = sorted(p for p in glob.glob(os.path.join(os.path.abspath(args[0]), "prop-*"))
                   if os.path.isdir(p))
    files = {"zz_door.rpy": block_file("class _URMMemory").encode("utf-8"),
             "zz_kit.rpy": kit_block().encode("utf-8"),
             "zz_kit_hub.rpy": block_file("def urmh_open").encode("utf-8"),
             "zz_kit_code.rpy": block_file("def urmk_code_words").encode("utf-8"),
             "zz_kit_screens.rpy": screens().encode("utf-8"),
             "zz_kit_sheet.rpy": SHEET.encode("utf-8"),
             "zz_old_look.rpy": LOOK.encode("utf-8")}
    files.update(fonts())
    baseline = read_baseline()
    measured = {}
    failed = checked = 0
    # Every engine starts at once (each is a process of its own): the kit's
    # sheet, and the kit beside URM.
    results = {}

    def start(key, prop, which, pics):
        results[key] = run(prop, which, pics)

    threads = [threading.Thread(target=start, args=(prop, prop, files, pictures)) for prop in props]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    for prop in props:
        verdict, version, lines, layout = results[prop]
        name = os.path.basename(prop)
        if verdict == "skip":
            print("skip  %s: its engine ignores loose script files" % name)
            continue
        checked += 1
        if layout:
            measured[version] = layout
            if not record:
                was = baseline.get(version)
                if was is None:
                    verdict = "failed"
                    lines.append("FAIL  no layout on record for Ren'Py %s: run --record, look at the pictures" % version)
                elif was != layout:
                    verdict = "failed"
                    gone = [l for l in was if l not in layout][:4]
                    new = [l for l in layout if l not in was][:4]
                    lines.append("FAIL  a part moved (Ren'Py %s): was %s; now %s" % (version, gone, new))
                else:
                    lines.append("pass  nothing moved (Ren'Py %s)" % version)
        if verdict == "pass":
            print("pass  %s (Ren'Py %s): %d checks" % (name, version, len(lines)))
            continue
        failed += 1
        print("FAIL  %s (Ren'Py %s): %s" % (name, version, verdict))
        for line in lines:
            if not line.startswith("pass"):
                print("      " + line)
    if record and measured and not failed:
        baseline.update(measured)
        write_baseline(baseline)
        print("recorded the layout of %d engine versions" % len(measured))
    if checked < 2:
        print("FAIL  only %d engines checked; the props hold at least 7.3 and 8.x" % checked)
        failed += 1
    _corner_src = io.open(os.path.join(TOOLKIT, "game_screens", "34_corner.rpy"), encoding="utf-8").read()
    if "focus_mask None" not in _corner_src.split("drag:", 1)[1].split("dragged ", 1)[0]:
        print("FAIL  34_corner.rpy drag does not set focus_mask None")
        failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
