"""
Générateur de code Python
"""

from typing import Dict, List, Any, Optional
from .base_generator import BaseCodeGenerator

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

            "module": '''"""
{module_name}
{description}
"""

{imports}

{code_body}

{main_code}
''',
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

            "hello_world": '''def main():
    """
    Programme simple affichant 'Hello, world!'
    """
    print("Hello, world!")

if __name__ == "__main__":
    main()''',

            "file_processor": '''import os
import csv
import json
from typing import List, Dict, Any

def read_csv_file(filepath: str) -> List[Dict[str, Any]]:
    """
    Lit un fichier CSV et retourne les données sous forme de liste de dictionnaires
    
    Args:
        filepath (str): Chemin vers le fichier CSV
        
    Returns:
        List[Dict[str, Any]]: Données du fichier CSV
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Le fichier {filepath} n'existe pas")
        
    data = []
    with open(filepath, 'r', newline='', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            data.append(row)
            
    return data

def save_to_json(data: List[Dict[str, Any]], output_filepath: str) -> None:
    """
    Sauvegarde des données dans un fichier JSON
    
    Args:
        data (List[Dict[str, Any]]): Données à sauvegarder
        output_filepath (str): Chemin du fichier de sortie
    """
    with open(output_filepath, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=4, ensure_ascii=False)
        
    print(f"Données sauvegardées dans {output_filepath}")

def process_file(input_filepath: str, output_filepath: str) -> None:
    """
    Traite un fichier CSV et sauvegarde les résultats en JSON
    
    Args:
        input_filepath (str): Chemin du fichier d'entrée (CSV)
        output_filepath (str): Chemin du fichier de sortie (JSON)
    """
    try:
        data = read_csv_file(input_filepath)
        # Ici, vous pourriez ajouter des traitements supplémentaires sur les données
        save_to_json(data, output_filepath)
    except Exception as e:
        print(f"Erreur lors du traitement du fichier: {e}")

if __name__ == "__main__":
    # Exemple d'utilisation
    input_file = "input.csv"  # À remplacer par votre fichier
    output_file = "output.json"
    
    process_file(input_file, output_file)''',
        }
    
    def generate_function(self, name: str, params: List[str] = None, description: str = "", 
                         body: str = None, return_value: str = "None") -> str:
        """
        Génère une fonction Python
        
        Args:
            name: Nom de la fonction
            params: Liste des paramètres
            description: Description de la fonction
            body: Corps de la fonction (code à l'intérieur)
            return_value: Valeur de retour
            
        Returns:
            str: Code de la fonction générée
        """
        if params is None:
            params = []
            
        if body is None:
            body = "    # TODO: Implémentez votre logique ici\n    pass"
            
        return self.templates["function"].format(
            name=name,
            params=", ".join(params),
            description=description or f"Fonction {name} générée automatiquement",
            body=body,
            return_value=return_value
        )
    
    def generate_class(self, name: str, description: str = "", 
                      attributes: List[str] = None, methods: List[Dict[str, Any]] = None) -> str:
        """
        Génère une classe Python
        
        Args:
            name: Nom de la classe
            description: Description de la classe
            attributes: Liste des attributs de la classe
            methods: Liste des méthodes de la classe (dictionnaires avec 'name', 'params', 'body', etc.)
            
        Returns:
            str: Code de la classe générée
        """
        if attributes is None:
            attributes = []
            
        if methods is None:
            methods = []
            
        # Générer le constructeur
        init_params = ""
        init_body = "        # Initialisation des attributs"
        
        if attributes:
            init_params = ", " + ", ".join(attributes)
            init_body = "\n        ".join([f"self.{attr} = {attr}" for attr in attributes])
            
        # Générer les méthodes
        methods_code = ""
        for method in methods:
            method_name = method.get("name", "method")
            method_params = method.get("params", [])
            method_body = method.get("body", "        pass")
            method_desc = method.get("description", f"Méthode {method_name}")
            
            methods_code += f"\n    def {method_name}(self{', ' + ', '.join(method_params) if method_params else ''}):\n"
            methods_code += f"        \"\"\"\n        {method_desc}\n        \"\"\"\n"
            methods_code += f"{method_body}\n"
            
        return self.templates["class"].format(
            name=name,
            description=description or f"Classe {name} générée automatiquement",
            init_params=init_params,
            init_body=init_body,
            methods=methods_code
        )
    
    def generate_hello_world(self) -> str:
        """
        Génère un programme Hello World en Python
        
        Returns:
            str: Code du programme Hello World
        """
        return self.patterns["hello_world"]
    
    def generate_factorial(self) -> str:
        """
        Génère une fonction de calcul de factorielle
        
        Returns:
            str: Code de la fonction factorielle
        """
        return self.patterns["factorial"]
        
    def generate_fibonacci(self) -> str:
        """
        Génère une fonction de génération de la séquence de Fibonacci
        
        Returns:
            str: Code de la fonction Fibonacci
        """
        return self.patterns["fibonacci"]
        
    def generate_sort_algorithm(self, algo_type: str = "all") -> str:
        """
        Génère un algorithme de tri
        
        Args:
            algo_type: Type d'algorithme ("bulle", "rapide", "all")
            
        Returns:
            str: Code de l'algorithme de tri
        """
        return self.patterns["sort"]
        
    def generate_file_processor(self) -> str:
        """
        Génère un processeur de fichiers (CSV, JSON)
        
        Returns:
            str: Code du processeur de fichiers
        """
        return self.patterns["file_processor"]
        
    def generate_module(self, name: str, description: str, imports: List[str] = None, 
                       functions: List[Dict[str, Any]] = None, classes: List[Dict[str, Any]] = None,
                       include_main: bool = True) -> str:
        """
        Génère un module Python complet
        
        Args:
            name: Nom du module
            description: Description du module
            imports: Liste des imports
            functions: Liste des fonctions à inclure
            classes: Liste des classes à inclure
            include_main: Si True, inclut un bloc if __name__ == "__main__"
            
        Returns:
            str: Code complet du module
        """
        if imports is None:
            imports = []
            
        if functions is None:
            functions = []
            
        if classes is None:
            classes = []
            
        # Générer les imports
        imports_code = "\n".join(imports) + ("\n\n" if imports else "")
        
        # Générer le corps du code (classes et fonctions)
        code_body = ""
        
        # Ajouter les classes
        for cls in classes:
            cls_name = cls.get("name", "MyClass")
            cls_desc = cls.get("description", f"Classe {cls_name}")
            cls_attrs = cls.get("attributes", [])
            cls_methods = cls.get("methods", [])
            
            code_body += self.generate_class(cls_name, cls_desc, cls_attrs, cls_methods) + "\n\n"
            
        # Ajouter les fonctions
        for func in functions:
            func_name = func.get("name", "my_function")
            func_params = func.get("params", [])
            func_desc = func.get("description", f"Fonction {func_name}")
            func_body = func.get("body", "    pass")
            func_return = func.get("return_value", "None")
            
            code_body += self.generate_function(func_name, func_params, func_desc, func_body, func_return) + "\n\n"
            
        # Générer le bloc main si demandé
        main_code = ""
        if include_main:
            main_code = self.templates["main"].format(
                main_body="    print('Exécution du module " + name + "')"
            )
            
        # Assembler le module complet
        return self.templates["module"].format(
            module_name=name,
            description=description,
            imports=imports_code,
            code_body=code_body,
            main_code=main_code
        )
    
    def generate_sort(self) -> str:
        """
        Génère un algorithme de tri en Python
        
        Returns:
            str: Code d'un algorithme de tri
        """
        return '''def tri_bulle(liste):
    """
    Implémentation du tri à bulle en Python
    
    Args:
        liste: Liste d'éléments à trier
        
    Returns:
        Liste triée
    """
    n = len(liste)
    for i in range(n):
        for j in range(0, n - i - 1):
            if liste[j] > liste[j + 1]:
                liste[j], liste[j + 1] = liste[j + 1], liste[j]
    return liste

def tri_rapide(liste):
    """
    Implémentation du tri rapide (quicksort) en Python
    
    Args:
        liste: Liste d'éléments à trier
        
    Returns:
        Liste triée
    """
    if len(liste) <= 1:
        return liste
    
    pivot = liste[len(liste) // 2]
    gauche = [x for x in liste if x < pivot]
    milieu = [x for x in liste if x == pivot]
    droite = [x for x in liste if x > pivot]
    
    return tri_rapide(gauche) + milieu + tri_rapide(droite)

# Test des algorithmes de tri
if __name__ == "__main__":
    # Exemple avec une liste non triée
    liste_test = [64, 34, 25, 12, 22, 11, 90]
    
    print("Liste non triée:", liste_test)
    
    # Test du tri à bulle
    liste_triee_bulle = tri_bulle(liste_test.copy())
    print("Tri à bulle:", liste_triee_bulle)
    
    # Test du tri rapide
    liste_triee_rapide = tri_rapide(liste_test.copy())
    print("Tri rapide:", liste_triee_rapide)
'''
