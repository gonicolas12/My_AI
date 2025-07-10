"""
Générateur de code JavaScript
"""

from typing import Dict, List, Any, Optional
from .base_generator import BaseCodeGenerator

class JavaScriptCodeGenerator(BaseCodeGenerator):
    """Générateur de code JavaScript"""
    
    def __init__(self):
        super().__init__("javascript")
    
    def _load_templates(self) -> Dict[str, str]:
        return {
            "function": '''function {name}({params}) {
    // {description}
    {body}
    return {return_value};
}''',
            
            "arrow_function": '''const {name} = ({params}) => {
    // {description}
    {body}
    return {return_value};
};''',

            "class": '''class {name} {
    /**
     * {description}
     */
    constructor({constructor_params}) {
        {constructor_body}
    }
    
    {methods}
}''',

            "module": '''/**
 * {module_name}
 * {description}
 */

{imports}

{code_body}

{exports}
''',
            
            "html_script": '''<!DOCTYPE html>
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
    {html_body}
    
    <script>
        {js_code}
    </script>
</body>
</html>''',

            "react_component": '''import React, { useState, useEffect } from 'react';

function {component_name}({props}) {
    {state_hooks}
    
    useEffect(() => {
        {effect_body}
    }, [{effect_dependencies}]);
    
    {functions}
    
    return (
        {jsx}
    );
}

export default {component_name};
''',
        }
    
    def _load_patterns(self) -> Dict[str, str]:
        return {
            "factorial": '''function factorial(n) {
    // Calculate the factorial of a number
    if (n < 0) {
        throw new Error("Factorial is not defined for negative numbers");
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

// Recursive version
function factorialRecursive(n) {
    // Recursive version of factorial
    if (n < 0) {
        throw new Error("Factorial is not defined for negative numbers");
    } else if (n === 0 || n === 1) {
        return 1;
    } else {
        return n * factorialRecursive(n - 1);
    }
}

// Tests
const testValues = [0, 1, 5, 10];
testValues.forEach(n => {
    console.log(`factorial(${n}) = ${factorial(n)}`);
});''',
            
            "fibonacci": '''function fibonacci(n) {
    // Generate Fibonacci sequence up to n terms
    if (n <= 0) {
        return [];
    } else if (n === 1) {
        return [0];
    } else if (n === 2) {
        return [0, 1];
    }
    
    const sequence = [0, 1];
    for (let i = 2; i < n; i++) {
        sequence.push(sequence[i-1] + sequence[i-2]);
    }
    
    return sequence;
}

// Usage example
console.log("Fibonacci sequence (10 terms):");
console.log(fibonacci(10));''',
            
            "sort": '''function bubbleSort(array) {
    // Bubble sort algorithm
    const arr = [...array]; // Create a copy to avoid modifying the original
    const n = arr.length;
    
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                // Swap elements
                [arr[j], arr[j + 1]] = [arr[j + 1], arr[j]];
            }
        }
    }
    
    return arr;
}

function quickSort(array) {
    // Quick sort algorithm
    if (array.length <= 1) {
        return array;
    }
    
    const pivot = array[Math.floor(array.length / 2)];
    const left = array.filter(x => x < pivot);
    const middle = array.filter(x => x === pivot);
    const right = array.filter(x => x > pivot);
    
    return [...quickSort(left), ...middle, ...quickSort(right)];
}

// Tests
const testArray = [64, 34, 25, 12, 22, 11, 90];
console.log(`Original array: ${testArray}`);
console.log(`Bubble sort: ${bubbleSort(testArray)}`);
console.log(`Quick sort: ${quickSort(testArray)}`);''',

            "hello_world": '''function greet() {
    // Simple Hello World program
    console.log("Hello, world!");
}

greet();''',

            "dom_manipulation": '''document.addEventListener('DOMContentLoaded', function() {
    // DOM Manipulation example
    const app = document.getElementById('app');
    
    // Create elements
    const header = document.createElement('h1');
    header.textContent = 'JavaScript DOM Manipulation';
    
    const paragraph = document.createElement('p');
    paragraph.textContent = 'This paragraph was created dynamically with JavaScript.';
    
    const button = document.createElement('button');
    button.textContent = 'Click me!';
    button.addEventListener('click', function() {
        alert('Button clicked!');
    });
    
    // Append elements to the app container
    app.appendChild(header);
    app.appendChild(paragraph);
    app.appendChild(button);
    
    console.log('DOM elements created successfully!');
});''',

            "fetch_api": '''async function fetchData(url) {
    try {
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching data:', error);
        throw error;
    }
}

async function displayUserData() {
    const userDataContainer = document.getElementById('userData');
    userDataContainer.innerHTML = 'Loading...';
    
    try {
        // Example API endpoint (JSONPlaceholder)
        const users = await fetchData('https://jsonplaceholder.typicode.com/users');
        
        let html = '<h2>User List</h2><ul>';
        users.forEach(user => {
            html += `<li>
                <strong>${user.name}</strong> (${user.username})<br>
                Email: ${user.email}<br>
                Company: ${user.company.name}
            </li>`;
        });
        html += '</ul>';
        
        userDataContainer.innerHTML = html;
    } catch (error) {
        userDataContainer.innerHTML = `<p class="error">Failed to load data: ${error.message}</p>`;
    }
}

// Execute when the page loads
document.addEventListener('DOMContentLoaded', displayUserData);''',

            "simple_react": '''import React, { useState } from 'react';
import ReactDOM from 'react-dom';

function Counter() {
    const [count, setCount] = useState(0);
    
    const increment = () => {
        setCount(prevCount => prevCount + 1);
    };
    
    const decrement = () => {
        setCount(prevCount => prevCount - 1);
    };
    
    return (
        <div className="counter">
            <h2>Counter: {count}</h2>
            <button onClick={decrement}>-</button>
            <button onClick={increment}>+</button>
        </div>
    );
}

function App() {
    return (
        <div className="app">
            <h1>React Counter App</h1>
            <Counter />
        </div>
    );
}

ReactDOM.render(<App />, document.getElementById('root'));'''
        }
    
    def generate_function(self, name: str, params: List[str] = None, description: str = "", 
                         body: str = None, return_value: str = "null", arrow: bool = False) -> str:
        """
        Génère une fonction JavaScript
        
        Args:
            name: Nom de la fonction
            params: Liste des paramètres
            description: Description de la fonction
            body: Corps de la fonction
            return_value: Valeur de retour
            arrow: Si True, génère une fonction fléchée, sinon une fonction classique
            
        Returns:
            str: Code de la fonction générée
        """
        if params is None:
            params = []
            
        if body is None:
            body = "    // TODO: Implement your logic here"
            
        template = self.templates["arrow_function"] if arrow else self.templates["function"]
        
        return template.format(
            name=name,
            params=", ".join(params),
            description=description or f"Function {name}",
            body=body,
            return_value=return_value
        )
    
    def generate_class(self, name: str, description: str = "", 
                      constructor_params: List[str] = None, constructor_body: str = None,
                      methods: List[Dict[str, Any]] = None) -> str:
        """
        Génère une classe JavaScript
        
        Args:
            name: Nom de la classe
            description: Description de la classe
            constructor_params: Paramètres du constructeur
            constructor_body: Corps du constructeur
            methods: Liste des méthodes à inclure
            
        Returns:
            str: Code de la classe générée
        """
        if constructor_params is None:
            constructor_params = []
            
        if constructor_body is None:
            constructor_body = "        // Initialize class properties here"
            
        if methods is None:
            methods = []
            
        # Générer les méthodes
        methods_code = ""
        for method in methods:
            method_name = method.get("name", "method")
            method_params = method.get("params", [])
            method_body = method.get("body", "        // Method implementation")
            
            methods_code += f"\n    {method_name}({', '.join(method_params)}) {{\n"
            methods_code += f"{method_body}\n"
            methods_code += "    }\n"
            
        return self.templates["class"].format(
            name=name,
            description=description or f"Class {name}",
            constructor_params=", ".join(constructor_params),
            constructor_body=constructor_body,
            methods=methods_code
        )
    
    def generate_hello_world(self) -> str:
        """
        Génère un programme Hello World en JavaScript
        
        Returns:
            str: Code du programme Hello World
        """
        return self.patterns["hello_world"]
    
    def generate_factorial(self) -> str:
        """
        Génère une fonction de calcul de factorielle en JavaScript
        
        Returns:
            str: Code de la fonction factorielle
        """
        return self.patterns["factorial"]
    
    def generate_fibonacci(self) -> str:
        """
        Génère une fonction de génération de la séquence de Fibonacci en JavaScript
        
        Returns:
            str: Code de la fonction Fibonacci
        """
        return self.patterns["fibonacci"]
        
    def generate_dom_manipulation(self) -> str:
        """
        Génère un exemple de manipulation du DOM en JavaScript
        
        Returns:
            str: Code de manipulation du DOM
        """
        return self.patterns["dom_manipulation"]
        
    def generate_fetch_example(self) -> str:
        """
        Génère un exemple d'utilisation de Fetch API
        
        Returns:
            str: Code d'exemple Fetch API
        """
        return self.patterns["fetch_api"]
        
    def generate_react_component(self, name: str, props: List[str] = None, 
                               state_vars: List[Dict[str, Any]] = None,
                               jsx: str = None) -> str:
        """
        Génère un composant React
        
        Args:
            name: Nom du composant
            props: Liste des props
            state_vars: Variables d'état (useState hooks)
            jsx: Code JSX du rendu
            
        Returns:
            str: Code du composant React
        """
        if props is None:
            props = []
            
        if state_vars is None:
            state_vars = []
            
        if jsx is None:
            jsx = "<div>Composant {name}</div>"
            
        # Générer les hooks d'état
        state_hooks_code = ""
        for state_var in state_vars:
            var_name = state_var.get("name", "state")
            setter_name = state_var.get("setter", f"set{var_name.capitalize()}")
            initial_value = state_var.get("initial", "null")
            
            state_hooks_code += f"    const [{var_name}, {setter_name}] = useState({initial_value});\n"
            
        # Générer les fonctions
        functions_code = ""
        
        # Générer le corps de useEffect
        effect_body = "// Effect code here"
        effect_dependencies = ""  # Dépendances vides = s'exécute une seule fois
        
        return self.templates["react_component"].format(
            component_name=name,
            props=", ".join(props) if props else "",
            state_hooks=state_hooks_code,
            effect_body=effect_body,
            effect_dependencies=effect_dependencies,
            functions=functions_code,
            jsx=jsx
        )
        
    def generate_module(self, name: str, description: str, imports: List[str] = None,
                       functions: List[Dict[str, Any]] = None, classes: List[Dict[str, Any]] = None,
                       export_default: str = None, named_exports: List[str] = None) -> str:
        """
        Génère un module JavaScript complet
        
        Args:
            name: Nom du module
            description: Description du module
            imports: Liste des imports
            functions: Liste des fonctions
            classes: Liste des classes
            export_default: Élément à exporter par défaut
            named_exports: Éléments à exporter nommément
            
        Returns:
            str: Code complet du module
        """
        if imports is None:
            imports = []
            
        if functions is None:
            functions = []
            
        if classes is None:
            classes = []
            
        if named_exports is None:
            named_exports = []
            
        # Générer les imports
        imports_code = "\n".join(imports) + ("\n\n" if imports else "")
        
        # Générer le corps du code
        code_body = ""
        
        # Ajouter les classes
        for cls in classes:
            cls_name = cls.get("name", "MyClass")
            cls_desc = cls.get("description", f"Class {cls_name}")
            cls_params = cls.get("constructor_params", [])
            cls_body = cls.get("constructor_body", "        // Initialize class properties")
            cls_methods = cls.get("methods", [])
            
            code_body += self.generate_class(cls_name, cls_desc, cls_params, cls_body, cls_methods) + "\n\n"
            
        # Ajouter les fonctions
        for func in functions:
            func_name = func.get("name", "myFunction")
            func_params = func.get("params", [])
            func_desc = func.get("description", f"Function {func_name}")
            func_body = func.get("body", "    // Function implementation")
            func_return = func.get("return_value", "null")
            func_arrow = func.get("arrow", False)
            
            code_body += self.generate_function(func_name, func_params, func_desc, 
                                              func_body, func_return, func_arrow) + "\n\n"
            
        # Générer les exports
        exports_code = ""
        
        if export_default:
            exports_code += f"export default {export_default};\n"
            
        if named_exports:
            exports_code += f"export {{ {', '.join(named_exports)} }};\n"
            
        # Assembler le module
        return self.templates["module"].format(
            module_name=name,
            description=description,
            imports=imports_code,
            code_body=code_body,
            exports=exports_code
        )
        
    def generate_sort(self) -> str:
        """
        Génère un algorithme de tri en JavaScript
        
        Returns:
            str: Code d'un algorithme de tri
        """
        return '''// Implémentation du tri à bulles en JavaScript
function bubbleSort(arr) {
    /**
     * Tri à bulles - compare les éléments adjacents et les échange si nécessaire
     * @param {Array} arr - Tableau à trier
     * @return {Array} Tableau trié
     */
    const n = arr.length;
    
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                // Échanger les éléments
                [arr[j], arr[j + 1]] = [arr[j + 1], arr[j]];
            }
        }
    }
    
    return arr;
}

// Implémentation du tri rapide (QuickSort) en JavaScript
function quickSort(arr) {
    /**
     * Tri rapide - utilise la stratégie "diviser pour régner"
     * @param {Array} arr - Tableau à trier
     * @return {Array} Tableau trié
     */
    if (arr.length <= 1) {
        return arr;
    }
    
    const pivot = arr[Math.floor(arr.length / 2)];
    const left = arr.filter(x => x < pivot);
    const middle = arr.filter(x => x === pivot);
    const right = arr.filter(x => x > pivot);
    
    return [...quickSort(left), ...middle, ...quickSort(right)];
}

// Test des algorithmes de tri
(function() {
    const testArray = [64, 34, 25, 12, 22, 11, 90];
    
    console.log("Tableau non trié:", testArray);
    
    // Test du tri à bulles
    const bubbleSorted = [...testArray];
    console.log("Tri à bulles:", bubbleSort(bubbleSorted));
    
    // Test du tri rapide
    const quickSorted = [...testArray];
    console.log("Tri rapide:", quickSort(quickSorted));
})();
'''