from text_sanitizer import strip_non_printable


def test_strip_non_printable_removes_hidden_copy_paste_chars():
    dirty = "Hel\u200blo\u0000\u202eworld\ufeff\u00ad"

    assert strip_non_printable(dirty) == "Helloworld"


def test_strip_non_printable_preserves_markdown_whitespace():
    dirty = "Line 1\n\t- item\r\nLine\u2028Break\u00a0Text\u202fDone"

    assert strip_non_printable(dirty) == "Line 1\n\t- item\r\nLine\nBreak Text Done"
