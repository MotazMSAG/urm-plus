# ---------------------------------------------------------------------------
# Now: values and flags, read without running the game's code
# ---------------------------------------------------------------------------
#
# The "now" layer's second piece (the first is 13_now): the read-only
# evaluator of the variable window (from 70) and the reading of flags a game
# keeps as words in a collection (from 83). Every display may ask them, and
# neither calls a function the game defined. Its own block after the script
# index (60): the operator tables are built from the index's ast names while
# the game loads. Moved unchanged (CODE_MAP.md, layers).

init 999 python:

    import operator as _urmp_op

    _URMP_UNK = python_object()

    _URMP_BIN = python_dict()
    for _urmp_k, _urmp_f in (("Add", _urmp_op.add), ("Sub", _urmp_op.sub),
                             ("Mult", _urmp_op.mul), ("Div", _urmp_op.truediv),
                             ("FloorDiv", _urmp_op.floordiv), ("Mod", _urmp_op.mod)):
        if hasattr(_urmi_ast, _urmp_k):
            _URMP_BIN[getattr(_urmi_ast, _urmp_k)] = _urmp_f

    _URMP_CMP = python_dict()
    for _urmp_k, _urmp_f in (("Eq", _urmp_op.eq), ("NotEq", _urmp_op.ne),
                             ("Lt", _urmp_op.lt), ("LtE", _urmp_op.le),
                             ("Gt", _urmp_op.gt), ("GtE", _urmp_op.ge),
                             ("Is", _urmp_op.is_), ("IsNot", _urmp_op.is_not),
                             ("In", lambda a, b: a in b),
                             ("NotIn", lambda a, b: a not in b)):
        if hasattr(_urmi_ast, _urmp_k):
            _URMP_CMP[getattr(_urmi_ast, _urmp_k)] = _urmp_f

    def _urmp_state():
        return _urm_kept("now_values", python_dict)

    def _urmp_bucket(key):
        st = _urmp_state()
        found = st.get(key)
        if found is None:
            found = python_dict()
            st[key] = found
        return found


    # ------------------------------------------------------------------
    # A read-only evaluator
    # ------------------------------------------------------------------

    def _urmp_parse(text):
        cache = _urmp_bucket("parse")
        try:
            return cache[text]
        except KeyError:
            pass
        try:
            tree = _urmi_ast.parse(text.strip(), mode="eval").body
        except Exception:
            tree = None
        cache[text] = tree
        return tree

    def _urmp_ev(node, target=None, cand=None, depth=0):
        """
        The value of an expression from the store as it is now - or, with
        `target`, as if that one name held `cand`. _URMP_UNK when it cannot
        tell. Only reads: the one call it makes is len().
        """

        if depth > 40 or node is None:
            return _URMP_UNK

        if isinstance(node, (_urmi_ast.Call, _urmi_ast.Compare)):
            flagname = _urmfl_name_of(node)
            if flagname is not None:
                if target is not None and flagname == target:
                    return cand
                value = urmfl_is_on(flagname)
                if value is None:
                    return _URMP_UNK
                rec = _urmp_state().get("deps")
                if rec is not None and len(rec) < 200:
                    rec[flagname] = value
                return value

        if isinstance(node, (_urmi_ast.Name, _urmi_ast.Attribute, _urmi_ast.Subscript)):
            if target is not None and _urmi_name(node) == target:
                return cand
            # While a panel is being worked out, remember every plain value it
            # read, so a cached panel is thrown away when one of them changes
            # (edit ainepoint, reopen aineroute: "you have 11" must not stay).
            rec = _urmp_state().get("deps")
            if rec is not None:
                value = _urmp_ev_inner(node, target, cand, depth)
                if len(rec) < 200 and isinstance(value, (bool, int, float, type(None)) + _urmi_text):
                    key = _urmi_name(node)
                    if key is not None:
                        rec[key] = value
                return value
        return _urmp_ev_inner(node, target, cand, depth)

    def _urmp_ev_inner(node, target, cand, depth):

        ok, value = _urmi_literal(node)
        if ok:
            return value

        try:
            if isinstance(node, _urmi_ast.Name):
                store = renpy.store.__dict__
                if node.id in store:
                    return store[node.id]
                return _URMP_UNK

            if isinstance(node, _urmi_ast.Attribute):
                base = _urmp_ev(node.value, target, cand, depth + 1)
                if base is _URMP_UNK:
                    return base
                return getattr(base, node.attr)

            if isinstance(node, _urmi_ast.Subscript):
                key = node.slice
                if hasattr(_urmi_ast, "Index") and isinstance(key, _urmi_ast.Index):
                    key = key.value
                if isinstance(key, _urmi_ast.Slice):
                    return _URMP_UNK
                base = _urmp_ev(node.value, target, cand, depth + 1)
                k = _urmp_ev(key, target, cand, depth + 1)
                if base is _URMP_UNK or k is _URMP_UNK:
                    return _URMP_UNK
                return base[k]

            if isinstance(node, _urmi_ast.BinOp):
                fn = _URMP_BIN.get(type(node.op))
                left = _urmp_ev(node.left, target, cand, depth + 1)
                right = _urmp_ev(node.right, target, cand, depth + 1)
                if fn is None or left is _URMP_UNK or right is _URMP_UNK:
                    return _URMP_UNK
                return fn(left, right)

            if isinstance(node, _urmi_ast.UnaryOp):
                inner = _urmp_ev(node.operand, target, cand, depth + 1)
                if inner is _URMP_UNK:
                    return inner
                if isinstance(node.op, _urmi_ast.Not):
                    return not inner
                if isinstance(node.op, _urmi_ast.USub):
                    return -inner
                if isinstance(node.op, _urmi_ast.UAdd):
                    return +inner
                return _URMP_UNK

            if isinstance(node, _urmi_ast.Compare):
                left = _urmp_ev(node.left, target, cand, depth + 1)
                if left is _URMP_UNK:
                    return left
                for op_node, comp in zip(node.ops, node.comparators):
                    fn = _URMP_CMP.get(type(op_node))
                    right = _urmp_ev(comp, target, cand, depth + 1)
                    if fn is None or right is _URMP_UNK:
                        return _URMP_UNK
                    if not fn(left, right):
                        return False
                    left = right
                return True

            if isinstance(node, _urmi_ast.BoolOp):
                unknown = False
                is_and = isinstance(node.op, _urmi_ast.And)
                result = is_and
                for part in node.values:
                    value = _urmp_ev(part, target, cand, depth + 1)
                    if value is _URMP_UNK:
                        unknown = True
                        continue
                    if is_and and not value:
                        return value
                    if not is_and and value:
                        return value
                    result = value
                if unknown:
                    return _URMP_UNK
                return result

            if isinstance(node, _urmi_ast.IfExp):
                test = _urmp_ev(node.test, target, cand, depth + 1)
                if test is _URMP_UNK:
                    return test
                return _urmp_ev(node.body if test else node.orelse, target, cand, depth + 1)

            if isinstance(node, _urmi_ast.Call):
                func = node.func
                if isinstance(func, _urmi_ast.Name) and func.id == "len" \
                        and len(node.args) == 1:
                    inner = _urmp_ev(node.args[0], target, cand, depth + 1)
                    if inner is _URMP_UNK:
                        return inner
                    return len(inner)
                return _URMP_UNK

        except Exception:
            return _URMP_UNK

        return _URMP_UNK

    def _urmp_value(name):
        if _urmfl_record(name) is not None:
            value = urmfl_is_on(name)
            return _URMP_UNK if value is None else value
        return _urmp_ev(_urmp_parse(name))
    def _urmfl_index():
        index = _urmi_index()
        if index is None or index.state != "ready" or not getattr(index, "flags", None):
            return None
        return index

    def _urmfl_record(name):
        index = _urmfl_index()
        if index is None or not isinstance(name, _urmi_text):
            return None
        return index.flags.get(name)

    def _urmfl_getters(index):
        found = getattr(index, "_urmflGetters", None)
        if found is None:
            found = python_dict()
            for fname, (role, coll, _attr) in index.helpers.items():
                if role == "get" and coll not in found:
                    found[coll] = fname
            index._urmflGetters = found
        return found

    def _urmfl_name_of(node):
        """The flag a test is, for true("x") and "x" in coll - else None."""

        index = _urmfl_index()
        if index is None:
            return None
        if isinstance(node, _urmi_ast.Call):
            if not isinstance(node.func, _urmi_ast.Name) or not node.args:
                return None
            ok, word = _urmi_literal(node.args[0])
            if not ok or not isinstance(word, _urmi_text):
                return None
            name = u'%s("%s")' % (node.func.id, word)
            return name if name in index.flags else None
        if isinstance(node, _urmi_ast.Compare) and len(node.ops) == 1 and \
                isinstance(node.ops[0], (_urmi_ast.In, _urmi_ast.NotIn)):
            ok, word = _urmi_literal(node.left)
            coll = _urmi_name(node.comparators[0])
            if not ok or not isinstance(word, _urmi_text) or coll is None:
                return None
            getter = _urmfl_getters(index).get(coll)
            name = u'%s("%s")' % (getter, word) if getter else u'"%s" in %s' % (word, coll)
            return name if name in index.flags else None
        return None

    def _urmfl_collection(rec):
        try:
            value = _urmp_ev(_urmp_parse(rec.coll))
        except Exception:
            return None
        if value is _URMP_UNK:
            return None
        return value

    def _urmfl_matches(rec, member):
        if rec.attr:
            return getattr(member, rec.attr, None) == rec.word
        return member == rec.word

    def urmfl_is_on(name):
        """True / False, or None when the game has not made the collection yet."""

        rec = _urmfl_record(name)
        if rec is None:
            return None
        coll = _urmfl_collection(rec)
        if coll is None:
            return False
        try:
            if isinstance(coll, python_dict):
                return bool(coll.get(rec.word))
            for member in coll:
                if _urmfl_matches(rec, member):
                    return True
            return False
        except Exception:
            return None

    def _urm_flag_truth(text):
        """
        A test whose only calls are flag tests the flags reading knows -
        true("x"), on_path("x") - worked out from the collections, without
        calling anything. None when any other call is in it, or when it
        cannot be told. Asked by _urm_truth (13_now) for a test with a call.
        """

        tree = _urmp_parse(text)
        if tree is None:
            return None
        for node in _urm_ast.walk(tree):
            if isinstance(node, _urm_ast.Call) and _urmfl_name_of(node) is None:
                return None
        value = _urmp_ev(tree)
        if value is _URMP_UNK:
            return None
        return bool(value)

# ---------------------------------------------------------------------------
# Take: an if-statement goes the way the player took
# ---------------------------------------------------------------------------
#
# The engine's side of Take on a way the game picks (13_now, the reader of
# what comes next, `_urm_take_way`): a list of [(if-statement, arm)], kept
# in our memory; when one of those if-statements runs, it goes down that
# arm (-1: none of its arms) instead of testing, once. Loading a save
# forgets it. Its own block: it changes the engine as the game loads, and
# the blocks a test loads for words and facts must not.

init 999 python:

    class _URMTakeState(python_object):
        def __init__(self):
            self.pending = python_list()   # [(if-statement, arm)], -1 = none matches

    def _urm_take_state():
        return _urm_kept("take", _URMTakeState)

    def _urm_take_due(node):
        """The arm for this if-statement now that it runs, used up."""

        pending = _urm_take_state().pending
        for i, (target, arm) in enumerate(pending):
            if target is node:
                del pending[i]
                return arm
        return None

    try:
        _urm_if_execute = renpy.ast.If.execute

        def _urm_if_taken(self):
            arm = _urm_take_due(self)
            if arm is None:
                return _urm_if_execute(self)
            entries = self.entries or ()
            if 0 <= arm < len(entries) and entries[arm][1]:
                target = entries[arm][1][0]
            else:
                target = self.next
            renpy.game.context().next_node = target

        if not getattr(renpy.ast.If.execute, "_urm_take", False):
            _urm_if_taken._urm_take = True
            renpy.ast.If.execute = _urm_if_taken
    except Exception as error:
        print("MRM: Take on a way the game picks stays off (%s)" % (error,))

    def _urm_take_forget():
        _urm_take_state().pending = python_list()

    if _urm_take_forget not in config.after_load_callbacks:
        config.after_load_callbacks.append(_urm_take_forget)
