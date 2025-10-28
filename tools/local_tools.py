"""
Outils locaux spécialisés pour raisonnement, calcul, recherche, extraction d'infos, etc.
"""

import os
import math
import glob
import re
from typing import List, Any
import argparse

import ast
import operator


def local_math(expr: str) -> Any:
    """Évalue une expression mathématique locale sans utiliser eval."""
    # Opérateurs autorisés
    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
        ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
    }

    def _eval(node):
        if isinstance(node, ast.Num):  # <number>
            return node.n
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            op_type = type(node.op)
            if op_type in allowed_operators:
                return allowed_operators[op_type](_eval(node.left), _eval(node.right))
            else:
                raise ValueError("Opérateur non autorisé")
        elif isinstance(node, ast.UnaryOp):  # - <operand> ou + <operand>
            op_type = type(node.op)
            if op_type in allowed_operators:
                return allowed_operators[op_type](_eval(node.operand))
            else:
                raise ValueError("Opérateur unaire non autorisé")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "math":
                func = getattr(math, node.func.attr, None)
                if func and all(
                    isinstance(arg, (ast.Num, ast.UnaryOp, ast.BinOp))
                    for arg in node.args
                ):
                    return func(*[_eval(arg) for arg in node.args])
            raise ValueError("Fonction mathématique non autorisée")
        else:
            raise ValueError("Expression non autorisée")

    try:
        node = ast.parse(expr, mode="eval").body
        return _eval(node)
    except (SyntaxError, ValueError, TypeError) as e:
        return f"Erreur: {e}"


def local_search(pattern: str, folder: str = ".") -> List[str]:
    """Recherche de fichiers locaux par motif."""
    return glob.glob(os.path.join(folder, pattern), recursive=True)


def extract_emails(text: str) -> List[str]:
    """Extraction d'adresses email d'un texte."""
    return re.findall(r"[\w\.-]+@[\w\.-]+", text)


def extract_dates(text: str) -> List[str]:
    """Extraction de dates simples (format JJ/MM/AAAA ou AAAA-MM-JJ)."""
    return re.findall(r"\b\d{2}/\d{2}/\d{4}\b|\b\d{4}-\d{2}-\d{2}\b", text)


def main():
    """
    Point d'entrée principal pour l'utilisation en ligne de commande des outils locaux.
    """
    parser = argparse.ArgumentParser(
        description="Outils locaux pour IA (calcul, recherche, extraction)"
    )
    parser.add_argument(
        "--tool", type=str, required=True, help="math/search/emails/dates"
    )
    parser.add_argument("--input", type=str, required=True, help="Entrée pour l'outil")
    parser.add_argument(
        "--folder", type=str, default=".", help="Dossier pour la recherche locale"
    )
    args = parser.parse_args()
    if args.tool == "math":
        print(local_math(args.input))
    elif args.tool == "search":
        print(local_search(args.input, args.folder))
    elif args.tool == "emails":
        print(extract_emails(args.input))
    elif args.tool == "dates":
        print(extract_dates(args.input))
    else:
        print("Outil non reconnu")


if __name__ == "__main__":
    main()
