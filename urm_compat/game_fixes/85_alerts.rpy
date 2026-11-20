# ---------------------------------------------------------------------------
# Alerts: stop and say so when the game checks something the player marked
# ---------------------------------------------------------------------------
#
# A player picks "feet fetish" early on, then skips scenes - and wants to be
# told when a scene checks that choice. Any variable or flag can be marked
# (the bell in its dialog, in the flag dialog, or on the Flags list). When an
# if-statement or a menu the game is running tests a marked name, the skip
# stops and a banner says what was checked, in which scene, and whether it
# passed - so the player knows whether the gated scene is about to play.
#
# The test is read from the condition itself - the same names the script
# index records - when the game executes the if or the menu, so it covers
# every way in: jumps, calls, replays. Checks made inside the game's own
# python functions are not seen, as everywhere else in URM+.
#
# The marks are kept in URM's own per-game settings.

init 999 python:

    try:
        x52URM.SettingsClass.defaultValues.setdefault("urmcAlerts", None)
    except Exception as error:
        print("URM+: alerts setting not registered (%s)" % (error,))

    class _URMALState(python_object):
        def __init__(self):
            self.names = python_dict()   # id(node) -> [(arm, condition, option, marked names)]
            self.lines = python_list()   # what the banner says
            self.marked = python_list()  # what the banner is about

    def _urmal_state():
        st = getattr(x52URM.Var, "_urmalState", None)
        if st is None:
            st = _URMALState()
            x52URM.Var._urmalState = st
        return st

    def urmal_marked():
        try:
            return x52URM.Settings.get("urmcAlerts") or ()
        except Exception:
            return ()

    def urmal_is(name):
        return name in urmal_marked()

    def urmal_toggle(name):
        marks = python_list(urmal_marked())
        if name in marks:
            marks.remove(name)
            words = "URM+: no longer alerting for %s"
        else:
            marks.append(name)
            words = "URM+: you will be alerted when the game checks %s"
        try:
            x52URM.Settings.set("urmcAlerts", marks)
        except Exception as error:
            renpy.notify("URM+: could not save the alert (%s)" % (error,))
            return
        renpy.notify(words % name)
        renpy.restart_interaction()

    def _urmal_tests(index, node):
        """Every condition of an if or a menu, with the marked names it tests."""

        ast = renpy.ast
        out = python_list()
        marks = urmal_marked()
        # The tests are the story graph's list (rework move 8); a menu
        # line with nothing under it is a caption, not an option.
        is_if = isinstance(node, ast.If)
        items = None if is_if else node.items
        for arm, cond, option in _urmsg_conds(node):
            if not is_if and items[arm][2] is None:
                continue
            if not cond or cond.strip() == "True":
                continue
            hit = sorted(n for n in _urmp_names_of(index, cond) if n in marks)
            if hit:
                out.append((arm, cond, option, hit))
        return out

    def _urmal_check(node):
        marks = urmal_marked()
        if not marks:
            return
        index = _urmi_index()
        if index is None or index.state != "ready":
            return
        st = _urmal_state()
        key = (id(node), tuple(marks))
        tests = st.names.get(key)
        if tests is None:
            if len(st.names) > 5000:
                st.names.clear()
            tests = _urmal_tests(index, node)
            st.names[key] = tests
        if not tests:
            return

        scene = _urmp_scene(index, node, node.filename, node.linenumber) or "?"
        lines = python_list()
        named = python_list()
        is_menu = isinstance(node, renpy.ast.Menu)
        fired = False
        for arm, cond, option, hit in tests:
            for name in hit:
                if name not in named:
                    named.append(name)
            try:
                passed = bool(renpy.python.py_eval(cond))
            except Exception:
                passed = None
            if is_menu:
                verdict = {True: "shown", False: "hidden", None: "can't tell"}[passed]
                lines.append(u'The choice "%s" needs it - %s' % (_urmp_plain(option, 60), verdict))
            elif passed and not fired:
                fired = True
                lines.append(u"%s - passes: what it gates plays now" % _urmp_plain(cond, 80))
            elif passed is None:
                lines.append(u"%s - can't tell" % _urmp_plain(cond, 80))
            else:
                lines.append(u"%s - %s" % (_urmp_plain(cond, 80),
                                           "doesn't pass" if not passed else "passes, but an earlier branch runs"))

        st.marked = named
        st.lines = python_list()
        st.lines.append(u"%s checked in %s" % (u", ".join(_urmp_plain(n, 60) for n in named),
                                              _urmp_plain(scene, 60)))
        st.lines.extend(lines[:4])
        if config.skipping:
            config.skipping = None
            st.lines.append(u"Skipping stopped.")
        if renpy.has_screen("urmal_alert"):
            for layer in (_urmi_layer, "overlay"):
                try:
                    renpy.show_screen("urmal_alert", _layer=layer)
                    break
                except Exception:
                    continue

    def _urmal_wrap(previous):
        def execute(self, *args, **kwargs):
            try:
                _urmal_check(self)
            except Exception:
                pass
            return previous(self, *args, **kwargs)
        execute._urmal = True
        # Keep the force-a-path patch's marker visible through this wrapper.
        execute._urmf = getattr(previous, "_urmf", False)
        return execute

    for _urmal_cls in (renpy.ast.If, renpy.ast.Menu):
        try:
            _urmal_prev = _urmal_cls.execute
            _urmal_prev = getattr(_urmal_prev, "__func__", _urmal_prev)
            if not getattr(_urmal_prev, "_urmal", False):
                _urmal_cls.execute = _urmal_wrap(_urmal_prev)
        except Exception as error:
            print("URM+: alerts not watching %s (%s)" % (_urmal_cls.__name__, error))

    # The banner is shown on URM's own layer, so a plain Hide('urmal_alert')
    # looks on the default "screens" layer, finds nothing, and the OK button,
    # "Stop alerting" and the timer all did nothing (2026-11-17). Hide it on
    # whichever layer it is on.
    def urmal_close():
        for layer in python_list(config.layers) + python_list(getattr(config, "top_layers", ())):
            try:
                if renpy.get_screen("urmal_alert", layer=layer) is not None:
                    renpy.hide_screen("urmal_alert", layer=layer)
            except Exception:
                continue

    def urmal_stop(name):
        urmal_toggle(name)
        urmal_close()

    def urmal_lines():
        return _urmal_state().lines

    def urmal_banner_marked():
        return _urmal_state().marked


