# ---------------------------------------------------------------------------
# The screen kit: soft grey frost
# ---------------------------------------------------------------------------
#
# Every colour, size and gap of our screens is written here, once. A screen
# draws with the kit's parts (game_screens/16_kit.rpy): a window (a banner
# is a window with a tone on its top edge), a card, a chip, three buttons,
# a switch, a row of choices, a menu row and a line between rows, a part the
# player drags (and where it was dropped, kept in a setting of ours), four
# text sizes and the gaps of an 8 px grid. The user's soft grey frost
# has a translucent grey background, a pale edge and a soft shadow. The
# 9-slice paints the window alone, keeping text, chips and controls sharp.
# The wider palette keeps tone colours on opaque fills and distinct states.
# Our own colours, the same
# under every URM theme: nothing here reads URM's theme. Roboto and the
# icon fonts are ours (urm_compat/fonts, shipped in our archive; Roboto
# under the OFL, Google's Material Icons under Apache 2.0, the same files URM
# ships).
#
# The Flags dialog keeps its control metrics and uses the same glass.
# The legacy palette and urmk_px_cut keep the gallery button and older
# model helpers compatible. The new palette styles URM+ surfaces only.
#
# Sizes are given as on a 1080-line screen and scaled to the game's
# (urmk_px). Text sizes follow one more value, urmk_look.text (1.0): a text
# size setting is that value and urmk_restyle().
#
# A panel's edge light, tone edge and shadow are one picture per kind, made
# here as a PNG on first use and stretched by its middle (a 9-slice Frame).
# A window's margins are negative by the shadow's reach, so a part's box is
# the panel itself and its shadow falls outside: placing a part, and the
# centring check (tests/check_kit.py), see the panel, never the shadow.

init 999 python:

    import math as _urmk_math

    # ---- the colours: the only place they are written
    URMK_COLOURS = python_dict((
        ("glass", "#dcdfe596"),         # translucent window only
        ("glass-rim", "#ffffffa6"),
        ("surface", "#e6ebf0"),         # opaque supporting surfaces
        ("surface-tint", "#ffffff32"),
        ("surface-2", "#d1d9e2"),
        ("track", "#24384a38"),
        ("thumb", "#344b68a6"),
        ("thumb-hover", "#263e59"),
        ("badge-rim", "#0f1013"),
        ("badge-muted", "#2a2d33"),
        ("badge-muted-ink", "#8a909a"),
        ("ink", "#0d1724"),
        ("ink-muted", "#141b25"),
        ("ink-faint", "#181b27"),
        ("line", "#23375055"),
        ("graph-line", "#415469"),
        ("accent", "#7ab0ff"),
        ("accent-ink", "#07172e"),
        ("overview-accent", "#3979bb"),
        ("on-accent", "#0b1a30"),
        ("on-tone", "#16181d"),
        ("gain-accent", "#8be6ad"),
        ("warn-accent", "#f6cd72"),
        ("disabled", "#303944"),
        ("scrim", "#0000008c"),
        # A tone drawn directly on glass needs darker ink than its chip.
        ("gain-on-glass", "#081b14"), ("warn-on-glass", "#221801"),
        ("loss-on-glass", "#2a1214"), ("set-on-glass", "#210e30"),
        ("frozen-on-glass", "#071a2c"), ("watch-on-glass", "#20102d"),
        ("gain-bg", "#bbefd7"), ("gain-ink", "#0a3a2b"),
        ("warn-bg", "#f8e6b6"), ("warn-ink", "#4b3204"),
        ("loss-bg", "#f7d4d1"), ("loss-ink", "#6c1f24"),
        ("set-bg", "#e5cfff"),  ("set-ink", "#32114e"),
        ("frozen-bg", "#cee6fa"), ("frozen-ink", "#153f64"),
        ("frozen-edge", "#33688d"), ("frozen-tint", "#489cdf24"),
        ("frozen-value", "#153f64"), ("frozen-on", "#ffffff"), ("frozen-line", "#416480"),
        ("watch-bg", "#e8def9"), ("watch-ink", "#44276c"),
        ("watch-edge", "#704a99"), ("watch-tint", "#9464c91b"),
        ("ignored-bg", "#d7dce2"), ("ignored-ink", "#303a45"),
        ("ignored-edge", "#616b77"), ("ignored-tint", "#65748815"), ("ignored-dim", "#181b27"),
        ("ignored-button", "#303a45"),
        ("row-on", "#c7d6e7"),
        ("plain-bg", "#dce5ee"), ("plain-ink", "#172638"),
        ("hover", "#ffffff48"),
        ("accent-hover", "#ffffff14"),
        ("divider", "#253b5340"),
    ))
    # Fixed compatibility colors for the standalone gallery button,
    # old Flags controls and legacy model helpers (urm_map_colour).
    URMK_OLD_COLOURS = python_dict((
        ("gain", "#D4ADFC"),
        ("plain", "#e4e4e44c"),
        ("box", "#2a316dff"),
        ("root", "#D4ADFC"),
        ("merge", "#D4ADFC"),
        ("accent", "#D4ADFC"),
        ("ink", "#e4e4e4"),
        ("inkOnPrimary", "#0C134F"),
        ("muted", "#e4e4e4b2"),
        ("gainBg", "#dff6dd"), ("gainText", "#107c10"),
        # "You are in a part others may not see": amber, the one tone
        # URM's themes have no colour for.
        ("warnBg", "#fff4ce"), ("warnText", "#6b5a00"),
        ("lossBg", "#fde7e9"), ("lossText", "#a80000"),
        ("setBg", "#5C469C"), ("setText", "#e4e4e4"),
        ("otherBg", "#0C134F"), ("otherText", "#e4e4e4"),
        ("screen", "#0c134ff4"),
        ("screenSolid", "#0C134F"),
        ("pill", "#0C134F"), ("pillText", "#D4ADFC"),
        ("bar", "#0C134F"),
        ("scroll", "#5C469C"), ("thumb", "#D4ADFC"), ("thumbHover", "#f2cbffff"),
        # buttons, the dialog and its close button, the veil behind a
        # dialog, a description line (the styles below)
        ("button", "#0C134F"), ("buttonHover", "#2a316dff"), ("buttonEdge", "#e4e4e4"),
        ("buttonInk", "#e4e4e4"), ("buttonOff", "#000031ff"), ("buttonEdgeOff", "#e4e4e49b"),
        ("buttonInkOff", "#e4e4e49b"),
        ("dialog", "#0c134fe6"), ("dialogBar", "#d4adfce6"), ("dialogEdge", "#e4e4e44b"),
        ("close", "#a80000"), ("closeHover", "#c61e1eff"), ("closeInk", "#fde7e9"),
        ("veil", "#0c134f66"), ("description", "#e4e4e473"),
    ))
    URMK_TONES = ("gain", "warn", "loss", "set", "plain", "frozen", "watch", "ignored")
    _URMK_TONE_ALIAS = python_dict((("other", "plain"),))

    # ---- sizes, at 1080 lines
    # text: name -> (size, line height); l and xl are bold
    URMK_TEXT = python_dict((("s", (16, 24)), ("m", (20, 32)), ("l", (28, 40)), ("xl", (48, 56))))
    URMK_ICON = 24
    URMK_GAPS = (8, 16, 24, 32, 48, 64)
    URMK_RADIUS = 14
    URMK_CHIP = (32, 16)                # height, words' padding at each side
    URMK_SCROLL_KEYS = tuple(k for k in ("rollback", "rollforward")
                             if k in (getattr(config, "keymap", None) or ()))

    class _URMKWheelGuard(renpy.display.core.Displayable):
        """Absorbs mousewheel events (buttons 4 and 5) that reach a
        backdrop so scrolling outside a URM+ window never rolls dialogue
        backward or forward, without adding a Viewport to the screen."""

        def render(self, width, height, st, at):
            return renpy.display.render.Render(0, 0)

        def event(self, ev, x, y, st):
            import pygame_sdl2
            if ev.type == pygame_sdl2.MOUSEBUTTONDOWN and getattr(ev, "button", None) in (4, 5):
                raise renpy.display.core.IgnoreEvent()
            return None
    # button: kind -> (height, words' padding, text size)
    URMK_BUTTON_SIZE = python_dict((("big", (48, 24, "m")), ("small", (40, 16, "s"))))
    URMK_SWITCH = (48, 28, 20, 4)       # width, height, knob, the knob's gap to the edge
    URMK_CHOICES = (40, 4, 32, 16)      # height, inset, a choice's height, its words' padding
    URMK_ROW = (48, 16, 10)             # a menu row: height, padding at the sides, pointed-at radius
    # a ground: kind -> (colour, edge light, shadow (down, blur) or None)
    URMK_GROUNDS = python_dict((
        ("window", ("glass", True, (16, 48))),
        ("card", ("glass", True, (4, 16))),
        ("bubble", ("glass", True, (8, 24))),
        ("inset", ("glass", True, None)),
        ("main", ("accent", False, None)),
        ("warn", ("warn-accent", False, None)),        # the main button, yellow: wait
        ("gain", ("gain-accent", False, None)),        # the main button, green: done
        ("plain", ("surface-2", True, None)),
        ("quiet", (None, False, None)),
    ))
    # painted ahead by the worker, in this order (_urmk_paint_ahead)
    URMK_GROUNDS_AHEAD = ("window", "card", "bubble", "inset", "plain", "quiet", "main", "warn", "gain")
    # a button's words: kind -> colour, colour when pointed at or focused
    URMK_BUTTON_INK = python_dict((
        ("main", ("on-accent", "on-accent")),
        ("warn", ("on-tone", "on-tone")),
        ("gain", ("on-tone", "on-tone")),
        ("plain", ("ink", "ink")),
        ("quiet", ("ink-muted", "ink")),
    ))
    # the three weights of the drawings (400, 500, 700), as their own files
    URMK_FONTS = python_dict((("regular", "urmplus/fonts/Roboto-Regular.ttf"),
                              ("medium", "urmplus/fonts/Roboto-Medium.ttf"),
                              ("bold", "urmplus/fonts/Roboto-Bold.ttf")))
    URMK_ICON_FONT = "urmplus/fonts/MaterialIconsOutlined-Regular.otf"
    URMK_ICON_FONT_SOLID = "urmplus/fonts/MaterialIcons-Regular.ttf"   # the older displays
    # Roboto's ascent, descent and capital height per point of size. The
    # engine makes a line the ascent and the descent, each rounded up; the
    # kit pads it to its line height so that capitals sit in the middle of
    # it (UX: centred by the ink), measured by tests/check_kit.py.
    _URMK_ROBOTO = (1900 / 2048.0, 500 / 2048.0, 1456 / 2048.0)

    class _URMKLook(python_object):
        pass

    urmk_look = _URMKLook()
    urmk_look.text = 1.0            # the text scale: one value for a text size setting
    urmk_look.made = python_dict()  # pictures, made once per run

    class _URMKBack(python_object):
        """A ground to draw a part on: its picture and how far its shadow
        reaches past the part on each side."""

        def __init__(self, image, left, top, right, bottom):
            self.image = image
            self.left, self.top, self.right, self.bottom = left, top, right, bottom

    def urmk_px(n):
        """n pixels on a 1080-line screen, on this game's screen."""

        return int(round(n * config.screen_height / 1080.0))

    def urmk_chip_pad():
        """The room above and below a chip's words: one line of them is
        exactly the chip's height (urmk_px(URMK_CHIP[0])) at every screen
        height and text size whose line fits; words that wrap make the
        chip taller (Neuvau, 2026-11-22)."""

        line = urmk_px(URMK_TEXT["s"][1] * urmk_look.text)
        return max(0, urmk_px(URMK_CHIP[0]) - line) // 2

    def urmk_px_cut(n):
        """n pixels on a 1080-line screen, on this game's screen, the
        fraction cut off: the sizes of the displays not yet drawn with the
        kit, as they were (urmk_px rounds). tests/check_kit.py holds it to
        URM's own scaling."""

        return int(n * (config.screen_height / 1080.0))

    def urmk_colour(token):
        return URMK_COLOURS[token]

    def urmk_tone(tone):
        """A tone the kit knows: the map's 'other' is plain."""

        tone = _URMK_TONE_ALIAS.get(tone, tone)
        return tone if tone in URMK_TONES else "plain"

    def _urmk_rgba(colour):
        return tuple(renpy.easy.color(URMK_COLOURS.get(colour, colour)))

    def urmk_tone_ink(tone):
        """Choose contrast-safe foreground for tone text directly on glass."""
        return URMK_COLOURS.get(urmk_tone(tone) + "-on-glass", URMK_COLOURS["ink-muted"])

    def urmk_chip_fill(tone, faded=False):
        """Keep a chip opaque even when its tone is muted."""
        fill = URMK_COLOURS[urmk_tone(tone) + "-bg"]
        if not faded:
            return fill
        key = ("faded-fill", fill)
        found = urmk_look.made.get(key)
        if found is None:
            colour, neutral = _urmk_rgba(fill), _urmk_rgba("surface-2")
            found = urmk_look.made[key] = tuple((c + n) // 2 for c, n in zip(colour, neutral))
        return found

    def urmk_chip_ink(tone, faded=False):
        return URMK_COLOURS["disabled" if faded else urmk_tone(tone) + "-ink"]

    # ---- pictures

    def _urmk_png_rows(w, h, colour_at, mirror=False):
        """The PNG's rows, one per step (its filter byte, then its pixels),
        so a painting can stop between rows (the worker). mirror: the
        picture is the same read from the right, so only the left half is
        worked out (exact: every x is a half pixel, its distance from the
        middle the same both ways). It runs on the game's thread: its range
        and tuples are as cheap as any (a thread job would need care: FINDINGS,
        Engines). A painting may stop between its rows."""

        half_w = (w + 1) // 2 if mirror else w
        for j in range(h):
            row = bytearray(1)
            left = tuple(colour_at(i, j) for i in range(half_w))
            for pixel in left:
                row.extend(pixel)
            if mirror:
                for i in range(w // 2 - 1, -1, -1):
                    row.extend(left[i])
            yield row

    def _urmk_png(w, h, colour_at, mirror=False):
        """A w x h PNG; colour_at(i, j) gives each pixel as (r, g, b, a)."""

        rows = bytearray()
        for row in _urmk_png_rows(w, h, colour_at, mirror):
            rows.extend(row)
        return _urmk_png_bytes(w, h, rows)

    def _urmk_png_bytes(w, h, rows):
        """The PNG of rows painted by _urmk_png_rows."""

        import struct
        import zlib

        def chunk(kind, data):
            body = kind + data
            return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)

        return (bytes(bytearray((137, 80, 78, 71, 13, 10, 26, 10)))
                + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(bytes(rows))) + chunk(b"IEND", b""))

    def _urmk_distance(x, y, box, r):
        """How far (x, y) is outside the rounded box (negative: inside)."""

        x0, y0, x1, y1 = box
        qx = abs(x - (x0 + x1) / 2.0) - ((x1 - x0) / 2.0 - r)
        qy = abs(y - (y0 + y1) / 2.0) - ((y1 - y0) / 2.0 - r)
        d = _urmk_math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - r
        return d

    def _urmk_cover(d):
        """How much of a pixel at distance d the shape covers (0 to 1)."""

        return min(1.0, max(0.0, 0.5 - d))

    def _urmk_ground_png(radius, ground, light, edge, shadow, hover):
        """See _urmk_ground_paint: the same, painted in one go."""

        w, h, at, left, top, right, bottom = _urmk_ground_paint(radius, ground, light, edge, shadow, hover)
        return _urmk_png(w, h, at, True), left, top, right, bottom

    def _urmk_lay(colour, amount, r, g, b, a):
        """colour laid over (r, g, b, a) (premultiplied, 0-1), covering
        `amount` of the pixel."""

        k = colour[3] / 255.0 * amount
        if k <= 0.0:
            return r, g, b, a
        return (colour[0] / 255.0 * k + r * (1.0 - k), colour[1] / 255.0 * k + g * (1.0 - k),
                colour[2] / 255.0 * k + b * (1.0 - k), k + a * (1.0 - k))

    def _urmk_ground_paint(radius, ground, light, edge, shadow, hover):
        """A rounded part, its edge light and tone edge laid on its top, its
        shadow around it: (PNG, left, top, right, bottom), the last four how
        far the shadow reaches past the part. The part is 2r + 4 pixels
        square: the engine's Frame shrinks its borders unless the middle is
        at least two pixels (imagelike.Frame.render, 7.3.5 - 8.5)."""

        if shadow:
            down, blur = urmk_px(shadow[0]), urmk_px(shadow[1])
            left = right = blur
            top, bottom = max(0, blur - down), blur + down
            spread = max(0.5, blur / 2.0) * _urmk_math.sqrt(2.0)
        else:
            down = blur = left = right = top = bottom = 0
        side = 2 * radius + 4
        box = (left, top, left + side, top + side)
        w, h = left + side + right, top + side + bottom
        fill = _urmk_rgba(ground) if ground else None
        tone = _urmk_rgba(URMK_COLOURS.get(urmk_tone(edge) + "-accent", urmk_chip_ink(edge))) if edge else None
        rim = _urmk_rgba("glass-rim" if ground == "glass" else "line")
        dark = _urmk_rgba("scrim")
        veil = _urmk_rgba("accent-hover" if ground in ("accent", "warn-accent", "gain-accent") else "hover")
        band = urmk_px(3)
        one = max(1, urmk_px(1))

        def at(i, j):
            x, y = i + 0.5, j + 0.5
            distance = _urmk_distance(x, y, box, radius)
            cov = _urmk_cover(distance)
            r = g = b = a = 0.0           # premultiplied, 0-1; laid bottom first
            if shadow:
                d = _urmk_distance(x, y - down, box, radius)
                r, g, b, a = _urmk_lay(dark, 0.5 * _urmk_math.erfc(d / spread) * (1.0 - cov), r, g, b, a)
            if fill:
                r, g, b, a = _urmk_lay(fill, cov, r, g, b, a)
            if ground == "glass":
                rim_cover = cov - _urmk_cover(one + distance)
                r, g, b, a = _urmk_lay(rim, max(0.0, rim_cover), r, g, b, a)
            if hover:
                r, g, b, a = _urmk_lay(veil, cov, r, g, b, a)
            if tone:
                r, g, b, a = _urmk_lay(tone, max(0.0, cov - _urmk_cover(_urmk_distance(x, y - band, box, radius))),
                                       r, g, b, a)
            if light:
                r, g, b, a = _urmk_lay(rim, max(0.0, cov - _urmk_cover(_urmk_distance(x, y - one, box, radius))),
                                       r, g, b, a)
            if a <= 0.0:
                return (0, 0, 0, 0)
            return (int(round(r / a * 255)), int(round(g / a * 255)), int(round(b / a * 255)),
                    int(round(a * 255)))

        return w, h, at, left, top, right, bottom

    def urmk_back(kind, edge=None, hover=False):
        """The ground of a part: 'window', 'card', 'bubble', 'inset', or a button's
        'main', 'plain', 'quiet'; edge: a tone for the top edge (a banner);
        hover: as pointed at or focused. Made once per run."""

        radius = urmk_px(URMK_RADIUS)
        key = (kind, edge, hover, radius)
        found = urmk_look.made.get(key)
        if found is None:
            for _step in _urmk_back_paint(kind, edge, hover):
                pass
            found = urmk_look.made[key]
        return found

    def _urmk_back_paint(kind, edge=None, hover=False):
        """Paint urmk_back's picture, a row per step, and keep it: the
        worker paints the usual ones ahead (_urmk_paint_ahead), so a screen
        opened for the first time finds them made."""

        radius = urmk_px(URMK_RADIUS)
        key = (kind, edge, hover, radius)
        if key in urmk_look.made:
            return
        ground, light, shadow = URMK_GROUNDS[kind]
        w, h, at, left, top, right, bottom = _urmk_ground_paint(radius, ground, light, edge, shadow, hover)
        rows = bytearray()
        for row in _urmk_png_rows(w, h, at, True):
            rows.extend(row)
            yield
        if key in urmk_look.made:
            return
        png = _urmk_png_bytes(w, h, rows)
        name = "urmk_%s_%s_%d_%d.png" % (kind, edge or "none", int(hover), radius)
        image = Frame(im.Data(png, name), left + radius, top + radius, right + radius, bottom + radius)
        urmk_look.made[key] = _URMKBack(image, left, top, right, bottom)

    def _urmk_paint_ahead():
        """The worker's job: every ground of URMK_GROUNDS, at rest and
        pointed at, painted between frames once the game is up."""

        for kind in URMK_GROUNDS_AHEAD:
            for hover in (False, True):
                for _step in _urmk_back_paint(kind, None, hover):
                    yield
        yield _URMWorkDone()

    _urm_work_slices("kit pictures", _urmk_paint_ahead)

    def urmk_pill(colour, radius):
        """A soft pill in one solid colour, `radius` round at each end."""

        rgba = tuple(renpy.easy.color(colour))
        key = ("pill", rgba, radius)
        found = urmk_look.made.get(key)
        if found is None:
            png = _urmk_ground_png(radius, colour, False, None, None, False)[0]
            name = "urmk_pill_%d_%s.png" % (radius, "".join("%02x" % c for c in rgba))
            found = Frame(im.Data(png, name), radius, radius)
            urmk_look.made[key] = found
        return found

    def urmk_ring(colour, radius, width):
        """A soft pill's outline alone, `width` thick, in one colour: an
        outlined button (the Remembered page's Freeze)."""

        rgba = tuple(renpy.easy.color(colour))
        key = ("ring", rgba, radius, width)
        found = urmk_look.made.get(key)
        if found is None:
            size = 2 * radius + 4
            box = (0, 0, size, size)

            def at(i, j):
                d = _urmk_distance(i + 0.5, j + 0.5, box, radius)
                a = max(0.0, min(1.0, 0.5 - d)) * max(0.0, min(1.0, d + width + 0.5))
                return rgba[:3] + (int(rgba[3] * a),)
            png = _urmk_png(size, size, at, True)
            name = "urmk_ring_%d_%d_%s.png" % (radius, width, "".join("%02x" % c for c in rgba))
            found = Frame(im.Data(png, name), radius + 1, radius + 1)
            urmk_look.made[key] = found
        return found

    def urmk_chip_bg(tone):
        return urmk_pill(urmk_chip_fill(tone), urmk_px(URMK_CHIP[0]) // 2)

    def urmk_edged_back(tone, dashed=False):
        """A group's card: its tone's tint, round, with an edge down its
        left side in the tone's edge colour, dashed or whole, so groups side
        by side are told apart by colour and by shape (the user's B2).
        Made once per run."""

        radius = urmk_px(URMK_RADIUS)
        bar, dash = max(2, urmk_px(4)), max(4, urmk_px(8))
        key = ("edged", tone, dashed, radius, bar, dash)
        found = urmk_look.made.get(key)
        if found is None:
            ground = _urmk_rgba(urmk_tone(tone) + "-tint")
            edge = _urmk_rgba(urmk_tone(tone) + "-edge")
            left = radius + bar
            w, h = left + radius + 4, 2 * radius + 2 * dash
            box = (0, 0, w, h)

            def at(i, j):
                d = _urmk_distance(i + 0.5, j + 0.5, box, radius)
                a = max(0.0, min(1.0, 0.5 - d))
                if a <= 0.0:
                    return (0, 0, 0, 0)
                if i < bar and (not dashed or (j - radius) % (2 * dash) < dash):
                    return edge[:3] + (int(edge[3] * a),)
                return ground[:3] + (int(ground[3] * a),)
            png = _urmk_png(w, h, at)
            name = "urmk_edged_%s_%d_%d_%d_%d.png" % (tone, int(dashed), radius, bar, dash)
            found = Frame(im.Data(png, name), left, radius, radius + 2, radius, tile=True)
            urmk_look.made[key] = found
        return found

    # ---- a part the player drags: where it was dropped, kept

    class _URMKDropped(python_object):
        """A drag's `dragged`: keeps where the part was dropped in a
        setting of ours, as a fraction of the screen, so it survives a
        change of window size. One per setting and level (urmk_dragged), so
        a screen sees the same one at every interaction."""

        def __init__(self, setting, every_game, room=None):
            self.setting, self.every_game, self.room = setting, every_game, room

        def __call__(self, drags, drop):
            try:
                d = drags[0]
                left, top = urmk_room(self.room)[:2]
                _urm_setting_set(self.setting, (float(d.x + left) / max(1, config.screen_width),
                                                float(d.y + top) / max(1, config.screen_height)),
                                 self.every_game)
            except Exception as error:
                print("MRM: where %s was dropped is not kept (%s)" % (self.setting, error))

    def urmk_dragged(setting, every_game=False, room=None):
        key = ("dragged", setting, bool(every_game), tuple(room or ()))
        found = urmk_look.made.get(key)
        if found is None:
            found = urmk_look.made[key] = _URMKDropped(setting, bool(every_game), room)
        return found

    def urmk_room(room):
        """A drag's room around its part, (left, top, right, bottom) at
        1080 lines, in pixels; None: none."""
        return tuple(urmk_px(n) for n in room) if room else (0, 0, 0, 0)

    def urmk_drag_at(setting, size, room=None):
        """Where the player last dropped the part kept in `setting`: the
        top left of what drags, in pixels, kept on the screen for a part
        `size` big (at 1080 lines) with its room around it (urmk_room: the
        setting keeps the part's own top left, so room that comes or goes
        never moves the part); None while it was never dropped."""
        kept = _urm_setting(setting)
        if not kept or len(kept) != 2:
            return None
        w, h = config.screen_width, config.screen_height
        left, top, right, bottom = urmk_room(room)
        return (max(0, min(int(kept[0] * w) - left, w - urmk_px(size[0]) - left - right)),
                max(0, min(int(kept[1] * h) - top, h - urmk_px(size[1]) - top - bottom)))

    # ---- styles: words and grounds that take nothing from the game's own

    def urmk_restyle():
        """Make the kit's styles; again after urmk_look.text changes (then
        renpy.style.rebuild())."""

        scale = urmk_look.text
        base = Style(style.default)
        for prop, value in (("font", URMK_FONTS["regular"]), ("color", URMK_COLOURS["ink"]), ("bold", False),
                            ("italic", False), ("underline", False), ("strikethrough", False),
                            ("outlines", []), ("drop_shadow", None), ("kerning", 0.0),
                            ("line_leading", 0), ("line_spacing", 0), ("text_align", 0.0),
                            ("first_indent", 0), ("rest_indent", 0), ("justify", False),
                            ("layout", "tex"), ("antialias", True), ("vertical", False),
                            ("min_width", 0), ("slow_cps", None), ("xalign", 0.0), ("yalign", 0.0),
                            ("background", None), ("alt", "")):
            setattr(base, prop, value)
        for prop, value in (("hinting", "auto"), ("mipmap", False)):
            try:
                setattr(base, prop, value)
            except Exception:
                pass
        style.urmk_text = base
        for name, (size, line) in URMK_TEXT.items():
            one = Style(style.urmk_text)
            px = urmk_px(size * scale)
            high = urmk_px(line * scale)
            up = int(_urmk_math.ceil(px * _URMK_ROBOTO[0]))
            down = int(_urmk_math.ceil(px * _URMK_ROBOTO[1]))
            above = int(round(high / 2.0 - up + px * _URMK_ROBOTO[2] / 2.0))
            one.size = px
            one.line_leading = above
            one.line_spacing = high - up - down - above
            if name in ("l", "xl"):
                one.font = URMK_FONTS["bold"]
            setattr(style, "urmk_" + name, one)
            if name in ("s", "m"):          # chips, buttons, labels: 500
                medium = Style(one)
                medium.font = URMK_FONTS["medium"]
                setattr(style, "urmk_%s_medium" % name, medium)
        icon = Style(style.urmk_text)
        icon.font = URMK_ICON_FONT
        icon.size = urmk_px(URMK_ICON * scale)
        style.urmk_icon = icon
        for name in ("urmk_frame", "urmk_button"):
            ground = Style(style.default)
            for prop, value in (("background", None), ("foreground", None), ("xpadding", 0),
                                ("ypadding", 0), ("xmargin", 0), ("ymargin", 0), ("xfill", False),
                                ("yfill", False), ("xminimum", 0), ("yminimum", 0),
                                ("xmaximum", None), ("ymaximum", None), ("xalign", 0.0),
                                ("yalign", 0.0), ("hover_sound", None), ("activate_sound", None),
                                ("focus_mask", None), ("mouse", None)):
                setattr(ground, prop, value)
            setattr(style, name, ground)

    urmk_restyle()

    # ---- persistent width cache (DECISIONS 2026-11-26):
    # Cache measured text widths (plain ints in _urm_kept, never saved) keyed by
    # (text, style_name) and invalidated on window/renderer/text-scale changes.
    # Never cache Ren'Py Render objects across frames: gldraw frees/recycles GL
    # texture IDs when screens close, turning stale Renders into black boxes or
    # unrelated textures (FINDINGS.md).

    def _urmk_word_gen():
        draw = getattr(renpy.display, "draw", None)
        psize = getattr(draw, "physical_size", None) if draw is not None else None
        return (id(draw), psize, config.screen_width, config.screen_height, urmk_look.text)

    def _urmk_word_cache():
        cache = _urm_kept("word_cache", python_dict)
        gen = _urmk_word_gen()
        if cache.get("gen") != gen:
            cache["gen"] = gen
            cache["widths"] = python_dict()
        return cache

    try:
        _URMKWordBase = renpy.text.text.Text
    except Exception:
        _URMKWordBase = python_object

    class _URMKWord(_URMKWordBase):
        """A Text displayable with substitute=False that delegates rendering to
        Ren'Py's Text.render so GL textures stay managed by the engine."""

        def __init__(self, words, style="urmk_m", color=None, hover_color=None,
                     font=None, size=None, min_width=None, text_align=None,
                     xmaximum=None, **kwargs):
            text_str = u"%s" % (words,)
            kw = dict(kwargs)
            kw["style"] = style
            kw["substitute"] = False
            if color is not None:
                kw["color"] = color
            if hover_color is not None:
                kw["hover_color"] = hover_color
            if font is not None:
                kw["font"] = font
            if size is not None:
                kw["size"] = size
            if min_width is not None:
                kw["min_width"] = min_width
            if text_align is not None:
                kw["text_align"] = text_align
            if xmaximum is not None:
                kw["xmaximum"] = xmaximum
            super(_URMKWord, self).__init__(text_str, **kw)

    def urmk_word(words, style="urmk_m", **kwargs):
        return _URMKWord(words, style=style, **kwargs)

    def urmk_text_width(words, style_name="urmk_s_medium"):
        """Cached pixel width of `words` in `style_name`."""
        cache = _urmk_word_cache()
        widths = cache["widths"]
        text_str = u"%s" % (words,)
        key = (text_str, style_name)
        found = widths.get(key)
        if found is None:
            found = renpy.text.text.Text(text_str, style=style_name, substitute=False).size()[0]
            if len(widths) >= 4000:
                widths.clear()
            widths[key] = found
        return found

    try:
        _URMKDispBase = renpy.display.core.Displayable
    except Exception:
        _URMKDispBase = python_object

    class _URMKWorkerPump(_URMKDispBase):
        """0x0 displayable that pumps _urm_work_tick() on each drawn frame
        via renpy.redraw(self, 0) while busy, with zero screen re-evaluation
        between ticks."""

        def __init__(self, busy_fn=None):
            super(_URMKWorkerPump, self).__init__()
            self._busy_fn = busy_fn
            self._primed = False

        def render(self, width, height, st, at):
            busy = self._busy_fn() if self._busy_fn is not None else _urm_work_busy()
            if busy:
                if not self._primed and st == 0 and _urmk_live():
                    self._primed = True
                    renpy.redraw(self, 0)
                    return renpy.display.render.Render(0, 0)
                self._primed = True
                _urm_work_tick()
                still = self._busy_fn() if self._busy_fn is not None else _urm_work_busy()
                if still:
                    renpy.redraw(self, 0)
            return renpy.display.render.Render(0, 0)

    def urmk_worker_pump(busy_fn=None):
        return _URMKWorkerPump(busy_fn)

    # ---- frame first (DECISIONS 2026-11-26 "Instant windows"): a window
    # just shown draws its frame in the click's own frame, and what it holds
    # in game_screens/16_kit's urmk_later one frame after. Drawing the words
    # of a full window is what a click waited on (FINDINGS "A restart
    # redraws only the parts the screen made anew"); after the first frame
    # the engine keeps what did not change. Which parts are drawn is kept in
    # the shown screen's own cache: the engine hands it on when the screen
    # is shown again over itself, starts it afresh for a window opened anew,
    # and never saves it.

    def _urmk_live():
        """Is the game's window running? A headless picture (the checks)
        is taken in one frame: the whole window at once."""
        return getattr(getattr(renpy.game, "interface", None), "started", True)

    def urmk_held(key):
        """True while the window being drawn shows only its frame for key."""
        if not _urmk_live():
            return False
        screen = renpy.current_screen()
        if screen is None:
            return False
        drawn = screen.cache.get("_urmk_drawn")
        return drawn is None or key not in drawn

    def urmk_draw_now(key):
        """urmk_later's timer: key's part is drawn from the next frame."""
        screen = renpy.current_screen()
        if screen is not None:
            screen.cache.setdefault("_urmk_drawn", set()).add(key)
            renpy.restart_interaction()


# ---- the older displays' look (see the top): URM's first theme. Its own
# block, after the kit's: what it draws with is the engine's own (Solid,
# Frame, InputValue), which the kit's block does not need.

init 999 python:

    def _urmk_old_box(size, parts, borders):
        """A ground made of plain colours: parts are (colour, x, y, w, h),
        laid in order on a picture `size` big (later ones over earlier
        ones), stretched by its middle (a 9-slice Frame) past `borders`."""

        box = Fixed(xysize=size)
        for colour, x, y, w, h in parts:
            box.add(Solid(URMK_OLD_COLOURS[colour], xysize=(w, h), xpos=x, ypos=y))
        return Frame(box, *borders)

    def urmk_old_button_box(fill, edge="buttonEdge"):
        """A button's ground: `fill` inside a 2-pixel `edge`."""

        return _urmk_old_box((6, 6), ((edge, 0, 0, 2, 6), (edge, 0, 0, 6, 2),
                                      (edge, 4, 0, 2, 6), (edge, 0, 4, 6, 2),
                                      (fill, 2, 2, 2, 2)), (2, 2))

    def _urmk_old_restyle():
        """Make the older displays' styles, urmk_old_<part>: what a screen
        with style_prefix 'urmk_old' draws with."""

        c = URMK_OLD_COLOURS
        cut = urmk_px_cut

        def make(name, parent, *props):
            one = Style(parent)
            for prop, value in props:
                setattr(one, prop, value)
            setattr(style, "urmk_old_" + name, one)
            return one

        base = make("default", style.default,
                    ("background", None), ("hover_background", None),
                    ("selected_background", None), ("selected_hover_background", None),
                    ("insensitive_background", None), ("xalign", 0.0), ("yalign", 0.0),
                    ("xpadding", 0), ("ypadding", 0), ("xmargin", 0), ("ymargin", 0),
                    ("spacing", 0), ("line_spacing", 0))
        for name in ("hbox", "vbox", "label"):
            make(name, base)
        words = make("text", base, ("font", URMK_FONTS["regular"]), ("color", urmk_colour("ink")),
                     ("size", cut(24)), ("text_align", 0.0), ("outlines", []), ("alt", ""))
        make("label_text", words, ("bold", True))
        icon = make("icon", words, ("font", URMK_ICON_FONT))
        make("iconSolid", icon, ("font", URMK_ICON_FONT_SOLID))
        make("description", words, ("size", cut(20)), ("color", urmk_colour("ink-muted")))
        make("overlay", style.default, ("background", Solid(urmk_colour("scrim"))))
        frame = make("frame", base, ("background", Solid(c["button"])),
                     ("xpadding", cut(7)), ("ypadding", cut(5)))
        make("vscrollbar", style.vscrollbar, ("xsize", cut(15)), ("ysize", None),
             ("left_bar", Solid(urmk_colour("track"))), ("right_bar", Solid(urmk_colour("track"))),
             ("thumb", Solid(urmk_colour("thumb"))), ("hover_thumb", Solid(urmk_colour("thumb-hover"))),
             ("unscrollable", "hide"))
        button = make("button", base, ("background", urmk_old_button_box("button")),
                      ("hover_background", urmk_old_button_box("buttonHover")),
                      ("selected_idle_background", urmk_old_button_box("buttonHover")),
                      ("insensitive_background", urmk_old_button_box("buttonOff", "buttonEdgeOff")),
                      ("xpadding", cut(8)), ("ypadding", cut(4)), ("xminimum", None),
                      ("yminimum", cut(36)), ("xmaximum", None), ("ymaximum", None))
        button_text = make("button_text", words, ("color", c["buttonInk"]),
                           ("insensitive_color", c["buttonInkOff"]), ("yalign", 0.5))
        make("icon_button", button)
        make("icon_button_text", button_text, ("font", URMK_ICON_FONT),
             ("hover_font", URMK_ICON_FONT_SOLID))
        make("input", button_text)
        # the dialog (urmk_old_dialog)
        make("dialog", frame, ("background", urmk_back("inset").image), ("xpadding", 2), ("ypadding", 2))
        make("dialogContent", frame, ("background", None), ("yoffset", cut(-20)),
             ("left_padding", cut(20)), ("right_padding", cut(20)), ("top_padding", 0),
             ("bottom_padding", cut(10)))
        make("dialogButtons", style.default, ("yoffset", cut(-40)), ("xalign", 1.0))
        close = make("dialogButton", button, ("background", Solid(c["button"])),
                     ("hover_background", Solid(c["buttonHover"])), ("ysize", cut(38)),
                     ("xpadding", cut(16)), ("ypadding", 0))
        make("dialogCloseButton", close, ("background", Solid(c["close"])),
             ("hover_background", Solid(c["closeHover"])))
        make("dialogIcon", style.urmk_old_iconSolid, ("size", cut(28)))

    _urmk_old_restyle()

    def _urmk_old_fading(trans, st, at):
        """The veil behind an older display's dialog fades in over 0.3 s
        when shown, and out over 0.3 s from where it was when hidden."""

        if getattr(trans, "hide_request", False):
            began = getattr(trans, "_urmk_out", None)
            if began is None:
                began = trans._urmk_out = (st, trans.alpha)
            done = (st - began[0]) / 0.3
            if done < 0.999999:
                trans.alpha = began[1] * (1.0 - done)
                trans.hide_response = False
                return 0
            trans.alpha = 0.0
            return None
        done = st / 0.3
        trans.alpha = done if done < 0.999999 else 1.0
        return 0 if trans.alpha < 1.0 else None

    urmk_old_fade = Transform(function=_urmk_old_fading)

    class _URMKInput(InputValue):
        """The words typed into a box of an older display. Enter is taken
        here, so it never reaches the game behind (the dialogue would move
        on). One per box and run (urmk_old_input): never held by a screen,
        so no save holds one."""

        default = True
        editable = True

        def __init__(self):
            self.words = u""

        def get_text(self):
            return self.words

        def set_text(self, words):
            self.words = words
            renpy.restart_interaction()

        def enter(self):
            raise renpy.IgnoreEvent()

    def urmk_old_input(name, fresh=False):
        """The box `name`'s words; fresh: emptied, as when its screen opens."""

        key = ("input", name)
        found = urmk_look.made.get(key)
        if found is None:
            found = urmk_look.made[key] = _URMKInput()
        if fresh:
            found.words = u""
        return found

# ---- a list built as far as it is scrolled (the speed plan: a list builds
# its first screenfuls, more as it is scrolled, never all its rows at once):
# the code view's lines, the Flags list. Search's groups share one room
# among them (50_search, _urmcp_room). Its own block: it needs only our
# memory (01_urm_door), so a check of a list loads it alone.

init 999 python:

    class _URMKRows(python_object):
        """A list's first `first` rows, `first` more each time its viewport
        (yadjustment: adj) nears its end, up to `most`. How far it is built
        is kept in our memory, never saved; top() starts it afresh."""

        def __init__(self, name, first, most=None):
            self.name, self.first, self.most = name, first, most
            self.adj = ui.adjustment(changed=self.scrolled)

        def room(self):
            return _urm_kept("rows", python_dict).get(self.name, self.first)

        def scrolled(self, value):
            adj = self.adj
            if value >= adj.range - 2 * adj.page:
                rooms = _urm_kept("rows", python_dict)
                room = rooms.get(self.name, self.first)
                if self.most is None or room < self.most:
                    rooms[self.name] = room + self.first
                    renpy.restart_interaction()
            return None

        def top(self):
            _urm_kept("rows", python_dict)[self.name] = self.first
            self.adj.change(0)
