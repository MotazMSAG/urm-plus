"""
Installs modcompat.py into a Ren'Py game so it can load stock .rpyc add-ons.

    python install.py "<game folder>"              inspect and install
    python install.py --check "<game folder>"      inspect only, change nothing
    python install.py --uninstall "<game folder>"  put it back

The <game folder> is the one holding renpy/ and game/ - the folder with the
.exe in it.

What it does:

  * reports the engine version and whether the build encrypts its script cache
  * works out which engine files are hash-checked, by appending a byte to each
    and seeing whether the engine still imports (restoring it either way)
  * refuses to touch any file that turns out to be checked
  * copies modcompat.py into renpy/ and calls it from renpy/bootstrap.py
  * re-runs the import check afterwards to confirm nothing was tripped

Run it with any Python 3; it locates the game's own interpreter for the probes.
"""

from __future__ import print_function

import os
import shutil
import subprocess
import sys

HOOK_ANCHOR = b"renpy.main.main()"

HOOK = (
    b"# Let this build load .rpyc files from stock-Ren'Py add-ons.\r\n"
    b"                import renpy.modcompat\r\n"
    b"                renpy.modcompat.apply()\r\n"
    b"\r\n"
    b"                renpy.main.main()"
)

# Engine files worth probing. The first three are the ones protected builds
# normally check, because they are where the anti-mod gates live.
PROBE_FILES = [
    "renpy/script.py",
    "renpy/loader.py",
    "renpy/main.py",
    "renpy/bootstrap.py",
]

PYTHON_CANDIDATES = [
    "lib/py3-windows-x86_64/python.exe",
    "lib/py3-windows-i686/python.exe",
    "lib/py3-linux-x86_64/python",
    "lib/py3-mac-universal/python",
    "lib/windows-x86_64/python.exe",
    "lib/linux-x86_64/python",
]


def find_python(base):
    for rel in PYTHON_CANDIDATES:
        path = os.path.join(base, rel)
        if os.path.exists(path):
            return path
    return None


def engine_imports(python, base):
    """
    True if the engine imports cleanly. A protected build calls sys.exit(1)
    from renpy/__init__.py when a hash-checked file has been altered, so this
    is how tampering shows up: silently, with no message.
    """

    code = "import sys, os; sys.path.insert(0, os.getcwd()); import renpy"

    try:
        result = subprocess.run(
            [python, "-c", code], cwd=base,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    except Exception as e:
        print("    ! could not run the game's Python: %s" % e)
        return None

    return result.returncode == 0


def probe_protected(python, base, relative):
    """
    Appends a comment to `relative`, checks whether the engine still imports,
    and restores the file. Returns True if the file is hash-checked.
    """

    path = os.path.join(base, relative)

    if not os.path.exists(path):
        return None

    with open(path, "rb") as f:
        original = f.read()

    try:
        with open(path, "wb") as f:
            f.write(original + b"\r\n# probe\r\n")
        ok = engine_imports(python, base)
    finally:
        with open(path, "wb") as f:
            f.write(original)

    if ok is None:
        return None

    return not ok


def describe(base):
    print("Game folder: %s" % base)

    init = os.path.join(base, "renpy", "__init__.py")
    script = os.path.join(base, "renpy", "script.py")

    version = "unknown"
    for candidate in ("renpy/vc_version.py", "renpy/__init__.py"):
        path = os.path.join(base, candidate)
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            for line in f:
                if line.strip().startswith(b"version ="):
                    version = line.strip().decode("utf-8", "replace")
                    break
        if version != "unknown":
            break
    print("  engine:            %s" % version)

    with open(init, "rb") as f:
        init_bytes = f.read()

    packed = b"_GL_DATA" in init_bytes
    native = [n for n in os.listdir(os.path.join(base, "renpy"))
              if n.startswith("_glcache")]

    custom_header = False
    if os.path.exists(script):
        with open(script, "rb") as f:
            for line in f:
                if line.strip().startswith(b"RPYC2_HEADER"):
                    custom_header = b'b"RENPY RPC2"' not in line
                    break

    print("  encrypted engine:  %s" % ("yes" if packed else "no"))
    print("  native module:     %s" % (", ".join(native) if native else "none"))
    print("  custom rpyc header:%s" % (" yes" if custom_header else " no"))

    return packed or bool(native) or custom_header


def install(base, check_only=False):
    if not os.path.isdir(os.path.join(base, "renpy")):
        print("No renpy/ directory here - is this the folder with the .exe?")
        return 1

    protected = describe(base)
    print()

    python = find_python(base)

    if python is None:
        print("  ! no bundled Python found; skipping the tamper probes.")
        checked = {}
    else:
        print("  probing which engine files are hash-checked")
        baseline = engine_imports(python, base)

        if baseline is not True:
            print("  ! the engine does not import even untouched - skipping probes.")
            print("    (harmless if the game still runs; the probe just cannot")
            print("     tell tampering apart from an unrelated import failure)")
            checked = {}
        else:
            checked = {}
            for relative in PROBE_FILES:
                result = probe_protected(python, base, relative)
                if result is None:
                    continue
                checked[relative] = result
                print("    %-22s %s" % (
                    relative, "HASH-CHECKED" if result else "free to edit"))

    print()

    if checked.get("renpy/bootstrap.py"):
        print("  ! renpy/bootstrap.py is hash-checked on this build, so the")
        print("    usual hook point is unavailable. Nothing was changed.")
        print("    Look for another module imported before renpy.main.main()")
        print("    that is not checked, and call modcompat.apply() from there.")
        return 1

    if check_only:
        print("  --check given; nothing was changed.")
        return 0

    bootstrap = os.path.join(base, "renpy", "bootstrap.py")

    with open(bootstrap, "rb") as f:
        content = f.read()

    if b"renpy.modcompat" in content:
        print("  already installed - refreshing modcompat.py only.")
    else:
        if content.count(HOOK_ANCHOR) != 1:
            print("  ! could not find a unique 'renpy.main.main()' in bootstrap.py")
            print("    (found %d). Nothing was changed." % content.count(HOOK_ANCHOR))
            return 1

        shutil.copyfile(bootstrap, bootstrap + ".bak")
        with open(bootstrap, "wb") as f:
            f.write(content.replace(HOOK_ANCHOR, HOOK))
        print("  hooked renpy/bootstrap.py (original saved as bootstrap.py.bak)")

    shutil.copyfile(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "modcompat.py"),
        os.path.join(base, "renpy", "modcompat.py"))
    print("  copied renpy/modcompat.py")

    if python is not None:
        print()
        if engine_imports(python, base):
            print("  verified: the engine still imports, so no check was tripped.")
        else:
            print("  ! the engine no longer imports. Reverting.")
            uninstall(base, quiet=True)
            return 1

    print()
    print("Done. Put the add-on's .rpa in %s and start the game."
          % os.path.join(base, "game"))

    if protected:
        print()
        print("Note: this build runs in release mode, so loose .rpy/.rpyc files")
        print("in game/ are ignored. Add-ons have to stay packed as .rpa.")

    return 0


def uninstall(base, quiet=False):
    bootstrap = os.path.join(base, "renpy", "bootstrap.py")
    backup = bootstrap + ".bak"
    shim = os.path.join(base, "renpy", "modcompat.py")

    if os.path.exists(backup):
        shutil.move(backup, bootstrap)
        if not quiet:
            print("  restored renpy/bootstrap.py")
    elif not quiet:
        print("  no bootstrap.py.bak found; leaving bootstrap.py alone")

    if os.path.exists(shim):
        os.remove(shim)
        if not quiet:
            print("  removed renpy/modcompat.py")

    cache = os.path.join(base, "renpy", "__pycache__")
    if os.path.isdir(cache):
        for name in os.listdir(cache):
            if name.startswith("modcompat."):
                os.remove(os.path.join(cache, name))

    return 0


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = set(a for a in argv[1:] if a.startswith("--"))

    if not args:
        print(__doc__)
        return 2

    base = os.path.abspath(args[0])

    if "--uninstall" in flags:
        return uninstall(base)

    return install(base, check_only="--check" in flags)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
