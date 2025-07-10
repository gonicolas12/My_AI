"""
Générateur de code principal avec détection de langage et gestion des générateurs spécifiques
"""

from typing import Dict, List, Any, Optional
import re
import datetime
import random
from .base_generator import BaseCodeGenerator
from .python_generator import PythonCodeGenerator
from .javascript_generator import JavaScriptCodeGenerator
from .html_generator import HTMLCodeGenerator


class CodeGenerator:
    """Générateur de code principal avec support multi-langage"""
    
    def __init__(self):
        """Initialise le générateur de code avec tous les générateurs par langage"""
        self.generators = {
            "python": PythonCodeGenerator(),
            "javascript": JavaScriptCodeGenerator(),
            "js": JavaScriptCodeGenerator(),
            "html": HTMLCodeGenerator(),
            "web": HTMLCodeGenerator(),
        }
    
    def generate_code(self, request: str, analysis: Optional[Dict[str, Any]] = None) -> str:
        """
        Génère du code basé sur la demande de l'utilisateur
        
        Args:
            request: Demande textuelle de l'utilisateur
            analysis: Analyse préalable de la demande (facultatif)
            
        Returns:
            str: Code généré
        """
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
            if hasattr(generator, 'generate_sort_algorithm'):
                return generator.generate_sort_algorithm()
            elif hasattr(generator, 'generate_sort'):
                return generator.generate_sort()
            else:
                return self.generators["python"].generate_sort()
        elif any(word in request_lower for word in ["calculer", "calculator", "calcul"]):
            if hasattr(generator, 'generate_calculator'):
                return generator.generate_calculator()
            else:
                return self._generate_calculator(language)
        elif any(word in request_lower for word in ["fonction", "function", "def"]):
            function_name = self._extract_function_name(request)
            return generator.generate_function(function_name)
        elif any(word in request_lower for word in ["classe", "class"]):
            class_name = self._extract_class_name(request)
            return generator.generate_class(class_name)
        elif any(word in request_lower for word in ["formulaire", "form"]):
            if language in ["html", "web"]:
                fields = [
                    {"type": "text", "name": "name", "label": "Nom", "required": True},
                    {"type": "email", "name": "email", "label": "Email", "required": True}
                ]
                return self.generators["html"].generate_form("/submit", "post", "Formulaire de contact", fields)
            else:
                return generator.generate_hello_world()
        elif any(word in request_lower for word in ["table", "tableau", "données", "data"]):
            if language in ["html", "web"]:
                headers = ["ID", "Nom", "Email", "Date"]
                rows = [
                    ["1", "Jean Dupont", "jean@example.com", "01/01/2025"],
                    ["2", "Marie Martin", "marie@example.com", "02/01/2025"],
                    ["3", "Pierre Paul", "pierre@example.com", "03/01/2025"]
                ]
                return self.generators["html"].generate_table(headers, rows)
            else:
                return generator.generate_hello_world()
        else:
            return self._generate_generic_code(request, language)
    
    def _detect_language(self, request: str) -> str:
        """
        Détecte le langage demandé en fonction des mots-clés présents dans la requête
        
        Args:
            request: Requête en minuscules
            
        Returns:
            str: Code du langage détecté
        """
        language_keywords = {
            "python": ["python", "py", "def", "class", "import", ".py", "django", "flask"],
            "javascript": ["javascript", "js", "function", "var", "let", "const", "node", "react", "vue", "angular"],
            "html": ["html", "page", "web", "site", "balise", "css", "form", "formulaire", "responsive"],
        }
        
        for lang, keywords in language_keywords.items():
            if any(keyword in request for keyword in keywords):
                return lang
        
        return "python"  # Par défaut
    
    def _extract_function_name(self, request: str) -> str:
        """
        Extrait le nom de fonction de la demande
        
        Args:
            request: Demande textuelle
            
        Returns:
            str: Nom de fonction extrait ou par défaut
        """
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
        """
        Extrait le nom de classe de la demande
        
        Args:
            request: Demande textuelle
            
        Returns:
            str: Nom de classe extrait ou par défaut
        """
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
        elif "utilisateur" in request.lower() or "user" in request.lower():
            return "Utilisateur"
        else:
            return "MaClasse"
    
    def _generate_generic_code(self, request: str, language: str) -> str:
        """
        Génère du code générique intelligent basé sur l'analyse de la demande
        
        Args:
            request: Demande textuelle
            language: Langage cible
            
        Returns:
            str: Code généré
        """
        generator = self.generators.get(language, self.generators["python"])
        
        # Analyse sémantique de la demande
        request_lower = request.lower()
        
        # Détection de patterns spécifiques
        if any(word in request_lower for word in ["lire", "read", "fichier", "file"]):
            if hasattr(generator, 'generate_file_processor'):
                return generator.generate_file_processor()
            else:
                return self._generate_file_handler(language)
        elif any(word in request_lower for word in ["api", "serveur", "server", "web"]):
            return self._generate_api_server(language)
        elif any(word in request_lower for word in ["base", "données", "database", "sql"]):
            return self._generate_database_handler(language)
        elif any(word in request_lower for word in ["gui", "interface", "fenêtre", "window"]):
            return self._generate_gui_app(language)
        elif any(word in request_lower for word in ["email", "mail", "envoi", "send"]):
            return self._generate_email_sender(language)
        elif any(word in request_lower for word in ["json", "xml", "csv", "parse"]):
            return self._generate_data_parser(language)
        elif any(word in request_lower for word in ["test", "unit", "pytest"]):
            return self._generate_test_framework(language)
        elif any(word in request_lower for word in ["math", "calcul", "somme", "addition", "soustraction", "multipli"]):
            return self._generate_math_operations(language)
        else:
            # Au lieu de générer hello world par défaut, indiquer qu'on n'a pas compris la demande
            return f"""# Je n'ai pas bien compris votre demande
# Voici quelques exemples de ce que vous pouvez demander:
# - Une fonction factorielle
# - Un programme Hello World
# - Une fonction pour lire un fichier
# - Une API simple
# - Une interface graphique
# - Une calculatrice
# - Un traitement de données CSV/JSON
# 
# Votre demande était: "{request}"
# 
# Essayez de reformuler avec plus de détails sur ce que vous souhaitez."""
    
    def _generate_file_handler(self, language: str) -> str:
        """
        Génère un gestionnaire de fichiers selon le langage
        
        Args:
            language: Langage cible
            
        Returns:
            str: Code généré
        """
        if language == "python" and hasattr(self.generators["python"], 'generate_file_processor'):
            return self.generators["python"].generate_file_processor()
        else:
            return self.generators[language].generate_hello_world()
    
    def _generate_api_server(self, language: str) -> str:
        """
        Génère un serveur API selon le langage
        
        Args:
            language: Langage cible
            
        Returns:
            str: Code généré
        """
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
    })'''
        else:
            return self.generators[language].generate_hello_world()

    def _generate_database_handler(self, language: str) -> str:
        """
        Génère un gestionnaire de base de données selon le langage
        
        Args:
            language: Langage cible
            
        Returns:
            str: Code généré
        """
        if language == "python":
            return '''import sqlite3
from typing import Dict, List, Any, Optional
import os
import datetime

class DatabaseHandler:
    """Gestionnaire de base de données SQLite"""
    
    def __init__(self, db_path: str = "app_database.db"):
        """Initialise le gestionnaire de base de données"""
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Obtient une connexion à la base de données"""
        return sqlite3.connect(self.db_path)
        
    def init_database(self):
        """Initialise la base de données avec des tables de base"""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
'''
        else:
            return self.generators[language].generate_hello_world()

    def _generate_gui_app(self, language: str) -> str:
        """
        Génère une application GUI selon le langage
        
        Args:
            language: Langage cible
            
        Returns:
            str: Code généré
        """
        if language == "python":
            return '''import tkinter as tk
from tkinter import ttk, messagebox
import datetime

class SimpleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Application Simple")
        self.root.geometry("400x300")
        self.setup_ui()
    
    def setup_ui(self):
        frame = ttk.Frame(self.root, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Application Demo").grid(column=0, row=0, columnspan=2)
        
        ttk.Button(frame, text="Afficher message", command=self.show_message).grid(column=0, row=1)
        ttk.Button(frame, text="Quitter", command=self.root.quit).grid(column=1, row=1)
    
    def show_message(self):
        now = datetime.datetime.now()
        messagebox.showinfo("Message", f"Hello World! Il est {now.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleApp(root)
    root.mainloop()
'''
        else:
            return self.generators[language].generate_hello_world()

    def _generate_email_sender(self, language: str) -> str:
        """
        Génère un module d'envoi d'email selon le langage
        
        Args:
            language: Langage cible
            
        Returns:
            str: Code généré
        """
        if language == "python":
            return '''import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime

class EmailSender:
    def __init__(self, smtp_server, port, username, password):
        self.smtp_server = smtp_server
        self.port = port
        self.username = username
        self.password = password
    
    def send_email(self, to_email, subject, body):
        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            server = smtplib.SMTP(self.smtp_server, self.port)
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            return {"success": True, "message": "Email envoyé avec succès"}
        except Exception as e:
            return {"success": False, "error": str(e)}
'''
        else:
            return self.generators[language].generate_hello_world()

    def _generate_data_parser(self, language: str) -> str:
        """
        Génère un module de traitement de données selon le langage
        
        Args:
            language: Langage cible
            
        Returns:
            str: Code généré
        """
        if language == "python":
            return '''import json
import csv
import xml.etree.ElementTree as ET

class DataParser:
    def __init__(self):
        self.supported_formats = ['json', 'csv', 'xml']
    
    def parse_json(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def parse_csv(self, file_path):
        results = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(dict(row))
        return results
    
    def parse_xml(self, file_path):
        tree = ET.parse(file_path)
        root = tree.getroot()
        return self._element_to_dict(root)
    
    def _element_to_dict(self, element):
        result = {}
        for child in element:
            if list(child):  # Has children
                result[child.tag] = self._element_to_dict(child)
            else:
                result[child.tag] = child.text
        return result
'''
        else:
            return self.generators[language].generate_hello_world()

    def _generate_test_framework(self, language: str) -> str:
        """
        Génère un framework de test selon le langage
        
        Args:
            language: Langage cible
            
        Returns:
            str: Code généré
        """
        if language == "python":
            return '''import unittest
from typing import Dict, Any

class TestCase(unittest.TestCase):
    """Classe de test étendue avec fonctionnalités supplémentaires"""
    
    def setUp(self):
        """Préparation avant chaque test"""
        self.test_data = {"key": "value"}
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        self.test_data = {}
    
    def test_example(self):
        """Test d'exemple"""
        self.assertEqual(1 + 1, 2)
        self.assertIn("key", self.test_data)
        self.assertEqual(self.test_data["key"], "value")

if __name__ == "__main__":
    unittest.main()
'''
        else:
            return self.generators[language].generate_hello_world()

    def _generate_calculator(self, language: str) -> str:
        """
        Génère une calculatrice selon le langage
        
        Args:
            language: Langage cible
            
        Returns:
            str: Code généré
        """
        if language == "python" and hasattr(self.generators["python"], 'generate_calculator'):
            return self.generators["python"].generate_calculator()
        else:
            return self.generators[language].generate_hello_world()

    def _generate_math_operations(self, language: str) -> str:
        """
        Génère des fonctions mathématiques selon le langage
        
        Args:
            language: Langage cible
            
        Returns:
            str: Code généré
        """
        if language == "python":
            return '''import math
from typing import List, Union, Optional

def addition(a: float, b: float) -> float:
    """
    Additionne deux nombres
    
    Args:
        a: Premier nombre
        b: Second nombre
        
    Returns:
        float: Résultat de l'addition
    """
    return a + b

def soustraction(a: float, b: float) -> float:
    """
    Soustrait b de a
    
    Args:
        a: Premier nombre
        b: Second nombre
        
    Returns:
        float: Résultat de la soustraction
    """
    return a - b

def multiplication(a: float, b: float) -> float:
    """
    Multiplie deux nombres
    
    Args:
        a: Premier nombre
        b: Second nombre
        
    Returns:
        float: Résultat de la multiplication
    """
    return a * b

def division(a: float, b: float) -> Optional[float]:
    """
    Divise a par b
    
    Args:
        a: Numérateur
        b: Dénominateur
        
    Returns:
        float: Résultat de la division, ou None si b est zéro
    """
    if b == 0:
        print("Erreur: Division par zéro")
        return None
    return a / b

def calculer(expression: str) -> Optional[float]:
    """
    Évalue une expression mathématique simple
    
    Args:
        expression: Expression à évaluer (ex: "2 + 3 * 4")
        
    Returns:
        float: Résultat de l'expression
    """
    try:
        # Attention: eval peut être dangereux dans un contexte réel
        return eval(expression)
    except Exception as e:
        print(f"Erreur lors de l'évaluation: {e}")
        return None

# Exemple d'utilisation
if __name__ == "__main__":
    print(f"2 + 3 = {addition(2, 3)}")
    print(f"5 - 2 = {soustraction(5, 2)}")
    print(f"4 * 6 = {multiplication(4, 6)}")
    print(f"8 / 2 = {division(8, 2)}")
    print(f"8 / 0 = {division(8, 0)}")
    print(f"Évaluation de '2 + 3 * 4' = {calculer('2 + 3 * 4')}")
'''
        elif language == "javascript":
            return '''/**
 * Module de fonctions mathématiques
 */

/**
 * Additionne deux nombres
 * @param {number} a - Premier nombre
 * @param {number} b - Second nombre
 * @returns {number} Le résultat de l'addition
 */
function addition(a, b) {
    return a + b;
}

/**
 * Soustrait b de a
 * @param {number} a - Premier nombre
 * @param {number} b - Second nombre
 * @returns {number} Le résultat de la soustraction
 */
function soustraction(a, b) {
    return a - b;
}

/**
 * Multiplie deux nombres
 * @param {number} a - Premier nombre
 * @param {number} b - Second nombre
 * @returns {number} Le résultat de la multiplication
 */
function multiplication(a, b) {
    return a * b;
}

/**
 * Divise a par b
 * @param {number} a - Numérateur
 * @param {number} b - Dénominateur
 * @returns {number|null} Le résultat de la division ou null si b est zéro
 */
function division(a, b) {
    if (b === 0) {
        console.error("Erreur: Division par zéro");
        return null;
    }
    return a / b;
}

/**
 * Évalue une expression mathématique
 * @param {string} expression - Expression à évaluer
 * @returns {number|null} Résultat de l'expression ou null en cas d'erreur
 */
function calculer(expression) {
    try {
        // Attention: eval peut être dangereux dans un contexte réel
        return eval(expression);
    } catch (e) {
        console.error(`Erreur lors de l'évaluation: ${e}`);
        return null;
    }
}

// Exemples d'utilisation
console.log(`2 + 3 = ${addition(2, 3)}`);
console.log(`5 - 2 = ${soustraction(5, 2)}`);
console.log(`4 * 6 = ${multiplication(4, 6)}`);
console.log(`8 / 2 = ${division(8, 2)}`);
console.log(`8 / 0 = ${division(8, 0)}`);
console.log(`Évaluation de '2 + 3 * 4' = ${calculer('2 + 3 * 4')}`);
'''
        else:
            return self.generators[language].generate_hello_world()
    
    def get_supported_languages(self) -> List[str]:
        """
        Retourne la liste des langages supportés
        
        Returns:
            List[str]: Liste des langages supportés
        """
        return list(self.generators.keys())
    
    def get_pattern_info(self, pattern_name: str) -> Optional[Dict[str, str]]:
        """
        Retourne des informations sur un pattern particulier
        
        Args:
            pattern_name: Nom du pattern
            
        Returns:
            Optional[Dict[str, str]]: Informations sur le pattern
        """
        patterns = {
            "factorial": {
                "description": "Calcule la factorielle d'un nombre",
                "complexity": "O(n)",
                "available_in": ["python", "javascript"]
            },
            "fibonacci": {
                "description": "Génère la séquence de Fibonacci",
                "complexity": "O(n)",
                "available_in": ["python"]
            },
            "sort": {
                "description": "Trie une liste de valeurs",
                "complexity": "O(n log n) ou O(n²)",
                "available_in": ["python"]
            }
        }
        
        return patterns.get(pattern_name)
