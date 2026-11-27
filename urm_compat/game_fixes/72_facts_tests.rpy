    # ------------------------------------------------------------------
    # Facts, part 2: the names a test reads, the scene a statement is in.
    # Moved unchanged from the variable window (70) so the gallery and the
    # alerts need no panel piece (CODE_MAP.md, layers).
    # ------------------------------------------------------------------

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

