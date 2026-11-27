"""
Release gate: install the standalone BAT on clean copies of the six props,
then check the loaded source, saves, features and input in the native engines.

    python check_installer.py <URM_fix.bat> <scratch folder> <prop folder>...

Probes are compiled through the installer's native compiler, including on the
protected engine. All saves and settings stay under the gate's scratch folder.
"""

from __future__ import print_function

import base64
import binascii
import glob
import io
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import urm_source  # noqa  (the add-on's code, joined from its pieces)
import check_layers  # noqa  (our screens and the screens each file defines)

BIG_FILE = 150 * 1024 * 1024

PROBE = u'''init 1999 python:
    import os as _po
    _l = []
    try:
        for _n in ("urmal_toggle", "urmfl_set", "urm_panel",
                   "_urms_note_line", "_urm_noise", "_urmr_apply"):
            _l.append("%s=%r" % (_n, hasattr(store, _n)))
        # The add-on's code is kept as pieces (urm_compat/game_fixes) and
        # reaches a game as ONE file: the pieces joined in the order of their
        # names. What this engine loaded must be exactly that join - the
        # installer stores the md5 of the file it compiled at the end of the
        # compiled one - and this engine must have queued its blocks in the
        # order they stand in it, each once: the one early block (998, run
        # before URM's own start-up statements), then the others at 999.
        import binascii as _ba
        _ad = _ba.hexlify(renpy.file("urmplus/addon.rpyc").read()[-16:]).decode("ascii")
        _l.append("addon_is_the_joined_pieces=%r" % (_ad == "@@ADDON_MD5@@" or _ad,))
        _io = [((getattr(_n, "name", None) or ("",))[0], _p, _n.linenumber) for _p, _n in renpy.game.script.initcode]
        _ao = [(_p, _ln) for _f, _p, _ln in _io if _f == "urmplus/addon.rpy"]
        _l.append("addon_blocks_run_in_order=%r" % (_ao == @@ADDON_HEADERS@@ or _ao,))
        _legacy_scripts = [_n for _n in renpy.list_files() if _n.startswith("0x52-URM/")]
        _l.append("no_original_urm=%r" % ((not hasattr(store, "x52URM") and not _legacy_scripts) or _legacy_scripts or "legacy store exposed",))
        _l.append("our_overlay=%r" % (_urmi_layer == "urmplus" and _urmi_layer in config.layers,))
        # Our own screens (urm_compat/game_screens) reach a game as one file
        # in our own archive, game/urmplus.rpa: what this engine loaded must
        # be exactly their join, and each screen of ours must be the one
        # defined there (a traceback in them names _urmfix_screens.rpy), not
        # one an older build wrote into URM's screen text.
        _sd5 = _ba.hexlify(renpy.file("urmplus/screens.rpyc").read()[-16:]).decode("ascii")
        _l.append("screens_are_the_joined_files=%r" % (_sd5 == "@@SCREENS_MD5@@" or _sd5,))
        _sw = []
        for _sn in @@SCREEN_NAMES@@:
            _sv = renpy.display.screen.get_screen_variant(_sn)
            _sf = getattr(getattr(_sv, "ast", None), "location", ("",))[0] if _sv is not None else None
            if _sf != "_urmfix_screens.rpy":
                _sw.append((_sn, _sf))
        _l.append("our_screens_are_ours=%r" % (not _sw or _sw,))
        _l.append("If_watched=%r" % (getattr(renpy.ast.If.execute, "_urmal", False),))
        _l.append("alert_screen=%r" % (renpy.has_screen("urmal_alert"),))
        _l.append("spots_watched=%r" % (getattr(renpy.display.focus.take_focuses, "_urmpin", False) and _urmpin_overlay in config.overlay_functions,))
        # The banner is shown on URM's layer, and a plain Hide looks on the
        # screen's own default layer - this engine's answer must differ, or
        # the test below proves nothing. (Screens can't be shown during init,
        # so the scene is stood in for: the banner "is" on _urmi_layer.)
        _dflt = renpy.display.screen.get_screen_layer(("urmal_alert",))
        _l.append("plain_hide_looks_elsewhere=%r" % (_dflt != _urmi_layer,))
        _hid = []
        _real = (renpy.get_screen, renpy.hide_screen)
        def _fake_get(name, layer=None):
            return object() if (name == "urmal_alert" and layer == _urmi_layer and not _hid) else None
        def _fake_hide(name, layer=None, **kw):
            _hid.append(layer)
        renpy.get_screen, renpy.hide_screen = _fake_get, _fake_hide
        try:
            urmal_close()
        finally:
            renpy.get_screen, renpy.hide_screen = _real
        _l.append("alert_ok_closes=%r" % (_hid == [_urmi_layer],))
        # A stray % in dialogue must not stop the game (old substitutions).
        _g = _urmpct_guard(u"100% correct [name]")
        try:
            _g % renpy.exports.tag_quoting_dict if config.old_substitutions else None
            _l.append("stray_percent_guard=True")
        except Exception as _e:
            _l.append("stray_percent_guard=%r" % (_e,))
        _l.append("say_guarded=%r" % (getattr(renpy.exports.say, "_urmpct", False),))
        # Game font: every option loads on this engine, the game's font is
        # swapped, URM's own and icon fonts are not.
        # A game that left something else than a table in
        # config.font_transforms (My Femdom Wife 0.7: a list) keeps it, and
        # is offered no font: the engine cannot apply one there.
        _fa = _urmft_available()
        _ftab = isinstance(config.font_transforms, python_dict)
        _l.append("font_options_all=%r" % ([r[0] for r in _fa] == (["dejavu", "roboto", "comfortaa", "mono", "dyslexic"] if _ftab else []) or [r[0] for r in _fa],))
        _ok = True
        for _k, _n, _p, _e in _fa:
            _head = renpy.file(_p).read(4)
            _ok = _ok and _head in (b"\\x00\\x01\\x00\\x00", b"OTTO", b"true")
            _m = _urmft_map(_k, "SomeGame/comic.ttf")
            _ok = _ok and _m != "SomeGame/comic.ttf" and type(_m).__name__ == "FontGroup"
            _ok = _ok and _urmft_map(_k, URMK_CODE_FONT) == URMK_CODE_FONT
            _ok = _ok and _urmft_map(_k, "gui/FontAwesome.otf") == "gui/FontAwesome.otf"
        _l.append("font_maps=%r" % (_ok,))
        if _ftab:
            _l.append("font_hook=%r" % (config.font_transforms.get("urmplus") is _urmft_transform,))
        else:
            _l.append("font_hook=%r" % (renpy.game.preferences.font_transform is None or renpy.game.preferences.font_transform,))
            with open(_po.path.join(config.basedir, "urm_probe_graph.txt"), "a") as _nf:
                _nf.write("\\nfont table: config.font_transforms is a %s in this game, left as it is; Game font is not offered\\n" % type(config.font_transforms).__name__)
        _l.append("font_set_hooked=%r" % (_urmft_changed in _urm_settings_st.watchers.get("urmcFont", ()),))
        # Settings belong to the local persistent store and our shared file.
        _sn = "urmcLookAhead"
        _urm_setting_set(_sn, 37)
        _urm_setting_set(_sn, 41, True)
        import json as _sj
        with open(_urm_shared_path(), "rb") as _sf:
            _sfile = _sj.loads(_sf.read().decode("utf-8"))["values"].get(_sn)
        _sok = [_urm_setting(_sn) == 37, _urm_setting_at(_sn, True) == 41,
                _urm_lookahead() == 37, renpy.game.persistent._urm_settings.get(_sn) == 37,
                _sfile == 41]
        _urm_setting_set(_sn, None)
        _sok += [_urm_setting(_sn) == 41]
        _urm_setting_set(_sn, None, True)
        _sok += [_urm_setting(_sn) == 20]
        _l.append("settings_in_our_store=%r" % (all(_sok) or _sok,))
        # Mazes: a choice that is only a jump shows the flags at its label,
        # a nested menu's outcomes, and a wrong turn back to this menu.
        _mz = [n for n in renpy.game.script.lookup("urmprobe_maze").block
               if isinstance(n, renpy.ast.Menu)][0]
        _mb = [i[2] for i in _mz.items if i[2] is not None]
        _mo = _urmm_outline(_mz, _mb)
        _l.append("maze_follows_jumps=%r" % (list(_mo[0][0]) == ["urmprobe_x = 1"],))
        _l.append("maze_nested=%r" % (list(_mo[1][0]) == ["urmprobe_y = 2"] and [(p, list(t), n) for p, t, n in _mo[1][1]] == [("C", ["urmprobe_z = 3"], None), ("D", [], "back to this menu")],))
        _l.append("maze_rows=%r" % (len(urm_maze_rows(_urmm_arms(_mz, _mb)[1])) == 3,))
        # Checked later: the real script index links the flag choice A sets
        # to the test after the rejoin. Built here in the foreground.
        _ix = _URMIndex()
        _ix.build(_urmi_all_stmts(), 0, None)
        _lt = _urmm_later(_urmm_plan(_mz, _mb)[1], _urmm_names(_urmm_arms(_mz, _mb)[0]), _ix)
        _l.append("maze_checked_later=%r" % ([r[:3] for r in _lt] == [("urmprobe_x", "urmprobe_x == 1", "urmprobe_done")] or [r[:3] for r in _lt],))
        # Idea 3: two meeting points that tie - the earlier in the script
        # wins on every engine (on Python 2 a dict's order used to decide).
        _tz = [n for n in renpy.game.script.lookup("urmprobe_tie").block
               if isinstance(n, renpy.ast.Menu)][0]
        _tp = _urmm_plan(_tz, [i[2] for i in _tz.items if i[2] is not None])[1]
        _l.append("maze_tie_earlier=%r" % (_tp is renpy.game.script.lookup("urmprobe_tie_earlier") or getattr(_tp, "name", _tp),))
        # The mirrored paths of Now and Then (the user's report, 2026-11-20):
        # two ways that share a scene one option goes around meet BEHIND
        # that scene, and the menu after the meeting point is on the map
        # once - it was there once per way.
        _mm = [n for n in renpy.game.script.lookup("urmprobe_mirror").block
               if isinstance(n, renpy.ast.If)][0]
        _mmp = _urmm_plan(_mm, [b for _c, b in _mm.entries])[1]
        _mmv = urm_map_build(renpy.game.script.lookup("urmprobe_mirror"), _ix)
        _mmq = [b.title for b in _mmv.boxes if b.title in ("Q", "R")]
        _l.append("map_mirror_once=%r" % ((_mmp is renpy.game.script.lookup("urmprobe_mirror_main") and _mmq == ["Q", "R"]) or (getattr(_mmp, "name", _mmp), _mmq),))
        # Idea 7: the map opened inside a called scene. THIS engine's own
        # context is given a place in the probe's called scene and the call
        # it would be inside; the map must lead both ways back to the
        # caller, where they meet, and say "Ending" only there.
        _ctx = renpy.game.context()
        _kc = _ctx.current
        _kr = list(_ctx.return_stack)
        try:
            _ctx.current = renpy.game.script.lookup("urmprobe_called").name
            _ctx.return_stack = [renpy.game.script.lookup("urmprobe_caller_back").name]
            _lv = _urmsg_live_stack()
            _l.append("live_stack_read=%r" % ([getattr(_n, "name", None) for _n in _lv] == ["urmprobe_caller_back"] or _lv,))
            _cv7 = urm_map_build(None, _ix)
            _cb7 = [(b.kind, b.title, [c[0] for c in b.chips], b.note) for b in _cv7.boxes if b.kind != "here"]
            _l.append("map_called_scene=%r" % (_cb7 == [("choice", "E", ["urmprobe_e: 1"], None), ("choice", "F", [], None), ("merge", "Paths meet again", ["urmprobe_back: 1"], "Ending")] or _cb7,))
        finally:
            _ctx.current = _kc
            _ctx.return_stack = _kr
        # Route map: the screen exists, it is in the URM+ menu with Alt+G,
        # and the probe maze lays out as 3 routes into one merge box, with
        # what it decides later in words.
        _l.append("map_screen=%r" % (renpy.has_screen("urm_route_map"),))
        _l.append("map_in_menu=%r" % (("alt_K_g", "story_line") in _urm_keys() and "route_map" not in [e.name for e in _urm_entries()],))
        _mv = urm_map_build(_mz, _ix)
        _ml = [b.title for b in _mv.boxes if not b.children and b.kind == "choice"]
        _l.append("map_routes=%r" % (_mv.empty is None and _ml == ["A", "C", "D"] and [b.kind for b in _mv.boxes].count("merge") == 1 and _mv.width > 0 and len(_mv.bars) > 0 or (_mv.empty, _ml),))
        _l.append("map_here_label=%r" % ([b.title for b in _mv.boxes if b.kind == "here"] == ["urmprobe_maze"] or [b.title for b in _mv.boxes if b.kind == "here"],))
        # The map's rows and box heights come from the engine's own text
        # layout (Text.size, as URM itself measures); counting characters
        # is only the way out when the engine cannot be asked. On every
        # engine here it must be the engine that answered, and every box
        # must be exactly as high as its parts added up.
        _l.append("map_text_from_engine=%r" % (_urmm_st.engine is True or _urmm_st.engine,))
        _l.append("map_rows_fit=%r" % (all(b.dot or b.h == _urmm_box_h(b, urmk_px_cut) and b.h >= 2 * urmk_px_cut(8) + sum(r[3] for r in b.rows) for b in _mv.boxes) or [(b.title, b.h) for b in _mv.boxes],))
        _l.append("map_later=%r" %(list(_mv.later) == [u"At urmprobe_done the game checks: urmprobe_x is 1  \\u00b7  not set yet"] or list(_mv.later),))
        # The soft chip (the user's pick 1a, 2026-11-21) in our own palette
        # (the screen kit, 16_kit; 1a, 2026-11-22): a solid pill made by our
        # own code as an image this engine decodes, made once per colour,
        # one look on every ground (a light box too), its words in the
        # palette's colour.
        _pp = urm_chip_bg('gain')
        _psz = _pp.image.load().get_size()
        _l.append("chip_pill=%r" % ((_psz[0] == _psz[1] >= 8 and urm_chip_bg('gain') is _pp and urm_chip_bg('gain', True) is _pp and urm_chip_ink('loss') == URMK_COLOURS['loss-ink']) or (_psz,),))
        # The screen kit in this engine, with URM as installed: the fonts it
        # names are there (our Roboto from our archive, URM's icons), the banner's ground (shadow, edge light, amber
        # edge) is a picture this engine decodes, its shadow reaching past
        # the panel.
        _kb = urmk_back('window', 'warn')
        _ksz = _kb.image.image.load().get_size()
        _l.append("kit_ready=%r" % ((all(renpy.loadable(_kf) for _kf in URMK_FONTS.values()) and renpy.loadable(URMK_ICON_FONT) and _ksz[0] > 2 * urmk_px(14) and _kb.bottom > _kb.top >= 0 and renpy.has_screen('urmk_window') and renpy.has_screen('urmal_alert')) or (_ksz, _kb.top, _kb.bottom),))
        # Idea 13 (the user's picks 1a, 2a, 3b): the way out of a hub says
        # what it takes; a menu whose every option has a test has the way
        # "If none apply", faded until no test holds on THIS engine's
        # store; a custom statement with content inside leaves a "?" - in
        # a box, and on the line where there is nothing else to say. No
        # game here registers such a statement, so two are made by hand
        # from this engine's own class and put after two statements of the
        # probe's story for the length of the check.
        _hb = renpy.game.script.lookup("urmprobe_hub").block
        _hm = [n for n in _hb if isinstance(n, renpy.ast.Menu)][0]
        _us = []
        for _an in ([n for n in _hb if isinstance(n, renpy.ast.Python)][0], [n for n in _hb if isinstance(n, renpy.ast.Pass)][0]):
            _u = renpy.ast.UserStatement.__new__(renpy.ast.UserStatement)
            _u.filename = _an.filename
            _u.linenumber = _an.linenumber
            _u.name = ("urmprobe_custom", len(_us))
            _u.line = "urmprobe_custom:"
            _u.parsed = None
            _u.block = [(_an.filename, _an.linenumber, "content", [])]
            _u.next = _an.next
            _us.append((_an, _an.next, _u))
        _w13 = lambda _v: [(b.kind, b.title, b.sub, [c[0] for c in b.chips], [k for k, _t in b.badges], b.faded) for b in _v.boxes if b.kind in ("choice", "branch")]
        try:
            for _an, _nx, _u in _us:
                _an.next = _u
            _urmsg_reset()
            _l.append("custom_statement_told=%r" % ([_urmsg_closed(_u) for _an, _nx, _u in _us] == [True, True] and not _urmsg_closed(_hm),))
            _v13 = urm_map_build(_hm, _ix)
            _b13 = _w13(_v13)
            _l.append("map_idea13_ways=%r" % (_b13 == [("choice", "I", None, ["urmprobe_i: 1"], [], False), ("branch", "Otherwise", "When nothing is left to pick", ["urmprobe_out: 1"], ["code"], False), ("choice", "J (if urmprobe_j >= 3)", None, ["urmprobe_jj: 1"], [], False), ("choice", "K (if urmprobe_k >= 3)", None, ["urmprobe_kk: 1"], [], False), ("branch", "If none apply", None, [], [], True), ("choice", "L", None, ["urmprobe_l: 1"], [], False), ("choice", "M", None, [], [], False)] or _b13,))
            _l.append("map_idea13_mark_on_line=%r" % ([t for _x, _y, t in _v13.codes] == ["The game runs its own code here"] and not [b.title for b in _v13.boxes if not b.dot and not (b.title or b.chips or b.note)] or list(_v13.codes),))
            store.urmprobe_j = 0
            store.urmprobe_k = 0
            _f13 = [b.faded for b in urm_map_build(_hm, _ix).boxes if b.title == "If none apply"]
            store.urmprobe_k = 5
            _f13 += [b.faded for b in urm_map_build(_hm, _ix).boxes if b.title == "If none apply"]
            _l.append("map_idea13_none_follows_game=%r" % (_f13 == [False, True] or _f13,))
        finally:
            for _an, _nx, _u in _us:
                _an.next = _nx
            _urmsg_reset()
        # Notification cards in words (option A), and closing them.
        _cv, _cf = _urmm_choice_view([i for i in _mz.items if i[2] is not None], _urmm_arms(_mz, _mb), [True, True], _urmm_later(_urmm_plan(_mz, _mb)[1], ["urmprobe_x"], _ix))
        _l.append("cards_words=%r" % ([c[3] for c in _cv] == ["A", "B"] and list(_cv[0][6][0][2]) == [("urmprobe_x: 1", "set")] and [r[1] for r in _cv[1][6]][1:] ==[u"\\u203a C", u"\\u203a D"] and _cf == [u"urmprobe_x matters at urmprobe_done  \\u00b7  checked for 1"] or (_cv, _cf),))
        _l.append("cards_closable=%r" % (urm_note_hidden("choices") is False and callable(urm_note_close),))
        # Shared or branch-only (IDEAS.md, PRIORITY). The tracker is hooked;
        # an If and a Jump report themselves through statement_callbacks on
        # this engine - the whole design rests on that; and the player's two
        # cases read right on this engine's real statements, with whatever
        # Translate wrappers it puts around a line fed in as they would be.
        _l.append("branch_hooked=%r" % (_urmb_record in config.statement_callbacks and _urmb_interact in config.interact_callbacks,))
        store.urmprobe_bx = True
        _bl = renpy.game.script.lookup("urmprobe_branch")
        _b0 = _urmb_rep(_bl.next)
        _bi = _urmb_rep(_b0.next)
        _b1 = _urmb_rep(_bi.entries[0][1][0])
        _b2 = _urmb_rep(_bi.next)
        _l.append("branch_shape=%r" % ([type(n).__name__.replace("TranslateSay", "Say") for n in (_b0, _bi, _b1, _b2)] == ["Say", "If", "Say", "Say"],))
        _rp = []
        def _rp_cb(name):
            _rp.append(name)
        config.statement_callbacks.append(_rp_cb)
        try:
            _bi.execute()
            _mz.items[0][2][0].execute()
        finally:
            config.statement_callbacks.remove(_rp_cb)
        _l.append("branch_if_and_jump_report=%r" % (_rp == ["if", "jump"] or _rp,))
        _s0 = _urmb_advance(None, (_bl.name, _bl.next.name, _b0.name), False, _b0)
        _s1 = _urmb_advance(_s0, (_b0.next.name, _bi.name, _bi.entries[0][1][0].name, _b1.name), False, _b1)
        _s2 = _urmb_advance(_s1, (_b1.next.name, _bi.next.name, _b2.name), False, _b2)
        _bv = [(_urmb_view(s, False, 2) or ("", ""))[1] for s in (_s0, _s1, _s2)]
        _l.append("branch_case_true=%r" % (_bv == ["", "Only because urmprobe_bx is true", "Back on the shared part"] or _bv,))
        _l.append("branch_count=%r" % ((_urmb_view(_s1, False, 2) or ("",) * 3)[2] == 0 or _urmb_view(_s1, False, 2),))
        _s3 = _urmb_advance(_s0, (_b0.next.name, _bi.name, _bi.next.name, _b2.name), False, _b2)
        _bv = (_urmb_view(_s3, False, 2) or ("", ""))[1]
        _l.append("branch_case_false=%r" % (_bv == u"Skipped a part  \\u00b7  needs urmprobe_bx true" or _bv,))
        _l.append("branch_same_again=%r" % (_urmb_advance(_s0, (_b0.next.name, _bi.name, _bi.entries[0][1][0].name, _b1.name), False, _b1) == _s1,))
        # The URM+ button says it (the user's b), on THIS engine, through
        # the chip's own hooks as play runs them: each statement noted as it
        # runs, the line worked out at its interaction, the button asking
        # at its draw. Yellow with 1 on the part's last line; green on the
        # line where the paths meet, and again after a rollback onto it (the
        # line before's state put back, the line's statement run again);
        # blue on the next; Hide turns it blue on its own line.
        _b3 = _urmb_rep(_b2.next)
        class _URMProbeLine(object):
            rollback = True
            init_phase = False
            current = None
        def _bplay(names):
            for _n in names:
                _URMProbeLine.current = _n
                _urmb_record(_n)
            _urmb_interact()
            _bs = _urm_status()
            return "blue" if _bs is None else (_bs.tone, _bs.count, urmh_kind(_bs))
        _bc = renpy.game.context
        _bw = []
        try:
            renpy.game.context = lambda *_a: _URMProbeLine()
            store._urmb_state = None
            _bw.append(_bplay((_bl.name, _bl.next.name, _b0.name)))
            _bw.append(_bplay((_b0.next.name, _bi.name, _bi.entries[0][1][0].name, _b1.name)))
            _bb = store._urmb_state
            _bw.append(_bplay((_b1.next.name, _bi.next.name, _b2.name)))
            store._urmb_state = _bb
            _bw.append(_bplay((_b2.name,)))
            _bw.append(_bplay(tuple(_n for _n in (_b2.next.name, _b3.name) if _n is not None)))
            store._urmb_state = None
            _bplay((_bl.name, _bl.next.name, _b0.name))
            _bplay((_b0.next.name, _bi.name, _bi.entries[0][1][0].name, _b1.name))
            urmh_hide()
            _bs = _urm_status()
            _bw.append("blue" if _bs is None else _bs.tone)
        except Exception:
            import traceback as _btb
            _bw.append(_btb.format_exc()[-500:])
        finally:
            renpy.game.context = _bc
            store._urmb_state = None
            _urmb_forget()
        _l.append("branch_button=%r" % (_bw == ["blue", ("warn", u"1", "warn"), ("gain", None, "gain"),
                                                ("gain", None, "gain"), "blue", "blue"] or _bw,))
        _l.append("branch_setting=%r" % (_urm_setting_at("urmcBranchChip") == 2 and store._urmb_state is None,))
        import pickle as _bpk
        _l.append("branch_state_plain=%r" % (b"_URM" not in _bpk.dumps(_s1, 2),))
        # A game with translations: a line of a translation must map back
        # to a statement of the original script, or nothing is ever tracked
        # for players of that language.
        _tr = renpy.game.script.translator
        _lgs = [l for l in (getattr(_tr, "languages", None) or ()) if l]
        if _lgs:
            _lg = sorted(_lgs)[0]
            _was = renpy.game.preferences.language
            renpy.game.preferences.language = _lg
            try:
                _tt = 0
                _tb = 0
                _ts = 0
                _ts1 = None
                for _key in _tr.language_translates:
                    if _key[1] != _lg or _tt >= 300:
                        continue
                    _tn = _tr.language_translates[_key]
                    _cands = [_tn] if getattr(_tn, "language", None) is not None and getattr(_tn, "what", None) is not None else list(getattr(_tn, "block", None) or ())[:1]
                    for _c in _cands:
                        _tt += 1
                        _d = _urmb_canon(_c)
                        if _d is _c or _d is None or "tl/" in (getattr(_d, "filename", "") or "").replace(chr(92), "/"):
                            _tb += 1
                        # Idea 14: the scene of a translated line is the
                        # scene of the line it stands for - asked of the
                        # real index (built above), not of its line number
                        # in the language file.
                        _sc1 = _urmsg_label_of(_ix, _c)
                        _sc2 = _urmsg_label_of(_ix, _d) if _d is not None else None
                        if _sc1 is None or _sc1 != _sc2:
                            _ts += 1
                            _ts1 = _ts1 or "%s:%s is in %r, its original in %r" % (getattr(_c, "filename", "?"), getattr(_c, "linenumber", "?"), _sc1, _sc2)
            finally:
                renpy.game.preferences.language = _was
            _l.append("branch_translated_lines_map_back=%r" % (_tb == 0 or "%d of %d do not (%s)" % (_tb, _tt, _lg),))
            _l.append("translated_lines_have_their_scene=%r" % (_ts == 0 or "%d of %d do not (%s): %s" % (_ts, _tt, _lg, _ts1),))
            if renpy.loadable("prop_script.rpyc"):
                _l.append("prop_translation_checked=%r" % (_tt >= 2 or "%d lines found" % _tt,))
            with open(_po.path.join(config.basedir, "urm_probe_graph.txt"), "a") as _nf:
                _nf.write("\\ntranslations: %s - %d of %d lines map back to the original script\\n" % (_lg, _tt - _tb, _tt))
        # The branch chip is read by the URM+ button.
        # ... and has no screen of its own any more: it says what it says
        # on the URM+ button (the user's b, 2026-11-22), nothing else
        # shows it.
        _sc = (renpy.has_screen("urmb_chip"), "branch" in _urm_offers().statuses,
               [c for c in config.interact_callbacks if getattr(c, "__name__", "") == "_urmb_show"])
        _l.append("chip_on_the_button=%r" % (_sc == (False, True, []) or _sc,))
        # A prop game (tests/make_props.py) must really hold its story: one
        # engine here ignores loose script files, and a prop built that way
        # passed while testing nothing of its own.
        if renpy.loadable("prop_script.rpyc"):
            _pl = [_n for _n in @@PROP_LABELS@@ if not renpy.has_label(_n)]
            _l.append("prop_story_loaded=%r" % (not _pl or "missing labels: %s" % ", ".join(_pl),))
        # Where this copy keeps its saves and URM its settings: in the
        # gate's own folder for it, never the player's (FINDINGS.md, "Scratch
        # copies share the real game's save folder").
        # (A game with no config.save_directory, as a prop, saves in its
        # own game/saves: in the copy, which is the gate's too.)
        _hm = [_po.path.normcase(_po.path.abspath(_h)) + _po.sep for _h in (_po.environ.get("URM_GATE_HOME") or "?", config.basedir)]
        _hw = [(_w, _p) for _w, _p in (("saves", config.savedir),
                                       ("MRM settings", _po.path.dirname(_urm_shared_path())))
               if not _p or not any(_po.path.normcase(_po.path.abspath(_p)).startswith(_h) for _h in _hm)]
        _l.append("clean_settings=%r" % (not _hw or "; ".join("%s in %s" % w for w in _hw),))
    except Exception as _e:
        _l.append("ERROR=%r" % (_e,))
    # The prop's own situations, each a past break of a real game, in the
    # prop's story (tests/make_props.py). Each on its own: an old build
    # that lacks a name fails that line only.
    if renpy.loadable("prop_script.rpyc"):
        # This run is a plain game: the quirks of real games are switched
        # on only in the quirky run (font_list, URM_GATE_QUIRKS), so the
        # way almost every game goes is run here, with no shim in it.
        try:
            _l.append("plain_game=%r" % (isinstance(EndReplay, type),))
        except Exception as _e:
            _l.append("plain_game=%r" % (_e,))
        # Real lines with a stray % ("100% correct": Freeloading Family),
        # through the engine's own say, which formats with % while
        # config.old_substitutions is on (the default through Ren'Py 7):
        # shown as written. A line that uses %(name)s on purpose is
        # still filled in.
        try:
            _pw = dict((n.what, n.what) for n in renpy.game.script.all_stmts if isinstance(n, renpy.ast.Say) and "tl/" not in (n.filename or "").replace(chr(92), "/") and n.what in ("You are 100% correct.", "It works, %(urmprobe_pn)s."))
            _po_old = config.old_substitutions
            _pg = []
            config.old_substitutions = True
            store.urmprobe_pn = "yes"
            try:
                for _pk in ("You are 100% correct.", "It works, %(urmprobe_pn)s."):
                    renpy.exports.say(lambda what, *a, **k: _pg.append(what), _pw[_pk])
            finally:
                config.old_substitutions = _po_old
            _l.append("stray_percent_real_line=%r" % (_pg == ["You are 100% correct.", "It works, yes."] or _pg,))
        except Exception as _e:
            _l.append("stray_percent_real_line=%r" % (_e,))
        # Skip past a small change, the strict rule, on THIS engine's own
        # statements: every line of a script sits inside a Translate, and
        # the look back from a changed line must pass them to the line
        # read before it (Nothing Is Forever, 2026-11-13). The lines
        # around it are marked seen under the key the engine writes after
        # a line (execution.py, Context.run: hashed where config.hash_seen
        # is on).
        _kc = renpy.game.context()
        _ks = renpy.game.persistent._seen_ever
        # The default rule (what a player gets unless strict is on) is
        # checked the same way in a translation: the line read just before
        # was played, and the line after it must be found seen in French.
        def _urmprobe_skip(_lang, _texts, _strict):
            # Its own index: an old build may have stopped the run above
            # before the shared one was built.
            _kix = _URMIndex()
            _kix.build(_urmi_all_stmts(), 0, None)
            _kn = dict((n.what, n) for n in renpy.game.script.all_stmts if isinstance(n, renpy.ast.Say) and n.what in _texts and ("tl/" in (n.filename or "").replace(chr(92), "/")) == bool(_lang))
            _kb = set(_ks)
            _kp = (_kc.current, renpy.game.preferences.language, store._urmi_index, getattr(_URMMemory, "skip_run", None))
            try:
                renpy.game.preferences.language = _lang
                for _t in (_texts[0], _texts[2]):
                    _kk = _kn[_t].name
                    _ks[renpy.astsupport.hash64(_kk) if getattr(renpy.config, "hash_seen", False) else _kk] = True
                store._urmi_index = lambda: _kix
                _URMMemory.skip_cache = None
                if _strict:
                    return _urms_small_change(_kn[_texts[1]].name, 3)
                _URMMemory.skip_run = None
                _kr = _urms_run()
                _kr.after_seen, _kr.unseen = True, 1
                return _urms_played_between(_kn[_texts[1]].name, 3)
            finally:
                _kc.current, renpy.game.preferences.language, store._urmi_index, _URMMemory.skip_run = _kp
                _URMMemory.skip_cache = None
                for _k in [k for k in _ks if k not in _kb]:
                    del _ks[_k]
        for _kl, _kname, _kt, _kstrict in ((None, "skip_looks_back_past_translate", ("Read before.", "Changed since.", "Read after."), True),
                                           ("french", "skip_looks_back_in_a_translation", ("Lu avant.", "Change depuis.", "Lu apres."), True),
                                           ("french", "skip_default_rule_in_a_translation", ("Lu avant.", "Change depuis.", "Lu apres."), False)):
            try:
                _kv = _urmprobe_skip(_kl, _kt, _kstrict)
                _l.append("%s=%r" % (_kname, _kv is True or _kv))
            except Exception as _e:
                _l.append("%s=%r" % (_kname, _e))
    try:
        # The story-graph comparison ran in its own block just before this one.
        # Idea 22 (parked, IDEAS.md): how much of this game is moved along
        # by clicking a screen instead of a text menu. A note for the user's
        # decision, never a gate; any failure here is swallowed.
        try:
            _cs_sites = 0
            _cs_names = set()
            for _n in renpy.game.script.all_stmts:
                if isinstance(_n, renpy.ast.UserStatement):
                    _ln = (getattr(_n, "line", "") or "").strip()
                    if _ln.startswith("call screen "):
                        _cs_sites += 1
                        _cs_names.add(_ln.split()[2].split("(")[0].rstrip(":"))
            def _cs_scan(_node, _found, _depth=0):
                if _depth > 60 or _node is None:
                    return
                for _pair in (getattr(_node, "keyword", None) or ()):
                    _v = _pair[1] if len(_pair) > 1 else None
                    if hasattr(_v, "find"):
                        if "Jump(" in _v or "Call(" in _v:
                            _found.add("jump")
                        if "Return(" in _v:
                            _found.add("return")
                for _c in (getattr(_node, "children", None) or ()):
                    _cs_scan(_c, _found, _depth + 1)
                for _e in (getattr(_node, "entries", None) or ()):
                    _cs_scan(_e[1] if len(_e) > 1 else None, _found, _depth + 1)
            _cs_jump = 0
            _cs_ret = 0
            for _nm in _cs_names:
                _sc = renpy.display.screen.get_screen_variant(_nm)
                _fd = set()
                _cs_scan(getattr(_sc, "ast", None), _fd)
                _cs_jump += "jump" in _fd
                _cs_ret += "return" in _fd
            with open(_po.path.join(config.basedir, "urm_probe_graph.txt"), "a") as _nf:
                _nf.write("\\nclickable screens: %d call-screen statements, %d screens; "
                          "%d jump from a button, %d hand a value back to the script\\n"
                          % (_cs_sites, len(_cs_names), _cs_jump, _cs_ret))
        except Exception:
            pass
        # What URM+ puts in a save must not need URM+ to load.
        import pickle as _pk
        _blob = _pk.dumps(store.urmr_middle_click, 2)
        _l.append("save_needs_no_URM+=%r" % (b"_URM" not in _blob,))
    except Exception as _e:
        _l.append("ERROR=%r" % (_e,))
    # Last, because it readies styles and screens the way the engine only
    # does after init: the route map's screen is built by THIS engine from
    # the probe maze's map - every expression in it evaluated, every
    # displayable made. A screen that parses can still fail here (a name,
    # a property this engine does not know), and the player would meet
    # that as an error screen on opening the map.
    try:
        for _st in list(getattr(renpy.translation, "deferred_styles", ())):
            _st.apply()
        renpy.style.build_styles()
        renpy.ui.reset()
        renpy.display.screen.prepare_screens()
        # URM's notifications, built by THIS engine with the chip to show:
        # the chip is not theirs any more; it draws from its own screen. Our corner card (road step A4),
        # built by THIS engine with a card to show, a row pointed at (its
        # Take), and with nothing to show. (Alt+G is the URM+ menu's now.)
        def _urm_tree(name, **scope):
            _sd = renpy.display.screen.ScreenDisplayable(renpy.display.screen.get_screen_variant(name), None, "screens")
            _sd.scope["_scope"] = None
            _sd.scope.update(scope)
            _sd.update()
            _ht, _hk2 = [], []
            _hq = [_sd.child]
            while _hq:
                _hd = _hq.pop()
                if isinstance(_hd, renpy.text.text.Text):
                    _ht.extend(t for t in _hd.text if isinstance(t, type(u"")))
                if isinstance(_hd, renpy.display.behavior.Keymap):
                    _hk2.extend(getattr(_hd, "keymap", {}).keys())
                _hq.extend(getattr(_hd, "children", None) or ([_hd.child] if getattr(_hd, "child", None) is not None else []))
            return _ht, _hk2
        _hk = (store.urm_corner_view, store.urm_branch_view)
        try:
            store.urm_branch_view = lambda: ("warn", u"urmprobe chip", 0, "in", True)
            store.urm_corner_view = lambda: [("choices", u"Choices", False,
                [(("num", u"1"), True, u"urmprobe card", True, None, [(0, None, [(u"you have 1, needs 2", "warn")], None)], True, True)], [])]
            # the chip's words atop the URM+ button's menu, in play
            renpy.game.contexts.append(renpy.execution.Context(True, renpy.game.context()))
            try:
                urmh_open()
                _bt = _urm_tree("urmh_button")[0]
            finally:
                urmh_close()
                renpy.game.contexts.pop()
            _ct, _ck = _urm_tree("urm_corner", _urmcAt=("choices", 0))
            store.urm_corner_view = lambda: []
            _et, _ek = _urm_tree("urm_corner")
            _hh = (u"urmprobe chip" in _bt, u"urmprobe card" in _ct, u"Take" in _ct,
                   u"you have 1, needs 2" in _ct, "alt_K_g" not in _ek, u"Take" not in _et)
            _l.append("corner_cards_draw=%r" % (_hh == (True,) * 6 or _hh,))
        finally:
            store.urm_corner_view, store.urm_branch_view = _hk
        # The URM+ button (17_hub), built by THIS engine from what the
        # features of this build registered: the menu open shows every entry
        # it was given and binds the registered keys (Alt+G for the route
        # map) and Alt+U; the settings window shows its sections and the
        # rows of the first, each with This game and All games. Built in
        # the context the story runs in (rollback on), and in one a game's
        # menu runs in (save, load, preferences, history; H hides the
        # interface the same way: a context of its own, no rollback), where
        # the button, its menu and its keys draw nothing, though the screen
        # is carried into it with every layer.
        try:
            _ub = _urmh_state()
            renpy.game.contexts.append(renpy.execution.Context(True, renpy.game.context()))
            try:
                urmh_open()
                _uw = [e.words for e in _ub.entries]
                _mt, _mk = _urm_tree("urmh_button")
                _ub.section = _urm_sections()[0].name
                _rw = [r.words for r in _urm_rows(_ub.section)]
                _pt = _urm_tree("urmh_settings")[0]
            finally:
                renpy.game.contexts.pop()
            renpy.game.contexts.append(renpy.execution.Context(False, renpy.game.context(), clear=True))
            try:
                _nt, _nk = _urm_tree("urmh_button")
            finally:
                renpy.game.contexts.pop()
            _l.append("hub_not_in_menus=%r" % ((not _nt and not _nk) or (_nt[:6], _nk),))
            _uh = (bool(_uw) and all(w in _mt for w in _uw), u"Story line" in _uw, u"Settings" in _uw,
                   "alt_K_g" in _mk and "alt_K_u" in _mk,
                   all(s.words in _pt for s in _urm_sections()), bool(_rw) and all(w in _pt for w in _rw),
                   u"This game" in _pt and u"All games" in _pt)
            _l.append("hub_builds=%r" % (_uh == (True,) * 7 or (_uh, _uw, _mt[:12]),))
        except Exception as _e:
            import traceback as _tbh
            _l.append("hub_builds=%r" % (_tbh.format_exc()[-700:],))
        finally:
            urmh_close()
            _urmh_state().section = None
        # Alt+U is no key of this engine's own (URM's screens: run_tests 4u).
        _ku = [n for n, keys in config.keymap.items() if "alt_K_u" in (keys or ())]
        _l.append("hub_key_free=%r" % (not _ku or _ku,))
        _urmm_st.view = urm_map_build(_mz, _ix)
        _sd = renpy.display.screen.ScreenDisplayable(renpy.display.screen.get_screen_variant("urm_route_map"), None, "screens")
        _sd.scope["_scope"] = None
        _sd.update()
        _l.append("map_screen_builds=%r" % (len(_urmm_st.view.boxes) > 0,))
        # ... and drawn by THIS engine: the part that shows the boxes keeps
        # the room under the header, whatever the game's own scrollbar
        # style says (Star Periphery's has no height: its bar took the
        # whole map, 2026-11-21). A bar takes at most URM's 15 px.
        # (no window: the engine refuses a render only in developer mode, as
        # lint runs are; text asks the renderer for its scale and textures -
        # a stand-in, as check_pins.py does; solids and frames only fill
        # their room here, as in research/preview/tools/map_trace.rpy)
        def _urm_fill_render(self, width, height, st, at):
            return renpy.display.render.Render(int(max(self.style.xminimum or 0, width)), int(max(self.style.yminimum or 0, height)))
        class _URMProbeDraw(object):
            draw_per_virt = 1.0
            draw_to_virt = renpy.display.render.IDENTITY
            virt_to_draw = renpy.display.render.IDENTITY
            info = {"renderer": "probe", "models": False}

            def mutated_surface(self, surf):
                pass

            def load_texture(self, surf, *args, **kwargs):
                return surf

            def ready_one_texture(self):
                return False

            def __getattr__(self, name):
                raise AttributeError("probe draw: " + name)
        _il = renpy.display.imagelike
        _ip = (config.developer, renpy.display.draw, _il.Solid.render, _il.Frame.render)
        try:
            config.developer = False
            if renpy.display.draw is None:
                renpy.display.draw = _URMProbeDraw()
            _il.Solid.render = _il.Frame.render = _urm_fill_render
            _rr = renpy.display.render.render(_sd, config.screen_width, config.screen_height, 0, 0)
        finally:
            config.developer, renpy.display.draw, _il.Solid.render, _il.Frame.render = _ip
        _vv = []
        _rq = [_rr]
        while _rq:
            _rc = _rq.pop()
            for _c in _rc.children:
                if isinstance(_c[0], renpy.display.render.Render):
                    if _c[0].render_of and isinstance(_c[0].render_of[0], renpy.display.viewport.Viewport):
                        _vv.append(int(_c[0].height))
                    _rq.append(_c[0])
        _vm = _urmm_st.view
        _vh = config.screen_height - urmk_px(70) - ((urmk_px(48) + urmk_px(30) * len(_vm.later[:6])) if _vm.later else 0)
        _l.append("map_screen_room=%r" % ((len(_vv) == 1 and _vv[0] >= _vh - urmk_px(15)) or (_vv, _vh),))
        # ... and from the map with the forms of idea 13 in it: a faded
        # box, a "?" in a box, a "?" on a line.
        _urmm_st.view = _v13
        _sd = renpy.display.screen.ScreenDisplayable(renpy.display.screen.get_screen_variant("urm_route_map"), None, "screens")
        _sd.scope["_scope"] = None
        _sd.update()
        _l.append("map_screen_builds_idea13=%r" % (len(_v13.codes) == 1 and any(b.faded for b in _v13.boxes),))
        # The user's picks "1b2b3a" (2026-11-20), on THIS engine's store and
        # with its own displayables. 3a: the ways of a check are titled with
        # the test in words and a chip for what the player has - red when
        # the test fails as things stand, green when it holds - never with
        # "Yes", "Or" or the label a way jumps to. 2b: no ring where paths
        # meet, and where a check that only changes lines stands right
        # before one that splits the story there is ONE mark, the big
        # diamond, which says both. 1b: the hover text is a bubble in the
        # part of the map in view, beside its mark and clear of it.
        store.urmprobe_ws = "okay"
        store.urmprobe_wn = 2
        _urmm_st.cache.clear()
        _vp = urm_map_build(renpy.game.script.lookup("urmprobe_ways"), _ix)
        _wp3 = [(b.title, b.sub, b.have) for b in _vp.boxes if b.kind == "branch"]
        _l.append("map_picks_ways=%r" % (_wp3 == [("Urmprobe_ws is bad", None, ("you: okay", "loss")), ("Urmprobe_wn is at least 1", None, ("2/1", "gain")), ("Otherwise", None, None), ("Urmprobe_wn is at least 2", None, ("2/2", "gain")), ("Otherwise", None, None)] or _wp3,))
        _pk = [t for _x, _y, t in _vp.picks]
        _l.append("map_picks_marks=%r" % ((_pk == [urm_pick_tip(None), urm_pick_tip("Lines change with urmprobe_wl")] and not list(_vp.dots) and not list(_vp.marks) and not [b.title for b in _vp.boxes if b.ring]) or (_pk, list(_vp.dots), list(_vp.marks)),))
        _shown = (config.screen_width, config.screen_height - urmk_px(70))
        _top = (max(_vp.height, _shown[1]) - _vp.height) // 2
        _adj = renpy.display.behavior.Adjustment()
        _bad = []
        _spots = [(t, x - urmk_px(16), y - urmk_px(16), urmk_px(32), urmk_px(32)) for x, y, t in _vp.picks]
        for b in _vp.boxes:
            for _lead, _spot, _f, _h, _cells in b.draw:
                if _spot is not None:
                    _spots.append(_spot)
                for _k, _w, _t in _cells:
                    if _k in ("check", "code"):
                        _spots.append(_w)
        for _spot in _spots:
            _bw, _bx, _by, _bww, _bhh, _room = urm_map_bubble_at(_spot, _vp, 0, 0, _shown)
            _mx, _my = _spot[1], _spot[2] + _top
            _clear = _bx + _bww <= _mx or _mx + _spot[3] <= _bx or _by + _bhh <= _my or _my + _spot[4] <= _by
            _in = 0 <= _bx and _bx + _bww <= _shown[0] and 0 <= _by and _by + _bhh <= _shown[1]
            _made = urm_map_bubble(0, 0, _spot, _vp, _adj, _adj, _shown)
            if not (_clear and _in and _bw == _spot[0] and isinstance(_made[0], renpy.display.layout.MultiBox)):
                _bad.append((_spot, _bx, _by, _bww, _bhh, type(_made[0]).__name__))
        _l.append("map_picks_bubble=%r" % ((len(_spots) >= 2 and not _bad) or (len(_spots), _bad[:2]),))
        _urmm_st.view = _vp
        _sd = renpy.display.screen.ScreenDisplayable(renpy.display.screen.get_screen_variant("urm_route_map"), None, "screens")
        _sd.scope["_scope"] = None
        _sd.scope["_urmmTip"] = _spots[0]
        _sd.update()
        _l.append("map_screen_builds_picks=%r" % (_sd.scope.get("_urmmTip") == _spots[0],))
    except Exception as _e:
        import traceback as _tb
        _l.append("map_screen_builds=%r" % (_tb.format_exc()[-700:],))
    # The variable sheet, our own (drawing c, 2026-11-22), built by THIS
    # engine both ways in: URM's editor (URM_modify_value, whose dialog line
    # draws it) and the Flags list's Details (urmfl_flag_dialog, on our
    # layer). A number (the ladder), a yes/no value, a text value, a flag;
    # at rest, looking at a value, the box open, a rung's page, More open,
    # Delete asked: every expression evaluated, every displayable made.
    _kp = store._urmi_index
    _ki = renpy.display.interface
    _kc = renpy.game.contexts[:]
    try:
        store._urmi_index = lambda: _ix
        _urmp_bucket("panels").clear()
        # No window here: the box (an Input) asks the display for text
        # being typed, so stand in for it while the sheet is built.
        # (an older engine's bar asks it for a timeout)
        if _ki is None:
            class _URMNoWindow(object):
                text_editing = None

                frame_time = 0.0
                interact_time = None

                def text_event_in_queue(self):
                    return False

                def timeout(self, seconds):
                    pass
            renpy.display.interface = _URMNoWindow()
        _kg = renpy.game.interface
        if _kg is None:
            renpy.game.interface = renpy.display.interface
        # the story runs here (rollback on): where the sheet draws, with
        # every layer (this context was made after URM's and ours were added)
        renpy.game.contexts.append(renpy.execution.Context(True, renpy.game.context()))
        renpy.game.context().init_phase = False
        renpy.game.log.begin(True)
        _ksl = renpy.game.context().scene_lists
        for _klayer in list(config.layers) + list(getattr(config, "top_layers", ())):
            if _klayer not in _ksl.layers:
                _ksl.layers[_klayer] = []
                _ksl.at_list[_klayer] = {}
                _ksl.layer_at_list[_klayer] = (None, [])

        def _urm_sheet_sd(name, args, kwargs, layer):
            _sd = renpy.display.screen.ScreenDisplayable(renpy.display.screen.get_screen_variant(name), None, layer)
            _sd.scope["_scope"] = None
            _sd.scope["_args"] = args
            _sd.scope["_kwargs"] = kwargs
            _sd.update()
            return _sd

        def _urm_sheet_words(_sd):
            _wt, _wk = [], []
            _wq = [_sd.child]
            while _wq:
                _wd = _wq.pop()
                if isinstance(_wd, renpy.text.text.Text):
                    _wt.extend(t for t in _wd.text if isinstance(t, type(u"")))
                if isinstance(_wd, renpy.display.behavior.Keymap):
                    _wk.extend(getattr(_wd, "keymap", {}).keys())
                _wq.extend(getattr(_wd, "children", None) or ([_wd.child] if getattr(_wd, "child", None) is not None else []))
            return _wt, _wk

        _ui = _urmp_bucket("ui")
        try:
            _vs, _vw = {}, []
            for _vn, _vval in (("urmprobe_wn", 2), ("urmprobe_bx", False), ("urmprobe_ws", "okay")):
                setattr(store, _vn, _vval)
                _vs[_vn] = urm_panel(_vn)
                for _state in ("rest", "look", "box", "page", "more", "delete"):
                    _ui.clear()
                    if _state == "look":
                        urmi_preview_set(_vn, {"urmprobe_wn": 1, "urmprobe_bx": True, "urmprobe_ws": "bad"}[_vn])
                    elif _state == "box":
                        urmi_box_start(_vn)
                    elif _state == "page":
                        urmi_open_page(_vn, 0)
                    elif _state in ("more", "delete"):
                        _ui[("rung", _vn)] = 0
                        _ui[("more", _vn)] = True
                        _ui[("delete", _vn)] = _state == "delete"
                    _sd = _urm_sheet_sd("urmi_sheet_at", (), {"name": _vn}, _urmi_layer)
                    _vw.append((_vn, _state, urmi_sheet_title(_vn) in _urm_sheet_words(_sd)[0]))
            _vk = [(_vn, _vs[_vn].state, _vs[_vn].mode, [g.words for g in _vs[_vn].win_rungs]) for _vn in ("urmprobe_wn", "urmprobe_bx", "urmprobe_ws")]
            _vbad = [w for w in _vw if not w[2]]
            _l.append("var_sheet_builds=%r" % ((_vk == [("urmprobe_wn", "ready", "number", ["1 or more", "2 or more"]), ("urmprobe_bx", "ready", "bool", ["true", "false"]), ("urmprobe_ws", "ready", "value", ['"bad"'])] and not _vbad) or (_vk, _vbad),))
            # The ladder of a number: rows for 3, 2, 1, you at 2... here 0 to 3.
            _ui.clear()
            _ld = urmi_ladder("urmprobe_wn")
            _l.append("var_sheet_ladder=%r" % ([r[1] for r in _ld[1]] == [u"3", u"2", u"1", u"0"] or _ld[1],))
            # A sheet opened again starts on its first page with nothing looked
            # at: the screen's own "show" event clears it.
            _ui[("rung", "urmprobe_wn")] = 1
            _ui[("preview", "urmprobe_wn")] = 1
            _sd = renpy.display.screen.ScreenDisplayable(renpy.display.screen.get_screen_variant("urmi_sheet_at"), None, _urmi_layer)
            _sd.scope["_scope"] = None
            _sd.scope["_args"] = ()
            _sd.scope["_kwargs"] = {"name": "urmprobe_wn"}
            _sd.set_transform_event("show")
            _sd.update()
            _vr = (_ui.get(("rung", "urmprobe_wn"), "gone"), _ui.get(("preview", "urmprobe_wn"), "gone"))
            _l.append("var_sheet_resets_on_show=%r" % (_vr == ("gone", "gone") or _vr,))
            # A flag's Details: the same sheet, on our layer, titled by its name;
            # a side looked at is never switched; its close takes it off our layer.
            _fr = []
            for _state in ("rest", "look", "page"):
                _ui.clear()
                if _state == "look":
                    urmi_preview_set("urmprobe_bx", True)
                elif _state == "page":
                    urmi_open_page("urmprobe_bx", 0)
                _sd = _urm_sheet_sd("urmfl_flag_dialog", (), {"name": "urmprobe_bx"}, _urmi_layer)
                _fr.append(urmi_sheet_title("urmprobe_bx") in _urm_sheet_words(_sd)[0])
            _fr.append(store.urmprobe_bx)
            urmfl_details("urmprobe_bx")
            _fr.append(renpy.get_screen("urmfl_flag_dialog", layer=_urmi_layer) is not None)
            Function(renpy.hide_screen, "urmfl_flag_dialog", layer=_urmi_layer)()
            _fr.append(renpy.get_screen("urmfl_flag_dialog", layer=_urmi_layer) is None)
            _l.append("flag_sheet_builds=%r" % (_fr == [True, True, True, False, True, True] or _fr,))
            # The scopes a save keeps (the screen shown, not the sheet it uses):
            # the name, the engine's own; nothing of ours.
            _sc = []
            for _sname, _sargs, _skw, _slayer in (("urmi_sheet_at", (), {"name": "urmprobe_wn"}, _urmi_layer),
                                                  ("urmfl_flag_dialog", (), {"name": "urmprobe_bx"}, _urmi_layer)):
                _sd = _urm_sheet_sd(_sname, _sargs, _skw, _slayer)
                for _sk, _sv in _sd.scope.items():
                    _st = type(_sv)
                    if _st.__module__.startswith("store") :
                        _sc.append((_sname, _sk, _st.__name__))
            _l.append("var_sheet_scope_plain=%r" % (_sc or True,))
        except Exception:
            import traceback as _tb
            _l.append("var_sheet_builds=%r" % (_tb.format_exc()[-700:],))
        # The corner card holds the skip. One primary click through the
        # quick-menu catcher and the engine's dialogue handler must both
        # end the interaction and restore the previous mode.
        def _urm_probe_skip_resume(_l):
            _kp = (config.skipping, getattr(_urmm_st, "check_in_view", None), store._urm_gate_ahead,
                   _urm_setting("stopSkippingOnPathDetection"), _urm_setting("showPathsNotification"))
            _kf = renpy.game.context().scene_lists
            _kfocused = _kf.focused
            _kpre = renpy.game.preferences
            _ksaved = (config.allow_skipping, store._skipping, config.afm_callback,
                       _kpre.afm_enable, _kpre.afm_time, _kpre.desktop_rollback_side,
                       _kpre.mobile_rollback_side, renpy.exports.rollback)
            _kafter_rollback, _khere = renpy.game.after_rollback, store._urmsg_here
            try:
                import pygame_sdl2 as _kpg
                _urm_setting_set("stopSkippingOnPathDetection", True)
                _urm_setting_set("showPathsNotification", True)
                config.allow_skipping = store._skipping = True
                _kpre.afm_enable = False
                _kpre.desktop_rollback_side = _kpre.mobile_rollback_side = "disable"
                _kx, _ky = config.screen_width // 2, config.screen_height // 2
                _kclick = _kpg.event.Event(_kpg.MOUSEBUTTONUP, button=1, pos=(_kx, _ky), mod=0)
                _kpress = _kpg.event.Event(_kpg.MOUSEBUTTONDOWN, button=1, pos=(_kx, _ky), mod=0)
                _ksay = renpy.display.behavior.SayBehavior()
                _kf.focused = _ksay

                def _kdispatch(ev, x=_kx, st=0):
                    try:
                        urmr_middle_click.event(ev, x, _ky, st)
                        return _ksay.event(ev, x, _ky, st)
                    except renpy.display.core.IgnoreEvent:
                        return "ignored"

                _kr = []
                for _kmode in ("slow", "fast"):
                    _kg = object()
                    store._urm_gate_ahead = lambda: _kg
                    config.skipping = _kmode
                    _urmm_stop_at_check()
                    _kbefore = config.skipping
                    _kdismissed = _kdispatch(_kclick)
                    _kafter = config.skipping
                    _urmm_stop_at_check()
                    _kr.append((_kbefore, _kdismissed, _kafter, config.skipping))
                _l.append("click_advances_dialogue_and_resumes_skip=%r" % (
                    _kr == [(None, True, "slow", "slow"), (None, True, "fast", "fast")] or _kr,))

                _kbindings = []
                _kbind_calls = []

                def _kbound_dismiss():
                    _kbind_calls.append(config.skipping)
                    return True

                for _kbinding, _kbound, _kother in (("mouseup_1", _kclick, _kpress),
                                                    ("mousedown_1", _kpress, _kclick)):
                    _ksay = renpy.display.behavior.SayBehavior(dismiss=[_kbinding],
                                                               allow_dismiss=_kbound_dismiss)
                    _kf.focused = _ksay
                    for _kmode in ("slow", "fast"):
                        del _kbind_calls[:]
                        config.skipping = _kmode
                        _urm_stop_skipping()
                        _kunbound = (_kdispatch(_kother), config.skipping, _urm_skip_held())
                        _kresult = (_kdispatch(_kbound), config.skipping, _urm_skip_held())
                        _kbindings.append((_kbinding, _kmode, _kunbound, _kresult, list(_kbind_calls)))
                _kbind_expected = [(binding, mode, (None, None, mode), (True, mode, None), [None])
                                   for binding in ("mouseup_1", "mousedown_1")
                                   for mode in ("slow", "fast")]
                _l.append("skip_resumes_on_configured_click_phase=%r" % (
                    _kbindings == _kbind_expected or _kbindings,))
                _ksay = renpy.display.behavior.SayBehavior()
                _kf.focused = _ksay

                def _khold():
                    config.skipping = "slow"
                    _urm_stop_skipping()

                _kedges = {}
                _kcalls = []

                def _kdeny():
                    _kcalls.append(config.skipping)
                    return False

                def _kapprove():
                    _kcalls.append(config.skipping)
                    return True

                _khold()
                _ksay.allow_dismiss = _kdeny
                _kedges["denied"] = (_kdispatch(_kclick), config.skipping, _urm_skip_held(),
                                      _ksay.allow_dismiss is _kdeny, list(_kcalls))
                _ksay.allow_dismiss = _kapprove
                _kedges["approved"] = (_kdispatch(_kclick), config.skipping, _urm_skip_held(),
                                        _ksay.allow_dismiss is _kapprove, list(_kcalls))

                def _kraise():
                    raise ValueError("dismiss callback")

                _khold()
                _ksay.allow_dismiss = _kraise
                try:
                    _kdispatch(_kclick)
                except ValueError as _ke:
                    _kedges["callback_raises"] = (str(_ke), config.skipping, _ksay.allow_dismiss is _kraise)
                _ksay.allow_dismiss = None

                # The dialogue handler itself checks focus and the rollback side.
                _khold()
                _kf.focused = renpy.display.layout.Null()
                _kedges["unfocused"] = (_kdispatch(_kclick), config.skipping, _urm_skip_held())
                _kf.focused = _ksay
                _krollbacks = []
                renpy.exports.rollback = lambda: _krollbacks.append(True)
                _kpre.desktop_rollback_side = _kpre.mobile_rollback_side = "left"
                _kedges["rollback_side"] = (_kdispatch(_kclick, x=0), config.skipping, _krollbacks)
                _kpre.desktop_rollback_side = _kpre.mobile_rollback_side = "disable"

                # An AFM timeout can return True on the same mouse event, without
                # running allow_dismiss. It must never resume held skipping.
                _kpre.afm_enable = True
                _kpre.afm_time = 10
                config.afm_callback = None
                _ksay = renpy.display.behavior.SayBehavior(afm="probe", allow_dismiss=_kdeny)
                _kf.focused = _ksay
                _ktime = _kpg.event.Event(renpy.display.core.TIMEEVENT, modal=False, mod=0)
                _kedges["afm"] = (_kdispatch(_kclick, st=999), _kdispatch(_ktime, st=999),
                                  config.skipping, list(_kcalls))
                _kpre.afm_enable = False
                _ksay = renpy.display.behavior.SayBehavior()
                _kf.focused = _ksay
                _kkey = _kpg.event.Event(_kpg.KEYDOWN, key=_kpg.K_SPACE, mod=0, unicode=u" ", repeat=False, scancode=0)
                _kedges["key"] = (_kdispatch(_kkey), config.skipping)

                config.allow_skipping = False
                _kedges["config_disallows"] = (_kdispatch(_kclick), config.skipping)
                config.allow_skipping = True
                _khold()
                store._skipping = False
                _kedges["game_disallows"] = (_kdispatch(_kclick), config.skipping)
                store._skipping = True

                _khold()
                config.skipping = "fast"
                _urmr_interact()
                _kedges["manual_stop"] = (_kdispatch(_kclick), config.skipping, _kdispatch(_kclick), config.skipping)

                _khold()
                renpy.game.after_rollback = True
                _urmr_interact()
                renpy.game.after_rollback = _kafter_rollback
                _kedges["rollback"] = (_kdispatch(_kclick), config.skipping)

                _khold()
                for _kc in config.after_load_callbacks:
                    if _kc is _urmr_forget_resume:
                        _kc()
                _kedges["load"] = (_kdispatch(_kclick), config.skipping)

                _khold()
                _kelsewhere = object()
                store._urmsg_here = lambda: _kelsewhere
                _urmr_interact()
                _kedges["another_statement"] = (_kdispatch(_kclick), config.skipping)

                _kexpected = {
                    "denied": ("ignored", None, "slow", True, [None]),
                    "approved": (True, "slow", None, True, [None, None]),
                    "callback_raises": ("dismiss callback", None, True),
                    "unfocused": (None, None, "slow"),
                    "rollback_side": ("ignored", None, [True]),
                    "afm": (True, True, None, [None, None]),
                    "key": (True, None),
                    "config_disallows": (True, None),
                    "game_disallows": (True, None),
                    "manual_stop": ("ignored", None, True, None),
                    "rollback": (True, None),
                    "load": (True, None),
                    "another_statement": (True, None),
                }
                _l.append("skip_resume_respects_engine_dismissal=%r" % (_kedges == _kexpected or _kedges,))
            except Exception:
                import traceback as _tb
                _l.append("skip_resume_respects_engine_dismissal=%r" % (_tb.format_exc()[-500:],))
            finally:
                renpy.game.after_rollback, store._urmsg_here = _kafter_rollback, _khere
                (config.allow_skipping, store._skipping, config.afm_callback,
                 _kpre.afm_enable, _kpre.afm_time, _kpre.desktop_rollback_side,
                 _kpre.mobile_rollback_side, renpy.exports.rollback) = _ksaved
                _kf.focused = _kfocused
                config.skipping, _urmm_st.check_in_view, store._urm_gate_ahead = _kp[:3]
                _urm_setting_set("stopSkippingOnPathDetection", _kp[3])
                _urm_setting_set("showPathsNotification", _kp[4])
                _urm_skip_forget()

        _urm_probe_skip_resume(_l)
        # What lands on the sheet is its own (the user's must 2): over a say
        # and the engine's own keys, a click on an empty spot of the sheet
        # and the wheel over it are taken; with the box open, Enter, Space,
        # Tab, PageUp and Esc are too; a click beside it reaches the say.
        import pygame_sdl2 as _pg

        class _URMSay(renpy.display.layout.Null):
            def event(self, ev, x, y, st):
                if ev.type == _pg.MOUSEBUTTONUP and getattr(ev, "button", 0) == 1:
                    return "said"
                return None

        _dr = renpy.display.draw
        _ip = (config.developer, _dr, _il.Solid.render, _il.Frame.render)

        def _urm_sheet_draw(_name, _args, _kwargs, _layer):
            _root = renpy.display.layout.Fixed()
            _root.add(_URMSay())
            for _u in config.underlay:
                _root.add(_u)
            _sd = _urm_sheet_sd(_name, _args, _kwargs, _layer)
            _sd.visit_all(lambda d: d.per_interact())
            _root.add(_sd)
            renpy.display.render.render_screen(_root, config.screen_width, config.screen_height)
            renpy.display.focus.take_focuses()
            return _root, _sd

        def _urm_dispatch(_root, _evs):
            _out = []
            for _ev, _x, _y in _evs:
                renpy.display.focus.mouse_handler(None, _x, _y)
                try:
                    _rv = _root.event(_ev, _x, _y, 0)
                    _out.append("said" if _rv == "said" else "passed")
                except renpy.display.core.IgnoreEvent:
                    _out.append("taken")
                except Exception as _ee:
                    _out.append("%s: %s" % (type(_ee).__name__, _ee))
            return _out

        def _urm_sheet_events(_name, _args, _kwargs, _layer, _evs):
            _root, _sd = _urm_sheet_draw(_name, _args, _kwargs, _layer)
            return _urm_dispatch(_root, _evs)

        def _urm_click(x, y):
            return [(_pg.event.Event(_pg.MOUSEBUTTONDOWN, button=1, pos=(x, y), mod=0), x, y),
                    (_pg.event.Event(_pg.MOUSEBUTTONUP, button=1, pos=(x, y), mod=0), x, y)]

        def _urm_key(k, u=u""):
            return (_pg.event.Event(_pg.KEYDOWN, key=k, mod=0, unicode=u, repeat=False, scancode=0), 0, 0)

        # (Each of the three checks below stands on its own, so a build
        # that fails one still runs the others.)
        try:
            config.developer = False
            if renpy.display.draw is None:
                renpy.display.draw = _URMProbeDraw()
            _il.Solid.render = _il.Frame.render = _urm_fill_render
            _W, _H = config.screen_width, config.screen_height
            _sx, _sy = _W - urmk_px(16 + 40), _H - urmk_px(40)
            _ui.clear()
            _ev1 = _urm_sheet_events("urmi_sheet_at", (), {"name": "urmprobe_wn"}, _urmi_layer,
                                     _urm_click(_sx, _sy)
                                     + [(_pg.event.Event(_pg.MOUSEBUTTONDOWN, button=4, pos=(_sx, _sy), mod=0), _sx, _sy)]
                                     + _urm_click(urmk_px(100), urmk_px(100)))
            # the box open (a build whose box is always open has no step)
            if hasattr(store, "urmi_box_start"):
                urmi_box_start("urmprobe_wn")
            _ev2 = _urm_sheet_events("urmi_sheet_at", (), {"name": "urmprobe_wn"}, _urmi_layer,
                                     [_urm_key(_pg.K_TAB, (u"%c" % 9)), _urm_key(_pg.K_PAGEUP), _urm_key(_pg.K_RETURN, (u"%c" % 13)),
                                      _urm_key(_pg.K_SPACE, u" "), _urm_key(_pg.K_ESCAPE)])
            _ev3 = _urm_sheet_events("urmfl_flag_dialog", (), {"name": "urmprobe_bx"}, _urmi_layer, _urm_click(_sx, _sy))
            _l.append("var_sheet_takes_its_events=%r" % ((_ev1, _ev2, _ev3) == (["taken"] * 5, ["taken"] * 5, ["taken", "taken"]) or (_ev1, _ev2, _ev3),))
        except Exception:
            import traceback as _tb
            _l.append("var_sheet_takes_its_events=%r" % (_tb.format_exc()[-500:],))
        try:
            _ui.clear()
            _draw_args = ("urmi_sheet_at", (), {"name": "urmprobe_bx"}, _urmi_layer)
            _root, _sd = _urm_sheet_draw(*_draw_args)
            _viewports = []
            _sd.visit_all(lambda d: _viewports.append(d) if isinstance(d, renpy.display.viewport.Viewport) else None)
            _vp = _viewports[0]
            # An ordinary yes/no sheet leaves room for the story above and
            # beside it, with no scroll range when all the rows fit.
            _size = (_vp.xadjustment.page, _vp.yadjustment.page, _vp.yadjustment.range)
            _ok_size = _size[0] < urmk_px(500) and 0 < _size[1] < urmk_px(450) and _size[2] == 0
            _l.append("var_sheet_fits_content=%r" % (_ok_size or _size,))
            _more = next(f for f in renpy.display.focus.focus_list
                         if f.x is not None and f.widget._get_tooltip() == u"More")
            _x, _y = int(_more.x + _more.w / 2), int(_more.y + _more.h / 2)
            _urm_dispatch(_root, _urm_click(_x, _y))
            _tip_after_click = GetTooltip()
            _root, _sd = _urm_sheet_draw(*_draw_args)
            _opened = u"Copy name" in _urm_sheet_words(_sd)[0]
            _urm_dispatch(_root, _urm_click(_x, _y))
            _root, _sd = _urm_sheet_draw(*_draw_args)
            _closed = u"Copy name" not in _urm_sheet_words(_sd)[0]
            _result = (_tip_after_click, _opened, _closed)
            _l.append("var_sheet_more_click_while_hovered=%r" % (_result == (u"More", True, True) or _result,))
        except Exception:
            import traceback as _tb
            _l.append("var_sheet_more_click_while_hovered=%r" % (_tb.format_exc()[-700:],))
        finally:
            config.developer, renpy.display.draw, _il.Solid.render, _il.Frame.render = _ip
            _ui.clear()
        # A game's menus carry our layer with them: there the sheet draws
        # nothing and binds no key, both ways in.
        try:
            renpy.game.contexts.append(renpy.execution.Context(False, renpy.game.context(), clear=True))
            try:
                _nt, _nk = _urm_sheet_words(_urm_sheet_sd("urmi_sheet_at", (), {"name": "urmprobe_wn"}, _urmi_layer))
                _ft, _fk = _urm_sheet_words(_urm_sheet_sd("urmfl_flag_dialog", (), {"name": "urmprobe_bx"}, _urmi_layer))
            finally:
                renpy.game.contexts.pop()
            _l.append("var_sheet_not_in_menus=%r" % ((not _nt and not _nk and not _ft and not _fk) or (_nt[:6], _nk, _ft[:6], _fk),))
        except Exception:
            import traceback as _tb
            _l.append("var_sheet_not_in_menus=%r" % (_tb.format_exc()[-500:],))
        # A Set holds, and when something puts the value back at the next
        # line (our freeze does), the sheet says so: never a quiet undo.
        try:
            store.urmprobe_wn = 2
            _sv = [urmi_set("urmprobe_wn", 3), store.urmprobe_wn, urmi_snapped("urmprobe_wn")]
            _urm_freeze("urmprobe_wn")
            try:
                store.urmprobe_wn = 5
                _urm_hold()
                _frozen = store.urmprobe_wn
                urmi_set("urmprobe_wn", 5)
                _urm_hold()
                _updated = store.urmprobe_wn
            finally:
                _urm_unfreeze("urmprobe_wn")
            _l.append("var_sheet_freeze_uses_our_set=%r" % ((_frozen, _updated) == (3, 5) or (_frozen, _updated),))
            store.urmprobe_wn = 3
            _sv += [store.urmprobe_wn, urmi_snapped("urmprobe_wn")]
            _l.append("var_sheet_set_says_put_back=%r" % (_sv == [None, 3, None, 3, u"The game put this back to 3"] or _sv,))
        except Exception:
            import traceback as _tb
            _l.append("var_sheet_set_says_put_back=%r" % (_tb.format_exc()[-500:],))
    except Exception as _e:
        import traceback as _tb
        _l.append("var_sheet_builds=%r" % (_tb.format_exc()[-700:],))
    finally:
        store._urmi_index = _kp
        renpy.game.contexts[:] = _kc
        if _ki is None:
            renpy.display.interface = None
            renpy.game.interface = _kg
        _urmp_bucket("ui").clear()
        _urmp_bucket("panels").clear()
    open(_po.path.join(config.basedir, "urm_probe.txt"), "w").write("\\n".join(_l))
    _po._exit(0)

label urmprobe_maze:
    menu:
        "A":
            jump urmprobe_a
        "B":
            jump urmprobe_b
    label urmprobe_a:
        $ urmprobe_x = 1
        "Text."
        jump urmprobe_done
    label urmprobe_b:
        $ urmprobe_y = 2
        menu:
            "C":
                $ urmprobe_z = 3
                jump urmprobe_done
            "D":
                jump urmprobe_maze
label urmprobe_done:
    if urmprobe_x == 1:
        $ urmprobe_after = 1
    return

label urmprobe_tie:
    menu:
        "G":
            jump urmprobe_tie_later
        "H":
            jump urmprobe_tie_earlier
label urmprobe_tie_earlier:
    $ urmprobe_te = 1
    jump urmprobe_tie_later
label urmprobe_tie_later:
    $ urmprobe_tl = 1
    jump urmprobe_tie_earlier

label urmprobe_caller:
    call urmprobe_called
label urmprobe_caller_back:
    $ urmprobe_back = 1
    return

label urmprobe_called:
    menu:
        "E":
            $ urmprobe_e = 1
            return
        "F":
            pass
    return

label urmprobe_branch:
    "Hello."
    if urmprobe_bx:
        "Only with it."
    "Shared again."
    "And on."
    return

label urmprobe_hub:
    menu:
        set urmprobe_seen
        "I":
            $ urmprobe_i = 1
            jump urmprobe_hub
    $ urmprobe_out = 1
    menu:
        "J" if urmprobe_j >= 3:
            $ urmprobe_jj = 1
        "K" if urmprobe_k >= 3:
            $ urmprobe_kk = 1
    pass
    menu:
        "L":
            $ urmprobe_l = 1
        "M":
            pass
    return

label urmprobe_ways:
    if urmprobe_ws == "bad":
        jump urmprobe_ways_back
    elif urmprobe_wn >= 1:
        menu:
            "S":
                $ urmprobe_wn += 1
            "T":
                pass
        jump urmprobe_ways_back
    else:
        jump urmprobe_ways_back
label urmprobe_ways_back:
    "Text."
    if urmprobe_wl == "x":
        "Text."
    if urmprobe_wn >= 2:
        jump urmprobe_ways_a
    else:
        jump urmprobe_ways_b
label urmprobe_ways_a:
    $ urmprobe_wa = 1
    return
label urmprobe_ways_b:
    $ urmprobe_wb = 1
    return

label urmprobe_mirror:
    if urmprobe_mu:
        menu:
            "N":
                jump urmprobe_mirror_scene
            "O":
                "Back 1."
                "Back 2."
                "Back 3."
                "Back 4."
                "Back 5."
                "Back 6."
                "Back 7."
                "Back 8."
                "Back 9."
                "Back 10."
                "Back 11."
                "Back 12."
                "Back 13."
                "Back 14."
                jump urmprobe_mirror_main
    else:
        menu:
            "N":
                jump urmprobe_mirror_scene
            "O":
                "Home 1."
                "Home 2."
                "Home 3."
                "Home 4."
                "Home 5."
                "Home 6."
                "Home 7."
                "Home 8."
                "Home 9."
                "Home 10."
                "Home 11."
                "Home 12."
                "Home 13."
                "Home 14."
                jump urmprobe_mirror_main
label urmprobe_mirror_scene:
    "Scene 1."
    "Scene 2."
    "Scene 3."
    "Scene 4."
    "Scene 5."
    "Scene 6."
    "Scene 7."
    "Scene 8."
    "Scene 9."
    "Scene 10."
    "Scene 11."
    "Scene 12."
    "Scene 13."
    "Scene 14."
    "Scene 15."
    "Scene 16."
    jump urmprobe_mirror_main
label urmprobe_mirror_main:
    menu:
        "Q":
            $ urmprobe_q = 1
        "R":
            pass
    return
'''

# The font list scenario (My Femdom Wife 0.7, the user's report of
# 2026-11-20). Asleep unless URM_GATE_FONT_LIST is set: then the game's
# story does what that game's does, word for word and at its priority, and a
# check right after URM and URM+ have started says how it went and ends the
# run. With URM as it shipped the engine never gets there: URM's FontsHandler
# stops the game at init 999 ("list indices must be integers").
FONT_LIST = u'''init python:
    import os as _urmgf_os
    _urmgf_on = bool(_urmgf_os.environ.get("URM_GATE_QUIRKS"))
    if _urmgf_on:
        config.font_transforms = ["smooth"]
        _urmgf_own = config.font_transforms
        # A game that opens its own links: config.hyperlink_callback (Aug
        # 2026). It took every link from URM, whose variable and label
        # editors are the "URMVarDialog" and "URMLabelDialog" protocols.
        def _urmgf_link(target):
            store.urmgf_link_opened = target
        config.hyperlink_callback = _urmgf_link
        # A game with its own EndReplay() that takes no argument (Aug 31
        # 2026): URM's watch panel calls EndReplay(False), and the game did
        # not start.
        def EndReplay():
            store.urmgf_end_replay = True
        # A game that sets its screen size at init 0, after URM has sized
        # its look (Star Periphery 7.7: gui.init in gui.rpy, no init
        # offset; 2026-11-21). URM's buttons and text came out sized for
        # the size before.
        _urmgf_h = 720 if config.screen_height == 1080 else 1080
        config.screen_width = _urmgf_h * 16 // 9
        config.screen_height = _urmgf_h

# After 00compat (init 1100), which copies a game's link callback into the
# style's link functions.
init 1200 python:
    if _urmgf_on:
        _urmgf = []
        try:
            _urmgf.append("font_list_no_urm=%r" % (not hasattr(store, "x52URM") and "x52Overlay" not in config.layers,))
            _urmgf.append("font_list_urm_plus_started=%r" % (hasattr(store, "urm_panel") and hasattr(store, "_urmft_available"),))
            _urmgf.append("font_list_game_keeps_its_own=%r" % ((config.font_transforms is _urmgf_own and len(_urmgf_own) == 1 and _urmgf_own[0] == "smooth") or repr(config.font_transforms),))
            _urmgf.append("font_list_no_font_offered=%r" % (len(_urmft_available()) == 0 or [r[0] for r in _urmft_available()],))
            _urmgf.append("font_list_no_override_asked=%r" % (renpy.game.preferences.font_transform is None or renpy.game.preferences.font_transform,))
        except Exception as _e:
            _urmgf.append("font_list_error=%r" % (_e,))
        try:
            for _st in list(getattr(renpy.translation, "deferred_styles", ())):
                _st.apply()
            renpy.style.build_styles()
            config.hyperlink_callback("propgame:news")
            _urmgf.append("quirk_link_callback_kept=%r" % (store.urmgf_link_opened == "propgame:news",))
        except Exception as _e:
            _urmgf.append("quirk_link_callback_kept=%r" % (_e,))
        try:
            _urmgf_l = (urmk_px(24), urmk_px(15))
            _urmgf.append("quirk_late_size_look_sized=%r" % (_urmgf_l == tuple(int(v * _urmgf_h / 1080.0 + .5) for v in (24, 15)) or (_urmgf_l, config.screen_height),))
        except Exception as _e:
            _urmgf.append("quirk_late_size_look_sized=%r" % (_e,))
        try:
            store.urmgf_end_replay = None
            EndReplay()
            _urmgf.append("quirk_end_replay_kept=%r" % (store.urmgf_end_replay is True,))
        except Exception as _e:
            _urmgf.append("quirk_end_replay_kept=%r" % (_e,))
        open(_urmgf_os.path.join(config.basedir, "urm_probe_fonts.txt"), "w").write("\\n".join(_urmgf))
        _urmgf_os._exit(0)

'''

FONT_LIST_LINES = ("font_list_no_urm", "font_list_urm_plus_started",
                   "font_list_game_keeps_its_own", "font_list_no_font_offered",
                   "font_list_no_override_asked",
                   "quirk_link_callback_kept", "quirk_end_replay_kept",
                   "quirk_late_size_look_sized")


def font_list(py, flags, start, copy, env):
    """The engine once more, as a game with the quirks real games had: a
    list in config.font_transforms, its own link callback, its own
    EndReplay, its screen size set after URM sized its look. Returns the
    problems found."""

    report = os.path.join(copy, "urm_probe_fonts.txt")
    trace = os.path.join(copy, "traceback.txt")
    for path in (report, trace):
        if os.path.exists(path):
            os.remove(path)
    listed = dict(env)
    listed["URM_GATE_QUIRKS"] = "1"
    try:
        subprocess.run([py] + flags + [start, ".", "lint"], cwd=copy, env=listed,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    except subprocess.TimeoutExpired:
        return ["quirky game: the engine timed out"]
    # Ren'Py 8.5 in lint mode notes an error raised while loading and goes
    # on (seen 2026-11-20: URM's FontsHandler raised, the check below still
    # ran). A player gets the error screen. So a traceback is a failure,
    # whether or not the check was reached.
    if raised(copy):
        return ["quirky game: the game raised while loading: %s" % raised(copy)]
    if not os.path.exists(report):
        return ["quirky game: the game did not load, and left no traceback"]
    values = dict(l.split("=", 1) for l in open(report).read().splitlines() if "=" in l)
    problems = ["quirky game: %s=%s" % (key, value)
                for key, value in sorted(values.items()) if value != "True"]
    problems += ["quirky game: %s missing" % key for key in FONT_LIST_LINES if key not in values]
    return problems


BUILD_PROBE = u'''import os, sys
sys.path.insert(0, sys.argv[3])
import urmfix
urmfix.BASE = os.path.abspath(sys.argv[1])
renpy = urmfix.load_engine()
name = sys.argv[4] if len(sys.argv) > 4 else "zzzz_urm_probe"
payload, digest = urmfix.compile_rpy(renpy, sys.argv[2], name + ".rpy")
urmfix.write_archive(os.path.join(urmfix.BASE, "game", name + ".rpa"),
                     {name + ".rpyc": urmfix.write_native_rpyc(renpy, [(1, payload)], digest)})
print("probe built")
'''

# With URM's archive removed: URM+ runs on its own. Its start-up block (init
# 998) ran, told the pieces URM is not there and hooked nothing - URM's
# update check and the game's font table untouched - and every one of its
# init 999 blocks ran: a name each of them defines is there. Then the
# engine's lint is replaced by a run of URM+ in a game under way (a context
# of its own, made after init, so its scene lists hold every layer):
#   - every interact callback runs;
#   - our screens are on our own layer, which the engine keeps: after its
#     clean-out at the end of an interaction (overlay_layers cleared, the
#     transient layers replaced) each is still there, the same object;
#   - the URM+ menu offers its entries, the route map among them; each
#     entry opens, and every screen of ours then shown draws;
#   - standing at a menu of the prop's story, Alt+G's way opens the route
#     map on our layer: it draws its title and the menu's choices, in a
#     part as high as the room under its header (no bar of the game's own
#     takes it), and closes;
#   - standing there and at the line before its check (prop_tl): both
#     corner cards draw with their words, Take and the route-map button;
#     Take on the way is remembered; the URM+ button draws with what the
#     branch chip says; an alert on the
#     checked flag shows its banner, which draws with the flag's name;
#   - the cards' titles open our code view on our layer, the scene around
#     the menu with its lines marked; code longer and wider than the panel
#     draws in a part as high as the panel's room and scrolls both ways;
#     in a game's menu (a context of its own) it draws nothing; it closes;
#   - the Flags list (one flag stubbed) draws with Details, which opens
#     our variable sheet on our layer, titled by the flag; its Esc takes it
#     off again;
#   - a resume save left from play with URM (it names URM's progress bar
#     callback, as 84% of real saves do) is offered as the game starts and
#     opens: the engine's own unpickler reads it.
# Each line must end in =True.
#
# The same probe also carries an old save across (URM_ABSENT_STEP, the
# engine's lint command replaced): "save", with URM there, saves a game
# whose shown screens hold an object of every URM and URM+ name real saves
# hold (lab/real_save_names.md; _URMRMiddleClick pickled the way builds
# before 2026-11-17 did; the three of URM+'s own are its real ones); "load", with URM's archive removed, loads it
# through the engine's own loader, updates the screens the engine draws
# after a load and saves again; "back", with URM back, loads that save.
ABSENT_PROBE = u'''init 1999 python:
    import os as _po
    _ua_step = _po.environ.get("URM_ABSENT_STEP", "lint")
    _pa_lines = [
        "early_ran=%r" % (hasattr(store, "_urm_own_layer"),),
        "no_urm=%r" % (not hasattr(store, "x52URM"),),
        "own_layer=%r" % (_urmi_layer == "urmplus",),
        "original_screens_absent=%r" % (not renpy.has_screen("URM_main"),),
        "every_block_ran=%r" % ([_n for _n in @@LATER_NAMES@@ if not hasattr(store, _n)] or True,),
    ]

    def _pa_write():
        with open(_po.path.join(config.basedir, "urm_absent.txt"), "w") as _f:
            _f.write("\\n".join(_pa_lines) + "\\n")

    if _ua_step == "lint":
        _pa_write()


    def _ua_out(lines):
        with open(_po.path.join(config.basedir, "urm_absent_%s.txt" % _ua_step), "w") as _f:
            _f.write("\\n".join(lines) + "\\n")
        _po._exit(0)

    def _ua_keep(slot):
        """The save's pickle, beside the game for the gate to read."""
        import glob, zipfile
        path = sorted(glob.glob(_po.path.join(config.savedir, slot + "*.save")))
        with open(_po.path.join(config.basedir, slot + ".log"), "wb") as f:
            f.write(zipfile.ZipFile(path[0]).read("log") if path else b"")

    def _ua_save_places():
        """Every folder the engine saves to that is neither the gate's own
        home nor this scratch copy (the player's own saves): none."""
        def norm(p):
            return _po.path.normcase(_po.path.abspath(p))
        mine = [norm(p) for p in (_po.environ.get("URM_GATE_HOME"), config.basedir) if p]
        places = [config.savedir] + [getattr(l, "directory", None) for l in
                                     getattr(renpy.loadsave.location, "locations", ())]
        return [p for p in places if p and not any(norm(p).startswith(m) for m in mine)]

    def _ua_checkpoint():
        """A statement begins and ends, as in play: the log keeps a copy
        of the context then."""
        ctx = renpy.game.context()
        ctx.init_phase = False
        ctx.rollback = True
        renpy.game.log.begin(True)
        store.main_menu = False
        renpy.game.log.complete(True)
        renpy.game.interface.started = True
        import struct, zlib
        def chunk(kind, data):
            body = kind + data
            return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)
        renpy.game.interface.screenshot = (
            bytes(bytearray((137, 80, 78, 71, 13, 10, 26, 10)))
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(bytearray(4)))) + chunk(b"IEND", b""))
        renpy.take_screenshot = lambda *a, **k: None

    # A feature's status on the URM+ button (17_hub): yellow, its hide a
    # function of the game's store, as a feature's would be.
    def _pa_lint():
        import sys, traceback
        import pygame_sdl2 as pygame
        said = []
        # a window drawn here is a picture of the whole of it, in one frame
        # (16_kit, frame first: the frame after is the kit check's)
        store._urmk_live = lambda: False

        class Tee(object):
            def write(self, s):
                said.append(s)

            def flush(self):
                pass

        def line(name, problems):
            _pa_lines.append("%s=%r" % (name, problems or True))

        def last():
            return traceback.format_exc().strip().splitlines()[-1][:200]

        def require(condition, detail):
            if not condition:
                raise AssertionError(detail)

        real_out = sys.stdout
        sys.stdout = Tee()
        try:
            renpy.python.make_clean_stores()
            renpy.exports.execute_default_statement(True)
            renpy.game.contexts.append(renpy.execution.Context(True))
            ctx = renpy.game.context()
            ctx.init_phase = False          # as in play
            ctx.rollback = True
            renpy.game.log.begin(True)
            store.main_menu = False
            # What play with URM leaves in a save: URM's progress bar
            # callback, by name. Made here with a class of that name, which
            # goes again once the save is made, unless URM+ itself keeps
            # one for old saves.
            native = bytes if sys.version_info[0] == 2 else str
            urm_name = native("store.x52URM")
            made = urm_name not in sys.modules
            if made:
                held = renpy.python.StoreDict()
                held["__name__"] = urm_name
                sys.modules[urm_name] = renpy.python.StoreModule(held)
            urm_module = sys.modules[urm_name]
            if made or not hasattr(urm_module, "progressDragged"):
                setattr(urm_module, "progressDragged",
                        type(native("progressDragged"), (object,), {"__module__": urm_name}))
            store.urmprobe_urm_left = urm_module.progressDragged
            renpy.game.log.complete(True)
            renpy.game.log.freeze(None)
            renpy.game.interface.started = True
            import struct, zlib

            def chunk(kind, data):
                body = kind + data
                return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)
            renpy.game.interface.screenshot = (
                bytes(bytearray((137, 80, 78, 71, 13, 10, 26, 10)))
                + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(bytes(bytearray([0] + [90] * 12) * 4)))
                + chunk(b"IEND", b""))
            resume_made = None
            places = _ua_save_places()
            if places or not _po.environ.get("URM_GATE_HOME"):
                resume_made = "not made: saves would go to %r" % (places or "no URM_GATE_HOME",)
            else:
                try:
                    renpy.save("_reload-1", u"")
                except Exception:
                    resume_made = last()
            store.urmprobe_urm_left = None
            if made:
                del sys.modules[urm_name]
            renpy.style.rebuild()
            renpy.display.screen.prepare_screens()
            __import__("renpy.display.swdraw")
            config.developer = False
            sl = ctx.scene_lists

            def surface(w, h):
                return pygame.Surface((max(1, int(w)), max(1, int(h))), pygame.SRCALPHA)

            class Draw(object):
                draw_per_virt = 1.0
                draw_to_virt = renpy.display.render.IDENTITY
                virt_to_draw = renpy.display.render.IDENTITY
                info = {"renderer": "sw", "models": False}

                def mutated_surface(self, surf):
                    pass

                def load_texture(self, surf, *args, **kwargs):
                    return surf.copy()

                def ready_one_texture(self):
                    return False

                def render_to_texture(self, what, alpha):
                    return surface(*what.get_size())

                def solid_texture(self, w, h, color):
                    return surface(w, h)

                def __getattr__(self, name):
                    raise AttributeError("probe draw: " + name)
            renpy.display.draw = Draw()

            def drawn(name, layer, scope):
                """The words a fresh copy of the screen draws."""
                sd = renpy.display.screen.ScreenDisplayable(
                    renpy.display.screen.get_screen_variant(name), name, layer, scope=dict(scope))
                sd.update()
                sd.visit_all(lambda d: d.per_interact())
                rv = renpy.display.render.render_screen(sd, config.screen_width, config.screen_height)
                words = []

                def walk(r):
                    for d in getattr(r, "render_of", ()) or ():
                        if isinstance(d, renpy.text.text.Text):
                            words.append(u"".join(t for t in d.text if isinstance(t, (type(u""), type("")))))
                    for c in r.children:
                        if isinstance(c[0], renpy.display.render.Render):
                            walk(c[0])
                walk(rv)
                return words

            def ours_shown():
                """{(screen, layer): (displayable, scope)} of ours shown."""
                out = {}
                for layer in list(config.layers) + list(getattr(config, "top_layers", ())):
                    for e in list(sl.layers.get(layer, [])):
                        name = getattr(e.displayable, "screen_name", None)
                        if name and name[0].startswith("urm"):
                            out[(name[0], layer)] = (e.displayable, dict(getattr(e.displayable, "scope", {}) or {}))
                return out

            def draw_all(after, problems):
                for (name, layer), (_d, scope) in sorted(ours_shown().items()):
                    try:
                        drawn(name, layer, scope)
                    except Exception:
                        problems.append("%s: %s on %s: %s" % (after, name, layer, last()))

            def callbacks(after, problems):
                for cb in list(config.interact_callbacks):
                    try:
                        cb()
                    except Exception:
                        problems.append("%s, %s: %s" % (after, getattr(cb, "__name__", cb), last()))

            # A synthetic prop menu is enough to exercise both readers in
            # the running engine, with no frozen or original-URM files.
            problems = []
            try:
                menu = next(n for n in renpy.game.script.lookup("p0_c6").block
                            if isinstance(n, renpy.ast.Menu))
                blocks = tuple(item[2] for item in menu.items if item[2])
                fixture_nodes = tuple(_urmi_all_stmts())
                no_truth = lambda expression: None

                def graph_reads():
                    for node in fixture_nodes:
                        _urmsg_flow(node)
                        _urmsg_stmt_text(node)
                        _urmsg_step_urm(node)
                        _urmsg_step_live(node, no_truth)
                        _urmsg_blocks_urm(node)
                        _urmsg_passes(node)
                        _urmsg_children(node)
                        _urmsg_conds(node)
                        if isinstance(node, renpy.ast.If):
                            chain = _urmsg_chain(node, 20, _urmsg_blocks_urm, _urmsg_step_urm)
                            _urmsg_gate_states(chain.steps, no_truth)
                            _urmb_info(node)
                        elif isinstance(node, renpy.ast.Python):
                            _urmsg_py_lines(node)
                    _urmsg_plan(menu, blocks)
                    _urmsg_next_split(menu, no_truth)
                    _urmsg_here()

                log = renpy.game.log
                old_mutations = log.mutated
                try:
                    log.mutated = python_dict()
                    control = [1]
                    require(log.mutated, "the rollback log did not record the control allocation")
                    log.mutated = python_dict()
                    _urmsg_reset()
                    graph_reads()
                    require(not log.mutated, "%d graph allocations entered the rollback log" % len(log.mutated))
                finally:
                    log.mutated = old_mutations
            except Exception:
                problems.append(last())
            line("native_graph_no_rollback_mutation", problems)

            problems = []
            try:
                ctx.current = menu.name
                index = _URMIndex()
                index.build(_urmi_all_stmts(), 0, None)
                _URMMemory.index = index

                def map_answer():
                    view = urm_map_build(menu, index)
                    require(len(view.boxes) > 2, "the test menu did not draw the old map")
                    return (tuple((box.kind, box.title, box.faded, box.x, box.y,
                                   box.w, box.h, tuple(box.chips), tuple(box.rows))
                                  for box in view.boxes),
                            tuple(view.bars), tuple(view.later), view.empty)

                _urmsg_reset()
                before = map_answer()
                urmnm_story_open()
                try:
                    story = renpy.get_screen("urmnm_story", layer=_urmi_layer)
                    require(story is not None, "Story line did not open")
                    for frame in range(800):
                        if urmnm_card_count():
                            break
                        _urm_work_tick()
                    require(urmnm_card_count(), "Story line did not read the choice")
                    words = drawn("urmnm_story", _urmi_layer, story.scope)
                    require(u"Story line" in words, ("story draw", words))
                    require(map_answer() == before, "opening Story line changed the old map's answer")
                finally:
                    urmnm_story_close()
            except Exception:
                problems.append(last())
            line("native_story_line_keeps_old_map", problems)

            problems = []
            callbacks("start", problems)
            line("callbacks_run", problems)

            # Our layer, kept by the engine.
            problems = []
            own = getattr(store, "_urm_own_layer", None)
            if _urmi_layer != own or own not in config.layers:
                problems.append("our screens go on %s" % (_urmi_layer,))
            for kept in ("overlay_layers", "transient_layers", "context_clear_layers"):
                if own in (getattr(config, kept, None) or ()):
                    problems.append("our layer is in config.%s" % kept)
            before = ours_shown()
            if ("urmh_button", _urmi_layer) not in before:
                problems.append("the URM+ button is not on our layer: %r" % (sorted(before),))
            for _i in config.overlay_layers:
                sl.clear(_i)
            sl.replace_transient()
            after = ours_shown()
            problems.extend("%s went at the clean-out" % (k,) for k in sorted(before)
                            if k not in after or after[k][0] is not before[k][0])
            line("our_layer_kept", problems)

            problems = []
            draw_all("start", problems)
            entries = [e.name for e in _urm_entries()]
            for name in ("search", "save", "load", "settings", "story_line"):
                if name not in entries:
                    problems.append("no %s" % name)
            line("menu_offers_map", problems)

            problems = []
            # The Console entry opens the engine's console, which holds the
            # game in an interaction of its own: running the engine's console
            # label in a new context is replaced here by a note of what it was
            # asked for; the label must exist and the console be there and started.
            _cons = getattr(store, "_console", None)
            _cons_real = renpy.call_in_new_context
            _cons_calls = []
            if _cons is not None:
                renpy.call_in_new_context = lambda label, *a, **k: _cons_calls.append(label)
            try:
                for name in entries:
                    del said[:]
                    _urm_open(name)
                    callbacks(name, problems)
                    draw_all(name, problems)
                    problems.extend("%s: %s" % (name, s.strip()) for s in said
                                    if s.strip().startswith(("MRM:", "URM+:")) and "failed" in s)
            finally:
                renpy.call_in_new_context = _cons_real
            if _cons is not None:
                if "console" not in entries:
                    problems.append("no console entry on an engine that has a console")
                elif _cons_calls != ["_console"]:
                    problems.append("the Console entry asked for %r, not the engine's _console label" % (_cons_calls,))
                elif not renpy.game.script.has_label("_console") or type(_cons.console).__name__ != "DebugConsole":
                    problems.append("the Console entry left no engine console behind it")
            before = ours_shown()
            for _i in config.overlay_layers:
                sl.clear(_i)
            sl.replace_transient()
            after = ours_shown()
            problems.extend("%s went at the clean-out" % (k,) for k in sorted(before)
                            if k not in after or after[k][0] is not before[k][0])
            line("entries_open_draw_and_stay", problems)

            urm_map_close()

            def viewports(name, layer, scope):
                """How high each viewport of a fresh copy of the screen is
                drawn, and its adjustments' (range, page)."""
                sd = renpy.display.screen.ScreenDisplayable(
                    renpy.display.screen.get_screen_variant(name), name, layer, scope=dict(scope))
                sd.update()
                sd.visit_all(lambda d: d.per_interact())
                rv = renpy.display.render.render_screen(sd, config.screen_width, config.screen_height)
                found = []
                todo = [rv]
                while todo:
                    r = todo.pop()
                    for c in r.children:
                        if isinstance(c[0], renpy.display.render.Render):
                            of = c[0].render_of
                            if of and isinstance(of[0], renpy.display.viewport.Viewport):
                                v = of[0]
                                found.append((int(c[0].height), (v.xadjustment.range, v.xadjustment.page),
                                              (v.yadjustment.range, v.yadjustment.page)))
                            todo.append(c[0])
                return found

            # The route map, at a menu of the story.
            problems = []
            menus = [n for n in _urmi_all_stmts()
                     if isinstance(n, renpy.ast.Menu) and "prop_script" in n.filename
                     and len([i for i in n.items if i[2]]) >= 2]
            try:
                ctx.current = menus[0].name
                urm_map_open("hotkey")
                if ("urm_route_map", _urmi_layer) not in ours_shown():
                    problems.append("the map is not on our layer: %r" % (sorted(ours_shown()),))
                else:
                    words = drawn("urm_route_map", _urmi_layer, {})
                    texts = [i[0] for i in menus[0].items if i[2]]
                    if u"Route map" not in words or not all(any(t in w for w in words) for t in texts):
                        problems.append("the map: %r" % (words[:14],))
                    view = urm_map_view()
                    room = config.screen_height - urmk_px_cut(70) - (
                        (urmk_px_cut(48) + urmk_px_cut(30) * len(view.later[:6])) if view.later else 0)
                    tall = viewports("urm_route_map", _urmi_layer, {})
                    if len(tall) != 1 or tall[0][0] < room - urmk_px_cut(15):
                        problems.append("the map's part: %r, room %d" % (tall, room))
                    # every line of the map in the line colour: a way with
                    # nothing gained is as plain to see as any other (only
                    # a faded box says "not as things stand")
                    sd = renpy.display.screen.ScreenDisplayable(
                        renpy.display.screen.get_screen_variant("urm_route_map"), "urm_route_map",
                        _urmi_layer, scope={})
                    sd.update()
                    line_ink = tuple(renpy.easy.color(urm_map_ink("line")))
                    inks = []
                    sd.visit_all(lambda d: inks.append(tuple(d.color)) if isinstance(d, renpy.display.imagelike.Solid)
                                 and getattr(d, "color", None) is not None else None)
                    bars = len(view.bars)
                    lines = len([c for c in inks if c == line_ink])
                    if bars == 0 or lines < bars:
                        problems.append("%d of the map's %d lines in the line colour" % (lines, bars))
                urm_map_close()
                if [k for k in ours_shown() if k[0] == "urm_route_map"]:
                    problems.append("the map did not close")
            except Exception:
                problems.append(last())
            line("map_opens_at_a_menu", problems)

            # The story: a menu, and the line before a check.
            problems = []
            try:
                menus = [n for n in _urmi_all_stmts()
                         if isinstance(n, renpy.ast.Menu) and "prop_script" in n.filename
                         and len([i for i in n.items if i[2]]) >= 2]
                ctx.current = menus[0].name
                cards = urm_corner_view()
                kinds = [c[0] for c in cards]
                if "choices" not in kinds:
                    problems.append("no choices card at a menu: %r" % (kinds,))
                words = drawn("urm_corner", _urmi_layer, {"_urmcAt": ("choices", 0)})
                if u"Take" not in words:
                    problems.append("the choices card has no Take: %r" % (words[:12],))
                if u"\\uf184" not in words:
                    problems.append("the choices card has no route-map button")
                tl = renpy.game.script.lookup("prop_tl").block
                ways = []
                for n in [n for n in _urmi_all_stmts() if "prop_script" in n.filename][:600]:
                    ctx.current = n.name
                    if _urm_chain():
                        ways = [c for c in urm_corner_view() if c[0] == "paths"]
                        if ways:
                            break
                if not ways:
                    problems.append("no path card before any check of the story")
                words = drawn("urm_corner", _urmi_layer, {"_urmcAt": ("paths", 0)})
                if u"Take" not in words or u"\\uf184" not in words:
                    problems.append("the path card: %r" % (words[:12],))
                urm_corner_take("paths", 0)
                pending = list(_urm_take_state().pending)
                if not pending:
                    problems.append("Take on the way was not remembered")
                for branch, arm in pending:
                    expected = branch.next if arm < 0 else branch.entries[arm][1][0]
                    branch.execute()
                    if ctx.next_node is not expected:
                        problems.append("Take did not reach that arm")
                if _urm_take_state().pending:
                    problems.append("Take was still pending after the check ran")
                drawn("urmh_button", _urmi_layer, {})
                index = _URMIndex()
                index.build(_urmi_all_stmts(), 0, None)
                _URMMemory.index = index
                urmal_toggle("prop_flag")
                _urmal_check([n for n in tl if isinstance(n, renpy.ast.If)][0])
                if ("urmal_alert", _urmi_layer) not in ours_shown():
                    problems.append("no alert banner on our layer")
                else:
                    words = drawn("urmal_alert", _urmi_layer, ours_shown()[("urmal_alert", _urmi_layer)][1])
                    if not [w for w in words if u"prop_flag" in w]:
                        problems.append("the banner: %r" % (words[:12],))
            except Exception:
                problems.append(last())
            line("story_cards_take_chip_alert", problems)

            # The code view: the cards' titles open it.
            problems = []
            try:
                ctx.current = menus[0].name
                urm_corner_open_code("choices")
                at = ("urmk_code_view", _urmi_layer)
                if at not in ours_shown():
                    problems.append("the choices' title opens no code view: %r" % (sorted(ours_shown()),))
                else:
                    scope = ours_shown()[at][1]
                    words = drawn("urmk_code_view", _urmi_layer, scope)
                    if not [w for w in words if u"menu" in w] or not scope.get("_kwargs", {}).get("marked"):
                        problems.append("the scene: %r, marked %r" % (words[:12], scope.get("_kwargs", {}).get("marked")))
                urm_corner_open_code("paths")
                if at not in ours_shown():
                    problems.append("the checks' title opens no code view")
                # code longer and wider than the panel
                long = u"\\n".join(u"    $ line_%d = 'a very long value that runs on and on past the side of the panel %d'" % (i, i)
                                    for i in range(120))
                urmk_code_show(long, u"Long")
                scope = ours_shown()[at][1]
                tall = viewports("urmk_code_view", _urmi_layer, scope)
                room = config.screen_height - 2 * urmk_px(16) - urmk_px(64) - urmk_px(56)
                if (len(tall) != 1 or tall[0][0] < room - urmk_px(16)
                        or tall[0][1][0] <= 0 or tall[0][2][0] <= 0):
                    problems.append("long code: %r, room %d" % (tall, room))
                # Shift + wheel moves the lines sideways, with developer
                # mode on too (a key with a modifier on a mouse button
                # stops the game there before 7.6)
                was = (config.developer, store._urmk_shift_held)
                try:
                    import pygame_sdl2
                    sd = renpy.display.screen.ScreenDisplayable(
                        renpy.display.screen.get_screen_variant("urmk_code_view"), "urmk_code_view",
                        _urmi_layer, scope=dict(scope))
                    sd.update()
                    sd.visit_all(lambda d: d.per_interact())
                    renpy.display.render.render_screen(sd, config.screen_width, config.screen_height)
                    # the engine draws nothing in developer mode while lint
                    # runs; the events are what it is on for
                    config.developer = True
                    xadj = sd.scope["_urmkvX"]
                    # the view's lines scroll on the kit's own adjustment (built as it scrolls)
                    yadj = sd.scope.get("_urmkvY") or store.urmk_code_adj
                    x, y = config.screen_width - urmk_px(400), config.screen_height // 2
                    moved = []
                    for shift in (True, False):
                        store._urmk_shift_held = (lambda held=shift: held)
                        before = (xadj.value, yadj.value)
                        ev = pygame_sdl2.event.Event(pygame_sdl2.MOUSEBUTTONDOWN, button=5, pos=(x, y), mod=0, which=0, touch=False)
                        try:
                            sd.event(ev, x, y, 0)
                        except renpy.display.core.IgnoreEvent:
                            pass
                        moved.append((xadj.value > before[0], yadj.value > before[1]))
                    if moved[0] != (True, False) or moved[1][0]:
                        problems.append("Shift + wheel (sideways, down): %r, then the wheel alone: %r" % tuple(moved))
                    motion = pygame_sdl2.event.Event(pygame_sdl2.MOUSEMOTION, pos=(x, y), rel=(1, 0), buttons=(0, 0, 0), mod=0, which=0, touch=False)
                    sd.event(motion, x, y, 0)
                except renpy.display.core.IgnoreEvent:
                    pass
                except Exception:
                    problems.append("with developer mode on: " + last())
                finally:
                    config.developer, store._urmk_shift_held = was
                # a game's menu runs in a context of its own: nothing there
                renpy.game.contexts.append(renpy.execution.Context(False, renpy.game.context(), clear=True))
                try:
                    menu_words = drawn("urmk_code_view", _urmi_layer, scope)
                finally:
                    renpy.game.contexts.pop()
                if menu_words:
                    problems.append("draws in a game's menu: %r" % (menu_words[:6],))
                urmk_code_close()
                if at in ours_shown():
                    problems.append("the code view did not close")
            except Exception:
                problems.append(last())
            line("code_view_opens_scrolls_closes", problems)

            problems = []
            real_rows = store.urmfl_rows
            store.urmfl_rows = lambda text, limit=200: ([(u"met_anna", u"met_anna", True, u"")], 1)
            try:
                words = drawn("urmfl_flags", _urmi_layer, {})
                if u"Details" not in words:
                    problems.append("no Details")
                if u"true" not in words:
                    problems.append("no switch: %r" % (words[:12],))
                urmfl_details(u"met_anna")
                shown = ours_shown().get(("urmfl_flag_dialog", _urmi_layer))
                if shown is None:
                    problems.append("Details opened no sheet on our layer")
                else:
                    words = drawn("urmfl_flag_dialog", _urmi_layer, shown[1])
                    if urmi_sheet_title(u"met_anna") not in words:
                        problems.append("the sheet: %r" % (words[:12],))
                    # Esc, as the sheet binds it, takes it off our layer
                    sd = shown[0]
                    sd.update()
                    esc, queue = None, [sd.child]
                    while queue and esc is None:
                        d = queue.pop()
                        if isinstance(d, renpy.display.behavior.Keymap):
                            esc = d.keymap.get("K_ESCAPE")
                        queue.extend(getattr(d, "children", None) or ([d.child] if getattr(d, "child", None) is not None else []))
                    if esc is None:
                        problems.append("the sheet binds no Esc")
                    else:
                        renpy.display.behavior.run(esc)
                        if ("urmfl_flag_dialog", _urmi_layer) in ours_shown():
                            problems.append("Esc left the sheet on our layer")
            except Exception:
                problems.append(last())
            store.urmfl_rows = real_rows
            line("flags_details_open_the_sheet", problems)

            problems = [resume_made] if resume_made else []
            try:
                renpy.loadsave.location.scan()
                store._restart = None
                renpy.session.pop("_reload_slot", None)
                _urmsv_offer_resume()
                slot = renpy.session.get("_reload_slot") if _urmsv_engine_reads_session() else "_reload-1"
                if not slot or not renpy.can_load(slot):
                    problems.append("the resume save is not offered: %r" % (slot,))
                else:
                    data = renpy.loadsave.location.load(slot)
                    # 7.7 on: (the log, its signature)
                    renpy.loadsave.loads(data[0] if isinstance(data, tuple) else data)
            except Exception:
                problems.append(last())
            line("resume_save_opens", problems)
        except Exception:
            _pa_lines.append("run=%r" % (traceback.format_exc().strip().splitlines()[-3:],))
        sys.stdout = real_out
        _pa_write()

    renpy.arguments.commands["lint"] = _pa_lint
'''
ABSENT_LINES = (
    "early_ran", "no_urm", "own_layer", "original_screens_absent", "every_block_ran",
    "native_graph_no_rollback_mutation", "native_story_line_keeps_old_map",
    "callbacks_run", "our_layer_kept", "menu_offers_map", "entries_open_draw_and_stay",
    "map_opens_at_a_menu", "story_cards_take_chip_alert", "code_view_opens_scrolls_closes",
    "flags_details_open_the_sheet", "resume_save_opens",
)
SAVE_LINES = {
    "native": ("save_directory_isolated", "plain_game", "ordinary_save_written", "legacy_save_written"),
    "standalone": ("save_directory_isolated", "standalone_game", "standalone_save_written",
                   "ordinary_save_loaded", "standalone_save_loaded", "legacy_scopes_loaded_and_drawn",
                   "legacy_scopes_resaved_and_reloaded"),
}


# Every URM and URM+ name the 7638 real saves hold (lab/real_save_names.md):
# (module, name), as a pickle names it. And _URMFlagVar: the Flags dialog
# kept one in its scope until our own variable sheet (2026-11-22).
OLD_SAVE_NAMES = [("store.x52URM", n) for n in (
    "progressDragged", "Var", "Input", "SetVarValue", "SettingsClass",
    "ProgressBarClass", "Tooltip", "Notification", "InputGroup", "URMFileStore")] + [
    ("store", "_URMRMiddleClick"), ("store", "urm_branch_close"), ("store", "urm_branch_dragged"),
    ("store", "_URMFlagVar")]


def pickle_globals(data):
    """The global names a pickle names, as module.name (GLOBAL, and
    STACK_GLOBAL with its two strings, memoised or not)."""

    import pickletools
    found, pushed, memo, last = set(), [], {}, None
    strings = ("SHORT_BINUNICODE", "BINUNICODE", "UNICODE", "BINUNICODE8",
               "SHORT_BINSTRING", "BINSTRING", "STRING")
    for op, arg, _pos in pickletools.genops(data):
        value = None
        if op.name == "GLOBAL":
            found.add(arg.replace(" ", "."))
        elif op.name == "STACK_GLOBAL" and len(pushed) > 1:
            found.add(pushed[-2] + "." + pushed[-1])
        elif op.name in strings:
            value = arg if isinstance(arg, str) else arg.decode("latin-1")
            pushed.append(value)
        elif op.name == "MEMOIZE":
            memo[len(memo)] = last
        elif op.name in ("PUT", "BINPUT", "LONG_BINPUT"):
            memo[arg] = last
        elif op.name in ("GET", "BINGET", "LONG_BINGET") and memo.get(arg) is not None:
            value = memo[arg]
            pushed.append(value)
        if op.name not in ("MEMOIZE", "PUT", "BINPUT", "LONG_BINPUT"):
            last = value
    return found

# The lines each step of the old save must write, all True.
ABSENT_SAVE_LINES = {"save": ("saves_in_scratch", "urm_there_untouched", "yellow_from_the_chip", "screens_built"),
                     "load": ("sheet_save_loads", "sheet_set_kept", "old_save_loads", "old_save_draws", "old_screens_back_undrawn", "old_objects_back", "reload_resets_stand_in"),
                     "back": ("resave_loads_with_urm", "resave_draws_with_urm", "stand_ins_load_as_urms",
                              "old_chip_save_loads_with_urm", "old_chip_draws_nothing")}


def interpreter(game):
    """The same choice the .bat makes."""

    found = sorted(glob.glob(os.path.join(game, "lib", "*x86_64*", "python.exe")))
    found += sorted(glob.glob(os.path.join(game, "lib", "*", "python.exe")))
    if os.path.exists(os.path.join(game, "lib", "python.exe")):
        found.append(os.path.join(game, "lib", "python.exe"))
    return found[0] if found else None


def environment(game, py, home=None):
    """What the game's own Python runs with. With `home`, an engine started
    on a copy keeps its saves, its persistent data and URM's settings there
    instead of the player's %APPDATA%\\RenPy: newer launchers ask
    RENPY_PATH_TO_SAVES, the 7.3 one and Now and Then's ask APPDATA, and
    MultiPersistent asks RENPY_MULTIPERSISTENT (FINDINGS.md, "Scratch copies
    share the real game's save folder")."""

    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    libs = glob.glob(os.path.join(game, "lib", "pythonlib*"))
    if libs:
        env["PYTHONPATH"] = libs[0] + os.pathsep + os.path.dirname(py)
    if home:
        if os.path.exists(home):
            shutil.rmtree(home)
        os.makedirs(os.path.join(home, "persistent"))
        # Where %APPDATA% always has it: launchers that ask APPDATA make
        # only their own folder inside (os.mkdir, not makedirs).
        os.makedirs(os.path.join(home, "RenPy"))
        env["URM_GATE_HOME"] = home
        env["RENPY_PATH_TO_SAVES"] = home
        env["APPDATA"] = home
        env["RENPY_MULTIPERSISTENT"] = os.path.join(home, "persistent")
    return env


def home(scratch, name):
    """The saves folder of one game's scratch copy."""

    return os.path.join(scratch, "_home", name)


def raised(copy):
    """The last line of the traceback an engine left in `copy`, and where,
    or None."""

    trace = os.path.join(copy, "traceback.txt")
    if not os.path.exists(trace):
        return None
    text = open(trace, "rb").read().decode("utf-8-sig", "replace")
    short = [l.strip() for l in text.split("-- Full Traceback")[0].splitlines() if l.strip()]
    where = [l for l in short if l.startswith("File ")]
    return "%s  [%s]" % (short[-1] if short else "?", where[-1] if where else "?")


def props_wanted():
    """What tests/make_props.py builds a prop from today: its stamp, and
    the labels its story must hold."""

    if not PROPS:
        import make_props
        PROPS["stamp"] = make_props.stamp()
        PROPS["labels"] = make_props.story_labels()
    return PROPS


PROPS = {}

# What a prop's probe run must print, on top of what every game prints.
PROP_LINES = ("prop_story_loaded", "prop_translation_checked", "plain_game",
              "stray_percent_real_line", "skip_looks_back_past_translate",
              "skip_looks_back_in_a_translation", "skip_default_rule_in_a_translation")


def py_flags(game, py):
    """The interpreter flags the .bat uses for this game's Python."""

    out = ["-I"] if "py3" in os.path.basename(os.path.dirname(py)) else ["-s"]
    if glob.glob(os.path.join(game, "lib", "pythonlib*")):
        out = ["-O"] + out  # a .pyo-only library, as the .bat knows
    return out


def launcher(game):
    for exe in glob.glob(os.path.join(game, "*.exe")):
        py = exe[:-4] + ".py"
        if os.path.exists(py):
            return os.path.basename(py)
    return None


def same_drive(a, b):
    return os.path.splitdrive(os.path.abspath(a))[0].lower() == \
        os.path.splitdrive(os.path.abspath(b))[0].lower()


def copy_game(game, dest):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    left_out = []

    for name in os.listdir(game):
        src = os.path.join(game, name)
        if name in ("lib", "renpy"):
            shutil.copytree(src, os.path.join(dest, name))
        elif name.endswith((".py", ".exe")) and os.path.isfile(src):
            shutil.copy2(src, dest)

    for root, dirs, files in os.walk(os.path.join(game, "game")):
        rel = os.path.relpath(root, game)
        dirs[:] = [d for d in dirs if not (rel == "game" and d in ("saves", "cache"))]
        os.makedirs(os.path.join(dest, rel))
        for f in files:
            src = os.path.join(root, f)
            out = os.path.join(dest, rel, f)
            if f.endswith((".rpyc", ".rpymc")) and os.path.exists(src[:-1]):
                continue
            if os.path.getsize(src) > BIG_FILE:
                if same_drive(src, dest):
                    os.link(src, out)
                else:
                    left_out.append(f)
                continue
            shutil.copy2(src, out)

    return left_out


def bat_result(bat, game):
    command = 'cmd /s /c ""%s" "%s" install"' % (bat, game)
    result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=900)
    return result.returncode, result.stdout.decode("utf-8", "replace")


def run_bat(bat, game):
    return bat_result(bat, game)[1]


def double_click(bat_in_game):
    """The .bat inside the game folder, no arguments, menu answered 1 then 0."""
    command = 'cmd /s /c ""%s""' % bat_in_game
    result = subprocess.run(command, input=b"1\r\n0\r\n", stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=900,
                            cwd=os.path.dirname(bat_in_game))
    return result.stdout.decode("utf-8", "replace")


def bad_lines(out):
    return [l.strip() for l in out.splitlines()
            if l.strip().startswith("!") or "Could not" in l or "Traceback" in l
            or "Error" in l]


class held(object):
    """Holds a file open the way a running game does: others may read it,
    nobody may write, rename or delete it. With writable=True others may
    also open it for writing, but still not rename or delete it: what lets
    an install get past its "is the game open" test and then fail."""

    def __init__(self, path, writable=False):
        self.path = path
        self.share = 3 if writable else 1

    def __enter__(self):
        import ctypes
        from ctypes import wintypes
        self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.k.CreateFileW.restype = wintypes.HANDLE
        self.k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                       wintypes.HANDLE]
        # GENERIC_READ, FILE_SHARE_READ (and WRITE), OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL
        self.h = self.k.CreateFileW(self.path, 0x80000000, self.share, None, 3, 0x80, None)
        if self.h in (None, wintypes.HANDLE(-1).value):
            raise OSError("could not hold %s open" % self.path)
        return self

    def __exit__(self, *exc):
        self.k.CloseHandle(wintypes_handle(self.h))


def wintypes_handle(h):
    from ctypes import wintypes
    return wintypes.HANDLE(h)


def digest(path):
    import hashlib
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


ODD_NAME = " (x!y) 100% & z^"


def rename_when_free(src, dst):
    """os.rename, waiting out a handle something else still has in the
    folder. Seen 2026-11-19 with six games checked at once: the rename right
    after the engine and the .bat had exited failed with WinError 32 on one
    game (a process still letting go, or a virus scanner reading what was
    just written). It is the gate's own housekeeping, not the installer."""

    import time
    for attempt in range(40):
        try:
            os.rename(src, dst)
            return
        except PermissionError:
            if attempt == 39:
                raise
            time.sleep(0.5)


def installer_code(tool):
    """The installer's own Python, as check() took it out of the .bat."""

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "urmfix_%d" % abs(hash(tool)), os.path.join(tool, "urmfix.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def probe_report_failures(path, required):
    if not os.path.isfile(path):
        return ["no report"]
    with io.open(path, encoding="utf-8") as f:
        rows = f.read().splitlines()
    names = {row.split("=", 1)[0] for row in rows if "=" in row}
    return ([row for row in rows if not row.endswith("=True")]
            + [name + " missing" for name in required if name not in names])


def clean_features(copy, py, flags, start, env, tool):
    """Exercise the interaction paths and draw the screens with no URM."""
    later = []
    lines = urm_source.join().decode("utf-8").splitlines()
    starts = [line for _priority, line in urm_source.block_order()]
    for at, end in zip(starts, starts[1:] + [len(lines) + 1]):
        for line in lines[at:end - 1]:
            found = re.match(r"    (?:(?:def|class) (\w+)|(\w+) = )", line)
            if found:
                later.append(found.group(1) or found.group(2))
                break
    absent_rpy = os.path.join(tool, "urm_absent.rpy")
    with io.open(absent_rpy, "w", encoding="utf-8", newline="\n") as f:
        f.write(ABSENT_PROBE.replace(u"@@LATER_NAMES@@", u"%r" % (later,)))
    built = subprocess.run([py] + flags + ["-B", os.path.join(tool, "build_probe.py"), copy,
                                           absent_rpy, tool, "zzzz_urm_absent"],
                           cwd=tool, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=600)
    if b"probe built" not in built.stdout:
        return ["clean features: probe: " + built.stdout.decode("utf-8", "replace")[-400:]]
    game = os.path.join(copy, "game")
    main_probe = os.path.join(game, "zzzz_urm_probe.rpa")
    report = os.path.join(copy, "urm_absent.txt")
    if os.path.isfile(report):
        os.remove(report)
    os.rename(main_probe, main_probe + ".aside")
    try:
        subprocess.run([py] + flags + [start, ".", "lint"], cwd=copy, env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1800)
    finally:
        os.rename(main_probe + ".aside", main_probe)
    return ["clean features: " + error for error in probe_report_failures(report, ABSENT_LINES)]


def native_saves(copy, py, flags, start, env, tool):
    source = os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe_standalone_saves.rpy")
    name = "zzzz_urm_saves_gate"
    args = [py] + flags + ["-B", os.path.join(tool, "build_probe.py"), copy, source, tool, name]
    built = subprocess.run(args, cwd=tool, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=600)
    if b"probe built" not in built.stdout:
        return ["saves: probe: " + built.stdout.decode("utf-8", "replace")[-400:]]
    game = os.path.join(copy, "game")
    installed = os.path.join(game, urm_source.ARCHIVE)
    raw = os.path.join(tool, "standalone-held.rpa")
    prior = ("zzzz_urm_probe.rpa", "zzzz_urm_absent.rpa")
    for previous in prior:
        rename_when_free(os.path.join(game, previous), os.path.join(tool, previous))
    problems = []
    try:
        for mode in ("native", "standalone"):
            report = os.path.join(copy, "saves_" + mode + ".txt")
            if os.path.isfile(report):
                os.remove(report)
            if mode == "native":
                rename_when_free(installed, raw)
            try:
                run_env = dict(env, URM_GATE_SAVES=mode)
                subprocess.run([py] + flags + [start, ".", "lint"], cwd=copy, env=run_env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
            finally:
                if mode == "native":
                    rename_when_free(raw, installed)
            wrong = probe_report_failures(report, SAVE_LINES[mode])
            if wrong:
                problems.append("save %s: %s" % (mode, "\n".join(wrong)))
    finally:
        os.remove(os.path.join(game, name + ".rpa"))
        for previous in prior:
            rename_when_free(os.path.join(tool, previous), os.path.join(game, previous))
    return problems


def native_features(copy, py, flags, start, env, tool):
    import prop_probes
    samples = [prop_probes.load_probe(path) for path in prop_probes.discover()]
    files = prop_probes.fixture_files(samples)
    source = os.path.join(tool, "feature_matrix.rpy")
    with open(source, "wb") as f:
        f.write(b"\n\n".join(files[key] for key in sorted(files)))
    name = "zzzz_urm_feature_matrix"
    cmd = [py] + flags + ["-B", os.path.join(tool, "build_probe.py"), copy, source, tool, name]
    built = subprocess.run(cmd, cwd=tool, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=600)
    if b"probe built" not in built.stdout:
        return ["feature matrix: probe: " + built.stdout.decode("utf-8", "replace")[-500:]]
    game = os.path.join(copy, "game")
    prior = ("zzzz_urm_probe.rpa", "zzzz_urm_absent.rpa")
    for previous in prior:
        rename_when_free(os.path.join(game, previous), os.path.join(tool, previous))
    try:
        env = environment(copy, py, os.path.join(tool, "feature-home"))
        if os.environ.get("URM_GATE_PICTURES"):
            pictures = os.environ["URM_GATE_PICTURES"]
            for sample in samples:
                if sample["pic_env"]:
                    env[sample["pic_env"]] = pictures
                    env[sample["tag_env"]] = os.path.basename(copy)
        boot = subprocess.run([py] + flags + [start, ".", "lint"], cwd=copy, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
    finally:
        os.remove(os.path.join(game, name + ".rpa"))
        for previous in prior:
            rename_when_free(os.path.join(tool, previous), os.path.join(game, previous))
    report = os.path.join(copy, "probe_out.txt")
    if not os.path.isfile(report):
        return ["feature matrix: %s" % (raised(copy) or boot.stdout.decode("utf-8", "replace")[-650:])]
    with io.open(report, encoding="utf-8") as f:
        results = prop_probes.parse_report(f.read().splitlines(), [sample["name"] for sample in samples])
    problems = []
    for name, lines in sorted(results.items()):
        if not lines:
            problems.append("feature matrix: %s had no checks" % name)
        problems.extend("feature matrix: %s: %s" % (name, line) for line in lines if not line.startswith("pass  "))
    return problems


def installer_scenarios(bat, copy, tool):
    """Our archive can be replaced atomically and original files stay put."""
    game = os.path.join(copy, "game")
    ours = os.path.join(game, urm_source.ARCHIVE)
    legacy = os.path.join(game, "0x52_URM.rpa")
    loose = os.path.join(game, "0x52-URM")
    tool_payload = installer_code(tool)
    problems = []
    contents = set(read_rpa_names(ours))
    original = {"0x52-URM/fixture.txt": b"plain original fixture"}
    tool_payload.write_archive(legacy, original)
    os.makedirs(loose)
    note = os.path.join(loose, "fixture.txt")
    with open(note, "wb") as f:
        f.write(b"loose original fixture")
    screens = os.path.join(loose, "screens")
    os.makedirs(screens)
    screen_path = os.path.join(screens, "settings.rpy.x52")
    with open(screen_path, "wb") as f:
        f.write(b"fixture plain original screen")

    def game_files():
        return {os.path.relpath(os.path.join(root, name), game): digest(os.path.join(root, name))
                for root, _dirs, files in os.walk(game) for name in files}

    unchanged = (digest(legacy), digest(note), digest(screen_path))
    try:
        status, output = bat_result(bat, copy)
        if (status or bad_lines(output) or "Done." not in output
                or "Wrote game/urmplus.rpa (MRM)" not in output):
            problems.append("reinstall: %s" % output.strip())
        if unchanged != (digest(legacy), digest(note), digest(screen_path)):
            problems.append("reinstall did not preserve original archives and loose files")
        if set(read_rpa_names(ours)) != contents:
            problems.append("reinstall archive inventory changed")

        for misplaced, data in ((screen_path, b"value = urmcSetting"),
                                (screen_path + "t", b"value = _urm_helper"),
                                (os.path.join(game, tool_payload.OLD_ADDON_ENTRY)[:-1],
                                 b"legacy add-on extracted as source")):
            with open(misplaced, "wb") as f:
                f.write(data)
            before = game_files()
            status, output = bat_result(bat, copy)
            if not status or "older combined" not in output or "backup outside game/" not in output:
                problems.append("extracted combined install was not refused: %s" % output.strip())
            if game_files() != before:
                problems.append("extracted combined refusal changed the game files")
            os.remove(misplaced)

        with held(ours):
            status, output = bat_result(bat, copy)
        if not status or "The game is open" not in output or digest(ours) is None:
            problems.append("held archive was not protected: %s" % output.strip())

        for entry, data in (
                ("0x52-URM/screens/settings.rpy.x52", b"value = urmcSetting"),
                (tool_payload.OLD_ADDON_ENTRY, b"combined fixture")):
            tool_payload.write_archive(legacy, {entry: data})
            before = game_files()
            status, output = bat_result(bat, copy)
            if not status or "older combined" not in output or game_files() != before:
                problems.append("combined archive refusal changed the game files: %s" % output.strip())
        combined = digest(legacy)
        rename_when_free(legacy, os.path.join(tool, "combined-backup.rpa"))
        status, output = bat_result(bat, copy)
        if status or "Done." not in output or os.path.exists(legacy):
            problems.append("reinstall after making a combined backup: %s" % output.strip())
        if digest(os.path.join(tool, "combined-backup.rpa")) != combined:
            problems.append("the combined backup changed")
        if not digest(ours):
            problems.append("reinstall lost MRM's archive")
        for field in (b"ADDON_B64", b"SCREENS_B64"):
            bad_dir = os.path.join(tool, field.decode("ascii"))
            os.makedirs(bad_dir)
            broken = os.path.join(bad_dir, "URM_fix.bat")
            import base64
            invalid = base64.b64encode(b"screen invalid(")
            with open(bat, "rb") as recipe:
                data = recipe.read()
            with open(broken, "wb") as candidate:
                candidate.write(re.sub(br"(?m)^" + field + br' = "[^"]+"',
                                       field + b' = "' + invalid + b'"', data, count=1))
            before = digest(ours)
            status, output = bat_result(broken, copy)
            if not status or "Could not build MRM" not in output or digest(ours) != before:
                problems.append("compile failure changed the installation: %s" % output.strip())
        if glob.glob(os.path.join(game, ".urmplus-*.tmp")):
            problems.append("installer left a pending archive")
    finally:
        if os.path.exists(legacy):
            os.remove(legacy)
        os.remove(note)
        if os.path.exists(screen_path):
            os.remove(screen_path)
        os.rmdir(screens)
        os.rmdir(loose)
    odd = copy + ODD_NAME
    rename_when_free(copy, odd)
    try:
        copy_bat = os.path.join(odd, "URM_fix.bat")
        shutil.copy2(bat, copy_bat)
        output = double_click(copy_bat)
        if ("Done." not in output or bad_lines(output)
                or "Multiversal Ren'Py Mod (MRM) installer" not in output
                or "Install MRM into this game" not in output):
            problems.append("installer menu in a folder with punctuation: %s" % output.strip())
    finally:
        rename_when_free(odd, copy)
    return problems


def read_rpa_names(path):
    with open(path, "rb") as f:
        head = f.readline().split()
        f.seek(int(head[1], 16))
        import pickle
        import zlib
        return tuple(pickle.loads(zlib.decompress(f.read())))


def check(bat, scratch, game):
    name = os.path.basename(os.path.normpath(game))
    copy = os.path.join(scratch, name)
    problems = []

    py = interpreter(game)
    start = launcher(game)
    if py is None or start is None:
        return name, ["no interpreter or launcher found"], ""

    prop = os.path.exists(os.path.join(game, "prop_stamp.txt"))
    if prop:
        # A prop must hold what the builder makes today: every story, and
        # an old save. One built before a story was added tests less, and
        # says nothing about it.
        with io.open(os.path.join(game, "prop_stamp.txt")) as f:
            have = f.read().strip()
        if have != props_wanted()["stamp"]:
            return name, ["prop: built from an older recipe (stamp %s, today's %s); rebuild it: "
                          "python urm_compat/tests/make_props.py --refresh props/prop-*"
                          % (have[:8], props_wanted()["stamp"][:8])], ""

    left_out = copy_game(game, copy)
    py = interpreter(copy)
    env = environment(copy, py, home(scratch, name))
    kind = os.path.basename(os.path.dirname(py))

    with open(bat, "rb") as f:
        if b"rem URM_BEGIN" in f.read():
            problems.append("the .bat carries URM")
    out = run_bat(bat, copy)
    problems.extend("install: " + p for p in bad_lines(out))
    if "Wrote game" not in out:
        problems.append("the .bat wrote nothing")
    if os.path.exists(os.path.join(copy, "game", "0x52_URM.rpa")):
        problems.append("the .bat wrote URM's archive")
    if problems:
        return name, problems, kind

    game_dir = os.path.join(copy, "game")
    installed = os.path.join(game_dir, urm_source.ARCHIVE)
    assets = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")
    actual = read_rpa_names(installed)
    expected = {"urmplus/addon.rpyc", "urmplus/screens.rpyc"}
    expected.update("urmplus/fonts/" + name for name in os.listdir(assets))
    if set(actual) != expected:
        problems.append("installed archive inventory: %s" % ", ".join(sorted(set(actual) ^ expected)))

    tool = os.path.join(scratch, "_tool", name)
    if not os.path.exists(tool):
        os.makedirs(tool)
    text = open(bat, "rb").read().decode("utf-8", "replace").replace("\r\n", "\n")
    payload = text.split("rem PAYLOAD_BEGIN\n", 1)[1]
    with open(os.path.join(tool, "urmfix.py"), "w", newline="\n") as f:
        f.write(payload)
    with open(os.path.join(tool, "build_probe.py"), "w") as f:
        f.write(BUILD_PROBE)
    probe = PROBE.replace(u"@@ADDON_MD5@@", ADDON["md5"]).replace(
        u"@@ADDON_HEADERS@@", u"%r" % (ADDON["headers"],)).replace(
        u"@@PROP_LABELS@@", u"%r" % (props_wanted()["labels"],)).replace(
        u"@@SCREENS_MD5@@", ADDON["screens_md5"]).replace(
        u"@@SCREEN_NAMES@@", u"%r" % (ADDON["screen_names"],))
    with io.open(os.path.join(tool, "urm_probe.rpy"), "w", encoding="utf-8", newline="\n") as f:
        f.write(FONT_LIST + probe)

    flags = py_flags(copy, py)
    built = subprocess.run([py] + flags + ["-B", os.path.join(tool, "build_probe.py"), copy,
                                           os.path.join(tool, "urm_probe.rpy"), tool],
                           cwd=tool, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=600)
    if b"probe built" not in built.stdout:
        problems.append("probe: " + built.stdout.decode("utf-8", "replace")[-400:])
        return name, problems, kind

    try:
        subprocess.run([py] + flags + [start, ".", "lint"], cwd=copy, env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1800)
    except subprocess.TimeoutExpired:
        problems.append("engine: timed out")
        return name, problems, kind
    report = os.path.join(copy, "urm_probe.txt")
    trace = raised(copy)
    if not os.path.exists(report):
        why = trace or "no traceback"
        if left_out:
            why = "game init needs media (%s left out): %s" % (", ".join(left_out), why)
        problems.append("engine: " + why)
        return name, problems, kind
    # Ren'Py 8.5 in lint mode notes an error raised while loading and goes
    # on to the probe (FINDINGS.md); a player gets the error screen.
    if trace:
        problems.append("engine: the game raised while loading: " + trace)

    values = dict(l.split("=", 1) for l in open(report).read().splitlines() if "=" in l)
    for key, value in sorted(values.items()):
        if value != "True":
            problems.append("engine: %s=%s" % (key, value))

    # The story-graph comparison must have run to its end: a probe that
    # stopped early would otherwise pass on the lines it did print.
    for key in ADDON_LINES + ("clean_settings",):
        if key not in values:
            problems.append("engine: %s missing" % key)
    if prop:
        for key in PROP_LINES:
            if key not in values:
                problems.append("engine: %s missing - the prop did not load its own script" % key)

    notes = os.path.join(copy, "urm_probe_graph.txt")
    if os.path.exists(notes):
        GRAPH_NOTES[name] = [l for l in io.open(notes, encoding="utf-8").read().splitlines()
                             if l.strip() and "=" not in l.split(":")[0]]
    if prop:
        problems.extend(font_list(py, flags, start, copy, env))
    problems.extend(clean_features(copy, py, flags, start, env, tool))
    problems.extend(native_saves(copy, py, flags, start, env, tool))
    problems.extend(native_features(copy, py, flags, start, env, tool))
    problems.extend(installer_scenarios(bat, copy, tool))
    return name, problems, kind


# The add-on as the pieces say it is (tests/urm_source.py): the md5 of the
# joined file and the line of each of its blocks. Filled in by main(); the
# probe compares what the engine loaded with it.
ADDON = {}

ADDON_LINES = ("addon_is_the_joined_pieces", "addon_blocks_run_in_order",
               "no_original_urm", "our_overlay", "screens_are_the_joined_files", "our_screens_are_ours",
               "chip_on_the_button", "branch_button",
               "corner_cards_draw", "hub_builds", "hub_not_in_menus", "hub_key_free",
               "map_screen_room",
               "var_sheet_builds", "var_sheet_ladder", "var_sheet_resets_on_show",
               "var_sheet_fits_content", "var_sheet_more_click_while_hovered",
               "flag_sheet_builds", "var_sheet_scope_plain", "var_sheet_takes_its_events",
               "var_sheet_not_in_menus", "var_sheet_set_says_put_back", "var_sheet_freeze_uses_our_set",
               "click_advances_dialogue_and_resumes_skip", "skip_resumes_on_configured_click_phase",
               "skip_resume_respects_engine_dismissal")

# Per game: what the story-graph comparison covered. Printed, never gating.
GRAPH_NOTES = {}

def timed_check(bat, scratch, game):
    import time
    began = time.time()
    try:
        name, problems, kind = check(bat, scratch, game)
    except Exception as error:
        # One game must not take the others' results down with it.
        import traceback
        name = os.path.basename(os.path.normpath(game))
        problems = ["gate: " + traceback.format_exc().strip().splitlines()[-1]]
        kind = type(error).__name__
    return name, problems, kind, time.time() - began


def jobs_for(count):
    """How many games to run at once. Every game is its own scratch copy,
    its own tool folder and its own engine process, so they share nothing;
    URM_GATE_JOBS=1 gives the old one-after-another run."""

    try:
        asked = int(os.environ.get("URM_GATE_JOBS", "0"))
    except ValueError:
        asked = 0
    if asked > 0:
        return min(asked, count)
    return max(1, min(count, (os.cpu_count() or 2) - 2))


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 2
    import time
    from concurrent.futures import ThreadPoolExecutor
    bat, scratch = os.path.abspath(argv[1]), os.path.abspath(argv[2])
    games = [os.path.abspath(g) for g in argv[3:]]
    if any(not os.path.isfile(os.path.join(game, "prop_stamp.txt")) for game in games):
        print("the standalone installer gate accepts prop folders only")
        return 2
    names = [os.path.basename(os.path.normpath(g)) for g in games]
    if len(set(names)) != len(names):
        print("two games share a folder name; their scratch copies would collide")
        return 2
    try:
        ADDON["md5"] = urm_source.md5()
        ADDON["headers"] = urm_source.block_order()
        ADDON["screens_md5"] = urm_source.screens_md5()
        ADDON["screen_names"] = sorted(
            n for _f, names in check_layers.screen_names().items() for n in names)
    except urm_source.SourceError as error:
        print("the add-on's pieces cannot be joined: %s" % error)
        return 2
    print("add-on: %d pieces, %d blocks, md5 %s"
          % (len(urm_source.layout()), len(ADDON["headers"]), ADDON["md5"]))
    props_wanted()
    failed = 0
    began = time.time()
    jobs = jobs_for(len(games))
    pool = ThreadPoolExecutor(max_workers=jobs)
    waiting = [pool.submit(timed_check, bat, scratch, game) for game in games]
    for future in waiting:
        name, problems, kind, took = future.result()
        print("%-4s %-36s %-22s %4d s" % ("ok" if not problems else "FAIL", name, kind, took))
        sys.stdout.flush()
        for p in problems:
            print("       " + p)
        for note in GRAPH_NOTES.get(name, ()):
            print("         note: " + note)
        failed += bool(problems)
    pool.shutdown()
    print()
    print("%d games, %d at a time, %d s" % (len(games), jobs, time.time() - began))
    print("all passed" if not failed else "%d FAILED" % failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
