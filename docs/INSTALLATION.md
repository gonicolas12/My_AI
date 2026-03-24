# 📖 Guide d'Installation - My Personal AI v7.0.0

## 🎯 Vue d'Ensemble

My Personal AI v7.0.0 est une **IA 100% locale** avec un système de contexte de **1 Million de tokens RÉEL** fonctionnant entièrement sur votre machine sans dépendances cloud obligatoires. Cette installation vous guide pour mettre en place votre IA privée et sécurisée.

## ⚡ Installation Rapide (5 minutes)

### 1. Prérequis Système

**Configuration minimale:**
- **Python 3.8+** (Python 3.10+ recommandé pour performances optimales)
- **4 GB RAM** (8 GB recommandé, 16 GB idéal pour 1M tokens)
- **500 MB d'espace disque** (1 GB recommandé pour cache et documents)
- **Windows/Linux/macOS** supportés
- **Connexion internet** (installation uniquement, optionnelle ensuite pour recherche web)

**Configuration recommandée:**
- Python 3.10 ou supérieur
- 16 GB RAM
- 2 GB d'espace disque
- Processeur multi-core (pour opérations parallèles)
- GPU (optionnel, pour accélération PyTorch)
- **Ollama** (optionnel mais recommandé pour des réponses de qualité LLM)

### 2. Installation Complète

```bash
# 1. Cloner ou télécharger le projet
cd My_AI

# 2. Créer un environnement virtuel (recommandé)
python -m venv venv

# Activer l'environnement virtuel:
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Installer toutes les dépendances
pip install -r requirements.txt

# 4. Vérifier l'installation
python -c "import customtkinter; print('Installation réussie!')"
```

### 3. Installation Ollama (Optionnel mais Recommandé)

Ollama permet d'avoir des réponses générées par un vrai LLM local.

**Étape 1 : Installer Ollama**
```bash
# Télécharger depuis https://ollama.com/download
# Installer selon votre OS (Windows, macOS, Linux)
```

**Étape 2 : Télécharger un modèle**
```bash
# Modèle recommandé pour 16 GB RAM
ollama pull qwen3.5:9b

# OU modèle plus léger pour 8 GB RAM
ollama pull qwen3.5:4b
```

**Étape 2b : Installer un modèle Vision (Optionnel pour l'analyse d'images)**
```bash
# Modèle vision recommandé (3 GB) — meilleur rapport qualité/vitesse
ollama pull minicpm-v

# OU autres modèles vision disponibles
ollama pull minicpm-v            # Bonne qualité (4.7 GB)
ollama pull llama3.2-vision      # Haute qualité mais lourd (7.9 GB)
ollama pull llava:13b            # Plus performant mais plus lourd
ollama pull bakllava             # Alternative
ollama pull moondream            # Plus léger
```

> **Note:** Le support d'images nécessite au moins un modèle vision installé. L'IA détectera automatiquement le premier modèle disponible parmi : llava, llama3.2-vision, bakllava, moondream.

**Étape 3 : Créer le modèle personnalisé**
```bash
# Dans le répertoire My_AI
.\create_custom_model.bat
```

**Vérifier l'installation :**
```bash
ollama list  # Voir les modèles installés
ollama run qwen3.5:4b "Bonjour"  # Tester
```

> **Note:** Si Ollama n'est pas installé, l'IA utilisera automatiquement le mode fallback (CustomAIModel avec patterns).

### 4. Lancement Rapide

```bash
# Lancement GUI (recommandé)
python launch_unified.py

# OU via main.py
python main.py --mode gui

# Lancement CLI
python main.py
```

## 📦 Dépendances Principales

### Core Dependencies (Requis)
```
click>=8.0.0              # CLI interface
aiohttp>=3.8.0            # Async HTTP
requests>=2.31.0          # HTTP requests
beautifulsoup4>=4.12.0    # Web scraping
pyyaml>=6.0               # Configuration
python-dotenv>=1.0.0      # Environment variables
```

### Document Processing (Requis)
```
PyMuPDF>=1.23.0          # PDF processing (primaire)
PyPDF2>=3.0.0            # PDF processing (fallback)
python-docx>=0.8.11      # DOCX processing
openpyxl>=3.1.0          # Excel files
python-pptx>=0.6.21      # PowerPoint files
reportlab>=4.0.0         # PDF generation
```

### GUI Interface (Requis pour GUI)
```
customtkinter>=5.2.0     # Modern UI framework
tkinterdnd2>=0.3.0       # Drag-and-drop support
pillow>=10.0.0           # Image processing
pygments                 # Code syntax highlighting
```

### Machine Learning (Requis)
```
torch>=2.0.0             # PyTorch
scikit-learn>=1.3.0      # ML algorithms
sentence-transformers>=2.2.0  # Embeddings
rapidfuzz                # Fuzzy matching
tiktoken                 # Token counting (compatible Llama 3 / cl100k_base)
```

### Monitoring GPU (Optionnel)

Le monitoring GPU dans l'onglet Agents détecte automatiquement votre carte graphique. Installez **uniquement le package correspondant à votre GPU** :

```bash
# NVIDIA (nécessite les drivers NVIDIA)
pip install pynvml GPUtil

# AMD (nécessite ROCm ou drivers AMDGPU + Microsoft C++ Build Tools pour compiler)
pip install pyamdgpuinfo

# Windows — tout GPU (infos basiques : nom et VRAM totale, pas d'usage en temps réel)
pip install wmi
```

**Ordre de détection automatique :** NVIDIA (pynvml) → NVIDIA (GPUtil) → AMD (pyamdgpuinfo) → AMD (rocm-smi CLI) → Windows WMI

> **Sans ces packages**, l'application fonctionne normalement. Les métriques GPU et VRAM affichent "N/A" dans l'onglet Statistiques.

### Modules v7.0.0 (Optionnel — dégradation gracieuse si absents)
```
fastapi>=0.100.0         # API REST locale
uvicorn>=0.23.0          # Serveur ASGI pour FastAPI
langdetect>=1.0.9        # Détection automatique de langue
diskcache>=5.6.0         # Cache web persistant
reportlab>=4.0.0         # Export PDF des conversations
```

### Advanced Features (Optionnel)
```
faiss-cpu>=1.7.4         # Semantic search
peft>=0.4.0              # LoRA fine-tuning
bitsandbytes>=0.40.0     # Quantization
sqlalchemy>=2.0.0        # Database ORM
cryptography>=41.0.0     # Encryption
```

### Development Tools (Optionnel)
```
pytest>=7.0.0            # Testing
black>=23.0.0            # Code formatting
flake8>=5.5.0            # Linting
isort>=5.12.0            # Import sorting
```

## 🏗️ Structure Projet Post-Installation

Après le premier lancement, ces répertoires seront créés automatiquement:

```
My_AI/
├── core/                  # Modules core système
├── models/                # Modèles IA
├── processors/            # Processeurs documents
├── generators/            # Générateurs contenu
├── interfaces/            # Interfaces utilisateur
├── tools/                 # Outils spécialisés
├── utils/                 # Utilitaires
├── data/                  # Données et enrichissements
│   ├── enrichissement/    # FAQ et connaissances
│   ├── context_storage/   # Storage contexte 1M tokens (créé auto)
│   ├── outputs/           # Documents générés (créé auto)
│   ├── temp/              # Fichiers temporaires (créé auto)
│   ├── backups/           # Sauvegardes (créé auto)
│   └── logs/              # Logs application (créé auto)
├── docs/                  # Documentation
├── examples/              # Exemples utilisation
├── tests/                 # Tests unitaires
├── config.yaml            # Configuration (créé auto si absent)
├── .env                   # Variables environnement (optionnel)
├── requirements.txt       # Dépendances Python
├── launch_unified.py      # Launcher principal
└── main.py               # Entry point CLI
```

## ⚙️ Configuration

### Fichier config.yaml (Optionnel)

Un fichier `config.yaml` sera créé automatiquement au premier lancement avec les valeurs par défaut. Vous pouvez le personnaliser:

```yaml
# config.yaml - Configuration My Personal AI

# Configuration IA
ai:
  name: "My Personal AI"
  version: "7.0.0"
  max_tokens: 4096          # Max tokens standard
  ultra_max_tokens: 1048576 # Max tokens ultra mode (1M)
  temperature: 0.7
  conversation_history_limit: 10

# Types fichiers supportés
file_processing:
  supported_types:
    - ".pdf"
    - ".docx"
    - ".txt"
    - ".py"
    - ".js"
    - ".md"
    - ".json"
    - ".csv"
  max_file_size_mb: 100

# Configuration UI
ui:
  cli:
    prompt: "💬 Vous> "
    ai_prompt: "🤖 IA> "
  gui:
    theme: "dark"
    font_family: "Segoe UI"
    font_size: 11

# Répertoires
directories:
  output: "data/outputs"
  temp: "data/temp"
  logs: "data/logs"
  backups: "data/backups"
  context_storage: "data/context_storage"

# ── Modules v7.0.0 ──────────────────────────

# API REST locale
api:
  enabled: false               # Activer le serveur REST
  host: "127.0.0.1"
  port: 8000
  cors_origins: ["http://localhost:*"]

# Workspaces / Sessions
workspaces:
  directory: "data/workspaces"
  auto_save: true
  auto_save_interval: 300      # secondes
  max_workspaces: 50

# Base de connaissances structurée
knowledge_base:
  directory: "data/knowledge_base"
  auto_extract: true
  max_facts: 10000

# Historique des commandes
command_history:
  enabled: true
  max_entries: 5000
  db_path: "data/command_history.db"

# Export conversations
export:
  output_directory: "outputs/exports"
  default_format: "markdown"   # markdown | html | pdf
  include_metadata: true

# Détection de langue
language:
  auto_detect: true
  default: "fr"
  supported: ["fr", "en", "es", "de", "it", "pt", "nl", "ru", "zh", "ja", "ko", "ar"]

# Cache web
web_cache:
  enabled: true
  ttl_seconds: 3600            # 1 heure
  max_entries: 1000
  directory: "data/web_cache"
```

### Variables d'Environnement (.env)

Pour des configurations sensibles ou spécifiques, créez un fichier `.env`:

```bash
# .env - Variables environnement

# GitHub token pour code generation (optionnel)
GITHUB_TOKEN=your_github_personal_access_token

# Debug mode
DEBUG=false

# Chemins personnalisés (optionnel)
DATA_DIR=./data
OUTPUT_DIR=./data/outputs
```

**Note:** Le token GitHub est optionnel. Il améliore les capacités de recherche de code mais n'est pas requis pour le fonctionnement de base.

### Configuration Ollama (Modelfile)

Le fichier `Modelfile` à la racine du projet configure le modèle personnalisé :

```dockerfile
# Modelfile pour My_AI
FROM qwen3.5:4b

# Paramètres
PARAMETER temperature 0.7
PARAMETER num_ctx 8192    # Fenêtre de contexte

# System prompt personnalisé
SYSTEM """
Tu es My_AI, un assistant IA personnel expert et bienveillant.
Réponds toujours en français par défaut.
"""
```

**Paramètres `num_ctx` recommandés selon RAM :**
| RAM | num_ctx | Usage |
|-----|---------|-------|
| 8 GB | 4096 | Conversations courtes |
| 16 GB | 8192 | Conversations moyennes |
| 32 GB | 16384 | Gros documents |

## 🚀 Options de Lancement

### 1. GUI Modern (Recommandé)

Interface graphique moderne avec thème sombre style Claude:

```bash
# Lancement direct
python launch_unified.py

# OU via main.py
python main.py --mode gui
```

**Features:**
- Interface chat moderne
- Code syntax highlighting
- Drag-and-drop fichiers
- Timestamps
- Commandes help/status intégrées

### 2. CLI Enhanced

Interface ligne de commande améliorée:

```bash
# Mode interactif
python main.py

# OU explicitement
python main.py --mode cli
```

**Commandes disponibles:**
- Requêtes normales → envoyées à l'IA
- `aide` ou `help` → afficher commandes
- `quitter` ou `exit` → fermer
- `statut` ou `status` → état système
- `historique` ou `history` → voir conversations
- `fichier <path>` → traiter fichier
- `generer <type> <desc>` → générer contenu

### 3. Direct Queries

Requêtes directes sans mode interactif:

```bash
# Chat direct
python main.py chat "Bonjour, comment ça va?"

# Analyser fichier
python main.py file analyze path/to/document.pdf

# Générer code
python main.py generate code "fonction pour trier une liste"

# Afficher statut
python main.py status
```

## 🔧 Configuration Avancée

### Installation GPU (CUDA) - Optionnel

Pour accélérer les opérations PyTorch avec GPU NVIDIA:

```bash
# Désinstaller torch CPU
pip uninstall torch torchvision torchaudio

# Installer torch GPU (CUDA 11.8)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Vérifier installation GPU
python -c "import torch; print(f'CUDA disponible: {torch.cuda.is_available()}')"
```

**Note:** CUDA doit être installé sur votre système. Visitez https://developer.nvidia.com/cuda-downloads

### Optimisation Mémoire

#### Pour machines 4-8 GB RAM:
```yaml
# Dans config.yaml
ai:
  max_tokens: 2048
  conversation_history_limit: 5
  ultra_max_tokens: 524288  # 512K au lieu de 1M
```

#### Pour machines 16+ GB RAM:
```yaml
# Dans config.yaml
ai:
  max_tokens: 8192
  conversation_history_limit: 20
  ultra_max_tokens: 1048576  # Full 1M tokens
```

### Configuration Enrichissement FAQ

Les fichiers d'enrichissement dans `data/enrichissement/` sont chargés par priorité:

1. `enrichissement_culture.jsonl` (Priorité 1)
2. `enrichissement_informatique.jsonl` (Priorité 2)
3. `enrichissement_général.jsonl` (Priorité 3)
4. `enrichissement_exemples.jsonl` (Priorité 4)

Format JSONL:
```json
{"input": "Question ici", "target": "Réponse ici"}
{"input": "Autre question", "target": "Autre réponse"}
```

Pour ajouter vos propres connaissances, éditez ces fichiers ou créez-en de nouveaux.

## 🧪 Vérification Installation

### Test Basique

```bash
# Test imports
python -c "from core.ai_engine import AIEngine; print('Core OK')"
python -c "from models.custom_ai_model import CustomAIModel; print('Models OK')"
python -c "from interfaces.gui_modern import ModernAIGUI; print('GUI OK')"

# Test complet
python tests/test_imports.py
```

### Test Fonctionnel

```bash
# Test requête simple
python main.py chat "Bonjour"

# Test traitement fichier (créer un test.txt d'abord)
echo "Contenu test" > test.txt
python main.py file analyze test.txt

# Test génération code
python main.py generate code "fonction addition"

# Test statut système
python main.py status
```

### Test Contexte 1M Tokens

```bash
# Test capacité contexte
python tests/test_real_1m_tokens.py

# Benchmark performance
python tests/benchmark_1m_tokens.py

# Demo interactive
python tests/demo_1m_tokens.py
```

## 🐛 Résolution Problèmes

### Problème: ModuleNotFoundError

**Erreur:** `ModuleNotFoundError: No module named 'customtkinter'`

**Solutions:**
```bash
# Vérifier environnement virtuel activé
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Réinstaller dépendances
pip install -r requirements.txt

# Installer module spécifique
pip install customtkinter
```

### Problème: Tkinter non disponible

**Erreur:** `No module named 'tkinter'` ou `_tkinter`

**Solutions:**
- **Windows:** Réinstaller Python avec option "tcl/tk" cochée
- **Ubuntu/Debian:** `sudo apt-get install python3-tk`
- **macOS:** `brew install python-tk`
- **Fallback:** Utiliser CLI mode → `python main.py --mode cli`

### Problème: PyMuPDF installation failed

**Erreur:** Problème compilation PyMuPDF/fitz

**Solutions:**
```bash
# Essayer version spécifique
pip install PyMuPDF==1.23.8

# OU utiliser wheel pre-compilé
pip install --upgrade pip
pip install --upgrade PyMuPDF

# En dernier recours, PyPDF2 sera utilisé en fallback
pip install PyPDF2
```

### Problème: Mémoire insuffisante

**Erreur:** `MemoryError` ou application lente

**Solutions:**
1. Réduire `max_tokens` dans config.yaml
2. Limiter `conversation_history_limit`
3. Fermer applications gourmandes en RAM
4. Utiliser mode CLI au lieu de GUI (moins de RAM)
5. Redémarrer l'application régulièrement

### Problème: Erreurs CUDA/GPU

**Erreur:** CUDA errors ou GPU non détecté

**Solutions:**
```bash
# Vérifier version CUDA
nvcc --version

# Réinstaller torch pour CPU seulement
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio

# L'IA fonctionnera sur CPU (plus lent mais stable)
```

### Problème: Permission denied (Linux/macOS)

**Erreur:** `Permission denied` lors de l'écriture

**Solutions:**
```bash
# Donner permissions sur répertoires
chmod -R u+w data/
chmod +x launch_unified.py
chmod +x main.py

# OU utiliser sudo (non recommandé)
sudo python main.py
```

### Problème: Port déjà utilisé

**Erreur:** Si intégration web future - port occupé

**Solutions:**
```bash
# Trouver processus sur port
# Windows:
netstat -ano | findstr :8000
# Linux/macOS:
lsof -i :8000

# Tuer processus ou changer port dans config
```

## 📊 Test Installation Complète

Script de test automatique:

```bash
# Créer test_installation.py
cat > test_installation.py << 'EOF'
#!/usr/bin/env python3
"""Test complet installation My Personal AI"""

def test_imports():
    print("🧪 Test imports modules...")
    try:
        from core.ai_engine import AIEngine
        from models.custom_ai_model import CustomAIModel
        from processors.pdf_processor import PDFProcessor
        from interfaces.cli import EnhancedCLI
        print("✅ Imports OK")
        return True
    except Exception as e:
        print(f"❌ Erreur imports: {e}")
        return False

def test_gpu():
    print("\n🧪 Test GPU disponibilité...")
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            print(f"✅ GPU disponible: {torch.cuda.get_device_name(0)}")
        else:
            print("⚠️  GPU non disponible (CPU sera utilisé)")
        return True
    except:
        print("⚠️  PyTorch non installé")
        return True

def test_directories():
    print("\n🧪 Test création répertoires...")
    from pathlib import Path
    dirs = ["data/outputs", "data/temp", "data/logs", "data/backups"]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    print("✅ Répertoires OK")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("  TEST INSTALLATION MY PERSONAL AI v7.0.0")
    print("=" * 50)

    tests = [test_imports(), test_gpu(), test_directories()]

    print("\n" + "=" * 50)
    if all(tests):
        print("✅ Installation complète et fonctionnelle!")
    else:
        print("⚠️  Problèmes détectés, voir détails ci-dessus")
    print("=" * 50)
EOF

# Exécuter test
python test_installation.py
```

## 🔄 Mise à Jour

### Mise à jour dépendances

```bash
# Mettre à jour toutes les dépendances
pip install -r requirements.txt --upgrade

# Mettre à jour package spécifique
pip install --upgrade customtkinter
pip install --upgrade transformers
```

### Mise à jour projet

```bash
# Si Git repository
git pull origin main

# Réinstaller dépendances si requirements.txt changé
pip install -r requirements.txt --upgrade
```

## 🎯 Optimisation Performances

### Pour Performances Maximales

1. **Utiliser GPU si disponible:**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

2. **Augmenter limites config:**
```yaml
ai:
  max_tokens: 8192
  conversation_history_limit: 20
```

3. **Activer cache:**
```yaml
performance:
  enable_cache: true
  cache_size_mb: 1000
```

### Pour Machines Limitées

1. **Réduire consommation mémoire:**
```yaml
ai:
  max_tokens: 2048
  conversation_history_limit: 5
```

2. **Utiliser CLI au lieu de GUI:**
```bash
python main.py --mode cli
```

3. **Désactiver features avancées:**
```yaml
features:
  enable_internet_search: false
  enable_advanced_code_gen: false
```

## 🌐 Configuration Réseau (Optionnel)

Pour activer la recherche internet (DuckDuckGo):

```yaml
# Dans config.yaml
internet_search:
  enabled: true
  max_results: 8
  cache_duration: 3600  # 1 heure
  timeout: 10  # secondes
```

**Note:** La recherche internet est optionnelle. L'IA fonctionne 100% localement sans connexion.

## 📱 Interface Web (Future/Expérimental)

Pour l'interface web Streamlit (en développement):

```bash
# Installer Streamlit
pip install streamlit>=1.25.0

# Lancer interface web
streamlit run interfaces/web_interface.py
```

**Note:** Interface web en cours de développement, CLI et GUI sont recommandées.

## 🎉 Installation Terminée!

Une fois l'installation complète, vous pouvez:

1. **Lancer l'IA:**
   ```bash
   python launch_unified.py  # GUI
   python main.py            # CLI
   ```

2. **Tester les capacités:**
   - Poser des questions générales
   - Traiter des documents PDF/DOCX
   - Générer du code
   - Rechercher sur internet
   - Utiliser la mémoire 1M tokens

3. **Explorer les exemples:**
   ```bash
   cd examples
   python basic_usage.py
   python file_processing.py
   ```

4. **Consulter la documentation:**
   - `docs/USAGE.md` - Guide utilisation
   - `docs/ARCHITECTURE.md` - Détails architecture
   - `docs/OPTIMIZATION.md` - Optimisations
   - `docs/FAQ.md` - Questions fréquentes

## 📞 Support

Si vous rencontrez des problèmes:

1. **Vérifier les logs:** `data/logs/`
2. **Mode verbose:** `python main.py --verbose`
3. **Tests diagnostiques:** `python tests/test_imports.py`
4. **Consulter FAQ:** `docs/FAQ.md`
5. **Exemples:** Voir `examples/` pour patterns d'utilisation

---

**Bon codage avec My Personal AI! 🚀**

*Version: 7.0.0 | Architecture: 100% locale | Capacité: 1M tokens*
