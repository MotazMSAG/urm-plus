# ---------------------------------------------------------------------------
# Clickable spots: a numbered pin on each, blinking; a new one stops skipping
# ---------------------------------------------------------------------------
#
# Point-and-click scenes hide what can be clicked: a car that only shows
# "EXAMINE" under the mouse, a note on the floor. Every clickable spot in the
# scene gets a small numbered dot that blinks for as long as it is on screen
# (DECISIONS.md, 2026-11-21: 1b, 2c), and a spot that appears while the
# player is skipping stops the skip, also in the middle of dialogue.
#
# Where the spots come from: the engine's own list of everything clickable,
# renpy.display.focus.focus_list, rebuilt with each spot's box on screen by
# take_focuses() after every frame is drawn - the list the mouse is matched
# against (FINDINGS.md, "Every clickable spot"). Whatever a game builds its
# spots from (imagebutton, button, imagemap hotspots) is in it; a button with
# no action, an insensitive one and a hover-only mousearea are not. A screen
# shown over the scene as modal empties the list below it, so URM's own
# windows hide the pins of the scene under them.
#
# Where a spot is: its box, except for a button clickable only where its
# picture is painted (focus_mask): the list gives the whole picture's box,
# often the full screen, so the spot is where the picture has ink
# (_urmpin_ink).
#
# Not every button is a spot (_urmpin_is_spot, _urmpin_ui_screen): a spot is
# one the player might miss, in the scene. Left out are
#   - menus: the main menu and the game menu
#   - the game's interface screens: dialogue, choices, the quick menu, the
#     standard screens by name, and every screen the game shows at all times
#     (config.overlay_screens: quick menus, stat bars, a phone icon)
#   - a screen on show as _URMPIN_LINES new lines of dialogue in a row
#     begin (two said in full, the third starting; a line gone back over
#     is not new): a row
#     of icons the game shows the ordinary way and keeps while the story
#     goes on (DECISIONS.md, 2026-11-21, 1c). Its pins show until then; once
#     known it stays known in the game's persistent data (_urmpin_line), so
#     it never blinks or stops a skip again, also after the game closes. A
#     hotspot scene waits for a click, so the story does not go on under it;
#     a room shown and talked through first is forgotten again once the
#     game waits on it with no line running (call screen, _urmpin_waited;
#     DECISIONS.md, 2026-11-21, 1b).
#   - phone screens (a phone the game shows is its own menu, not the scene)
#   - URM's and URM+'s screens (their names, URM's layer)
#   - a spot covering most of the screen (click anywhere to go on)
#   - a button that is only words: its words already say it is clickable
#     (an empty text button, an invisible spot some games use, stays)
#
# Skipping: the check runs right after take_focuses(), which every
# interaction runs on its first frame, before any event - so the skip is
# stopped before the line it is on would advance. It stops the way the
# engine's own say behaviour does (config.skipping = None plus
# restart_interaction). Only a spot that was not there one frame earlier
# stops it: a player who starts skipping with spots on screen keeps
# skipping. A spot is known by the line of the screen that makes it and the
# picture it shows (_urmpin_key), not by its box: one that moves stays the
# same spot, one that takes another's place is new. Transitions do not run
# while skipping, so a spot never blinks out and back in during a skip.
# A fast skip (to the next choice) draws no frame for the lines it passes:
# each one only calls config.fast_skipping_callbacks. There, a screen of the
# scene that is new since the last frame turns the fast skip into a normal
# one, so the next line is drawn: spots on it stop the skip there, and
# without spots the fast skip goes on (_urmpin_fast).
#
# The pins are drawn on the overlay layer (config.overlay_functions, in
# every engine 7.3.5 - 8.5 and hidden in menus), one frame behind the list:
# a change in the spots redraws them at once.

init 999 python:

    # The game's interface screens, by the names Ren'Py's own screens.rpy
    # gives them.
    _URMPIN_UI = frozenset((
        "say", "choice", "nvl", "nvl_choice", "input", "confirm", "yesno_prompt",
        "notify", "skip_indicator", "quick_menu", "ctc", "bubble",
        "main_menu", "game_menu", "navigation", "file_slots", "save", "load",
        "preferences", "history", "help", "about", "keyboard_help",
        "mouse_help", "gamepad_help"))

    # Part of the screen a spot may cover and still be a spot.
    _URMPIN_MOST = 0.75
    # Lines of dialogue a screen stays up through to count as interface.
    _URMPIN_LINES = 3
    # One blink, in seconds.
    _URMPIN_PULSE = 1.2

    # The pin's number: DejaVu Sans Bold, which every Ren'Py ships, drawn
    # unhinted with the FreeType shaper in every engine (8.x's HarfBuzz
    # shaper places glyphs differently; hinting snaps them by size). Then a
    # digit's box is 0.70 of the type size wide, and its ink stands in from
    # the box's left, right, top and bottom by these parts of the type size
    # (measured 7.3.5 - 8.5, the box 1.165 high). The number is placed by
    # its ink, not by its box.
    _URMPIN_FONT = "DejaVuSans-Bold.ttf"
    _URMPIN_ADVANCE = 0.70
    _URMPIN_LINE = 1.165
    _URMPIN_INK = {
        "0": (0.0725, 0.0250, 0.190, 0.220), "1": (0.1475, 0.0375, 0.200, 0.235),
        "2": (0.1250, 0.0450, 0.185, 0.235), "3": (0.1050, 0.0425, 0.190, 0.220),
        "4": (0.0700, 0.0250, 0.200, 0.235), "5": (0.1100, 0.0400, 0.200, 0.220),
        "6": (0.0850, 0.0325, 0.190, 0.220), "7": (0.1050, 0.0425, 0.200, 0.235),
        "8": (0.0900, 0.0350, 0.190, 0.220), "9": (0.0800, 0.0375, 0.190, 0.220)}
    _URMPIN_STYLE = python_dict()
    for _urmpin_prop, _urmpin_value in (("shaper", "freetype"), ("hinting", "none")):
        if _urmpin_prop in getattr(renpy.style, "prefixed_all_properties", ()):
            _URMPIN_STYLE[_urmpin_prop] = _urmpin_value

    class _URMPinState(python_object):
        def __init__(self):
            self.spots = ()             # ((x, y, w, h), ...), in reading order
            self.keys = frozenset()     # _urmpin_key of each spot
            self.shown = frozenset()    # (layer, tag) of the screens shown
            self.slowed = False         # a fast skip made normal for a frame
            self.inks = python_dict()   # picture -> where it has ink
            self.lines = python_dict()  # (layer, tag) -> lines it stayed up through

    _urmpin_st = _URMPinState()

    def _urmpin_known():
        """(layer, tag) of the screens known as interface for this game:
        kept in its persistent data, so they stay known after it closes."""

        return getattr(renpy.game.persistent, "_urmpin_ui", None) or frozenset()

    def _urmpin_ui_screen(screen, always, known):
        """True when the screen is not part of the scene."""

        if screen is None:
            return True
        if getattr(screen, "layer", None) == _urmi_layer:
            return True
        if (getattr(screen, "layer", None), getattr(screen, "tag", None)) in known:
            return True
        names = python_list(getattr(screen, "screen_name", None) or ())[:1]
        tag = getattr(screen, "tag", None)
        if tag:
            names.append(tag)
        for name in names:
            low = str(name).lower()
            if name in _URMPIN_UI or name in always:
                return True
            if low.startswith("urm") or "phone" in low:
                return True
        return False

    def _urmpin_mask_picture(widget):
        """The picture a focus_mask button is clickable on, or None."""

        style = widget.style
        mask = getattr(style, "focus_mask", None)
        if not mask:
            return None
        found = mask
        if mask is True:
            # what the button shows now: an imagebutton's picture for its
            # state (get_child), or a button's child
            shows = getattr(widget, "get_child", None)
            found = shows() if shows is not None else None
            found = found or getattr(style, "child", None) or getattr(widget, "child", None)
        for _depth in range(8):
            if found is None or isinstance(found, renpy.display.im.ImageBase):
                return found
            target = getattr(found, "target", None)
            if target is None and hasattr(found, "find_target"):
                found.find_target()
                target = getattr(found, "target", None)
            found = target if target is not None else getattr(found, "child", None)
        return None

    def _urmpin_ink(widget, box):
        """Where on screen the button can be clicked: its box, or for a
        focus_mask button the part of its picture that has ink. None when
        the picture has no ink at all."""

        try:
            picture = _urmpin_mask_picture(widget)
            if picture is None:
                return box
            inks = _urmpin_st.inks
            found = inks.get(picture)
            if found is None:
                # Decoded here once per picture (the renderer keeps only its
                # texture); then kept in inks.
                surf = picture.load()
                sw, sh = surf.get_size()
                r = surf.get_bounding_rect()
                found = (sw, sh, r.x, r.y, r.w, r.h)
                inks[picture] = found
            sw, sh, rx, ry, rw, rh = found
            if not rw or not rh:
                return None
            x, y, w, h = box
            fx, fy = w / float(sw), h / float(sh)
            return (x + rx * fx, y + ry * fy, rw * fx, rh * fy)
        except Exception:
            return box

    def _urmpin_look(widget):
        """What a button shows when idle, as a value that stays the same
        from frame to frame: an image's name, or a picture's identity."""

        states = getattr(widget, "state_children", None)
        d = states.get("idle_") if states else None
        if d is None:
            d = getattr(widget, "child", None)
        for _depth in range(8):
            if d is None:
                return None
            if isinstance(d, renpy.display.image.ImageReference) and getattr(d, "name", None):
                return ("image",) + tuple(d.name)
            if isinstance(d, renpy.display.im.ImageBase):
                return ("im", d.identity)
            d = getattr(d, "target", None) or getattr(d, "child", None)
        return None

    def _urmpin_key(screen, widget):
        """Which spot this is, the same while it moves: its screen, the line
        of the screen's code that makes it, and its picture."""

        return (getattr(screen, "layer", None), getattr(screen, "tag", None),
                getattr(widget, "_location", None), _urmpin_look(widget))

    def _urmpin_is_spot(focus):
        if focus.x is None or not focus.w or not focus.h:
            return False
        widget = focus.widget
        if not isinstance(widget, renpy.display.behavior.Button):
            return False
        child = getattr(widget, "child", None)
        if isinstance(child, renpy.text.text.Text):
            # Words on show say it is clickable; an empty text button is an
            # invisible spot.
            words = getattr(child, "text", None) or ()
            if u"".join(w for w in words if isinstance(w, basestring)).strip():
                return False
        return True

    def _urmpin_find(focuses):
        """(spots, keys) for a focus list: the spots' boxes in reading order,
        and a key for each that stays while it moves (_urmpin_key, and an
        order among spots that share one, as a loop's buttons do)."""

        store = renpy.store
        if getattr(store, "_menu", False) or getattr(store, "main_menu", False):
            return (), frozenset()
        width, height = config.screen_width, config.screen_height
        most = _URMPIN_MOST * width * height
        always = frozenset(getattr(config, "overlay_screens", ()) or ())
        known = _urmpin_known()
        verdict = python_dict()
        boxes = python_set()
        alike = python_dict()
        for focus in focuses:
            if not _urmpin_is_spot(focus):
                continue
            screen = focus.screen
            if id(screen) not in verdict:
                verdict[id(screen)] = _urmpin_ui_screen(screen, always, known)
            if verdict[id(screen)]:
                continue
            ink = _urmpin_ink(focus.widget, (focus.x, focus.y, focus.w, focus.h))
            if ink is None or ink[2] * ink[3] >= most:
                continue
            box = tuple(int(round(v)) for v in ink)
            boxes.add(box)
            alike.setdefault(_urmpin_key(screen, focus.widget), python_set()).add(box)
        keys = python_set()
        for key, held in alike.items():
            for n in range(len(held)):
                keys.add(key + (n,))
        row = height / 12.0
        spots = tuple(sorted(boxes, key=lambda b: (int((b[1] + b[3] / 2.0) / row), b[0] + b[2] / 2.0)))
        return spots, frozenset(keys)

    def _urmpin_shown():
        """{(layer, tag): screen} of the screens shown in this context."""

        out = python_dict()
        try:
            for layer, entries in renpy.game.context().scene_lists.layers.items():
                for entry in entries:
                    d = getattr(entry, "displayable", None)
                    if isinstance(d, renpy.display.screen.ScreenDisplayable):
                        out[(layer, getattr(entry, "tag", None))] = d
        except Exception:
            pass
        return out

    def _urmpin_waited(shown):
        """A screen known as interface that the game now waits on, with no
        line running (call screen: shown for that one wait), is a room after
        all: forgotten, so its spots get pins again (DECISIONS.md,
        2026-11-21, 1b). A screen the game keeps up while it waits on
        another stays known."""

        known = _urmpin_known()
        back = frozenset(key for key, screen in shown.items()
                         if key in known and getattr(screen, "transient", False))
        if back:
            renpy.game.persistent._urmpin_ui = frozenset(known) - back

    def _urmpin_after_focus():
        st = _urmpin_st
        shown = _urmpin_shown()
        _urmpin_waited(shown)
        spots, keys = _urmpin_find(renpy.display.focus.focus_list)
        stopped = False
        if config.skipping and (keys - st.keys):
            config.skipping = None
            renpy.restart_interaction()
            stopped = True
        if st.slowed:
            # The line a fast skip was slowed down for is drawn: no spot
            # stopped it, so the fast skip goes on.
            st.slowed = False
            if not stopped and config.skipping == "slow":
                config.skipping = "fast"
        st.keys = keys
        st.shown = frozenset(shown)
        if spots != st.spots:
            st.spots = spots
            renpy.redraw(_urmpin_view, 0)

    def _urmpin_fast():
        """config.fast_skipping_callbacks: a line passed by a fast skip. A
        screen of the scene shown since the last frame may hold spots, and
        no frame is drawn to find them: skip the next line normally."""

        st = _urmpin_st
        if config.skipping != "fast":
            return
        always = frozenset(getattr(config, "overlay_screens", ()) or ())
        known = _urmpin_known()
        for key, screen in _urmpin_shown().items():
            if key not in st.shown and not _urmpin_ui_screen(screen, always, known):
                config.skipping = "slow"
                st.slowed = True
                return

    def _urmpin_line():
        """A line of dialogue begins, or a fast skip passes one: each screen
        of the scene that stayed up since the line before has stayed up
        through one more. One up through _URMPIN_LINES is the game's
        interface, kept in the game's persistent data."""

        st = _urmpin_st
        always = frozenset(getattr(config, "overlay_screens", ()) or ())
        known = _urmpin_known()
        lines = python_dict()
        new = python_list()
        for key, screen in _urmpin_shown().items():
            if _urmpin_ui_screen(screen, always, known):
                continue
            lines[key] = st.lines.get(key, 0) + 1
            if lines[key] >= _URMPIN_LINES:
                new.append(key)
        st.lines = lines
        if new:
            renpy.game.persistent._urmpin_ui = frozenset(known) | frozenset(new)

    def _urmpin_png(side, fill, ink, ring):
        """A round pin, `side` pixels square, as PNG bytes: `fill` inside a
        ring of `ink` `ring` pixels wide, its edges smoothed. Drawn here, so
        it is round and centred to the pixel in every engine (a font's dot
        sits where the font puts it: 6 px low at this size)."""

        import math
        import struct
        import zlib
        outer = side / 2.0 - 1.0
        inner = outer - ring
        rows = bytearray()
        for j in range(side):
            rows.append(0)
            dy = j + 0.5 - side / 2.0
            for i in range(side):
                dx = i + 0.5 - side / 2.0
                d = math.sqrt(dx * dx + dy * dy)
                a_out = min(1.0, max(0.0, outer - d + 0.5))
                a_in = min(1.0, max(0.0, inner - d + 0.5))
                if a_out <= 0.0:
                    rows.extend((0, 0, 0, 0))
                    continue
                k = a_in / a_out
                rows.extend([int(round(fill[c] * k + ink[c] * (1.0 - k))) for c in range(3)])
                rows.append(int(round(255 * a_out)))

        def chunk(kind, data):
            body = kind + data
            return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)

        return (bytes(bytearray((137, 80, 78, 71, 13, 10, 26, 10)))
                + chunk(b"IHDR", struct.pack(">IIBBBBB", side, side, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(bytes(rows))) + chunk(b"IEND", b""))

    class _URMPinView(renpy.Displayable):
        """The pins: a numbered dot on the middle of each spot, blinking."""

        def __init__(self):
            renpy.Displayable.__init__(self)
            self.parts = python_dict()

        def side(self):
            """The dot's width on screen, from the game's height."""
            return max(28, int(config.screen_height / 20)) // 2 * 2

        def pin_of(self, n, side):
            """One pin, `side` pixels square, as a displayable made once:
            the engine keeps its render from frame to frame."""

            fill = renpy.easy.color(urm_map_colour("warnBg"))
            ink = renpy.easy.color(urm_map_colour("warnText"))
            key = (n, side, tuple(fill), tuple(ink))
            found = self.parts.get(key)
            if found is not None:
                return found
            # The dot, drawn at twice the size and shown at half: sharp on a
            # window up to twice the game's own size.
            png = _urmpin_png(2 * side, fill, ink, max(2, side // 9))
            name = "urm_pin_%d_%s_%s.png" % (side, "".join("%02x" % c for c in fill),
                                             "".join("%02x" % c for c in ink))
            disc = Transform(im.Data(png, name), zoom=0.5)
            size = max(12, int(side * 0.55))
            text = Text(u"%d" % n, font=_URMPIN_FONT, size=size, bold=False,
                        color=urm_map_colour("warnText"), outlines=[], drop_shadow=None,
                        italic=False, underline=False, strikethrough=False,
                        kerning=0, layout="nobreak", text_align=0.5, **_URMPIN_STYLE)
            digits = [_URMPIN_INK[d] for d in u"%d" % n]
            left = digits[0][0]
            right = len(digits) * _URMPIN_ADVANCE - digits[-1][1]
            top = min(d[2] for d in digits)
            bottom = _URMPIN_LINE - max(d[3] for d in digits)
            # whole pixels: what every renderer draws alike
            at_x = int(round(side / 2.0 - (left + right) / 2.0 * size))
            at_y = int(round(side / 2.0 - (top + bottom) / 2.0 * size))
            found = renpy.display.layout.Fixed(xysize=(side, side))
            found.add(Transform(disc, xpos=0, ypos=0, xanchor=0, yanchor=0))
            found.add(Transform(text, xpos=at_x, ypos=at_y, xanchor=0, yanchor=0))
            self.parts[key] = found
            return found

        def pin(self, n, side, st, at):
            return renpy.render(self.pin_of(n, side), side, side, st, at)

        def render(self, width, height, st, at):
            rv = renpy.Render(width, height)
            spots = _urmpin_st.spots
            if not spots:
                return rv
            side = self.side()
            # A pin does not change with time (the blink is this render's
            # alpha): drawn at time 0, the engine draws each pin once.
            for number, (x, y, w, h) in enumerate(spots, 1):
                rv.blit(self.pin(number, side, 0, 0),
                        (int(round(x + w / 2.0 - side / 2.0)), int(round(y + h / 2.0 - side / 2.0))))
            # The blink: full, down to a third, and back, once a period.
            wave = 0.5 + 0.5 * __import__("math").cos(2 * 3.141592653589793 * (st % _URMPIN_PULSE) / _URMPIN_PULSE)
            rv.alpha = 0.3 + 0.7 * wave
            renpy.redraw(self, 1.0 / 30)
            return rv

        def visit(self):
            return []

    _urmpin_view = _URMPinView()

    def _urmpin_overlay():
        ui.add(_urmpin_view)

    def _urmpin_wrap(original):
        def take_focuses(*args, **kwargs):
            rv = original(*args, **kwargs)
            try:
                renpy.store._urmpin_after_focus()
            except Exception:
                pass
            return rv
        take_focuses._urmpin = True
        return take_focuses

    def _urmpin_fast_skipping():
        try:
            renpy.store._urmpin_line()
            renpy.store._urmpin_fast()
        except Exception:
            pass
    _urmpin_fast_skipping._urmpin = True

    def _urmpin_said(event, **kwargs):
        """config.all_character_callbacks: a line of dialogue begins. A line
        the player goes back or forward over again (rollback, roll-forward:
        the engine's own test, loadsave.py) is not a new one."""
        if event == "begin" and not (renpy.game.after_rollback or renpy.exports.in_rollback()):
            try:
                renpy.store._urmpin_line()
            except Exception:
                pass
    _urmpin_said._urmpin = True

    # A generator, not a list: a list's loop name lands in the game's
    # store on Python 2 (check_store_names.py).
    try:
        if not getattr(renpy.display.focus.take_focuses, "_urmpin", False):
            renpy.display.focus.take_focuses = _urmpin_wrap(renpy.display.focus.take_focuses)
        if _urmpin_overlay not in config.overlay_functions:
            config.overlay_functions.append(_urmpin_overlay)
        if not any(getattr(c, "_urmpin", False) for c in config.fast_skipping_callbacks):
            config.fast_skipping_callbacks.append(_urmpin_fast_skipping)
        if not any(getattr(c, "_urmpin", False) for c in config.all_character_callbacks):
            config.all_character_callbacks.append(_urmpin_said)
    except Exception as error:
        print("MRM: clickable spots are not pinned (%s)" % (error,))
