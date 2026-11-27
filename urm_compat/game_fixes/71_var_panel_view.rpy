    # ------------------------------------------------------------------
    # The panel: what the variable sheet is drawn from
    # ------------------------------------------------------------------
    #
    # urm_panel(name) reads the script once per name, value and position
    # and hands the sheet (74_var_window, layout C) its rungs, its story
    # line, the choice on screen and one verdict. The long text of the
    # first panel (answer paragraphs, warnings, three tabs) went with it.

    class _URMPanel(python_object):
        def __init__(self, name):
            self.name = name
            self.state = "ready"
            self.pct = None
            self.message = None
            self.deps = None
            self.mode = None
            # The window (74_var_window): rungs, story line, choice on
            # screen, one verdict as (words, tone).
            self.win_rungs = python_list()
            self.win_story = python_list()
            self.win_now = python_list()
            self.win_verdict = None

    def _urmp_mode(index, name, now):
        reads = index.reads.get(name) or ()
        boolish = 0
        nums = 0
        texts = 0
        for _s, op, lit in reads:
            if op in ("truthy", "falsy") or lit is True or lit is False:
                boolish += 1
            elif _urm_isnum(lit):
                nums += 1
            elif isinstance(lit, _urmi_text) and op in ("==", "!="):
                texts += 1
        total = max(len(reads), 1)
        if isinstance(now, bool):
            return "bool"
        if (now is _URMP_UNK or now in (0, 1)) and boolish * 10 > total * 6 and not nums:
            return "bool"
        if _urm_isnum(now) or (now is _URMP_UNK and nums >= texts and nums):
            return "number"
        if isinstance(now, _urmi_text) or (now is _URMP_UNK and texts):
            return "value"
        return "generic"

    def urm_panel(name):
        """Everything the variable panel draws, cached per name, value and position."""

        state, pct = urm_index_status()
        if state != "ready":
            p = _URMPanel(name)
            p.state = state
            p.pct = pct
            if state == "building":
                p.message = "Reading the game's script... %s%%. This fills in when it's done." % (pct or 0)
            elif state == "failed":
                p.message = "Couldn't read the game's script, so this can't show what %s does." % name
            else:
                p.message = None
            return p

        index = _urmi_index()
        now = _urmp_value(name)
        cur = _urmp_current(index)
        try:
            lang = _preferences.language
        except Exception:
            lang = None
        try:
            shown = repr(now)[:120]
        except Exception:
            shown = "?"
        key = (id(index), index.finished_at, name, shown, cur[0] if cur else None, lang)
        cache = _urmp_bucket("panels")
        found = cache.get(key)
        if found is not None and _urmp_deps_hold(found.deps):
            return found
        # Per-open caches: words like "(with hard_love at 30 now)" and
        # speaker names depend on values that may have changed since.
        st = _urmp_state()
        st["req"] = python_dict()
        st["speakers"] = python_dict()
        st["deps"] = python_dict()
        try:
            p = _urmp_compose(index, name, now, cur)
            p.deps = st["deps"]
        except Exception as error:
            p = _URMPanel(name)
            p.state = "failed"
            p.message = "The panel hit a problem reading %s (%s). The value box above still works." % (
                name, _urmp_plain(u"%s: %s" % (type(error).__name__, error), 120))
            import traceback
            traceback.print_exc()
        st["deps"] = None
        if len(cache) >= 8:
            cache.clear()
        cache[key] = p
        return p

    def _urmp_deps_hold(deps):
        """The values a cached panel was worked out from are still the same."""

        if not deps:
            return True
        for dep, value in deps.items():
            current = _urmp_value(dep)
            if current is _URMP_UNK or type(current) is not type(value) or current != value:
                return False
        return True

    def _urmp_compose(index, name, now, cur):
        p = _URMPanel(name)
        budget = python_list()
        budget.append(_URMP_NODE_BUDGET)
        seen = _URMPSeen()
        mode = _urmp_mode(index, name, now)
        p.mode = mode

        rows = _urmp_rows(index, name)
        writes = _urmp_writes(index, name)

        # --- edge states -------------------------------------------------
        if not rows and not writes:
            funcs = _urmp_function_mentions(name)
            if funcs:
                p.message = (u"The story script never uses %s directly. The game's own code mentions it in %s. "
                             u"What that code does with it isn't shown." % (name, ", ".join("%s()" % f for f in funcs[:3])))
            else:
                p.message = (u"The story script never checks or sets %s by name. "
                             u"It may still be used in the game's screens or its own code." % name)
            p.win_verdict = (u"Does nothing in the story", "other")
            return p

        # --- where it is checked ------------------------------------------
        for r in rows:
            r.summary = _urmp_summary(r.block, budget, 6)
            r.status = _urmp_status(r.label, r.file, r.line, r.summary.first_node, cur, seen)
            r.weight = _urmp_weight(r.summary, index, budget)
        rows = [r for r in rows if r.kind != "loop"]

        # An on/off value: which side of it each check plays.
        if mode == "bool":
            on_value, off_value = (1, 0) if _urmp_isint(now) else (True, False)
            for r in rows:
                _t, mine, _o = _urmp_atoms(r.cond, name)
                on = all(_urmp_ev(a, name, on_value) is True for a in mine) if mine else False
                off = all(_urmp_ev(a, name, off_value) is True for a in mine) if mine else False
                r.side = None if on == off else ("on" if on else "off")

        # --- who sets it --------------------------------------------------
        mass = _urmp_mass_labels(index) if writes else python_set()
        menus = python_dict()
        menu_order = python_list()
        auto = python_list()
        for w in writes:
            w.status = _urmp_status(w.label, w.file, w.line, None, cur, seen)
            if w.menu is not None:
                # An option that names the variable itself - "set
                # switch_213 to True" - is the game's own scene-select or
                # cheat menu, not a story choice.
                if w.scene in mass or name.lower() in (u"%s" % (w.option,)).lower():
                    continue
                g = menus.get(id(w.menu))
                if g is None:
                    g = python_list()
                    menus[id(w.menu)] = g
                    menu_order.append(w.menu)
                g.append(w)
            else:
                auto.append(w)

        current_menu = None
        if cur is not None:
            for m in menu_order:
                if id(m) == cur[4]:
                    current_menu = m
            for r in rows:
                if r.kind == "option" and id(r.node) == cur[4]:
                    current_menu = r.node

        # Set again before it matters: in most scenes that check it, the
        # game sets it itself shortly before.
        overwritten = False
        reading_scenes = python_dict()
        for r in rows:
            reading_scenes.setdefault(r.scene, r.line)
        if len(reading_scenes) >= 3:
            reset_here = 0
            for scene, line in reading_scenes.items():
                for w in auto:
                    if w.scene == scene and w.op == "=" and w.line < line:
                        reset_here += 1
                        break
            if reset_here * 10 >= len(reading_scenes) * 8:
                overwritten = True

        _urmp_window(p, name, now, mode, rows, menus, menu_order, auto,
                     current_menu, seen, overwritten)
        return p


    # ------------------------------------------------------------------
    # What the screen calls
    # ------------------------------------------------------------------

    def urmi_ui(key, default=None):
        return _urmp_bucket("ui").get(key, default)

    def urmi_ui_set(key, value):
        _urmp_bucket("ui")[key] = value
        renpy.restart_interaction()

    def urmi_ui_toggle(key):
        ui = _urmp_bucket("ui")
        ui[key] = not ui.get(key, False)
        renpy.restart_interaction()
