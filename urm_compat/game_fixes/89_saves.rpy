# ---------------------------------------------------------------------------
# Our own save page: a band across the bottom (the user's pick c2)
# ---------------------------------------------------------------------------
#
# The page is a view on the engine's own saves: every step is one of
# Ren'Py's own calls (renpy.save, renpy.load, renpy.unlink_save,
# renpy.copy_save, renpy.rename_save, the page names through
# FilePageNameInputValue, the page through FilePage), on the engine's own
# slot names ("2-5", "auto-1", "quick-1", "_reload-1"). Nothing here writes
# or extends a save file, so a save made here is an ordinary game save and
# the game's own save screen shows it, and the other way round. The game's
# own Save and Load buttons are left alone (the user's 2a).
#
# Two switches at the top: Save | Load (what a click on a save does) and
# Timeline | Pages. Timeline: every save in time order, grouped by day;
# saves on a page are cards, auto saves rings and quick saves diamonds on
# the line; "Earlier" steps back. Pages: the engine's page strip and the
# page's slots, as many as the game's own save screen shows (its
# gui.file_slot_cols x gui.file_slot_rows), so every save made here shows
# there too; a save is dragged onto a slot or a page to move it
# (Ctrl held: copied). On either view a save's bubble can pick it up to
# move or copy it with clicks instead. Right: the quick resume save
# ("_reload-1"), which the engine loads as the game next starts.
#
# A save made here is the save the game's own Save makes: with no name
# typed it takes the game's own save_name, and it is made only where the
# game's own FileSave would save (not in a replay, not on the Auto page).
#
# The quick resume save. Ren'Py 7.3 and 7.4 load "_reload-1" at every
# start, renaming it away first; from 7.5 the engine loads only the save
# its own reload named in renpy.session (00keymap.rpy, _load_reload_game),
# so a resume save set here did nothing there. On such an engine the save
# is renamed as the game starts (a start callback, which runs before that
# step) and its new name put in renpy.session: the engine's
# own step loads it, and a save that fails to load is not tried again at
# the next start (FINDINGS.md).
#
# The thumbnail. The engine saves the screenshot it took last. The page
# opens empty for one frame, so the picture taken then shows the game, not
# the menu the page was opened from, and is kept for every save made while
# the page is open.
#
# Four settings with URM's meanings: a name is asked for each save; Alt+Q
# sets the quick resume save, Alt+S quick saves, Alt+L quick loads, each
# off until switched on (off, Alt+S stays the engine's screenshot). They
# are ours under the names URM gives its own four (askSaveName,
# quickResumeSaveHotKey, quickSaveHotKey, quickLoadHotKey), on purpose:
# the doorway (01_urm_door) then copies URM's values once at each level,
# and answers URM's own reads of them from our store, so URM's keys and
# options page, while URM is there, follow the one switch (one press does
# one thing; off is off).
#
# Ways in: the URM+ menu's Save and Load, and URM's quick bar Save and
# Load buttons while URM is there (a hook in ui_tweaks.py; the user's 1b).

init 999 python:

    import time as _urmsv_time

    URMSV_RESUME = "_reload-1"         # the engine's own resume save
    URMSV_RESUME_TRIED = "_reload-3"   # offered once, on an engine that reads its session
    _URMSV_RE = r"^(\d+|auto|quick)-\d+$"

    class _URMSVState(python_object):
        def __init__(self):
            self.mode = "load"          # "save" or "load": what a click on a save does
            self.view = "timeline"      # "timeline" or "pages"
            self.pill = "all"           # timeline: "all", "auto", "quick" or a page number
            self.back = python_list()   # timeline: how many newer saves each Earlier hid
            self.rows = None            # the saves, read when the page opens or changes
            self.focus = None           # the save whose bubble shows
            self.leaving = False        # the pointer left it: the bubble goes soon
            self.ask = None             # (words, about, yes words, what yes does)
            self.naming = None          # the slot a name is asked for
            self.name_text = u""
            self.carry = None           # (slot, True to copy): picked up to move
            self.gen = 0                # drags are made new after a drop
            self.gear = False           # the settings bubble shows
            self.shot = False           # the picture for the saves is taken
            self.editing = None         # "page" (its name) or "goto" (a page number)
            self.goto_text = u""
            self.note = None            # one line said after a step ("Page 4 is full")
            self.xs = python_dict()     # timeline: the middle of each save shown, in the band
            self.shown = 0              # timeline: how many saves it shows
            self.area = None            # pages: the width the slots share
            self.pill_from = 0          # timeline: the first page pill shown

    def _urmsv_state():
        return _urm_kept("saves", _URMSVState)

    # ---- the settings (see the top: URM's names, on purpose)

    URMSV_SETTINGS = (("askSaveName", True), ("quickResumeSaveHotKey", False),
                      ("quickSaveHotKey", False), ("quickLoadHotKey", False))
    for _urmsv_n, _urmsv_d in URMSV_SETTINGS:
        _urm_setting_add(_urmsv_n, _urmsv_d)

    # ---- the quick resume save, offered once (see the top)

    def _urmsv_engine_reads_session():
        """Does this engine's own resume step load the save its session
        names (7.5 on), rather than "_reload-1" itself?"""
        node = renpy.game.script.lookup("_load_reload_game")
        while node is not None and not isinstance(node, renpy.ast.If):
            node = (node.block[0] if getattr(node, "block", None) else None) \
                if isinstance(node, renpy.ast.Label) else getattr(node, "next", None)
        return node is not None and any("_reload_slot" in cond for cond, _block in node.entries)

    def _urmsv_starting():
        """A real start of the game: not the restart that Main Menu or the
        story's end makes (the engine's own auto load asks the same:
        `not _restart`, 00start.rpy), and not a replay; both pass through
        the engine's start step and its start callbacks too."""
        return not getattr(store, "_restart", None) and not getattr(store, "_in_replay", None)

    def _urmsv_offer_resume():
        """As the game starts, before the engine's own resume step (a start
        callback: the save folders are read by then on every engine)."""
        try:
            if (_urmsv_starting() and renpy.can_load(URMSV_RESUME)
                    and not renpy.session.get("_reload_slot") and _urmsv_engine_reads_session()):
                renpy.rename_save(URMSV_RESUME, URMSV_RESUME_TRIED)
                renpy.loadsave.location.scan()
                renpy.session["_reload_slot"] = URMSV_RESUME_TRIED
        except Exception as error:
            print("MRM: the resume save is not offered to the engine (%s)" % (error,))

    if _urmsv_offer_resume not in config.start_callbacks:
        config.start_callbacks.append(_urmsv_offer_resume)

    # ---- what the page shows: the saves, as plain rows

    class _URMSVSave(python_object):
        """One save: its slot, page ("2", "auto", "quick"), place on the
        page, kind ("page", "auto", "quick"), name and when it was made."""

        def __init__(self, slot):
            self.slot = slot
            page, n = slot.rsplit("-", 1)
            self.page, self.n = page, int(n)
            self.kind = page if page in ("auto", "quick") else "page"
            json = renpy.slot_json(slot) or python_dict()
            self.name = (json.get("_save_name") or u"").strip()
            # When it was made: the engine's own record where it keeps one
            # (7.5 on), else the file's time (a copy is new then).
            self.when = json.get("_ctime") or renpy.slot_mtime(slot) or 0

    def _urmsv_rows():
        """The saves on the page, oldest first, read once per change."""

        st = _urmsv_state()
        if st.rows is None:
            found = python_list()
            for slot in renpy.list_slots(_URMSV_RE):
                try:
                    found.append(_URMSVSave(slot))
                except Exception as error:
                    print("MRM: save %s left out (%s)" % (slot, error))
            found.sort(key=lambda r: (r.when, r.slot))
            st.rows = found
        return st.rows

    def _urmsv_changed():
        # The engine lists saves from what it last read of each save folder.
        # Where two of its folders are one (a game with no save_directory,
        # 7.3), a save moved by one is still listed by the other until the
        # engine's own scan comes round: read them again now, as that scan
        # does (FINDINGS.md).
        try:
            renpy.loadsave.location.scan()
        except Exception as error:
            print("MRM: the save folders were not read again (%s)" % (error,))
        st = _urmsv_state()
        st.rows = None
        st.focus = None
        st.gen += 1
        renpy.restart_interaction()

    def _urmsv_row(slot):
        for r in _urmsv_rows():
            if r.slot == slot:
                return r
        return None

    def urmsv_newest():
        rows = _urmsv_rows()
        return rows[-1] if rows else None

    def _urmsv_day(when):
        now = _urmsv_time.localtime()
        then = _urmsv_time.localtime(when)
        days = (_urmsv_time.mktime(now[:3] + (0, 0, 0, 0, 0, -1))
                - _urmsv_time.mktime(then[:3] + (0, 0, 0, 0, 0, -1)))
        days = int(round(days / 86400.0))
        if days == 0:
            return u"Today"
        if days == 1:
            return u"Yesterday"
        return u"%s %d" % (_urmsv_time.strftime("%b", then), then.tm_mday)

    def urmsv_clock(when):
        return _urmsv_time.strftime("%H:%M", _urmsv_time.localtime(when))

    def urmsv_when(r):
        """'Today 14:05', 'Nov 18 21:40'."""
        return u"%s %s" % (_urmsv_day(r.when), urmsv_clock(r.when))

    def urmsv_page_name(page):
        """A page as the player named it, through the engine's own page
        names (a name given in URM's save tab is the same name)."""
        if page == "auto":
            return u"Auto"
        if page == "quick":
            return u"Quick"
        try:
            return FilePageNameInputValue(page=int(page)).get_text()
        except Exception:
            return u"Page %s" % (page,)

    def urmsv_title(r):
        """What a save is called: its name, else what it is."""
        if r.name:
            return r.name
        if r.kind == "auto":
            return u"Auto save"
        if r.kind == "quick":
            return u"Quick save"
        return u"Page %s, slot %d" % (r.page, r.n)

    def urmsv_place(r):
        """Where a save sits: 'P2\u00b75', 'Auto', 'Quick'."""
        if r.kind != "page":
            return u"Auto" if r.kind == "auto" else u"Quick"
        return u"P%s\u00b7%d" % (r.page, r.n)

    # ---- the timeline

    URMSV_CARD = 184                    # a card's width (at 1080 lines), as drawn
    URMSV_CARD_GAP = 20
    URMSV_DOT = 56
    URMSV_DAY = 32
    URMSV_SAVE_NOW = 244                # the Save now slot and its gap

    def urmsv_pills():
        """The timeline's filter: (words, count, key), All first."""
        rows = _urmsv_rows()
        out = python_list([(u"All", None, "all")])
        for kind, words in (("quick", u"Quick"), ("auto", u"Auto")):
            out.append((words, sum(1 for r in rows if r.kind == kind), kind))
        used = python_dict()
        for r in rows:
            if r.kind == "page" and r.page.isdigit():
                used[int(r.page)] = used.get(int(r.page), 0) + 1
        last = max(list(used.keys()) + [0])
        for p in range(1, max(last, 3) + 3):
            out.append((urmsv_page_name(p), used.get(p, 0), p))
        return out

    def _urmsv_shown_rows():
        st = _urmsv_state()
        rows = _urmsv_rows()
        if st.pill == "all":
            return rows
        if st.pill in ("auto", "quick"):
            return [r for r in rows if r.kind == st.pill]
        return [r for r in rows if r.kind == "page" and r.page == str(st.pill)]

    def urmsv_timeline(width):
        """What the timeline draws in `width` pixels, newest at the right:
        (items, earlier, later). Each item is (kind, x, what): 'card' and
        'dot' with their save, 'day' with its words; x in pixels."""

        st = _urmsv_state()
        rows = _urmsv_shown_rows()
        hidden = sum(st.back)
        end = len(rows) - hidden
        right = width - (urmk_px(URMSV_SAVE_NOW) if st.mode == "save" and st.pill == "all" else 0)
        x = right
        items = python_list()
        st.xs = python_dict()
        day = None
        i = end - 1
        shown = 0
        left = urmk_px(24)
        while i >= 0:
            r = rows[i]
            w = urmk_px(URMSV_CARD + URMSV_CARD_GAP) if r.kind == "page" else urmk_px(URMSV_DOT)
            this_day = _urmsv_day(r.when)
            need = w + (urmk_px(URMSV_DAY) if day is not None and this_day != day else 0)
            if x - need < left and shown:
                break
            if day is not None and this_day != day:
                x -= urmk_px(URMSV_DAY) // 2
                items.append(("day", x, day))
                x -= urmk_px(URMSV_DAY) // 2
            day = this_day
            x -= w
            items.append(("card" if r.kind == "page" else "dot", x, r))
            st.xs[r.slot] = x + w // 2 - (urmk_px(URMSV_CARD_GAP) // 2 if r.kind == "page" else 0)
            shown += 1
            i -= 1
        if day is not None:
            items.append(("day", max(x - urmk_px(URMSV_DAY) // 2, 0), day))
        st.shown = shown
        return items, i >= 0, bool(st.back)

    def urmsv_earlier():
        st = _urmsv_state()
        st.back.append(max(1, st.shown - 1))
        st.focus = None
        renpy.restart_interaction()

    def urmsv_later():
        st = _urmsv_state()
        if st.back:
            st.back.pop()
        st.focus = None
        renpy.restart_interaction()

    # ---- pages

    def urmsv_page():
        """The page shown: the engine's own current page."""
        page = persistent._file_page
        return str(page) if page is not None else "1"

    def urmsv_go(page):
        """Show another page: the engine's own FilePage, so the game's own
        save screen opens on it too."""
        renpy.run(FilePage(page))
        st = _urmsv_state()
        st.editing = None
        st.focus = None
        renpy.restart_interaction()

    def urmsv_page_strip():
        """The pages around the one shown, as the engine pages them."""
        page = urmsv_page()
        if not page.isdigit():
            return python_list(range(1, 8))
        n = int(page)
        first = max(1, n - 3)
        return python_list(range(first, first + 7))

    def urmsv_grid():
        """(columns, rows) of a page, as the game's own save screen lays
        it out (Ren'Py's template: 3 x 2); 3 x 3 for a game that keeps no
        such size."""
        try:
            cols, rows = int(gui.file_slot_cols), int(gui.file_slot_rows)
            if 0 < cols <= 6 and 0 < rows <= 6:
                return cols, rows
        except Exception:
            pass
        return 3, 3

    def urmsv_per_page():
        cols, rows = urmsv_grid()
        return cols * rows

    def urmsv_slots():
        """The shown page's slots: (n, its save or None)."""
        page = urmsv_page()
        held = python_dict((r.n, r) for r in _urmsv_rows() if r.page == page)
        return [(n, held.get(n)) for n in range(1, urmsv_per_page() + 1)]

    def _urmsv_next_slot():
        """Where Save now saves: after the last save on the shown page, or
        on the next page with room after it."""
        page = urmsv_page()
        page = int(page) if page.isdigit() else 1
        rows = _urmsv_rows()
        while True:
            used = [r.n for r in rows if r.page == str(page)]
            after = max(used + [0]) + 1
            if after <= urmsv_per_page():
                return "%d-%d" % (page, after)
            page += 1

    def urmsv_next_words():
        page, n = _urmsv_next_slot().split("-")
        return u"to %s \u00b7 slot %s" % (urmsv_page_name(page), n)

    def _urmsv_first_free(page):
        held = python_set(r.n for r in _urmsv_rows() if r.page == str(page))
        for n in range(1, urmsv_per_page() + 1):
            if n not in held:
                return "%s-%d" % (page, n)
        return None

    # ---- opening and closing

    def urmsv_open(mode="load"):
        """Open the page in Save or Load mode. On the main menu there is
        nothing to save: it opens in Load."""
        st = _urmsv_state()
        st.mode = "load" if (mode != "save" or urmsv_no_game()) else "save"
        st.rows = None
        st.focus = st.ask = st.naming = st.carry = st.editing = st.note = None
        st.gear = False
        st.back = python_list()
        st.shot = urmsv_no_game()
        renpy.show_screen("urmsv_page", _layer="screens")
        renpy.restart_interaction()

    def urmsv_shoot():
        """The first frame of the page drew nothing: the game's picture."""
        st = _urmsv_state()
        if not st.shot:
            st.shot = True
            try:
                renpy.take_screenshot()
            except Exception as error:
                print("MRM: no picture for the saves (%s)" % (error,))
            renpy.restart_interaction()

    def urmsv_close():
        st = _urmsv_state()
        st.rows = None
        renpy.hide_screen("urmsv_page", layer="screens")
        renpy.restart_interaction()

    def urmsv_escape():
        """Esc: the step under way stops, else the page closes."""
        st = _urmsv_state()
        if st.ask or st.naming or st.editing:
            st.ask = st.naming = st.editing = None
        elif st.carry:
            st.carry = None
        elif st.gear:
            st.gear = False
        else:
            urmsv_close()
            return
        renpy.restart_interaction()

    def urmsv_can_save(slot="1-1"):
        """Would the game's own FileSave save into `slot` now? Not on the
        main menu, in a replay, on the Auto page, or wherever the game
        says not."""
        page, n = slot.rsplit("-", 1)
        try:
            return bool(renpy.is_sensitive(FileSave(int(n), page=page, confirm=False)))
        except Exception:
            return False

    def urmsv_no_game():
        """Nothing can be saved now: Save mode is not offered."""
        return not urmsv_can_save("1-1")

    def urmsv_set_mode(mode):
        st = _urmsv_state()
        if mode == "save" and urmsv_no_game():
            return
        st.mode = mode
        st.focus = None
        renpy.restart_interaction()

    def urmsv_set_view(view):
        st = _urmsv_state()
        st.view = view
        st.focus = None
        st.editing = None
        renpy.restart_interaction()

    def urmsv_set_pill(key):
        st = _urmsv_state()
        st.pill = key
        st.back = python_list()
        st.focus = None
        renpy.restart_interaction()

    # ---- the bubble of the save pointed at

    def urmsv_hover(slot):
        st = _urmsv_state()
        if st.focus != slot or st.leaving:
            st.focus, st.leaving = slot, False
            renpy.restart_interaction()

    def urmsv_unhover(slot=None):
        st = _urmsv_state()
        if st.focus is not None and (slot is None or slot == st.focus):
            st.leaving = True
            renpy.restart_interaction()

    def urmsv_bubble_kept():
        st = _urmsv_state()
        st.leaving = False

    def urmsv_bubble_gone():
        st = _urmsv_state()
        if st.leaving:
            st.focus, st.leaving = None, False
            renpy.restart_interaction()

    # ---- what a click does: each through the engine's own calls

    def _urmsv_ask(words, about, yes, fn, *args):
        _urmsv_state().ask = (words, about, yes, (fn, args))
        renpy.restart_interaction()

    def urmsv_yes():
        st = _urmsv_state()
        ask, st.ask = st.ask, None
        if ask:
            fn, args = ask[3]
            fn(*args)
        renpy.restart_interaction()

    def urmsv_no():
        _urmsv_state().ask = None
        renpy.restart_interaction()

    def _urmsv_quote(r):
        return u"\u201c%s\u201d" % urmsv_title(r)

    def urmsv_click(slot):
        """A save, or an empty slot, was clicked."""
        st = _urmsv_state()
        if st.carry:
            urmsv_put(slot)
            return
        r = _urmsv_row(slot)
        if st.mode == "load":
            if r is not None:
                _urmsv_ask(u"Load %s?" % _urmsv_quote(r), u"What you have not saved is lost.",
                           u"Load", _urmsv_load, slot)
            return
        if not urmsv_can_save(slot):
            st.note = u"The game does not save there now"
            renpy.restart_interaction()
            return
        if r is not None:
            _urmsv_ask(u"Save over %s?" % _urmsv_quote(r), u"The old save is replaced by this moment.",
                       u"Save over", _urmsv_save_named, slot, r.name)
        else:
            _urmsv_save_named(slot, u"")

    def urmsv_save_now():
        urmsv_click(_urmsv_next_slot())

    def _urmsv_save_named(slot, name):
        """Save, asking for a name first when the setting says so."""
        st = _urmsv_state()
        if _urm_setting("askSaveName"):
            st.naming, st.name_text = slot, name or u""
            renpy.restart_interaction()
        else:
            _urmsv_save(slot, name)

    def urmsv_name_done():
        st = _urmsv_state()
        slot, st.naming = st.naming, None
        if slot:
            _urmsv_save(slot, st.name_text.strip())

    def _urmsv_save(slot, name):
        """Save as the game's own FileSave does: no name typed, the game's
        own save_name."""
        if not urmsv_can_save(slot):
            return
        renpy.save(slot, name or getattr(store, "save_name", u"") or u"")
        _urmsv_state().note = None
        _urmsv_changed()

    def _urmsv_load(slot):
        renpy.load(slot)

    def urmsv_delete(slot):
        r = _urmsv_row(slot)
        if r is not None:
            _urmsv_ask(u"Delete %s?" % _urmsv_quote(r), u"A deleted save cannot be brought back.",
                       u"Delete", _urmsv_unlink, slot)

    def _urmsv_unlink(slot):
        renpy.unlink_save(slot)
        _urmsv_changed()

    # ---- moving and copying: drag on Pages, or pick up and click

    def urmsv_pick_up(slot, copy=False):
        st = _urmsv_state()
        st.carry = (slot, bool(copy))
        st.view = "pages"
        st.focus = None
        st.note = None
        renpy.restart_interaction()

    def urmsv_carry_words():
        st = _urmsv_state()
        r = _urmsv_row(st.carry[0]) if st.carry else None
        if r is None:
            return None
        return u"%s %s: click a slot, or a page and then a slot \u00b7 Esc stops" % (
            u"Copying" if st.carry[1] else u"Moving", _urmsv_quote(r))

    def urmsv_put(dest):
        """The picked-up save goes to `dest` (a slot), asking first when a
        save is there."""
        st = _urmsv_state()
        if not st.carry:
            return
        source, copy = st.carry
        _urmsv_place(source, dest, copy)

    def _urmsv_place(source, dest, copy):
        st = _urmsv_state()
        r = _urmsv_row(source)
        if r is None or source == dest:
            st.carry = None
            renpy.restart_interaction()
            return
        if dest.rsplit("-", 1)[0] in ("auto", "quick"):
            st.note = u"The Auto and Quick pages are the game's own"
            st.carry = None
            _urmsv_changed()
            return
        there = _urmsv_row(dest)
        if there is not None:
            _urmsv_ask(u"Replace %s?" % _urmsv_quote(there),
                       u"%s takes its place; the save there is lost." % _urmsv_quote(r),
                       u"Replace", _urmsv_move, source, dest, copy)
        else:
            _urmsv_move(source, dest, copy)

    def _urmsv_move(source, dest, copy):
        if copy:
            renpy.copy_save(source, dest)
        else:
            renpy.rename_save(source, dest)
        _urmsv_state().carry = None
        _urmsv_changed()

    def _urmsv_ctrl():
        try:
            import pygame_sdl2 as pygame
        except ImportError:
            import pygame
        try:
            return bool(pygame.key.get_mods() & pygame.KMOD_CTRL)
        except Exception:
            return False

    def urmsv_dropped(drop, drags):
        """A save dragged on Pages was dropped on a slot or a page."""
        if drop is None or not drags:
            _urmsv_changed()
            return
        # drag names: "urmsv<gen>|slot|2-5", "urmsv<gen>|page|3"
        source = drags[0].drag_name.split("|")[2]
        what, target = drop.drag_name.split("|")[1:3]
        copy = _urmsv_ctrl()
        if what == "slot":
            _urmsv_place(source, target, copy)
        elif what == "page":
            dest = _urmsv_first_free(target)
            if dest is None:
                _urmsv_state().note = u"%s is full" % urmsv_page_name(target)
                _urmsv_changed()
            else:
                _urmsv_place(source, dest, copy)
        _urmsv_state().gen += 1
        renpy.restart_interaction()

    def urmsv_drag_name(*parts):
        return "|".join(["urmsv%d" % _urmsv_state().gen] + [str(p) for p in parts])

    # ---- the page's name and Go to page

    def urmsv_edit(what):
        st = _urmsv_state()
        st.editing = what
        st.goto_text = u""
        renpy.restart_interaction()

    class _URMSVInput(InputValue):
        """The name box and the Go to page box: what they hold is ours."""

        default = True
        returnable = False

        def __init__(self, field):
            self.field = field

        def get_text(self):
            return getattr(_urmsv_state(), self.field)

        def set_text(self, text):
            if self.field == "goto_text":
                text = u"".join(c for c in text if c.isdigit())[:5]
            setattr(_urmsv_state(), self.field, text)
            renpy.restart_interaction()

        def enter(self):
            st = _urmsv_state()
            if self.field == "name_text":
                urmsv_name_done()
            elif st.goto_text.isdigit() and int(st.goto_text) > 0:
                if st.view == "pages":
                    urmsv_go(int(st.goto_text))
                else:
                    urmsv_set_pill(int(st.goto_text))
                st.editing = None
            raise renpy.IgnoreEvent()

    urmsv_name_box = _URMSVInput("name_text")
    urmsv_goto_box = _URMSVInput("goto_text")

    # ---- the quick resume save

    def urmsv_resume():
        """When the resume save was made, or None."""
        if not renpy.can_load(URMSV_RESUME):
            return None
        json = renpy.slot_json(URMSV_RESUME) or python_dict()
        return json.get("_ctime") or renpy.slot_mtime(URMSV_RESUME)

    def urmsv_resume_set(notify=False):
        """Save this moment as the resume save; the next start loads it."""
        renpy.save(URMSV_RESUME, u"")
        if notify:
            renpy.notify(u"Quick resume saved")
        _urmsv_changed()

    def urmsv_resume_clear():
        _urmsv_ask(u"Clear the resume save?", u"The next start opens on the title screen again.",
                   u"Clear", _urmsv_resume_unlink)

    def _urmsv_resume_unlink():
        renpy.unlink_save(URMSV_RESUME)
        _urmsv_changed()

    # ---- the settings bubble and the URM+ settings page

    URMSV_SETTING_WORDS = (
        ("askSaveName", u"Name each save", u"Ask for a name when saving here"),
        ("quickResumeSaveHotKey", u"Alt+Q", u"Set the resume save"),
        ("quickSaveHotKey", u"Alt+S", u"Quick save (off: Ren'Py's screenshot)"),
        ("quickLoadHotKey", u"Alt+L", u"Quick load"))

    def urmsv_flip(name):
        """A switch of the settings bubble: the value in effect flips, for
        all games (this game's own value, if it kept one, goes)."""
        value = not _urm_setting(name)
        _urm_setting_set(name, None)
        _urm_setting_set(name, value, True)

    for _urmsv_n, _urmsv_w, _urmsv_a in URMSV_SETTING_WORDS:
        _urm_row_add(_urmsv_n, "game", _urmsv_w if _urmsv_n == "askSaveName" else u"%s: %s" % (_urmsv_w, _urmsv_a.lower()),
                     _urmsv_a + u".", ((u"On", True), (u"Off", False)), setting=_urmsv_n, order=60)

    # ---- for the screens: words, places and pictures

    def urmsv_state_now():
        return _urmsv_state()

    def urmsv_hint():
        """What a click does now, or the step under way."""
        st = _urmsv_state()
        if st.carry:
            return urmsv_carry_words()
        if st.note:
            return st.note
        if st.mode == "load":
            words = u"Click a save to load it"
        elif st.view == "pages":
            words = u"Click a slot to save there, or a save to write over it"
        else:
            words = u"Click Save now, or a save to write over it"
        if st.view == "pages":
            words += u" \u00b7 drag a save onto a slot or a page to move it, Ctrl copies"
        return words

    def urmsv_hint_tone():
        st = _urmsv_state()
        return "ink" if st.carry else ("warn-on-glass" if st.note else "ink-muted")

    def urmsv_fit(words, style_name, width):
        """The words, cut with an ellipsis to fit `width` pixels."""
        if width <= 0 or urmsv_text_w(words, style_name) <= width:
            return words
        lo, hi = 0, len(words)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if urmsv_text_w(words[:mid].rstrip() + u"\u2026", style_name) <= width:
                lo = mid
            else:
                hi = mid - 1
        return words[:lo].rstrip() + u"\u2026"

    def urmsv_header_words():
        """(what a click does, where the player was last), each fitted to
        the room the top row leaves, the second given up first."""
        room = config.screen_width - urmk_px(32) - urmk_px(32 + 24) - urmk_px(220 + 2 * 48 + 2 * 8) - urmk_px(150 + 16)
        hint = urmsv_hint()
        n = urmsv_newest()
        last = urmsv_title(n) if n is not None else u""
        hint_w = urmsv_text_w(hint, "urmk_s")
        fixed = (urmsv_text_w(u"You were last at", "urmk_s") + urmsv_text_w(u"\u00b7 " + urmsv_when(n), "urmk_s")
                 + urmk_px(2 + 4 * 16)) if n is not None else 0
        last_w = urmsv_text_w(last, "urmk_m_medium") if last else 0
        if hint_w + urmk_px(16) + fixed + last_w <= room:
            return hint, last
        if last and hint_w + urmk_px(16) + fixed + urmk_px(120) <= room:
            return hint, urmsv_fit(last, "urmk_m_medium", room - hint_w - urmk_px(16) - fixed)
        return urmsv_fit(hint, "urmk_s", room), None

    def urmsv_pills_shown(area):
        """The timeline's pills that fit beside Go to page and the legend:
        All, Quick and Auto always, the pages from st.pill_from; and
        whether more pages follow."""
        st = _urmsv_state()
        pills = urmsv_pills()
        head, pages = pills[:3], pills[3:]
        st.pill_from = max(0, min(st.pill_from, len(pages) - 1))
        room = area - urmk_px(32) - urmk_px(300) - urmk_px(190) - urmk_px(2 * 48)
        used = sum(urmsv_text_w(w, "urmk_s_medium") + urmk_px(32 + 8) + (urmk_px(28) if c is not None else 0)
                   for w, c, k in head) + urmk_px(18)
        shown = python_list(head)
        rest = pages[st.pill_from:]
        for w, c, k in rest:
            need = urmsv_text_w(w, "urmk_s_medium") + urmk_px(32 + 8 + 28)
            if used + need > room and len(shown) > 3:
                break
            used += need
            shown.append((w, c, k))
        return shown, len(shown) - 3 < len(rest)

    def urmsv_pills_step(step):
        st = _urmsv_state()
        st.pill_from = max(0, st.pill_from + step)
        renpy.restart_interaction()

    def urmsv_at1080(px):
        """Pixels on this screen, as the kit's sizes at 1080 lines."""
        return px * 1080.0 / config.screen_height

    def urmsv_above(top):
        """A kit window's y (bottom aligned) that puts it just above `top`."""
        return -urmsv_at1080(config.screen_height - top + urmk_px(12))

    def urmsv_caret():
        """The field's caret: our ink, 2 pixels wide."""
        return Fixed(urmk_pill(urmk_colour("ink"), 0), xysize=(max(1, urmk_px(2)), urmk_px(28)))

    def urmsv_none_words():
        st = _urmsv_state()
        if st.pill == "all":
            return u"No saves yet"
        return u"No saves in %s" % (urmsv_page_name(st.pill) if st.pill not in ("auto", "quick")
                                    else (u"Auto" if st.pill == "auto" else u"Quick"))

    def urmsv_newest_card():
        """The newest save on a page (its card says Newest)."""
        for r in reversed(_urmsv_rows()):
            if r.kind == "page":
                return r
        return None

    def urmsv_day_clock(when):
        return u"%s %s" % (_urmsv_day(when), urmsv_clock(when))

    def urmsv_long_when(r):
        return _urmsv_time.strftime("%a, %b %d %Y, %H:%M", _urmsv_time.localtime(r.when))

    def urmsv_where(r):
        if r.kind != "page":
            return u"Auto save" if r.kind == "auto" else u"Quick save"
        return u"%s \u00b7 slot %d" % (urmsv_page_name(r.page), r.n)

    def urmsv_resume_slot():
        return URMSV_RESUME

    def urmsv_focus_row():
        st = _urmsv_state()
        if isinstance(st.focus, basestring if str is bytes else str):
            return _urmsv_row(st.focus)
        return None

    def urmsv_prev_page():
        page = urmsv_page()
        if page in ("auto", "quick"):
            return "auto"
        return "quick" if int(page) <= 1 else int(page) - 1

    def urmsv_next_page():
        page = urmsv_page()
        if page == "auto":
            return "quick"
        if page == "quick":
            return 1
        return int(page) + 1

    def urmsv_page_pill(key):
        """A page of the strip clicked: the shown page's own pill opens its
        name for editing; another shows that page."""
        if str(key) == urmsv_page() and str(key).isdigit() and not _urmsv_state().carry:
            urmsv_edit("page")
        else:
            urmsv_go(key)

    class _URMSVPageName(FilePageNameInputValue):
        """The engine's own page name input; Enter also closes the box."""

        def enter(self):
            _urmsv_state().editing = None
            renpy.restart_interaction()
            raise renpy.IgnoreEvent()

    def urmsv_page_box():
        return _URMSVPageName(page=int(urmsv_page()), default=True)

    def urmsv_text_w(words, style_name):
        return int(renpy.text.text.Text(words, style=style_name, substitute=False).size()[0])

    def urmsv_strip_layout(area):
        """The Pages strip after its two arrows: [(page, x, width, words,
        shown)] for Auto, Quick and seven numbered pages, as the engine
        pages them; x in pixels from the band's left."""
        page = urmsv_page()
        x = urmk_px(32 + 2 * 40 + 2 * 8)
        out = python_list()
        keys = python_list(["auto", "quick"]) + urmsv_page_strip()
        for key in keys:
            on = str(key) == page
            if key in ("auto", "quick"):
                words = u"Auto" if key == "auto" else u"Quick"
            else:
                name = urmsv_page_name(key)
                words = (u"%d \u00b7 %s" % (key, name)) if on and name != u"Page %d" % key else (u"%d" % key)
            w = urmsv_text_w(words, "urmk_s_medium") + urmk_px(32)
            if on and key not in ("auto", "quick"):
                w += urmk_px(8 + 20)
            out.append((key, x, w, words, on))
            x += w + urmk_px(8)
            if key == "quick":
                x += urmk_px(2 + 16)
        _urmsv_state().area = area
        return out

    def urmsv_tile_h():
        """A slot's height on Pages: 112 as drawn, less when the game's
        grid has more than three rows."""
        cols, rows = urmsv_grid()
        return min(urmk_px(112), (urmk_px(372) - (rows - 1) * urmk_px(12)) // rows)

    def urmsv_tile_box(n, area):
        """Where slot n sits on Pages: (x, y, width) in the band, in the
        game's own grid."""
        cols, rows = urmsv_grid()
        w = (area - urmk_px(32) - urmk_px(32) - (cols - 1) * urmk_px(16)) // cols
        return (urmk_px(32) + ((n - 1) % cols) * (w + urmk_px(16)),
                urmk_px(144) + ((n - 1) // cols) * (urmsv_tile_h() + urmk_px(12)), w)

    # The engine's own keys that move the story or open its menus, held
    # while the page is open (its keymap is below every screen, and a
    # modal screen lets keys reach it); only the ones this engine has.
    URMSV_HELD_KEYS = tuple(k for k in (
        "rollback", "rollforward", "skip", "toggle_skip", "fast_skip", "hide_windows",
        "dismiss", "dismiss_unfocused", "quicksave", "quickload", "self_voicing",
        "toggle_afm", "director", "accessibility", "help", "choose_renderer",
        "progress_screen", "console") if k in config.keymap)

    def urmsv_bubble_x(width):
        """The bubble's left: over the middle of the save pointed at, kept
        on the screen."""
        st = _urmsv_state()
        mid = config.screen_width // 2
        if st.view == "timeline":
            mid = urmk_px(16) + st.xs.get(st.focus, mid)
        else:
            r = _urmsv_row(st.focus)
            if r is not None and getattr(st, "area", None):
                x, y, w = urmsv_tile_box(r.n, st.area)
                mid = urmk_px(16) + x + w // 2
        return max(urmk_px(16), min(mid - width // 2, config.screen_width - urmk_px(16) - width))

    # pictures: made once per size and colour, kept with the kit's

    def _urmsv_made(key, make):
        found = urmk_look.made.get(("urmsv",) + key)
        if found is None:
            found = urmk_look.made[("urmsv",) + key] = make()
        return found

    def _urmsv_mix(colour, amount):
        c = tuple(renpy.easy.color(URMK_COLOURS.get(colour, colour)))
        return (c[0], c[1], c[2], int(round(c[3] * max(0.0, min(1.0, amount)))))

    def urmsv_outline(colour, radius=14, dashed=False):
        """A rounded line 2 pixels wide around whatever it is laid on;
        dashed: in dashes, which repeat along the sides."""

        def make():
            r = urmk_px(radius)
            t = max(1, urmk_px(2))
            period = urmk_px(12) if dashed else 4
            side = 2 * r + period
            box = (0, 0, side, side)

            def at(i, j):
                x, y = i + 0.5, j + 0.5
                d = _urmk_distance(x, y, box, r)
                cov = _urmk_cover(d) - _urmk_cover(d + t)
                if dashed and r <= i < r + period and (i - r) >= period // 2:
                    cov = 0.0
                if dashed and r <= j < r + period and (j - r) >= period // 2:
                    cov = 0.0
                return _urmsv_mix(colour, cov)

            png = _urmk_png(side, side, at)
            return Frame(im.Data(png, "urmsv_outline_%s_%d_%d.png" % (colour.strip("#"), r, int(dashed))),
                         r, r, r, r, tile=bool(dashed))
        return _urmsv_made(("outline", colour, radius, dashed, config.screen_height), make)

    def _urmsv_shape(name, size, inside):
        """A small mark `size` pixels (at 1080 lines) square: inside(x, y,
        half) gives each pixel's (colour, cover) laid bottom first."""

        def make():
            s = urmk_px(size)
            half = s / 2.0

            def at(i, j):
                out = (0, 0, 0, 0)
                for colour, cov in inside(i + 0.5 - half, j + 0.5 - half, half):
                    c = _urmsv_mix(colour, cov)
                    k = c[3] / 255.0
                    a = out[3] / 255.0
                    na = k + a * (1 - k)
                    if na <= 0:
                        continue
                    out = tuple(int(round((c[n] * k + out[n] * a * (1 - k)) / na)) for n in range(3)) + (int(round(na * 255)),)
                return out
            return im.Data(_urmk_png(s, s, at), "urmsv_%s_%d.png" % (name, s))
        return _urmsv_made(("shape", name, size, config.screen_height), make)

    def urmsv_ring_dot(size):
        """An auto save: a ring."""
        t = max(1.0, urmk_px(2))

        def inside(x, y, half):
            d = (x * x + y * y) ** 0.5
            return (("surface", _urmk_cover(d - half + 0.5)),
                    ("ink-muted", _urmk_cover(d - half + 0.5) - _urmk_cover(d - half + 0.5 + t)))
        return _urmsv_shape("ring", size, inside)

    def urmsv_diamond(size):
        """A quick save: a diamond."""
        def inside(x, y, half):
            return (("ink", _urmk_cover((abs(x) + abs(y)) / 1.4142 - half / 1.4142 + 0.5)),)
        return _urmsv_shape("diamond", size, inside)

    def urmsv_node(size):
        """Where a card stands on the line."""
        def inside(x, y, half):
            return (("ink", _urmk_cover((x * x + y * y) ** 0.5 - half + 0.5)),)
        return _urmsv_shape("node", size, inside)

    def urmsv_fade(width, height):
        """The band's ground fading out to the left of the oldest card shown."""
        def make():
            w = 64
            def at(i, j):
                return _urmsv_mix("surface", 1.0 if i < w * 0.3 else max(0.0, 1.0 - (i - w * 0.3) / (w * 0.7)))
            return im.Data(_urmk_png(w, 2, at), "urmsv_fade.png")
        return im.Scale(_urmsv_made(("fade",), make), width, height)

    def urmsv_dashes(height):
        """The dashed stem from Save now down to the line."""
        def make():
            t = max(1, urmk_px(2))
            dash = urmk_px(6)
            def at(i, j):
                return _urmsv_mix("accent-ink", 1.0 if (j // dash) % 2 == 0 else 0.0)
            return im.Data(_urmk_png(t, height, at), "urmsv_dashes_%d.png" % height)
        return _urmsv_made(("dashes", height), make)

    def urmsv_veil(width, height):
        return Fixed(urmk_pill("#0b1a308c", urmk_px(8)), xysize=(width, height))

    def urmsv_thumb(slot, width, height):
        """A save's picture at that size, or a quiet ground without one."""
        shot = None
        try:
            shot = renpy.slot_screenshot(slot)
        except Exception:
            shot = None
        if shot is None:
            return Fixed(urmk_pill(urmk_colour("plain-bg"), urmk_px(8)), xysize=(width, height))
        return Fixed(im.Scale(shot, width, height), xysize=(width, height))

    # ---- the keys: each only while its setting is on, so an unused key
    # stays the engine's (Alt+S: its screenshot)

    def _urmsv_quick_save():
        action = QuickSave()
        if renpy.is_sensitive(action):
            renpy.run(action)

    def _urmsv_quick_load():
        action = QuickLoad()
        if renpy.is_sensitive(action):
            renpy.run(action)

    def _urmsv_resume_key():
        if renpy.is_sensitive(QuickSave()):
            renpy.take_screenshot()
            urmsv_resume_set(True)

    # (name, key, the setting that turns it on, what it does)
    _URMSV_KEYS = (("urmsv_resume", "alt_K_q", "quickResumeSaveHotKey", _urmsv_resume_key),
                   ("urmsv_quick_save", "alt_K_s", "quickSaveHotKey", _urmsv_quick_save),
                   ("urmsv_quick_load", "alt_K_l", "quickLoadHotKey", _urmsv_quick_load))
    for _urmsv_k, _urmsv_key, _urmsv_s, _urmsv_f in _URMSV_KEYS:
        config.keymap[_urmsv_k] = [_urmsv_key]

    class _URMSVKeys(renpy.Displayable):
        """The keys, below every screen: a key whose setting is off is
        left to whatever else wants it."""

        def event(self, ev, x, y, st):
            for name, key, setting, fn in _URMSV_KEYS:
                if renpy.map_event(ev, name) and _urm_setting(setting):
                    try:
                        fn()
                    except Exception as error:
                        print("MRM: %s failed (%s)" % (key, error))
                    raise renpy.IgnoreEvent()
            return None

        def render(self, width, height, st, at):
            return renpy.Render(0, 0)

    config.underlay.append(_URMSVKeys())

    # ---- the URM+ menu: Save and Load (shown once the menu's button lands)

    _urm_entry_add("save", u"Save", u"\ue161", lambda: urmsv_open("save"),
                   shown=lambda: not urmsv_no_game(), group=1, order=20)
    _urm_entry_add("load", u"Load", u"\ue037", lambda: urmsv_open("load"), group=1, order=21)
