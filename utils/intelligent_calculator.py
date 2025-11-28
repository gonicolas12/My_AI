"""
Calculateur Intelligent
Système de calcul avancé avec reconnaissance en français et symboles
"""

import re
import ast
import math
from typing import Union, Dict, Any


class IntelligentCalculator:
    """Calculateur intelligent avec reconnaissance en français et symboles"""

    def __init__(self):
        # Mappings des opérations en français vers symboles
        self.french_operations = {
            # Opérations de base
            "plus": "+",
            "ajouté": "+",
            "ajoutée": "+",
            "additionné": "+",
            "et": "+",
            "moins": "-",
            "soustrait": "-",
            "retiré": "-",
            "enlevé": "-",
            "diminué": "-",
            "fois": "*",
            "multiplié": "*",
            "par": "*",
            "x": "*",
            "divisé": "/",
            "sur": "/",
            "divisée": "/",
            "divisé par": "/",

            # Opérations avancées
            "puissance": "**",
            "exposant": "**",
            "élevé": "**",
            "carré": "**2",
            "cube": "**3",
            "racine": "sqrt",
            "racine carrée": "sqrt",
            "racine carree": "sqrt",
            "modulo": "%",
            "reste": "%",

            # Parenthèses
            "parenthèse": "(",
            "ouverte": "(",
            "fermée": ")",
            "ouvre": "(",
            "ferme": ")",
        }

        # Nombres en français
        self.french_numbers = {
            "zéro": "0",
            "zero": "0",
            "un": "1",
            "une": "1",
            "deux": "2",
            "trois": "3",
            "quatre": "4",
            "cinq": "5",
            "six": "6",
            "sept": "7",
            "huit": "8",
            "neuf": "9",
            "dix": "10",
            "onze": "11",
            "douze": "12",
            "treize": "13",
            "quatorze": "14",
            "quinze": "15",
            "seize": "16",
            "dix-sept": "17",
            "dix-huit": "18",
            "dix-neuf": "19",
            "vingt": "20",
            "trente": "30",
            "quarante": "40",
            "cinquante": "50",
            "soixante": "60",
            "soixante-dix": "70",
            "quatre-vingt": "80",
            "quatre-vingts": "80",
            "quatre-vingt-dix": "90",
            "cent": "100",
            "mille": "1000",
            "million": "1000000",
            "milliard": "1000000000",
        }

        # Fonctions mathématiques supportées
        self.math_functions = {
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "sqrt": math.sqrt,
            "log": math.log,
            "ln": math.log,
            "exp": math.exp,
            "abs": abs,
            "floor": math.floor,
            "ceil": math.ceil,
            "round": round,
        }

        # Constantes mathématiques
        self.math_constants = {
            "pi": math.pi,
            "π": math.pi,
            "e": math.e,
            "euler": math.e,
        }

    def is_calculation_request(self, text: str) -> bool:
        """Détecte si le texte est une demande de calcul"""
        text_lower = text.lower().strip()

        # Patterns de détection
        calc_patterns = [
            r"^(calcule|calcul|calcule moi|calculate|combien font?|combien fait|résultat|result)",
            r"^(qu[ae]l est le résultat|qu[ae]l est le résultat de|que fait|que font)",
            r"^\d+\s*[\+\-\*/]",  # Commence par un nombre et opération
            r"calcul",
            r"mathématique",
            r"addition|soustraction|multiplication|division",
            r"sqrt|racine",  # Détection de racine carrée
        ]

        for pattern in calc_patterns:
            if re.search(pattern, text_lower):
                return True

        # Détection de nombres avec opérations
        if re.search(r"\d+\s*[\+\-\*/\^%]\s*\d+", text):
            return True

        return False

    def extract_expression(self, text: str) -> str:
        """Extrait l'expression mathématique du texte"""
        text = text.strip()

        # Supprimer les mots de début - ordre important (plus longs d'abord)
        prefixes = [
            "calcule moi",
            "calcule",
            "combien font",
            "combien fait",
            "quel est le résultat de",
            "que fait",
            "que font",
            "résultat de",
            "calcul de",
            "calcul",
            "calculate",
            "mathématique",
        ]

        text_lower = text.lower()
        for prefix in prefixes:
            if text_lower.startswith(prefix):
                text = text[len(prefix) :].strip()
                break

        # Supprimer les mots parasites courants
        parasites = ["moi", "le", "la", "les", "de", "du", "des"]
        words = text.split()
        filtered_words = []
        for word in words:
            if word.lower() not in parasites or word.isdigit():
                filtered_words.append(word)
        text = " ".join(filtered_words)

        # Supprimer les mots de fin
        suffixes = ["?", "stp", "s'il te plaît", "please", "merci"]
        for suffix in suffixes:
            if text.lower().endswith(suffix):
                text = text[: -len(suffix)].strip()

        return text

    def normalize_expression(self, expression: str) -> str:
        """Normalise l'expression en remplaçant les mots français par des symboles"""
        expr = expression.lower()

        # Remplacer les nombres en français
        for french, number in self.french_numbers.items():
            expr = re.sub(r"\b" + re.escape(french) + r"\b", number, expr)

        # Remplacer les opérations en français
        for french, symbol in self.french_operations.items():
            expr = re.sub(r"\b" + re.escape(french) + r"\b", f" {symbol} ", expr)

        # Nettoyer les espaces multiples
        expr = re.sub(r"\s+", " ", expr).strip()

        # Corriger les patterns spéciaux
        expr = expr.replace("puissance de", "**")
        expr = expr.replace("à la puissance", "**")
        expr = expr.replace("au carré", "**2")
        expr = expr.replace("au cube", "**3")

        # Gérer sqrt: ajouter des parenthèses et multiplication implicite
        # Pattern: nombre + sqrt + nombre -> nombre * sqrt(nombre)
        expr = re.sub(r"(\d+)\s+sqrt\s+(\d+)", r"\1*sqrt(\2)", expr)
        # Pattern: sqrt + nombre -> sqrt(nombre)
        expr = re.sub(r"sqrt\s+(\d+)", r"sqrt(\1)", expr)

        return expr

    def safe_eval(self, expression: str) -> Union[float, int, str]:
        """Évaluation sécurisée d'expressions mathématiques"""
        try:
            # Nettoyer l'expression en préservant les espaces entre nombres et opérateurs
            expr = expression.strip()

            # Remplacer les fonctions mathématiques
            for func_name, func in self.math_functions.items():
                expr = expr.replace(func_name + "(", f"math.{func_name}(")

            # Remplacer les constantes
            for const_name, const_value in self.math_constants.items():
                expr = expr.replace(const_name, str(const_value))

            # Supprimer les espaces seulement après avoir traité les fonctions et constantes
            expr = expr.replace(" ", "")

            # Vérifier que l'expression ne contient que des caractères sûrs
            allowed_chars = set("0123456789+-*/.()%** \t")
            allowed_words = {
                "math",
                "sin",
                "cos",
                "tan",
                "sqrt",
                "log",
                "ln",
                "exp",
                "abs",
                "floor",
                "ceil",
                "round",
            }

            # Parser l'AST pour vérifier la sécurité
            try:
                tree = ast.parse(expr, mode="eval")
                # Vérifier que seules les opérations mathématiques sont utilisées
                for node in ast.walk(tree):
                    if (
                        isinstance(node, ast.Name)
                        and node.id not in allowed_words
                        and node.id not in self.math_constants
                    ):
                        return f"Erreur: Variable non autorisée '{node.id}'"
                    elif isinstance(node, ast.Call) and not (
                        isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "math"
                    ):
                        return "Erreur: Fonction non autorisée"
            except SyntaxError as e:
                return f"Erreur de syntaxe: {e.msg}"

            # Évaluer l'expression
            # Créer un contexte sécurisé
            safe_dict = {"__builtins__": {}, "math": math, **self.math_constants}

            result = eval(expr, safe_dict, {})

            # Formater le résultat
            if isinstance(result, float):
                if result.is_integer():
                    return int(result)
                else:
                    return round(result, 10)  # Limiter la précision

            return result

        except ZeroDivisionError:
            return "Erreur: Division par zéro"
        except OverflowError:
            return "Erreur: Résultat trop grand"
        except ValueError as e:
            return f"Erreur de valeur: {str(e)}"
        except Exception as e:
            return f"Erreur de calcul: {str(e)}"

    def calculate(self, text: str) -> Dict[str, Any]:
        """Fonction principale de calcul"""
        if not self.is_calculation_request(text):
            return {
                "is_calculation": False,
                "message": "Ce n'est pas une demande de calcul.",
            }

        # Extraire l'expression
        expression = self.extract_expression(text)
        if not expression:
            return {
                "is_calculation": True,
                "error": "Impossible d'extraire l'expression mathématique.",
                "original_text": text,
            }

        # Normaliser l'expression
        normalized_expr = self.normalize_expression(expression)

        # Calculer
        result = self.safe_eval(normalized_expr)

        return {
            "is_calculation": True,
            "original_text": text,
            "extracted_expression": expression,
            "normalized_expression": normalized_expr,
            "result": result,
            "success": not isinstance(result, str) or not result.startswith("Erreur"),
        }

    def symbols_to_french(self, expression: str) -> str:
        """Convertit les symboles mathématiques en français"""
        result = expression
        # Remplacer les fonctions mathématiques
        result = result.replace("sqrt", "racine carrée de")
        # Remplacer ** avant * pour éviter les conflits
        result = result.replace("**", " puissance ")
        result = result.replace("*", " fois ")
        result = result.replace("+", " plus ")
        result = result.replace("-", " moins ")
        result = result.replace("/", " divisé par ")
        result = result.replace("%", " modulo ")

        # Nettoyer les espaces multiples
        result = re.sub(r"\s+", " ", result).strip()
        return result

    def format_response(self, calc_result: Dict[str, Any]) -> str:
        """Formate la réponse de calcul pour l'utilisateur"""
        if not calc_result["is_calculation"]:
            return calc_result["message"]

        if not calc_result.get("success", False):
            return f"❌ {calc_result['result']}"

        result = calc_result["result"]
        original = calc_result["original_text"]
        expression = calc_result["extracted_expression"]

        # Convertir les symboles en français pour l'affichage
        expression_french = self.symbols_to_french(expression)

        # Formatage du résultat
        if isinstance(result, (int, float)):
            if isinstance(result, float) and result.is_integer():
                result_str = str(int(result))
            else:
                result_str = f"{result:,}".replace(",", " ")  # Séparateur de milliers
        else:
            result_str = str(result)

        response = f"Le résultat de {expression_french} est **{result_str}**"

        # Ajouter des infos supplémentaires pour grands nombres
        if isinstance(result, (int, float)) and abs(result) >= 1000000:
            if abs(result) >= 1000000000:
                response += f" ({result/1000000000:.2f} milliards)"
            elif abs(result) >= 1000000:
                response += f" ({result/1000000:.2f} millions)"

        return response


# Instance globale du calculateur
intelligent_calculator = IntelligentCalculator()
