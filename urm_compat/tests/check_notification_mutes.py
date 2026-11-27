"""Path notifications and Menu entry points in the props' Ren'Py engines."""
# run_tests: props
# prop_probe: standalone

import sys

import prop_probes


SCRIPT = """
label mute_probe_mixed:
    "Outside the school."
    if bravery_points >= 1 and mute_probe_day == 2:
        jump mute_probe_school
    "After."
    return

label mute_probe_mixed_again:
    "A different morning."
    if bravery_points >= 1 and mute_probe_day == 2:
        jump mute_probe_school
    "After."
    return

label mute_probe_school:
    "You go to school."
    return

label mute_probe_separate:
    "Before two checks."
    if bravery_points >= 1:
        "First."
    if mute_probe_day == 2:
        "Second."
    "After."

label mute_probe_elif:
    "Before the alternatives."
    if bravery_points >= 1:
        "First."
    elif mute_probe_day == 2:
        "Second."
    else:
        "Third."
    "After."

label mute_probe_words:
    "You arrive."
    if mute_probe_day == "bravery_points" or mute_probe_day == 2:
        "Ready."
    "After."

label mute_probe_opaque:
    "Before the opaque check."
    if bravery_points >= 1 and mute_probe_function():
        "Inside."
    "After."

label mute_probe_constant:
    "Before the constant check."
    if True:
        "Inside."
    "After."

label mute_probe_paths:
    "Before the dotted and indexed check."
    if store.mute_probe_stats.bravery >= 1 or mute_probe_stats["day"] == 2:
        "Inside."
    "After."

label mute_probe_dynamic:
    "Before the dynamic check."
    if mute_probe_stats[mute_probe_key] == 2:
        "Inside."
    "After."

label mute_probe_summary:
    "Before the two alternatives."
    if Bravery or store.Trust:
        "Inside."
    "After."
    return

label mute_probe_group_a:
    "Before a nested check."
    if Bravery and (Trust or Day):
        "Inside."
    "After."
    return

label mute_probe_group_b:
    "Before a different nested check."
    if (Bravery and Trust) or Day:
        "Inside."
    "After."
    return

label mute_probe_separate_other:
    "Before two different checks."
    if bravery_points >= 1:
        "First."
    if mute_probe_day == 3:
        "Second."
    "After."
    return

label mute_probe_summary_label:
    "Before a named destination."
    if route == "mute_probe_school":
        "Inside."
    "After."
    return

label mute_probe_summary_label_key:
    "Back in the reading room."
    if mute_probe_seen["mute_probe_school"]:
        "Inside."
    "After."
    return

label mute_probe_summary_file_key:
    "Before another check."
    if mute_probe_seen["intro.rpy"] or (Bravery and mute_probe_seen["end.rpyc"]):
        "Inside."
    "After."
    return

label mute_probe_summary_ordinary_key:
    "Before an ordinary flag."
    if mute_probe_seen["Gate_OPEN"] and Trust:
        "Inside."
    "After."
    return

label mute_probe_summary_opaque:
    "Before an opaque test."
    if unknown_hook({"value": "[Day]"}):
        "Inside."
    "After."
    return

label mute_probe_choices:
    menu:
        "Stay":
            "Stayed."
        "Go":
            "Went."

label readability_hidden_scene:
    return
"""
SCRIPT += (
    '\nlabel mute_probe_capped:\n    "Before many checks."\n'
    + '    if bravery_points >= 1:\n        "Inside."\n' * 14
    + '    "After."\n'
)

PROBE_CODE = r'''
init 1999 python:
    def _mup_draw(name, picture=None, args=(), point=False, state=None):
        screens = renpy.display.screen
        screens.updated_screens.clear()
        root = renpy.display.layout.Fixed()
        root.add(renpy.display.imagelike.Solid("#515866"))
        sd = screens.ScreenDisplayable(
            screens.get_screen_variant(name), name, "screens", scope={"_kwargs": {}, "_args": args})
        if state is not None:
            sd.scope.update(state)
        focus = renpy.display.focus
        if point:
            focus.tooltip = "Mute this notification"
            if hasattr(focus, "screen_of_focused_names"):
                focus.screen_of_focused_names = (name,)
            else:
                focus.screen_of_focused = sd
        sd.update()
        sd.visit_all(lambda d: d.per_interact())
        root.add(sd)
        rv = renpy.display.render.render_screen(root, config.screen_width, config.screen_height)
        words, buttons = [], []

        def walk(r, x, y):
            for displayable in getattr(r, "render_of", ()) or ():
                if isinstance(displayable, renpy.text.text.Text):
                    said = u"".join(t for t in displayable.text if isinstance(t, (type(u""), type(""))))
                    words.append((said, x, y, r.width, r.height))
                elif isinstance(displayable, renpy.display.behavior.Button):
                    buttons.append((displayable, x, y, r.width, r.height))
            for child in r.children:
                if isinstance(child[0], renpy.display.render.Render):
                    walk(child[0], x + child[1], y + child[2])

        walk(rv, 0, 0)
        if picture:
            import pygame_sdl2 as pygame
            surf = pygame.Surface((config.screen_width, config.screen_height), pygame.SRCALPHA)
            surf.fill((0, 0, 0, 255))
            renpy.display.swdraw.draw(surf, None, rv, 0, 0, True)
            pygame.image.save(surf, picture)
        return words, buttons

    def _mup_chip_readability(check, pic):
        old_view, old_moved = store.urm_corner_view, _urmm_st.moved
        old_size = (config.screen_width, config.screen_height)
        store.readability_points = 2
        store.readability_ready = True
        store.readability_extra = True
        store.readability_route = "one and two: {3}"
        store.readability_deliberately_long_ready_flag_to_wrap = True
        called = []
        store.readability_opaque = lambda *args: called.append(args)
        try:
            _urmm_st.moved = None
            urmk_restyle()
            renpy.style.rebuild()
            renpy.display.screen.prepare_screens()
            choices = ((0, "A short choice", "True", ()),
                       (1, "A longer choice title that wraps across more than one line on the card",
                        "readability_points >= 3 and readability_deliberately_long_ready_flag_to_wrap", ()))
            items = tuple(choice[1:] for choice in choices)
            effects = (((), "readability_points += 2"), ((), "readability_debt -= 1"),
                       ((), 'readability_route = "one and two: {3}"'), ((), "readability_extra = False"),
                       ((), "readability_unknown = someone_else"))
            arms = ((effects, ("meet",)), ((), ("meet",)))
            cards, footer = _urmm_choice_view(items, arms, (True, False), (), named=True)
            corner = _urmm_corner_choices(choices, (u"", cards, footer, []))
            store.urm_corner_view = lambda: (corner,)
            words, buttons = _mup_draw("urm_corner", pic("chip_choices"))

            def word_with(part):
                return next((row for row in words if part in row[0].replace(u"\n", "")), None)

            title, delta = word_with("A short choice"), word_with("+2")
            check("1080p keeps a 16 px chip font and 32 px short pill",
                  style.urmk_s_medium.size == 16 and any(h == 32 and getattr(button.action, "callable", None)
                  is urm_corner_open_value for button, _x, _y, _w, h in buttons))
            check("Choices draws its variable effects below the choice heading",
                  title is not None and delta is not None and word_with("readability_debt") is not None
                  and min(delta[2], word_with("readability_debt")[2]) >= title[2] + title[4])
            check("Choices emphasizes only the signed value in its effect chip",
                  delta is not None and "readability_points {font=" in delta[0] and "+2{/font}" in delta[0])
            ratio = word_with("2/3")
            and_word = next((row for row in words if row[0] == "and"), None)
            right_condition = word_with("readability_deliberately_long_ready_flag_to_wrap")
            check("Choices wraps the conjunction with its following condition",
                  and_word is not None and right_condition is not None
                  and and_word[1] < right_condition[1] and abs(and_word[2] - right_condition[2]) < 8
                  and ratio is not None and ratio[2] < right_condition[2]
                  and right_condition[1] + right_condition[3] <= config.screen_width - urmk_px(16 + 12),
                  repr((and_word, right_condition, ratio)))
            check("a wrapped variable name keeps the full search key",
                  any(getattr(button.action, "callable", None) is urm_corner_open_value
                      and button.action.args[0] == "readability_deliberately_long_ready_flag_to_wrap"
                      for button, _x, _y, _w, _h in buttons))
            check("only genuine values are emphasized, with signs, colons and escaped braces preserved",
                  "-1{/font}" in word_with("readability_debt")[0]
                  and "false{/font}" in word_with("readability_extra")[0]
                  and "one and two: {{3}{/font}" in word_with("readability_route")[0]
                  and "{font=" not in word_with("readability_unknown")[0])
            press = next((button.action for button, _x, _y, _w, _h in buttons
                          if getattr(button.action, "callable", None) is urm_corner_open_value
                          and button.action.args[0] == "readability_points"), None)
            old_value_view, opened = store._urm_value_view, []
            store._urm_value_view = lambda name, beside: opened.append((name, beside)) or True
            try:
                check("the emphasized effect opens the named variable beside the card without ending the interaction",
                      press is not None and press() is None and opened == [("readability_points", urm_corner_beside(("choices",)))])
            finally:
                store._urm_value_view = old_value_view

            corner[3][0][5].append((0, u"\u203a Only if", urm_need_chips("readability_ready", True), None))
            folded = (urm_corner_key(("choices",)), "choices", 0)
            words, buttons = _mup_draw("urm_corner", pic("chip_choices_hover"),
                                       state={"_urmcAt": ("choices", 0), "_urmcOpen": folded})
            prefix, nested = word_with(u"\u203a Only if"), word_with("readability_ready:")
            check("the hovered choice keeps Take and its unfolded variables start below the way heading",
                  word_with("Take") is not None and prefix is not None and nested is not None
                  and nested[2] >= prefix[2] + prefix[4])

            both = 'readability_route == "one and two: {3}" or readability_deliberately_long_ready_flag_to_wrap'
            steps = (("gate", both, None), ("else", None, None))
            route_effect = (u"readability_debt -1", "loss", "readability_debt", (17, 19))
            path_cards = ((u"", "gain", u"1", None, False, "Runs now", ()),
                          (u"", "muted", u"", None, True, "Skipped", ((0, None, (route_effect,), None),)))
            path = _urmm_corner_ways(steps, path_cards, None)
            store.urm_corner_view = lambda: (path,)
            words, _buttons = _mup_draw("urm_corner", pic("chip_paths"))
            title, route = word_with("Active Path"), word_with("one and two:")
            other, effect = word_with("Otherwise"), word_with("readability_debt")
            or_word = next((row for row in words if row[0] == "or"), None)
            alternative = word_with("readability_deliberately_long_ready_flag_to_wrap")
            check("Active Path keeps a quoted conjunction intact and puts variables below a real heading",
                  route is not None and "one and two: {{3}{/font}" in route[0]
                  and or_word is not None and not any(w[0] == "and" for w in words)
                  and route[2] <= title[2] + title[4] + urmk_px(40)
                  and effect[2] >= other[2] + other[4], repr((route, title, effect, other)))
            check("Active Path wraps the disjunction with its full condition inside the edge",
                  alternative is not None and or_word is not None and route is not None
                  and or_word[1] < alternative[1] and abs(or_word[2] - alternative[2]) < 8
                  and route[2] < alternative[2]
                  and alternative[1] + alternative[3] <= config.screen_width - urmk_px(16 + 12),
                  repr((or_word, alternative, route)))

            condition = "readability_ready and (readability_points >= 3 or readability_extra)"
            mixed = _urmm_corner_choices(((0, "Grouped choice", condition, ()),), (u"", [], [], []))
            chips = mixed[3][0][5][0][2]
            summary = chips[0][0].replace(u"\u00a0", " ") if len(chips) == 1 else ""
            check("a mixed condition keeps its full grouping in one fallback",
                  "and (" in summary and " or " in summary
                  and summary.endswith("readability_extra is true)"), repr(chips))
            opaque = 'readability_ready and (readability_opaque("private-probe.rpy") or readability_extra)'
            unknown_cards = ((u"", "muted", u"1", None, False, "Can't tell yet", ()),)
            opaque_path = _urmm_corner_ways((("gate", opaque, None),), unknown_cards, None)
            fallback = opaque_path[3][0][2]
            check("opaque checks remain grouped and neutral without calling or showing the game hook",
                  opaque_path[3][0][4] == (_URMM_UNSURE, "ink-muted")
                  and not opaque_path[3][0][5] and "a game check or" in fallback
                  and "private-probe" not in fallback and not called, repr(fallback))
            long = 'readability_ready and (readability_route == "%s" or readability_extra)' % ("long word " * 24)
            long_path = _urmm_corner_ways((("gate", long, None),), path_cards[:1], None)
            store.urm_corner_view = lambda: (path, mixed, opaque_path, long_path)
            config.screen_width, config.screen_height = 1024, 576
            urmk_restyle()
            renpy.style.rebuild()
            renpy.display.screen.prepare_screens()
            words, _buttons = _mup_draw("urm_corner", pic("chip_narrow"))
            check("the narrow render bounds long mixed and opaque checks without losing the ordinary chips",
                  word_with("Depends on a game check") is not None and word_with("one and two:") is not None
                  and all(0 <= x <= 1024 - w and 0 <= y <= 576 - h for _said, x, y, w, h in words))
        finally:
            store.urm_corner_view, _urmm_st.moved = old_view, old_moved
            config.screen_width, config.screen_height = old_size
            urmk_restyle()
            renpy.style.rebuild()
            renpy.display.screen.prepare_screens()
            del store.readability_points, store.readability_ready, store.readability_extra
            del store.readability_route, store.readability_deliberately_long_ready_flag_to_wrap, store.readability_opaque

    def _mup_condition_meaning(check, pic):
        saved_random = getattr(store, "random", None)
        had_random = hasattr(store, "random")
        old_view = store.urm_corner_view
        used_random = []
        class ProbeRandom(object):
            def randint(self, *args):
                used_random.append(args)
                return 1
        store.random = ProbeRandom()
        store.readability_route = "readability_hidden_scene"
        store.readability_ready = True
        store.readability_extra = False
        store.readability_points = -4
        store.readability_total = 14
        store.readability_power = 512
        try:
            def path_card(cond):
                return _urmm_corner_ways((("gate", cond, None),),
                                         ((u"", "muted", u"1", None, False, "Can't tell yet", ()),), None)

            def path_test(cond):
                return path_card(cond)[3][0][2]

            def choices_test(cond):
                return _urmm_corner_conditions(cond, _urm_truth(cond))

            cond = 'readability_route == "alpha or beta" or readability_ready'
            scene = choices_test(cond)
            store.readability_route = "intro_readability.rPyC"
            filename = choices_test(cond)
            check("current scene and script names are hidden while the other condition remains a named chip",
                  len(scene) == len(filename) == 3 and scene[0] == ("readability_route: a scene", "loss", "readability_route")
                  and filename[0] == ("readability_route: a script file", "loss", "readability_route")
                  and scene[2][:3] == ("readability_ready: true", "gain", "readability_ready"), repr((scene, filename)))

            literal = _urmw_corner_fallback('readability_route == u"readability_hidden_scene" or readability_route == r"intro_readability.rPyC"')
            assignments = _urmm_chips((((), 'readability_route = u"readability_hidden_scene"'),
                                        ((), 'readability_file = r"intro_readability.rPyC"')), named=True)
            check("quoted and prefixed source locations are hidden in comparisons and effects",
                  "a scene" in literal and "a script file" in literal and "intro_readability" not in literal
                  and [chip[0] for chip in assignments] == ["readability_route", "readability_file"],
                  repr((literal, assignments)))

            standalone = path_test("random.randint(1, 3) == 1")
            combined = path_test("readability_ready and (random.randint(1, 3) == 1 or readability_extra)")
            check("standalone and embedded chance keep their meaning without rolling the dice",
                  standalone == "By chance" and "by chance or" in combined
                  and combined.startswith("readability_ready is true and") and not used_random,
                  repr((standalone, combined, used_random)))
            quote = _urmw_corner_fallback('readability_route == "random.randint(1, 3)"')
            uncertain = path_test("random.randint(1, 3) + readability_opaque() > 1")
            check("words in a quote and a call with unsupported inputs are not treated as pure chance",
                  "random.randint(1, 3)" in quote and uncertain == "A game check" and not used_random,
                  repr((quote, uncertain)))

            grouped = path_test("readability_ready and (readability_total >= 3 or readability_extra)")
            check("a grouped check keeps the first variable's raw spelling",
                  grouped.startswith("readability_ready is true"), repr(grouped))
            cleared = _urmm_chips((((), "readability_route = None"),), named=True)[0]
            check("cleared is an emphasized assignment value",
                  len(cleared) == 4 and cleared[0][cleared[3][0]:cleared[3][1]] == "cleared", repr(cleared))
            signed = _urmm_chips((((), "readability_total = +3"),), named=True)[0]
            check("an explicitly positive assignment keeps its value span",
                  len(signed) == 4 and signed[0][signed[3][0]:signed[3][1]] == "+3", repr(signed))

            conditional = "readability_total == 100 if readability_extra else readability_ready"
            guarded = "readability_extra and " + conditional
            failing = "readability_ready or readability_total == 100 if readability_extra else readability_extra"
            for text, holds, tone in ((conditional, True, "gain"), (guarded, True, "gain"), (failing, False, "loss")):
                chips = choices_test(text)
                check("a conditional expression stays whole and uses the engine's result",
                      _urm_truth(text) is holds and chips == [(u"A game check", tone)], repr(chips))
            check("Active Path describes a conditional expression as a whole",
                  path_test(guarded) == u"A game check", repr(path_test(guarded)))

            cases = (("readability_points == -2 ** 2", True),
                     ("readability_points == (-2) ** 2", False),
                     ("readability_power == 2 ** 3 ** 2", True),
                     ("readability_total == 2 + 3 * 4", True),
                     ("readability_total == (2 + 3) * 4", False),
                     ("readability_points < 0 < readability_total", True),
                     ("not readability_total > 10 and readability_ready", False),
                     ("readability_extra or readability_ready and not readability_extra", True),
                     ("(readability_extra or readability_ready) and readability_extra", False))
            for cond, holds in cases:
                chips = choices_test(cond)
                tone = "gain" if holds else "loss"
                check("native precedence and compact tone for " + cond,
                      _urm_truth(cond) is holds and chips[0][1] == tone, repr(chips))

            rows = ((("num", u"1"), False, "Choice with a script value", False, None,
                     ((0, None, scene, None),), False, True),
                    (("num", u"2"), False, "Choice that clears a value", False, None,
                     ((0, None, (cleared,), None),), False, True),
                    (("num", u"3"), False, "Choice with an opaque check", False, None,
                     ((0, u"Only if", choices_test(guarded), None), (0, None, (signed,), None)), False, True))
            result = ("choices", "Choices", False, rows, ())
            store.urm_corner_view = lambda: (result, path_card("random.randint(1, 3) == 1"),
                path_card("readability_ready and (random.randint(1, 3) == 1 or readability_extra)"))
            words, _buttons = _mup_draw("urm_corner", pic("chip_meaning"))
            captions = tuple(text for text, _x, _y, _w, _h in words)
            check("the rendered notifications keep safe values and chance without exposing IDs",
                  any("cleared{/font}" in text for text in captions) and "By chance" in captions
                  and any("+3{/font}" in text for text in captions)
                  and not any("readability_hidden_scene" in text or "intro_readability" in text for text in captions),
                  repr(captions))
            store.urm_corner_view = lambda: (path_card(guarded),)
            words, _buttons = _mup_draw("urm_corner", pic("chip_conditional"))
            captions = tuple(text for text, _x, _y, _w, _h in words)
            check("Active Path renders no misleading branch from an opaque conditional",
                  "A game check" in captions and not any("readability_" in text for text in captions), repr(captions))
        finally:
            store.urm_corner_view = old_view
            if had_random:
                store.random = saved_random
            else:
                del store.random
            del store.readability_route, store.readability_ready, store.readability_extra
            del store.readability_points, store.readability_total, store.readability_power

    def _mup_probe(lines, check, pic):
        import pickle
        old_in_game, old_here = store._urm_in_game, store._urmsg_here
        saved, lists = persistent._urm_settings, persistent._urm_lists
        focus = renpy.display.focus
        focus_names = getattr(focus, "screen_of_focused_names", None)
        previous_focus = (focus.tooltip, focus.screen_of_focused)
        old_size = (config.screen_width, config.screen_height)
        names = ("Bravery", "Trust", "Day")
        old_values = {name: getattr(store, name) for name in names if hasattr(store, name)}
        old_skip = config.skipping
        old_closed = getattr(_urmm_st, "closed", None)
        old_moved = getattr(_urmm_st, "moved", None)
        old_tab = _urmcp_state().tab
        old_alert_tab = urmcp_alert_tab()
        ctx = renpy.game.context()
        old_init = ctx.init_phase
        try:
            ctx.init_phase = False
            sl = ctx.scene_lists
            for layer in config.layers:
                if layer not in sl.layers:
                    sl.layers[layer] = []
                    sl.at_list[layer] = {}
                    sl.layer_at_list[layer] = (None, [])
            store._urm_in_game = lambda: True
            store.bravery_points, store.mute_probe_day = 1, 2
            store.mute_probe_stats = {"day": 2}
            _urmm_st.closed = python_dict()
            _urmm_st.moved = None
            persistent._urm_lists = None
            _urm_setting_set("showPathsNotification", True)
            _urm_setting_set("stopSkippingOnPathDetection", True)
            _urm_setting_set("urmcPathMutes", None)

            def at(name):
                label = renpy.game.script.lookup("mute_probe_" + name)
                node = label.block[0]
                if isinstance(node, renpy.ast.Translate):
                    node = node.block[0]
                store._urmsg_here = lambda: node
                _urmm_st.path_notice = None
                _urmm_st.check_in_view = None
                return node

            def path_rows():
                return [card[3] for card in urm_corner_view() if card[0] == "paths"]

            def stop():
                config.skipping = "fast"
                _urmm_stop_at_check()
                return config.skipping is None

            at("mixed")
            first = _urm_gate_ahead()
            check("the prop's real if-statement is read from the dialogue before it",
                  first is not None and _urmm_path_notice(first, (), ()),
                  repr((type(_urmsg_here()).__name__, first)))
            baseline_rows = path_rows()
            _urm_ignore("bravery_points", "path")
            check("one ignored read leaves every row of the mixed check present",
                  bool(baseline_rows) and path_rows() == baseline_rows and stop(),
                  repr((len(baseline_rows), _urm_in_game())))
            _urm_ignore("mute_probe_day", "path")
            at("mixed")
            check("all ignored reads hide the whole notification and do not stop a skip",
                  not path_rows() and not stop() and _urm_gate_ahead() is not None and urm_path_view() is not None)
            _urm_unignore("mute_probe_day", "path")
            at("separate")
            check("a later separate check can keep all earlier rows on the card",
                  path_rows() and len(path_rows()[0]) >= 2)
            at("elif")
            check("an unignored elif keeps the whole notification visible",
                  path_rows() and len(path_rows()[0]) == 3)
            _urm_ignore("mute_probe_day", "path")
            at("separate")
            check("ignoring both separate gates hides the entire card", not path_rows())
            at("elif")
            check("ignoring the if and elif hides the entire card, including otherwise", not path_rows())
            _urm_unignore("mute_probe_day", "path")
            at("words")
            check("a quoted ignored name does not count as a read", path_rows())
            at("opaque")
            check("a call makes the check opaque even though its known read is ignored", path_rows())
            at("constant")
            check("a check without a store read remains visible", path_rows())
            at("paths")
            _urm_ignore("mute_probe_stats.bravery", "path")
            _urm_ignore('mute_probe_stats["day"]', "path")
            check("literal subscripts and dotted store names are matched in Search's spelling", not path_rows())
            at("dynamic")
            _urm_ignore("mute_probe_stats", "path")
            _urm_ignore("mute_probe_key", "path")
            check("a dynamic subscript is opaque even when its container and key are ignored", path_rows())
            at("capped")
            check("a capped chain is still announced", path_rows() and urm_corner_mute_key() is None)
            persistent._urm_lists = None

            def summary(name, values):
                at(name)
                store.Bravery, store.Trust, store.Day = values
                key = _urmm_path_key(_urm_read_chain(_urm_gate_ahead()))
                urm_corner_mute_ask(key)
                recorded, title, cue = renpy.get_screen("urm_corner_mute", layer=_urmi_layer).scope["_args"]
                urm_corner_mute_close()
                return recorded, title, cue

            with_brave = summary("summary", (True, False, False))
            with_trust = summary("summary", (False, True, False))
            with_neither = summary("summary", (False, False, False))
            check("mute title keeps the full test and exact name case at every live value",
                  with_brave == with_trust == with_neither and
                  with_brave[1] == "Bravery is true or Trust is true",
                  repr((with_brave[1], with_trust[1], with_neither[1])))
            group_a = summary("group_a", (True, True, True))[1]
            group_b = summary("group_b", (True, True, True))[1]
            check("mute titles keep the grouping of mixed boolean checks",
                  "(Trust is true or Day is true)" in group_a and
                  "(Bravery is true and Trust is true)" in group_b, repr((group_a, group_b)))
            separate = summary("separate", (False, False, False))
            separate_other = summary("separate_other", (False, False, False))
            check("different later gates distinguish notifications with the same first gate",
                  "mute_probe_day is 2" in separate[1] and "mute_probe_day is 3" in separate_other[1],
                  repr((separate[1], separate_other[1])))
            later_arm = summary("elif", (False, False, False))[1]
            check("the condition of every elif appears in its saved wording",
                  "bravery_points is at least 1" in later_arm and "Otherwise if mute_probe_day is 2" in later_arm)
            neutral = "Check about a script location"
            direct = summary("summary_label", (False, False, False))[1]
            check("a direct quoted script label has a neutral caption", direct == neutral, repr(direct))
            check("a direct quoted filename has a neutral caption",
                  _urmm_mute_condition('route == "intro.rpyc"') == neutral)
            redacted = summary("summary_label_key", (False, False, False))
            check("a script label written as a dictionary key is also kept out of the caption",
                  redacted[1] == neutral, repr(redacted[1]))
            compound = summary("summary_file_key", (True, False, False))[1]
            check("script filenames in compound dictionary checks have a neutral caption",
                  compound == neutral, repr(compound))
            ordinary = summary("summary_ordinary_key", (False, True, False))[1]
            check("an ordinary dictionary key retains its full Search spelling and compound test",
                  ordinary == 'mute_probe_seen["Gate_OPEN"] is true and Trust is true', repr(ordinary))
            at("summary_label_key")
            check("the exact key retains the script check and the saved cue retains the spoken line",
                  redacted[0][0][2] == ('mute_probe_seen["mute_probe_school"]',)
                  and "Back in the reading room" in redacted[2])
            urm_corner_mute_close(*redacted)
            check("the captioned mute still hides its exact check", not path_rows())
            urmcp_mute_remove(redacted[0])
            check("Unmute still restores the exact check", path_rows() and not _urm_path_mutes())
            check("a malformed condition retains its literal fallback",
                  _urmm_mute_condition("broken[") == "broken[")
            opaque = summary("summary_opaque", (False, False, False))[1]
            check("an opaque condition keeps its literal meaning with UI-safe braces",
                  opaque == 'unknown_hook({{"value": "[Day]"})', repr(opaque))

            at("mixed")
            config.skipping = None

            def action(buttons, fn, argv=None):
                for button, x, y, w, h in buttons:
                    current = button.action
                    if getattr(current, "callable", None) is fn:
                        if argv is None or current.args == argv:
                            return current, (x, y, w, h)
                return None, None

            words, buttons = _mup_draw("urm_corner", pic("path"))
            ask, bell = action(buttons, urm_corner_mute_ask)
            _story, story = action(buttons, urm_corner_story)
            _close, close = action(buttons, urm_note_close, ("paths",))
            check("the corner header places the bell just before Story line and close",
                  bool(bell and story and close and bell[0] < story[0] < close[0]))
            if ask is None:
                return
            original_key = ask.args[0]
            def tooltip_at(edge, evidence):
                if edge is None:
                    _urmm_st.moved = None
                else:
                    _urmm_st.moved = (urm_corner_key(("paths",)), edge, 0.55,
                                     urmk_px(_URMM_CORNER[0]), urmk_px(160), 1)
                words, hit = _mup_draw("urm_corner", pic(evidence), point=True)
                _hover, hitbox = action(hit, urm_corner_mute_ask)
                tip = next(((x, y, w, h) for word, x, y, w, h in words if word == "Mute this notification"), None)
                if not tip or not hitbox:
                    return False, repr((tip, hitbox))
                x, y, w, h = tip
                bx, by, bw, bh = hitbox
                overlaps_words = any(other and other != "Mute this notification"
                                     and x < ox + ow and ox < x + w and y < oy + oh and oy < y + h
                                     for other, ox, oy, ow, oh in words)
                return (0 <= x <= config.screen_width - w and 0 <= y <= config.screen_height - h
                        and x <= bx + bw and x + w >= bx and by + bh <= y <= by + bh + urmk_px(24)
                        and not overlaps_words), repr((tip, hitbox, overlaps_words))

            for edge, picture in ((None, "path_hover"), (0.0, "path_left_hover")):
                okay, detail = tooltip_at(edge, picture)
                check("the tooltip is below the bell without covering words at " + picture, okay, detail)
            config.screen_width, config.screen_height = 1024, 768
            for edge, picture in ((1.0, "path_narrow_hover"), (0.0, "path_narrow_left_hover")):
                okay, detail = tooltip_at(edge, picture)
                check("the tooltip is below the bell and in view at " + picture, okay, detail)
            _urmm_st.moved = None
            config.screen_width, config.screen_height = old_size
            focus.tooltip, focus.screen_of_focused = previous_focus
            if focus_names is not None:
                focus.screen_of_focused_names = focus_names
            ask()
            dialog = renpy.get_screen("urm_corner_mute", layer=_urmi_layer)
            args = dialog.scope["_args"]
            words, buttons = _mup_draw("urm_corner_mute", pic("confirm"), args)
            no, _box = action(buttons, urm_corner_mute_close, ())
            yes, _box = action(buttons, urm_corner_mute_close, args)
            check("the real confirmation shows the question and has separate No and Yes actions",
                  bool(no and yes and any(w == "Mute this notification?" for w, x, y, width, height in words)))
            no()
            check("No leaves the original notification visible", path_rows() and not _urm_path_mutes())
            ask()
            dialog = renpy.get_screen("urm_corner_mute", layer=_urmi_layer)
            dialog.update()
            escape = []
            dialog.visit_all(lambda d: escape.append(d.keymap["K_ESCAPE"])
                             if isinstance(d, renpy.display.behavior.Keymap) and "K_ESCAPE" in d.keymap else None)
            check("Escape is bound to dismiss the confirmation", len(escape) == 1)
            escape[0]()
            check("Escape leaves the original notification visible", path_rows() and not _urm_path_mutes())
            ask()
            at("mixed_again")
            yes()
            check("Yes keeps the captured check mute even if the scene changed",
                  len(_urm_path_mutes()) == 1 and _urm_path_mutes()[0][0] == original_key)
            check("an identical condition at a different source location remains visible",
                  path_rows() and urm_corner_mute_key() != original_key)
            at("mixed")
            persistent._urm_settings = pickle.loads(pickle.dumps(persistent._urm_settings))
            _URMMemory.path_mute_keys = None
            check("persistent mute survives reconstructing settings and never stops an invisible skip",
                  not path_rows() and not stop() and _urm_gate_ahead() is not None and urm_path_view() is not None)
            check("Story line can still read the muted check",
                  any(s.node is _urm_gate_ahead() for s in urmnm_model(_urmsg_here(), 2)))
            at("choices")
            _words, buttons = _mup_draw("urm_corner")
            check("Choices has no mute action", action(buttons, urm_corner_mute_ask)[0] is None)
            _mup_chip_readability(check, pic)
            _mup_condition_meaning(check, pic)
            config.skipping = None

            _urm_setting_set("urmcAlerts", ("bravery_points",))
            entry_names = [e.name for e in _urm_entries()]
            settings_index = entry_names.index("settings")
            check("Search remains first, and the distinct Menu row is directly above Settings",
                  entry_names[:1] == ["search"]
                  and entry_names[settings_index - 1:settings_index + 1] == ["menu", "settings"])
            urmh_open()
            _mup_draw("urmh_button_in_game", pic("hub_menu"))
            urmh_close()
            _urm_open("search")
            check("Search still opens the quick sheet",
                  renpy.get_screen("urmcp_sheet") is not None and not _urmcp_state().full)
            _urm_open("menu")
            check("Menu opens the existing full page directly",
                  renpy.get_screen("urmcp_page") is not None and _urmcp_state().full)
            urmcp_tab("alerts")
            urmcp_select_alert_tab("alerts")
            words, buttons = _mup_draw("urmcp_page", pic("menu_alerts"))
            stop_alert, _box = action(buttons, urmcp_alert_stop)
            check("Alerts & Mutes opens with the existing Stop action for alerts",
                  stop_alert is not None and any(w == "Alerts & Mutes" for w, x, y, width, height in words))
            stop_alert()
            check("Stop clears the alert and leaves the mute", not urmcp_alert_rows() and len(urmcp_mute_rows()) == 1)
            urmcp_select_alert_tab("mutes")
            words, buttons = _mup_draw("urmcp_page", pic("menu_mutes"))
            unmute, _box = action(buttons, urmcp_mute_remove, (original_key,))
            check("the mute row uses a human-readable condition and spoken scene cue",
                  unmute is not None and any("Outside the school" in w for w, x, y, width, height in words)
                  and any("bravery" in w.lower() for w, x, y, width, height in words)
                  and not any("mute_probe.rpy" in w for w, x, y, width, height in words))
            unmute()
            at("mixed")
            check("Unmute restores that exact notification", not _urm_path_mutes() and path_rows())
            words, _buttons = _mup_draw("urmcp_page")
            check("the active empty Mutes tab explains its empty state",
                  any(w == "No muted notifications for this game." for w, x, y, width, height in words))
            urm_note_close("paths")
            check("close is temporary and never creates a mute", not path_rows() and not _urm_path_mutes())
            at("mixed_again")
            check("the next location shows the notification again", path_rows())
            urmcp_close()
            check("Menu Quick access starts hidden", "menu" not in [x[0] for x in urmq_buttons()])
            urmh_settings("quick")
            settings, _buttons = _mup_draw("urmh_settings", pic("quick_settings"))
            check("Quick access settings draws Menu with the other button settings",
                  any(w == "Menu" for w, x, y, width, height in settings) and
                  any(w == "Opens the full page." for w, x, y, width, height in settings))
            urmh_settings_close()
            _urm_setting_set("urmcQuick", True)
            _urm_setting_set("urmcQuickMenu", True)
            _words, buttons = _mup_draw("urmh_button_in_game", pic("quick_menu"))
            quick_menu, _box = action(buttons, urmq_open, ("menu",))
            check("enabling Menu adds the same action to the ordinary Quick access pill", quick_menu is not None)
            quick_menu()
            check("the Quick access Menu opens the same full page", renpy.get_screen("urmcp_page") is not None)
            _urm_setting_set("urmcQuickMenu", False)
            check("disabling Menu removes its Quick access button only", "menu" not in [x[0] for x in urmq_buttons()])
        finally:
            store._urm_in_game, store._urmsg_here = old_in_game, old_here
            persistent._urm_settings, persistent._urm_lists = saved, lists
            _urmm_st.closed, _urmm_st.moved = old_closed, old_moved
            _urmm_st.path_notice = None
            _urmm_st.check_in_view = None
            config.skipping = old_skip
            config.screen_width, config.screen_height = old_size
            focus.tooltip, focus.screen_of_focused = previous_focus
            if focus_names is not None:
                focus.screen_of_focused_names = focus_names
            for screen in ("urmcp_sheet", "urmcp_page"):
                renpy.hide_screen(screen, layer="screens")
            renpy.hide_screen("urm_corner_mute", layer=_urmi_layer)
            _urmcp_state().tab = old_tab
            urmcp_select_alert_tab(old_alert_tab)
            _urm_work_cancel("search open")
            _urm_work_cancel("search")
            ctx.init_phase = old_init
            for name in names:
                if name in old_values:
                    setattr(store, name, old_values[name])
                else:
                    delattr(store, name)
            del store.bravery_points, store.mute_probe_day, store.mute_probe_stats
'''

PROBE_FILES = {"mute_probe.rpy": SCRIPT.encode("utf-8")}
PROBE_ENTRY = "_mup_probe"
PROBE_PIC_ENV = "URMMUP_PICTURES"
PROBE_TAG_ENV = "URMMUP_TAG"
PROBE_MIN_ENGINES = 2

if __name__ == "__main__":
    sys.exit(prop_probes.main_single(__file__, sys.argv))
