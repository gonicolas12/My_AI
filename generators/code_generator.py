"""
Générateur de code
Création et assistance à la programmation avec Ollama
"""

import os
import re
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING

# Import du LLM local (Ollama)
if TYPE_CHECKING:
    from models.local_llm import LocalLLM

try:
    from models.local_llm import LocalLLM

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


class CodeGenerator:
    """
    Générateur de code dans différents langages utilisant Ollama
    """

    def __init__(self, llm: Optional[LocalLLM] = None):
        """
        Initialise le générateur de code

        Args:
            llm: Instance de LocalLLM (Ollama) pour la génération dynamique
        """
        self.llm = llm if llm else (LocalLLM() if OLLAMA_AVAILABLE else None)
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """
        Charge les templates de code
        """
        return {
            "python": {
                "class": '''class {class_name}:
    """
    {description}
    """
    
    def __init__(self{init_params}):
        """
        Initialise {class_name}
        """
        {init_body}
    
    {methods}
''',
                "function": '''def {function_name}({parameters}){return_type}:
    """
    {description}
    
    Args:
        {args_doc}
    
    Returns:
        {return_doc}
    """
    {body}
''',
                "script": '''#!/usr/bin/env python3
"""
{description}
"""

{imports}

def main():
    """
    Fonction principale
    """
    {main_body}

if __name__ == "__main__":
    main()
''',
            },
            "html": {
                "page": """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {css}
    </style>
</head>
<body>
    {body}
    
    <script>
        {javascript}
    </script>
</body>
</html>
""",
                "component": """<div class="{class_name}">
    {content}
</div>
""",
            },
            "css": {
                "component": """.{component_name} {{
    {properties}
}}
""",
                "responsive": """/* Mobile First */
{base_styles}

/* Tablet */
@media (min-width: 768px) {{
    {tablet_styles}
}}

/* Desktop */
@media (min-width: 1024px) {{
    {desktop_styles}
}}
""",
            },
            "javascript": {
                "function": """function {function_name}({parameters}) {{
    {body}
}}
""",
                "class": """class {class_name} {{
    constructor({constructor_params}) {{
        {constructor_body}
    }}
    
    {methods}
}}
""",
            },
        }

    async def generate_code(
        self, query: str, filename: Optional[str] = None, is_interrupted_callback=None,
        memory: str = "",
    ) -> Dict[str, Any]:
        """
        Génère du code basé sur la requête en utilisant Ollama

        Args:
            query: Demande de génération de code
            filename: Nom de fichier suggéré (optionnel)
            is_interrupted_callback: Fonction pour vérifier si l'opération est interrompue
            memory: Faits mémorisés sur l'utilisateur, une ligne chacun (voir
                _generate_with_ollama)

        Returns:
            Code généré avec métadonnées
        """
        try:
            # Analyse de la requête pour extraire le langage et le type
            code_info = self._analyze_code_request(query)
            language = code_info.get("language", "python")

            # Extraire le nom de fichier de la requête si non fourni
            if not filename:
                filename = self._extract_filename(query, language)

            # 🤖 Génération avec Ollama si disponible
            if self.llm and OLLAMA_AVAILABLE:
                # Vérifier l'interruption AVANT de démarrer la génération Ollama
                if is_interrupted_callback and is_interrupted_callback():
                    print("⚠️ [CodeGenerator] Interruption détectée AVANT génération Ollama")
                    return {
                        "success": False,
                        "interrupted": True,
                        "message": "⚠️ Génération interrompue par l'utilisateur.",
                    }

                print(f"🚀 [CodeGenerator] Démarrage génération Ollama pour {filename}...")
                code = await self._generate_with_ollama(
                    query, language, code_info, is_interrupted_callback, memory
                )

                # Vérifier l'interruption APRÈS la génération Ollama
                if is_interrupted_callback and is_interrupted_callback():
                    print("⚠️ [CodeGenerator] Interruption détectée APRÈS génération Ollama")
                    return {
                        "success": False,
                        "interrupted": True,
                        "message": "⚠️ Génération interrompue par l'utilisateur.",
                    }

                if code:
                    # Vérifier l'interruption AVANT de sauvegarder
                    if is_interrupted_callback and is_interrupted_callback():
                        print("⚠️ [CodeGenerator] Interruption détectée AVANT sauvegarde")
                        return {
                            "success": False,
                            "interrupted": True,
                            "message": "⚠️ Génération interrompue par l'utilisateur.",
                        }

                    print(f"💾 [CodeGenerator] Sauvegarde de {filename}...")
                    # Sauvegarder automatiquement le fichier
                    save_result = await self.save_code(
                        {"code": code, "language": language}, filename
                    )

                    return {
                        "success": True,
                        "code": code,
                        "language": language,
                        "filename": filename,
                        "file_path": save_result.get("file_path"),
                        "method": "ollama",
                        "message": f"✅ Fichier {filename} généré avec succès !",
                    }

            # Fallback sur templates si Ollama non disponible
            return await self._generate_with_templates(query, language, filename)

        except Exception as e:
            return {
                "error": f"Erreur lors de la génération de code: {str(e)}",
                "success": False,
            }

    async def _generate_with_ollama(
        self, query: str, language: str, _code_info: Dict, is_interrupted_callback=None,
        memory: str = "",
    ) -> Optional[str]:
        """
        Génère du code en utilisant Ollama

        Args:
            query: Requête utilisateur
            language: Langage de programmation
            code_info: Informations extraites de la requête
            is_interrupted_callback: Fonction pour vérifier si l'opération est interrompue
            memory: Faits mémorisés sur l'utilisateur, une ligne chacun : sans
                eux, « un fichier qui affiche mon prénom » ignorait son prénom

        Returns:
            Code généré ou None
        """
        try:
            # Vérifier l'interruption avant de commencer
            if is_interrupted_callback and is_interrupted_callback():
                print("⚠️ [CodeGenerator] Génération interrompue avant l'appel Ollama")
                return None

            # Construire un prompt optimisé pour la génération de code
            system_prompt = f"""Tu es un expert en programmation {language}.
Génère du code propre, bien commenté et fonctionnel.
Réponds UNIQUEMENT avec le code, sans explications avant ou après.
Le code doit être prêt à être exécuté."""

            # Faits mémorisés (l'appelant ne les passe que si la demande parle de
            # l'utilisateur) : rien d'autre que ce qu'elle réclame, sans quoi
            # le modèle les plaçait tous en en-tête, son chat compris
            memory_block = ""
            if memory and memory.strip():
                memory_block = (
                    "Ce que tu sais de l'utilisateur (sa mémoire) : n'en reprends que ce "
                    "que la demande réclame (son prénom si elle parle de « mon prénom », "
                    "par exemple), et rien d'autre, ni en commentaire ni en en-tête :\n"
                    f"{memory.strip()}\n\n"
                )

            # Prompt utilisateur détaillé
            user_prompt = f"""Génère un fichier {language} complet pour : {query}

Exigences :
- Code fonctionnel et testé
- Commentaires explicatifs
- Bonnes pratiques du langage {language}
- Structure claire et organisée

{memory_block}Génère le code maintenant :"""

            # Appel à Ollama (synchrone car LocalLLM.generate est synchrone)
            loop = asyncio.get_event_loop()
            code = await loop.run_in_executor(
                None, lambda: self.llm.generate(user_prompt, system_prompt)
            )

            # Vérifier l'interruption après la génération
            if is_interrupted_callback and is_interrupted_callback():
                print("⚠️ [CodeGenerator] Génération interrompue après l'appel Ollama")
                return None

            if code:
                # Nettoyer le code (enlever les marqueurs markdown si présents)
                code = self._clean_generated_code(code, language)
                return code

            return None

        except Exception as e:
            print(f"⚠️ Erreur génération Ollama: {e}")
            return None

    def _clean_generated_code(self, code: str, _language: str) -> str:
        """
        Nettoie le code généré (enlève les marqueurs markdown, etc.)

        Args:
            code: Code brut généré
            language: Langage de programmation

        Returns:
            Code nettoyé
        """
        # Enlever les blocs de code markdown
        code = re.sub(r"^```\w*\n", "", code)
        code = re.sub(r"\n```$", "", code)
        code = code.strip()

        return code

    def _extract_filename(self, query: str, language: str) -> str:
        """
        Extrait ou génère un nom de fichier depuis la requête

        Args:
            query: Requête utilisateur
            language: Langage de programmation

        Returns:
            Nom de fichier
        """
        # Rechercher un nom de fichier explicite dans la requête
        # Ex: "génère moi un fichier main.py qui..."
        filename_match = re.search(
            r"fichier\s+([a-zA-Z0-9_\-]+\.\w+)", query, re.IGNORECASE
        )
        if filename_match:
            return filename_match.group(1)

        # Si aucun nom explicite, demander à Ollama de suggérer un nom pertinent
        if self.llm and hasattr(self.llm, 'generate'):
            try:
                suggestion_prompt = f"""Basé sur cette description : "{query}"

Suggère UN SEUL nom de fichier court et descriptif en {language}.
Réponds UNIQUEMENT avec le nom du fichier (sans chemin, juste le nom avec extension).
Exemple: calculator.py ou sorting_algorithm.py

Nom de fichier :"""

                suggested_name = self.llm.generate(suggestion_prompt, system_prompt="Tu es un assistant qui suggère des noms de fichiers pertinents. Réponds uniquement avec le nom du fichier.")

                if suggested_name:
                    # Nettoyer la suggestion (enlever espaces, guillemets, etc.)
                    suggested_name = suggested_name.strip().strip('"').strip("'").strip()
                    # Vérifier que c'est bien un nom de fichier valide
                    if re.match(r'^[a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+$', suggested_name):
                        print(f"📝 Nom suggéré par Ollama: {suggested_name}")
                        return suggested_name
            except Exception as e:
                print(f"⚠️ Erreur suggestion nom: {e}")

        # Fallback: générer un nom basé sur les mots-clés
        keywords = re.findall(r"\b([a-zA-Z]{3,})\b", query.lower())
        if keywords:
            base_name = (
                keywords[0]
                if keywords[0] not in ["fichier", "code", "script", "programme", "génère", "crée"]
                else (keywords[1] if len(keywords) > 1 else "generated")
            )
        else:
            base_name = "generated"

        # Extension selon le langage
        extensions = {
            "python": "py",
            "javascript": "js",
            "html": "html",
            "css": "css",
            "java": "java",
            "cpp": "cpp",
            "c": "c",
        }
        ext = extensions.get(language, "txt")

        return f"{base_name}.{ext}"

    async def _generate_with_templates(
        self, query: str, language: str, _filename: str
    ) -> Dict[str, Any]:
        """
        Génère du code avec les templates (fallback)

        Args:
            query: Requête utilisateur
            language: Langage de programmation
            filename: Nom de fichier

        Returns:
            Résultat de la génération
        """
        code_type, _ = self._analyze_code_request(query)

        # Génération selon le type
        if code_type == "class":
            return await self._generate_class(query, language)
        elif code_type == "function":
            return await self._generate_function(query, language)
        elif code_type == "script":
            return await self._generate_script(query, language)
        else:
            return await self._generate_generic_code(query, language)

    def _analyze_code_request(self, query: str) -> Dict[str, Any]:
        """
        Analyse la requête pour déterminer le type de code et le langage

        Args:
            query: Requête utilisateur

        Returns:
            Dictionnaire avec type_de_code et langage
        """
        query_lower = query.lower()

        # Détection du langage
        language = "python"  # Par défaut
        if "html" in query_lower or "page web" in query_lower:
            language = "html"
        elif "css" in query_lower or "style" in query_lower:
            language = "css"
        elif "javascript" in query_lower or "js" in query_lower:
            language = "javascript"
        elif "java" in query_lower and "javascript" not in query_lower:
            language = "java"
        elif "c++" in query_lower or "cpp" in query_lower:
            language = "cpp"

        # Détection du type
        code_type = "script"  # Par défaut : script complet
        if "classe" in query_lower or "class" in query_lower:
            code_type = "class"
        elif "fonction" in query_lower or "function" in query_lower:
            code_type = "function"
        elif "page" in query_lower and language == "html":
            code_type = "web_page"

        return {"type": code_type, "language": language}

    async def _generate_class(self, query: str, language: str) -> Dict[str, Any]:
        """
        Génère une classe
        """
        # Extraction des informations de la classe
        class_info = self._extract_class_info(query)

        if language == "python":
            template = self.templates["python"]["class"]

            # Génération des méthodes
            methods = []
            for method in class_info.get("methods", []):
                method_code = f'''    def {method["name"]}(self{method.get("params", "")}):
        """
        {method.get("description", "Méthode générée")}
        """
        {method.get("body", "pass")}
'''
                methods.append(method_code)

            code = template.format(
                class_name=class_info.get("name", "GeneratedClass"),
                description=class_info.get(
                    "description", "Classe générée automatiquement"
                ),
                init_params=class_info.get("init_params", ""),
                init_body=class_info.get("init_body", "pass"),
                methods="\n".join(methods),
            )

        elif language == "javascript":
            template = self.templates["javascript"]["class"]

            methods = []
            for method in class_info.get("methods", []):
                method_code = f"""    {method["name"]}({method.get("params", "")}) {{
        {method.get("body", "// TODO: Implémenter")}
    }}
"""
                methods.append(method_code)

            code = template.format(
                class_name=class_info.get("name", "GeneratedClass"),
                constructor_params=class_info.get("constructor_params", ""),
                constructor_body=class_info.get(
                    "constructor_body", "// TODO: Implémenter"
                ),
                methods="\n".join(methods),
            )

        else:
            return {
                "error": f"Génération de classe non supportée pour {language}",
                "success": False,
            }

        return {
            "success": True,
            "code": code,
            "language": language,
            "type": "class",
            "info": class_info,
        }

    async def _generate_function(self, query: str, language: str) -> Dict[str, Any]:
        """
        Génère une fonction
        """
        func_info = self._extract_function_info(query)

        if language == "python":
            template = self.templates["python"]["function"]

            # Génération de la documentation des arguments
            args_doc = []
            for param in func_info.get("parameters", []):
                args_doc.append(
                    f"        {param['name']}: {param.get('description', 'Paramètre')}"
                )

            code = template.format(
                function_name=func_info.get("name", "generated_function"),
                parameters=", ".join(
                    [p["name"] for p in func_info.get("parameters", [])]
                ),
                return_type=(
                    f" -> {func_info['return_type']}"
                    if func_info.get("return_type")
                    else ""
                ),
                description=func_info.get(
                    "description", "Fonction générée automatiquement"
                ),
                args_doc="\n".join(args_doc) if args_doc else "        Aucun paramètre",
                return_doc=func_info.get(
                    "return_description", "Résultat de la fonction"
                ),
                body=func_info.get("body", "    pass"),
            )

        elif language == "javascript":
            template = self.templates["javascript"]["function"]

            code = template.format(
                function_name=func_info.get("name", "generatedFunction"),
                parameters=", ".join(
                    [p["name"] for p in func_info.get("parameters", [])]
                ),
                body=func_info.get("body", "    // TODO: Implémenter"),
            )

        else:
            return {
                "error": f"Génération de fonction non supportée pour {language}",
                "success": False,
            }

        return {
            "success": True,
            "code": code,
            "language": language,
            "type": "function",
            "info": func_info,
        }

    async def _generate_script(self, query: str, language: str) -> Dict[str, Any]:
        """
        Génère un script complet
        """
        script_info = self._extract_script_info(query)

        if language == "python":
            template = self.templates["python"]["script"]

            code = template.format(
                description=script_info.get(
                    "description", "Script généré automatiquement"
                ),
                imports=script_info.get("imports", "# Imports nécessaires"),
                main_body=script_info.get("main_body", "    print('Hello, World!')"),
            )

        else:
            return {
                "error": f"Génération de script non supportée pour {language}",
                "success": False,
            }

        return {
            "success": True,
            "code": code,
            "language": language,
            "type": "script",
            "info": script_info,
        }

    async def _generate_web_page(self) -> Dict[str, Any]:
        """
        Génère une page web complète
        """
        page_info = self._extract_page_info()

        template = self.templates["html"]["page"]

        code = template.format(
            title=page_info.get("title", "Page générée"),
            css=page_info.get(
                "css", "body { font-family: Arial, sans-serif; margin: 20px; }"
            ),
            body=page_info.get(
                "body", "<h1>Bienvenue</h1><p>Page générée automatiquement.</p>"
            ),
            javascript=page_info.get("javascript", "console.log('Page chargée');"),
        )

        return {
            "success": True,
            "code": code,
            "language": "html",
            "type": "web_page",
            "info": page_info,
        }

    async def _generate_generic_code(self, query: str, language: str) -> Dict[str, Any]:
        """
        Génère du code générique basé sur la description
        """
        # Code simple basé sur le langage
        if language == "python":
            code = f'''# Code généré pour: {query}

def main():
    """
    Code principal généré automatiquement
    """
    # TODO: Implémenter la logique demandée
    print("Fonctionnalité à implémenter: {query}")

if __name__ == "__main__":
    main()
'''
        elif language == "javascript":
            code = f"""// Code généré pour: {query}

function main() {{
    // TODO: Implémenter la logique demandée
    console.log("Fonctionnalité à implémenter: {query}");
}}

main();
"""
        else:
            code = f"/* Code généré pour: {query} */\n// TODO: Implémenter"

        return {
            "success": True,
            "code": code,
            "language": language,
            "type": "generic",
            "query": query,
        }

    def _extract_class_info(self, query: str) -> Dict[str, Any]:
        """
        Extrait les informations pour générer une classe
        """
        # Extraction basique du nom de classe
        class_match = re.search(r"classe?\s+(\w+)", query, re.IGNORECASE)
        class_name = (
            class_match.group(1).capitalize() if class_match else "GeneratedClass"
        )

        return {
            "name": class_name,
            "description": f"Classe {class_name} générée automatiquement",
            "init_params": "",
            "init_body": "pass",
            "methods": [
                {
                    "name": "example_method",
                    "params": "",
                    "description": "Méthode d'exemple",
                    "body": "pass",
                }
            ],
        }

    def _extract_function_info(self, query: str) -> Dict[str, Any]:
        """
        Extrait les informations pour générer une fonction
        """
        # Extraction basique du nom de fonction
        func_match = re.search(r"fonction?\s+(\w+)", query, re.IGNORECASE)
        func_name = func_match.group(1) if func_match else "generated_function"

        return {
            "name": func_name,
            "description": f"Fonction {func_name} générée automatiquement",
            "parameters": [],
            "return_type": None,
            "return_description": "Résultat de la fonction",
            "body": "    pass",
        }

    def _extract_script_info(self, query: str) -> Dict[str, Any]:
        """
        Extrait les informations pour générer un script
        """
        return {
            "description": f"Script généré pour: {query}",
            "imports": "# Imports nécessaires",
            "main_body": "    # TODO: Implémenter la logique du script\n    pass",
        }

    def _extract_page_info(self) -> Dict[str, Any]:
        """
        Extrait les informations pour générer une page web
        """
        return {
            "title": "Page Web Générée",
            "css": "body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }",
            "body": "<h1>Bienvenue</h1><p>Cette page a été générée automatiquement.</p>",
            "javascript": "console.log('Page chargée avec succès');",
        }

    async def generate_file(
        self, query: str, is_interrupted_callback=None, memory: str = ""
    ) -> Dict[str, Any]:
        """
        Génère un fichier complet basé sur la requête utilisateur
        Méthode principale à utiliser pour "génère moi un fichier..."

        Args:
            query: Requête complète de l'utilisateur
            is_interrupted_callback: Fonction pour vérifier si l'opération est interrompue
            memory: Faits mémorisés sur l'utilisateur, une ligne chacun

        Returns:
            Résultat avec chemin du fichier créé
        """
        try:
            # Extraire le nom de fichier et les détails
            code_info = self._analyze_code_request(query)
            language = code_info.get("language", "python")
            filename = self._extract_filename(query, language)

            print(f"🔧 Génération du fichier {filename} ({language})...")

            # Générer le code avec Ollama en passant le callback
            result = await self.generate_code(
                query, filename, is_interrupted_callback, memory=memory
            )

            # Vérifier si l'opération a été interrompue
            if result.get("interrupted"):
                print("⚠️ [generate_file] Propagation de l'interruption")
                return {
                    "success": False,
                    "interrupted": True,
                    "message": "⚠️ Création du fichier interrompue.",
                }

            if result.get("success"):
                return {
                    "success": True,
                    "message": f"✅ Fichier '{filename}' créé avec succès !",
                    "file_path": result.get("file_path"),
                    "filename": filename,
                    "code": result.get("code"),
                    "language": language,
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Erreur inconnue"),
                    "message": "❌ Impossible de générer le fichier",
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Erreur: {str(e)}",
            }

    async def save_code(
        self, code_data: Dict[str, Any], filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sauvegarde le code généré dans un fichier

        Args:
            code_data: Données du code généré
            filename: Nom de fichier personnalisé

        Returns:
            Résultat de la sauvegarde
        """
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                language = code_data.get("language", "txt")
                ext = {
                    "python": "py",
                    "javascript": "js",
                    "html": "html",
                    "css": "css",
                }.get(language, "txt")
                filename = f"generated_code_{timestamp}.{ext}"

            filepath = os.path.join("outputs", filename)
            os.makedirs("outputs", exist_ok=True)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code_data["code"])

            return {
                "success": True,
                "file_path": filepath,
                "file_name": filename,
                "size": os.path.getsize(filepath),
            }

        except Exception as e:
            return {
                "error": f"Erreur lors de la sauvegarde: {str(e)}",
                "success": False,
            }
