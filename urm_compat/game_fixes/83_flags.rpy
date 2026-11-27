# ---------------------------------------------------------------------------
# Flags: choices a game keeps as words in a collection
# ---------------------------------------------------------------------------
#
# Many games do not give a choice a variable of its own. Nothing Is Forever
# adds a word to one set - option("ch6_kim_accept") - and tests it with
# true("ch6_kim_accept"), 1,133 and 1,987 times; its paths are objects in
# another set, added with new_path(kim_mercy_path) and tested with
# on_path("kim_mercy_path"). URM's editor sees "a set" and stops there.
#
# The index learns each game's helpers from their definitions (_URMIndex.
# _helpers) and turns every test and every setter call into a flag named by
# the code that tests it - true("ch6_kim_accept"), on_path("kim_mercy_path"),
# or "met_kim" in diary for a word tested directly. From there a flag is a
# variable like any other to the variable panel: what each side gets you,
# which choice sets it, warnings.
#
# Reading a flag never calls the game's helper: the collection is read
# directly. Switching one edits the collection directly too - adding the word,
# or the object that stands for it - rather than calling new_path(), which
# would also pop the game's "new path" notification.

init 999 python:


    def _urmfl_object(rec):
        """The object that stands for an object-kept flag, e.g. kim_mercy_path."""

        for objname in rec.objects:
            value = _urmp_value(objname)
            if value is not _URMP_UNK and _urmfl_matches(rec, value):
                return value
        count = 0
        for value in python_list(renpy.store.__dict__.values()):
            count += 1
            if count > 50000:
                break
            try:
                if not callable(value) and getattr(value, rec.attr, None) == rec.word:
                    return value
            except Exception:
                continue
        return None

    def urmfl_set(name, on):
        rec = _urmfl_record(name)
        if rec is None:
            return
        coll = _urmfl_collection(rec)
        if coll is None:
            renpy.notify("URM: %s does not exist in this save yet" % rec.coll)
            return
        current = urmfl_is_on(name)
        try:
            if on and not current:
                member = rec.word
                if rec.attr:
                    member = _urmfl_object(rec)
                    if member is None:
                        renpy.notify("URM: could not find what stands for %s" % rec.word)
                        return
                if isinstance(coll, python_dict):
                    coll[rec.word] = True
                elif hasattr(coll, "add"):
                    coll.add(member)
                else:
                    coll.append(member)
            elif not on and current:
                if isinstance(coll, python_dict):
                    coll.pop(rec.word, None)
                else:
                    for member in python_list(coll):
                        if _urmfl_matches(rec, member):
                            coll.remove(member)
        except Exception as error:
            renpy.notify("URM: could not change %s (%s)" % (rec.word, error))
            return
        renpy.notify("URM: %s is now %s" % (rec.word, "ON" if on else "OFF"))
        renpy.restart_interaction()

    def urmfl_has():
        return _urmfl_index() is not None

    def urmfl_rows(text, limit=200):
        """([(flag, word, on, what it is)], how many match) for the Flags screen."""

        index = _urmfl_index()
        rows = python_list()
        if index is None:
            return (rows, 0)
        needle = (text or u"").strip().lower()
        matched = 0
        for name in sorted(index.flags, key=lambda n: index.flags[n].word.lower()):
            rec = index.flags[name]
            if needle and needle not in rec.word.lower() and needle not in name.lower():
                continue
            matched += 1
            if len(rows) >= limit:
                continue
            reads = len(index.reads.get(name) or ())
            writes = len(index.writes.get(name) or ())
            info = u"checked in %d place%s, set in %d" % (reads, "" if reads == 1 else "s", writes)
            rows.append((name, _urmi_safe(rec.word), urmfl_is_on(name), _urmi_safe(info)))
        return (rows, matched)

    # ---- a name old saves hold
    #
    # The Flags dialog before our own sheet (until 2026-11-22) kept one of
    # these in its screen's scope, and it was not modal, so a save made with
    # a flag's Details open names it (FINDINGS). Kept so such a save loads:
    # the class takes whatever the save holds and does nothing.

    class _URMFlagVar(python_object):
        pass

    # ---- a flag's Details: the variable sheet (our own, with URM or
    # without), on our layer, so it opens and closes here.

    def urmfl_details(name):
        if renpy.has_screen("urmfl_flag_dialog"):
            renpy.show_screen("urmfl_flag_dialog", name=name, _layer=_urmi_layer)
            renpy.restart_interaction()

    _urmfl_open = urmfl_details

    config.hyperlink_handlers["URMFlag"] = _urmfl_open

    import re as _urmfl_re
    _URMFL_CALL = _urmfl_re.compile(
        r"(\{color=[^{}]*\})?\b([A-Za-z_]\w*)(\{/color\})?"
        r"\((\{color=[^{}]*\})?([\"'])([^\"'{}]*)\5(\{/color\})?\)")

    def _urmfl_links(view, coloredCode):
        """In the code view and on the path cards, true("x") opens the flag."""

        index = _urmfl_index()
        if index is None:
            return coloredCode

        def link(match):
            name = u'%s("%s")' % (match.group(2), match.group(6))
            if name not in index.flags:
                return match.group()
            return u"{a=URMFlag:%s}%s{/a}" % (name, match.group())

        try:
            return _URMFL_CALL.sub(link, coloredCode)
        except Exception:
            return coloredCode

    # ---- the Flags list (game_screens/83_flags): on our layer, so it opens
    # and closes here, not with Show and Hide (they look on the "screens"
    # layer). Its filter box starts empty each time.

    # The list is built as far as it is scrolled (DECISIONS 2026-11-26
    # "Instant windows"): 0.35 s to open on Being a DIK with all 200 rows.
    URMFL_ROWS = _URMKRows("flags", 40, 200)

    def urmfl_open():
        if renpy.has_screen("urmfl_flags"):
            urmk_old_input("flags", fresh=True)
            URMFL_ROWS.top()
            renpy.show_screen("urmfl_flags", _layer=_urmi_layer)
            renpy.restart_interaction()

    def urmfl_close():
        if renpy.get_screen("urmfl_flags", layer=_urmi_layer) is not None:
            renpy.hide_screen("urmfl_flags", layer=_urmi_layer)
            renpy.restart_interaction()

    # ---- the URM+ menu (the registry, 01_urm_door): only in a game that
    # keeps choices as words

    def _urmfl_shown():
        return urmfl_has() and renpy.has_screen("urmfl_flags")

    def _urmfl_count():
        return u"%d" % len(_urmfl_index().flags)

    _urm_entry_add("flags", "Flags", u"\ue153", lambda: urmfl_open(),
                   count=_urmfl_count, shown=_urmfl_shown, group=1, order=20)


