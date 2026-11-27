    # ------------------------------------------------------------------
    # Facts: what a choice holds, what a branch changes, the gates ahead
    # ------------------------------------------------------------------

    _URM_MAX_GATES = 4

    def _urm_idempotent(text):
        """
        Whether running this twice is the same as running it once.

        This is what decides when a duplicate may be dropped. A jump or a call
        leaves the block, and a plain assignment to a value overwrites. An
        augmented assignment or a bare function call does not: `love += 1`
        drawn once for code that runs it ten times is a false statement about
        the game, and that was the single most frequent falsehood in the first
        version of this file.
        """

        if text.startswith("jump ") or text.startswith("call ") or text == "return":
            return True

        head, sep, tail = text.partition("=")

        if not sep or tail.startswith("="):
            return False

        head = head.strip()

        if not head or not (head[0].isalpha() or head[0] == "_"):
            return False

        for ch in head:
            if not (ch.isalnum() or ch in "._"):
                return False

        return True

    def _urm_reduce(records):
        """
        L2 and L3, and an honest count of what they removed.

        Both only ever remove a row that another row already accounts for, and
        both are now limited to statements where that is actually true. A
        repeated `love += 1` is not a duplicate of itself - it is ten points of
        love - so repeats are collapsed into one row carrying a multiplier
        rather than silently thrown away.

        Returns (records, removed) where a record is (guards, text, count) and
        removed is how many rows were dropped outright, for the "+N more" tally.
        """

        plain = set(text for guards, text in records if not guards)

        removed = 0
        order = []
        index = {}

        for guards, text in records:

            # L2: a guarded copy of something that also happens unguarded,
            # and only when running it twice would change nothing.
            if guards and text in plain and _urm_idempotent(text):
                removed += 1
                continue

            key = (guards, text)

            if key in index:
                # L3: the same statement under the same guards. Idempotent
                # ones collapse; the rest keep a count, because the number of
                # times they run is the whole point of them.
                if _urm_idempotent(text):
                    removed += 1
                else:
                    index[key][2] += 1
                continue

            entry = [guards, text, 1]
            index[key] = entry
            order.append(entry)

        return [(g, t, n) for g, t, n in order], removed

    # ------------------------------------------------------------------
    # The chain of gates
    # ------------------------------------------------------------------

    def _urm_chain():
        """
        Every gate ahead of the cursor, in the order they are tested.

        The whole chain is collected before any card is built, so the summary
        can say how many gates there really are even when the card list is
        capped. The first gate is the core's reader's (_urm_gate_ahead);
        the walk is the story graph's (_urmsg_chain, rework move 5) and so
        is each step (_urmsg_step_urm, move 5b: URM's nextNode, read from
        the same statement fields). A step URM's own code would raise on - a
        jump ahead that cannot be followed - no longer empties the card
        (idea 2): the gates found before it are returned, closed by the
        step that says where the chain stops.
        """

        # Parallel to steps: (if-statement, arm index) for each, or (None, -1)
        # for the fall-through tail. Kept in our memory, so Take can name
        # the exact arm without walking again.
        chain = _urm_read_chain(_urm_gate_ahead())
        _URMMemory.chain_meta = chain.meta if chain is not None else ()
        _URMMemory.chain_ways = chain.ways if chain is not None else ()
        return chain.steps if chain is not None else python_list()

    def _urm_read_chain(first):
        if first is None:
            return None
        return _urmsg_chain(first, _urm_lookahead(), _urmsg_blocks_urm,
                            _urmsg_step_urm, _URM_MAX_GATES + 4, origin=_urmsg_here())

    # Unlike the graph's general read hints, these must account for every
    # read. The result distinguishes a constant expression from an opaque
    # one. A path uses its own name as Search does, without its prefixes.
    _URM_CHECK_READS = python_dict()
    _URM_CHECK_OPERANDS = python_dict((
        ("BoolOp", ("values",)), ("BinOp", ("left", "right")),
        ("UnaryOp", ("operand",)), ("Compare", ("left", "comparators")),
        ("IfExp", ("test", "body", "orelse")),
        ("Tuple", ("elts",)), ("List", ("elts",)), ("Set", ("elts",)),
        ("Dict", ("keys", "values")),
    ))

    def _urm_check_read(node, names):
        if _urmsg_literal(node)[0]:
            return True
        kind = _urmsg_kind_of(node)
        if kind in ("Name", "Attribute", "Subscript"):
            name = _urmsg_name(node)
            if name is None:
                return False
            names.add(name)
            return True
        fields = _URM_CHECK_OPERANDS.get(kind)
        if fields is None:
            return False
        for field in fields:
            value = getattr(node, field)
            for child in value if isinstance(value, python_list) else (value,):
                if not _urm_check_read(child, names):
                    return False
        return True

    def _urm_check_reads(condition):
        """All the names a check reads, or None when any read is unknown."""

        text = (u"%s" % (condition,)).strip()
        if text not in _URM_CHECK_READS:
            names = python_set()
            try:
                parsed = _urmsg_parse(text, "eval")
                result = frozenset(names) if _urm_check_read(parsed.body, names) else None
            except (SyntaxError, ValueError, RuntimeError):
                result = None
            _URM_CHECK_READS[text] = result
        return _URM_CHECK_READS[text]

    def _urm_chain_ignored(chain, ignored):
        """Whether every read in the whole notification can be ignored."""

        if not ignored or chain.cut or chain.lost or chain.live:
            return False
        found = False
        for kind, condition, _block in chain.steps:
            if kind == "gate":
                reads = _urm_check_reads(condition)
                if reads is None or not reads.issubset(ignored):
                    return False
                found = found or bool(reads)
        return found

    def _urm_choice_nodes(choice):
        """A choice's own block: choice is one of _urm_choices_here()."""

        try:
            return choice[3]
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Reach: what playing on can still do to a number, and whether a value
    # it needs is still in reach. Moved from the variable window (70, 74),
    # unchanged but for the core prefix, so the route map and the choice
    # cards can read it too.
    #
    # A write is any object with .op ("=", "+=", "-=", ...), .value (the
    # literal, None when the index could not read it), .node (the statement)
    # and, for _urm_picks, .option (the choice it sits under, or None) and
    # .status: "later" or "not" is still ahead (_URM_AHEAD), "played",
    # "never" or "above" is behind (_URM_BEHIND), "" not known. The
    # variable window makes them today (70_var_panel_facts).
    #
    #   _urm_picks(menus, menu_order, auto, current_menu)
    #       menus: {id(menu): [its writes]}; menu_order: those menus, in
    #       any order (the result is sums, max and min); auto: the writes
    #       under no choice; current_menu: the menu on screen, or None.
    #       Gives ([gains], [losses], unreadable).
    #   _urm_reach(need, gains, losses, unreadable)
    #       need: target minus the value now. Gives "gain" (in reach with a
    #       pick to spare), "warn" (only by taking every pick that helps),
    #       "loss" (no pick left gets there) or None (a write ahead cannot
    #       be read, so no guess).
    # ------------------------------------------------------------------

    _URM_AHEAD = ("later", "not")
    _URM_BEHIND = ("played", "never", "above")

    def _urm_isnum(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _urm_value_ok(w):
        """Whether the literal in a write is known - None from the index means 'computed'."""

        if w.op == "=":
            return w.value is not None or _urm_assign_none(w)
        return w.value is not None

    def _urm_assign_none(w):
        node = w.node
        source = getattr(getattr(node, "code", None), "source", "") or ""
        return "None" in source


    def _urm_delta(w):
        """The number a write adds, or None when it is not a plain + or -."""

        if w.op in ("+=", "-=") and _urm_value_ok(w) and _urm_isnum(w.value):
            return w.value if w.op == "+=" else -w.value
        return None

    def _urm_picks(menus, menu_order, auto, current_menu):
        """
        What playing on can still do to a number: ([gains], [losses],
        unreadable). One entry per menu ahead (its best option each way:
        one pick per menu) and one per change the game makes by itself
        ahead. unreadable: a write ahead that is not a plain + or -.
        """

        ups = python_list()
        downs = python_list()
        unreadable = False
        for m in menu_order:
            g = menus[id(m)]
            if not (m is current_menu or g[0].status in _URM_AHEAD):
                continue
            per = python_dict()
            for w in g:
                d = _urm_delta(w)
                if d is None:
                    unreadable = True
                    continue
                per[w.option] = per.get(w.option, 0) + d
            best = max(per.values()) if per else 0
            worst = min(per.values()) if per else 0
            if best > 0:
                ups.append(best)
            if worst < 0:
                downs.append(-worst)
        for w in auto:
            if w.status not in _URM_AHEAD:
                continue
            d = _urm_delta(w)
            if d is None:
                unreadable = True
            elif d > 0:
                ups.append(d)
            elif d < 0:
                downs.append(-d)
        return ups, downs, unreadable

    def _urm_reach(need, ups, downs, unreadable):
        """gain / warn / loss / None for a number `need` away (0: it holds)."""

        if need == 0:
            return "gain"
        steps = ups if need > 0 else downs
        need = abs(need)
        total = sum(steps)
        if total >= need:
            if total - min(steps) >= need:
                return "gain"
            return "warn"
        if unreadable:
            return None
        return "loss"

    # ------------------------------------------------------------------
    # Open now, or one step away: the tests a way stands behind as things
    # stand, keyed by the one value it still lacks (map rework 5; the new
    # map's sandbox by place, the user's 4a, 2026-11-23).
    # ------------------------------------------------------------------

    def _urm_one_step(tests):
        """
        tests: the (test, wanted) pairs a way stands behind (wanted True:
        must hold, False: must not). A test wanted to hold whose parts are
        joined by `and` counts as its parts. Each part is asked of
        _urm_truth, the one answer (a flag test is read from its collection,
        never run). ("open", None, None) when every part is met now;
        ("step", key, (test, wanted)) when exactly one is not and it tests
        one value (key: that value, _urm_one_value); ("locked", None, None)
        when two or more are not; None when that cannot be told.
        """

        parts = python_list()
        for test, wanted in tests:
            if test is None:
                return None
            split = _urm_and_parts(test) if wanted else None
            if split:
                parts.extend((part, True) for part in split)
            else:
                parts.append((test, wanted))
        unmet = python_list()
        unknown = False
        for test, wanted in parts:
            holds = _urm_truth(test)
            if holds is None:
                unknown = True
            elif bool(holds) is not bool(wanted):
                unmet.append((test, wanted))
        if len(unmet) >= 2:
            return ("locked", None, None)
        if unknown:
            return None
        if not unmet:
            return ("open", None, None)
        key = _urm_one_value(unmet[0][0])
        if key is None:
            return None
        return ("step", key, unmet[0])

    def _urm_and_parts(test):
        """The parts of a test joined by `and` at its top, as text; None
        when it is not such a test."""

        text = (u"%s" % (test,)).strip()
        try:
            tree = _urmsg_parse(text, "eval")
        except Exception:
            return None
        body = tree.body
        if _urmsg_kind_of(body) != "BoolOp" or _urmsg_kind_of(body.op) != "And":
            return None
        # Python 2's parser gives no end of a part: the text is cut at its
        # top-level "and"s, and taken only when that gives the same parts.
        out = python_list(part.strip() for part in text.split(u" and "))
        if len(out) != len(body.values):
            return None
        for part in out:
            try:
                _urmsg_parse(part, "eval")
            except Exception:
                return None
        return out

    def _urm_one_value(test):
        """The one value a test reads: a store name tested alone or against
        a literal (`love >= 3`, `not met`, `day == 2`), or a flag test the
        flags reading knows (true("x"): that test). None for anything
        else."""

        text = (u"%s" % (test,)).strip()
        try:
            node = _urmsg_parse(text, "eval").body
        except Exception:
            return None
        while _urmsg_kind_of(node) == "UnaryOp" and _urmsg_kind_of(node.op) == "Not":
            node = node.operand
        flag = _urmfl_name_of(node) if _urmsg_kind_of(node) in ("Call", "Compare") else None
        if flag is not None:
            return flag
        name = _urmsg_version_name(node)
        if name is not None:
            return name
        if _urmsg_kind_of(node) != "Compare" or len(node.ops) != 1:
            return None
        left, right = node.left, node.comparators[0]
        name = _urmsg_version_name(left)
        if name is not None and _urmsg_version_lits(right, False) is not None:
            return name
        name = _urmsg_version_name(right)
        if name is not None and _urmsg_version_lits(left, False) is not None:
            return name
        return None
