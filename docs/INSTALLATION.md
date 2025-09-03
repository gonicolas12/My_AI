# 📖 Guide d'Installation - My Personal AI ULTRA v5.0.0 (1M Tokens RÉEL)

## 🎯 Vue d'Ensemble Ultra

My Personal AI Ultra v5.0.0 introduit le **système révolutionnaire de 1 Million de tokens RÉEL** fonctionnant **entièrement localement** sans dépendance à des services externes. Cette installation vous guide pour mettre en place votre IA ultra-performante, privée et sécurisée avec capacités étendues.

## 🚀 Installation Express Ultra (7 minutes)

### 1. Prérequis Pour le Système Ultra

- **Python 3.9+** (REQUIS: Python 3.10+ pour performances optimales 1M tokens)
- **~500 MB d'espace disque** (pour la base SQLite et cache intelligent)
- **8 GB RAM minimum** (16 GB recommandé pour 1M tokens)
- **Windows/Linux/macOS** supportés
- **Aucune connexion internet requise** après installation
- **Processeur moderne** (pour compression et recherche sémantique)

### 2. Installation Automatique Ultra

```bash
# 1. Aller dans le répertoire du projet
cd My_AI

# 2. Installer TOUTES les dépendances Ultra (ML inclus)
pip install -r requirements.txt

# Dépendances Ultra spécifiques :
pip install scikit-learn customtkinter pdfplumber python-docx requests beautifulsoup4 pygments

# 3. Lancement Ultra immédiat
.\launch_ultra.bat   # 🚀 NOUVEAU : Lancement mode Ultra
# OU
python launch_ultra.py
```

### 3. Vérification du Système Ultra

```bash
# Test du système 1M tokens
python launch_ultra.py

# Vérification du statut Ultra
python main_ultra.py status

# Test de traitement de gros documents (NOUVEAU)
python main_ultra.py process gros_document.pdf --ultra

# Statistiques contexte 1M tokens
python -c "from models.ultra_custom_ai import UltraCustomAI; print(UltraCustomAI().get_context_stats())"
```

## 🧠 Architecture Ultra 1M Tokens 100% Locale

### Nouveaux Composants Ultra

L'IA Ultra utilise exclusivement des composants locaux révolutionnaires :

- **Moteur IA Custom** : Logique de raisonnement développée spécialement
- **Reconnaissance d'intentions** : Patterns linguistiques locaux
- **Mémoire conversationnelle** : Stockage local des contextes
- **Base de connaissances** : Informations encodées localement
- **Processeurs de documents** : Traitement PDF/DOCX sans cloud

### Aucun Service Externe

❌ **Pas de dépendances externes** :
- Pas d'API OpenAI
- Pas de Claude/Anthropic
- Pas de Google Bard
- Pas de services cloud
- Pas d'envoi de données à l'extérieur

✅ **Tout reste sur votre machine** :
- Conversations privées
- Documents confidentiels
- Code source sécurisé
- Historique local uniquement

## 🔧 Configuration Avancée

### Personnalisation de l'IA

Éditez le fichier `config.yaml` pour adapter l'IA à vos besoins :

```yaml
# Configuration personnalisée
ai:
  name: "Mon IA Personnelle"
  max_tokens: 4096
  temperature: 0.7
  conversation_history_limit: 20
  
  # Types de fichiers supportés
  supported_file_types:
    - ".pdf"
    - ".docx"
    - ".txt"
    - ".py"
    - ".md"
```

### Optimisation des Performances

#### Pour machines avec peu de RAM (4 GB) :
```yaml
ai:
  max_tokens: 2048
  conversation_history_limit: 5
  enable_learning: false
```

#### Pour machines puissantes (16 GB+) :
```yaml
ai:
  max_tokens: 8192
  conversation_history_limit: 50
  enable_learning: true
  advanced_reasoning: true
```

```bash
# Modèle recommandé (léger et performant)
ollama pull llama3.2

# Modèles alternatifs
ollama pull mistral
ollama pull codellama
ollama pull llama3.2:13b  # Plus gros, plus performant
```

4. **Vérifier le fonctionnement**:

```bash
ollama list
ollama run llama3.2
```

#### Configuration dans l'IA:

L'IA détectera automatiquement Ollama. Pour personnaliser:

```yaml
# Dans config.yaml
llm:
  default_backend: "ollama"
  ollama:
    base_url: "http://localhost:11434"
    default_model: "llama3.2"
```

### Option 2: Hugging Face Transformers

Pour utiliser directement les modèles Transformers:

```bash
# Installation des dépendances GPU (optionnel)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### Configuration:

```yaml
# Dans config.yaml
llm:
  default_backend: "transformers"
  transformers:
    default_model: "microsoft/DialoGPT-medium"
    device: "auto"  # Détection automatique CPU/GPU
```

## 📁 Structure des Répertoires

Après le premier lancement, ces répertoires seront créés:

```
My_AI/
├── outputs/          # Fichiers générés
├── logs/            # Fichiers de log
├── temp/            # Fichiers temporaires
├── backups/         # Sauvegardes
└── models_cache/    # Cache des modèles (si Transformers)
```

## ⚙️ Configuration Avancée

### Personnalisation du config.yaml

Le fichier `config.yaml` permet de personnaliser tous les aspects:

```yaml
# Exemple de personnalisation
ai:
  temperature: 0.8        # Créativité (0.0-1.0)
  max_tokens: 8192       # Longueur des réponses
  
file_processing:
  max_file_size_mb: 100  # Taille max des fichiers

ui:
  cli:
    prompt: "🤖 MonIA> " # Personnaliser le prompt
```

### Variables d'Environnement

Créez un fichier `.env` pour les configurations sensibles:

```bash
# .env
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=your_key_here  # Si vous voulez utiliser OpenAI en fallback
DEBUG=false
```

## 🐛 Résolution des Problèmes

### Problème: "Aucun modèle LLM disponible"

**Solutions:**
1. Vérifiez qu'Ollama est démarré: `ollama serve`
2. Vérifiez qu'un modèle est installé: `ollama list`
3. Testez la connexion: `curl http://localhost:11434/api/tags`

### Problème: "Import 'torch' could not be resolved"

**Solutions:**
1. Installez PyTorch: `pip install torch`
2. Pour GPU: `pip install torch --index-url https://download.pytorch.org/whl/cu118`

### Problème: "Permission denied" sur Linux/macOS

**Solutions:**
1. Rendez le script exécutable: `chmod +x main.py`
2. Utilisez Python explicitement: `python main.py`

### Problème: Erreurs de mémoire

**Solutions:**
1. Réduisez `max_tokens` dans la config
2. Utilisez un modèle plus petit (llama3.2 au lieu de llama3.2:13b)
3. Fermez les autres applications gourmandes

## 📊 Vérification de l'Installation

### Test Complet:

```bash
# Test du statut
python main.py status

# Test d'une requête simple
python main.py chat "Dis bonjour"

# Test de lecture de fichier
echo "Hello World" > test.txt
python main.py file read test.txt

# Test de génération de code
python main.py generate code "fonction qui additionne deux nombres"
```

### Mode Debug:

```bash
# Lancer avec plus de logs
python main.py --verbose

# Lancer en mode interactif avec debug
python main.py --verbose --mode cli
```

## 🔄 Mise à Jour

Pour mettre à jour les dépendances:

```bash
pip install -r requirements.txt --upgrade
```

Pour mettre à jour les modèles Ollama:

```bash
ollama pull llama3.2  # Re-télécharge la dernière version
```

## 🎯 Optimisation des Performances

### Pour des Performances Maximales:

1. **Utilisez un GPU** (si disponible):
   ```bash
   pip install torch --index-url https://download.pytorch.org/whl/cu118
   ```

2. **Utilisez des modèles optimisés**:
   - `llama3.2` : Léger, rapide
   - `mistral` : Bon compromis
   - `llama3.2:13b` : Plus performant mais plus lourd

3. **Configurez le cache**:
   ```yaml
   performance:
     enable_cache: true
     cache_size_mb: 500
   ```

### Pour des Performances Minimales (PC faible):

1. **Utilisez des modèles légers**
2. **Limitez les tokens**:
   ```yaml
   ai:
     max_tokens: 1024
     temperature: 0.5
   ```

3. **Désactivez le cache** si peu de RAM:
   ```yaml
   performance:
     enable_cache: false
   ```

## 📞 Support

Si vous rencontrez des problèmes:

1. Vérifiez les logs dans `logs/`
2. Lancez avec `--verbose` pour plus d'informations
3. Consultez les exemples dans `examples/`
4. Vérifiez la configuration dans `config.yaml`

## 🎉 Vous êtes prêt !

Une fois l'installation terminée, vous pouvez:

- Lancer l'IA: `python main.py`
- Taper `aide` pour voir toutes les commandes
- Commencer à poser des questions à votre IA personnelle !

Bon codage! 🚀
