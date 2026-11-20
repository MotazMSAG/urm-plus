# ---------------------------------------------------------------------------
# Search: dotted names, depth, value operators, and the cost of getting there
# ---------------------------------------------------------------------------
#
# URM's search is good at what it does and blind to one whole shape of game.
# Four things are wrong with it, and the first two are invisible rather than
# merely slow:
#
#   * a dotted query can never match. classes/search.rpy:227 compares the one
#     path SEGMENT against the query - matchStringValue(varName, query), not
#     fullVarName - so "mc.str" is tested against "mc" and then against "str"
#     and matches neither. Bare "str" finds mc.str, the exact name does not.
#
#   * object recursion stops at one level. The two descent branches
#     (search.rpy:206 and :216) are guarded by `not parentVarName`, which reads
#     "only descend when standing on a bare store variable". Once inside `mc`,
#     `inventory` is matched by name and never entered, so mc.inventory.gold
#     cannot be found by any query. Games that nest - mc.stats.corruption,
#     player.relationships.sarah.love - hide most of themselves from search.
#
#   * value search walks the store twice. matchVarName guards
#     `fullVarName == 'store'` at :181 because `store` is a name in the store
#     pointing at the store itself; matchVarValue has no such guard, and
#     'store' passes isSupportedVarType, so every variable is reported once
#     bare and once as store.X.
#
#   * every type lookup is an eval of a source string. Var.getVarType
#     (classes/vars.rpy:408) does eval(varName, renpy.store.__dict__), which
#     compiles the string afresh each call, and the descent branches eval the
#     same name two or three times in one pass. The count per search is
#     roughly N_names + 2*N_objects + N_attrs.
#
# What is NOT wrong, having checked: int/float queries already cross-match
# (getValType tests bool before int, so a boolean never reaches the int
# branch, and float('3') == 3.0 holds), and basestring comes from Ren'Py's own
# compat module rather than URM, so it is defined under both engines.
#
# The contract for everything below:
#
#   * nothing here may make an unasked-for search slower. The optimisations
#     return identical results for less work and are unconditional; anything
#     that scans MORE to find more is off by default and switched on by the
#     user - urmcSearchDepth, or the Deeper button, which pays per click.
#   * every patch is wrapped in its own try. A failure leaves URM's own method
#     in place, so the worst case is URM 2.6.2 behaving exactly as shipped.
#   * URM's private names are found by suffix rather than written out. The
#     compiled archive mangles them to _m1_<file>__<name>, which is a build
#     artefact, not something to depend on.

init 999 python:

    # Four levels is the point past which a result list stops being readable,
    # whatever the cost; the setting is clamped to it rather than trusted.
    _URMC_DEPTH_CAP = 4
    _URMC_PATH_LIMIT = 20000

    # Parsed paths are cached on Var, which lives in URM's `_constant` store,
    # so the cache is not written into saves. That alone is not enough: in a
    # store, dict, list and set are themselves rebound to the rollback-tracked
    # Revertable kinds (renpy/minstore.py:37-50), and [] / {} literals are
    # rewritten to them as well. A tracked cache is copied into the rollback
    # log on the first change of every interaction - 20,000 entries at a time.
    # So every container here that outlives one call is a python_dict,
    # python_list or python_set, the untracked originals minstore keeps.

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
        cannot walk; the caller falls back to URM's own lookup for the second
        case, so the two never need telling apart here.
        """

        cache = x52URM.Var._urmcPaths

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

    def _urmc_join(parent, child, kind):
        """
        A child's full name. URM's own __getFullVarName asks getVarType what
        the parent is, which is one more lookup per child; the caller already
        knows, so it says.
        """

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


# A second block, so a failure to read URM's internals leaves the first one's
# helpers defined and simply does not install anything.
init 999 python:

    def _urmc_private(cls, suffix):
        """URM's mangled attribute name for `suffix`, or None."""

        for key in vars(cls):
            if key.endswith(suffix):
                return key
        return None

    _urmc_installed = False

    try:
        _URMC_RESULTS = _urmc_private(x52URM.SearchClass, "__results")
        _urmc_matchstr = getattr(
            x52URM.SearchClass,
            _urmc_private(x52URM.SearchClass, "__matchStringValue"))
        _urmc_fullname = getattr(
            x52URM.SearchClass,
            _urmc_private(x52URM.SearchClass, "__getFullVarName"))

        _urmc_getValType = x52URM.Var.getValType
        _urmc_isSupported = x52URM.Var.isSupportedVarType
        _urmc_evalVarType = x52URM.Var.getVarType
        _urmc_namePath = x52URM.Var.namePath

        _urmc_orig_doSearch = x52URM.SearchClass.doSearch
        _urmc_orig_reset = x52URM.SearchClass.resetSearch

        if _URMC_RESULTS is None:
            raise AttributeError("SearchClass has no private results list")

        _urmc_ready = True
    except Exception as error:
        _urmc_ready = False
        print("URM+: leaving search as it ships (%s)" % (error,))


    def _urmc_maxDepth(search=None):
        """
        How many levels to walk: the setting, plus whatever the Deeper button
        has added to this search, clamped to the cap.
        """

        try:
            depth = int(x52URM.Settings.urmcSearchDepth)
        except Exception:
            depth = 1

        if search is not None:
            try:
                depth += int(getattr(search, "_urmcExtra", 0) or 0)
            except Exception:
                pass

        if depth < 1:
            return 1
        if depth > _URMC_DEPTH_CAP:
            return _URMC_DEPTH_CAP
        return depth

    def _urmc_visited(search):
        """The set of containers this search has already entered."""

        seen = getattr(search, "_urmcVisited", None)
        if seen is None:
            seen = python_set()
            search._urmcVisited = seen
        return seen

    def _urmc_container(varType, value, found):
        """
        'dict', 'object' or None - what this value's children are reached by.

        Lists are deliberately not containers here: their items have no names,
        which is why URM's name search never entered them either.
        """

        if not found:
            return None
        if varType == "dict":
            return "dict"
        if varType in ("string", "boolean", "int", "float"):
            return None
        try:
            if hasattr(value, "__dict__"):
                return "object"
        except Exception:
            pass
        return None

    def _urmc_type(full):
        """
        (found, value, varType) for a name, walking rather than evaluating and
        falling back to URM's eval only for names that are not plain paths.
        """

        found, value = _urmc_resolve(full)
        if found:
            return (True, value, _urmc_getValType(value))

        try:
            return (False, None, _urmc_evalVarType(full))
        except Exception:
            return (False, None, "unknown")

    def _urmc_hit(search, leaf, full, query):
        """
        Does this variable's name match?

        The leaf is tried first, which is URM's behaviour and keeps a bare
        "str" finding mc.str. The full dotted name is only tried when the
        query itself is dotted or subscripted, so this adds one string compare
        for queries that could not have matched at all before, and nothing
        otherwise. It costs no extra traversal, which is why it is not
        optional.
        """

        if _urmc_matchstr(search, leaf, query):
            return True

        if full != leaf and ("." in query or "[" in query):
            return _urmc_matchstr(search, full, query)

        return False


    def _urmc_matchVarName(search, varName, query, parentVarName=None,
                           _depth=0, _full=None):

        if not isinstance(varName, _URM_TEXT):
            return None

        try:
            settings = x52URM.Settings

            # Cheap string test before the type lookup. URM does it the other
            # way round (search.rpy:178 then :184), so every internal variable
            # was resolved and then discarded.
            if varName.startswith("_") and not settings.searchInternalVars:
                return None

            full = _full
            if full is None:
                full = _urmc_fullname(search, varName, parentVarName)

            if full == "store":
                return None

            if search.searchType == "labels":
                if _urmc_hit(search, varName, full, query):
                    return [x52URM.Var(full)]
                return None

            found, value, varType = _urmc_type(full)

            if varType == "unknown" and not settings.showUnsupportedVariables:
                return None

            if (varType not in ("persistent", "store", "unknown")
                    and not _urmc_isSupported(varType)):
                return None

            hit = _urmc_hit(search, varName, full, query)

            if full == "persistent":
                if not settings.searchPersistent:
                    return None
                return _urmc_descend(search, _urmc_matchVarName, full, value,
                                     "object", query, _depth, [])

            kind = _urmc_container(varType, value, found)

            if kind and settings.searchObjects and _depth < _urmc_maxDepth(search):
                # The container itself counts as a result when its own name
                # matched. URM records it as Var(varName) - the leaf - which is
                # the same thing only at depth 0.
                return _urmc_descend(search, _urmc_matchVarName, full, value,
                                     kind, query, _depth,
                                     [x52URM.Var(full)] if hit else [])

            return [x52URM.Var(full)] if hit else None

        except Exception as error:
            print('0x52: matchVarName failed for variable "{}". {}'.format(
                varName, error))


    def _urmc_matchVarValue(search, varName, query, parentVarName=None,
                            _depth=0, _full=None):

        if not isinstance(varName, _URM_TEXT):
            return None

        try:
            settings = x52URM.Settings

            if varName.startswith("_") and not settings.searchInternalVars:
                return None

            full = _full
            if full is None:
                full = _urmc_fullname(search, varName, parentVarName)

            # The guard matchVarName has and this did not. Without it every
            # variable is also reported as store.X, at double the cost.
            if full == "store":
                return None

            found, value, varType = _urmc_type(full)

            if varType == "persistent":
                if not settings.searchPersistent:
                    return None
                if _depth >= _urmc_maxDepth(search):
                    return None
                return _urmc_descend(search, _urmc_matchVarValue, full, value,
                                     "object", query, _depth, [])

            if not _urmc_isSupported(varType):
                return None

            if varType == "string":
                if _urmc_matchstr(search, value, query):
                    return [x52URM.Var(full)]
                return None

            if varType == "boolean":
                want = (query or "").strip().lower()
                if want not in ("true", "false"):
                    return None
                if bool(value) == (want == "true"):
                    return [x52URM.Var(full)]
                return None

            if varType in ("int", "float"):
                if _urmc_number(value, query):
                    return [x52URM.Var(full)]
                return None

            kind = _urmc_container(varType, value, found)

            if kind and settings.searchObjects and _depth < _urmc_maxDepth(search):
                return _urmc_descend(search, _urmc_matchVarValue, full, value,
                                     kind, query, _depth, [])

            return None

        except Exception as error:
            print('0x52: matchVarValue failed for variable "{}". {}'.format(
                varName, error))


    def _urmc_descend(search, matcher, full, value, kind, query, depth, found):
        """
        `matcher` over one container's children, one level down.

        The id() set holds what is on the stack right now, and the marker is
        dropped again on the way out. mc.game.player is mc is a common shape,
        and marking the whole search instead would be the wrong guard twice
        over: the depth cap already bounds the walk, and an object two store
        variables both point at would have its children scanned under
        whichever name came first and silently skipped under the other.
        """

        seen = _urmc_visited(search)
        marker = id(value)

        if marker in seen:
            return found or None

        seen.add(marker)
        out = python_list(found)

        try:
            for child in _urmc_keys(value, kind):
                hits = matcher(search, child, query, full, depth + 1,
                               _urmc_join(full, child, kind))
                if hits:
                    out.extend(hits)
        finally:
            seen.discard(marker)

        return out or None


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


    def _urmc_after(search):
        """
        Rank the results, then say which level a further click would reach.

        Both are settled once, here, and read from the screen as a plain
        attribute. Working either of them out in a screen expression would put
        it on the redraw path, which is the exact cost this block exists to
        remove.
        """

        try:
            query = (search.searchQuery or "").strip().lower()
            results = search.results or []
            if query and len(results) > 1 and search.searchType != "values":
                setattr(search, _URMC_RESULTS,
                        sorted(results,
                               key=lambda var: _urmc_rank(var.name, query)))
        except Exception:
            pass

        try:
            if search.searchType == "labels":
                # Labels are a flat namespace; there is nothing under them.
                search.urmcNextDepth = 0
            else:
                current = _urmc_maxDepth(search)
                if current >= _URMC_DEPTH_CAP:
                    search.urmcNextDepth = 0
                else:
                    search.urmcNextDepth = current + 1
        except Exception:
            search.urmcNextDepth = 0


    def _urmc_doSearch(search):
        """URM's search, ranked, and back to the depth the settings ask for."""

        search._urmcVisited = python_set()
        search._urmcExtra = 0

        try:
            _urmc_orig_doSearch(search)
        finally:
            search._urmcVisited = python_set()
            _urmc_after(search)


    def _urmc_resetSearch(search, keepInputQuery=False):

        _urmc_orig_reset(search, keepInputQuery)

        search._urmcVisited = python_set()
        search._urmcExtra = 0
        search.urmcNextDepth = 0


    def _urmc_deepen(search):
        """
        The same query, one level deeper, paid for on click.

        An earlier version of this descended only into the containers already
        in the results, which sounded cheaper and was useless: searching
        "gold" in a game that keeps it in mc.inventory returns no containers
        at all, so there was nothing to open. The level has to be raised and
        the store walked again.

        That is still nothing until asked for - a search nobody deepens costs
        exactly what it did before - and the walk is this rather than a call
        back into URM's doSearch so that recursive search, which replaces the
        collection with the previous results, cannot turn "deeper" into
        "narrower".
        """

        try:
            query = search.searchQuery
            if not query:
                return

            if search.searchType == "labels":
                return

            before = _urmc_maxDepth(search)
            if before >= _URMC_DEPTH_CAP:
                return

            search._urmcExtra = int(getattr(search, "_urmcExtra", 0) or 0) + 1

            matcher = (_urmc_matchVarValue
                       if search.searchType == "values"
                       else _urmc_matchVarName)

            search._urmcVisited = python_set()
            results = python_list()

            for name in python_list(renpy.store.__dict__):
                hits = matcher(search, name, query)
                if hits:
                    results.extend(hits)

            # Only keep the deeper pass if it did not lose anything. A walk
            # that threw part way through would otherwise replace a good
            # result list with a short one.
            if len(results) >= len(search.results or []):
                setattr(search, _URMC_RESULTS, results)

            _urmc_after(search)

        except Exception as error:
            print("0x52: searching deeper failed. {}".format(error))

        finally:
            search._urmcVisited = python_set()


    def _urmc_namePath_get(self):
        """
        namePath, cached.

        It is two regex scans over the name, it is called by value, by
        nameShortened and by the results screen, and it cannot go stale: a
        Var's name is set in __init__ and never reassigned. That last part is
        why only this property is cached. varType, isExpandable and isSupported
        guard on hasattr(self, '__varType'), which never hits - the string
        literal is not name-mangled while the assignment is - and making them
        cache would freeze a type that the user can change from the editor
        two rows below.
        """

        cache = self.__dict__

        try:
            return cache["_urmcNamePath"]
        except KeyError:
            pass

        value = _urmc_namePath.fget(self)
        cache["_urmcNamePath"] = value
        return value


    # Registering a setting is one insert: Settings.__getattr__ and
    # __setattr__ look the name up in defaultValues on every read and write
    # (classes/settings.rpy:137,143,148) with no snapshot taken at
    # construction. The value lands in persistent.URMSettings, so it is per
    # save file, and both columns of the options table work on it unchanged.
    # Defaults are today's behaviour: depth 1 is URM's own one level, and the
    # quickmenu button starts hidden.
    #
    # This stands on its own, because the quickmenu button has nothing to do
    # with search and must not be lost if URM's search internals move.
    try:
        _urmc_defaults = x52URM.SettingsClass.defaultValues
        _urmc_defaults.setdefault("urmcSearchDepth", 1)
        _urmc_defaults.setdefault("quickmenuBtnSkipUnseen", False)
    except Exception as error:
        print("URM+: could not register settings (%s)" % (error,))


    if _urmc_ready:
        try:
            x52URM.Var._urmcPaths = python_dict()
            x52URM.Var.getVarType = staticmethod(
                lambda name: _urmc_type(name)[2])
            x52URM.Var.namePath = property(_urmc_namePath_get)

            x52URM.SearchClass.matchVarName = _urmc_matchVarName
            x52URM.SearchClass.matchVarValue = _urmc_matchVarValue
            x52URM.SearchClass.doSearch = _urmc_doSearch
            x52URM.SearchClass.resetSearch = _urmc_resetSearch
            x52URM.SearchClass.urmcDeepen = _urmc_deepen
            x52URM.SearchClass.urmcNextDepth = 0

            _urmc_installed = True

        except Exception as error:
            print("URM+: search upgrades not installed (%s)"
                  % (error,))


