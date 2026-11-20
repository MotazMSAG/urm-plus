    # ------------------------------------------------------------------
    # The panel
    # ------------------------------------------------------------------

    class _URMPanel(python_object):
        def __init__(self, name):
            self.name = name
            self.state = "ready"
            self.pct = None
            self.message = None
            self.answer = python_list()
            self.now_header = None
            self.now_lines = python_list()
            self.later = python_list()
            self.warnings = python_list()
            self.okline = None
            self.tabs = python_list()
            self.tab = "gives"
            self.blocks = python_list()
            self.gives_tail = python_list()
            self.choices = python_list()
            self.choices_tail = python_list()
            self.details = python_list()
            self.detail_checks = python_list()
            self.footer = python_list()
            self.next_line = None
            self.next_value = _URMP_NOSET
            self.deps = None
            self.mode = None

    class _URMPBlock(python_object):
        def __init__(self, header, value=None, sub=None):
            self.header = header
            self.value = _URMP_NOSET if value is None else value
            self.sub = sub
            self.rows = python_list()
            self.small = python_list()
            self.marker = False
            self.key = header

    def _urmp_row_view(index, r, name, now, cur, seen, budget):
        """The drawable form of a row: status, head, quote, extra lines, code."""

        if not hasattr(r, "summary"):
            r.summary = _urmp_summary(r.block, budget, 6)
            r.other_summary = _urmp_summary(r.other, budget, 3) if r.other else None
        s = r.summary
        r.status = _urmp_status(r.label, r.file, r.line, s.first_node, cur, seen)
        r.weight = _urmp_weight(s, index, budget)
        r.size = _urmp_size_words(s, index, budget)

        head = u"%s  \u00b7  %s" % (r.scene, r.size)
        if r.kind == "option":
            quote = u'the choice "%s" appears' % _urmp_plain(r.option, 80)
        elif r.kind == "loop":
            quote = "repeats while this holds"
        elif s.first:
            quote = s.first
        elif s.target:
            quote = None
        else:
            quote = None

        extra = python_list()
        _tree, _mine, others = _urmp_atoms(r.cond, name)
        r.needs_unmet = python_list()
        for atom in others[:3]:
            words, met = _urmp_need(atom)
            extra.append(u"also needs %s" % words)
            if met is not True:
                r.needs_unmet.append(words)
        if r.other_summary is not None:
            o = r.other_summary
            if o.lines or o.target or o.calls:
                text = u"otherwise: %s" % _urmp_size_words(o, index, budget)
                if o.first:
                    text += u" - %s" % o.first
                extra.append(text)
            for w in o.writes:
                if w[0] == name:
                    extra.append(u"and otherwise the game %s here" % _urmp_write_words(w)[1:-1])
                    break

        r.view_status = _URMP_STATUS_TEXT.get(r.status, "")
        r.view_head = head
        r.view_quote = quote
        r.view_extra = extra
        r.view_lines = s.preview
        r.view_replay = r.label if isinstance(r.label, _urmi_text) and r.label in index.labels else None
        r.key = "%s:%s:%s" % (r.file, r.line, r.cond)
        r.view_code = _urmp_code(r)
        return r

    def _urmp_stmt_code(node, indent, out, limit):
        ast = renpy.ast
        pad = "    " * indent
        if len(out) >= limit:
            return
        if isinstance(node, ast.Translate):
            for child in node.block or ():
                _urmp_stmt_code(child, indent, out, limit)
        elif isinstance(node, ast.Say):
            who = getattr(node, "who", None)
            what = (getattr(node, "what", "") or "").replace("\n", " ")
            if len(what) > 120:
                what = what[:117] + "..."
            out.append(u'%s%s"%s"' % (pad, (who + " ") if who else "", what))
        elif isinstance(node, (ast.Show, ast.Scene)) and getattr(node, "imspec", None):
            out.append(u"%s%s %s" % (pad, type(node).__name__.lower(), " ".join(node.imspec[0])))
        elif isinstance(node, ast.Python):
            source = getattr(getattr(node, "code", None), "source", "") or ""
            for line in source.split("\n")[:4]:
                out.append(u"%s$ %s" % (pad, line.strip()))
        elif isinstance(node, ast.Jump):
            out.append(u"%sjump %s" % (pad, node.target))
        elif isinstance(node, ast.Call):
            out.append(u"%scall %s" % (pad, node.label))
        elif isinstance(node, ast.If):
            for i, (cond, block) in enumerate(node.entries):
                if i == 0:
                    out.append(u"%sif %s:" % (pad, cond))
                elif cond.strip() == "True":
                    out.append(u"%selse:" % pad)
                else:
                    out.append(u"%selif %s:" % (pad, cond))
                for child in (block or ())[:3]:
                    _urmp_stmt_code(child, indent + 1, out, limit)
        elif isinstance(node, ast.Menu):
            out.append(u"%smenu:" % pad)
            for item in node.items:
                if item[2] is not None:
                    out.append(u'%s    "%s"%s:' % (pad, item[0], "" if item[1] in (None, "True") else " if " + item[1]))
        elif isinstance(node, ast.Return):
            out.append(u"%sreturn" % pad)

    def _urmp_code(r):
        out = python_list()
        out.append(u"# %s, %s line %s" % (r.scene, (r.file or "?").split("/")[-1], r.line))
        if r.kind == "option":
            out.append(u"menu:")
            out.append(u'    "%s" if %s:' % (r.option, r.cond))
            for child in (r.block or ())[:14]:
                _urmp_stmt_code(child, 2, out, 18)
        elif r.kind == "loop":
            out.append(u"while %s:" % r.cond)
            for child in (r.block or ())[:12]:
                _urmp_stmt_code(child, 1, out, 16)
        else:
            out.append(u"if %s:" % r.cond)
            for child in (r.block or ())[:12]:
                _urmp_stmt_code(child, 1, out, 16)
            if r.other is not None:
                out.append(u"else:")
                for child in (r.other or ())[:6]:
                    _urmp_stmt_code(child, 1, out, 24)
            elif r.other_kind == "elif":
                out.append(u"elif ...")
        return u"\n".join(out)

    def _urmp_sort(rows):
        rows.sort(key=lambda r: (_URMP_STATUS_RANK.get(r.status, 4), -r.weight))
        return rows

    def _urmp_fill_block(block, rows):
        """Big rows shown, small ones (3 lines or fewer) folded per scene."""

        for r in _urmp_sort(rows):
            if r.weight <= 3 and r.kind != "option" and not r.needs_unmet:
                block.small.append(r)
            else:
                block.rows.append(r)
        if not block.rows and block.small:
            block.rows = block.small
            block.small = python_list()

    def _urmp_small_line(block):
        if not block.small:
            return None
        scenes = python_list()
        never = 0
        for r in block.small:
            if r.scene not in scenes:
                scenes.append(r.scene)
            if r.status in ("not", "never"):
                never += 1
        text = u"+ %d small change%s (3 lines or fewer) in %s" % (
            len(block.small), "" if len(block.small) == 1 else "s",
            ", ".join(u"%s" % s for s in scenes[:3]) + (" and more" if len(scenes) > 3 else ""))
        if never:
            text += u" - %d not seen" % never
        return text

    def _urmp_mode(index, name, now):
        reads = index.reads.get(name) or ()
        boolish = 0
        nums = 0
        texts = 0
        for _s, op, lit in reads:
            if op in ("truthy", "falsy") or lit is True or lit is False:
                boolish += 1
            elif _urmp_isnum(lit):
                nums += 1
            elif isinstance(lit, _urmi_text) and op in ("==", "!="):
                texts += 1
        total = max(len(reads), 1)
        if isinstance(now, bool):
            return "bool"
        if (now is _URMP_UNK or now in (0, 1)) and boolish * 10 > total * 6 and not nums:
            return "bool"
        if _urmp_isnum(now) or (now is _URMP_UNK and nums >= texts and nums):
            return "number"
        if isinstance(now, _urmi_text) or (now is _URMP_UNK and texts):
            return "value"
        return "generic"

    def urm_panel(name):
        """Everything the variable panel draws, cached per name, value and position."""

        state, pct = urm_index_status()
        if state != "ready":
            p = _URMPanel(name)
            p.state = state
            p.pct = pct
            if state == "building":
                p.message = "Reading the game's script... %s%%. This fills in when it's done." % (pct or 0)
            elif state == "failed":
                p.message = "Couldn't read the game's script, so this can't show what %s does." % name
            else:
                p.message = None
            return p

        index = _urmi_index()
        now = _urmp_value(name)
        cur = _urmp_current(index)
        try:
            lang = _preferences.language
        except Exception:
            lang = None
        try:
            shown = repr(now)[:120]
        except Exception:
            shown = "?"
        key = (id(index), index.finished_at, name, shown, cur[0] if cur else None, lang)
        cache = _urmp_bucket("panels")
        found = cache.get(key)
        if found is not None and _urmp_deps_hold(found.deps):
            return found
        # Per-open caches: words like "(with hard_love at 30 now)" and
        # speaker names depend on values that may have changed since.
        st = _urmp_state()
        st["req"] = python_dict()
        st["speakers"] = python_dict()
        st["deps"] = python_dict()
        try:
            p = _urmp_compose(index, name, now, cur)
            p.deps = st["deps"]
        except Exception as error:
            p = _URMPanel(name)
            p.state = "failed"
            p.message = "The panel hit a problem reading %s (%s). URM's own editor above still works." % (
                name, _urmp_plain(u"%s: %s" % (type(error).__name__, error), 120))
            import traceback
            traceback.print_exc()
        st["deps"] = None
        if len(cache) >= 8:
            cache.clear()
        cache[key] = p
        return p

    def _urmp_deps_hold(deps):
        """The values a cached panel was worked out from are still the same."""

        if not deps:
            return True
        for dep, value in deps.items():
            current = _urmp_value(dep)
            if current is _URMP_UNK or type(current) is not type(value) or current != value:
                return False
        return True

    def _urmp_compose(index, name, now, cur):
        p = _URMPanel(name)
        budget = python_list()
        budget.append(_URMP_NODE_BUDGET)
        seen = _URMPSeen()
        mode = _urmp_mode(index, name, now)
        p.mode = mode
        boolish = mode == "bool"
        on_value, off_value = True, False
        if boolish and _urmp_isint(now):
            on_value, off_value = 1, 0

        def onoff(v):
            return "ON" if v else "OFF"

        rows = _urmp_rows(index, name)
        writes = _urmp_writes(index, name)
        funcs = _urmp_function_mentions(name)
        mass = _urmp_mass_labels(index) if writes else python_set()

        if now is _URMP_UNK:
            now_words = "not set yet"
        elif boolish:
            now_words = onoff(now)
        else:
            now_words = _urmp_plain(_urmi_show(now), 60)

        # --- edge states -------------------------------------------------
        if not rows and not writes:
            if funcs:
                p.message = (u"The story script never uses %s directly. The game's own code mentions it in %s. "
                             u"What that code does with it isn't shown." % (name, ", ".join("%s()" % f for f in funcs[:3])))
            else:
                p.message = (u"The story script never checks or sets %s by name. "
                             u"It may still be used in the game's screens or its own code." % name)
            return p

        for r in rows:
            _urmp_row_view(index, r, name, now, cur, seen, budget)

        loops = [r for r in rows if r.kind == "loop"]
        rows = [r for r in rows if r.kind != "loop"]

        # Identical outcomes (281 x "jump resetGalleryVar") collapse to one line.
        groups = python_dict()
        for r in rows:
            s = r.summary
            if s.lines or s.choice or r.kind == "option":
                continue
            if s.target:
                sig = u"goes to %s" % s.target
            elif s.calls:
                sig = u"plays %s" % s.calls[0]
            elif s.funcs:
                sig = u"runs the game's code (%s)" % s.funcs[0]
            elif s.writes:
                sig = _urmp_write_words(s.writes[0])[1:-1]
            else:
                continue
            groups.setdefault((r.cond, sig), python_list()).append(r)
        collapsed = python_set()
        collapse_lines = python_list()
        biggest_group = None
        for (cond, sig), members in groups.items():
            if len(members) < 5:
                continue
            for r in members:
                collapsed.add(id(r))
            scenes = python_set()
            for r in members:
                scenes.add(r.scene)
            req = _urmp_requirement(members[0], name, now)[0]
            line = u"In %d places in %d scene%s: when it is %s \u2192 the game %s (no dialogue)." % (
                len(members), len(scenes), "" if len(scenes) == 1 else "s", req, sig)
            collapse_lines.append(line)
            if biggest_group is None or len(members) > biggest_group[0]:
                biggest_group = (len(members), req, sig)
        shown_rows = [r for r in rows if id(r) not in collapsed]

        # Rows that only change other values, with no dialogue at all.
        quiet = [r for r in shown_rows if not r.summary.lines and not r.summary.target
                 and not r.summary.calls and not r.summary.choice and r.kind != "option"
                 and not r.summary.pictures]
        quiet_ids = python_set(id(r) for r in quiet)
        shown_rows = [r for r in shown_rows if id(r) not in quiet_ids]

        # --- writers -----------------------------------------------------
        menus = python_dict()
        menu_order = python_list()
        auto = python_list()
        mass_hidden = python_dict()
        for w in writes:
            w.status = _urmp_status(w.label, w.file, w.line, None, cur, seen)
            if w.menu is not None:
                # An option that names the variable itself - "set
                # switch_213 to True" - is the game's own scene-select or
                # cheat menu, not a story choice.
                if w.scene in mass or name.lower() in (u"%s" % (w.option,)).lower():
                    mass_hidden.setdefault(w.scene, python_list()).append(w)
                    continue
                g = menus.get(id(w.menu))
                if g is None:
                    g = python_list()
                    menus[id(w.menu)] = g
                    menu_order.append(w.menu)
                g.append(w)
            else:
                auto.append(w)

        current_menu = None
        if cur is not None:
            for m in menu_order:
                if id(m) == cur[4]:
                    current_menu = m
            for r in rows:
                if r.kind == "option" and id(r.node) == cur[4]:
                    current_menu = r.node

        choice_count = len(menu_order)
        option_count = 0
        for m in menu_order:
            options = python_set()
            for w in menus[id(m)]:
                options.add(w.option)
            option_count += len(options)

        # --- A. the answer -----------------------------------------------
        ahead = [r for r in shown_rows if r.status in ("later", "not")]
        A = p.answer

        if biggest_group is not None and biggest_group[0] * 10 >= len(rows) * 8:
            A.append(u"%s is %s. Almost every check (%d of %d) does the same thing: when it is %s, the game %s (no dialogue)." % (
                name, now_words, biggest_group[0], len(rows), biggest_group[1], biggest_group[2]))
        elif mode == "bool":
            on_rows = python_list()
            off_rows = python_list()
            both = python_list()
            for r in shown_rows:
                _t, mine, _o = _urmp_atoms(r.cond, name)
                on = all(_urmp_ev(a, name, on_value) is True for a in mine) if mine else False
                off = all(_urmp_ev(a, name, off_value) is True for a in mine) if mine else False
                if on == off:
                    r.side = None
                    both.append(r)
                    continue
                r.side = "on" if on else "off"
                if r.other_summary is not None and r.other_summary.lines:
                    both.append(r)
                elif on:
                    on_rows.append(r)
                else:
                    off_rows.append(r)
            on_lines = sum(r.weight for r in on_rows)
            off_lines = sum(r.weight for r in off_rows)
            text = u"%s is %s." % (name, now_words)
            if on_rows:
                text += u" ON plays something extra in %d place%s (about %d lines)." % (
                    len(on_rows), "" if len(on_rows) == 1 else "s", on_lines)
            if off_rows:
                text += u" OFF has its own lines in %d place%s (about %d lines)." % (
                    len(off_rows), "" if len(off_rows) == 1 else "s", off_lines)
            diff = [r for r in both if r.side is not None]
            if diff:
                text += u" Different version either way: %d place%s." % (len(diff), "" if len(diff) == 1 else "s")
            A.append(text)
            big = None
            for r in on_rows + off_rows:
                if r.needs_unmet and r.weight >= 100 and (big is None or r.weight > big.weight):
                    big = r
            if big is not None:
                A.append(u"The biggest (about %d lines, %s) also needs %s." % (big.weight, big.scene, big.needs_unmet[0]))

            sub_on = _urmp_choice_hint(writes, on_value, mass)
            sub_off = _urmp_choice_hint(writes, off_value, mass)
            b = _URMPBlock(u"ONLY WITH ON  (%d place%s, about %d lines)" % (len(on_rows), "" if len(on_rows) == 1 else "s", on_lines), on_value, sub_on)
            _urmp_fill_block(b, on_rows)
            if on_rows:
                p.blocks.append(b)
            b = _URMPBlock(u"ONLY WITH OFF  (%d place%s, about %d lines)" % (len(off_rows), "" if len(off_rows) == 1 else "s", off_lines), off_value, sub_off)
            _urmp_fill_block(b, off_rows)
            if off_rows:
                p.blocks.append(b)
            if diff:
                b = _URMPBlock(u"A DIFFERENT VERSION EITHER WAY  (%d place%s)" % (len(diff), "" if len(diff) == 1 else "s"))
                for r in diff:
                    o = r.other_summary
                    side = "ON" if r.side == "on" else "OFF"
                    other = "OFF" if r.side == "on" else "ON"
                    r.view_head = u"%s  \u00b7  %s: %s / %s: %s" % (
                        r.scene, side, r.size, other, _urmp_size_words(o, index, budget))
                    r.view_quote = u"%s: %s" % (side, r.summary.first or "(no dialogue)")
                    keep = python_list()
                    keep.append(u"%s: %s" % (other, o.first or "(no dialogue)"))
                    for e in r.view_extra:
                        if not e.startswith("otherwise:"):
                            keep.append(e)
                    r.view_extra = keep
                    r.weight = max(r.weight, _urmp_weight(o, index, budget))
                _urmp_fill_block(b, diff)
                p.blocks.append(b)
            rest = [r for r in both if r.side is None]
            if rest:
                b = _URMPBlock(u"CHECKED TOGETHER WITH OTHER THINGS  (%d)" % len(rest))
                for r in rest:
                    r.view_extra.insert(0, u"when %s" % _urmp_cond_words(r.cond))
                _urmp_fill_block(b, rest)
                p.blocks.append(b)

        elif mode == "number":
            ladder = python_dict()
            exact_only = True
            numeric_seen = False
            rival = 0
            for r in shown_rows:
                words, value, sort = _urmp_requirement(r, name, now)
                if sort is not None:
                    numeric_seen = True
                    if not words.startswith("exactly"):
                        exact_only = False
                relative = None
                if "(with " in words:
                    exact_only = False
                    words, relative = words.split(" (with ", 1)
                    relative = u"with " + relative[:-1]
                b = ladder.get(words)
                if b is None:
                    b = _URMPBlock(words, value)
                    b.sort = sort
                    b.relative = python_list()
                    ladder[words] = b
                if relative and relative not in b.relative:
                    b.relative.append(relative)
                    b.sub = u"; ".join(b.relative[:2]) + (
                        u" - it moves when that changes" if len(b.relative) == 1 else u" - it moves when those change")
                if relative:
                    rival += 1
                b.rows.append(r)
            blocks = python_list(ladder.values())
            for b in blocks:
                members = b.rows
                b.rows = python_list()
                _urmp_fill_block(b, members)
            blocks.sort(key=lambda b: (b.sort is None, b.sort if b.sort is not None else 0,
                                       0 if b.header.startswith("exactly") else 1, b.header))
            if _urmp_isnum(now):
                marker = _URMPBlock(u"\u2500\u2500  you: %s  \u2500\u2500" % _urmi_show(now))
                marker.marker = True
                pos = 0
                for i, b in enumerate(blocks):
                    if b.sort is not None and b.sort <= now:
                        pos = i + 1
                blocks.insert(pos, marker)
            p.blocks = blocks

            reqs = [b.header for b in blocks if not b.marker and b.sort is not None]
            if exact_only and numeric_seen and len(reqs) >= 2:
                nums = [_urmi_show(b.sort) for b in blocks if not b.marker and b.sort is not None]
                text = u"%s is %s. The game only checks exact numbers: %s. Any other number matches nothing." % (
                    name, now_words, _urmp_some(nums, 10))
            elif rival * 2 > max(len(shown_rows), 1):
                others = python_list()
                for _s, _op, other in index.rivals.get(name) or ():
                    tree = _urmp_parse(other)
                    if tree is None:
                        continue
                    for n in _urmp_names_in(tree):
                        if n != name and n not in others:
                            others.append(n)
                parts = python_list()
                for n in others[:2]:
                    v = _urmp_value(n)
                    parts.append(u"%s (now %s)" % (_urmp_link(n), "?" if v is _URMP_UNK else _urmp_plain(_urmi_show(v), 20)))
                text = u"%s is %s. It is mostly compared with %s, not with fixed numbers." % (
                    name, now_words, " and ".join(parts) if parts else "other values")
                bands = [b.header for b in blocks if not b.marker]
                if bands:
                    text += u" With those values, the numbers that change something are: %s." % _urmp_some(bands, 6)
            else:
                text = u"%s is %s. The numbers that change something: %s." % (
                    name, now_words, _urmp_some([b.header for b in blocks if not b.marker], 6) or "none found")
            A.append(text)
            if exact_only and numeric_seen:
                p.gives_tail.append("Any number not listed matches nothing.")

            # The NEXT helper: the smallest requirement still ahead, and the
            # choices in that same scene that come before it.
            nxt = None
            if _urmp_isnum(now):
                for b in blocks:
                    if b.marker or b.sort is None or b.sort <= now:
                        continue
                    for r in b.rows + b.small:
                        if r.status in ("later", "not"):
                            if nxt is None or (b.sort, -r.weight) < (nxt[0].sort, -nxt[1].weight):
                                nxt = (b, r)
            if nxt is not None:
                b, r = nxt
                text = u"NEXT: %s in %s (%s)." % (b.header, r.scene, r.size)
                best = python_dict()
                for w in writes:
                    if w.menu is None or w.op != "+=" or not _urmp_isnum(w.value) or w.value <= 0:
                        continue
                    if w.scene != r.scene or w.file != r.file or w.line >= r.line:
                        continue
                    if cur is not None and w.scene == cur[1] and w.line <= cur[3]:
                        continue
                    k = id(w.menu)
                    if k not in best or w.value > best[k][0]:
                        best[k] = (w.value, w.option)
                if best and _urmp_isnum(b.sort):
                    d = sum(v for v, _o in best.values())
                    opts = [u'"%s"' % _urmp_plain(o, 40) for _v, o in best.values()][:3]
                    start = b.sort - d
                    text += u" %d choice%s in that scene come%s before it: %s (+%s). Arrive with %s and take them \u2192 %s." % (
                        len(best), "" if len(best) == 1 else "s", "s" if len(best) == 1 else "",
                        ", ".join(opts), _urmi_show(d), _urmi_show(start), _urmi_show(b.sort))
                    p.next_value = start
                else:
                    p.next_value = b.sort
                p.next_line = text
            gain = python_dict()
            for w in writes:
                if w.menu is None or w.op != "+=" or not _urmp_isnum(w.value) or w.value <= 0:
                    continue
                if w.scene in mass:
                    continue
                k = id(w.menu)
                gain[k] = max(gain.get(k, 0), w.value)
            if gain:
                p.gives_tail.append(u"The story script offers at most +%s in total (one pick per choice, counting every choice that adds to it; not counting the game's own code)." % _urmi_show(sum(gain.values())))

        elif mode == "value":
            byval = python_dict()
            for r in shown_rows:
                words, value, sort = _urmp_requirement(r, name, now)
                b = byval.get(words)
                if b is None:
                    hint = None
                    if isinstance(value, _urmi_text):
                        for w in writes:
                            if w.menu is not None and w.op == "=" and w.value == value:
                                hint = u'the choice "%s" in %s' % (_urmp_plain(w.option, 60), w.scene)
                                break
                    header = words
                    if isinstance(value, _urmi_text) and value == now:
                        header += u"   \u2190 now"
                    b = _URMPBlock(header, value, hint)
                    byval[words] = b
                b.rows.append(r)
            p.blocks = python_list(byval.values())
            for b in p.blocks:
                members = b.rows
                b.rows = python_list()
                _urmp_fill_block(b, members)
            text = u"%s is %s." % (name, now_words)
            if isinstance(now, _urmi_text):
                hint = None
                for w in writes:
                    if w.menu is not None and w.op == "=" and w.value == now:
                        hint = u' That\'s the choice "%s" in %s.' % (_urmp_plain(w.option, 60), w.scene)
                        break
                text += hint or " No choice in the story script sets this value."
            A.append(text)

        else:
            b = _URMPBlock(u"WHERE THE GAME CHECKS IT  (%d)" % len(shown_rows))
            for r in shown_rows:
                r.view_extra.insert(0, u"when %s" % _urmp_cond_words(r.cond))
            _urmp_fill_block(b, shown_rows)
            p.blocks.append(b)
            scenes = python_set(r.scene for r in rows)
            A.append(u"%s is %s. It is checked in %d place%s in %d scene%s." % (
                name, now_words, len(rows), "" if len(rows) == 1 else "s",
                len(scenes), "" if len(scenes) == 1 else "s"))

        # A2: is any of it still ahead?
        if shown_rows:
            later = [r for r in shown_rows if r.status == "later"]
            notp = [r for r in shown_rows if r.status == "not"]
            never = [r for r in shown_rows if r.status == "never"]
            known = [r for r in shown_rows if r.status]
            if later or notp or never:
                parts = python_list()
                if notp:
                    parts.append(u"%d in scenes you haven't played" % len(notp))
                if later:
                    parts.append(u"%d later in this scene" % len(later))
                if never:
                    parts.append(u"%d in scenes you played but never saw that version" % len(never))
                A.append(u"Of the places shown: %s." % "; ".join(parts))
            elif known and len(known) == len(shown_rows):
                A.append(u"All of them are in scenes you've already played. Changing it now only matters on a replay, an earlier save, or inside the game's own code.")

        # A3: who sets it.
        auto_scenes = python_set(w.scene for w in auto)
        if choice_count:
            text = u"Set by %d choice%s" % (option_count, "" if option_count == 1 else "s")
            if choice_count != option_count:
                text += u" in %d menu%s" % (choice_count, "" if choice_count == 1 else "s")
            if current_menu is not None and id(current_menu) in menus:
                text += u", one of them on your screen now"
            text += "."
            if auto:
                text += u" The game also sets it by itself in %d place%s." % (len(auto), "" if len(auto) == 1 else "s")
        elif auto:
            text = u"No choice sets it. The game changes it by itself in %d place%s." % (len(auto), "" if len(auto) == 1 else "s")
        else:
            text = u"Nothing in the story script sets it - only its starting value."
        if mass_hidden:
            text += u" (Also set by %s, which look%s like the game's own chapter select or scene-select menu.)" % (
                ", ".join(python_list(mass_hidden)[:2]), "s" if len(mass_hidden) == 1 else "")
        if funcs:
            text += u" %s in the game's own code also mention%s it." % (
                ", ".join("%s()" % f for f in funcs[:3]), "s" if len(funcs) == 1 else "")
        A.append(text)

        # --- B. right now ------------------------------------------------
        if current_menu is not None:
            q = _urmp_question(index, current_menu)
            p.now_header = u"THE CHOICE ON YOUR SCREEN" + (u"  -  after %s" % q if q else "")
            mine = menus.get(id(current_menu)) or ()
            for item in current_menu.items:
                label, cond, block = item[0], item[1], item[2]
                if block is None:
                    continue
                effects = python_list()
                for w in mine:
                    if w.option == label:
                        effects.append(_urmp_effect(w, now, boolish)[0])
                text = u'"%s"  \u2192  %s' % (_urmp_plain(label, 70), "; ".join(effects) if effects else "doesn't change it")
                value = _URMP_NOSET
                if cond and cond.strip() != "True" and name in _urmp_names_of(index, cond):
                    tree = _urmp_parse(cond)
                    visible = _urmp_ev(tree)
                    words = _urmp_cond_words(cond)
                    if visible is False:
                        r = _URMPRow()
                        r.cond = cond
                        req = _urmp_requirement(r, name, now)
                        text = u'"%s" is hidden right now - it needs %s' % (_urmp_plain(label, 70), words)
                        value = req[1]
                    elif visible is True:
                        text += u"   (offered because %s)" % words
                p.now_lines.append((text, value))
            if mine:
                p.now_lines.append((u"Picking one in the game sets it the same way - you don't need to change it here.", _URMP_NOSET))

        for r in shown_rows:
            if r.status == "later":
                p.later.append(r)
        p.later.sort(key=lambda r: r.line)

        # --- C. before you change it ------------------------------------
        W = p.warnings
        ahead_auto = [w for w in auto if w.status in ("later", "not")]
        resets = python_list()
        ahead_auto.sort(key=lambda w: (0 if w.op == "=" else 1, _URMP_STATUS_RANK.get(w.status, 4)))
        for w in ahead_auto:
            text = u"The game %s by itself in %s" % (_urmp_effect_named(w, name), w.scene)
            if w.cond:
                text += u" when %s" % _urmp_cond_words(w.cond)
            elif w.unless:
                text += u" unless %s" % " or ".join(_urmp_cond_words(c) for c in w.unless[:2])
            if w.status == "later":
                text += u" (later in this scene)"
            resets.append(text + ".")
        if resets:
            more = len(resets) - 1
            W.append(u"! " + resets[0] + (u" It changes it by itself in %d more place%s you haven't reached." % (
                more, "" if more == 1 else "s") if more else ""))
        later_choices = python_list()
        for m in menu_order:
            if current_menu is not None and m is current_menu:
                continue
            g = menus[id(m)]
            if g[0].status in ("later", "not"):
                for w in g:
                    later_choices.append(u'"%s" (%s) \u2192 %s' % (_urmp_plain(w.option, 50), w.scene, _urmp_effect(w, now, boolish)[0]))
        if later_choices:
            W.append(u"! %d choice%s you haven't reached change it again: %s%s" % (
                len(later_choices), "" if len(later_choices) == 1 else "s",
                "; ".join(later_choices[:2]), u" (+%d more)" % (len(later_choices) - 2) if len(later_choices) > 2 else ""))
        big = None
        for r in ahead:
            if r.weight >= 100 and r.needs_unmet and (big is None or r.weight > big.weight):
                big = r
        if big is not None:
            W.append(u"! The biggest moment still ahead (about %d lines, %s) also needs %s." % (big.weight, big.scene, big.needs_unmet[0]))
        if mode == "number" and _urmp_isnum(now):
            exact = all(_urmp_requirement(r, name, now)[0].startswith("exactly") for r in shown_rows) if shown_rows else False
            lowers = any(w.op in ("-=",) or (w.op == "=" and _urmp_isnum(w.value) and w.value < now) for w in writes)
            if exact and not lowers and ahead:
                upcoming = sorted(python_set(_urmp_requirement(r, name, now)[2] for r in ahead if _urmp_requirement(r, name, now)[2] is not None and _urmp_requirement(r, name, now)[2] > now))
                if upcoming:
                    W.append(u"! Only exact numbers are checked and nothing in the story script lowers it. Going past %s skips that moment." % _urmi_show(upcoming[0]))
        reading_scenes = python_dict()
        for r in rows:
            reading_scenes.setdefault(r.scene, r.line)
        if len(reading_scenes) >= 3:
            reset_here = 0
            for scene, line in reading_scenes.items():
                for w in auto:
                    if w.scene == scene and w.op == "=" and w.line < line:
                        reset_here += 1
                        break
            if reset_here * 10 >= len(reading_scenes) * 8:
                W.append(u"! In %d of the %d scenes that check it, the game sets it itself shortly before - a value set here is likely replaced before it matters." % (reset_here, len(reading_scenes)))
        if not W and ahead:
            p.okline = "Nothing in scenes you haven't played resets or changes it, as far as the story script shows."

        # --- D1 tail ----------------------------------------------------
        for line in collapse_lines:
            p.gives_tail.append(line)
        if quiet:
            eg = quiet[0]
            what = _urmp_write_words(eg.summary.writes[0])[1:-1] if eg.summary.writes else "change something"
            p.gives_tail.append(u"Also: %d check%s only change other values, with no dialogue - e.g. in %s: %s." % (
                len(quiet), "" if len(quiet) == 1 else "s", eg.scene, what))
        if loops:
            lscenes = python_set(r.scene for r in loops)
            p.gives_tail.append(u"%d loop%s in %d scene%s repeat while %s holds a certain value." % (
                len(loops), "" if len(loops) == 1 else "s", len(lscenes), "" if len(lscenes) == 1 else "s", name))

        # --- D2. choices -------------------------------------------------
        ordered = sorted(menu_order, key=lambda m: (
            0 if current_menu is not None and m is current_menu else 1,
            _URMP_STATUS_RANK.get(menus[id(m)][0].status, 4),
            menus[id(m)][0].file or "", menus[id(m)][0].line))
        for m in ordered:
            g = menus[id(m)]
            first = g[0]
            status = "here, on your screen" if current_menu is not None and m is current_menu else {
                "later": "later in this scene", "not": "not played", "never": "played",
                "above": "earlier in this scene", "played": "played"}.get(first.status, "")
            q = _urmp_question(index, m)
            header = u"%s%s%s" % (first.scene, (u"  \u00b7  " + status) if status else "",
                                  (u"  \u00b7  after %s" % q) if q else "")
            lines = python_list()
            for item in m.items:
                label, block = item[0], item[2]
                if block is None:
                    continue
                effects = python_list()
                value = _URMP_NOSET
                for w in g:
                    if w.option == label:
                        words, v = _urmp_effect(w, now, boolish)
                        effects.append(words)
                        value = v
                text = u'"%s"  \u2192  %s' % (_urmp_plain(label, 70), "; ".join(effects) if effects else "doesn't change it")
                also = python_list()
                for node in (block or ())[:12]:
                    if isinstance(node, renpy.ast.Python):
                        source = getattr(getattr(node, "code", None), "source", "") or ""
                        for wr in _urmp_effects(source)[0]:
                            if wr[0] != name and len(also) < 3:
                                also.append(_urmp_write_words(wr)[1:-1])
                if also:
                    text += u"   (also: %s)" % ", ".join(also)
                if seen.label(first.scene):
                    picked = seen.picked(m, label)
                    if picked is True:
                        text += u"   {color=#1e88e5}picked before{/color}"
                lines.append((text, value))
            p.choices.append((header, lines))
        if auto:
            groups_auto = python_dict()
            order = python_list()
            for w in auto:
                k = (w.scene, w.op, repr(w.value), w.cond, tuple(w.unless or ()))
                if k not in groups_auto:
                    groups_auto[k] = python_list()
                    order.append(k)
                groups_auto[k].append(w)
            texts = python_list()
            for k in order[:8]:
                w = groups_auto[k][0]
                text = u"%s in %s" % (_urmp_effect_named(w, "it"), w.scene)
                if w.cond:
                    text += u" when %s" % _urmp_cond_words(w.cond)
                elif w.unless:
                    text += u" unless %s" % " or ".join(_urmp_cond_words(c) for c in w.unless[:2])
                if len(groups_auto[k]) > 1:
                    text += u" (x%d)" % len(groups_auto[k])
                texts.append(text)
            p.choices_tail.append(u"By itself: " + u"  \u00b7  ".join(texts) + (u"  \u00b7  and %d more" % (len(order) - 8) if len(order) > 8 else ""))
        for scene, ws in mass_hidden.items():
            p.choices_tail.append(u"%s sets it too (%d option%s) - it looks like the game's own chapter select, skip or scene-select menu, not a story choice." % (
                scene, len(ws), "" if len(ws) == 1 else "s"))

        # --- tabs ----------------------------------------------------------
        if p.blocks or p.gives_tail:
            p.tabs.append(("gives", "What each value gives"))
        p.tabs.append(("choices", "Choices that set it (%d)" % choice_count))
        p.tabs.append(("details", "Details"))
        p.tab = p.tabs[0][0]

        # --- D3. details ----------------------------------------------------
        summary, _checks = urm_checks(name)
        if summary:
            p.details.append(_urmi_safe(summary))
        rcount, readers = urm_readers(name, 40)
        if rcount:
            p.details.append(u"{b}Checked in %d place%s:{/b}" % (rcount, "" if rcount == 1 else "s"))
            for line in readers:
                p.details.append(_urmi_safe(line))
        wcount, wlines = urm_writers(name, 40)
        if wcount:
            p.details.append(u"{b}Set in %d place%s:{/b}" % (wcount, "" if wcount == 1 else "s"))
            for line in wlines:
                p.details.append(_urmi_safe(line))
        declared = index.declared.get(name)
        if declared is not None and declared[1]:
            p.details.append(_urmi_safe(u"Starting value written in the script: %s" % declared[1]))
        p.detail_checks = _checks

        # --- E. footer -----------------------------------------------------
        p.footer.append(u"From the game's story script. Uses inside the game's own functions and screens aren't shown. "
                        u"Played / seen / picked = on this computer, in any playthrough. Line counts are approximate "
                        u"and include lines inside nested choices.")
        if seen.ever is None:
            p.footer.append(u"\"Never saw this version\" is off (the game is translated, or this engine doesn't record it).")
        if budget[0] <= 0:
            p.footer.append(u"Some sizes are lower bounds - very long scenes were not fully counted.")
        return p

    def _urmp_some(items, limit):
        if len(items) <= limit:
            return u", ".join(items)
        return u"%s and %d more" % (u", ".join(items[:limit]), len(items) - limit)

    def _urmp_choice_hint(writes, value, mass):
        found = python_list()
        for w in writes:
            if w.menu is None or w.op != "=" or w.scene in mass:
                continue
            if w.value is value or (w.value == value and type(w.value) == type(value)):
                text = u'"%s" in %s' % (_urmp_plain(w.option, 50), w.scene)
                if text not in found:
                    found.append(text)
        if not found:
            return None
        return u"same as picking " + u" or ".join(found[:2])


    # ------------------------------------------------------------------
    # What the screen calls
    # ------------------------------------------------------------------

    def urmi_ui(key, default=None):
        return _urmp_bucket("ui").get(key, default)

    def urmi_ui_set(key, value):
        _urmp_bucket("ui")[key] = value
        renpy.restart_interaction()

    def urmi_ui_toggle(key):
        ui = _urmp_bucket("ui")
        ui[key] = not ui.get(key, False)
        renpy.restart_interaction()

    def urmi_block_limit(panel, block):
        """Rows shown before "Show all": a number ladder shows one place per rung."""

        if panel.mode == "number":
            return 1
        return _URMP_ROWS_SHOWN

    def urmi_small_line(block):
        return _urmp_small_line(block)

    def urmi_settable(var, value):
        """Whether a [Set] button can put this value into URM's box."""

        if value is _URMP_NOSET or value is None:
            return False
        try:
            if not var.isEditable:
                return False
            kind = var.varType
        except Exception:
            return False
        if kind == "boolean":
            return value in (True, False, 0, 1)
        if kind in ("int", "float"):
            return _urmp_isnum(value) or isinstance(value, bool)
        if kind == "string":
            return isinstance(value, _urmi_text)
        return False

    def urmi_set_words(value):
        if value is True:
            return "Set ON"
        if value is False:
            return "Set OFF"
        return u"Set %s" % _urmp_plain(_urmi_show(value), 30)


