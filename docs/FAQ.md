# ❓ FAQ - My Personal AI

## 🤖 Questions Générales

### Mon IA est-elle vraiment 100% locale ?
Oui ! Absolument aucune donnée n'est envoyée à l'extérieur. Votre IA fonctionne entièrement sur votre machine sans connexion internet après installation. Vos conversations, documents et code restent complètement privés.

### Ai-je besoin d'Ollama, OpenAI ou autres services ?
**Ollama est optionnel mais recommandé !**

| Configuration | Qualité des réponses | Installation |
|---------------|---------------------|--------------|
| **Avec Ollama** | LLM complet (llama3.1:8b) - conversations naturelles | Télécharger depuis ollama.com |
| **Sans Ollama** | Mode patterns/règles - fonctionnel mais basique | Rien à installer |

L'IA fonctionne dans les deux cas, mais Ollama offre des réponses beaucoup plus intelligentes et naturelles. **Aucun compte OpenAI ou service cloud n'est requis.**

### Comment installer Ollama ?
1. Téléchargez depuis **https://ollama.com/download**
2. Installez le modèle : `ollama pull llama3.1:8b`
3. Créez le modèle personnalisé : `.\create_custom_model.bat`

L'application détecte automatiquement Ollama au démarrage.

### Quel modèle Ollama choisir selon ma RAM ?

| RAM | Modèle recommandé | Commande |
|-----|-------------------|----------|
| 8 GB | llama3.2 (3B) | `ollama pull llama3.2` |
| 16 GB | llama3.1:8b ✅ | `ollama pull llama3.1:8b` |
| 32 GB+ | llama3.1:70b | `ollama pull llama3.1:70b` |

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
ollama pull llama3.1:8b
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
2. Testez manuellement : `ollama run llama3.1:8b "Bonjour"`
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
La mémoire de session est effacée à la fermeture, mais vous pouvez configurer la persistance dans `config.yaml` si désiré.

## 🚀 Évolutions et Support

### L'IA va-t-elle s'améliorer avec le temps ?
Oui ! Évolutions prévues :
- Extension VS Code intégrée
- Support de plus de types de fichiers
- API REST locale

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

💡 **Question non listée ?** Envoyez-moi un message sur mon **LinkedIn : [Nicolas Gouy](https://www.linkedin.com/in/nicolas-gouy-99120932b/)**

🤖 **My Personal AI** - Votre assistant local intelligent et sécurisé
