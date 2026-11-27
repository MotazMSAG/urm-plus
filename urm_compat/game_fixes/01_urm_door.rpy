# ---------------------------------------------------------------------------
# Settings, remembered items and session memory
# ---------------------------------------------------------------------------

# Settings. A piece registers each of its own with _urm_setting_add(name,
# default), reads it with _urm_setting(name), writes it with
# _urm_setting_set(name, value), and may ask to hear of a change with
# _urm_setting_watch(name, fn). A value lives at one of two levels, the two
# settings levels shown on the URM+ page:
#   this game   persistent._urm_settings, a plain dict
#   all games   settings.json in our own folder beside the game's saves
#               (path_to_saves(gamedir, "URMplus")), shared by every game
# and is read this game -> all games -> default. None is never a value: writing None clears that level.
#
# Lists. The player's Remembered and Ignored variables, kept for this game
# in persistent._urm_lists: {"vars": ((name, label, ignored), ...)}, in the
# player's order; label is the words the player gave it, ignored a tuple of
# "path" and "code". Plain builtin data only, so the persistent data still
# loads with URM+ gone. (Rows written before 2026-11-22's Freeze had a
# fourth field, a frozen mark never set; it is read past.) Read and written
# only through _urm_remember / _urm_forget / _urm_is_remembered,
# _urm_ignore / _urm_unignore / _urm_is_ignored / _urm_ignored_names and
# _urm_remembered().
# They start empty: players are taken never to have used URM's own
# Remember and Ignore (DECISIONS 2026-11-22), so nothing is copied from URM
# and nothing of URM's is read. The variable sheet and the corner card use
# these alone.
#
# Frozen. A freeze is a name and the value it holds, and lives in the save
# like a value the game set (DECISIONS 2026-11-22, 1a): store._urm_freezes,
# a tuple of (name, value), value a number, words or yes/no of exactly a
# builtin type (a game's own kind is not frozen), so a save loads with URM+
# gone. Each change puts a new tuple, so a
# rollback past a freeze undoes it, and a save made before has none (the
# engine's load starts from a clean store). _urm_hold puts the held values
# back before every statement (config.statement_callbacks: after a Python
# line, and before an `if` that follows a screen action) and at every
# interaction (a screen's SetVariable): it reads only the frozen names,
# never the whole store, and does nothing at all while nothing is frozen.
# Inside one Python block the game still reads its own change; the value
# goes back when the block ends. Names are read and written by the search
# engine's own walker (dotted names, keys), which it hands in at init
# (_urm_walker); the core never names the feature. _urm_freeze(name) holds
# what the name holds now (and remembers it), _urm_unfreeze, _urm_is_frozen,
# _urm_can_freeze (for a button), _urm_frozen(); _urm_set(name, value) is
# our Set: a frozen name then holds the new value. Every Set of ours ends with _urm_after_set(name): kept in a
# save made at once (FINDINGS: a name joins a save only once a statement
# that changed it ends; _urm_keep), and a frozen name holds the new value.
#
# Memory. What a piece keeps while the game runs (caches, the script index,
# a feature's state) is an attribute of _URMMemory, made by _urm_kept(name,
# make). A class is neither saved nor rolled back, so nothing on it reaches
# a save or the rollback log. (Before 2026-11-21 it hung on x52URM.Var for
# that reason.)
#
# What a feature offers the player: the URM+ menu and settings page. A
# feature registers what it offers here; the menu and the page only walk
# these lists, so they never name a feature (a feature never uses another
# feature, and the menu is not a feature's).
#   _urm_entry_add(name, words, icon, action, ...)   an entry in the menu:
#       something to open (the route map), a switch (skip unseen text) or a
#       step (back to the last choice), or a list that folds out (the
#       alerts' marked names, each with Stop). Anyone opens one by its name:
#       _urm_open(name). _urm_entries() works out, when the menu opens,
#       which to show and what each says; _urm_keys() the hotkeys.
#   _urm_section_add(name, words, icon)               a section of the page
#   _urm_row_add(name, section, words, about, options, setting=...)
#       a row of the page: a setting of ours, shown at both its levels
#       (this game, which can be cleared, and all games), or with get= and
#       put= a value the engine keeps for this game alone. _urm_rows(section)
#       lists them, _urm_row_view(name) says what a row shows,
#       _urm_row_pick(name, value, all_games) and _urm_row_clear(name) write
#       through the settings above, so a value lands where URM's options
#       page put it and carries over untouched.
# Nothing a feature registers is called until the menu or the page opens,
# and then each inside try/except: a feature that fails is left out and
# said once in the log, never stops the menu.

init 999 python:

    import json as _urm_json
    import os as _urm_os

    class _URMMemory(python_object):
        """What URM+ keeps while the game runs, as class attributes."""

    def _urm_in_game():
        """The story is running in the game's main context: the one rule for
        when our screens on the game (the URM+ button, the branch chip, the
        corner card) draw. A game's menus (save, load, preferences, history)
        and H, which hides the interface, run in a context of their own with
        no rollback, and every layer is carried into it."""
        try:
            ctx = renpy.game.context()
            return bool(ctx.rollback) and not ctx.init_phase
        except Exception:
            return False

    def _urm_kept(name, make):
        """The object kept under `name`, made by make() the first time."""
        found = getattr(_URMMemory, name, None)
        if found is None:
            found = make()
            setattr(_URMMemory, name, found)
        return found

    class _URMSettingsState(python_object):
        def __init__(self):
            self.defaults = python_dict()   # name -> default: every setting of ours
            self.watchers = python_dict()   # name -> [fn], called after a write
            self.shared = None              # all games: name -> value, read on first use
            self.path = None                # all games: the file, "" when there is none

    _urm_settings_st = _URMSettingsState()

    # --- where the values live -------------------------------------------

    def _urm_shared_path():
        st = _urm_settings_st
        if st.path is None:
            st.path = ""
            try:
                import __main__
                folder = __main__.path_to_saves(config.gamedir, "URMplus")
                if folder:
                    st.path = _urm_os.path.join(folder, "settings.json")
            except Exception as error:
                print("MRM: no settings for all games (%s)" % (error,))
        return st.path

    def _urm_shared():
        """The all-games values, read from their file once."""
        st = _urm_settings_st
        if st.shared is None:
            st.shared = python_dict()
            path = _urm_shared_path()
            if path and _urm_os.path.isfile(path):
                try:
                    with open(path, "rb") as f:
                        data = _urm_json.loads(f.read().decode("utf-8"))
                    st.shared.update(data.get("values") or python_dict())
                except Exception as error:
                    print("MRM: could not read %s (%s)" % (path, error))
        return st.shared

    def _urm_shared_save():
        st = _urm_settings_st
        path = _urm_shared_path()
        if not path:
            return
        try:
            folder = _urm_os.path.dirname(path)
            if not _urm_os.path.isdir(folder):
                _urm_os.makedirs(folder)
            data = _urm_json.dumps(python_dict(values=st.shared), sort_keys=True)
            new = path + ".new"
            with open(new, "wb") as f:
                f.write(data.encode("utf-8"))
            replace = getattr(_urm_os, "replace", None)
            if replace is not None:
                replace(new, path)
            else:
                # Python 2 renames over nothing on Windows.
                if _urm_os.path.exists(path):
                    _urm_os.remove(path)
                _urm_os.rename(new, path)
        except Exception as error:
            print("MRM: could not save %s (%s)" % (path, error))

    def _urm_persistent():
        return renpy.game.persistent

    def _urm_local():
        found = getattr(_urm_persistent(), "_urm_settings", None)
        return found if isinstance(found, python_dict) else python_dict()

    def _urm_local_put(name, value):
        # A new dict each time, so the engine sees the persistent data change.
        local = python_dict(_urm_local())
        if value is None:
            local.pop(name, None)
        else:
            local[name] = value
        _urm_persistent()._urm_settings = local

    # --- reading and writing ---------------------------------------------

    def _urm_setting_at(name, level=None):
        """level None: the value in effect (this game, all games, default);
        True: all games, or the default; False: this game, None when unset."""
        if not level:
            local = _urm_local()
            if name in local:
                return local[name]
            if level is not None:
                return None
        shared = _urm_shared()
        if name in shared:
            return shared[name]
        return _urm_settings_st.defaults.get(name)

    def _urm_setting(name):
        """The value of a setting of ours that is in effect."""
        return _urm_setting_at(name)

    def _urm_setting_set(name, value, level=None):
        """level true: all games, else this game. None clears it."""
        if level:
            shared = _urm_shared()
            if value is None:
                shared.pop(name, None)
            else:
                shared[name] = value
            _urm_shared_save()
        else:
            _urm_local_put(name, value)
        for fn in _urm_settings_st.watchers.get(name, ()):
            try:
                fn()
            except Exception as error:
                print("MRM: after %s changed (%s)" % (name, error))
        renpy.restart_interaction()

    def _urm_setting_watch(name, fn):
        """Call fn() after every write of `name`, from any screen."""
        found = _urm_settings_st.watchers.setdefault(name, python_list())
        if fn not in found:
            found.append(fn)

    def _urm_setting_add(name, default):
        """Register a setting and its default."""
        _urm_settings_st.defaults.setdefault(name, default)

    # --- our lists: Remembered, Ignored, Frozen ---------------------------

    _URM_LIST_WHEN = ("path", "code")

    def _urm_plain_words(text):
        """Words as the builtin type, never a subclass (persistent must load
        without anything of URM's or ours)."""
        return text if type(text) in (type(u""), type("")) else u"%s" % (text,)

    def _urm_lists_rows():
        """Our list, a tuple of (name, label, ignored)."""
        found = getattr(_urm_persistent(), "_urm_lists", None)
        if isinstance(found, python_dict) and isinstance(found.get("vars"), tuple):
            return tuple(row[:3] for row in found["vars"])
        return ()

    def _urm_lists_put(rows):
        # A new dict each time, so the engine sees the persistent data change.
        _urm_persistent()._urm_lists = python_dict(vars=tuple(
            (_urm_plain_words(n), _urm_plain_words(l), tuple(w for w in _URM_LIST_WHEN if w in i))
            for n, l, i in rows))

    def _urm_lists_row(name):
        for row in _urm_lists_rows():
            if row[0] == name:
                return row
        return None

    def _urm_lists_change(name, change):
        """Write the row of `name`: change(row or None) gives the new row,
        or None to drop it."""
        rows = python_list(_urm_lists_rows())
        for i, row in enumerate(rows):
            if row[0] == name:
                new = change(row)
                if new is None:
                    del rows[i]
                else:
                    rows[i] = new
                break
        else:
            new = change(None)
            if new is None:
                return
            rows.append(new)
        _urm_lists_put(rows)
        renpy.restart_interaction()

    def _urm_remembered():
        """Our list, in the player's order: [(name, label, ignored)]."""
        return python_list(_urm_lists_rows())

    def _urm_is_remembered(name):
        return _urm_lists_row(name) is not None

    def _urm_remember(name, label=None):
        """Remember `name`, under `label` (its own name when none)."""
        def change(row):
            if row is None:
                return (name, label or name, ())
            return (name, label or row[1], row[2])
        _urm_lists_change(name, change)

    def _urm_forget(name):
        """Forget `name`, with its ignore marks; a freeze of it ends."""
        _urm_lists_change(name, lambda row: None)
        _urm_unfreeze(name)

    def _urm_is_ignored(name, when="path"):
        row = _urm_lists_row(name)
        return row is not None and when in row[2]

    def _urm_ignore(name, when=_URM_LIST_WHEN):
        """Ignore `name` for paths and/or the code view; it is remembered."""
        when = (when,) if when in _URM_LIST_WHEN else tuple(when)
        def change(row):
            row = row or (name, name, ())
            return (name, row[1], tuple(w for w in _URM_LIST_WHEN if w in row[2] or w in when))
        _urm_lists_change(name, change)

    def _urm_unignore(name, when=_URM_LIST_WHEN):
        when = (when,) if when in _URM_LIST_WHEN else tuple(when)
        def change(row):
            if row is None:
                return None
            return (name, row[1], tuple(w for w in row[2] if w not in when))
        _urm_lists_change(name, change)

    def _urm_ignored_names(when="path"):
        """The names ignored for `when`, in the player's order."""
        return python_list(r[0] for r in _urm_lists_rows() if when in r[2])

    # --- muted Path notifications: exact checks, kept for this game only

    def _urm_path_mutes():
        """The ordered (key, title, cue) records, made of plain values."""
        return _urm_setting_at("urmcPathMutes", False) or ()

    def _urm_path_is_muted(key, rows):
        cached = getattr(_URMMemory, "path_mute_keys", None)
        if cached is None or cached[0] is not rows:
            cached = (rows, frozenset(row[0] for row in rows))
            _URMMemory.path_mute_keys = cached
        return key in cached[1]

    def _urm_path_mute(key, title, cue):
        rows = _urm_path_mutes()
        if key and not _urm_path_is_muted(key, rows):
            _urm_setting_set("urmcPathMutes", rows + ((key, title, cue),), False)

    def _urm_path_unmute(key):
        rows = _urm_path_mutes()
        if _urm_path_is_muted(key, rows):
            left = tuple(row for row in rows if row[0] != key)
            _urm_setting_set("urmcPathMutes", left or None, False)

    # --- frozen: a name and the value it holds, in the save ---------------

    # What a freeze holds: a number, words or yes/no, of exactly these
    # builtin types (Python 2's long and byte words too). A game's own kind
    # (a subclass) is refused: putting it back as a plain value would swap
    # the game's object.
    _URM_HELD_KINDS = (type(True), type(0), type(1 << 70), type(0.0), type(u"")) + (
        (type(b""),) if __import__("sys").version_info[0] == 2 else ())

    def _urm_walker(read, write):
        """The search engine's reader, name -> (found, value), and writer,
        (name, value), of a name at any depth: what a freeze walks with."""
        _URMMemory.walker = (read, write)

    def _urm_keep(name=None):
        """A change of ours outlives the load's return to the last checkpoint,
        so a save made at once has it; and a store `name` it made goes into
        that save, as the engine's own `default` statement puts its names
        there."""
        if name is not None:
            renpy.python.store_dicts["store"].ever_been_changed.add(name)
        renpy.retain_after_load()

    def _urm_after_set(name):
        """What follows every Set of ours on `name`: a save made at once has
        it (a plain store name joins the save; an attribute or key is saved
        with what holds it, when the game saves that), and a frozen name
        holds the new value."""
        _urm_keep(None if ("." in name or "[" in name) else name)
        _urm_stmt_bump()
        if _urm_is_frozen(name):
            _urm_hold_now(name)

    def _urm_frozen():
        """[(name, value held)], in the order frozen."""
        found = renpy.store.__dict__.get("_urm_freezes")
        return python_list(found) if isinstance(found, tuple) else python_list()

    def _urm_is_frozen(name):
        for n, v in _urm_frozen():
            if n == name:
                return True
        return False

    def _urm_frozen_put(pairs):
        renpy.store._urm_freezes = tuple(pairs)
        _urm_keep("_urm_freezes")
        renpy.restart_interaction()

    def _urm_freezable_now(name):
        """(True, value) when `name` can be frozen at what it holds now: it
        can be read, and is a number, words or yes/no; else (False, None)."""
        walker = getattr(_URMMemory, "walker", None)
        if walker is None:
            return False, None
        found, value = walker[0](name)
        if not found or type(value) not in _URM_HELD_KINDS:
            return False, None
        return True, value

    def _urm_can_freeze(name):
        """Whether Freeze can hold `name` now (a frozen one can, too)."""
        return _urm_freezable_now(name)[0]

    def _urm_hold_now(name):
        """`name` holds what it holds now: True, or False when it cannot be
        read or is not a number, words or yes/no."""
        ok, value = _urm_freezable_now(name)
        if not ok:
            return False
        pairs = _urm_frozen()
        for i, (n, v) in enumerate(pairs):
            if n == name:
                pairs[i] = (n, value)
                break
        else:
            pairs.append((_urm_plain_words(name), value))
        _urm_frozen_put(pairs)
        return True

    def _urm_freeze(name):
        """Freeze `name` at what it holds now, and remember it. True when
        frozen; False when it cannot be read or is not a number, words or
        yes/no."""
        if not _urm_hold_now(name):
            return False
        if not _urm_is_remembered(name):
            _urm_remember(name)
        return True

    def _urm_unfreeze(name):
        pairs = _urm_frozen()
        kept = [(n, v) for n, v in pairs if n != name]
        if len(kept) != len(pairs):
            _urm_frozen_put(kept)

    def _urm_set(name, value):
        """Our Set: `value` into `name` as the game's own code would put it
        (rollback has it); a frozen name then holds it. True when written."""
        walker = getattr(_URMMemory, "walker", None)
        if walker is None or not walker[1](name, value):
            return False
        _urm_after_set(name)
        return True

    def _urm_hold(*args):
        """Before every statement (an `if` too, after a screen's action that
        jumped) and at every interaction: each frozen name that holds
        anything else gets its value back. Reads the frozen names alone;
        nothing at all while none is frozen. Never raises into the game."""
        held = renpy.store.__dict__.get("_urm_freezes")
        if not held:
            return
        try:
            read, write = _URMMemory.walker
            for name, value in held:
                try:
                    found, now = read(name)
                    if found and (type(now) is not type(value) or now != value):
                        write(name, value)
                except Exception:
                    pass        # a name gone from the game: nothing to put back
        except Exception:
            pass                # no walker: nothing can be put back

    def _urm_stmt_bump(*args):
        """Advance the store-change counter whenever the story steps, loads,
        or URM+ writes."""
        _URMMemory.stmt_seq = getattr(_URMMemory, "stmt_seq", 0) + 1

    def _urm_store_stamp():
        """Cheap identity of the store's current state: (stmt_seq, rollback
        log node id). Unchanged across opening/closing URM+ screens on the
        same line; changes on statement, save load, rollback/rollforward,
        or URM+ Set."""
        log = getattr(renpy.game, "log", None)
        cur = getattr(log, "current", None) if log is not None else None
        return (getattr(_URMMemory, "stmt_seq", 0), id(cur))

    try:
        if _urm_hold not in config.statement_callbacks:
            config.statement_callbacks.append(_urm_hold)
        if _urm_hold not in config.interact_callbacks:
            config.interact_callbacks.append(_urm_hold)
        if _urm_stmt_bump not in config.statement_callbacks:
            config.statement_callbacks.append(_urm_stmt_bump)
        if _urm_stmt_bump not in config.after_load_callbacks:
            config.after_load_callbacks.append(_urm_stmt_bump)
    except Exception as error:
        print("MRM: freeze not hooked (%s)" % (error,))

    # --- what a feature offers: the URM+ menu and settings page ----------

    class _URMOffer(python_object):
        """A menu entry, a section or a row, as a feature registered it."""

        def __init__(self, **fields):
            self.__dict__.update(fields)

    class _URMOffers(python_object):
        def __init__(self):
            self.entries = python_dict()    # name -> _URMOffer
            self.sections = python_dict()
            self.rows = python_dict()
            self.statuses = python_dict()   # name -> _URMOffer: what the button says
            self.under = python_dict()      # name -> _URMOffer: a part under the button
            self.failed = python_set()      # what was said in the log already

    def _urm_offers():
        return _urm_kept("offers", _URMOffers)

    def _urm_offer_failed(what, name, error):
        """Say once in the log that a feature's offer failed."""
        failed = _urm_offers().failed
        if (what, name) not in failed:
            failed.add((what, name))
            print("MRM: %s %s left out (%s)" % (what, name, error))

    def _urm_entry_add(name, words, icon, action, on=None, count=None, shown=None,
                       items=None, key=None, key_words=None, more=False, group=1, order=50):
        """An entry in the URM+ menu, named `name` (unique).
        words: what it says; icon: a glyph of the kit's icon font.
        action(): what picking it does; for a switch, it flips it. None
        for an entry that only folds out its items.
        on(): makes the entry a switch, true when it is on.
        count(): words after it ("12", "2 on"), or None for none.
        shown(): false leaves it out of the menu for now.
        items(): rows the menu folds out under it when it is picked, each
        (words, a step's words, what the step does), as the alerts' marked
        names, each with Stop.
        key: a key that does the same from anywhere ('alt_K_g'), and
        key_words how the menu writes it ('Alt+G').
        more: it opens a further page (the menu marks it so).
        group: the menu draws its entries in groups with a line between:
        1 what opens a display, 2 quick switches and steps, 9 the settings.
        order: its place inside its group."""
        _urm_offers().entries[name] = _URMOffer(
            name=name, words=words, icon=icon, action=action, on=on, count=count,
            shown=shown, items=items, key=key, key_words=key_words, more=more, group=group, order=order)

    def _urm_entries():
        """The entries to show now, in their order, each with what it says
        now (.on: True, False or None for no switch; .count: words or
        None; .items: the rows it folds out, or None). Every feature's function is called here, inside try/except:
        an entry that fails is left out."""
        out = python_list()
        found = sorted(_urm_offers().entries.values(), key=lambda e: (e.group, e.order, e.name))
        for e in found:
            try:
                if e.shown is not None and not e.shown():
                    continue
                on = bool(e.on()) if e.on is not None else None
                count = e.count() if e.count is not None else None
                items = (python_list((w, s, a) for w, s, a in e.items())
                         if e.items is not None else None)
            except Exception as error:
                _urm_offer_failed("menu entry", e.name, error)
                continue
            out.append(_URMOffer(name=e.name, words=e.words, icon=e.icon, on=on, count=count,
                                 items=items, key_words=e.key_words, more=e.more, group=e.group))
        return out

    def _urm_control_exceptions():
        """Ren'Py's rollback/jump/restart signals: never swallow them."""
        game = getattr(renpy, "game", None)
        found = getattr(game, "CONTROL_EXCEPTIONS", ())
        return found if isinstance(found, tuple) else ()

    def _urm_open(name):
        """Do what the entry `name` does: open it, flip it, take the step.
        False when there is no such entry, it only folds out, or it failed."""
        e = _urm_offers().entries.get(name)
        if e is None or e.action is None:
            return False
        try:
            e.action()
        except _urm_control_exceptions():
            raise
        except Exception as error:
            print("MRM: %s failed (%s)" % (name, error))
            return False
        renpy.restart_interaction()
        return True

    # --- what shows a value: one feature registers it (the variable sheet),
    # any other asks through here (the corner card's chips, the user's 4a)
    # and never names that feature.

    def _urm_value_viewer_add(open):
        """open(name, beside): show the value `name` (an expression the
        read-only evaluator reads); beside: (left, right) of what asked, in
        pixels, or None."""
        _urm_offers().viewer = open

    def _urm_value_viewable():
        """Whether anything can show a value."""
        return getattr(_urm_offers(), "viewer", None) is not None

    def _urm_value_view(name, beside=None):
        """Show the value `name` beside (left, right). False when nothing
        can show values or showing it failed (said once in the log)."""
        open = getattr(_urm_offers(), "viewer", None)
        if open is None:
            return False
        try:
            open(name, beside)
        except Exception as error:
            _urm_offer_failed("value viewer", name, error)
            return False
        renpy.restart_interaction()
        return True

    # One feature owns native scene playback. Other entry points ask for an
    # offer for an indexed label and open the captured offer on demand.
    def _urm_replay_add(offer, open):
        _urm_offers().replay = (offer, open)

    def _urm_replay_offer(label, cue):
        replay = getattr(_urm_offers(), "replay", None)
        return replay[0](label, cue) if replay is not None else None

    def _urm_replay_open(offer):
        replay = getattr(_urm_offers(), "replay", None)
        if replay is not None:
            replay[1](offer)

    def _urm_keys():
        """[(key, entry name)] of every entry that has a key, read from the
        registrations alone: nothing of a feature's is called."""
        return sorted((e.key, e.name) for e in _urm_offers().entries.values() if e.key)

    def _urm_status_add(name, status, order=50):
        """What the URM+ button says, named `name` (unique). status():
        None while there is nothing to say, else (tone, icon, count, tip,
        head, hide):
        tone: 'warn' turns the button yellow, 'gain' green, anything else
        leaves it blue; icon: a glyph of the kit's icon font, the picture
        of the badge on the button's corner and of the menu's head;
        count: words the badge shows instead of the picture ("14"), or
        None; tip: the few words pointing at the button shows; head: the
        words atop the menu (the tip under them), or None for no head;
        hide: (words, what it does) for a button in the head, or None.
        The first that says something, by order then name, is drawn."""
        _urm_offers().statuses[name] = _URMOffer(name=name, status=status, order=order)

    def _urm_status():
        """What the button says now, or None: .tone .icon .count .tip
        .head .hide_words .hide. Every feature's function is called here,
        each time the button is drawn, and nothing of it is kept: what a
        feature says changes with the line on screen. Inside try/except:
        one that fails is left out (said in the log once)."""
        found = sorted(_urm_offers().statuses.values(), key=lambda s: (s.order, s.name))
        for s in found:
            try:
                said = s.status()
                if said is None:
                    continue
                tone, icon, count, tip, head, hide = said
                hide_words, hide = hide if hide is not None else (None, None)
            except Exception as error:
                _urm_offer_failed("button status", s.name, error)
                continue
            return _URMOffer(name=s.name, tone=tone, icon=icon, count=count, tip=tip, head=head,
                             hide_words=hide_words, hide=hide)
        return None

    def _urm_under_add(name, screen, shown, height, order=50):
        """A part a feature hangs under the URM+ button (above it while the
        button is in the bottom half), drawn with the button so it moves
        with it (Quick access's tray). screen: its screen's name, used with
        no arguments; shown(): true while it shows; height(): its height
        in pixels."""
        _urm_offers().under[name] = _URMOffer(name=name, screen=screen, shown=shown,
                                             height=height, order=order)

    def _urm_under():
        """The parts under the button that show now, in their order: each
        .screen and .height. Inside try/except: one that fails is left out
        (said in the log once)."""
        out = python_list()
        found = sorted(getattr(_urm_offers(), "under", python_dict()).values(),
                       key=lambda u: (u.order, u.name))
        for u in found:
            try:
                if not u.shown():
                    continue
                out.append(_URMOffer(name=u.name, screen=u.screen, height=int(u.height())))
            except Exception as error:
                _urm_offer_failed("part under the button", u.name, error)
        return out

    def _urm_player_text_add(fn):
        _urm_offers().player_text = fn

    def _urm_player_text(text):
        fn = getattr(_urm_offers(), "player_text", None)
        return fn(text) if fn is not None else text

    def _urm_section_add(name, words, icon, order=50, screen=None, on_open=None, badge=None):
        """A section of Settings, with registered rows or its own content."""
        _urm_offers().sections[name] = _URMOffer(name=name, words=words, icon=icon,
                                               order=order, screen=screen, on_open=on_open, badge=badge)

    def _urm_section_screen(name):
        section = _urm_offers().sections.get(name)
        return section.screen if section is not None else None

    def _urm_section_badge(name):
        section = _urm_offers().sections.get(name)
        return section.badge() if section is not None and section.badge is not None else None

    def _urm_section_open(name):
        section = _urm_offers().sections.get(name)
        if section is not None and section.on_open is not None:
            section.on_open()

    def _urm_sections():
        """The sections that hold at least one row, in their order. A row
        in a section nobody registered is never shown: said in the log."""
        offers = _urm_offers()
        held = python_set(r.section for r in offers.rows.values())
        for r in offers.rows.values():
            if r.section not in offers.sections:
                _urm_offer_failed("settings row", r.name, "no section %s" % (r.section,))
        return sorted((s for s in offers.sections.values() if s.name in held or s.screen),
                      key=lambda s: (s.order, s.name))

    def _urm_row_add(name, section, words, about, options, setting=None, get=None, put=None,
                     order=50, percent=False):
        """A row of the URM+ settings page, named `name` (unique), in
        `section`. words: its title; about: one plain sentence under it.
        options: a tuple of (words, value) in the order shown, or a
        function that gives them when the page opens.
        setting: the name of a setting of ours (_urm_setting_add): the row
        shows its two levels, this game (which can be cleared) and all
        games. Or get() and put(value): a value the engine keeps for this
        game alone; the row shows only this game. percent: use a 0-100
        slider in place of the choices."""
        _urm_offers().rows[name] = _URMOffer(
            name=name, section=section, words=words, about=about, options=options,
            setting=setting, get=get, put=put, order=order, percent=percent)

    def _urm_rows(section):
        """The rows of a section, in their order."""
        return sorted((r for r in _urm_offers().rows.values() if r.section == section),
                      key=lambda r: (r.order, r.name))

    def _urm_row_view(name):
        """What a row shows now, or None when it cannot be worked out:
        .options [(words, value)]; .game_only; .game this game's value
        (None: this game keeps none); .shared the all-games value, or the
        default (None for a game-only row); .value the one in effect;
        .own: this game keeps its own value, so all games' does not count
        here."""
        r = _urm_offers().rows.get(name)
        if r is None:
            return None
        try:
            options = r.options() if callable(r.options) else r.options
            options = python_list((words, value) for words, value in options)
            if r.setting is None:
                game = r.get()
                return _URMOffer(name=name, options=options, percent=r.percent, game_only=True, game=game,
                                 shared=None, value=game, own=True)
            game = _urm_setting_at(r.setting, False)
            shared = _urm_setting_at(r.setting, True)
            return _URMOffer(name=name, options=options, percent=r.percent, game_only=False, game=game,
                             shared=shared, value=game if game is not None else shared,
                             own=game is not None)
        except Exception as error:
            _urm_offer_failed("settings row", name, error)
            return None

    def _urm_row_pick(name, value, all_games=False):
        """The player picked `value` on a row: at all games' level, or this
        game's. A game-only row has this game alone."""
        r = _urm_offers().rows[name]
        if r.setting is None:
            r.put(value)
            renpy.restart_interaction()
        else:
            _urm_setting_set(r.setting, value, all_games)

    def _urm_row_clear(name):
        """This game keeps no value of its own for the row any more: all
        games' counts again."""
        r = _urm_offers().rows[name]
        if r.setting is not None:
            _urm_setting_set(r.setting, None)
