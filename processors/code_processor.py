"""
Processeur de code source
Analyse, validation et génération de code
"""

import os
import ast
import re
from typing import Dict, Any
from pathlib import Path


class CodeProcessor:
    """
    Processeur pour les fichiers de code source
    """

    def __init__(self):
        """
        Initialise le processeur de code
        """
        self.supported_languages = {
            ".py": "python",
            ".html": "html",
            ".css": "css",
            ".js": "javascript",
            ".json": "json",
            ".xml": "xml",
            ".sql": "sql",
            ".md": "markdown",
            ".txt": "text",
        }
        self.supported_extensions = [
            ".py",
            ".js",
            ".html",
            ".css",
            ".java",
            ".c",
            ".cpp",
            ".cs",
            ".php",
        ]
        self.language_extensions = {
            "python": [".py"],
            "javascript": [".js", ".ts"],
            "html": [".html", ".htm"],
            "css": [".css"],
            "java": [".java"],
            "c": [".c", ".h"],
            "cpp": [".cpp", ".hpp"],
            "csharp": [".cs"],
            "php": [".php"],
        }

    def generate_detailed_explanation(
        self, file_path: str, real_file_name: str = None
    ) -> str:
        """
        Génère une explication détaillée, structurée et pédagogique d'un fichier Python.
        """
        analysis = self.analyze_code(file_path)
        if not analysis.get("success"):
            return f"**Erreur lors de l'analyse du fichier** : {analysis.get('error', 'Inconnue')}"

        content = analysis.get("content", "")
        language = analysis.get("language", "unknown")
        lines = content.splitlines()
        docstring = ""

        # Chercher un docstring de module
        if lines and lines[0].strip().startswith('"""'):
            docstring_lines = []
            for line in lines[1:]:
                if line.strip().startswith('"""'):
                    break
                docstring_lines.append(line)
            docstring = "\n".join(docstring_lines).strip()

        explanation = []
        # Titre principal
        file_display = real_file_name if real_file_name else os.path.basename(file_path)
        explanation.append(f"# Explication détaillée du fichier `{file_display}`\n")

        # 1. Objectif général
        explanation.append("## 1. Objectif général\n")
        if docstring:
            # CORRECTION : Enlever le mot "docstring" et garder juste le contenu dans '''
            explanation.append(f"'''{docstring}'''\n")
        else:
            explanation.append(
                "> Ce fichier ne contient pas de docstring de module explicite. Il s'agit d'un fichier de code en Python.\n"
            )

        # 2. Modules et bibliothèques utilisés
        explanation.append("## 2. Modules et bibliothèques utilisés\n")
        imports = analysis.get("imports", [])
        if imports:
            for imp in imports:
                if imp["type"] == "import":
                    mod = imp["module"]
                    alias = f" (alias : `{imp['alias']}`)" if imp["alias"] else ""
                    explanation.append(f"- `{mod}`{alias}")
                elif imp["type"] == "from_import":
                    mod = imp["module"]
                    name = imp["name"]
                    alias = f" (alias : `{imp['alias']}`)" if imp["alias"] else ""
                    explanation.append(f"- `from {mod} import {name}`{alias}")
        else:
            explanation.append("Aucun import détecté.")

        # CORRECTION : Ajouter retour à la ligne AVANT le titre 3
        explanation.append("\n## 3. Structure principale\n")
        classes = analysis.get("classes", [])
        functions = analysis.get("functions", [])

        if classes:
            explanation.append(f"Le fichier contient **{len(classes)} classe(s)** :\n")
            for c in classes:
                bases = (
                    f" (hérite de {', '.join([f'`{b}`' for b in c['bases']])})"
                    if c["bases"]
                    else ""
                )
                # CORRECTION : Enlever le mot "docstring"
                doc = f"\n'''{c['docstring']}'''" if c["docstring"] else ""
                explanation.append(
                    f"- Classe `{c['name']}`{bases} (ligne {c['line']}){doc}"
                )
        else:
            explanation.append("Aucune classe définie dans ce fichier.")

        if functions:
            explanation.append(
                f"\nLe fichier contient **{len(functions)} fonction(s)** :\n"
            )
            for f in functions:
                args_list = ", ".join([f"`{a}`" for a in f["args"]])

                # Gestion spéciale de la docstring pour extraire Args: et Returns:
                doc_formatted = ""
                if f["docstring"]:
                    doc_lines = f["docstring"].split("\n")
                    formatted_lines = []
                    for line in doc_lines:
                        line_stripped = line.strip()
                        # CIBLER SPÉCIFIQUEMENT Args: et Returns: en début de ligne
                        if line_stripped == "Args:" or line_stripped.startswith(
                            "Args:"
                        ):
                            formatted_lines.append(line.replace("Args:", "**Args:**"))
                        elif line_stripped == "Returns:" or line_stripped.startswith(
                            "Returns:"
                        ):
                            formatted_lines.append(
                                line.replace("Returns:", "**Returns:**")
                            )
                        else:
                            formatted_lines.append(line)
                    # CORRECTION : Enlever le mot "docstring"
                    doc_formatted = f"\n'''{chr(10).join(formatted_lines)}'''"

                explanation.append(
                    f"- Fonction `{f['name']}`(args: {args_list}) (ligne {f['line']}){doc_formatted}"
                )
        else:
            explanation.append("Aucune fonction définie dans ce fichier.")

        # 4. Points particuliers
        explanation.append(
            "\n## 4. Points particuliers\n"
        )  # AJOUT d'un retour à la ligne ici aussi
        if "try" in content or "except" in content:
            explanation.append(
                "- Ce fichier gère des exceptions avec des blocs `try/except`."
            )
        if "fallback" in content.lower():
            explanation.append(
                "- Des mécanismes de **fallback** sont présents pour garantir la robustesse."
            )
        if "class " in content and "__init__" in content:
            explanation.append(
                "- Utilisation de classes avec constructeurs (`__init__`) pour structurer le code."
            )
        if "validate" in content or "validation" in content:
            explanation.append("- Le code inclut des fonctions de **validation**.")
        if "analyze" in content or "analyse" in content:
            explanation.append("- Le code inclut des fonctions d'**analyse** de code.")
        if "supported_languages" in content:
            explanation.append("- Ce fichier gère plusieurs langages de programmation.")

        # CORRECTION : Ajouter retour à la ligne AVANT le titre 5
        explanation.append("\n## 5. Résumé technique\n")
        explanation.append(f"- **Langage détecté :** {language}")
        explanation.append(
            f"- **Nombre de lignes :** {analysis.get('line_count', '?')}"
        )
        explanation.append(
            f"- **Nombre de caractères :** {analysis.get('character_count', '?')}"
        )
        explanation.append(
            f"- **Taille du fichier :** {analysis.get('file_size', '?')} octets"
        )

        return "\n".join(explanation)

    def read_code_file(self, file_path: str) -> str:
        """
        Lit le contenu d'un fichier de code source

        Args:
            file_path: Chemin du fichier

        Returns:
            str: Contenu du fichier
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except UnicodeDecodeError:
            # Essai avec une autre encodage si utf-8 échoue
            try:
                with open(file_path, "r", encoding="latin-1") as file:
                    return file.read()
            except Exception as e:
                return f"Erreur de lecture du fichier: {str(e)}"
        except Exception as e:
            return f"Erreur de lecture du fichier: {str(e)}"

    def analyze_code(self, file_path: str) -> Dict[str, Any]:
        """
        Analyse un fichier de code

        Args:
            file_path: Chemin vers le fichier de code

        Returns:
            Analyse du code
        """
        if not os.path.exists(file_path):
            return {"error": "Fichier non trouvé"}

        file_ext = Path(file_path).suffix.lower()
        language = self.supported_languages.get(file_ext, "unknown")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    content = f.read()
            except Exception as e:
                return {"error": f"Impossible de lire le fichier: {str(e)}"}

        analysis = {
            "success": True,
            "file_path": file_path,
            "language": language,
            "file_size": os.path.getsize(file_path),
            "line_count": len(content.splitlines()),
            "character_count": len(content),
            "content": content,
        }

        # Analyse spécifique selon le langage
        if language == "python":
            analysis.update(self._analyze_python(content))
        elif language == "html":
            analysis.update(self._analyze_html(content))
        elif language == "css":
            analysis.update(self._analyze_css(content))
        elif language == "javascript":
            analysis.update(self._analyze_javascript(content))

        return analysis

    def _analyze_python(self, content: str) -> Dict[str, Any]:
        """
        Analyse spécifique du code Python
        """
        analysis = {"functions": [], "classes": [], "imports": [], "syntax_errors": []}

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis["functions"].append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "args": [arg.arg for arg in node.args.args],
                            "docstring": ast.get_docstring(node),
                        }
                    )

                elif isinstance(node, ast.ClassDef):
                    analysis["classes"].append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "bases": [
                                base.id if isinstance(base, ast.Name) else str(base)
                                for base in node.bases
                            ],
                            "docstring": ast.get_docstring(node),
                        }
                    )

                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            analysis["imports"].append(
                                {
                                    "module": alias.name,
                                    "alias": alias.asname,
                                    "line": node.lineno,
                                    "type": "import",
                                }
                            )
                    else:  # ImportFrom
                        for alias in node.names:
                            analysis["imports"].append(
                                {
                                    "module": node.module,
                                    "name": alias.name,
                                    "alias": alias.asname,
                                    "line": node.lineno,
                                    "type": "from_import",
                                }
                            )

        except SyntaxError as e:
            analysis["syntax_errors"].append(
                {"message": str(e), "line": e.lineno, "offset": e.offset}
            )

        return analysis

    def _analyze_html(self, content: str) -> Dict[str, Any]:
        """
        Analyse spécifique du code HTML
        """
        analysis = {"tags": [], "links": [], "images": [], "forms": []}

        # Extraction des tags
        tag_pattern = r"<(\w+)([^>]*)>"
        tags = re.findall(tag_pattern, content)
        analysis["tags"] = [
            {"tag": tag[0], "attributes": tag[1].strip()} for tag in tags
        ]

        # Extraction des liens
        link_pattern = r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>'
        analysis["links"] = re.findall(link_pattern, content)

        # Extraction des images
        img_pattern = r'<img[^>]*src=["\']([^"\']*)["\'][^>]*>'
        analysis["images"] = re.findall(img_pattern, content)

        # Extraction des formulaires
        form_pattern = r"<form[^>]*>"
        analysis["forms"] = len(re.findall(form_pattern, content))

        return analysis

    def _analyze_css(self, content: str) -> Dict[str, Any]:
        """
        Analyse spécifique du code CSS
        """
        analysis = {"selectors": [], "properties": [], "media_queries": []}

        # Extraction des sélecteurs
        selector_pattern = r"([^{]+)\s*{"
        selectors = re.findall(selector_pattern, content)
        analysis["selectors"] = [sel.strip() for sel in selectors]

        # Extraction des propriétés
        property_pattern = r"(\w+)\s*:\s*([^;]+);"
        properties = re.findall(property_pattern, content)
        analysis["properties"] = [
            {"property": prop[0], "value": prop[1]} for prop in properties
        ]

        # Extraction des media queries
        media_pattern = r"@media\s+([^{]+)"
        analysis["media_queries"] = re.findall(media_pattern, content)

        return analysis

    def _analyze_javascript(self, content: str) -> Dict[str, Any]:
        """
        Analyse spécifique du code JavaScript
        """
        analysis = {"functions": [], "variables": [], "comments": []}

        # Extraction des fonctions
        function_pattern = r"function\s+(\w+)\s*\([^)]*\)"
        functions = re.findall(function_pattern, content)
        analysis["functions"] = functions

        # Extraction des variables
        var_pattern = r"(?:var|let|const)\s+(\w+)"
        variables = re.findall(var_pattern, content)
        analysis["variables"] = variables

        # Extraction des commentaires
        comment_pattern = r"//.*?$|/\*.*?\*/"
        comments = re.findall(comment_pattern, content, re.MULTILINE | re.DOTALL)
        analysis["comments"] = comments

        return analysis

    def validate_code(self, content: str, language: str) -> Dict[str, Any]:
        """
        Valide le code selon le langage

        Args:
            content: Contenu du code
            language: Langage de programmation

        Returns:
            Résultat de la validation
        """
        validation = {"valid": True, "errors": [], "warnings": []}

        if language == "python":
            try:
                ast.parse(content)
            except SyntaxError as e:
                validation["valid"] = False
                validation["errors"].append(
                    {
                        "type": "SyntaxError",
                        "message": str(e),
                        "line": e.lineno,
                        "offset": e.offset,
                    }
                )

        # Autres validations peuvent être ajoutées ici

        return validation

    def extract_functions(self, file_path: str) -> Dict[str, Any]:
        """
        Extrait toutes les fonctions d'un fichier

        Args:
            file_path: Chemin vers le fichier

        Returns:
            Liste des fonctions trouvées
        """
        analysis = self.analyze_code(file_path)

        if not analysis.get("success"):
            return analysis

        return {
            "success": True,
            "file_path": file_path,
            "language": analysis["language"],
            "functions": analysis.get("functions", []),
        }

    def search_in_code(self, file_path: str, search_term: str) -> Dict[str, Any]:
        """
        Recherche un terme dans le code

        Args:
            file_path: Chemin vers le fichier
            search_term: Terme à rechercher

        Returns:
            Résultats de la recherche
        """
        analysis = self.analyze_code(file_path)

        if not analysis.get("success"):
            return analysis

        content = analysis["content"]
        lines = content.splitlines()
        results = []

        for line_num, line in enumerate(lines, 1):
            if search_term.lower() in line.lower():
                results.append(
                    {
                        "line_number": line_num,
                        "line_content": line.strip(),
                        "context": {
                            "before": lines[max(0, line_num - 2) : line_num - 1],
                            "after": lines[line_num : min(len(lines), line_num + 2)],
                        },
                    }
                )

        return {
            "success": True,
            "search_term": search_term,
            "results": results,
            "total_matches": len(results),
        }

    def get_code_metrics(self, file_path: str) -> Dict[str, Any]:
        """
        Calcule des métriques sur le code

        Args:
            file_path: Chemin vers le fichier

        Returns:
            Métriques du code
        """
        analysis = self.analyze_code(file_path)

        if not analysis.get("success"):
            return analysis

        content = analysis["content"]
        lines = content.splitlines()

        # Comptage des lignes
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith("#"))
        code_lines = total_lines - blank_lines - comment_lines

        metrics = {
            "success": True,
            "file_path": file_path,
            "language": analysis["language"],
            "total_lines": total_lines,
            "code_lines": code_lines,
            "blank_lines": blank_lines,
            "comment_lines": comment_lines,
            "complexity_score": self._calculate_complexity(
                content
            ),
        }

        # Métriques spécifiques Python
        if analysis["language"] == "python":
            metrics.update(
                {
                    "function_count": len(analysis.get("functions", [])),
                    "class_count": len(analysis.get("classes", [])),
                    "import_count": len(analysis.get("imports", [])),
                }
            )

        return metrics

    def _calculate_complexity(self, content: str) -> int:
        """
        Calcule un score de complexité simple
        """
        complexity = 0

        # Mots-clés augmentant la complexité
        complex_keywords = [
            "if",
            "elif",
            "else",
            "for",
            "while",
            "try",
            "except",
            "with",
        ]

        for keyword in complex_keywords:
            complexity += content.count(keyword)

        return complexity

    def detect_language(self, file_path: str = None, content: str = None) -> str:
        """
        Détecte le langage de programmation d'un fichier ou d'un contenu

        Args:
            file_path: Chemin du fichier (optionnel)
            content: Contenu du code (optionnel)

        Returns:
            str: Nom du langage détecté
        """
        # Détection par extension de fichier
        if file_path:
            ext = Path(file_path).suffix.lower()
            if ext in self.supported_languages:
                return self.supported_languages[ext]

        # Si pas de fichier ou extension non reconnue, tenter de détecter par contenu
        if content:
            # Indices Python
            if re.search(r"def\s+\w+\s*\(.*\):", content) or re.search(
                r"import\s+\w+", content
            ):
                return "python"
            # Indices JavaScript
            elif re.search(r"function\s+\w+\s*\(.*\)", content) or re.search(
                r"let|const|var\s+\w+\s*=", content
            ):
                return "javascript"
            # Indices HTML
            elif re.search(r"<!DOCTYPE\s+html>", content, re.IGNORECASE) or re.search(
                r"<html.*>.*</html>", content, re.DOTALL
            ):
                return "html"
            # Indices CSS
            elif re.search(r"[\.\#]?[\w-]+\s*{[^}]*}", content):
                return "css"

        # Par défaut
        return "unknown"

    def is_supported(self, file_path: str) -> bool:
        """
        Vérifie si le fichier est supporté

        Args:
            file_path: Chemin vers le fichier

        Returns:
            True si le fichier est supporté
        """
        return Path(file_path).suffix.lower() in self.supported_languages

    def validate_syntax(self, file_path: str) -> Dict[str, Any]:
        """
        Valide la syntaxe d'un fichier de code source

        Args:
            file_path: Chemin vers le fichier de code

        Returns:
            Résultat de la validation
        """
        file_ext = Path(file_path).suffix.lower()
        language = self.supported_languages.get(file_ext, "unknown")

        if language != "python":
            return {
                "error": f"La validation de syntaxe n'est pas disponible pour le langage '{language}'"
            }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            ast.parse(content)
            return {"success": True, "message": "La syntaxe est valide."}
        except SyntaxError as e:
            return {"error": f"Erreur de syntaxe: {str(e)}"}
        except Exception as e:
            return {"error": f"Erreur lors de la validation: {str(e)}"}

    def extract_text_from_file(self, file_path: str) -> str:
        """
        Extrait le texte d'un fichier de code (compatible avec l'interface GUI)

        Args:
            file_path: Chemin vers le fichier de code

        Returns:
            Contenu du fichier de code
        """
        return self.read_code_file(file_path)
