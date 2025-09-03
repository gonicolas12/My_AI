# 📚 Guide d'Utilisation Ultra - My Personal AI v5.0.0 (1M Tokens RÉEL)

## 🚀 Démarrage Ultra

### Lancement de l'IA Ultra 1M Tokens

```bash
# 🚀 Interface graphique ULTRA (recommandée)
python launch_ultra.py
# OU via launcher interactif
python launcher.py   # Choisir option 1 pour Ultra

# Interface graphique moderne avec 1M tokens
python -m interfaces.gui_modern  --ultra

# Mode CLI Ultra pour utilisateurs experts
python main_ultra.py --cli

# Commande directe Ultra avec contexte étendu
python main_ultra.py chat "Analyse ce document complexe en profondeur" --context-1m

# Vérifier le statut du système Ultra
python main_ultra.py status --ultra-stats
```

## � Capacités Ultra 1M Tokens

### 🧠 Contexte Révolutionnaire

Avec **1,048,576 tokens réels**, vous pouvez désormais :

- **Analyser des documents entiers** : PDFs de 50+ pages, code complet
- **Conversations ultra-longues** : Contexte maintenu sur des heures
- **Projets complexes** : Analyse multi-fichiers avec mémoire totale
- **Recherches approfondies** : Internet + contexte massif simultané

### 🔍 Reconnaissance d'Intentions Ultra

L'IA Ultra reconnaît automatiquement et traite avec le contexte étendu :

#### 👋 Salutations avec Stats Ultra
```
🤖 Vous : slt
🤖 IA Ultra : Salut ! 🚀 Système 1M tokens opérationnel !
         📊 Contexte actuel: 0 / 1,048,576 tokens
         💾 Documents traités: 0
         🧩 Chunks actifs: 0
         Comment puis-je t'aider avec ce système ultra-étendu ?

🤖 Vous : bonjour
🤖 IA Ultra : Bonjour ! 🎯 Mode Ultra 1M tokens activé !
         Capacités : analyse complète documents, contexte massif,
         mémoire persistante. Que souhaitez-vous explorer ?
```

#### 💻 Questions Techniques Ultra avec Contexte Massif
```
🤖 Vous : Analyse complète de ce projet Python de 50 fichiers
🤖 IA Ultra : [Analyse ultra-détaillée avec :
              - Contexte de TOUS les fichiers simultanément
              - Relations entre modules complètes
              - Suggestions d'optimisation globales
              - Patterns de design détectés
              - Documentation générée automatiquement]

🤖 Vous : Continue cette conversation de 2000 messages
🤖 IA Ultra : [Accès immédiat à TOUT l'historique de conversation
              grâce au contexte 1M tokens, réponses cohérentes
              avec références précises aux échanges précédents]
```

#### 📄 Questions sur Documents
```
🤖 Vous : résume ce document
🤖 IA : [Résumé du document PDF/DOCX précédemment chargé]

🤖 Vous : que dit le PDF sur les performances ?
🤖 IA : [Extraction des informations pertinentes du document]

🤖 Vous : quels sont les points clés du rapport ?
🤖 IA : [Analyse et points principaux du document]
```

### Interface Graphique

L'interface principale offre :
- **Zone de conversation** : Historique complet des échanges
- **Zone de saisie** : Entrée de texte avec support multilignes
- **Bouton "Envoyer"** : Validation des messages
- **Bouton "Clear Chat"** : Remise à zéro complète (conversation + mémoire)
- **Glisser-déposer** : Chargement direct de fichiers PDF/DOCX

### Exemples de Conversations Avancées

```bash

# Session complète avec mémoire contextuelle
🤖 Vous : bonjour
🤖 IA : Bonjour ! Comment puis-je vous aider aujourd'hui ?

🤖 Vous : [glisse un fichier rapport.pdf]
🤖 IA : J'ai bien reçu le fichier "rapport.pdf". Il a été traité et son contenu est maintenant en mémoire.

🤖 Vous : résume ce document
🤖 IA : Voici un résumé du rapport.pdf : [résumé détaillé basé sur le contenu réel]

🤖 Vous : comment implémenter les recommandations en Python ?
🤖 IA : Basé sur les recommandations du rapport, voici comment les implémenter en Python : [code adapté au contenu du document]

🤖 Vous : [bouton Clear Chat]
🤖 IA : Conversation et mémoire effacées. Bonjour ! Comment puis-je vous aider ?
```

## 📁 Traitement de Fichiers Avancé

### Chargement de Documents

L'IA supporte plusieurs méthodes de chargement :

#### Glisser-Déposer (Interface Graphique):
- Faites glisser directement vos fichiers PDF/DOCX dans l'interface
- Traitement automatique et mise en mémoire
- Confirmation de chargement avec nom du fichier

#### Commande Directe:
```bash
python main.py process document.pdf
python main.py process rapport.docx
```

### Types de Documents Supportés

#### Documents PDF:
- **Extraction complète** : Texte, structure, métadonnées
- **Mémoire persistante** : Contenu disponible pour toute la session
- **Analyse contextuelle** : Réponses basées sur le contenu réel

#### Documents DOCX:
- **Structure préservée** : Titres, paragraphes, listes
- **Formatage intelligent** : Conservation de la hiérarchie
- **Extraction complète** : Texte intégral avec contexte

### Mémoire Conversationnelle

#### Stockage Intelligent:
- **Documents** : Contenu complet avec référence au nom de fichier
- **Code** : Snippets et analyses de code avec contexte
- **Historique** : Conversations précédentes pour continuité

#### Utilisation de la Mémoire:
```bash
🤖 MyAI> fichier lire C:\Documents\rapport.pdf
🤖 MyAI> fichier analyser C:\Documents\manuel.pdf
```

#### Documents Word (DOCX):
```bash
🤖 MyAI> fichier lire document.docx
🤖 MyAI> Résume le contenu de contrat.docx
```

#### Code Source:
```bash
🤖 MyAI> fichier analyser script.py
🤖 MyAI> fichier lire index.html
🤖 MyAI> Explique ce que fait ce code dans app.js
```

#### Fichiers Texte:
```bash
🤖 MyAI> fichier lire notes.txt
🤖 MyAI> Analyse ce fichier de log: error.log
```

### Commandes de Fichiers

| Commande | Description | Exemple |
|----------|-------------|---------|
| `fichier lire <chemin>` | Lit et résume un fichier | `fichier lire rapport.pdf` |
| `fichier analyser <chemin>` | Analyse détaillée | `fichier analyser code.py` |
| `fichier info <chemin>` | Informations du fichier | `fichier info document.docx` |

## 🛠️ Génération de Code

### Création de Code

L'IA peut générer du code dans plusieurs langages:

#### Python:
```bash
🤖 MyAI> generer code fonction qui calcule la factorielle
🤖 MyAI> generer code classe pour gérer une liste de tâches
🤖 MyAI> generer code script qui lit un fichier CSV
```

#### Web (HTML/CSS/JavaScript):
```bash
🤖 MyAI> generer code page web avec formulaire de contact
🤖 MyAI> generer code fonction JavaScript pour valider un email
🤖 MyAI> generer code CSS pour un menu responsive
```

#### Autres langages:
```bash
🤖 MyAI> generer code fonction SQL pour sélectionner des données
🤖 MyAI> generer code script bash pour sauvegarder des fichiers
```

### Types de Code Générés

- **Fonctions** avec documentation complète
- **Classes** avec méthodes et attributs
- **Scripts complets** avec imports et main()
- **Pages web** avec HTML, CSS et JavaScript
- **Composants** réutilisables

### Exemple de Génération

```bash
🤖 MyAI> generer code classe Calculator en Python

# L'IA génère:
class Calculator:
    """
    Calculatrice simple pour opérations arithmétiques
    """
    
    def __init__(self):
        """
        Initialise Calculator
        """
        pass
    
    def add(self, a, b):
        """
        Addition de deux nombres
        
        Args:
            a: Premier nombre
            b: Deuxième nombre
        
        Returns:
            Somme des deux nombres
        """
        return a + b
    # ... autres méthodes
```

## 📄 Génération de Documents

### Création de Documents

L'IA peut créer différents types de documents:

#### Rapports et Documents:
```bash
🤖 MyAI> generer document rapport sur l'analyse des ventes
🤖 MyAI> generer document guide d'utilisation pour une API
🤖 MyAI> generer document présentation du projet
```

#### Formats Supportés:
- **PDF** : Documents professionnels
- **Word (DOCX)** : Documents éditables
- **Texte** : Documentation simple
- **Markdown** : Documentation technique

### Personnalisation des Documents

```bash
🤖 MyAI> generer document manuel utilisateur au format PDF
🤖 MyAI> generer rapport technique avec graphiques
🤖 MyAI> Crée un document de spécifications en Word
```

## 🎯 Commandes Avancées

### Commandes Système

| Commande | Description |
|----------|-------------|
| `statut` | Affiche l'état de l'IA |
| `historique` | Historique des conversations |
| `aide` | Affiche l'aide complète |
| `quitter` | Ferme l'application |

### Commandes par Ligne de Commande

```bash
# Requête directe
python main.py chat "Votre question"

# Traitement de fichier
python main.py file read chemin/vers/fichier.pdf
python main.py file analyze script.py

# Génération avec sauvegarde
python main.py generate code "fonction tri" --output tri.py
python main.py generate document "rapport" --output rapport.pdf

# Statut du système
python main.py status
```

## 🔍 Fonctionnalités Spécialisées

### Analyse de Code

L'IA peut analyser votre code et fournir:
- **Explication** ligne par ligne
- **Suggestions d'amélioration**
- **Détection de bugs** potentiels
- **Optimisations** possibles
- **Documentation** automatique

```bash
🤖 MyAI> Analyse ce code et suggère des améliorations
```

### Aide au Développement

```bash
🤖 MyAI> Comment déboguer cette erreur Python?
🤖 MyAI> Quelle est la meilleure façon de structurer ce projet?
🤖 MyAI> Peux-tu optimiser cette fonction?
```

### Assistance Documentation

```bash
🤖 MyAI> Génère la documentation pour cette fonction
🤖 MyAI> Crée un README pour ce projet
🤖 MyAI> Écris des tests unitaires pour cette classe
```

## 📊 Gestion des Fichiers Générés

### Localisation des Fichiers

Tous les fichiers générés sont sauvés dans:
```
outputs/
├── generated_code_20240707_143022.py
├── document_20240707_143156.pdf
└── rapport_20240707_143301.docx
```

### Types de Fichiers Créés

- **Code** : `.py`, `.js`, `.html`, `.css`
- **Documents** : `.pdf`, `.docx`, `.txt`
- **Données** : `.json`, `.csv`, `.xml`

## 🎨 Personnalisation

### Configuration du Prompt

Vous pouvez modifier le prompt dans `config.yaml`:

```yaml
ui:
  cli:
    prompt: "🧠 MonIA> "  # Personnalisez votre prompt
```

### Ajustement de l'IA

```yaml
ai:
  temperature: 0.8    # Plus créatif (0.0-1.0)
  max_tokens: 8192   # Réponses plus longues
```

## 💡 Conseils d'Utilisation

### Pour de Meilleurs Résultats:

1. **Soyez précis** dans vos demandes
2. **Donnez du contexte** quand nécessaire
3. **Utilisez des exemples** pour clarifier
4. **Décomposez** les tâches complexes

### Exemples de Bonnes Pratiques:

❌ **Mauvais**: "Fais du code"
✅ **Bon**: "Crée une fonction Python qui lit un fichier CSV et retourne une liste de dictionnaires"

❌ **Mauvais**: "Analyse ce fichier"
✅ **Bon**: "Analyse ce fichier Python et explique la logique de chaque fonction"

## 🔧 Dépannage Courant

### L'IA ne répond pas:
- Vérifiez que le modèle LLM est bien chargé
- Lancez `python main.py status` pour diagnostiquer

### Erreur de lecture de fichier:
- Vérifiez le chemin du fichier
- Assurez-vous que le format est supporté

### Code généré incomplet:
- Augmentez `max_tokens` dans la configuration
- Décomposez votre demande en plusieurs parties

## 🎓 Exemples Pratiques

### Scenario 1: Développement Web

```bash
🤖 MyAI> generer code page HTML avec CSS pour un portfolio
🤖 MyAI> generer code fonction JavaScript pour un carousel d'images
🤖 MyAI> fichier analyser style.css et suggère des améliorations
```

### Scenario 2: Analyse de Données

```bash
🤖 MyAI> generer code script Python pour analyser un fichier CSV
🤖 MyAI> fichier lire data.csv et explique les colonnes
🤖 MyAI> generer code visualisation des données avec matplotlib
```

### Scenario 3: Documentation

```bash
🤖 MyAI> fichier analyser projet.py et génère la documentation
🤖 MyAI> generer document guide utilisateur pour cette API
🤖 MyAI> Crée un README complet pour ce projet
```

Profitez de votre IA personnelle ! 🚀
