"""House word rules for every listing (Diane, 11/25/2026).

Never use: amber, ivory, faux. NELLY swaps them for plain words, then checks
again and refuses to send a listing if any are still there.
"""
from __future__ import annotations

import re

BANNED = ("amber", "ivory", "faux")

SWAPS = [
    (r"\bfaux\b", "imitation"),
    (r"\bivory\b", "off-white"),
    (r"\bamber\b", "golden brown"),
]


class BannedWordError(ValueError):
    pass


def _match_case(src: str, new: str) -> str:
    return new[0].upper() + new[1:] if src[:1].isupper() else new


def clean(text: str) -> str:
    for pat, new in SWAPS:
        text = re.sub(pat, lambda m: _match_case(m.group(0), new), text, flags=re.I)
    return text


def found(text: str) -> list[str]:
    return [w for w in BANNED if re.search(w, text, re.I)]


def check(*texts: str) -> None:
    """Hard stop: raise if any banned word is anywhere in the listing text."""
    hits = sorted({w for t in texts for w in found(t or "")})
    if hits:
        raise BannedWordError("Listing still has banned word(s): " + ", ".join(hits))
