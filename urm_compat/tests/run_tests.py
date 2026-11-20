"""
Checks the UI tweaks against a real URM archive, without launching a game.
    python run_tests.py "<a Ren'Py game folder>" [path to 0x52_URM.rpa]
The game folder is only borrowed for its bundled Ren'Py - the tests parse
URM's screens with the same parser the engine uses, so a screen that would
fail to load fails here instead. Nothing in the game is read or written.
What it checks:
  1. every tweak still matches URM's current screen source
  2. applying them twice changes nothing (installing over an install is safe)
  3. the patched screens parse as valid Ren'Py screen language
  4. the unpatched screens parse too, so a failure in 3 is really the tweak
  5. the condition text actually reaches the places it should
Exit code 0 means everything passed.
"""
from __future__ import print_function
import io
import os
import pickle
import shutil
import subprocess
import sys
import tempfile
import zlib
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, TOOLKIT)
sys.path.insert(0, HERE)
import ui_tweaks  # noqa
import urm_source  # noqa  (the add-on's code, joined from its pieces)
PYTHONS = [
    "lib/py3-windows-x86_64/python.exe",
    "lib/py3-windows-i686/python.exe",
    "lib/py3-linux-x86_64/python",
    "lib/py3-mac-universal/python",
]
# Text that must survive into the patched screens, per file.
EXPECTED = {
    "0x52-URM/screens/paths.rpy.x52": [
        "x52URM.scaleText(statement.condition",
        # The gates after the detected one, read-only because URM can only
        # force a path through the node it detected.
        "urm_later_gate_rows()",
        "urmf_force_later",
    ],
    "0x52-URM/screens/choices.rpy.x52": ["x52URM.scaleText(choice.condition"],
    "0x52-URM/screens/watchpanel.rpy.x52": [
        "$ _urmView = (urm_path_view()",
        "$ _urmView = (urm_choice_view()",
        "for _urmIc, _urmIcT, _urmNum, _urmTitle, _urmDim, _urmNeeds, _urmCardRows in _urmView[1]",
        "for _urmDepth, _urmPre, _urmChips, _urmNote in _urmCardRows",
        # The degradation contract: a missing helper must not raise.
        "hasattr(renpy.store, 'urm_path_view')",
        "hasattr(renpy.store, 'urm_choice_view')",
        # Both notifications can be closed until the situation changes.
        "action Function(urm_note_close, 'choices')",
        "action Function(urm_note_close, 'paths')",
        # The route map is reachable without URM's quickmenu (off by
        # default): a Map button in both headers, and Alt+G.
        "action Function(urm_map_open, 'choices')",
        "action Function(urm_map_open, 'paths')",
        "key 'alt_K_g' action Function(urm_map_open, 'hotkey')",
        "urm_note_hidden('choices')",
        "urm_note_hidden('paths')",
        # Shared or branch-only: the chip at the top of the column, its
        # guard, and its close button.
        "hasattr(renpy.store, 'urm_branch_view')",
        "$ _urmbV = urm_branch_view()",
        "add urm_branch_strip(_urmbV[3]",
        "action Function(urm_branch_close)",
        # ... as its own draggable piece (bottom left by default), no
        # longer an item of the notification column.
        "drag_name 'urmb_chip'",
        "dragged urm_branch_dragged",
        "(the shared-or-branch chip is its own draggable piece, above)",
        # The approved look (UX.md): theme colours through urm_map_colour,
        # cards on the theme's box colour, chips coloured by their tone.
        "background urm_map_colour('box')",
        "background urm_map_colour(_urmCt + 'Bg')",
        # Status glyphs (tick, lock) in the icon font, never in the text.
        "text _urmIc style_suffix 'icon'",
    ],
    "0x52-URM/screens/search.rpy.x52": [
        # The Deeper button, and its degradation guard: no helper, no button.
        "getattr(x52URM.Search, 'urmcNextDepth', 0) > 0",
        "Function(x52URM.Search.urmcDeepen)",
        # The depth rows, hidden unless the setting was actually registered.
        "'urmcSearchDepth' in x52URM.SettingsClass.defaultValues",
        "SetField(x52URM.Settings, 'urmcSearchDepth', 2)",
        # Browse the whole store, without knowing a name.
        "SetLocalVariable('expandObjectVars', urm_store_root())",
    ],
    "0x52-URM/screens/vars.rpy.x52": [
        "Function(urm_copy, var.name)",
        # The prophecy panel, and its guard: no compiled helper, no panel.
        "renpy.has_screen('urmi_var_panel')",
        "use urmi_var_panel(var, valueInput)",
        # The alert banner closes on whichever layer it was shown on.
        "action Function(urmal_close)",
        # The route map draws the rows game_fixes.rpy decided, each at the
        # height it was given and through the fade; a box has a title only
        # when it was given one; check diamonds ride on the line.
        "for _urmmRl, _urmmRtip, _urmmRf, _urmmRh, _urmmRc in _urmmB.draw:",
        "at urm_map_fade(_urmmRf)",
        "ysize _urmmRh",
        "if _urmmB.title:",
        "for _urmmDx, _urmmDy, _urmmDtip in _urmmV.marks:",
        # Idea 13: a way's box goes through the fade too ("If none apply"),
        # and the "?" of a custom statement with content inside is drawn in
        # a box and on a line, its reason said through the diamonds' tip.
        "at urm_map_fade(_urmmB.faded)",
        "for _urmmDx, _urmmDy, _urmmDtip in _urmmV.codes:",
        "elif _urmmCk == 'code':",
        # The picks "1b2b3a": the hover text is a bubble in the part of the
        # map in view, beside its mark (a spot); big diamonds can be pointed
        # at; the legend names the two marks; a way's box shows what the
        # player has after its title.
        "add DynamicDisplayable(urm_map_bubble, _urmmTip, _urmmV, _urmmXadj, _urmmYadj, (config.screen_width, _urmmViewH))",
        "for _urmmDx, _urmmDy, _urmmDtip in _urmmV.picks:",
        "hovered SetScreenVariable('_urmmTip', (_urmmDtip, _urmmDx - _urmmS(12), _urmmDy - _urmmS(12), _urmmS(24), _urmmS(24)))",
        "text 'the game picks the way'",
        "text 'only lines change (point at one)'",
        "if _urmmB.title and _urmmB.have and _urmmB.have_beside:",
    ],
    "0x52-URM/screens/labels.rpy.x52": [
        "urm_labels(str(labelFilter))",
        "enumerate(_urmLabels[",
        "urm_seen(labelName)",
        "title='What the marks mean'",
    ],
    "0x52-URM/screens/quickmenu.rpy.x52": [
        "use URM_quickmenu_button('\\uf184', '{urm_notl}Map{/urm_notl}', Function(urm_map_open))",
        "if x52URM.Settings.quickmenuBtnSkipUnseen:",
        # Straight at the field, not Preference("skip", ...), whose name
        # lookup compares against the translated word.
        "ToggleField(_preferences, 'skip_unseen', True, False)",
    ],
    "0x52-URM/screens/options.rpy.x52": [
        "('quickmenuBtnSkipUnseen', {",
        "'urmcLookAhead': {",
        "'urmcBranchChip': {",
        # Game font, and its guard: no add-on, no choices instead of a crash.
        "('urmcFont', {",
        "urmft_options() if hasattr(renpy.store, 'urmft_options') else {}",
        # The URM+ badge on every URM+ row of every settings table.
        "if settingName.startswith('urmc') or settingName == 'quickmenuBtnSkipUnseen':",
        "text '{urm_notl}URM+{/urm_notl}' size",
    ],
}
# Text that must NOT survive - an older version of a tweak left in place
# alongside the new one would render every line twice.
FORBIDDEN = {
    # A bare Hide looks on the "screens" layer; the banner is on URM's own,
    # so OK, "Stop alerting" and the timer did nothing.
    "0x52-URM/screens/vars.rpy.x52": ["Hide('urmal_alert')"],
    "0x52-URM/screens/watchpanel.rpy.x52": [
        "_urmItem.condition",
        "urm_summary(_urmItem)",
        "urm_condition(_urmItem)",
        "urm_next_gates()",
        # URM's bundled Roboto is subsetted and has no U+2192, so an arrow
        # renders as a missing-glyph box.
        "\\u2192",
        # v7's two-value row, and the xsize that did not pad the column.
        "for _urmMark, _urmBody in ",
        "xsize x52URM.scalePxInt(52)",
        # v8's marker column and its single-rule-between-gates layout.
        "_urmRows",
        "min_width x52URM.scalePxInt(44)",
        # Solid(None) raises while the overlay is drawn, and a theme name that
        # does not resolve returns None silently - so backgrounds stay bare.
        "background Solid(",
        # The code-dump cards the user rejected ("disgusting notifications").
        "urm_choice_cards()",
        "urm_path_cards()",
    ],
}
# The helpers the patched screens call, which the installer compiles into the
# archive from game_fixes.rpy. A screen calling a helper that is not there
# raises while the overlay is being drawn.
HELPERS = ["urm_branch_view", "urm_branch_close", "urm_branch_strip",
           "urm_branch_pos", "urm_branch_dragged", "urm_map_overview", "urm_map_fade",
           "urm_path_view", "urm_choice_view", "urm_note_close",
           "urm_note_hidden", "urm_map_open", "urm_map_close", "urm_map_view",
           "urm_map_colour", "urm_map_esc", "urm_copy", "urm_store_root",
           "urm_labels", "urm_seen", "urm_later_gates",
           # The script index and what the editor asks it.
           "urm_index_status", "urm_checks", "urm_writers", "urm_readers",
           "urm_gate_count", "urm_var_panel", "urmi_fill",
           # The variable panel the editor draws.
           "urm_panel", "urmi_ui", "urmi_ui_set", "urmi_ui_toggle",
           "urmi_settable", "urmi_set_words", "urmi_block_limit",
           "urmi_small_line",
           # The gallery switch.
           "urmg_toggle", "urmg_badge_text",
           # Rollback: back to the last choice.
           "urmr_back_to_choice",
           # Forcing paths URM marks "not forceable".
           "urm_later_gate_rows", "urmf_force_later",
           # Flags: choices kept as words in a collection.
           "urmfl_has", "urmfl_rows", "urmfl_set", "urmfl_var", "urmfl_is_on",
           # Alerts.
           "urmal_toggle", "urmal_is", "urmal_lines", "urmal_banner_marked"]

# Inside a Ren'Py store, dict / list / set are rebound to the rollback-tracked
# Revertable kinds (minstore.py:37-50) and [] / {} literals are rewritten to
# them. A long-lived cache built from those is copied into the rollback log on
# every interaction it changes in. Code in these blocks must use python_dict,
# python_list and python_set - and the unit tests cannot see the difference,
# because plain Python maps those straight back to the builtins. So it is
# checked here, as text.
import re as _re
TRACKED = _re.compile(r"(?<![\w.])(dict|list|set)\(|=\s*(\[\]|\{\})\s*$")
TRACKED_BLOCKS = ("_urmc_", "_urmi_", "_URMIndex", "_urmp_", "_urmm_",
                  "class _URMSGraph", "_urmb_")
# Blocks held to the strict rule of step 7p: asked on every line or redraw.
STRICT_BLOCKS = (("class _URMSGraph", "story-graph"),
                 ("def _urmb_advance", "branch"))
# What the check_*.py loaders search game_fixes.rpy for. Each must be in
# exactly one "init 999 python:" chunk (step 7o).
LOADER_NEEDLES = ("class _URMSGraph", "def _urmb_advance",
                  "def _urm_flatten", "def _urmm_walk", "def _urms_next",
                  "def _urms_small_change", "class _URMIndex",
                  "class _URMFState", "def _urmc_matchVarName",
                  "def _urmc_parse", "def urm_later_gate_rows",
                  "def urm_checks", "def urm_panel", "def urmfl_set",
                  "def urmal_toggle", "def urmg_toggle",
                  "def urmr_back_to_choice")


def find_python(game):
    for rel in PYTHONS:
        path = os.path.join(game, rel)
        if os.path.exists(path):
            return path
    return None
def read_archive(path):
    with open(path, "rb") as f:
        parts = f.readline().split()
        offset = int(parts[1], 16)
        key = int(parts[2], 16) if parts[0] == b"RPA-3.0" else 0
        f.seek(offset)
        index = pickle.loads(zlib.decompress(f.read()))
        out = {}
        for name, entries in index.items():
            if isinstance(name, bytes):
                name = name.decode("utf-8")
            chunks = []
            for entry in entries:
                start = entry[0] ^ key
                length = entry[1] ^ key
                prefix = entry[2] if len(entry) > 2 else b""
                if isinstance(prefix, str):
                    prefix = prefix.encode("latin-1")
                f.seek(start)
                chunks.append(prefix + f.read(length - len(prefix)))
            out[name] = b"".join(chunks)
    return out
def parse_screens(python, game, paths):
    """Returns (ok, output) from the Ren'Py parser."""
    cmd = [python, "-I", "-B", os.path.join(HERE, "validate_x52.py"), game] + paths
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
    return result.returncode == 0, result.stdout.decode("utf-8", "replace")
def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    game = os.path.abspath(argv[1])
    rpa = os.path.abspath(argv[2]) if len(argv) > 2 else os.path.join(
        TOOLKIT, "0x52_URM.rpa")
    if not os.path.isdir(os.path.join(game, "renpy")):
        print("%s has no renpy/ in it - point me at a Ren'Py game folder." % game)
        return 2
    if not os.path.exists(rpa):
        print("No URM archive at %s" % rpa)
        return 2
    python = find_python(game)
    if python is None:
        print("No bundled Python under %s/lib" % game)
        return 2
    print("URM archive: %s" % rpa)
    print("Ren'Py from: %s" % game)
    print()
    failures = []
    # --- 0. the add-on's source is the pieces, and nothing moved ---------
    # A game gets the pieces of urm_compat/game_fixes/ joined in the order
    # of their names (tests/urm_source.py). The join is compared with the
    # hash on record, so an edit nobody meant - a line lost while moving
    # code between pieces, a stray file in the folder - cannot go unnoticed.
    # After an edit that IS meant: python tests/urm_source.py --pin
    print("[0] the add-on's pieces join to the source on record")
    try:
        source_layout = urm_source.layout()
        source_hash = urm_source.sha256()
    except urm_source.SourceError as error:
        print("    FAIL  %s" % error)
        print()
        print("1 FAILED")
        print("  - the pieces cannot be joined, so nothing else was run")
        return 1
    if source_hash == urm_source.pinned():
        print("    pass  %d pieces, %d lines, sha256 %s"
              % (len(source_layout), sum(p[2] for p in source_layout), source_hash[:16]))
    else:
        failures.append("the joined source is not the one on record")
        print("    FAIL  joined  %s" % source_hash)
        print("          record  %s" % urm_source.pinned())
        print("          An edit you meant? Then: python tests/urm_source.py --pin")
    work = tempfile.mkdtemp(prefix="urm_tests_")
    try:
        contents = read_archive(rpa)
        screens = sorted(n for n in contents
                         if n.endswith(".x52") and "/screens/" in n)
        # --- 4. the unpatched screens parse -----------------------------
        plain = os.path.join(work, "plain")
        os.makedirs(plain)
        for name in screens:
            with open(os.path.join(plain, os.path.basename(name)), "wb") as f:
                f.write(contents[name])
        ok, out = parse_screens(
            python, game,
            [os.path.join(plain, os.path.basename(n)) for n in screens])
        print("[1] URM's own screens parse")
        if ok:
            print("    pass  (%d files)" % len(screens))
        else:
            failures.append("URM's unpatched screens do not parse")
            print(out)
        # --- 1. every tweak matches -------------------------------------
        applied, skipped = ui_tweaks.apply(contents)
        print("[2] every tweak still matches URM's source")
        for name, note in applied:
            print("    pass  %s%s" % (name, "  (%s)" % note if note else ""))
        for name, why in skipped:
            failures.append("tweak not applied: %s (%s)" % (name, why))
            print("    FAIL  %s  -- %s" % (name, why))
        # --- 2. applying twice is a no-op -------------------------------
        before = dict(contents)
        ui_tweaks.apply(contents)
        changed = [n for n in before if before[n] != contents[n]]
        print("[3] applying the tweaks twice changes nothing")
        if changed:
            failures.append("second apply rewrote: %s" % ", ".join(changed))
            print("    FAIL  rewrote %s" % ", ".join(changed))
        else:
            print("    pass")
        # --- 5. the condition text reached the right places -------------
        print("[4] the condition reaches the screens that show it")
        for name, needles in EXPECTED.items():
            data = contents.get(name, b"")
            for needle in needles:
                if needle.encode("utf-8") in data:
                    print("    pass  %s <- %s" % (os.path.basename(name), needle))
                else:
                    failures.append("%s is missing %s" % (name, needle))
                    print("    FAIL  %s is missing %s" % (name, needle))
        for name, needles in FORBIDDEN.items():
            data = contents.get(name, b"")
            for needle in needles:
                if needle.encode("utf-8") in data:
                    failures.append("%s still contains %s" % (name, needle))
                    print("    FAIL  %s still contains %s" % (
                        os.path.basename(name), needle))
                else:
                    print("    pass  %s has no stale %s" % (
                        os.path.basename(name), needle))
        # --- 6. an archive patched by an older build upgrades cleanly ----
        print("[5] an archive from an older build upgrades, not doubles")
        wp = "0x52-URM/screens/watchpanel.rpy.x52"
        for version, template in (("v1", ui_tweaks._LINE_V1),
                                  ("v2", ui_tweaks._LINE_V2),
                                  ("v3", ui_tweaks._LINE_V3),
                                  ("v4", ui_tweaks._LINE_V4)):
            older = read_archive(rpa)
            # Reproduce what that build wrote, then re-apply.
            text = older[wp]
            for anchor, source in (
                    (ui_tweaks._PATH_COUNT, "x52URM.PathDetection.statements"),
                    (ui_tweaks._CHOICE_HIDDEN, "x52URM.Choices.currentChoices")):
                text = text.replace(
                    ui_tweaks._as_bytes(anchor),
                    ui_tweaks._as_bytes(anchor + "\n\n" + template % source), 1)
            older[wp] = text
            ui_tweaks.apply(older)
            upgraded = older[wp]
            # Two: one call per block. The hasattr guard names the helper as
            # a quoted string, so it does not match "name()".
            blocks = (upgraded.count(b"urm_path_view()")
                      + upgraded.count(b"urm_choice_view()"))
            stale = sum(upgraded.count(n.encode("utf-8"))
                        for n in FORBIDDEN[wp])
            if blocks == 2 and stale == 0:
                print("    pass  %s upgraded: both blocks carded, 0 left over"
                      % version)
            else:
                failures.append(
                    "%s upgrade left %d calls and %d stale lines"
                    % (version, blocks, stale))
                print("    FAIL  %s: %d calls, %d stale lines"
                      % (version, blocks, stale))

        # v5 and v7 appended their block after URM's own line; v8 replaced it
        # outright and carried its own fallback, so it is rebuilt from the
        # template the installer still keeps for exactly this purpose.
        def put_v5_v7(text, template):
            for anchor, helper in (
                    (ui_tweaks._PATH_COUNT, "urm_path_lines"),
                    (ui_tweaks._CHOICE_HIDDEN, "urm_choice_lines")):
                text = text.replace(
                    ui_tweaks._as_bytes(anchor),
                    ui_tweaks._as_bytes(anchor + template % helper), 1)
            return text

        # v9: the code-style cards (urm_*_cards), the build before the chips.
        def put_v9(text, _template):
            text = text.replace(
                ui_tweaks._as_bytes(ui_tweaks._PATH_COUNT),
                ui_tweaks._as_bytes(ui_tweaks._draw(
                    "urm_path_cards", ui_tweaks._PATH_FALLBACK)), 1)
            return text.replace(
                ui_tweaks._as_bytes(ui_tweaks._CHOICE_HIDDEN),
                ui_tweaks._as_bytes(ui_tweaks._CHOICE_HIDDEN + "\n"
                                    + ui_tweaks._draw("urm_choice_cards")), 1)

        def put_v8(text, _template):
            text = text.replace(
                ui_tweaks._as_bytes(ui_tweaks._PATH_COUNT),
                ui_tweaks._as_bytes(ui_tweaks._draw_v8(
                    "urm_path_lines", ui_tweaks._PATH_FALLBACK)), 1)
            return text.replace(
                ui_tweaks._as_bytes(ui_tweaks._CHOICE_HIDDEN),
                ui_tweaks._as_bytes(ui_tweaks._CHOICE_HIDDEN + "\n"
                                    + ui_tweaks._draw_v8("urm_choice_lines")), 1)

        for version, template, place in (("v5", ui_tweaks._DRAW_V5, put_v5_v7),
                                         ("v7", ui_tweaks._DRAW_V7, put_v5_v7),
                                         ("v8", None, put_v8),
                                         ("v9", None, put_v9)):
            older = read_archive(rpa)
            older[wp] = place(older[wp], template)

            ui_tweaks.apply(older)
            upgraded = older[wp]
            blocks = (upgraded.count(b"urm_path_view()")
                      + upgraded.count(b"urm_choice_view()"))
            carded = upgraded.count(
                b"_urmNeeds, _urmCardRows in _urmView[1]")
            stale = sum(upgraded.count(n.encode("utf-8"))
                        for n in FORBIDDEN[wp])

            if blocks == 2 and carded == 2 and stale == 0:
                print("    pass  %s upgraded: both blocks carded, 0 left over"
                      % version)
            else:
                failures.append(
                    "%s upgrade left %d calls, %d carded, %d stale"
                    % (version, blocks, carded, stale))
                print("    FAIL  %s: %d calls, %d carded, %d stale"
                      % (version, blocks, carded, stale))

        # The route map's screen as each earlier build installed it
        # (inserted last, right before URM_add_item) must become the
        # current one - never two screens of the same name, never the old
        # one left in place.
        vars_rpy = "0x52-URM/screens/vars.rpy.x52"
        add = ui_tweaks._as_bytes(ui_tweaks._ADD_ITEM)
        now = ui_tweaks._as_bytes(ui_tweaks._ROUTE_MAP_SCREEN_V6)
        for label, earlier in (("v1", ui_tweaks._ROUTE_MAP_SCREEN),
                               ("v2", ui_tweaks._ROUTE_MAP_SCREEN_V2),
                               ("v3", ui_tweaks._ROUTE_MAP_SCREEN_V3),
                               ("v4", ui_tweaks._ROUTE_MAP_SCREEN_V4),
                               ("v5", ui_tweaks._ROUTE_MAP_SCREEN_V5)):
            older = read_archive(rpa)
            ui_tweaks.apply(older)
            was = older[vars_rpy].count(now + add)
            older[vars_rpy] = older[vars_rpy].replace(
                now + add, ui_tweaks._as_bytes(earlier) + add)
            # what only the current screen has: an earlier one must not
            stale = b"in _urmmV.picks:" in older[vars_rpy]
            ui_tweaks.apply(older)
            map_screens = older[vars_rpy].count(b"screen urm_route_map(")
            newer = older[vars_rpy].count(now + add)
            if was == 1 and not stale and map_screens == 1 and newer == 1:
                print("    pass  route map %s upgraded to the current screen, one screen" % label)
            else:
                failures.append("route map %s upgrade: %d before, stale %r, %d screens, %d new"
                                % (label, was, stale, map_screens, newer))
                print("    FAIL  route map %s upgrade: %d before, stale %r, %d screens, %d new"
                      % (label, was, stale, map_screens, newer))

        # --- 6b. game_fixes.rpy parses at all ----------------------------
        print("[6] game_fixes.rpy parses with the real Ren'Py parser")
        result = subprocess.run(
            [python, "-I", "-B", os.path.join(HERE, "check_rpy.py"), game],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        out = result.stdout.decode("utf-8", "replace")
        if result.returncode == 0:
            for line in out.splitlines():
                if line.startswith("pass"):
                    print("    %s" % line)
        else:
            failures.append("game_fixes.rpy does not parse")
            print(out)

        # --- 8. the effect flattener and its three reductions ------------
        print("[7] the effect flattener only merges what it can prove")
        result = subprocess.run(
            [python, "-I", "-B", os.path.join(HERE, "check_cards.py"), game],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        out = result.stdout.decode("utf-8", "replace")
        if result.returncode == 0:
            print("    pass  (%d cases)" % out.count("pass  "))
        else:
            failures.append("the statement filter unit checks failed")
            print(out)

        # --- 8a. mazes: choices followed to where their effects are ------
        print("[7a] a choice that only jumps shows the flags at its label")
        result = subprocess.run(
            [python, "-I", "-B", os.path.join(HERE, "check_maze.py"), game],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        out = result.stdout.decode("utf-8", "replace")
        if result.returncode == 0:
            print("    pass  (%d cases)" % out.count("pass  "))
        else:
            failures.append("the maze walk unit checks failed")
            print(out)

        print("[7q] shared or branch-only: the player's two cases and the rest")
        result = subprocess.run(
            [python, "-I", "-B", os.path.join(HERE, "check_branch.py"), game],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        out = result.stdout.decode("utf-8", "replace")
        if result.returncode == 0:
            print("    pass  (%d cases)" % out.count("pass  "))
        else:
            failures.append("the branch tracker unit checks failed")
            print(out)

        # --- story-graph rework: the yardstick and the parity diff -------
        # check_graph: today's readers frozen as references, proven against
        # the live code (and, once it exists, the shared graph against them).
        # parity_graph: the pre-rework file and the working file must show
        # the player the same thing. See research/story_graph.
        for step, script, what in (
                ("[7m]", "check_graph.py", "the frozen references match the live readers"),
                ("[7n]", "parity_graph.py", "the working file shows what the pre-rework file showed")):
            print("%s %s" % (step, what))
            result = subprocess.run(
                [python, "-I", "-B", os.path.join(HERE, script), game],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
            out = result.stdout.decode("utf-8", "replace")
            if result.returncode == 0:
                print("    pass  (%d checks)" % out.count("pass  "))
            else:
                failures.append("%s failed" % script)
                print(out)

        # Every test loads pieces of game_fixes.rpy by a needle that must
        # sit in exactly one "init 999 python:" chunk - comments included.
        # A second copy of a needle makes a loader exec the wrong code or
        # abort, so it is counted here once, for all of them.
        print("[7o] every loader needle is in exactly one block")
        needle_chunks = urm_source.chunks()
        needle_bad = []
        for needle in LOADER_NEEDLES:
            count = len([c for c in needle_chunks if needle in c])
            if count != 1:
                needle_bad.append("%r is in %d blocks" % (needle, count))
        if needle_bad:
            failures.append("loader needles: " + "; ".join(needle_bad))
            for line in needle_bad:
                print("    FAIL  %s" % line)
        else:
            print("    pass  (%d needles)" % len(LOADER_NEEDLES))

        # The shared graph block is held to a stricter rule than 7d: inside a
        # game the engine turns EVERY list, dict or set display and every
        # comprehension of them into an object rollback tracks, the moment it
        # is created - and the store's range, sorted and object do the same.
        # The graph is asked on every redraw, so none of them may appear.
        print("[7p] the story-graph and branch blocks build no rollback-tracked object")
        import ast as _ast
        graph_bad = []
        for strict_needle, strict_name in STRICT_BLOCKS:
          graph_chunks = [c for c in needle_chunks if strict_needle in c]
          if len(graph_chunks) == 1:
              newline = chr(10)
              graph_src = newline.join(
                  line[4:] if line.startswith("    ") else line
                  for line in graph_chunks[0].split(newline))
              banned = (_ast.List, _ast.ListComp, _ast.Dict, _ast.DictComp,
                        _ast.Set, _ast.SetComp, _ast.Starred)
              names = ("dict", "list", "set", "range", "sorted", "object",
                       "defaultdict", "Set")
              for node in _ast.walk(_ast.parse(graph_src)):
                  if isinstance(node, banned):
                      graph_bad.append("%s line %d: a %s" % (strict_name, node.lineno, type(node).__name__))
                  elif isinstance(node, _ast.Name) and node.id in names:
                      graph_bad.append("%s line %d: the name %s" % (strict_name, node.lineno, node.id))
                  elif isinstance(node, _ast.ClassDef):
                      bases = [getattr(b, "id", None) for b in node.bases]
                      # _urmsg_text is the text type: a subclass of it is not
                      # an object rollback tracks (_URMSGNote).
                      if bases != ["python_object"] and bases != ["_urmsg_text"]:
                          graph_bad.append("line %d: class %s derives from %r"
                                           % (node.lineno, node.name, bases))
              # The block's own text rules: ASCII, LF only, no backslash
              # continuation. Its chunk ends where the next block's column-0
              # header comment starts.
              own = graph_chunks[0].split(newline + "# ----", 1)[0]
              if not all(ord(ch) < 128 for ch in own):
                  graph_bad.append("a non-ASCII character")
              if "\r" in own:
                  graph_bad.append("a CR line ending")
              for number, line in enumerate(own.split(newline)):
                  if line.rstrip().endswith("\\"):
                      graph_bad.append("line %d ends with a backslash" % number)
          else:
              graph_bad.append("%d blocks hold the %s code" % (len(graph_chunks), strict_name))
        if graph_bad:
            failures.append("%d tracked constructs in the strict blocks" % len(graph_bad))
            for line in graph_bad[:12]:
                print("    FAIL  %s" % line)
        else:
            print("    pass")

        # --- 8b. the search upgrades -------------------------------------
        # Its stand-ins are 0x52's own code, so it is not published.
        print("[7b] the search upgrades do what they claim")
        if not os.path.exists(os.path.join(HERE, "check_search.py")):
            print("    skip  (check_search.py is not part of the public tests)")
        else:
            result = subprocess.run(
                [python, "-I", "-B", os.path.join(HERE, "check_search.py"), game],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            out = result.stdout.decode("utf-8", "replace")
            if result.returncode == 0:
                print("    pass  (%d cases)" % out.count("pass  "))
            else:
                failures.append("the search unit checks failed")
                print(out)

        # --- 8c. the script index -----------------------------------------
        print("[7c] the script index reads what the game checks and sets")
        result = subprocess.run(
            [python, "-I", "-B", os.path.join(HERE, "check_index.py"), game],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        out = result.stdout.decode("utf-8", "replace")
        if result.returncode == 0:
            print("    pass  (%d cases)" % out.count("pass  "))
        else:
            failures.append("the script index unit checks failed")
            print(out)

        print("[7e] the variable panel tells the player what a value gets them")
        result = subprocess.run(
            [python, "-I", "-B", os.path.join(HERE, "check_panel.py"), game],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        out = result.stdout.decode("utf-8", "replace")
        if result.returncode == 0:
            print("    pass  (%d cases)" % out.count("pass  "))
        else:
            failures.append("the variable panel unit checks failed")
            print(out)

        print("[7h] urm_plus.rpy patches URM's screens exactly as the archive build does")
        result = subprocess.run(
            [python, "-I", "-B", os.path.join(HERE, "check_runtime.py"), game, rpa],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        out = result.stdout.decode("utf-8", "replace")
        if result.returncode == 0:
            print("    pass  (%d cases)" % out.count("pass  "))
        else:
            failures.append("the one-file install checks failed")
            print(out)

        print("[7i] any path can be forced, even behind a jump")
        result = subprocess.run(
            [python, "-I", "-B", os.path.join(HERE, "check_force.py"), game],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        out = result.stdout.decode("utf-8", "replace")
        if result.returncode == 0:
            print("    pass  (%d cases)" % out.count("pass  "))
        else:
            failures.append("the force-a-path checks failed")
            print(out)

        print("[7j] flags: choices a game keeps as words in a collection")
        result = subprocess.run(
            [python, "-I", "-B", os.path.join(HERE, "check_flags.py"), game],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        out = result.stdout.decode("utf-8", "replace")
        if result.returncode == 0:
            print("    pass  (%d cases)" % out.count("pass  "))
        else:
            failures.append("the flag checks failed")
            print(out)

        print("[7k] skipping carries on past a small change")
        result = subprocess.run(
            [python, "-I", "-B", os.path.join(HERE, "check_skip.py"), game],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        out = result.stdout.decode("utf-8", "replace")
        if result.returncode == 0:
            print("    pass  (%d cases)" % out.count("pass  "))
        else:
            failures.append("the skip-past-small-changes checks failed")
            print(out)

        print("[7l] alerts: a marked variable or flag being checked stops the skip")
        result = subprocess.run(
            [python, "-I", "-B", os.path.join(HERE, "check_alerts.py"), game],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        out = result.stdout.decode("utf-8", "replace")
        if result.returncode == 0:
            print("    pass  (%d cases)" % out.count("pass  "))
        else:
            failures.append("the alert checks failed")
            print(out)

        print("[7r] a game whose config.font_transforms is not a table: URM starts, the game keeps its own")
        result = subprocess.run(
            [python, "-I", "-B", os.path.join(HERE, "check_fonts.py")],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        out = result.stdout.decode("utf-8", "replace")
        if result.returncode == 0:
            print("    pass  (%d cases)" % out.count("pass  "))
        else:
            failures.append("the font table checks failed")
            print(out)

        print("[7g] rollback goes back to the last choice, and further")
        result = subprocess.run(
            [python, "-I", "-B", os.path.join(HERE, "check_rollback.py"), game],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        out = result.stdout.decode("utf-8", "replace")
        if result.returncode == 0:
            print("    pass  (%d cases)" % out.count("pass  "))
        else:
            failures.append("the rollback checks failed")
            print(out)

        print("[7f] the gallery switch unlocks in menus and writes nothing")
        result = subprocess.run(
            [python, "-I", "-B", os.path.join(HERE, "check_gallery.py"), game],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        out = result.stdout.decode("utf-8", "replace")
        if result.returncode == 0:
            print("    pass  (%d cases)" % out.count("pass  "))
        else:
            failures.append("the gallery switch checks failed")
            print(out)

        # --- 8d. no rollback-tracked containers in long-lived code --------
        print("[7d] long-lived caches use untracked containers")
        bad = []
        for chunk in urm_source.chunks()[1:]:
            if not any(tag in chunk for tag in TRACKED_BLOCKS):
                continue
            for line in chunk.split("\n"):
                code = line.split("#", 1)[0]
                if not code.strip() or code.lstrip().startswith(('"', "'")):
                    continue
                if TRACKED.search(code):
                    bad.append(line.strip())
        if bad:
            failures.append("%d tracked container(s) in index/search code"
                            % len(bad))
            for line in bad[:12]:
                print("    FAIL  %s" % line)
        else:
            print("    pass")

        # --- 7. the helpers the screens call actually exist --------------
        print("[8] game_fixes.rpy defines the helpers the screens call")
        try:
            fixes = urm_source.raw().decode("utf-8", "replace")
        except Exception as e:
            fixes = ""
            failures.append("could not read game_fixes.rpy: %s" % e)
        for helper in HELPERS:
            if ("def %s(" % helper) in fixes:
                print("    pass  %s" % helper)
            else:
                failures.append("game_fixes.rpy has no %s()" % helper)
                print("    FAIL  game_fixes.rpy has no %s()" % helper)
        # --- 9b. the compiled helper loads on Ren'Py 7 too ---------------
        # This one needs the BUILT archive: the helper is compiled into it by
        # build_rpa.py and is not in the URM archive the tweaks are read from.
        print("[10] the compiled helper loads on Ren'Py 7 as well as 8")
        built = os.path.join(TOOLKIT, "..", "dist", "0x52_URM.rpa")
        if not os.path.exists(built):
            print("    skip  no build yet - run build_rpa.py first")
        elif os.path.getmtime(built) < urm_source.newest_mtime():
            # An archive built before the last edit would pass here while
            # saying nothing about the current helper. The installer gate
            # (check_installer.py) compiles and loads the current one on
            # every engine kind; this step is only a quick local check.
            print("    STALE dist/0x52_URM.rpa is older than game_fixes.rpy:"
                  " not checked here. Rebuild with build_rpa.py, or rely on"
                  " the installer gate.")
        else:
            result = subprocess.run(
                [python, "-I", "-B", os.path.join(HERE, "check_rpyc7.py"),
                 game, os.path.abspath(built)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            out = result.stdout.decode("utf-8", "replace")
            if result.returncode == 0:
                for line in out.splitlines():
                    if line.startswith("pass"):
                        print("    %s" % line)
            else:
                failures.append("the helper cannot load on Ren'Py 7")
                print(out)

        # --- 3. the patched screens parse -------------------------------
        patched = os.path.join(work, "patched")
        os.makedirs(patched)
        for name in screens:
            with open(os.path.join(patched, os.path.basename(name)), "wb") as f:
                f.write(contents[name])
        ok, out = parse_screens(
            python, game,
            [os.path.join(patched, os.path.basename(n)) for n in screens])
        print("[9] the patched screens parse")
        if ok:
            print("    pass  (%d files)" % len(screens))
        else:
            failures.append("the patched screens do not parse")
            print(out)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print()
    if failures:
        print("%d FAILED" % len(failures))
        for item in failures:
            print("  - %s" % item)
        return 1
    print("all passed")
    return 0
if __name__ == "__main__":
    sys.exit(main(sys.argv))
