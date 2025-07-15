# 🚀 Guide de Démarrage Rapide - My Personal AI v3.0.0

## 📋 Qu'est-ce que My Personal AI ?

Une IA **hybride locale/internet** qui fonctionne principalement sur votre machine, avec accès optionnel aux informations web en temps réel. Elle comprend vos intentions, se souvient de vos documents, et vous aide dans vos tâches quotidiennes.

### 🌟 Recherche Internet
- 🌐 Accès aux informations en temps réel
- 🔍 Résumés automatiques des résultats web
- 🤖 Intelligence contextuelle pour adapter les recherches
- 🔒 Recherches anonymes via DuckDuckGo

## ⚡ Installation Express

### 1. Prérequis
- Python 3.8+ installé sur votre système
- Environ 100 MB d'espace disque libre

### 2. Installation
```bash
# Clonez ou téléchargez le projet
cd My_AI

# Installez les dépendances
pip install -r requirements.txt
```

### 3. Premier Lancement
```bash
# Interface graphique (recommandée)
python main.py

# Ou utilisez le script batch
.\launch.bat
# Puis choisissez l'option 1
```

## 🎯 Premiers Pas (5 minutes)

### Étape 1 : Saluer l'IA
```
🤖 Vous : slt
🤖 IA : Salut ! Comment puis-je t'aider aujourd'hui ?
```
✅ L'IA reconnaît les salutations naturelles : "slt", "salut", "bonjour", "bjr", etc.

### Étape 2 : Poser une Question Technique
```
🤖 Vous : Comment créer une liste en Python ?
🤖 IA : [Réponse technique complète avec exemples]
```
✅ L'IA distingue automatiquement les questions techniques et adapte ses réponses.

### Étape 3 : 🌐 NOUVEAU - Recherche Internet
```
🤖 Vous : Cherche sur internet les actualités Python
🤖 IA : [Recherche et résumé des dernières actualités Python]

🤖 Vous : Trouve-moi des infos sur l'IA en 2025
🤖 IA : [Synthèse d'informations récentes sur l'IA]
```
✅ L'IA accède aux informations en temps réel et fait des résumés intelligents.

### Étape 4 : Analyser un Document
1. Glissez un fichier PDF ou DOCX dans l'interface
2. Tapez : "résume ce document"
```
🤖 IA : Voici un résumé du fichier "votre_document.pdf" : [résumé intelligent]
```
✅ L'IA se souvient des documents et peut y faire référence plus tard.

### Étape 4 : Vider la Conversation
- Cliquez sur "Clear Chat" pour tout remettre à zéro
✅ Conversation et mémoire effacées proprement.

## 🧠 Fonctionnalités Intelligentes

### Reconnaissance d'Intentions
L'IA détecte automatiquement :
- **Salutations** : "slt", "bonjour", "bjr", "hello"
- **Questions Code** : Programmation, debug, syntaxe
- **Questions Documents** : Résumés, analyses, extractions
- **Conversation Générale** : Discussion libre

### Mémoire Contextuelle
- **Documents traités** : L'IA se souvient de tous les PDF/DOCX chargés
- **Code analysé** : Référence aux snippets de code précédents
- **Historique** : Continuité dans les conversations

### Réponses Adaptatives
- **Format technique** : Pour les questions de code
- **Résumés structurés** : Pour les documents
- **Ton conversationnel** : Pour les salutations et discussions

## 🔧 Interface Utilisateur

### Interface Graphique (GUI)
- **Zone de conversation** : Historique complet des échanges
- **Zone de saisie** : Entrée de texte intuitive
- **Glisser-déposer** : Chargement direct de fichiers
- **Bouton Clear Chat** : Remise à zéro complète

### Interface Ligne de Commande (CLI)
```bash
# Mode interactif
python main.py --cli

# Commande directe
python main.py chat "votre question"

# Traitement de fichier
python main.py process document.pdf
```

## 📚 Exemples d'Usage

### Session Complète Type
```
🤖 Vous : bonjour
🤖 IA : Bonjour ! Comment puis-je vous aider aujourd'hui ?

🤖 Vous : [glisse rapport_annuel.pdf]
🤖 IA : J'ai bien reçu le fichier "rapport_annuel.pdf". Il a été traité et son contenu est maintenant en mémoire.

🤖 Vous : quels sont les points clés de ce rapport ?
🤖 IA : Voici les points clés du rapport annuel : [analyse détaillée]

🤖 Vous : comment implémenter ces recommandations en Python ?
🤖 IA : Basé sur les recommandations du rapport, voici du code Python : [code contextualisé]

🤖 Vous : merci, au revoir
🤖 IA : De rien ! N'hésitez pas à revenir si vous avez d'autres questions. Au revoir !
```

## 🔍 Dépannage Rapide

### L'IA ne démarre pas
```bash
# Vérifiez les dépendances
pip install -r requirements.txt

# Vérifiez la version Python
python --version  # Doit être 3.8+
```

### Les fichiers ne se chargent pas
- Vérifiez que le fichier est un PDF ou DOCX valide
- Essayez de le glisser directement dans la zone de conversation
- Vérifiez l'espace disque disponible

### L'IA ne répond pas
- Vérifiez les logs dans le dossier `logs/`
- Redémarrez l'application
- Utilisez "Clear Chat" pour reset l'état

## 📖 Documentation Complète

- **[README.md](../README.md)** : Vue d'ensemble complète
- **[ARCHITECTURE.md](ARCHITECTURE.md)** : Structure technique
- **[USAGE.md](USAGE.md)** : Guide d'utilisation détaillé
- **[Exemples](../examples/)** : Scripts et cas d'usage

## 🎯 Prochaines Étapes

1. **Explorez les exemples** : Dossier `examples/` pour des cas d'usage avancés
2. **Personnalisez** : Modifiez `config.yaml` selon vos besoins
3. **Intégrez** : Utilisez l'API interne pour vos propres scripts
4. **Contribuez** : Proposez des améliorations et nouvelles fonctionnalités

---
🤖 **My Personal AI** - Votre IA locale intelligente, privée et sécurisée !
