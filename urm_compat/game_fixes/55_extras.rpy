init 999 python:

    def urm_copy(text):
        """Put `text` on the system clipboard and say so."""

        try:
            data = text if isinstance(text, bytes) else (text or u"").encode("utf-8")
        except Exception:
            return

        done = False

        for module in ("pygame_sdl2", "pygame"):
            try:
                scrap = __import__(module).scrap
                scrap.put(scrap.SCRAP_TEXT, data)
                done = True
                break
            except Exception:
                continue

        try:
            renpy.notify("Copied" if done else "This build has no clipboard")
        except Exception:
            pass



    def urm_seen(label):
        """
        True seen, False not seen, None when the engine cannot say.

        None covers a label that is not in this build at all, which is the
        common case for a save carried across an update - and it must not be
        drawn as "not seen", because that would read as missable content.
        """

        try:
            if not renpy.has_label(label):
                return None
            return bool(renpy.seen_label(label))
        except Exception:
            return None
