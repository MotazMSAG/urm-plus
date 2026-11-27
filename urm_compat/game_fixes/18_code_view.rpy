# The code view: a scene's script lines, coloured, in a full-height panel
# at the right (UX rule 2: the code stays one click away; the user's pick
# 2b, 2026-11-22). The corner card's title opens it (urmk_code_show) with
# the lines it is about marked by a blue edge; the screen is in
# game_screens/18_code_view. It lives on our layer, draws only while the
# story runs (a game's menus carry our layer with them), and closes with
# its close button, Esc and right-click. Lines do not wrap unless the
# player turns wrapping on; the wheel scrolls up and down, Shift + wheel
# sideways, and both bars are the view's own (a game's scrollbar style can
# have no height).

init 999 python:

    import re as _urmk_code_re

    # The code's colours, on its opaque ground: one per kind of word, softened
    # for our panels (the user's 3a). None of them is a tone: they say what a
    # word is, never good or bad.
    URMK_CODE_COLOURS = python_dict((
        ("ground", "#edf0f4"),
        ("keyword", "#881c4d"),    # a statement or Python keyword, $
        ("string", "#843c22"),
        ("name", "#163f7a"),       # a name: a value, a speaker, an image
        ("call", "#6c4700"),       # a label jumped to, a function called
        ("number", "#275724"),     # a number, True, False, None
        ("op", "#303a46"),         # the signs between words
        ("comment", "#425661"),
        ("gutter", "#4f5863"),     # the line numbers
        ("mark", "#c5dcff"),     # a marked line's ground
        ("bar", "#24384a38"),      # a scrollbar's track
        ("thumb", "#344b68a6"),    # and its thumb
    ))
    URMK_CODE_FONT = "urmplus/fonts/RobotoMono.ttf"
    URMK_CODE_SIZE = (16, 28)      # the code's words and line, at 1080 lines
    URMK_CODE_WIDTH = 860          # the panel, at 1080 lines
    URMK_CODE_SIDE = 64            # what Shift + wheel moves, at 1080 lines

    _URMK_CODE_KEYWORDS = frozenset((
        "and", "or", "not", "is", "in", "if", "elif", "else", "for", "while",
        "jump", "call", "return", "pass", "import", "from", "as", "with",
        "try", "except", "finally", "raise", "break", "continue", "del",
        "def", "class", "lambda", "global", "label", "menu", "scene", "show",
        "hide", "at", "play", "stop", "queue", "voice", "window", "pause",
        "python", "init", "define", "default", "expression", "nvl"))
    _URMK_CODE_CONSTANTS = frozenset(("True", "False", "None"))
    _URMK_CODE_TOKEN = _urmk_code_re.compile(
        r"(#.*$)"
        r"|(\"(?:[^\"\\]|\\.)*\"?|'(?:[^'\\]|\\.)*'?)"
        r"|(\b\d+(?:\.\d+)?\b)"
        r"|([A-Za-z_][\w.]*)"
        r"|(\$)")

    def _urmk_code_plain(text):
        """The game's own words as words: a `{` would start a text tag
        (tags are read even where nothing is substituted)."""

        return text.replace(u"{", u"{{")

    def _urmk_code_ink(kind, text):
        if not text:
            return u""
        return u"{color=%s}%s{/color}" % (URMK_CODE_COLOURS[kind], _urmk_code_plain(text))

    def _urmk_code_gap(text):
        """What lies between two words: spaces as they are, signs muted."""

        return _urmk_code_ink("op", text) if text.strip() else text

    def _urmk_code_line(line):
        """One line, its parts coloured."""

        out = python_list()
        at = 0
        before = u""
        for found in _URMK_CODE_TOKEN.finditer(line):
            out.append(_urmk_code_gap(line[at:found.start()]))
            at = found.end()
            word = found.group()
            if found.group(1):
                kind = "comment"
            elif found.group(2):
                kind = "string"
            elif found.group(3) or word in _URMK_CODE_CONSTANTS:
                kind = "number"
            elif found.group(5) or word in _URMK_CODE_KEYWORDS:
                kind = "keyword"
            elif before in ("jump", "call") or line[at:].lstrip().startswith(u"("):
                kind = "call"
            else:
                kind = "name"
            out.append(_urmk_code_ink(kind, word))
            before = word
        out.append(_urmk_code_gap(line[at:]))
        return u"".join(out)

    def urmk_code_words(code):
        """The code as the view shows it: every line coloured."""

        return u"\n".join(_urmk_code_line(line) for line in (code or u"").split(u"\n"))

    def urmk_code_rows(code, marked=None):
        """The view's rows: (number, coloured line, marked)."""

        marked = marked or ()
        rows = python_list()
        for n, line in enumerate((code or u"").split(u"\n")):
            on = any(first <= n < end for first, end in marked)
            rows.append((n + 1, _urmk_code_line(line), on))
        return rows

    # The code's words, urmk_code: our mono font at the code's size.
    style.urmk_code = Style("urmk_text")
    style.urmk_code.font = URMK_CODE_FONT
    style.urmk_code.size = urmk_px(URMK_CODE_SIZE[0])
    style.urmk_code.line_spacing = max(0, urmk_px(URMK_CODE_SIZE[1]) - urmk_px(URMK_CODE_SIZE[0]) - urmk_px(5))

    def urmk_code_mark():
        """A marked line's ground: the accent's edge, 3 wide, on a faint
        tint of it."""

        found = urmk_look.made.get("code_mark")
        if found is None:
            edge = urmk_px(3)
            box = Fixed(Solid(URMK_COLOURS["accent-ink"], xysize=(edge, 4)),
                        Solid(URMK_CODE_COLOURS["mark"], xpos=edge, xysize=(4, 4)),
                        xysize=(edge + 4, 4))
            found = urmk_look.made["code_mark"] = Frame(box, edge, 0, 0, 0)
        return found

    def urmk_code_side(adjustment, step):
        """Shift + wheel: the lines move sideways by `step` steps."""

        adjustment.change(adjustment.value + step * urmk_px(URMK_CODE_SIDE))

    def _urmk_shift_held():
        import pygame_sdl2
        return bool(pygame_sdl2.key.get_mods() & pygame_sdl2.KMOD_SHIFT)

    class _URMKCodeSide(renpy.display.core.Displayable):
        """Shift + wheel over the code view: the lines move sideways, and
        the view does not scroll down. Read here, not with a screen `key`:
        before 7.6 the engine reads no modifier on a mouse button, and with
        developer mode on "shift_mousedown_4" stops the game."""

        def __init__(self, adjustment, **properties):
            super(_URMKCodeSide, self).__init__(**properties)
            self.adjustment = adjustment

        def render(self, width, height, st, at):
            return renpy.display.render.Render(0, 0)

        def event(self, ev, x, y, st):
            import pygame_sdl2
            if (ev.type == pygame_sdl2.MOUSEBUTTONDOWN and getattr(ev, "button", None) in (4, 5)
                    and _urmk_shift_held()):
                urmk_code_side(self.adjustment, -1 if ev.button == 4 else 1)
                raise renpy.display.core.IgnoreEvent()
            return None

    # The view's lines are built as far as it is scrolled: a screenful and
    # more at first (URMK_CODE_ROOM), the next when it nears its end - a
    # scene's every line was 0.2 s to draw on Thief of Hearts 2 (FINDINGS).
    URMK_CODE_ROOM = 44
    URMK_CODE_ROWS = _URMKRows("code view", URMK_CODE_ROOM)
    urmk_code_adj = URMK_CODE_ROWS.adj

    def urmk_code_room():
        return URMK_CODE_ROWS.room()

    def urmk_code_show(code, title, marked=None, note=None, zorder=None):
        """Show `code` under `title` in the code view, on our layer:
        marked, the (first, end) lines to mark; note, what the marks are. A
        view already open gives way to it. zorder, its place on our layer
        when it opens above another window."""

        if not code or not renpy.has_screen("urmk_code_view"):
            return
        urmk_code_close()
        URMK_CODE_ROWS.top()
        renpy.show_screen("urmk_code_view", code=code, title=title,
                          marked=tuple(tuple(m) for m in (marked or ())), note=note,
                          _layer=_urmi_layer, _zorder=zorder)
        renpy.restart_interaction()

    def urmk_code_close():
        if renpy.get_screen("urmk_code_view", layer=_urmi_layer) is not None:
            renpy.hide_screen("urmk_code_view", layer=_urmi_layer)
            renpy.restart_interaction()
