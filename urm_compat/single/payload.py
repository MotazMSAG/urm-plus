"""
MRM installer - the tool half of URM_fix.bat.

Run by the .bat with the game folder as its only argument, using the game's
own bundled interpreter. Everything is driven from the menu in main().
"""

from __future__ import print_function

import base64
import hashlib
import os
import pickle
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

STOCK_HEADER = b"RENPY RPC2"
SLOT_ENTRIES = 3
SLOT_TABLE_SIZE = SLOT_ENTRIES * 12
MD5_SIZE = 16

# Filled in at build time.
MODCOMPAT_B64 = "@@MODCOMPAT_B64@@"
ADDON_B64 = "@@ADDON_B64@@"
SCREENS_B64 = "@@SCREENS_B64@@"
# Our own files beside the code, "entry=base64;entry=base64" (the fonts our
# screens draw with, and their licence).
OUR_FILES_B64 = "@@OUR_FILES_B64@@"

# Standalone MRM: the joined code, screens and licensed fonts.
OUR_ARCHIVE = "urmplus.rpa"
ADDON_ENTRY = "urmplus/addon.rpyc"
SCREENS_ENTRY = "urmplus/screens.rpyc"

# Where builds before 2026-11-21 put the add-on: inside URM's own archive.
OLD_ADDON_ENTRY = "0x52-URM/zzz_urm_compat.rpyc"


HOOK_ANCHOR = b"renpy.main.main()"
HOOK = (
    b"# Let this build load .rpyc files from stock-Ren'Py add-ons.\r\n"
    b"                import renpy.modcompat\r\n"
    b"                renpy.modcompat.apply()\r\n"
    b"\r\n"
    b"                renpy.main.main()"
)

PROBE_FILES = [
    "renpy/script.py",
    "renpy/loader.py",
    "renpy/main.py",
    "renpy/bootstrap.py",
]

BASE = None
RENPY = None


# ---------------------------------------------------------------- engine ---

def load_engine():
    """
    Imports the game's engine, which decrypts and keys its native module as a
    side effect. Returns None if the engine refuses to load.
    """

    global RENPY

    if RENPY is not None:
        return RENPY

    os.chdir(BASE)

    if BASE not in sys.path:
        sys.path.insert(0, BASE)

    # Ren'Py 7.3 and older import pygame_sdl2 under the name pygame; their
    # launcher sets that up before the engine loads, so do the same.
    try:
        import pygame_sdl2
        pygame_sdl2.import_as_pygame()
    except Exception:
        pass

    try:
        import renpy
    except SystemExit:
        return None
    except Exception:
        return None

    RENPY = renpy
    return renpy


def engine_imports():
    """
    True if the engine imports in a fresh process. A protected build exits
    silently when a hash-checked file has been altered, so this is how
    tampering shows up.
    """

    code = "import sys, os; sys.path.insert(0, os.getcwd()); import renpy"

    try:
        result = subprocess.Popen(
            # -O carries over: Ren'Py 7.3 and older ship only .pyo files.
            [sys.executable] + (["-O"] if sys.flags.optimize else [])
            + (["-I"] if sys.version_info[0] == 3 else ["-s"]) + ["-c", code],
            cwd=BASE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result.communicate()
    except Exception:
        return None

    return result.returncode == 0


def probe_protected(relative):
    """
    Appends a comment to `relative`, checks whether the engine still imports,
    and restores the file. True if the file is hash-checked.
    """

    path = os.path.join(BASE, relative)

    if not os.path.exists(path):
        return None

    with open(path, "rb") as f:
        original = f.read()

    try:
        with open(path, "wb") as f:
            f.write(original + b"\r\n# probe\r\n")
        ok = engine_imports()
    finally:
        with open(path, "wb") as f:
            f.write(original)

    if ok is None:
        return None

    return not ok


# --------------------------------------------------------------- archive ---

def read_archive(path):
    """
    Reads an RPA-2.0 or RPA-3.0 archive into {name: bytes}.
    """

    with open(path, "rb") as f:
        parts = f.readline().split()

        if parts[0] == b"RPA-3.0":
            offset = int(parts[1], 16)
            key = int(parts[2], 16)
        elif parts[0] == b"RPA-2.0":
            offset = int(parts[1], 16)
            key = 0
        else:
            raise ValueError("%s is not an RPA-2.0 or RPA-3.0 archive." % path)

        f.seek(offset)
        index = pickle.loads(zlib.decompress(f.read()))

        contents = {}

        for name, entries in index.items():
            if isinstance(name, bytes):
                name = name.decode("utf-8")

            chunks = []

            for entry in entries:
                start = entry[0] ^ key
                length = entry[1] ^ key
                prefix = entry[2] if len(entry) > 2 else b""

                if isinstance(prefix, str):
                    prefix = prefix.encode("latin-1")

                # The stored length covers the bytes in the file only; any
                # prefix is held in the index and sits in front of them.
                f.seek(start)
                chunks.append(prefix + f.read(length))

            contents[name] = b"".join(chunks)

    return contents


def read_archive_names(path):
    """
    Just the entry names, without pulling any content into memory - the game's
    own archives can be hundreds of megabytes.
    """

    with open(path, "rb") as f:
        parts = f.readline().split()

        if parts[0] not in (b"RPA-3.0", b"RPA-2.0"):
            raise ValueError("not an RPA-2.0 or RPA-3.0 archive")

        f.seek(int(parts[1], 16))
        index = pickle.loads(zlib.decompress(f.read()))

    return [n.decode("utf-8") if isinstance(n, bytes) else n for n in index]


def write_archive(path, contents):
    """
    Writes a stock RPA-3.0 archive. The container is not what these builds
    change, so this stays standard.
    """

    key = 0x42424242
    index = {}

    with open(path, "wb") as f:
        f.write(b" " * 34)

        for name in sorted(contents):
            data = contents[name]
            start = f.tell()
            f.write(data)
            index[name] = [(start ^ key, len(data) ^ key, b"")]

        offset = f.tell()
        f.write(zlib.compress(pickle.dumps(index, 2), 3))

        f.seek(0)
        f.write(b"RPA-3.0 %016x %08x\n" % (offset, key))


def write_native_rpyc(renpy, slots, digest):
    """
    Emits a .rpyc the way this build's write_rpyc_* methods would.
    """

    header = getattr(renpy, "_RPYC_HEADER", STOCK_HEADER)
    pack = getattr(renpy, "compress_bytecode_stream", None)

    out = bytearray()
    out += header
    out += b"\x00" * SLOT_TABLE_SIZE

    table = []

    for slot, payload in slots:
        if pack is not None:
            payload = pack(payload)

        table.append((slot, len(out), len(payload)))
        out += payload

    pos = len(header)

    for entry in table:
        out[pos:pos + 12] = struct.pack("III", *entry)
        pos += 12

    out += digest

    return bytes(out)


READY = []


def ready_engine(renpy):
    """
    Readies the engine to parse, once per run: import_all() a second time
    fails (it pickles the stand-in script below), and screen statements need
    the screen-language parser, which the engine's own start sets up.
    """

    if READY:
        return

    renpy.import_all()
    renpy.sl2.slparser.init()

    class FakeScript(object):
        record_pycode = False
        all_pycode = []
        serial = 0

        def __getattr__(self, name):
            return None

    class FakeContext(object):
        init_phase = True

    renpy.game.script = FakeScript()

    if not renpy.game.contexts:
        renpy.game.contexts = [FakeContext()]

    READY.append(True)


def compile_rpy(renpy, path, script_name):
    with open(path, "rb") as f:
        return compile_source(renpy, f.read(), path, script_name)


def compile_source(renpy, source, filename, script_name):
    """Compile source in the game's format. The engine builds slot 2."""
    ready_engine(renpy)

    if sys.version_info[0] == 2:
        # Every Ren'Py 7 writes its .rpyc files with protocol 2 (script.py:
        # dumps((data, stmts), 2)). 7.4's renpy.compat.pickle.dumps takes the
        # protocol as an argument and defaults lower, where the AST's
        # __slots__ classes cannot be pickled at all.
        import cPickle

        def dumps(value):
            return cPickle.dumps(value, 2)
    else:
        from renpy.compat.pickle import dumps

    script = renpy.game.script
    statements = renpy.parser.parse(filename, filedata=source.decode("utf-8").lstrip(u"\ufeff"))

    if statements is None:
        raise ValueError("%s failed to parse." % filename)

    # Every node needs a unique name, or the loader rejects the file as
    # defining a name twice.
    # On Python 2 this is an unbound method, which refuses a FakeScript.
    assign = renpy.script.Script.assign_names
    getattr(assign, "__func__", assign)(script, statements, script_name)

    data = {}
    data['version'] = renpy.script_version
    data['key'] = 'unlocked'
    # Older engines (Ren'Py 7.3 and before) have no deferred parse errors.
    if hasattr(renpy.parser, "deferred_parse_errors"):
        data['deferred_parse_errors'] = renpy.parser.deferred_parse_errors

    payload = zlib.compress(dumps((data, statements)), 3)

    return payload, hashlib.md5(source).digest()


# ---------------------------------------------------------------- source ---

def is_ours(contents):
    """
    True for a URM archive an older URM+ build wrote: it carries the add-on
    and the interface tweaks of its day, so installing from it would keep
    those - only a plain URM is a good starting point. (Builds since
    2026-11-21 leave URM's archive as URM ships it.)
    """

    if OLD_ADDON_ENTRY in contents:
        return True

    # A failed install can leave the tweaks without the add-on (the build of
    # 2026-10-28 wrote exactly that). Every build's tweaks name a setting
    # urmc... or a helper _urm...; plain URM's screens mention neither.
    return any(old_screen_edit(data)
               for name, data in contents.items()
               if name.endswith((".x52", ".x52t")))


def old_screen_edit(data):
    return b"urmc" in data or b"_urm" in data


def urm_holds_old_addon():
    """Recognize an older combined install, archived or extracted."""
    game = os.path.join(BASE, "game")
    previous = os.path.join(game, OLD_ADDON_ENTRY)
    if os.path.isfile(previous) or os.path.isfile(previous[:-1]):
        return True
    loose = os.path.dirname(previous)
    for directory, _folders, files in os.walk(loose):
        for name in files:
            if name.endswith((".x52", ".x52t")):
                with open(os.path.join(directory, name), "rb") as f:
                    if old_screen_edit(f.read()):
                        return True
    installed = os.path.join(game, "0x52_URM.rpa")
    return os.path.isfile(installed) and is_ours(read_archive(installed))


# --------------------------------------------------------------- actions ---

def game_is_open():
    """
    True when the game in BASE is running. A running program's .exe, and an
    archive the engine is reading, cannot be opened for writing on Windows -
    so try exactly that, without writing anything. Ren'Py 8 keeps its
    archives open while it runs, and replacing an open archive failed
    with a raw PermissionError.
    """

    busy = [os.path.join(BASE, n) for n in os.listdir(BASE) if n.lower().endswith(".exe")]
    busy.append(os.path.join(BASE, "game", OUR_ARCHIVE))

    for path in busy:
        # A read-only file refuses writing for its own reason; not "open".
        if not os.path.isfile(path) or not os.access(path, os.W_OK):
            continue
        try:
            # Binary: Windows opens a file for writing in text mode by
            # default, and then cuts a last byte of Ctrl+Z (0x1A) off it - an
            # archive whose index happens to end in one came back broken.
            fd = os.open(path, os.O_RDWR | getattr(os, "O_BINARY", 0))
        except (IOError, OSError):
            return True
        os.close(fd)

    return False


def say_game_is_open():
    print()
    print("  ! The game is open. Close it, then run this again.")
    print("    Nothing was changed.")


def write_install(target, contents):
    """Publish the complete archive in one filesystem operation."""
    fd, pending = tempfile.mkstemp(prefix=".urmplus-", suffix=".tmp", dir=os.path.dirname(target))
    os.close(fd)
    try:
        write_archive(pending, contents)
        if hasattr(os, "replace"):
            os.replace(pending, target)
        elif os.name == "nt":
            import ctypes
            move = ctypes.windll.kernel32.MoveFileExW
            encoding = sys.getfilesystemencoding()
            source = pending.decode(encoding) if isinstance(pending, bytes) else pending
            dest = target.decode(encoding) if isinstance(target, bytes) else target
            if not move(source, dest, 1 | 8):
                raise ctypes.WinError()
        else:
            os.rename(pending, target)
    finally:
        if os.path.exists(pending):
            os.remove(pending)


def action_install():
    if game_is_open():
        say_game_is_open()
        return False

    try:
        if urm_holds_old_addon():
            print()
            print("  ! An older combined URM and URM+ copy is in game/.")
            print("    Move game/0x52_URM.rpa or the combined game/0x52-URM folder")
            print("    to a backup outside game/, then run this installer again.")
            print("    Keep the backup. Nothing was changed.")
            return False
    except (IOError, OSError, ValueError, EOFError, zlib.error, pickle.UnpicklingError) as error:
        print("  ! Could not examine the older archive: %s" % error)
        print("    Nothing was changed.")
        return False

    renpy = load_engine()
    if renpy is None:
        print()
        print("  The engine will not load. If you patched it earlier, undo")
        print("  that with option 3 first.")
        return False

    contents = {}
    try:
        for filename, encoded, entry in (
                ("_urmfix_hyperlink.rpy", ADDON_B64, ADDON_ENTRY),
                ("_urmfix_screens.rpy", SCREENS_B64, SCREENS_ENTRY)):
            data, digest = compile_source(renpy, base64.b64decode(encoded), filename, entry[:-1])
            contents[entry] = write_native_rpyc(renpy, [(1, data)], digest)
        for item in OUR_FILES_B64.split(";"):
            entry, encoded = item.split("=", 1)
            contents[entry] = base64.b64decode(encoded)
    except Exception as error:
        print()
        print("  ! Could not build MRM for this game: %s" % error)
        print("    Nothing was changed. Please report this line.")
        return False

    target = os.path.join(BASE, "game", OUR_ARCHIVE)
    try:
        write_install(target, contents)
    except (IOError, OSError) as error:
        if game_is_open():
            say_game_is_open()
        else:
            print("  ! Could not write game/%s: %s" % (OUR_ARCHIVE, error))
            print("    Nothing was changed.")
        return False

    print("  Wrote game/%s (MRM)" % OUR_ARCHIVE)
    print("  Done. Start the game.")
    return True


def action_patch_engine():
    bootstrap = os.path.join(BASE, "renpy", "bootstrap.py")

    if not os.path.exists(bootstrap):
        print("\n  No renpy/bootstrap.py here.")
        return

    print()
    print("  Checking which engine files are hash-checked...")

    baseline = engine_imports()

    if baseline is not True:
        print("  ! The engine does not import even untouched, so the check")
        print("    cannot tell tampering from an unrelated failure.")
        print("    Carrying on, but undo with option 3 if the game stops")
        print("    starting.")
    else:
        for relative in PROBE_FILES:
            result = probe_protected(relative)

            if result is None:
                continue

            print("      %-22s %s" % (
                relative, "hash-checked" if result else "free to edit"))

            if result and relative == "renpy/bootstrap.py":
                print()
                print("  ! bootstrap.py is hash-checked on this build, so there")
                print("    is nowhere safe to hook. Use option 1 instead.")
                return

    with open(bootstrap, "rb") as f:
        content = f.read()

    if b"renpy.modcompat" in content:
        print("\n  Already patched - refreshing the shim only.")
    elif content.count(HOOK_ANCHOR) != 1:
        print("\n  ! Could not find a unique renpy.main.main() in bootstrap.py.")
        print("    Nothing was changed.")
        return
    else:
        shutil.copyfile(bootstrap, bootstrap + ".bak")

        with open(bootstrap, "wb") as f:
            f.write(content.replace(HOOK_ANCHOR, HOOK))

        print("\n  Patched renpy/bootstrap.py (original kept as bootstrap.py.bak)")

    with open(os.path.join(BASE, "renpy", "modcompat.py"), "wb") as f:
        f.write(base64.b64decode(MODCOMPAT_B64))

    print("  Wrote renpy/modcompat.py")

    if engine_imports():
        print()
        print("  Verified: the engine still loads.")
        print("  Put URM's .rpa in game/ as it comes - no conversion needed.")
    else:
        print()
        print("  ! The engine no longer loads. Undoing.")
        action_unpatch_engine(quiet=True)


def action_unpatch_engine(quiet=False):
    bootstrap = os.path.join(BASE, "renpy", "bootstrap.py")
    backup = bootstrap + ".bak"
    shim = os.path.join(BASE, "renpy", "modcompat.py")
    touched = False

    if os.path.exists(backup):
        shutil.move(backup, bootstrap)
        touched = True
        if not quiet:
            print("\n  Restored renpy/bootstrap.py")

    if os.path.exists(shim):
        os.remove(shim)
        touched = True
        if not quiet:
            print("  Removed renpy/modcompat.py")

    cache = os.path.join(BASE, "renpy", "__pycache__")

    if os.path.isdir(cache):
        for name in os.listdir(cache):
            if name.startswith("modcompat."):
                os.remove(os.path.join(cache, name))

    if not touched and not quiet:
        print("\n  Nothing to undo - the engine is not patched.")


def action_diagnose():
    renpy = load_engine()

    print()

    if renpy is None:
        print("  The engine will not load. Either a hash-checked file was")
        print("  edited, or the game is not a Ren'Py game.")
        return

    header = getattr(renpy, "_RPYC_HEADER", STOCK_HEADER)
    pack = getattr(renpy, "compress_bytecode_stream", None)

    print("  Ren'Py version:     %s" % renpy.version)
    print("  rpyc header:        %r%s" % (
        header, "" if header != STOCK_HEADER else "   (stock)"))
    print("  stream encryption:  %s" % ("yes" if pack else "no"))
    print("  native module:      %s" % (", ".join(
        n for n in os.listdir(os.path.join(BASE, "renpy"))
        if n.startswith("_glcache")) or "none"))

    print()
    print("  Archives in game/:")

    for name in sorted(os.listdir(os.path.join(BASE, "game"))):
        if not name.lower().endswith(".rpa"):
            continue

        try:
            entries = read_archive_names(os.path.join(BASE, "game", name))
        except Exception as e:
            print("      %-28s (unreadable: %s)" % (name, e))
            continue

        scripts = sum(1 for n in entries if n.endswith(".rpyc"))
        print("      %-28s %5d files, %4d script files"
              % (name, len(entries), scripts))

    print()
    print("  Engine patched:     %s" % (
        "yes" if os.path.exists(os.path.join(BASE, "renpy", "modcompat.py"))
        else "no"))

    print()
    print("  Checking which engine files are hash-checked...")

    if engine_imports() is not True:
        print("      (skipped - the engine does not import cleanly)")
        return

    for relative in PROBE_FILES:
        result = probe_protected(relative)

        if result is None:
            continue

        print("      %-22s %s" % (
            relative, "hash-checked" if result else "free to edit"))


# ------------------------------------------------------------------ menu ---

def banner():
    renpy = load_engine()

    name = os.path.basename(BASE)
    version = renpy.version if renpy else "engine will not load"

    protected = "no"

    if renpy is not None:
        if getattr(renpy, "compress_bytecode_stream", None) is not None:
            protected = "yes - script cache is encrypted"

    print()
    print("  " + "=" * 62)
    print("   Multiversal Ren'Py Mod (MRM) installer")
    print("  " + "=" * 62)
    print()
    print("   Game:      %s" % name)
    print("   Engine:    %s" % version)
    print("   Protected: %s" % protected)
    print()


def ask(prompt):
    """
    Reads one line. Returns None at end of input, so the loop can stop instead
    of spinning when there is no console.
    """

    sys.stdout.write(prompt)
    sys.stdout.flush()

    try:
        line = sys.stdin.readline()
    except (EOFError, KeyboardInterrupt):
        return None

    if not line:
        return None

    return line.strip()


def menu():
    while True:
        print("  " + "-" * 62)
        print("   1)  Install MRM into this game       (start here)")
        print("   2)  Patch the engine for other add-ons")
        print("   3)  Undo the engine patch")
        print("   4)  Show me what this game does")
        print("   0)  Quit")
        print("  " + "-" * 62)
        print()

        choice = ask("   Choice: ")

        if choice is None:
            return

        print()

        if choice == "1":
            action_install()
        elif choice == "2":
            action_patch_engine()
        elif choice == "3":
            action_unpatch_engine()
        elif choice == "4":
            action_diagnose()
        elif choice in ("0", "q", "Q"):
            return
        else:
            print("\n   Pick 1, 2, 3, 4 or 0.")

        print()


def main(argv):
    global BASE

    if len(argv) < 2:
        print("Run this through URM_fix.bat.")
        return 2

    BASE = os.path.abspath(argv[1])

    if not os.path.isdir(os.path.join(BASE, "game")):
        print()
        print("  %s has no game\\ folder in it, so it is not a Ren'Py game." % BASE)
        print("  Put URM_fix.bat next to the game's .exe and run it there.")
        return 1

    # "install" as a third argument installs without the menu - how a batch
    # of games gets updated, so every one goes through the same detection.
    try:
        if len(argv) > 3 and argv[3] == "install":
            return 0 if action_install() else 1

        banner()
        menu()
    except KeyboardInterrupt:
        return 1
    except Exception:
        import traceback
        print()
        print("  ! Something went wrong that this tool does not know about.")
        print("    The details below say where - please report them.")
        print()
        traceback.print_exc(file=sys.stdout)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
