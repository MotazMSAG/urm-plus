# ---------------------------------------------------------------------------
# The variable panel: what a value gets the player, and whether it is too late
# ---------------------------------------------------------------------------
#
# The first panel said where a name sits in the code - "found in 18 checks,
# 18 as on/off", file:line, "== 3 x2" - and a player cannot decide anything
# with that. This one answers what they opened the editor to ask:
#
#   * what does each value get me - which scenes, how much, what is said
#   * have I played that, is it still ahead of me in this scene
#   * which choices set it, and does the game change it on its own
#   * will my edit stick, and is it enough (the game may reset it, or the
#     big scene may also need something else)
#
# Everything comes from the index's nodes, read at the moment the dialog
# opens. Nothing the game defines is called: conditions are worked out by a
# small evaluator that only reads values, and gives up on any function call
# except len().
#
# What it must not claim, and the footer says so: uses inside the game's own
# functions and screens are invisible; "played" means seen on this computer
# in any playthrough; line counts include every nested branch, so they are
# "about"; story order across scenes is not knowable from the script, so the
# only order used is line order inside the one scene the player is in.
#
# Everything cached here lives on x52URM.Var, in URM's _constant store, and
# is built from python_* containers only - nothing reaches a save or the
# rollback log.

init 999 python:

    import re as _urmp_re
    import sys as _urmp_sys
    import operator as _urmp_op

    _URMP_UNK = python_object()
    _URMP_NOSET = python_object()

    _URMP_STATUS_RANK = python_dict()
    for _urmp_i, _urmp_k in enumerate(("later", "not", "never", "above", "", "played")):
        _URMP_STATUS_RANK[_urmp_k] = _urmp_i

    _URMP_STATUS_TEXT = python_dict()
    for _urmp_k, _urmp_t, _urmp_c in (
            ("later", "LATER IN THIS SCENE", "#e0a800"),
            ("not", "NOT PLAYED", "#43a047"),
            ("never", "PLAYED, NEVER SAW THIS", "#1e88e5"),
            ("above", "EARLIER IN THIS SCENE", "#9e9e9e"),
            ("played", "PLAYED", "#9e9e9e")):
        _URMP_STATUS_TEXT[_urmp_k] = "{color=%s}{b}%s{/b}{/color}" % (_urmp_c, _urmp_t)

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

    _URMP_NODE_BUDGET = 40000
    _URMP_BRANCH_CAP = 3000
    _URMP_ROWS_SHOWN = 10


    # Stand-ins until the Flags block below replaces them, so the panel works
    # on its own if that block is missing or failed.
    def _urmfl_record(name):
        return None

    def _urmfl_name_of(node):
        return None

    def urmfl_is_on(name):
        return None

    def _urmp_state():
        holder = x52URM.Var
        st = getattr(holder, "_urmpState", None)
        if st is None:
            st = python_dict()
            holder._urmpState = st
        return st

    def _urmp_bucket(key):
        st = _urmp_state()
        found = st.get(key)
        if found is None:
            found = python_dict()
            st[key] = found
        return found

    def _urmp_isnum(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _urmp_isint(value):
        return isinstance(value, int) and not isinstance(value, bool)

    def _urmp_letters(text):
        n = 0
        for ch in text:
            if ch.isalpha():
                n += 1
                if n >= 2:
                    return True
        return False


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

    def _urmp_src(node, depth=0):
        """An expression written back out, for the few that have no words."""

        if depth > 12 or node is None:
            return None
        name = _urmi_name(node)
        if name is not None:
            return name
        ok, value = _urmi_literal(node)
        if ok:
            return _urmi_show(value)
        if isinstance(node, _urmi_ast.BinOp):
            op = _URMI_BINOPS.get(type(node.op))
            left = _urmp_src(node.left, depth + 1)
            right = _urmp_src(node.right, depth + 1)
            if op and left and right:
                return "%s %s %s" % (left, op, right)
            return None
        if isinstance(node, _urmi_ast.UnaryOp):
            inner = _urmp_src(node.operand, depth + 1)
            if inner is None:
                return None
            if isinstance(node.op, _urmi_ast.Not):
                return "not " + inner
            if isinstance(node.op, _urmi_ast.USub):
                return "-" + inner
            return inner
        if isinstance(node, _urmi_ast.Compare):
            parts = python_list()
            first = _urmp_src(node.left, depth + 1)
            if first is None:
                return None
            parts.append(first)
            for op_node, comp in zip(node.ops, node.comparators):
                op = _URMI_OPS.get(type(op_node))
                right = _urmp_src(comp, depth + 1)
                if op is None or right is None:
                    return None
                parts.append(op)
                parts.append(right)
            return " ".join(parts)
        if isinstance(node, _urmi_ast.BoolOp):
            joiner = " and " if isinstance(node.op, _urmi_ast.And) else " or "
            parts = python_list()
            for value in node.values:
                text = _urmp_src(value, depth + 1)
                if text is None:
                    return None
                if isinstance(value, _urmi_ast.BoolOp):
                    text = "(" + text + ")"
                parts.append(text)
            return joiner.join(parts)
        if isinstance(node, _urmi_ast.Call):
            func = _urmi_name(node.func)
            if func is None:
                return None
            args = python_list()
            for arg in node.args:
                text = _urmp_src(arg, depth + 1)
                if text is None:
                    return None
                args.append(text)
            return "%s(%s)" % (func, ", ".join(args))
        return None

    def _urmp_names_in(node):
        found = python_list()
        _urmp_mentions(node, found)
        return found

    def _urmp_mentions(node, out):
        """_urmi_mentions, with each flag test - true("x") - as one name."""

        if isinstance(node, (_urmi_ast.Call, _urmi_ast.Compare)):
            flagname = _urmfl_name_of(node)
            if flagname is not None:
                out.append(flagname)
                return
        if isinstance(node, (_urmi_ast.Name, _urmi_ast.Attribute, _urmi_ast.Subscript)):
            name = _urmi_name(node)
            if name is not None:
                out.append(name)
                return
        if isinstance(node, _urmi_ast.Call):
            for arg in node.args:
                _urmp_mentions(arg, out)
            for kw in getattr(node, "keywords", None) or ():
                _urmp_mentions(kw.value, out)
            return
        for child in _urmi_ast.iter_child_nodes(node):
            _urmp_mentions(child, out)


    # ------------------------------------------------------------------
    # Script text, made fit to show
    # ------------------------------------------------------------------

    _URMP_TAG = _urmp_re.compile(r"\{\{|\{[^{}]*\}")
    _URMP_INTERP = _urmp_re.compile(r"\[\[|\[([A-Za-z_][\w.]*)(?:![a-z]+)?\]")

    def _urmp_interp(match):
        if match.group() == "[[":
            return "["
        value = _urmp_value(match.group(1))
        if isinstance(value, _urmi_text) and len(value) <= 40:
            return value
        name = getattr(value, "name", None) if value is not _URMP_UNK else None
        if isinstance(name, _urmi_text) and len(name) <= 40 and "[" not in name:
            return name
        return match.group()

    def _urmp_plain(text, limit=110):
        """Dialogue as plain words: tags dropped, [names] filled in, braces escaped."""

        try:
            text = u"%s" % (text,)
        except Exception:
            return u""
        text = _URMP_TAG.sub(lambda m: "{" if m.group() == "{{" else "", text)
        try:
            text = _URMP_INTERP.sub(_urmp_interp, text)
        except Exception:
            pass
        text = u" ".join(text.split())
        if len(text) > limit:
            text = text[:limit - 3].rstrip() + u"..."
        return text.replace("{", "{{")

    def _urmp_speaker(who):
        if not who:
            return None
        cache = _urmp_bucket("speakers")
        try:
            return cache[who]
        except KeyError:
            pass
        name = None
        raw = who.strip()
        if raw[:1] in ("'", '"') and raw[-1:] == raw[:1]:
            name = raw[1:-1]
        else:
            value = _urmp_value(raw)
            if value is not _URMP_UNK:
                found = getattr(value, "name", None)
                if isinstance(found, _urmi_text) and found.strip():
                    name = found
        if name is None:
            name = raw
        name = _urmp_plain(name, 30)
        cache[who] = name
        return name

    def _urmp_say_line(node, limit=110):
        text = _urmp_plain(getattr(node, "what", "") or "", limit)
        who = _urmp_speaker(getattr(node, "who", None))
        if who:
            return u'%s: "%s"' % (who, text)
        return u'"%s"' % (text,)

    def _urmp_link(name):
        if _urmfl_record(name) is not None:
            return u"{a=URMFlag:%s}%s{/a}" % (name, name.replace("{", "{{"))
        return u"{a=URMVarDialog:%s}%s{/a}" % (name, name.replace("{", "{{"))


    # ------------------------------------------------------------------
    # What a branch plays
    # ------------------------------------------------------------------

    class _URMPSum(python_object):
        def __init__(self):
            self.lines = 0
            self.pictures = 0
            self.first = None        # first say with real words
            self.first_node = None   # first say at all, for "seen"
            self.target = None       # where it jumps
            self.calls = python_list()
            self.writes = python_list()   # (name, op, ok, value)
            self.funcs = python_list()
            self.preview = python_list()
            self.truncated = False
            self.choice = False

    def _urmp_effects(source):
        """Assignments with literals and bare calls in a $ line, cached by text."""

        cache = _urmp_bucket("fx")
        try:
            return cache[source]
        except KeyError:
            pass
        writes = python_list()
        funcs = python_list()
        try:
            # The story graph's parse (rework move 9), read the panel's
            # way: only the text's own statements, in the order written.
            for event in _urmsg_py_top(_urmsg_py_parse(source)[1]):
                if event[0] == "w":
                    _kind, _depth, _top, name, op, ok, value, spread = event
                    if name is not None and not spread:
                        writes.append((name, op, ok, value))
                    continue
                _kind, _depth, _top, callee, _args, _names, attr, owner, coll = event
                if owner is not None and coll:
                    writes.append((owner, "." + attr, coll[0][0], coll[0][1]))
                elif callee is not None:
                    funcs.append(callee)
        except Exception:
            pass
        cache[source] = (writes, funcs)
        return (writes, funcs)

    def _urmp_walk(nodes, s, budget, depth, want):
        """Fill `s` from a block. True when the block ends here (jump/return)."""

        ast = renpy.ast
        for node in nodes or ():
            if budget[0] <= 0:
                s.truncated = True
                return True
            budget[0] -= 1

            if isinstance(node, ast.Translate):
                if _urmp_walk(node.block, s, budget, depth, want):
                    return True

            elif isinstance(node, ast.Say):
                s.lines += 1
                if s.first_node is None:
                    s.first_node = node
                if s.first is None and _urmp_letters(_urmp_plain(getattr(node, "what", "") or "", 200)):
                    s.first = _urmp_say_line(node)
                if len(s.preview) < want:
                    s.preview.append(_urmp_say_line(node, 140))

            elif isinstance(node, (ast.Show, ast.Scene)):
                s.pictures += 1
                if len(s.preview) < want:
                    if s.preview and s.preview[-1].startswith("(picture"):
                        s.preview[-1] = "(pictures)"
                    else:
                        s.preview.append("(picture)")

            elif isinstance(node, ast.Jump):
                if not getattr(node, "expression", False):
                    s.target = node.target
                    if len(s.preview) < want:
                        s.preview.append(u"\u2192 goes to %s" % (node.target,))
                return True

            elif isinstance(node, ast.Call):
                if not getattr(node, "expression", False):
                    s.calls.append(node.label)
                    if len(s.preview) < want:
                        s.preview.append(u"\u2192 plays %s, then comes back" % (node.label,))

            elif isinstance(node, ast.Python):
                source = getattr(getattr(node, "code", None), "source", None)
                if source:
                    writes, funcs = _urmp_effects(source)
                    for w in writes:
                        s.writes.append(w)
                        if len(s.preview) < want:
                            s.preview.append(_urmp_write_words(w))
                    for f in funcs:
                        s.funcs.append(f)
                        if len(s.preview) < want:
                            s.preview.append("(runs the game's code: %s)" % (f,))

            elif isinstance(node, ast.If):
                if depth < 6:
                    for _cond, block in node.entries:
                        _urmp_walk(block, s, budget, depth + 1, 0)

            elif isinstance(node, ast.Menu):
                s.choice = True
                if len(s.preview) < want:
                    texts = python_list()
                    for item in node.items:
                        if item[2] is not None and item[0]:
                            texts.append(u'"%s"' % _urmp_plain(item[0], 50))
                    s.preview.append(u"(a choice: %s)" % u" / ".join(texts[:4]))
                if depth < 6:
                    for item in node.items:
                        _urmp_walk(item[2], s, budget, depth + 1, 0)

            elif isinstance(node, ast.Return):
                return True

        return False

    def _urmp_write_words(w):
        name, op, ok, value = w
        if op == "=" and ok:
            if value is True:
                return "(turns %s ON)" % name
            if value is False:
                return "(turns %s OFF)" % name
            return "(sets %s to %s)" % (name, _urmp_plain(_urmi_show(value), 40))
        if op in ("+=", "-=") and ok and _urmp_isnum(value):
            return "(%s %s%s)" % (name, "+" if op == "+=" else "-", _urmi_show(value))
        return "(changes %s)" % name

    def _urmp_summary(block, budget, want=0):
        s = _URMPSum()
        if block:
            local = python_list()
            local.append(min(budget[0], _URMP_BRANCH_CAP))
            before = local[0]
            _urmp_walk(block, s, local, 0, want)
            budget[0] -= before - local[0]
            if local[0] <= 0:
                s.truncated = True
        return s

    def _urmp_label_size(index, label, budget):
        """Lines a jump target plays: its block, or the statements after it."""

        cache = _urmp_bucket("labelsize")
        key = (id(index), label)
        try:
            return cache[key]
        except KeyError:
            pass
        node = index.labels.get(label)
        s = _URMPSum()
        if node is not None:
            local = python_list()
            local.append(min(budget[0], 2000))
            before = local[0]
            if getattr(node, "block", None):
                _urmp_walk(node.block, s, local, 0, 0)
            else:
                cur = getattr(node, "next", None)
                one = python_list()
                one.append(None)
                while cur is not None and local[0] > 0:
                    if isinstance(cur, renpy.ast.Label):
                        break
                    one[0] = cur
                    if _urmp_walk(one, s, local, 0, 0):
                        break
                    cur = getattr(cur, "next", None)
            budget[0] -= before - local[0]
        cache[key] = s.lines
        return s.lines

    def _urmp_size_words(s, index, budget):
        if s.lines:
            if s.lines == 1:
                text = "1 line"
            else:
                text = "about %d lines" % s.lines
            if s.truncated:
                text = "at least %d lines" % s.lines
            return text
        if s.target:
            n = _urmp_label_size(index, s.target, budget)
            if n == 1:
                return "goes to %s (1 line there)" % s.target
            if n:
                return "goes to %s (about %d lines there)" % (s.target, n)
            return "goes to %s" % s.target
        if s.calls:
            return "plays %s" % s.calls[0]
        if s.pictures:
            return "pictures only"
        return "no dialogue"

    def _urmp_weight(s, index, budget):
        """How much a branch plays, counting what a jump leads into."""

        if s.lines:
            return s.lines
        if s.target:
            return _urmp_label_size(index, s.target, budget)
        return 0


    # ------------------------------------------------------------------
    # Conditions in words
    # ------------------------------------------------------------------

    def _urmp_opwords(op, lit):
        """(words, value that satisfies it or NOSET) for `<name> op lit`."""

        if op in ("==", "is"):
            if lit is True:
                return ("ON", True)
            if lit is False:
                return ("OFF", False)
        if op in ("!=", "is not"):
            if lit is True:
                return ("OFF", False)
            if lit is False:
                return ("ON", True)
        if lit is None:
            if op in ("==", "is"):
                return ("empty (None)", None)
            if op in ("!=", "is not"):
                return ("not empty", _URMP_NOSET)
        if isinstance(lit, _urmi_text):
            shown = _urmp_plain(lit, 60)
            if op == "==":
                return (u'"%s"' % shown, lit)
            if op == "!=":
                return (u'anything but "%s"' % shown, _URMP_NOSET)
        if _urmp_isnum(lit):
            shown = _urmi_show(lit)
            if op == "==":
                return ("exactly %s" % shown, lit)
            if op == "!=":
                return ("anything but %s" % shown, _URMP_NOSET)
            if op == ">=":
                return ("%s or more" % shown, lit)
            if op == "<=":
                return ("%s or less" % shown, lit)
            if op == ">":
                if _urmp_isint(lit):
                    return ("%d or more" % (lit + 1), lit + 1)
                return ("more than %s" % shown, _URMP_NOSET)
            if op == "<":
                if _urmp_isint(lit):
                    return ("%d or less" % (lit - 1), lit - 1)
                return ("less than %s" % shown, _URMP_NOSET)
        if op in ("in", "not in") and isinstance(lit, (list, tuple)):
            shown = ", ".join(_urmp_plain(_urmi_show(v), 30) for v in lit[:6])
            if op == "in":
                return ("one of %s" % shown, lit[0] if lit else _URMP_NOSET)
            return ("none of %s" % shown, _URMP_NOSET)
        return (None, _URMP_NOSET)

    def _urmp_simple(atom, target):
        """
        (words, set value) when `atom` is a plain test of `target` - flag,
        not flag, target op literal, "x" in target - else None.
        """

        flagname = _urmfl_name_of(atom) if isinstance(atom, (_urmi_ast.Call, _urmi_ast.Compare)) else None
        if flagname is not None:
            if flagname != target:
                return None
            if isinstance(atom, _urmi_ast.Compare) and isinstance(atom.ops[0], _urmi_ast.NotIn):
                return ("OFF", False)
            return ("ON", True)
        if isinstance(atom, _urmi_ast.UnaryOp) and isinstance(atom.op, _urmi_ast.Not) and \
                isinstance(atom.operand, (_urmi_ast.Call, _urmi_ast.Compare)):
            flagname = _urmfl_name_of(atom.operand)
            if flagname is not None:
                return ("OFF", False) if flagname == target else None
        if isinstance(atom, (_urmi_ast.Name, _urmi_ast.Attribute, _urmi_ast.Subscript)):
            if _urmi_name(atom) == target:
                return ("ON", True)
            return None
        if isinstance(atom, _urmi_ast.UnaryOp) and isinstance(atom.op, _urmi_ast.Not):
            if _urmi_name(atom.operand) == target:
                return ("OFF", False)
            return None
        if isinstance(atom, _urmi_ast.Compare) and len(atom.ops) == 1:
            op = _URMI_OPS.get(type(atom.ops[0]))
            left, right = atom.left, atom.comparators[0]
            if op in ("in", "not in"):
                ok, token = _urmi_literal(left)
                if ok and _urmi_name(right) == target:
                    shown = _urmp_plain(_urmi_show(token), 50)
                    if op == "in":
                        return ("contains %s" % shown, _URMP_NOSET)
                    return ("doesn't contain %s" % shown, _URMP_NOSET)
                if _urmi_name(left) == target and isinstance(right, (_urmi_ast.List, _urmi_ast.Tuple)):
                    values = python_list()
                    for elt in right.elts:
                        ok, v = _urmi_literal(elt)
                        if not ok:
                            return None
                        values.append(v)
                    words, value = _urmp_opwords(op, values)
                    if words:
                        return (words, value)
                return None
            if op is None:
                return None
            if _urmi_name(left) == target:
                ok, lit = _urmi_literal(right)
                if ok:
                    words, value = _urmp_opwords(op, lit)
                    if words:
                        return (words, value)
            if _urmi_name(right) == target:
                ok, lit = _urmi_literal(left)
                if ok:
                    words, value = _urmp_opwords(_URMI_FLIP.get(op, op), lit)
                    if words:
                        return (words, value)
        return None

    def _urmp_band(atoms, target, now):
        """
        Words for a numeric requirement that is not a plain literal test -
        love < hard_love - 30 - by trying whole numbers with everything else
        at its value now. (words, set value) or None.
        """

        lits = python_list()
        others = python_list()
        for atom in atoms:
            for sub in _urmi_ast.walk(atom):
                ok, v = _urmi_literal(sub)
                if ok and _urmp_isnum(v):
                    lits.append(v)
            for name in _urmp_names_in(atom):
                if name != target and name not in others:
                    others.append(name)
        spread = python_list()
        spread.append(100)
        for v in lits:
            spread.append(abs(int(v)))
        for name in others:
            v = _urmp_value(name)
            if _urmp_isnum(v):
                spread.append(abs(int(v)) * 2)
        if _urmp_isnum(now):
            spread.append(abs(int(now)) * 2)
        hi = min(max(spread) + 5, 600)
        lo = -5
        for v in lits:
            if v < 0:
                lo = max(int(v) - 5, -600)

        runs = python_list()
        start = None
        for c in range(lo, hi + 1):
            passed = True
            for atom in atoms:
                r = _urmp_ev(atom, target, c)
                if r is _URMP_UNK:
                    return None
                if not r:
                    passed = False
                    break
            if passed and start is None:
                start = c
            elif not passed and start is not None:
                runs.append((start, c - 1))
                start = None
        if start is not None:
            runs.append((start, hi))

        if not runs:
            words, value = "never, with things as they are", _URMP_NOSET
        elif len(runs) > 1:
            return None
        else:
            a, b = runs[0]
            if a == lo and b == hi:
                words, value = "any number, with things as they are", _URMP_NOSET
            elif a == lo:
                words, value = "%d or less" % b, b
            elif b == hi:
                words, value = "%d or more" % a, a
            elif a == b:
                words, value = "exactly %d" % a, a
            else:
                words, value = "%d to %d" % (a, b), a

        if others:
            parts = python_list()
            for name in others[:2]:
                v = _urmp_value(name)
                if v is _URMP_UNK:
                    parts.append(name)
                else:
                    parts.append("%s at %s" % (name, _urmp_plain(_urmi_show(v), 20)))
            words += " (with %s now)" % " and ".join(parts)
        return (words, value)

    def _urmp_have(name):
        v = _urmp_value(name)
        if v is _URMP_UNK:
            return None
        if v is True:
            return "it's ON"
        if v is False:
            return "it's OFF"
        if v is None:
            return "it's empty"
        if _urmp_isnum(v) or isinstance(v, _urmi_text):
            return "you have %s" % _urmp_plain(_urmi_show(v), 30)
        return None

    def _urmp_need(atom):
        """Another requirement in words, with its name linked: (words, met now)."""

        met = _urmp_ev(atom)
        names = _urmp_names_in(atom)
        words = None
        if len(names) == 1:
            simple = _urmp_simple(atom, names[0])
            if simple is not None:
                words = u"%s %s" % (_urmp_link(names[0]), simple[0])
                have = _urmp_have(names[0])
                if have and met is not True:
                    words += " (%s)" % have
        if words is None:
            text = _urmp_src(atom)
            if text is None:
                words = "another condition (see Code)"
            else:
                words = u"%s" % _urmp_plain(text, 80)
        return (words, met)


    # ------------------------------------------------------------------
    # One row per place the game checks the name
    # ------------------------------------------------------------------

    class _URMPRow(python_object):
        pass

    def _urmp_names_of(index, cond):
        cache = _urmp_bucket("condnames")
        try:
            return cache[cond]
        except KeyError:
            pass
        names = python_set()
        for kind, a, b, _c in index._condition(cond):
            if kind == "token":
                names.add(b)
            elif kind != "call":
                names.add(a)
        tree = _urmp_parse(cond)
        if tree is not None and index.flags:
            for name in _urmp_names_in(tree):
                names.add(name)
        cache[cond] = names
        return names

    def _urmp_scene(index, node, filename, line):
        # The story graph's one rule for "which scene is this in" (idea 1).
        return _urmsg_label_of(index, node, filename, line)

    def _urmp_scene_name(scene, filename):
        if isinstance(scene, _urmi_text):
            return scene
        return u"early in %s" % ((filename or "?").split("/")[-1],)

    def _urmp_rows(index, name):
        rows = python_list()
        done = python_set()
        ast = renpy.ast
        for site, _op, _lit in index.reads.get(name) or ():
            nid = site[2]
            if nid in done:
                continue
            done.add(nid)
            node = index.nodes.get(nid)
            if node is None:
                continue
            fn = getattr(node, "filename", "?")
            ln = getattr(node, "linenumber", 0)
            if (fn, ln) in done:
                continue
            done.add((fn, ln))
            scene = _urmp_scene(index, node, fn, ln)
            scene_text = _urmp_scene_name(scene, fn)

            def make(kind, cond, block):
                r = _URMPRow()
                r.node = node
                r.kind = kind
                r.cond = cond
                r.block = block
                r.other = None
                r.other_kind = None
                r.option = None
                r.scene = scene_text
                r.label = scene
                r.file = fn
                r.line = ln
                return r

            if isinstance(node, ast.If):
                entries = node.entries
                for i, (cond, block) in enumerate(entries):
                    if not cond or cond.strip() == "True":
                        continue
                    if name not in _urmp_names_of(index, cond):
                        continue
                    r = make("if", cond, block)
                    if i + 1 < len(entries):
                        nxt_cond, nxt_block = entries[i + 1]
                        if nxt_cond.strip() == "True":
                            r.other = nxt_block
                            r.other_kind = "else"
                        else:
                            r.other_kind = "elif"
                    rows.append(r)
            elif isinstance(node, ast.Menu):
                for item in node.items:
                    cond = item[1]
                    if not cond or cond.strip() == "True" or item[2] is None:
                        continue
                    if name not in _urmp_names_of(index, cond):
                        continue
                    r = make("option", cond, item[2])
                    r.option = item[0]
                    rows.append(r)
            elif isinstance(node, ast.While):
                rows.append(make("loop", node.condition, node.block))
        return rows

    def _urmp_atoms(cond, name):
        tree = _urmp_parse(cond)
        if tree is None:
            return (None, python_list(), python_list())
        if isinstance(tree, _urmi_ast.BoolOp) and isinstance(tree.op, _urmi_ast.And):
            parts = tree.values
        else:
            parts = python_list()
            parts.append(tree)
        mine = python_list()
        others = python_list()
        for part in parts:
            if name in _urmp_names_in(part) or _urmp_simple(part, name) is not None:
                mine.append(part)
            else:
                others.append(part)
        return (tree, mine, others)

    def _urmp_requirement(row, name, now):
        """(words, set value, sort number) for this variable's part of the row."""

        cache = _urmp_bucket("req")
        key = (row.cond, name)
        if key in cache:
            return cache[key]
        _tree, mine, _others = _urmp_atoms(row.cond, name)
        result = None
        if len(mine) == 1:
            simple = _urmp_simple(mine[0], name)
            if simple is not None:
                result = simple
        if result is None and mine and (_urmp_isnum(now) or now is _URMP_UNK):
            result = _urmp_band(mine, name, now)
        if result is None:
            text = _urmp_src(mine[0]) if len(mine) == 1 else None
            if text:
                result = (u"when %s" % _urmp_plain(text, 80), _URMP_NOSET)
            else:
                result = ("a condition shown in Code", _URMP_NOSET)
        words, value = result
        sort = value if _urmp_isnum(value) else None
        out = (words, value, sort)
        cache[key] = out
        return out


    # ------------------------------------------------------------------
    # Where the player is, and what they have seen
    # ------------------------------------------------------------------

    def _urmp_current(index):
        """(node name, scene, filename, line) of the statement the game is on."""

        try:
            name = renpy.game.context().current
        except Exception:
            return None
        node = _urmsg_here()
        if node is None:
            return None
        fn = getattr(node, "filename", None)
        ln = getattr(node, "linenumber", 0)
        return (name, _urmp_scene(index, node, fn, ln), fn, ln, id(node))

    class _URMPSeen(python_object):
        def __init__(self):
            self.labels = python_dict()
            try:
                self.ever = renpy.game.persistent._seen_ever
            except Exception:
                self.ever = None
            try:
                if _preferences.language is not None:
                    self.ever = None
            except Exception:
                pass
            try:
                self.chosen = renpy.game.persistent._chosen
            except Exception:
                self.chosen = None

        def label(self, label):
            if not isinstance(label, _urmi_text):
                return None
            try:
                return self.labels[label]
            except KeyError:
                pass
            if len(self.labels) > 400:
                return None
            found = urm_seen(label)
            self.labels[label] = found
            return found

        def node(self, node):
            if self.ever is None or node is None:
                return None
            try:
                return _urm_was_seen(node.name, self.ever)
            except Exception:
                return None

        def picked(self, menu, option):
            if self.chosen is None or not option or "[" in option:
                return None
            try:
                return (menu.name, option) in self.chosen
            except Exception:
                return None

    def _urmp_status(scene, filename, line, first_node, cur, seen):
        if cur is not None and scene is not None and scene == cur[1] and filename == cur[2]:
            if line > cur[3]:
                return "later"
            return "above"
        played = seen.label(scene)
        if played is False:
            return "not"
        if played is True:
            saw = seen.node(first_node)
            if saw is False:
                return "never"
            return "played"
        return ""


    # ------------------------------------------------------------------
    # Who sets it
    # ------------------------------------------------------------------

    class _URMPWrite(python_object):
        pass

    def _urmp_question(index, menu):
        """The line the choice answers: the menu's own caption, or the say before it."""

        for item in menu.items:
            if item[2] is None and item[0]:
                return _urmp_plain(item[0], 90)
        link = index.parent.get(id(menu))
        if link is None:
            return None
        parent = link[0]
        ast = renpy.ast
        if isinstance(parent, ast.If):
            blocks = [b for _c, b in parent.entries]
        elif isinstance(parent, ast.Menu):
            blocks = [i[2] for i in parent.items if i[2]]
        else:
            blocks = [getattr(parent, "block", None) or ()]
        for block in blocks:
            for i, n in enumerate(block):
                if n is menu:
                    for back in reversed(block[max(0, i - 4):i]):
                        if isinstance(back, ast.Say):
                            return _urmp_say_line(back, 90)
                        if isinstance(back, ast.Translate):
                            for s in back.block or ():
                                if isinstance(s, ast.Say):
                                    return _urmp_say_line(s, 90)
                    return None
        return None

    def _urmp_writes(index, name):
        """Every assignment of `name`, with the choice or the condition behind it."""

        out = python_list()
        done = python_set()
        for site, op, value, _text in index.writes.get(name) or ():
            key = (site[0], site[1], op, repr(value))
            if key in done:
                continue
            done.add(key)
            node = index.nodes.get(site[2])
            w = _URMPWrite()
            w.op = op
            w.value = value
            w.ok = value is not None or op == "="
            w.node = node
            w.file = site[0]
            w.line = site[1]
            w.label = _urmp_scene(index, node, site[0], site[1])
            w.scene = _urmp_scene_name(w.label, site[0])
            w.menu = None
            w.option = None
            w.cond = None
            w.unless = None
            for parent, kind, extra in _urmsg_climb(index.parent, node):
                if kind == "option":
                    w.menu = parent
                    w.option = extra
                    break
                if kind == "if" and w.cond is None and w.unless is None:
                    if extra and extra.strip() != "True":
                        w.cond = extra
                    else:
                        before = python_list()
                        for c, _b in parent.entries:
                            if c and c.strip() != "True":
                                before.append(c)
                        if before:
                            w.unless = before
                if kind == "label":
                    break
            out.append(w)
        return out

    def _urmp_value_ok(w):
        """Whether the literal in a write is known - None from the index means 'computed'."""

        if w.op == "=":
            return w.value is not None or _urmp_assign_none(w)
        return w.value is not None

    def _urmp_assign_none(w):
        node = w.node
        source = getattr(getattr(node, "code", None), "source", "") or ""
        return "None" in source

    def _urmp_effect(w, now, boolish):
        """(words, set value) for what one write does to the name."""

        op, value = w.op, w.value
        ok = _urmp_value_ok(w)
        if op == "=":
            if not ok:
                return ("changes it (worked out by the game)", _URMP_NOSET)
            if boolish and value in (True, False) and not isinstance(value, _urmi_text):
                return ("turns it ON" if value else "turns it OFF", value)
            return ("sets it to %s" % _urmp_plain(_urmi_show(value), 50), value)
        if op in ("+=", "-=") and ok and _urmp_isnum(value):
            delta = value if op == "+=" else -value
            sign = "+" if delta >= 0 else "-"
            text = "%s%s" % (sign, _urmi_show(abs(delta)))
            if _urmp_isnum(now):
                return ("%s (you'd have %s)" % (text, _urmi_show(now + delta)), now + delta)
            return (text, _URMP_NOSET)
        if op in (".append", ".add") and ok:
            return ("adds %s" % _urmp_plain(_urmi_show(value), 40), _URMP_NOSET)
        if op in (".remove", ".discard") and ok:
            return ("removes %s" % _urmp_plain(_urmi_show(value), 40), _URMP_NOSET)
        return ("changes it", _URMP_NOSET)

    def _urmp_effect_named(w, name):
        """What a write does, as a phrase that names the variable."""

        op, value = w.op, w.value
        ok = _urmp_value_ok(w)
        if op == "=" and ok:
            if value is True:
                return "turns %s ON" % name
            if value is False:
                return "turns %s OFF" % name
            return "sets %s to %s" % (name, _urmp_plain(_urmi_show(value), 40))
        if op in ("+=", "-=") and ok and _urmp_isnum(value):
            up = (op == "+=") == (value >= 0)
            return "%s %s by %s" % ("raises" if up else "lowers", name, _urmi_show(abs(value)))
        if op in (".append", ".add") and ok:
            return "adds %s to %s" % (_urmp_plain(_urmi_show(value), 40), name)
        if op in (".remove", ".discard") and ok:
            return "removes %s from %s" % (_urmp_plain(_urmi_show(value), 40), name)
        return "changes %s" % name

    def _urmp_cond_words(cond, skip=None):
        """A whole condition in words, every name linked."""

        tree = _urmp_parse(cond)
        if tree is None:
            return _urmp_plain(cond, 80)
        if isinstance(tree, _urmi_ast.BoolOp) and isinstance(tree.op, _urmi_ast.And):
            parts = tree.values
        else:
            parts = python_list()
            parts.append(tree)
        words = python_list()
        for part in parts:
            words.append(_urmp_need(part)[0])
        return " and ".join(words)

    def _urmp_mass_labels(index):
        """Labels that set 15+ different names at once: chapter select, skip menus."""

        cache = _urmp_bucket("mass")
        key = id(index), index.finished_at
        if cache.get("key") == key:
            return cache["labels"]
        tally = python_dict()
        total = 0
        for name, bucket in index.writes.items():
            total += len(bucket)
            if total > 60000:
                break
            for site, _op, _v, _t in bucket:
                label = _urmp_scene(index, index.nodes.get(site[2]), site[0], site[1])
                if label is None:
                    continue
                names = tally.get(label)
                if names is None:
                    names = python_set()
                    tally[label] = names
                names.add(name)
        found = python_set()
        for label, names in tally.items():
            if len(names) >= 15:
                found.add(label)
        cache["key"] = key
        cache["labels"] = found
        return found

    def _urmp_function_mentions(name):
        """Names of the game's own functions whose code mentions `name`."""

        cache = _urmp_bucket("funcs")
        if "map" not in cache:
            import types
            found = python_dict()
            count = 0
            try:
                for fname, value in python_list(renpy.store.__dict__.items()):
                    if not isinstance(value, types.FunctionType):
                        continue
                    count += 1
                    if count > 5000:
                        break
                    code = getattr(value, "__code__", None) or getattr(value, "func_code", None)
                    stack = python_list()
                    stack.append(code)
                    seen_names = python_set()
                    while stack:
                        c = stack.pop()
                        if c is None:
                            continue
                        for n in c.co_names:
                            seen_names.add(n)
                        for const in c.co_consts:
                            if hasattr(const, "co_names"):
                                stack.append(const)
                    if fname.startswith("_urm") or fname.startswith("urm"):
                        continue
                    for n in seen_names:
                        bucket = found.get(n)
                        if bucket is None:
                            bucket = python_list()
                            found[n] = bucket
                        if len(bucket) < 6:
                            bucket.append(fname)
            except Exception:
                pass
            cache["map"] = found
        base = _urmp_re.split(r"[.\[]", name, 1)[0]
        return cache["map"].get(base) or ()


