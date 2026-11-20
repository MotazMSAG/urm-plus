"""
Checks a game whose config.font_transforms is not a table.

    <any python, 2.7 or 3> -B check_fonts.py

My Femdom Wife 0.7 (Ren'Py 8.3.7) has `config.font_transforms = ["smooth"]`
at init 0. URM's FontsHandler indexes that table by name at init 999 and the
game stopped while loading; URM+'s own "Game font" wrote to the same table
one block later.

Two pieces of the add-on are run here as the engine runs them, against
stand-ins for the engine and URM:
  - the early block of 00_urm_fixes (init 998), then URM's FontsHandler loop
    word for word, then the hand-back the first init 999 block starts with;
  - the block of 87_font, on a table and on the game's list.

No engine is needed: nothing here depends on one. The gate runs the same
case on every real engine (check_installer.py, the font list scenario).
"""

from __future__ import print_function

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import urm_source  # noqa  (the add-on's code, joined from its pieces)

failures = []


def check(name, got, want=True):
    if got == want:
        print("pass  %s" % name)
    else:
        failures.append(name)
        print("FAIL  %s" % name)
        print("        expected %r" % (want,))
        print("        got      %r" % (got,))


class Bag(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)


def engine_fonts():
    """What the engine puts there (renpy/common/00accessibility.rpy)."""

    def opendyslexic(f):
        return ("group", f)

    def dejavusans(f):
        return "DejaVuSans.ttf"

    return {"opendyslexic": opendyslexic, "dejavusans": dejavusans}


ICONS = ["MaterialIcons-Regular.ttf", "MaterialIconsOutlined-Regular.otf"]


def urm_fonts_handler(config):
    """URM 2.6.2, classes/FontsHandler.rpy:11-23, word for word."""

    def createHandler(fontName, originalMethod):
        def handler(requestedFontName):
            if requestedFontName.endswith(ICONS[0]) or requestedFontName.endswith(ICONS[1]):
                return requestedFontName
            elif originalMethod:
                return originalMethod(requestedFontName)
        return handler

    if hasattr(config, "font_transforms"):
        for font in config.font_transforms:
            config.font_transforms[font] = createHandler(font, config.font_transforms[font])


def early(config):
    """The early block, run on `config`. Returns its namespace."""

    space = {"renpy": Bag(config=config), "python_dict": dict, "python_list": list,
             "str": type(u"")}
    exec(compile(urm_source.early_block(), "early block", "exec"), space)
    return space


# --- 1. the early block -----------------------------------------------------

def early_cases():

    print("[1] the game's list: URM starts, the list goes back as it was")
    own = ["smooth"]
    config = Bag(font_transforms=own)
    space = early(config)
    check("while URM starts, a table stands in for the list",
          (type(config.font_transforms), len(config.font_transforms), config.font_transforms is own),
          (dict, 0, False))
    try:
        urm_fonts_handler(config)
        raised = None
    except Exception as error:
        raised = "%s: %s" % (type(error).__name__, error)
    check("URM's FontsHandler runs without raising", raised, None)
    space["_urm_fonts_close"]()
    check("afterwards the game's own list is back, the same object",
          (config.font_transforms is own, own), (True, ["smooth"]))
    space["_urm_fonts_close"]()
    check("handing back twice changes nothing", config.font_transforms is own)

    print("[2] a real table is never touched")
    table = engine_fonts()
    before = dict(table)
    config = Bag(font_transforms=table)
    space = early(config)
    check("the table is left where it is", config.font_transforms is table)
    urm_fonts_handler(config)
    space["_urm_fonts_close"]()
    check("still the same table afterwards", config.font_transforms is table)
    check("URM wrapped its entries: an icon font is kept by every override",
          sorted((name, table[name]("0x52-URM/framework/" + ICONS[0])) for name in table),
          sorted((name, "0x52-URM/framework/" + ICONS[0]) for name in before))
    check("and any other font still goes through the engine's own function",
          (table["dejavusans"]("game/comic.ttf"), table["opendyslexic"]("game/comic.ttf")),
          ("DejaVuSans.ttf", ("group", "game/comic.ttf")))

    print("[3] other values a game can leave there")
    for value in (None, ("smooth",), "smooth", 3):
        config = Bag(font_transforms=value)
        space = early(config)
        try:
            urm_fonts_handler(config)
            raised = None
        except Exception as error:
            raised = "%s: %s" % (type(error).__name__, error)
        space["_urm_fonts_close"]()
        check("%r: URM starts and the value goes back" % (value,),
              (raised, config.font_transforms is value), (None, True))

    config = Bag(font_transforms=["smooth"])
    space = early(config)
    newer = {"mine": len}
    config.font_transforms = newer
    space["_urm_fonts_close"]()
    check("a value the game put there while URM started is not overwritten",
          config.font_transforms is newer)

    config = Bag()
    space = early(config)
    space["_urm_fonts_close"]()
    check("an engine without config.font_transforms: nothing is added",
          hasattr(config, "font_transforms"), False)


try:
    early_cases()
except SystemExit as stop:
    check("the early block is in the source", str(stop), "")

# --- 2. URM+'s own Game font ------------------------------------------------

def font_block(table, wanted=None, preference=None):
    """The block of 87_font, run with `table` as config.font_transforms.
    Returns (namespace, config, preferences, error)."""

    settings = Bag(defaultValues={}, set=lambda self, name, *a, **k: None)
    config = Bag(font_transforms=table, interact_callbacks=[])
    prefs = Bag(font_transform=preference)

    class Group(object):
        def __init__(self):
            self.parts = []

        def add(self, *args):
            self.parts.append(args)

    space = {
        "python_object": object, "python_dict": dict, "python_list": list,
        "str": type(u""), "config": config, "FontGroup": Group,
        "x52URM": Bag(SettingsClass=settings,
                      Settings=Bag(get=lambda name: wanted),
                      OrderedDict=dict),
        "renpy": Bag(loadable=lambda path: True, game=Bag(preferences=prefs),
                     free_memory=lambda: None, restart_interaction=lambda: None,
                     display=Bag(interface=Bag(display_reset=False))),
    }
    try:
        exec(compile(urm_source.block("def _urmft_available"), "87_font", "exec"), space)
        error = None
    except Exception as e:
        error = "%s: %s" % (type(e).__name__, e)
    return space, config, prefs, error


print("[4] Game font, in a game with the engine's table")
table = engine_fonts()
space, config, prefs, error = font_block(table, wanted="roboto")
check("the block runs", error, None)
if error is None:
    check("every option is offered",
          [row[0] for row in space["_urmft_available"]()],
          ["dejavu", "roboto", "comfortaa", "mono", "dyslexic"])
    check("URM+'s override is in the engine's table",
          table.get("urmplus") is space["_urmft_transform"])
    check("the chosen font is applied through the engine's preference",
          prefs.font_transform, "urmplus")

print("[5] Game font, in a game with a list there")
own = ["smooth"]
space, config, prefs, error = font_block(own, wanted="roboto", preference=None)
check("the block runs", error, None)
if error is None:
    check("the game's list is as it was", (config.font_transforms is own, own), (True, ["smooth"]))
    check("no option is offered", space["_urmft_available"](), [])
    check("the menu shows only the game's own font", len(space["urmft_options"]()), 1)
    check("a font chosen in another game is not asked of the engine "
          "(with a list there, any override stops the game)", prefs.font_transform, None)
    space["_urmft_interact"]()
    check("nor at the next interaction", prefs.font_transform, None)

space, config, prefs, error = font_block(["smooth"], wanted=None, preference="urmplus")
if error is None:
    check("a preference URM+ left earlier is taken back", prefs.font_transform, None)
else:
    check("the block runs with a preference left earlier", error, None)

print()
if failures:
    print("%d FAILED" % len(failures))
    for name in failures:
        print("  - " + name)
    sys.exit(1)
print("all passed")
