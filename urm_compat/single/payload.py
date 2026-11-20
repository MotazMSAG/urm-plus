"""
URM compatibility helper - the tool half of URM_fix.bat.

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
import zlib

STOCK_HEADER = b"RENPY RPC2"
SLOT_ENTRIES = 3
SLOT_TABLE_SIZE = SLOT_ENTRIES * 12
MD5_SIZE = 16

# Filled in at build time.
MODCOMPAT_B64 = "@@MODCOMPAT_B64@@"
HYPERLINK_FIX_B64 = "@@HYPERLINK_FIX_B64@@"
UI_TWEAKS_B64 = "@@UI_TWEAKS_B64@@"


def load_ui_tweaks():
    """
    The ui_tweaks module, run out of the copy embedded in this file. It only
    edits URM's own screen source, so a failure here is never fatal.
    """

    namespace = {"__name__": "ui_tweaks"}

    try:
        exec(base64.b64decode(UI_TWEAKS_B64).decode("utf-8"), namespace)
    except Exception:
        return None

    return namespace

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
BAT = None


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
            [sys.executable] + (["-O"] if sys.flags.optimize else []) + ["-c", code],
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


def read_stock_slots(data):
    """
    Pulls each slot's compressed payload out of a stock .rpyc, plus the md5 at
    the end. None if `data` is not a stock v2 .rpyc.
    """

    if data[:len(STOCK_HEADER)] != STOCK_HEADER:
        return None

    slots = []
    pos = len(STOCK_HEADER)

    for _ in range(SLOT_ENTRIES):
        slot, start, length = struct.unpack("III", data[pos:pos + 12])

        if slot == 0:
            break

        slots.append((slot, data[start:start + length]))
        pos += 12

    if not slots:
        return None

    return slots, data[-MD5_SIZE:]


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


def compile_rpy(renpy, path, script_name):
    """
    Compiles a .rpy into the slot 1 payload of a .rpyc, as Script.load_file
    does after parsing a source file. The engine applies static transforms
    itself for a file with no slot 2.
    """

    renpy.import_all()

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

    class FakeScript(object):
        record_pycode = False
        all_pycode = []
        serial = 0

        def __getattr__(self, name):
            return None

    class FakeContext(object):
        init_phase = True

    script = FakeScript()
    renpy.game.script = script

    if not renpy.game.contexts:
        renpy.game.contexts = [FakeContext()]

    statements = renpy.parser.parse(path)

    if statements is None:
        raise ValueError("%s failed to parse." % path)

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

    with open(path, "rb") as f:
        digest = hashlib.md5(f.read()).digest()

    return payload, digest


# ---------------------------------------------------------------- source ---

URM_MARKER = "rem URM_BEGIN"
PAYLOAD_MARKER = "rem PAYLOAD_BEGIN"


def read_embedded_urm():
    """
    Reads URM's archive back out of the .bat, where it sits base64 encoded
    between the two markers.
    """

    if not BAT or not os.path.exists(BAT):
        return None

    lines = []
    collecting = False

    with open(BAT, "r") as f:
        for line in f:
            line = line.strip()

            if line == URM_MARKER:
                collecting = True
                continue

            if line == PAYLOAD_MARKER:
                break

            if collecting and line:
                lines.append(line)

    if not lines:
        return None

    try:
        return base64.b64decode("".join(lines))
    except Exception:
        return None


def shadowing_copy():
    """
    Path to a loose, unpacked copy of URM sitting in game/, or None.

    Ren'Py looks on disk before it looks in an archive, so an unpacked
    0x52-URM/ directory - what UnRen leaves behind - wins over game/0x52_URM.rpa
    completely. URM still loads, so nothing looks wrong, but it is the old
    unpacked copy running and no change to the archive has any effect.
    """

    loose = os.path.join(BASE, "game", "0x52-URM")

    if os.path.isdir(loose):
        return loose

    return None


def move_shadowing_copy(loose):
    """
    Moves a loose copy out of game/ so the archive is used again. Returns the
    new location, or None if it could not be moved.
    """

    target = os.path.join(BASE, "0x52-URM.unpacked-copy")

    suffix = 2
    while os.path.exists(target):
        target = os.path.join(BASE, "0x52-URM.unpacked-copy-%d" % suffix)
        suffix += 1

    try:
        shutil.move(loose, target)
    except Exception:
        return None

    return target


def is_ours(contents):
    """
    True for an archive this tool or a URM+ build already wrote. It carries
    the add-on and the interface tweaks of its day, so installing from it
    would keep those - only a plain URM is a good starting point.
    """

    if "0x52-URM/zzz_urm_compat.rpyc" in contents:
        return True

    # A failed install can leave the tweaks without the add-on. The tweaks'
    # settings are all named urmc..., which plain URM never mentions.
    return any(b"urmc" in data for name, data in contents.items()
               if name.endswith(".x52"))


def choose_source(renpy):
    """
    Where to take URM from, in order of how deliberate the choice is:

      1. a 0x52_URM.rpa the user dropped next to the .bat - an explicit
         override, and how a newer URM gets used without a new .bat
      2. one already sitting in game/ in stock form - what a normal URM
         install leaves behind, possibly a newer version than the bundled one
      3. the copy embedded in this .bat

    Returns (label, contents) or (None, None).
    """

    beside = os.path.join(os.path.dirname(BAT or BASE), "0x52_URM.rpa")

    if os.path.exists(beside):
        try:
            contents = read_archive(beside)

            if not is_ours(contents):
                return "the copy next to this .bat", contents
        except Exception:
            pass

    installed = os.path.join(BASE, "game", "0x52_URM.rpa")

    if os.path.exists(installed):
        try:
            contents = read_archive(installed)
            scripts = [n for n in contents if n.endswith(".rpyc")]

            if not is_ours(contents) and scripts and all(
                    contents[n][:len(STOCK_HEADER)] == STOCK_HEADER for n in scripts):
                return "the copy already in game/", contents
        except Exception:
            pass

    blob = read_embedded_urm()

    if blob is None:
        return None, None

    temp = os.path.join(BASE, "_urmfix_source.rpa")

    try:
        with open(temp, "wb") as f:
            f.write(blob)

        return "the copy built into this .bat", read_archive(temp)
    finally:
        if os.path.exists(temp):
            os.remove(temp)


# --------------------------------------------------------------- actions ---

def game_is_open():
    """
    True when the game in BASE is running. A running program's .exe, and an
    archive the engine is reading, cannot be opened for writing on Windows -
    so try exactly that, without writing anything. Ren'Py 8 keeps its
    archives open while it runs, and writing over 0x52_URM.rpa then failed
    with a raw PermissionError (Obscure Affairs, 2026-11-18).
    """

    busy = [os.path.join(BASE, n) for n in os.listdir(BASE) if n.lower().endswith(".exe")]
    busy.append(os.path.join(BASE, "game", "0x52_URM.rpa"))

    for path in busy:
        # A read-only file refuses writing for its own reason; not "open".
        if not os.path.isfile(path) or not os.access(path, os.W_OK):
            continue
        try:
            fd = os.open(path, os.O_RDWR)
        except (IOError, OSError):
            return True
        os.close(fd)

    return False


def say_game_is_open():
    print()
    print("  ! The game is open. Close it, then run this again.")
    print("    Nothing was changed.")


def replace_file(src, dst):
    """os.replace, which Python 2 does not have."""

    if hasattr(os, "replace"):
        os.replace(src, dst)
        return
    if not os.path.exists(dst):
        os.rename(src, dst)
        return
    old = dst + ".urmold"
    if os.path.exists(old):
        os.remove(old)
    os.rename(dst, old)
    try:
        os.rename(src, dst)
    except Exception:
        os.rename(old, dst)
        raise
    os.remove(old)


def action_install():
    """
    Writes URM into game/, re-encoded to this build's script format if it uses
    one. The same path serves both kinds of game: on a normal build the
    re-encode is a no-op, so nothing about the archive changes except the
    hyperlink fix being added.

    Only ever writes game/0x52_URM.rpa. The game's own archives are never read
    or touched.
    """

    if game_is_open():
        say_game_is_open()
        return False

    renpy = load_engine()

    if renpy is None:
        print()
        print("  The engine will not load. If you patched it earlier, undo")
        print("  that with option 3 first.")
        return False

    header = getattr(renpy, "_RPYC_HEADER", STOCK_HEADER)
    pack = getattr(renpy, "compress_bytecode_stream", None)
    protected = header != STOCK_HEADER or pack is not None

    label, contents = choose_source(renpy)

    if contents is None:
        print()
        print("  Could not find URM to install - this .bat looks damaged.")
        print("  Re-download it, or put a 0x52_URM.rpa next to it.")
        return False

    print()
    print("  Installing from %s." % label)

    if protected:
        print("  This game encrypts its script cache, so URM is being")
        print("  re-encoded to match.")
    else:
        print("  This game reads add-on scripts as they come, so no")
        print("  re-encoding is needed.")

    # URM's screens are plain text inside its archive, so the interface tweaks
    # are literal edits made here, before anything is re-encoded.
    tweaks = load_ui_tweaks()

    if tweaks is not None:
        try:
            applied, skipped = tweaks["apply"](contents)

            for name, _note in applied:
                print("  Showing %s." % name)

            for name, why in skipped:
                print("  ! Skipped '%s' - %s" % (name, why))
        except Exception as e:
            print("  ! Could not apply the interface tweaks: %s" % e)

    converted = 0

    for name in sorted(contents):
        if not name.endswith(".rpyc"):
            continue

        slots = read_stock_slots(contents[name])

        if slots is None:
            continue

        contents[name] = write_native_rpyc(renpy, slots[0], slots[1])
        converted += 1

    if not converted:
        print()
        print("  That archive holds no stock script files. If it is already")
        print("  converted, URM is installed - just start the game.")
        return True

    try:
        temp = os.path.join(BASE, "_urmfix_hyperlink.rpy")

        with open(temp, "wb") as f:
            f.write(base64.b64decode(HYPERLINK_FIX_B64))

        try:
            name = "0x52-URM/zzz_urm_compat.rpyc"
            payload, digest = compile_rpy(renpy, temp, name[:-1])
            contents[name] = write_native_rpyc(renpy, [(1, payload)], digest)
            print("  Added the compatibility fixes.")
        finally:
            os.remove(temp)
    except Exception as e:
        # Stop, and leave the game exactly as it was. Writing URM without the
        # add-on used to be the fallback, but the screens are already tweaked
        # to use the add-on, and saves made with it refer to it: Freeloading
        # Family (Ren'Py 7.4.11) got that half install and its saves stopped
        # loading with "'StoreModule' object has no attribute ...".
        print()
        print("  ! Could not build URM+ for this game: %s" % e)
        print("    Nothing was changed - the game is exactly as it was.")
        print("    Please report this line; it names what went wrong.")
        return False

    target = os.path.join(BASE, "game", "0x52_URM.rpa")
    side = target + ".urmnew"

    # Written beside the old archive and swapped in whole, so a failure at
    # any point leaves the old one exactly as it was.
    try:
        write_archive(side, contents)
        replace_file(side, target)
    except (IOError, OSError) as e:
        try:
            if os.path.exists(side):
                os.remove(side)
        except (IOError, OSError):
            pass
        if game_is_open():
            say_game_is_open()
        else:
            print()
            print("  ! Could not write game\\0x52_URM.rpa: %s" % e)
            print("    Nothing was changed.")
        return False

    loose = shadowing_copy()

    if loose is not None:
        moved = move_shadowing_copy(loose)

        if moved is not None:
            print()
            print("  There was an unpacked copy of URM in game\\0x52-URM, left")
            print("  behind by an extraction tool. Ren'Py reads loose files")
            print("  before archives, so that copy was being used instead of")
            print("  URM's archive - and nothing written here would have had")
            print("  any effect. Moved it to %s." % os.path.basename(moved))
        else:
            print()
            print("  ! There is an unpacked copy of URM in game\\0x52-URM.")
            print("    Ren'Py reads loose files before archives, so that copy")
            print("    is used instead of the one just written. Delete or move")
            print("    game\\0x52-URM, then start the game.")

    print("  Wrote %s  (%d script files)"
          % (os.path.relpath(target, BASE), converted))

    print()
    print("  Done. Start the game - URM's tab is in the top-left corner.")
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

    loose = shadowing_copy()

    if loose is not None:
        print()
        print("  ! game\\0x52-URM exists - an unpacked copy of URM. Ren'Py")
        print("    reads loose files before archives, so this is what runs,")
        print("    not game\\0x52_URM.rpa. Installing cannot change anything")
        print("    until it is moved away. Option 1 moves it for you.")

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
    print("   URM compatibility helper")
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
        print("   1)  Install URM into this game        (start here)")
        print("   2)  Patch the engine instead")
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
    global BASE, BAT

    if len(argv) < 2:
        print("Run this through URM_fix.bat.")
        return 2

    BASE = os.path.abspath(argv[1])

    if len(argv) > 2:
        BAT = os.path.abspath(argv[2])

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
