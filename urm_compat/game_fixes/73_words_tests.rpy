    # ------------------------------------------------------------------
    # Words and tones, part 3: the game's text made plain (tags and [name]
    # interpolations). Moved unchanged from the variable window (70) so
    # the alerts need no panel piece (CODE_MAP.md, layers).
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Script text, made fit to show
    # ------------------------------------------------------------------

    _URMP_TAG = _urmp_re.compile(r"\{\{|\{[^{}]*\}")
    _URMP_INTERP = _urmp_re.compile(r"\[\[|\[([A-Za-z_][\w.]*)(?:![a-z]+)?\]")

    def _urmp_interp(match):
        if match.group() == "[[":
            return "["
        value = _urmp_value(match.group(1))
        if isinstance(value, _urmi_text) and len(value) <= 40:
            return value
        name = getattr(value, "name", None) if value is not _URMP_UNK else None
        if isinstance(name, _urmi_text) and len(name) <= 40 and "[" not in name:
            return name
        return match.group()

    def _urmp_plain(text, limit=110):
        """Dialogue as plain words: tags dropped, [names] filled in, braces escaped."""

        try:
            text = u"%s" % (text,)
        except Exception:
            return u""
        text = _URMP_TAG.sub(lambda m: "{" if m.group() == "{{" else "", text)
        try:
            text = _URMP_INTERP.sub(_urmp_interp, text)
        except Exception:
            pass
        text = u" ".join(text.split())
        if len(text) > limit:
            text = text[:limit - 3].rstrip() + u"..."
        return text.replace("{", "{{")

