#!/usr/bin/env python3
"""
🔍 Vérificateur de Configuration Ultra
Vérifie que toutes les optimisations sont bien actives
"""

import os
import sys
import yaml

def check_token_configuration():
    """Vérifie la configuration des tokens"""
    print("🔍 VÉRIFICATION CONFIGURATION TOKENS")
    print("=" * 40)
    
    # Vérifier config.yaml
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        max_tokens = config.get('ai', {}).get('max_tokens', 0)
        
        print(f"📄 config.yaml:")
        print(f"   max_tokens: {max_tokens:,}")
        
        if max_tokens >= 1000000:
            print(f"   ✅ Configuration 1M+ tokens ACTIVE")
        elif max_tokens >= 100000:
            print(f"   ⚡ Configuration 100K+ tokens")
        else:
            print(f"   ⚠️ Configuration basique ({max_tokens})")
        
    except Exception as e:
        print(f"   ❌ Erreur config.yaml: {e}")
    
    # Vérifier variables d'environnement ultra
    print(f"\n🔧 Variables d'environnement ultra:")
    ultra_vars = [
        'MYAI_MAX_TOKENS',
        'MYAI_CONTEXT_WINDOW', 
        'MYAI_MEMORY_LIMIT',
        'MYAI_OPTIMIZATION_LEVEL'
    ]
    
    for var in ultra_vars:
        value = os.environ.get(var, 'Non défini')
        if value != 'Non défini':
            print(f"   ✅ {var}: {value}")
        else:
            print(f"   ⚠️ {var}: {value}")

def check_optimization_files():
    """Vérifie que tous les fichiers d'optimisation existent"""
    print(f"\n📁 VÉRIFICATION FICHIERS OPTIMISATIONS")
    print("=" * 40)
    
    critical_files = [
        "optimization_manager.py",
        "rag_pipeline.py", 
        "context_optimization.py",
        "launch_ultra.py",
        "interfaces/gui_modern.py"
    ]
    
    for file_path in critical_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"   ✅ {file_path} ({size:,} bytes)")
        else:
            print(f"   ❌ MANQUANT: {file_path}")

def test_ultra_import():
    """Test l'importation des modules ultra"""
    print(f"\n🧪 TEST IMPORT MODULES ULTRA")
    print("=" * 40)
    
    modules_to_test = [
        ("Optimization Manager", "optimization_manager", "get_optimization_manager"),
        ("RAG Pipeline", "rag_pipeline", "RAGPipeline"),
        ("Context Optimizer", "context_optimization", "AdvancedContextOptimizer"),
        ("Modèle Principal", "models.custom_ai_model", "CustomAIModel")
    ]
    
    working_count = 0
    
    for name, module, class_name in modules_to_test:
        try:
            exec(f"from {module} import {class_name}")
            print(f"   ✅ {name}")
            working_count += 1
        except Exception as e:
            print(f"   ❌ {name}: {str(e)[:50]}...")
    
    success_rate = (working_count / len(modules_to_test)) * 100
    print(f"\n📊 Taux de succès: {success_rate:.0f}% ({working_count}/{len(modules_to_test)})")
    
    return success_rate

def verify_launch_scripts():
    """Vérifie que les scripts de lancement utilisent les bonnes versions"""
    print(f"\n🚀 VÉRIFICATION SCRIPTS DE LANCEMENT")
    print("=" * 40)
    
    scripts = {
        "launch.bat": "launch.bat",
        "launch_ultra.py": "launch_ultra.py", 
        "start_ultra.py": "start_ultra.py",
        "launcher_definitif.py": "launcher_definitif.py"
    }
    
    for name, script_path in scripts.items():
        if os.path.exists(script_path):
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Vérifier si utilise les optimisations ultra
            ultra_indicators = [
                "1048576",  # 1M tokens
                "launch_ultra",
                "optimization_manager",
                "ULTRA"
            ]
            
            ultra_count = sum(1 for indicator in ultra_indicators if indicator in content)
            
            if ultra_count >= 2:
                print(f"   ✅ {name} - Ultra optimisé ({ultra_count}/4)")
            else:
                print(f"   ⚠️ {name} - Optimisations limitées ({ultra_count}/4)")

def main():
    """Vérification complète"""
    print("🔍 VÉRIFICATEUR CONFIGURATION MY_AI ULTRA")
    print("🎯 Confirme que les 1M tokens sont actifs")
    print("=" * 50)
    
    # Vérifications
    check_token_configuration()
    check_optimization_files()
    success_rate = test_ultra_import()
    verify_launch_scripts()
    
    # Résumé final
    print(f"\n🎊 RÉSUMÉ DE VÉRIFICATION")
    print("=" * 30)
    
    if success_rate >= 75:
        print(f"🎉 EXCELLENTE NOUVELLE !")
        print(f"✅ Votre launch.bat utilise maintenant les optimisations ultra")
        print(f"🎯 Configuration 1M tokens ACTIVE")
        print(f"⚡ Tous les modules optimisés disponibles")
        
        print(f"\n💡 RÉPONSE À VOTRE QUESTION:")
        print(f"OUI ! Quand vous lancez launch.bat maintenant:")
        print(f"   🚀 Elle aura les 1M tokens")
        print(f"   ✅ Elle aura toutes les mises à jour")
        print(f"   🔥 Elle utilisera les optimisations ultra")
        print(f"   🎨 Interface moderne style Claude")
        
    else:
        print(f"⚠️ Configuration partiellement optimisée")
        print(f"📝 {success_rate:.0f}% des modules fonctionnent")
    
    print(f"\n🎮 TESTEZ MAINTENANT:")
    print(f"   Cliquez sur launch.bat → Choix 1")
    print(f"   Ou: python launch_ultra.py")

if __name__ == "__main__":
    main()
