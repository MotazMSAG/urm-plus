# Getting URM into a Ren'Py game that encrypts its script cache

Some Ren'Py builds write their `.rpyc` files with a custom header and an extra
encryption layer under the usual zlib compression, and reject anything a stock
Ren'Py produced. URM ships stock `.rpyc` files, so the game dies at startup
with:

    Exception: Could not load from archive 0x52-URM/classes/API.rpyc.

Those builds normally also hash-check `renpy/script.py`, `renpy/loader.py` and
`renpy/main.py`, and call `sys.exit(1)` from `renpy/__init__.py` if any of them
changed - no window, no log, no traceback. That is why patching the loader
directly appears to do nothing.

There are two ways around it.

## Route A - repack URM (recommended)

Re-encode URM's `.rpyc` files into the format the target build writes, using
that build's own header and packer. The engine then loads them through its
normal path, and **no engine file is touched at all**.

```
"<game>/lib/py3-windows-x86_64/python.exe" repack.py "<game>" "0x52_URM.rpa"
```

That writes a converted `0x52_URM.rpa` into `<game>/game/`. It also compiles
`hyperlink_fix.rpy` into the archive - see below.

Run it with the target game's own interpreter: the key lives inside that
game's native module, and the output only works on the game it was built for.

Trade-off: the conversion has to be redone when you update URM, and separately
for every game.

## Route B - hook the engine

Copy `modcompat.py` into `<game>/renpy/` and call it from `renpy/bootstrap.py`,
which these builds do not hash-check. The engine then accepts stock `.rpyc`
files, so URM's `.rpa` can be dropped in unmodified and updated freely.

```
python install.py --check "<game>"
```

```
python install.py "<game>"
```

```
python install.py --uninstall "<game>"
```

`--check` reports the engine version, whether the build encrypts its script
cache, and which engine files are hash-checked - it works that out empirically,
by appending a byte to each file and seeing whether the engine still imports,
restoring it either way. Do not run it while the game is running.

If `renpy/bootstrap.py` turns out to be hash-checked on some build, `install.py`
refuses to change anything and says so. Use Route A there.

## hyperlink_fix.rpy

Independent of the loading problem, and worth having either way.

Ren'Py routes a link by looking its protocol up in `config.hyperlink_handlers`;
URM registers its editors as the `URMVarDialog` and `URMLabelDialog` protocols.
A game that sets `config.hyperlink_callback` - commonly to open its Patreon or
Discord link in a browser - makes `renpy/common/00compat` replace the whole
`style.default.hyperlink_functions` tuple, discarding the function that does
that lookup. Every link in the game then goes to `webbrowser.open()` whatever
its protocol, so clicking a variable in URM makes Windows offer to find an
application for a `urmvardialog:` link.

The fix restores protocol dispatch, keeps the game's callback as the fallback
for real URLs, and reinstalls itself once per interaction if anything replaces
it. Route A compiles it into the archive; Route B includes it in `modcompat.py`.

## Things that are still per-game

- **Which files are hash-checked.** Probed automatically, but if the hook point
  itself is checked you need Route A or another unchecked module.
- **Whether the archive reader passes plain files through.** This family
  decrypts an archive entry only if it carries the build's asset header, so
  URM's `.rpa` reads fine. A build that decrypts unconditionally would need its
  container format matched too. Symptom: still `Could not load from archive`
  after installing.
- **Release mode.** These builds ignore loose `.rpy`/`.rpyc` in `game/`, so
  add-ons have to stay packed as `.rpa`.
- **Do not leave UnRen output in `game/`.** Extraction bypasses the asset
  decryption, so the unpacked files are encrypted garbage that shadows the
  archives. Symptom: `Could not load image ...: Unsupported image format`.
