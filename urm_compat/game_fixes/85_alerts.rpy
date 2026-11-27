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
# The marks are kept in URM+'s own per-game settings.

init 999 python:

    _urm_setting_add("urmcAlerts", None)

    class _URMALState(python_object):
        def __init__(self):
            self.names = python_dict()   # id(node) -> [(arm, condition, option, marked names)]
            self.head = u""              # the banner's headline: what was checked, where
            self.rows = python_list()    # (what was tested, its verdict, the verdict's tone)
            self.stopped = False         # the alert stopped a skip
            self.marked = python_list()  # what the banner is about

    def _urmal_state():
        return _urm_kept("alerts", _URMALState)

    def urmal_marked():
        return _urm_setting("urmcAlerts") or ()

    def urmal_is(name):
        return name in urmal_marked()

    def urmal_toggle(name):
        marks = python_list(urmal_marked())
        if name in marks:
            marks.remove(name)
            words = "MRM: no longer alerting for %s"
        else:
            marks.append(name)
            words = "MRM: you will be alerted when the game checks %s"
        try:
            _urm_setting_set("urmcAlerts", marks)
        except Exception as error:
            renpy.notify("MRM: could not save the alert (%s)" % (error,))
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
        rows = python_list()
        named = python_list()
        is_menu = isinstance(node, renpy.ast.Menu)
        fired = False
        for arm, cond, option, hit in tests:
            for name in hit:
                if name not in named:
                    named.append(name)
            passed = _urm_truth(cond)
            # The verdict is a tone chip (UX rule 9): green it plays, red it
            # does not, amber it passes but another way runs, plain unknown.
            # A number test that plays or not says it as a goal (rule 8,
            # the user's pick 2b): "you have 1, needs 3".
            if is_menu:
                what = u'The choice "%s" needs it' % _urmp_plain(option, 60)
                verdict, tone = {True: (u"shown", "gain"), False: (u"hidden", "loss"),
                                 None: (u"can't tell", "plain")}[passed]
            else:
                what = _urmp_plain(cond, 80)
                if passed and not fired:
                    fired = True
                    verdict, tone = u"passes: what it gates plays now", "gain"
                elif passed is None:
                    verdict, tone = u"can't tell", "plain"
                elif not passed:
                    verdict, tone = u"doesn't pass", "loss"
                else:
                    verdict, tone = u"passes, but an earlier branch runs", "warn"
            if tone in ("gain", "loss"):
                verdict = urm_goal_words(cond) or verdict
            rows.append((what, verdict, tone))

        st.marked = named
        st.head = u"%s checked in %s" % (u", ".join(_urmp_plain(n, 60) for n in named),
                                         _urmp_plain(scene, 60))
        st.rows = python_list(rows[:4])
        st.stopped = bool(config.skipping)
        if st.stopped:
            config.skipping = None
        if renpy.has_screen("urmal_alert"):
            try:
                renpy.show_screen("urmal_alert", _layer=_urmi_layer)
            except Exception as error:
                print("MRM: the alert could not show (%s)" % (error,))

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
            print("MRM: alerts not watching %s (%s)" % (_urmal_cls.__name__, error))

    # The banner is shown on the URM+ layer, so a plain Hide('urmal_alert')
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

    def urmal_view():
        """What the banner shows: (headline, rows, whether a skip stopped,
        the names it is about)."""

        st = _urmal_state()
        return st.head, st.rows, st.stopped, st.marked

    # ---- the URM+ menu (the registry, 01_urm_door): only while something
    # is marked, since there is nothing to stop otherwise

    def _urmal_count():
        return u"%d on" % len(urmal_marked())

    def _urmal_items():
        """Each marked name in words, with a Stop that unmarks it."""
        return [(_urmp_plain(name, 60), u"Stop", (lambda n=name: urmal_toggle(n)))
                for name in urmal_marked()]

    # The menu folds the marked names out under it (the user's pick a,
    # 2026-11-22).
    _urm_entry_add("alerts", "Alerts", u"\ue7f4", None, count=_urmal_count,
                   shown=lambda: bool(urmal_marked()), items=_urmal_items, group=1, order=30)
