"""
Release gate: runs the real URM_fix.bat on scratch copies of real games, the
way a user does, then starts each copy's own engine headlessly and checks
URM+ is loaded.

    python check_installer.py <URM_fix.bat> <scratch folder> <game folder>...

Pick one game of each kind - the installer has a different path for each:

    Ren'Py 8 (lib/py3-windows-*)            e.g. Aihvala
    Ren'Py 7.4+ (lib/py2-windows-*)         e.g. Thief of Hearts 2, NIF
    Ren'Py 7.4 before py2- names (lib/windows-x86_64 + lib/python2.7)
                                            e.g. Freeloading Family
    Ren'Py 7.3 and older (lib/windows-* + lib/pythonlib2.7)
                                            e.g. anna_ea_remake
    a protected build (own .rpyc format)    HoS

Nothing is written to the game folders. Each copy holds the engine, the
launcher and game/ minus saves and cache; files over BIG_FILE are hard-linked
when the game is on the scratch folder's drive and left out otherwise (some
games need their images at init - those report "game init needs media").

A game passes only when:
  - the .bat's own output shows a write and no "!" or "Could not" line, and
  - the engine, started on the copy, reaches a probe at init 1999 that finds
    URM and URM+ (alerts, flags, the panel, the skip rule, the card filter)
    and sees If.execute watched, and
  - what the engine loaded is the add-on's pieces (urm_compat/game_fixes,
    joined by tests/urm_source.py) with its blocks queued in their order -
    so the .bat must be built from the pieces as they are now, and
  - on a prop, the engine started once more as a game whose
    config.font_transforms is a list (font_list()) loads with URM, and
  - the situations in scenarios() go right, the last of them an upgrade: the
    build from before the pieces installed first, then this one.

The probe goes in its own archive, built with the installer's own compiler,
because protected builds ignore loose .rpy files.
"""

from __future__ import print_function

import binascii
import glob
import io
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import urm_source  # noqa  (the add-on's code, joined from its pieces)

BIG_FILE = 150 * 1024 * 1024

# The last build made from the single game_fixes.rpy, before the add-on's code
# was cut into pieces (2026-11-20): what a game installed before then holds.
OLD_BAT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "baseline", "URM_fix_single_file.bat")

PROBE = u'''init 1999 python:
    import os as _po
    _l = []
    try:
        for _n in ("x52URM", "urmal_toggle", "urmfl_set", "urm_panel",
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
        _ad = _ba.hexlify(renpy.file("0x52-URM/zzz_urm_compat.rpyc").read()[-16:]).decode("ascii")
        _l.append("addon_is_the_joined_pieces=%r" % (_ad == "@@ADDON_MD5@@" or _ad,))
        _ao = [(_p, _n.linenumber) for _p, _n in renpy.game.script.initcode if (getattr(_n, "name", None) or ("",))[0] == "0x52-URM/zzz_urm_compat.rpy"]
        _l.append("addon_blocks_run_in_order=%r" % (_ao == @@ADDON_HEADERS@@ or _ao,))
        _l.append("If_watched=%r" % (getattr(renpy.ast.If.execute, "_urmal", False),))
        _l.append("alert_screen=%r" % (renpy.has_screen("urmal_alert"),))
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
            _ok = _ok and _urmft_map(_k, "0x52-URM/framework/Roboto-Regular.ttf") == "0x52-URM/framework/Roboto-Regular.ttf"
            _ok = _ok and _urmft_map(_k, "gui/FontAwesome.otf") == "gui/FontAwesome.otf"
        _l.append("font_maps=%r" % (_ok,))
        if _ftab:
            _l.append("font_hook=%r" % (config.font_transforms.get("urmplus") is _urmft_transform,))
        else:
            _l.append("font_hook=%r" % (renpy.game.preferences.font_transform is None or renpy.game.preferences.font_transform,))
            with open(_po.path.join(config.basedir, "urm_probe_graph.txt"), "a") as _nf:
                _nf.write("\\nfont table: config.font_transforms is a %s in this game, left as it is; Game font is not offered\\n" % type(config.font_transforms).__name__)
        _l.append("font_set_hooked=%r" % (getattr(x52URM.SettingsClass.set, "_urmft", False) or getattr(getattr(x52URM.SettingsClass.set, "__func__", None), "_urmft", False),))
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
            _l.append("map_called_scene=%r" % (_cb7 == [("choice", "E", ["Urmprobe e: 1"], None), ("choice", "F", [], None), ("merge", "Paths meet again", ["Urmprobe back: 1"], "Ending")] or _cb7,))
        finally:
            _ctx.current = _kc
            _ctx.return_stack = _kr
        # Route map: the screen exists, the button's setting is on by
        # default, and the probe maze lays out as 3 routes into one merge
        # box, with what it decides later in words.
        _l.append("map_screen=%r" % (renpy.has_screen("urm_route_map"),))
        _l.append("map_button_default=%r" % (x52URM.SettingsClass.defaultValues.get("urmcBtnRouteMap") is True,))
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
        _l.append("map_rows_fit=%r" % (all(b.dot or b.h == _urmm_box_h(b, x52URM.scalePxInt) and b.h >= 2 * x52URM.scalePxInt(8) + sum(r[3] for r in b.rows) for b in _mv.boxes) or [(b.title, b.h) for b in _mv.boxes],))
        _l.append("map_later=%r" %(list(_mv.later) == [u"At urmprobe_done the game checks: Urmprobe x is 1  \\u00b7  not set yet"] or list(_mv.later),))
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
            _l.append("map_idea13_ways=%r" % (_b13 == [("choice", "I", None, ["Urmprobe i: 1"], [], False), ("branch", "Otherwise", "When nothing is left to pick", ["Urmprobe out: 1"], ["code"], False), ("choice", "J (if urmprobe_j >= 3)", None, ["Urmprobe jj: 1"], [], False), ("choice", "K (if urmprobe_k >= 3)", None, ["Urmprobe kk: 1"], [], False), ("branch", "If none apply", None, [], [], True), ("choice", "L", None, ["Urmprobe l: 1"], [], False), ("choice", "M", None, [], [], False)] or _b13,))
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
        _l.append("cards_words=%r" % ([c[3] for c in _cv] == ["A", "B"] and list(_cv[0][6][0][2]) == [("Urmprobe x: 1", "set")] and [r[1] for r in _cv[1][6]][1:] ==[u"\\u203a C", u"\\u203a D"] and _cf == [u"Urmprobe x matters at urmprobe_done  \\u00b7  checked for 1"] or (_cv, _cf),))
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
        _l.append("branch_case_true=%r" % (_bv == ["", "Only because Urmprobe bx is on", "Back on the shared part"] or _bv,))
        _l.append("branch_count=%r" % ((_urmb_view(_s1, False, 2) or ("",) * 3)[2] == "last line" or _urmb_view(_s1, False, 2),))
        _s3 = _urmb_advance(_s0, (_b0.next.name, _bi.name, _bi.next.name, _b2.name), False, _b2)
        _bv = (_urmb_view(_s3, False, 2) or ("", ""))[1]
        _l.append("branch_case_false=%r" % (_bv == u"Skipped a part  \\u00b7  needs Urmprobe bx on" or _bv,))
        _l.append("branch_same_again=%r" % (_urmb_advance(_s0, (_b0.next.name, _bi.name, _bi.entries[0][1][0].name, _b1.name), False, _b1) == _s1,))
        _l.append("branch_strip=%r" % (type(urm_branch_strip("in", 18, "warn")).__name__ != "Null",))
        _l.append("branch_setting=%r" % (x52URM.SettingsClass.defaultValues.get("urmcBranchChip") == 2 and store._urmb_state is None,))
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
        # An archive patched by an earlier build is upgraded in place. After
        # it there must be ONE chip (the draggable one, not also the one the
        # first version put in the notification column) and ONE map screen,
        # the current one. Read from the screen sources in the archive.
        _wp = renpy.file("0x52-URM/screens/watchpanel.rpy.x52").read().decode("utf-8")
        _vr = renpy.file("0x52-URM/screens/vars.rpy.x52").read().decode("utf-8")
        _cn = (_wp.count("drag_name 'urmb_chip'"), _wp.count("urm_branch_view()"), _wp.count("urm_branch_close"))
        _l.append("chip_is_one_draggable_piece=%r" % (_cn == (1, 1, 1) or _cn,))
        _mn = (_vr.count("screen urm_route_map("), _vr.count("DynamicDisplayable(urm_map_overview"), _vr.count("SetScreenVariable('_urmmTip'"), _vr.count("in _urmmB.draw:"), _vr.count("in _urmmV.codes:"), _vr.count("in _urmmV.picks:"), _vr.count("DynamicDisplayable(urm_map_bubble"), _vr.count("_urmmAsk"), _vr.count("in _urmmV.dots:"))
        _l.append("map_screen_is_the_new_one_once=%r" % (_mn == (1, 1, _mn[2], 1, 1, 1, 1, 0, 0) and _mn[2] >= 5 or _mn,))
        # The chip's DEFAULT place is bottom left. Where the player dropped
        # it is kept in the game's saved settings, and a scratch copy of a
        # real game reads the player's own: Now and Then failed here with
        # (1362, 1034) once the chip had been dragged in the real game. So
        # the kept place is put aside for this one call, and noted.
        _sc = type(x52URM.Settings)
        _sh = "get" in _sc.__dict__
        _sr = _sc.__dict__.get("get")
        _sg = _sc.get
        def _nokept(self, name, *a, **k):
            if name == "urmcBranchPos":
                return None
            return _sg(self, name, *a, **k)
        try:
            _kp = x52URM.Settings.get("urmcBranchPos")
        except Exception:
            _kp = None
        _sc.get = _nokept
        try:
            _bp = urm_branch_pos()
        finally:
            if _sh:
                _sc.get = _sr
            else:
                del _sc.get
        _l.append("chip_place=%r" % (_bp[0] < config.screen_width // 4 and _bp[1] > config.screen_height * 3 // 4 or _bp,))
        if _kp:
            with open(_po.path.join(config.basedir, "urm_probe_graph.txt"), "a") as _nf:
                _nf.write("\\nchip: the player's own place in this game is %r of the screen, drawn at %r; the default was checked\\n" % (tuple(_kp), urm_branch_pos()))
        # A prop game (tests/make_props.py) must really hold its story: one
        # engine here ignores loose script files, and a prop built that way
        # passed while testing nothing of its own.
        if renpy.loadable("prop_script.rpyc"):
            _l.append("prop_story_loaded=%r" % (renpy.has_label("prop_tl") and renpy.has_label("p0_c6") and renpy.has_label("p17_many"),))
        # The story-graph comparison ran in its own block just before this one.
        _l.extend(globals().get("_urmpg_lines") or ["graph_probe=missing"])
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
        # The game's newest real save, unpickled with URM+ installed.
        _sv = _po.path.join(config.basedir, "urm_probe_save.save")
        if _po.path.exists(_sv):
            import zipfile as _zf
            try:
                from renpy.compat.pickle import loads as _ld
            except ImportError:
                from cPickle import loads as _ld
            try:
                _ld(_zf.ZipFile(_sv).read("log"))
                _l.append("newest_save_loads=True")
            except Exception as _e:
                _l.append("newest_save_loads=%r" % (_e,))
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
        _urmm_st.view = urm_map_build(_mz, _ix)
        _sd = renpy.display.screen.ScreenDisplayable(renpy.display.screen.get_screen_variant("urm_route_map"), None, "screens")
        _sd.scope["_scope"] = None
        _sd.update()
        _l.append("map_screen_builds=%r" % (len(_urmm_st.view.boxes) > 0,))
        # ... and from the map with the forms of idea 13 in it: a faded
        # box, a "?" in a box, a "?" on a line.
        _urmm_st.view = _v13
        _sd = renpy.display.screen.ScreenDisplayable(renpy.display.screen.get_screen_variant("urm_route_map"), None, "screens")
        _sd.scope["_scope"] = None
        _sd.update()
        _l.append("map_screen_builds_idea13=%r" % (len(_v13.codes) == 1 and any(b.faded for b in _v13.boxes),))
        # The user's picks "1b2b3a" (2026-11-20), on THIS engine's store and
        # with its own displayables. 3a: the ways of a check are titled with
        # the test in words and a chip for what the player has - amber when
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
        _l.append("map_picks_ways=%r" % (_wp3 == [("Urmprobe ws is bad", None, ("you: okay", "warn")), ("Urmprobe wn is at least 1", None, ("you: 2", "gain")), ("Otherwise", None, None), ("Urmprobe wn is at least 2", None, ("you: 2", "gain")), ("Otherwise", None, None)] or _wp3,))
        _pk = [t for _x, _y, t in _vp.picks]
        _l.append("map_picks_marks=%r" % ((_pk == [urm_pick_tip(None), urm_pick_tip("Lines change with Urmprobe wl")] and not list(_vp.dots) and not list(_vp.marks) and not [b.title for b in _vp.boxes if b.ring]) or (_pk, list(_vp.dots), list(_vp.marks)),))
        _shown = (config.screen_width, config.screen_height - x52URM.scalePxInt(70))
        _top = (max(_vp.height, _shown[1]) - _vp.height) // 2
        _adj = renpy.display.behavior.Adjustment()
        _bad = []
        _spots = [(t, x - x52URM.scalePxInt(16), y - x52URM.scalePxInt(16), x52URM.scalePxInt(32), x52URM.scalePxInt(32)) for x, y, t in _vp.picks]
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
    _urmgf_on = bool(_urmgf_os.environ.get("URM_GATE_FONT_LIST"))
    if _urmgf_on:
        config.font_transforms = ["smooth"]
        _urmgf_own = config.font_transforms

init 1000 python:
    if _urmgf_on:
        _urmgf = []
        try:
            _urmgf.append("font_list_urm_started=%r" % (hasattr(store, "x52URM") and renpy.has_screen("URM_main") and "x52Overlay" in config.layers,))
            _urmgf.append("font_list_urm_plus_started=%r" % (hasattr(store, "urm_panel") and hasattr(store, "_urmft_available"),))
            _urmgf.append("font_list_game_keeps_its_own=%r" % ((config.font_transforms is _urmgf_own and len(_urmgf_own) == 1 and _urmgf_own[0] == "smooth") or repr(config.font_transforms),))
            _urmgf.append("font_list_no_font_offered=%r" % (len(_urmft_available()) == 0 or [r[0] for r in _urmft_available()],))
            _urmgf.append("font_list_no_override_asked=%r" % (renpy.game.preferences.font_transform is None or renpy.game.preferences.font_transform,))
        except Exception as _e:
            _urmgf.append("font_list_error=%r" % (_e,))
        open(_urmgf_os.path.join(config.basedir, "urm_probe_fonts.txt"), "w").write("\\n".join(_urmgf))
        _urmgf_os._exit(0)

'''

FONT_LIST_LINES = ("font_list_urm_started", "font_list_urm_plus_started",
                   "font_list_game_keeps_its_own", "font_list_no_font_offered",
                   "font_list_no_override_asked")


def font_list(py, flags, start, copy, env):
    """The engine once more, as a game whose config.font_transforms is a
    list. Returns the problems found."""

    report = os.path.join(copy, "urm_probe_fonts.txt")
    trace = os.path.join(copy, "traceback.txt")
    for path in (report, trace):
        if os.path.exists(path):
            os.remove(path)
    listed = dict(env)
    listed["URM_GATE_FONT_LIST"] = "1"
    try:
        subprocess.run([py] + flags + [start, ".", "lint"], cwd=copy, env=listed,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    except subprocess.TimeoutExpired:
        return ["font list: the engine timed out"]
    # Ren'Py 8.5 in lint mode notes an error raised while loading and goes
    # on (seen 2026-11-20: URM's FontsHandler raised, the check below still
    # ran). A player gets the error screen. So a traceback is a failure,
    # whether or not the check was reached.
    if os.path.exists(trace):
        text = open(trace, "rb").read().decode("utf-8-sig", "replace")
        short = [l.strip() for l in text.split("-- Full Traceback")[0].splitlines() if l.strip()]
        where = [l for l in short if l.startswith("File ")]
        return ["font list: the game raised while loading with config.font_transforms = [\"smooth\"]: %s  [%s]"
                % (short[-1] if short else "?", where[-1] if where else "?")]
    if not os.path.exists(report):
        return ["font list: the game did not load with config.font_transforms = [\"smooth\"], and left no traceback"]
    values = dict(l.split("=", 1) for l in open(report).read().splitlines() if "=" in l)
    problems = ["font list: %s=%s" % (key, value)
                for key, value in sorted(values.items()) if value != "True"]
    problems += ["font list: %s missing" % key for key in FONT_LIST_LINES if key not in values]
    return problems


BUILD_PROBE = u'''import os, sys
sys.path.insert(0, sys.argv[3])
import urmfix
urmfix.BASE = os.path.abspath(sys.argv[1])
renpy = urmfix.load_engine()
payload, digest = urmfix.compile_rpy(renpy, sys.argv[2], "zzzz_urm_probe.rpy")
urmfix.write_archive(os.path.join(urmfix.BASE, "game", "zzzz_urm_probe.rpa"),
                     {"zzzz_urm_probe.rpyc": urmfix.write_native_rpyc(renpy, [(1, payload)], digest)})
print("probe built")
'''


def interpreter(game):
    """The same choice the .bat makes."""

    found = sorted(glob.glob(os.path.join(game, "lib", "*x86_64*", "python.exe")))
    found += sorted(glob.glob(os.path.join(game, "lib", "*", "python.exe")))
    if os.path.exists(os.path.join(game, "lib", "python.exe")):
        found.append(os.path.join(game, "lib", "python.exe"))
    return found[0] if found else None


def environment(game, py):
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    libs = glob.glob(os.path.join(game, "lib", "pythonlib*"))
    if libs:
        env["PYTHONPATH"] = libs[0] + os.pathsep + os.path.dirname(py)
    return env


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


def run_bat(bat, game):
    command = 'cmd /s /c ""%s" "%s" install"' % (bat, game)
    result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=900)
    return result.stdout.decode("utf-8", "replace")


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
    nobody may write, rename or delete it."""

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        import ctypes
        from ctypes import wintypes
        self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.k.CreateFileW.restype = wintypes.HANDLE
        self.k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                       wintypes.HANDLE]
        # GENERIC_READ, FILE_SHARE_READ, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL
        self.h = self.k.CreateFileW(self.path, 0x80000000, 1, None, 3, 0x80, None)
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


def addon_in(copy, read_archive):
    """What of the add-on a game folder holds: the entries of URM's archive,
    the md5 the installer stored at the end of the compiled add-on, and every
    file or folder that could be a second copy of the add-on or what an
    install left lying about."""

    contents = read_archive(os.path.join(copy, "game", "0x52_URM.rpa"))
    entry = contents.get(urm_source.ENTRY)
    stored = binascii.hexlify(entry[-16:]).decode("ascii") if entry else None
    loose = []
    for root, dirs, files in os.walk(copy):
        for name in dirs + files:
            low = name.lower()
            if low.startswith(("game_fixes", "zzz_urm_compat", "_urmfix_", "0x52-urm")) \
                    or low.endswith((".urmnew", ".urmold")):
                loose.append(os.path.relpath(os.path.join(root, name), copy))
    return sorted(contents), stored, sorted(loose)


def scenarios(bat, copy, tool):
    """What users run into besides a clean install. Run on an installed copy."""

    problems = []
    archive = os.path.join(copy, "game", "0x52_URM.rpa")
    exes = [os.path.join(copy, n) for n in os.listdir(copy) if n.lower().endswith(".exe")]

    # The game is open: its .exe (and on Ren'Py 8 its archives) are held.
    for what, path in [("game open", e) for e in exes[:1]] + [("archive open", archive)]:
        before = digest(archive)
        with held(path):
            out = run_bat(bat, copy)
        why = []
        if "The game is open" not in out:
            why.append("no 'The game is open' message")
        if "Traceback" in out:
            why.append("traceback")
        if "Wrote game" in out:
            why.append("claims it wrote")
        if digest(archive) != before:
            why.append("archive changed")
        if os.path.exists(archive + ".urmnew"):
            why.append("left 0x52_URM.rpa.urmnew behind")
        if why:
            tail = " | ".join(l.strip() for l in out.strip().splitlines()[-3:])
            problems.append("%s: %s  [%s]" % (what, ", ".join(why), tail))
    if not exes:
        problems.append("game open: no .exe in the copy to hold")

    # Upgrade: the game has the build from before the pieces - the add-on as
    # one game_fixes.rpy - and this build is installed over it. It must end
    # up with exactly what a clean install of this build gives: the same
    # entries in URM's archive, the add-on in it this build's and there
    # once, and nothing of either install lying loose. The old add-on left
    # in beside the new one would define everything twice.
    read_archive = installer_code(tool).read_archive
    clean = addon_in(copy, read_archive)
    if not os.path.exists(OLD_BAT):
        problems.append("upgrade: %s is missing" % OLD_BAT)
    else:
        why = []
        if "Wrote game" not in run_bat(OLD_BAT, copy):
            why.append("the build from before the pieces did not install")
        out = run_bat(bat, copy)
        why += ["bat: " + b for b in bad_lines(out)]
        if "Wrote game" not in out:
            why.append("wrote nothing")
        names, stored, loose = addon_in(copy, read_archive)
        if stored != ADDON["md5"]:
            why.append("the add-on in the archive is not this build's (md5 %s)" % stored)
        extra = [n for n in names if n not in clean[0]]
        gone = [n for n in clean[0] if n not in names]
        if extra:
            why.append("left in the archive: %s" % ", ".join(extra))
        if gone:
            why.append("gone from the archive: %s" % ", ".join(gone))
        if loose:
            why.append("left in the game folder: %s" % ", ".join(loose))
        if why:
            tail = " | ".join(l.strip() for l in out.strip().splitlines()[-3:])
            problems.append("upgrade: %s  [%s]" % (", ".join(why), tail))

    # A folder name with every character cmd treats specially, started by
    # double-clicking the .bat inside it.
    odd = copy + ODD_NAME
    if os.path.exists(odd):
        shutil.rmtree(odd)
    rename_when_free(copy, odd)
    try:
        inside = os.path.join(odd, "URM_fix.bat")
        shutil.copy2(bat, inside)
        before = os.path.getmtime(os.path.join(odd, "game", "0x52_URM.rpa"))
        out = double_click(inside)
        os.remove(inside)
        why = ["bat: " + b for b in bad_lines(out)]
        if "Wrote game" not in out:
            why.append("wrote nothing")
        elif os.path.getmtime(os.path.join(odd, "game", "0x52_URM.rpa")) == before:
            why.append("says it wrote, archive not replaced")
        if why:
            tail = " | ".join(l.strip() for l in out.strip().splitlines()[-4:])
            problems.append("odd folder name: %s  [%s]" % (", ".join(why), tail))
    finally:
        rename_when_free(odd, copy)

    return problems


def check(bat, scratch, game):
    name = os.path.basename(os.path.normpath(game))
    copy = os.path.join(scratch, name)
    problems = []

    py = interpreter(game)
    start = launcher(game)
    if py is None or start is None:
        return name, ["no interpreter or launcher found"], ""

    left_out = copy_game(game, copy)
    saves = glob.glob(os.path.join(game, "game", "saves", "*.save"))
    if saves:
        shutil.copy2(max(saves, key=os.path.getmtime), os.path.join(copy, "urm_probe_save.save"))
    py = interpreter(copy)
    env = environment(copy, py)
    kind = os.path.basename(os.path.dirname(py))

    out = run_bat(bat, copy)
    bad = bad_lines(out)
    if "Wrote game" not in out:
        bad.append("the .bat wrote nothing")
    if bad:
        problems.extend("bat: " + b for b in bad)
        return name, problems, kind

    tool = os.path.join(scratch, "_tool", name)
    if not os.path.exists(tool):
        os.makedirs(tool)
    text = open(bat, "rb").read().decode("utf-8", "replace").replace("\r\n", "\n")
    payload = text.split("rem PAYLOAD_BEGIN\n", 1)[1]
    with open(os.path.join(tool, "urmfix.py"), "w", newline="\n") as f:
        f.write(payload)
    with open(os.path.join(tool, "build_probe.py"), "w") as f:
        f.write(BUILD_PROBE)
    # The frozen reference readers (init 1998), the story-graph comparison
    # (init 1999, first), then the main probe. UTF-8 with LF, as the engine
    # reads it - the host's default encoding is not UTF-8 on Windows.
    here = os.path.dirname(os.path.abspath(__file__))
    with io.open(os.path.join(here, "baseline", "graph_refs.rpy"), encoding="ascii") as f:
        refs = f.read()
    # The references of rework moves 8 and 9: the script index, frozen whole.
    with io.open(os.path.join(here, "baseline", "graph_refs_m8.rpy"), encoding="ascii") as f:
        refs = refs + u"\n" + f.read()
    with io.open(os.path.join(here, "probe_graph.rpy"), encoding="utf-8") as f:
        graph = f.read()
    probe = PROBE.replace(u"@@ADDON_MD5@@", ADDON["md5"]).replace(
        u"@@ADDON_HEADERS@@", u"%r" % (ADDON["headers"],))
    with io.open(os.path.join(tool, "urm_probe.rpy"), "w", encoding="utf-8", newline="\n") as f:
        f.write(FONT_LIST + refs + u"\n" + graph + u"\n" + probe)

    flags = ["-I"] if "py3" in kind else ["-s"]
    if glob.glob(os.path.join(copy, "lib", "pythonlib*")):
        flags = ["-O"] + flags  # a .pyo-only library, as the .bat knows
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
    if not os.path.exists(report):
        tb = os.path.join(copy, "traceback.txt")
        why = open(tb, "rb").read().decode("utf-8", "replace").strip().splitlines()[-1] \
            if os.path.exists(tb) else "no traceback"
        if left_out:
            why = "game init needs media (%s left out): %s" % (", ".join(left_out), why)
        problems.append("engine: " + why)
        return name, problems, kind

    values = dict(l.split("=", 1) for l in open(report).read().splitlines() if "=" in l)
    for key, value in sorted(values.items()):
        if value != "True":
            problems.append("engine: %s=%s" % (key, value))

    # The story-graph comparison must have run to its end: a probe that
    # stopped early would otherwise pass on the lines it did print.
    for key in GRAPH_LINES + ADDON_LINES:
        if key not in values:
            problems.append("engine: %s missing" % key)
    if os.path.exists(os.path.join(game, "prop_stamp.txt")):
        for key in ("prop_story_loaded", "prop_translation_checked"):
            if key not in values:
                problems.append("engine: %s missing - the prop did not load its own script" % key)

    notes = os.path.join(copy, "urm_probe_graph.txt")
    if os.path.exists(notes):
        GRAPH_NOTES[name] = [l for l in io.open(notes, encoding="utf-8").read().splitlines()
                             if l.strip() and "=" not in l.split(":")[0]]

    # A game with a list in config.font_transforms must load with URM. On
    # the props, so every engine is asked and none takes long; a real game
    # that has one says so itself in the run above.
    if os.path.exists(os.path.join(game, "prop_stamp.txt")):
        problems.extend(font_list(py, flags, start, copy, env))

    problems.extend(scenarios(bat, copy, tool))
    return name, problems, kind


# The add-on as the pieces say it is (tests/urm_source.py): the md5 of the
# joined file and the line of each of its blocks. Filled in by main(); the
# probe compares what the engine loaded with it.
ADDON = {}
ADDON_LINES = ("addon_is_the_joined_pieces", "addon_blocks_run_in_order")

# Per game: what the story-graph comparison covered. Printed, never gating.
GRAPH_NOTES = {}

# Every line tests/probe_graph.rpy must print (each must also be True).
GRAPH_LINES = (
    "ref_live_flow", "ref_live_text", "ref_live_live", "ref_live_lex",
    "ref_live_chain", "ref_live_search", "ref_live_run", "ref_live_nextmenu",
    "ref_live_stretch",
    "graph_flow_same", "graph_text_same", "graph_urm_same",
    "graph_blocking_same", "graph_passes_same", "graph_live_same",
    "graph_lex_quiet_same",
    "graph_lex_same", "graph_run_same", "graph_run_trunk_same",
    "graph_chain_same", "graph_chain_urm_same", "graph_search_plan_same",
    "graph_search_reach_same", "graph_search_dist_same",
    "graph_search_nextmenu_same", "graph_here_same", "graph_index_same",
    "graph_py_same", "graph_contain_same", "graph_states_ok", "graph_untracked",
    "graph_fixes_on_walk",
    "graph_no_mutation",
)


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
    names = [os.path.basename(os.path.normpath(g)) for g in games]
    if len(set(names)) != len(names):
        print("two games share a folder name; their scratch copies would collide")
        return 2
    try:
        ADDON["md5"] = urm_source.md5()
        ADDON["headers"] = urm_source.block_order()
    except urm_source.SourceError as error:
        print("the add-on's pieces cannot be joined: %s" % error)
        return 2
    print("add-on: %d pieces, %d blocks, md5 %s"
          % (len(urm_source.layout()), len(ADDON["headers"]), ADDON["md5"]))
    failed = 0
    began = time.time()
    jobs = jobs_for(len(games))
    # Measured 2026-11-19, six games at once on 16 CPUs: the two loops of
    # probe_graph.rpy that stop on a 90 s budget got through 0.68-0.74 of
    # what they do alone. 1.45 gives that back (about 80 s on a big game).
    if jobs > 1:
        os.environ.setdefault("URM_GATE_BUDGET_SCALE", "1.45")
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
