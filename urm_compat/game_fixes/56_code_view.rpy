# A separate block: a failure to patch one of URM's classes must not take the
# helpers above with it.
init 999 python:

    # ------------------------------------------------------------------
    # How far path detection is allowed to look
    # ------------------------------------------------------------------
    #
    # lookAheadLimit is a hardcoded 20 (PathDetection.rpy:6) and it is charged
    # per NODE, not per line. `scene x with dissolve` is three nodes, so about
    # seven lines of cinematic run-up exhaust it and the player gets "No path
    # detected" with no way to look further.
    #
    # Exposing it beats refining what the budget charges for: not counting
    # Scene/Show/With/Python would mean replacing nextIfStatement, which is
    # also the node the force-a-path code rewrites, and the player-visible
    # result is the same as simply allowing a larger number. Default stays 20,
    # so detection behaves as it shipped until asked otherwise.

    _URMC_LOOKAHEAD_MIN = 5
    _URMC_LOOKAHEAD_MAX = 500

    def _urmc_lookahead():

        try:
            value = int(x52URM.Settings.urmcLookAhead)
        except Exception:
            return 20

        if value < _URMC_LOOKAHEAD_MIN:
            return _URMC_LOOKAHEAD_MIN
        if value > _URMC_LOOKAHEAD_MAX:
            return _URMC_LOOKAHEAD_MAX
        return value


    # ------------------------------------------------------------------
    # renpy.jump('label') in the code view
    # ------------------------------------------------------------------
    #
    # interactiveLabels needs the bare statement form - keywords-coloured
    # jump, one space, functions-coloured name (codeview.rpy:143) - so a
    # python jump never links, although stripRenpyCode deliberately keeps
    # those lines alive (:219). Most modern games jump from python, so the one
    # line that says where the story goes next is the one piece of dead text
    # in the view.

    def _urmc_python_label_links(view, coloredCode):

        try:
            colors = view.colors
            pattern = (r"{color=" + colors["keywords"] + r"}(?:call|jump){/color}"
                       r"\(\s*{color=" + colors["strings"]
                       + r"}['\"]([\w\.]+)['\"]{/color}")

            def addLink(match):
                return "{{a=URMLabelDialog:{}}}{}{{/a}}".format(
                    match.group(1), match.group())

            return renpy.re.sub(pattern, addLink, coloredCode)
        except Exception:
            return coloredCode


    # ------------------------------------------------------------------
    # Bare names in the code view and on the path cards
    # ------------------------------------------------------------------
    #
    # URM only colours - and so only links - a name with an operator beside
    # it (codeview.rpy:51-59). A condition that is just a flag, `if
    # lilithmad:` or a card reading `lilithmad`, stays dead text, and the most
    # common gate in these games is exactly that. Any plain word left after
    # URM's own colouring that names a value in the store gets the variables
    # colour, and URM's interactiveVariables then links it as usual. Functions,
    # classes, modules and Characters are callable or modules and stay plain;
    # a dotted name links only when every step of it resolves.

    _URMC_BARE = renpy.re.compile(
        r"(\{\{|\{color=[^}]*\}.*?\{/color\}|\{[^{}]*\})"
        r"|(?<![\w.])([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)(?![\w.(])")

    def _urmc_store_value(name):
        import keyword
        if keyword.iskeyword(name) or name in ("None", "True", "False"):
            return False
        parts = name.split(".")
        store = renpy.store.__dict__
        if parts[0] not in store:
            return False
        value = store[parts[0]]
        for part in parts[1:]:
            try:
                value = getattr(value, part)
            except Exception:
                return False
        return not (callable(value) or type(value).__name__ == "module")

    def _urmc_bare_var_links(view, coloredCode):

        try:
            color = view.colors["variables"]

            def mark(match):
                word = match.group(2)
                if word is None or not _urmc_store_value(word):
                    return match.group()
                return "{{color={}}}{}{{/color}}".format(color, word)

            return _URMC_BARE.sub(mark, coloredCode)
        except Exception:
            return coloredCode


    try:
        # Fetched again rather than reusing the search block's local: that
        # block may have declined to install, and this setting has nothing to
        # do with search.
        x52URM.SettingsClass.defaultValues.setdefault("urmcLookAhead", 20)
    except Exception as error:
        print("URM+: could not register urmcLookAhead (%s)" % (error,))

    try:
        # children carries the same dead cache guard as varType - hasattr on a
        # string literal that is never the mangled name - so it is rebuilt on
        # every access, and URM_objectVar reads it five times per execution.
        # Over the store root that is thousands of Var constructions per
        # interaction, which is the difference between a browser and a hang.
        #
        # Unlike varType this is safe to cache: the children are name HANDLES,
        # so an edited value still re-resolves and shows through. What goes
        # stale is a key added or removed while you are looking at the list,
        # and leaving the tab re-reads it.
        _urmc_children = x52URM.Var.children

        def _urmc_children_get(self):

            cache = self.__dict__

            try:
                return cache["_urmcChildren"]
            except KeyError:
                pass

            value = _urmc_children.fget(self)
            cache["_urmcChildren"] = value
            return value

        x52URM.Var.children = property(_urmc_children_get)
    except Exception as error:
        print("URM+: children left uncached (%s)" % (error,))

    try:
        x52URM.PathDetectionClass.lookAheadLimit = property(
            lambda self: _urmc_lookahead())
    except Exception as error:
        print("URM+: look-ahead left at 20 (%s)" % (error,))

    try:
        _urmc_orig_labels = x52URM.CodeViewClass.interactiveLabels

        def _urmc_interactiveLabels(self, coloredCode):
            return _urmc_python_label_links(
                self, _urmc_orig_labels(self, coloredCode))

        x52URM.CodeViewClass.interactiveLabels = _urmc_interactiveLabels
    except Exception as error:
        print("URM+: python jumps left unlinked (%s)" % (error,))

    try:
        _urmc_orig_vars = x52URM.CodeViewClass.interactiveVariables

        def _urmc_interactiveVariables(self, coloredCode):
            # Flags first (true("x") opens the flag), then bare names.
            try:
                coloredCode = _urmfl_links(self, coloredCode)
            except Exception:
                pass
            return _urmc_orig_vars(
                self, _urmc_bare_var_links(self, coloredCode))

        x52URM.CodeViewClass.interactiveVariables = _urmc_interactiveVariables
    except Exception as error:
        print("URM+: bare names left unlinked (%s)" % (error,))

