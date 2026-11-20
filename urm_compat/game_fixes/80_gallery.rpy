# ---------------------------------------------------------------------------
# Gallery: unlock everything, or show only what you really unlocked
# ---------------------------------------------------------------------------
#
# One switch, two places: a row in URM's settings, and a small button in the
# corner of the main and game menus - which is where galleries live, and
# where URM's own overlay is never shown.
#
# Nothing is written. Turning it on changes what the game READS, not what it
# has stored, so turning it off is exact: your own unlocks are untouched,
# nothing is saved, and uninstalling URM leaves no trace.
#
# Games build galleries in a handful of ways, and each is covered:
#
#   * Ren'Py's Replay action and most hand-made galleries ask
#     renpy.seen_label / seen_image / seen_audio - those answer yes
#   * Ren'Py's own Gallery class - its buttons and images report unlocked
#   * persistent flags (persistent.scene3_unlocked, persistent.gallery
#     ["kim"], "x" in persistent.unlocked) - read as set. Which flags: every
#     persistent name the game's own gallery screens and gallery labels test,
#     plus names that say what they are (gallery, replay, unlock, scene,
#     memory, ending, cg...) and not what they aren't (settings, pages,
#     counters, anything of URM's or Ren'Py's own)
#
# And only where it cannot change the story: while a menu is open (main menu,
# game menu - the context Ren'Py marks _menu), while one of the game's gallery
# screens is showing, or while the game is inside a gallery label. A replay
# runs in a context of its own, so the scene you replay sees your real flags.
#
# When the switch is off, nothing here is installed at all: the persistent
# class and renpy.seen_* are exactly as the engine ships them.

init 999 python:

    import re as _urmg_re
    import sys as _urmg_sys

    _URMG_WORDS = _urmg_re.compile(
        r"galler|replay|unlock|memor|album|recollect|bonus|scene|seen|reward"
        r"|ending|(?:^|_)cgs?(?:\d|_|$)", _urmg_re.I)
    _URMG_NOT = _urmg_re.compile(
        r"urm|enable|setting|option|skip|mode|volume|patch|name|lang|font"
        r"|difficult|disable|^show_|^hide_|first|warning|intro|tutorial|page"
        r"|index|count|current|select|last|version|update|notif|sort|filter",
        _urmg_re.I)
    _URMG_SCREENS = _urmg_re.compile(
        r"galler|replay|memor|album|recollect|bonus|extra|(?:^|_)cgs?(?:$|_)"
        r"|scene_?(?:select|list|menu|room|viewer)", _urmg_re.I)
    _URMG_LABELS = _urmg_re.compile(r"galler|replay|memor|album|recollect|bonus|extras", _urmg_re.I)
    # Thief of Hearts 2 shows scr_end_replay during a replay; counting it would
    # unlock flags inside the replayed scene itself. URM's own URM_replay
    # dialogs are not the game's gallery either.
    _URMG_NOT_SCREENS = _urmg_re.compile(r"end_?replay|replay_?end|exit|^urm", _urmg_re.I)
    _URMG_PERSISTENT = _urmg_re.compile(r"persistent\.([A-Za-z_]\w*)")

    # Inside a Ren'Py 7 store, `str` is Ren'Py's compat str - unicode - but
    # Python 2's parser hands back string literals as byte strings. So text
    # types come from the real builtins, never from the store's names.
    try:
        import __builtin__ as _urm_builtins
        _urmg_strings = (_urm_builtins.str, _urm_builtins.unicode)
    except ImportError:
        _urmg_strings = (str,)

    try:
        x52URM.SettingsClass.defaultValues.setdefault("urmcGalleryAll", False)
        x52URM.SettingsClass.defaultValues.setdefault("urmcGalleryBadge", True)
    except Exception as error:
        print("URM+: gallery settings not registered (%s)" % (error,))

    class _URMGState(python_object):
        def __init__(self):
            self.on = False
            self.names = python_set()      # persistent names the gallery screens/labels test
            self.screens = python_list()   # the game's gallery screens, by name
            self.wanted = python_dict()    # name -> bool, cached
            self.unlock = python_dict()    # name -> the value that means unlocked
            self.labels = python_dict()    # current statement -> inside a gallery label?
            self.originals = python_dict() # (module id, function name) -> original
            self.scanned = False

    def _urmg_state():
        holder = x52URM.Var
        st = getattr(holder, "_urmgState", None)
        if st is None:
            st = _URMGState()
            holder._urmgState = st
        return st

    def _urmg_setting(name):
        try:
            return x52URM.Settings.get(name)
        except Exception:
            return None


    # ------------------------------------------------------------------
    # Where an unlock may apply
    # ------------------------------------------------------------------

    def _urmg_active():
        st = _urmg_state()
        if not st.on:
            return False
        try:
            ctx = renpy.game.context()
        except Exception:
            return False
        if getattr(ctx, "_menu", False):
            return True
        if _urmg_gallery_showing():
            return True
        current = getattr(ctx, "current", None)
        if current is None:
            return False
        try:
            return st.labels[current]
        except KeyError:
            pass
        # Only an answer the script index gave is remembered: asked before
        # the index is ready, or when reading it failed, it is asked again.
        inside = False
        known = False
        try:
            node = _urmsg_here()
            index = _urmi_index()
            if index is not None and index.state == "ready":
                if node is not None:
                    label = _urmp_scene(index, node, node.filename, node.linenumber)
                    inside = bool(label and _URMG_LABELS.search(label))
                known = True
        except Exception:
            inside = False
        if known:
            if len(st.labels) > 2000:
                st.labels.clear()
            st.labels[current] = inside
        return inside

    def _urmg_in_init(index, site):
        """A write in startup code (init / default), not one the story makes."""

        for parent, kind, _extra in _urmsg_climb(index.parent, index.nodes.get(site[2])):
            if isinstance(parent, renpy.ast.Init):
                return True
            if kind == "label":
                return False
        return index.label_at(site[0], site[1]) is None

    def _urmg_unlock_value(name):
        """
        The value that means "unlocked" for one persistent flag.

        Most galleries test `if persistent.x:` and the scene sets it True, but
        Thief of Hearts 2 tests `persistent.replay_x == False` and its scenes
        set False (True is written at startup, meaning locked). So the value
        is learnt from what the story itself writes when the scene is earned -
        writes outside init code - and True is only the fallback for a flag
        the script never writes.
        """

        st = _urmg_state()
        try:
            return st.unlock[name]
        except KeyError:
            pass
        index = _urmi_index()
        if index is None or index.state != "ready":
            return True
        counts = python_dict()
        try:
            for site, op, value, _t in index.writes.get("persistent." + name) or ():
                if op != "=" or not isinstance(value, bool):
                    continue
                if _urmg_in_init(index, site):
                    continue
                counts[value] = counts.get(value, 0) + 1
        except Exception:
            counts = python_dict()
        if not counts:
            unlocked = True
        elif len(counts) == 1:
            unlocked = python_list(counts)[0]
        else:
            unlocked = counts.get(True, 0) >= counts.get(False, 0)
        st.unlock[name] = unlocked
        return unlocked

    def _urmg_gallery_showing():
        for name in _urmg_state().screens[:12]:
            try:
                if renpy.get_screen(name):
                    return True
            except Exception:
                pass
        return False

    def _urmg_is_wanted(name):
        st = _urmg_state()
        try:
            return st.wanted[name]
        except KeyError:
            pass
        if name[:1] == "_":
            found = False
        elif name in st.names:
            found = True
        else:
            found = bool(_URMG_WORDS.search(name)) and not _URMG_NOT.search(name)
        st.wanted[name] = found
        return found


    # ------------------------------------------------------------------
    # What the game reads while it applies
    # ------------------------------------------------------------------

    class _URMGAllSet(python_set):
        def __contains__(self, item):
            return True

    class _URMGAllList(python_list):
        def __contains__(self, item):
            return True

    _URMG_NO_DEFAULT = python_object()

    class _URMGAllDict(python_dict):
        """
        A stored dict as an unlocked gallery reads it. Nested containers are
        unlocked too - The Lost Guardian keeps one list per girl,
        persistent.masterreplist["Jill"] - but only a dict of flags or of
        lists says yes to a key it does not have: a dict of tooltip strings
        next to it (persistent.replay_hints) must keep answering None.
        """

        def _fill(self):
            kinds = python_set()
            for value in python_dict.values(self):
                if value is True or value is False or value is None:
                    kinds.add("flag")
                elif isinstance(value, (python_list, python_set, frozenset, python_dict)):
                    kinds.add("coll")
                else:
                    return _URMG_NO_DEFAULT
            if kinds == python_set(("coll",)):
                return _URMGAllList()
            if not kinds or kinds == python_set(("flag",)):
                return True
            return _URMG_NO_DEFAULT

        def __contains__(self, key):
            if python_dict.__contains__(self, key):
                return True
            return self._fill() is not _URMG_NO_DEFAULT

        def __getitem__(self, key):
            try:
                value = python_dict.__getitem__(self, key)
            except KeyError:
                fill = self._fill()
                if fill is _URMG_NO_DEFAULT:
                    raise
                return fill
            if value is False or value is None:
                return True
            return _urmg_wrap(value)

        def get(self, key, default=None):
            try:
                return self[key]
            except KeyError:
                return default

    def _urmg_wrap(value):
        if isinstance(value, (_URMGAllSet, _URMGAllList, _URMGAllDict)):
            return value
        if isinstance(value, python_dict):
            return _URMGAllDict(value)
        if isinstance(value, python_list):
            return _URMGAllList(value)
        if isinstance(value, (python_set, frozenset)):
            return _URMGAllSet(value)
        return value

    _urmg_plain_get = object.__getattribute__

    def _urmg_getattribute(self, name):
        if name[:1] == "_":
            return _urmg_plain_get(self, name)
        try:
            value = _urmg_plain_get(self, name)
        except AttributeError:
            # Never set: the game's own Persistent.__getattr__ would say None.
            if _urmg_is_wanted(name) and _urmg_active():
                return _urmg_unlock_value(name)
            raise
        if value is True or value is False or value is None:
            if _urmg_is_wanted(name) and _urmg_active():
                unlocked = _urmg_unlock_value(name)
                if value is not unlocked:
                    return unlocked
        elif isinstance(value, (python_set, frozenset, python_list, python_dict)):
            if _urmg_is_wanted(name) and _urmg_active():
                return _urmg_wrap(value)
        return value

    def _urmg_seen_wrapper(original):
        def seen(*args, **kwargs):
            if _urmg_active():
                return True
            return original(*args, **kwargs)
        seen._urmg_original = original
        return seen

    def _urmg_check_wrapper(original):
        def check_unlock(self, *args, **kwargs):
            if _urmg_active():
                return True
            return original(self, *args, **kwargs)
        check_unlock._urmg_original = original
        return check_unlock


    # ------------------------------------------------------------------
    # Finding the game's gallery
    # ------------------------------------------------------------------

    def _urmg_walk(root, names):
        """Every persistent.x named anywhere in a screen's parsed source."""

        stack = python_list()
        stack.append(root)
        done = python_set()
        visited = 0
        while stack and visited < 200000:
            obj = stack.pop()
            visited += 1
            if isinstance(obj, _urmg_strings):
                if "persistent." in obj:
                    for name in _URMG_PERSISTENT.findall(obj):
                        names.add(name)
                continue
            if id(obj) in done:
                continue
            done.add(id(obj))
            if isinstance(obj, (python_list, tuple)):
                for item in obj:
                    stack.append(item)
                continue
            if isinstance(obj, python_dict):
                for item in obj.values():
                    stack.append(item)
                continue
            module = getattr(type(obj), "__module__", "") or ""
            if not module.startswith("renpy."):
                continue
            try:
                attrs = vars(obj)
            except TypeError:
                attrs = None
            if attrs:
                for item in attrs.values():
                    stack.append(item)
            source = getattr(obj, "source", None)
            if isinstance(source, _urmg_strings):
                stack.append(source)

    def _urmg_scan():
        st = _urmg_state()
        names = python_set()
        screens = python_list()

        registry = getattr(_urmg_sys.modules.get("renpy.display.screen"), "screens", None) or {}
        for key, screen in python_list(registry.items()):
            try:
                name = key[0] if isinstance(key, tuple) else key
                if not isinstance(name, _urmg_strings) or not _URMG_SCREENS.search(name):
                    continue
                if _URMG_NOT_SCREENS.search(name):
                    continue
                if name not in screens:
                    screens.append(name)
                ast = getattr(screen, "ast", None)
                if ast is not None:
                    _urmg_walk(ast, names)
            except Exception:
                continue

        try:
            index = _urmi_index()
            if index is not None and index.state == "ready":
                for name, bucket in index.reads.items():
                    if not name.startswith("persistent."):
                        continue
                    base = _urmg_re.split(r"[.\[]", name[11:], 1)[0]
                    for site, _op, _lit in bucket:
                        label = index.where(site)[0]
                        if label and _URMG_LABELS.search(label):
                            names.add(base)
                            break
        except Exception:
            pass

        # Ren'Py's own Gallery: every button and image reports unlocked.
        try:
            for value in python_list(renpy.store.__dict__.values()):
                buttons = getattr(value, "buttons", None)
                if type(value).__name__ != "Gallery" or not isinstance(buttons, python_dict):
                    continue
                for button in buttons.values():
                    things = python_list()
                    things.append(button)
                    for image in getattr(button, "images", None) or ():
                        things.append(image)
                    for thing in things:
                        cls = type(thing)
                        check = cls.__dict__.get("check_unlock")
                        if check is not None and not hasattr(check, "_urmg_original"):
                            cls.check_unlock = _urmg_check_wrapper(check)
        except Exception as error:
            print("URM+: Gallery class left as is (%s)" % (error,))

        for name in python_list(names):
            if name.startswith("_") or "urm" in name.lower():
                names.discard(name)
        st.names = names
        st.screens = screens
        st.wanted = python_dict()
        st.unlock = python_dict()
        # Done for good only once the script has been read: the names gallery
        # labels test come from the index, so a scan before that runs again.
        index = _urmi_index()
        st.scanned = index is not None and index.state == "ready"

    def _urmg_modules():
        found = python_list()
        for mod in (_urmg_sys.modules.get("renpy.exports"), renpy):
            if mod is not None and hasattr(mod, "seen_label") and mod not in found:
                found.append(mod)
        return found


    # ------------------------------------------------------------------
    # The switch
    # ------------------------------------------------------------------

    def _urmg_install():
        st = _urmg_state()
        if st.on:
            return
        _urmg_scan()
        st.on = True
        try:
            type(renpy.game.persistent).__getattribute__ = _urmg_getattribute
        except Exception as error:
            print("URM+: persistent gallery flags not unlocked (%s)" % (error,))
        for mod in _urmg_modules():
            for fname in ("seen_label", "seen_image", "seen_audio"):
                current = getattr(mod, fname, None)
                if current is None or hasattr(current, "_urmg_original"):
                    continue
                st.originals[(id(mod), fname)] = current
                setattr(mod, fname, _urmg_seen_wrapper(current))

    def _urmg_uninstall():
        st = _urmg_state()
        if not st.on:
            return
        st.on = False
        try:
            cls = type(renpy.game.persistent)
            if cls.__dict__.get("__getattribute__") is _urmg_getattribute:
                del cls.__getattribute__
        except Exception:
            pass
        for mod in _urmg_modules():
            for fname in ("seen_label", "seen_image", "seen_audio"):
                original = st.originals.pop((id(mod), fname), None)
                if original is not None:
                    setattr(mod, fname, original)

    def _urmg_apply():
        if _urmg_setting("urmcGalleryAll"):
            _urmg_install()
        else:
            _urmg_uninstall()

    def urmg_toggle():
        try:
            x52URM.Settings.set("urmcGalleryAll", not _urmg_setting("urmcGalleryAll"))
        except Exception as error:
            print("URM+: gallery switch failed (%s)" % (error,))
        _urmg_apply()
        renpy.restart_interaction()

    def urmg_badge_text():
        if _urmg_state().on:
            return "{urm_notl}URM gallery: {b}everything unlocked{/b}{/urm_notl}"
        return "{urm_notl}URM gallery: my unlocks{/urm_notl}"

    def _urmg_interact():
        try:
            _urmg_apply()
        except Exception:
            pass
        try:
            st = _urmg_state()
            if not st.scanned:
                index = _urmi_index()
                if index is not None and index.state == "ready":
                    _urmg_scan()
            # Ren'Py's menus, or one of the game's own gallery screens - Thief
            # of Hearts 2 opens its gallery from an in-game menu screen.
            where = getattr(renpy.game.context(), "_menu", False) or _urmg_gallery_showing()
            want = bool(where and _urmg_setting("urmcGalleryBadge") is not False
                        and renpy.has_screen("urmg_badge"))
            shown = renpy.get_screen("urmg_badge", layer=_urmi_layer)
            if want and not shown:
                renpy.show_screen("urmg_badge", _layer=_urmi_layer)
            elif shown and not want:
                renpy.hide_screen("urmg_badge", layer=_urmi_layer)
        except Exception:
            pass

    if _urmg_interact not in config.interact_callbacks:
        config.interact_callbacks.append(_urmg_interact)


