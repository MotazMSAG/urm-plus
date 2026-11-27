# Search engine, Find, Menu and Remembered.

init 999 python:

    # Four levels is the point past which a result list stops being readable,
    # whatever the cost; the setting is clamped to it rather than trusted.
    _URMC_DEPTH_CAP = 4
    _URMC_PATH_LIMIT = 20000

    # Parsed paths are cached in our memory (_URMMemory, 01_urm_door), so
    # the cache is not written into saves. That alone is not enough: in a
    # store, dict, list and set are themselves rebound to the rollback-tracked
    # Revertable kinds (renpy/minstore.py:37-50), and [] / {} literals are
    # rewritten to them as well. A tracked cache is copied into the rollback
    # log on the first change of every interaction - 20,000 entries at a time.
    # So every container here that outlives one call is a python_dict,
    # python_list or python_set, the untracked originals minstore keeps.
    _urm_kept("search_paths", python_dict)

    class _URMSearchKinds(python_object):
        """
        How a search tells what a value is: of(value) names its kind
        ("string", "boolean", "int", "float", "dict", ...), shown(kind) says
        whether a result row can show that kind, and guess(name) names the
        kind of a name that is not a plain path (an expression) or "unknown".
        The page that draws the results decides all three.
        """

        def __init__(self, of, shown, guess):
            self.of = of
            self.shown = shown
            self.guess = guess

    class _URMSearchAsk(python_object):
        """
        One search: what to look for and how.

        query  the text the player typed
        mode   what is searched: a key of _URMC_WALKS ("values"), or names
               ("variable names", and "labels", where nothing is looked up)
        opts   the switches, read when the walk needs them, by the names the
               search options use: searchInternalVars, searchPersistent,
               searchObjects, showUnsupportedVariables, useWildcardSearch
        kinds  a _URMSearchKinds
        depth  how many levels to walk into objects and dicts

        The three ways a search can be made better are methods, so a later
        search changes one of them and the walk stays as it is: hit() is
        what counts as a match (any true value; "quoted" for exact, typos
        forgiven otherwise), rank() orders the results by name (exact hits
        above forgiven ones, engine names sunk but kept), and a new kind of
        thing to search (story lines, choices, our flags) is a new entry in
        _URMC_WALKS. A filter such as "changed since the last choice", and
        what a result leads to (where a label can be reached from), work on
        the names _urmc_find gives and need nothing here.
        """

        def __init__(self, query, mode, opts, kinds, depth=1):
            self.query = query
            self._mode = mode
            self.opts = opts
            self.kinds = kinds
            self._depth = depth
            # The containers on the walk's stack right now (_urmc_descend).
            self.seen = python_set()

        @property
        def mode(self):
            return self._mode

        def depth(self):
            return self._depth

        def hit(self, text):
            """
            Does this text answer the query? A part of it, in any case; with
            wildcard search on, all of it, where * stands for any run of
            characters and ? for one.
            """

            query = self.query
            if self.opts.useWildcardSearch:
                # Imported here: a module kept in the store would itself
                # turn up in a search of internal variables.
                import re
                pattern = "".join(
                    ".*" if char == "*" else "." if char == "?"
                    else re.escape(char)
                    for char in query)
                return bool(re.match("^" + pattern + "$", text, re.IGNORECASE))
            return query.lower() in text.lower()

        def rank(self, name):
            """The sort key of a result's name (_urmc_rank)."""

            return _urmc_rank(name, (self.query or "").strip().lower())

    def _urmc_ident(word):
        """Is `word` a bare Python identifier?"""

        if not word:
            return False
        if not (word[0].isalpha() or word[0] == "_"):
            return False
        for char in word:
            if not (char.isalnum() or char == "_"):
                return False
        return True

    def _urmc_parse(name):
        """
        `name` as a walkable path, or None when it is an expression.

        ('a', attr) for a dotted step, ('k', key) for a subscript, with the
        store name first. Returning None for anything else is what keeps the
        eval fallback honest: a watched expression like len(items) is not a
        path and must still be evaluated.
        """

        length = len(name)
        if not length:
            return None

        end = 0
        while end < length and name[end] not in ".[":
            end += 1

        root = name[:end]
        if not _urmc_ident(root):
            return None

        parts = python_list((root,))
        index = end

        while index < length:
            char = name[index]

            if char == ".":
                index += 1
                end = index
                while end < length and name[end] not in ".[":
                    end += 1
                word = name[index:end]
                if not _urmc_ident(word):
                    return None
                parts.append(("a", word))
                index = end

            elif char == "[":
                end = name.find("]", index)
                if end < 0:
                    return None
                key = name[index + 1:end]
                if len(key) >= 2 and key[0] in "\"'" and key[-1] == key[0]:
                    parts.append(("k", key[1:-1]))
                elif key.isdigit():
                    parts.append(("k", int(key)))
                elif key[:1] == "-" and key[1:].isdigit():
                    parts.append(("k", int(key)))
                else:
                    return None
                index = end + 1

            else:
                return None

        return parts

    def _urmc_resolve(name):
        """
        (found, value) for a variable path, without eval.

        `found` is False both for a name that is not there and for one this
        cannot walk; the caller falls back to evaluating it for the second
        case, so the two never need telling apart here.
        """

        cache = _URMMemory.search_paths

        try:
            parts = cache[name]
        except KeyError:
            parts = _urmc_parse(name)
            if len(cache) < _URMC_PATH_LIMIT:
                cache[name] = parts

        if parts is None:
            return (False, None)

        store = renpy.store.__dict__
        root = parts[0]

        if root not in store:
            return (False, None)

        value = store[root]

        for kind, key in parts[1:]:
            try:
                value = getattr(value, key) if kind == "a" else value[key]
            except Exception:
                return (False, None)

        return (True, value)

    def _urmc_type(full, kinds):
        """
        (found, value, kind) for a name, walking rather than evaluating and
        falling back to kinds.guess only for names that are not plain paths.
        """

        found, value = _urmc_resolve(full)
        if found:
            return (True, value, kinds.of(value))

        try:
            return (False, None, kinds.guess(full))
        except Exception:
            return (False, None, "unknown")

    def _urmc_join(parent, child, kind):
        """A child's full name: parent["key"] in a dict, parent.name else."""

        if not parent:
            return child
        if kind == "dict":
            return parent + '["' + str(child) + '"]'
        return parent + "." + str(child)

    def _urmc_keys(value, kind):
        """The child names of a container, text keys only."""

        try:
            if kind == "dict":
                names = value.keys()
            else:
                names = value.__dict__.keys()
            return [key for key in names if isinstance(key, _URM_TEXT)]
        except Exception:
            return []

    def _urmc_container(kind, value, found):
        """
        'dict', 'object' or None - what this value's children are reached by.

        Lists are deliberately not containers here: their items have no names,
        which is why URM's name search never entered them either.
        """

        if not found:
            return None
        if kind == "dict":
            return "dict"
        if kind in ("string", "boolean", "int", "float"):
            return None
        try:
            if hasattr(value, "__dict__"):
                return "object"
        except Exception:
            pass
        return None

    def _urmc_num(text):
        """A number, or None. int first, so 3 stays 3 rather than 3.0."""

        text = text.strip()
        if not text:
            return None
        try:
            return int(text)
        except Exception:
            pass
        try:
            return float(text)
        except Exception:
            return None

    # Longest first: '>=' has to be tried before '>'.
    _URMC_OPS = (">=", "<=", "!=", "==", ">", "<")

    def _urmc_number(value, query):
        """
        Does a numeric variable satisfy the query?

        Equality is all URM offers, and equality is rarely what you want when
        hunting a stat. '>50', '<=10', '!=0' and '40..60' are read here; a
        query that is none of those is compared as before, so nothing that
        matched yesterday stops matching.
        """

        text = (query or "").strip()
        if not text:
            return False

        if ".." in text:
            low, _sep, high = text.partition("..")
            lower = _urmc_num(low)
            upper = _urmc_num(high)
            if lower is None or upper is None:
                return False
            if lower > upper:
                lower, upper = upper, lower
            return lower <= value <= upper

        for token in _URMC_OPS:
            if text.startswith(token):
                other = _urmc_num(text[len(token):])
                if other is None:
                    return False
                if token == ">=":
                    return value >= other
                if token == "<=":
                    return value <= other
                if token == "!=":
                    return value != other
                if token == "==":
                    return value == other
                if token == ">":
                    return value > other
                return value < other

        other = _urmc_num(text)
        return other is not None and value == other

    def _urmc_hit(ask, leaf, full):
        """
        Does this variable's name match?

        The leaf is tried first, which is URM's behaviour and keeps a bare
        "str" finding mc.str. The full dotted name is only tried when the
        query itself is dotted or subscripted, so this adds one string compare
        for queries that could not have matched at all before, and nothing
        otherwise. It costs no extra traversal, which is why it is not
        optional.
        """

        if ask.hit(leaf):
            return True

        query = ask.query
        if full != leaf and ("." in query or "[" in query):
            return ask.hit(full)

        return False

    def _urmc_name_hits(ask, varName, _depth=0, _full=None):
        """The full names under `varName` whose name answers the query."""

        if not isinstance(varName, _URM_TEXT):
            return None

        try:
            opts = ask.opts

            # The cheap string test before the type lookup, so an internal
            # variable is never resolved only to be dropped.
            if varName.startswith("_") and not opts.searchInternalVars:
                return None

            full = varName if _full is None else _full

            if full == "store":
                return None

            if ask.mode == "labels":
                if _urmc_hit(ask, varName, full):
                    return python_list((full,))
                return None

            kinds = ask.kinds
            found, value, kind = _urmc_type(full, kinds)

            if kind == "unknown" and not opts.showUnsupportedVariables:
                return None

            if (kind not in ("persistent", "store", "unknown")
                    and not kinds.shown(kind)):
                return None

            hit = _urmc_hit(ask, varName, full)

            if full == "persistent":
                if not opts.searchPersistent:
                    return None
                return _urmc_descend(ask, _urmc_name_hits, full, value,
                                     "object", _depth, ())

            container = _urmc_container(kind, value, found)

            if container and opts.searchObjects and _depth < ask.depth():
                # The container itself counts as a result when its own name
                # matched, recorded at its full path.
                return _urmc_descend(ask, _urmc_name_hits, full, value,
                                     container, _depth,
                                     (full,) if hit else ())

            return python_list((full,)) if hit else None

        except Exception as error:
            print('0x52: matchVarName failed for variable "{}". {}'.format(
                varName, error))

    def _urmc_value_hits(ask, varName, _depth=0, _full=None):
        """The full names under `varName` whose value answers the query."""

        if not isinstance(varName, _URM_TEXT):
            return None

        try:
            opts = ask.opts

            if varName.startswith("_") and not opts.searchInternalVars:
                return None

            full = varName if _full is None else _full

            # `store` is the store itself: walking it would list every
            # variable a second time, as store.X.
            if full == "store":
                return None

            kinds = ask.kinds
            found, value, kind = _urmc_type(full, kinds)

            if kind == "persistent":
                if not opts.searchPersistent:
                    return None
                if _depth >= ask.depth():
                    return None
                return _urmc_descend(ask, _urmc_value_hits, full, value,
                                     "object", _depth, ())

            if not kinds.shown(kind):
                return None

            if kind == "string":
                if ask.hit(value):
                    return python_list((full,))
                return None

            if kind == "boolean":
                want = (ask.query or "").strip().lower()
                if want not in ("true", "false"):
                    return None
                if bool(value) == (want == "true"):
                    return python_list((full,))
                return None

            if kind in ("int", "float"):
                if _urmc_number(value, ask.query):
                    return python_list((full,))
                return None

            container = _urmc_container(kind, value, found)

            if container and opts.searchObjects and _depth < ask.depth():
                return _urmc_descend(ask, _urmc_value_hits, full, value,
                                     container, _depth, ())

            return None

        except Exception as error:
            print('0x52: matchVarValue failed for variable "{}". {}'.format(
                varName, error))

    def _urmc_descend(ask, matcher, full, value, kind, depth, found):
        """
        `matcher` over one container's children, one level down.

        The id() set holds what is on the stack right now, and the marker is
        dropped again on the way out. mc.game.player is mc is a common shape,
        and marking the whole search instead would be the wrong guard twice
        over: the depth cap already bounds the walk, and an object two store
        variables both point at would have its children scanned under
        whichever name came first and silently skipped under the other.
        """

        seen = ask.seen
        marker = id(value)

        if marker in seen:
            return python_list(found) or None

        seen.add(marker)
        out = python_list(found)

        try:
            for child in _urmc_keys(value, kind):
                hits = matcher(ask, child, depth + 1,
                               _urmc_join(full, child, kind))
                if hits:
                    out.extend(hits)
        finally:
            seen.discard(marker)

        return out or None

    def _urmc_find(ask, names):
        """
        Every full name that answers `ask`, walking from each of `names`
        (store names, label names, or the names of earlier results) in their
        order.
        """

        matcher = _URMC_WALKS.get(ask.mode, _urmc_name_hits)
        out = python_list()
        for name in python_list(names):
            hits = matcher(ask, name)
            if hits:
                out.extend(hits)
        return out

    def _urmc_rank(name, query):
        """
        Sort key: exact leaf, then leaf prefix, then anything, then shortest.

        Results arrive in renpy.store.__dict__ order, which is arbitrary, so
        the thing you typed can sit anywhere in a hundred rows. Ordering an
        already-built list is one sort and changes nothing about what is in it.
        """

        low = (name or "").lower()
        leaf = low.rsplit(".", 1)[-1]

        if leaf == query or low == query:
            tier = 0
        elif leaf.startswith(query):
            tier = 1
        elif query in leaf:
            tier = 2
        else:
            tier = 3

        return (tier, len(low), low)

    def _urmc_ranked(ask, items, name_of):
        """
        `items` in ask.rank order of name_of(item). A value search keeps its
        order: there the name is not what was typed.
        """

        if (ask.query or "").strip() and len(items) > 1 and ask.mode != "values":
            return sorted(items, key=lambda item: ask.rank(name_of(item)))
        return items

    # What each mode walks, from one starting name; names by default. A new
    # kind of thing to search is a new entry here.
    _URMC_WALKS = python_dict(values=_urmc_value_hits)

    def _urmc_next_depth(mode, depth):
        """The level one more Deeper press would reach, or 0 for none."""

        if mode == "labels" or depth >= _URMC_DEPTH_CAP:
            # Labels are a flat namespace; there is nothing under them.
            return 0
        return depth + 1

    # Depth 1 matches URM's own one level ahead of the adapter, so it is
    # not lost if URM's search internals move.


# The page: our own Search page, the quick sheet and the full page
# (game_screens/50_search). It names nothing of URM's. The engine above
# answers one variable at a time for URM's page; ours asks once, when the
# sheet opens, for a catalog of the whole store (every name down to the
# depth cap, with its value then), and every key press filters that list.
# Lines and choices come from the script once per language. Values are
# read again for the rows on screen, so a row never shows a stale value.
#
#   * one box finds names and values: every word typed must be found in the
#     name at any depth ("mc str" finds mc.strength, "mc" shows what mc
#     holds), or the value must answer it (text that holds it, a number
#     equal to it or passing '>50', '40..60', yes/no for a switch);
#   * typos are forgiven: a word not found may be one letter off a word of
#     the name (a deletion on either side, which also covers a letter
#     changed or two swapped); "quoted" words are matched exactly and never
#     forgiven; every exact result ranks above every forgiven one;
#   * names the game's own script never touches (the engine's, persistent)
#     sink into one folded group, still found and still editable;
#   * "changed since": the values at your last choice, at a moment you
#     marked, and at the last load or start.
#
# Everything here lives in our memory (_URMMemory, never saved): a catalog
# holds live game objects, and a save or the rollback log must not.

init 999 python:

    import numbers as _urmcp_numbers

    _URMCP_LIMIT = 20000        # names in a catalog, at most
    _URMCP_ROWS = 200           # rows drawn for one group, at most
    # Rows built at first, then a screenful more each time the list is
    # scrolled near its end: the rows on screen and a spare. Every row built
    # is words laid out on the click's frame, the most of its time with a
    # graphics card (FINDINGS "With a real graphics card the card is not
    # the cost"): 24 rows were 66-72 ms a key on Thief of Hearts 2.
    _URMCP_ROOM = 8             # the quick sheet: rows of about 100 px
    _URMCP_ROOM_PAGE = 16       # the full page: one-line rows of 64 px
    _URMCP_SNAPS = 12           # choices remembered for "since your last choice"
    # Store names of the engine's, for when the script index is not ready
    # yet to say which names the game's own script uses.
    _URMCP_ENGINE = frozenset((
        "config", "gui", "style", "preferences", "build", "achievement", "iap",
        "layout", "theme", "director", "bubble", "updater", "ui", "im", "anim",
        "renpy", "store", "persistent", "main_menu", "save_name", "suppress_overlay",
        "mouse_visible", "default_mouse", "nvl_list", "menu_window", "narrator",
        "centered", "vcentered", "extend", "adv", "nvl", "name_only", "predict_menu",
        "nvl_variant", "nvl_narrator", "nvl_menu", "menu", "save_name"))

    class _URMCPEntry(python_object):
        """One name of the catalog. owners: the names it sits under, outermost
        first; words: the whole name in lower case, its parts split by
        spaces; kind: text, bool, int, float, none, list, dict, object."""

        __slots__ = ("path", "owners", "leaf", "kind", "value", "internal",
                     "words", "depth", "inside")

        def __init__(self, path, owners, leaf, kind, value, internal, depth):
            self.path = path
            self.owners = owners
            self.leaf = leaf
            self.kind = kind
            self.value = value
            self.internal = internal
            self.depth = depth
            self.inside = 0
            self.words = _urmcp_norm(path)

    class _URMCPLine(python_object):
        """A line or a choice of the script, in the language played."""

        __slots__ = ("kind", "node", "seen_node", "text", "low")

        def __init__(self, kind, node, seen_node, text):
            self.kind = kind
            self.node = node
            self.seen_node = seen_node
            self.text = text
            self.low = text.lower()

    _URMCP_SHOWN = _urmsg_re.compile(r"\[([A-Za-z_][\w.]*)")

    class _URMCPState(python_object):
        """What the page shows and holds, kept for the run."""

        def __init__(self):
            self.query = u""
            self.pill = "all"            # all vars lines choices flags changed labels engine
            self.tab = "find"            # the full page's menu
            self.alert_tab = "alerts"
            self.alert_room = _URMCP_ROOM_PAGE
            self.full = False            # the full page is open
            self.since = "choice"        # choice, mark, load
            self.catalog = None          # python_list of _URMCPEntry
            self.by_path = python_dict()
            self.vocab = None            # deletion -> words, for forgiving typos
            self.lines = None            # (language, python_list of _URMCPLine)
            self.lines_vocab = None      # the lines' words for forgiving typos, made with them
            self.labels = None           # (the script, ((label, its words), ...))
            self.room = _URMCP_ROOM      # rows built now (_urmcp_room)
            self.reading = False         # the catalog is being read behind the open window (urmcp_open)
            self.search_language = None  # language last requested by the open Search
            self.language_reading = False
            self.catalog_stamp = None    # _urmcp_stamp() when st.catalog was built
            self.result_query = None     # query st.result was computed for
            self.shown = python_set()    # names the lines show ([name])
            self.notes = python_dict()   # path -> its note, until a value changes
            self.result = None           # _URMCPResult of the query
            self.selected = None         # a path, or a line
            self.selected_line = None    # the exact line or choice behind the selected position
            self.editing = None          # a path
            self.edit_text = u""
            self.edit_error = None
            self.undo = None             # (path, old value) after a switch
            self.creating = False        # the new-variable form is open
            self.new_name = u""
            self.new_text = u""
            self.new_error = None
            self.deleting = None         # a path being asked about
            self.engine_open = False
            self.more = False            # the quick sheet shows Labels and Engine
            self.open_paths = python_set()   # objects unfolded with no query
            self.snaps = python_dict()   # "mark", "load": (python_dict) of values
            self.choice_snaps = python_list()  # [[the menu's log entry, values, past]]
            self.log_front = None        # the rollback log's first entry, when last looked

    def _urmcp_state():
        return _urm_kept("search_page", _URMCPState)

    # ---- names and words

    def _urmcp_norm(text):
        """A name or a query as plain lower-case words: mc.stats["luck"] ->
        mc stats luck."""

        out = python_list()
        for char in (text or u"").lower():
            out.append(char if char.isalnum() else u" ")
        return u" ".join(u"".join(out).split())

    def _urmcp_ours(name):
        """Our own names: never listed. (URM's store objects are modules
        and classes, which the page never lists either: _urmcp_kind.)"""

        return name.lower().startswith(("urm", "_urm"))

    def _urmcp_kind(value):
        """What a value is to the page, or None for what it never lists
        (functions, classes, modules, the engine's own objects). A switch is
        tested before a number: True is an int to Python."""

        if value is None:
            return "none"
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, _URM_TEXT):
            return "text"
        if isinstance(value, _urmcp_numbers.Integral):
            return "int"
        if isinstance(value, _urmcp_numbers.Real):
            return "float"
        if isinstance(value, dict):
            return "dict"
        if isinstance(value, (list, tuple, set, frozenset)):
            return "list"
        try:
            if callable(value):
                return None
            # The player's settings (preferences.transitions...) are an
            # object of the engine's own, listed like the game's.
            if isinstance(value, type(renpy.game.preferences)):
                return "object"
            module = getattr(type(value), "__module__", "") or ""
            if module.startswith("renpy") or module in ("builtins", "__builtin__"):
                return None
            if hasattr(value, "__dict__"):
                return "object"
        except Exception:
            pass
        return None

    def _urmcp_game_names():
        """The store names the game's own script reads, writes or declares
        (not the engine's, not URM's, not ours), or None while the script
        index is not ready."""

        index = _urmi_index()
        if index is None or index.state != "ready":
            return None
        found = getattr(index, "_urmcp_game", None)
        if found is not None:
            return found
        found = python_set()
        for table in (index.reads, index.writes):
            for name, records in table.items():
                for record in records:
                    site = record[0]
                    if not _urmsg_engine_file(site[0] or u""):
                        found.add(name.split(".")[0].split("[")[0])
                        break
        for name, record in index.declared.items():
            if not _urmsg_engine_file(record[0][0] or u""):
                found.add(name.split(".")[0].split("[")[0])
        index._urmcp_game = found
        return found

    # ---- the catalog

    # What the engine's walk calls a value (its kinds), for the page.
    _URMCP_ENGINE_KIND = python_dict((
        ("text", "string"), ("bool", "boolean"), ("int", "int"), ("float", "float"),
        ("dict", "dict"), ("list", "list"), ("object", "object"), ("none", "none")))

    def _urmcp_engine_kind(value):
        if value is renpy.store.__dict__.get("persistent", False):
            return "persistent"
        return _URMCP_ENGINE_KIND.get(_urmcp_kind(value), "other")

    class _URMCPSwitches(python_object):
        """The page's search switches, by the names the engine reads."""

        searchInternalVars = False
        searchPersistent = True
        searchObjects = True
        showUnsupportedVariables = False
        useWildcardSearch = False

    _URMCP_KINDS = _URMSearchKinds(_urmcp_engine_kind, lambda kind: kind != "other",
                                   lambda name: "unknown")

    class _URMCPEvery(_URMSearchAsk):
        """The engine's own walk, asked for every name down to the depth
        cap: the page's catalog is that walk, done once."""

        def __init__(self):
            _URMSearchAsk.__init__(self, u"", "variable names", _URMCPSwitches(),
                                   _URMCP_KINDS, _URMC_DEPTH_CAP)

        def hit(self, text):
            return True

    def _urmcp_build():
        """Every name of the store worth a row, as a fresh catalog."""

        for said in _urmcp_build_steps():
            if isinstance(said, _URMWorkDone):
                return said.result

    def _urmcp_build_steps():
        """_urmcp_build, a step after each store name walked (the engine's
        walk, _urmc_find, one name at a time); ends with the catalog in a
        _URMWorkDone (the worker reads it behind an opening Search)."""

        game = _urmcp_game_names()
        made = _urmcp_made()
        store = renpy.store.__dict__
        names = sorted(name for name in python_list(store.keys())
                       if isinstance(name, _URM_TEXT)
                       and name != "store" and not _urmcp_ours(name))
        out = python_list()
        by_path = python_dict()
        ask = _URMCPEvery()
        paths = python_list()
        total = float(max(1, len(names)))
        for at, name in enumerate(names):
            if len(paths) >= _URMCP_LIMIT:
                break
            paths.extend(_urmc_find(ask, (name,)))
            yield 0.5 * at / total
        for at, path in enumerate(paths[:_URMCP_LIMIT]):
            if not (at + 1) % 500:
                yield 0.5 + 0.5 * at / len(paths)
            parts = _urmc_parse(path)
            if not parts:
                continue
            found, value = _urmc_resolve(path)
            if not found:
                continue
            kind = "object" if path == "persistent" else _urmcp_kind(value)
            if kind is None:
                continue
            root = parts[0]
            internal = (root == "persistent" or
                        ((root not in game and root not in made) if game is not None
                         else (root in _URMCP_ENGINE)))
            keys = python_list(u"%s" % (part[1],) for part in parts[1:])
            owners = (tuple((root,)) + tuple(keys[:-1])) if keys else ()
            leaf = keys[-1] if keys else root
            entry = _URMCPEntry(path, owners, leaf, kind, value, internal, len(keys))
            out.append(entry)
            by_path[path] = entry
        # how many names each object holds, one level down
        for entry in out:
            if entry.owners:
                parent = by_path.get(_urmcp_parent(entry))
                if parent is not None:
                    parent.inside += 1
        yield _URMWorkDone(out)

    def _urmcp_parent(entry):
        """The path of what holds an entry."""

        parts = _urmc_parse(entry.path)
        path = parts[0]
        for kind, key in parts[1:-1]:
            path = path + (u".%s" % key if kind == "a" else u'["%s"]' % key)
        return path

    def _urmcp_values(catalog):
        """The values of a catalog's plain names: a snapshot."""

        out = python_dict()
        for entry in catalog:
            if entry.kind in ("text", "bool", "int", "float", "none"):
                out[entry.path] = entry.value
        return out

    def _urmcp_refresh():
        """A new catalog, from the store as it is now."""

        _urmcp_take(_urmcp_build())
        _urmcp_run()

    def _urmcp_stamp():
        fn = globals().get("_urm_store_stamp")
        return fn() if fn is not None else None

    def _urmcp_take(catalog):
        """A catalog just read becomes the page's."""

        st = _urmcp_state()
        st.catalog = catalog
        st.by_path = python_dict((entry.path, entry) for entry in catalog)
        st.vocab = None
        st.notes = python_dict()
        st.catalog_stamp = _urmcp_stamp()
        st.result_query = None

    def _urmcp_now(path):
        """(found, value) of a name as it is now."""

        return _urmc_resolve(path)

    # ---- lines and choices, in the language played

    def _urmcp_say_text(node):
        what = getattr(node, "what", None)
        if isinstance(what, _URM_TEXT):
            return what
        return None

    def _urmcp_played(node):
        """The line a player of the language being played reads for this
        line of the original script, and the line the engine marks seen."""

        for twin in _urmsg_played_twins(node) or ():
            text = _urmcp_say_text(twin)
            if text is None:
                for inner in getattr(twin, "block", None) or ():
                    text = _urmcp_say_text(inner)
                    if text is not None:
                        return text, inner
                continue
            return text, twin
        return _urmcp_say_text(node), node

    def _urmcp_choice_text(text):
        try:
            return renpy.translate_string(text)
        except Exception:
            return text

    def _urmcp_language():
        try:
            return renpy.game.preferences.language
        except Exception:
            return None

    def _urmcp_clear_story_selection(st):
        if st.selected is not None and st.selected.startswith(u"line:"):
            st.selected = None
            st.selected_line = None

    def _urmcp_lines():
        """The script's lines and choices, read once per language (the
        worker reads them at start-up: _urmcp_lines_ahead)."""

        st = _urmcp_state()
        language = _urmcp_language()
        if st.lines is not None and st.lines[0] == language:
            return st.lines[1]
        # the start-up read still running: finished now, not read twice
        _urm_work_finish("search lines")
        if st.lines is None or st.lines[0] != language:
            for _step in _urmcp_lines_steps(language):
                pass
        return st.lines[1]

    def _urmcp_lines_steps(language):
        """_urmcp_lines' read, a step every 2000 statements; keeps the lines
        in the page's state, and the typo table of their words."""

        st = _urmcp_state()
        out = python_list()
        shown = python_set()
        say = getattr(renpy.ast, "Say", None)
        menu = getattr(renpy.ast, "Menu", None)
        stmts = _urmi_all_stmts()
        total = float(max(1, len(stmts)))
        for at, node in enumerate(stmts):
            if not (at + 1) % 2000:
                yield at / total
            try:
                if _urmsg_engine_file(getattr(node, "filename", u"") or u""):
                    continue
                if say is not None and isinstance(node, say):
                    if _urmsg_default_twin(node) is not node:
                        continue        # a line of a translation: its original stands for it
                    text, seen = _urmcp_played(node)
                    if text and u"[" in text:
                        shown.update(_URMCP_SHOWN.findall(text))
                    if text:
                        out.append(_URMCPLine("line", node, seen, _urmp_plain(text, 400).replace(u"{{", u"{")))
                elif menu is not None and isinstance(node, menu):
                    for item in node.items:
                        if item[2] is None or not isinstance(item[0], _URM_TEXT):
                            continue
                        text = _urmp_plain(_urmcp_choice_text(item[0]), 400).replace(u"{{", u"{")
                        if text:
                            out.append(_URMCPLine("choice", node, node, text))
            except Exception:
                continue
        words = python_set()
        for at, line in enumerate(out):
            if not (at + 1) % 2000:
                yield 1.0
            words.update(_urmcp_norm(line.text).split())
        vocab = python_dict()
        for word in words:
            _urmcp_vocab_add(vocab, word)
        if st.lines is not None and st.lines[0] != language:
            _urmcp_clear_story_selection(st)
            st.result_query = None
        st.lines = (language, out)
        st.lines_vocab = vocab
        st.shown = shown

    def _urmcp_lines_ahead():
        """The worker's job: the lines in the language played, at start-up."""

        language = _urmcp_language()
        st = _urmcp_state()
        if st.lines is None or st.lines[0] != language:
            for said in _urmcp_lines_steps(language):
                yield said
        yield _URMWorkDone()

    try:
        _urm_work_slices("search lines", _urmcp_lines_ahead)
    except Exception as error:
        print("MRM: search reads the lines when first opened (%s)" % (error,))

    def _urmcp_scene_label(node):
        """The scene a statement is in, once the index can tell us."""

        index = _urmi_index()
        if index is None or index.state != "ready" or node is None:
            return None
        try:
            return _urmsg_label_of(index, node)
        except Exception:
            return None

    def _urmcp_scene(node):
        """The scene a statement is in, said plainly, or None."""

        label = _urmcp_scene_label(node)
        return _urmm_pretty(label.split(".")[-1]) if label else None

    def _urmcp_seen(line):
        try:
            seen = renpy.game.persistent._seen_ever
        except Exception:
            return None
        return _urm_was_seen(line.seen_node.name, seen)

    # ---- typos

    def _urmcp_deletes(word):
        out = python_set((word,))
        for i in range(len(word)):
            out.add(word[:i] + word[i + 1:])
        return out

    def _urmcp_vocab_add(vocab, word):
        if len(word) < 3 or word.isdigit():
            return
        for cut in _urmcp_deletes(word):
            bucket = vocab.get(cut)
            if bucket is None:
                vocab[cut] = bucket = python_list()
            bucket.append(word)

    def _urmcp_vocab():
        """Every word of the names, by its one-letter deletions: two words a
        letter apart share one. The lines' words are a table of their own,
        made once with the lines (st.lines_vocab): a word in both is in both
        tables, and _urmcp_forgiven asks both."""

        st = _urmcp_state()
        if st.vocab is not None:
            return st.vocab
        words = python_set()
        for entry in st.catalog or ():
            words.update(entry.words.split())
        vocab = python_dict()
        for word in words:
            _urmcp_vocab_add(vocab, word)
        st.vocab = vocab
        return vocab

    def _urmcp_forgiven(token):
        """The words a typed word may have meant: one letter off. A word of
        three letters or fewer is never forgiven."""

        if len(token) < 4 or token.isdigit():
            return ()
        _urmcp_lines()
        tables = (_urmcp_vocab(), getattr(_urmcp_state(), "lines_vocab", None) or python_dict())
        out = python_set()
        for cut in _urmcp_deletes(token):
            for vocab in tables:
                for word in vocab.get(cut, ()):
                    if word != token:
                        out.add(word)
        return out

    # ---- the query

    class _URMCPAsk(_URMSearchAsk):
        """A query of our page, read once: its words, whether it is quoted,
        what it asks of a value. The engine's ask, with the switches and
        kinds of the page; tier() is what counts as a match here, and how
        well (the page filters its catalog with it)."""

        def __init__(self, text):
            _URMSearchAsk.__init__(self, text or u"", "variable names", _URMCPSwitches(),
                                   _URMCP_KINDS, _URMC_DEPTH_CAP)
            text = (text or u"").strip()
            self.text = text
            self.quoted = len(text) >= 2 and text[0] == text[-1] and text[0] in u"\"'"
            if len(text) >= 2 and text[0] == u"\u201c" and text[-1] == u"\u201d":
                self.quoted = True
            if self.quoted:
                text = text[1:-1]
            self.phrase = text.lower()
            self.norm = _urmcp_norm(text)
            self.tokens = tuple(self.norm.split())
            self.empty = not self.phrase.strip()
            low = self.phrase.strip()
            self.switch = (True if low in (u"true", u"on", u"yes")
                           else False if low in (u"false", u"off", u"no") else None)
            self.numeric = _urmcp_number_test(low)
            self._near = python_dict()

        def near(self, token):
            found = self._near.get(token)
            if found is None:
                found = () if self.quoted else _urmcp_forgiven(token)
                self._near[token] = found
            return found

        def tier(self, entry):
            """How well a catalog entry answers (_urmcp_tier)."""

            return _urmcp_tier(self, entry)

    def _urmcp_number_test(text):
        """Is the text a number, or a test of one ('>50', '40..60')?"""

        if ".." in text:
            low, _sep, high = text.partition("..")
            return _urmc_num(low) is not None and _urmc_num(high) is not None
        for token in _URMC_OPS:
            if text.startswith(token):
                return _urmc_num(text[len(token):]) is not None
        return _urmc_num(text) is not None

    def _urmcp_value_hit(ask, kind, value):
        if ask.empty:
            return False
        if kind == "text":
            return len(ask.phrase) >= 2 and ask.phrase in value.lower()
        if kind == "bool":
            return ask.switch is not None and bool(value) == ask.switch
        if kind in ("int", "float"):
            return ask.numeric and _urmc_number(value, ask.phrase)
        return False

    def _urmcp_name_tier(ask, words, leaf):
        """How well a name (its words, its last part's) answers: 0 exactly,
        1 its last part starts with the last word typed, 2 every word found,
        4 forgiven (a typo), None not at all."""

        if ask.empty or not ask.norm:
            return None
        if ask.quoted:
            if leaf == ask.norm or words == ask.norm:
                return 0
            return 2 if ask.norm in words else None
        if leaf == ask.norm or words == ask.norm:
            return 0
        if all(token in words for token in ask.tokens):
            return 1 if leaf.startswith(ask.tokens[-1]) else 2
        parts = words.split()
        for token in ask.tokens:
            if token in words:
                continue
            near = ask.near(token)
            if not near or not any(part in near for part in parts):
                return None
        return 4

    def _urmcp_tier(ask, entry):
        """How well an entry answers: its name's tier, else 3 for its value;
        every forgiven name (4) ranks below every value."""

        if ask.empty:
            return None
        tier = _urmcp_name_tier(ask, entry.words, _urmcp_norm(entry.leaf))
        if tier is not None and tier < 3:
            return tier
        if _urmcp_value_hit(ask, entry.kind, entry.value):
            return 3
        return tier

    def _urmcp_line_tier(ask, line):
        if ask.empty or len(ask.phrase.strip()) < 2:
            return None
        if ask.phrase in line.low:
            return 0
        if ask.quoted or not ask.tokens:
            return None
        if all(token in line.low for token in ask.tokens):
            return 2
        for token in ask.tokens:
            if token in line.low:
                continue
            near = ask.near(token)
            if not near or not any(word in line.low for word in near):
                return None
        return 4

    class _URMCPResult(python_object):
        """What a query found, by group. vars, engine and changed hold
        entries, lines and choices their places in _urmcp_lines(), labels
        and flags their names."""

        def __init__(self):
            self.vars = python_list()
            self.engine = python_list()
            self.lines = python_list()
            self.choices = python_list()
            self.line_corpus = None     # the corpus those positions were found in
            self.labels = python_list()
            self.flags = python_list()
            self.changed = python_list()

        def counts(self):
            current = _urmcp_result_language(_urmcp_state(), self)
            return python_dict((
                ("vars", len(self.vars)), ("lines", len(self.lines) if current else 0),
                ("choices", len(self.choices) if current else 0), ("flags", len(self.flags)),
                ("labels", len(self.labels)), ("changed", len(self.changed)),
                ("engine", len(self.engine))))

        def found(self):
            story = len(self.lines) + len(self.choices) if _urmcp_result_language(_urmcp_state(), self) else 0
            return len(self.vars) + story + len(self.flags)

    def _urmcp_result_language(st, result):
        return result.line_corpus is None or (st.lines is not None
                and result.line_corpus is st.lines[1] and st.lines[0] == _urmcp_language())

    def _urmcp_rank(tier, entry):
        return (tier, entry.depth, len(entry.path), entry.path.lower())

    def _urmcp_since_values():
        """The values of the moment "changed since" compares with, or None."""

        if _urm_work_state("search snap") in ("waiting", "running"):
            _urm_work_finish("search snap")
        st = _urmcp_state()
        if st.since == "choice":
            return _urmcp_last_choice()
        return st.snaps.get(st.since)

    def _urmcp_changed(entry, before):
        if entry.kind not in ("text", "bool", "int", "float", "none"):
            return False
        if entry.path not in before:
            return True
        old = before[entry.path]
        try:
            return type(old) is not type(entry.value) or old != entry.value
        except Exception:
            return True

    def _urmcp_find(text):
        """Everything that answers `text`, ranked, by group."""

        for said in _urmcp_find_steps(text):
            if isinstance(said, _URMWorkDone):
                return said.result

    def _urmcp_labels():
        """(label, its words) of the script's own labels, read once per
        script (it was read again at every key: 80 ms on Being a DIK)."""

        st = _urmcp_state()
        script = getattr(renpy.game, "script", None)
        found = getattr(st, "labels", None)
        if found is not None and found[0] is script:
            return found[1]
        try:
            every = renpy.get_all_labels()
        except Exception:
            every = ()
        out = tuple((label, _urmcp_norm(label)) for label in every
                    if isinstance(label, _URM_TEXT) and not label.startswith("_"))
        st.labels = (script, out)
        return out

    def _urmcp_flags(index):
        """(name, its words) of the index's flags, sorted, once per index."""

        found = getattr(index, "_urmcp_flags", None)
        if found is None:
            found = tuple((name, _urmcp_norm(name)) for name in sorted(index.flags.keys()))
            index._urmcp_flags = found
        return found

    def _urmcp_find_steps(text):
        """_urmcp_find, a step every 2000 lines; ends with its result in a
        _URMWorkDone (the worker runs it after a pause in typing)."""

        st = _urmcp_state()
        ask = _URMCPAsk(text)
        out = _URMCPResult()
        catalog = st.catalog or ()
        before = _urmcp_since_values()

        if ask.empty:
            # Nothing typed: the game's own names, objects folded.
            for entry in catalog:
                if entry.internal:
                    continue
                if entry.depth == 0 or _urmcp_unfolded(entry):
                    out.vars.append(entry)
        else:
            vars_ = python_list()
            engine = python_list()
            for entry in catalog:
                if entry.kind in ("dict", "object"):
                    continue
                tier = ask.tier(entry)
                if tier is None:
                    continue
                (engine if entry.internal else vars_).append((_urmcp_rank(tier, entry), entry))
            vars_.sort(key=lambda pair: pair[0])
            engine.sort(key=lambda pair: pair[0])
            out.vars = python_list(pair[1] for pair in vars_)
            out.engine = python_list(pair[1] for pair in engine)

            lines = python_list()
            choices = python_list()
            if len(ask.phrase.strip()) >= 2:
                out.line_corpus = _urmcp_lines()
                for place, line in enumerate(out.line_corpus):
                    if not (place + 1) % 1000:
                        yield 0.5
                    tier = _urmcp_line_tier(ask, line)
                    if tier is None:
                        continue
                    (choices if line.kind == "choice" else lines).append((tier, len(line.text), place))
            lines.sort(key=lambda item: item[:2])
            choices.sort(key=lambda item: item[:2])
            out.lines = python_list(item[2] for item in lines)
            out.choices = python_list(item[2] for item in choices)

            labels = python_list()
            for label, words in _urmcp_labels():
                if ask.tokens and all(token in words for token in ask.tokens):
                    labels.append((0 if words == ask.norm else 2, len(label), label))
            labels.sort()
            out.labels = python_list(item[2] for item in labels)

            index = _urmi_index()
            if index is not None and index.state == "ready":
                for name, words in _urmcp_flags(index):
                    if ask.tokens and all(token in words for token in ask.tokens):
                        out.flags.append(name)

        if before is not None:
            pool = catalog if ask.empty else (out.vars + out.engine)
            out.changed = python_list(entry for entry in pool
                                      if not entry.internal or not ask.empty
                                      if _urmcp_changed(entry, before))
        yield _URMWorkDone(out)

    def _urmcp_unfolded(entry):
        st = _urmcp_state()
        owners = entry.owners
        if not owners:
            return True
        path = owners[0]
        if path not in st.open_paths:
            return False
        # every owner on the way down is open
        for i in range(1, len(owners)):
            child = st.by_path.get(path)
            kind = child.kind if child is not None else "object"
            path = _urmc_join(path, owners[i], "dict" if kind == "dict" else "object")
            if path not in st.open_paths:
                return False
        return True

    def _urmcp_run():
        st = _urmcp_state()
        if getattr(st, "reading", False):
            # asked before the catalog's read behind the open window got
            # there: it is read now, once
            _urm_work_finish("search open")
        if st.catalog is None:
            st.result = _URMCPResult()
            return
        st.result = _urmcp_find(st.query)

    # ---- what a page does

    def urmcp_open(full=False):
        """Open the quick sheet (or the full page): instant and warm when the
        store has not changed since the last catalog; otherwise the window
        opens at once and its catalog builds behind it between frames."""

        st = _urmcp_state()
        st.full = bool(full)
        st.search_language = _urmcp_language()
        st.language_reading = False
        if not st.full and st.tab in ("changes", "alerts"):
            st.tab = "find"
            st.pill = "all"
        st.editing = None
        st.undo = None
        st.edit_error = None
        _urmcp_rows_top()
        if st.tab == "alerts":
            _urmcp_alert_top()
        _urm_work_cancel("search open")
        _urm_work_cancel("search")

        stamp = _urmcp_stamp()
        warm = (st.catalog is not None and stamp is not None
                and getattr(st, "catalog_stamp", None) == stamp)
        if warm:
            st.reading = False
            if (st.result is None or st.result_query != st.query
                    or not _urmcp_result_language(st, st.result)):
                st.result = _urmcp_find(st.query)
                st.result_query = st.query
            st.room = _urmcp_screenful()
        else:
            st.reading = True
            st.result = None

            def job():
                for said in _urmcp_build_steps():
                    if isinstance(said, _URMWorkDone):
                        _urmcp_take(said.result)
                        break
                    yield said
                if st.language_reading:
                    return
                for said in _urmcp_find_steps(st.query):
                    yield said

            def then(result):
                st.reading = False
                if st.language_reading:
                    return          # the queued query will use this catalog
                st.result = result if result is not None else _URMCPResult()
                st.result_query = st.query
                st.room = _urmcp_screenful()
                renpy.restart_interaction()

            _urm_work_slices("search open", job, then, first=True)

        renpy.show_screen("urmcp_page" if st.full else "urmcp_sheet", _layer="screens")
        renpy.hide_screen("urmcp_sheet" if st.full else "urmcp_page", layer="screens")
        renpy.restart_interaction()

    def urmcp_close():
        st = _urmcp_state()
        if st.creating or st.deleting is not None:
            st.creating = False
            st.new_error = None
            st.deleting = None
            renpy.restart_interaction()
            return
        if st.editing is not None:
            st.editing = None
            st.edit_error = None
            renpy.restart_interaction()
            return
        renpy.hide_screen("urmcp_sheet", layer="screens")
        renpy.hide_screen("urmcp_page", layer="screens")
        _urm_work_cancel("search open")
        _urm_work_cancel("search")
        st.reading = False
        st.language_reading = False
        renpy.restart_interaction()

    def urmcp_pumping():
        return urmcp_reading() or _urm_work_state("search") in ("waiting", "running")

    def urmcp_toggle():
        if renpy.get_screen("urmcp_sheet", layer="screens") or renpy.get_screen("urmcp_page", layer="screens"):
            st = _urmcp_state()
            st.editing = None
            st.creating = False
            st.deleting = None
            urmcp_close()
        else:
            urmcp_open()

    def urmcp_query(text):
        st = _urmcp_state()
        st.query = text
        st.undo = None
        st.editing = None
        st.room = _urmcp_screenful()
        _urm_work_cancel("search")
        st.language_reading = False
        _urmcp_run()
        st.result_query = text
        renpy.restart_interaction()

    _URMCP_INLINE_BUDGET = 0.0035  # seconds spent searching inline before yielding to worker

    def urmcp_typed(text):
        """A key in the search box: runs inline up to _URMCP_INLINE_BUDGET
        so normal stores update in the same frame with zero debounce; only
        searches that exceed the budget continue in worker slices."""

        import time
        st = _urmcp_state()
        st.query = text
        st.undo = None
        st.editing = None
        _urm_work_cancel("search")

        gen = None
        if not (st.reading or st.language_reading) and st.catalog is not None:
            gen = _urmcp_find_steps(text)
            end = time.time() + _URMCP_INLINE_BUDGET
            try:
                while True:
                    said = next(gen)
                    if isinstance(said, _URMWorkDone):
                        st.result = said.result
                        st.result_query = text
                        st.room = _urmcp_screenful()
                        renpy.restart_interaction()
                        return
                    if time.time() >= end:
                        break
            except StopIteration:
                st.result = _URMCPResult()
                st.result_query = text
                st.room = _urmcp_screenful()
                renpy.restart_interaction()
                return

        _urmcp_queue_query(st, text, gen)
        renpy.restart_interaction()

    def _urmcp_queue_query(st, text, gen=None):
        """Finish a typed query in slices, reading its new language first if needed."""

        language = _urmcp_language()

        def job():
            while st.reading:
                yield _URM_WORK_WAIT
            if _urmcp_language() != language:
                return
            if st.catalog is None:
                yield _URMWorkDone(None)
                return
            if st.language_reading and (st.lines is None or st.lines[0] != language):
                for said in _urmcp_lines_steps(language):
                    yield said
                    if _urmcp_language() != language:
                        return
            steps = gen if gen is not None else _urmcp_find_steps(text)
            for said in steps:
                yield said

        def then(result):
            if st.query != text or _urmcp_language() != language:
                return
            if result is None or st.catalog is None:
                if st.language_reading:
                    st.language_reading = False
                    renpy.restart_interaction()
                return
            st.language_reading = False
            st.result = result
            st.result_query = text
            st.room = _urmcp_screenful()
            renpy.restart_interaction()

        _urm_work_slices("search", job, then, first=True)

    def _urmcp_refresh_language(st):
        language = _urmcp_language()
        if language == st.search_language:
            return
        if not (renpy.get_screen("urmcp_sheet", layer="screens") or
                renpy.get_screen("urmcp_page", layer="screens")):
            return
        st.search_language = language
        _urmcp_clear_story_selection(st)
        st.result = _URMCPResult()
        st.result_query = None
        st.language_reading = True
        _urm_work_cancel("search lines")
        _urmcp_queue_query(st, st.query)

    def urmcp_pill(pill):
        """Show one group of what was found (the search found them all)."""
        st = _urmcp_state()
        st.pill = pill
        st.undo = None
        st.room = _urmcp_screenful()
        if st.result is None:
            _urmcp_run()
        renpy.restart_interaction()

    def urmcp_tab(tab):
        st = _urmcp_state()
        st.tab = tab
        st.pill = "changed" if tab == "changes" else "all"
        st.editing = None
        _urmcp_rows_top()
        if tab == "alerts":
            _urmcp_alert_top()
        if st.result is None:
            _urmcp_run()
        renpy.restart_interaction()

    def urmcp_since(since):
        st = _urmcp_state()
        st.since = since
        _urmcp_run()
        renpy.restart_interaction()

    def urmcp_mark():
        st = _urmcp_state()
        st.snaps["mark"] = _urmcp_values(st.catalog if st.catalog is not None else _urmcp_build())
        st.since = "mark"
        _urmcp_run()
        renpy.restart_interaction()

    def urmcp_select(what):
        st = _urmcp_state()
        st.selected = None if st.selected == what and not st.full else what
        st.selected_line = _urmcp_row_line(st, st.selected)
        st.undo = None
        renpy.restart_interaction()

    def urmcp_fold(path):
        st = _urmcp_state()
        if path in st.open_paths:
            st.open_paths.discard(path)
        else:
            st.open_paths.add(path)
        if _URMCPAsk(st.query).empty or st.result is None:
            _urmcp_run()        # what is unfolded shows only with nothing typed
        renpy.restart_interaction()

    def urmcp_engine_fold():
        st = _urmcp_state()
        st.engine_open = not st.engine_open
        renpy.restart_interaction()

    def urmcp_full():
        urmcp_open(True)

    # ---- doorway navigation (via 01_urm_door only; never imports peer UI)

    def _urmcp_close_now():
        """Close Search cleanly (leaving any active edit/create/delete form)
        before handing control to another hub entry or value sheet."""

        st = _urmcp_state()
        st.editing = None
        st.creating = False
        st.deleting = None
        urmcp_close()

    def _urmcp_entry_named(name):
        try:
            for entry in _urm_entries():
                if entry.name == name:
                    return entry
        except Exception:
            pass
        return None

    def urmcp_can_open(name):
        return _urmcp_entry_named(name) is not None

    def urmcp_go(name):
        _urmcp_close_now()
        _urm_open(name)
        return None

    def urmcp_can_map():
        return urmcp_can_open("story_line")

    def urmcp_open_map():
        return urmcp_go("story_line")

    def urmcp_can_sheet():
        return bool(_urm_value_viewable())

    def urmcp_open_sheet(path):
        _urm_value_view(path, None)
        return None

    def urmcp_alert_rows():
        entry = _urmcp_entry_named("alerts")
        if entry is None:
            return python_list()
        return python_list((w, s) for w, s, _a in (entry.items or ()))

    def urmcp_alert_stop(words):
        entry = _urmcp_entry_named("alerts")
        if entry is not None:
            for w, _s, action in (entry.items or ()):
                if w == words:
                    if action is not None:
                        action()
                    renpy.restart_interaction()
                    break
        return None

    def urmcp_alert_tab():
        return _urmcp_state().alert_tab

    def urmcp_select_alert_tab(tab):
        # A Function action's return value would end the current dialogue.
        _urmcp_state().alert_tab = tab
        _urmcp_alert_top()
        renpy.restart_interaction()

    def urmcp_mute_rows():
        return _urm_path_mutes()

    def urmcp_mute_remove(key):
        _urm_path_unmute(key)

    def urmcp_alert_room():
        return _urmcp_state().alert_room

    def _urmcp_alert_top():
        _urmcp_state().alert_room = _URMCP_ROOM_PAGE
        urmcp_alert_adj.change(0)

    def _urmcp_alert_scrolled(value):
        adj = urmcp_alert_adj
        if value > 0 and value >= adj.range - 2 * adj.page:
            _urmcp_state().alert_room += _URMCP_ROOM_PAGE
            renpy.restart_interaction()

    urmcp_alert_adj = ui.adjustment(changed=_urmcp_alert_scrolled)

    # ---- editing

    def urmcp_edit(path):
        """Open the box on a value, filled with what it holds now."""

        st = _urmcp_state()
        found, value = _urmcp_now(path)
        if not found or _urmcp_kind(value) not in ("text", "int", "float", "none"):
            return
        st.editing = path
        st.selected = path
        st.edit_text = u"" if value is None else (u"%s" % (_urm_number(value) if _urm_isnum(value) else value))
        st.edit_error = None
        st.undo = None
        renpy.restart_interaction()

    def urmcp_edit_text(text):
        st = _urmcp_state()
        st.edit_text = text
        st.edit_error = None
        renpy.restart_interaction()

    def _urmcp_parse_value(kind, text):
        """(ok, value) for the text typed into the box of a `kind` value."""

        raw = text
        text = text.strip()
        if kind == "int":
            try:
                return True, int(text)
            except Exception:
                try:
                    number = float(text)
                except Exception:
                    return False, u"A whole number, please"
                if number == int(number):
                    return True, int(number)
                return True, number
        if kind == "float":
            try:
                return True, float(text)
            except Exception:
                return False, u"A number, please"
        if kind == "none":
            number = _urmc_num(text)
            return True, (number if number is not None else raw)
        return True, raw

    def _urmcp_write(path, value):
        """Set a name, at any depth: the leaf is set on what holds it, as the
        game's own code would set it, so rollback records it."""

        parts = _urmc_parse(path)
        if parts is None:
            return False
        if len(parts) == 1:
            setattr(renpy.store, parts[0], value)
            return True
        store = renpy.store.__dict__
        if parts[0] not in store:
            return False
        owner = store[parts[0]]
        for kind, key in parts[1:-1]:
            owner = getattr(owner, key) if kind == "a" else owner[key]
        kind, key = parts[-1]
        if kind == "a":
            setattr(owner, key, value)
        else:
            owner[key] = value
        return True

    # A freeze reads and writes names with this engine's own walker
    # (01_urm_door); our Sets go through the core's _urm_set.
    _urm_walker(_urmc_resolve, _urmcp_write)

    def _urmcp_after_write(path, value):
        st = _urmcp_state()
        entry = st.by_path.get(path)
        if entry is not None:
            entry.value = value
            entry.kind = _urmcp_kind(value) or entry.kind
        st.notes = python_dict()
        _urmcp_run()
        renpy.restart_interaction()

    def urmcp_commit():
        """Enter: set the value in the box."""

        st = _urmcp_state()
        path = st.editing
        if path is None:
            return
        found, old = _urmcp_now(path)
        if not found:
            st.editing = None
            renpy.restart_interaction()
            return
        ok, value = _urmcp_parse_value(_urmcp_kind(old), st.edit_text)
        if not ok:
            st.edit_error = value
            renpy.restart_interaction()
            return
        try:
            _urm_set(path, value)
        except Exception as error:
            st.edit_error = u"The game refused it: %s" % (error,)
            renpy.restart_interaction()
            return
        st.editing = None
        st.edit_error = None
        _urmcp_after_write(path, value)

    def urmcp_step(delta):
        """- and +: the number in the box, one down or up."""

        st = _urmcp_state()
        number = _urmc_num(st.edit_text)
        if number is None:
            number = 0
        number += delta
        st.edit_text = u"%s" % (_urm_number(number),)
        st.edit_error = None
        renpy.restart_interaction()

    def urmcp_fill(value):
        """A value the game checks for, into the box: never set."""

        st = _urmcp_state()
        st.edit_text = u"%s" % (_urm_number(value) if _urm_isnum(value) else value,)
        st.edit_error = None
        renpy.restart_interaction()

    def urmcp_switch(path):
        """A yes/no value flips with one click; Undo puts it back."""

        st = _urmcp_state()
        found, old = _urmcp_now(path)
        if not found or not isinstance(old, bool):
            return
        _urm_set(path, not old)
        st.editing = None
        _urmcp_after_write(path, not old)
        st.undo = (path, old)

    def urmcp_undo():
        st = _urmcp_state()
        if st.undo is None:
            return
        path, old = st.undo
        _urm_set(path, old)
        st.undo = None
        _urmcp_after_write(path, old)

    # ---- a new variable, and deleting one (the user's ticket, 2026-11-23)
    #
    # Made and removed as the game's own code would ($ name = value, del), so
    # rollback has them and a save made at once carries them (_urm_set,
    # _urm_keep). The names we made are kept in the player's persistent data
    # (never in a save, and not in the store) so that a later run still knows
    # which names it may delete: a name the game's script never touches is
    # the engine's, and the engine's is never deleted. Only a plain store
    # name goes: never one inside an object, one starting with _, one of the
    # engine's (_URMCP_ENGINE), persistent, the player's settings or ours.

    _URMCP_NAME = _urmsg_re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
    _urmcp_sys = __import__("sys")
    _urmcp_builtins = _urmcp_sys.modules.get("builtins") or _urmcp_sys.modules.get("__builtin__")

    def _urmcp_made():
        """The names we made, a tuple, for this game."""
        found = getattr(_urm_persistent(), "_urm_made", None)
        return found if isinstance(found, tuple) else ()

    def _urmcp_made_put(names):
        _urm_persistent()._urm_made = tuple(_urm_plain_words(n) for n in names)

    def _urmcp_name_error(name):
        """None when `name` may be made, else why not, in words."""
        if not name:
            return u"Give it a name"
        if not _URMCP_NAME.match(name):
            return u"Letters, numbers and _ only, starting with a letter"
        if (__import__("keyword").iskeyword(name) or name in ("True", "False", "None")
                or hasattr(_urmcp_builtins, name)):
            return u"Python already uses that word"
        if name.lower().startswith("urm") or name in _URMCP_ENGINE:
            return u"That name is kept for the engine"
        if name in renpy.store.__dict__:
            return u"There is already a variable called %s" % name
        return None

    def _urmcp_new_value(text):
        """(kind, value) of what was typed for a new variable: True or False
        a switch, None nothing, a number, "words" in quotes or plain words;
        (None, None) for nothing typed."""
        raw = text.strip()
        low = raw.lower()
        if not raw:
            return None, None
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in u"\"'":
            return "text", raw[1:-1]
        if low in (u"true", u"false"):
            return "bool", low == u"true"
        if low == u"none":
            return "none", None
        number = _urmc_num(raw) if any(c.isdigit() for c in raw) else None
        if number is not None:
            return ("int" if isinstance(number, int) else "float"), number
        return "text", raw

    def urmcp_new_words():
        """What the value typed will be, said under the box."""
        kind, _value = _urmcp_new_value(_urmcp_state().new_text)
        return {"int": u"A whole number", "float": u"A number with decimals", "bool": u"A true/false value",
                "none": u"Nothing yet (empty)", "text": u"Words"}.get(kind, u"")

    def urmcp_new_open():
        st = _urmcp_state()
        st.creating = True
        st.new_name = u""
        st.new_text = u""
        st.new_error = None
        st.editing = None
        st.deleting = None
        renpy.restart_interaction()

    def urmcp_new_set(field, text):
        st = _urmcp_state()
        setattr(st, field, text)
        st.new_error = None
        renpy.restart_interaction()

    def urmcp_new_name(text):
        urmcp_new_set("new_name", text)

    def urmcp_new_text(text):
        urmcp_new_set("new_text", text)

    def urmcp_new_commit():
        """Create: the variable goes into the game, and the page shows it."""
        st = _urmcp_state()
        name = st.new_name.strip()
        error = _urmcp_name_error(name)
        kind, value = _urmcp_new_value(st.new_text)
        if error is None and kind is None:
            error = u"Type a value: words, a number, True or False"
        if error is None:
            try:
                if not _urm_set(name, value):
                    error = u"The game refused it"
            except Exception as why:
                error = u"The game refused it: %s" % (why,)
        if error is not None:
            st.new_error = error
            renpy.restart_interaction()
            return
        _urmcp_made_put(_urmcp_made() + (name,))
        st.creating = False
        st.new_error = None
        st.pill = "all"
        st.query = name
        _urmcp_refresh()
        st.selected = name
        renpy.restart_interaction()

    def urmcp_can_delete(path):
        """A plain name of the game's own, or one we made: never one inside
        an object, one with a leading _, the engine's, persistent, the
        player's settings or ours (which the catalog never holds)."""
        entry = _urmcp_state().by_path.get(path)
        return (entry is not None and not entry.internal and not entry.depth
                and _URMCP_NAME.match(path) is not None and path not in _URMCP_ENGINE
                and not _urmcp_ours(path) and path in renpy.store.__dict__)

    def urmcp_deleting():
        return _urmcp_state().deleting

    def urmcp_delete(path):
        """Delete: asks first; nothing is removed yet."""
        st = _urmcp_state()
        if not urmcp_can_delete(path):
            return
        st.deleting = path
        st.editing = None
        renpy.restart_interaction()

    def urmcp_delete_no():
        _urmcp_state().deleting = None
        renpy.restart_interaction()

    def urmcp_delete_words(path):
        """The one question before a variable goes."""
        words = u"Delete %s? It is removed from the game." % (urmcp_title(path),)
        index, reads = _urmcp_reads(path)
        if reads:
            words += u" The story still reads it: the game may stop with an error."
        return words

    def urmcp_delete_yes():
        st = _urmcp_state()
        path = st.deleting
        st.deleting = None
        if path is None or not urmcp_can_delete(path):
            renpy.restart_interaction()
            return
        if _urm_is_remembered(path):
            _urm_forget(path)           # a freeze of it ends too
        elif _urm_is_frozen(path):
            _urm_unfreeze(path)
        try:
            delattr(renpy.store, path)
        except Exception as why:
            st.edit_error = u"The game refused it: %s" % (why,)
            renpy.restart_interaction()
            return
        _urm_keep(path)
        if "_urm_stmt_bump" in globals():
            _urm_stmt_bump()
        _urmcp_made_put(n for n in _urmcp_made() if n != path)
        st.selected = None
        _urmcp_refresh()
        renpy.restart_interaction()

    # ---- what a value matters for (the one coloured note), and the values
    # the game checks for (the chips under the box)

    def _urmcp_reads(path):
        index = _urmi_index()
        if index is None or index.state != "ready":
            return None, ()
        return index, index.reads.get(path) or ()

    def _urmcp_target(op, literal):
        """The value that passes `op literal`, as urm_checks gives it."""

        if isinstance(literal, bool) or not _urm_isnum(literal):
            return literal if op == "==" else None
        if op in ("==", ">=", "<="):
            return literal
        if op == ">":
            return literal + 1 if isinstance(literal, int) else literal
        if op == "<":
            return literal - 1 if isinstance(literal, int) else literal
        return None

    def _urmcp_passes(value, op, literal):
        try:
            if op == "==":
                return value == literal
            if op == "!=":
                return value != literal
            if op == ">=":
                return value >= literal
            if op == ">":
                return value > literal
            if op == "<=":
                return value <= literal
            if op == "<":
                return value < literal
        except Exception:
            return None
        return None

    def _urmcp_where(index, site):
        try:
            label = index.where(site)[0]
        except Exception:
            return None
        if not label:
            return None
        return _urmm_pretty(label.split(".")[-1])

    def _urmcp_read_at_all(path):
        """True when the story's tests read this name, False when they never
        do, None when that cannot be told (_urmsg_checked)."""

        try:
            checked = _urmsg_checked()
        except Exception:
            return None
        if checked is None or checked == _URMSG_ANY:
            return None
        parts = _urmc_parse(path)
        if not parts:
            return None
        keys = python_list((("g", parts[0]),))
        for kind, key in parts[1:]:
            if kind == "a":
                keys = python_list((("a", key),))
        return any(key in checked for key in keys)

    def _urmcp_in_text(entry):
        """Is the name put into the dialogue ([name])?"""

        _urmcp_lines()
        return entry.path in _urmcp_state().shown

    def urmcp_note(path):
        """The one coloured note of a variable's row: (words, tone), or None
        when nothing can be said."""

        st = _urmcp_state()
        found, value = _urmcp_now(path)
        if not found:
            return None
        kind = _urmcp_kind(value)
        index, reads = _urmcp_reads(path)
        if index is None:
            return None
        if reads:
            goals = python_list()
            switches = python_list()
            others = python_list()
            for site, op, literal in reads:
                if op in ("truthy", "falsy"):
                    switches.append((site, op))
                elif op in ("==", "!=", ">=", ">", "<=", "<"):
                    goals.append((site, op, literal))
                else:
                    others.append(site)
            if kind in ("int", "float"):
                unmet = python_list()
                met = python_list()
                for site, op, literal in goals:
                    if not _urm_isnum(literal) or isinstance(literal, bool):
                        continue
                    passes = _urmcp_passes(value, op, literal)
                    target = _urmcp_target(op, literal)
                    if passes is False and target is not None:
                        unmet.append((abs(target - value), target, site, op, literal))
                    elif passes:
                        met.append((literal, site))
                if unmet:
                    unmet.sort(key=lambda item: item[:2])
                    _gap, target, site, op, literal = unmet[0]
                    scene = _urmcp_where(index, site)
                    words = urm_goal(path, op, literal) or (u"needs %s" % (_urm_number(target),))
                    return (words + (u" in %s" % scene if scene else u""), "loss")
                if met:
                    scene = _urmcp_where(index, met[-1][1])
                    return ((u"opens %s" % scene) if scene else u"passes every check", "gain")
            if kind == "bool" and switches:
                site, op = switches[0]
                scene = _urmcp_where(index, site)
                wanted = op == "truthy"
                if bool(value) == wanted:
                    return ((u"opens %s" % scene) if scene else u"passes its check", "gain")
                return ((u"%s needs %s" % (scene, u"true" if wanted else u"false")) if scene
                        else (u"needs %s" % (u"true" if wanted else u"false")), "loss")
            if kind == "text" and goals:
                for site, op, literal in goals:
                    if op == "==" and literal == value:
                        scene = _urmcp_where(index, site)
                        return ((u"opens %s" % scene) if scene else u"passes its check", "gain")
            site = (goals[0][0] if goals else switches[0][0] if switches else others[0] if others else None)
            scene = _urmcp_where(index, site) if site is not None else None
            return ((u"checked in %s" % scene) if scene else u"checked by the story", "plain")
        read = _urmcp_read_at_all(path)
        if read is None or read:
            return None
        entry = st.by_path.get(path)
        if entry is not None and _urmcp_in_text(entry):
            return (u"only shown in text", "plain")
        return (u"flavour only", "plain")

    def urmcp_checks(path):
        """The values the game checks this name for, as chips under the box:
        [(words, value to fill, tone)], the next one still ahead amber."""

        found, value = _urmcp_now(path)
        index, reads = _urmcp_reads(path)
        if not found or index is None or not reads:
            return python_list()
        targets = python_dict()
        order = python_list()
        for site, op, literal in reads:
            target = _urmcp_target(op, literal)
            if target is None or isinstance(target, bool):
                continue
            key = (type(target).__name__, target)
            scenes = targets.get(key)
            if scenes is None:
                targets[key] = scenes = python_list()
                order.append((target, key))
            scene = _urmcp_where(index, site)
            if scene and scene not in scenes:
                scenes.append(scene)
        if not order:
            return python_list()
        try:
            order.sort(key=lambda item: (not _urm_isnum(item[0]), item[0]))
        except Exception:
            pass
        ahead = None
        if _urm_isnum(value):
            for target, _key in order:
                if _urm_isnum(target) and target > value:
                    ahead = target
                    break
        out = python_list()
        for target, key in order:
            scenes = targets[key]
            words = u"%s" % (_urm_number(target) if _urm_isnum(target) else target,)
            scene = scenes[0] if len(scenes) == 1 else None
            if target == ahead and _urm_isnum(target):
                words += (u" \u00b7 %s needs this" % scene) if scene else u" \u00b7 needed next"
                out.append((words, target, "warn"))
            else:
                if scene:
                    words += u" \u00b7 %s" % scene
                out.append((words, target, "plain"))
        return out

    def _urmcp_need(path, op, literal):
        """"needs over 150": what a number test asks, without what the player
        has (the value is shown beside it); None for a test that is not a
        goal."""

        if isinstance(literal, bool) or not _urm_isnum(literal):
            return None
        if op in _URM_GOAL_NEED:
            return u"needs %s%s" % (_URM_GOAL_NEED[op], _urm_number(literal))
        if op == "==":
            return u"needs %s" % (_urm_number(literal),)
        return None

    def urmcp_about(path):
        """The selected variable in words: where the story checks it and
        where it changes."""

        index, reads = _urmcp_reads(path)
        if index is None:
            return u""
        parts = python_list()
        scenes = python_list()
        needs = python_dict()
        for site, op, literal in reads:
            scene = _urmcp_where(index, site)
            if scene is None:
                continue
            if scene not in needs:
                scenes.append(scene)
                needs[scene] = python_list()
            words = _urmcp_need(path, op, literal)
            if words and words not in needs[scene]:
                needs[scene].append(words)
        if scenes:
            said = python_list()
            for scene in scenes[:3]:
                if needs[scene]:
                    words = needs[scene][:3]
                    # needs 500, 1000: the word once
                    words = words[:1] + python_list(
                        one[len(u"needs "):] if one.startswith(u"needs ") else one for one in words[1:])
                    said.append(u"%s (%s)" % (scene, u", ".join(words)))
                else:
                    said.append(scene)
            parts.append(u"Checked in %s." % u", ".join(said))
        changed = python_list()
        for record in index.writes.get(path) or ():
            scene = _urmcp_where(index, record[0])
            if scene and scene not in changed:
                changed.append(scene)
        if changed:
            parts.append(u"Changed in %s." % u", ".join(changed[:3]))
        if not parts:
            note = urmcp_note(path)
            if note is not None:
                parts.append(note[0][:1].upper() + note[0][1:] + u".")
        return u" ".join(parts)

    # ---- rows on screen

    def _urmcp_split(path):
        """(owners, leaf) of a name the search's catalog may not hold:
        mc.stats.luck is (("mc", "stats"), "luck")."""

        entry = _urmcp_state().by_path.get(path)
        if entry is not None:
            return (tuple(entry.owners), entry.leaf)
        parts = _urmc_parse(path)
        if not parts:
            return ((), path)
        words = [parts[0]] + [u"%s" % key for kind, key in parts[1:]]
        return (tuple(words[:-1]), words[-1])

    # ---- the Remembered page (the user's 3b, drawn as B2): three groups,
    # each its own colour and shape of edge, icon, count and a line on what
    # it means; Unfreeze on a frozen row, Freeze on a watched one, Stop
    # ignoring on an ignored one. Frozen names are in the save, the others
    # in our lists (01_urm_door).

    _URMCP_KEPT = (
        ("frozen", u"FROZEN", u"\ueb3b", "frozen", False, u"the game can't change these"),
        ("watch", u"WATCHING", u"\ue8f4", "watch", False, u"kept close, found at a glance"),
        ("ignored", u"IGNORED FOR PATHS", u"\ue14b", "ignored", True, u"left out of the map and cards"),
    )

    def urmcp_kept_groups():
        """[(key, title, icon, tone, dashed, line, rows)], rows
        [(path, owners, name, kind, words, frozen, can_freeze)]: plain words
        and names only, for the screens. A frozen name is in Frozen alone;
        the other remembered ones are in Watching, or Ignored for paths."""

        frozen = python_list(n for n, v in _urm_frozen())
        lists = _urm_remembered()
        names = python_dict((
            ("frozen", frozen),
            ("watch", python_list(r[0] for r in lists if r[0] not in frozen and "path" not in r[2])),
            ("ignored", python_list(r[0] for r in lists if r[0] not in frozen and "path" in r[2]))))
        out = python_list()
        for key, title, icon, tone, dashed, line in _URMCP_KEPT:
            rows = python_list()
            for path in names[key]:
                kind, words = urmcp_value(path)
                owners, leaf = _urmcp_split(path)
                rows.append((path, u" \u203a ".join(owners), leaf.replace(u"_", u" "), kind,
                             words if kind != "gone" else u"not there now",
                             path in frozen, _urm_can_freeze(path)))
            out.append((key, title, icon, tone, dashed, line, rows))
        return out

    def urmcp_freeze(path):
        """Freeze a name at what it holds now, or unfreeze it."""

        if _urm_is_frozen(path):
            _urm_unfreeze(path)
        else:
            _urm_freeze(path)
        renpy.restart_interaction()

    def urmcp_remember(path):
        """Remember a name, or forget it (a freeze of it ends too). A name
        the search did not find is no longer a row once forgotten: the
        detail panel lets it go."""

        if _urm_is_remembered(path):
            _urm_forget(path)
            st = _urmcp_state()
            if st.selected == path and path not in st.by_path:
                st.selected = None
        else:
            _urm_remember(path)

    def urmcp_unignore(path):
        """Stop ignoring a name for paths and code view: it stays remembered."""

        _urm_unignore(path)

    def urmcp_frozen(path):
        """Whether a name is frozen: its value is drawn in ice blue."""

        return _urm_is_frozen(path)

    def urmcp_frozen_words(path):
        """Frozen at 999. (and where the story checks it), or None."""

        if not _urm_is_frozen(path):
            return None
        about = urmcp_about(path)
        return u"Frozen at %s.%s" % (urmcp_value(path)[1], (u" " + about) if about else u"")

    def urmcp_freeze_words(path):
        """(words, live) of the Freeze button for a name."""

        if _urm_is_frozen(path):
            return (u"Unfreeze", True)
        if _urm_can_freeze(path):
            val = urmcp_value(path)[1]
            if len(val) > 16:
                val = val[:15] + u"\u2026"
            return (u"Freeze at %s" % val, True)
        return (u"Freeze", False)

    def urmcp_name(entry):
        """(owner words, the name) of a row: mc \u203a stats \u203a, luck."""

        owners = u" \u203a ".join(entry.owners)
        leaf = entry.leaf.replace(u"_", u" ")
        if not entry.owners:
            leaf = leaf[:1].upper() + leaf[1:]
        return owners, leaf

    def urmcp_value(path):
        """(kind, words) of a value as it is now."""

        found, value = _urmcp_now(path)
        if not found:
            return ("gone", u"")
        kind = _urmcp_kind(value)
        if kind in ("int", "float"):
            return (kind, u"%s" % (_urm_number(value),))
        if kind == "text":
            return (kind, value)
        if kind == "bool":
            return (kind, u"true" if value else u"false")
        if kind == "none":
            return (kind, u"empty")
        if kind == "list":
            try:
                n = len(value)
                return (kind, u"1 item" if n == 1 else u"%d items" % n)
            except Exception:
                return (kind, u"items")
        if kind in ("dict", "object"):
            st = _urmcp_state()
            entry = st.by_path.get(path)
            return (kind, u"%d inside" % (entry.inside if entry is not None else 0))
        return ("other", u"")

    def urmcp_line_note(line):
        """Line \u00b7 Caf\u00e9 \u00b7 seen"""

        parts = python_list((u"Line" if line.kind == "line" else u"Choice",))
        scene = _urmcp_scene(line.node)
        if scene:
            parts.append(scene)
        if line.kind == "line":
            seen = _urmcp_seen(line)
            if seen is not None:
                parts.append(u"seen" if seen else u"not seen yet")
        return u" \u00b7 ".join(parts)

    def urmcp_label_note(label):
        parts = python_list((u"Label",))
        try:
            parts.append(u"seen" if renpy.seen_label(label) else u"not seen yet")
        except Exception:
            pass
        return u" \u00b7 ".join(parts)

    _URMCP_FIT = python_dict()
    _URMCP_FIT_GEN = [None]

    def urmcp_fit(text, style_name, width):
        """text cut to `width` pixels in that style, with ... when cut: the
        width asked of the engine (UX 22), remembered."""

        gen_fn = globals().get("_urmk_word_gen")
        if gen_fn is not None:
            gen = gen_fn()
            if _URMCP_FIT_GEN[0] != gen:
                _URMCP_FIT.clear()
                _URMCP_FIT_GEN[0] = gen
        key = (text, style_name, width)
        found = _URMCP_FIT.get(key)
        if found is not None:
            return found
        width_fn = globals().get("urmk_text_width")
        def wide(words):
            try:
                if width_fn is not None:
                    return width_fn(words, style_name)
                return renpy.text.text.Text(words, style=style_name, substitute=False).size()[0]
            except Exception:
                return len(words) * 10
        safe = text.replace(u"{", u"{{")
        if wide(safe) <= width:
            found = safe
        else:
            low, high = 0, len(text)
            while low < high:
                middle = (low + high + 1) // 2
                if wide(text[:middle].replace(u"{", u"{{") + u"...") <= width:
                    low = middle
                else:
                    high = middle - 1
            found = text[:low].rstrip().replace(u"{", u"{{") + u"..."
        if len(_URMCP_FIT) > 4000:
            _URMCP_FIT.clear()
        _URMCP_FIT[key] = found
        return found

    def urmcp_rows(group):
        """The rows of a group for the current query, at most _URMCP_ROWS."""

        st = _urmcp_state()
        result = st.result
        if result is None:
            return python_list()
        return getattr(result, group)[:_URMCP_ROWS]

    def urmcp_flag(name):
        """on, off, or None when the game has not made its collection yet."""

        try:
            return urmfl_is_on(name)
        except Exception:
            return None

    # ---- "changed since": the values at a choice, a mark, a load

    def _urmcp_sweep(entries):
        """Forget the menus a rollback took back. The engine's rollback log
        loses entries two ways: a rollback takes them off its end, and a
        long scene lets the oldest go off its front (config.rollback_length).
        A menu gone from the log while the front seen last is still there
        was rolled back; one gone with that front went into the past, and
        stays a choice made. The menus' entries are held here (our memory,
        never saved), so an id is never another entry's."""

        st = _urmcp_state()
        there = python_set(id(entry) for entry in entries)
        front = st.log_front
        trimmed = front is not None and id(front) not in there
        keep = python_list()
        for snap in st.choice_snaps:
            if snap[2] or id(snap[0]) in there:
                keep.append(snap)
            elif trimmed and _urmcp_answered(snap[0]):
                snap[2] = True
                keep.append(snap)
        st.choice_snaps = keep
        st.log_front = entries[0] if entries else None

    def _urmcp_snap_choice(entry, values):
        """The values at a menu, before its choice: once per menu shown."""

        st = _urmcp_state()
        for snap in st.choice_snaps:
            if snap[0] is entry:
                return
        st.choice_snaps.append(python_list((entry, values, False)))
        del st.choice_snaps[:-_URMCP_SNAPS]

    def _urmcp_last_choice():
        """The values at the menu of the newest choice made and not rolled
        back: after rolling back past a choice, the one that is now the
        last; after a long scene, still the last one."""

        st = _urmcp_state()
        try:
            log = renpy.game.log
            entries = log.log
        except Exception:
            return None
        _urmcp_sweep(entries)
        for entry, values, past in reversed(st.choice_snaps):
            if entry is log.current:
                continue
            if past or _urmcp_answered(entry):
                return values
        return None

    def _urmcp_answered(entry):
        value = getattr(entry, "forward", None)
        return value is not None and not isinstance(value, bool)

    def _urmcp_live():
        return bool(getattr(getattr(renpy.game, "interface", None), "started", False))

    def _urmcp_snap_async(kind, entry=None):
        """Snapshot store values in worker slices when the live game is running,
        and pre-warm the catalog if the store stays at the same stamp."""
        st = _urmcp_state()
        snap_stamp = _urmcp_stamp()

        def job():
            for said in _urmcp_build_steps():
                yield said

        def then(catalog):
            if catalog is None:
                return
            values = _urmcp_values(catalog)
            if kind == "load":
                st.snaps["load"] = values
            elif kind == "choice" and entry is not None:
                _urmcp_snap_choice(entry, values)
            if snap_stamp is not None and _urmcp_stamp() == snap_stamp:
                if st.catalog is None or getattr(st, "catalog_stamp", None) != snap_stamp:
                    _urmcp_take(catalog)

        _urm_work_slices("search snap", job, then)

    def _urmcp_interact():
        """At a menu: the values before the choice. At the first interaction
        of a run: the values at the start, as at a load."""

        st = _urmcp_state()
        _urmcp_refresh_language(st)
        try:
            if getattr(renpy.store, "main_menu", False):
                # a game ended: the next one starts with no choices made
                st.choice_snaps = python_list()
                st.log_front = None
                st.snaps.pop("load", None)
                return
            if "load" not in st.snaps:
                if _urmcp_live():
                    _urmcp_snap_async("load")
                else:
                    st.snaps["load"] = _urmcp_values(_urmcp_build())
            _urmcp_sweep(renpy.game.log.log)
            current = renpy.game.context().current
            node = renpy.game.script.namemap.get(current) if current is not None else None
            menu = getattr(renpy.ast, "Menu", None)
            if menu is None or not isinstance(node, menu):
                return
            entry = renpy.game.log.current
            if entry is not None:
                if _urmcp_live():
                    _urmcp_snap_async("choice", entry)
                else:
                    _urmcp_snap_choice(entry, _urmcp_values(_urmcp_build()))
        except Exception:
            pass

    def _urmcp_loaded():
        st = _urmcp_state()
        try:
            if _urmcp_live():
                _urmcp_snap_async("load")
            else:
                st.snaps["load"] = _urmcp_values(_urmcp_build())
            st.choice_snaps = python_list()
            st.log_front = None
        except Exception:
            pass

    if _urmcp_interact not in config.interact_callbacks:
        config.interact_callbacks.append(_urmcp_interact)
    if _urmcp_loaded not in config.after_load_callbacks:
        config.after_load_callbacks.append(_urmcp_loaded)

    # Alt+F opens and closes the quick sheet, in every context (the
    # user's pick, 2026-11-22, not Ctrl+F: Ctrl held is Ren'Py's skip).
    # Ren'Py's own f (full screen) matches only with Alt up.
    config.keymap["urmcp_search"] = ["alt_K_f"]
    # The same from the URM+ menu, with the mouse: its first row. The key
    # is registered so the list of hotkeys (_urm_keys) knows it, and bound
    # here while the menu binds none; once it binds registered keys, this
    # Keymap goes (IDEAS.md).
    _urm_entry_add("search", "Search", u"\ue8b6", urmcp_toggle, key="alt_K_f",
                   key_words="Alt+F", group=1, order=5)
    _urm_entry_add("menu", "Menu", u"\ue5d2", urmcp_full, group=9, order=40)
    config.underlay.append(renpy.display.behavior.Keymap(urmcp_search=urmcp_toggle))

    class _URMCPInput(InputValue):
        """The search box and the edit box: what they hold is the page's."""

        returnable = False

        def __init__(self, field):
            self.field = field
            # the new-variable form's value box waits for a click: its name
            # box takes the focus when the form opens
            self.default = field != "new_text"

        FIELDS = {"query": "query", "edit": "edit_text", "new_name": "new_name", "new_text": "new_text"}

        def get_text(self):
            return getattr(_urmcp_state(), _URMCPInput.FIELDS[self.field])

        def set_text(self, text):
            if self.field == "query":
                urmcp_typed(text)
            elif self.field == "edit":
                urmcp_edit_text(text)
            else:
                urmcp_new_set(self.field, text)

        def enter(self):
            if self.field in ("new_name", "new_text"):
                urmcp_new_commit()
            elif self.field != "query":
                urmcp_commit()
            raise renpy.IgnoreEvent()

    urmcp_query_box = _URMCPInput("query")
    urmcp_edit_box = _URMCPInput("edit")
    urmcp_new_name_box = _URMCPInput("new_name")
    urmcp_new_text_box = _URMCPInput("new_text")

    # ---- rows for the screens: plain words and names only, so a screen's
    # scope never holds a game object or a statement

    def _urmcp_note_of(path):
        st = _urmcp_state()
        if path in st.notes:
            return st.notes[path]
        try:
            note = urmcp_note(path)
        except Exception:
            note = None
        st.notes[path] = note
        return note

    # The groups a pill shows, in the order the pages draw them.
    _URMCP_GROUPS = python_dict((
        ("all", ("vars", "flags", "choices", "lines", "engine")),
        ("vars", ("vars", "engine")), ("flags", ("flags",)), ("choices", ("choices",)),
        ("lines", ("lines",)), ("labels", ("labels",)), ("engine", ("engine",)),
        ("changed", ("changed",))))

    def _urmcp_room(group):
        """How many rows of `group` to build now: up to _URMCP_ROWS each, as
        many as st.room leaves after the groups drawn above it. A page builds
        the rows a player can see and a spare (_urmcp_screenful); scrolling
        near the end builds the next screenful (urmcp_rows_adj): a list of
        hundreds of rows was 0.3-1 s to build and draw on every key on Being
        a DIK (FINDINGS)."""

        st = _urmcp_state()
        result = st.result
        if result is None:
            return 0
        room = getattr(st, "room", _URMCP_ROOM)
        for name in _URMCP_GROUPS.get(st.pill, (group,)):
            have = min(len(getattr(result, name)), _URMCP_ROWS)
            if name == group:
                return max(0, min(have, room))
            if name == "engine" and not st.engine_open and st.pill != "engine":
                continue
            room -= have
        return max(0, min(len(getattr(result, group)), _URMCP_ROWS, room))

    def _urmcp_screenful():
        """The rows of one screenful and a spare, on the page shown."""

        return _URMCP_ROOM_PAGE if _urmcp_state().full else _URMCP_ROOM

    def _urmcp_scrolled(value):
        """The rows list was scrolled: near its end, build the next rows."""

        adj = urmcp_rows_adj
        if value >= adj.range - 2 * adj.page:
            st = _urmcp_state()
            room = getattr(st, "room", _URMCP_ROOM)
            if st.result is not None and room < 8 * _URMCP_ROWS:
                st.room = room + _urmcp_screenful()
                renpy.restart_interaction()
        return None

    urmcp_rows_adj = ui.adjustment(changed=_urmcp_scrolled)

    def _urmcp_rows_top():
        """A rows list shown afresh (Search opened, the page switched, back
        to Find from another tab) starts at its top with its first rows, as
        a list with an adjustment of its own did: the shared one would keep
        the last scroll."""

        _urmcp_state().room = _urmcp_screenful()
        urmcp_rows_adj.change(0)

    def urmcp_var_rows(group):
        """[(path, owners, name, kind, words, note, fold)] of a group of
        names (vars, engine, changed); fold is None for a value, else
        whether the object is open."""

        st = _urmcp_state()
        if st.result is None:
            return python_list()
        out = python_list()
        for entry in getattr(st.result, group)[:_urmcp_room(group)]:
            kind, words = urmcp_value(entry.path)
            owners, name = urmcp_name(entry)
            fold = None
            note = None
            if entry.kind in ("dict", "object"):
                fold = entry.path in st.open_paths
            elif kind in ("int", "float", "text", "bool", "none"):
                note = _urmcp_note_of(entry.path)
            out.append((entry.path, owners, name, kind, words, note, fold))
        return out

    def urmcp_line_rows(group):
        """[(key, text, note)] of the lines or the choices found."""

        st = _urmcp_state()
        if st.result is None or st.result.line_corpus is None:
            return python_list()
        lines = _urmcp_lines()
        if st.result.line_corpus is not lines:
            return python_list()
        out = python_list()
        for place in getattr(st.result, group)[:_urmcp_room(group)]:
            line = lines[place]
            out.append((u"line:%d" % place, line.text, urmcp_line_note(line)))
        return out

    def urmcp_label_rows():
        st = _urmcp_state()
        if st.result is None:
            return python_list()
        return python_list((u"label:" + label, _urmm_pretty(label.split(".")[-1]), urmcp_label_note(label))
                           for label in st.result.labels[:_urmcp_room("labels")])

    def urmcp_flag_rows():
        st = _urmcp_state()
        if st.result is None:
            return python_list()
        out = python_list()
        for name in st.result.flags[:_urmcp_room("flags")]:
            on = urmcp_flag(name)
            out.append((u"flag:" + name, _urmm_pretty(name),
                        u"true" if on else u"false" if on is not None else u"not made yet"))
        return out

    def urmcp_counts():
        st = _urmcp_state()
        if st.result is None:
            return python_dict()
        return st.result.counts()

    def urmcp_found():
        st = _urmcp_state()
        return st.result.found() if st.result is not None else 0

    def urmcp_reading():
        """Search is waiting on the catalog or matching the current language."""
        st = _urmcp_state()
        return st.reading or st.language_reading

    def urmcp_engine_hint():
        """e.g. persistent.money_hint: the first name of the folded group."""

        st = _urmcp_state()
        if st.result is None or not st.result.engine:
            return u""
        return st.result.engine[0].path

    def urmcp_title(path):
        """mc: money"""

        st = _urmcp_state()
        entry = st.by_path.get(path)
        if entry is None:
            owners, leaf = _urmcp_split(path)
            return u"%s: %s" % (u" ".join(owners), leaf) if owners else leaf.replace(u"_", u" ")
        if entry.owners:
            return u"%s: %s" % (u" ".join(entry.owners), entry.leaf)
        return entry.leaf.replace(u"_", u" ")

    def urmcp_since_words():
        """[(key, words, there)] of the moments "changed since" can use."""

        st = _urmcp_state()
        return python_list((
            ("choice", u"your last choice", _urmcp_last_choice() is not None),
            ("mark", u"the moment you marked", "mark" in st.snaps),
            ("load", u"the last load", "load" in st.snaps)))

    # ---- what the screens ask

    # The page's own grounds, all from the kit's colours: (colour, radius
    # at 1080 lines).
    _URMCP_GROUNDS = python_dict((
        ("pill", ("surface-2", 20)), ("pill-on", ("accent", 20)),
        ("key", ("plain-bg", 8)), ("key-on", ("#0b1a3033", 8)),
        ("value", ("surface-2", 8)),
        ("field-on", ("accent", 14)), ("field", ("surface", 12)),
    ))

    def _urmcp_veil(colour):
        """A colour with the kit's hover veil laid on it (white at .08)."""

        r, g, b, a = tuple(renpy.easy.color(URMK_COLOURS.get(colour, colour)))
        v = 0.08
        return "#%02x%02x%02x%02x" % (int(round(r + (255 - r) * v)), int(round(g + (255 - g) * v)),
                                      int(round(b + (255 - b) * v)), max(a, 40))

    def urmcp_ground(kind, hover=False):
        colour, radius = _URMCP_GROUNDS[kind]
        colour = URMK_COLOURS.get(colour, colour)
        if hover:
            colour = _urmcp_veil(colour)
        return urmk_pill(colour, urmk_px(radius))

    def urmcp_state_pill():
        return _urmcp_state().pill

    def urmcp_state_tab():
        return _urmcp_state().tab

    def urmcp_state_since():
        return _urmcp_state().since

    def urmcp_state_query():
        return _urmcp_state().query

    def urmcp_state_empty():
        return not (_urmcp_state().query or u"").strip()

    def urmcp_editing():
        return _urmcp_state().editing

    def urmcp_creating():
        return _urmcp_state().creating

    def urmcp_new_error():
        return _urmcp_state().new_error

    def urmcp_selected():
        return _urmcp_state().selected

    def _urmcp_row_line(st, key):
        if (key is None or not key.startswith(u"line:") or st.lines is None
                or st.lines[0] != _urmcp_language()):
            return None
        place = int(key[5:])
        lines = st.lines[1]
        return lines[place] if place < len(lines) else None

    def urmcp_replay_offer(key):
        """Capture a replay for the statement behind the selected result."""

        st = _urmcp_state()
        if st.selected != key:
            return None
        line = _urmcp_row_line(st, key)
        if line is None or line is not st.selected_line:
            return None
        label = _urmcp_scene_label(line.node)
        if not label:
            return None
        if _URMCP_SHOWN.search(line.text):
            return _urm_replay_offer(label, None)
        cue = line.text if len(line.text) <= 100 else line.text[:99].rstrip() + u"\u2026"
        return _urm_replay_offer(label, u"\u201c%s\u201d" % cue.replace(u"{", u"{{"))

    def urmcp_edit_error():
        return _urmcp_state().edit_error

    def urmcp_engine_open():
        st = _urmcp_state()
        return st.engine_open or st.pill == "engine"

    def urmcp_more():
        return _urmcp_state().more

    def urmcp_show_more():
        _urmcp_state().more = True
        renpy.restart_interaction()

    def urmcp_undo_for(path):
        undo = _urmcp_state().undo
        return undo is not None and undo[0] == path

    def urmcp_set_words(path):
        """Set to 500, from what is in the box."""

        text = _urmcp_state().edit_text.strip()
        if not text:
            return u"Set"
        if len(text) > 12:
            text = text[:11] + u"\u2026"
        return u"Set to %s" % text

    def urmcp_is_var(key):
        """A variable's row: one the search found, or a name on the
        Remembered page (remembered or frozen, maybe deeper than the search
        walks)."""
        return key in _urmcp_state().by_path or _urm_is_remembered(key) or _urm_is_frozen(key)

    def urmcp_other(key):
        """(words, note) of a selected line, choice, label or flag."""

        try:
            kind, rest = key.split(u":", 1)
        except Exception:
            return (u"", u"")
        if kind == u"line":
            _urmcp_lines()
            st = _urmcp_state()
            line = _urmcp_row_line(st, key) if st.selected == key else None
            if line is None or line is not st.selected_line:
                return (u"", u"")
            return (u"\u201c%s\u201d" % line.text.replace(u"{", u"{{"), urmcp_line_note(line))
        if kind == u"label":
            return (_urmm_pretty(rest.split(".")[-1]), urmcp_label_note(rest))
        if kind == u"flag":
            on = urmcp_flag(rest)
            return (_urmm_pretty(rest), u"Flag \u00b7 " + (u"true" if on else u"false" if on is not None else u"not made yet"))
        return (u"", u"")

    def urmcp_nothing():
        """True when the pill picked shows no row."""

        st = _urmcp_state()
        if st.reading or st.language_reading:
            return False        # its rows are on their way, not missing
        if st.result is None:
            return True
        counts = st.result.counts()
        pill = st.pill
        if pill == "all":
            return not (counts["vars"] or counts["lines"] or counts["choices"]
                        or counts["flags"] or counts["engine"])
        return not counts.get(pill)

    def urmcp_empty_words():
        st = _urmcp_state()
        if st.pill == "changed":
            if _urmcp_since_values() is None:
                return python_dict((
                    ("choice", u"No choice made since the game was loaded."),
                    ("mark", u"Nothing marked yet: Mark now keeps the values as they are."),
                    ("load", u"The values at the last load are not known yet."))).get(st.since, u"")
            return u"Nothing changed since then."
        if not (st.query or u"").strip():
            return u"Type a name, a value or words of a line."
        return u"Nothing found."
