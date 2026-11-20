init 1999 python:
    # Story-graph rework, inside a real engine: the frozen references
    # (graph_refs.rpy, loaded just above as an init 1998 block) against the
    # live readers, and the shared graph against the references, over this
    # game's own script. Every gating line prints True, or what differed.
    # Counts and notes go to urm_probe_graph.txt and are never gating.
    #
    # Nothing here evaluates the game's own conditions: truth is replaced by
    # stand-ins (always False, always True, always raising, and two that
    # depend on the condition's own text) for the run.
    #
    # Each loop has its own time budget, started when the loop starts. A
    # line that had things to compare and compared none does not print True.
    _urmpg_lines = []
    _urmpg_notes = []

    def _urmpg_run():
        import time
        import os

        ast = renpy.ast
        full = os.path.exists(os.path.join(config.basedir, "urm_probe_full"))
        # The gate checks several games side by side, and each engine then
        # gets less done per second. It passes a factor so a loop that stops
        # on its budget still looks at as much as it did running alone.
        try:
            scale = float(os.environ.get("URM_GATE_BUDGET_SCALE", "1"))
        except Exception:
            scale = 1.0

        # Stop the background index build: it competes for the interpreter.
        try:
            x52URM.Var._urmcIndexGeneration = int(getattr(x52URM.Var, "_urmcIndexGeneration", 0)) + 1
        except Exception:
            pass

        stmts = [n for n in (renpy.game.script.all_stmts or ())]

        # Every 16th statement first, then the rest, so a budget that runs
        # out has still sampled the whole script.
        order = stmts[::16] + [n for i, n in enumerate(stmts) if i % 16]

        def norm(value, depth=0):
            if depth > 30:
                return "<deep>"
            if isinstance(value, ast.Node):
                return ("n", id(value))
            if isinstance(value, (python_list, list, tuple)):
                return [norm(v, depth + 1) for v in value]
            if isinstance(value, (python_dict, dict)):
                return sorted((k, norm(v, depth + 1)) for k, v in value.items())
            if isinstance(value, (python_set, set, frozenset)):
                return sorted(norm(v, depth + 1) for v in value)
            return value

        def got(fn, *args):
            # A port must raise where its original raises: compare that too.
            try:
                return ("ok", norm(fn(*args)))
            except Exception as error:
                return ("raised", type(error).__name__)

        def written_true(nodes, depth=0):
            """
            RETIRED by idea 4 (design fix C3, 2026-11-20): a block that holds a
            written `if True:`. Such an arm tests nothing, so the working file no
            longer puts an "only if True" guard on what is in it; the frozen readers
            still do. The flat-record comparisons skip exactly these blocks (every
            other comparison on them stays), and check_maze.py's "if True:" cases
            hold the new behaviour.
            """
        
            for n in (nodes or ()):
                if isinstance(n, ast.If):
                    for cond, block in n.entries:
                        if isinstance(cond, ast.PyExpr) and (u"%s" % (cond,)).strip() == u"True":
                            return True
                        if depth < 12 and written_true(block, depth + 1):
                            return True
            return False

        _URMPG_DYN = ("jump to a computed label", "call a computed label")

        def idea8_missing(name):
            try:
                return renpy.game.script.lookup(name) is None
            except Exception:
                return True

        def idea8_static(n):
            """
            RETIRED by idea 8 (design fix C7, 2026-11-20): a jump, a call or
            a python line that jumps to a label that is not in the script.
            The frozen readers name the label; the working file says the one
            record for a jump that cannot be followed. A computed target
            reads the same in both and is still compared.
            """
            if isinstance(n, ast.Jump):
                return not getattr(n, "expression", False) and idea8_missing(n.target)
            if isinstance(n, ast.Call):
                return not getattr(n, "expression", False) and idea8_missing(n.label)
            if isinstance(n, ast.Python):
                hop = _urmrefm_pyjump(n)
                return bool(hop) and idea8_missing(hop[1])
            return False

        def idea8_block(nodes, depth=0):
            for n in (nodes or ()):
                if idea8_static(n):
                    return True
                if isinstance(n, ast.If) and depth < 12:
                    for _cond, block in n.entries:
                        if idea8_block(block, depth + 1):
                            return True
            return False

        def idea8_walk(value, depth=0):
            """RETIRED by idea 8: a walk of the working file that met a jump
            or a call it cannot follow - it says so in its records, whoever
            walks, and ends as "dyn"."""
            if depth > 40:
                return False
            if isinstance(value, (list, tuple)):
                for v in value:
                    if idea8_walk(v, depth + 1):
                        return True
                return False
            try:
                return value in _URMPG_DYN or value == "dyn"
            except Exception:
                return False

        def idea8_tail(result):
            """RETIRED by idea 8, for a gate chain: the text of a closing
            step that is a jump or a call that cannot be followed."""
            def unfollowed(text):
                try:
                    if text in _URMPG_DYN:
                        return True
                    if text.startswith("jump ") or text.startswith("call "):
                        name = text[5:].strip()
                        return " " not in name and idea8_missing(name)
                except Exception:
                    pass
                return False

            def walk(v, depth=0):
                if depth > 40:
                    return v
                if isinstance(v, (list, tuple)):
                    if len(v) == 3 and v[0] == "tail" and unfollowed(v[2]):
                        return ["tail", v[1], "<idea 8>"]
                    return [walk(x, depth + 1) for x in v]
                return v

            try:
                return (result[0], walk(result[1]))
            except Exception:
                return result

        def blocks_of(node):
            out = []
            for entry in (getattr(node, "entries", None) or []):
                out.append(entry[1])
            for item in (getattr(node, "items", None) or []):
                if item[2] is not None:
                    out.append(item[2])
            return out

        class Line(object):
            """One gating line. tick() once per item looked at, check() per
            comparison. Closes as True only if nothing differed AND, when
            there were items, at least one was looked at."""

            def __init__(self, name, budget):
                self.name = name
                self.end = None if full else time.time() + budget * scale
                self.items = 0
                self.checks = 0
                self.diff = None

            def spent(self):
                return self.end is not None and time.time() > self.end

            def tick(self):
                self.items += 1

            def check(self, what, a, b):
                self.checks += 1
                if self.diff is None and a != b:
                    try:
                        self.diff = "%s: %r != %r" % (what, a, b)
                    except Exception:
                        self.diff = "%s: differs" % (what,)

            def close(self, total):
                if self.diff is not None:
                    value = self.diff[:300].encode("ascii", "replace").decode("ascii")
                elif total and not self.items:
                    value = "compared nothing (%d to compare)" % total
                else:
                    value = True
                _urmpg_lines.append("%s=%s" % (self.name, value))
                _urmpg_notes.append("%s: %d of %d looked at, %d comparisons"
                                    % (self.name, self.items, total, self.checks))

        def where(node):
            return "%s:%s" % (getattr(node, "filename", "?"), getattr(node, "linenumber", "?"))

        def reset():
            _urmm_st.succ.clear()
            _urmrefm_st.succ.clear()

        ifs = [n for n in order if isinstance(n, ast.If)]
        menus = [n for n in order if isinstance(n, ast.Menu)]
        labels = [n for n in order if isinstance(n, ast.Label)]
        pythons = [n for n in order if isinstance(n, ast.Python)]

        store = renpy.store
        real_eval = renpy.python.py_eval
        real_truth = store._urm_truth
        real_ref_truth = store._urmref_truth

        def boom(*a, **k):
            raise NameError("probe stand-in")

        def text_number(cond):
            return sum(bytearray((u"%s" % (cond,)).encode("utf-8"))) % 3

        def by_text(cond, *a, **k):
            n = text_number(cond)
            if n == 0:
                raise NameError("probe stand-in")
            return n == 1

        def by_text_shifted(cond, *a, **k):
            n = (text_number(cond) + 1) % 3
            if n == 0:
                raise NameError("probe stand-in")
            return n == 1

        # Evaluators: return a value or raise. The last two depend on the
        # condition, so a second or third arm of an if is the one taken.
        stand_ins = (("false", lambda *a, **k: False),
                     ("true", lambda *a, **k: True),
                     ("raises", boom),
                     ("text", by_text),
                     ("shifted", by_text_shifted))

        def as_truth(fn):
            def truth(cond, *a, **k):
                try:
                    return bool(fn(cond))
                except Exception:
                    return None
            return truth

        # The behaviour fixes are switched off for the comparisons with the
        # frozen readers (each _URMSG_FIX_ name is True in a game), and put
        # back in the finally below.
        fixes = [n for n in dir(store) if n.startswith("_URMSG_FIX_")]
        kept_fixes = [(n, getattr(store, n)) for n in fixes]

        try:
            for n in fixes:
                setattr(store, n, False)
            _urmpg_notes.append("behaviour fixes switched off for the comparisons: %s"
                                % ", ".join(sorted(fixes)))
            store._urm_truth = lambda *a, **k: None
            store._urmref_truth = lambda *a, **k: None

            # ---- flow and text, every statement
            reset()
            flow = Line("ref_live_flow", 70)
            text = Line("ref_live_text", 70)
            for n in order:
                if flow.spent():
                    break
                flow.tick()
                text.tick()
                flow.check(where(n), got(_urmm_successors, n), got(_urmrefm_successors, n))
                if not idea8_static(n):
                    text.check(where(n), got(_urm_statement, n), got(_urmref_statement, n))
            flow.close(len(order))
            text.close(len(order))

            # ---- the skip look-ahead's step, under every stand-in
            live = Line("ref_live_live", 90)
            for tag, fn in stand_ins:
                renpy.python.py_eval = fn
                for n in order:
                    if live.spent():
                        break
                    live.tick()
                    live.check(tag + " " + where(n), got(_urms_next, n), got(_urmrefs_next, n))
            renpy.python.py_eval = real_eval
            live.close(len(order) * len(stand_ins))

            # ---- lexical readers: python lines, flatten, pure, quiet, says
            lex = Line("ref_live_lex", 70)
            for n in pythons:
                if lex.spent():
                    break
                lex.tick()
                da, db = [0], [0]
                lex.check("pylines " + where(n), (got(_urm_python_lines, n, da), da[0]),
                          (got(_urmref_python_lines, n, db), db[0]))
                lex.check("pyjump " + where(n), got(_urmm_pyjump, n), got(_urmrefm_pyjump, n))
            for n in ifs + menus:
                if lex.spent():
                    break
                lex.tick()
                if isinstance(n, ast.If):
                    da, db = [0], [0]
                    if not written_true([n]) and not idea8_block([n]):
                      lex.check("flatten " + where(n), (got(lambda x, d: _urm_flatten([x], dropped=d), n, da), da[0]),
                              (got(lambda x, d: _urmref_flatten([x], dropped=d), n, db), db[0]))
                    lex.check("pure " + where(n), got(lambda x: _urmm_pure([x], 0), n), got(lambda x: _urmrefm_pure([x], 0), n))
                    lex.check("quiet " + where(n), got(_urms_quiet_if, n), got(_urmrefs_quiet_if, n))
                else:
                    lex.check("textmenu " + where(n), got(_urmm_text_menu, n), got(_urmrefm_text_menu, n))
                for b in blocks_of(n):
                    da, db = [0], [0]
                    if not written_true(b) and not idea8_block(b):
                      lex.check("flatten arm " + where(n), (got(lambda x, d: _urm_flatten(x, dropped=d), b, da), da[0]),
                              (got(lambda x, d: _urmref_flatten(x, dropped=d), b, db), db[0]))
                    lex.check("pure arm " + where(n), got(_urmm_pure, b), got(_urmrefm_pure, b))
                    lex.check("tag " + where(n), got(_urmm_target_tag, b), got(_urmrefm_target_tag, b))
                    lex.check("says " + where(n), got(_urms_says_in, b), got(_urmrefs_says_in, b))
            lex.close(len(pythons) + len(ifs) + len(menus))

            # ---- the gate chain, from every If, as URM would have found it
            chain = Line("ref_live_chain", 50)
            cls = type(x52URM.PathDetection)
            had = cls.__dict__.get("nextIfStatement")
            current = [None]
            cls.nextIfStatement = property(lambda self: (current[0], True))
            try:
                for n in ifs:
                    if chain.spent():
                        break
                    chain.tick()
                    current[0] = n
                    def live_chain():
                        steps = _urm_chain()
                        return (steps, python_list(x52URM.Var._urmChainMeta))
                    # Since rework move 5b a chain that cannot be followed
                    # raises LookupError, not what URM's step raised: every
                    # caller catches both alike, so THAT it raises is compared.
                    a, b = got(live_chain), got(_urmref_chain, n)
                    # RETIRED by idea 2 (design fix C1, 2026-11-20): a chain
                    # whose step is lost no longer raises - it returns the
                    # gates it found, closed by the step that says where it
                    # stops. A lost chain is compared as lost.
                    if a[0] == "ok" and _urmsg_chain(
                            n, x52URM.PathDetection.lookAheadLimit,
                            x52URM.PathDetection.nodeIsBlocking, _urmsg_step_urm,
                            _URM_MAX_GATES + 4).lost:
                        a = ("raised", "lost")
                    if a[0] == "raised":
                        a = ("raised", "lost")
                    if b[0] == "raised":
                        b = ("raised", "lost")
                    chain.check(where(n), idea8_tail(a), idea8_tail(b))
            finally:
                if had is not None:
                    cls.nextIfStatement = had
                else:
                    del cls.nextIfStatement
            chain.close(len(ifs))

            # ---- searches and walks, per menu
            search = Line("ref_live_search", 90)
            run = Line("ref_live_run", 90)
            for m in menus:
                if search.spent():
                    break
                search.tick()
                blocks = blocks_of(m)
                reset()
                pa = got(_urmm_plan, m, blocks)
                pb = got(_urmrefm_plan, m, blocks)
                search.check("plan " + where(m), pa, pb)
                if pa[0] != "ok" or pa[1] is None:
                    continue
                starts, stop = _urmm_plan(m, blocks)
                rstarts, rstop = _urmrefm_plan(m, blocks)
                for s, rs in zip(starts, rstarts):
                    search.check("reach " + where(m), got(_urmm_reach, s, m), got(_urmrefm_reach, rs, m))
                search.check("dist " + where(m), got(_urmm_distances, stop), got(_urmrefm_distances, rstop))
                # The live arm walk is not compared with the frozen one any
                # more (a split inside a way closes at its own rejoin; the
                # budget is shared out - FINDINGS.md 2026-11-20). What is
                # checked on every real menu instead: it must not raise,
                # and no way may be left unread while another was read.
                if not run.spent():
                    run.tick()
                    walked = got(_urmm_arms, m, blocks, (starts, stop))
                    run.check("arms walk " + where(m), walked[0], "ok")
            search.close(len(menus))
            run.close(len(menus))

            # ---- per label: the next menu ahead, and the trunk walk
            nextm = Line("ref_live_nextmenu", 40)
            for tag, fn in stand_ins:
                truth = as_truth(fn)
                store._urm_truth = truth
                store._urmref_truth = truth
                for n in labels:
                    if nextm.spent():
                        break
                    nextm.tick()
                    nextm.check(tag + " " + where(n), got(_urmm_next_menu, n), got(_urmrefm_next_menu, n))
            store._urm_truth = lambda *a, **k: None
            store._urmref_truth = lambda *a, **k: None
            nextm.close(len(labels) * len(stand_ins))

            stretch = Line("ref_live_stretch", 40)
            for n in labels:
                if stretch.spent():
                    break
                stretch.tick()
                walked = got(_urmm_stretch, n)
                if not idea8_walk(walked[1]):
                    stretch.check(where(n), walked, got(_urmrefm_stretch, n))
            stretch.close(len(labels))

            # ============================================================
            # The shared graph against the references (nothing uses it yet)
            # ============================================================
            if "_urmsg_flow" not in globals():
                _urmpg_lines.append("graph_block=missing")
                return

            _urmsg_reset()
            reset()
            limit = x52URM.PathDetection.lookAheadLimit
            blocking = x52URM.PathDetection.nodeIsBlocking
            real_next = x52URM.PathDetection.nextNode

            def py_truth(cond):
                try:
                    taken = renpy.python.py_eval(cond)
                except Exception:
                    return None
                return bool(taken)

            def urm_step(n):
                try:
                    return real_next(n)
                except Exception:
                    return _URMSG_LOST

            def lost(result):
                return ("raised", "lost") if result[0] == "raised" else idea8_tail(result)

            def graph_chain(n, step, blocks):
                c = _urmsg_chain(n, limit, blocks, step)
                if c.lost:
                    raise LookupError("lost")
                return (c.steps, c.meta)

            def graph_step(n):
                found = _urmsg_step_urm(n)
                return "LOST" if found is _URMSG_LOST else found

            gflow = Line("graph_flow_same", 60)
            gtext = Line("graph_text_same", 60)
            gurm = Line("graph_urm_same", 60)
            gblock = Line("graph_blocking_same", 60)
            # Move 6: "a dialogue line can sit next to this statement", the
            # frozen test against the graph's and against the skip block's
            # wrapper, for every kind of statement this game has.
            gpass = Line("graph_passes_same", 60)
            for n in order:
                if gflow.spent():
                    break
                gflow.tick()
                gtext.tick()
                gurm.tick()
                gblock.tick()
                gpass.tick()
                ref_pass = got(_urmrefs_passes, n)
                gpass.check("graph " + where(n), ref_pass, got(_urmsg_passes, n))
                gpass.check("skip block " + where(n), ref_pass, got(_urms_passes, n))
                gflow.check(where(n), got(_urmrefm_successors, n), got(_urmsg_flow, n))
                if not idea8_static(n):
                    gtext.check(where(n), got(_urmref_statement, n), got(_urmsg_stmt_text, n))
                a = got(real_next, n)
                if a[0] == "raised":
                    a = ("ok", "LOST")
                gurm.check(where(n), a, got(graph_step, n))
                gblock.check(where(n), got(blocking, n), got(_urmsg_blocks_urm, n))
            gflow.close(len(order))
            gtext.close(len(order))
            gurm.close(len(order))
            gblock.close(len(order))
            gpass.close(len(order))

            glive = Line("graph_live_same", 80)
            for tag, fn in stand_ins:
                renpy.python.py_eval = fn
                for n in order:
                    if glive.spent():
                        break
                    glive.tick()
                    glive.check(tag + " " + where(n), got(_urmrefs_next, n), got(_urmsg_step_live, n, py_truth))
            renpy.python.py_eval = real_eval
            glive.close(len(order) * len(stand_ins))

            glex = Line("graph_lex_quiet_same", 30)
            for n in ifs:
                if glex.spent():
                    break
                glex.tick()
                glex.check("quiet " + where(n), got(_urmrefs_quiet_if, n), got(_urmsg_quiet_if, n))
            for n in pythons:
                if glex.spent():
                    break
                glex.tick()
                glex.check("hop " + where(n), got(_urmrefm_pyjump, n), got(_urmsg_hop, n))
            glex.close(len(ifs) + len(pythons))

            # ---- M1: what a block does, graph against the references
            def ref_lines(x):
                d = [0]
                return (_urmref_python_lines(x, d), d[0])

            def ref_flat(x):
                d = [0]
                return (_urmref_flatten(x, dropped=d), d[0])

            def new_flat(x):
                d = [0]
                return (_urmsg_flat(x, (), 0, d), d[0])

            glex2 = Line("graph_lex_same", 60)
            for n in pythons:
                if glex2.spent():
                    break
                glex2.tick()
                glex2.check("pylines " + where(n), got(ref_lines, n), got(_urmsg_py_lines, n))
            for n in ifs + menus:
                if glex2.spent():
                    break
                glex2.tick()
                if isinstance(n, ast.If):
                    if not written_true([n]) and not idea8_block([n]):
                        glex2.check("flat " + where(n), got(ref_flat, [n]), got(new_flat, [n]))
                    glex2.check("pure " + where(n), got(lambda x: _urmrefm_pure([x], 0), n),
                                got(lambda x: _urmsg_pure((x,), 0), n))
                else:
                    glex2.check("textmenu " + where(n), got(_urmrefm_text_menu, n), got(_urmsg_text_menu, n))
                for b in blocks_of(n):
                    ref = (got(new_flat, b) if written_true(b) or idea8_block(b)
                           else got(ref_flat, b))
                    glex2.check("flat arm " + where(n), ref, got(new_flat, b))
                    glex2.check("arm recs " + where(n), ref, got(_urmsg_arm_recs, b))
                    glex2.check("pure arm " + where(n), got(_urmrefm_pure, b), got(_urmsg_pure, b))
                    glex2.check("tag " + where(n), got(_urmrefm_target_tag, b), got(_urmsg_target_tag, b))
                    glex2.check("says " + where(n), got(_urmrefs_says_in, b), got(_urmsg_says_in, b))
            glex2.close(len(pythons) + len(ifs) + len(menus))

            # ---- M1: the shared run, stitched back into the arm walk and
            # the trunk walk. The stitch is what the maze block keeps.
            def stitch_walk(w, node, stack, seen, depth):
                stack = python_list(stack)
                seen = python_set(seen)
                records, end, at = _urmsg_run(w, node, stack, seen)
                if end[0] != "split":
                    return records, end
                if isinstance(at, ast.If):
                    arms = []
                    exhaustive = False
                    for cond, block in (getattr(at, "entries", None) or []):
                        if not _urmsg_is_else(cond):
                            label = "if " + _urmsg_clip(str(cond), 18)
                        else:
                            label = "otherwise"
                            exhaustive = True
                        start = block[0] if block else at.next
                        arms.append((label + _urmsg_target_tag(block), start))
                    if not exhaustive:
                        arms.append(("otherwise", at.next))
                    return records, ("fork", [(label, stitch_walk(w, start, stack, seen, depth))
                                              for label, start in arms], "if")
                items = [i for i in (getattr(at, "items", None) or []) if i[2] is not None]
                if depth >= _URMREFM_DEPTH:
                    return records, ("more", len(items))
                return records, ("fork", [(_urmrefm_choice_label(i),
                                           stitch_walk(w, i[2][0] if i[2] else at.next, stack, seen, depth + 1))
                                          for i in items], "menu")

            def stitch_arms(menu, plan):
                starts, stop = plan
                w = _URMSGWalk(id(stop) if stop is not None else None, menu,
                               _URMREFM_STEPS, _URMSG_KEEP_ARM)
                return [stitch_walk(w, s, (), (), 0) for s in starts]

            def stitch_stretch(start):
                blocks = python_list((python_list((None, python_list())),))
                w = _URMSGWalk(None, None, _URMREFM_STRETCH, _URMSG_KEEP_TRUNK, blocks)
                _records, end, at = _urmsg_run(w, start, python_list(), python_set())
                if end[0] == "split":
                    return blocks, at, None
                return blocks, None, end[0]

            grun = Line("graph_run_same", 90)
            for m in menus:
                if grun.spent():
                    break
                grun.tick()
                blocks = blocks_of(m)
                reset()
                pa = got(_urmrefm_plan, m, blocks)
                if pa[0] != "ok" or pa[1] is None:
                    continue
                plan = _urmrefm_plan(m, blocks)
                stitched = got(stitch_arms, m, plan)
                if not idea8_walk(stitched[1]):
                    grun.check("arms " + where(m), got(_urmrefm_arms, m, blocks, plan), stitched)
            grun.close(len(menus))

            gtrunk = Line("graph_run_trunk_same", 40)
            for n in labels:
                if gtrunk.spent():
                    break
                gtrunk.tick()
                stitched = got(stitch_stretch, n)
                if not idea8_walk(stitched[1]):
                    gtrunk.check(where(n), got(_urmrefm_stretch, n), stitched)
            gtrunk.close(len(labels))

            gchain = Line("graph_chain_same", 40)
            gchain2 = Line("graph_chain_urm_same", 40)
            for n in ifs:
                if gchain.spent():
                    break
                gchain.tick()
                gchain2.tick()
                ref = lost(got(_urmref_chain, n))
                gchain.check(where(n), ref, lost(got(graph_chain, n, urm_step, blocking)))
                gchain2.check(where(n), ref, lost(got(graph_chain, n, _urmsg_step_urm, _urmsg_blocks_urm)))
            gchain.close(len(ifs))
            gchain2.close(len(ifs))

            gplan = Line("graph_search_plan_same", 90)
            greach = Line("graph_search_reach_same", 90)
            gdist = Line("graph_search_dist_same", 90)
            for m in menus:
                if gplan.spent():
                    break
                gplan.tick()
                blocks = blocks_of(m)
                reset()
                pa = got(_urmrefm_plan, m, blocks)
                gplan.check(where(m), pa, got(_urmsg_plan, m, blocks))
                # Move 7: the plan is remembered per split. Asked again, and
                # with the arms the other way round, it is still the answer
                # of the frozen search.
                gplan.check("again " + where(m), pa, got(_urmsg_plan, m, blocks))
                turned = blocks[::-1]
                gplan.check("turned " + where(m), got(_urmrefm_plan, m, turned),
                            got(_urmsg_plan, m, turned))
                if pa[0] != "ok" or pa[1] is None:
                    continue
                greach.tick()
                gdist.tick()
                starts, stop = _urmrefm_plan(m, blocks)
                for s in starts:
                    greach.check(where(m), got(_urmrefm_reach, s, m),
                                 got(lambda x, y: _urmsg_reach(x, y, 4000, True)[0], s, m))
                gdist.check(where(m), got(_urmrefm_distances, stop),
                            got(lambda x: _urmsg_reach(x, None, 8000, False)[0], stop))
            gplan.close(len(menus))
            greach.close(greach.items)
            gdist.close(gdist.items)

            gnext = Line("graph_search_nextmenu_same", 40)
            for tag, fn in stand_ins:
                truth = as_truth(fn)
                store._urmref_truth = truth
                for n in labels:
                    if gnext.spent():
                        break
                    gnext.tick()
                    gnext.check(tag + " " + where(n), got(_urmrefm_next_menu, n),
                                got(lambda x: _urmsg_next_split(x, truth)[0], n))
            gnext.close(len(labels) * len(stand_ins))

            # Move 7: the statement the game is on. At init the game is on
            # none; the position is set to a statement for the test and put
            # back. The graph's answer, the maze's and the engine's own.
            ghere = Line("graph_here_same", 20)
            try:
                ctx = renpy.game.context()
                had_current = ctx.current
            except Exception:
                ctx = None
            if ctx is None:
                _urmpg_notes.append("graph_here_same: this engine has no context at init")
            else:
                try:
                    for n in order[:400]:
                        if ghere.spent():
                            break
                        if getattr(n, "name", None) is None:
                            continue
                        ghere.tick()
                        ctx.current = n.name
                        engine = got(renpy.game.script.lookup, n.name)
                        ghere.check("graph " + where(n), engine, got(_urmsg_here))
                        ghere.check("maze " + where(n), engine, got(_urmm_here))
                    ctx.current = ("urm probe", "no such statement", 0)
                    ghere.check("not in the script", ("ok", None), got(_urmsg_here))
                finally:
                    ctx.current = had_current
            ghere.close(min(len(order), 400) if ctx is not None else 0)

            # ============================================================
            # Moves 8 and 9: the script index, and the climbs up its links
            # ============================================================
            #
            # The index as it was before move 8 is frozen whole
            # (graph_refs_m8.rpy, _URMREF8Index). Both are built here, in
            # the foreground, over every statement of this game, and every
            # table must come out the same: which block each statement sits
            # in, what every condition and python line reads and writes,
            # the labels, the flags. Then every statement is asked where it
            # sits, the frozen readers on the frozen index against the live
            # readers on the live one.
            if "_URMREF8Index" not in globals():
                _urmpg_lines.append("graph_refs_m8=missing")
            else:
                began = time.time()
                ref_index = _URMREF8Index()
                ref_index.build(stmts)
                ref_took = time.time() - began
                began = time.time()
                new_index = _URMIndex()
                new_index.build(stmts)
                new_took = time.time() - began

                def flag_fields(flag):
                    return sorted((k, norm(v)) for k, v in vars(flag).items())

                gindex = Line("graph_index_same", 600)
                sizes = []
                for table in ("reads", "writes", "rivals", "tokens", "calls", "callreads",
                              "callnames", "declared", "helpers", "flags", "labels",
                              "label_lines", "parent", "prev", "prev_many"):
                    a = getattr(ref_index, table)
                    b = getattr(new_index, table)
                    gindex.tick()
                    sizes.append("%s %d" % (table, len(a)))
                    gindex.check(table + ": entries", len(a), len(b))
                    for k in a:
                        if k not in b:
                            gindex.check(table + ": only before", repr(k)[:80], None)
                            break
                        va, vb = a[k], b[k]
                        if table == "flags":
                            va, vb = flag_fields(va), flag_fields(vb)
                        if va is vb or va == vb:
                            gindex.checks += 1
                            continue
                        gindex.check("%s[%s]" % (table, repr(k)[:60]), norm(va), norm(vb))
                        if gindex.diff is not None:
                            break
                gindex.tick()
                gindex.check("state", (ref_index.state, ref_index.checks, ref_index.total),
                             (new_index.state, new_index.checks, new_index.total))
                gindex.check("built", new_index.state, "ready")
                gindex.close(16)
                _urmpg_notes.append("index: %s" % ", ".join(sizes))
                _urmpg_notes.append("index build, foreground: %.1f s before the move, %.1f s now (%d statements)"
                                    % (ref_took, new_took, len(stmts)))

                # Move 9: what the panel reads from a python statement, for
                # every python source of this game: the frozen reader
                # against the live one (the index's reading of the same
                # parse is in the tables above).
                gpy = Line("graph_py_same", 60)
                unparsed = 0
                for n in pythons:
                    if gpy.spent():
                        break
                    source = getattr(getattr(n, "code", None), "source", None)
                    if source is None:
                        continue
                    gpy.tick()
                    gpy.check(where(n), got(_urmref8p_effects, source), got(_urmp_effects, source))
                    if not _urmsg_py_parse(source)[0]:
                        unparsed += 1
                gpy.close(len(pythons))
                _urmpg_notes.append("python statements: %d looked at, %d not valid python"
                                    % (gpy.items, unparsed))

                # RETIRED by idea 1 (a behaviour fix, 2026-11-20): "the label
                # guessed from a line number is the one the frozen index
                # guessed" - the nearest label above, even one nested in the
                # scene before. The frozen readers are handed the live
                # guess; every climb and every fall back to the line is
                # still compared. How many lines the old guess named
                # differently is counted, for the notes.
                old_at = ref_index.label_at
                ref_index.label_at = new_index.label_at
                renamed = 0
                renamed_first = None

                gcont = Line("graph_contain_same", 90)
                tl_total = 0
                tl_none = 0
                for n in order:
                    if gcont.spent():
                        break
                    gcont.tick()
                    fn = getattr(n, "filename", "?")
                    ln = getattr(n, "linenumber", 0)
                    site = (fn, ln, id(n))
                    here = where(n)
                    if old_at(fn, ln) != new_index.label_at(fn, ln):
                        renamed += 1
                        if renamed_first is None:
                            renamed_first = "%s: %s, was %s" % (here, new_index.label_at(fn, ln), old_at(fn, ln))
                    label = got(_urmm_label_of, n, new_index)
                    gcont.check("label_of " + here, got(_urmref8m_label_of, n, ref_index), label)
                    gcont.check("where " + here, got(ref_index.where, site), got(new_index.where, site))
                    gcont.check("scene " + here, got(_urmref8p_scene, ref_index, n, fn, ln),
                                got(_urmp_scene, new_index, n, fn, ln))
                    gcont.check("in_init " + here, got(_urmref8g_in_init, ref_index, site),
                                got(_urmg_in_init, new_index, site))
                    gcont.check("block " + here, got(_urmref8s_block, ref_index, n),
                                got(_urms_block, new_index, n))
                    if "tl/" in (u"%s" % (fn,)).replace(chr(92), "/"):
                        tl_total += 1
                        if label == ("ok", None):
                            tl_none += 1
                gcont.close(len(order))
                _urmpg_notes.append("language files: %d statements looked at, %d with no label"
                                    % (tl_total, tl_none))
                _urmpg_notes.append("scene by line: %d statements where the guess no longer names a nested label above (%s)"
                                    % (renamed, renamed_first))

            # The gate-state machine on fixed vectors.
            three = (("gate", "a", None), ("gate", "b", None), ("else", None, None))
            states_ok = (
                norm(_urmsg_gate_states(three, lambda c: c == "b")) == [["dead", 1], ["runs", 2], ["dead", 0]]
                and norm(_urmsg_gate_states(three, lambda c: None)) == [["unknown", 1], ["unknown", 2], ["unknown", 0]]
                and norm(_urmsg_gate_states(three, lambda c: False)) == [["dead", 1], ["dead", 2], ["runs", 0]])
            _urmpg_lines.append("graph_states_ok=%r" % (states_ok,))

            # Memo tables are untracked containers of tuples.
            g = _urmsg_st.g
            tables = (g.facts, g.labels, g.py, g.q, g.arms, _urmsg_st.kinds)
            good = all(type(t) is python_dict for t in tables)
            for f in g.facts.values():
                if not (type(f.e) is tuple and type(f.flow) is tuple and type(f.arms) is tuple):
                    good = False
                    break
            _urmpg_lines.append("graph_untracked=%r" % (good,))
            _urmpg_notes.append("graph tables: %d facts, %d labels, %d python sources, %d skipped lookups"
                                % (len(g.facts), len(g.labels), len(g.py), g.skipped))

            # ---- a cold run of the graph must register nothing with rollback
            #
            # The engine's log is swapped for an empty one while a window
            # runs. A window is a plain function holding only graph calls
            # and while-counters: a display, a comprehension or a slice of
            # a store list inside it would be the probe's own tracked object.
            # Everything a window needs is prepared here, outside.
            log = getattr(renpy.game, "log", None)
            if log is None or not hasattr(log, "mutated"):
                _urmpg_lines.append("graph_no_mutation=True")
                _urmpg_notes.append("graph_no_mutation: this engine has no rollback log at init")
            else:
                some_nodes = python_list()
                i = 0
                while i < len(order) and i < 3000:
                    some_nodes.append(order[i])
                    i += 1
                some_ifs = python_list()
                i = 0
                while i < len(ifs) and i < 60:
                    some_ifs.append(ifs[i])
                    i += 1
                some_menus = python_list()
                i = 0
                while i < len(menus) and i < 5:
                    some_menus.append((menus[i], python_list(blocks_of(menus[i]))))
                    i += 1
                some_labels = python_list()
                i = 0
                while i < len(labels) and i < 60:
                    some_labels.append(labels[i])
                    i += 1
                no_truth = lambda cond: None
                fixed = (("gate", "a", None), ("else", None, None))
                some_blocks = python_list()
                for n in some_ifs:
                    for b in blocks_of(n):
                        some_blocks.append(b)
                some_pythons = python_list()
                i = 0
                while i < len(pythons) and i < 200:
                    some_pythons.append(pythons[i])
                    i += 1
                one = (0,)

                def w_flow():
                    for n in some_nodes:
                        _urmsg_flow(n)
                        _urmsg_stmt_text(n)

                def w_steps():
                    for n in some_nodes:
                        _urmsg_step_urm(n)
                        _urmsg_step_live(n, no_truth)
                        _urmsg_blocks_urm(n)
                        _urmsg_passes(n)
                    _urmsg_here()

                def w_chain():
                    for n in some_ifs:
                        _urmsg_quiet_if(n)
                        c = _urmsg_chain(n, limit, _urmsg_blocks_urm, _urmsg_step_urm)
                        _urmsg_gate_states(c.steps, no_truth)
                    _urmsg_gate_states(fixed, no_truth)

                def w_search():
                    for pair in some_menus:
                        _urmsg_plan(pair[0], pair[1])
                        _urmsg_plan(pair[0], pair[1])
                    for n in some_labels:
                        _urmsg_next_split(n, no_truth)

                # M1: what a block does, and the shared run in both modes.
                def w_lex():
                    for n in some_pythons:
                        _urmsg_py_lines(n)
                    for b in some_blocks:
                        _urmsg_flat(b)
                        _urmsg_arm_recs(b)
                        _urmsg_pure(b)
                        _urmsg_target_tag(b)
                        _urmsg_says_in(b)
                    for pair in some_menus:
                        _urmsg_text_menu(pair[0])

                def w_run():
                    for n in some_labels:
                        blocks = python_list((python_list((None, python_list())),))
                        w = _URMSGWalk(None, None, 300, _URMSG_KEEP_TRUNK, blocks)
                        _urmsg_run(w, n, python_list(), python_set())
                        w = _URMSGWalk(None, None, 300, _URMSG_KEEP_ARM)
                        _urmsg_run(w, n, python_list(), python_set())

                # The branch tracker reads every check it passes on each line.
                def w_branch():
                    for n in some_ifs:
                        info = _urmb_info(n)
                        _urmb_rejoin(n, 0, info)
                        _urmb_arm(info, getattr(n, "next", None))
                    for pair in some_menus:
                        info = _urmb_info(pair[0])
                        _urmb_rejoin(pair[0], 0, info)

                # Move 8: listing a statement's blocks and tests, and a
                # climb up a table of links.
                links = python_dict()

                def w_structure():
                    for n in some_nodes:
                        for kind, arm, extra, members in _urmsg_children(n):
                            for child in members:
                                links[id(child)] = (n, kind, extra)
                        _urmsg_conds(n)
                    for n in some_nodes:
                        _urmsg_climb(links, n)
                        _urmsg_block_link(links, n)
                    for n in some_pythons:
                        _urmsg_py_top(_urmsg_py_parse(n.code.source)[1])

                def w_selftest():
                    return [1, 2, 3]

                def measure(fn):
                    kept = log.mutated
                    fresh = python_dict()
                    log.mutated = fresh
                    try:
                        try:
                            fn()
                        except Exception:
                            pass
                    finally:
                        log.mutated = kept
                    return len(fresh)

                _urmsg_reset()
                found = python_list()
                for name, fn in (("flow", w_flow), ("steps", w_steps),
                                 ("chain", w_chain), ("search", w_search),
                                 ("lex", w_lex), ("run", w_run),
                                 ("branch", w_branch), ("structure", w_structure)):
                    count = measure(fn)
                    if count:
                        found.append("%s=%d" % (name, count))
                seen_self = measure(w_selftest)
                _urmpg_notes.append("graph_no_mutation: self-test saw %d tracked object(s)" % seen_self)
                if not seen_self:
                    # Nothing shows up for a deliberate display: this engine
                    # does not register at creation here, so the windows
                    # prove nothing. The AST rule in run_tests is the proof.
                    _urmpg_lines.append("graph_no_mutation=True")
                    _urmpg_notes.append("graph_no_mutation: not measurable on this engine at init")
                else:
                    _urmpg_lines.append("graph_no_mutation=%s" % (True if not found else " ".join(found)))

        finally:
            renpy.python.py_eval = real_eval
            store._urm_truth = real_truth
            store._urmref_truth = real_ref_truth
            for n, value in kept_fixes:
                setattr(store, n, value)
            reset()

        # ---- the behaviour fixes switched ON again, as they are in a game.
        # Everything above compared with them off. Here every menu of this
        # game gets its plan and its walked ways, and every label its
        # stretch, the way a player's game makes them: none may raise. How
        # many menus now meet somewhere else than the frozen search says is
        # a note, not a verdict.
        try:
            _urmsg_reset()
            reset()
            gon = Line("graph_fixes_on_walk", 70)
            moved = 0
            first_moved = None
            for m in menus:
                if gon.spent():
                    break
                gon.tick()
                blocks = blocks_of(m)
                pa = got(_urmm_plan, m, blocks)
                gon.check("plan " + where(m), pa[0], "ok")
                if pa[0] != "ok" or pa[1] is None:
                    continue
                if got(_urmrefm_plan, m, blocks) != pa:
                    moved += 1
                    if first_moved is None:
                        first_moved = where(m)
                gon.check("arms " + where(m), got(_urmm_arms, m, blocks, _urmm_plan(m, blocks))[0], "ok")
            looked = gon.items
            for n in labels:
                if gon.spent():
                    break
                gon.tick()
                gon.check("stretch " + where(n), got(_urmm_stretch, n)[0], "ok")
            gon.close(len(menus) + len(labels))
            _urmpg_notes.append("fixes on: %d of %d menus looked at meet somewhere else than "
                                "the frozen search says (first: %s); %d labels remembered as "
                                "coming back or not"
                                % (moved, looked, first_moved, len(_urmsg_graph().rets)))
        except Exception as error:
            _urmpg_lines.append("graph_fixes_on_walk=%r" % (error,))

        _urmpg_notes.append("statements %d, ifs %d, menus %d, labels %d, python %d, full run %r"
                            % (len(stmts), len(ifs), len(menus), len(labels), len(pythons), full))

    try:
        _urmpg_run()
    except Exception as _urmpg_error:
        import traceback as _urmpg_tb
        _urmpg_lines.append("graph_ERROR=%r" % (_urmpg_error,))
        _urmpg_notes.append(_urmpg_tb.format_exc())

    try:
        import io as _urmpg_io
        import os as _urmpg_os
        _urmpg_io.open(_urmpg_os.path.join(config.basedir, "urm_probe_graph.txt"), "w", encoding="utf-8").write(
            u"\n".join(u"%s" % _urmpg_x for _urmpg_x in (_urmpg_lines + _urmpg_notes)))
    except Exception:
        pass
