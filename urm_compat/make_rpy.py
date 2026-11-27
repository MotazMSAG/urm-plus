"""
Build a single source fixture for testing on engines that read loose scripts.

    python make_rpy.py [output path]

The fixture joins the same gameplay and screen source as the BAT. Tests
supply the fonts alongside it. Protected engines use the BAT's native
compiler because they may ignore loose source.
"""

from __future__ import print_function

import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tests"))

import urm_source  # noqa  (the add-on's code, joined from its pieces)


HEADER = '''\
# URM+ loose-source test fixture
# The release BAT bundles fonts and compiles for the game's own engine.
#
# https://github.com/MotazMSAG/urm-plus - edit those, not this.


'''


def build():
    return "\n\n".join((HEADER, urm_source.join().decode("utf-8"),
                       urm_source.join_screens().decode("utf-8")))


def main(argv):
    output = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(HERE, "dist", "urm_plus.rpy")
    if not os.path.isdir(os.path.dirname(output)):
        os.makedirs(os.path.dirname(output))
    text = build()
    with io.open(output, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("Wrote %s (%.0f KB)" % (output, os.path.getsize(output) / 1024.0))
    print("For scratch tests on engines that read loose scripts.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
