"""
Builds the single-file URM_fix.bat out of header.bat and payload.py.

    python build.py [output path]

The embedded sources - modcompat.py, ui_tweaks.py and the add-on - go in
base64 encoded, so no quoting or escaping in them can break the payload.

The add-on is the pieces of urm_compat/game_fixes/, joined in the order of
their names into the ONE file the installer compiles into URM's archive
(tests/urm_source.py holds the join and its rules). The build stops if a
game_fixes.rpy is back next to the pieces, or if anything in that folder
is not a piece.
"""

import base64
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)

sys.path.insert(0, os.path.join(TOOLKIT, "tests"))

import urm_source  # noqa  (the add-on's code, joined from its pieces)


def encoded(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def main(argv):
    output = argv[1] if len(argv) > 1 else os.path.join(
        TOOLKIT, "..", "dist", "URM_fix.bat")
    output = os.path.abspath(output)

    try:
        addon = urm_source.join()
    except urm_source.SourceError as error:
        raise SystemExit("Not built: %s" % error)

    with io.open(os.path.join(HERE, "header.bat"), encoding="utf-8", newline="") as f:
        header = f.read()

    with io.open(os.path.join(HERE, "payload.py"), encoding="utf-8", newline="") as f:
        payload = f.read()

    payload = payload.replace(
        "@@MODCOMPAT_B64@@", encoded(os.path.join(TOOLKIT, "modcompat.py")))
    payload = payload.replace(
        "@@HYPERLINK_FIX_B64@@", base64.b64encode(addon).decode("ascii"))
    payload = payload.replace(
        "@@UI_TWEAKS_B64@@", encoded(os.path.join(TOOLKIT, "ui_tweaks.py")))

    if "@@" in payload:
        raise SystemExit("A placeholder was left unfilled.")

    # cmd reads the file line by line and stops at exit /b, so the payload
    # below never reaches the parser. more(1) rewrites line endings, so keep
    # everything CRLF and tab-free.
    if "\t" in payload:
        raise SystemExit("Tabs in payload.py would be mangled by more.")

    # Layout: the batch script, then URM's archive as base64, then the Python.
    # The Python has to come last so `more +N` can pull it out with a single
    # unbounded skip; the tool reads the base64 back out of the .bat itself.
    urm = os.path.join(TOOLKIT, "0x52_URM.rpa")

    if not os.path.exists(urm):
        raise SystemExit(
            "Put a copy of 0x52_URM.rpa in %s - it gets embedded in the .bat."
            % TOOLKIT)

    with open(urm, "rb") as f:
        blob = base64.b64encode(f.read()).decode("ascii")

    lines = header.replace("\r\n", "\n").split("\n")

    lines.append("rem URM_BEGIN")
    lines += [blob[i:i + 76] for i in range(0, len(blob), 76)]

    lines.append("rem PAYLOAD_BEGIN")
    lines += payload.replace("\r\n", "\n").split("\n")

    if not os.path.isdir(os.path.dirname(output)):
        os.makedirs(os.path.dirname(output))

    with open(output, "wb") as f:
        f.write("\r\n".join(lines).encode("utf-8"))

    size = os.path.getsize(output)
    print("Wrote %s  (%.0f KB; the add-on: %d pieces, %d lines)"
          % (output, size / 1024.0, len(urm_source.layout()),
             addon.count(b"\n")))

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
