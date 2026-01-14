# 🎯 Génération de Fichiers avec Ollama

## 📖 Vue d'ensemble

Le système de génération de fichiers permet de créer automatiquement des fichiers de code complets en utilisant **Ollama** pour la génération intelligente de contenu.

## ✨ Nouvelles Fonctionnalités

### 🔥 Génération de Fichiers Intelligente

Vous pouvez maintenant demander à My_AI de générer des fichiers complets avec du code fonctionnel :

```
génère moi un fichier main.py qui me permet de jouer au morpion
```

```
crée moi un fichier calculatrice.py avec les 4 opérations de base
```

```
génère un fichier server.js pour un serveur Express simple
```

### 🎯 Comment ça marche

1. **Détection automatique** : Le système détecte les demandes de génération de fichiers
2. **Ollama génère le code** : Utilise votre modèle Ollama local pour créer du code de qualité
3. **Sauvegarde automatique** : Le fichier est automatiquement créé dans le dossier `outputs/`
4. **Prévisualisation** : Vous recevez un aperçu du code généré dans l'interface

## 🛠️ Architecture Technique

### Modules Modifiés

#### 1. `generators/code_generator.py`
- ✅ Intégration avec `LocalLLM` (Ollama)
- ✅ Méthode `generate_file()` pour créer des fichiers complets
- ✅ Détection intelligente du langage et du nom de fichier
- ✅ Nettoyage automatique du code généré
- ✅ Sauvegarde dans `outputs/`

#### 2. `core/ai_engine.py`
- ✅ Nouveau routage pour "génère moi un fichier..."
- ✅ Détection prioritaire dans `_analyze_query_type()`
- ✅ Handler `_handle_code_generation()` amélioré
- ✅ Support de `OllamaCodeGenerator` + `WebCodeGenerator`

#### 3. `generators/document_generator.py`
- ✅ Intégration avec `LocalLLM` pour génération de contenu
- ⏳ Prêt pour génération de documents avec Ollama

## 🚀 Utilisation

### Via l'Interface GUI

1. Lancez l'application : `python launch_unified.py`
2. Tapez votre demande dans le chat :
   ```
   génère moi un fichier morpion.py pour jouer au morpion
   ```
3. Le fichier est créé dans `outputs/morpion.py`

### Via le CLI

```bash
python main.py chat "génère moi un fichier main.py qui me permet de jouer au morpion"
```

### Test Direct

```bash
python test_file_generation.py
```

## 📋 Formats Supportés

### Langages Détectés Automatiquement

- **Python** (.py) - par défaut
- **JavaScript** (.js)
- **HTML** (.html)
- **CSS** (.css)
- **Java** (.java)
- **C++** (.cpp)
- **C** (.c)

### Exemples de Requêtes

```
# Python (défaut)
génère moi un fichier main.py qui me permet de jouer au morpion

# JavaScript
génère un fichier server.js pour un serveur Express

# HTML
crée une page web index.html avec un formulaire de contact

# CSS
génère un fichier styles.css avec un design moderne
```

## 🔧 Configuration

### Prérequis

1. **Ollama installé et en cours d'exécution** :
   ```bash
   ollama serve
   ```

2. **Modèle Ollama disponible** (my_ai, llama3, etc.)

3. **Dépendances Python** :
   ```bash
   pip install -r requirements.txt
   ```

### Vérification

Pour vérifier que Ollama fonctionne :

```bash
curl http://localhost:11434
```

## 📊 Flux de Traitement

```
Requête Utilisateur
    ↓
Analyse de la requête (_analyze_query_type)
    ↓
Détection "génère moi un fichier"
    ↓
Extraction du langage et nom de fichier
    ↓
Appel à Ollama (LocalLLM.generate)
    ↓
Nettoyage du code généré
    ↓
Sauvegarde dans outputs/
    ↓
Retour du résultat à l'utilisateur
```

## 💡 Exemples Complets

### Exemple 1 : Jeu de Morpion

**Requête** :
```
génère moi un fichier main.py qui me permet de jouer au morpion
```

**Résultat** :
- ✅ Fichier créé : `outputs/main.py`
- 🎮 Code du jeu de morpion complet
- 💻 Prêt à être exécuté

### Exemple 2 : Calculatrice

**Requête** :
```
crée un fichier calculatrice.py avec les 4 opérations de base
```

**Résultat** :
- ✅ Fichier créé : `outputs/calculatrice.py`
- ➕➖✖️➗ Fonctions d'addition, soustraction, multiplication, division
- 🖥️ Interface utilisateur incluse

### Exemple 3 : Serveur Web

**Requête** :
```
génère un fichier server.js pour un serveur Express simple avec une route /api/hello
```

**Résultat** :
- ✅ Fichier créé : `outputs/server.js`
- 🌐 Serveur Express fonctionnel
- 🛣️ Route API configurée

## 🐛 Dépannage

### Ollama ne répond pas

```bash
# Vérifier le statut
ollama list

# Redémarrer Ollama
ollama serve
```

### Le fichier n'est pas créé

1. Vérifier les logs : Le système affiche des messages de débogage
2. Vérifier les permissions du dossier `outputs/`
3. S'assurer qu'Ollama est accessible

### Code incomplet ou incorrect

- Essayez un modèle plus puissant (llama3, mixtral, etc.)
- Reformulez votre demande avec plus de détails
- Augmentez le timeout dans `LocalLLM` si le modèle est lent

## 🎨 Personnalisation

### Changer le dossier de sortie

Dans `code_generator.py` :
```python
filepath = os.path.join("outputs", filename)  # Modifier "outputs"
```

### Changer le prompt Ollama

Dans `code_generator.py`, méthode `_generate_with_ollama()` :
```python
system_prompt = f"""Tu es un expert en programmation {language}.
Génère du code propre, bien commenté et fonctionnel.
# Ajoutez vos instructions ici
"""
```

## 📚 Documentation Additionnelle

- [Architecture du projet](docs/ARCHITECTURE.md)
- [Guide d'utilisation](docs/USAGE.md)
- [Installation](docs/INSTALLATION.md)

## ✅ Checklist de Vérification

- [x] Ollama installé et configuré
- [x] `LocalLLM` intégré dans `CodeGenerator`
- [x] Détection "génère moi un fichier" dans `ai_engine.py`
- [x] Méthode `generate_file()` fonctionnelle
- [x] Sauvegarde automatique dans `outputs/`
- [x] Support multi-langages (Python, JS, HTML, CSS, etc.)
- [x] Nettoyage du code généré (suppression markdown)
- [x] Gestion des erreurs et fallbacks
- [x] Tests unitaires créés

## 🚀 Prochaines Étapes

- [ ] Support de génération de documents (PDF, DOCX) avec Ollama
- [ ] Génération de tests unitaires automatiques
- [ ] Support de templates de projets complets
- [ ] Intégration de linters automatiques
- [ ] Génération de documentation automatique

---

**Version** : 1.0.0  
**Date** : 14 Janvier 2026  
**Auteur** : [Nicolas Gouy](https://github.com/gonicolas12)
