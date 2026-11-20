"""
The source of the URM+ add-on, for every test and tool.

The add-on's code is kept as pieces in urm_compat/game_fixes/, one job per
file. What reaches a game is ONE file: the pieces joined in the order of
their names, compiled by the installer into 0x52-URM/zzz_urm_compat.rpyc.
Nothing else reads the pieces: the build, the gate and every check ask here.

    python tests/urm_source.py              the pieces, their lines, the hash
    python tests/urm_source.py --line 4711  which piece a line of the joined
                                            file is in (a traceback in a game
                                            names _urmfix_hyperlink.rpy, the
                                            name the installer compiles the
                                            joined file under, and its line)
    python tests/urm_source.py --join OUT   write the joined file to OUT
    python tests/urm_source.py --pin        record the joined file's hash as
                                            the one the unit suite expects

The join is plain: the bytes of each piece, one after the other, nothing
added and nothing taken away. So:

  - a piece that starts at column 0 opens its own "init 999 python:" block
    (a comment banner, then the header);
  - a piece that starts indented CONTINUES the block of the piece before it:
    its code runs in that same block, right after that piece's last line.

One block is not at priority 999: "init 998 python:", at the top of the first
piece, above its "init 999 python:". URM's own compiled start-up code runs at
999 and before the add-on there, so what has to be in place before URM starts
is done a priority earlier (00_urm_fixes: a game whose config.font_transforms
is not a table). For the cut into blocks it is part of what stands above the
first block; early_block() gives its code.

URM_CHECK_SOURCE names another source for the checks to run on - one old
single file (a game_fixes.rpy from before the split) or a folder of pieces -
for proving that a new case fails on the code before a fix. The build and
the gate never honour it: they take the pieces.

Runs on Python 2.7 and 3: some checks run under a game's own interpreter.
"""

from __future__ import print_function

import hashlib
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)

# The pieces, and the single file they replaced. A game_fixes.rpy back next
# to them would be a second source nothing reads: refused, loudly.
PIECES = os.path.join(TOOLKIT, "game_fixes")
OLD_SINGLE = os.path.join(TOOLKIT, "game_fixes.rpy")

# What the unit suite expects the joined file to be (step [0s]).
PIN = os.path.join(HERE, "baseline", "joined_source.sha256")

HEADER = u"init 999 python:"
# The one block that runs before URM's own init 999 statements.
EARLY = u"init 998 python:"
NAME = re.compile(r"^[0-9][0-9]_[a-z0-9_]+\.rpy$")

# Where the installer puts the compiled add-on inside URM's archive.
ENTRY = "0x52-URM/zzz_urm_compat.rpyc"


class SourceError(Exception):
    pass


def pieces(folder=None):
    """[(name, bytes)] in load order - the order of the names. Raises
    SourceError for anything that would make the join ambiguous."""

    folder = folder or PIECES

    if os.path.abspath(folder) == os.path.abspath(PIECES) and os.path.exists(OLD_SINGLE):
        raise SourceError(
            "%s exists next to the pieces in %s. The pieces are the source; "
            "a single file beside them is read by nothing. Move its changes "
            "into the pieces and delete it." % (OLD_SINGLE, PIECES))

    if not os.path.isdir(folder):
        raise SourceError("%s is not a folder of pieces." % folder)

    names = sorted(os.listdir(folder))
    out = []
    numbers = {}

    for name in names:
        path = os.path.join(folder, name)

        if not NAME.match(name) or not os.path.isfile(path):
            raise SourceError(
                "%s is not a piece: every file in %s is joined into the "
                "add-on and must be named NN_job.rpy." % (name, folder))

        if name[:2] in numbers:
            raise SourceError("%s and %s share a number: their order would "
                              "depend on the rest of the name."
                              % (numbers[name[:2]], name))
        numbers[name[:2]] = name

        with open(path, "rb") as f:
            data = f.read()

        if b"\r" in data:
            raise SourceError("%s has CR line endings; the pieces are LF." % name)
        if not data.endswith(b"\n"):
            raise SourceError("%s does not end with a newline: the next "
                              "piece would be glued to its last line." % name)
        if data[:1] in (b" ", b"\n") and not data.startswith(b"    ") or data.startswith(b"     "):
            raise SourceError("%s must start at column 0 (its own block) or "
                              "with a line indented four spaces (it "
                              "continues the block before it)." % name)
        if not out and data.startswith(b" "):
            raise SourceError("%s is the first piece and continues nothing: "
                              "it must start at column 0." % name)
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as e:
            raise SourceError("%s is not UTF-8: %s" % (name, e))

        out.append((name, data))

    if not out:
        raise SourceError("%s holds no pieces." % folder)

    return out


def join(folder=None):
    """The bytes of the one file a game gets: the pieces, in order."""

    return b"".join(data for _name, data in pieces(folder))


def sha256(folder=None):
    return hashlib.sha256(join(folder)).hexdigest()


def md5(folder=None):
    """The digest the installer stores at the end of the compiled add-on."""

    return hashlib.md5(join(folder)).hexdigest()


def layout(folder=None):
    """[(name, first line in the joined file, lines, continues)]."""

    out = []
    line = 1
    for name, data in pieces(folder):
        count = data.count(b"\n")
        out.append((name, line, count, data.startswith(b" ")))
        line += count
    return out


def locate(line, folder=None):
    """(piece, line in that piece) for a line of the joined file, or None."""

    for name, first, count, _continues in layout(folder):
        if first <= line < first + count:
            return name, line - first + 1
    return None


def header_lines(folder=None):
    """The line of every "init 999 python:" in the joined file, in order -
    the order the engine must run the blocks in."""

    text = join(folder).decode("utf-8")
    return [n + 1 for n, line in enumerate(text.split(u"\n")) if line == HEADER]


def block_order(folder=None):
    """[(priority, line)] of every block of the joined file, in the order
    the engine must run them: the early block, then the others as they
    stand."""

    text = join(folder).decode("utf-8")
    lines = text.split(u"\n")
    early = [(998, n + 1) for n, line in enumerate(lines) if line == EARLY]
    return early + [(999, n) for n in header_lines(folder)]


def newest_mtime(folder=None):
    folder = folder or PIECES
    return max(os.path.getmtime(os.path.join(folder, name))
               for name, _data in pieces(folder))


def write_joined(path, folder=None):
    """The joined file on disk, for what needs a path (the Ren'Py parser)."""

    with open(path, "wb") as f:
        f.write(join(folder))
    return path


# ------------------------------------------------------- what the checks read

def working():
    """What the checks run on: URM_CHECK_SOURCE when set, else the pieces."""

    return os.environ.get("URM_CHECK_SOURCE") or PIECES


def raw(path=None):
    """The source's bytes as they are on disk. `path` is a folder of pieces
    or one single file; without it, working()."""

    path = path or working()

    if os.path.isdir(path):
        return join(path)

    with open(path, "rb") as f:
        return f.read()


def read(path=None):
    """The joined source as text (a single file read as every check always
    read it: UTF-8, any line ending as a newline)."""

    path = path or working()

    if os.path.isdir(path):
        return join(path).decode("utf-8")

    with io.open(path, encoding="utf-8") as f:
        return f.read()


def chunks(path=None, text=None):
    """The source cut at every "init 999 python:". The first chunk is the
    comment above the first block; each of the others is one block's code
    followed by the comment banner of the next. `text` is a source already
    in hand (a check that alters a line to prove it can fail)."""

    return (text if text is not None else read(path)).split(HEADER)


def body(chunk):
    """One block's code at column 0.

    Four spaces off whatever has them, rather than textwrap.dedent: a block
    is followed by the next block's comment banner at column 0, so the
    common prefix is "" and dedent strips nothing. A comment left at column
    0 is legal anywhere.
    """

    newline = chr(10)
    return newline.join(line[4:] if line.startswith("    ") else line
                        for line in chunk.split(newline))


def block(needle, path=None, text=None):
    """The code, at column 0, of the one block that holds `needle`. A needle
    in no block or in two would run the wrong code: that ends the check."""

    found = [c for c in chunks(path, text) if needle in c]
    if len(found) != 1:
        raise SystemExit("FAIL  %d init blocks hold %r in %s, expected 1"
                         % (len(found), needle,
                            os.path.basename(path or working())))
    return body(found[0])


def early_block(path=None, text=None):
    """The code, at column 0, of the "init 998 python:" block: from its
    header to the first "init 999 python:" (the comment banner of that
    block comes along, as comments)."""

    above = chunks(path, text)[0]
    if above.count(EARLY) != 1:
        raise SystemExit("FAIL  %d %r blocks above the first block in %s, expected 1"
                         % (above.count(EARLY), EARLY,
                            os.path.basename(path or working())))
    return body(above.split(EARLY, 1)[1])


def top_defs(code, names):
    """The listed top-level defs of a block's code (as block() gives it),
    without the rest of the block."""

    lines = code.split("\n")
    out = []
    for name in names:
        start = None
        for i, line in enumerate(lines):
            if line.startswith("def %s(" % name):
                start = i
                break
        if start is None:
            raise SystemExit("FAIL  no def %s" % name)
        end = start + 1
        while end < len(lines) and (not lines[end].strip()
                                    or lines[end].startswith((" ", "#"))):
            end += 1
        out.append("\n".join(lines[start:end]))
    return "\n\n".join(out)


# ------------------------------------------------------------------- the pin

def pinned():
    """The hash the unit suite expects, or None when none is recorded."""

    if not os.path.exists(PIN):
        return None
    with io.open(PIN, encoding="ascii") as f:
        return f.read().split()[0]


def pin():
    with io.open(PIN, "w", encoding="ascii", newline="\n") as f:
        f.write(u"%s  joined source (python tests/urm_source.py --pin)\n" % sha256())


def main(argv):
    try:
        if len(argv) > 2 and argv[1] == "--line":
            found = locate(int(argv[2]))
            if found is None:
                print("the joined file has no line %s" % argv[2])
                return 1
            print("%s line %d" % found)
            return 0
        if len(argv) > 2 and argv[1] == "--join":
            write_joined(os.path.abspath(argv[2]))
            print("Wrote %s" % os.path.abspath(argv[2]))
            return 0
        if len(argv) > 1 and argv[1] == "--pin":
            pin()
            print("Pinned %s" % sha256())
            return 0
        if len(argv) > 1:
            print(__doc__)
            return 2
        total = 0
        for name, first, count, continues in layout():
            total += count
            print("%-28s %5d lines  from line %5d%s"
                  % (name, count, first, "  (continues the block before)" if continues else ""))
        print("%d pieces, %d lines, %d blocks" % (len(layout()), total, len(header_lines())))
        print("sha256 %s%s" % (sha256(), "" if sha256() == pinned() else "   (NOT the pinned one)"))
    except SourceError as e:
        print("FAIL  %s" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
