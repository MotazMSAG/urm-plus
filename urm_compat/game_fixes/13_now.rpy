# ---------------------------------------------------------------------------
# Now: is a test true in the game right now
# ---------------------------------------------------------------------------
#
# The layer under every feature that asks the live store. Then, in the same
# block: facts (14_facts: what a choice holds, the gates ahead) and words
# and tones (15_words: text, colours, icons, a branch's rows). Moved here
# unchanged from 20_cards, so a feature no longer needs the cards feature
# to use them (CODE_MAP.md, layers).

init 999 python:

    # A behaviour fix, switched like the story graph's (every _URMSG_FIX_
    # name is True in a game; the comparisons with the frozen readers turn
    # them off): a test that calls a function is never run to see whether
    # it holds. A call can do anything - roll the game's dice, count a
    # visit - so every display says "cannot tell" instead (the user's pick,
    # 2026-11-20).
    _URMSG_FIX_CALLS = True

    import ast as _urm_ast

    # The text of a test -> whether it calls something. Asked on every
    # redraw, so remembered; the script's tests are a fixed set.
    _URM_CALLS = python_dict()

    def _urm_engine_answer(call):
        """A call that only reads the engine's fixed answer for the device -
        renpy.variant("pc") - handed nothing but a literal: no dice, no
        visit count, no game code (Summer with Mia's name screens)."""

        func = call.func
        if not (isinstance(func, _urm_ast.Attribute) and func.attr == "variant"
                and isinstance(func.value, _urm_ast.Name) and func.value.id == "renpy"):
            return False
        if (getattr(call, "keywords", None) or getattr(call, "starargs", None)
                or getattr(call, "kwargs", None) or len(call.args) != 1):
            return False
        try:
            _urm_ast.literal_eval(call.args[0])
        except Exception:
            return False
        return True

    def _urm_calls(text):
        """True when the test calls a function, False when it does not,
        None when it cannot be read as an expression. Asking the engine
        which device it runs on (_urm_engine_answer) is not a call."""

        try:
            return _URM_CALLS[text]
        except KeyError:
            pass
        try:
            found = False
            for node in _urm_ast.walk(_urm_ast.parse(text.strip(), mode="eval")):
                if isinstance(node, _urm_ast.Call) and not _urm_engine_answer(node):
                    found = True
                    break
        except Exception:
            found = None
        _URM_CALLS[text] = found
        return found

    def _urm_truth(expression):
        """
        Whether a condition holds right now, or None if that cannot be said:
        the one answer every display gives (the user's pick, 2026-11-20).

        A test that calls a function is not run (_URMSG_FIX_CALLS): a flag
        test the flags reading knows is read from its collection instead
        (_urm_flag_truth, 61_now_values), and any other call cannot be told. A test is worked out the way
        Ren'Py works out the game's own tests (renpy.python.py_eval), so it
        reads the same in a Python 2 game.

        BaseException is caught, not Exception: this runs while the overlay is
        being built, and a game condition that calls sys.exit would otherwise
        surface as Ren'Py's exception screen rather than a quiet unknown.
        """

        try:
            text = u"%s" % (expression,)
            if _URMSG_FIX_CALLS:
                calls = _urm_calls(text)
                if calls is True:
                    return _urm_flag_truth(text)
                if calls is None:
                    return None
            return bool(renpy.python.py_eval(text))
        except BaseException:
            return None

    def _urm_now(name):
        """
        (True, value) for what a store name holds right now - elena_love,
        persistent.seen_end, mc.trust - or (False, None) when it cannot be
        read (not set yet). The one reader of "what the player has now":
        the map, the cards and the alert's goal words all ask it.
        """

        try:
            obj = renpy.store
            parts = name.split(".")
            if parts[0] == "persistent":
                obj = persistent
                parts = parts[1:]
            for part in parts:
                obj = getattr(obj, part)
            return True, obj
        except BaseException:
            return False, None

    # ------------------------------------------------------------------
    # What comes next: the menu on screen, the check ahead, taking either
    # ------------------------------------------------------------------
    #
    # Read the menu or check ahead from the story graph. A menu is on screen
    # when the game is
    # on a Menu statement; a check is ahead when the line on screen waits
    # for the player and an if-statement follows before anything else
    # waits, within the look-ahead (the player's setting, 20 by default:
    # counted per statement, so `scene x with dissolve` is three). A jump
    # or a call on the way is followed to its label. What is announced is
    # decided by the notification after it reads the whole chain.

    _urm_setting_add("urmcLookAhead", 20)

    _URM_LOOKAHEAD_MIN = 5
    _URM_LOOKAHEAD_MAX = 500

    def _urm_lookahead():
        """How many statements ahead a check is looked for."""

        try:
            value = int(_urm_setting("urmcLookAhead"))
        except Exception:
            return 20
        return min(_URM_LOOKAHEAD_MAX, max(_URM_LOOKAHEAD_MIN, value))

    def _urm_menu_here():
        """The Menu statement the game is on, or None."""

        node = _urmsg_here()
        if node is not None and _urmsg_kind(node) == _URMSG_K_MENU:
            return node
        return None

    def _urm_choice_here():
        """The choice the game is on, in any shape (_urmsg_choice: a menu, a
        called screen, buttons before ui.interact, a menu shown by a
        function), or None. A route the code picks is not on screen. The
        map rework opens on it; the readers above stay as they are."""

        node = _urmsg_here()
        if node is None:
            return None
        choice = _urmsg_choice(node)
        if choice is None or choice.shape == "code":
            return None
        return choice

    def _urm_choices_here():
        """The choices of the menu on screen, [(index, text, condition,
        block)], index into the menu's items; a caption (no block) is not
        a choice, and neither is one the menu's `set` already holds: the
        engine leaves those off the screen (renpy.exports.menu, every
        engine 7.3.5 - 8.5). Empty when no menu is on screen."""

        return _urm_choices_of(_urm_menu_here())

    def _urm_choices_of(menu):
        """_urm_choices_here for a given Menu statement (None: [])."""

        out = python_list()
        if menu is None:
            return out
        chosen = ()
        if getattr(menu, "set", None):
            try:
                chosen = renpy.python.py_eval(menu.set)
            except BaseException:
                chosen = ()
        for i, item in enumerate(getattr(menu, "items", None) or ()):
            if len(item) >= 3 and item[2]:
                try:
                    if item[0] in chosen:
                        continue
                except Exception:
                    pass
                out.append((i, item[0], item[1], item[2]))
        return out

    def _urm_gate_ahead():
        """The first if-statement ahead of the line on screen, or None."""

        try:
            node = _urmsg_here()
            if node is None or not _urmsg_blocks_urm(node):
                return None
            ahead = _urmsg_step_urm(node)
            for _n in range(_urm_lookahead()):
                if ahead is None or ahead is _URMSG_LOST:
                    return None
                if _urmsg_kind(ahead) == _URMSG_K_IF:
                    return ahead
                if _urmsg_blocks_urm(ahead):
                    return None
                ahead = _urmsg_step_urm(ahead)
        except Exception:
            pass
        return None

    # ---- a skip stopped at a check, held to resume
    #
    # A feature that stops a skip because a check comes into view (the
    # corner card's "Stop skipping at a check", 34_words) stops it here,
    # and the skip it stopped - slow, or fast to the next choice - is held
    # with the statement on screen. The dialogue click that resumes it
    # (81_rollback) asks _urm_skip_held, which gives
    # it only on that same statement and drops it anywhere else: a player
    # who read on with a key, or started a new game, never sees a skip
    # start out of nowhere. Kept in our memory, never in a save.

    class _URMSkipHold(python_object):
        def __init__(self):
            self.resume = None   # the skip stopped: "slow" or "fast"
            self.at = None       # the statement it stopped on

    def _urm_skip_hold():
        return _urm_kept("skip_hold", _URMSkipHold)

    def _urm_stop_skipping():
        """Stop the skip, held to resume on this statement."""

        if config.skipping:
            hold = _urm_skip_hold()
            hold.resume, hold.at = config.skipping, _urmsg_here()
        config.skipping = None

    def _urm_skip_held():
        """The skip held on the statement on screen, or None."""

        hold = _urm_skip_hold()
        if hold.resume and hold.at is not _urmsg_here():
            _urm_skip_forget()
        return hold.resume

    def _urm_skip_forget():
        hold = _urm_skip_hold()
        hold.resume = hold.at = None

    # ---- taking a choice or a way
    #
    # A choice is taken at once, hidden or not: the menu returns it as if
    # it had been clicked (fixed rollback allowed, as URM's Select did). A
    # way the game picks is taken when the game gets there: Take remembers
    # [(if-statement, arm)] - every earlier if-statement falls through
    # (arm -1), then the arm - and the if-statement goes that way when it
    # runs, however the game reached it, once (the engine's side is its own
    # block, at the end of 61_now_values). Loading a save forgets what was
    # not reached yet.

    def _urm_take_choice(index):
        """Pick choice `index` (into the menu's items) of the menu on screen."""

        menu = _urm_menu_here()
        if menu is None or not (0 <= index < len(menu.items)):
            renpy.notify("MRM: that choice is no longer on screen")
            return None
        renpy.game.log.rollback_is_fixed = False
        return renpy.ui.ChoiceReturn(menu.items[index][0], index)()

    def _urm_take_way(spec, words=None):
        """Take these ways when the game gets there: spec is
        [(if-statement, arm or -1)], in the order the game runs them."""

        _urm_take_state().pending = python_list(spec)
        renpy.notify(words or "MRM: that way will be taken when the game gets there")
        renpy.restart_interaction()

    def _urm_taken(node):
        """The arm a Take still waits to send this if-statement down, or None."""

        for target, arm in _urm_take_state().pending:
            if target is node:
                return arm
        return None
