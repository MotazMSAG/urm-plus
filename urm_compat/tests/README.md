# Tests

Checks the UI tweaks in `../ui_tweaks.py` against a real URM archive, without
launching a game.

```bash
"<game>/lib/py3-windows-x86_64/python.exe" -I run_tests.py "<game>"
```

`<game>` is any Ren'Py game folder — it is only borrowed for its bundled
Ren'Py, and nothing in it is read or written. Pass a second argument to test a
different `0x52_URM.rpa`; it defaults to the one in `../`.

Exit code 0 means everything passed.

## What it checks

1. **URM's own screens parse.** The baseline. If this fails, the harness is
   broken, not the tweak.
2. **Every tweak still matches.** The whole design rests on literal text
   matches against URM's screen source. When URM updates, this is the test
   that tells you which tweak needs re-aiming — before a user finds out.
3. **Applying twice changes nothing.** Installing over an existing install,
   or over an already-patched archive, has to be a no-op.
4. **The condition reaches the screens that show it.** Guards against a tweak
   that applies cleanly but drops the thing it was meant to add.
5. **The patched screens parse.** The real gate. URM loads its screens with
   `renpy.load_string`, so a syntax error means URM fails to start. This runs
   the same parser the engine would, so that never reaches a game.

## The tools

| File | What it does |
|---|---|
| `run_tests.py` | the suite above |
| `validate_x52.py` | parses `.x52` screen files with the real Ren'Py SL2 parser; usable on its own against any file |
| `decomp.py` | decompiles URM's `.rpyc` files to readable source, for when you need to look at what a class actually does |

`validate_x52.py` has to stand in for a few things `main()` would normally set
up before any script is parsed — the SL2 statement set, and the ATL warpers
that `renpy/common/000atl.rpy` registers. Without those, ordinary URM screens
report spurious errors.

### Decompiling URM

```bash
"<game>/lib/py3-windows-x86_64/python.exe" -I decomp.py "<game>" <extracted-urm-dir> <out-dir>
```

`<game>` must contain `unrpyc.py` and `decompiler/`. It stubs out
`multiprocessing`, which the bundled interpreters do not ship and which
`unrpyc.py` touches at import.

### Checking the path chain against a real game

`check_gates.py` runs the shipped `urm_path_lines()` against a game's own
compiled script, so you can see what the notification would draw without
launching anything:

```bash
"<game>/lib/py3-windows-x86_64/python.exe" -I check_gates.py "<game>" <file.rpyc> "<condition>"
```

Use the engine belonging to the game the `.rpyc` came from — an AST pickled by
one Ren'Py does not always unpickle in another.

It execs the helper block straight out of the add-on's source (the pieces in
`game_fixes/`, read through `tests/urm_source.py`) against thin
stand-ins for the parts of URM it calls. `nodesToCode` is the one with real
behaviour worth mimicking (URM emits python, jumps and calls, and drops
dialogue), so it is reproduced there rather than imported — which means its
rendering can drift from URM's. The structure, numbering and which row is
marked as taken are the parts this checks.

## Not covered

The tweaks are verified as far as "URM loads and the text is there". Whether a
condition reads well in the corner notification at a given window size is a
look-at-it judgement — these tests cannot make it.
