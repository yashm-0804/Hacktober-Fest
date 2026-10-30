"""Render untrusted text (patient input, chat, model output) as plain text inside st.markdown."""
import html
import re

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|>~])")


def safe_md(text) -> str:
    """Escape HTML and markdown syntax so links, images and fake formatting render as literal text."""
    return _MD_SPECIAL.sub(r"\\\1", html.escape(str(text or ""), quote=False))
