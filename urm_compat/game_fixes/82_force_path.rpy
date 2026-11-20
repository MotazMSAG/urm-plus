# ---------------------------------------------------------------------------
# Force any path, even one behind a jump or call
# ---------------------------------------------------------------------------
#
# URM forces a path by rewriting the chain of statements between the cursor
# and the if-statement (PathDetection.rpy:146-184): it copies each node and
# points the last one's .next at the chosen arm. A jump or call in between
# leaves no .next to rewrite - the target is looked up by name - so URM marks
# the row "Not forceable, probably because it's behind a call or jump", and
# in a game that jumps between scenes that is most of them.
#
# This forces at the other end instead. Select remembers which arm of which
# if-statement was picked, and when the game executes that if-statement it
# goes down that arm, however it got there. It is one-shot: once taken, the
# if-statement tests its conditions normally again, and loading a save
# forgets anything not yet reached.
#
# The same works for the gates after the table: picking one makes every
# if-statement before it fall through, then takes the picked arm.

init 999 python:

    class _URMFState(python_object):
        def __init__(self):
            self.pending = python_list()   # [(if-statement, arm)], -1 = none matches

    def _urmf_state():
        holder = x52URM.Var
        st = getattr(holder, "_urmfState", None)
        if st is None:
            st = _URMFState()
            holder._urmfState = st
        return st

    def _urmf_set(spec, words):
        st = _urmf_state()
        st.pending = python_list(spec)
        renpy.notify(words)

    def _urmf_take(node):
        """The arm a pending force wants for this if-statement, or None."""

        st = _urmf_state()
        if not st.pending:
            return None
        for i, (target, arm) in enumerate(st.pending):
            if target is node:
                del st.pending[i]
                return arm
        return None

    try:
        _urmf_if_execute = renpy.ast.If.execute

        def _urmf_execute(self):
            arm = _urmf_take(self)
            if arm is None:
                return _urmf_if_execute(self)
            entries = self.entries or ()
            if 0 <= arm < len(entries) and entries[arm][1]:
                target = entries[arm][1][0]
            else:
                target = self.next
            renpy.game.context().next_node = target

        if not getattr(renpy.ast.If.execute, "_urmf", False):
            _urmf_execute._urmf = True
            renpy.ast.If.execute = _urmf_execute
    except Exception as error:
        print("URM+: paths behind a jump stay unforceable (%s)" % (error,))

    def _urmf_forget():
        _urmf_state().pending = python_list()

    if _urmf_forget not in config.after_load_callbacks:
        config.after_load_callbacks.append(_urmf_forget)

    class _URMFForce(python_object):
        """Select on a row of the Path options table that URM cannot force."""

        def __init__(self, arm):
            self.arm = arm

        def __call__(self):
            detected = x52URM.PathDetection.nextIfStatement
            if not detected:
                renpy.notify("URM: the path is no longer ahead")
                return
            spec = python_list()
            spec.append((detected[0], self.arm))
            _urmf_set(spec, "URM: path %d will be taken when the game gets there" % (self.arm + 1))

        def __eq__(self, other):
            return isinstance(other, _URMFForce) and other.arm == self.arm

        def __ne__(self, other):
            return not self.__eq__(other)

        def __hash__(self):
            return hash(("urmf", self.arm))

    def urmf_force_later(row):
        specs = getattr(x52URM.Var, "_urmfLaterSpecs", None) or ()
        if row >= len(specs):
            renpy.notify("URM: that path is no longer ahead")
            return
        _urmf_set(specs[row], "URM: that path will be taken when the game gets there")

    try:
        _urmf_action = x52URM.Path.Action

        def _urmf_action_get(self):
            action = _urmf_action.fget(self)
            if action is not None:
                return action
            arm = getattr(self, "_m1_PathDetection__index", None)
            if arm is None:
                return None
            return _URMFForce(arm)

        x52URM.Path.Action = property(_urmf_action_get)
    except Exception as error:
        print("URM+: Select stays off for paths behind a jump (%s)" % (error,))


