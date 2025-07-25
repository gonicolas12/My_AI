"""
Outil de calcul mathématique local pour l'IA
"""
def calculate(expression: str) -> str:
    try:
        result = eval(expression, {"__builtins__": {}})
        return str(result)
    except Exception as e:
        return f"Erreur de calcul: {e}"
