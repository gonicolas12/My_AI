"""
Outil de calcul mathématique local pour l'IA
"""

import ast

def calculate(expression: str) -> str:
    """
    Évalue une expression mathématique simple et retourne le résultat sous forme de chaîne.

    Args:
        expression: Expression mathématique à évaluer (ex: "2 + 2")

    Returns:
        Résultat de l'expression ou message d'erreur
    """
    try:
        result = ast.literal_eval(expression)
        return str(result)
    except (ValueError, SyntaxError) as e:
        return f"Erreur de calcul: {e}"
