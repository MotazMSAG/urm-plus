    # ------------------------------------------------------------------
    # Words and tones, part 2: names, values and a test said in words;
    # the map's colours. Moved unchanged from the map (30-34) so the chip
    # needs no map piece (CODE_MAP.md, layers).
    # ------------------------------------------------------------------

    _URMM_TAG = _urmm_re.compile(r"\{[^{}]*\}")
    _URMM_CAMEL_A = _urmm_re.compile(r"([a-z0-9])([A-Z])")
    _URMM_CAMEL_B = _urmm_re.compile(r"([A-Z]+)([A-Z][a-z])")

    def _urmm_pretty(name):
        """Raw variable name with only store./persistent. stripped (DECISIONS
        2026-11-26, 2a: one name everywhere, matching Search and variable sheet)."""

        if name.startswith("persistent."):
            name = name[len("persistent."):]
        if name.startswith("store."):
            name = name[len("store."):]
        return u"%s" % (name,)

    _URMM_STEP = _urmm_re.compile(r"\.([A-Za-z_]\w*)|\[\s*([^\[\]]+?)\s*\]")

    def _urmm_own_name(obj):
        """An object's own name when it is plain words - not a Character's
        "[mc_name]", not text tags, not something that fails to be read."""

        if obj is None:
            return None
        try:
            own = getattr(obj, "name", None)
        except Exception:
            return None
        if not isinstance(own, (str, u"".__class__)):
            return None
        own = own.strip()
        if not own or u"[" in own or u"{" in own or len(own) > 30:
            return None
        return own

    def _urmm_path_words(path):
        """Raw path with only store./persistent. stripped (2a)."""

        if path.startswith("persistent."):
            path = path[len("persistent."):]
        if path.startswith("store."):
            path = path[len("store."):]
        return _urm_clip(path, 48)

    def _urmm_value(text):
        """A literal as a player would say it: "yes" -> yes, True -> on,
        "" -> empty, for example a name the player has not typed."""

        text = text.strip()
        if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
            return text[1:-1] or "empty"
        if text == "True":
            return "true"
        if text == "False":
            return "false"
        if text == "None":
            return "cleared"
        return text

    # A name, or a value reached through a list or a dict:
    # rivals[0].stats['charm'] (Heavenly Vows) - said by _urmm_path_words.
    _URMM_HUMAN = _urmm_re.compile(
        r"^([A-Za-z_][\w.]*(?:\[[^\[\]=]+\][\w.]*)*)\s*(\+=|-=|\*=|/=|=)\s*(.+)$")
    _URMM_NUMBER = _urmm_re.compile(r"^-?\d+(\.\d+)?$")

    def _urmw_names_label(literal):
        """True for a quoted word written in the script that is the name of
        one of its labels: said as written it would put a
        script name on the screen (Being a DIK keeps its events so)."""

        text = (u"%s" % (literal,)).strip()
        while len(text) >= 2 and text[0] in "uUrRbB" and text[1] in "\"'":
            text = text[1:]
        if len(text) < 3 or text[0] != text[-1] or text[0] not in "\"'":
            return False
        try:
            return _urmsg_lookup(text[1:-1]) is not None
        except Exception:
            return False

    # ---- a change as a chip (words, tone)

    def _urmw_value_chip(who, sep, value, tone, with_value):
        prefix = (u"%s%s" % (who, sep)) if who else u""
        words = prefix + value
        if with_value:
            return (words, tone, (len(prefix), len(words)))
        return (words, tone)

    def _urmw_scalar(text):
        try:
            node = _urmsg_parse(text, "eval").body
        except Exception:
            return False, None
        if isinstance(node, _urmsg_ast.UnaryOp) and isinstance(node.op, _urmsg_ast.UAdd):
            ok, value = _urmsg_literal(node.operand)
            return (True, value) if ok and _urm_isnum(value) else (False, None)
        return _urmsg_literal(node)

    def _urmw_hidden_source(value):
        """Use one neutral description wherever a chip knows a script location."""
        if isinstance(value, type(b"")):
            value = value.decode("utf-8", "replace")
        if not isinstance(value, _urmsg_texts) or not value:
            return None
        if _urmsg_lookup(value) is not None:
            return u"a scene"
        if value.lower().endswith((".rpy", ".rpyc", ".rpym", ".rpymc")):
            return u"a script file"
        return None

    def urm_map_chip(text, with_value=False):
        """
        One change as (words, tone). tone is gain, loss, set or other, and
        decides the chip's colour - so "better or worse" reads without
        reading. In core words (from the map, 2026-11-23): every display
        that says a change draws its chip from here.
        """

        m = _URMM_HUMAN.match(text.strip())
        if not m:
            return (_urm_clip(text.strip(), 40), "other")

        name, op, value = m.group(1), m.group(2), m.group(3).strip()
        who = _urmm_path_words(name) if "[" in name else _urmm_pretty(name)
        number = _URMM_NUMBER.match(value) is not None
        negative = number and value.startswith("-")

        if op == "+=":
            if number:
                return _urmw_value_chip(who, " ", ("" if negative else "+") + value,
                                        "loss" if negative else "gain", with_value)
            return ("%s + %s" % (who, _urm_clip(value, 16)), "other")

        if op == "-=":
            if number:
                return _urmw_value_chip(who, " ", value[1:] if negative else "-" + value,
                                        "gain" if negative else "loss", with_value)
            return ("%s - %s" % (who, _urm_clip(value, 16)), "other")

        if op in ("*=", "/="):
            return _urmw_value_chip(who, " ", ("x" if op == "*=" else "/") + _urm_clip(value, 12),
                                    "other", with_value and number)

        literal, scalar = _urmw_scalar(value) if with_value else (False, None)
        if _urmw_names_label(value) or (literal and _urmw_hidden_source(scalar)):
            # A label's name kept in a value (Being a DIK's events): a
            # script name, never said - the change says only what it sets.
            return (who, "set")
        return _urmw_value_chip(who, ": ", _urm_clip(_urmm_value(value), 20), "set", literal)

    _URMM_SAY_OP = python_dict((
        ("==", "is"), ("!=", "is not"), (">=", "is at least"),
        (">", "is over"), ("<=", "is at most"), ("<", "is under"),
    ))

    def urm_map_colour(key):
        """A colour of the displays not yet drawn with the kit (16_kit,
        URMK_OLD_COLOURS); a key it does not know is the words' colour."""

        return URMK_OLD_COLOURS.get(key) or URMK_OLD_COLOURS["ink"]

    # ---- a chip on the route map and the choice cards: the kit's chip (our
    # palette, 16_kit), one look on every ground, the soft pill of the
    # user's pick 1a (2026-11-21), in our colours now (1a, 2026-11-22; light
    # URM themes are not a target). Those two screens still sit on URM's
    # ground and call these names; `loud` (a chip on the map's light "you
    # are here" box) needs nothing of its own any more: the pill is solid.

    def urm_chip_bg(tone, loud=False, faded=False):
        return urmk_pill(urmk_chip_fill(tone, faded), max(4, urmk_px_cut(8)))

    def urm_chip_ink(tone, loud=False, faded=False):
        return urmk_chip_ink(tone, faded)

    _URMM_COND = _urmm_re.compile(
        r"^\s*(not\s+)?([A-Za-z_][\w.]*)\s*(?:(==|!=|>=|<=|>|<)\s*(.+?))?\s*$")

    # ---- a test in words: the one place every display takes them from

    def _urmw_match(text, quoted=False):
        """_URMM_COND on one plain test, or None for anything it would
        misread (a call, a second test hiding in the value)."""

        text = text.strip()
        m = _URMM_COND.match(text)
        if not m or (m.group(1) and m.group(3)):
            return None
        if m.group(2) in ("True", "False", "None", "not"):
            return None
        if quoted and m.group(3):
            try:
                node = _urmsg_parse(text, "eval").body
            except Exception:
                return None
            if not isinstance(node, _urmsg_ast.Compare):
                return None
        if "(" in text or " and " in text or " or " in text:
            if not quoted or not m.group(3) or not _urmw_scalar(m.group(4))[0]:
                return None
        return m

    def _urmw_simple(text, was=False):
        """'carol_love >= 3' -> 'Carol love is at least 3'; None if not
        plain, or when the value is a label's name (_urmw_names_label)."""

        m = _urmw_match(text)
        if m is None:
            return None
        who = _urmm_pretty(m.group(2))
        if m.group(3):
            if _urmw_names_label(m.group(4)):
                return None
            said = _URMM_SAY_OP.get(m.group(3))
            if was:
                said = "was" + said[2:]
            return "%s %s %s" % (who, said, _urmm_value(m.group(4)))
        return "%s %s %s" % (who, "was" if was else "is", "false" if m.group(1) else "true")

    _URMW_FLIP = python_dict((
        ("==", "!="), ("!=", "=="), (">=", "<"), ("<", ">="),
        (">", "<="), ("<=", ">"),
    ))

    def _urmw_not(text):
        """The opposite of one plain test, as a test; None if not plain."""

        m = _urmw_match(text)
        if m is None:
            return None
        if m.group(3):
            return "%s %s %s" % (m.group(2), _URMW_FLIP[m.group(3)], m.group(4))
        return m.group(2) if m.group(1) else "not " + m.group(2)

    def _urmw_dice(text):
        return "renpy.random" in text or "random." in text

    # A test of the device the game runs on (Summer with Mia's
    # `if renpy.variant("pc"):`): the engine's fixed answer, worked out like
    # a plain test (_urm_calls, 13_now). Said for the names a player knows;
    # any other stays unsaid.
    _URMW_VARIANT = _urmm_re.compile(
        r"""^\s*(not\s+)?renpy\.variant\(\s*(?:"(\w+)"|'(\w+)')\s*\)\s*$""")
    _URMW_DEVICES = python_dict((
        ("pc", "a PC"), ("mobile", "a phone or tablet"), ("android", "Android"),
        ("ios", "iOS"), ("touch", "a touch screen"), ("web", "the web"),
        ("tablet", "a tablet"), ("phone", "a phone"), ("tv", "a TV"),
    ))

    def _urmw_device(text):
        """'renpy.variant("pc")' -> 'on a PC', 'not renpy.variant("pc")' ->
        'not on a PC'; None for any other test."""

        m = _URMW_VARIANT.match(text)
        if m is None:
            return None
        device = _URMW_DEVICES.get(m.group(2) or m.group(3))
        if device is None:
            return None
        return ("not on " if m.group(1) else "on ") + device

    def _urmw_one(text, was=False, flags=False):
        """One part of a test in words: a plain test (_urmw_simple), or with
        flags a flag test (_urmw_flag); None for any other call or shape."""

        if flags:
            said = _urmw_flag(text, was)
            if said is not None:
                return said
        if "(" in text:
            return None
        return _urmw_simple(text, was)

    def _urmw_flag_parts(text):
        """(pretty_name, wanted) for a flag test the flags reading knows,
        or None for any other test."""

        try:
            node = _urmsg_parse((u"%s" % (text,)).strip(), "eval").body
        except Exception:
            return None
        on = True
        while _urmsg_kind_of(node) == "UnaryOp" and _urmsg_kind_of(node.op) == "Not":
            on = not on
            node = node.operand
        kind = _urmsg_kind_of(node)
        try:
            if kind not in ("Call", "Compare") or _urmfl_name_of(node) is None:
                return None
        except Exception:
            return None
        if kind == "Call":
            word = _urmsg_version_lits(node.args[0], False)
        else:
            word = _urmsg_version_lits(node.left, False)
            if _urmsg_kind_of(node.ops[0]) == "NotIn":
                on = not on
        if not word or not isinstance(word[0], _urmsg_texts) or _urmsg_lookup(word[0]) is not None:
            # (A flag's word that is a label's name is never said.)
            return None
        return (_urmm_pretty(word[0]), on)

    def _urmw_flag(text, was=False):
        """A flag test the flags reading knows (61, _urmfl_name_of), said as
        its word: 'true("ch6_kim_accept")' -> 'Ch6 kim accept is on',
        'not true("x")' -> 'X is off'; None for any other test (nothing is
        guessed from a function's name)."""

        parts = _urmw_flag_parts(text)
        if parts is None:
            return None
        return u"%s %s %s" % (parts[0], "was" if was else "is", "true" if parts[1] else "false")

    def urm_need_chip(cond, holds=None, named=True, with_value=False):
        """One compact (words, tone) chip for what a test asks and where
        the player stands: 'Rae love 2/3' red while short, green when met;
        'Orphan: true' green when holding, 'Nadia alive: false' red when
        failing (flipped for negative tests); or None when not plain."""

        text = (u"%s" % (cond,)).strip() if cond else u""
        if not text:
            return None
        m = _urmw_match(text, quoted=with_value)
        if m is not None:
            neg, name, op, literal = m.group(1), m.group(2), m.group(3), m.group(4)
            who = _urmm_pretty(name)
            lit = literal.strip() if op else u""
            if op in _URM_GOAL_NEED and _URMM_NUMBER.match(lit) is not None:
                known, now = _urm_now(name)
                if not known or not _urm_isnum(now):
                    return None
                lit_val = float(lit) if "." in lit else int(lit)
                if holds is None:
                    holds = _urm_truth(text)
                tone = "gain" if holds is True else ("loss" if holds is False else "plain")
                goal = urm_goal(name, op, lit_val)
                if goal is None:
                    return None
                return _urmw_value_chip(who if named else None, " ", goal, tone, with_value)
            if op == "==" and _URMM_NUMBER.match(lit) is not None:
                known, now = _urm_now(name)
                if known and _urm_isnum(now) and not isinstance(now, bool):
                    if holds is None:
                        holds = _urm_truth(text)
                    if holds is not None:
                        lit_val = float(lit) if "." in lit else int(lit)
                        ratio = u"%s/%s" % (_urm_number(now), _urm_number(lit_val))
                        return _urmw_value_chip(who if named else None, ": ", ratio,
                                                "gain" if holds else "loss", with_value)
            if op is None or (op in ("==", "!=") and lit in ("True", "False")):
                known, _now = _urm_now(name)
                if not known:
                    return None
                wanted = (not bool(neg)) if op is None else ((lit == "True") == (op == "=="))
                if holds is None:
                    holds = _urm_truth(text)
                if holds is None:
                    return None
                is_true = (bool(holds) == wanted)
                val_word = u"true" if is_true else u"false"
                tone = "gain" if holds else "loss"
                return _urmw_value_chip(who if named else "you", ": ", val_word, tone, with_value)
            if _urmw_names_label(literal):
                return None
            if with_value and ('"' in literal or "'" in literal) and _urmw_hidden_source(_urmw_scalar(literal)[1]):
                return None
            known, now = _urm_now(name)
            if holds is None:
                holds = _urm_truth(text)
            if not known or holds is None:
                return None
            hidden = _urmw_hidden_source(now) if with_value else None
            if hidden:
                val = hidden
            elif now is None:
                val = u"cleared"
            elif isinstance(now, bool):
                val = u"true" if now else u"false"
            elif isinstance(now, ("".__class__, u"".__class__)):
                val = now or u"empty"
            elif _urm_isnum(now):
                val = _urm_number(now)
            elif with_value:
                return None
            else:
                val = _urm_clip(u"%r" % (now,), 24)
            return _urmw_value_chip(who if named else "you", ": ", val,
                                    "gain" if holds else "loss", with_value and not hidden)
        parts = _urmw_flag_parts(text)
        if parts is not None:
            who, wanted = parts
            if holds is None:
                holds = _urm_truth(text)
            if holds is None:
                return None
            is_true = (bool(holds) == wanted)
            val_word = u"true" if is_true else u"false"
            tone = "gain" if holds else "loss"
            return _urmw_value_chip(who if named else "you", ": ", val_word, tone, with_value)
        return None

    import io as _urmw_io
    import tokenize as _urmw_tokenize
    _URMW_BOOL_WORD = _urmm_re.compile(r"\b(?:and|or)\b")

    def _urmw_corner_condition(text):
        """Read the top-level boolean words; keep literals and nested groups intact."""

        if "\n" in text:
            return None, None
        if not _URMW_BOOL_WORD.search(text):
            return (text,), None
        parts = python_list()
        depth = start = 0
        try:
            node = _urmsg_parse(text, "eval").body
            if not isinstance(node, _urmsg_ast.BoolOp):
                return (text,), None
            joiner = "and" if isinstance(node.op, _urmsg_ast.And) else "or"
            for kind, token, position, end, _line in _urmw_tokenize.generate_tokens(_urmw_io.StringIO(text).readline):
                if kind == _urmw_tokenize.OP:
                    if token in ("(", "[", "{"):
                        depth += 1
                    elif token in (")", "]", "}"):
                        depth -= 1
                elif kind == _urmw_tokenize.NAME and not depth and token in ("and", "or"):
                    if token != joiner:
                        return None, None
                    parts.append(text[start:position[1]].strip())
                    start = end[1]
        except (_urmw_tokenize.TokenError, SyntaxError):
            return None, None
        parts.append(text[start:].strip())
        if len(parts) != len(node.values):
            return None, None
        return parts, joiner

    _URMW_RANDOM_RESULTS = frozenset((
        "random", "randint", "randrange", "uniform", "choice", "choices", "sample",
        "getrandbits", "randbytes", "triangular", "gauss", "normalvariate",
        "lognormvariate", "expovariate", "vonmisesvariate", "gammavariate",
        "betavariate", "paretovariate", "weibullvariate", "binomialvariate"))

    def _urmw_corner_chance(node):
        """Recognize result-producing RNG calls without running them."""
        calls = tuple(_urmsg_call_name(child) for child in _urmsg_ast.walk(node)
                      if _urmsg_kind_of(child) == "Call")
        if not calls:
            return False
        for name in calls:
            group, _dot, method = (name or "").rpartition(".")
            if group not in ("random", "renpy.random") or method not in _URMW_RANDOM_RESULTS:
                return False
        return True

    def _urmw_corner_leaf(node):
        if isinstance(node, _urmsg_ast.IfExp):
            return u"a game check"
        literal, constant = _urmsg_literal(node)
        if literal and isinstance(constant, bool):
            return u"true" if constant else u"false"
        text = _urmsg_unparse(node)
        m = _urmw_match(text, quoted=True) if text else None
        if m is None:
            return u"by chance" if _urmw_corner_chance(node) else u"a game check"
        who, op = _urmm_pretty(m.group(2)), m.group(3)
        if not op:
            return u"%s is %s" % (who, u"false" if m.group(1) else u"true")
        ok, value = _urmsg_literal(node.comparators[0])
        if not ok:
            return u"a game check"
        hidden = _urmw_hidden_source(value)
        if hidden:
            value = hidden
        elif isinstance(value, _urmsg_texts):
            value = (u"\u201c%s\u201d" % value) if value else u"empty"
        else:
            value = _urmm_value(u"%s" % (value,))
        return u"%s %s %s" % (who, _URMM_SAY_OP[op], value)

    def _urmw_corner_group(node, depth=0):
        if depth > 4:
            return None
        kind = _urmsg_kind_of(node)
        if kind == "BoolOp":
            if len(node.values) > 16:
                return None
            parts = tuple(_urmw_corner_group(part, depth + 1) for part in node.values)
            if any(part is None for part in parts):
                return None
            joiner = u" and\u00a0" if _urmsg_kind_of(node.op) == "And" else u" or\u00a0"
            words = joiner.join(parts)
            return u"(%s)" % words if depth else words
        if (kind == "UnaryOp" and _urmsg_kind_of(node.op) == "Not"
                and _urmsg_kind_of(node.operand) not in ("Name", "Attribute")):
            part = _urmw_corner_group(node.operand, depth + 1)
            if part is None or part == u"by chance":
                return part
            return u"not\u00a0%s" % part if part.startswith("(") else u"not\u00a0(%s)" % part
        return _urmw_corner_leaf(node)

    def _urmw_corner_fallback(text):
        """One bounded, grouped summary, even when an operand is opaque."""

        device = _urmw_device(text)
        if device is not None:
            return device[:1].upper() + device[1:]
        try:
            node = _urmsg_parse(text, "eval").body
            words = _urmw_corner_group(node)
        except Exception:
            words = None
        if words is None or len(words) > 144:
            return u"Depends on a game check"
        if words in (u"by chance", u"a game check"):
            return words[:1].upper() + words[1:]
        return words

    def urm_need_chips(cond, holds=None, named=True, joiners=False, with_value=False):
        """A list of (words, tone, key) chips for one plain test or an
        `and`/`or`-chain of plain tests (up to 4 parts), so compound checks
        like `not a and b` yield one clickable chip per variable. With
        joiners=True, interleaves (joiner, 'join', None) items."""

        text = (u"%s" % (cond,)).strip() if cond else u""
        if not text:
            return python_list()
        if with_value:
            parts, joiner = _urmw_corner_condition(text)
            if parts is None:
                return python_list()
        else:
            has_and = " and " in text
            has_or = " or " in text
            if (has_or and not joiners) or (has_and and has_or):
                return python_list()
            joiner = " and " if has_and else (" or " if has_or else None)
            parts = text.split(joiner) if joiner else [text]
        if len(parts) > 4:
            return python_list()
        if not with_value and len(parts) > 1 and any(p.count('"') % 2 or p.count("'") % 2 or p.count("(") != p.count(")") for p in parts):
            return python_list()
        out = python_list()
        for idx, part in enumerate(parts):
            chip = urm_need_chip(part, holds=holds if len(parts) == 1 else None,
                                 named=named or len(parts) > 1, with_value=with_value)
            if chip is None:
                return python_list()
            if joiners and len(parts) > 1 and idx > 0:
                out.append((u"%s" % (joiner.strip(),), "join", None))
            m = _urmw_match(part, quoted=with_value)
            raw_name = m.group(2) if m is not None else None
            norm_name = None
            if raw_name is not None:
                try:
                    norm_name = _urmsg_name(_urmsg_ast.parse(raw_name.strip(), mode="eval").body)
                except Exception:
                    norm_name = None
                if norm_name is None:
                    norm_name = raw_name[6:] if raw_name.startswith("store.") else raw_name
            out.append((chip[0], chip[1], norm_name) + chip[2:])
        return out

    def _urmw_say(cond, was=False, flags=False):
        """
        A test in words: one plain test, two joined by "and", or the part of
        an "or" that holds now. "by chance" for dice. None when it cannot be
        said in words - never code on the chip. flags: a flag test the flags
        reading knows is said as its word too (the new map's; today's
        displays do not ask it, so what they say is as it was).
        """

        text = (u"%s" % (cond,)).strip()
        if _urmw_dice(text):
            return "by chance"
        device = _urmw_device(text)
        if device is not None:
            return device
        if " or " in text:
            if " and " in text:
                return None
            for part in text.split(" or "):
                said = _urmw_one(part, was, flags)
                if said is None:
                    return None
                if _urm_truth(part) is True:
                    return said
            return None
        parts = text.split(" and ")
        if len(parts) > 2:
            return None
        said = None
        for part in parts:
            one = _urmw_one(part, was, flags)
            if one is None:
                return None
            said = one if said is None else said + " and " + one
        return said

