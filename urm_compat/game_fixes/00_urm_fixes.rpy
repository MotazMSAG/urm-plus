# Standalone overlay and the names found in older save files.

init 998 python:

    # A save can refer to classes held by old screens, even after removing
    # the mod that defined them. Keep that pickle data under its old name.
    # The module is registered for unpickling only, outside the game store.
    _URM_SAVE_NAMES = (
        ("store.x52URM", "progressDragged"), ("store.x52URM", "Var"),
        ("store.x52URM", "Input"), ("store.x52URM", "SetVarValue"),
        ("store.x52URM", "SettingsClass"), ("store.x52URM", "ProgressBarClass"),
        ("store.x52URM", "Tooltip"), ("store.x52URM", "Notification"),
        ("store.x52URM", "InputGroup"), ("store.x52URM", "URMFileStore"),
        ("store", "_URMRMiddleClick"), ("store", "urm_branch_close"),
        ("store", "urm_branch_dragged"))

    class _URMSaveName(python_dict):
        """What a save held under a name that is gone: kept, never used."""

        def __init__(self, *args, **kwargs):
            python_dict.__init__(self, *args, **kwargs)

        def __call__(self, *args, **kwargs):
            return None

    def _urm_save_names():
        import sys
        # the interpreter's own str: the store's is unicode on Ren'Py 7
        native = bytes if sys.version_info[0] == 2 else str
        modules = python_dict()
        for module, name in _URM_SAVE_NAMES:
            module, name = native(module), native(name)
            if module == "store":
                home = renpy.store
            elif module in modules:
                home = modules[module]
            elif module in sys.modules:
                continue
            else:
                found = renpy.python.StoreDict()
                found["__name__"] = module
                home = modules[module] = sys.modules[module] = renpy.python.StoreModule(found)
            setattr(home, name, type(name, (_URMSaveName,), {"__module__": module}))
        # An old _URMRMiddleClick holds the engine's own style object, which
        # pickles only inside a real displayable: saved again, it is the
        # plain Null that URM+ saves in its place since 2026-11-17
        # (81_rollback).
        renpy.store._URMRMiddleClick.__reduce__ = _urm_saved_as_null

    def _urm_saved_as_null(self):
        return (renpy.display.layout.Null, ())

    _urm_own_layer = "urmplus"
    if _urm_own_layer not in renpy.config.layers:
        renpy.config.layers.append(_urm_own_layer)
    _urm_save_names()
