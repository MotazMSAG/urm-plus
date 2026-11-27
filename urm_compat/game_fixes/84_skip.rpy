# ---------------------------------------------------------------------------
# Keep skipping past a small change - a typo fix, a reworded line
# ---------------------------------------------------------------------------
#
# A developer who fixes a typo gives that line a new identity, so a player who
# has read the scene before is stopped by a skip on one changed line. Ren'Py
# decides "seen" in one place, Context.seen_current (execution.py:888), asked
# by the say statement and the dialogue's skip handling for both slow and fast
# skip (behavior.py:814, character.py:483 and :536).
#
# While skipping, an unseen line now counts as seen when it is one of at most
# N unseen lines sitting between seen lines - a seen line before them in the
# same passage, and one after them - so N new lines in a row are skipped and
# N+1 stop the skip as before:
#
#     seen  new  new  new  seen         -> keeps skipping (N = 3)
#     seen  new  new  new  new  seen    -> stops
#
# The look-ahead follows the script the way it will run: through jumps, into
# calls, and down the if-branch whose condition is true now. A choice menu, a
# return or anything it cannot follow ends it as "not a small change", so new
# content still stops the skip. The look back stays inside the passage: a short
# reply to a choice the player never made starts a block of its own and still
# stops the skip. Only while skipping; reading is untouched.

init 999 python:

    import sys as _urms_sys

    _urm_setting_add("urmcSkipTyposStrict", False)
    _urm_setting_add("urmcSkipTypos", 3)

    _URMS_WALK = 400

    def _urms_limit():
        value = _urm_setting("urmcSkipTypos")
        if value is None:
            return 3
        try:
            return int(value)
        except Exception:
            return 0

    def _urms_lookup(name):
        try:
            return renpy.game.script.lookup(name)
        except Exception:
            return None

    # The four readers below are the shared story graph's (rework move 6):
    # one copy of "what runs next as the game stands", "an if that shows
    # no line", "the lines in a block" and "a statement a line can sit next
    # to". _urms_lookup stays: it finds the statement the game is on.

    def _urms_truth(cond):
        """Whether a condition holds now: True, False, or None when it
        cannot be told - the one answer every display gives (13_now). Kept
        as the look-ahead's own name: the tests put stand-ins in its place."""

        return _urm_truth(cond)

    def _urms_next(node):
        """The statement that runs after `node`, or None where it cannot be told."""

        return _urmsg_step_live(node, _urms_truth)

    def _urms_line(node):
        """The dialogue line a statement is, or None."""

        return node if isinstance(node, renpy.ast.Say) else None

    # A player of a translation is on a line of that language, and the
    # engine marks THAT line seen. The rule walks the original script (the
    # one the story graph knows): it starts from the original of the line
    # played, and a line counts as seen when it or its line in the language
    # being played was seen.

    def _urms_here(current):
        """The statement of the original script the game is on."""

        return _urmsg_default_twin(_urms_lookup(current))

    def _urms_seen(line, seen):
        if _urm_was_seen(line.name, seen):
            return True
        for twin in _urmsg_played_twins(line):
            if _urm_was_seen(twin.name, seen):
                return True
        return False

    # Statements a line can sit next to without leaving its passage.
    def _urms_passes(node):
        return _urmsg_passes(node)

    def _urms_block(index, node):
        """The block a statement sits in: (its container, the kind of link, which arm)."""

        link = _urmsg_block_link(index.parent, node)
        if not link:
            return None
        return (id(link[0]), link[1], link[2])

    def _urms_quiet_if(node, depth=0):
        """An if whose branches only change pictures, sound or values - no dialogue, no choice."""

        return _urmsg_quiet_if(node, depth)

    def _urms_says_in(block, depth=0):
        """Every dialogue line directly in a block (and in ifs inside it)."""

        return _urmsg_says_in(block, depth)

    def _urms_changed_construct(index, first, seen, limit):
        """
        True when `first` opens a branch of an if or a menu whose every branch
        has dialogue, none of which shows as seen, with seen dialogue before
        the if or menu.

        Passing that point before means one of its branches was seen. If the
        player saw a different branch, this one is new to them - it stops. If
        no branch shows as seen at all, the whole construct got new identities
        in an update (re-indented, reworded) - it is the same content. An if
        without an else can be passed with no dialogue at all, so it does not
        qualify.
        """

        link = _urmsg_block_link(index.parent, first)
        if not link or link[1] not in ("if", "option"):
            return False
        construct = link[0]

        if link[1] == "if":
            blocks = [b for _c, b in construct.entries]
            if not construct.entries or construct.entries[-1][0].strip() != "True":
                return False
        else:
            blocks = [item[2] for item in construct.items if item[2] is not None]
        if len(blocks) < 2:
            return False
        for block in blocks:
            says = _urms_says_in(block)
            if not says:
                return False
            for say in says:
                if _urms_seen(say, seen):
                    return False

        # Seen dialogue before the construct, in its passage.
        walk = _urms_back(index, construct)
        steps = 0
        while walk is not None and steps < _URMS_WALK:
            steps += 1
            line = _urms_line(walk)
            if line is not None:
                return _urms_seen(line, seen)
            if not _urms_passes(walk):
                return False
            walk = _urms_back(index, walk)
        return False

    def _urms_back(index, node):
        """
        The statement before `node` in the same passage, or None at its start.

        Where several statements lead in, it is the end of an if or a menu. An
        if that only changes pictures - `if hair: scene a / else: scene b` -
        is still the same passage (Aihvala 0.7.1 re-indented such a scene and
        gave the line after it a new identity), so it is stepped over.
        """

        found = index.prev.get(id(node))
        if found is not None or id(node) not in getattr(index, "prev_many", ()):
            return found
        for lead in index.prev_many[id(node)]:
            if isinstance(lead, renpy.ast.If) and _urms_quiet_if(lead):
                return lead
        return None

    # ------------------------------------------------------------------
    # The lines the player actually went through
    # ------------------------------------------------------------------
    #
    # The default rule is the one asked for, word for word: up to N unseen
    # lines between seen lines keep skipping. "Between" is in the order the
    # player meets them, so the lines just played are counted as they run -
    # Say.execute, which Ren'Py 8.5's TranslateSay also calls - and the look
    # ahead finds the next seen line. That includes a short reply to a choice
    # the player has not picked before; the strict rule below stops on those.

    class _URMSRun(python_object):
        def __init__(self):
            self.unseen = 0          # unseen lines in a row, the current one included
            self.after_seen = False  # a seen line came before them

    def _urms_run():
        return _urm_kept("skip_run", _URMSRun)

    def _urms_note_line(node):
        """Called as each dialogue line starts: count it in the current run."""

        run = _urms_run()
        try:
            seen = renpy.game.persistent._seen_ever
        except Exception:
            return
        if _urm_was_seen(node.name, seen):
            run.unseen = 0
            run.after_seen = True
        else:
            run.unseen += 1

    def _urms_forget_run():
        run = _urms_run()
        run.unseen = 0
        run.after_seen = False

    try:
        _urms_say_execute = renpy.ast.Say.execute
        _urms_say_execute = getattr(_urms_say_execute, "__func__", _urms_say_execute)

        def _urms_execute(self, *args, **kwargs):
            try:
                _urms_note_line(self)
            except Exception:
                pass
            return _urms_say_execute(self, *args, **kwargs)

        if not getattr(_urms_say_execute, "_urms", False):
            _urms_execute._urms = True
            renpy.ast.Say.execute = _urms_execute
    except Exception as error:
        print("MRM: dialogue is not followed for skipping (%s)" % (error,))

    if _urms_forget_run not in config.after_load_callbacks:
        config.after_load_callbacks.append(_urms_forget_run)

    def _urms_ahead(node, unseen, limit, seen):
        """A seen line comes within `limit` unseen lines, `unseen` already counted."""

        walk = _urms_next(node)
        steps = 0
        while walk is not None and steps < _URMS_WALK:
            steps += 1
            if isinstance(walk, renpy.ast.Say):
                if _urms_seen(walk, seen):
                    return True
                unseen += 1
                if unseen > limit:
                    return False
            elif isinstance(walk, renpy.ast.Menu):
                # A choice stops any skip anyway: going on to it loses nothing.
                return True
            walk = _urms_next(walk)
        return False

    def _urms_played_between(current, limit):
        """The default rule: the lines just played, then the lines ahead."""

        run = _urms_run()
        if not run.after_seen or run.unseen < 1 or run.unseen > limit:
            return False
        node = _urms_here(current)
        if not isinstance(node, renpy.ast.Say):
            return False
        return _urms_ahead(node, run.unseen, limit, renpy.game.persistent._seen_ever)

    def _urms_small_change(current, limit):
        """
        True when `current` is one of at most `limit` unseen lines sitting
        between seen lines: a seen line before them in the same passage, and a
        seen line after them on the way the game will run.

        The line before must be in the same passage - not across a menu option
        or an if-branch - because a short reply to a choice the player never
        made also sits between seen lines, after the menu and before the merge.
        A typo fix sits inside text already read; a new reply starts its own
        block, with nothing before it there.

        A changed line can also be the first line of a block - the first thing
        said after picking an option the player did take. That counts too, but
        only when a seen line follows inside the same block: a reply to a
        choice never taken is followed by unseen lines until the story merges
        back, so its first seen line is outside the block.
        """

        index = _urmi_index()
        if index is None or index.state != "ready" or not getattr(index, "prev", None):
            return False

        cache = getattr(_URMMemory, "skip_cache", None)
        if cache is None or len(cache) > 500:
            cache = python_dict()
            _URMMemory.skip_cache = cache
        key = (current, limit, getattr(renpy.game.preferences, "language", None))
        if key in cache:
            return cache[key]

        result = False
        node = _urms_here(current)
        seen = renpy.game.persistent._seen_ever
        if isinstance(node, renpy.ast.Say):
            unseen = 1

            # Backwards, inside this passage, to a seen line - or to the start
            # of the block, which is enough if a seen line follows in it.
            before = False
            at_start = False
            first = node
            walk = _urms_back(index, node)
            steps = 0
            while walk is not None and steps < _URMS_WALK and unseen <= limit:
                steps += 1
                line = _urms_line(walk)
                if line is not None:
                    if _urms_seen(line, seen):
                        before = True
                        break
                    unseen += 1
                    first = line
                elif not _urms_passes(walk):
                    break
                walk = _urms_back(index, walk)
            else:
                at_start = walk is None and unseen <= limit
            if not before and walk is not None and not _urms_passes(walk) \
                    and _urms_line(walk) is None:
                at_start = unseen <= limit

            # Forwards, the way the game will run, to a seen line - inside the
            # same block when the run starts the block.
            if (before or at_start) and unseen <= limit:
                block = _urms_block(index, first) if not before else None
                walk = _urms_next(node)
                steps = 0
                while walk is not None and steps < _URMS_WALK:
                    steps += 1
                    if isinstance(walk, renpy.ast.Say):
                        if _urms_seen(walk, seen):
                            result = before or _urms_block(index, walk) == block or \
                                _urms_changed_construct(index, first, seen, limit)
                            break
                        unseen += 1
                        if unseen > limit:
                            break
                    walk = _urms_next(walk)
        cache[key] = result
        return result

    try:
        _urms_context = _urms_sys.modules["renpy.execution"].Context
        _urms_original = _urms_context.seen_current
        # The plain function: on Python 2 the unbound method insists on a real
        # Context as self, which a test's stand-in is not.
        _urms_original = getattr(_urms_original, "__func__", _urms_original)

        def _urms_seen_current(self, ever):
            if _urms_original(self, ever):
                return True
            if not ever or not config.skipping:
                return False
            limit = _urms_limit()
            if limit <= 0:
                return False
            try:
                if _urm_setting("urmcSkipTyposStrict"):
                    return _urms_small_change(self.current, limit)
                return _urms_played_between(self.current, limit)
            except Exception:
                return False

        if not getattr(_urms_original, "_urms", False):
            _urms_seen_current._urms = True
            _urms_context.seen_current = _urms_seen_current
    except Exception as error:
        print("MRM: skipping still stops on small changes (%s)" % (error,))

    # ---- the URM+ menu and settings page (the registry, 01_urm_door)

    def _urms_unseen():
        return bool(_preferences.skip_unseen)

    def _urms_unseen_flip():
        _preferences.skip_unseen = not _preferences.skip_unseen

    def _urms_unseen_put(on):
        _preferences.skip_unseen = bool(on)

    # The engine keeps "skip unseen text" for this game alone: its row has
    # no all-games level. Removed from URM+ menu (available in Settings and Quick access).
    _urm_row_add("skip_small_changes", "skipping", "Skip past small changes",
                 "When an update rewords lines you have read, skipping carries on.",
                 (("Off", 0), ("1 line", 1), ("2 lines", 2), ("3 lines", 3)),
                 setting="urmcSkipTypos", order=10)
    _urm_row_add("skip_replies", "skipping", "Replies to new choices",
                 "A short reply to a choice you have not picked before.",
                 (("Skip them", False), ("Stop on them", True)),
                 setting="urmcSkipTyposStrict", order=20)
    _urm_row_add("skip_unseen", "skipping", "Skip unseen text",
                 "Skipping runs through text you have never read.",
                 (("On", True), ("Off", False)),
                 get=_urms_unseen, put=_urms_unseen_put, order=30)


