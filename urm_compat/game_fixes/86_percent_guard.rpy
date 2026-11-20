# ---------------------------------------------------------------------------
# Game bug guard: a stray % in a line of dialogue
# ---------------------------------------------------------------------------
#
# With config.old_substitutions on - the engine default through Ren'Py 7 -
# every line is run through Python's % formatting before it is shown, so a
# line the writer typed as "100% correct" has to be "100%% correct". Games
# ship with the single %, and the line stops the game with "%c requires int
# or char" (Freeloading Family 0.32, ver21.rpy:602 - the plain game, with no
# URM at all, fails the same way).
#
# Only a line whose formatting would fail is touched: its % signs are
# doubled, so it shows exactly as written. A line that formats - including
# one using %(name)s on purpose - is passed on as it is. A missing variable
# (KeyError) is a different bug and is left to raise.

init 999 python:

    def _urmpct_guard(what):
        if not renpy.config.old_substitutions:
            return what
        try:
            what % renpy.exports.tag_quoting_dict
        except (TypeError, ValueError):
            try:
                return what.replace("%", "%%")
            except Exception:
                return what
        except Exception:
            return what
        return what

    try:
        _urmpct_say = renpy.exports.say
        if not getattr(_urmpct_say, "_urmpct", False):
            def _urmpct_exports_say(who, what, *args, **kwargs):
                return _urmpct_say(who, _urmpct_guard(what), *args, **kwargs)
            _urmpct_exports_say._urmpct = True
            renpy.exports.say = _urmpct_exports_say
            renpy.say = _urmpct_exports_say
    except Exception as error:
        print("URM+: stray-percent guard not installed (%s)" % (error,))


