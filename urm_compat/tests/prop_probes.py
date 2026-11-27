"""Shared native-engine probes for the standalone screens.

    python prop_probes.py <props folder> [--pictures <folder>] [probe.py ...]
"""

from __future__ import print_function

from concurrent.futures import ThreadPoolExecutor
import glob
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, TOOLKIT)
sys.path.insert(0, HERE)

import check_kit  # noqa  (engine(), fonts())
import make_rpy  # noqa  (the add-on as one file)

PROBE_MARKER = re.compile(r"^# prop_probe: standalone\s*$", re.M)

DRAW_HELPER = u'''
init 1999 python:
    def _pp_draw():
        __import__("renpy.display.swdraw")
        import pygame_sdl2 as pygame
        config.developer = False

        class _ProbeDraw(object):
            draw_per_virt = 1.0
            draw_to_virt = renpy.display.render.IDENTITY
            virt_to_draw = renpy.display.render.IDENTITY
            info = {"renderer": "sw", "models": False}

            def mutated_surface(self, surf):
                pass

            def load_texture(self, surf, *args, **kwargs):
                return surf.copy()

            def solid_texture(self, w, h, color):
                w, h = max(1, int(w)), max(1, int(h))
                surf = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
                surf.fill(tuple(color))
                return surf.subsurface((2, 2, w, h))

            def ready_one_texture(self):
                return False

            def render_to_texture(self, what, alpha):
                w, h = what.get_size()
                surf = pygame.Surface((max(1, int(w)), max(1, int(h))), pygame.SRCALPHA)
                surf.fill((0, 0, 0, 0))
                renpy.display.swdraw.draw(surf, None, what, 0, 0, True)
                return surf

            def __getattr__(self, name):
                raise AttributeError("probe draw: " + name)
        renpy.display.draw = _ProbeDraw()
'''

HARNESS_TAIL = u'''
init 1999 python:
    def _pp_lint():
        import os, traceback
        out_lines = []
        base_dir = config.basedir
        for name, fn, pic_env, tag_env in _PP_PROBES:
            out_lines.append("PROBE_BEGIN %s" % name)
            probe_lines = []

            def check(msg, ok, detail=""):
                probe_lines.append("%s  %s%s" % ("pass" if ok else "FAIL", msg, ("  " + detail) if detail else ""))

            folder = os.environ.get(pic_env) if pic_env else None
            tag = os.environ.get(tag_env, "engine") if tag_env else "engine"

            def pic(pic_name):
                return os.path.join(folder, "%s_%s.png" % (pic_name, tag)) if folder else None

            try:
                config.screen_width, config.screen_height = 1920, 1080
                renpy.style.rebuild()
                renpy.display.screen.prepare_screens()
                _pp_draw()
                fn(probe_lines, check, pic)
            except Exception:
                probe_lines.append("FAIL  " + traceback.format_exc())
            out_lines.extend(probe_lines)
            out_lines.append("PROBE_END %s" % name)
        with open(os.path.join(base_dir, "probe_out.txt"), "w") as fh:
            fh.write("\\n".join(out_lines) + "\\n")
        os._exit(0)

    renpy.arguments.commands["lint"] = _pp_lint
'''


def discover(folder=HERE):
    """Return sorted list of paths to check_*.py files carrying `# prop_probe:`."""

    paths = []
    for name in sorted(os.listdir(folder)):
        if not (name.startswith("check_") and name.endswith(".py")):
            continue
        path = os.path.join(folder, name)
        with io.open(path, encoding="utf-8", errors="replace") as f:
            if PROBE_MARKER.search(f.read()):
                paths.append(path)
    return paths


def load_probe(path):
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location("urm_probe_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {
        "name": name,
        "path": path,
        "files": getattr(mod, "PROBE_FILES", {}),
        "code": getattr(mod, "PROBE_CODE", u""),
        "entry": getattr(mod, "PROBE_ENTRY", ""),
        "pic_env": getattr(mod, "PROBE_PIC_ENV", ""),
        "tag_env": getattr(mod, "PROBE_TAG_ENV", ""),
        "min_engines": getattr(mod, "PROBE_MIN_ENGINES", 2),
        "title": getattr(mod, "PROBE_TITLE", name),
    }


def fixture_files(probes):
    found = {}
    entries = []
    found["zzzz_probe_00_draw.rpy"] = DRAW_HELPER.encode("utf-8")
    for i, p in enumerate(probes):
        for fname, fdata in p["files"].items():
            found[fname] = fdata
        entries.append((p["name"], p["entry"], p["pic_env"], p["tag_env"]))
        found["zzzz_probe_%02d_%s.rpy" % (i + 1, p["name"])] = p["code"].encode("utf-8")
    harness = (
        u"\ninit 1999 python:\n    _PP_PROBES = [\n"
        + u"".join(
            u"        (%r, %s, %r, %r),\n" % (n, e, pe, te)
            for n, e, pe, te in entries
        )
        + u"    ]\n"
        + HARNESS_TAIL
    )
    found["zzzz_probe_99_harness.rpy"] = harness.encode("utf-8")
    return found


def build_files(probes):
    found = fixture_files(probes)
    found["urm_plus.rpy"] = make_rpy.build().encode("utf-8")
    found.update(check_kit.fonts())
    return found


def parse_report(raw_lines, probe_names):
    """Split probe_out.txt into {probe_name: [lines]}."""

    by_probe = dict((n, []) for n in probe_names)
    current = None
    for line in raw_lines:
        if line.startswith("PROBE_BEGIN "):
            current = line[len("PROBE_BEGIN "):].strip()
        elif line.startswith("PROBE_END "):
            current = None
        elif current in by_probe:
            by_probe[current].append(line)
    return by_probe


def run_prop(prop, probes, found, pictures=None):
    """Run one prop engine across all probes in `probes`.
    Returns (verdict, by_probe_lines, extra_lines)."""

    engine = check_kit.engine(prop)
    if engine is None:
        return "no engine", {}, []
    py, flags, start, env = engine
    base = tempfile.mkdtemp(prefix="urm_probes_")
    try:
        game = os.path.join(base, "game")
        home = os.path.join(base, "_home")
        os.makedirs(os.path.join(home, "persistent"))
        os.makedirs(os.path.join(home, "RenPy"))
        for name, data in found.items():
            path = os.path.join(game, *name.split("/"))
            if not os.path.isdir(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            with open(path, "wb") as f:
                f.write(data)
        env.update(RENPY_PATH_TO_SAVES=home, APPDATA=home,
                   RENPY_MULTIPERSISTENT=os.path.join(home, "persistent"))
        if pictures:
            tag = os.path.basename(prop).replace("prop-", "").split("-")[0].replace(" ", "_")
            for p in probes:
                if p["pic_env"]:
                    env[p["pic_env"]] = pictures
                if p["tag_env"]:
                    env[p["tag_env"]] = tag
        out = os.path.join(base, "probe_out.txt")
        try:
            result = subprocess.run([py] + flags + ["-B", start, base, "lint"], cwd=base, env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            said = result.stdout.decode("utf-8", "replace")
        except subprocess.TimeoutExpired:
            return "the engine did not finish in 300 s", {}, []
        if not os.path.exists(out):
            trace = os.path.join(base, "traceback.txt")
            if os.path.exists(trace):
                with io.open(trace, encoding="utf-8", errors="replace") as f:
                    said = f.read()
                if "Could not load from archive" in said:
                    return "protected", {}, []
            elif not glob.glob(os.path.join(game, "*.rpyc")):
                return "skip", {}, []
            return "the engine stopped", {}, said.strip().splitlines()[-14:]
        with io.open(out, encoding="utf-8", errors="replace") as f:
            raw = [l for l in f.read().splitlines() if l.strip()]
        by_probe = parse_report(raw, [p["name"] for p in probes])
        return "ok", by_probe, []
    finally:
        shutil.rmtree(base, ignore_errors=True)


def run_suite(props_dir, probe_paths=None, pictures=None):
    """Run all selected probes, sharing 1 URM boot + 1 standalone boot per prop.
    Returns (overall_rc, per_probe_results)."""

    paths = list(probe_paths) if probe_paths else discover()
    probes = [load_probe(p) for p in paths]
    if not probes:
        return 0, {}
    props = sorted(p for p in glob.glob(os.path.join(os.path.abspath(props_dir), "prop-*"))
                   if os.path.isdir(p))
    files = build_files(probes)
    results = {}
    with ThreadPoolExecutor(max_workers=len(props) or 1) as pool:
        futures = {prop: pool.submit(run_prop, prop, probes, files, pictures) for prop in props}
        for prop, future in futures.items():
            results[prop] = future.result()

    overall_failed = 0
    summary = {}
    for p in probes:
        pname = p["name"]
        checked = failed = 0
        out_lines = []
        for prop in props:
            verdict, by_probe, extra = results[prop]
            label = os.path.basename(prop)
            if verdict in ("skip", "protected"):
                out_lines.append("skip  %s: %s" % (
                    label, "its engine ignores loose script files" if verdict == "skip"
                    else "it reads only archives the installer re-encodes"))
                continue
            checked += 1
            if verdict != "ok":
                failed += 1
                out_lines.append("FAIL  %s: %s" % (label, verdict))
                for line in extra:
                    out_lines.append("      " + line)
                continue
            lines = by_probe.get(pname) or []
            bad = [l for l in lines if not l.startswith("pass")]
            if lines and not bad:
                out_lines.append("pass  %s: %d checks" % (label, len(lines)))
            else:
                failed += 1
                out_lines.append("FAIL  %s: %s" % (label, "failed" if lines else "no output"))
                for line in bad:
                    out_lines.append("      " + line)
        min_eng = p["min_engines"]
        if checked < min_eng:
            out_lines.append("FAIL  only %d engine runs checked (need at least %d)" % (checked, min_eng))
            failed += 1
        summary[pname] = (failed == 0, out_lines)
        overall_failed += bool(failed)
    return (1 if overall_failed else 0), summary


def main_single(probe_file, argv):
    """CLI entry point for an individual check_*.py probe run standalone."""

    args = [a for a in argv[1:] if not a.startswith("--")]
    pictures = None
    if "--pictures" in argv:
        idx = argv.index("--pictures")
        pictures = os.path.abspath(argv[idx + 1])
        args.remove(argv[idx + 1])
        if not os.path.isdir(pictures):
            os.makedirs(pictures)
    if not args:
        return 2
    rc, summary = run_suite(args[0], [probe_file], pictures)
    for _name, (_ok, lines) in summary.items():
        for line in lines:
            print(line)
    return rc


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    pictures = None
    if "--pictures" in argv:
        idx = argv.index("--pictures")
        pictures = os.path.abspath(argv[idx + 1])
        args.remove(argv[idx + 1])
        if not os.path.isdir(pictures):
            os.makedirs(pictures)
    if not args:
        print(__doc__)
        return 2
    props_dir = args[0]
    probe_paths = [os.path.abspath(p) for p in args[1:]] or None
    rc, summary = run_suite(props_dir, probe_paths, pictures)
    for pname, (ok, lines) in summary.items():
        print("[%s] %s" % (pname, "pass" if ok else "FAIL"))
        for line in lines:
            print("  " + line)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
