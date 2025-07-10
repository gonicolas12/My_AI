"""
Générateur de code intelligent pour l'IA locale
Génération de code modulaire et séparée par langage
"""

from typing import Dict, List, Any, Optional
import re
import datetime
import random
from abc import ABC, abstractmethod


class BaseCodeGenerator(ABC):
    """Classe de base pour les générateurs de code spécifiques à un langage"""
    
    def __init__(self, language: str):
        self.language = language
        self.templates = self._load_templates()
        self.patterns = self._load_patterns()
    
    @abstractmethod
    def _load_templates(self) -> Dict[str, str]:
        """Charge les templates spécifiques au langage"""
        pass
    
    @abstractmethod
    def _load_patterns(self) -> Dict[str, str]:
        """Charge les patterns de code prédéfinis"""
        pass
    
    @abstractmethod
    def generate_function(self, name: str, params: List[str] = None, description: str = "") -> str:
        """Génère une fonction basique"""
        pass
    
    @abstractmethod
    def generate_class(self, name: str, description: str = "") -> str:
        """Génère une classe basique"""
        pass
    
    @abstractmethod
    def generate_hello_world(self) -> str:
        """Génère un programme Hello World"""
        pass
    
    @abstractmethod
    def generate_factorial(self) -> str:
        """Génère une fonction factorielle"""
        pass


class PythonCodeGenerator(BaseCodeGenerator):
    """Générateur de code Python"""
    
    def __init__(self):
        super().__init__("python")
    
    def _load_templates(self) -> Dict[str, str]:
        return {
            "function": '''def {name}({params}):
    """
    {description}
    """
    {body}
    return {return_value}''',
            
            "class": '''class {name}:
    """
    {description}
    """
    
    def __init__(self{init_params}):
        {init_body}
    
    {methods}''',
            
            "main": '''if __name__ == "__main__":
    {main_body}''',
        }
    
    def _load_patterns(self) -> Dict[str, str]:
        return {
            "factorial": '''def factorielle(n):
    """
    Calcule la factorielle d'un nombre n
    Args:
        n (int): Le nombre dont on veut calculer la factorielle
    Returns:
        int: La factorielle de n
    """
    if n < 0:
        raise ValueError("La factorielle n'est pas définie pour les nombres négatifs")
    elif n == 0 or n == 1:
        return 1
    else:
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result

# Version récursive alternative
def factorielle_recursive(n):
    """Version récursive de la factorielle"""
    if n < 0:
        raise ValueError("La factorielle n'est pas définie pour les nombres négatifs")
    elif n == 0 or n == 1:
        return 1
    else:
        return n * factorielle_recursive(n - 1)

# Tests
if __name__ == "__main__":
    test_values = [0, 1, 5, 10]
    for n in test_values:
        print(f"factorielle({n}) = {factorielle(n)}")''',
            
            "fibonacci": '''def fibonacci(n):
    """
    Génère la séquence de Fibonacci jusqu'à n termes
    Args:
        n (int): Nombre de termes à générer
    Returns:
        list: Liste des n premiers termes de Fibonacci
    """
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    sequence = [0, 1]
    for i in range(2, n):
        sequence.append(sequence[i-1] + sequence[i-2])
    
    return sequence

# Exemple d'utilisation
if __name__ == "__main__":
    print("Séquence de Fibonacci (10 termes):")
    print(fibonacci(10))''',
            
            "sort": '''def tri_bulle(liste):
    """
    Tri à bulles d'une liste
    Args:
        liste (list): Liste à trier
    Returns:
        list: Liste triée
    """
    n = len(liste)
    liste_copiee = liste.copy()  # Ne pas modifier l'original
    
    for i in range(n):
        for j in range(0, n - i - 1):
            if liste_copiee[j] > liste_copiee[j + 1]:
                liste_copiee[j], liste_copiee[j + 1] = liste_copiee[j + 1], liste_copiee[j]
    
    return liste_copiee

def tri_rapide(liste):
    """
    Tri rapide (quicksort)
    Args:
        liste (list): Liste à trier
    Returns:
        list: Liste triée
    """
    if len(liste) <= 1:
        return liste
    
    pivot = liste[len(liste) // 2]
    gauche = [x for x in liste if x < pivot]
    milieu = [x for x in liste if x == pivot]
    droite = [x for x in liste if x > pivot]
    
    return tri_rapide(gauche) + milieu + tri_rapide(droite)

# Tests
if __name__ == "__main__":
    test_list = [64, 34, 25, 12, 22, 11, 90]
    print(f"Liste originale: {test_list}")
    print(f"Tri bulle: {tri_bulle(test_list)}")
    print(f"Tri rapide: {tri_rapide(test_list)}")''',
        }
    
    def generate_function(self, name: str, params: List[str] = None, description: str = "") -> str:
        if params is None:
            params = []
        
        return self.templates["function"].format(
            name=name,
            params=", ".join(params) if params else "",
            description=description or f"Fonction {name} générée automatiquement",
            body="    # TODO: Implémentez votre logique ici\n    pass",
            return_value="None"
        )
    
    def generate_class(self, name: str, description: str = "") -> str:
        return self.templates["class"].format(
            name=name,
            description=description or f"Classe {name} générée automatiquement",
            init_params=", *args, **kwargs",
            init_body="        pass  # TODO: Initialisez vos attributs",
            methods='''    def __str__(self):
        """Représentation string de l'objet"""
        return f"<{self.__class__.__name__} object>"
    
    def methode_exemple(self):
        """Méthode d'exemple à personnaliser"""
        return "Méthode appelée"'''
        )
    
    def generate_hello_world(self) -> str:
        return '''#!/usr/bin/env python3
"""
Programme Hello World complet
"""

def dire_bonjour(nom="Monde"):
    """
    Fonction qui dit bonjour
    Args:
        nom (str): Nom à saluer
    Returns:
        str: Message de salutation
    """
    return f"Bonjour, {nom}!"

def main():
    """Fonction principale"""
    print("=== Programme Hello World ===")
    print("Hello, World!")
    print("Bonjour, Monde!")
    print(dire_bonjour())
    print(dire_bonjour("Python"))
    
    # Interaction utilisateur
    nom = input("Votre nom: ")
    if nom.strip():
        print(dire_bonjour(nom))

if __name__ == "__main__":
    main()'''
    
    def generate_factorial(self) -> str:
        return self.patterns["factorial"]
    
    def generate_fibonacci(self) -> str:
        return self.patterns["fibonacci"]
    
    def generate_sort(self) -> str:
        return self.patterns["sort"]
    
    def generate_calculator(self) -> str:
        return '''class Calculatrice:
    """
    Calculatrice simple avec les opérations de base
    """
    
    def __init__(self):
        self.historique = []
    
    def addition(self, a, b):
        """Addition de deux nombres"""
        resultat = a + b
        self.historique.append(f"{a} + {b} = {resultat}")
        return resultat
    
    def soustraction(self, a, b):
        """Soustraction de deux nombres"""
        resultat = a - b
        self.historique.append(f"{a} - {b} = {resultat}")
        return resultat
    
    def multiplication(self, a, b):
        """Multiplication de deux nombres"""
        resultat = a * b
        self.historique.append(f"{a} × {b} = {resultat}")
        return resultat
    
    def division(self, a, b):
        """Division de deux nombres"""
        if b == 0:
            raise ValueError("Division par zéro impossible")
        resultat = a / b
        self.historique.append(f"{a} ÷ {b} = {resultat}")
        return resultat
    
    def puissance(self, a, b):
        """Élévation à la puissance"""
        resultat = a ** b
        self.historique.append(f"{a}^{b} = {resultat}")
        return resultat
    
    def afficher_historique(self):
        """Affiche l'historique des calculs"""
        print("Historique des calculs:")
        for operation in self.historique:
            print(f"  {operation}")
    
    def effacer_historique(self):
        """Efface l'historique"""
        self.historique.clear()

# Exemple d'utilisation
if __name__ == "__main__":
    calc = Calculatrice()
    
    print("=== Calculatrice Simple ===")
    print(f"2 + 3 = {calc.addition(2, 3)}")
    print(f"10 - 4 = {calc.soustraction(10, 4)}")
    print(f"5 × 6 = {calc.multiplication(5, 6)}")
    print(f"15 ÷ 3 = {calc.division(15, 3)}")
    print(f"2^8 = {calc.puissance(2, 8)}")
    
    print()
    calc.afficher_historique()'''


class JavaScriptCodeGenerator(BaseCodeGenerator):
    """Générateur de code JavaScript"""
    
    def __init__(self):
        super().__init__("javascript")
    
    def _load_templates(self) -> Dict[str, str]:
        return {
            "function": '''function {name}({params}) {{
    /**
     * {description}
     */
    {body}
    return {return_value};
}}''',
            
            "class": '''class {name} {{
    /**
     * {description}
     */
    constructor({constructor_params}) {{
        {constructor_body}
    }}
    
    {methods}
}}''',
        }
    
    def _load_patterns(self) -> Dict[str, str]:
        return {
            "factorial": '''function factorielle(n) {
    /**
     * Calcule la factorielle d'un nombre
     * @param {number} n - Le nombre
     * @returns {number} La factorielle
     */
    if (n < 0) {
        throw new Error("La factorielle n'est pas définie pour les nombres négatifs");
    } else if (n === 0 || n === 1) {
        return 1;
    } else {
        let result = 1;
        for (let i = 2; i <= n; i++) {
            result *= i;
        }
        return result;
    }
}

// Version récursive
function factorielleRecursive(n) {
    if (n < 0) {
        throw new Error("La factorielle n'est pas définie pour les nombres négatifs");
    } else if (n === 0 || n === 1) {
        return 1;
    } else {
        return n * factorielleRecursive(n - 1);
    }
}

// Tests
[0, 1, 5, 10].forEach(n => {
    console.log(`factorielle(${n}) = ${factorielle(n)}`);
});''',
        }
    
    def generate_function(self, name: str, params: List[str] = None, description: str = "") -> str:
        if params is None:
            params = []
        
        return self.templates["function"].format(
            name=name,
            params=", ".join(params) if params else "",
            description=description or f"Fonction {name} générée automatiquement",
            body="    // TODO: Implémentez votre logique ici",
            return_value="undefined"
        )
    
    def generate_class(self, name: str, description: str = "") -> str:
        return self.templates["class"].format(
            name=name,
            description=description or f"Classe {name} générée automatiquement",
            constructor_params="...args",
            constructor_body="        // TODO: Initialisez vos propriétés",
            methods='''    methodeExemple() {
        return "Méthode appelée";
    }
    
    toString() {
        return `[object ${this.constructor.name}]`;
    }'''
        )
    
    def generate_hello_world(self) -> str:
        return '''/**
 * Programme Hello World en JavaScript
 */

function direBonjour(nom = "Monde") {
    return `Bonjour, ${nom}!`;
}

function main() {
    console.log("=== Programme Hello World ===");
    console.log("Hello, World!");
    console.log("Bonjour, Monde!");
    console.log(direBonjour());
    console.log(direBonjour("JavaScript"));
    
    // En environnement navigateur
    if (typeof document !== 'undefined') {
        document.body.innerHTML = `
            <h1>Hello World!</h1>
            <p>${direBonjour("Web")}</p>
        `;
    }
}

// Exécution
if (typeof window === 'undefined') {
    // Node.js
    main();
} else {
    // Navigateur
    document.addEventListener('DOMContentLoaded', main);
}'''
    
    def generate_factorial(self) -> str:
        return self.patterns["factorial"]


class HTMLCodeGenerator(BaseCodeGenerator):
    """Générateur de code HTML"""
    
    def __init__(self):
        super().__init__("html")
    
    def _load_templates(self) -> Dict[str, str]:
        return {
            "basic": '''<!DOCTYPE html>
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
</html>''',
        }
    
    def _load_patterns(self) -> Dict[str, str]:
        return {}
    
    def generate_function(self, name: str, params: List[str] = None, description: str = "") -> str:
        return f"<!-- Les fonctions HTML sont en JavaScript -->\n<script>\n{JavaScriptCodeGenerator().generate_function(name, params, description)}\n</script>"
    
    def generate_class(self, name: str, description: str = "") -> str:
        return f"<!-- Les classes HTML sont en JavaScript -->\n<script>\n{JavaScriptCodeGenerator().generate_class(name, description)}\n</script>"
    
    def generate_hello_world(self) -> str:
        return self.templates["basic"].format(
            title="Hello World",
            css='''        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .container {
            background: white;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            text-align: center;
        }
        
        h1 { color: #333; margin-bottom: 1rem; }
        .greeting { color: #666; font-size: 1.2rem; }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
        }
        button:hover { background: #5a6fd8; }''',
            body='''    <div class="container">
        <h1>🌍 Hello World!</h1>
        <p class="greeting">Bienvenue sur cette page!</p>
        <button onclick="direBonjour()">Dire Bonjour</button>
        <button onclick="afficherHeure()">Afficher l'heure</button>
        <div id="output"></div>
    </div>''',
            javascript='''        function direBonjour() {
            document.getElementById('output').innerHTML = 
                '<h3>👋 Bonjour depuis JavaScript!</h3>';
        }
        
        function afficherHeure() {
            const now = new Date();
            document.getElementById('output').innerHTML = 
                `<h3>⏰ Il est ${now.toLocaleTimeString()}</h3>`;
        }'''
        )
    
    def generate_factorial(self) -> str:
        return "<!-- Factorielle implémentée en JavaScript dans la page HTML -->"


class CodeGenerator:
    """Générateur de code principal avec support multi-langage"""
    
    def __init__(self):
        self.generators = {
            "python": PythonCodeGenerator(),
            "javascript": JavaScriptCodeGenerator(),
            "js": JavaScriptCodeGenerator(),
            "html": HTMLCodeGenerator(),
            "web": HTMLCodeGenerator(),
        }
    
    def generate_code(self, request: str, analysis: Optional[Dict[str, Any]] = None) -> str:
        """Génère du code basé sur la demande"""
        if analysis is None:
            analysis = {}
        
        request_lower = request.lower()
        
        # Détection du langage
        language = self._detect_language(request_lower)
        generator = self.generators.get(language, self.generators["python"])
        
        # Génération selon le type de demande
        if any(word in request_lower for word in ["factorielle", "factorial"]):
            return generator.generate_factorial()
        elif any(word in request_lower for word in ["hello", "world", "bonjour", "monde"]):
            return generator.generate_hello_world()
        elif any(word in request_lower for word in ["fibonacci", "fibo"]):
            if hasattr(generator, 'generate_fibonacci'):
                return generator.generate_fibonacci()
            else:
                return self.generators["python"].generate_fibonacci()
        elif any(word in request_lower for word in ["tri", "trier", "sort"]):
            if hasattr(generator, 'generate_sort'):
                return generator.generate_sort()
            else:
                return self.generators["python"].generate_sort()
        elif any(word in request_lower for word in ["calculer", "calculator", "calcul"]):
            if hasattr(generator, 'generate_calculator'):
                return generator.generate_calculator()
            else:
                return self.generators["python"].generate_calculator()
        elif any(word in request_lower for word in ["fonction", "function", "def"]):
            function_name = self._extract_function_name(request)
            return generator.generate_function(function_name)
        elif any(word in request_lower for word in ["classe", "class"]):
            class_name = self._extract_class_name(request)
            return generator.generate_class(class_name)
        else:
            return self._generate_generic_code(request, language)
    
    def _detect_language(self, request: str) -> str:
        """Détecte le langage demandé"""
        language_keywords = {
            "python": ["python", "py", "def", "class", "import"],
            "javascript": ["javascript", "js", "function", "var", "let", "const"],
            "html": ["html", "page", "web", "site", "balise"],
        }
        
        for lang, keywords in language_keywords.items():
            if any(keyword in request for keyword in keywords):
                return lang
        
        return "python"  # Par défaut
    
    def _extract_function_name(self, request: str) -> str:
        """Extrait le nom de fonction de la demande"""
        # Recherche de patterns comme "fonction nom_fonction" ou "def nom_fonction"
        match = re.search(r'(?:fonction|function|def)\s+(\w+)', request, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Recherche d'un nom après certains mots-clés
        for word in ["pour", "qui", "de", "appelée", "nommée"]:
            if word in request:
                words = request.split()
                try:
                    index = words.index(word)
                    if index + 1 < len(words):
                        return words[index + 1].strip("(){}[].,;:")
                except ValueError:
                    continue
        
        # Analyse sémantique pour deviner le nom
        if "calcul" in request.lower():
            return "calculer"
        elif "tri" in request.lower():
            return "trier"
        elif "affich" in request.lower():
            return "afficher"
        elif "convert" in request.lower():
            return "convertir"
        elif "verif" in request.lower():
            return "verifier"
        else:
            return "ma_fonction"
    
    def _extract_class_name(self, request: str) -> str:
        """Extrait le nom de classe de la demande"""
        match = re.search(r'(?:classe|class)\s+(\w+)', request, re.IGNORECASE)
        if match:
            return match.group(1).capitalize()
        
        # Analyse sémantique pour deviner le nom
        if "personne" in request.lower():
            return "Personne"
        elif "voiture" in request.lower():
            return "Voiture"
        elif "animal" in request.lower():
            return "Animal"
        elif "compte" in request.lower():
            return "Compte"
        elif "produit" in request.lower():
            return "Produit"
        else:
            return "MaClasse"
    
    def _generate_generic_code(self, request: str, language: str) -> str:
        """Génère du code générique intelligent basé sur l'analyse de la demande"""
        generator = self.generators.get(language, self.generators["python"])
        
        # Analyse sémantique de la demande
        request_lower = request.lower()
        
        # Détection de patterns spécifiques
        if any(word in request_lower for word in ["lire", "read", "fichier", "file"]):
            return self._generate_file_handler(language, request)
        elif any(word in request_lower for word in ["api", "serveur", "server", "web"]):
            return self._generate_api_server(language, request)
        elif any(word in request_lower for word in ["base", "données", "database", "sql"]):
            return self._generate_database_handler(language, request)
        elif any(word in request_lower for word in ["gui", "interface", "fenêtre", "window"]):
            return self._generate_gui_app(language, request)
        elif any(word in request_lower for word in ["email", "mail", "envoi", "send"]):
            return self._generate_email_sender(language, request)
        elif any(word in request_lower for word in ["json", "xml", "csv", "parse"]):
            return self._generate_data_parser(language, request)
        elif any(word in request_lower for word in ["test", "unit", "pytest"]):
            return self._generate_test_framework(language, request)
        else:
            return generator.generate_hello_world()
    
    def _generate_file_handler(self, language: str, request: str) -> str:
        """Génère un gestionnaire de fichiers intelligent"""
        if language == "python":
            return '''import os
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional

class FileHandler:
    """Gestionnaire de fichiers polyvalent"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    def lire_fichier_texte(self, nom_fichier: str) -> str:
        """Lit un fichier texte et retourne son contenu"""
        chemin = self.base_path / nom_fichier
        try:
            with open(chemin, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Fichier {nom_fichier} non trouvé")
            return ""
        except Exception as e:
            print(f"Erreur lors de la lecture: {e}")
            return ""
    
    def ecrire_fichier_texte(self, nom_fichier: str, contenu: str) -> bool:
        """Écrit du contenu dans un fichier texte"""
        chemin = self.base_path / nom_fichier
        try:
            with open(chemin, 'w', encoding='utf-8') as f:
                f.write(contenu)
            return True
        except Exception as e:
            print(f"Erreur lors de l'écriture: {e}")
            return False
    
    def lire_json(self, nom_fichier: str) -> Dict[str, Any]:
        """Lit un fichier JSON"""
        chemin = self.base_path / nom_fichier
        try:
            with open(chemin, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erreur lors de la lecture JSON: {e}")
            return {}
    
    def ecrire_json(self, nom_fichier: str, data: Dict[str, Any]) -> bool:
        """Écrit des données en JSON"""
        chemin = self.base_path / nom_fichier
        try:
            with open(chemin, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Erreur lors de l'écriture JSON: {e}")
            return False
    
    def lire_csv(self, nom_fichier: str) -> List[Dict[str, str]]:
        """Lit un fichier CSV et retourne une liste de dictionnaires"""
        chemin = self.base_path / nom_fichier
        try:
            with open(chemin, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)
        except Exception as e:
            print(f"Erreur lors de la lecture CSV: {e}")
            return []
    
    def ecrire_csv(self, nom_fichier: str, data: List[Dict[str, Any]], colonnes: List[str] = None) -> bool:
        """Écrit des données en CSV"""
        if not data:
            return False
        
        chemin = self.base_path / nom_fichier
        try:
            colonnes = colonnes or list(data[0].keys())
            with open(chemin, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=colonnes)
                writer.writeheader()
                writer.writerows(data)
            return True
        except Exception as e:
            print(f"Erreur lors de l'écriture CSV: {e}")
            return False
    
    def lister_fichiers(self, extension: str = None) -> List[str]:
        """Liste les fichiers dans le répertoire"""
        pattern = f"*.{extension}" if extension else "*"
        return [f.name for f in self.base_path.glob(pattern) if f.is_file()]

# Exemple d'utilisation
if __name__ == "__main__":
    handler = FileHandler("./data")
    
    # Test écriture/lecture texte
    handler.ecrire_fichier_texte("test.txt", "Hello, World!")
    contenu = handler.lire_fichier_texte("test.txt")
    print(f"Contenu lu: {contenu}")
    
    # Test JSON
    data = {"nom": "Jean", "age": 30, "ville": "Paris"}
    handler.ecrire_json("test.json", data)
    data_lue = handler.lire_json("test.json")
    print(f"Données JSON: {data_lue}")
    
    # Test CSV
    donnees_csv = [
        {"nom": "Alice", "age": "25", "ville": "Lyon"},
        {"nom": "Bob", "age": "30", "ville": "Paris"}
    ]
    handler.ecrire_csv("test.csv", donnees_csv)
    csv_lu = handler.lire_csv("test.csv")
    print(f"Données CSV: {csv_lu}")
    
    # Liste des fichiers
    print(f"Fichiers: {handler.lister_fichiers()}")'''
        
        else:
            return f"// Gestionnaire de fichiers en {language} non implémenté"
    
    def _generate_api_server(self, language: str, request: str) -> str:
        """Génère un serveur API intelligent"""
        if language == "python":
            return '''from flask import Flask, request, jsonify
from typing import Dict, Any, List
import json
import datetime

app = Flask(__name__)

# Base de données en mémoire pour la démonstration
users_db = []
products_db = []

@app.route('/')
def home():
    """Page d'accueil de l'API"""
    return jsonify({
        "message": "Bienvenue sur l'API",
        "version": "1.0.0",
        "endpoints": {
            "users": "/api/users",
            "products": "/api/products",
            "health": "/api/health"
        }
    })

@app.route('/api/health')
def health_check():
    """Vérification de santé de l'API"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "uptime": "Running"
    })

@app.route('/api/users', methods=['GET'])
def get_users():
    """Récupère tous les utilisateurs"""
    return jsonify({
        "users": users_db,
        "count": len(users_db)
    })

@app.route('/api/users', methods=['POST'])
def create_user():
    """Crée un nouvel utilisateur"""
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({"error": "Le nom est requis"}), 400
    
    user = {
        "id": len(users_db) + 1,
        "name": data['name'],
        "email": data.get('email', ''),
        "created_at": datetime.datetime.now().isoformat()
    }
    
    users_db.append(user)
    return jsonify(user), 201

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Récupère un utilisateur spécifique"""
    user = next((u for u in users_db if u['id'] == user_id), None)
    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404
    return jsonify(user)

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Met à jour un utilisateur"""
    user = next((u for u in users_db if u['id'] == user_id), None)
    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404
    
    data = request.get_json()
    if data:
        user.update(data)
        user['updated_at'] = datetime.datetime.now().isoformat()
    
    return jsonify(user)

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Supprime un utilisateur"""
    global users_db
    users_db = [u for u in users_db if u['id'] != user_id]
    return jsonify({"message": "Utilisateur supprimé"}), 200

@app.route('/api/products', methods=['GET'])
def get_products():
    """Récupère tous les produits"""
    return jsonify({
        "products": products_db,
        "count": len(products_db)
    })

@app.route('/api/products', methods=['POST'])
def create_product():
    """Crée un nouveau produit"""
    data = request.get_json()
    
    if not data or 'name' not in data or 'price' not in data:
        return jsonify({"error": "Le nom et le prix sont requis"}), 400
    
    product = {
        "id": len(products_db) + 1,
        "name": data['name'],
        "price": float(data['price']),
        "description": data.get('description', ''),
        "created_at": datetime.datetime.now().isoformat()
    }
    
    products_db.append(product)
    return jsonify(product), 201

@app.errorhandler(404)
def not_found(error):
    """Gestionnaire d'erreur 404"""
    return jsonify({"error": "Endpoint non trouvé"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Gestionnaire d'erreur 500"""
    return jsonify({"error": "Erreur interne du serveur"}), 500

if __name__ == '__main__':
    # Données de test
    users_db.extend([
        {"id": 1, "name": "Alice", "email": "alice@test.com", "created_at": "2025-01-01T10:00:00"},
        {"id": 2, "name": "Bob", "email": "bob@test.com", "created_at": "2025-01-01T11:00:00"}
    ])
    
    products_db.extend([
        {"id": 1, "name": "Produit A", "price": 29.99, "description": "Description A"},
        {"id": 2, "name": "Produit B", "price": 19.99, "description": "Description B"}
    ])
    
    print("Serveur API démarré sur http://localhost:5000")
    print("Endpoints disponibles:")
    print("  GET  /api/users")
    print("  POST /api/users")
    print("  GET  /api/users/<id>")
    print("  PUT  /api/users/<id>")
    print("  DELETE /api/users/<id>")
    print("  GET  /api/products")
    print("  POST /api/products")
    
    app.run(debug=True, port=5000)'''
        
        else:
            return f"// Serveur API en {language} non implémenté"
