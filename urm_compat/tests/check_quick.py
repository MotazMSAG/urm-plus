"""
Quick access (92_quick, the user's 1a) drawn and clicked in each prop's own
engine, with URM and without it.

    python check_quick.py <props folder> [--pictures <folder>]

Each prop's engine is started read-only with its `lint` command replaced,
on a base folder of its own (a temporary folder: nothing is written to the
prop): game/ holds the add-on as the one file a player can install
(make_rpy.build()), our fonts, the probe, and URM's archive in one of the
two runs. The probe lays out and renders the URM+ button's screen with the
engine and reads back where every word and icon is drawn: the tray under
the button in its blue, yellow and green states, never in the badge's room
and never in the choices card's usual spot; above it, past the badge, when
the button is dropped bottom left; gone while the menu is open or Quick
access is off. It runs the tray's buttons as a click would: the engine's
Auto (with a game speed of 0), Skip on a line never read, a right click
(the button's alternate) and a middle click (the tray's key) on Skip, and
the quick bar's middle-click catcher on the tray's Skip. A save keeps the
screen's scope: it must pickle.

--pictures writes the button and tray in each state, 1:1, per engine.
"""
# run_tests: props
# prop_probe: standalone

from __future__ import print_function

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import prop_probes  # noqa  (shared 1-boot-per-prop runner)

PROBE_CODE = u'''
init 1999 python:
    _qa_last = []
    _qa_boxes = []    # (button, x, y, w, h) of every button drawn

    def _qa_screen(name, picture=None):
        """The screen laid out and rendered by the engine: [(words, x, y,
        w, h, colour)] of every text drawn; with picture, also that PNG over
        a grey scene."""
        root = renpy.display.layout.Fixed()
        if picture:
            root.add(renpy.display.imagelike.Solid("#6f7c8c"))
        sd = renpy.display.screen.ScreenDisplayable(
            renpy.display.screen.get_screen_variant(name), name, "screens", scope={"_kwargs": {}})
        sd.update()
        sd.visit_all(lambda d: d.per_interact())
        root.add(sd)
        _qa_last[:] = [sd]
        rv = renpy.display.render.render_screen(root, config.screen_width, config.screen_height)
        out = []
        del _qa_boxes[:]

        def walk(r, x, y):
            for d in getattr(r, "render_of", ()) or ():
                if isinstance(d, renpy.text.text.Text):
                    said = u"".join(t for t in d.text if isinstance(t, (type(u""), type(""))))
                    out.append((said, x, y, r.width, r.height, tuple(renpy.easy.color(d.style.color))[:3],
                                d.style.size))
                elif isinstance(d, renpy.display.behavior.Button):
                    _qa_boxes.append((d, x, y, r.width, r.height))
            for c in r.children:
                if isinstance(c[0], renpy.display.render.Render):
                    walk(c[0], x + c[1], y + c[2])
        walk(rv, 0, 0)
        if picture:
            import pygame_sdl2 as pygame
            surf = pygame.Surface((config.screen_width, config.screen_height), pygame.SRCALPHA)
            surf.fill((0, 0, 0, 255))
            renpy.display.swdraw.draw(surf, None, rv, 0, 0, True)
            pygame.image.save(surf, picture)
        return out

    def urmq_pointed_name(button):
        fn = getattr(getattr(button, "action", None), "callable", None)
        return {urmq_auto: "auto", urmq_skip: "skip", urmq_unseen: "unseen"}.get(fn)

    def _qa_parts(kind):
        found = []
        _qa_last[0].visit_all(lambda d: found.append(d) if isinstance(d, kind) else None)
        return found

    def _qa_probe(lines, check, pic):
        import pickle
        try:
            W, H = config.screen_width, config.screen_height
            ICONS = (u"\\ue037", u"\\ue01f", u"\\ue8f4")
            says = {"now": None}
            _urm_status_add("aaqa", lambda: says["now"], order=-100)
            STATES = (("blue", None),
                      ("yellow", ("warn", u"\\ue0b6", u"14", u"14 lines until the paths meet",
                                  u"You picked: Stay", None)),
                      ("green", ("gain", u"\\ue5ca", None, u"The paths meet on this line",
                                 u"You picked: Stay", None)))
            hub = _urmh_state()

            # the lint run has no game running: the engine's Skip asks
            # whether a menu or the main menu is up
            renpy.context()._menu = False
            renpy.context()._main_menu = False
            check("quick access buttons are a usable, consistently clickable size",
                  36 <= URMQ["button"] <= 40, repr(URMQ))

            def drawn(picture=None):
                """(every word, the tray's icons, the URM+ label, the tray's
                buttons as boxes, the URM+ button's box)."""
                found = _qa_screen("urmh_button_in_game", picture)
                icons = [t for t in found if t[0] in ICONS and t[6] == urmq_px("icon")]
                label = [t for t in found if t[0] == u"MRM"]
                tray = [b for b in _qa_boxes if b[0].alternate is not None]
                main = [b for b in _qa_boxes if label and b[1] <= label[0][1] < b[1] + b[3]
                        and b[2] <= label[0][2] < b[2] + b[4]]
                return found, icons, label, tray, (sorted(main, key=lambda b: b[3] * b[4]) or [None])[0]

            # ---- off by default; the menu, the settings tab
            found, icons, label, tray, main = drawn()
            check("Quick access is off at first: only the button", not icons and label, repr([t[0] for t in found]))
            entry = [e for e in _urm_entries() if e.name == "quick"]
            check("the URM+ menu has a Quick access switch, off", entry and entry[0].on is False
                  and entry[0].words == "Quick access", repr(entry and entry[0].__dict__))
            sec = [s.words for s in _urm_sections()]
            rows = [(r.words, _urm_row_view(r.name).game_only) for r in _urm_rows("quick")]
            check("a settings tab Quick access, its rows with This game and All games",
                  "Quick access" in sec and rows == [("Quick access buttons", False), ("Auto", False),
                                                    ("Skip", False), ("Skip unseen text", False),
                                                    ("Menu", False), ("Story line", False),
                                                    ("Settings", False)], repr((sec, rows)))
            _urm_open("quick")
            check("the switch turns it on for all games", _urm_setting_at("urmcQuick", True) is True
                  and _urm_setting_at("urmcQuick", False) is None, "")

            # ---- under the button in each of its states
            room = urmk_room(urmh_room())
            pad = urmq_px("pad")
            near = lambda a, b: abs(a - b) <= 1

            def spans(boxes):
                return (min(b[1] for b in boxes), min(b[2] for b in boxes),
                        max(b[1] + b[3] for b in boxes), max(b[2] + b[4] for b in boxes))

            bad = []
            for name, status in STATES:
                says["now"] = status
                found, icons, label, tray, main = drawn(pic("tray_%s" % name))
                if len(icons) != 3 or len(tray) != 3 or main is None:
                    bad.append("%s: icons %r, %d buttons, button %r" % (name, [t[0] for t in found], len(tray), main))
                    continue
                left, top, right, bottom = spans(tray)
                _d, mx, my, mw, mh = main
                tone = [tuple(renpy.easy.color(URMK_COLOURS[k])[:3]) for k in ("warn-accent", "gain-accent")]
                if top - pad < my + mh + urmk_px(URMH_UNDER_GAP) - 1:
                    bad.append("%s: the tray reaches the button (%s, button ends %s)" % (name, top - pad, my + mh))
                if left < 0 or right > W:
                    bad.append("%s: tray buttons extend past the screen (%s, %s)" % (name, left, right))
                if [t for t in icons if tuple(t[5]) in tone]:
                    bad.append("%s: the tray takes the button's tone" % name)
                if name == "blue":
                    blue_at = (mx, my)
                elif (mx, my) != blue_at:
                    bad.append("%s: the button moved" % name)
            says["now"] = STATES[1][1]
            check("the tray hangs inside the screen under the button in blue, yellow and green: 8 under it, "
                  "never the tone's colour, the button where it was", not bad, "; ".join(bad))
            check("the choices card's usual spot is told how far the tray reaches",
                  urmh_under_px() == urmk_px(URMH_UNDER_GAP) + urmq_height(), repr(urmh_under_px()))
            # the choices card at its usual spot, drawn by its own screen:
            # its top (its title, less the card's padding and header) under
            # the tray, never over it
            tray_bottom = spans(tray)[3] + pad
            view = store.urm_corner_view
            store.urm_corner_view = lambda: [("choices", u"Probe card", False,
                                               [(("num", u"1"), False, u"Go left", False, None, [], False, False)],
                                               [])]
            try:
                card = _qa_screen("urm_corner")
            finally:
                store.urm_corner_view = view
            title = [t for t in card if t[0] == u"Probe card"]
            check("the choices card at its usual spot starts below the tray, never under it",
                  title and title[0][2] - urmk_px(16 + 12) >= tray_bottom,
                  repr((title and title[0][2], tray_bottom)))

            _urm_setting_set("urmcHubPos", (0.02, 0.9), True)
            found, icons, label, tray, main = drawn(pic("tray_bottom_left"))
            ok = len(tray) == 3 and main is not None
            if ok:
                left, top, right, bottom = spans(tray)
                ok = (bottom + pad <= main[2] - room[1] - urmk_px(URMH_UNDER_GAP) + 1
                      and near((left + right) / 2.0, main[1] + main[3] / 2.0))
            check("the button dropped bottom left: the tray centred above it, past the badge's room",
                  ok, repr(([b[1:] for b in tray], main and main[1:])))
            _urm_setting_set("urmcHubPos", None, True)

            hub.open, hub.entries = True, _urm_entries()
            found, icons, label, tray, main = drawn()
            check("while the URM+ menu is open the tray is gone (the menu opens there)", not icons and not tray, "")
            hub.open, hub.entries = False, []
            _urm_setting_set("urmcQuickAuto", False, True)
            found, icons, label, tray, main = drawn()
            check("a button hidden on the settings tab is left out", [t[0] for t in icons] == list(ICONS[1:]), "")
            _urm_setting_set("urmcQuickAuto", None, True)
            _urm_setting_set("urmcQuick", False, True)
            found, icons, label, tray, main = drawn()
            check("Quick access switched off: the tray is gone at once", not tray and not icons, "")
            _urm_setting_set("urmcQuick", True, True)

            # ---- the buttons, as clicked
            found, icons, label, tray, main = drawn()
            tray = [b[0] for b in tray]
            check("each of the three buttons takes a right click itself (never the game's menu)",
                  len(tray) == 3, repr(len(tray)))
            held = []
            for d in _qa_parts(renpy.display.dragdrop.Drag):
                if d.drag_name == "urmh_button":
                    d.visit_all(lambda x: held.append(x))
            check("the tray is drawn inside the URM+ button's own drag, so it moves with it while dragged",
                  tray and all(b in held for b in tray), repr(len(held)))
            _preferences.afm_time, _preferences.afm_enable = 0, False
            urmq_auto()
            found, icons, label, _t, _m = drawn()
            lit = [t for t in icons if t[0] == ICONS[0] and tuple(t[5]) == tuple(renpy.easy.color(URMK_COLOURS["accent-ink"])[:3])]
            check("Auto in a game whose speed is 0: on, at the engine's starting speed, lit",
                  _preferences.afm_enable and _preferences.afm_time == URMQ_AUTO_SPEED and lit,
                  repr((_preferences.afm_enable, _preferences.afm_time)))
            urmq_auto()
            check("Auto again: off", not _preferences.afm_enable, "")

            ctx = renpy.game.context()
            ctx.seen_current = lambda *a: False
            config.skipping = None
            _preferences.skip_unseen = False
            urmq_skip()
            urmq_skip(True)
            check("Skip on a line never read, skip unseen off: the engine says no, nothing starts",
                  not config.skipping, repr(config.skipping))
            _preferences.skip_unseen = True
            urmq_skip()
            slow = config.skipping
            urmq_skip(True)
            fast = config.skipping
            urmq_skip()
            check("Skip: a click skips, a right click goes on to the next choice, a click stops",
                  (slow, fast, config.skipping) == ("slow", "fast", None), repr((slow, fast, config.skipping)))
            urmq_skip(True)
            _urm_stop_skipping()
            check("the tray's skip stopped at a check is held, so the next empty click resumes it",
                  not config.skipping and _urm_skip_held() == "fast", repr(_urm_skip_held()))
            _urm_skip_forget()
            del ctx.seen_current

            backs = []
            entry = _urm_offers().entries.get("back_to_choice")
            entry_action = entry.action
            entry.action = lambda: backs.append(1)
            # what the engine has in focus: one of the tray's buttons, by
            # what it does, or nothing
            focus = renpy.display.focus
            was = focus.get_focused
            by_name = dict((urmq_pointed_name(b), b) for b in tray)

            def point(name):
                focus.get_focused = lambda: by_name.get(name)

            _, _, _, unhovered_tray, _ = drawn()
            point("skip")
            found, icons, label, _t, _m = drawn()
            check("pointing at a tray button never shifts the tray",
                  unhovered_tray and _t and spans(_t) == spans(unhovered_tray),
                  repr((unhovered_tray and spans(unhovered_tray), _t and spans(_t))))
            keys = [k for k in _qa_parts(renpy.display.behavior.Keymap) if "mouseup_2" in k.keymap]
            import pygame_sdl2 as pygame
            up2 = pygame.event.Event(pygame.MOUSEBUTTONUP, button=2, pos=(0, 0), mod=0)
            taken = False
            try:
                keys[0].event(up2, 0, 0, 0)
            except renpy.display.core.IgnoreEvent:
                taken = True
            except Exception:
                pass
            check("a middle click on Skip goes back to the last choice once, and goes no further (never hides the windows)",
                  len(keys) == 1 and taken and backs == [1], repr((len(keys), taken, backs)))
            quick_bar = _urmr_skip_focused()
            check("the quick bar's middle-click catcher leaves the tray's Skip alone: one step a click",
                  "skip" in by_name and quick_bar is False, repr(quick_bar))
            point("unseen")
            found, icons, label, _t, _m = drawn()
            keys = [k for k in _qa_parts(renpy.display.behavior.Keymap) if "mouseup_2" in k.keymap]
            try:
                keys[0].event(up2, 0, 0, 0)
            except renpy.display.core.IgnoreEvent:
                pass
            check("a middle click on another of its buttons does nothing", backs == [1], repr(backs))
            point(None)
            found, icons, label, _t, _m = drawn()
            keys = [k for k in _qa_parts(renpy.display.behavior.Keymap) if "mouseup_2" in k.keymap]
            check("with no button of the tray pointed at, a middle click reaches the game", not keys, "")
            # the Critic's case: pointing at Skip, the menu opens over the
            # tray (Alt+U), and closes with the mouse elsewhere: the engine
            # never says the button was left
            point("skip")
            drawn()
            hub.open, hub.entries = True, _urm_entries()
            drawn()
            point(None)
            hub.open, hub.entries = False, []
            found, icons, label, _t, _m = drawn()
            keys = [k for k in _qa_parts(renpy.display.behavior.Keymap) if "mouseup_2" in k.keymap]
            urmq_middle()
            check("pointed at Skip, the menu opened and closed with the mouse elsewhere: a middle click reaches "
                  "the game, nothing goes back, no tip", not keys and backs == [1] and urmq_tip() is None,
                  repr((len(keys), backs, urmq_tip())))
            entry.action = entry_action

            point("skip")
            drawn(pic("tray_tip"))
            scope = dict((k, w) for k, w in _qa_last[0].scope.items() if k.startswith("_urm"))
            try:
                pickle.dumps(scope, 2)
                kept = None
            except Exception as e:
                kept = repr(e)
            check("a save with the tray shown: the screen's scope pickles", kept is None, kept or "")
            focus.get_focused = was
            hub.section = "quick"
            page = _qa_screen("urmh_settings", pic("settings_quick"))
            words = [t[0] for t in page]
            check("the settings window's Quick access tab: seven rows, This game and All games on each",
                  words.count(u"This game") == 7 and words.count(u"All games") == 7
                  and u"Quick access buttons" in words and u"Menu" in words, repr(words))
            before = [row[0] for row in urmq_buttons()]
            check("the new shortcuts start out hidden", before == ["auto", "skip", "unseen"], repr(before))
            _urm_setting_set("urmcQuickStory", True)
            story = [row[0] for row in urmq_buttons()]
            check("Story line can be enabled on its own", story == before + ["story_line"], repr(story))
            _urm_setting_set("urmcQuickSettings", True)
            buttons = urmq_buttons()
            expanded = drawn(pic("tray_story_settings"))[3]
            check("both shortcuts fit in the same pill as the three existing buttons",
                  [row[0] for row in buttons] == before + ["story_line", "settings"]
                  and len(expanded) == 5 and 0 <= spans(expanded)[0] and spans(expanded)[2] <= W,
                  repr(spans(expanded)))
            _urm_setting_set("urmcQuickSkip", False)
            _urm_setting_set("urmcQuickUnseen", False)
            for edge in (0.0, 1.0, 0.5):
                _urm_setting_set("urmcHubPos", (edge, 0.0), True)
                _f, _i, _l, tray, main = drawn()
                left, _top, right, _bottom = spans(tray)
                centered = edge != 0.5 or near((left + right) / 2.0, main[1] + main[3] / 2.0)
                check("three buttons fit at either edge and stay centered when there is room",
                      len(tray) == 3 and 0 <= left and right <= W and centered,
                      repr((edge, left, right)))
            opened = []
            for row in buttons[-2:]:
                entry = _urm_offers().entries[row[0]]
                action = entry.action
                try:
                    entry.action = lambda name=row[0]: opened.append(name)
                    check("shortcut keeps the interaction open", row[3]() is None, row[0])
                finally:
                    entry.action = action
            check("shortcuts call the existing menu entries", opened == ["story_line", "settings"], repr(opened))
        finally:
            _urm_setting_set("urmcQuickStory", None)
            _urm_setting_set("urmcQuickSettings", None)
            _urm_setting_set("urmcQuickSkip", None)
            _urm_setting_set("urmcQuickUnseen", None)
            says["now"] = None
            _urm_setting_set("urmcQuick", None, True)
            _urm_setting_set("urmcHubPos", None, True)
'''

PROBE_FILES = {}
PROBE_ENTRY = "_qa_probe"
PROBE_PIC_ENV = "URMQA_PICTURES"
PROBE_TAG_ENV = "URMQA_TAG"
PROBE_MIN_ENGINES = 2


if __name__ == "__main__":
    sys.exit(prop_probes.main_single(__file__, sys.argv))
