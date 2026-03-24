# ❓ FAQ - My Personal AI

## 🤖 Questions Générales

### Mon IA est-elle vraiment 100% locale ?
Oui ! Absolument aucune donnée n'est envoyée à l'extérieur. Votre IA fonctionne entièrement sur votre machine sans connexion internet après installation. Vos conversations, documents et code restent complètement privés.

### Ai-je besoin d'Ollama, OpenAI ou autres services ?
**Ollama est optionnel mais recommandé !**

| Configuration | Qualité des réponses | Installation |
|---------------|---------------------|--------------|
| **Avec Ollama** | LLM complet - conversations naturelles | Télécharger depuis ollama.com |
| **Sans Ollama** | Mode patterns/règles - fonctionnel mais basique | Rien à installer |

L'IA fonctionne dans les deux cas, mais Ollama offre des réponses beaucoup plus intelligentes et naturelles. **Aucun compte OpenAI ou service cloud n'est requis.**

### Comment changer de modèle Ollama ?

Trois étapes, dans l'ordre :

**Étape 1 — `config.yaml`** (pilote tout le code Python) :
```yaml
llm:
  local:
    default_model: "qwen3.5:2b"  # ← nouvelle valeur
```

**Étape 2 — `Modelfile`** (doit correspondre à `config.yaml`) :
```
FROM qwen3.5:2b   # ← même valeur
```

**Étape 3 — Terminal** :
```bash
ollama pull qwen3.5:2b
.\create_custom_model.bat
```

> ⚠️ `config.yaml` et `Modelfile` doivent toujours avoir la **même valeur**. `config.yaml` contrôle le code Python, `Modelfile` contrôle la construction du modèle custom `my_ai` dans Ollama.

### Comment installer Ollama ?
1. Téléchargez depuis **https://ollama.com/download**
2. Installez le modèle : `ollama pull qwen3.5:4b`
3. Créez le modèle personnalisé : `.\create_custom_model.bat`

L'application détecte automatiquement Ollama au démarrage.

### Quel modèle Ollama choisir selon ma RAM ?

| RAM | Modèle recommandé | Commande |
|-----|-------------------|----------|
| 8 GB | qwen3.5:4b | `ollama pull qwen3.5:4b` |
| 16 GB | qwen3.5:9b ✅ | `ollama pull qwen3.5:9b` |
| 32 GB+ | qwen3.5:27b | `ollama pull qwen3.5:27b` |

### Mes données restent-elles confidentielles avec Ollama ?
**Oui, 100% !** Ollama exécute le modèle **localement sur votre PC**. Aucune donnée n'est envoyée sur internet. C'est l'avantage principal par rapport à ChatGPT ou Claude.

### Quelle est la différence avec ChatGPT ou Claude ?

- **Confidentialité** : Vos données restent sur votre machine
- **Pas d'abonnement** : Gratuit une fois installé
- **Spécialisé** : Optimisé pour l'aide au développement et l'analyse de documents
- **Mémoire locale** : Se souvient de vos documents et conversations, mais stocke tout localement
- **Open source** : Le code est entièrement accessible, modifiable et vérifiable par tous

## 🔧 Installation et Configuration

### Quels sont les prérequis pour installer l'IA ?
 
- Python 3.8+ (3.10+ recommandé)
- 4 GB RAM minimum (8 GB recommandé)
- ~100 MB d'espace disque
- Windows, macOS ou Linux

### L'installation est-elle compliquée ?
Non ! Installation en 3 commandes :
```bash
cd My_AI
pip install -r requirements.txt
.\launch.bat
```

**Pour Ollama (optionnel mais recommandé) :**
```bash
# Télécharger depuis https://ollama.com/download
ollama pull qwen3.5:4b
.\create_custom_model.bat
```

### Que faire si l'installation échoue ?
Vérifiez :
1. Version de Python : `python --version` (doit être 3.8+)
2. Dépendances : `pip install -r requirements.txt`
3. Permissions : Exécutez en administrateur si nécessaire
4. Consultez les logs dans le dossier `logs/`

## 💬 Utilisation et Fonctionnalités

### Comment l'IA reconnaît-elle mes intentions ?
L'IA analyse vos messages et détecte automatiquement :
- **Salutations** : "slt", "bonjour", "bjr", "hello"
- **Questions techniques** : Code, programmation, debug
- **Questions sur documents** : Après traitement d'un PDF/DOCX
- **Conversation générale** : Discussion libre

### Comment traiter des documents PDF ou DOCX ?

1. **Interface graphique** : Glissez le fichier dans la zone de conversation
2. **Ligne de commande** : `python main.py process votre_document.pdf`
3. **Questions** : Ensuite, tapez "résume ce document" ou posez des questions spécifiques

### L'IA se souvient-elle de ce que je lui dis ?
Oui ! L'IA garde en mémoire :
- Les documents que vous avez traités
- Le code que vous avez analysé
- Le contexte pour des réponses cohérentes

### Comment effacer l'historique et repartir à zéro ?
Utilisez le bouton "Clear Chat" dans l'interface graphique, ou redémarrez l'application. Cela efface complètement la conversation et la mémoire.

## 🐛 Dépannage

### L'IA ne démarre pas, que faire ?

1. Vérifiez Python : `python --version`
2. Réinstallez les dépendances : `pip install -r requirements.txt`
3. Vérifiez les logs : dossier `logs/`
4. Essayez en mode debug : `python main.py --debug`

### Les fichiers PDF/DOCX ne se chargent pas

- Vérifiez que le fichier n'est pas corrompu
- Essayez en ayant votre fichier fermé
- Essayez avec un autre fichier
- Vérifiez l'espace disque disponible
- Redémarrez l'application

### L'IA donne des réponses étranges ou incohérentes

- Utilisez "Clear Chat" pour remettre à zéro
- Vérifiez que votre question est claire
- Essayez de reformuler différemment
- **Si Ollama est installé** : Vérifiez qu'il tourne (`ollama list`)
- **Si mode fallback** : Les réponses sont basées sur des patterns, moins naturelles
- Consultez les logs pour diagnostic

### Ollama ne fonctionne pas, que faire ?

1. Vérifiez qu'Ollama est lancé : `ollama list`
2. Testez manuellement : `ollama run qwen3.5:4b "Bonjour"`
3. Vérifiez le port : `curl http://localhost:11434`
4. Redémarrez Ollama si nécessaire
5. L'application fonctionnera en mode fallback si Ollama est indisponible

### L'interface graphique ne s'affiche pas

- Vérifiez que Tkinter est installé : `python -m tkinter`
- Utilisez l'interface CLI : `python launcher.py gui`
- Sur Linux, installez : `sudo apt-get install python3-tk`

## 📚 Fonctionnalités Avancées

### L'IA peut-elle générer du code ?
Oui ! L'IA peut :
- Générer des fonctions Python
- Expliquer du code existant
- Suggérer des améliorations
- Détecter des problèmes
- Proposer des alternatives

### Puis-je utiliser l'IA en ligne de commande ?
Absolument ! 
```bash
# Mode interactif CLI
python main.py --cli

# Commande directe
python main.py chat "votre question"

# Traitement de fichier
python main.py process document.pdf
```

## 🔒 Sécurité et Confidentialité

### Mes données sont-elles vraiment sécurisées ?
Oui ! Garanties :
- **Pas de réseau** : Aucun envoi de données externes
- **Stockage local** : Tout reste sur votre machine
- **Code ouvert** : Architecture vérifiable
- **Pas de télémétrie** : Aucun tracking

### Puis-je utiliser l'IA pour des documents confidentiels ?
Absolument ! C'est même recommandé. Vos documents restent 100% sur votre machine, idéal pour :
- Documents d'entreprise confidentiels
- Code source propriétaire
- Données personnelles sensibles
- Informations légales ou médicales

### L'IA conserve-t-elle mes données après fermeture ?
Avec les **Workspaces v7.0.0**, oui ! Vos conversations sont sauvegardées automatiquement dans des espaces de travail isolés (`data/workspaces/`). Vous pouvez les charger à tout moment. Sans workspace, la mémoire de session est effacée à la fermeture.

## 🆕 Questions v7.0.0

### Comment utiliser l'API REST ?
Activez `api.enabled: true` dans `config.yaml`, puis accédez à `http://localhost:8000/api/health` pour vérifier que le serveur tourne. Tous les endpoints sont documentés dans [USAGE.md](USAGE.md#-api-rest-locale).

### Comment exporter une conversation ?
L'export se fait via le module `ConversationExporter`. Les formats disponibles sont Markdown (.md), HTML (.html, avec thème sombre) et PDF (.pdf). Les fichiers sont sauvegardés dans `outputs/exports/`.

### Comment fonctionne la base de connaissances ?
L'IA extrait automatiquement des faits depuis vos conversations (préférences, décisions, personnes, procédures, informations techniques). Ces faits sont stockés dans SQLite (`data/knowledge_base/facts.db`) avec un score de confiance. Les faits pertinents sont injectés dans le contexte des futures conversations.

### L'IA peut-elle répondre dans une autre langue ?
Oui ! Le `LanguageDetector` détecte automatiquement la langue de votre message parmi 12 langues (français, anglais, espagnol, allemand, italien, portugais, néerlandais, russe, chinois, japonais, coréen, arabe) et génère un suffix de prompt système pour que l'IA réponde dans la même langue.

### Comment attacher des fichiers aux agents ?
Cliquez sur le bouton **"+"** dans la zone de saisie de l'onglet Agents, sélectionnez vos fichiers, et ils seront automatiquement lus et injectés dans le prompt de l'agent. Dans un workflow multi-agents, tous les agents reçoivent les fichiers joints.

### L'IA demande-t-elle confirmation avant de supprimer un fichier ?
Oui ! Depuis la v7.0.0, quand l'IA utilise l'outil MCP `delete_local_file`, une fenêtre de confirmation s'affiche avec le chemin du fichier. Vous devez explicitement cliquer "Oui, supprimer" pour autoriser la suppression.

### Les nouveaux modules v7.0.0 sont-ils obligatoires ?
Non ! Tous les modules v7.0.0 sont **optionnels** avec dégradation gracieuse. Si une dépendance est manquante (ex: `fastapi` pour l'API REST, `langdetect` pour la détection de langue), un warning est loggé et le module est désactivé. Le reste de l'application fonctionne normalement.

## 🚀 Évolutions et Support

### L'IA va-t-elle s'améliorer avec le temps ?
Oui ! Évolutions prévues :
- Extension VS Code intégrée
- Application web
- Intégrations API tierces

### Puis-je contribuer au développement ?
Bien sûr ! Le projet est ouvert aux contributions :
- Rapporter des bugs
- Proposer des fonctionnalités
- Améliorer la documentation
- Ajouter des exemples d'usage

### Où trouver de l'aide supplémentaire ?

- **Documentation** : Dossier `docs/`
- **Exemples** : Dossier `examples/`
- **Logs** : Dossier `logs/` pour diagnostic
- **Code source** : Architecture complètement ouverte

---

💡 **Question non listée ?** Envoyez-moi un message sur mon **LinkedIn : [Nicolas Gouy](https://www.linkedin.com/in/nicolas-gouy/)**

🤖 **My Personal AI** - Votre assistant local intelligent et sécurisé
