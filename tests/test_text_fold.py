"""
Texte replié pour comparer des mots (utils/text_fold.py).

Régression : la décomposition Unicode laisse « œ » et « æ » entiers, et ne garder
ensuite que [a-z0-9] coupait « sœur » en « s » et « ur ». « J'ai une sœur » n'avait
plus aucun mot qui compte, et « soeur », tapé sans la ligature, ne retrouvait pas
« sœur ».
"""

import pytest

from utils.text_fold import fold


@pytest.mark.parametrize("text, folded", [
    ("Sœur Élise", "soeur elise"),
    ("ŒUVRE complète", "oeuvre complete"),
    ("Æsop et l'ex æquo", "aesop et l'ex aequo"),
    ("le ﬁlm", "le film"),
    ("Straße", "strasse"),
    ("", ""),
    (None, ""),
])
def test_fold(text, folded):
    assert fold(text) == folded
