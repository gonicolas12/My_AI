# ❓ FAQ - My Personal AI

## 🤖 Questions Générales

### Mon IA est-elle vraiment 100% locale ?
Oui ! Absolument aucune donnée n'est envoyée à l'extérieur. Votre IA fonctionne entièrement sur votre machine sans connexion internet après installation. Vos conversations, documents et code restent complètement privés.

### Ai-je besoin d'Ollama, OpenAI ou autres services ?
Non ! My Personal AI possède son propre moteur d'IA intégré. Pas besoin d'installer Ollama, de créer un compte OpenAI, ou d'utiliser des services externes. Tout est inclus dans le package.

### Quelle est la différence avec ChatGPT ou Claude ?

- **Confidentialité** : Vos données restent sur votre machine
- **Pas d'abonnement** : Gratuit une fois installé
- **Spécialisé** : Optimisé pour l'aide au développement et l'analyse de documents
- **Mémoire temporaire** : Se souvient de vos documents et conversations, jusqu'à ce que vous fermez le programme (pour des questions de sécurité)
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
- Consultez les logs pour diagnostic

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

💡 **Question non listée ?** Envoyez-moi un message sur mon **LinkedIn** : [Nicolas Gouy](https://www.linkedin.com/in/nicolas-gouy-99120932b/)

🤖 **My Personal AI** - Votre assistant local intelligent et sécurisé
