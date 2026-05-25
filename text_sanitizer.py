import unicodedata


_ALLOWED_CONTROL_WHITESPACE = {"\n", "\r", "\t"}
_SPACE_TRANSLATIONS = {
    "\u00a0": " ",  # non-breaking space
    "\u2007": " ",  # figure space
    "\u202f": " ",  # narrow non-breaking space
}
_LINE_TRANSLATIONS = {
    "\u2028": "\n",  # line separator
    "\u2029": "\n",  # paragraph separator
}


def strip_non_printable(text):
    """Remove hidden/non-printable copy-paste artifacts while preserving Markdown whitespace."""
    if text is None:
        return ""

    cleaned = []
    for char in str(text):
        if char in _SPACE_TRANSLATIONS:
            cleaned.append(_SPACE_TRANSLATIONS[char])
            continue
        if char in _LINE_TRANSLATIONS:
            cleaned.append(_LINE_TRANSLATIONS[char])
            continue
        if char in _ALLOWED_CONTROL_WHITESPACE:
            cleaned.append(char)
            continue
        if unicodedata.category(char).startswith("C"):
            continue
        cleaned.append(char)

    return "".join(cleaned)
