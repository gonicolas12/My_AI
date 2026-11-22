"""Texte replié pour comparer des mots : minuscules, sans accents ni ligatures.

La décomposition Unicode (NFKD) sépare « é » en « e » et son accent, « ﬁ » en
« fi », mais laisse « œ » et « æ », des lettres à part entière. Ensuite, ne
garder que [a-z0-9] coupait « sœur » en « s » et « ur », deux bouts trop courts
pour compter : « j'ai une sœur » n'avait aucun mot qui compte (la mémoire ne
pouvait pas le retenir d'elle-même), et « soeur », tapé sans la ligature, ne
retrouvait pas « sœur ».
"""

from __future__ import annotations

import unicodedata

_LIGATURES = str.maketrans({"œ": "oe", "Œ": "OE", "æ": "ae", "Æ": "AE"})


def fold(text: str) -> str:
    """Minuscules, sans accents ni ligatures : « Sœur Élise » → « soeur elise »."""
    decomposed = unicodedata.normalize("NFKD", (text or "").translate(_LIGATURES))
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()
