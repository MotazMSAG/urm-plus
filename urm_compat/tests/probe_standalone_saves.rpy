# Save three distinct games using each prop's own native save and load.
screen urm_save_fixture_active():
    null width 8 height 8

init 1998 python:
    import os as _ss_os
    import sys as _ss_sys

    _SS_NAMES = (
        "progressDragged", "Var", "Input", "SetVarValue", "SettingsClass",
        "ProgressBarClass", "Tooltip", "Notification", "InputGroup", "URMFileStore",
    )
    _SS_LAYER = "x52Overlay"
    _SS_MODE = _ss_os.environ.get("URM_GATE_SAVES")
    _ss_results = python_list()

    def _ss_require(condition, detail):
        if not condition:
            raise AssertionError(detail)

    def _ss_ok(name):
        _ss_results.append(name + "=True")

    if _SS_MODE == "native":
        # These obsolete screens and names are present only while making the
        # legacy save. They contain synthetic data and no original UI code.
        config.layers.append(_SS_LAYER)
        for screen_name in ("URM_overlay", "urmb_chip", "urmh_button"):
            renpy.define_screen(screen_name, lambda **scope: None)

        class _URMRMiddleClick(renpy.Displayable):
            def render(self, width, height, st, at):
                return renpy.Render(0, 0)

        def urm_branch_close():
            pass

        def urm_branch_dragged(drags, drop):
            pass

        class _URMFlagVar(python_object):
            pass

    def _ss_legacy_screens():
        native = bytes if _ss_sys.version_info[0] == 2 else str
        module = native("store.x52URM")
        space = renpy.python.StoreDict()
        space["__name__"] = module
        saved = _ss_sys.modules[module] = renpy.python.StoreModule(space)
        objects = []
        for name in _SS_NAMES:
            cls = type(native(name), (object,), {"__module__": module})
            setattr(saved, name, cls)
            if name == "progressDragged":
                objects.append(cls)
            else:
                record = cls()
                record.fixture_payload = name
                objects.append(record)

        for name in ("URM_overlay", "urmb_chip", "urmh_button"):
            renpy.show_screen(name, _layer=_SS_LAYER)
        flag = _URMFlagVar()
        flag.name, flag.word, flag.where = ("fixture_flag", "fixture word", "")
        overlay = renpy.get_screen("URM_overlay", layer=_SS_LAYER)
        overlay.scope["fixture_values"] = tuple(objects) + (_URMRMiddleClick(),)
        chip = renpy.get_screen("urmb_chip", layer=_SS_LAYER)
        chip.scope["fixture_values"] = (urm_branch_close, urm_branch_dragged, flag)
        renpy.show_screen("urm_save_fixture_active")

    def _ss_play():
        renpy.python.make_clean_stores()
        renpy.exports.execute_default_statement(True)
        ctx = renpy.game.context()
        ctx.init_phase = False
        ctx.rollback = True
        ctx.current = renpy.game.script.lookup("prop_tl").name
        # The context used by lint predates init-time layer registrations.
        scene = ctx.scene_lists
        for layer in config.layers + config.top_layers:
            if layer not in scene.layers:
                scene.layers[layer] = []
                scene.at_list[layer] = {}
                scene.layer_at_list[layer] = (None, [])
        scene.after_setstate()
        store.main_menu = False
        config.developer = False
        renpy.game.interface.started = True
        # A usual save has a thumbnail. Use one pixel for headless runs.
        import binascii
        renpy.game.interface.screenshot = binascii.unhexlify(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
            "0000000b49444154789c636000020000050001a5f645400000000049454e44ae426082")
        renpy.style.rebuild()
        renpy.display.screen.prepare_screens()

    def _ss_save(slot, number, extras=None):
        ctx = renpy.game.context()
        ctx.current = renpy.game.script.lookup("prop_tl").name
        renpy.game.log.begin(True)
        store.prop_voice = number
        if extras:
            extras()
        renpy.game.log.checkpoint(hard=True)
        renpy.game.log.complete(True)
        renpy.game.log.begin(True)
        renpy.game.log.complete(True)
        renpy.save(slot, u"Standalone gate")

    def _ss_native():
        _ss_require(not hasattr(store, "_urm_setting"), "ordinary game loaded URM+")
        _ss_ok("plain_game")
        _ss_save("batch-ordinary", 21)
        _ss_ok("ordinary_save_written")
        _ss_save("batch-legacy", 22, _ss_legacy_screens)
        _ss_ok("legacy_save_written")

    def _ss_load(slot):
        try:
            renpy.load(slot)
        except BaseException as error:
            if type(error).__name__.startswith("Restart"):
                renpy.game.context().init_phase = False
                return
            raise
        raise AssertionError("load did not restart the context")

    def _ss_check_legacy_screens(resaved):
        ctx = renpy.game.context()
        active = renpy.get_screen("urm_save_fixture_active")
        _ss_require(active is not None, "the game screen did not restore")
        old = {entry.displayable.screen_name[0]: entry.displayable
               for entry in ctx.scene_lists.layers.get(_SS_LAYER, ())}
        _ss_require(_SS_LAYER not in config.layers + config.top_layers, "the legacy layer is visible")
        if resaved:
            _ss_require(not old, ("obsolete screens after resave", sorted(old)))
            overlay, chip = active.scope["fixture_values"]
        else:
            _ss_require(set(old) == {"URM_overlay", "urmb_chip", "urmh_button"},
                        ("restored obsolete screens", sorted(old)))
            overlay = old["URM_overlay"].scope["fixture_values"]
            chip = old["urmb_chip"].scope["fixture_values"]
        _ss_require(len(overlay) == len(_SS_NAMES) + 1, "legacy overlay scope length changed")
        callback = overlay[0]
        _ss_require((callback.__module__, callback.__name__) == ("store.x52URM", _SS_NAMES[0]),
                    "legacy progress callback changed name")
        for name, record in zip(_SS_NAMES[1:], overlay[1:-1]):
            _ss_require((type(record).__module__, type(record).__name__) == ("store.x52URM", name),
                        ("legacy type", name, type(record)))
            _ss_require(record.fixture_payload == name, ("legacy payload", name, record.fixture_payload))
        expected = renpy.display.layout.Null if resaved else _URMRMiddleClick
        _ss_require(type(overlay[-1]) is expected, ("legacy middle click", type(overlay[-1])))
        close, dragged, flag = chip
        _ss_require(close is urm_branch_close and dragged is urm_branch_dragged, "legacy chip callbacks changed")
        _ss_require(type(flag) is _URMFlagVar and (flag.name, flag.word, flag.where) == ("fixture_flag", "fixture word", ""),
                    "legacy flag state changed")

        # Let the engine update and draw the layers it normally shows. The
        # obsolete screens stay in the save and never enter this render.
        drawn = []
        for layer in config.layers + config.top_layers:
            for entry in ctx.scene_lists.layers.get(layer, ()):
                displayable = entry.displayable
                if isinstance(displayable, renpy.display.screen.ScreenDisplayable):
                    displayable.update()
                    displayable.visit_all(lambda child: child.per_interact())
                    renpy.display.render.render_screen(displayable, config.screen_width, config.screen_height)
                    drawn.append(displayable.screen_name[0])
        _ss_require("urm_save_fixture_active" in drawn and not set(drawn).intersection(old),
                    ("screens drawn after load", drawn))
        return overlay, chip

    def _ss_standalone():
        _ss_require(_urmi_layer == "urmplus" and not hasattr(store, "x52URM"),
                    "the game did not start with URM+ alone")
        _ss_ok("standalone_game")
        def standalone():
            _ss_require(_urm_freeze("prop_voice"), "could not freeze the standalone value")
        _ss_save("batch-standalone", 23, standalone)
        _ss_ok("standalone_save_written")
        for slot, number in (("batch-ordinary", 21), ("batch-standalone", 23), ("batch-legacy", 22)):
            store.prop_voice = 0
            _ss_load(slot)
            restored = getattr(store, "prop_voice", None)
            _ss_require(restored == number, (slot, "restored value", restored))
            if slot == "batch-standalone":
                _ss_require(_urm_is_frozen("prop_voice"), "standalone save lost the frozen value")
                _ss_ok("standalone_save_loaded")
            elif slot == "batch-legacy":
                saved_scopes = _ss_check_legacy_screens(False)
                _ss_ok("legacy_scopes_loaded_and_drawn")

                def keep_scopes():
                    # New checkpoints drop unregistered layers. Keep the
                    # references on a drawn screen to exercise re-pickling.
                    renpy.get_screen("urm_save_fixture_active").scope["fixture_values"] = saved_scopes
                _ss_save("batch-resave", 24, keep_scopes)
                _ss_load("batch-resave")
                _ss_require(store.prop_voice == 24, "resave lost the game value")
                _ss_check_legacy_screens(True)
                _ss_ok("legacy_scopes_resaved_and_reloaded")
            else:
                _ss_require(not _urm_is_frozen("prop_voice"), "ordinary save unexpectedly froze the value")
                _ss_ok("ordinary_save_loaded")

    def _ss_lint():
        import traceback
        mode = _ss_os.environ["URM_GATE_SAVES"]
        try:
            home = _ss_os.path.normcase(_ss_os.path.abspath(_ss_os.environ["URM_GATE_HOME"]))
            savedir = _ss_os.path.normcase(_ss_os.path.abspath(config.savedir))
            scratch = _ss_os.path.normcase(_ss_os.path.abspath(config.basedir))
            _ss_require(savedir.startswith(home + _ss_os.sep) or savedir.startswith(scratch + _ss_os.sep),
                        "save directory is outside the scratch copy")
            _ss_ok("save_directory_isolated")
            _ss_play()
            {"native": _ss_native, "standalone": _ss_standalone}[mode]()
        except Exception:
            _ss_results.append(traceback.format_exc())
        with open(_ss_os.path.join(config.basedir, "saves_" + mode + ".txt"), "w") as out:
            out.write("\n".join(_ss_results))
        _ss_os._exit(0)

    if "URM_GATE_SAVES" in _ss_os.environ:
        renpy.arguments.commands["lint"] = _ss_lint
