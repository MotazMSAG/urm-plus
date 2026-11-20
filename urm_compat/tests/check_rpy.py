"""
Parses the add-on's source - the pieces of urm_compat/game_fixes/, joined by
tests/urm_source.py - with the real Ren'Py parser, the way the build does.

    <a game's bundled python> -I check_rpy.py <that game folder>

The installer compiles this file into URM's archive, so a file that does not
parse means no helpers in the build - and the screens then fall back to URM's
own line, silently, with everything looking installed.

It also refuses CR bytes. Ren'Py's lexer does not join a backslash followed by
CRLF, so a file saved with Windows line endings can orphan the continuation
line and fail with an indentation error pages away from the real cause. The
file is LF, and this keeps it that way.
"""

from __future__ import print_function

import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import urm_source  # noqa  (the add-on's code, joined from its pieces)

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(2)

failures = []

# The parser needs a file: the joined source, under the name it has in a game.
# Read before the chdir below, so a relative URM_CHECK_SOURCE still resolves.
try:
    raw = urm_source.raw()
except urm_source.SourceError as error:
    print("FAIL  %s" % error)
    sys.exit(1)
FOLDER = tempfile.mkdtemp(prefix="urm_check_rpy_")
TARGET = os.path.join(FOLDER, "zzz_urm_compat.rpy")
with open(TARGET, "wb") as f:
    f.write(raw)
if b"\r" in raw:
    failures.append("game_fixes.rpy contains %d CR bytes - it must be LF"
                    % raw.count(b"\r"))
    print("FAIL  line endings: %d CR bytes" % raw.count(b"\r"))
else:
    print("pass  line endings are LF")

base = os.path.abspath(sys.argv[1])
os.chdir(base)
sys.path.insert(0, base)

import renpy  # noqa

renpy.import_all()
renpy.config.basedir = base
renpy.config.gamedir = os.path.join(base, "game")

# game_fixes.rpy now defines screens (the index progress line and the editor
# panel). Screen-language statements - add, python, text and the rest - are
# only registered by this call; without it every one of them is reported as
# "not a valid child of the screen statement". validate_x52.py does the same.
renpy.sl2.slparser.init()


class FakeScript(object):
    record_pycode = False
    all_pycode = []
    serial = 0

    def __getattr__(self, name):
        return None


renpy.game.script = FakeScript()
renpy.game.log = type("L", (), {"mutated": {}})()
if not renpy.game.contexts:
    renpy.game.contexts = [type("C", (), {"init_phase": True})()]

try:
    statements = renpy.parser.parse(TARGET)
finally:
    shutil.rmtree(FOLDER, ignore_errors=True)

if statements is None:
    failures.append("game_fixes.rpy does not parse")
    print("FAIL  the parser rejected it:")
    for error in getattr(renpy.parser, "parse_errors", [])[:10]:
        print("        %s" % error)
    print("        (a line of the joined file: python tests/urm_source.py"
          " --line N names the piece)")
else:
    print("pass  parses with Ren'Py %s  (%d statements)"
          % (renpy.version_only, len(statements)))

    # game_fixes.rpy is compiled once, by Ren'Py 8, and its pickle is loaded
    # by every engine the games run. repack.py makes PyCode portable; nothing
    # else in it is. A PyExpr - which every screen expression, `if`, `menu`
    # condition and `default` carries - takes four constructor arguments on
    # 7.4+ and three on 7.3.5 and 7.2.1, so one stray screen here costs every
    # Ren'Py 7.3 game the whole helper. Screens go in the .x52 text instead,
    # which each game compiles with its own engine.
    stray = []
    for node in statements:
        # The parser closes every file with an implicit bare Return. It holds
        # no expression, so nothing version-specific is pickled, and every
        # build of the helper that has loaded on 7.3 carried one.
        if isinstance(node, renpy.ast.Return) and \
                getattr(node, "expression", None) is None:
            continue
        if not isinstance(node, renpy.ast.Init):
            stray.append("%s at line %s" % (type(node).__name__,
                                            getattr(node, "linenumber", "?")))
            continue
        for child in node.block or ():
            if not isinstance(child, renpy.ast.Python):
                stray.append("%s inside init at line %s"
                             % (type(child).__name__,
                                getattr(child, "linenumber", "?")))
    if stray:
        failures.append("game_fixes.rpy holds statements other than init python")
        print("FAIL  only init python may be compiled into the helper, found:")
        for line in stray[:10]:
            print("        %s" % line)
    else:
        print("pass  nothing but init python (portable across engines)")

print()
print("all passed" if not failures else "%d FAILED" % len(failures))
sys.exit(1 if failures else 0)
