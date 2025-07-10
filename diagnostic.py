#!/usr/bin/env python3
"""
Script de diagnostic pour My AI Personal Assistant
Aide à identifier et résoudre les problèmes d'installation
"""
import sys
import os
import subprocess
import importlib
from pathlib import Path

def print_header(title):
    """Affiche un en-tête formaté."""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def check_python():
    """Vérifie la version de Python."""
    print_header("VÉRIFICATION PYTHON")
    
    version = sys.version_info
    print(f"Version Python: {version.major}.{version.minor}.{version.micro}")
    
    if version < (3, 8):
        print("❌ Python 3.8+ requis")
        print("💡 Téléchargez Python depuis: https://python.org")
        return False
    elif version < (3, 10):
        print("⚠️ Python 3.10+ recommandé")
        print("✅ Version acceptable")
        return True
    else:
        print("✅ Version excellente")
        return True

def check_pip():
    """Vérifie pip."""
    print_header("VÉRIFICATION PIP")
    
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ pip disponible: {result.stdout.strip()}")
            return True
        else:
            print("❌ pip non disponible")
            print("💡 Réinstallez Python avec pip inclus")
            return False
    except Exception as e:
        print(f"❌ Erreur pip: {e}")
        return False

def check_virtual_env():
    """Vérifie les environnements virtuels."""
    print_header("VÉRIFICATION ENVIRONNEMENTS VIRTUELS")
    
    venv_paths = ['venv', 'ai_env', '.venv']
    found_venv = False
    
    for venv_path in venv_paths:
        if os.path.exists(venv_path):
            print(f"✅ Environnement virtuel trouvé: {venv_path}")
            
            # Vérifier l'activation
            if os.name == 'nt':  # Windows
                activate_script = os.path.join(venv_path, 'Scripts', 'activate.bat')
            else:  # Unix/Linux
                activate_script = os.path.join(venv_path, 'bin', 'activate')
            
            if os.path.exists(activate_script):
                print(f"✅ Script d'activation trouvé: {activate_script}")
                found_venv = True
            else:
                print(f"⚠️ Script d'activation manquant: {activate_script}")
    
    if not found_venv:
        print("⚠️ Aucun environnement virtuel trouvé")
        print("💡 Créez un environnement virtuel:")
        print("   python -m venv ai_env")
        if os.name == 'nt':
            print("   ai_env\\Scripts\\activate")
        else:
            print("   source ai_env/bin/activate")
        print("   pip install -r requirements.txt")
    
    return found_venv

def check_dependencies():
    """Vérifie les dépendances."""
    print_header("VÉRIFICATION DÉPENDANCES")
    
    critical_deps = [
        ('click', 'Interface CLI'),
        ('yaml', 'Configuration'),
        ('rich', 'Interface colorée'),
        ('transformers', 'Modèles AI'),
        ('torch', 'Deep Learning')
    ]
    
    optional_deps = [
        ('fitz', 'Traitement PDF'),
        ('docx', 'Traitement DOCX'),
        ('tkinter', 'Interface graphique'),
        ('pytest', 'Tests')
    ]
    
    missing_critical = []
    missing_optional = []
    
    print("📦 Dépendances critiques:")
    for dep, desc in critical_deps:
        try:
            if dep == 'yaml':
                import yaml
            elif dep == 'fitz':
                import fitz
            elif dep == 'docx':
                import docx
            else:
                importlib.import_module(dep)
            print(f"  ✅ {dep} ({desc})")
        except ImportError:
            print(f"  ❌ {dep} ({desc})")
            missing_critical.append(dep)
    
    print("\n📦 Dépendances optionnelles:")
    for dep, desc in optional_deps:
        try:
            if dep == 'fitz':
                import fitz
            elif dep == 'docx':
                import docx
            elif dep == 'tkinter':
                import tkinter
            else:
                importlib.import_module(dep)
            print(f"  ✅ {dep} ({desc})")
        except ImportError:
            print(f"  ⚠️ {dep} ({desc})")
            missing_optional.append(dep)
    
    return missing_critical, missing_optional

def check_project_structure():
    """Vérifie la structure du projet."""
    print_header("VÉRIFICATION STRUCTURE PROJET")
    
    required_files = [
        'launcher.py',
        'main.py',
        'requirements.txt',
        'config.yaml',
        'README.md'
    ]
    
    required_dirs = [
        'core',
        'models',
        'processors',
        'generators',
        'interfaces',
        'utils'
    ]
    
    missing_files = []
    missing_dirs = []
    
    print("📁 Fichiers requis:")
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file}")
            missing_files.append(file)
    
    print("\n📁 Répertoires requis:")
    for dir in required_dirs:
        if os.path.exists(dir) and os.path.isdir(dir):
            print(f"  ✅ {dir}/")
        else:
            print(f"  ❌ {dir}/")
            missing_dirs.append(dir)
    
    return missing_files, missing_dirs

def provide_solutions(missing_critical, missing_optional):
    """Fournit des solutions pour les problèmes détectés."""
    print_header("SOLUTIONS RECOMMANDÉES")
    
    if missing_critical:
        print("🔧 Pour installer les dépendances critiques:")
        print("   pip install --upgrade pip")
        print("   pip install -r requirements.txt")
        print("")
        print("   Ou individuellement:")
        for dep in missing_critical:
            if dep == 'yaml':
                print(f"   pip install pyyaml")
            elif dep == 'fitz':
                print(f"   pip install PyMuPDF")
            elif dep == 'docx':
                print(f"   pip install python-docx")
            else:
                print(f"   pip install {dep}")
    
    if missing_optional:
        print("\n🔧 Pour installer les dépendances optionnelles:")
        for dep in missing_optional:
            if dep == 'fitz':
                print(f"   pip install PyMuPDF  # pour traitement PDF")
            elif dep == 'docx':
                print(f"   pip install python-docx  # pour traitement DOCX")
            elif dep == 'tkinter':
                if os.name == 'nt':
                    print(f"   # tkinter inclus avec Python sur Windows")
                else:
                    print(f"   sudo apt-get install python3-tk  # sur Ubuntu/Debian")
            else:
                print(f"   pip install {dep}")
    
    print("\n🔧 Si vous voyez 'Defaulting to user installation...':")
    print("   C'est normal ! Les packages sont installés dans votre répertoire utilisateur.")
    print("   Cela ne pose aucun problème de fonctionnement.")
    print("")
    print("   Pour éviter ce message, utilisez un environnement virtuel:")
    print("   python -m venv ai_env")
    if os.name == 'nt':
        print("   ai_env\\Scripts\\activate")
    else:
        print("   source ai_env/bin/activate")
    print("   pip install -r requirements.txt")

def main():
    """Fonction principale de diagnostic."""
    print("🤖 My AI Personal Assistant - Diagnostic")
    print("Ce script va vérifier votre installation et proposer des solutions.")
    
    # Vérifications
    python_ok = check_python()
    pip_ok = check_pip()
    venv_found = check_virtual_env()
    missing_critical, missing_optional = check_dependencies()
    missing_files, missing_dirs = check_project_structure()
    
    # Résumé
    print_header("RÉSUMÉ")
    
    if python_ok and pip_ok and not missing_critical and not missing_files and not missing_dirs:
        print("🎉 Excellent ! Votre installation semble complète.")
        print("💡 Vous pouvez maintenant lancer:")
        print("   python launcher.py gui")
        print("   python launcher.py demo")
    else:
        print("⚠️ Quelques problèmes détectés, mais corrigeables.")
        
        if missing_critical:
            print(f"❌ {len(missing_critical)} dépendances critiques manquantes")
        if missing_optional:
            print(f"⚠️ {len(missing_optional)} dépendances optionnelles manquantes")
        if missing_files:
            print(f"❌ {len(missing_files)} fichiers manquants")
        if missing_dirs:
            print(f"❌ {len(missing_dirs)} répertoires manquants")
    
    # Solutions
    if missing_critical or missing_optional:
        provide_solutions(missing_critical, missing_optional)
    
    print("\n💡 Commandes de test utiles:")
    print("   python launcher.py status    # Vérifier le statut")
    print("   python launcher.py demo      # Tester les fonctionnalités")
    print("   python health_check.py       # Diagnostic complet")
    print("   python launcher.py test      # Exécuter les tests")

if __name__ == "__main__":
    main()
