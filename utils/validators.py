"""
Validateurs et utilitaires de validation
"""

import re
import os
import ast
import json
from pathlib import Path
from typing import Dict, Any, List


class InputValidator:
    """
    Validateur d'entrées utilisateur
    """

    @staticmethod
    def validate_file_path(file_path: str) -> Dict[str, Any]:
        """
        Valide un chemin de fichier

        Args:
            file_path: Chemin à valider

        Returns:
            Résultat de la validation
        """
        result = {"valid": True, "errors": [], "warnings": []}

        if not file_path or not file_path.strip():
            result["valid"] = False
            result["errors"].append("Chemin de fichier vide")
            return result

        path = Path(file_path)

        # Vérification de l'existence
        if not path.exists():
            result["warnings"].append("Le fichier n'existe pas")

        # Vérification de la longueur du chemin
        if len(str(path)) > 260:  # Limite Windows
            result["warnings"].append(
                "Chemin très long (peut causer des problèmes sur Windows)"
            )

        # Caractères invalides
        invalid_chars = '<>"|?*'
        for char in invalid_chars:
            if char in file_path:
                result["valid"] = False
                result["errors"].append(f"Caractère invalide trouvé: {char}")

        return result

    @staticmethod
    def validate_query(
        query: str, min_length: int = 1, max_length: int = 10000
    ) -> Dict[str, Any]:
        """
        Valide une requête utilisateur

        Args:
            query: Requête à valider
            min_length: Longueur minimale
            max_length: Longueur maximale

        Returns:
            Résultat de la validation
        """
        result = {"valid": True, "errors": [], "warnings": []}

        if not query or not query.strip():
            result["valid"] = False
            result["errors"].append("Requête vide")
            return result

        query_clean = query.strip()

        # Vérification de la longueur
        if len(query_clean) < min_length:
            result["valid"] = False
            result["errors"].append(
                f"Requête trop courte (minimum {min_length} caractères)"
            )

        if len(query_clean) > max_length:
            result["valid"] = False
            result["errors"].append(
                f"Requête trop longue (maximum {max_length} caractères)"
            )

        # Caractères suspects
        suspicious_patterns = [
            r"<script.*?>.*?</script>",  # Scripts
            r"javascript:",  # JavaScript inline
            r"eval\(",  # eval() functions
            r"exec\(",  # exec() functions
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, query_clean, re.IGNORECASE):
                result["warnings"].append("Contenu potentiellement dangereux détecté")
                break

        return result

    @staticmethod
    def validate_code(code: str, language: str) -> Dict[str, Any]:
        """
        Valide du code source

        Args:
            code: Code à valider
            language: Langage de programmation

        Returns:
            Résultat de la validation
        """
        result = {"valid": True, "errors": [], "warnings": []}

        if not code or not code.strip():
            result["valid"] = False
            result["errors"].append("Code vide")
            return result

        # Validation spécifique Python
        if language.lower() == "python":

            try:
                ast.parse(code)
            except SyntaxError as e:
                result["valid"] = False
                result["errors"].append(f"Erreur de syntaxe Python: {e}")

            except ValueError as e:
                result["warnings"].append(f"Problème d'analyse: {e}")

        # Vérifications de sécurité
        dangerous_patterns = {
            "python": [
                r"exec\s*\(",
                r"eval\s*\(",
                r"__import__\s*\(",
                r"open\s*\(",
                r"file\s*\(",
                r"input\s*\(",
                r"raw_input\s*\(",
            ],
            "javascript": [
                r"eval\s*\(",
                r"Function\s*\(",
                r"setTimeout\s*\(",
                r"setInterval\s*\(",
            ],
        }

        patterns = dangerous_patterns.get(language.lower(), [])
        for pattern in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                result["warnings"].append(
                    f"Fonction potentiellement dangereuse détectée: {pattern}"
                )

        return result

    @staticmethod
    def validate_filename(filename: str) -> Dict[str, Any]:
        """
        Valide un nom de fichier

        Args:
            filename: Nom de fichier à valider

        Returns:
            Résultat de la validation
        """
        result = {"valid": True, "errors": [], "warnings": []}

        if not filename or not filename.strip():
            result["valid"] = False
            result["errors"].append("Nom de fichier vide")
            return result

        # Caractères interdits
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            if char in filename:
                result["valid"] = False
                result["errors"].append(f"Caractère invalide: {char}")

        # Noms réservés Windows
        reserved_names = [
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        ]

        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved_names:
            result["valid"] = False
            result["errors"].append(f"Nom réservé système: {name_without_ext}")

        # Longueur
        if len(filename) > 255:
            result["valid"] = False
            result["errors"].append("Nom de fichier trop long (>255 caractères)")

        # Espaces en début/fin
        if filename != filename.strip():
            result["warnings"].append("Espaces en début ou fin de nom")

        return result


class SecurityValidator:
    """
    Validateur de sécurité
    """

    @staticmethod
    def scan_for_malicious_content(content: str) -> Dict[str, Any]:
        """
        Scanne le contenu pour détecter du contenu malveillant

        Args:
            content: Contenu à scanner

        Returns:
            Résultat du scan
        """
        result = {"safe": True, "threats": [], "warnings": []}

        # Patterns suspects
        malicious_patterns = [
            (r"<script.*?>.*?</script>", "Script HTML détecté"),
            (r"javascript:", "JavaScript inline détecté"),
            (r"data:text/html", "HTML en data URI détecté"),
            (r"eval\s*\(", "Fonction eval() détectée"),
            (r"exec\s*\(", "Fonction exec() détectée"),
            (r"system\s*\(", "Appel système détecté"),
            (r"shell_exec\s*\(", "Exécution shell détectée"),
            (r"`.*`", "Commande shell backtick détectée"),
            (r"\$\(.*\)", "Substitution de commande détectée"),
        ]

        for pattern, description in malicious_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                result["safe"] = False
                result["threats"].append(description)

        # URLs suspectes
        url_patterns = [
            r"http://[^\s]+",
            r"https://[^\s]+",
            r"ftp://[^\s]+",
        ]

        for pattern in url_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                result["warnings"].append(f"URLs détectées: {len(matches)}")

        return result

    @staticmethod
    def validate_file_upload(
        file_path: str, allowed_extensions: List[str] = None
    ) -> Dict[str, Any]:
        """
        Valide un fichier uploadé

        Args:
            file_path: Chemin du fichier
            allowed_extensions: Extensions autorisées

        Returns:
            Résultat de la validation
        """
        result = {"safe": True, "errors": [], "warnings": []}

        if not os.path.exists(file_path):
            result["safe"] = False
            result["errors"].append("Fichier non trouvé")
            return result

        path = Path(file_path)

        # Vérification de l'extension
        if allowed_extensions:
            if path.suffix.lower() not in [ext.lower() for ext in allowed_extensions]:
                result["safe"] = False
                result["errors"].append(f"Extension non autorisée: {path.suffix}")

        # Taille du fichier
        file_size = path.stat().st_size
        max_size = 50 * 1024 * 1024  # 50MB

        if file_size > max_size:
            result["safe"] = False
            result["errors"].append(
                f"Fichier trop volumineux: {file_size / (1024*1024):.1f}MB"
            )

        # Double extension
        if len(path.suffixes) > 1:
            result["warnings"].append("Fichier avec double extension détecté")

        return result


class DataValidator:
    """
    Validateur de données
    """

    @staticmethod
    def validate_json(json_string: str) -> Dict[str, Any]:
        """
        Valide une chaîne JSON

        Args:
            json_string: Chaîne JSON à valider

        Returns:
            Résultat de la validation
        """
        result = {"valid": True, "errors": [], "data": None}

        try:
            result["data"] = json.loads(json_string)
        except json.JSONDecodeError as e:
            result["valid"] = False
            result["errors"].append(f"JSON invalide: {e}")

        return result

    @staticmethod
    def validate_email(email: str) -> Dict[str, Any]:
        """
        Valide une adresse email

        Args:
            email: Adresse email à valider

        Returns:
            Résultat de la validation
        """
        result = {"valid": True, "errors": []}

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(email_pattern, email):
            result["valid"] = False
            result["errors"].append("Format d'email invalide")

        return result

    @staticmethod
    def validate_url(url: str) -> Dict[str, Any]:
        """
        Valide une URL

        Args:
            url: URL à valider

        Returns:
            Résultat de la validation
        """
        result = {"valid": True, "errors": [], "warnings": []}

        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"

        if not re.match(url_pattern, url, re.IGNORECASE):
            result["valid"] = False
            result["errors"].append("Format d'URL invalide")

        # Vérification du protocole
        if not url.lower().startswith(("http://", "https://")):
            result["warnings"].append("Protocole non sécurisé")

        return result
