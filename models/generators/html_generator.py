"""
Générateur de code HTML
"""

from typing import Dict, List, Any, Optional
from .base_generator import BaseCodeGenerator

class HTMLCodeGenerator(BaseCodeGenerator):
    """Générateur de code HTML"""
    
    def __init__(self):
        super().__init__("html")
    
    def _load_templates(self) -> Dict[str, str]:
        return {
            "basic_page": '''<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {styles}
</head>
<body>
    {content}
    {scripts}
</body>
</html>''',

            "component": '''<!-- {name} Component -->
<div class="{name}">
    {content}
</div>''',

            "form": '''<form action="{action}" method="{method}">
    <h2>{title}</h2>
    {form_elements}
    <button type="submit">{submit_text}</button>
</form>''',

            "table": '''<table class="{table_class}">
    <thead>
        <tr>
            {headers}
        </tr>
    </thead>
    <tbody>
        {rows}
    </tbody>
</table>''',

            "list": '''<{list_type} class="{list_class}">
    {items}
</{list_type}>''',

            "navbar": '''<nav class="navbar {navbar_class}">
    <div class="navbar-brand">
        <a href="{home_url}">{brand_name}</a>
    </div>
    <ul class="navbar-menu">
        {menu_items}
    </ul>
</nav>''',

            "css": '''<style>
{css_content}
</style>''',

            "script": '''<script>
{script_content}
</script>''',

            "card": '''<div class="card {card_class}">
    {card_header}
    <div class="card-body">
        {card_content}
    </div>
    {card_footer}
</div>''',

            "grid": '''<div class="grid {grid_class}">
    {grid_items}
</div>''',
        }
    
    def _load_patterns(self) -> Dict[str, str]:
        return {
            "hello_world": '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hello World</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .container {
            text-align: center;
            background-color: white;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 20px;
        }
        p {
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Hello, World!</h1>
        <p>Voici une page HTML simple.</p>
    </div>
</body>
</html>''',

            "login_form": '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Formulaire de Connexion</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .login-container {
            background-color: white;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            width: 350px;
        }
        h2 {
            color: #333;
            margin-bottom: 20px;
            text-align: center;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
        }
        input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 12px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        .forgot-password {
            text-align: center;
            margin-top: 15px;
        }
        .forgot-password a {
            color: #666;
            text-decoration: none;
        }
        .forgot-password a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h2>Connexion</h2>
        <form action="/login" method="post">
            <div class="form-group">
                <label for="username">Nom d'utilisateur</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Mot de passe</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Se connecter</button>
        </form>
        <div class="forgot-password">
            <a href="/forgot-password">Mot de passe oublié?</a>
        </div>
    </div>
</body>
</html>''',

            "responsive_layout": '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Layout Responsive</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
        }
        
        .container {
            width: 90%;
            max-width: 1200px;
            margin: 0 auto;
            overflow: hidden;
        }
        
        header {
            background-color: #333;
            color: white;
            padding: 1rem;
        }
        
        nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 1.5rem;
            font-weight: bold;
        }
        
        .menu {
            display: flex;
            list-style: none;
        }
        
        .menu li {
            margin-left: 1rem;
        }
        
        .menu a {
            color: white;
            text-decoration: none;
        }
        
        .menu a:hover {
            text-decoration: underline;
        }
        
        .hero {
            background-color: #f4f4f4;
            padding: 4rem 0;
            text-align: center;
        }
        
        .hero h1 {
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }
        
        .hero p {
            font-size: 1.2rem;
            margin-bottom: 2rem;
        }
        
        .btn {
            display: inline-block;
            background-color: #333;
            color: white;
            padding: 0.75rem 1.5rem;
            text-decoration: none;
            border-radius: 5px;
        }
        
        .btn:hover {
            background-color: #555;
        }
        
        .features {
            padding: 4rem 0;
        }
        
        .features h2 {
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 2rem;
        }
        
        .feature {
            background-color: #fff;
            padding: 2rem;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }
        
        .feature h3 {
            margin-bottom: 1rem;
        }
        
        footer {
            background-color: #333;
            color: white;
            text-align: center;
            padding: 2rem 0;
        }
        
        /* Media queries pour le responsive */
        @media (max-width: 768px) {
            .menu {
                display: none;
            }
            
            .hero h1 {
                font-size: 2rem;
            }
            
            .grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <nav>
                <div class="logo">MonSite</div>
                <ul class="menu">
                    <li><a href="#">Accueil</a></li>
                    <li><a href="#">Fonctionnalités</a></li>
                    <li><a href="#">À propos</a></li>
                    <li><a href="#">Contact</a></li>
                </ul>
            </nav>
        </div>
    </header>
    
    <section class="hero">
        <div class="container">
            <h1>Bienvenue sur notre site</h1>
            <p>Un site web responsive moderne et élégant</p>
            <a href="#" class="btn">En savoir plus</a>
        </div>
    </section>
    
    <section class="features">
        <div class="container">
            <h2>Nos fonctionnalités</h2>
            <div class="grid">
                <div class="feature">
                    <h3>Fonctionnalité 1</h3>
                    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam id dolor id nibh ultricies.</p>
                </div>
                <div class="feature">
                    <h3>Fonctionnalité 2</h3>
                    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam id dolor id nibh ultricies.</p>
                </div>
                <div class="feature">
                    <h3>Fonctionnalité 3</h3>
                    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam id dolor id nibh ultricies.</p>
                </div>
            </div>
        </div>
    </section>
    
    <footer>
        <div class="container">
            <p>&copy; 2023 MonSite. Tous droits réservés.</p>
        </div>
    </footer>
</body>
</html>''',

            "data_table": '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tableau de données</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        h1 {
            text-align: center;
            margin-bottom: 30px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        th {
            background-color: #f8f8f8;
            font-weight: bold;
        }
        
        tr:hover {
            background-color: #f5f5f5;
        }
        
        .search-container {
            margin-bottom: 20px;
        }
        
        .search-container input {
            padding: 8px;
            width: 300px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        
        .pagination {
            display: flex;
            justify-content: center;
            list-style: none;
            padding: 0;
        }
        
        .pagination li {
            margin: 0 5px;
        }
        
        .pagination a {
            display: block;
            padding: 8px 12px;
            text-decoration: none;
            border: 1px solid #ddd;
            color: #333;
            border-radius: 4px;
        }
        
        .pagination a.active {
            background-color: #4CAF50;
            color: white;
            border-color: #4CAF50;
        }
        
        .pagination a:hover:not(.active) {
            background-color: #ddd;
        }
    </style>
</head>
<body>
    <h1>Liste des utilisateurs</h1>
    
    <div class="search-container">
        <input type="text" id="searchInput" placeholder="Rechercher..." onkeyup="searchTable()">
    </div>
    
    <table id="dataTable">
        <thead>
            <tr>
                <th>ID</th>
                <th>Nom</th>
                <th>Email</th>
                <th>Rôle</th>
                <th>Date d'inscription</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>1</td>
                <td>Jean Dupont</td>
                <td>jean.dupont@example.com</td>
                <td>Administrateur</td>
                <td>10/01/2023</td>
            </tr>
            <tr>
                <td>2</td>
                <td>Marie Martin</td>
                <td>marie.martin@example.com</td>
                <td>Éditeur</td>
                <td>15/02/2023</td>
            </tr>
            <tr>
                <td>3</td>
                <td>Pierre Dubois</td>
                <td>pierre.dubois@example.com</td>
                <td>Utilisateur</td>
                <td>20/03/2023</td>
            </tr>
            <tr>
                <td>4</td>
                <td>Sophie Lefebvre</td>
                <td>sophie.lefebvre@example.com</td>
                <td>Éditeur</td>
                <td>05/04/2023</td>
            </tr>
            <tr>
                <td>5</td>
                <td>Thomas Bernard</td>
                <td>thomas.bernard@example.com</td>
                <td>Utilisateur</td>
                <td>18/05/2023</td>
            </tr>
        </tbody>
    </table>
    
    <ul class="pagination">
        <li><a href="#">&laquo;</a></li>
        <li><a href="#" class="active">1</a></li>
        <li><a href="#">2</a></li>
        <li><a href="#">3</a></li>
        <li><a href="#">4</a></li>
        <li><a href="#">5</a></li>
        <li><a href="#">&raquo;</a></li>
    </ul>
    
    <script>
        function searchTable() {
            // Récupérer le texte de recherche et convertir en minuscules
            var input = document.getElementById("searchInput");
            var filter = input.value.toLowerCase();
            var table = document.getElementById("dataTable");
            var rows = table.getElementsByTagName("tr");
            
            // Parcourir toutes les lignes du tableau, en commençant par l'index 1 (pour éviter les en-têtes)
            for (var i = 1; i < rows.length; i++) {
                var showRow = false;
                var cells = rows[i].getElementsByTagName("td");
                
                // Parcourir toutes les cellules de la ligne
                for (var j = 0; j < cells.length; j++) {
                    var cell = cells[j];
                    if (cell) {
                        var content = cell.textContent || cell.innerText;
                        if (content.toLowerCase().indexOf(filter) > -1) {
                            showRow = true;
                            break;
                        }
                    }
                }
                
                // Afficher ou masquer la ligne en fonction du résultat de la recherche
                rows[i].style.display = showRow ? "" : "none";
            }
        }
    </script>
</body>
</html>''',
        }
    
    def generate_function(self, name: str, params: List[str] = None, description: str = "") -> str:
        """
        HTML n'a pas vraiment de fonctions comme en programmation,
        cette méthode renvoie donc un commentaire HTML indiquant que
        HTML n'a pas de fonctions.
        
        Returns:
            str: Message explicatif
        """
        return f"<!-- HTML n'a pas de fonctions comme dans les langages de programmation. -->"
    
    def generate_class(self, name: str, description: str = "") -> str:
        """
        HTML n'a pas de classes comme en programmation (bien qu'il y ait des classes CSS),
        cette méthode renvoie donc un commentaire HTML.
        
        Returns:
            str: Message explicatif
        """
        return f"<!-- HTML n'a pas de classes comme dans les langages de programmation. -->"
    
    def generate_hello_world(self) -> str:
        """
        Génère une page HTML Hello World
        
        Returns:
            str: Code HTML Hello World
        """
        return self.patterns["hello_world"]
    
    def generate_factorial(self) -> str:
        """
        HTML ne peut pas calculer de factorielle directement,
        cette méthode renvoie donc une page HTML avec JavaScript pour calculer des factorielles
        
        Returns:
            str: Page HTML avec calcul de factorielle en JavaScript
        """
        return '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calcul de Factorielle</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #333;
        }
        .input-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
        }
        input, button {
            padding: 8px;
        }
        button {
            background-color: #4CAF50;
            color: white;
            border: none;
            cursor: pointer;
        }
        button:hover {
            background-color: #45a049;
        }
        #result {
            margin-top: 20px;
            padding: 10px;
            border: 1px solid #ddd;
            background-color: #f9f9f9;
        }
    </style>
</head>
<body>
    <h1>Calculateur de Factorielle</h1>
    
    <div class="input-group">
        <label for="number">Entrez un nombre :</label>
        <input type="number" id="number" min="0" max="170" step="1" value="5">
        <button onclick="calculateFactorial()">Calculer</button>
    </div>
    
    <div id="result">
        Le résultat s'affichera ici
    </div>
    
    <script>
        function factorial(n) {
            if (n < 0) {
                return "La factorielle n'est pas définie pour les nombres négatifs";
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
        
        function calculateFactorial() {
            const number = parseInt(document.getElementById("number").value);
            const resultElement = document.getElementById("result");
            
            if (isNaN(number)) {
                resultElement.textContent = "Veuillez entrer un nombre valide";
            } else if (number > 170) {
                resultElement.textContent = "Nombre trop grand pour JavaScript (max 170)";
            } else {
                const result = factorial(number);
                resultElement.textContent = `${number}! = ${result}`;
            }
        }
    </script>
</body>
</html>'''
    
    def generate_basic_page(self, title: str, content: str, 
                          css: str = None, javascript: str = None, lang: str = "fr") -> str:
        """
        Génère une page HTML basique
        
        Args:
            title: Titre de la page
            content: Contenu HTML du body
            css: CSS optionnel
            javascript: JavaScript optionnel
            lang: Code de langue
            
        Returns:
            str: Code HTML complet
        """
        styles = ""
        if css:
            styles = self.templates["css"].format(css_content=css)
            
        scripts = ""
        if javascript:
            scripts = self.templates["script"].format(script_content=javascript)
            
        return self.templates["basic_page"].format(
            lang=lang,
            title=title,
            styles=styles,
            content=content,
            scripts=scripts
        )
    
    def generate_form(self, action: str, method: str, title: str, fields: List[Dict[str, Any]],
                    submit_text: str = "Envoyer") -> str:
        """
        Génère un formulaire HTML
        
        Args:
            action: Action du formulaire (URL)
            method: Méthode du formulaire (GET, POST)
            title: Titre du formulaire
            fields: Liste des champs (dictionnaires avec type, name, label, etc.)
            submit_text: Texte du bouton d'envoi
            
        Returns:
            str: Code HTML du formulaire
        """
        form_elements = ""
        
        for field in fields:
            field_type = field.get("type", "text")
            field_name = field.get("name", "")
            field_id = field.get("id", field_name)
            field_label = field.get("label", field_name.capitalize())
            field_required = "required" if field.get("required", False) else ""
            field_placeholder = field.get("placeholder", "")
            
            form_elements += f'''    <div class="form-group">
        <label for="{field_id}">{field_label}</label>
'''
            
            if field_type == "textarea":
                form_elements += f'        <textarea id="{field_id}" name="{field_name}" placeholder="{field_placeholder}" {field_required}></textarea>\n'
            elif field_type == "select":
                form_elements += f'        <select id="{field_id}" name="{field_name}" {field_required}>\n'
                options = field.get("options", [])
                for option in options:
                    option_value = option.get("value", "")
                    option_text = option.get("text", option_value)
                    form_elements += f'            <option value="{option_value}">{option_text}</option>\n'
                form_elements += '        </select>\n'
            else:
                form_elements += f'        <input type="{field_type}" id="{field_id}" name="{field_name}" placeholder="{field_placeholder}" {field_required}>\n'
                
            form_elements += '    </div>\n'
            
        return self.templates["form"].format(
            action=action,
            method=method,
            title=title,
            form_elements=form_elements,
            submit_text=submit_text
        )
    
    def generate_table(self, headers: List[str], rows: List[List[str]], 
                     table_class: str = "data-table") -> str:
        """
        Génère un tableau HTML
        
        Args:
            headers: Liste des en-têtes de colonnes
            rows: Liste des lignes (chaque ligne est une liste de cellules)
            table_class: Classe CSS du tableau
            
        Returns:
            str: Code HTML du tableau
        """
        headers_html = "\n            ".join([f"<th>{header}</th>" for header in headers])
        
        rows_html = ""
        for row in rows:
            cells = "\n            ".join([f"<td>{cell}</td>" for cell in row])
            rows_html += f"        <tr>\n            {cells}\n        </tr>\n"
            
        return self.templates["table"].format(
            table_class=table_class,
            headers=headers_html,
            rows=rows_html
        )
    
    def generate_list(self, items: List[str], ordered: bool = False,
                    list_class: str = "") -> str:
        """
        Génère une liste HTML (ordonnée ou non)
        
        Args:
            items: Liste des éléments
            ordered: Si True, génère une liste ordonnée (ol), sinon non ordonnée (ul)
            list_class: Classe CSS de la liste
            
        Returns:
            str: Code HTML de la liste
        """
        list_type = "ol" if ordered else "ul"
        items_html = "\n    ".join([f"<li>{item}</li>" for item in items])
        
        return self.templates["list"].format(
            list_type=list_type,
            list_class=list_class,
            items=items_html
        )
    
    def generate_navbar(self, brand_name: str, menu_items: List[Dict[str, str]], 
                      home_url: str = "/", navbar_class: str = "") -> str:
        """
        Génère une barre de navigation
        
        Args:
            brand_name: Nom de la marque
            menu_items: Liste des éléments du menu (dictionnaires avec 'url' et 'text')
            home_url: URL de la page d'accueil
            navbar_class: Classes CSS supplémentaires
            
        Returns:
            str: Code HTML de la barre de navigation
        """
        items_html = ""
        for item in menu_items:
            url = item.get("url", "#")
            text = item.get("text", "Lien")
            items_html += f'        <li><a href="{url}">{text}</a></li>\n'
            
        return self.templates["navbar"].format(
            navbar_class=navbar_class,
            home_url=home_url,
            brand_name=brand_name,
            menu_items=items_html
        )
    
    def generate_card(self, title: str, content: str, footer: str = "", 
                    card_class: str = "") -> str:
        """
        Génère une carte (composant card)
        
        Args:
            title: Titre de la carte
            content: Contenu de la carte
            footer: Pied de la carte (optionnel)
            card_class: Classes CSS supplémentaires
            
        Returns:
            str: Code HTML de la carte
        """
        card_header = f'<div class="card-header">\n        <h3>{title}</h3>\n    </div>'
        
        card_footer = ""
        if footer:
            card_footer = f'<div class="card-footer">\n        {footer}\n    </div>'
            
        return self.templates["card"].format(
            card_class=card_class,
            card_header=card_header,
            card_content=content,
            card_footer=card_footer
        )
    
    def generate_grid(self, items: List[str], grid_class: str = "") -> str:
        """
        Génère une grille d'éléments
        
        Args:
            items: Liste des éléments HTML à inclure dans la grille
            grid_class: Classes CSS supplémentaires
            
        Returns:
            str: Code HTML de la grille
        """
        grid_items = "\n    ".join([f'<div class="grid-item">{item}</div>' for item in items])
        
        return self.templates["grid"].format(
            grid_class=grid_class,
            grid_items=grid_items
        )
        
    def generate_sort(self) -> str:
        """
        Génère une page HTML avec démonstration d'algorithmes de tri
        
        Returns:
            str: Page HTML avec des algorithmes de tri et visualisation
        """
        return '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visualisation des algorithmes de tri</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }
        h1, h2 {
            color: #333;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .array-container {
            display: flex;
            justify-content: center;
            align-items: flex-end;
            height: 200px;
            margin: 20px 0;
        }
        .array-bar {
            width: 30px;
            margin: 0 2px;
            background-color: #3498db;
            transition: height 0.2s ease;
        }
        .controls {
            margin: 20px 0;
            text-align: center;
        }
        button {
            padding: 10px 15px;
            margin: 0 5px;
            background-color: #2ecc71;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #27ae60;
        }
        .code {
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            font-family: monospace;
            overflow-x: auto;
            margin: 15px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Visualisation des algorithmes de tri</h1>
        
        <div class="controls">
            <button id="randomize">Mélanger</button>
            <button id="bubbleSort">Tri à bulles</button>
            <button id="quickSort">Tri rapide</button>
            <button id="mergeSort">Tri fusion</button>
        </div>
        
        <div class="array-container" id="arrayContainer">
            <!-- Les barres seront générées par JavaScript -->
        </div>
        
        <h2>Code des algorithmes</h2>
        
        <h3>Tri à bulles</h3>
        <div class="code">
            <pre>
function bubbleSort(arr) {
    const n = arr.length;
    
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                [arr[j], arr[j + 1]] = [arr[j + 1], arr[j]];
            }
        }
    }
    
    return arr;
}
            </pre>
        </div>
        
        <h3>Tri rapide (QuickSort)</h3>
        <div class="code">
            <pre>
function quickSort(arr) {
    if (arr.length <= 1) {
        return arr;
    }
    
    const pivot = arr[Math.floor(arr.length / 2)];
    const left = arr.filter(x => x < pivot);
    const middle = arr.filter(x => x === pivot);
    const right = arr.filter(x => x > pivot);
    
    return [...quickSort(left), ...middle, ...quickSort(right)];
}
            </pre>
        </div>
    </div>
    
    <script>
        // Tableau à trier
        let array = [];
        
        // Fonction pour générer un tableau aléatoire
        function generateRandomArray(size = 10) {
            array = [];
            for (let i = 0; i < size; i++) {
                array.push(Math.floor(Math.random() * 100) + 10);
            }
            renderArray(array);
        }
        
        // Fonction pour afficher le tableau
        function renderArray(arr) {
            const container = document.getElementById('arrayContainer');
            container.innerHTML = '';
            
            arr.forEach(value => {
                const bar = document.createElement('div');
                bar.className = 'array-bar';
                bar.style.height = `${value * 2}px`;
                bar.textContent = value;
                container.appendChild(bar);
            });
        }
        
        // Tri à bulles avec visualisation
        async function visualBubbleSort() {
            const arr = [...array];
            const n = arr.length;
            
            for (let i = 0; i < n; i++) {
                for (let j = 0; j < n - i - 1; j++) {
                    if (arr[j] > arr[j + 1]) {
                        [arr[j], arr[j + 1]] = [arr[j + 1], arr[j]];
                        renderArray(arr);
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                }
            }
        }
        
        // Initialiser l'application
        document.addEventListener('DOMContentLoaded', () => {
            generateRandomArray();
            
            document.getElementById('randomize').addEventListener('click', () => {
                generateRandomArray();
            });
            
            document.getElementById('bubbleSort').addEventListener('click', () => {
                visualBubbleSort();
            });
        });
    </script>
</body>
</html>'''
