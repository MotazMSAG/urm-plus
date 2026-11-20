"""
Builds a drop-in 0x52_URM.rpa - URM with the interface tweaks and the game
compatibility fixes baked in, in stock Ren'Py format.

    python build_rpa.py "<a normal Ren'Py game>" [output path]

The game folder is borrowed for its Ren'Py, which compiles the add-on's code
(the pieces of game_fixes/, joined by tests/urm_source.py).
It must be an ordinary game, not one that encrypts its script cache, or the
compiled file comes out in that game's private format and works nowhere else.
Nothing in it is read or written.

The result is used exactly like URM's own archive: put it in the game's game/
folder. That covers every game whose engine reads add-on scripts as they come,
which is almost all of them. Games that encrypt their script cache reject any
archive not re-encoded for that specific game, and need URM_fix.bat instead -
there is no one file that can serve both, because the key is per game.
"""

from __future__ import print_function

import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tests"))

import repack      # noqa
import ui_tweaks   # noqa
import urm_source  # noqa  (the add-on's code, joined from its pieces)

FIX_NAME = "0x52-URM/zzz_urm_compat.rpyc"


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2

    game = os.path.abspath(argv[1])
    source = os.path.join(HERE, "0x52_URM.rpa")
    output = os.path.abspath(argv[2]) if len(argv) > 2 else os.path.join(
        HERE, "..", "dist", "0x52_URM.rpa")
    output = os.path.abspath(output)

    if not os.path.exists(source):
        print("Missing %s" % source)
        return 1

    try:
        joined = urm_source.join()
    except urm_source.SourceError as error:
        print(error)
        return 1

    contents = repack.read_archive(source)
    print("Read %s  (%d entries)" % (source, len(contents)))

    applied, skipped = ui_tweaks.apply(contents)
    for name, note in applied:
        print("  tweak: %s%s" % (name, "  (%s)" % note if note else ""))
    for name, why in skipped:
        print("  ! skipped %s - %s" % (name, why))

    if skipped:
        print()
        print("Refusing to build with a tweak missing - run tests/run_tests.py")
        print("to see which pattern URM moved.")
        return 1

    # load_engine chdirs, so everything above has to be resolved by now.
    renpy = repack.load_engine(game)

    header = getattr(renpy, "_RPYC_HEADER", repack.STOCK_HEADER)
    if header != repack.STOCK_HEADER or getattr(renpy, "compress_bytecode_stream", None):
        print()
        print("%s encrypts its script cache. Build from an ordinary game." % game)
        return 1

    print("Compiling the add-on with Ren'Py %s" % renpy.version_only)

    # The compiler reads a file: the joined pieces, in a folder of their own.
    # The same folder every time - the compiled file records the path.
    folder = os.path.join(tempfile.gettempdir(), "urm_build_rpa")
    if not os.path.isdir(folder):
        os.makedirs(folder)
    try:
        fixes = os.path.join(folder, "zzz_urm_compat.rpy")
        with open(fixes, "wb") as f:
            f.write(joined)
        payload, digest = repack.compile_rpy(renpy, fixes, FIX_NAME[:-1])
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    contents[FIX_NAME] = repack.write_native_rpyc(renpy, [(1, payload)], digest)

    if not os.path.isdir(os.path.dirname(output)):
        os.makedirs(os.path.dirname(output))

    repack.write_archive(output, contents)

    print()
    print("Wrote %s  (%.0f KB)" % (output, os.path.getsize(output) / 1024.0))
    print("Drop it in a game's game/ folder, like URM's own archive.")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
