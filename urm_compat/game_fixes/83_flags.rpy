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

    def _urmfl_index():
        index = _urmi_index()
        if index is None or index.state != "ready" or not getattr(index, "flags", None):
            return None
        return index

    def _urmfl_record(name):
        index = _urmfl_index()
        if index is None or not isinstance(name, _urmi_text):
            return None
        return index.flags.get(name)

    def _urmfl_getters(index):
        found = getattr(index, "_urmflGetters", None)
        if found is None:
            found = python_dict()
            for fname, (role, coll, _attr) in index.helpers.items():
                if role == "get" and coll not in found:
                    found[coll] = fname
            index._urmflGetters = found
        return found

    def _urmfl_name_of(node):
        """The flag a test is, for true("x") and "x" in coll - else None."""

        index = _urmfl_index()
        if index is None:
            return None
        if isinstance(node, _urmi_ast.Call):
            if not isinstance(node.func, _urmi_ast.Name) or not node.args:
                return None
            ok, word = _urmi_literal(node.args[0])
            if not ok or not isinstance(word, _urmi_text):
                return None
            name = u'%s("%s")' % (node.func.id, word)
            return name if name in index.flags else None
        if isinstance(node, _urmi_ast.Compare) and len(node.ops) == 1 and \
                isinstance(node.ops[0], (_urmi_ast.In, _urmi_ast.NotIn)):
            ok, word = _urmi_literal(node.left)
            coll = _urmi_name(node.comparators[0])
            if not ok or not isinstance(word, _urmi_text) or coll is None:
                return None
            getter = _urmfl_getters(index).get(coll)
            name = u'%s("%s")' % (getter, word) if getter else u'"%s" in %s' % (word, coll)
            return name if name in index.flags else None
        return None

    def _urmfl_collection(rec):
        try:
            value = _urmp_ev(_urmp_parse(rec.coll))
        except Exception:
            return None
        if value is _URMP_UNK:
            return None
        return value

    def _urmfl_matches(rec, member):
        if rec.attr:
            return getattr(member, rec.attr, None) == rec.word
        return member == rec.word

    def urmfl_is_on(name):
        """True / False, or None when the game has not made the collection yet."""

        rec = _urmfl_record(name)
        if rec is None:
            return None
        coll = _urmfl_collection(rec)
        if coll is None:
            return False
        try:
            if isinstance(coll, python_dict):
                return bool(coll.get(rec.word))
            for member in coll:
                if _urmfl_matches(rec, member):
                    return True
            return False
        except Exception:
            return None

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

    class _URMFlagVar(python_object):
        """What the variable panel needs from a variable, for a flag."""

        isFlag = True
        isEditable = True
        varType = "boolean"

        def __init__(self, name):
            self.name = name
            rec = _urmfl_record(name)
            self.word = _urmi_safe(rec.word if rec else name)
            if rec is None:
                self.where = u""
            elif rec.getter:
                self.where = _urmi_safe(u"Kept in %s, tested with %s()" % (rec.coll, rec.getter))
            else:
                self.where = _urmi_safe(u"Kept in %s" % rec.coll)

        @property
        def value(self):
            return urmfl_is_on(self.name)

    def urmfl_var(name):
        return _URMFlagVar(name)

    def _urmfl_open(name):
        if renpy.has_screen("urmfl_flag_dialog"):
            renpy.show_screen("urmfl_flag_dialog", name=name)
            renpy.restart_interaction()

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


