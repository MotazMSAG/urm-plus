# ---------------------------------------------------------------------------
# Game font: replace the game's own font with a readable one
# ---------------------------------------------------------------------------
#
# Some games set every line in Comic Sans. "Game font" in Miscellaneous swaps
# the game's fonts for one that already ships: DejaVu Sans and OpenDyslexic
# come with every Ren'Py, Roboto, Comfortaa and Roboto Mono with URM+ (our
# own copies from Google Fonts, urm_compat/fonts, under the OFL).
#
# It rides on the engine's own accessibility hook (preferences.font_transform
# plus config.font_transforms, there since Ren'Py 6.99 - the Shift+A font
# override). The transform leaves our screens' fonts, URM's own (while URM
# is installed beside us, its screens keep their font) and any icon font alone,
# and keeps the game's font for characters the new one does not have, so a
# Japanese or emoji line still renders. With "Game's own" the preference is
# put back to None, and an unknown transform name is ignored by the engine,
# so removing URM+ leaves nothing behind.

init 999 python:

    _urm_setting_add("urmcFont", None)

    # Characters Roboto, Comfortaa and Roboto Mono all have (read from the
    # fonts URM shipped; ours have them all, tests/check_fonts.py): Latin
    # with accents, Greek, Cyrillic, punctuation. DejaVu Sans has all of them
    # too.
    _URMFT_CHARSET = ("20-7e a0-148 14a-17f 192 1a0-1a1 1af-1b0 1fa-1ff 218-21b 237 259 2bc "
                      "2c6-2c7 2c9 2d8-2dd 300-301 303 309 30f 323 384-38a 38c 38e-3a1 3a3-3ce "
                      "400-45f 462-463 46a-46b 472-475 490-49d 4a0-4a5 4aa-4ab 4ae-4b1 4b6-4bb "
                      "4c0-4c2 4cb-4cc 4cf-4d9 4dc-4df 4e2-4e9 4ee-4f9 1e80-1e85 1ea0-1ef9 "
                      "2013-2015 2017-201e 2020-2022 2026 2030 2032-2033 2039-203a 203c 2044 2074 "
                      "20a3-20a4 20a7 20ab-20ac 2105 2113 2116 2122 2126 212e 215b-215e 2202 2206 "
                      "220f 2211-2212 221a 221e 222b 2248 2260 2264-2265")

    # key, name shown, file the option needs, how it is applied. DejaVu is
    # not the engine's "dejavusans": before 8.x that one swaps every
    # character, with no fallback, so a Japanese line became boxes.
    _URMFT_FONTS = (
        ("dejavu", "DejaVu Sans", "DejaVuSans.ttf", None),
        ("roboto", "Roboto", "urmplus/fonts/Roboto-Regular.ttf", None),
        ("comfortaa", "Comfortaa", "urmplus/fonts/Comfortaa.ttf", None),
        ("mono", "Roboto Mono", "urmplus/fonts/RobotoMono.ttf", None),
        ("dyslexic", "OpenDyslexic", "_OpenDyslexic3-Regular.ttf", "opendyslexic"),
    )

    _URMFT_KEEP = ("icon", "awesome", "symbol", "emoji", "material", "dingbat", "wingding", "webding")

    class _URMFTState(python_object):
        def __init__(self):
            self.applied = None
            self.groups = python_dict()

    _urmft_st = _URMFTState()

    def _urmft_table():
        """The engine's table of font overrides. None in a game that put
        something else there (My Femdom Wife 0.7: a list): the engine cannot
        apply any override then, and asking it for one stops the game."""
        table = getattr(config, "font_transforms", None)
        return table if isinstance(table, python_dict) else None

    def _urmft_available():
        out = python_list()
        table = _urmft_table()
        if table is None:
            return out
        for key, name, path, engine in _URMFT_FONTS:
            try:
                if engine is not None and engine not in table:
                    continue
                if renpy.loadable(path):
                    out.append((key, name, path, engine))
            except Exception:
                continue
        return out

    def _urmft_find(key):
        for row in _urmft_available():
            if row[0] == key:
                return row
        return None

    def _urmft_keep(f):
        if not isinstance(f, (str, type(u""))):
            return True   # already a FontGroup the game built - leave it whole
        name = f.replace("\\", "/").lower()
        if name.startswith("urmplus/"):
            return True     # the screen kit has its own fonts
        return any(word in name for word in _URMFT_KEEP)

    def _urmft_map(key, f):
        """What font `f` becomes with option `key` (None: unchanged)."""
        if key is None or _urmft_keep(f):
            return f
        row = _urmft_find(key)
        if row is None:
            return f
        _key, _name, path, engine = row
        if engine is not None:
            return config.font_transforms[engine](f)
        group = _urmft_st.groups.get((path, f))
        if group is None:
            group = FontGroup()
            for part in _URMFT_CHARSET.split():
                start, _sep, end = part.partition("-")
                group.add(path, int(start, 16), int(end or start, 16))
            group.add(f, None, None)
            _urmft_st.groups[(path, f)] = group
        return group

    def _urmft_transform(f):
        try:
            return _urmft_map(_urmft_st.applied, f)
        except Exception:
            return f

    if _urmft_table() is not None:
        config.font_transforms["urmplus"] = _urmft_transform

    def _urmft_wanted():
        key = _urm_setting("urmcFont")
        return key if _urmft_find(key) is not None else None

    def _urmft_sync(reset):
        key = _urmft_wanted()
        prefs = renpy.game.preferences
        current = getattr(prefs, "font_transform", None)
        if key == _urmft_st.applied and (current == "urmplus") == (key is not None):
            return
        _urmft_st.applied = key
        if key is not None:
            prefs.font_transform = "urmplus"
        elif current == "urmplus":
            prefs.font_transform = None
        if reset:
            # What the engine's own font preference does (_DisplayReset).
            renpy.free_memory()
            renpy.display.interface.display_reset = True
            renpy.restart_interaction()

    def _urmft_choices():
        """[(words, value)]: the game's own font, then each one it can load."""
        rows = [("Game's own", None)]
        rows += [(name, key) for key, name, _p, _e in _urmft_available()]
        return rows

    # The row in URM's options page (a hook) asks these two, until our own
    # settings page takes its place.
    def urmft_options():
        import collections
        return collections.OrderedDict(_urmft_choices())

    def urmft_label():
        row = _urmft_find(_urmft_wanted())
        return row[1] if row else "Game's own"

    def _urmft_interact():
        try:
            _urmft_sync(True)
        except Exception:
            pass

    try:
        _urmft_sync(False)
    except Exception as error:
        print("MRM: game font not applied (%s)" % (error,))

    if _urmft_interact not in config.interact_callbacks:
        config.interact_callbacks.append(_urmft_interact)

    # Apply at once when the option is clicked, not at the next line.
    def _urmft_changed():
        _urmft_sync(True)

    _urm_setting_watch("urmcFont", _urmft_changed)

    # ---- the URM+ settings page (the registry, 01_urm_door)

    _urm_row_add("game_font", "look", "Game font",
                 "Shows the game's text in another font. Only fonts that already ship are offered.",
                 _urmft_choices, setting="urmcFont", order=10)
