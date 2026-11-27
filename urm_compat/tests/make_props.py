"""
Builds "prop" games: a real engine with a tiny game of our own in it.

    python make_props.py <props folder> <game folder> [<game folder> ...]
    python make_props.py --refresh <prop folder> [<prop folder> ...]

(needs dist/URM_fix.bat: the script is compiled with the installer's own
compiler, by each game's own Python). --refresh rebuilds a prop from the
engine it already holds: no real game is needed. The gate fails a prop
whose prop_stamp.txt is not today's stamp().

The installer gate (check_installer.py) spends almost all its time in the
engine, and that time follows the size of the game's script: a real game of
200,000 statements takes minutes, one of 1,400 takes seconds. A prop is the
engine of a real game (its lib/ and renpy/ folders and its launcher) with a
game/ folder holding only test scripts, so the same gate runs on every
engine version in under a minute.

What a prop's game holds:
  - every script of tests/graph_corpus.py (the shapes the story-graph
    comparisons were written for), each with its labels prefixed so they can
    live in one game;
  - a short story with a check in it, and a French translation of it - one
    line translated by a single line, one by two statements. No real test
    game has a translation, and a translated line is a different statement
    from the one the story graph knows;
  - lines for past breaks: three in a row for the skip rule (also in
    French), a stray % and a %(name)s on purpose;
  - an old save (game/saves), made by the build players had before the
    pieces (SAVE_MAKER).

What a prop does NOT replace: a real game's own code, screens and size.
Real games are in no check (DECISIONS.md, 2026-11-21): a break only a
real game shows reaches the user first, then becomes a prop case.

The story script is delivered the way a released game delivers its own:
compiled, inside an archive (game/prop_script.rpa). One of the test games
("Game where URM doesn't work") ships an engine changed to ignore loose
script files in the game folder, so a loose script.rpy was silently not
loaded there and that prop tested nothing of its own; a loose file under
tl/ was not loaded either. So a prop has no loose script at all: the story
and its translation are both in the archive.

The props are then passed to check_installer.py as its game folders.
"""

from __future__ import print_function

import hashlib
import io
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import graph_corpus  # noqa
import check_installer as gate  # noqa  (interpreter, environment: the .bat's own choices)

BAT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "dist", "URM_fix.bat")

# One script per process: the installer's compiler starts the engine, and an
# engine cannot be started twice in one process. Mode "one" compiles a script
# to a .rpyc beside it; mode "pack" puts the compiled files in the archive.
COMPILE = u'''import io, os, sys
sys.path.insert(0, sys.argv[2])
import urmfix
urmfix.BASE = os.path.abspath(sys.argv[1])
if sys.argv[3] == "one":
    renpy = urmfix.load_engine()
    payload, digest = urmfix.compile_rpy(renpy, sys.argv[4], sys.argv[5])
    with io.open(sys.argv[4] + "c", "wb") as f:
        f.write(urmfix.write_native_rpyc(renpy, [(1, payload)], digest))
    print("prop compiled")
else:
    files = {}
    for pair in sys.argv[4:]:
        source, name = pair.split("=", 1)
        with io.open(source + "c", "rb") as f:
            files[name + "c"] = f.read()
    urmfix.write_archive(os.path.join(urmfix.BASE, "game", "prop_script.rpa"), files)
    print("prop packed")
'''

# (source file in prop_src, the name the engine knows it by)
SOURCES = (("script.rpy", "prop_script.rpy"),
           ("prop_story_french.rpy", "tl/french/prop_story.rpy"))

LABEL = re.compile(r"^(\s*label\s+)([A-Za-z_]\w*)")
JUMP = re.compile(r"^(\s*jump\s+)(?!expression\b)([A-Za-z_]\w*)")
CALL = re.compile(r"^(\s*call\s+)(?!expression\b|screen\b)([A-Za-z_]\w*)")
FROM = re.compile(r"(\bfrom\s+)([A-Za-z_]\w*)\s*$")
HOP = re.compile(r"""(renpy\.(?:jump|call)\(\s*(?:label\s*=\s*)?["'])([\w.]+)""")


def prefixed(source, prefix):
    """One corpus script with every label, and every plain jump or call to
    one, given a prefix - so 18 scripts can share a game. Computed targets
    and label names inside strings are left as they are."""

    out = []
    for line in source.split("\n"):
        line = LABEL.sub(lambda m: m.group(1) + prefix + m.group(2), line)
        line = JUMP.sub(lambda m: m.group(1) + prefix + m.group(2), line)
        if CALL.match(line):
            line = CALL.sub(lambda m: m.group(1) + prefix + m.group(2), line)
            line = FROM.sub(lambda m: m.group(1) + prefix + m.group(2), line)
        line = HOP.sub(lambda m: m.group(1) + prefix + m.group(2), line)
        out.append(line)
    return "\n".join(out)


STORY = u'''
label start:
    return

label prop_tl:
    "Hello there."
    if prop_flag:
        "Only with the flag."
    "Shared again."
    return

label prop_skip:
    "Read before."
    "Changed since."
    "Read after."
    return

label prop_percent:
    "You are 100% correct."
    "It works, %(urmprobe_pn)s."
    return
'''

# The labels a prop's story must hold: its own, and the first of every
# corpus script (the gate checks them all, so a prop built before a script
# was added fails).
OWN_LABELS = ("prop_tl", "prop_skip", "prop_percent")


def say_id(label, *codes):
    """The identifier the engine gives a translatable block: the label, and
    the first 8 hex digits of the md5 of each statement's canonical code
    followed by CR LF (renpy/translation/__init__.py, create_translate)."""

    md5 = hashlib.md5()
    for code in codes:
        md5.update((code + "\r\n").encode("utf-8"))
    return "%s_%s" % (label, md5.hexdigest()[:8])


TRANSLATION = u'''
translate french %s:
    "Bonjour."

translate french %s:
    $ prop_voice = 1
    "Seulement avec le drapeau."

translate french %s:
    "Lu avant."

translate french %s:
    "Change depuis."

translate french %s:
    "Lu apres."
''' % (say_id("prop_tl", '"Hello there."'), say_id("prop_tl", '"Only with the flag."'),
       say_id("prop_skip", '"Read before."'), say_id("prop_skip", '"Changed since."'),
       say_id("prop_skip", '"Read after."'))


def script_text():
    parts = [u"# Built by urm_compat/tests/make_props.py. Do not edit.\n", STORY]
    for number, (name, source) in enumerate(graph_corpus.SCRIPTS):
        parts.append(u"\n# ---- %s\n" % name)
        parts.append(prefixed(source, "p%d_" % number))
    return u"\n".join(parts)


def story_labels():
    out = list(OWN_LABELS)
    for number, (name, source) in enumerate(graph_corpus.SCRIPTS):
        first = [m.group(2) for m in map(LABEL.match, source.split("\n")) if m]
        out.append("p%d_%s" % (number, first[0]))
    return out


def stamp():
    """Changes whenever what a prop holds changes."""

    md5 = hashlib.md5()
    md5.update(script_text().encode("utf-8"))
    md5.update(TRANSLATION.encode("utf-8"))
    md5.update(COMPILE.encode("utf-8"))
    return md5.hexdigest()


def compile_script(dest):
    """game/prop_script.rpa from prop_src/script.rpy, with the prop's own
    Python and the installer's compiler. Returns an error text or None."""

    import subprocess

    tool = os.path.join(dest, "prop_src")
    text = io.open(BAT, "rb").read().decode("utf-8", "replace").replace("\r\n", "\n")
    with io.open(os.path.join(tool, "urmfix.py"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text.split("rem PAYLOAD_BEGIN\n", 1)[1])
    with io.open(os.path.join(tool, "compile_prop.py"), "w", encoding="utf-8", newline="\n") as f:
        f.write(COMPILE)

    py = gate.interpreter(dest)
    if py is None:
        return "no interpreter in the prop"
    env = gate.environment(dest, py)
    flags = gate.py_flags(dest, py)
    def run(*args):
        done = subprocess.run([py] + flags + ["-B", os.path.join(tool, "compile_prop.py"),
                                              dest, tool] + list(args),
                              cwd=tool, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=600)
        return done.stdout.decode("utf-8", "replace")

    for source, name in SOURCES:
        out = run("one", os.path.join(tool, source), name)
        if "prop compiled" not in out:
            return "%s: %s" % (source, out[-600:])
    out = run("pack", *["%s=%s" % (os.path.join(tool, source), name) for source, name in SOURCES])
    if "prop packed" not in out:
        return "archive: " + out[-600:]
    return None


def build(dest, game=None):
    """The prop `dest`, from `game`'s engine - or, with no game, from the
    engine the prop already has (--refresh: no real game needed)."""

    mark = os.path.join(dest, "prop_stamp.txt")
    want = stamp()

    engine_ready = os.path.isdir(os.path.join(dest, "lib")) and os.path.isdir(os.path.join(dest, "renpy"))
    if engine_ready and os.path.exists(mark) and io.open(mark).read().strip() == want:
        return dest, "kept"
    if os.path.exists(mark):
        os.remove(mark)

    if not engine_ready:
        if game is None:
            return dest, "FAILED: no engine in the prop to refresh from"
        if os.path.exists(dest):
            shutil.rmtree(dest)
        os.makedirs(dest)
        for entry in os.listdir(game):
            src = os.path.join(game, entry)
            if entry in ("lib", "renpy"):
                shutil.copytree(src, os.path.join(dest, entry))
            elif os.path.isfile(src) and entry.lower().endswith((".py", ".exe", ".sh")):
                shutil.copy2(src, dest)

    game_dir = os.path.join(dest, "game")
    source_dir = os.path.join(dest, "prop_src")
    for folder in (game_dir, source_dir):
        if os.path.exists(folder):
            shutil.rmtree(folder)
    os.makedirs(game_dir)
    os.makedirs(source_dir)
    with io.open(os.path.join(source_dir, "script.rpy"), "w", encoding="utf-8", newline="\n") as f:
        f.write(script_text())
    with io.open(os.path.join(source_dir, "prop_story_french.rpy"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(TRANSLATION)
    error = compile_script(dest)
    if error:
        return dest, "FAILED to compile: " + error
    with io.open(mark, "w") as f:
        f.write(u"%s\n" % want)
    return dest, "built"


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    if argv[1] == "--refresh":
        jobs = [(os.path.abspath(p), None) for p in argv[2:]]
    else:
        props = os.path.abspath(argv[1])
        if not os.path.exists(props):
            os.makedirs(props)
        jobs = [(os.path.join(props, "prop-" + os.path.basename(os.path.normpath(g))),
                 os.path.abspath(g)) for g in argv[2:]]
    # A lane's props/ is a junction to the main folder's (lane.py): building
    # through it would change the props every other lane tests with.
    root = os.path.realpath(os.path.dirname(os.path.dirname(HERE)))
    outside = [dest for dest, _g in jobs
               if not os.path.realpath(dest).lower().startswith(root.lower() + os.sep)]
    if outside:
        print("refused: these props are outside this folder (%s):\n  %s\n"
              "In a lane, run first: python urm_compat/tests/lane.py own-props <job>"
              % (root, "\n  ".join(os.path.realpath(d) for d in outside)))
        return 2
    from concurrent.futures import ThreadPoolExecutor
    failed = 0
    with ThreadPoolExecutor(max_workers=gate.jobs_for(len(jobs))) as pool:
        for dest, what in pool.map(lambda job: build(*job), jobs):
            print("%-6s %s" % (what, dest))
            failed += what.startswith("FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
