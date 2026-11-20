# ---------------------------------------------------------------------------
# The script index: what this game checks, what it sets, and where
# ---------------------------------------------------------------------------
#
# URM's forward vision is twenty nodes. Everything it knows about a variable
# is its value right now. It has never read the game.
#
# Ren'Py keeps every node of every loaded script in one flat list for the
# whole session - renpy.game.script.all_stmts, in Ren'Py 7 and 8 alike
# (script.py, extended in finish_load, never released). This walks that list
# once and records, for every name the script touches:
#
#   reads   each condition that tests it - the operator, the literal it is
#           compared against, the label, and the menu option text when the
#           test is a menu condition
#   writes  each assignment - the operator, the literal written, the label,
#           and the menu option the player picked to reach it
#   rivals  each comparison of one name against another (rel_strong >
#           rel_passive), where no single edit can satisfy the gate
#   tokens  each `"x" in coll` test, so a word kept in a list or set is
#           findable by the word
#
# Everything is read from the script as written. Nothing is evaluated,
# nothing the game defines is called, and the store is never touched.
#
# What it cannot see, and every surface built on it must say so: tests inside
# the game's own helper functions, conditions in screens, names built at run
# time by concatenation, and anything passed through eval. So results are
# always "found in the script", never "all".
#
# Two things about Ren'Py's store decide how this is written:
#
#   * in a store, dict, list, set and object are rebound to the rollback-
#     tracked Revertable kinds (renpy/minstore.py:37-50), and [] / {} literals
#     are rewritten to them too (python.py WrapNode). An index built from
#     those would be copied into the rollback log as it grew. So it is built
#     only from python_dict / python_list / python_set / python_object, and
#     the hot code has no container literals at all.
#   * the index object lives on a URM class in URM's _constant store, which
#     is neither saved nor rolled back.

init 999 python:

    import ast as _urmi_ast

    # Inside a Ren'Py 7 store, `str` is Ren'Py's compat str - unicode - but
    # Python 2's parser hands back string literals as byte strings. So text
    # types come from the real builtins, never from the store's names.
    try:
        import __builtin__ as _urm_builtins
        _urmi_text = (_urm_builtins.str, _urm_builtins.unicode)
    except ImportError:
        _urmi_text = (str,)

    _URMI_OPS = python_dict()
    for _urmi_pair in (("Eq", "=="), ("NotEq", "!="), ("Lt", "<"),
                       ("LtE", "<="), ("Gt", ">"), ("GtE", ">="),
                       ("In", "in"), ("NotIn", "not in"),
                       ("Is", "is"), ("IsNot", "is not")):
        if hasattr(_urmi_ast, _urmi_pair[0]):
            _URMI_OPS[getattr(_urmi_ast, _urmi_pair[0])] = _urmi_pair[1]

    # A literal on the LEFT reads the other way round: 3 < x is x > 3.
    _URMI_FLIP = python_dict()
    for _urmi_pair in (("==", "=="), ("!=", "!="), ("<", ">"), (">", "<"),
                       ("<=", ">="), (">=", "<=")):
        _URMI_FLIP[_urmi_pair[0]] = _urmi_pair[1]

    _URMI_YIELD_EVERY = 1500


    # The literal, name and callee readers are the story graph's since
    # rework move 9 (its _urmsg_py_parse needs them, and so does the table
    # of augmented assignments, which went with them); these names are what
    # the rest of this file calls.
    _urmi_literal = _urmsg_literal
    _urmi_name = _urmsg_name
    _urmi_callee = _urmsg_callee

    _URMI_BINOPS = python_dict()
    for _urmi_pair in (("Add", "+"), ("Sub", "-"), ("Mult", "*"),
                       ("Div", "/"), ("FloorDiv", "//"), ("Mod", "%")):
        if hasattr(_urmi_ast, _urmi_pair[0]):
            _URMI_BINOPS[getattr(_urmi_ast, _urmi_pair[0])] = _urmi_pair[1]

    def _urmi_expr_text(node, depth=0):
        """
        Small arithmetic over names and numbers, written back out:
        `hard_love - 30`, `max_love - love`. None for anything bigger.

        Twisted Thoughts writes its caps as `love < hard_love-30` and
        `max_love-love>9`; without this, a comparison with arithmetic on one
        side recorded nothing at all.
        """

        if depth > 4:
            return None
        name = _urmi_name(node)
        if name is not None:
            return name
        ok, value = _urmi_literal(node)
        if ok:
            return "%r" % (value,)
        if isinstance(node, _urmi_ast.BinOp):
            op = _URMI_BINOPS.get(type(node.op))
            left = _urmi_expr_text(node.left, depth + 1)
            right = _urmi_expr_text(node.right, depth + 1)
            if op and left is not None and right is not None:
                return "%s %s %s" % (left, op, right)
        return None

    def _urmi_mentions(node, out):
        """
        Every variable named anywhere in an expression - longest chain only,
        so mc.stats.love is one mention, not three. A call's function name is
        not a variable read; its arguments are.
        """

        if isinstance(node, (_urmi_ast.Name, _urmi_ast.Attribute,
                             _urmi_ast.Subscript)):
            name = _urmi_name(node)
            if name is not None:
                out.append(name)
                return
        if isinstance(node, _urmi_ast.Call):
            for arg in node.args:
                _urmi_mentions(arg, out)
            for kw in getattr(node, "keywords", None) or ():
                _urmi_mentions(kw.value, out)
            return
        for child in _urmi_ast.iter_child_nodes(node):
            _urmi_mentions(child, out)


    def _urm_was_seen(name, seen):
        """
        Whether a statement is in a seen record (_seen_ever / seen_session).

        Ren'Py 8.5 can store a 64-bit hash of the statement's name instead of
        the name (config.hash_seen; execution.py: `seen_key =
        renpy.astsupport.hash64(self.current)`), and its own seen_current
        accepts either. So: the name, then its hash where the engine has one.
        """

        if seen is None:
            return False
        try:
            if name in seen:
                return True
        except Exception:
            return False
        hasher = getattr(__import__("sys").modules.get("renpy.astsupport"), "hash64", None)
        if hasher is None:
            return False
        try:
            return hasher(name) in seen
        except Exception:
            return False

    class _URMIFlag(python_object):
        """One word a game keeps in a collection, named by the code that tests it."""

        def __init__(self, name, word, coll, getter, attr):
            self.name = name
            self.word = word
            self.coll = coll          # store name of the collection
            self.getter = getter      # the game's test function, or None
            self.attr = attr          # members are objects matched on this attribute
            self.objects = python_list()  # store names of objects that stand for it

    def _urmi_helper_role(fn, param):
        """("get" | "add" | "remove", collection, attribute or None), or None."""

        role = None
        coll = None
        attr = None
        remover = fn.name.lower().startswith(("remove", "del", "unset", "lose", "drop", "clear"))

        for node in _urmi_ast.walk(fn):
            # o in coll
            if isinstance(node, _urmi_ast.Compare) and len(node.ops) == 1 and \
                    isinstance(node.ops[0], _urmi_ast.In) and \
                    isinstance(node.left, _urmi_ast.Name) and node.left.id == param:
                target = _urmi_name(node.comparators[0])
                if target is not None and role is None:
                    role, coll = "get", target

            # any(x.name == i for x in coll)
            if isinstance(node, (_urmi_ast.GeneratorExp, _urmi_ast.ListComp)) and node.generators:
                gen = node.generators[0]
                target = _urmi_name(gen.iter)
                var = getattr(gen.target, "id", None)
                for sub in _urmi_ast.walk(node):
                    if not isinstance(sub, _urmi_ast.Compare) or len(sub.ops) != 1:
                        continue
                    sides = (sub.left, sub.comparators[0])
                    for one, other in (sides, sides[::-1]):
                        if isinstance(one, _urmi_ast.Attribute) and \
                                isinstance(one.value, _urmi_ast.Name) and one.value.id == var:
                            mine = (isinstance(other, _urmi_ast.Name) and other.id == param) or (
                                isinstance(other, _urmi_ast.Attribute) and
                                isinstance(other.value, _urmi_ast.Name) and other.value.id == param)
                            if mine and target is not None:
                                if remover:
                                    return ("remove", target, one.attr)
                                if role is None and isinstance(sub.ops[0], _urmi_ast.Eq):
                                    role, coll, attr = "get", target, one.attr

            # coll.add(i) / coll.append(i) / coll.remove(i) / coll.discard(i)
            if isinstance(node, _urmi_ast.Call) and isinstance(node.func, _urmi_ast.Attribute) \
                    and node.args and isinstance(node.args[0], _urmi_ast.Name) \
                    and node.args[0].id == param:
                target = _urmi_name(node.func.value)
                if target is not None:
                    if node.func.attr in ("add", "append"):
                        return ("add", target, None)
                    if node.func.attr in ("remove", "discard"):
                        return ("remove", target, None)

        if role == "get":
            return (role, coll, attr)
        return None

    class _URMIndex(python_object):
        """
        Built once, read many times. Fields are plain python containers.

        A site is a tuple: (filename, line, node id) - the id lets the label
        and the enclosing menu option be worked out on demand from `parent`
        instead of being stored on every record.
        """

        def __init__(self):
            self.state = "idle"          # idle, building, ready, failed
            self.done = 0
            self.total = 0
            self.error = None
            self.seconds = 0.0
            self.generation = 0
            self.finished_at = None
            self.checks = 0              # every recorded read, for the "done" line

            self.reads = python_dict()   # name -> [(site, op, literal)]
            self.writes = python_dict()  # name -> [(site, op, literal or None, text)]
            self.rivals = python_dict()  # name -> [(site, op, other)]
            self.tokens = python_dict()  # token -> [(site, collection, op)]
            self.calls = python_dict()   # callee -> [(site, string args)]
            self.declared = python_dict()  # name -> (site, source text)

            # Flags: games that keep choices as words in a collection rather
            # than as variables - option("x") / true("x"), new_path(p) /
            # on_path("p"). See _URMIndex._helpers and _flags.
            self.helpers = python_dict()   # function -> (role, collection, attribute or None)
            self.callreads = python_dict() # callee -> [(site, string args, "truthy"/"falsy")]
            self.callnames = python_dict() # callee -> [(site, name args)]
            self.flags = python_dict()     # flag name -> _URMIFlag

            self.parent = python_dict()  # id(node) -> (parent node, kind, extra)
            self.labels = python_dict()  # label name -> Label node
            # id(node) -> the one statement whose .next it is, or None when
            # several lead to it (the statement after an if or a menu)
            self.prev = python_dict()
            self.prev_many = python_dict()  # id(node) -> [every statement leading to it]
            # filename -> (sorted lines, names): the label a line falls under,
            # for scripts whose label bodies are not indented under the label
            self.label_lines = python_dict()
            # filename -> (ends, ups), one entry per label of label_lines:
            # the last line a label inside a block holds (None for a label
            # at the top level of the file - it runs on to the next one),
            # and the place of the label to ask once past that line (-1:
            # none). See label_at.
            self.label_ends = python_dict()
            self.nodes = python_dict()   # id(node) -> node, for site lookups
            self._conds = python_dict()  # condition text -> parsed findings

        # -------------------------------------------------------------- build

        def _add(self, table, key, item):
            bucket = table.get(key)
            if bucket is None:
                bucket = python_list()
                table[key] = bucket
            bucket.append(item)

        def _site(self, node):
            self.nodes[id(node)] = node
            return (getattr(node, "filename", "?"),
                    getattr(node, "linenumber", 0),
                    id(node))

        def _condition(self, text):
            """
            What a condition tests, parsed once per distinct string.

            Returns a list of (kind, a, b, c) with kind one of:
                cmp    name, op, literal
                rival  name, op, other name
                token  token, collection, op
                truth  name, "truthy"/"falsy", None
                call   callee, (string args), None
            """

            cached = self._conds.get(text)
            if cached is not None:
                return cached

            found = python_list()

            try:
                tree = _urmi_ast.parse(text.strip(), mode="eval")
            except Exception:
                self._conds[text] = found
                return found

            negated = python_set()
            for node in _urmi_ast.walk(tree):
                if isinstance(node, _urmi_ast.UnaryOp) and isinstance(
                        node.op, _urmi_ast.Not) and isinstance(node.operand, _urmi_ast.Call):
                    negated.add(id(node.operand))

            for node in _urmi_ast.walk(tree):

                if isinstance(node, _urmi_ast.Compare):
                    left = node.left
                    for op_node, right in zip(node.ops, node.comparators):
                        op = _URMI_OPS.get(type(op_node))
                        if op is not None:
                            self._compare(found, left, op, right)
                        left = right

                elif isinstance(node, _urmi_ast.UnaryOp) and isinstance(
                        node.op, _urmi_ast.Not):
                    name = _urmi_name(node.operand)
                    if name is not None:
                        found.append(("truth", name, "falsy", None))

                elif isinstance(node, _urmi_ast.Call):
                    callee = _urmi_callee(node)
                    if callee is not None:
                        args = python_list()
                        for arg in node.args:
                            ok, value = _urmi_literal(arg)
                            if ok and isinstance(value, _urmi_text):
                                args.append(value)
                        found.append(("call", callee, tuple(args),
                                      "falsy" if id(node) in negated else "truthy"))

            # Bare names used as truth values: `if flag:`, `a and b`.
            self._truths(found, tree.body)

            # Anything the structured kinds above did not cover is still a
            # read: a name inside arithmetic, a function argument, a slice.
            # Gate counts and "where is this checked" must not miss it.
            covered = python_set()
            for kind, a, b, _c in found:
                if kind in ("cmp", "truth", "rival"):
                    covered.add(a)
                elif kind == "token":
                    covered.add(b)
            mentioned = python_list()
            _urmi_mentions(tree.body, mentioned)
            for name in mentioned:
                if name not in covered:
                    covered.add(name)
                    found.append(("mention", name, None, None))

            self._conds[text] = found
            return found

        def _truths(self, found, node):
            if isinstance(node, _urmi_ast.BoolOp):
                for value in node.values:
                    self._truths(found, value)
                return
            name = _urmi_name(node)
            if name is not None:
                found.append(("truth", name, "truthy", None))

        def _compare(self, found, left, op, right):

            if op in ("in", "not in"):
                ok, token = _urmi_literal(left)
                coll = _urmi_name(right)
                if ok and isinstance(token, _urmi_text) and coll is not None:
                    found.append(("token", token, coll, op))
                return

            lname = _urmi_name(left)
            rname = _urmi_name(right)
            lok, lval = _urmi_literal(left)
            rok, rval = _urmi_literal(right)

            if lname is not None and rok:
                found.append(("cmp", lname, op, rval))
            elif rname is not None and lok:
                found.append(("cmp", rname, _URMI_FLIP.get(op, op), lval))
            elif lname is not None and rname is not None:
                found.append(("rival", lname, op, rname))
                found.append(("rival", rname, _URMI_FLIP.get(op, op), lname))
            elif lname is not None:
                # love < hard_love - 30
                other = _urmi_expr_text(right)
                if other is not None:
                    found.append(("rival", lname, op, other))
            elif rname is not None:
                other = _urmi_expr_text(left)
                if other is not None:
                    found.append(("rival", rname, _URMI_FLIP.get(op, op), other))

        def _record_condition(self, node, text, extra):
            site = self._site(node)
            for kind, a, b, c in self._condition(text):
                if kind == "cmp":
                    self._add(self.reads, a, (site, b, c))
                elif kind == "truth":
                    self._add(self.reads, a, (site, b, None))
                elif kind == "rival":
                    self._add(self.rivals, a, (site, b, c))
                    self._add(self.reads, a, (site, "vs", c))
                elif kind == "token":
                    self._add(self.tokens, a, (site, b, c))
                    self._add(self.reads, b, (site, c, a))
                elif kind == "call":
                    self._add(self.calls, a, (site, b))
                    self._add(self.callreads, a, (site, b, c or "truthy"))
                elif kind == "mention":
                    self._add(self.reads, a, (site, "mention", None))

        def _python(self, node, source):
            """Every assignment and every bare helper call in a $ line or block."""

            # The text is parsed once by the story graph (rework move 9: a
            # pure function, safe on this thread); what follows is this
            # block's reading of it, in the order it has always recorded.
            parsed, events = _urmsg_py_parse(source)
            if not parsed:
                return

            site = self._site(node)

            for event in events:
                if event[0] == "w":
                    # An assignment, at any depth. A name unpacked from a
                    # tuple is written with no value.
                    _kind, _depth, _top, name, op, ok, value, _spread = event
                    if name is not None:
                        self._add(self.writes, name,
                                  (site, op, value if ok else None, None))
                    continue

                _kind, _depth, _top, callee, args, names, attr, owner, coll = event
                if callee is None:
                    continue
                self._add(self.calls, callee, (site, args))
                if names:
                    self._add(self.callnames, callee, (site, names))

                # coll.append("x") / coll.add("x") writes a token.
                if owner is not None:
                    for ok, value in coll:
                        if ok:
                            self._add(self.writes, owner,
                                      (site, "." + attr, value, None))

        def _link(self, node):
            """Remember which container each block member sits in."""

            # Which blocks a statement holds is the story graph's answer
            # (rework move 8); a pure function, safe on this thread.
            for kind, _arm, extra, members in _urmsg_children(node):
                for child in members:
                    self.parent[id(child)] = (node, kind, extra)

        def check_count(self):
            return self.checks

        def build(self, stmts, generation=0, alive=None):
            """
            Walk every node once. Safe to call from a background thread.

            `alive` is asked every few thousand nodes; when it says no - the
            player pressed Shift+R and a newer build has started - this one
            stops rather than finishing work nobody will read.
            """

            import time

            ast = renpy.ast
            started = time.time()
            self.state = "building"
            self.generation = generation

            # Node classes vary by engine version - Default arrived later than
            # Define, and a missing one must cost that one kind of record, not
            # abort the whole walk with an AttributeError.
            def kinds(*names):
                found = python_list()
                for name in names:
                    cls = getattr(ast, name, None)
                    if cls is not None:
                        found.append(cls)
                return tuple(found) or (type(None),)

            IF = kinds("If")
            WHILE = kinds("While")
            MENU = kinds("Menu")
            PYTHON = kinds("Python")
            DECLARE = kinds("Default", "Define")
            LABEL = kinds("Label")
            pairs = python_dict()
            label_nodes = python_dict()  # (filename, line, name) -> Label

            try:
                nodes = python_list(stmts)
                self.total = len(nodes)

                for index, node in enumerate(nodes):
                    self.done = index

                    if index % _URMI_YIELD_EVERY == 0 and index:
                        # Let the render loop have the GIL.
                        time.sleep(0.001)
                        if alive is not None and not alive():
                            self.state = "abandoned"
                            return

                    try:
                        self._link(node)

                        # Dialogue in a translation block chains as
                        # Translate -> Say -> EndTranslate -> next Translate
                        # (Ren'Py 7.5). An engine whose Translate points past
                        # its own block would give the EndTranslate two
                        # predecessors; that link is left out so the chain
                        # stays a single line either way.
                        after = getattr(node, "next", None)
                        if after is not None and not (
                                isinstance(node, renpy.ast.Translate) and node.block
                                and after is not node.block[0]):
                            key = id(after)
                            if key in self.prev:
                                many = self.prev_many.get(key)
                                if many is None:
                                    many = python_list()
                                    if self.prev[key] is not None:
                                        many.append(self.prev[key])
                                    self.prev_many[key] = many
                                many.append(node)
                                self.prev[key] = None
                            else:
                                self.prev[key] = node

                        if isinstance(node, LABEL):
                            name = getattr(node, "name", None)
                            if isinstance(name, _urmi_text):
                                self.labels[name] = node
                                fn = getattr(node, "filename", None)
                                bucket = pairs.get(fn)
                                if bucket is None:
                                    bucket = python_list()
                                    pairs[fn] = bucket
                                bucket.append((getattr(node, "linenumber", 0), name))
                                label_nodes[(fn, getattr(node, "linenumber", 0), name)] = node
                            continue

                        # The tests of a statement are the story graph's
                        # list (rework move 8); which of them are recorded
                        # stays this block's rule.
                        if isinstance(node, IF):
                            for _arm, cond, _text in _urmsg_conds(node):
                                if not _urmsg_no_test(cond):
                                    self._record_condition(node, cond, None)

                        elif isinstance(node, WHILE):
                            for _arm, cond, _text in _urmsg_conds(node):
                                self._record_condition(node, cond, None)

                        elif isinstance(node, MENU):
                            for _arm, cond, text in _urmsg_conds(node):
                                if not _urmsg_no_test(cond):
                                    self._record_condition(node, cond, text)

                        elif isinstance(node, PYTHON):
                            source = getattr(getattr(node, "code", None),
                                             "source", None)
                            if source:
                                self._python(node, source)
                                if "def " in source:
                                    self._helpers(source)

                        elif isinstance(node, DECLARE):
                            self._declare(node)

                    except Exception:
                        continue

                for fn, bucket in pairs.items():
                    bucket.sort()
                    lines = python_list()
                    names = python_list()
                    # For label_at: a label inside a block (it has a link)
                    # holds only the lines down to its last statement; one
                    # at the top level of the file runs on to the next.
                    # `open_at` is the labels a line may still be in,
                    # outermost first.
                    ends = python_list()
                    ups = python_list()
                    open_at = python_list()
                    for line, name in bucket:
                        lines.append(line)
                        names.append(name)
                        held = label_nodes.get((fn, line, name))
                        if held is None or id(held) not in self.parent:
                            end = None
                            del open_at[:]
                        else:
                            end = _urmsg_last_line(held)
                            while open_at and ends[open_at[-1]] is not None \
                                    and ends[open_at[-1]] < line:
                                open_at.pop()
                        ups.append(open_at[-1] if open_at else -1)
                        open_at.append(len(ends))
                        ends.append(end)
                    self.label_lines[fn] = (lines, names)
                    self.label_ends[fn] = (tuple(ends), tuple(ups))

                try:
                    self._flags()
                except Exception as error:
                    print("URM+: flags not indexed (%s)" % (error,))

                total = 0
                for bucket in self.reads.values():
                    total += len(bucket)
                self.checks = total

                self.done = self.total
                self.seconds = time.time() - started
                self.finished_at = time.time()
                # Last: everything above is complete before anyone sees ready.
                self.state = "ready"

            except Exception as error:
                self.error = "%s: %s" % (type(error).__name__, error)
                self.seconds = time.time() - started
                self.finished_at = time.time()
                self.state = "failed"

        def _helpers(self, source):
            """
            Learn the game's flag helpers from their definitions:

                def true(o):        if o in mc_choices: return True
                def option(i):      mc_choices.add(i)
                def on_path(i):     any(x.name == i for x in mc_paths)
                def new_path(i):    mc_paths.add(i)
                def remove_path(i): rebuilds mc_paths without i

            Only module-level functions with a first parameter; a method is
            the game's class at work, not a flag. Recorded as (role,
            collection, attribute) with role "get", "add" or "remove".
            """

            try:
                tree = _urmi_ast.parse(source, mode="exec")
            except Exception:
                return

            for fn in tree.body:
                if not isinstance(fn, _urmi_ast.FunctionDef):
                    continue
                args = getattr(fn.args, "args", None) or ()
                if not args:
                    continue
                first = args[0]
                param = getattr(first, "arg", None) or getattr(first, "id", None)
                if not param:
                    continue
                found = _urmi_helper_role(fn, param)
                if found is not None:
                    self.helpers[fn.name] = found

        def _flags(self):
            """
            Turn helper calls into flags, each a named variable of its own:
            reads for every getter call in a condition, writes for every setter
            or remover call, and the same for words tested directly with
            `"x" in coll` and written with coll.add / append / remove.

            A flag is named by the code that tests it - true("x"), or "x" in
            coll when the game has no getter - so the name is what the player
            sees in the condition.
            """

            getters = python_dict()        # collection -> getter function
            for fname, (role, coll, attr) in self.helpers.items():
                if role == "get" and coll not in getters:
                    getters[coll] = (fname, attr)

            def flag(coll, word, objname=None):
                if coll in getters:
                    fname, attr = getters[coll]
                    name = '%s("%s")' % (fname, word)
                else:
                    fname, attr = None, None
                    name = '"%s" in %s' % (word, coll)
                rec = self.flags.get(name)
                if rec is None:
                    rec = _URMIFlag(name, word, coll, fname, attr)
                    self.flags[name] = rec
                if objname and objname not in rec.objects:
                    rec.objects.append(objname)
                return name

            for coll, (fname, attr) in getters.items():
                for site, args, op in self.callreads.get(fname, ()):
                    if args:
                        self._add(self.reads, flag(coll, args[0]), (site, op, None))

            for fname, (role, coll, attr) in self.helpers.items():
                if role not in ("add", "remove"):
                    continue
                on = role == "add"
                for site, args in self.calls.get(fname, ()):
                    if args:
                        self._add(self.writes, flag(coll, args[0]), (site, "=", on, None))
                for site, names in self.callnames.get(fname, ()):
                    word = self._object_word(names[0], getters.get(coll, (None, None))[1])
                    if word:
                        self._add(self.writes, flag(coll, word, names[0]), (site, "=", on, None))

            # Words tested directly: "met_kim" in diary.
            for word, bucket in self.tokens.items():
                for site, coll, op in bucket:
                    if op in ("in", "not in"):
                        self._add(self.reads, flag(coll, word),
                                  (site, "truthy" if op == "in" else "falsy", None))
            for coll in python_list(self.writes.keys()):
                if coll in self.flags:
                    continue
                for site, op, value, _t in self.writes.get(coll) or ():
                    if op in (".add", ".append", ".remove", ".discard") and \
                            isinstance(value, _urmi_text):
                        named = flag(coll, value)
                        if named in self.reads:
                            self._add(self.writes, named, (site, "=", op in (".add", ".append"), None))

            # A word only ever written, never tested, is not a flag anyone needs.
            for name in python_list(self.flags.keys()):
                if name not in self.reads:
                    del self.flags[name]

        def _object_word(self, objname, attr):
            """The word an object stands for: Path("kim_mercy_path", ...) -> kim_mercy_path."""

            if not attr:
                return None
            declared = self.declared.get(objname)
            source = declared[1] if declared else None
            if source:
                try:
                    tree = _urmi_ast.parse(source.strip(), mode="eval").body
                    if isinstance(tree, _urmi_ast.Call):
                        for arg in tree.args:
                            ok, value = _urmi_literal(arg)
                            if ok and isinstance(value, _urmi_text):
                                return value
                        for kw in getattr(tree, "keywords", None) or ():
                            if kw.arg == attr:
                                ok, value = _urmi_literal(kw.value)
                                if ok and isinstance(value, _urmi_text):
                                    return value
                except Exception:
                    pass
            try:
                value = getattr(getattr(renpy.store, objname), attr)
                if isinstance(value, _urmi_text):
                    return value
            except Exception:
                pass
            return None

        def _declare(self, node):
            varname = getattr(node, "varname", None)
            if not varname:
                return
            store = getattr(node, "store", "store") or "store"
            if store == "store":
                name = varname
            elif store.startswith("store."):
                name = store[6:] + "." + varname
            else:
                name = varname
            source = getattr(getattr(node, "code", None), "source", None)
            self.declared[name] = (self._site(node), source)

        # -------------------------------------------------------------- query

        def where(self, site):
            """(label, option text, filename, line) for a site."""

            filename, line, nid = site
            node = self.nodes.get(nid)
            option = None

            for _parent, kind, extra in _urmsg_climb(self.parent, node):
                if kind == "option":
                    option = extra
                    break

            # The scene is the story graph's one rule (idea 1).
            label = _urmsg_label_of(self, node, filename, line)

            return (label, option, filename, line)

        def label_at(self, filename, line):
            """
            The label a script line falls under, for a statement whose
            chain of containers reaches no label. Many games write a label
            and then carry on at the same indent, so the statements are its
            siblings, not its block - where() used to hand back the node's
            internal tuple name then.

            The nearest label above, but a label that sits inside a block
            counts only for the lines it holds: past its last line the
            answer is the label round it, or the label above at the top
            level of the file (idea 1: a line used to be named after a
            label nested in the scene before it).
            """

            import bisect
            found = self.label_lines.get(filename)
            if not found:
                return None
            lines, names = found
            i = bisect.bisect_right(lines, line) - 1
            spans = self.label_ends.get(filename)
            if spans is not None:
                ends, ups = spans
                n = 0
                while i >= 0 and ends[i] is not None and ends[i] < line and n < 200:
                    i = ups[i]
                    n += 1
            if i < 0:
                return None
            return names[i]


    def _urmi_all_stmts():
        try:
            stmts = renpy.game.script.all_stmts
            if stmts:
                return stmts
        except Exception:
            pass
        return ()

    def _urmi_index():
        """The live index, or None before it has been started."""
        return getattr(x52URM.Var, "_urmcIndex", None)

# ---------------------------------------------------------------------------
# Building the index as the game starts, and saying so
# ---------------------------------------------------------------------------
#
# The index is built on a background thread the moment init finishes, so the
# window and the main menu come up exactly as fast as they did before. A small
# line in the corner says it is working and disappears when it is done.
#
# It cannot use URM's own overlay for that: URM only shows URM_overlay once
# the game reaches `start` or a save is loaded (classes/main.rpy:55-75), so it
# is absent from the splash screen and the main menu - which is where this
# line matters. config.interact_callbacks runs at the start of every
# interaction in every context, menus included, and exists in every engine
# this mod supports.
#
# The thread only READS the script, which is fixed once loaded. It never
# touches the store. If threads are unavailable it builds in the foreground,
# with the same line shown on the first interaction afterwards.

init 999 python:

    def _urmi_start():

        try:
            generation = int(getattr(x52URM.Var, "_urmcIndexGeneration", 0)) + 1
        except Exception:
            generation = 1

        index = _URMIndex()
        x52URM.Var._urmcIndexGeneration = generation
        x52URM.Var._urmcIndex = index
        stmts = _urmi_all_stmts()

        def alive():
            return getattr(x52URM.Var, "_urmcIndexGeneration", generation) == generation

        def run():
            index.build(stmts, generation, alive)

        try:
            import threading
            worker = threading.Thread(target=run, name="URM script index")
            worker.daemon = True
            worker.start()
        except Exception:
            run()

    try:
        _urmi_start()
    except Exception as error:
        print("URM+: script index not started (%s)" % (error,))


    # ------------------------------------------------------------------
    # The corner line
    # ------------------------------------------------------------------

    _URMI_DONE_SHOWN_FOR = 4.0

    def _urmi_progress_text(st, at):
        """DynamicDisplayable body: redraws itself, needs no interaction."""

        import time

        index = _urmi_index()
        if index is None:
            return (Null(), None)

        if index.state == "building":
            total = max(index.total, 1)
            pct = int(100.0 * index.done / total)
            message = "URM: reading the game's script... %d%%" % pct
            again = 0.25

        elif index.state == "ready":
            finished = getattr(index, "finished_at", None)
            if finished is None or time.time() - finished > _URMI_DONE_SHOWN_FOR:
                return (Null(), None)
            message = ("URM: script read - %d checks on %d names found"
                       % (index.check_count(), len(index.reads)))
            again = 0.5

        elif index.state == "failed":
            finished = getattr(index, "finished_at", None)
            if finished is None or time.time() - finished > _URMI_DONE_SHOWN_FOR * 2:
                return (Null(), None)
            message = "URM: could not read the script; prophecy features are off"
            again = 0.5

        else:
            return (Null(), 0.25)

        # Plain ASCII and an explicit outline: this is drawn over whatever the
        # game's own font and colours are, before any of URM's styling exists.
        return (Text(message, size=16, color="#ffffffdd",
                     outlines=((2, "#000000aa", 0, 0),)), again)

    _urmi_layer = "x52Overlay" if "x52Overlay" in config.layers else "overlay"

    def _urmi_interact():
        """Show the corner line in this context if there is anything to say."""

        index = _urmi_index()
        if index is None:
            return
        # Once the line has said its piece, stop looking every interaction.
        finished = getattr(index, "finished_at", None)
        if index.state != "building" and finished and \
                __import__("time").time() - finished > _URMI_DONE_SHOWN_FOR * 2:
            return
        try:
            if not renpy.get_screen("urmi_progress", layer=_urmi_layer):
                renpy.show_screen("urmi_progress", _layer=_urmi_layer)
        except Exception:
            pass

    if _urmi_interact not in config.interact_callbacks:
        config.interact_callbacks.append(_urmi_interact)


# ---------------------------------------------------------------------------
# What the screens ask the index
# ---------------------------------------------------------------------------
#
# Every answer is ready-to-draw text, built here once, so no screen does any
# work on redraw. Every answer is also qualified: the index only knows what is
# written in the script, so it says "found in the script" and never "all".

init 999 python:

    def urm_index_status():
        """('ready'|'building'|'failed'|'off', percent or None)."""

        index = _urmi_index()
        if index is None:
            return ("off", None)
        if index.state == "building":
            return ("building", int(100.0 * index.done / max(index.total, 1)))
        return (index.state, None)

    def _urmi_num(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _urmi_show(value):
        if isinstance(value, _urmi_text):
            return '"%s"' % value
        return "%r" % (value,)

    def urm_checks(name):
        """
        What the game compares `name` against, for the editor.

        Returns (summary, rows) where each row is (button text, value to set
        or None, how many places). Rows are the literal comparisons, sorted
        numerically when they are numbers, so the editor reads like the ladder
        the game actually climbs.
        """

        index = _urmi_index()
        if index is None or index.state != "ready":
            return ("", python_list())

        reads = index.reads.get(name) or ()
        if not reads:
            return ("", python_list())

        counts = python_dict()
        truthy = 0
        rivals = 0
        mentions = 0
        ops_seen = python_set()

        for _site, op, literal in reads:
            if op in ("truthy", "falsy"):
                truthy += 1
                continue
            if op == "vs":
                rivals += 1
                continue
            if op == "mention":
                mentions += 1
                continue
            if op in ("in", "not in"):
                continue
            key = (op, literal if not isinstance(literal, list) else repr(literal))
            counts[key] = counts.get(key, 0) + 1
            ops_seen.add(op)

        rows = python_list()
        for (op, literal), count in counts.items():
            target = None
            if op in ("==", ">=", "<="):
                target = literal
            elif op == ">" and _urmi_num(literal):
                target = literal + 1 if isinstance(literal, int) else literal
            elif op == "<" and _urmi_num(literal):
                target = literal - 1 if isinstance(literal, int) else literal
            text = "%s %s" % (op, _urmi_show(literal))
            if count > 1:
                text += "  x%d" % count
            rows.append((text, target, count, op, literal))

        def order(row):
            literal = row[4]
            if _urmi_num(literal):
                return (0, literal, row[3])
            return (1, _urmi_show(literal), row[3])

        rows.sort(key=order)

        # Comparisons against another variable or a calculation: readable,
        # never clickable - there is no single value that satisfies them.
        seen_rivals = python_set()
        for _site, op, other in index.rivals.get(name) or ():
            text = "%s %s" % (op, other)
            if text in seen_rivals:
                continue
            seen_rivals.add(text)
            rows.append((text, None, 1, op, other))

        gates = len(reads)
        parts = python_list()
        parts.append("found in %d check%s in the script"
                     % (gates, "" if gates == 1 else "s"))
        if truthy:
            parts.append("%d as on/off" % truthy)
        if rivals:
            parts.append("%d against another variable" % rivals)
        if mentions:
            parts.append("%d inside a calculation or function call" % mentions)

        summary = ", ".join(parts)

        # The 99 problem: a counter the game only ever tests with == has no
        # "enough" - a value between the listed ones matches nothing at all.
        numeric_ops = python_set()
        for op, literal in counts:
            if _urmi_num(literal):
                numeric_ops.add(op)
        if numeric_ops == python_set(("==",)) and len(counts) >= 2:
            summary += (". Only these exact numbers are ever checked - "
                        "a value in between, or above them, matches none of them.")

        out = python_list()
        for row in rows:
            out.append((row[0], row[1], row[2]))
        return (summary, out)

    def _urmi_describe(index, site, op, value, use_option=True):
        label, option, filename, line = index.where(site)
        where = "%s, %s:%s" % (label or "?", (filename or "?").split("/")[-1], line)
        if use_option and option:
            return '"%s"  %s %s   (%s)' % (option, op, _urmi_show(value) if value is not None else "", where)
        return "%s %s   (%s)" % (op, _urmi_show(value) if value is not None else "...", where)

    def urm_writers(name, limit=8):
        """Where the script sets `name`, newest-looking first is not knowable - script order."""

        index = _urmi_index()
        if index is None or index.state != "ready":
            return (0, python_list())
        writes = index.writes.get(name) or ()
        rows = python_list()
        for site, op, value, _text in writes[:limit]:
            rows.append(_urmi_describe(index, site, op, value))
        return (len(writes), rows)

    def urm_readers(name, limit=8):
        """Where the script tests `name`."""

        index = _urmi_index()
        if index is None or index.state != "ready":
            return (0, python_list())
        reads = index.reads.get(name) or ()
        rows = python_list()
        for site, op, literal in reads[:limit]:
            if op in ("truthy", "falsy"):
                rows.append(_urmi_describe(index, site, "is on" if op == "truthy" else "is off", None, False))
            elif op == "vs":
                rows.append(_urmi_describe(index, site, "compared with", literal, False))
            elif op == "mention":
                rows.append(_urmi_describe(index, site, "used in a calculation", None, False))
            else:
                rows.append(_urmi_describe(index, site, op, literal, False))
        return (len(reads), rows)

    def urm_gate_count(name):
        index = _urmi_index()
        if index is None or index.state != "ready":
            return None
        return len(index.reads.get(name) or ())

    def _urmi_safe(text):
        """Script text drawn as-is: braces would be read as text tags."""
        return (u"%s" % (text,)).replace("{", "{{")

    def urm_var_panel(name):
        """
        Everything the editor shows about `name`, as one ready-to-draw tuple:
        (state, percent, summary, checks, writer count, writers, reader count).
        """

        state, pct = urm_index_status()
        if state != "ready":
            return (state, pct, "", python_list(), 0, python_list(), 0)

        summary, checks = urm_checks(name)
        wcount, writers = urm_writers(name, 6)
        rcount = urm_gate_count(name) or 0

        safe_checks = python_list()
        for text, value, count in checks:
            safe_checks.append((_urmi_safe(text), value, count))

        safe_writers = python_list()
        for line in writers:
            safe_writers.append(_urmi_safe(line))

        return ("ready", None, _urmi_safe(summary), safe_checks,
                wcount, safe_writers, rcount)

    def urmi_fill(var, valueInput, value):
        """Put one of the game's own values into the editor - not commit it."""

        if getattr(var, "isFlag", False):
            # A flag has no value box: Set ON / Set OFF switch it directly.
            urmfl_set(var.name, bool(value))
            return

        try:
            if var.varType == "boolean":
                SetScreenVariable("newValue", bool(value))()
            elif isinstance(value, _urmi_text):
                valueInput.set_text(value)
            else:
                valueInput.set_text(str(value))
        except Exception:
            pass


