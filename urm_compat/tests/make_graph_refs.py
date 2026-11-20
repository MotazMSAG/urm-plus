"""
Freezes today's script readers as reference functions.

    python make_graph_refs.py            # writes tests/baseline/graph_refs.rpy
    python make_graph_refs.py --check    # exits 1 if the committed file differs
    python make_graph_refs.py --m8       # writes tests/baseline/graph_refs_m8.rpy
    python make_graph_refs.py --m8 --check

The story-graph rework (FINDINGS.md, 2026-11-19; research/story_graph) moves
every feature that reads the game's script onto one shared reader. Each move
has to prove it changed nothing. The proof is a frozen copy of the readers as
they were before the rework, taken from tests/baseline/game_fixes_pre_graph.rpy
(a byte copy of game_fixes.rpy that is never replaced by the working file)
and kept under their own names so they can sit next to the live code, in the
unit tests and inside a real engine.

Pieces are cut BY NAME, not by line number: each anchor is a top-level
statement of an init block (a constant, a class, a def), taken from its
first line to the line before the next top-level statement. Every anchor
must be found exactly once.

The only changes made to the text, all mechanical:
  D1  identifier prefixes: _urmm_ -> _urmrefm_, _urms_ -> _urmrefs_,
      _urm_ -> _urmref_, _URMM -> _URMREFM, _URM_ -> _URMREF_
  D2  the gate chain takes its first If as an argument and returns
      (steps, meta) instead of reading URM's detected statement and writing
      the meta list onto URM's store
  D3  non-ASCII characters are written as \\u escapes, so the file is ASCII

To change a frozen reader on purpose (a bug fix that must also be in the
baseline): make the same edit in tests/baseline/game_fixes_pre_graph.rpy,
re-run this script, and pin the new sha256 in check_graph.py.

--m8: the references of rework moves 8 and 9, frozen at the start of move 8
into their own file. They are the script index as a whole (the block holding
its class: how statements are linked to the block they sit in, which
conditions and python lines are recorded) and the readers that climb its
links: the label a statement is in for the map, the panel and the gallery,
the block it is in for the skip rule, and the panel's reading of a python
line. Every one of them was byte for byte the same in the working file as in
the baseline when move 8 began (move 8 checked it), so they are cut from the
same pinned baseline. Names: _urmi_ -> _urmref8i_, _URMI -> _URMREF8I,
_urmm_ -> _urmref8m_, _urmp_ -> _urmref8p_, _urmg_ -> _urmref8g_,
_urms_ -> _urmref8s_, _urm_ -> _urmref8_; the panel's cache holder
_urmpState -> _urmref8pState, so the frozen copy never shares a cache with
the live code.
"""

from __future__ import print_function

import hashlib
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(HERE, "baseline", "game_fixes_pre_graph.rpy")
OUTPUT = os.path.join(HERE, "baseline", "graph_refs.rpy")
OUTPUT_M8 = os.path.join(HERE, "baseline", "graph_refs_m8.rpy")

# Moves 8 and 9: the whole block holding this needle, then these readers.
M8_BLOCK = "class _URMIndex"
M8_ANCHORS = [
    "_urmm_label_of",
    "_urmp_state", "_urmp_bucket", "_urmp_effects", "_urmp_scene",
    "_urmg_in_init",
    "_urms_block",
]
M8_RENAMES = [
    (re.compile(r"(?<![A-Za-z0-9_])_urmi_"), "_urmref8i_"),
    (re.compile(r"(?<![A-Za-z0-9_])_URMI"), "_URMREF8I"),
    (re.compile(r"(?<![A-Za-z0-9_])_urmm_"), "_urmref8m_"),
    (re.compile(r"(?<![A-Za-z0-9_])_urmp_"), "_urmref8p_"),
    (re.compile(r"(?<![A-Za-z0-9_])_urmg_"), "_urmref8g_"),
    (re.compile(r"(?<![A-Za-z0-9_])_urms_"), "_urmref8s_"),
    (re.compile(r"(?<![A-Za-z0-9_])_urm_"), "_urmref8_"),
    (re.compile(r"_urmpState"), "_urmref8pState"),
]

# In the order they are written. Constants and state first, then the
# readers in the order they appear in the file.
ANCHORS = [
    "_URM_MAX_GATES", "_URM_MAX_ROWS", "_URM_MAX_TOTAL_ROWS",
    "_URM_MAX_GUARD_CHARS", "_URM_MAX_DEPTH",
    "_URMM_REACH", "_URMM_STEPS", "_URMM_PATHS", "_URMM_DEPTH",
    "_URMM_LABEL_CHARS", "import re as _urmm_re", "_URMM_PYJUMP", "_URMM_TAG",
    "_URMM_LATER", "_URMM_STRETCH",
    "_URMMState", "_urmm_st",
    "_urm_truth", "_urm_is_condition", "_urm_clip", "_urm_statement",
    "_URM_NOISE_CALLS", "_urm_noise", "_urm_python_lines", "_urm_flatten",
    "_urm_lift", "_urm_tail", "_urm_chain",
    "_urmm_lookup", "_urmm_pyjump", "_urmm_after", "_urmm_successors",
    "_urmm_successors_of", "_urmm_reach", "_URMM_CANDIDATES", "_urmm_region",
    "_urmm_meets", "_urmm_meeting",
    "_urmm_pure", "_urmm_choice_label", "_URMM_MARK_CHECK", "_URMM_MARK_MENU",
    "_urmm_real", "_urmm_target_tag", "_urmm_arm_label", "_urmm_text_menu",
    "_URMMWalk", "_urmm_walk",
    "_urmm_plan", "_urmm_arms", "_urmm_distances", "_urmm_next_menu",
    "_urmm_stretch",
    "_urms_lookup", "_urms_next", "_urms_passes", "_urms_quiet_if",
    "_urms_says_in",
]

# A top-level statement of an init block starts at four spaces with
# something that is not a comment and not a closing bracket.
START = re.compile(r"^    [^\s#)\]}]")

RENAMES = [
    (re.compile(r"(?<![A-Za-z0-9_])_urmm_"), "_urmrefm_"),
    (re.compile(r"(?<![A-Za-z0-9_])_urms_"), "_urmrefs_"),
    (re.compile(r"(?<![A-Za-z0-9_])_urm_"), "_urmref_"),
    (re.compile(r"(?<![A-Za-z0-9_])_URMM"), "_URMREFM"),
    (re.compile(r"(?<![A-Za-z0-9_])_URM_"), "_URMREF_"),
]

# D2, as exact text. Each must match once.
CHAIN_EDITS = [
    ("    def _urm_chain():\n", "    def _urm_chain(first):\n"),
    ("        meta = python_list()\n"
     "        x52URM.Var._urmChainMeta = meta\n"
     "\n"
     "        detected = x52URM.PathDetection.nextIfStatement\n"
     "\n"
     "        if not detected:\n"
     "            return steps\n"
     "\n"
     "        node = detected[0]\n",
     "        meta = python_list()\n"
     "        node = first\n"),
]


def statements(lines):
    """[(first line index, last line index)] of every top-level statement."""

    starts = [i for i, line in enumerate(lines) if START.match(line)]
    spans = []

    for n, first in enumerate(starts):
        last = (starts[n + 1] if n + 1 < len(starts) else len(lines)) - 1

        # Blank lines and comments between two statements belong to the next.
        while last > first:
            stripped = lines[last].strip()
            if stripped and not (stripped.startswith("#")
                                 and len(lines[last]) - len(lines[last].lstrip()) <= 4):
                break
            last -= 1

        spans.append((first, last))

    return spans


def head_of(line):
    """The name a top-level statement defines, or the statement itself."""

    text = line[4:].rstrip()
    m = re.match(r"(?:def|class) ([A-Za-z_][A-Za-z0-9_]*)", text)
    if m:
        return m.group(1)
    m = re.match(r"([A-Za-z_][A-Za-z0-9_]*) =", text)
    if m:
        return m.group(1)
    return text


def generate():
    with io.open(BASELINE, encoding="utf-8", newline="") as f:
        source = f.read()

    if "\r" in source:
        raise SystemExit("baseline has CR line endings")

    lines = source.split("\n")
    found = {}

    for first, last in statements(lines):
        found.setdefault(head_of(lines[first]), []).append((first, last))

    pieces = []

    for anchor in ANCHORS:
        spans = found.get(anchor) or []
        if len(spans) != 1:
            raise SystemExit("anchor %r found %d times, expected 1"
                             % (anchor, len(spans)))
        first, last = spans[0]
        pieces.append("\n".join(lines[first:last + 1]) + "\n")

    text = "\n".join(pieces)

    for old, new in CHAIN_EDITS:
        if text.count(old) != 1:
            raise SystemExit("chain edit matched %d times: %r"
                             % (text.count(old), old[:40]))
        text = text.replace(old, new)

    chain_at = text.index("    def _urm_chain(first):\n")
    chain_end = text.index("\n    def ", chain_at + 1)
    chain = text[chain_at:chain_end]
    if chain.count("return steps\n") < 2:
        raise SystemExit("the gate chain no longer returns steps as expected")
    text = (text[:chain_at]
            + chain.replace("return steps\n", "return steps, meta\n")
            + text[chain_end:])

    for pattern, replacement in RENAMES:
        text = pattern.sub(replacement, text)

    text = "".join(ch if ord(ch) < 128 else "\\u%04x" % ord(ch) for ch in text)

    header = (
        "# GENERATED by tests/make_graph_refs.py from\n"
        "# tests/baseline/game_fixes_pre_graph.rpy - do not edit by hand.\n"
        "# Today's script readers, frozen under _urmref* names, as the\n"
        "# yardstick for the story-graph rework.\n"
        "\n"
        "init 1998 python:\n"
        "\n")

    return header + text


def generate_m8():
    with io.open(BASELINE, encoding="utf-8", newline="") as f:
        source = f.read()

    if "\r" in source:
        raise SystemExit("baseline has CR line endings")

    # The whole index block: from its header to the line before the next
    # thing at column 0 (the next block's comment header).
    blocks = [c for c in source.split("init 999 python:") if M8_BLOCK in c]
    if len(blocks) != 1:
        raise SystemExit("%d blocks hold %r, expected 1" % (len(blocks), M8_BLOCK))
    body = []
    for line in blocks[0].split("\n"):
        if line and not line.startswith(" "):
            break
        body.append(line)
    while body and not body[-1].strip():
        body.pop()
    while body and not body[0].strip():
        body.pop(0)
    pieces = ["\n".join(body) + "\n"]

    lines = source.split("\n")
    found = {}
    for first, last in statements(lines):
        found.setdefault(head_of(lines[first]), []).append((first, last))

    for anchor in M8_ANCHORS:
        spans = found.get(anchor) or []
        if len(spans) != 1:
            raise SystemExit("anchor %r found %d times, expected 1"
                             % (anchor, len(spans)))
        first, last = spans[0]
        pieces.append("\n".join(lines[first:last + 1]) + "\n")

    text = "\n".join(pieces)

    for pattern, replacement in M8_RENAMES:
        text = pattern.sub(replacement, text)

    text = "".join(ch if ord(ch) < 128 else "\\u%04x" % ord(ch) for ch in text)

    header = (
        "# GENERATED by tests/make_graph_refs.py --m8 from\n"
        "# tests/baseline/game_fixes_pre_graph.rpy - do not edit by hand.\n"
        "# The script index and the readers that climb its links, frozen\n"
        "# under _urmref8* names as the yardstick for rework moves 8 and 9.\n"
        "\n"
        "init 1998 python:\n"
        "\n")

    return header + text


def digest(text):
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def main(argv):
    m8 = "--m8" in argv
    text = generate_m8() if m8 else generate()
    output = OUTPUT_M8 if m8 else OUTPUT
    name = os.path.basename(output)

    if "--check" in argv:
        with io.open(output, encoding="ascii", newline="") as f:
            committed = f.read()
        if committed != text:
            print("FAIL  %s differs from what the baseline generates" % name)
            return 1
        print("pass  %s regenerates byte for byte  sha256 %s"
              % (name, digest(text)))
        return 0

    with io.open(output, "w", encoding="ascii", newline="") as f:
        f.write(text)
    print("wrote %s  (%d lines)  sha256 %s"
          % (output, text.count("\n"), digest(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
