# Compatibility shim that lets a Ren'Py game load third-party .rpyc add-ons.
#
# Drop this into the game's renpy/ directory and call modcompat.apply() from
# renpy/bootstrap.py, just before it calls renpy.main.main(). install.py does
# both of those for you.
#
# Nothing here is specific to one game. Every build-specific value - the .rpyc
# header, the stream codec, the game's own hyperlink callback - is read from
# the running engine, so the same file works on a protected build and on a
# stock one.
#
#
# 1. Reading .rpyc files that a stock Ren'Py produced.
#
# Some builds write their script cache with a custom header and an extra
# encryption layer under the usual zlib compression. Script.read_rpyc_data then
# rejects any .rpyc that a stock Ren'Py produced, and the loader raises
# "Could not load from archive ..." on the add-on's files.
#
# The replacement below understands both layouts: it accepts the stock
# "RENPY RPC2" header alongside whatever header the build uses, and treats a
# slot that is not wrapped in the extra layer as plain zlib. Everything else -
# the slot table walk, archive decryption, the release-mode gate - is left
# alone, so the game's own files load exactly as before.
#
# This is deliberately kept out of script.py, loader.py and main.py. Builds
# that encrypt their script cache usually also hash-check those three files and
# exit silently if their bytes change. Patching them is what makes the game
# die with no window, no log and no traceback.
#
#
# 2. Keeping hyperlink protocol dispatch alive.
#
# Ren'Py routes a link by looking its protocol up in config.hyperlink_handlers.
# Add-ons register their dialogs there - URM uses the "URMVarDialog" and
# "URMLabelDialog" protocols for its variable and label editors.
#
# A game that sets config.hyperlink_callback (commonly to open its Patreon or
# Discord link in a browser) makes renpy/common/00compat react by replacing the
# whole style.default.hyperlink_functions tuple with
# (config.hyperlink_styler, config.hyperlink_callback, config.hyperlink_focus).
# That discards Ren'Py's own hyperlink_function, the only thing that consults
# config.hyperlink_handlers, and every link in the game then goes straight to
# webbrowser.open() whatever its protocol. Clicking a variable in the add-on
# asks the OS to find an application for a "urmvardialog:" URL.
#
# dispatch() below is Ren'Py's own routing logic with the game's callback kept
# as the fallback for anything that is not a registered protocol. It is
# installed in both places the engine can consult on a click - the style tuple
# and config.hyperlink_callback - and reinstalled once per interaction if
# anything replaces it. Registered protocols reach their handler; the game's
# own links behave exactly as the game intended.

from __future__ import division, absolute_import, with_statement, print_function, unicode_literals

import struct
import zlib

import renpy

# The header a stock Ren'Py writes at the start of a v2 .rpyc file. Builds that
# use a custom header keep the same length, so the slot table that follows sits
# at the same offset either way.
STOCK_RPYC_HEADER = b"RENPY RPC2"

# The game's own hyperlink callback, kept unwrapped so dispatch() can fall back
# to it without calling itself.
game_hyperlink_callback = None


def unpack_slot(data):
    """
    Decompresses the contents of one .rpyc slot. Slots written by a protected
    build may carry an extra stream layer; slots from a stock Ren'Py are plain
    zlib. Returns None if `data` is neither.
    """

    plain = None

    # Absent on an unmodified Ren'Py, where every slot is plain zlib.
    decompress_stream = getattr(renpy, "decompress_bytecode_stream", None)

    if decompress_stream is not None:
        try:
            plain = decompress_stream(data)
        except Exception:
            plain = None

    if plain is None:
        plain = data

    try:
        return zlib.decompress(plain)
    except Exception:
        return None


def read_rpyc_data(self, f, slot):
    """
    Reads the binary data from `slot` in a .rpyc (v1 or v2) file. Returns the
    data if the slot exists, or None if the slot does not exist.
    """

    header_data = f.read(1024)

    # Whatever header this build writes. Read from the engine rather than
    # hardcoded, so this works whatever value was packed into it.
    native = getattr(renpy.script, "RPYC2_HEADER", STOCK_RPYC_HEADER)

    if header_data[:len(native)] == native:
        header_length = len(native)
    elif header_data[:len(STOCK_RPYC_HEADER)] == STOCK_RPYC_HEADER:
        header_length = len(STOCK_RPYC_HEADER)
    else:
        header_length = None

    # Legacy path - a v1 file, which is a single slot and no header.
    if header_length is None:
        if slot != 1:
            return None

        f.seek(0)
        return unpack_slot(f.read())

    pos = header_length

    while True:
        header_slot, start, length = struct.unpack("III", header_data[pos:pos + 12])

        if slot == header_slot:
            break

        if header_slot == 0:
            return None

        pos += 12

    f.seek(start)
    return unpack_slot(f.read(length))


def split_target(target):
    """
    Splits a link target into its protocol and value, supplying the default
    protocol when the target does not name one.
    """

    if ":" not in target:
        default_protocol = getattr(
            renpy.config, "hyperlink_protocol", "call_in_new_context")
        target = default_protocol + ":" + target

    protocol, _, value = target.partition(":")

    return target, protocol, value


def log_unrouted(target, protocol, handlers):
    """
    Records a link that should have had a handler but did not.
    """

    try:
        import io, time

        with io.open("modcompat_unrouted_links.log", "a", encoding="utf-8") as f:
            f.write(u"%s  target=%r protocol=%r known=%r\n" % (
                time.strftime("%Y-%m-%d %H:%M:%S"), target, protocol,
                sorted(handlers)))
    except Exception:
        pass


def styler(target):

    return renpy.store.style.hyperlink_text


def dispatch(target):
    """
    Hands `target` to the handler registered for its protocol, and anything
    else to the game's own callback.
    """

    target, protocol, value = split_target(target)

    handlers = getattr(renpy.config, "hyperlink_handlers", None) or { }

    if protocol in handlers:
        return handlers[protocol](value)

    # An add-on protocol that reached the fallback means something replaced the
    # handler table. Leave a note rather than silently opening a browser - this
    # is the failure this shim exists to prevent, and it should never happen.
    if protocol.upper().startswith("URM"):
        log_unrouted(target, protocol, handlers)

    if game_hyperlink_callback is not None:
        return game_hyperlink_callback(target)

    try:
        import webbrowser
        webbrowser.open(target)
    except Exception:
        pass


dispatch.dispatches_protocols = True


def sensitive(target):

    target, protocol, value = split_target(target)

    table = getattr(renpy.config, "hyperlink_sensitive", None) or { }

    if protocol not in table:
        return True

    return table[protocol](value)


def install_hyperlink_dispatch():
    """
    Puts protocol dispatch in front of whatever callback the game installed.
    Runs after all init code, so it wins regardless of the order the init
    blocks ran in.
    """

    global game_hyperlink_callback

    existing = getattr(renpy.config, "hyperlink_callback", None)

    if existing is not None and not getattr(existing, "dispatches_protocols", False):
        game_hyperlink_callback = existing

    # Covers the case where 00compat copies this into the style tuple later,
    # on a second init pass.
    renpy.config.hyperlink_callback = dispatch

    style = renpy.store.style

    if style is None:
        return

    # Ren'Py's tuple is (styler, clicked, focus, sensitive). Keep the arity:
    # text.py indexes 2 for focus and 3 for sensitive.
    style.default.hyperlink_functions = (
        styler, dispatch, getattr(renpy.config, "hyperlink_focus", None), sensitive)

    renpy.style.rebuild()


def ensure_dispatch():
    """
    Reinstalls the dispatcher if something has replaced it.

    The style system is snapshotted before the game starts and rolled back to
    that snapshot by translation.change_language(), which a language selector
    triggers; 00compat can also overwrite the tuple on a second init pass.
    Rather than depend on any particular ordering, this runs once per
    interaction and only does real work when the tuple is not ours.
    """

    style = renpy.store.style

    if style is None:
        return

    functions = style.default.hyperlink_functions

    if functions and len(functions) > 1 and functions[1] is dispatch:
        return

    install_hyperlink_dispatch()


def wrap_run():
    """
    Arranges for install_hyperlink_dispatch to run after init code, by wrapping
    the main.run that main() calls once the script is loaded and initialised.
    """

    import renpy.main

    if getattr(renpy.main.run, "installs_dispatch", False):
        return

    original_run = renpy.main.run

    def run(restart):
        install_hyperlink_dispatch()

        if ensure_dispatch not in renpy.config.interact_callbacks:
            renpy.config.interact_callbacks.append(ensure_dispatch)

        return original_run(restart)

    run.installs_dispatch = True
    renpy.main.run = run


def apply():
    """
    Installs both fixes. Safe to call more than once - reload_all() brings the
    engine back to its stock state, so this runs on every restart.
    """

    import renpy.script

    if not getattr(renpy.script.Script.read_rpyc_data, "stock_rpyc_aware", False):
        read_rpyc_data.stock_rpyc_aware = True
        renpy.script.Script.read_rpyc_data = read_rpyc_data

    wrap_run()
