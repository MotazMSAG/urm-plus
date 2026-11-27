    # ------------------------------------------------------------------
    # The gate chain
    # ------------------------------------------------------------------

    def _urmsg_chain(first_if, limit, blocks, step, max_ifs=8, origin=None):
        """
        Every gate ahead, in the order they are tested, as a _URMSGChain.
        blocks(statement) says whether a statement waits for the player;
        step(statement) gives the next one, None, or _URMSG_LOST. origin:
        the line on screen, when known - what it and the lines up to the
        first if-statement write is read into the way facts.

        Where the step is lost - a jump or a call that cannot be followed -
        the chain keeps the gates it found and closes with the one record
        for that (idea 2 and idea 8): `lost` is set, and the last step is
        ("tail", None, _URMSG_DYN_JUMP or _URMSG_DYN_CALL).

        The steps are of SEPARATE if-statements one after another, not one
        if/elif: `ways`, parallel to the steps, says which is which and what
        each arm does to the next (_urmsg_gate_read).
        """

        c = _URMSGChain()
        node = first_if
        ifs = 0
        passed = python_set()

        if origin is not None:
            at = origin
            n = 0
            while at is not None and at is not _URMSG_LOST and at is not first_if and n <= limit:
                n += 1
                passed |= _urmsg_passed_writes(at)
                at = step(at)

        while ifs < max_ifs:
            ifs += 1
            closed = False
            arm = 0
            before = frozenset(passed)
            passed = python_set()

            for cond, block in (getattr(node, "entries", None) or ()):
                way = (ifs, _urmsg_block_leaves(block), before, _urmsg_block_writes(block))
                if _urmsg_is_else(cond):
                    c.steps.append(("else", None, block))
                    c.meta.append((node, arm))
                    c.ways.append(way + (frozenset(),))
                    closed = True
                    break
                c.steps.append(("gate", cond, block))
                c.meta.append((node, arm))
                c.ways.append(way + (_urmsg_test_keys(cond),))
                arm += 1

            if closed:
                return c

            tail_way = (ifs + 1, None, frozenset(), frozenset(), frozenset())
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
                passed |= _urmsg_passed_writes(ahead)
                gone = ahead
                ahead = step(ahead)
                if ahead is _URMSG_LOST:
                    c.lost = True
                    c.steps.append(("tail", None,
                                    _urmsg_unfollowed(gone) or _URMSG_DYN_JUMP))
                    c.meta.append((None, -1))
                    c.ways.append(tail_way)
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
                    c.ways.append(tail_way)
                return c

        c.cut = True
        return c

    # ---- what each way of the chain does to the next (Summer with Mia,
    # 2026-11-22: "is this a PC?", then "is the name empty?" - two separate
    # if-statements; the name is typed before the second reads it)
    #
    # A way fact is (if-statement, leaves, before, writes, reads):
    #   if-statement  which one of the chain (1, 2, ...); the tail has its own
    #   leaves        True when the arm's block always ends by leaving (a jump,
    #                 a return), False when it always carries on, None when
    #                 that cannot be told
    #   before        keys (_urmsg_keys) written by the lines passed on the way
    #                 to this if-statement
    #   writes        keys the arm's block may write
    #   reads         keys the arm's test reads
    # Keys come from the one reader of what a line writes. A line whose
    # writes cannot be told, and a call of a scene from inside a way, add
    # _URMSG_ALL: every later test is then not told (show nothing rather
    # than a guess - the ticket's must, plan check 2026-11-23).

    _URMSG_TEST_KEYS = python_dict()
    _URMSG_ALL = (u"*", u"*")

    def _urmsg_keys_of(paths):
        if paths is None:
            return python_set((_URMSG_ALL,))
        keys = python_set()
        for path in paths:
            if path:
                keys.update(_urmsg_keys(path))
        return keys

    def _urmsg_stmt_writes(node):
        """The keys one statement writes on its own: a python statement's
        lines, or the line the walks give it (_urmsg_stmt_text: `call
        screen` cannot be told). A jump or a call statement writes nothing
        itself: on the way the walk follows it and passes its lines. A
        python line that jumps or calls goes where the walk does not
        follow: cannot be told."""

        if _urmsg_kind(node) != _URMSG_K_PY:
            text = _urmsg_stmt_text(node)
            if text is None:
                return frozenset()
            return frozenset(_urmsg_keys_of(_urmsg_line_writes(text)))
        try:
            source = node.code.source or u""
        except Exception:
            return frozenset((_URMSG_ALL,))
        if _urmsg_hop(node) is not None:
            return frozenset((_URMSG_ALL,))
        return frozenset(_urmsg_keys_of(_urmsg_line_writes(source)))

    def _urmsg_passed_writes(node):
        """The keys a statement the walk passes may write: read as an arm's
        block is (_urmsg_block_writes), so a loop or a translation the walk
        steps over is opened too. A label, a jump and a call are not: the
        walk goes into them and passes their lines itself."""

        k = _urmsg_kind(node)
        if k == _URMSG_K_LABEL or k == _URMSG_K_JUMP or k == _URMSG_K_CALL:
            return frozenset()
        return _urmsg_block_writes((node,))

    def _urmsg_block_writes(block, depth=0):
        """The keys a block may write, inside its checks and choices too."""

        keys = python_set()
        for node in (block or ()):
            k = _urmsg_kind(node)
            if k == _URMSG_K_CALL:
                # A scene called from inside a way: not followed here.
                keys.add(_URMSG_ALL)
                continue
            keys |= _urmsg_stmt_writes(node)
            if depth >= _URMSG_MAX_DEPTH:
                if k in (_URMSG_K_IF, _URMSG_K_MENU, _URMSG_K_WHILE):
                    keys.add(_URMSG_ALL)
            else:
                for kind, _i, _x, inner in _urmsg_children(node):
                    keys |= _urmsg_block_writes(inner, depth + 1)
        return frozenset(keys)

    def _urmsg_block_leaves(block, depth=0):
        """True when a block always ends by leaving - its last statement is
        a jump, a return or a python line that always jumps, or a check
        whose every way does; False when it always carries on - nothing in
        it, at any depth, may leave (_urmsg_may_leave); None when that
        cannot be told."""

        if not block:
            return False
        last = block[-1]
        k = _urmsg_kind(last)
        if k == _URMSG_K_JUMP or k == _URMSG_K_RET:
            return True
        if k == _URMSG_K_PY:
            try:
                py = _urmsg_py(last.code.source)
            except Exception:
                return None
            if py.hop is not None and py.hop[0] == "jump" and not py.hop_indented:
                return True
        if k == _URMSG_K_IF and depth < _URMSG_MAX_DEPTH:
            entries = getattr(last, "entries", None) or ()
            if (any(_urmsg_is_else(cond) for cond, _inner in entries)
                    and all(_urmsg_block_leaves(inner, depth + 1) is True
                            for _cond, inner in entries)):
                return True
        return None if _urmsg_may_leave(block, depth) else False

    def _urmsg_may_leave(block, depth=0):
        """True when anything in a block, at any depth, may send the story
        elsewhere: a jump, a return, a call (the scene may not come back), a
        python line that jumps or calls, or what cannot be read. The gate
        card's harmless default (final check 2026-11-23): a way carries on
        only when nothing in it may leave."""

        for node in (block or ()):
            k = _urmsg_kind(node)
            if k == _URMSG_K_JUMP or k == _URMSG_K_RET or k == _URMSG_K_CALL:
                return True
            if k == _URMSG_K_PY:
                try:
                    if _urmsg_py(node.code.source).hop is not None:
                        return True
                except Exception:
                    return True
            children = _urmsg_children(node)
            if children and depth >= _URMSG_MAX_DEPTH:
                return True
            for _kind, _i, _x, inner in children:
                if _urmsg_may_leave(inner, depth + 1):
                    return True
        return False

    def _urmsg_test_keys(cond):
        """The keys a test reads (every name and attribute in it), by its
        text; remembered, the script's tests being a fixed set."""

        text = (u"%s" % (cond,)).strip()
        try:
            return _URMSG_TEST_KEYS[text]
        except KeyError:
            pass
        keys = python_set()
        try:
            tree = _urmsg_parse(text, "eval")
            for node in _urmsg_pyast.walk(tree):
                if _urmsg_kind_of(node) in ("Name", "Attribute", "Subscript"):
                    path = _urmsg_path_of(node, python_dict())
                    if isinstance(path, tuple) and path:
                        keys.update(_urmsg_keys(path))
        except Exception:
            pass
        keys = frozenset(keys)
        _URMSG_TEST_KEYS[text] = keys
        return keys

    def _urmsg_gate_read(steps, truth, ways=None):
        """
        For each step, (state, gate number or 0, told): state "runs",
        "unknown" or "dead"; told False when the test reads what may be
        written on the way to it - the answer now is not the answer there,
        so it is not asked. truth(cond) gives True, False or None.

        ways: the chain's way facts (_urmsg_chain). Without them the steps
        are one if/elif, the tail its else. Within one if-statement the
        first arm known true runs and the rest are dead; an arm known false
        is dead even after one that cannot be told; one known true after it
        cannot be told either, and closes the rest. The next if-statement
        is reached unless every way out of this one leaves; the tail (what
        follows the last) runs when it is reached.
        """

        out = python_list()
        written = python_set()
        reach = True
        number = 0
        group = None
        closed = open_ = False
        ends = writes = None

        def after(reach, closed, ends):
            if reach is False:
                return False
            if not closed:
                ends = tuple(ends) + (False,)     # it may fall through
            if all(e is False for e in ends):
                return reach
            if all(e is True for e in ends):
                return False
            return None

        for at, (kind, cond, _payload) in enumerate(steps):
            way = ways[at] if ways is not None and at < len(ways) else None
            here = way[0] if way is not None else 0
            if here != group:
                if group is not None:
                    reach = after(reach, closed, ends)
                    written |= writes
                group = here
                closed, open_ = False, True
                ends, writes = python_list(), python_set()
                if way is not None:
                    written |= way[2]
            reads = way[4] if way is not None else ()
            told = _URMSG_ALL not in written and not any(key in written for key in reads)

            if kind == "gate":
                number += 1
                if reach is False or closed:
                    state = "dead"
                else:
                    t = truth(cond) if told else None
                    if t is False:
                        state = "dead"
                    elif t is True:
                        state = "runs" if (reach is True and open_) else "unknown"
                        closed = True
                    else:
                        state = "unknown"
                        open_ = False
                out.append((state, number, told))
            elif kind == "tail" and way is not None:
                state = "runs" if reach is True else "dead" if reach is False else "unknown"
                out.append((state, 0, True))
                continue
            else:
                if reach is False or closed:
                    state = "dead"
                elif open_ and reach is True:
                    state = "runs"
                else:
                    state = "unknown"
                closed = True
                out.append((state, 0, True))

            if state != "dead" and way is not None:
                ends.append(way[1])
                writes |= way[3]

        return out

    def _urmsg_gate_states(steps, truth, ways=None):
        """For each step, ("runs" | "unknown" | "dead", gate number or 0):
        _urmsg_gate_read without told."""

        return python_list((s, n) for s, n, _t in _urmsg_gate_read(steps, truth, ways))

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

        return _urmsg_tl_tables(language)[0]

    def _urmsg_tl_tables(language):
        """(_urmsg_tl's table, {id(line of the original script): [its lines
        in this language]}), remembered together."""

        g = _urmsg_graph()
        if g.tl is not None and g.tl[0] == language:
            return g.tl[1], g.tl[2]

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

        # A one-line translation on Ren'Py 8 is a TranslateSay of its own,
        # with no block: it is in language_translates, not in the table.
        back = python_dict()
        try:
            defaults = renpy.game.script.translator.default_translates
            lines = python_list(table.values())
            items = renpy.game.script.translator.language_translates
            for key in items:
                if key[1] == language and not getattr(items[key], "block", None):
                    lines.append((items[key], key[0]))
            for child, ident in lines:
                if _urmsg_kind(child) != _URMSG_K_SAY:
                    continue
                d = defaults.get(ident)
                if d is None:
                    d = defaults.get(ident.replace(".", "_"))
                orig = _urmsg_rep(d) if d is not None else None
                if orig is not None:
                    back.setdefault(id(orig), python_list()).append(child)
        except Exception:
            pass

        g.tl = (language, table, back)
        return table, back

    def _urmsg_played_twins(node):
        """
        The lines of the language being played that a line of the original
        script is shown as - what the player reads, and what the engine
        marks seen (_urmsg_default_twin the other way). Empty while no
        translation is played, or for a line the language leaves out.
        """

        try:
            language = renpy.game.preferences.language
        except Exception:
            language = None
        if language is None or node is None:
            return ()
        return _urmsg_tl_tables(language)[1].get(id(node), ())

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



    # ------------------------------------------------------------------
    # The player's ways: every shape of a choice (the map rework, 2026-11-23)
    # ------------------------------------------------------------------
    #
    # The readers above see a player's choice only as a menu. A game may
    # let the player pick on a screen whose buttons jump (Him has no menu
    # at all), on a screen that hands back a value an `if` then reads
    # (Being a DIK's interlude), with buttons made in python before
    # `ui.interact()` (its free-roam rooms), through a game function around
    # renpy.display_menu (The Office Wife); and a route can be picked in a
    # python block (Katawa Shoujo). FINDINGS.md, 2026-11-23.
    #
    # One record for all of them: _urmsg_choice(statement). Each way says
    # where it goes, what it hands on and, when it can be read, which arm
    # of the check that reads the handed value it takes. Where a part of a
    # choice cannot be read the record says so (whole False, why) - it never
    # fills in a guess.
    #
    # EVERYTHING HERE IS OPT-IN. No reader above calls it, so no display
    # changes; a display asks for it (_urmsg_flow_ways, ways=True on the
    # searches and on a walk). And it never touches their memories: every
    # reader here runs inside the graph's TWIN (_urmsg_own), which shares
    # only what is read straight from the script and keeps its own
    # memories of everything a search or a function reader works out -
    # those can depend on what was asked first (FINDINGS.md, 2026-11-23),
    # so asking these readers can never change an old answer.

    # The twin shares these with the graph it is made from: the script and
    # what is read straight from it, the same whatever was asked first.
    # (tl, defs and methods are worked out on first use; one the base had
    # not worked out yet the twin works out again for itself - the same
    # answer.) Every other slot is the twin's own. check_ways.py names every
    # slot and every field filled later, so a new one is placed on purpose.
    _URMSG_TWIN_SHARED = ("gen", "script", "count", "over", "labels", "tl",
                          "defs", "trees", "fdefs", "methods")

    def _urmsg_own():
        """Put the graph's twin in place, for a reader of this section.
        Returns the graph to put back (_urmsg_own_end), or None when a twin
        is already in place (a reader called from another)."""

        st = _urmsg_st
        g = _urmsg_graph()
        if g.base is not None:
            return None
        twin = g.twin
        if twin is None:
            twin = _URMSGraph(g.gen)
            for name in _URMSG_TWIN_SHARED:
                setattr(twin, name, getattr(g, name))
            twin.base = g
            g.twin = twin
        st.g = twin
        return g

    def _urmsg_own_end(g):
        if g is not None:
            _urmsg_st.g = g

    def _urmsg_owned_steps(steps):
        """A twin reader's steps (a generator) for the worker: the twin is
        put in place for each step and taken away before the pause, so what
        runs between frames reads the game's own graph."""

        while True:
            g0 = _urmsg_own()
            try:
                said = next(steps)
            except StopIteration:
                return
            finally:
                _urmsg_own_end(g0)
            yield said

    class _URMSGWay(python_object):
        """
        One way of a choice. go: "enter" (a block of the choice: a menu
        option, an arm of a python check), "leave" (a jump), "visit" (a
        call; the story then goes on after the choice), "back" (the story
        goes on after the choice). target: the statement the way goes to
        first (None when it cannot be found). label: the label of a leave
        or a visit. tests: (test, holds) pairs that must all be met for the
        way to be offered (test None: one that cannot be quoted); inside:
        True when one of them reads a value the screen itself decides (its
        own sets, its variables, its parameters) - never to be checked
        against the store. sets: the (name, value) pairs the way hands on
        (value _URMSG_ANY: not a literal). arm: (check, arm index) the check
        that reads a handed value takes - index -1 when it is passed by -
        or None when that cannot be told. caption: the words, or None.
        """

        __slots__ = ("caption", "tests", "inside", "go", "label", "target",
                     "sets", "arm", "param")

        def __init__(self, go, caption=None, tests=(), label=None, sets=()):
            # param: the screen parameter whose argument is the caption
            # (a screen read alone does not know it; its choice does).
            self.param = None
            self.caption = caption
            self.tests = tests
            self.inside = False
            self.go = go
            self.label = label
            self.target = None
            self.sets = sets
            self.arm = None

    class _URMSGChoice(python_object):
        """
        A place where the story splits. shape: "menu", "screen", "ui"
        (buttons made before ui.interact), "shown" (screens shown before
        the game waits in a pause loop, a hard pause or a bare
        ui.interact), "function" (a menu shown by
        renpy.display_menu or a game function around it), "code" (a python
        block that picks where to jump - not the player's pick). ways: its
        _URMSGWay in script order. whole: False when the choice may offer
        more than its ways say (why holds the reasons). after: the statement
        the story goes on to after it. names: the names its ways hand on.
        check: the check that reads them, or None. screen: the screen's name.
        """

        __slots__ = ("node", "shape", "ways", "whole", "why", "after",
                     "names", "check", "screen")

        def __init__(self, node, shape):
            self.node = node
            self.shape = shape
            self.ways = ()
            self.whole = True
            self.why = ()
            self.after = getattr(node, "next", None)
            self.names = ()
            self.check = None
            self.screen = None

    def _urmsg_not_whole(record, why):
        record.whole = False
        if why not in record.why:
            record.why = record.why + (why,)

    # ---- small readers of parsed python

    def _urmsg_call_name(node):
        """`Jump` for Jump(...), `ui.returns` for ui.returns(...), else None."""

        if _urmsg_kind_of(node) != "Call":
            return None
        return _urmsg_name(node.func)

    def _urmsg_word(node):
        """(True, value) for a literal, a literal handed to _() or __(), or
        a tuple of those; else (False, None)."""

        if node is None:
            return False, None
        ok, value = _urmsg_literal(node)
        if ok:
            return ok, value
        if (_urmsg_call_name(node) in ("_", "__") and len(node.args) == 1
                and not node.keywords):
            return _urmsg_literal(node.args[0])
        if _urmsg_kind_of(node) == "Tuple":
            out = python_list()
            for elt in node.elts:
                ok, value = _urmsg_word(elt)
                if not ok:
                    return False, None
                out.append(value)
            return True, tuple(out)
        return False, None

    def _urmsg_arg(call, at, name):
        """The argument at position `at`, or named `name`, or None."""

        if len(call.args) > at:
            return call.args[at]
        for kw in (call.keywords or ()):
            if kw.arg == name:
                return kw.value
        return None

    def _urmsg_lit_arg(call, at, name):
        """(True, value) for a literal argument; else (False, None)."""

        return _urmsg_word(_urmsg_arg(call, at, name))

    _URMSG_OPS = python_dict((("Eq", u"=="), ("NotEq", u"!="), ("Lt", u"<"),
                              ("LtE", u"<="), ("Gt", u">"), ("GtE", u">="),
                              ("In", u"in"), ("NotIn", u"not in")))

    def _urmsg_unparse(expr):
        """The text of a parsed test, for the plain shapes a screen's If
        action is written with; None for anything else."""

        kind = _urmsg_kind_of(expr)
        name = _urmsg_name(expr)
        if name is not None:
            return name
        ok, value = _urmsg_literal(expr)
        if ok:
            return u"%r" % (value,)
        if kind == "UnaryOp" and _urmsg_kind_of(expr.op) == "Not":
            inner = _urmsg_unparse(expr.operand)
            return None if inner is None else u"not " + inner
        if kind == "Compare" and len(expr.ops) == 1:
            op = _URMSG_OPS.get(_urmsg_kind_of(expr.ops[0]))
            left = _urmsg_unparse(expr.left)
            right = _urmsg_unparse(expr.comparators[0])
            if op is None or left is None or right is None:
                return None
            return u"%s %s %s" % (left, op, right)
        return None

    def _urmsg_names_read(text):
        """The store names a test's text reads (plain names and dotted
        paths), or None when it does not parse."""

        try:
            tree = _urmsg_parse(u"%s" % (text,), "eval")
        except Exception:
            return None
        out = python_set()
        for node in _urmsg_pyast.walk(tree):
            if _urmsg_kind_of(node) == "Name":
                out.add(node.id)
            elif _urmsg_kind_of(node) == "Attribute":
                name = _urmsg_name(node)
                if name is not None:
                    out.add(name)
        return out

    # ---- actions: what clicking does. Jump leaves, Call visits, Return
    # ends the screen with a value; the Set family hands on a name and a
    # value; Show opens another screen, read for its ways; the rest below
    # sends nothing. Any other action (Function, a game's own class) cannot
    # be told.

    _URMSG_ACT_SETS = frozenset(("SetVariable", "SetDict", "SetField",
                                 "ToggleVariable", "ToggleDict", "ToggleField",
                                 "SetLocalVariable", "ToggleLocalVariable"))
    _URMSG_ACT_SCREEN_VARS = frozenset(("SetScreenVariable", "ToggleScreenVariable"))
    _URMSG_ACT_SHOWS = frozenset(("Show", "ShowTransient", "ToggleScreen"))
    _URMSG_ACT_QUIET = frozenset((
        "NullAction", "Hide", "Rollback", "RollForward", "Skip", "Preference",
        "QuickSave", "QuickLoad", "FileSave", "FileLoad", "FileAction",
        "FileDelete", "FilePage", "FilePageNext", "FilePagePrevious",
        "Play", "Stop", "Queue", "PauseAudio", "SetMixer", "SetMute",
        "ToggleMute", "OpenURL", "Notify", "SelectedIf", "SensitiveIf",
        "With", "Help", "Language", "MainMenu", "Quit", "HideInterface",
        "Screenshot", "CaptureFocus", "ClearFocus", "ToggleFocus",
        "MouseMove", "Scroll", "InvertSelected", "ShowMenu", "Replay",
        "EndReplay"))

    def _urmsg_act(expr, results):
        """
        What the action `expr` (parsed) does after each of results, or
        None when that cannot be told. A result is a list [tests, sets, go,
        label, value, shows]: go None while nothing was sent (then value is
        what a Return handed back so far, or None); "leave" or "visit" with
        its label; shows the screens it opened. An action list runs in
        order and the last value handed back wins (renpy.run); after a jump
        or a call nothing more runs.
        """

        kind = _urmsg_kind_of(expr)
        if kind in ("List", "Tuple"):
            for one in expr.elts:
                results = _urmsg_act(one, results)
                if results is None:
                    return None
            return results
        ok, value = _urmsg_literal(expr)
        if ok and value is None:
            return results
        name = _urmsg_call_name(expr)
        if name is None:
            return None
        out = python_list()

        if name == "If":
            cond = _urmsg_arg(expr, 0, "expression")
            text = _urmsg_unparse(cond) if cond is not None else None
            if text is None:
                return None
            for holds, branch in ((True, _urmsg_arg(expr, 1, "true")),
                                  (False, _urmsg_arg(expr, 2, "false"))):
                part = python_list()
                for res in results:
                    if res[2] is not None:
                        part.append(res)
                    else:
                        part.append(python_list((res[0] + ((text, holds),), res[1],
                                                 None, None, res[4], res[5])))
                if branch is not None:
                    part = _urmsg_act(branch, part)
                    if part is None:
                        return None
                out.extend(part)
            return out

        for res in results:
            if res[2] is not None:
                out.append(res)
                continue
            res = python_list(res)
            if name in ("Jump", "Call", "ui.jumps"):
                ok, label = _urmsg_lit_arg(expr, 0, "label")
                if not ok or not isinstance(label, _urmsg_texts):
                    return None
                res[2] = "visit" if name == "Call" else "leave"
                res[3] = label
            elif name in ("Return", "ui.returns"):
                arg = _urmsg_arg(expr, 0, "value")
                if arg is None:
                    res[4] = True
                else:
                    ok, value = _urmsg_word(arg)
                    if not ok:
                        res[4] = _URMSG_ANY
                    elif value is None:
                        res[4] = True
                    else:
                        res[4] = value
            elif name in _URMSG_ACT_SETS:
                target = None
                value = _URMSG_ANY
                if "Variable" in name:
                    ok, target = _urmsg_lit_arg(expr, 0, "name")
                    if not ok or not isinstance(target, _urmsg_texts):
                        return None
                    at = 1
                else:
                    what = "dict" if "Dict" in name else "object"
                    base = _urmsg_arg(expr, 0, what)
                    base = _urmsg_name(base) if base is not None else None
                    ok, key = _urmsg_lit_arg(expr, 1, "key" if "Dict" in name else "field")
                    if base is None or not ok:
                        return None
                    if "Dict" in name:
                        if isinstance(key, _urmsg_texts):
                            target = base + u'["' + key + u'"]'
                        else:
                            target = base + u"[" + u"%s" % (key,) + u"]"
                    else:
                        target = base + u"." + u"%s" % (key,)
                    at = 2
                if name.startswith("Set"):
                    ok, lit = _urmsg_lit_arg(expr, at, "value")
                    if ok:
                        value = lit
                res[1] = res[1] + ((target, value),)
            elif name in _URMSG_ACT_SCREEN_VARS:
                ok, target = _urmsg_lit_arg(expr, 0, "name")
                if not ok or not isinstance(target, _urmsg_texts):
                    return None
                res[1] = res[1] + ((u"\x00screen " + target, _URMSG_ANY),)
            elif name in _URMSG_ACT_SHOWS:
                ok, shown = _urmsg_lit_arg(expr, 0, "screen")
                if not ok or not isinstance(shown, _urmsg_texts):
                    return None
                res[5] = res[5] + (shown,)
            elif name in _URMSG_ACT_QUIET:
                pass
            elif name == "Function":
                fn = _urmsg_arg(expr, 0, "callable")
                fn = _urmsg_name(fn) if fn is not None else None
                if fn is None or not _urmsg_fn_quiet(fn, 0, ()):
                    return None
            else:
                return None
            out.append(res)
        return out

    # The engine's calls a quiet function may make: sound, a note, a
    # redraw. Nothing that opens a screen or writes.
    _URMSG_FN_NOISE = ("renpy.play", "renpy.sound.", "renpy.music.", "renpy.notify",
                       "renpy.restart_interaction", "renpy.vibrate")

    def _urmsg_fn_quiet(name, depth, seen):
        """
        True when `Function(name)` on a button sends nothing, opens
        nothing and writes nothing: a game function whose def hands back
        nothing (no return with a value), writes only its own locals, and
        calls nothing but the engine's sound and notes (_URMSG_FN_NOISE) and
        the game's own quiet functions (Being a DIK plays a sound on every
        choice button). False for anything else, or anything that cannot be
        read.
        """

        if u"." in name or name in seen or depth > _URMSG_FN_DEPTH:
            return False
        fn = _urmsg_game_fn(getattr(renpy.store, name, None))
        fdef = _urmsg_def_of(fn) if fn is not None else None
        if fdef is None:
            return False
        for node in _urmsg_inside(fdef.body):
            kind = _urmsg_kind_of(node)
            if kind in ("Raise", "Yield", "YieldFrom", "Exec", "Global", "Nonlocal"):
                return False
            if kind == "Return" and node.value is not None:
                ok, value = _urmsg_literal(node.value)
                if not ok or value is not None:
                    return False
            if kind in ("Assign", "AugAssign", "AnnAssign", "Delete"):
                for target in (getattr(node, "targets", None) or (getattr(node, "target", None),)):
                    if _urmsg_kind_of(target) != "Name":
                        # A store name, an object's field, an item: it writes.
                        return False
            if kind != "Call":
                continue
            called = _urmsg_call_name(node)
            if called is None:
                return False
            if called.startswith(_URMSG_FN_NOISE):
                continue
            if called.startswith(u"renpy.") or u"." in called:
                return False
            if not _urmsg_fn_quiet(called, depth + 1, seen + (name,)):
                return False
        return True

    def _urmsg_act_text(text):
        """What an action written as text does (_urmsg_act), from nothing
        sent yet; None when that cannot be told."""

        try:
            tree = _urmsg_parse(u"%s" % (text,), "eval")
        except Exception:
            return None
        return _urmsg_act(tree.body, python_list((python_list(((), (), None, None, None, ())),)))

    # ---- screens

    _URMSG_SCREEN_DEPTH = 3
    _URMSG_CALL_SCREEN = _urmsg_re.compile(
        r"^call\s+screen\s+(expression\s+)?([A-Za-z_][\w.]*)")
    # Keywords that carry an action. `action` and `clicked` of anything but
    # a timer or a dismiss are ways; the others can only make the choice
    # not whole. hovered and unhovered are never the player's pick.
    _URMSG_ACT_WAYS = ("action", "clicked")
    _URMSG_ACT_OTHER = ("alternate", "dragged", "dropped", "changed", "activated")
    _URMSG_TIMED = frozenset(("timer", "dismiss"))

    class _URMSGScreen(python_object):
        """What a screen offers: ways (_URMSGWay, no target yet), whole and
        why, the names its actions write, its own names (variables and
        parameters), and the file it is written in."""

        __slots__ = ("name", "ways", "whole", "why", "writes", "own", "file",
                     "params")

        def __init__(self, name):
            # params: the screen's parameters in order, for its arguments.
            self.params = ()
            self.name = name
            self.ways = python_list()
            self.whole = True
            self.why = ()
            self.writes = python_set()
            self.own = python_set()
            self.file = u""

    def _urmsg_screen_find(name):
        """(the screen's tree, its file) as the engine would pick it now
        (variants included), or None."""

        try:
            screen = renpy.display.screen.get_screen_variant(name)
        except Exception:
            return None
        tree = getattr(screen, "ast", None)
        if tree is None:
            return None
        where = (getattr(screen, "location", None) or getattr(tree, "location", None)
                 or ())
        return tree, (where[0] if where else u"")

    def _urmsg_shown_name(node):
        """The name a screen-language displayable is written with:
        `textbutton`, `imagebutton`, `timer`, ..."""

        name = getattr(node, "name", None)
        if name:
            return u"%s" % (name,)
        made = getattr(node, "displayable", None)
        name = getattr(made, "__name__", None) or u""
        return name.lstrip(u"_").lower()

    def _urmsg_caption(node, shown):
        """A button's own words: a text button's text, or the text inside a
        button. None for anything else (a text beside a button is not its
        caption - which one belongs to which cannot be told)."""

        texts = python_list()
        if shown == "textbutton":
            texts.extend(getattr(node, "positional", None) or ())
        else:
            for child in (getattr(node, "children", None) or ()):
                if _urmsg_shown_name(child) == "text":
                    texts.extend((getattr(child, "positional", None) or ())[:1])
                    break
        for text in texts[:1]:
            try:
                ok, value = _urmsg_word(_urmsg_parse(u"%s" % (text,), "eval").body)
            except Exception:
                ok = False
            if ok and isinstance(value, _urmsg_texts):
                return value
        return None

    def _urmsg_screen(name, depth=0, seen=()):
        """What the screen `name` offers (_URMSGScreen), remembered by name
        in the twin's own memory."""

        g = _urmsg_graph()
        hit = g.screens.get(name)
        if hit is not None:
            return hit
        rec = _URMSGScreen(name)
        found = _urmsg_screen_find(name)
        if found is None:
            _urmsg_not_whole(rec, u"a screen that is not in the game")
        else:
            _urmsg_screen_read(rec, found[0], depth, seen + (name,))
            rec.file = found[1]
            _urmsg_mark_inside(rec)
        if len(g.screens) >= _URMSG_CAP_LABELS:
            g.screens.clear()
        g.screens[name] = rec
        return rec

    def _urmsg_screen_read(rec, tree, depth, seen):
        """Fill rec from a screen's tree."""

        if _urmsg_kind_of(tree) != "SLScreen":
            _urmsg_not_whole(rec, u"a screen in the old screen language")
            return
        info = getattr(tree, "parameters", None)
        params = getattr(info, "parameters", None) or ()
        if hasattr(params, "keys"):
            for one in params.keys():
                rec.own.add(one)
        else:
            for one in params:
                rec.own.add(one[0] if isinstance(one, tuple) else getattr(one, "name", None))
        if depth == 0:
            order = getattr(info, "positional", None)
            if order is None and not hasattr(params, "keys"):
                order = python_list(one[0] if isinstance(one, tuple) else getattr(one, "name", None)
                                    for one in params)
            rec.params = tuple(order or ())
        places = _urmsg_sl_places(tree, rec.params)
        texts = python_list()

        # The walk meets the last node first; ways are gathered last first
        # and turned round at the end, so they stand in script order.

        def merge(other, tests, out):
            for way in other.ways:
                copy = _URMSGWay(way.go, way.caption, tests + way.tests, way.label, way.sets)
                copy.inside = way.inside
                out.append(copy)
            rec.writes |= other.writes
            rec.own |= other.own
            for why in other.why:
                _urmsg_not_whole(rec, why)

        def opened(names, tests):
            """The ways of the screens these open or use, in script order."""
            out = python_list()
            for shown in names:
                if shown in seen:
                    continue
                if depth + 1 > _URMSG_SCREEN_DEPTH:
                    _urmsg_not_whole(rec, u"screens opened too deep")
                    continue
                other = _URMSGScreen(shown)
                found = _urmsg_screen_find(shown)
                if found is None:
                    _urmsg_not_whole(rec, u"a screen that is not in the game")
                    continue
                _urmsg_screen_read(other, found[0], depth + 1, seen + (shown,))
                merge(other, tests, out)
            return out

        def visit(node, kind, tests, loop):
            if kind not in _URMSG_SL_KINDS:
                _urmsg_not_whole(rec, u"a screen statement that cannot be read")
                return False
            if kind == "SLDefault":
                rec.own.add(getattr(node, "variable", None))
            elif kind in ("SLUse", "SLCustomUse"):
                target = getattr(node, "target", None)
                if target is None or not _URMSG_WORD.match(u"%s" % (target,)):
                    _urmsg_not_whole(rec, u"a screen used by a worked-out name")
                else:
                    for way in reversed(opened((u"%s" % (target,),), tests)):
                        rec.ways.append(way)
            elif kind == "SLDisplayable":
                before = len(rec.ways)
                _urmsg_button(rec, node, tests, loop, opened)
                shown = _urmsg_shown_name(node)
                if len(rec.ways) > before:
                    mine = python_list()
                    k = before
                    param = _urmsg_caption_param(node, shown, rec.params)
                    while k < len(rec.ways):
                        way = rec.ways[k]
                        if param is not None:
                            # "[word]": the words handed in, not the brackets.
                            way.caption = None
                            way.param = param
                        mine.append(way)
                        k += 1
                    buttons.append((places.get(id(node)), mine))
                    return True
                if shown == "text" and not loop:
                    param = _urmsg_text_param(node, rec.params)
                    if param is not None:
                        texts.append((places.get(id(node)), param))
            return True

        buttons = python_list()
        _urmsg_sl_walk(tree, visit)
        # A text beside a button, showing a parameter, is that button's
        # caption only when they are placed by the same parameters and no
        # other button or text is with the same coordinates.
        for place, mine in buttons:
            if not place:
                continue
            same = python_list(param for at, param in texts if at == place)
            others = python_list(1 for at, _ways in buttons if at == place)
            if len(same) == 1 and len(others) == 1:
                for way in mine:
                    if way.caption is None and way.param is None:
                        way.param = same[0]
        rec.ways.reverse()

    def _urmsg_button(rec, node, tests, loop, opened):
        """Read one displayable's actions into rec."""

        shown = _urmsg_shown_name(node)
        keywords = python_dict()
        for key, value in (getattr(node, "keyword", None) or ()):
            keywords[key] = value
        own_tests = tests
        if "sensitive" in keywords:
            own_tests = own_tests + ((keywords["sensitive"], True),)

        for key in _URMSG_ACT_WAYS + _URMSG_ACT_OTHER:
            text = keywords.get(key)
            if text is None:
                continue
            results = _urmsg_act_text(text)
            if results is None:
                _urmsg_not_whole(rec, u"an action that cannot be read")
                continue
            for res in results:
                for target, _value in res[1]:
                    rec.writes.add(target)
            sends = python_list(res for res in results
                                if res[2] is not None or res[4] is not None or res[5])
            if not sends:
                continue
            if key in _URMSG_ACT_OTHER or shown in _URMSG_TIMED:
                _urmsg_not_whole(rec, u"the screen may end by itself or by a drag")
                continue
            if loop:
                _urmsg_not_whole(rec, u"buttons made in a loop")
                continue
            caption = _urmsg_caption(node, shown)
            mine = python_list()
            for res in sends:
                way_tests = own_tests + res[0]
                if res[5]:
                    mine.extend(opened(res[5], way_tests))
                if res[2] is not None:
                    mine.append(_URMSGWay(res[2], caption, way_tests, res[3], res[1]))
                elif res[4] is not None:
                    mine.append(_URMSGWay("back", caption, way_tests, None,
                                          res[1] + ((u"_return", res[4]),)))
            for way in reversed(mine):
                rec.ways.append(way)

    # Keywords that place a displayable on the screen.
    _URMSG_PLACE_KEYS = frozenset((
        "pos", "xpos", "ypos", "align", "xalign", "yalign", "offset", "xoffset",
        "yoffset", "center", "xcenter", "ycenter", "anchor", "xanchor", "yanchor",
        "area", "xycenter"))

    def _urmsg_sl_places(tree, params):
        """id(screen node) -> the screen parameters its place reads (its own
        keywords and those of the boxes around it), as a frozenset."""

        mine = python_set(params)
        out = python_dict()
        todo = python_list(((tree, frozenset()),))
        while todo:
            node, above = todo.pop()
            here = python_set(above)
            for key, value in (getattr(node, "keyword", None) or ()):
                if key in _URMSG_PLACE_KEYS:
                    read = _urmsg_names_read(value) or ()
                    for name in read:
                        if name in mine:
                            here.add(name)
            here = frozenset(here)
            out[id(node)] = here
            for _cond, block in (getattr(node, "entries", None) or ()):
                if block is not None:
                    todo.append((block, here))
            for child in (getattr(node, "children", None) or ()):
                todo.append((child, here))
        return out

    def _urmsg_param_shown(text, params):
        """The parameter a text's words are: `p`, `"%s" % p`, `"[p]"`."""

        try:
            expr = _urmsg_parse(u"%s" % (text,), "eval").body
        except Exception:
            return None
        kind = _urmsg_kind_of(expr)
        if kind == "Name":
            return expr.id if expr.id in params else None
        if kind == "BinOp" and _urmsg_kind_of(expr.op) == "Mod":
            ok, value = _urmsg_literal(expr.left)
            right = expr.right
            if ok and value == u"%s" and _urmsg_kind_of(right) == "Name" and right.id in params:
                return right.id
            return None
        ok, value = _urmsg_literal(expr)
        if ok and isinstance(value, _urmsg_texts):
            m = _URMSG_BRACKET_PARAM.match(value)
            if m is not None and m.group(1) in params:
                return m.group(1)
        return None

    _URMSG_BRACKET_PARAM = _urmsg_re.compile(r"^\[([A-Za-z_]\w*)\]$")

    def _urmsg_text_param(node, params):
        """The parameter a `text` statement shows, or None."""

        texts = getattr(node, "positional", None) or ()
        return _urmsg_param_shown(texts[0], params) if texts and params else None

    def _urmsg_caption_param(node, shown, params):
        """The parameter a button's own words show, or None."""

        if not params:
            return None
        if shown == "textbutton":
            texts = getattr(node, "positional", None) or ()
            return _urmsg_param_shown(texts[0], params) if texts else None
        for child in (getattr(node, "children", None) or ()):
            if _urmsg_shown_name(child) == "text":
                return _urmsg_text_param(child, params)
        return None

    def _urmsg_bound(rec, args):
        """The literal words handed to a screen's parameters: (positional,
        keywords) of a call -> {parameter: words}."""

        out = python_dict()
        if args is None:
            return out
        positional, named = args
        k = 0
        while k < len(positional) and k < len(rec.params):
            if positional[k] is not None:
                out[rec.params[k]] = positional[k]
            k += 1
        for name in named:
            if named[name] is not None:
                out[name] = named[name]
        return out

    def _urmsg_call_args(call):
        """(positional, keywords) of a parsed call: each a literal text or
        None."""

        positional = python_list()
        for arg in call.args:
            ok, value = _urmsg_word(arg)
            positional.append(value if ok and isinstance(value, _urmsg_texts) else None)
        named = python_dict()
        for kw in (call.keywords or ()):
            if kw.arg is None:
                continue
            ok, value = _urmsg_word(kw.value)
            named[kw.arg] = value if ok and isinstance(value, _urmsg_texts) else None
        return positional, named

    def _urmsg_line_args(rest):
        """The arguments written after `call screen name` on its line, or
        None."""

        rest = rest.lstrip()
        if not rest.startswith(u"("):
            return None
        at = 0
        while True:
            at = rest.find(u")", at + 1)
            if at < 0:
                return None
            try:
                call = _urmsg_parse(u"f" + rest[:at + 1], "eval").body
            except Exception:
                continue
            if _urmsg_kind_of(call) == "Call":
                return _urmsg_call_args(call)
            return None

    def _urmsg_mark_inside(rec):
        """Mark each way whose tests read a value the screen decides."""

        mine = python_set(rec.own)
        for name in rec.writes:
            if name.startswith(u"\x00screen "):
                mine.add(name[8:])
            else:
                mine.add(name)
        for way in rec.ways:
            for test, _holds in way.tests:
                read = _urmsg_names_read(test) if test is not None else None
                if read and (read & mine):
                    way.inside = True

    # ---- the statements a choice can be

    def _urmsg_choice(node):
        """The choice this statement is (_URMSGChoice), or None. Remembered
        per statement in the twin's own memory."""

        g = _urmsg_own()
        try:
            return _urmsg_choice_in(node)
        finally:
            _urmsg_own_end(g)

    def _urmsg_choice_in(node):
        if node is None:
            return None
        g = _urmsg_graph()
        hit = g.choices.get(id(node))
        if hit is not None and hit[0] is node:
            return hit[1]
        choice = _urmsg_choice_read(node)
        if choice is not None and choice.shape != "menu":
            _urmsg_targets(choice)
            _urmsg_handoff(choice)
        if len(g.choices) >= _URMSG_CAP_FACTS:
            g.choices.clear()
        g.choices[id(node)] = (node, choice)
        return choice

    def _urmsg_choice_read(node):
        k = _urmsg_kind(node)
        if k == _URMSG_K_MENU:
            fact = _urmsg_fact(node)
            if not fact.arms:
                return None
            choice = _URMSGChoice(node, "menu")
            ways = python_list()
            for _i, cond, _a, _block, start, caption in fact.arms:
                tests = () if _urmsg_no_test(cond) else ((_urmsg_text_of(cond), True),)
                way = _URMSGWay("enter", caption, tests)
                way.target = start
                ways.append(way)
            choice.ways = tuple(ways)
            return choice
        if k == _URMSG_K_USER:
            line = u"%s" % (getattr(node, "line", None) or u"",)
            m = _URMSG_CALL_SCREEN.match(line.strip())
            if m is None:
                return None
            choice = _URMSGChoice(node, "screen")
            if m.group(1):
                _urmsg_not_whole(choice, u"a screen worked out while playing")
                return choice
            _urmsg_screen_choice(choice, m.group(2), (),
                                 _urmsg_line_args(line.strip()[m.end():]))
            return choice
        if k == _URMSG_K_PY:
            source = getattr(getattr(node, "code", None), "source", None)
            tree = _urmsg_tree(source) if source else None
            if tree is None:
                return None
            return _urmsg_py_choice(node, tree)
        if k == _URMSG_K_WHILE and _urmsg_waits_only(getattr(node, "block", None)):
            return _urmsg_shown_choice(node)
        return None

    def _urmsg_text_of(expr):
        return u"%s" % (expr,)

    def _urmsg_screen_choice(choice, name, handed, args=None):
        """A choice made on the screen `name`; handed: the names its value
        is also written to (`x = renpy.call_screen(...)`); args: the
        literal words handed to its parameters (_urmsg_call_args), for the
        captions that show them."""

        choice.screen = name
        rec = _urmsg_screen(name)
        bound = _urmsg_bound(rec, args)
        ways = python_list()
        for way in rec.ways:
            sets = way.sets
            for target, value in way.sets:
                if target == u"_return":
                    for also in handed:
                        sets = sets + ((also, value),)
            caption = way.caption
            if caption is None and way.param is not None:
                caption = bound.get(way.param)
            copy = _URMSGWay(way.go, caption, way.tests, way.label, sets)
            copy.inside = way.inside
            ways.append(copy)
        choice.ways = tuple(ways)
        for why in rec.why:
            _urmsg_not_whole(choice, why)

    def _urmsg_one_call(tree):
        """(name assigned or None, the call) for a python line that is one
        call, bare or assigned to one name; else (None, None)."""

        if len(tree.body) != 1:
            return None, None
        top = tree.body[0]
        kind = _urmsg_kind_of(top)
        if kind == "Expr" and _urmsg_kind_of(top.value) == "Call":
            return None, top.value
        if (kind == "Assign" and len(top.targets) == 1
                and _urmsg_kind_of(top.value) == "Call"):
            name = _urmsg_name(top.targets[0])
            if name is not None:
                return name, top.value
        return None, None

    def _urmsg_py_choice(node, tree):
        target, call = _urmsg_one_call(tree)
        if call is not None:
            name = _urmsg_call_name(call)
            if name == "renpy.call_screen":
                choice = _URMSGChoice(node, "screen")
                ok, screen = _urmsg_lit_arg(call, 0, "_screen_name")
                if not ok or not isinstance(screen, _urmsg_texts):
                    _urmsg_not_whole(choice, u"a screen worked out while playing")
                    return choice
                positional, named = _urmsg_call_args(call)
                _urmsg_screen_choice(choice, screen, (target,) if target else (),
                                     (positional[1:], named))
                return choice
            if name == "ui.interact" and target is not None:
                return _urmsg_ui_choice(node, target)
            if target is None and (name == "ui.interact" or (
                    name == "renpy.pause" and any(
                        kw.arg == "hard" and _urmsg_word(kw.value) == (True, True)
                        for kw in (call.keywords or ())))):
                return _urmsg_shown_choice(node)
            if target is not None and name is not None:
                choice = _urmsg_fn_menu(node, target, call, name)
                if choice is not None:
                    return choice
            return None
        return _urmsg_code_pick(node, tree)

    # ---- a menu shown by a function

    _URMSG_MENU_FNS = frozenset(("renpy.display_menu", "renpy.exports.display_menu"))

    def _urmsg_shows_menu(fdef, depth, seen):
        """True when a game function's def reaches renpy.display_menu,
        itself or through the game's functions it calls."""

        for node in _urmsg_pyast.walk(fdef):
            name = _urmsg_call_name(node)
            if name is None:
                continue
            if name in _URMSG_MENU_FNS:
                return True
            if depth < _URMSG_FN_DEPTH and u"." not in name and name not in seen:
                fn = _urmsg_game_fn(getattr(renpy.store, name, None))
                inner = _urmsg_def_of(fn) if fn is not None else None
                if inner is not None and _urmsg_shows_menu(inner, depth + 1, seen + (name,)):
                    return True
        return False

    def _urmsg_fn_menu(node, target, call, name):
        """`x = renpy.display_menu([...])`, or `x = f([...])` where f is a
        game function that shows one: the player picks one of the listed
        captions, handed on in x. The game's function may leave some out or
        add its own, so such a choice is never whole."""

        direct = name in _URMSG_MENU_FNS
        if not direct:
            if u"." in name:
                return None
            fn = _urmsg_game_fn(getattr(renpy.store, name, None))
            fdef = _urmsg_def_of(fn) if fn is not None else None
            if fdef is None or not _urmsg_shows_menu(fdef, 0, (name,)):
                return None
        items = _urmsg_arg(call, 0, "items")
        if items is None or _urmsg_kind_of(items) not in ("List", "Tuple"):
            return None
        choice = _URMSGChoice(node, "function")
        if not direct:
            _urmsg_not_whole(choice, u"a game function decides what is offered")
        ways = python_list()
        for elt in items.elts:
            ok, value = _urmsg_word(elt)
            if ok and isinstance(value, _urmsg_texts):
                caption = value
            elif (ok and isinstance(value, tuple) and len(value) == 2
                    and isinstance(value[0], _urmsg_texts)):
                caption, value = value
                if value is None:
                    # A caption line of the menu, not a choice.
                    continue
            else:
                _urmsg_not_whole(choice, u"an option that cannot be read")
                continue
            if not direct:
                # What the game's function hands back is its own business
                # (a caption, an index, a value it was handed): not read.
                value = _URMSG_ANY
            ways.append(_URMSGWay("back", caption, (), None, ((target, value),)))
        choice.ways = tuple(ways)
        return choice

    # ---- a route picked in a python block

    _URMSG_PY_IF = _urmsg_re.compile(r"^\s*(?:el)?if\s+(.*?)\s*:\s*(#.*)?$")

    def _urmsg_code_pick(node, tree):
        """
        A python block whose jumps all stand at the end of the arms of one
        if/elif/else chain at its top level: the code picks where the story
        goes. Each arm is a way (its test quoted from the source); an arm
        that does not jump carries on after the block. None for any other
        block - and for one that jumps through a name (that is not a pick
        the script can show).
        """

        source = node.code.source
        jumps = python_list()
        for one in _urmsg_inside(tree.body):
            name = _urmsg_call_name(one)
            if name in ("renpy.jump", "renpy.call"):
                jumps.append(one)
        if not jumps:
            return None
        chain = None
        for top in tree.body:
            holds = any(one in jumps for one in _urmsg_inside((top,)))
            if not holds:
                continue
            if chain is not None or _urmsg_kind_of(top) != "If":
                return None
            chain = top
        lines = source.split(u"\n")
        choice = _URMSGChoice(node, "code")
        ways = python_list()
        before = ()
        arm = chain
        while arm is not None:
            m = _URMSG_PY_IF.match(lines[arm.lineno - 1]) if 0 < arm.lineno <= len(lines) else None
            text = m.group(1) if m else None
            body = arm.body
            orelse = arm.orelse
            way = _urmsg_code_arm(body, jumps, before + ((text, True),))
            if way is False:
                return None
            ways.append(way)
            before = before + ((text, False),)
            if len(orelse) == 1 and _urmsg_kind_of(orelse[0]) == "If":
                arm = orelse[0]
                continue
            if orelse:
                way = _urmsg_code_arm(orelse, jumps, before)
                if way is False:
                    return None
                ways.append(way)
            else:
                ways.append(_URMSGWay("back", None, before))
            arm = None
        choice.ways = tuple(ways)
        return choice

    def _urmsg_code_arm(body, jumps, tests):
        """The way of one arm of a code pick, or False when its jumps do not
        all stand as its one last statement."""

        mine = python_list(one for one in _urmsg_inside(body) if one in jumps)
        if not mine:
            return _URMSGWay("back", None, tests)
        last = body[-1]
        if (len(mine) != 1 or _urmsg_kind_of(last) != "Expr" or last.value is not mine[0]):
            return False
        ok, label = _urmsg_lit_arg(mine[0], 0, "label")
        if not ok or not isinstance(label, _urmsg_texts):
            return False
        go = "visit" if _urmsg_call_name(mine[0]) == "renpy.call" else "leave"
        return _URMSGWay(go, None, tests, label)

    # ---- buttons made in python before ui.interact()

    def _urmsg_homes():
        """
        id(statement) -> (statement, the statement whose block holds it,
        that block, its place in it), for every statement of the script;
        for a statement at the top of a file (a released game's compiled
        script often has `label x:` with nothing in its block and the scene
        after it at the top level, as Being a DIK does): (statement, None,
        None, the statement before it at the top level or None).

        The script's own shape, the same in both memories: one table, kept
        in the base (the twin asks it), built by the worker at start-up
        (_urmsg_homes_ahead) - the Story line's first open built its own,
        0.9 s on Being a DIK.
        """

        g = _urmsg_graph()
        home = g.base if g.base is not None else g
        if home.homes is None:
            # its start-up job, finished from where it is, not begun again
            _urm_work_finish("statement homes")
        if home.homes is None:
            for _step in _urmsg_homes_build(home, None):
                pass
        return home.homes

    def _urmsg_homes_build(g, t):
        """Build _urmsg_homes's table into g.homes, as a generator: with a
        stretch table t, it yields whenever that pass's slice is long."""

        homes = python_dict()
        every = getattr(renpy.game.script, "all_stmts", None) or ()
        for parent in every:
            if t is not None and _urmsg_stretch_late(t):
                yield
            for _kind, _arm, _extra, block in _urmsg_children(parent):
                at = 0
                for child in block:
                    homes[id(child)] = (child, parent, block, at)
                    at += 1
        tops = python_list()
        for node in every:
            if t is not None and _urmsg_stretch_late(t):
                yield
            if id(node) not in homes:
                tops.append(node)
        for node in tops:
            homes[id(node)] = (node, None, None, None)
        for node in tops:
            if t is not None and _urmsg_stretch_late(t):
                yield
            nx = getattr(node, "next", None)
            home = homes.get(id(nx)) if nx is not None else None
            if home is not None and home[0] is nx and home[2] is None:
                homes[id(nx)] = (nx, None, None, node)
        g.homes = homes

    class _URMSGBeat(python_object):
        """A clock for _urmsg_stretch_late outside the stretch pass: a slice
        of `seconds` (the worker's share of a frame)."""

        def __init__(self, seconds):
            self.tick = 0
            self.beat = _urmsg_clock()
            self.beat_len = seconds

    def _urmsg_homes_ahead():
        """The worker's job: the homes table, in slices, at start-up."""

        g = _urmsg_graph()
        home = g.base if g.base is not None else g
        if home.homes is None:
            beat = _URMSGBeat(0.006)
            for _step in _urmsg_homes_build(home, beat):
                yield None
                if home.homes is not None:
                    break       # another reader built it meanwhile
                beat.beat = _urmsg_clock()
        yield _URMWorkDone()

    try:
        _urm_work_slices("statement homes", _urmsg_homes_ahead)
    except Exception as error:
        print("MRM: the homes table waits for its first reader (%s)" % (error,))

    def _urmsg_before(node):
        """(the statement before this one in its block, or None; the
        statement whose block it starts, or None)."""

        home = _urmsg_homes().get(id(node))
        if home is None or home[0] is not node:
            return None, None
        _child, parent, block, at = home
        if block is None:
            return at, None
        if at > 0:
            return block[at - 1], None
        return None, parent

    _URMSG_UI_BUTTONS = frozenset(("ui.imagebutton", "ui.textbutton", "ui.button",
                                   "ui.hotspot"))
    _URMSG_UI_PLAIN = frozenset((
        "ui.add", "ui.text", "ui.image", "ui.frame", "ui.vbox", "ui.hbox",
        "ui.close", "ui.fixed", "ui.window", "ui.null", "ui.at", "ui.layer",
        "ui.grid", "ui.side", "ui.viewport", "ui.transform", "ui.keymap",
        "renpy.hide_screen"))
    _URMSG_WAITS = frozenset((
        "ui.interact", "renpy.pause", "renpy.with_statement", "renpy.input",
        "renpy.call_screen", "renpy.say", "renpy.display_menu", "renpy.transition"))
    _URMSG_USER_WAITS = ("pause", "call screen", "with ")
    _URMSG_USER_QUIET = ("hide", "play", "stop", "queue", "voice", "window",
                         "nvl clear", "camera")

    def _urmsg_ui_choice(node, target):
        """
        Buttons made with ui.* calls, then `target = ui.interact()`. The
        buttons of the choice are the ones made since the last thing that
        waited for the player: walking back from the interact, the window
        opens after the nearest label, statement that waits (a say, a
        pause, a `with`, a menu, a called screen, another interact), or
        check each of whose arms either waits after the last thing it puts
        up or puts up nothing. In the window a button is a way (a check
        around it gives its test); anything else that puts up something to
        click makes the choice not whole; hides, images, literal
        assignments and the engine's noise pass.
        """

        choice = _URMSGChoice(node, "ui")
        found = python_list()
        here = node
        while True:
            before, parent = _urmsg_before(here)
            if before is not None:
                step_ways, stopped = _urmsg_ui_step(before, (), choice, target)
                found.extend(step_ways)
                if stopped:
                    break
                here = before
                continue
            if parent is None or _urmsg_kind(parent) != _URMSG_K_IF:
                break
            here = parent
        found.reverse()
        choice.ways = tuple(found)
        return choice

    def _urmsg_ui_step(node, tests, choice, target):
        """One statement before ui.interact, walked back: (ways, stopped)
        where stopped is True when a wait was reached before or inside it."""

        k = _urmsg_kind(node)
        if k in (_URMSG_K_LABEL, _URMSG_K_SAY, _URMSG_K_MENU, _URMSG_K_TRANS,
                 _URMSG_K_JUMP, _URMSG_K_RET):
            return (), True
        if k == _URMSG_K_CALL or k == _URMSG_K_WHILE:
            _urmsg_not_whole(choice, u"something before the buttons that cannot be read")
            return (), True
        if k == _URMSG_K_PLAIN:
            if type(node).__name__ == "With":
                return (), True
            return (), False
        if k == _URMSG_K_USER:
            line = (u"%s" % (getattr(node, "line", None) or u"",)).strip()
            if line.startswith(_URMSG_USER_WAITS) or line == u"pause":
                return (), True
            if line.startswith(_URMSG_USER_QUIET):
                return (), False
            _urmsg_not_whole(choice, u"something put up that cannot be read")
            return (), False
        if k == _URMSG_K_IF:
            return _urmsg_ui_check(node, tests, choice, target)
        if k == _URMSG_K_PY:
            source = getattr(getattr(node, "code", None), "source", None)
            tree = _urmsg_tree(source) if source else None
            if tree is None:
                _urmsg_not_whole(choice, u"python that does not parse")
                return (), False
            ways = python_list()
            body = python_list(tree.body)
            body.reverse()
            for top in body:
                step = _urmsg_ui_line(top, tests, choice, target)
                if step is True:
                    return ways, True
                ways.extend(step)
            return ways, False
        return (), False

    def _urmsg_ui_line(top, tests, choice, target):
        """One parsed python statement before ui.interact (as
        _urmsg_ui_step)."""

        kind = _urmsg_kind_of(top)
        call = None
        if kind == "Expr":
            call = top.value
        elif kind in ("Assign", "AugAssign"):
            call = top.value
            if not any(_urmsg_kind_of(one) == "Call" for one in _urmsg_pyast.walk(call)):
                # An assignment puts nothing up.
                return ()
        name = _urmsg_call_name(call) if call is not None else None
        if name is None:
            _urmsg_not_whole(choice, u"python before the buttons that cannot be read")
            return ()
        if name in _URMSG_WAITS:
            return True
        if name in _URMSG_UI_BUTTONS:
            clicked = None
            for kw in (call.keywords or ()):
                if kw.arg == "clicked":
                    clicked = kw.value
            if clicked is None:
                return ()
            results = _urmsg_act(clicked, python_list((python_list(((), (), None, None, None, ())),)))
            if results is None:
                _urmsg_not_whole(choice, u"a button whose click cannot be read")
                return ()
            caption = None
            if name == "ui.textbutton":
                ok, value = _urmsg_lit_arg(call, 0, "label")
                if ok and isinstance(value, _urmsg_texts):
                    caption = value
            ways = python_list()
            for res in results:
                if res[5]:
                    _urmsg_not_whole(choice, u"a button opens a screen")
                if res[2] is not None:
                    ways.append(_URMSGWay(res[2], caption, tests + res[0], res[3], res[1]))
                elif res[4] is not None:
                    ways.append(_URMSGWay("back", caption, tests + res[0], None,
                                          res[1] + ((target, res[4]),)))
            ways.reverse()
            return ways
        if name != "renpy.show_screen" and (name in _URMSG_UI_PLAIN
                                            or name.startswith(_URMSG_NOISE)):
            return ()
        _urmsg_not_whole(choice, u"something put up that cannot be read")
        return ()

    def _urmsg_ui_check(node, tests, choice, target):
        """A check before ui.interact, walked back (as _urmsg_ui_step)."""

        arms = python_list()
        before = tests
        has_else = False
        for cond, block in (getattr(node, "entries", None) or ()):
            if _urmsg_is_else(cond):
                arm_tests = before
                has_else = True
            else:
                arm_tests = before + ((_urmsg_text_of(cond), True),)
                before = before + ((_urmsg_text_of(cond), False),)
            arms.append((arm_tests, block or ()))
        if not has_else:
            arms.append((before, ()))

        found = python_list()
        waits = 0
        opens = True
        for arm_tests, block in arms:
            ways = python_list()
            waited = False
            put = False
            for stmt in block:
                step_ways, stopped = _urmsg_ui_step(stmt, arm_tests, choice, target)
                if stopped:
                    waited = True
                    put = False
                    ways = python_list()
                if step_ways:
                    put = True
                    for way in reversed(step_ways):
                        ways.append(way)
            if waited:
                waits += 1
            if put:
                opens = False
                found.extend(ways)
        if waits and opens:
            return (), True
        if waits and not opens:
            _urmsg_not_whole(choice, u"a check that both waits and puts up buttons")
        found.reverse()
        return found, False

    # ---- screens shown before the game waits (Finding Cloud 9's rooms:
    # `show screen HouseFrontScreen` then `while SceneIsActive == False:
    # pause`; a hard pause; a bare ui.interact()). The player leaves by a
    # button of a screen on show. Only these waits are read so: a plain
    # pause ends on a click and is no choice.

    def _urmsg_waits_only(block):
        """True for a loop body that only waits: pauses."""

        if not block:
            return False
        for stmt in block:
            k = _urmsg_kind(stmt)
            if k == _URMSG_K_USER:
                if not (u"%s" % (getattr(stmt, "line", None) or u"",)).strip().startswith(u"pause"):
                    return False
            elif k == _URMSG_K_PY:
                tree = _urmsg_tree(stmt.code.source)
                target, call = _urmsg_one_call(tree) if tree is not None else (None, None)
                if call is None or target is not None or _urmsg_call_name(call) != "renpy.pause":
                    return False
            else:
                return False
        return True

    _URMSG_SHOW_SCREEN = _urmsg_re.compile(r"^(show|hide)\s+screen\s+([A-Za-z_][\w.]*)")

    def _urmsg_shown_choice(node):
        """
        The screens shown on the straight way before a wait, and the ways
        out of them: walking back from the wait, every `show screen` (and
        renpy.show_screen) not hidden since, up to the label it stands in,
        the first statement that leaves or waits on a choice, or the first
        line that cannot be read (what it does to screens shown before it
        is not known; screens shown earlier are the walks' "on show"). A
        button that only ends the pause makes the choice not whole. No
        shown screen with a way out: no choice.
        """

        choice = _URMSGChoice(node, "shown")
        shown = python_list()
        hidden = python_set()
        here = node
        while True:
            before, parent = _urmsg_before(here)
            if before is not None:
                if _urmsg_shown_step(before, shown, hidden):
                    break
                here = before
                continue
            if parent is None or _urmsg_kind(parent) not in (_URMSG_K_IF, _URMSG_K_WHILE):
                break
            here = parent
        shown.reverse()
        ways = python_list()
        tested = python_set()
        if _urmsg_kind(node) == _URMSG_K_WHILE:
            tested = _urmsg_names_read(getattr(node, "condition", u"")) or python_set()
        for name in shown:
            rec = _urmsg_screen(name)
            for why in rec.why:
                _urmsg_not_whole(choice, why)
            if tested & rec.writes:
                _urmsg_not_whole(choice, u"a button ends the wait")
            for way in rec.ways:
                if way.go in ("leave", "visit"):
                    copy = _URMSGWay(way.go, way.caption, way.tests, way.label, way.sets)
                    copy.inside = way.inside
                    ways.append(copy)
                else:
                    _urmsg_not_whole(choice, u"a button only ends the wait")
        if not ways:
            return None
        choice.ways = tuple(ways)
        choice.screen = shown[0] if len(shown) == 1 else None
        return choice

    def _urmsg_shown_step(node, shown, hidden):
        """One statement before a wait, walked back: True to stop."""

        k = _urmsg_kind(node)
        if k in (_URMSG_K_SAY, _URMSG_K_PLAIN):
            return False
        if k == _URMSG_K_USER:
            line = (u"%s" % (getattr(node, "line", None) or u"",)).strip()
            m = _URMSG_SHOW_SCREEN.match(line)
            if m is not None:
                if m.group(1) == u"hide":
                    hidden.add(m.group(2))
                elif m.group(2) not in hidden and m.group(2) not in shown:
                    shown.append(m.group(2))
                return False
            return not (line.startswith(_URMSG_USER_QUIET) or line.startswith(u"pause"))
        if k == _URMSG_K_PY:
            tree = _urmsg_tree(node.code.source)
            if tree is None:
                return True
            body = python_list(tree.body)
            body.reverse()
            for top in body:
                kind = _urmsg_kind_of(top)
                if kind in ("Assign", "AugAssign") and not any(
                        _urmsg_kind_of(one) == "Call" for one in _urmsg_pyast.walk(top.value)):
                    continue
                call = top.value if kind == "Expr" else None
                name = _urmsg_call_name(call) if call is not None else None
                if name in ("renpy.show_screen", "renpy.hide_screen"):
                    ok, screen = _urmsg_lit_arg(call, 0, "_screen_name")
                    if not ok or not isinstance(screen, _urmsg_texts):
                        return True
                    if name == "renpy.hide_screen":
                        hidden.add(screen)
                    elif screen not in hidden and screen not in shown:
                        shown.append(screen)
                    continue
                if name is not None and name.startswith(_URMSG_NOISE):
                    continue
                return True
            return False
        return True

    # ---- what is on show while a walk goes on (walks with ways=True)

    _URMSG_NOT_SHOWN = u"\x00not known"

    def _urmsg_live_shown():
        """The names of the screens the game shows right now (a walk that
        starts where the game is starts with them), or None."""

        out = python_list()
        try:
            layers = renpy.game.context().scene_lists.layers
            for layer in layers:
                for entry in layers[layer]:
                    name = getattr(getattr(entry, "displayable", None), "screen_name", None)
                    if isinstance(name, tuple):
                        name = name[0] if name else None
                    if name and name not in out:
                        out.append(name)
        except Exception:
            return None
        return out

    def _urmsg_walk_shown(w):
        """What a run of w left on show, to hand to the runs of the arms
        of the split it stopped at (`shown` of _urmsg_run)."""

        return python_list(w.live) if w.live is not None else _URMSG_NOT_SHOWN

    def _urmsg_live_step(w, node, k):
        """A statement a walk passes: the screens it shows and hides."""

        if k == _URMSG_K_USER:
            line = (u"%s" % (getattr(node, "line", None) or u"",)).strip()
            m = _URMSG_SHOW_SCREEN.match(line)
            if m is None:
                return
            if m.group(1) == u"hide":
                if m.group(2) in w.live:
                    w.live.remove(m.group(2))
            elif m.group(2) not in w.live:
                w.live.append(m.group(2))
            return
        source = getattr(getattr(node, "code", None), "source", None) or u""
        if u"show_screen" not in source and u"hide_screen" not in source:
            return
        tree = _urmsg_tree(source)
        if tree is None:
            w.live = None
            return
        calls = python_list()
        for one in _urmsg_inside(tree.body):
            name = _urmsg_call_name(one)
            if name in ("renpy.show_screen", "renpy.hide_screen"):
                calls.append((getattr(one, "lineno", 0), getattr(one, "col_offset", 0), name, one))
        calls.sort(key=_urmsg_first_two)
        for _line, _col, name, call in calls:
            ok, screen = _urmsg_lit_arg(call, 0, "_screen_name")
            if not ok or not isinstance(screen, _urmsg_texts):
                w.live = None
                return
            if name == "renpy.hide_screen":
                if screen in w.live:
                    w.live.remove(screen)
            elif screen not in w.live:
                w.live.append(screen)

    def _urmsg_first_two(row):
        return row[0], row[1]

    def _urmsg_on_show(w):
        """The game's own screens on show where the last run of w stopped
        (the engine's, URM's and ours left out), each as (name, what it
        offers: _urmsg_screen): next to a stretch's kind, never changing it.
        None when that is not known."""

        if w.live is None:
            return None
        g = _urmsg_own()
        try:
            out = python_list()
            for name in w.live:
                rec = _urmsg_screen(name)
                if rec.file and _urmsg_engine_file(rec.file):
                    continue
                out.append((name, rec))
            return tuple(out)
        finally:
            _urmsg_own_end(g)

    # ---- what a choice's ways go to, and the check that reads them

    def _urmsg_targets(choice):
        """Find each way's first statement; read what a visited label hands
        on."""

        for way in choice.ways:
            if way.go in ("leave", "visit"):
                way.target = _urmsg_lookup(way.label)
                if way.go == "visit" and way.target is not None:
                    sets = _urmsg_label_sets(way.target)
                    if sets is not None:
                        way.sets = way.sets + sets
            elif way.go == "back":
                way.target = choice.after
        names = python_list()
        for way in choice.ways:
            for name, _value in way.sets:
                if name is not None and not name.startswith(u"\x00") and name not in names:
                    names.append(name)
        if choice.shape == "screen" and u"_return" not in names:
            names.append(u"_return")
        choice.names = tuple(names)

    def _urmsg_label_sets(label):
        """The (name, value) pairs a label writes before it returns, when it
        returns immediately after writing them; else
        None."""

        out = python_list()
        for stmt in (getattr(label, "block", None) or ()):
            k = _urmsg_kind(stmt)
            if k == _URMSG_K_RET:
                return tuple(out)
            if k != _URMSG_K_PY:
                return None
            tree = _urmsg_tree(stmt.code.source)
            if tree is None:
                return None
            for top in tree.body:
                if _urmsg_kind_of(top) != "Assign" or len(top.targets) != 1:
                    return None
                name = _urmsg_name(top.targets[0])
                ok, value = _urmsg_word(top.value)
                if name is None or not ok:
                    return None
                out.append((name, value))
        return None

    _URMSG_HANDOFF_STEPS = 16

    def _urmsg_handoff(choice):
        """
        The check right after a choice that reads a value its ways hand on
        (`if tmp_choice == 1:`, `if result == "go_up":`): each way that hands
        on a literal gets the arm it takes. Only statements that write
        nothing are stepped over (a line, an image, `$ x = x`); every test
        of the check must compare one handed name with literals (== or in),
        or be its `else`. Anything else: no arm is told.
        """

        names = python_set(choice.names)
        if not names:
            return
        node = choice.after
        steps = 0
        while node is not None and steps < _URMSG_HANDOFF_STEPS:
            steps += 1
            k = _urmsg_kind(node)
            if k == _URMSG_K_IF:
                break
            if k in (_URMSG_K_SAY, _URMSG_K_PLAIN):
                node = node.next
                continue
            if k == _URMSG_K_USER:
                line = (u"%s" % (getattr(node, "line", None) or u"",)).strip()
                if line.startswith(_URMSG_USER_QUIET) or line == u"pause":
                    node = node.next
                    continue
                return
            if k == _URMSG_K_PY:
                tree = _urmsg_tree(node.code.source)
                if tree is None or not _urmsg_writes_none(tree):
                    return
                node = node.next
                continue
            return
        else:
            return

        tested = None
        arms = python_list()
        index = 0
        for cond, _block in node.entries:
            if _urmsg_is_else(cond) or _urmsg_no_test(cond):
                arms.append((index, None, None))
                index += 1
                continue
            try:
                test = _urmsg_parse(u"%s" % (cond,), "eval").body
            except Exception:
                return
            if _urmsg_kind_of(test) != "Compare" or len(test.ops) != 1:
                return
            op = _urmsg_kind_of(test.ops[0])
            name = _urmsg_name(test.left)
            if name is None or name not in names or (tested is not None and name != tested):
                return
            tested = name
            ok, value = _urmsg_word(test.comparators[0])
            if op == "In" and not ok and _urmsg_kind_of(test.comparators[0]) == "List":
                values = python_list()
                for elt in test.comparators[0].elts:
                    one_ok, one = _urmsg_word(elt)
                    if not one_ok:
                        return
                    values.append(one)
                ok, value = True, tuple(values)
            if not ok or op not in ("Eq", "In"):
                return
            if op == "In" and not isinstance(value, tuple):
                return
            arms.append((index, op, value))
            index += 1
        if tested is None:
            return
        choice.check = node
        for way in choice.ways:
            # Only a way that comes back after the choice reaches the check:
            # one that ends it, or a visit to a label known to return.
            if way.go == "visit":
                if way.target is None or _urmsg_returns(way.target) is not True:
                    continue
            elif way.go != "back":
                continue
            value = _URMSG_ANY
            for name, one in way.sets:
                if name == tested:
                    value = one
            if value is _URMSG_ANY:
                continue
            taken = -1
            for at, op, want in arms:
                if op is None or (op == "Eq" and value == want) or (op == "In" and value in want):
                    taken = at
                    break
            way.arm = (node, taken)

    def _urmsg_writes_none(tree):
        """True for python that writes nothing: `x = x`, or the engine's
        noise (sounds, a pause is not here - it waits, which is fine)."""

        for top in tree.body:
            kind = _urmsg_kind_of(top)
            if (kind == "Assign" and len(top.targets) == 1
                    and _urmsg_name(top.targets[0]) is not None
                    and _urmsg_name(top.targets[0]) == _urmsg_name(top.value)):
                continue
            if kind == "Expr":
                name = _urmsg_call_name(top.value)
                if name is not None and name.startswith(_URMSG_NOISE):
                    continue
            return False
        return True

    def _urmsg_way_start(choice, way):
        """The statement a way's story really goes on with: the arm of the
        check it takes when that is told, else its target."""

        if way.arm is not None:
            check, at = way.arm
            if at < 0:
                return check.next
            block = check.entries[at][1]
            return block[0] if block else check.next
        return way.target

    # ---- the successor rule with every shape of choice (opt-in)

    def _urmsg_name_jump(node):
        """True for a python statement that jumps or calls through a name
        (`renpy.jump(currentEvent)`): where it goes is not in the script."""

        if _urmsg_kind(node) != _URMSG_K_PY:
            return False
        source = getattr(getattr(node, "code", None), "source", None) or u""
        if u"renpy.jump" not in source and u"renpy.call" not in source:
            return False
        tree = _urmsg_tree(source)
        if tree is None:
            return True
        for one in _urmsg_inside(tree.body):
            if _urmsg_call_name(one) in ("renpy.jump", "renpy.call"):
                ok, label = _urmsg_lit_arg(one, 0, "label")
                if not ok or not isinstance(label, _urmsg_texts):
                    return True
        return False

    def _urmsg_flow_ways(node):
        """
        Every statement control can reach next, with the player's ways of a
        choice of every shape: a screen's jumps and calls, the statement
        after it for ways that end it; a call that comes back is a visit,
        as in _urmsg_flow_visit. A choice that is not whole also goes on
        after it. A jump through a name leads nowhere the script can show:
        nothing. Every other statement as _urmsg_flow_visit.
        """

        g = _urmsg_own()
        try:
            return _urmsg_flow_ways_in(node)
        finally:
            _urmsg_own_end(g)

    def _urmsg_flow_ways_in(node):
        if _urmsg_name_jump(node):
            return ()
        choice = _urmsg_choice_in(node)
        if choice is None or choice.shape == "menu":
            return _urmsg_flow_visit(node)
        out = python_list()
        for way in choice.ways:
            if way.go == "visit" and way.target is not None:
                back = _urmsg_returns(way.target)
                if back is not False and choice.after is not None:
                    out.append(choice.after)
                if back is not True:
                    out.append(way.target)
            elif way.target is not None:
                out.append(way.target)
        if not choice.whole and choice.after is not None:
            out.append(choice.after)
        kept = python_list()
        for one in out:
            if all(one is not other for other in kept):
                kept.append(one)
        return tuple(kept)

    def _urmsg_flow_ways_meet(sites):
        """_urmsg_flow_ways for the search for a rejoin: a `return` leads
        to where the calls around the split go back to."""

        if not sites:
            return _urmsg_flow_ways_in

        def flow(node):
            if _urmsg_kind(node) == _URMSG_K_RET:
                return sites
            return _urmsg_flow_ways_in(node)

        return flow

    def _urmsg_is_pick(node):
        """True for a statement where the player picks (a choice of any
        shape but a code pick)."""

        choice = _urmsg_choice_in(node)
        return choice is not None and choice.shape != "code"

    def _urmsg_next_choice(start, truth, limit=3000):
        """_urmsg_next_split with ways: the nearest choice of the player of
        any shape at or ahead of start, and whether the search was cut."""

        g = _urmsg_own()
        try:
            return _urmsg_next_split_in(start, truth, limit, _urmsg_flow_ways_in,
                                        _urmsg_is_pick)
        finally:
            _urmsg_own_end(g)

    def _urmsg_plan_ways(origin, cap=4000, sites=()):
        """
        _urmsg_plan for a choice of any shape: (the statements its ways go
        on with, the rejoin or None), or None when it is no choice.
        Remembered per choice in the twin's own memory.
        """

        g0 = _urmsg_own()
        try:
            choice = _urmsg_choice_in(origin)
            if choice is None:
                return None
            g = _urmsg_graph()
            key = ("ways", id(origin), cap)
            if sites:
                marks = python_list()
                for site in sites:
                    marks.append(id(site))
                key = key + (tuple(marks),)
            hit = g.q.get(key)
            if hit is not None and hit[0] is origin:
                return python_list(hit[1]), hit[2]
            skipped = g.skipped
            starts = python_list()
            for way in choice.ways:
                starts.append(_urmsg_way_start(choice, way))
            if not choice.whole:
                starts.append(choice.after)
            rejoin = _urmsg_meeting(starts, origin, choice.after, cap,
                                    _urmsg_flow_ways_meet(sites))
            if g.skipped == skipped:
                if len(g.q) >= _URMSG_CAP_Q:
                    g.q.clear()
                g.q[key] = (origin, tuple(starts), rejoin)
            return starts, rejoin
        finally:
            _urmsg_own_end(g0)

    # ---- where the ways of a split go after it (the new map's reader facts)
    #
    # For each way of a split: does it reach the statement where the ways
    # meet again, end the game, only lead back to the split, go on its own
    # and never meet, or can that not be told; and the fewest said lines the
    # player hears on it before the meeting. Then whether the ways are
    # versions of one value. Asked in the twin and kept nowhere: a reader of
    # this section, never the index thread (FINDINGS.md, 2026-11-23).

    class _URMSGApartWay(python_object):
        """
        Where one way of a split goes. end: "meet" (the meeting point is
        ahead of it), "end" (read to its end, it never gets there and a
        `return` with no call around it can be reached: the game ends
        there), "back" (read to its end, it never gets there and leads back
        to the split), "never" (read to its end, it goes on its own and
        never gets there), or None (cannot tell: the search was cut, a jump
        or a call through a name, a call that may not come back, a `return`
        that may be a called scene's). cut: its search stopped at the cap.
        said: the fewest said lines (a Say that waits) the player hears on
        it before the meeting point, or None; said_cut: that count is only a
        floor - "at least" (its search was cut first, or a called scene's
        lines could not all be told). A way that does not meet has said
        None, unless its search was cut: then the floor of what it says
        before the cut.
        """

        __slots__ = ("end", "cut", "said", "said_cut")

        def __init__(self):
            self.end = None
            self.cut = False
            self.said = None
            self.said_cut = False

    class _URMSGApart(python_object):
        """The ways of one split after it: meet, the statement where two or
        more of them meet again - None when no such statement is found or a
        way that does not reach it cannot be told; ways, one _URMSGApartWay
        per start, in order."""

        __slots__ = ("meet", "ways")

        def __init__(self, meet, ways):
            self.meet = meet
            self.ways = tuple(ways)

    def _urmsg_apart(starts, origin, after, cap=4000, sites=(), top=False):
        """
        Where the ways of the split at origin go (starts: the statement each
        way goes on with; after: the statement after the split). sites: the
        statements the calls the split is inside go back to, when known
        (_urmsg_live_stack, for a split met from where the game is): a
        `return` leads there. top: the caller knows no call is around the
        split - only then is a `return` the end of the game.
        """

        g0 = _urmsg_own()
        try:
            return _urmsg_drain(_urmsg_apart_steps(starts, origin, after, cap, sites, top))
        finally:
            _urmsg_own_end(g0)

    def _urmsg_apart_steps(starts, origin, after, cap=4000, sites=(), top=False):
        """_urmsg_apart in steps. Only for a caller that has the twin in
        place while each step runs (_urmsg_owned_steps): its searches pause
        only then (_urmsg_meeting_steps)."""

        flow = _urmsg_flow_ways_meet(sites)
        meet = None
        for said in _urmsg_meeting_steps(starts, origin, after, cap, flow, True):
            if isinstance(said, _URMSGDone):
                meet = said.result
                break
            yield said
        lines = python_dict()
        ways = python_list()
        for start in starts:
            one = _URMSGApartWay()
            table, cut = python_dict(), False
            for said in _urmsg_reach_steps(start, origin, cap, True, flow):
                if isinstance(said, _URMSGDone):
                    table, cut = said.result
                    break
                yield said
            one.cut = cut
            if start is not None and meet is not None and id(meet) in table:
                one.end = "meet"
                one.said, one.said_cut = _urmsg_said_to(start, origin, meet, cap, flow, lines)
            elif start is None:
                pass
            elif cut:
                floor, _f = _urmsg_said_to(start, origin, None, cap, flow, lines)
                if floor is not None:
                    one.said, one.said_cut = floor, True
            else:
                one.end = _urmsg_apart_end(table, origin, flow, bool(top and not sites))
            ways.append(one)
        met = sum(1 for one in ways if one.end == "meet")
        if meet is not None and (met < 2 or any(one.end is None for one in ways)):
            # Two or more must meet there, and every other way must be
            # told: a way that cannot be told may meet them later.
            meet = None
        if meet is None:
            # What was told against a meeting point that is not kept
            # goes with it; an ending, a way back and a floor stay.
            for one in ways:
                if one.end == "meet":
                    one.said, one.said_cut = None, False
                if one.end in ("meet", "never"):
                    one.end = None
        yield _URMSGDone(_URMSGApart(meet, ways))

    def _urmsg_apart_end(table, origin, flow, top):
        """end for a way read to its end that never meets the others: a
        reach table of it (_urmsg_reach with pairs)."""

        back = False
        ending = False
        for _d, node in table.values():
            if origin is not None and node is origin:
                back = True
                continue
            if _urmsg_name_jump(node) or _urmsg_unfollowed(node) is not None:
                return None
            k = _urmsg_kind(node)
            if k == _URMSG_K_CALL or k == _URMSG_K_PY:
                fact = _urmsg_fact(node)
                if ((k == _URMSG_K_CALL or fact.via == "call") and fact.target is not None
                        and _urmsg_returns(fact.target) is None):
                    # It may lead into the scene and out by its `return`.
                    return None
            if flow(node):
                continue
            if k == _URMSG_K_RET and top:
                ending = True
            else:
                # A `return` that may be a called scene's, or a statement
                # the story cannot be followed past.
                return None
        if ending:
            return "end"
        if back:
            return "back"
        return "never"

    def _urmsg_said_line(node):
        """True for a line the player reads and clicks past: a Say that
        waits."""

        return _urmsg_kind(node) == _URMSG_K_SAY and bool(getattr(node, "interact", True))

    _URMSG_SAID_RETURN = python_object()   # stop: the first `return`
    _URMSG_SAID_DEPTH = 4           # called scenes inside called scenes counted

    def _urmsg_said_to(start, origin, stop, cap, flow, lines, depth=0):
        """
        (fewest, floor): the fewest said lines on the way from start to stop
        (stop's own not counted; _URMSG_SAID_RETURN: the first `return`),
        not through origin; a call that comes back adds the fewest lines of
        its scene (lines: what was counted per scene, for this ask). floor
        True when that is only a floor: the search was cut before stop was
        reached (then fewest is the least any way past the cut can say), or
        a scene on the way could not be counted. (None, False) when stop
        cannot be reached; stop None: run to the end, (None, False) when it
        gets there, the floor when cut.
        """

        import heapq
        if start is None:
            return None, False
        # (lines, floor, order, statement): of two ways with as many lines,
        # the exact one is taken first.
        heap = python_list(((0, False, 0, start),))
        settled = python_set()
        n = 0
        while heap:
            d, fl, _n, node = heapq.heappop(heap)
            if id(node) in settled:
                continue
            if node is stop or (stop is _URMSG_SAID_RETURN and _urmsg_kind(node) == _URMSG_K_RET):
                return d, fl
            settled.add(id(node))
            if len(settled) > cap:
                return d, True
            if origin is not None and node is origin:
                continue
            w = 1 if _urmsg_said_line(node) else 0
            past = _urmsg_said_past(node, lines, depth)
            for nxt in flow(node):
                if id(nxt) in settled:
                    continue
                add, more = w, fl
                if past is not None and nxt is past[0]:
                    add += past[1]
                    more = more or past[2]
                elif _urmsg_unfollowed(node) == _URMSG_DYN_CALL:
                    more = True
                n += 1
                heapq.heappush(heap, (d + add, more, n, nxt))
        return None, False

    def _urmsg_said_past(node, lines, depth):
        """For a call that comes back: (the statement after it, the fewest
        said lines of its scene, floor); None for every other statement."""

        k = _urmsg_kind(node)
        if k != _URMSG_K_CALL and k != _URMSG_K_PY:
            return None
        fact = _urmsg_fact(node)
        if not (k == _URMSG_K_CALL or fact.via == "call") or fact.target is None:
            return None
        if fact.nx is None or _urmsg_returns(fact.target) is not True:
            return None
        hit = lines.get(id(fact.target))
        if hit is None:
            if depth >= _URMSG_SAID_DEPTH:
                hit = (0, True)
            else:
                # While a scene is counted it counts as a floor of 0 (a
                # scene that calls itself).
                lines[id(fact.target)] = (0, True)
                fewest, floor = _urmsg_said_to(fact.target, None, _URMSG_SAID_RETURN,
                                               _URMSG_CAP_RETURN, _urmsg_flow_visit,
                                               lines, depth + 1)
                hit = (fewest or 0, floor or fewest is None)
            lines[id(fact.target)] = hit
        return fact.nx, hit[0], hit[1]

    class _URMSGVersions(python_object):
        """A split whose ways are versions of one value: name, the store
        name tested as written; values, one per way - the literal values it
        stands for, or None for a last way that tests nothing ("otherwise")."""

        __slots__ = ("name", "values")

        def __init__(self, name, values):
            self.name = name
            self.values = tuple(values)

    def _urmsg_versions(node, ways_tests, whole=True):
        """
        A _URMSGVersions when the split at node is one if/elif (a check of
        the game, or a route picked in code) whose every way but a last
        "otherwise" tests ONE store name for literal values, all different
        (`x == 1`, `1 == x`, `x in (1, 2)`, `x == 1 or x == 2`); ways_tests:
        per way, its (test, wanted) pairs - the wanted ones are its own, the
        others the earlier ways' turned down. None when anything else, when
        a way was not read (whole False), when a value names a label of the
        script (a dispatcher: Being a DIK's events), and when the stretch
        the split is in is not the story (a roam dispatcher, a loop that
        cannot be told: Him's positions) - or not worked out yet.
        """

        if not whole or len(ways_tests) < 2:
            return None
        name = None
        values = python_list()
        seen = python_list()
        last = len(ways_tests) - 1
        for at, tests in enumerate(ways_tests):
            own = python_list(test for test, wanted in tests if wanted)
            if not own:
                if at != last or not values:
                    return None
                values.append(None)
                continue
            if len(own) != 1 or own[0] is None:
                return None
            one = _urmsg_version_test(own[0])
            if one is None or (name is not None and one[0] != name):
                return None
            name = one[0]
            for value in one[1]:
                if any(value == other and type(value) is type(other) for other in seen):
                    return None
                if isinstance(value, _urmsg_texts) and _urmsg_lookup(value) is not None:
                    return None
                seen.append(value)
            values.append(one[1])
        if sum(1 for v in values if v is not None) < 2:
            return None
        if _urmsg_stretch(node) != "story":
            return None
        return _URMSGVersions(name, values)

    _URMSG_VERSION_VALUES = (_urmsg_builtins_mod.bool, _urmsg_builtins_mod.int,
                             _urmsg_builtins_mod.float) + tuple(_urmsg_texts)
    _URMSG_VERSION_MANY = (_urmsg_builtins_mod.tuple, _urmsg_builtins_mod.list,
                           _urmsg_builtins_mod.set, _urmsg_builtins_mod.frozenset)

    def _urmsg_version_test(test):
        """(name, values) for a test of one store name against literals, or
        None."""

        try:
            tree = _urmsg_parse((u"%s" % (test,)).strip(), "eval")
        except Exception:
            return None
        return _urmsg_version_node(tree.body)

    def _urmsg_version_node(node):
        kind = _urmsg_kind_of(node)
        if kind == "BoolOp":
            if _urmsg_kind_of(node.op) != "Or":
                return None
            name = None
            values = python_list()
            for part in node.values:
                one = _urmsg_version_node(part)
                if one is None or (name is not None and one[0] != name):
                    return None
                name = one[0]
                values.extend(one[1])
            return name, tuple(values)
        if kind != "Compare" or len(node.ops) != 1:
            return None
        op = _urmsg_kind_of(node.ops[0])
        left, right = node.left, node.comparators[0]
        if op == "Eq":
            name, lit = _urmsg_version_name(left), right
            if name is None:
                name, lit = _urmsg_version_name(right), left
            values = _urmsg_version_lits(lit, False)
        elif op == "In":
            name = _urmsg_version_name(left)
            values = _urmsg_version_lits(right, True)
        else:
            return None
        if name is None or values is None:
            return None
        return name, values

    def _urmsg_version_name(node):
        """The dotted store name a test reads, or None."""

        parts = python_list()
        while _urmsg_kind_of(node) == "Attribute":
            parts.append(node.attr)
            node = node.value
        if _urmsg_kind_of(node) != "Name" or node.id in ("True", "False", "None"):
            return None
        parts.append(node.id)
        return u".".join(reversed(parts))

    def _urmsg_version_lits(node, many):
        """The literal values written: one, or (many) the items of a tuple,
        list or set of them. None when not plain literals."""

        try:
            value = _urmsg_pyast.literal_eval(node)
        except Exception:
            return None
        items = value if many else (value,)
        if many and not isinstance(value, _URMSG_VERSION_MANY):
            return None
        out = python_list()
        for item in items:
            if item is None or not isinstance(item, _URMSG_VERSION_VALUES):
                return None
            out.append(item)
        return tuple(out) if out else None

    # ------------------------------------------------------------------
    # Free roam and the kind of a stretch (the map rework, 2026-11-23)
    # ------------------------------------------------------------------
    #
    # Where the player roams - a place the story keeps coming back to, the
    # player picking where to go next - and where the story runs on. Worked
    # out from the shape of the script alone (never from names: the user's
    # 1a), the same from every start, and None where it cannot be told.
    #
    # One pass per graph, in the twin, run only when asked for: in slices
    # (_urmsg_stretch_step) or whole (_urmsg_stretches). Until it is done
    # every kind is None; asking a kind never runs it.
    #   1. every statement a label of the game reaches and where it can go
    #      next (_urmsg_flow_ways_in: a call that comes back is stepped
    #      over, a choice of any shape goes to its ways);
    #   2. the names the script jumps through (renpy.jump(n), jump
    #      expression n, ...), what each statement writes into them, and
    #      where each one's value can still be read;
    #   3. states: a statement with the values those names hold there,
    #      walked forward from where the game starts the story - so a jump
    #      through a name goes to the label written last on its own way,
    #      never to one written for another way (a shared exit
    #      sends each room's events back to that room only);
    #   4. loop regions over the states: the states that can each reach the
    #      other (a flood fill forward and backward: what both reach). A
    #      region is ROAM when a player picks in it and it holds a jump
    #      through a name, or a dispatcher (checks whose arms enter two or
    #      more of its labels, testing nothing a choice there hands on) with
    #      a pick that comes back to itself without passing a write of what
    #      the dispatcher tests (a story's day loop always passes one);
    #   5. kinds: roam; story when everything ahead is read in full; a
    #      statement inside a called scene takes the kind of that scene's
    #      calls; else None. A statement's kind is its states' when they
    #      agree.
    # FINDINGS.md, 2026-11-23 (free roam).

    import time as _urmsg_time
    import array as _urmsg_array
    _urmsg_real_time = _urmsg_time.time

    def _urmsg_clock():
        # Prefer monotonic() so wall-clock jumps cannot stall slices; honor
        # tests that swap _urmsg_time.time for a fake clock.
        if _urmsg_time.time is _urmsg_real_time:
            fn = getattr(_urmsg_time, "monotonic", None)
            if fn is not None:
                return fn()
        return _urmsg_time.time()

    # The array type code as the running Python wants it (a byte string on
    # Python 2, where the store's literals are unicode).
    _URMSG_LONG = b"l" if bytes is str else u"l"

    _URMSG_STRETCH_WRITES = 3000    # statements a called label is read for writes
    _URMSG_STRETCH_STATES = 3000000 # states the pass may make (and 4 per statement)
    _URMSG_STRETCH_CALLERS = 48     # called scenes one region can be inside
    # A slice of the pass yields once it has worked this long (seconds), so
    # a display that drives _urmsg_stretch_step between frames never waits
    # long for one (map rework Batch 2's longest single step was 4.4 s on
    # Being a DIK). The clock is read every _URMSG_STRETCH_TICKS asks.
    _URMSG_STRETCH_BEAT = 0.04
    _URMSG_STRETCH_TICKS = 8
    _URMSG_KIND_WORDS = (None, u"story", u"roam")
    _URMSG_EVERY_LABEL = u"\x00every label"
    # A name's value in a state: a label's index; these below; or -(L + 3)
    # for label L written just before a jump whose next line is L (the jump
    # through the name comes back there: a call in disguise).
    _URMSG_V_DEAD = -1              # no jump reads it any more
    _URMSG_V_UNKNOWN = -2           # cannot be told

    class _URMSGStretches(python_object):
        """
        The stretch table of one graph. Statements by index: nodes, at (id
        -> index), succ (index -> the indexes it goes to next), calls (index
        -> the labels it calls and comes back from), names (index -> (verb,
        name) of a jump or call through a name), unread (index -> why it
        cannot be read). The names jumped through: tracked; pre and post
        (index -> ((name's place, value), ...) written by the statement, and
        by the labels it calls); live (per name, per statement: a jump may
        still read it); callish (index of a jump -> (name's place, label)
        when it leaves for a scene that jumps back through the name to its
        next line). States: snode (state -> statement), svals, ssucc,
        scalls (state -> the states its calls enter), sbad (state -> why it
        cannot be read), sret (states that end a scene like a return),
        seeds, sat (statement -> its states), targets (statement -> the
        labels its jump through a name went to). scomp: state -> region;
        roam: the regions that are roam, why: what made each roam; kinds
        and kinds_stop: region -> 0 None, 1 story, 2 roam (as the ticket
        says, and stopping at a roam region's entry). failed: why the pass
        gave up, or None.
        """

        __slots__ = ("work", "done", "failed", "seconds", "slowest",
                     "nodes", "at", "succ", "calls", "names", "unread",
                     "tracked", "pre", "post", "live", "callish",
                     "label_writes", "written", "snode", "svals", "ssucc",
                     "scalls", "sbad", "sret", "seeds", "sat", "targets",
                     "scomp", "count", "roam", "why", "kinds", "kinds_stop",
                     "members", "tops", "unclear", "beat", "tick", "beat_len")

        def __init__(self):
            self.beat = 0.0
            self.tick = 0
            self.beat_len = _URMSG_STRETCH_BEAT
            self.tops = None
            self.unclear = python_set()
            self.work = None
            self.done = False
            self.failed = None
            self.seconds = 0.0
            self.slowest = 0.0
            self.nodes = python_list()
            self.at = python_dict()
            self.succ = python_list()
            self.calls = python_dict()
            self.names = python_dict()
            self.unread = python_dict()
            self.tracked = ()
            self.pre = python_dict()
            self.post = python_dict()
            self.live = ()
            self.callish = python_dict()
            self.label_writes = python_dict()
            self.written = python_dict()
            self.snode = None
            self.svals = python_list()
            self.ssucc = python_list()
            self.scalls = python_dict()
            self.sbad = python_dict()
            self.sret = python_set()
            self.seeds = python_list()
            self.sat = python_dict()
            self.targets = python_dict()
            self.scomp = None
            self.count = 0
            self.roam = python_set()
            self.why = python_dict()
            self.kinds = None
            self.kinds_stop = None
            self.members = python_dict()

    def _urmsg_stretch_table():
        """The graph's stretch table as far as it is worked out (in the
        twin, made when missing)."""

        g = _urmsg_graph()
        if g.stretch is None:
            g.stretch = _URMSGStretches()
        return g.stretch

    def _urmsg_stretch_run(t, seconds):
        """Run the pass for about `seconds` (None: to the end). True when
        it is done."""

        if t.done:
            return True
        if t.work is None:
            t.work = _urmsg_stretch_pass(t)
        t.beat_len = _URMSG_STRETCH_BEAT if seconds is None else min(_URMSG_STRETCH_BEAT, seconds)
        began = _urmsg_clock()
        try:
            while True:
                step = _urmsg_clock()
                t.beat = step
                next(t.work)
                now = _urmsg_clock()
                if now < began:
                    began = now
                if now < step:
                    step = now
                if now - step > t.slowest:
                    t.slowest = now - step
                if seconds is not None and now - began >= seconds:
                    break
        except StopIteration:
            t.done = True
            t.work = None
        except Exception as error:
            t.failed = u"%s: %s" % (type(error).__name__, error)
            t.done = True
            t.work = None
            raise
        t.seconds += max(0.0, _urmsg_clock() - began)
        return t.done

    def _urmsg_stretch_step(seconds):
        """Work the pass out for about `seconds`; True when it is done. For
        a display that wants the kinds without a wait: call it between
        frames until it says True."""

        g = _urmsg_own()
        try:
            return _urmsg_stretch_run(_urmsg_stretch_table(), seconds)
        finally:
            _urmsg_own_end(g)

    def _urmsg_stretches():
        """The whole stretch table, the pass run to its end (seconds on the
        biggest games: never when a display opens)."""

        g = _urmsg_own()
        try:
            t = _urmsg_stretch_table()
            _urmsg_stretch_run(t, None)
            return t
        finally:
            _urmsg_own_end(g)

    def _urmsg_stretch_override():
        """The kind the player set by hand for this game (1c), or None."""

        try:
            value = _urm_setting(u"urm_stretch_kind")
        except Exception:
            return None
        return value if value in (u"story", u"roam") else None

    def _urmsg_stretch_states(t, node):
        i = t.at.get(id(node))
        if i is None or t.nodes[i] is not node:
            return ()
        return t.sat.get(i, ())

    def _urmsg_stretch(node, stop=False):
        """
        "roam", "story" or None for a statement: the kind the player set
        for this game by hand when there is one, else the stretch table's
        (stop: a story stretch read up to the entry of a roam region, not
        beyond it). None while the pass is not done: asking never runs it.
        """

        over = _urmsg_stretch_override()
        if over is not None:
            return over
        g = _urmsg_own()
        try:
            t = _urmsg_stretch_table()
            if not t.done or t.failed is not None:
                return None
            kinds = t.kinds_stop if stop else t.kinds
            if kinds is None:
                return None
            answer = None
            for s in _urmsg_stretch_states(t, node):
                one = kinds[t.scomp[s]]
                if answer is None:
                    answer = one
                elif one != answer:
                    return None
            return _URMSG_KIND_WORDS[answer] if answer else None
        finally:
            _urmsg_own_end(g)

    def _urmsg_stretch_region(node):
        """For a statement of a roam region: (its statements, its exits as
        (statement, the statement outside it goes to)). None otherwise or
        while the pass is not done."""

        g = _urmsg_own()
        try:
            t = _urmsg_stretch_table()
            if not t.done or t.failed is not None:
                return None
            regions = python_list()
            for s in _urmsg_stretch_states(t, node):
                c = t.scomp[s]
                if c not in t.roam:
                    return None
                if c not in regions:
                    regions.append(c)
            if not regions:
                return None
            inside = python_list()
            seen = python_set()
            exits = python_list()
            for c in regions:
                for s in _urmsg_stretch_members(t, c):
                    v = t.snode[s]
                    if v not in seen:
                        seen.add(v)
                        inside.append(v)
                    for w in t.ssucc[s]:
                        if t.scomp[w] not in regions:
                            pair = (v, t.snode[w])
                            if pair not in exits:
                                exits.append(pair)
            inside.sort()
            return (tuple(t.nodes[v] for v in inside),
                    tuple((t.nodes[a], t.nodes[b]) for a, b in exits))
        finally:
            _urmsg_own_end(g)

    def _urmsg_stretch_jumps(node):
        """The labels a jump or call through a name went to on the ways the
        pass followed, as the story wrote them; None when one way could not
        be told, it is no such jump, or the pass is not done."""

        g = _urmsg_own()
        try:
            t = _urmsg_stretch_table()
            if not t.done or t.failed is not None:
                return None
            i = t.at.get(id(node))
            if i is None or t.nodes[i] is not node or i not in t.names:
                return None
            for s in t.sat.get(i, ()):
                if s in t.sbad:
                    return None
            got = t.targets.get(i)
            if not got:
                return None
            order = python_list(got)
            order.sort()
            return tuple(t.nodes[j] for j in order)
        finally:
            _urmsg_own_end(g)

    def _urmsg_stretch_members(t, c):
        hit = t.members.get(c)
        if hit is None:
            out = python_list()
            comp = t.scomp
            n = len(comp)
            s = 0
            while s < n:
                if comp[s] == c:
                    out.append(s)
                s += 1
            hit = tuple(out)
            t.members[c] = hit
        return hit

    # ---- the names the script jumps through

    def _urmsg_stretch_plain(expr):
        """The store name a parsed expression is, or None."""

        path = _urmsg_path_of(expr, python_dict())
        if isinstance(path, tuple) and len(path) == 1 and path[0] != _URMSG_ANY:
            return path[0]
        return None

    def _urmsg_stretch_name(node):
        """(verb, name) for a jump or call through a name - name None when
        it is not a plain name the statement always jumps through - or None
        for any other statement."""

        k = _urmsg_kind(node)
        if k == _URMSG_K_JUMP or k == _URMSG_K_CALL:
            if not getattr(node, "expression", False):
                return None
            verb = u"jump" if k == _URMSG_K_JUMP else u"call"
            text = node.target if k == _URMSG_K_JUMP else node.label
            try:
                return verb, _urmsg_stretch_plain(_urmsg_parse(u"%s" % (text,), "eval").body)
            except Exception:
                return verb, None
        if k != _URMSG_K_PY or not _urmsg_name_jump(node):
            return None
        tree = _urmsg_tree(node.code.source)
        if tree is None or not tree.body:
            return u"jump", None
        found = python_list()
        for one in _urmsg_inside(tree.body):
            if _urmsg_call_name(one) in ("renpy.jump", "renpy.call"):
                found.append(one)
        last = tree.body[-1]
        call = getattr(last, "value", None)
        if len(found) != 1 or _urmsg_kind_of(last) != "Expr" or call is not found[0]:
            return u"jump", None
        verb = u"jump" if _urmsg_call_name(call) == "renpy.jump" else u"call"
        arg = _urmsg_arg(call, 0, "label")
        return verb, (_urmsg_stretch_plain(arg) if arg is not None else None)

    def _urmsg_stretch_paths(paths):
        """Store names out of written paths (an attribute of an object that
        cannot be told: its own name)."""

        out = python_set()
        for path in paths:
            if path:
                out.add(path[-1] if path[0] == _URMSG_ANY else path[0])
        return out

    def _urmsg_stretch_writes(nodes, expression):
        """The store names some parsed statements (or one expression) may
        write, or None when that cannot be told."""

        if expression:
            nodes = python_list(_urmsg_pyast.walk(nodes[0]))
        else:
            nodes = _urmsg_inside(nodes)
        writes = python_list()
        if not _urmsg_nodes_effects(nodes, python_dict(), _urmsg_always_declared,
                                    0, python_set(), writes):
            return None
        return _urmsg_stretch_paths(writes)

    def _urmsg_stretch_py_writes(node, tracked, skip_jump):
        """
        What a python statement leaves in the tracked names: ((name, label
        text, or None for a value that cannot be told), ...), the last
        write of each, read backwards. A line whose writes cannot be told
        leaves every tracked name not decided yet unknown. skip_jump: its
        own renpy.jump / renpy.call line writes nothing.
        """

        source = getattr(getattr(node, "code", None), "source", None) or u""
        tree = _urmsg_tree(source)
        if tree is None:
            return tuple((name, None) for name in tracked)
        whole = _urmsg_line_effects(source.strip())
        if whole is not None and not (_urmsg_stretch_paths(whole) & python_set(tracked)):
            plain = True
            for top in tree.body:
                if _urmsg_kind_of(top) == "Assign":
                    for target in top.targets:
                        if _urmsg_stretch_plain(target) in tracked:
                            plain = False
            if plain:
                return ()
        decided = python_dict()
        body = tree.body
        n = len(body)
        while n > 0 and len(decided) < len(tracked):
            n -= 1
            top = body[n]
            kind = _urmsg_kind_of(top)
            if (skip_jump and kind == "Expr"
                    and _urmsg_call_name(top.value) in ("renpy.jump", "renpy.call")):
                continue
            if kind == "Assign" and len(top.targets) == 1:
                name = _urmsg_stretch_plain(top.targets[0])
                if name in tracked:
                    if name not in decided:
                        ok, value = _urmsg_literal(top.value)
                        decided[name] = value if ok and isinstance(value, _urmsg_texts) else None
                    if _urmsg_stretch_writes(python_list((top.value,)), True) is None:
                        for one in tracked:
                            decided.setdefault(one, None)
                    continue
            writes = _urmsg_stretch_writes(python_list((top,)), False)
            if writes is None:
                for one in tracked:
                    decided.setdefault(one, None)
                continue
            for one in writes:
                if one in tracked:
                    decided.setdefault(one, None)
        return tuple((name, decided[name]) for name in tracked if name in decided)

    def _urmsg_stretch_choice_writes(choice):
        """The names a choice's ways set, or None when it is not whole."""

        if not choice.whole:
            return None
        out = python_set()
        for way in choice.ways:
            for target, _value in way.sets:
                out.add(target[6:] if target.startswith(u"store.") else target)
        return out

    def _urmsg_stretch_label_writes(t, label):
        """The store names a call of this label may write before it comes
        back (read forward to its returns, the calls in it entered), or
        None when that cannot be told."""

        key = id(label)
        hit = t.label_writes.get(key)
        if hit is not None and hit[0] is label:
            return hit[1]
        t.label_writes[key] = (label, None)
        seen = python_set((id(label),))
        todo = python_list((label,))
        out = python_set()
        while todo:
            if len(seen) > _URMSG_STRETCH_WRITES:
                out = None
                break
            node = todo.pop()
            k = _urmsg_kind(node)
            got = python_set()
            if k == _URMSG_K_PY:
                source = getattr(getattr(node, "code", None), "source", None) or u""
                got = _urmsg_line_effects(source.strip())
                got = None if got is None else _urmsg_stretch_paths(got)
            elif k == _URMSG_K_USER or k == _URMSG_K_WHILE:
                choice = _urmsg_choice_in(node)
                if choice is not None:
                    got = _urmsg_stretch_choice_writes(choice)
            if got is None:
                out = None
                break
            out |= got
            if k == _URMSG_K_RET:
                continue
            for nxt in _urmsg_flow(node):
                if id(nxt) not in seen:
                    seen.add(id(nxt))
                    todo.append(nxt)
        t.label_writes[key] = (label, out)
        return out

    def _urmsg_stretch_written(t, name):
        """The label indexes written into `name` anywhere in the script's
        python and its define / default as literals, or _URMSG_EVERY_LABEL
        when it is ever written as anything else there or by a screen, or
        never written: where a jump through it whose value could not be
        told may still go."""

        if t.written.get(name) is None:
            for _step in _urmsg_stretch_written_work(t, name):
                pass
        return t.written[name]

    def _urmsg_stretch_written_work(t, name):
        """_urmsg_stretch_written's answer into t.written[name], as a
        generator of the pass's slices (one name reads the whole script:
        up to 3 s on Being a DIK)."""

        out = python_set()
        every = getattr(renpy.game.script, "all_stmts", None) or ()
        found = False
        for node in every:
            if _urmsg_stretch_late(t):
                yield
            if type(node).__name__ in ("Define", "Default"):
                if getattr(node, "varname", None) != name:
                    continue
                found = True
                try:
                    ok, value = _urmsg_literal(_urmsg_parse(node.code.source, "eval").body)
                except Exception:
                    ok, value = False, None
                target = _urmsg_lookup(value) if ok and isinstance(value, _urmsg_texts) else None
                j = t.at.get(id(target)) if target is not None else None
                if j is not None:
                    out.add(j)
                continue
            if _urmsg_kind(node) != _URMSG_K_PY:
                continue
            source = getattr(getattr(node, "code", None), "source", None) or u""
            if name not in source:
                continue
            tree = _urmsg_tree(source)
            if tree is None:
                out = _URMSG_EVERY_LABEL
                break
            for one in _urmsg_pyast.walk(tree):
                kind = _urmsg_kind_of(one)
                if kind == "Assign":
                    targets = one.targets
                elif kind in ("AugAssign", "AnnAssign"):
                    targets = (one.target,)
                else:
                    continue
                hit_name = False
                for target in targets:
                    path = _urmsg_path_of(target, python_dict())
                    if isinstance(path, tuple) and path and (path[0] == name or path[-1] == name):
                        hit_name = True
                if not hit_name:
                    continue
                found = True
                ok, value = _urmsg_literal(one.value) if kind == "Assign" else (False, None)
                if not ok or not isinstance(value, _urmsg_texts) or len(targets) != 1:
                    out = _URMSG_EVERY_LABEL
                    break
                target = _urmsg_lookup(value)
                j = t.at.get(id(target)) if target is not None else None
                if j is not None:
                    out.add(j)
            if out is _URMSG_EVERY_LABEL:
                break
        if out is not _URMSG_EVERY_LABEL:
            for screen in _urmsg_screen_names():
                if _urmsg_stretch_late(t):
                    yield
                rec = _urmsg_screen(screen)
                if name in rec.writes or (u"store." + name) in rec.writes:
                    out = _URMSG_EVERY_LABEL
                    break
        if not found:
            # Never written in the script: the value comes from elsewhere.
            out = _URMSG_EVERY_LABEL
        t.written[name] = out

    def _urmsg_screen_names():
        """Every screen the game defines, by name."""

        out = python_list()
        try:
            for key in renpy.display.screen.screens:
                one = key[0] if isinstance(key, tuple) else key
                if one not in out:
                    out.append(one)
        except Exception:
            pass
        return out

    def _urmsg_stretch_comes_back(t, i, label):
        """The index of the jump right after statement i, in its own block,
        whose next line is `label` (statement i wrote label's name into a
        name the scene jumped to will jump back through), or None."""

        node = getattr(t.nodes[i], "next", None)
        steps = 0
        while node is not None and steps < 8:
            k = _urmsg_kind(node)
            if k == _URMSG_K_JUMP:
                if not getattr(node, "expression", False) and _urmsg_stretch_follows(t, node, label):
                    return t.at.get(id(node))
                return None
            if k not in (_URMSG_K_SAY, _URMSG_K_PLAIN, _URMSG_K_PY, _URMSG_K_TRANS):
                return None
            node = getattr(node, "next", None)
            steps += 1
        return None

    def _urmsg_stretch_tops(t):
        """id(statement at the top of a file) -> the one written after it
        (a label with a block has its block as next, not the label after)."""

        if t.tops is None:
            for _step in _urmsg_stretch_tops_work(t):
                pass
        return t.tops

    def _urmsg_stretch_tops_work(t):
        """_urmsg_stretch_tops's table into t.tops, as a generator of the
        pass's slices."""

        if t.tops is None:
            files = python_dict()
            for home in _urmsg_homes().values():
                if _urmsg_stretch_late(t):
                    yield
                node = home[0]
                if home[2] is None:
                    where = getattr(node, "filename", None)
                    files.setdefault(where, python_list()).append(
                        (getattr(node, "linenumber", 0) or 0, id(node), node))
            tops = python_dict()
            for rows in files.values():
                rows.sort()
                k = 1
                while k < len(rows):
                    tops[rows[k - 1][1]] = rows[k][2]
                    k += 1
            t.tops = tops

    def _urmsg_stretch_follows(t, jump, label):
        """True when `label` is the line written right after `jump` (a jump
        has no next of its own): after it in its block, or after the
        statements whose blocks it ends."""

        homes = _urmsg_homes()
        node = jump
        steps = 0
        while steps < 8:
            home = homes.get(id(node))
            if home is None or home[0] is not node:
                return False
            _child, parent, block, at = home
            if block is None:
                return _urmsg_stretch_tops(t).get(id(node)) is label
            if at + 1 < len(block):
                return block[at + 1] is label
            if parent is None or _urmsg_kind(parent) == _URMSG_K_WHILE:
                return False
            node = parent
            steps += 1
        return False

    # ---- the pass

    def _urmsg_stretch_late(t):
        """True when the slice of the pass running now has worked long
        enough: the step yields there (every loop of the pass asks)."""

        t.tick += 1
        if t.tick % _URMSG_STRETCH_TICKS:
            return False
        now = _urmsg_clock()
        if now < t.beat:
            t.beat = now
            return False
        if now - t.beat < t.beat_len:
            return False
        t.beat = now
        return True

    def _urmsg_stretch_pass(t):
        """The pass, as a generator: it yields now and then so it can be
        run in slices (_urmsg_stretch_run)."""

        for _step in _urmsg_stretch_statements(t):
            yield
        for _step in _urmsg_stretch_names(t):
            yield
        for _step in _urmsg_stretch_walk(t):
            yield
        if t.failed is not None:
            return
        for _step in _urmsg_stretch_regions(t):
            yield
        for _step in _urmsg_stretch_kinds(t):
            yield

    def _urmsg_stretch_statements(t):
        """Step 1: every statement a label of the game reaches, where it
        goes next, the labels it calls and comes back from."""

        nodes = t.nodes
        at = t.at
        succ = t.succ
        engine = python_dict()

        def own(node):
            i = at.get(id(node))
            if i is not None:
                return i
            name = getattr(node, "filename", None) or u""
            hit = engine.get(name)
            if hit is None:
                hit = bool(_urmsg_engine_file(name))
                engine[name] = hit
            if hit:
                return None
            i = len(nodes)
            at[id(node)] = i
            nodes.append(node)
            succ.append(())
            return i

        def call(i, target):
            j = own(target)
            if j is not None:
                got = t.calls.get(i, ())
                if j not in got:
                    t.calls[i] = got + (j,)

        g = _urmsg_graph()
        g = g.base if g.base is not None else g
        if g.homes is None:
            # The statement-to-block table the choice reads ask for (up to
            # 2 s whole on Being a DIK), built here in slices.
            for _step in _urmsg_homes_build(g, t):
                yield
        every = getattr(renpy.game.script, "all_stmts", None) or ()
        for node in every:
            if _urmsg_stretch_late(t):
                yield
            if _urmsg_kind(node) == _URMSG_K_LABEL:
                own(node)
        i = 0
        while i < len(nodes):
            if _urmsg_stretch_late(t):
                yield
            node = nodes[i]
            k = _urmsg_kind(node)
            nx = getattr(node, "next", None)
            named = _urmsg_stretch_name(node)
            if named is not None:
                # Where it goes is worked out on the states (step 3).
                t.names[i] = named
                nxt = (nx,) if named[0] == u"call" and nx is not None else ()
            else:
                nxt = _urmsg_flow_ways_in(node)
                choice = None
                if k == _URMSG_K_USER or k == _URMSG_K_PY or k == _URMSG_K_WHILE:
                    choice = _urmsg_choice_in(node)
                if choice is not None and choice.shape != "menu":
                    if not choice.whole:
                        t.unread[i] = choice.why[0] if choice.why else u"a choice that is not whole"
                    for way in choice.ways:
                        if way.go == "visit" and way.label:
                            target = _urmsg_lookup(way.label)
                            if target is not None and all(one is not target for one in nxt):
                                call(i, target)
                elif k == _URMSG_K_JUMP or k == _URMSG_K_CALL or k == _URMSG_K_PY:
                    fact = _urmsg_fact(node)
                    via = u"jump" if k == _URMSG_K_JUMP else (
                        u"call" if k == _URMSG_K_CALL else fact.via)
                    if via is not None and fact.target is None:
                        t.unread[i] = u"a jump to a label that is not there"
                    elif via == u"call" and all(one is not fact.target for one in nxt):
                        call(i, fact.target)
            row = python_list()
            for one in nxt:
                j = own(one)
                if j is not None and j not in row:
                    row.append(j)
            succ[i] = tuple(row)
            i += 1

    def _urmsg_stretch_names(t):
        """Step 2: the names jumped through; what each statement writes in
        them; where each one's value can still be read (live)."""

        nodes = t.nodes
        n = len(nodes)
        tracked = python_list()
        for i in t.names:
            name = t.names[i][1]
            if name is not None and name not in tracked:
                tracked.append(name)
        tracked.sort()
        t.tracked = tuple(tracked)
        if not tracked:
            return
        for _step in _urmsg_stretch_tops_work(t):
            yield
        place = python_dict()
        k = 0
        while k < len(tracked):
            place[tracked[k]] = k
            k += 1
        unknown_all = tuple((place[name], _URMSG_V_UNKNOWN) for name in tracked)

        def coded(i, pairs):
            out = python_list()
            for name, value in pairs:
                k = place[name]
                if value is None:
                    out.append((k, _URMSG_V_UNKNOWN))
                    continue
                target = _urmsg_lookup(value)
                j = t.at.get(id(target)) if target is not None else None
                if j is None:
                    out.append((k, _URMSG_V_UNKNOWN))
                    continue
                back = _urmsg_stretch_comes_back(t, i, target)
                if back is not None:
                    t.callish[back] = (k, j)
                    out.append((k, -(j + 3)))
                else:
                    out.append((k, j))
            return tuple(out)

        i = 0
        while i < n:
            if _urmsg_stretch_late(t):
                yield
            node = nodes[i]
            kind = _urmsg_kind(node)
            pre = ()
            if kind == _URMSG_K_PY:
                pre = coded(i, _urmsg_stretch_py_writes(node, t.tracked, i in t.names))
            elif kind == _URMSG_K_USER or kind == _URMSG_K_WHILE:
                choice = _urmsg_choice_in(node)
                if choice is not None:
                    got = _urmsg_stretch_choice_writes(choice)
                    if got is None:
                        pre = unknown_all
                    else:
                        pre = tuple((place[name], _URMSG_V_UNKNOWN) for name in tracked if name in got)
            if pre:
                t.pre[i] = pre
            post = python_list()
            for j in t.calls.get(i, ()):
                got = _urmsg_stretch_label_writes(t, nodes[j])
                pairs = unknown_all if got is None else tuple(
                    (place[name], _URMSG_V_UNKNOWN) for name in tracked if name in got)
                for pair in pairs:
                    if pair not in post:
                        post.append(pair)
            if post:
                t.post[i] = tuple(post)
            i += 1

        # Live: backwards from each jump through a name, stopping at a
        # statement that writes it, over the steps, the calls, and the way
        # from a jump through a name into every label written into that
        # name as a literal (an event of Being a DIK is entered only so).
        written = python_list(python_set() for _name in tracked)
        for pairs in t.pre.values():
            for k, value in pairs:
                if value >= 0:
                    written[k].add(value)
                elif value <= -3:
                    written[k].add(-value - 3)
        preds = python_list(() for _v in nodes)
        v = 0
        while v < n:
            if _urmsg_stretch_late(t):
                yield
            for w in t.succ[v]:
                preds[w] = preds[w] + (v,)
            for w in t.calls.get(v, ()):
                preds[w] = preds[w] + (v,)
            named = t.names.get(v)
            if named is not None and named[1] is not None:
                for w in written[place[named[1]]]:
                    preds[w] = preds[w] + (v,)
            v += 1
        yield
        live = python_list()
        for name in tracked:
            k = place[name]
            mark = bytearray(n)
            todo = python_list()
            for i in t.names:
                if t.names[i][1] == name and not any(p[0] == k for p in t.pre.get(i, ())):
                    mark[i] = 1
                    todo.append(i)
            while todo:
                if _urmsg_stretch_late(t):
                    yield
                w = todo.pop()
                for p in preds[w]:
                    if mark[p]:
                        continue
                    if any(q[0] == k for q in t.pre.get(p, ())) or any(
                            q[0] == k for q in t.post.get(p, ())):
                        continue
                    mark[p] = 1
                    todo.append(p)
            live.append(mark)
            yield
        t.live = tuple(live)

    def _urmsg_stretch_walk(t):
        """Step 3: the states, walked forward from where the game starts
        the story."""

        nodes = t.nodes
        n = len(nodes)
        width = len(t.tracked)
        live = t.live
        dead = tuple(_URMSG_V_DEAD for _k in t.tracked)
        cap = min(_URMSG_STRETCH_STATES, 4 * n + 1000)
        snode = _urmsg_array.array(_URMSG_LONG)
        svals = t.svals
        ssucc = t.ssucc
        sat = t.sat
        keys = python_dict()
        todo = python_list()

        # The names still read ahead of each statement (most: none).
        live_at = python_dict()
        k = 0
        while k < width:
            mark = live[k]
            w = 0
            while w < n:
                if _urmsg_stretch_late(t):
                    yield
                if mark[w]:
                    live_at[w] = live_at.get(w, ()) + (k,)
                w += 1
            k += 1

        def mask(vals, w):
            ks = live_at.get(w)
            if not ks:
                return dead
            out = python_list(dead)
            for k in ks:
                out[k] = vals[k]
            out = tuple(out)
            return dead if out == dead else out

        def state(w, vals):
            key = w if vals is dead else (w, vals)
            s = keys.get(key)
            if s is None:
                s = len(snode)
                keys[key] = s
                snode.append(w)
                svals.append(vals)
                ssucc.append(())
                sat[w] = sat.get(w, ()) + (s,)
                todo.append(s)
            return s

        def apply(vals, pairs):
            if not pairs:
                return vals
            out = python_list(vals)
            for k, value in pairs:
                out[k] = value
            return tuple(out)

        # Where the game starts the story: a label nothing in the script
        # enters (start, a splash screen, one only a screen jumps to), but
        # not one a literal names for a jump through a name.
        entered = bytearray(n)
        v = 0
        while v < n:
            if _urmsg_stretch_late(t):
                yield
            for w in t.succ[v]:
                entered[w] = 1
            for w in t.calls.get(v, ()):
                entered[w] = 1
            v += 1
        aimed = python_set()
        for pairs in t.pre.values():
            if _urmsg_stretch_late(t):
                yield
            for _k, value in pairs:
                if value >= 0:
                    aimed.add(value)
                elif value <= -3:
                    aimed.add(-value - 3)
        unknown = tuple(_URMSG_V_UNKNOWN for _k in t.tracked)
        v = 0
        while v < n:
            if _urmsg_stretch_late(t):
                yield
            if (_urmsg_kind(nodes[v]) == _URMSG_K_LABEL and not entered[v]
                    and v not in aimed):
                t.seeds.append(state(v, mask(unknown, v)))
            v += 1
        yield

        head = 0
        unseen = 0
        while True:
            while head < len(todo):
                if _urmsg_stretch_late(t):
                    yield
                if len(snode) > cap:
                    t.failed = u"too many states (%d for %d statements)" % (len(snode), n)
                    t.snode = snode
                    return
                s = todo[head]
                head += 1
                v = snode[s]
                vals1 = apply(svals[s], t.pre.get(v))
                calls = python_list(t.calls.get(v, ()))
                nxt = t.succ[v]
                if v in t.unread:
                    t.sbad[s] = t.unread[v]
                named = t.names.get(v)
                if named is not None:
                    verb, name = named
                    k = t.tracked.index(name) if name is not None else -1
                    value = vals1[k] if k >= 0 else _URMSG_V_UNKNOWN
                    if value == _URMSG_V_UNKNOWN or value == _URMSG_V_DEAD:
                        t.sbad[s] = (u"a jump through a name that cannot be read" if name is None
                                     else u"a jump through %s, whose value cannot be told here" % (name,))
                    else:
                        label = value if value >= 0 else -value - 3
                        t.targets[v] = t.targets.get(v, frozenset()) | frozenset((label,))
                        if value <= -3:
                            # Back to the line after the jump that left: it ends
                            # this scene as a return would.
                            t.sret.add(s)
                            nxt = ()
                        elif verb == u"jump":
                            nxt = (label,)
                        else:
                            back = _urmsg_returns(nodes[label])
                            if back is False:
                                nxt = (label,)
                            else:
                                calls.append(label)
                                if back is None:
                                    nxt = nxt + (label,)
                else:
                    hit = t.callish.get(v)
                    if hit is not None and vals1[hit[0]] == -(hit[1] + 3):
                        # A jump to a scene that comes back through the name:
                        # stepped over, as a call that comes back.
                        calls.extend(nxt)
                        nxt = (hit[1],)
                for w in calls:
                    if _urmsg_stretch_late(t):
                        yield
                    c = state(w, mask(vals1, w))
                    t.scalls[s] = t.scalls.get(s, ()) + (c,)
                vals2 = apply(vals1, t.post.get(v))
                out = python_list()
                had = python_set()
                for w in nxt:
                    if _urmsg_stretch_late(t):
                        yield
                    one = state(w, mask(vals2, w))
                    if one not in had:
                        had.add(one)
                        out.append(one)
                ssucc[s] = tuple(out)
            # A label nothing has reached (a loop only a screen of the game
            # or the engine enters, a scene that writes its own name): a
            # start of its own.
            while unseen < n and (unseen in sat
                                  or _urmsg_kind(nodes[unseen]) != _URMSG_K_LABEL):
                unseen += 1
            if unseen >= n:
                break
            if _urmsg_stretch_late(t):
                yield
            t.seeds.append(state(unseen, mask(unknown, unseen)))
        t.snode = snode

    def _urmsg_stretch_regions(t):
        """Step 4: loop regions over the states (Tarjan, without
        recursion), and which of them are roam."""

        ssucc = t.ssucc
        n = len(t.snode)
        index = _urmsg_array.array(_URMSG_LONG, (-1,)) * n
        low = _urmsg_array.array(_URMSG_LONG, (0,)) * n
        comp = _urmsg_array.array(_URMSG_LONG, (-1,)) * n
        onstack = bytearray(n)
        stack = python_list()
        counter = 0
        count = 0
        r = 0
        while r < n:
            if index[r] < 0:
                index[r] = low[r] = counter
                counter += 1
                stack.append(r)
                onstack[r] = 1
                work = python_list(((r, 0),))
                while work:
                    if _urmsg_stretch_late(t):
                        yield
                    v, at = work[-1]
                    row = ssucc[v]
                    if at < len(row):
                        work[-1] = (v, at + 1)
                        w = row[at]
                        if index[w] < 0:
                            index[w] = low[w] = counter
                            counter += 1
                            stack.append(w)
                            onstack[w] = 1
                            work.append((w, 0))
                        elif onstack[w] and index[w] < low[v]:
                            low[v] = index[w]
                        continue
                    work.pop()
                    if work:
                        u = work[-1][0]
                        if low[v] < low[u]:
                            low[u] = low[v]
                    if low[v] == index[v]:
                        while True:
                            w = stack.pop()
                            onstack[w] = 0
                            comp[w] = count
                            if w == v:
                                break
                        count += 1
            r += 1
            if _urmsg_stretch_late(t):
                yield
        t.scomp = comp
        t.count = count

        size = _urmsg_array.array(_URMSG_LONG, (0,)) * count
        s = 0
        while s < n:
            if _urmsg_stretch_late(t):
                yield
            size[comp[s]] += 1
            s += 1
        loops = python_dict()
        s = 0
        while s < n:
            if _urmsg_stretch_late(t):
                yield
            c = comp[s]
            if size[c] > 1 or s in ssucc[s]:
                got = loops.get(c)
                if got is None:
                    got = python_list()
                    loops[c] = got
                got.append(s)
            s += 1
        for c in loops:
            t.members[c] = tuple(loops[c])
            if _urmsg_stretch_is_roam(t, c, loops[c]):
                t.roam.add(c)
            yield

    def _urmsg_stretch_is_roam(t, c, inside):
        """
        A loop region is roam when a player picks in it and a jump
        through a name in it goes back to two or more of its labels (the
        place the story comes back to is where the player was: Being a
        DIK's endEvent; a scene's loop that jumps back to its own top, or a
        jump back to the line after it, sends one place only). A loop where
        a pick comes back to itself through dispatching checks - checks
        whose arms enter two or more of its labels, testing nothing a
        choice there hands on - without passing a write of what they test
        (a story told day by day moves the day on each time round) may be
        one too, but cannot be told from a scene's own loop: unclear, None.
        """

        nodes = t.nodes
        statements = python_set()
        for s in inside:
            statements.add(t.snode[s])
        picks = python_list()
        handed = python_set((u"_return",))
        checks = python_list()
        places = python_dict()
        for s in inside:
            v = t.snode[s]
            node = nodes[v]
            k = _urmsg_kind(node)
            if v in t.names and s not in t.sbad and s not in t.sret:
                for w in t.ssucc[s]:
                    if t.scomp[w] == c:
                        places.setdefault(v, python_set()).add(t.snode[w])
            if k == _URMSG_K_IF:
                checks.append(s)
            if k in (_URMSG_K_MENU, _URMSG_K_USER, _URMSG_K_PY, _URMSG_K_WHILE):
                choice = _urmsg_choice_in(node)
                if choice is None:
                    continue
                if choice.shape == "code":
                    checks.append(s)
                    continue
                if s not in t.sbad:
                    picks.append(s)
                for one in choice.names:
                    handed.add(one)
                if choice.check is not None:
                    handed.add(choice.check)
        if not picks:
            return False
        for v in places:
            if len(places[v]) >= 2:
                t.why[c] = u"a jump through a name back to where the player was"
                return True
        # A dispatcher is one check, or one run of checks written one after
        # the other (with the checks inside their arms): Witch Trainer
        # Silver's chain of `if day >= N: if not done: jump ev`. Checks far
        # apart that each enter one label (a scene's own loop) are none.
        units = python_dict()
        for s in checks:
            node = nodes[t.snode[s]]
            got = _urmsg_stretch_dispatch(t, node, statements, handed)
            if got is None or not got[0]:
                continue
            key = id(_urmsg_stretch_run_head(node))
            unit = units.get(key)
            if unit is None:
                unit = units[key] = (python_list(), python_set(), python_set())
            unit[0].append(s)
            unit[1].update(got[0])
            unit[2].update(got[1])
        dispatch = python_dict()
        tested = python_set()
        for states, labels, reads in units.values():
            if len(labels) >= 2:
                for s in states:
                    dispatch[s] = labels
                tested |= reads
        if not dispatch:
            return False
        keep = python_set()
        for s in inside:
            got = _urmsg_stretch_statement_writes(t, t.snode[s])
            if got is not None and not (got & tested):
                keep.add(s)
        if _urmsg_stretch_cycles(t, keep, picks, dispatch):
            # A dispatcher cannot yet tell a free roam from a scene's own
            # loop (Him's position loops, Now and Then's question rounds;
            # FINDINGS.md): such a loop reads None, never a guess.
            t.why[c] = u"a dispatcher (cannot be told)"
            t.unclear.add(c)
        return False

    def _urmsg_stretch_run_head(node):
        """The first check of the run of checks a check belongs to: out of
        the arms of the checks around it, back over the checks before it."""

        homes = _urmsg_homes()
        while True:
            home = homes.get(id(node))
            parent = home[1] if home is not None and home[0] is node else None
            if parent is not None and _urmsg_kind(parent) == _URMSG_K_IF:
                node = parent
                continue
            prev = _urmsg_before(node)[0]
            if prev is not None and _urmsg_kind(prev) == _URMSG_K_IF:
                node = prev
                continue
            return node

    def _urmsg_stretch_statement_writes(t, v):
        """The store names a statement may write (with what the labels it
        calls write), or None when that cannot be told."""

        node = t.nodes[v]
        k = _urmsg_kind(node)
        out = python_set()
        if k == _URMSG_K_PY:
            source = getattr(getattr(node, "code", None), "source", None) or u""
            got = _urmsg_line_effects(source.strip())
            if got is None:
                return None
            out |= _urmsg_stretch_paths(got)
        elif k == _URMSG_K_USER or k == _URMSG_K_WHILE:
            choice = _urmsg_choice_in(node)
            if choice is not None:
                got = _urmsg_stretch_choice_writes(choice)
                if got is None:
                    return None
                out |= got
        for j in t.calls.get(v, ()):
            got = _urmsg_stretch_label_writes(t, t.nodes[j])
            if got is None:
                return None
            out |= got
        return out

    def _urmsg_stretch_cycles(t, keep, picks, dispatch):
        """True when a pick comes back to itself, within the states in
        keep, through dispatching checks that enter two or more labels."""

        ssucc = t.ssucc
        back = python_dict()
        for s in keep:
            for w in ssucc[s]:
                if w in keep:
                    back.setdefault(w, python_list()).append(s)
        for p in picks:
            if p not in keep:
                continue
            ahead = python_set()
            todo = python_list(w for w in ssucc[p] if w in keep)
            while todo:
                w = todo.pop()
                if w in ahead:
                    continue
                ahead.add(w)
                for x in ssucc[w]:
                    if x in keep and x not in ahead:
                        todo.append(x)
            if p not in ahead:
                continue
            behind = python_set()
            todo = python_list(back.get(p, ()))
            while todo:
                w = todo.pop()
                if w in behind:
                    continue
                behind.add(w)
                todo.extend(back.get(w, ()))
            entered = python_set()
            for s in dispatch:
                if s in ahead and s in behind:
                    entered |= dispatch[s]
            if len(entered) >= 2:
                return True
        return False

    def _urmsg_stretch_dispatch(t, node, statements, handed):
        """For a check of a region: (the region's labels its arms enter, the
        names its tests read), or None when it tests what a choice of the
        region hands on (that check is the choice's own)."""

        if node in handed:
            return None
        labels = python_set()
        reads = python_set()
        if _urmsg_kind(node) == _URMSG_K_IF:
            for cond, block in node.entries:
                if not _urmsg_is_else(cond):
                    read = _urmsg_names_read(cond)
                    if read is None or (read & handed):
                        return None
                    reads |= read
                got = _urmsg_stretch_enters(t, block or (), statements)
                if got is not None:
                    labels.add(got)
        else:
            choice = _urmsg_choice_in(node)
            for way in choice.ways:
                for test, _holds in way.tests:
                    read = _urmsg_names_read(test) if test is not None else None
                    if read is None or (read & handed):
                        return None
                    reads |= read
                target = _urmsg_lookup(way.label) if way.label else None
                j = t.at.get(id(target)) if target is not None else None
                if j is not None and j in statements:
                    labels.add(j)
        return labels, reads

    def _urmsg_stretch_enters(t, block, statements):
        """The label of the region an arm enters first (a jump to it, or a
        call of it made in the region), or None."""

        for node in block:
            k = _urmsg_kind(node)
            verb = None
            target = None
            if k == _URMSG_K_JUMP or k == _URMSG_K_CALL:
                fact = _urmsg_fact(node)
                if fact.dyn:
                    return None
                verb = u"jump" if k == _URMSG_K_JUMP else u"call"
                target = fact.target
            elif k == _URMSG_K_PY:
                hop = _urmsg_hop(node)
                if hop:
                    verb = u"jump" if hop[0] == "jump" else u"call"
                    target = _urmsg_lookup(hop[1])
            if verb is not None:
                j = t.at.get(id(target)) if target is not None else None
                if j is None:
                    return None
                if verb == u"jump":
                    return j if j in statements else None
                i = t.at.get(id(node))
                return j if i is not None and i in statements else None
            if k in (_URMSG_K_IF, _URMSG_K_MENU, _URMSG_K_WHILE, _URMSG_K_RET):
                return None
        return None

    def _urmsg_stretch_kinds(t):
        """Step 5: each region's kind, as the ticket says (kinds) and
        stopping at a roam region's entry (kinds_stop). Worked on the graph
        of the regions (each region: the regions its states go to)."""

        nodes = t.nodes
        snode = t.snode
        ssucc = t.ssucc
        comp = t.scomp
        count = t.count
        n = len(snode)
        roam = t.roam

        # Regions are numbered below every region that can reach them
        # (Tarjan numbers them so): 0 .. count-1 is "what follows first".
        rnext = python_list()
        rall = python_list()
        own_ret = bytearray(count)
        real_ret = bytearray(count)
        c = 0
        while c < count:
            rnext.append(python_set())
            rall.append(python_set())
            c += 1
        s = 0
        while s < n:
            if _urmsg_stretch_late(t):
                yield
            c = comp[s]
            for w in ssucc[s]:
                d = comp[w]
                if d != c:
                    rnext[c].add(d)
                    rall[c].add(d)
            for w in t.scalls.get(s, ()):
                d = comp[w]
                if d != c:
                    rall[c].add(d)
            if _urmsg_kind(nodes[snode[s]]) == _URMSG_K_RET:
                own_ret[c] = 1
                real_ret[c] = 1
            elif s in t.sret:
                own_ret[c] = 1
            s += 1
        yield

        def spread_back(marks, stop):
            """Mark every region that can reach a marked one (stop: never
            through a roam region), in place - as a generator of the
            pass's slices."""
            changed = True
            while changed:
                changed = False
                c = 0
                while c < count:
                    if _urmsg_stretch_late(t):
                        yield
                    if not marks[c] and not (stop and c in roam):
                        for d in rall[c]:
                            if marks[d] and not (stop and d in roam):
                                marks[c] = 1
                                changed = True
                                break
                    c += 1

        # What cannot be read, and where each unread spot may still go: an
        # unread jump through a name, to a label ever written into it; any
        # other, anywhere. A `return` such a call may come back from is
        # not known either.
        bad = bytearray(count)
        for c in t.unclear:
            bad[c] = 1
        anywhere = bytearray(count)
        candidates = python_dict()
        returns_unknown = False
        starts = python_list()
        for s in t.sbad:
            named = t.names.get(snode[s])
            if named is not None and named[1] is not None and t.written.get(named[1]) is None:
                for _step in _urmsg_stretch_written_work(t, named[1]):
                    yield
        for s in t.sbad:
            c = comp[s]
            bad[c] = 1
            named = t.names.get(snode[s])
            got = _URMSG_EVERY_LABEL
            if named is not None and named[1] is not None:
                got = _urmsg_stretch_written(t, named[1])
            if got is _URMSG_EVERY_LABEL:
                anywhere[c] = 1
                if named is not None and named[0] == u"call":
                    returns_unknown = True
            else:
                candidates.setdefault(c, python_set()).update(got)
                if named is not None and named[0] == u"call":
                    starts.extend(got)
        if returns_unknown:
            # (A jump through a name back to the line after the jump that
            # left goes back to a known place: not one of these.)
            c = 0
            while c < count:
                if real_ret[c]:
                    bad[c] = 1
                c += 1
        elif starts:
            seen = bytearray(len(nodes))
            for v in starts:
                seen[v] = 1
            while starts:
                if _urmsg_stretch_late(t):
                    yield
                v = starts.pop()
                if _urmsg_kind(nodes[v]) == _URMSG_K_RET:
                    for s in t.sat.get(v, ()):
                        bad[comp[s]] = 1
                for w in t.succ[v]:
                    if not seen[w]:
                        seen[w] = 1
                        starts.append(w)
        yield

        ahead = bytearray(bad)
        for _step in spread_back(ahead, False):
            yield
        ahead_stop = bytearray(bad)
        for _step in spread_back(ahead_stop, True):
            yield
        yield

        # Stopping at a roam region's entry holds only while nothing unread
        # past it can come back: a region that reaches an unread spot with
        # ways that cannot be told, or one whose candidates reach back to
        # it, is not read in full either.
        if any(anywhere):
            for _step in spread_back(anywhere, False):
                yield
            c = 0
            while c < count:
                if anywhere[c]:
                    ahead_stop[c] = 1
                c += 1
        for c in candidates:
            fwd = bytearray(count)
            todo = python_list()
            for j in candidates[c]:
                for s in t.sat.get(j, ()):
                    if not fwd[comp[s]]:
                        fwd[comp[s]] = 1
                        todo.append(comp[s])
            while todo:
                if _urmsg_stretch_late(t):
                    yield
                d = todo.pop()
                for e in rall[d]:
                    if not fwd[e]:
                        fwd[e] = 1
                        todo.append(e)
            rev = bytearray(count)
            rev[c] = 1
            for _step in spread_back(rev, False):
                yield
            d = 0
            while d < count:
                if rev[d] and fwd[d]:
                    ahead_stop[d] = 1
                d += 1
            yield

        # Can reach the end of a scene (a `return`, or a jump through a name
        # back to the line after the jump that left); reached from where the
        # game starts the story without a call.
        rets = bytearray(own_ret)
        c = 0
        while c < count:
            if _urmsg_stretch_late(t):
                yield
            if not rets[c]:
                for d in rnext[c]:
                    if rets[d]:
                        rets[c] = 1
                        break
            c += 1
        free = bytearray(count)
        mark = bytearray(n)
        todo = python_list(t.seeds)
        for s in todo:
            mark[s] = 1
        while todo:
            if _urmsg_stretch_late(t):
                yield
            s = todo.pop()
            free[comp[s]] = 1
            for w in ssucc[s]:
                if not mark[w]:
                    mark[w] = 1
                    todo.append(w)
        yield

        # The called scenes a region is inside: the called states that reach
        # it, carried forward (regions from the last number down).
        many = _URMSG_EVERY_LABEL

        def merge(a, b):
            if a is None:
                return b
            if a is many or b is many:
                return many
            if b <= a:
                return a
            both = a | b
            return many if len(both) > _URMSG_STRETCH_CALLERS else both

        sites = python_dict()
        entries = python_dict()
        for s in t.scalls:
            for e in t.scalls[s]:
                sites.setdefault(e, python_list()).append(s)
                entries.setdefault(comp[e], python_list()).append(e)
        carried = python_dict()
        callers = python_dict()
        c = count - 1
        while c >= 0:
            if _urmsg_stretch_late(t):
                yield
            mine = carried.pop(c, None)
            if rets[c]:
                for e in entries.get(c, ()):
                    mine = merge(mine, frozenset((e,)))
                if mine is not None:
                    callers[c] = mine
                    for d in rnext[c]:
                        if rets[d]:
                            carried[d] = merge(carried.get(d), mine)
            c -= 1
        yield

        def kinds_for(ahead, kinds):
            """Each region's kind into kinds, as a generator of slices."""
            state = bytearray(count)    # 0 to do, 1 being worked out, 2 done

            def kind_of(c):
                if state[c] == 2:
                    return kinds[c]
                if state[c] == 1:
                    return 0
                state[c] = 1
                answer = 0
                if c in roam:
                    answer = 2
                else:
                    votes = python_set()
                    mine = callers.get(c)
                    if mine is many:
                        votes.add(0)
                    elif mine:
                        for e in mine:
                            for site in sites.get(e, ()):
                                votes.add(kind_of(comp[site]))
                        if free[c]:
                            votes.add(1)
                    else:
                        votes.add(1)
                    if len(votes) == 1 and 2 in votes:
                        answer = 2
                    elif len(votes) == 1 and 1 in votes and not ahead[c]:
                        answer = 1
                kinds[c] = answer
                state[c] = 2
                return answer

            c = 0
            while c < count:
                if _urmsg_stretch_late(t):
                    yield
                kind_of(c)
                c += 1

        kinds = bytearray(count)
        for _step in kinds_for(ahead, kinds):
            yield
        kinds_stop = bytearray(count)
        for _step in kinds_for(ahead_stop, kinds_stop):
            yield
        t.kinds = kinds
        t.kinds_stop = kinds_stop
