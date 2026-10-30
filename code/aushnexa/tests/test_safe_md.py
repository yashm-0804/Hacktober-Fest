from core.safe_md import safe_md


def test_markdown_image_and_link_are_literal():
    out = safe_md("![x](http://evil.example/p.png) [click](http://evil.example)")
    assert "](" not in out.replace("\\]\\(", "")  # brackets and parens are escaped
    assert "\\!" in out and "\\[" in out


def test_html_is_escaped_and_hindi_survives():
    assert "&lt;img" in safe_md("<img src=x onerror=alert(1)>")
    assert safe_md("डॉक्टर से पुष्टि करें।") == "डॉक्टर से पुष्टि करें।"
