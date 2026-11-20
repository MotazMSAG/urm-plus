"""
Re-encodes an add-on's .rpa into the script format a protected Ren'Py build
expects, so the add-on loads with no changes to the engine at all.

    python repack.py "<game folder>" "<source .rpa>" [-o <output .rpa>]

    <game folder>   the folder holding renpy/ and game/ - the one with the .exe
    <source .rpa>   a pristine add-on archive, e.g. 0x52_URM.rpa
    -o              where to write; defaults to <game folder>/game/<same name>

Builds that encrypt their script cache write .rpyc files with their own header
and an extra stream layer under the zlib compression, and reject anything a
stock Ren'Py produced. This script converts in that direction: it reads the
add-on's stock .rpyc files and re-emits them the way the target build writes
its own, using that build's own header and packer. The engine then loads them
through its normal path.

The conversion is per-game. The header and the stream key are baked into each
build, so the output only works on the game it was produced for.

Everything that is not a .rpyc is copied through untouched - archive contents
are only decrypted if they carry the build's asset header, so plain files are
passed straight through by the loader.

Run this with the target game's own interpreter, since the key lives inside its
native module:

    "<game folder>/lib/py3-windows-x86_64/python.exe" repack.py ...
"""

from __future__ import print_function

import os
import pickle
import struct
import sys
import zlib

STOCK_HEADER = b"RENPY RPC2"

# write_rpyc_header reserves three slot entries of twelve bytes each.
SLOT_ENTRIES = 3
SLOT_TABLE_SIZE = SLOT_ENTRIES * 12

MD5_SIZE = 16


def load_engine(base):
    """
    Imports the target game's engine, which decrypts and configures its native
    module as a side effect.
    """

    base = os.path.abspath(base)
    os.chdir(base)
    sys.path.insert(0, base)

    import renpy

    return renpy


def read_archive(path):
    """
    Reads a stock RPA-2.0 or RPA-3.0 archive. Returns {name: bytes}.
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
            raise SystemExit("%s is not an RPA-2.0 or RPA-3.0 archive." % path)

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

                f.seek(start)
                chunks.append(prefix + f.read(length - len(prefix)))

            contents[name] = b"".join(chunks)

    return contents


def read_stock_slots(data):
    """
    Pulls the compressed payload of each slot out of a stock .rpyc, along with
    the md5 digest at the end. Returns (slots, digest) or None if `data` is not
    a stock v2 .rpyc.
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
    Emits a .rpyc the way the target build's write_rpyc_* methods would: its own
    header, a three entry slot table, then each slot's payload run through the
    build's stream packer.
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
    Compiles a .rpy into the slot 1 payload of a .rpyc, the same way
    Script.load_file does when it compiles a source file it has just read.

    Slot 1 holds the tree before static transforms; the engine applies those
    itself when it loads a file that has no slot 2.
    """

    import hashlib

    # The parser needs the whole engine, not just the package.
    renpy.import_all()

    from renpy.compat.pickle import dumps

    # The parser wants enough of a live engine to resolve line numbers.
    class FakeScript(object):
        record_pycode = False
        all_pycode = [ ]
        serial = 0

        def __getattr__(self, name):
            return None

    class FakeContext(object):
        init_phase = True

    script = FakeScript()
    renpy.game.script = script

    if not renpy.game.contexts:
        renpy.game.contexts = [ FakeContext() ]

    statements = renpy.parser.parse(path)

    if statements is None:
        raise SystemExit("%s failed to parse." % path)

    # Every node needs a unique name, the way load_file gives them one after
    # parsing. Without this the loader rejects the file as defining a name
    # twice. The name is what shows up in tracebacks, so use the path the file
    # will have inside the archive.
    renpy.script.Script.assign_names(script, statements, script_name)

    data = { }
    data['version'] = renpy.script_version
    data['key'] = 'unlocked'
    data['deferred_parse_errors'] = renpy.parser.deferred_parse_errors

    payload = zlib.compress(dumps((data, statements)), 3)

    with open(path, "rb") as f:
        digest = hashlib.md5(f.read()).digest()

    return payload, digest


def write_archive(path, contents):
    """
    Writes a stock RPA-3.0 archive. The container format is not what the build
    changed, so this stays standard.
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


def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))

    positional = []
    output = None
    rest = list(argv[1:])

    while rest:
        arg = rest.pop(0)

        if arg == "-o":
            output = rest.pop(0) if rest else None
        elif arg.startswith("-"):
            continue
        else:
            positional.append(arg)

    if not positional:
        print(__doc__)
        return 2

    base = os.path.abspath(positional[0])

    # Default to the add-on archive sitting next to this script.
    if len(positional) > 1:
        source = os.path.abspath(positional[1])
    else:
        source = os.path.join(here, "0x52_URM.rpa")

    if not os.path.exists(source):
        print("Cannot find the add-on archive: %s" % source)
        print()
        print("Put 0x52_URM.rpa next to this script, or pass its path as the")
        print("second argument.")
        return 1

    if not os.path.isdir(os.path.join(base, "game")):
        print("%s does not look like a Ren'Py game folder - no game/ in it." % base)
        return 1

    if output is None:
        output = os.path.join(base, "game", os.path.basename(source))
    output = os.path.abspath(output)

    renpy = load_engine(base)

    header = getattr(renpy, "_RPYC_HEADER", STOCK_HEADER)
    pack = getattr(renpy, "compress_bytecode_stream", None)

    print("Target: %s" % base)
    print("  engine:        %s" % renpy.version)
    print("  rpyc header:   %r%s" % (
        header, "" if header != STOCK_HEADER else "  (stock)"))
    print("  stream packer: %s" % ("present" if pack else "absent"))

    if header == STOCK_HEADER and pack is None:
        print()
        print("  This build reads stock .rpyc files already, so nothing needs")
        print("  re-encoding. Carrying on anyway to add the hyperlink fix.")

    contents = read_archive(source)
    print()
    print("Source: %s  (%d entries)" % (source, len(contents)))

    converted = 0
    copied = 0

    for name in sorted(contents):
        slots = read_stock_slots(contents[name]) if name.endswith(".rpyc") else None

        if slots is None:
            copied += 1
            continue

        contents[name] = write_native_rpyc(renpy, slots[0], slots[1])
        converted += 1

    print("  re-encoded %d .rpyc, copied %d other files" % (converted, copied))

    if not converted:
        print()
        print("No .rpyc files were found in the source. Is it really the")
        print("add-on's archive, and not one that has already been converted?")
        return 1

    if "--no-extras" not in argv:
        extra = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "hyperlink_fix.rpy")

        if os.path.exists(extra):
            name = "0x52-URM/zzz_hyperlink_fix.rpyc"
            payload, digest = compile_rpy(renpy, extra, name[:-1])
            contents[name] = write_native_rpyc(renpy, [(1, payload)], digest)
            print("  compiled and added %s" % name)

    write_archive(output, contents)
    print()
    print("Wrote %s" % output)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
