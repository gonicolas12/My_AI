"""
Tests pour le système de génération de code modulaire
"""
import unittest
import sys
import os

# Ajouter le répertoire parent au path pour que les imports fonctionnent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.generators import CodeGenerator, PythonCodeGenerator, JavaScriptCodeGenerator, HTMLCodeGenerator


class TestCodeGenerator(unittest.TestCase):
    """Test du générateur de code modulaire"""
    
    def setUp(self):
        self.code_generator = CodeGenerator()
        self.python_generator = PythonCodeGenerator()
        self.js_generator = JavaScriptCodeGenerator()
        self.html_generator = HTMLCodeGenerator()
        
    def test_main_generator(self):
        """Test du générateur principal avec détection de langage"""
        # Test Python
        python_code = self.code_generator.generate_code("Générez une fonction factorielle en Python")
        self.assertIn("def factorielle", python_code)
        self.assertIn("calcule la factorielle", python_code.lower())
        
        # Test JavaScript
        js_code = self.code_generator.generate_code("Générez une fonction pour calculer une factorielle en JavaScript")
        self.assertIn("function", js_code)
        self.assertIn("factorial", js_code)
        
        # Test HTML
        html_code = self.code_generator.generate_code("Créez un formulaire HTML")
        self.assertIn("<form", html_code)
        self.assertIn("</form>", html_code)
        
    def test_python_generator(self):
        """Test du générateur Python"""
        # Hello World
        hello_world = self.python_generator.generate_hello_world()
        self.assertIn("print", hello_world)
        self.assertIn("Hello, World", hello_world)
        
        # Fonction
        function_code = self.python_generator.generate_function("calculer_age")
        self.assertIn("def calculer_age", function_code)
        
        # Classe
        class_code = self.python_generator.generate_class("Personne")
        self.assertIn("class Personne", class_code)
        self.assertIn("__init__", class_code)
        
    def test_js_generator(self):
        """Test du générateur JavaScript"""
        # Hello World
        hello_world = self.js_generator.generate_hello_world()
        self.assertIn("console.log", hello_world)
        self.assertIn("Hello, World", hello_world)
        
        # Fonction
        function_code = self.js_generator.generate_function("calculateAge")
        self.assertIn("function calculateAge", function_code)
        
        # Classe
        class_code = self.js_generator.generate_class("Person")
        self.assertIn("class Person", class_code)
        self.assertIn("constructor", class_code)
        
    def test_html_generator(self):
        """Test du générateur HTML"""
        # Hello World
        hello_world = self.html_generator.generate_hello_world()
        self.assertIn("<!DOCTYPE html>", hello_world)
        self.assertIn("<html", hello_world)
        
        # Formulaire
        fields = [
            {"type": "text", "name": "name", "label": "Nom", "required": True},
            {"type": "email", "name": "email", "label": "Email", "required": True}
        ]
        form_code = self.html_generator.generate_form("/submit", "post", "Formulaire de contact", fields)
        self.assertIn("<form", form_code)
        self.assertIn("action=\"/submit\"", form_code)
        self.assertIn("method=\"post\"", form_code)
        self.assertIn("<input type=\"text\"", form_code)
        self.assertIn("<input type=\"email\"", form_code)


if __name__ == '__main__':
    unittest.main()
