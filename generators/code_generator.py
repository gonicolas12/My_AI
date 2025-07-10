"""
Générateur de code
Création et assistance à la programmation
"""

import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

class CodeGenerator:
    """
    Générateur de code dans différents langages
    """
    
    def __init__(self):
        """
        Initialise le générateur de code
        """
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
                "page": '''<!DOCTYPE html>
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
''',
                "component": '''<div class="{class_name}">
    {content}
</div>
''',
            },
            "css": {
                "component": '''.{component_name} {{
    {properties}
}}
''',
                "responsive": '''/* Mobile First */
{base_styles}

/* Tablet */
@media (min-width: 768px) {{
    {tablet_styles}
}}

/* Desktop */
@media (min-width: 1024px) {{
    {desktop_styles}
}}
''',
            },
            "javascript": {
                "function": '''function {function_name}({parameters}) {{
    {body}
}}
''',
                "class": '''class {class_name} {{
    constructor({constructor_params}) {{
        {constructor_body}
    }}
    
    {methods}
}}
''',
            }
        }
    
    async def generate_code(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Génère du code basé sur la requête
        
        Args:
            query: Demande de génération de code
            context: Contexte et paramètres
            
        Returns:
            Code généré
        """
        try:
            # Analyse de la requête
            code_type, language = self._analyze_code_request(query)
            
            # Génération selon le type
            if code_type == "class":
                return await self._generate_class(query, language, context)
            elif code_type == "function":
                return await self._generate_function(query, language, context)
            elif code_type == "script":
                return await self._generate_script(query, language, context)
            elif code_type == "web_page":
                return await self._generate_web_page(query, context)
            else:
                return await self._generate_generic_code(query, language, context)
                
        except Exception as e:
            return {
                "error": f"Erreur lors de la génération de code: {str(e)}",
                "success": False
            }
    
    def _analyze_code_request(self, query: str) -> tuple:
        """
        Analyse la requête pour déterminer le type de code
        
        Args:
            query: Requête utilisateur
            
        Returns:
            (type_de_code, langage)
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
        
        # Détection du type
        if "classe" in query_lower or "class" in query_lower:
            code_type = "class"
        elif "fonction" in query_lower or "function" in query_lower:
            code_type = "function"
        elif "script" in query_lower or "programme" in query_lower:
            code_type = "script"
        elif "page" in query_lower and language == "html":
            code_type = "web_page"
        else:
            code_type = "generic"
        
        return code_type, language
    
    async def _generate_class(self, query: str, language: str, context: Dict[str, Any]) -> Dict[str, Any]:
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
                description=class_info.get("description", "Classe générée automatiquement"),
                init_params=class_info.get("init_params", ""),
                init_body=class_info.get("init_body", "pass"),
                methods="\n".join(methods)
            )
        
        elif language == "javascript":
            template = self.templates["javascript"]["class"]
            
            methods = []
            for method in class_info.get("methods", []):
                method_code = f'''    {method["name"]}({method.get("params", "")}) {{
        {method.get("body", "// TODO: Implémenter")}
    }}
'''
                methods.append(method_code)
            
            code = template.format(
                class_name=class_info.get("name", "GeneratedClass"),
                constructor_params=class_info.get("constructor_params", ""),
                constructor_body=class_info.get("constructor_body", "// TODO: Implémenter"),
                methods="\n".join(methods)
            )
        
        else:
            return {
                "error": f"Génération de classe non supportée pour {language}",
                "success": False
            }
        
        return {
            "success": True,
            "code": code,
            "language": language,
            "type": "class",
            "info": class_info
        }
    
    async def _generate_function(self, query: str, language: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Génère une fonction
        """
        func_info = self._extract_function_info(query)
        
        if language == "python":
            template = self.templates["python"]["function"]
            
            # Génération de la documentation des arguments
            args_doc = []
            for param in func_info.get("parameters", []):
                args_doc.append(f"        {param['name']}: {param.get('description', 'Paramètre')}")
            
            code = template.format(
                function_name=func_info.get("name", "generated_function"),
                parameters=", ".join([p["name"] for p in func_info.get("parameters", [])]),
                return_type=f" -> {func_info['return_type']}" if func_info.get("return_type") else "",
                description=func_info.get("description", "Fonction générée automatiquement"),
                args_doc="\n".join(args_doc) if args_doc else "        Aucun paramètre",
                return_doc=func_info.get("return_description", "Résultat de la fonction"),
                body=func_info.get("body", "    pass")
            )
        
        elif language == "javascript":
            template = self.templates["javascript"]["function"]
            
            code = template.format(
                function_name=func_info.get("name", "generatedFunction"),
                parameters=", ".join([p["name"] for p in func_info.get("parameters", [])]),
                body=func_info.get("body", "    // TODO: Implémenter")
            )
        
        else:
            return {
                "error": f"Génération de fonction non supportée pour {language}",
                "success": False
            }
        
        return {
            "success": True,
            "code": code,
            "language": language,
            "type": "function",
            "info": func_info
        }
    
    async def _generate_script(self, query: str, language: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Génère un script complet
        """
        script_info = self._extract_script_info(query)
        
        if language == "python":
            template = self.templates["python"]["script"]
            
            code = template.format(
                description=script_info.get("description", "Script généré automatiquement"),
                imports=script_info.get("imports", "# Imports nécessaires"),
                main_body=script_info.get("main_body", "    print('Hello, World!')")
            )
        
        else:
            return {
                "error": f"Génération de script non supportée pour {language}",
                "success": False
            }
        
        return {
            "success": True,
            "code": code,
            "language": language,
            "type": "script",
            "info": script_info
        }
    
    async def _generate_web_page(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Génère une page web complète
        """
        page_info = self._extract_page_info(query)
        
        template = self.templates["html"]["page"]
        
        code = template.format(
            title=page_info.get("title", "Page générée"),
            css=page_info.get("css", "body { font-family: Arial, sans-serif; margin: 20px; }"),
            body=page_info.get("body", "<h1>Bienvenue</h1><p>Page générée automatiquement.</p>"),
            javascript=page_info.get("javascript", "console.log('Page chargée');")
        )
        
        return {
            "success": True,
            "code": code,
            "language": "html",
            "type": "web_page",
            "info": page_info
        }
    
    async def _generate_generic_code(self, query: str, language: str, context: Dict[str, Any]) -> Dict[str, Any]:
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
            code = f'''// Code généré pour: {query}

function main() {{
    // TODO: Implémenter la logique demandée
    console.log("Fonctionnalité à implémenter: {query}");
}}

main();
'''
        else:
            code = f"/* Code généré pour: {query} */\n// TODO: Implémenter"
        
        return {
            "success": True,
            "code": code,
            "language": language,
            "type": "generic",
            "query": query
        }
    
    def _extract_class_info(self, query: str) -> Dict[str, Any]:
        """
        Extrait les informations pour générer une classe
        """
        # Extraction basique du nom de classe
        class_match = re.search(r'classe?\s+(\w+)', query, re.IGNORECASE)
        class_name = class_match.group(1).capitalize() if class_match else "GeneratedClass"
        
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
                    "body": "pass"
                }
            ]
        }
    
    def _extract_function_info(self, query: str) -> Dict[str, Any]:
        """
        Extrait les informations pour générer une fonction
        """
        # Extraction basique du nom de fonction
        func_match = re.search(r'fonction?\s+(\w+)', query, re.IGNORECASE)
        func_name = func_match.group(1) if func_match else "generated_function"
        
        return {
            "name": func_name,
            "description": f"Fonction {func_name} générée automatiquement",
            "parameters": [],
            "return_type": None,
            "return_description": "Résultat de la fonction",
            "body": "    pass"
        }
    
    def _extract_script_info(self, query: str) -> Dict[str, Any]:
        """
        Extrait les informations pour générer un script
        """
        return {
            "description": f"Script généré pour: {query}",
            "imports": "# Imports nécessaires",
            "main_body": "    # TODO: Implémenter la logique du script\n    pass"
        }
    
    def _extract_page_info(self, query: str) -> Dict[str, Any]:
        """
        Extrait les informations pour générer une page web
        """
        return {
            "title": "Page Web Générée",
            "css": "body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }",
            "body": "<h1>Bienvenue</h1><p>Cette page a été générée automatiquement.</p>",
            "javascript": "console.log('Page chargée avec succès');"
        }
    
    async def save_code(self, code_data: Dict[str, Any], filename: Optional[str] = None) -> Dict[str, Any]:
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
                ext = {"python": "py", "javascript": "js", "html": "html", "css": "css"}.get(language, "txt")
                filename = f"generated_code_{timestamp}.{ext}"
            
            filepath = os.path.join("outputs", filename)
            os.makedirs("outputs", exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code_data["code"])
            
            return {
                "success": True,
                "file_path": filepath,
                "file_name": filename,
                "size": os.path.getsize(filepath)
            }
            
        except Exception as e:
            return {
                "error": f"Erreur lors de la sauvegarde: {str(e)}",
                "success": False
            }
