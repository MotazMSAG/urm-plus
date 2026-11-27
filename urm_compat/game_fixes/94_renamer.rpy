# One game-local rename per original speaker. Change only the store slots
# linked to that speaker; the displayed text uses the same rename list.
init 999 python:
    import re as _urmrn_re

    _URMRN_SETTING = "urmcCharacterNames"
    _URMRN_RECEIPTS = "_urmrn_name_receipts"
    URMRN_PAGE = 4
    _URMRN_NAME = _urmrn_re.compile(r"^[^{}\[\]%\x00-\x1f\x7f]{1,56}$")
    _URMRN_PATH = _urmrn_re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")
    _urm_setting_add(_URMRN_SETTING, ())

    class _URMRNState(python_object):
        def __init__(self):
            self.source = u""
            self.target = u""
            self.editing = None
            self.catalog = None
            self.rules = None
            self.names = python_dict()
            self.bindings = python_dict()
            self.pattern = None
            self.speech_prefix = python_dict()
            self.speech = ()
            self.page = 0
            self.revision = 0

    def urmrn_state():
        return _urm_kept("renamer", _URMRNState)

    def _urmrn_name(value):
        return (isinstance(value, (str, type(u""))) and value == value.strip()
                and _URMRN_NAME.match(value) is not None and any(c.isalnum() for c in value))

    def _urmrn_rules():
        return _urm_setting_at(_URMRN_SETTING, False) or ()

    def _urmrn_stores():
        return renpy.python.store_dicts

    def _urmrn_slot(expr):
        if not isinstance(expr, (str, type(u""))) or _URMRN_PATH.match(expr) is None:
            return None
        parent, dot, key = expr.rpartition(".")
        if not dot:
            return ("store", key)
        return ((parent if parent == "store" or parent.startswith("store.")
                 else "store." + parent), key)

    def _urmrn_catalog():
        st = urmrn_state()
        if st.catalog is not None:
            return st.catalog
        stores = _urmrn_stores()
        names = python_dict()
        siblings = python_dict()
        # Catalog only actual engine Character objects. A dynamic expression
        # can run game code, so discovery resolves simple store paths only.
        for scope, table in stores.items():
            for key, char in table.items():
                if not isinstance(char, renpy.character.ADVCharacter):
                    continue
                original = char.name
                if char.dynamic or (isinstance(original, (str, type(u"")))
                                    and original.startswith("[") and original.endswith("]")):
                    expr = original if char.dynamic else original[1:-1]
                    slot = _urmrn_slot(expr)
                    if slot is None:
                        continue
                    parent, name = slot
                    original = stores.get(parent, {}).get(name)
                    binding = ("var", parent, name)
                else:
                    binding = ("char", scope, key)
                if _urmrn_name(original):
                    names.setdefault(original, python_set()).add(binding)
                    siblings[binding] = original
        # A binding that already wears a preferred name still belongs to
        # the original entry in the editor.
        for original, preferred, bindings in _urmrn_rules():
            for binding in bindings:
                if siblings.get(binding) == preferred:
                    names[preferred].discard(binding)
                names.setdefault(original, python_set()).add(binding)
        st.catalog = python_dict((name, tuple(sorted(bindings))) for name, bindings in names.items()
                                 if bindings or any(name == row[0] for row in _urmrn_rules()))
        return st.catalog

    def _urmrn_match(text, resolved=False):
        st = urmrn_state()
        if st.pattern is None or not isinstance(text, (str, type(u""))):
            return text
        replace = lambda words: st.pattern.sub(lambda m: st.names[m.group(0)], words)
        if "{" not in text and (resolved or "[" not in text):
            return replace(text)
        marks = "{" if resolved else "{["
        parts = python_list()
        start = i = 0
        while i < len(text):
            mark = text[i]
            if mark not in marks:
                i += 1
                continue
            parts.append(replace(text[start:i]))
            end = i + 1
            if text[end:end + 1] == mark:
                end += 1
            else:
                close = "}" if mark == "{" else "]"
                depth = 1
                while end < len(text) and depth:
                    char = text[end]
                    depth += (char == mark) - (char == close)
                    end += 1
            parts.append(text[i:end])
            start = i = end
        parts.append(replace(text[start:]))
        return u"".join(parts)

    def _urmrn_sync():
        st = urmrn_state()
        rules = _urmrn_rules()
        if rules != st.rules:
            st.rules = rules
            st.revision += 1
            st.names = python_dict((original, preferred) for original, preferred, _bindings in rules)
            # A name already resolved by interpolation or a Character can
            # include the old name, as in Mara becoming Mara Vale.
            for preferred in tuple(st.names.values()):
                st.names.setdefault(preferred, preferred)
            st.bindings = python_dict()
            for original, preferred, slots in rules:
                for slot in slots:
                    st.bindings.setdefault(slot, python_dict())[original] = preferred
            ordered = sorted(st.names, key=lambda n: (-len(n), n))
            st.pattern = (_urmrn_re.compile(u"(?<!\\w)(?:%s)(?!\\w)" %
                         u"|".join(_urmrn_re.escape(n) for n in ordered), _urmrn_re.UNICODE)
                          if ordered else None)
            st.catalog = None
        root = _urmrn_stores()["store"]
        kept = root.get(_URMRN_RECEIPTS, ())
        if not rules and not kept:
            return
        wanted = st.bindings
        receipts = python_dict((slot, (original, value)) for slot, original, value in kept)
        # Retain the previous and last written name in each save. A game
        # that writes a different name keeps its own subsequent decision.
        stores = _urmrn_stores()
        slots = python_set(wanted).union(receipts)
        for slot in slots:
            kind, scope, key = slot
            table = stores.get(scope, {})
            current = table.get(key)
            previous = receipts.get(slot)
            rule = wanted.get(slot, {})
            character = None
            if kind == "char":
                character = current
                if not isinstance(character, renpy.character.ADVCharacter) or character.dynamic:
                    receipts.pop(slot, None)
                    continue
                current = character.name
                # The save slot locates a Character. Only the actual object
                # can attest that URM+ wrote its name.
                previous = getattr(character, "_urmrn_written_name", None)
                if previous and current != previous[1]:
                    del character._urmrn_written_name
                    previous = None
            original = previous[0] if previous and current == previous[1] else current
            if not _urmrn_name(original):
                receipts.pop(slot, None)
                continue
            value = rule.get(original, original)
            if current != value:
                if character is None:
                    table[key] = value
                else:
                    character.name = value
                    if value != original:
                        character._urmrn_written_name = (original, value)
                    elif previous is not None:
                        del character._urmrn_written_name
                table.ever_been_changed.add(key)
                _urm_keep()
            if value != original:
                receipts[slot] = (original, value)
            else:
                receipts.pop(slot, None)
        record = tuple((slot, pair[0], pair[1]) for slot, pair in sorted(receipts.items()))
        if record != kept:
            root[_URMRN_RECEIPTS] = record
            _urm_keep(_URMRN_RECEIPTS)

    def _urmrn_refresh():
        st = urmrn_state()
        st.catalog = None
        _urmrn_sync()
        _urm_stmt_bump()

    def _urmrn_open():
        urmrn_state().catalog = None

    def urmrn_list():
        return tuple((a, b) for a, b, _slots in _urmrn_rules())

    def urmrn_page(delta):
        st = urmrn_state()
        last = max(0, (len(_urmrn_rules()) - 1) // URMRN_PAGE)
        st.page = max(0, min(last, st.page + delta))

    def urmrn_candidates():
        st = urmrn_state()
        query = st.source.strip().lower()
        names = _urmrn_catalog()
        return tuple(name for name in sorted(names, key=lambda n: (n.lower(), n))
                     if query in name.lower())

    def urmrn_edit(original, preferred=u""):
        st = urmrn_state()
        st.source, st.target = original, preferred
        st.editing = original

    def urmrn_cancel():
        st = urmrn_state()
        st.source = st.target = u""
        st.editing = None

    def urmrn_problem():
        st = urmrn_state()
        original, preferred = st.source.strip(), st.target.strip()
        if not _urmrn_name(original) or not _urmrn_name(preferred) or preferred == original:
            return u""
        if preferred in _urmrn_catalog() or any(
                a != original and (a == preferred or b in (original, preferred))
                for a, b, _slots in _urmrn_rules()):
            return u"That name already belongs to another character."
        return None

    def urmrn_put():
        if urmrn_problem() is not None:
            return
        st = urmrn_state()
        original, preferred = st.source.strip(), st.target.strip()
        rules = python_dict((a, (b, slots)) for a, b, slots in _urmrn_rules())
        slots = python_set(rules.get(original, (None, ()))[1])
        slots.update(_urmrn_catalog().get(original, ()))
        rules[original] = (preferred, tuple(sorted(slots)))
        _urm_setting_set(_URMRN_SETTING, tuple((a, b, keys)
                         for a, (b, keys) in sorted(rules.items())))
        urmrn_cancel()

    def urmrn_restore(original):
        _urm_setting_set(_URMRN_SETTING, tuple(row for row in _urmrn_rules() if row[0] != original))
        urmrn_page(0)
        if urmrn_state().editing == original:
            urmrn_cancel()

    def urmrn_preview():
        sample = urmrn_state().target.strip()
        return sample if _urmrn_name(sample) else u""

    def _urmrn_esc(words):
        return words.replace(u"{", u"{{").replace(u"[", u"[[")

    _urmrn_character = renpy.character.ADVCharacter
    _urmrn_prefix = getattr(_urmrn_character, "prefix_suffix", None)
    _urmrn_display = _urmrn_character.do_display

    def _urmrn_speaker_source(character, who):
        if not urmrn_state().pattern or who is None:
            return who
        name = character.name
        if character.dynamic:
            slot = _urmrn_slot(name)
        elif isinstance(name, (str, type(u""))) and name.startswith("[") and name.endswith("]"):
            slot = _urmrn_slot(name[1:-1])
        else:
            written = getattr(character, "_urmrn_written_name", None)
            return written[0] if written and name == who == written[1] else who
        if slot is not None:
            scope, key = slot
            current = _urmrn_stores().get(scope, {}).get(key)
            if who == current or not character.dynamic and who == name:
                for binding, original, preferred in _urmrn_stores()["store"].get(_URMRN_RECEIPTS, ()):
                    if binding == ("var", scope, key) and current == preferred:
                        return original
        return who

    if _urmrn_prefix is not None:
        def _urmrn_prefix_suffix(self, thing, prefix, body, suffix):
            st = urmrn_state()
            if thing == "who":
                body = _urmrn_speaker_source(self, body)
            source = _urmrn_prefix(self, thing, prefix, body, suffix)
            changed = _urmrn_match(source, resolved=config.new_substitutions)
            if changed != source:
                st.speech_prefix[thing] = (self, source, changed)
            else:
                st.speech_prefix.pop(thing, None)
            return changed
        _urmrn_character.prefix_suffix = _urmrn_prefix_suffix

    def _urmrn_speech_pair(original, changed, dialogue=False, dtt=None):
        if original == changed:
            return None
        if dialogue and "{" in original:
            original_tags = renpy.character.DialogueTextTags(original)
            changed_tags = dtt if dtt is not None else renpy.character.DialogueTextTags(changed)
            return (original_tags.text, changed_tags.text,
                    tuple(zip(changed_tags.pause_start + changed_tags.pause_end,
                              original_tags.pause_start + original_tags.pause_end)))
        return (original, changed, ((0, 0), (len(changed), len(original))))

    def _urmrn_do_display(self, who, what, **display_args):
        st = urmrn_state()
        if _urmrn_prefix is None:
            # Ren'Py 7.3 resolves substitutions above do_display and creates
            # the pause boundaries inside it.
            source_who = _urmrn_speaker_source(self, who)
            source_what = what
            who = _urmrn_match(source_who, resolved=config.new_substitutions)
            what = _urmrn_match(source_what, resolved=config.new_substitutions)
        else:
            before_who = st.speech_prefix.pop("who", None)
            before_what = st.speech_prefix.pop("what", None)
            source_who = before_who[1] if before_who and before_who[0] is self and before_who[2] == who else who
            source_what = before_what[1] if before_what and before_what[0] is self and before_what[2] == what else what
        previous = st.speech
        who_pair = _urmrn_speech_pair(source_who, who)
        what_pair = _urmrn_speech_pair(source_what, what, True, display_args.get("dtt"))
        if not who_pair and not what_pair and not previous:
            return _urmrn_display(self, who, what, **display_args)
        st.speech = (who_pair, what_pair)
        try:
            return _urmrn_display(self, who, what, **display_args)
        finally:
            st.speech = previous

    _urmrn_character.do_display = _urmrn_do_display

    if _urmrn_prefix is None:
        # Ren'Py 7.3 appends history and NVL page entries outside ADV's
        # do_display. NVL also has its own display path before pause layout.
        _urmrn_history = _urmrn_character.add_history
        _urmrn_nvl = store.NVLCharacter
        _urmrn_nvl_show = _urmrn_nvl.do_display
        _urmrn_nvl_push = _urmrn_nvl.push_nvl_list

        def _urmrn_legacy_words(who, what):
            resolved = config.new_substitutions
            return _urmrn_match(who, resolved=resolved), _urmrn_match(what, resolved=resolved)

        def _urmrn_add_history(self, kind, who, what, multiple=None, **kwargs):
            who, what = _urmrn_legacy_words(who, what)
            return _urmrn_history(self, kind, who, what, multiple=multiple, **kwargs)

        def _urmrn_nvl_display(self, who, what, multiple=None, **display_args):
            who, what = _urmrn_legacy_words(who, what)
            return _urmrn_nvl_show(self, who, what, multiple=multiple, **display_args)

        def _urmrn_nvl_entry(self, who, what, multiple=None):
            who, what = _urmrn_legacy_words(who, what)
            return _urmrn_nvl_push(self, who, what, multiple=multiple)

        _urmrn_character.add_history = _urmrn_add_history
        _urmrn_nvl.do_display = _urmrn_nvl_display
        _urmrn_nvl.push_nvl_list = _urmrn_nvl_entry

    def _urmrn_visible(widget, speech=None):
        if not isinstance(widget, renpy.text.text.Text):
            return
        current = tuple(widget.text)
        previous = getattr(widget, "_urmrn_visible_text", None)
        if previous and current == previous[1]:
            original = previous[0]
            offsets = previous[2]
        else:
            original = current
            offsets = (widget.start, widget.end)
            if speech and current and current[0] == speech[1]:
                original = (speech[0],) + current[1:]
                boundaries = python_dict(speech[2])
                offsets = tuple(boundaries.get(offset, offset) for offset in offsets)
        changed = tuple(_urmrn_match(part, resolved=True) for part in original)
        if changed == current:
            return
        if original and isinstance(original[0], (str, type(u""))):
            start, end = offsets
            widget.start = len(_urmrn_match(original[0][:start], resolved=True)) if start is not None else None
            widget.end = len(_urmrn_match(original[0][:end], resolved=True)) if end is not None else None
        widget.text = python_list(changed)
        widget._urmrn_visible_text = (original, changed, offsets)
        widget.dirty = True
        renpy.display.render.invalidate(widget)

    def _urmrn_choice_button(widget):
        if isinstance(widget, renpy.display.behavior.Button):
            action = getattr(widget, "action", None)
            if isinstance(action, (Return, Jump, renpy.ui.ChoiceReturn)):
                widget.visit_all(_urmrn_visible)

    _urmrn_screen_update = renpy.display.screen.ScreenDisplayable.update

    def _urmrn_update(sd):
        if not sd.transient:
            return _urmrn_screen_update(sd)
        st = urmrn_state()
        previous = getattr(sd, "_urmrn_revision", None)
        dialogue = sd.screen_name == ("say",) or "what" in sd.widget_properties
        if dialogue and previous is None:
            # First show is handled by Character before Ren'Py computes
            # pause positions. Only redraw an already open line on edit.
            sd._urmrn_revision = st.revision
            if st.speech:
                scope = sd.scope.get("_kwargs", sd.scope)
                sd._urmrn_speech = tuple(pair if pair and scope.get(key) == pair[1] else None
                                         for key, pair in zip(("who", "what"), st.speech))
            return _urmrn_screen_update(sd)
        if not st.pattern and previous is None:
            return _urmrn_screen_update(sd)
        old = sd.child
        result = _urmrn_screen_update(sd)
        if sd.child is None or sd.child is old:
            return result
        if dialogue:
            if previous != st.revision:
                who, what = getattr(sd, "_urmrn_speech", (None, None))
                _urmrn_visible(sd.widgets.get("who"), who)
                _urmrn_visible(sd.widgets.get("what"), what)
            return result
        # Text widgets have already resolved Ren'Py interpolation. The
        # original MenuEntry captions and actions stay in engine scope.
        source = sd.scope.get("_kwargs", sd.scope)
        items = source.get("items")
        sd._urmrn_revision = st.revision
        if isinstance(items, (tuple, python_list)) and items and type(items[0]).__name__ == "MenuEntry":
            sd.child.visit_all(_urmrn_visible)
        else:
            sd.child.visit_all(_urmrn_choice_button)
        return result

    renpy.display.screen.ScreenDisplayable.update = _urmrn_update
    _urm_player_text_add(_urmrn_match)
    _urm_setting_watch(_URMRN_SETTING, _urmrn_refresh)
    config.interact_callbacks.append(_urmrn_sync)
    config.start_callbacks.append(_urmrn_refresh)
    config.after_load_callbacks.append(_urmrn_refresh)
    _urm_section_add("character_names", "Character names", u"\ue7fd", order=50,
                     screen="urmrn_settings", on_open=_urmrn_open)
