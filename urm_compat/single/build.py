"""
Builds the single-file URM_fix.bat out of header.bat and payload.py.

    python build.py [output path]

The payload contains the standalone code, its screens and the font files
and licences. Base64 keeps the sources outside the batch parser.
"""

import base64
import io
import os
import re
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
        screens = urm_source.join_screens()
    except urm_source.SourceError as error:
        raise SystemExit("Not built: %s" % error)

    version = re.search(rb'^    URMU_VERSION = "((?:0|[1-9][0-9]{0,3})(?:\.(?:0|[1-9][0-9]{0,3})){2})"\r?$',
                        addon, re.MULTILINE)
    if version is None:
        raise SystemExit("Set URMU_VERSION to a three-part version before building.")

    with io.open(os.path.join(HERE, "header.bat"), encoding="utf-8", newline="") as f:
        header = f.read().replace("@@URMPLUS_VERSION@@", version.group(1).decode("ascii"))

    with io.open(os.path.join(HERE, "payload.py"), encoding="utf-8", newline="") as f:
        payload = f.read()

    payload = payload.replace(
        "@@MODCOMPAT_B64@@", encoded(os.path.join(TOOLKIT, "modcompat.py")))
    payload = payload.replace(
        "@@ADDON_B64@@", base64.b64encode(addon).decode("ascii"))
    payload = payload.replace(
        "@@SCREENS_B64@@", base64.b64encode(screens).decode("ascii"))
    # The fonts our screens draw with, and their licence (urm_compat/fonts),
    # as urmplus/fonts/<name> in our archive.
    fonts = os.path.join(TOOLKIT, "fonts")
    files = {}
    for name in sorted(os.listdir(fonts)):
        with open(os.path.join(fonts, name), "rb") as f:
            files["urmplus/fonts/" + name] = base64.b64encode(f.read()).decode("ascii")
    payload = payload.replace(
        "@@OUR_FILES_B64@@", ";".join("%s=%s" % (k, files[k]) for k in sorted(files)))

    if "@@" in payload:
        raise SystemExit("A placeholder was left unfilled.")

    # cmd reads the file line by line and stops at exit /b, so the payload
    # below never reaches the parser. The header extracts the Python text.
    lines = header.replace("\r\n", "\n").split("\n")

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
