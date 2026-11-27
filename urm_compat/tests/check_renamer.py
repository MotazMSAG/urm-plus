"""Character names through Settings, the engine's speech and choice screens."""
# run_tests: props
# prop_probe: standalone

import sys

import prop_probes

PROBE_CODE = u'''
default qrn_name = "Mara"
default qrn_unrelated = "Mara"
define qrn_dynamic = Character("qrn_name", dynamic=True)
define qrn_literal = Character("Mara")
define qrn_eli = Character("Eli")
define qrn_live = Character("Mara", screen="qrn_say")
define qrn_live_dynamic = Character("qrn_name", dynamic=True, screen="qrn_say")
define qrn_replaced = Character("Mara")
define qrn_nvl = Character("Mara", kind=nvl, who_prefix="{b}", who_suffix="{/b}")

label qrn_jump_target:
    return

screen qrn_choices(items):
    $ _qrn_seen[:] = items
    vbox:
        for item index item.action in items:
            textbutton item.caption action item.action

screen qrn_custom_choice():
    vbox:
        textbutton "Ask Mara" action Return(7)
        textbutton "Follow Mara" action _qrn_jump
        textbutton "Toggle Mara" action SetVariable("qrn_unrelated", "Toggled")

screen qrn_say(who, what):
    vbox:
        text who id "who"
        text what id "what"

screen nvl(dialogue, items=None):
    vbox:
        for entry index entry.what_id in dialogue:
            vbox:
                text entry.who id entry.who_id
                text entry.what id entry.what_id

init 1999 python:
    _qrn_seen = []
    _qrn_jump = Jump("qrn_jump_target")

    def _qrn_probe(lines, check, pic):
        ds = renpy.display.screen
        core = renpy.display.layout
        previous = _urm_setting_at(_URMRN_SETTING, False)
        # Lint invokes the probe with no scene running.
        ctx = renpy.game.context()
        init = ctx.init_phase
        ctx.init_phase = False
        retain = renpy.retain_after_load
        retained = []
        renpy.retain_after_load = lambda: retained.append(True)
        store.qrn_name, store.qrn_unrelated = "Mara", "Mara"

        def choose(old, new):
            urmrn_edit(old, new)
            urmrn_put()

        def update(screen):
            if hasattr(ds, "updated_screens"):
                ds.updated_screens.clear()
            screen.update()
            words = []
            def see(d):
                if isinstance(d, renpy.text.text.Text):
                    words.extend(d.text)
            screen.visit_all(see)
            return words

        try:
            renpy.show_screen("qrn_say", who="Mara", what="Ask Mara", _transient=True,
                              _widget_properties={"what": {}}, _layer=config.choice_layer)
            active = renpy.get_screen("qrn_say", layer=config.choice_layer)
            update(active)
            names = _urmrn_catalog()
            check("the character picker sees literal and variable-backed names",
                  ("char", "store", "qrn_literal") in names.get("Mara", ()) and
                  ("var", "store", "qrn_name") in names.get("Mara", ()), repr(names.get("Mara")))
            choose("Eli", "Theo")
            choose("Mara", "Nora")
            check("one rename reaches actual Characters and verified name variables",
                  qrn_literal.name == qrn_name == "Nora" and qrn_unrelated == "Mara")
            check("whole names change once, preserving tags, interpolation and longer names",
                  _urmrn_match("Mara and Marabelle; {a=Mara}Mara{/a} [Mara]{w}") ==
                  "Nora and Marabelle; {a=Mara}Nora{/a} [Mara]{w}")
            choose("Mara", "Theo")
            check("a second character cannot claim the same visible name", qrn_literal.name == "Nora")
            update(active)
            live = (active.widgets["who"].text, active.widgets["what"].text)
            check("the open line updates its speaker and dialogue on settings changes",
                  live == (["Nora"], ["Ask Nora"]), repr(live))
            renpy.hide_screen("qrn_say", layer=config.choice_layer)

            # Go through the engine's normal menu path. The real MenuEntry
            # keeps its action, including the original choice identity.
            action = renpy.ui.ChoiceReturn("Ask Mara", 7, "qrn-choice")
            renpy.display_menu([("Ask Mara", action)], interact=False, screen="qrn_choices")
            shown = renpy.get_screen("qrn_choices", layer=config.choice_layer)
            caption = update(shown)
            item = _qrn_seen[0]
            check("the choice screen receives the renamed caption and original action",
                  "Ask Nora" in caption and item.caption == "Ask Mara" and item.action is action
                  and item.action.label == "Ask Mara" and item.action.value == 7,
                  repr((caption, item, item.action.label)))
            check("the choice card uses the same visible name as the game",
                  _urmm_choice_title("Ask Mara") == "Ask Nora")
            choose("Mara", "Mara Vale")
            check("changing a rename refreshes the choice already on screen",
                  "Ask Mara Vale" in update(shown) and _qrn_seen[0].action is action)
            check("names that contain the original name are changed only once",
                  _urmrn_match("Mara and Mara Vale") == "Mara Vale and Mara Vale")
            choose("Mara", "Nora")
            renpy.hide_screen("qrn_choices", layer=config.choice_layer)
            store.Mara = ["Mara"]
            renpy.display_menu([("Ask [Mara[0]]", action)], interact=False, screen="qrn_choices")
            shown = renpy.get_screen("qrn_choices", layer=config.choice_layer)
            words = update(shown)
            check("nested interpolation is resolved by the engine before names are matched",
                  words == ["Ask Nora"] and _qrn_seen[0].caption == "Ask [Mara[0]]", repr(words))
            renpy.hide_screen("qrn_choices", layer=config.choice_layer)
            renpy.display_menu([("Ask [[Mara]", action)], interact=False, screen="qrn_choices")
            shown = renpy.get_screen("qrn_choices", layer=config.choice_layer)
            words = update(shown)
            check("escaped square brackets become visible punctuation before matching",
                  words == ["Ask [Nora]"] and _qrn_seen[0].caption == "Ask [[Mara]", repr(words))
            renpy.hide_screen("qrn_choices", layer=config.choice_layer)
            renpy.show_screen("qrn_custom_choice", _transient=True, _layer=config.choice_layer)
            custom = renpy.get_screen("qrn_custom_choice", layer=config.choice_layer)
            words = update(custom)
            jumps = []
            custom.visit_all(lambda d: jumps.append(getattr(d, "action", None)))
            check("game-owned Return and Jump choices change labels and keep their actions",
                  "Ask Nora" in words and "Follow Nora" in words
                  and any(action is _qrn_jump for action in jumps), repr(words))
            check("an unrelated control in the same screen keeps its text", "Toggle Mara" in words, repr(words))
            renpy.hide_screen("qrn_custom_choice", layer=config.choice_layer)

            say_layer = getattr(config, "say_layer", "screens")
            for speaker, kind, line in ((qrn_live, "literal", "Ask %s about Nora."),
                                        (qrn_live_dynamic, "variable-backed", "Ask %s{w} about Nora.")):
                speaker(line % "Mara", interact=False)
                active = renpy.get_screen("qrn_say", layer=say_layer)
                seen = []
                expected = []
                for name in ("Nora", "Iris Quinn", "Mara"):
                    if name == "Iris Quinn":
                        choose("Mara", name)
                        update(active)
                    elif name == "Mara":
                        urmrn_restore("Mara")
                        update(active)
                    shown = active.widgets["what"]
                    seen.append((active.widgets["who"].text[0], shown.text[0]))
                    expected.append((name, renpy.character.DialogueTextTags(line % name).text))
                check("edit and restore a real open line with a %s speaker and overlapping names" % kind,
                      seen == expected, repr((seen, expected)))
                renpy.hide_screen("qrn_say", layer=say_layer)
                choose("Mara", "Nora")

            if _urmrn_prefix is not None:
                spoke = qrn_literal.prefix_suffix("what", "", "Mara{w} and Eli.", "")
                check("the speech hook runs before the engine calculates pauses",
                      spoke == "Nora{w} and Theo.", repr(spoke))
            else:
                qrn_live("Mara{w} and Eli.", interact=False)
                active = renpy.get_screen("qrn_say", layer=say_layer)
                spoke = (active.widgets["who"].text[0], active.widgets["what"].text[0])
                expected = renpy.character.DialogueTextTags("Nora{w} and Theo.")
                check("the legacy say path carries the new speaker and engine pause positions",
                      spoke == ("Nora", expected.text)
                      and active.widgets["what"].end == expected.pause_end[-1], repr(spoke))
                renpy.hide_screen("qrn_say", layer=say_layer)
                history_state = (config.history_length, getattr(store, "_history", False),
                                 getattr(store, "_history_list", None), store.nvl_list,
                                 getattr(store, "_nvl_language", None), ctx.rollback)
                try:
                    config.history_length, store._history, store._history_list = 10, True, []
                    store.nvl_list, ctx.rollback = [], False
                    store._nvl_language = _preferences.language
                    store.qrn_history_names = ["Mara"]
                    line = "Ask [qrn_history_names[0]] and [[Mara]."
                    for name in ("Nora", "Mara"):
                        if name == "Mara":
                            urmrn_restore("Mara")
                        expected = "Ask %s and [%s]." % (name, name)
                        qrn_live(line, interact=False)
                        adv = store._history_list[-1]
                        check("legacy ADV history uses the resolved %s line" % name,
                              (adv.who, adv.what) == (name, expected), repr((adv.who, adv.what)))
                        qrn_nvl(line, interact=False)
                        nvl_entry = store.nvl_list[-1][:2]
                        nvl_history = store._history_list[-1]
                        nvl_words = renpy.get_widget("nvl", "what", config.nvl_layer).text[0]
                        nvl_expected = ("{b}%s{/b}" % name, expected)
                        check("legacy NVL displays and retains the resolved %s line and speaker tags" % name,
                              nvl_entry == nvl_expected and (nvl_history.who, nvl_history.what) == nvl_expected
                              and nvl_words == expected, repr((nvl_entry, nvl_history.what, nvl_words)))
                    renpy.hide_screen("nvl", layer=config.nvl_layer)
                    renpy.hide_screen("qrn_say", layer=say_layer)
                    choose("Mara", "Nora")
                finally:
                    (config.history_length, store._history, store._history_list,
                     store.nvl_list, store._nvl_language, ctx.rollback) = history_state

            # An old save has no receipt. It still receives the active
            # rule when the identified variable holds its original name.
            store.qrn_name = "Mara"
            setattr(store, _URMRN_RECEIPTS, ())
            _urmrn_refresh()
            check("an old save receives the rename and records the original and written name",
                  store.qrn_name == "Nora" and bool(getattr(store, _URMRN_RECEIPTS)) and bool(retained))
            import pickle
            saved = pickle.loads(pickle.dumps(getattr(store, _URMRN_RECEIPTS), 2))
            choose("Mara", "Iris")
            store.qrn_name = "Nora"
            setattr(store, _URMRN_RECEIPTS, saved)
            _urmrn_refresh()
            check("loading an earlier rename applies the current name with its original intact",
                  store.qrn_name == "Iris" and qrn_literal.name == "Iris")
            store.qrn_name = "Lila"
            _urmrn_refresh()
            choose("Lila", "Ada")
            store.qrn_name = "Mara"
            _urmrn_refresh()
            first_save = store.qrn_name
            store.qrn_name = "Lila"
            _urmrn_refresh()
            check("one variable can apply different rename rules in different saves",
                  first_save == "Iris" and store.qrn_name == "Ada", repr((first_save, store.qrn_name)))
            urmrn_restore("Lila")
            store.qrn_literal = pickle.loads(pickle.dumps(qrn_literal, 2))
            replacement = Character("Iris")
            store.qrn_replaced = replacement
            store.qrn_name = "Changed by the game"
            urmrn_restore("Mara")
            check("restore preserves an unrelated later game write and restores the literal Character",
                  qrn_name == "Changed by the game" and qrn_literal.name == "Mara")
            check("restore keeps a replacement Character even when its name matches our last write",
                  qrn_replaced is replacement and qrn_replaced.name == "Iris", repr(qrn_replaced.name))
            store.qrn_name = "Mara"
            choose("Mara", "Nora")
            urmrn_restore("Mara")
            check("restore returns a name variable to its original value", qrn_name == "Mara")
            choose("Mara", "Nora")
            saved_character = pickle.dumps(qrn_literal, 2)
            saved_receipts = getattr(store, _URMRN_RECEIPTS)
            urmrn_restore("Mara")
            store.qrn_literal = pickle.loads(saved_character)
            setattr(store, _URMRN_RECEIPTS, saved_receipts)
            _urmrn_refresh()
            check("loading a marked Character from a save after restoring the preference restores its name",
                  qrn_literal.name == "Mara" and not hasattr(qrn_literal, "_urmrn_written_name"))

            # A real render through the Settings shell, with a saved rename
            # on the right and the speaker/dialogue/choice preview on the left.
            urmrn_edit("Mara", "Nora")
            _urmh_state().section = "character_names"
            sd = ds.ScreenDisplayable(ds.get_screen_variant("urmh_settings"), "urmh_settings",
                                      "screens", scope={"_kwargs": {}})
            sd.update()
            sd.visit_all(lambda d: d.per_interact())
            root = core.Fixed()
            root.add(sd)
            rendered = renpy.display.render.render_screen(root, config.screen_width, config.screen_height)
            words, at = [], {}
            def walk(r, x):
                for d in getattr(r, "render_of", ()) or ():
                    if isinstance(d, renpy.text.text.Text):
                        for v in d.text:
                            if isinstance(v, (str, type(u""))):
                                words.append(v)
                                at[v] = (x, d.style.size)
                for child in r.children:
                    if isinstance(child[0], renpy.display.render.Render):
                        walk(child[0], x + child[1])
            walk(rendered, 0)
            check("Settings has both real input widgets and the Character names section",
                  "source" in sd.widgets and "target" in sd.widgets
                  and _urm_section_screen("character_names") == "urmrn_settings")
            check("the engine draws the preview and the saved name's edit and restore controls",
                  all(word in words for word in ("Preview", "Nora left a light on.", "Ask Nora about the light",
                                                  "Edit", "Restore", "Eli to Theo")), repr(words))
            fields = (at.get("Nora"), at.get("Nora left a light on."), at.get("Ask Nora about the light"))
            check("all preview values use a readable size and align at the same x",
                  all(field is not None and field[1] >= urmk_px(22) for field in fields)
                  and max(field[0] for field in fields) - min(field[0] for field in fields) <= 1,
                  repr(fields))
            picture = pic("character_names")
            if picture:
                import pygame_sdl2 as pygame
                surf = pygame.Surface((config.screen_width, config.screen_height), pygame.SRCALPHA)
                surf.fill((20, 22, 26, 255))
                renpy.display.swdraw.draw(surf, None, rendered, 0, 0, True)
                pygame.image.save(surf, picture)
        finally:
            urmrn_cancel()
            _urm_setting_set(_URMRN_SETTING, previous)
            _urmh_state().section = None
            ctx.init_phase = init
            renpy.retain_after_load = retain
'''

PROBE_ENTRY = "_qrn_probe"
PROBE_PIC_ENV = "URMRN_PICTURES"
PROBE_TAG_ENV = "URMRN_TAG"
PROBE_MIN_ENGINES = 2

if __name__ == "__main__":
    sys.exit(prop_probes.main_single(__file__, sys.argv))
