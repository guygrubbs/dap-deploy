"""
sanitize_html.py
================

Backend wrapper that strips or whitelists HTML exactly the way the
front‑end `sanitizeHtml()` utility does, preventing XSS when we store or
render AI‑generated strings.

Uses **bleach** (well‑maintained, OWASP‑aligned).  If bleach is missing the
function still imports and *falls back* to a very conservative “strip all
tags” implementation so the app never crashes.

Public API
----------
sanitize_html(text: str) -> str
cleanse_json(value: Any) -> Any   # recursively sanitises str leaves
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --------------------------------------------------------------------------- #
# Configuration – mirror the front‑end's allowed tags/attributes
# --------------------------------------------------------------------------- #

ALLOWED_TAGS = [
    "b",
    "i",
    "strong",
    "em",
    "u",
    "br",
    "p",
    "ul",
    "ol",
    "li",
    "span",
    "a",
]
ALLOWED_ATTRIBUTES: dict[str, list[str] | dict[str, str]] = {
    "a": ["href", "title", "target", "rel"],
    "span": ["style"],
}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

# --------------------------------------------------------------------------- #
# Try to import bleach; fall back to regex stripping if unavailable
# --------------------------------------------------------------------------- #

try:
    import bleach  # type: ignore
except ImportError:  # pragma: no cover
    logger.warning(
        "bleach package not found – falling back to naive HTML stripping. "
        "Install bleach>=6.0 for full sanitisation."
    )

    TAG_RE = re.compile(r"<[^>]+?>")

    def sanitize_html(text: str) -> str:  # type: ignore
        """Remove **all** HTML tags – no white‑listing available."""
        return TAG_RE.sub("", text)

else:

    def sanitize_html(text: str) -> str:  # type: ignore
        """
        Return a sanitised HTML fragment safe for insertion into the DOM.

        • Allows a minimal formatting subset (bold, lists, links, spans).  
        • Strips disallowed tags/attrs.  
        • Removes any `<script>` or event‑handler attributes automatically.
        """
        cleaned = bleach.clean(
            text,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            protocols=ALLOWED_PROTOCOLS,
            strip=True,
        )
        return cleaned


# --------------------------------------------------------------------------- #
# Convenience helper – recurse through JSON structures
# --------------------------------------------------------------------------- #

def cleanse_json(value: Any) -> Any:
    """
    Walk a nested dict / list and sanitise every string leaf.

    Useful when you want to scrub an entire JSON payload before
    `json.dumps` or DB insertion::

        safe_dict = cleanse_json(raw_json_dict)
    """
    if isinstance(value, str):
        return sanitize_html(value)
    if isinstance(value, list):
        return [cleanse_json(v) for v in value]
    if isinstance(value, dict):
        return {k: cleanse_json(v) for k, v in value.items()}
    return value
