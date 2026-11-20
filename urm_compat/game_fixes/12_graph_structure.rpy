    # ------------------------------------------------------------------
    # The gate chain
    # ------------------------------------------------------------------

    def _urmsg_chain(first_if, limit, blocks, step, max_ifs=8):
        """
        Every gate ahead, in the order they are tested, as a _URMSGChain.
        blocks(statement) says whether a statement waits for the player;
        step(statement) gives the next one, None, or _URMSG_LOST.

        Where the step is lost - a jump or a call that cannot be followed -
        the chain keeps the gates it found and closes with the one record
        for that (idea 2 and idea 8): `lost` is set, and the last step is
        ("tail", None, _URMSG_DYN_JUMP or _URMSG_DYN_CALL).
        """

        c = _URMSGChain()
        node = first_if
        ifs = 0

        while ifs < max_ifs:
            ifs += 1
            closed = False
            arm = 0

            for cond, block in (getattr(node, "entries", None) or ()):
                if _urmsg_is_else(cond):
                    c.steps.append(("else", None, block))
                    c.meta.append((node, arm))
                    closed = True
                    break
                c.steps.append(("gate", cond, block))
                c.meta.append((node, arm))
                arm += 1

            if closed:
                return c

            following = step(node)
            if following is _URMSG_LOST:
                c.lost = True
                return c

            node = None
            ahead = following
            n = 0

            while n < limit:
                n += 1
                if ahead is None:
                    break
                if _urmsg_kind(ahead) == _URMSG_K_IF:
                    node = ahead
                    break
                if blocks(ahead):
                    break
                if _urmsg_kind(ahead) == _URMSG_K_JUMP and getattr(ahead, "expression", False):
                    c.live = True
                gone = ahead
                ahead = step(ahead)
                if ahead is _URMSG_LOST:
                    c.lost = True
                    c.steps.append(("tail", None,
                                    _urmsg_unfollowed(gone) or _URMSG_DYN_JUMP))
                    c.meta.append((None, -1))
                    return c

            if node is None:
                tail = ""
                try:
                    at = following
                    n = 0
                    while n < limit:
                        n += 1
                        if at is None:
                            break
                        text = _urmsg_stmt_text(at)
                        if text is not None:
                            tail = text
                            break
                        if blocks(at):
                            break
                        if _urmsg_kind(at) == _URMSG_K_JUMP and getattr(at, "expression", False):
                            c.live = True
                        at = step(at)
                        if at is _URMSG_LOST:
                            break
                except Exception:
                    tail = ""
                if tail:
                    c.steps.append(("tail", None, tail))
                    c.meta.append((None, -1))
                return c

        c.cut = True
        return c

    def _urmsg_gate_states(steps, truth):
        """
        For each step, ("runs" | "unknown" | "dead", gate number or 0): which
        gate fires, given what is true now. truth(cond) is asked only while
        no earlier gate has fired.
        """

        out = python_list()
        fired = False
        unknown = False
        number = 0

        for kind, cond, _payload in steps:
            if kind == "gate":
                number += 1
                t = None if fired else truth(cond)
                if t is None and not fired:
                    unknown = True
                runs = (t is True and not fired and not unknown)
                if runs:
                    fired = True
                    out.append(("runs", number))
                elif unknown and not fired:
                    out.append(("unknown", number))
                else:
                    out.append(("dead", number))
            else:
                if fired:
                    out.append(("dead", 0))
                elif unknown:
                    out.append(("unknown", 0))
                else:
                    out.append(("runs", 0))
                fired = True

        return out

    # ------------------------------------------------------------------
    # Structure: what sits in what (M8)
    # ------------------------------------------------------------------
    #
    # The script index links every statement to the block it sits in and
    # records what every condition tests; the map, the panel, the gallery
    # switch, the skip rule and the branch tracker then climb those links
    # ("which label is this in", "which choice gave this"). The four
    # functions below are the one copy of how a statement's blocks and
    # tests are listed and how the links are climbed; each caller keeps
    # its own question and its own fallback.
    #
    # They are PURE: they read no graph state, no kind table and no label,
    # because the index calls the first two from its own thread
    # (tests/check_graph.py holds them to it).

    def _urmsg_children(node):
        """
        The blocks a statement holds, as (kind, arm, extra, members):
        ("if", i, test, block) per arm of an if; ("option", i, caption,
        block) per item of a menu; ("label" or "while", -1, name, block);
        and for any other statement with a block ("block", -1, None,
        members), members being only what is a statement in it.
        """

        ast = renpy.ast
        out = python_list()

        if isinstance(node, ast.If):
            arm = 0
            for cond, block in node.entries:
                out.append(("if", arm, cond, block or ()))
                arm += 1
        elif isinstance(node, ast.Menu):
            arm = 0
            for item in node.items:
                out.append(("option", arm, item[0], item[2] or ()))
                arm += 1
        elif isinstance(node, (ast.Label, ast.While)):
            out.append((type(node).__name__.lower(), -1,
                        getattr(node, "name", None),
                        getattr(node, "block", None) or ()))
        else:
            members = python_list()
            for child in getattr(node, "block", None) or ():
                if isinstance(child, ast.Node):
                    members.append(child)
            if members:
                out.append(("block", -1, None, tuple(members)))

        return tuple(out)

    def _urmsg_conds(node):
        """
        The tests a statement makes, as (arm, test, caption or None): one
        per arm of an if, one per item of a menu (arm is its place among
        the items), one for a while. Nothing for any other statement.
        """

        ast = renpy.ast
        out = python_list()

        if isinstance(node, ast.If):
            arm = 0
            for cond, _block in node.entries:
                out.append((arm, cond, None))
                arm += 1
        elif isinstance(node, ast.Menu):
            arm = 0
            for item in node.items:
                out.append((arm, item[1], item[0]))
                arm += 1
        elif isinstance(node, ast.While):
            out.append((-1, node.condition, None))

        return tuple(out)

    # ------------------------------------------------------------------
    # A game played in a translation (idea 14, design fix C13)
    # ------------------------------------------------------------------
    #
    # In a translated game the line on screen is a statement of the
    # language file (tl/<language>/...). Nothing in the script leads into
    # that file and its blocks sit under no label, so a reader that starts
    # from the line on screen found no scene for it. One rule: such a
    # statement stands for a statement of the original script - its
    # "default twin" - and everything that asks what a statement sits in
    # asks that of the twin.

    def _urmsg_rep(node):
        """
        The first statement at or after `node` that reports itself when it
        runs. Translate and EndTranslate report on 7.3-7.5 and not on later
        engines, so they are stepped over everywhere.
        """

        steps = 0
        while node is not None and steps < 24:
            steps += 1
            if _urmsg_kind(node) == _URMSG_K_TRANS:
                block = getattr(node, "block", None)
                node = block[0] if block else getattr(node, "next", None)
            elif type(node).__name__ == "EndTranslate":
                node = getattr(node, "next", None)
            else:
                return node
        return node

    def _urmsg_tl(language):
        """{id(statement in a translation block of this language):
        (statement, identifier)}, remembered for one language at a time
        until the script changes."""

        g = _urmsg_graph()
        if g.tl is not None and g.tl[0] == language:
            return g.tl[1]

        table = python_dict()
        try:
            items = renpy.game.script.translator.language_translates
            for key in items:
                if key[1] != language:
                    continue
                block = getattr(items[key], "block", None)
                if not block:
                    continue
                todo = python_list(block)
                count = 0
                while todo and count < 64:
                    count += 1
                    child = todo.pop()
                    table[id(child)] = (child, key[0])
                    sub = getattr(child, "block", None)
                    if sub:
                        todo.extend(sub)
        except Exception:
            pass

        g.tl = (language, table)
        return table

    def _urmsg_default_twin(node):
        """
        The statement of the original script that a statement of the
        language being played stands for; any other statement is itself,
        and so is every statement while no translation is being played.
        """

        if node is None:
            return None
        try:
            language = renpy.game.preferences.language
        except Exception:
            language = None
        if language is None:
            return node

        try:
            ident = None
            if getattr(node, "language", None) is not None and getattr(node, "identifier", None):
                ident = node.identifier
            else:
                hit = _urmsg_tl(language).get(id(node))
                if hit is not None and hit[0] is node:
                    ident = hit[1]
            if ident is None:
                return node
            defaults = renpy.game.script.translator.default_translates
            d = defaults.get(ident)
            if d is None:
                d = defaults.get(ident.replace(".", "_"))
            if d is None:
                return node
            return _urmsg_rep(d) or node
        except Exception:
            return node

    def _urmsg_climb(parents, node, limit=200):
        """
        The links from a statement upward, nearest first: each is the
        index's (container, kind, extra). Stops where a statement has no
        link, and after `limit` links. A statement of the language being
        played is climbed from its twin in the original script
        (_urmsg_default_twin).
        """

        out = python_list()
        cur = _urmsg_default_twin(node)
        n = 0
        while cur is not None and n < limit:
            n += 1
            link = parents.get(id(cur))
            if link is None:
                break
            out.append(link)
            cur = link[0]
        return out

    def _urmsg_block_link(parents, node):
        """The link of the block a statement sits in; a line inside a
        translation block sits where that block does."""

        link = parents.get(id(node))
        if link and isinstance(link[0], renpy.ast.Translate):
            link = parents.get(id(link[0]))
        return link

    def _urmsg_label_of(index, node, filename=None, line=None):
        """
        The scene (label) of a statement - the one rule for every reader:
        the label its chain of containers reaches. Only when the chain
        reaches none (a script whose label bodies are not indented, or no
        statement at hand) is the line asked: index.label_at, which never
        answers with a label nested in an earlier scene unless that label
        holds the line.
        """

        twin = _urmsg_default_twin(node)
        if twin is not node:
            # A line of the language being played: the scene, and the line
            # asked when no container reaches one, are its twin's.
            node = twin
            filename = None
        for _parent, kind, extra in _urmsg_climb(index.parent, node):
            if kind == "label" and isinstance(extra, _urmsg_texts):
                return extra
        if filename is None and node is not None:
            filename = getattr(node, "filename", None)
            line = getattr(node, "linenumber", 0)
        return index.label_at(filename, line)

    def _urmsg_last_line(node, limit=200):
        """The line of the last statement a statement holds; its own line
        when it holds none. PURE: the index asks on its own thread."""

        best = getattr(node, "linenumber", 0)
        cur = node
        n = 0
        while cur is not None and n < limit:
            n += 1
            last = None
            for _kind, _arm, _extra, members in _urmsg_children(cur):
                if members:
                    last = members[-1]
            if last is None:
                break
            ln = getattr(last, "linenumber", 0)
            if ln > best:
                best = ln
            cur = last
        return best

    # ------------------------------------------------------------------
    # What a python line assigns and calls (M9)
    # ------------------------------------------------------------------
    #
    # The script index (every assignment and helper call, at any depth) and
    # the variable panel (what a top-level line gives) each parsed the same
    # python text with a loop of their own. _urmsg_py_parse parses it once
    # into events; each of the two keeps only its own reading of them.
    #
    # PURE, like the structure functions above: the index calls it from its
    # own thread, so nothing here is remembered.

    import ast as _urmsg_ast

    # Inside a Ren'Py 7 store, `str` is Ren'Py's compat str - unicode - but
    # Python 2's parser hands back string literals as byte strings. So text
    # types come from the real builtins, never from the store's names.
    try:
        import __builtin__ as _urmsg_builtins
        _urmsg_texts = (_urmsg_builtins.str, _urmsg_builtins.unicode)
    except ImportError:
        _urmsg_texts = (_urmsg_text,)

    # Constant node kinds across Python 2, 3.4-3.7 and 3.8+. Missing ones are
    # simply absent from the tuple.
    _urmsg_const_kinds = python_list()
    for _urmsg_kind_name in ("Constant", "Num", "Str", "NameConstant", "Bytes"):
        if hasattr(_urmsg_ast, _urmsg_kind_name):
            _urmsg_const_kinds.append(getattr(_urmsg_ast, _urmsg_kind_name))
    _urmsg_const_kinds = tuple(_urmsg_const_kinds)

    _URMSG_AUG = python_dict()
    for _urmsg_pair in (("Add", "+="), ("Sub", "-="), ("Mult", "*="),
                        ("Div", "/="), ("FloorDiv", "//="), ("Mod", "%="),
                        ("Pow", "**="), ("BitOr", "|="), ("BitAnd", "&=")):
        if hasattr(_urmsg_ast, _urmsg_pair[0]):
            _URMSG_AUG[getattr(_urmsg_ast, _urmsg_pair[0])] = _urmsg_pair[1]

    # A def, a class or a lambda is the game DEFINING a helper: its body is
    # not a story event, and its locals are not the game's variables.
    _urmsg_py_skip = python_list()
    for _urmsg_kind_name in ("FunctionDef", "ClassDef", "Lambda", "AsyncFunctionDef"):
        if hasattr(_urmsg_ast, _urmsg_kind_name):
            _urmsg_py_skip.append(getattr(_urmsg_ast, _urmsg_kind_name))
    _urmsg_py_skip = tuple(_urmsg_py_skip)

    _URMSG_COLLECT = ("append", "add", "remove", "discard")

    def _urmsg_literal(node):
        """(True, value) for a literal the script wrote, else (False, None)."""

        if isinstance(node, _urmsg_const_kinds):
            for attr in ("value", "n", "s"):
                if hasattr(node, attr):
                    return (True, getattr(node, attr))
            return (False, None)

        # Python 2 spells True, False and None as names.
        if isinstance(node, _urmsg_ast.Name):
            if node.id == "True":
                return (True, True)
            if node.id == "False":
                return (True, False)
            if node.id == "None":
                return (True, None)

        # -3 is UnaryOp(USub, 3).
        if (isinstance(node, _urmsg_ast.UnaryOp)
                and isinstance(node.op, _urmsg_ast.USub)):
            ok, value = _urmsg_literal(node.operand)
            if ok and isinstance(value, (int, float)) and not isinstance(value, bool):
                return (True, -value)

        return (False, None)

    def _urmsg_name(node):
        """
        The name URM itself would give this expression, or None.

        Matches Var naming exactly - a.b, a["k"], a[3] - so an index key and
        a search result are the same string. store.x is just x.
        """

        if isinstance(node, _urmsg_ast.Name):
            if node.id in ("True", "False", "None"):
                return None
            return node.id

        if isinstance(node, _urmsg_ast.Attribute):
            base = _urmsg_name(node.value)
            if base is None:
                return None
            if base == "store":
                return node.attr
            return base + "." + node.attr

        if isinstance(node, _urmsg_ast.Subscript):
            base = _urmsg_name(node.value)
            if base is None:
                return None
            key = node.slice
            # Before 3.9 the key is wrapped in Index().
            if hasattr(_urmsg_ast, "Index") and isinstance(key, _urmsg_ast.Index):
                key = key.value
            ok, value = _urmsg_literal(key)
            if not ok:
                return None
            if isinstance(value, _urmsg_texts):
                return base + '["' + value + '"]'
            if isinstance(value, int) and not isinstance(value, bool):
                return base + "[" + str(value) + "]"
            return None

        return None

    def _urmsg_callee(node):
        """`setflag` for setflag(...), `kim._var` for kim._var(...)."""

        if isinstance(node, _urmsg_ast.Call):
            return _urmsg_name(node.func)
        return None

    def _urmsg_py_targets(events, depth, top, target, op, ok, value, spread):
        """One "w" event per name an assignment gives a value to. Names
        unpacked from a tuple or a list do not get the value."""

        if isinstance(target, (_urmsg_ast.Tuple, _urmsg_ast.List)):
            for elt in target.elts:
                _urmsg_py_targets(events, depth, top, elt, op, False, None, True)
            return
        events.append(("w", depth, top, _urmsg_name(target), op, ok, value, spread))

    def _urmsg_py_parse(source):
        """
        (parsed, events) for the text of a python statement. parsed is False
        when it is not valid python. An event is one of:

          ("w", depth, top, name, op, ok, value, spread)
              an assignment to `name` (None when it has no name URM would
              give it); op is "=" or the augmented one; (ok, value) is the
              literal assigned, when it is one; spread is True for a name
              unpacked from a tuple or list.
          ("c", depth, top, callee, args, names, attr, owner, coll)
              a call standing as a statement: callee as URM would name it or
              None; args its text arguments; names the names of the others;
              attr the method called; owner the collection when attr is
              append / add / remove / discard; coll (ok, value) per argument.

        depth is 0 for a statement of the text itself and more inside its
        ifs and loops; top is which statement of the text it belongs to.
        Events come in the order the index has always visited the tree
        (last statement first, each statement before what is inside it):
        the index's tables are lists in that order.
        """

        try:
            tree = _urmsg_ast.parse(source, mode="exec")
        except Exception:
            return False, ()

        events = python_list()
        stack = python_list()
        stack.append((tree, -1, -1))

        while stack:
            cur, depth, top = stack.pop()

            if isinstance(cur, _urmsg_py_skip):
                continue

            if isinstance(cur, _urmsg_ast.Assign):
                ok, value = _urmsg_literal(cur.value)
                for target in cur.targets:
                    _urmsg_py_targets(events, depth, top, target, "=", ok, value, False)

            elif isinstance(cur, _urmsg_ast.AugAssign):
                ok, value = _urmsg_literal(cur.value)
                op = _URMSG_AUG.get(type(cur.op), "op=")
                _urmsg_py_targets(events, depth, top, cur.target, op, ok, value, False)

            elif isinstance(cur, _urmsg_ast.Expr) and isinstance(
                    cur.value, _urmsg_ast.Call):
                call = cur.value
                args = python_list()
                names = python_list()
                coll = python_list()
                for arg in call.args:
                    ok, value = _urmsg_literal(arg)
                    coll.append((ok, value))
                    if ok and isinstance(value, _urmsg_texts):
                        args.append(value)
                    else:
                        argname = _urmsg_name(arg)
                        if argname is not None:
                            names.append(argname)
                attr = None
                owner = None
                if isinstance(call.func, _urmsg_ast.Attribute):
                    attr = call.func.attr
                    if attr in _URMSG_COLLECT:
                        owner = _urmsg_name(call.func.value)
                events.append(("c", depth, top, _urmsg_callee(call), tuple(args),
                               tuple(names), attr, owner, tuple(coll)))

            at = 0
            for child in _urmsg_ast.iter_child_nodes(cur):
                stack.append((child, depth + 1, at if depth < 0 else top))
                at += 1

        return True, tuple(events)

    def _urmsg_py_top(events):
        """The events of the text's own statements (depth 0), in the order
        they are written."""

        count = 0
        for event in events:
            if event[1] == 0 and event[2] >= count:
                count = event[2] + 1

        slots = python_list()
        at = 0
        while at < count:
            slots.append(python_list())
            at += 1

        for event in events:
            if event[1] == 0:
                slots[event[2]].append(event)

        out = python_list()
        for slot in slots:
            out.extend(slot)
        return out


