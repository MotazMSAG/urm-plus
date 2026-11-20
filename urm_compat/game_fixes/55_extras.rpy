# ---------------------------------------------------------------------------
# Six things a player wanted and URM did not have
# ---------------------------------------------------------------------------
#
# Each one is a public helper in this store, or a method swapped on one of
# URM's classes. The screens that use them are guarded on the helper's own
# name, so a build whose zzz_urm_compat.rpyc did not compile for this engine
# draws URM's UI exactly as it ships.

init 999 python:

    # ------------------------------------------------------------------
    # Copy to clipboard
    # ------------------------------------------------------------------
    #
    # There is not one clipboard call anywhere in URM 2.6.2: a variable name,
    # a value, a condition and a file:line can only be retyped. Values are
    # less of a problem than they look - they land in an x52URM.Input, and
    # Ren'Py's Input already handles ctrl+C through its copypaste path
    # (display/behavior.py:1743) - so what is actually missing is the names,
    # which are never editable text.
    #
    # Ren'Py 7 and 8 both reach the clipboard through pygame_sdl2, which is
    # also registered under the name pygame; both are tried because which one
    # is importable from a store varies with how the game was built.

    def urm_copy(text):
        """Put `text` on the system clipboard and say so."""

        try:
            data = text if isinstance(text, bytes) else (text or u"").encode("utf-8")
        except Exception:
            return

        done = False

        for module in ("pygame_sdl2", "pygame"):
            try:
                scrap = __import__(module).scrap
                scrap.put(scrap.SCRAP_TEXT, data)
                done = True
                break
            except Exception:
                continue

        try:
            renpy.notify("Copied" if done else "This build has no clipboard")
        except Exception:
            pass


    # ------------------------------------------------------------------
    # Browse the whole store
    # ------------------------------------------------------------------
    #
    # URM can only show a variable you already found by name, or loaded from a
    # .urm file. If you do not know roughly what it is called, there is no way
    # in at all - which makes search the single entry point to every variable
    # in the game.
    #
    # Nothing new is needed to render it. Var.children already handles
    # varType 'store' (vars.rpy:361) and URM_objectVar already draws a paged,
    # expandable table of children with the breadcrumb above it, so the whole
    # feature is handing that screen a Var over the store itself.
    #
    # A list rather than a Var, so the screen can hand it straight to
    # expandObjectVars and an engine where this does not resolve gives an
    # empty browser instead of a crash.

    def urm_store_root():
        """[Var('store')], or [] if this engine will not expand it."""

        try:
            root = x52URM.Var("store")
            if root.isExpandable:
                return [root]
        except Exception:
            pass
        return []


    # ------------------------------------------------------------------
    # Remembered labels: a filter, and whether you have been there
    # ------------------------------------------------------------------
    #
    # The Labels tab paginates and sorts and nothing else, so with fifty
    # remembered labels the only way to find one is to click through pages.
    # It also cannot say whether you have already seen a label: the thumbnail
    # view colours by renpy.has_label, which is existence, not visited.

    def urm_labels(text):
        """The remembered labels narrowed by `text`, as [(name, props)]."""

        try:
            items = python_list(x52URM.LabelsStore.store.items())
        except Exception:
            return []

        needle = (text or u"").strip().lower()
        if not needle:
            return items

        found = python_list()

        for name, props in items:
            shown = u""
            try:
                shown = props.get("name") or u""
            except Exception:
                pass
            try:
                if needle in (name or u"").lower() or needle in shown.lower():
                    found.append((name, props))
            except Exception:
                continue

        return found

    def urm_seen(label):
        """
        True seen, False not seen, None when the engine cannot say.

        None covers a label that is not in this build at all, which is the
        common case for a save carried across an update - and it must not be
        drawn as "not seen", because that would read as missable content.
        """

        try:
            if not renpy.has_label(label):
                return None
            return bool(renpy.seen_label(label))
        except Exception:
            return None


    # ------------------------------------------------------------------
    # The gates the Path dialog does not show
    # ------------------------------------------------------------------
    #
    # PathDetection.statements is ifStatement[0].entries and stops there
    # (PathDetection.rpy:75), so the dialog lists the arms of one
    # if-statement. When that if has no else, not matching it falls straight
    # through to whatever check comes next, and those gates are invisible -
    # the same blind spot the notification cards already fixed with
    # _urm_chain.
    #
    # They are deliberately read-only. URM forces a path by rewriting the
    # chain up to the DETECTED node (PathDetection.rpy:160-178); a gate two
    # statements later is not that node, so a Select button there would not
    # work. Showing the rows without one is honest; showing one that silently
    # does nothing is not.

    def urm_later_gates():
        """[(icon, number, condition, effects)] for the gates after the first if."""

        out = python_list()
        for _i, icon, number, head, effects in urm_later_gate_rows():
            out.append((icon, number, head, effects))
        return out

    def urm_later_gate_rows():
        """
        [(row, icon, number, condition, effects)] for every gate after the
        if-statement the Path options table shows - the ones the script runs
        into when none of that table matches.

        This used to be "every card but the first", and the first if's own
        arms are cards too: the section repeated rows 2.. of the table. Each
        row now also remembers how to force it (urmf_force_later).
        """

        rows = python_list()
        specs = python_list()
        try:
            steps = _urm_chain()
            meta = getattr(x52URM.Var, "_urmChainMeta", None) or ()
            if not steps or len(meta) != len(steps):
                return rows
            first = meta[0][0]
            success = _urm_signal("success")
            error = _urm_signal("error")

            order = python_list()      # the if-statements, in the order run
            states = _urmsg_gate_states(steps, _urm_truth)
            at = 0
            for (kind, cond, payload), (node, arm) in zip(steps, meta):
                state, number = states[at]
                at += 1
                if node is not None and node not in order:
                    order.append(node)

                if kind == "gate":
                    if state == "runs":
                        icon = _urm_tint(_URM_ICON_LIVE, success)
                    elif state == "unknown":
                        icon = _URM_ICON_UNKNOWN
                    else:
                        icon = _urm_tint(_URM_ICON_DEAD, error)
                    head = _urm_colorize(str(cond))
                    effects = _urm_effects(payload)
                    label = "%d" % number
                else:
                    icon = _urm_fallback_icon(state == "dead", state == "unknown",
                                              success, error)
                    head = _urm_words("nothing above matches")
                    label = ""
                    if kind == "else":
                        effects = _urm_effects(payload)
                    else:
                        effects = python_list()
                        effects.append((_URM_ICON_EFFECT, _urm_colorize(payload)))

                if node is first or len(rows) >= _URM_MAX_GATES:
                    continue

                # Miss every if-statement before this one, then take this arm.
                spec = python_list()
                for earlier in order:
                    if earlier is node:
                        break
                    spec.append((earlier, -1))
                if node is not None:
                    spec.append((node, arm))
                rows.append((len(rows), icon, label, head, effects))
                specs.append(spec)
        except BaseException:
            del rows[:]
            del specs[:]
        x52URM.Var._urmfLaterSpecs = specs
        return rows


