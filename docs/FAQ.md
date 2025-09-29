# ❓ FAQ - My Personal AI

## 🤖 Questions Générales

### Q: Mon IA est-elle vraiment 100% locale ?
**R:** Oui ! Absolument aucune donnée n'est envoyée à l'extérieur. Votre IA fonctionne entièrement sur votre machine sans connexion internet après installation. Vos conversations, documents et code restent complètement privés.

### Q: Ai-je besoin d'Ollama, OpenAI ou autres services ?
**R:** Non ! My Personal AI possède son propre moteur d'IA intégré. Pas besoin d'installer Ollama, de créer un compte OpenAI, ou d'utiliser des services externes. Tout est inclus dans le package.

### Q: Quelle est la différence avec ChatGPT ou Claude ?
**R:** 
- **Confidentialité** : Vos données restent sur votre machine
- **Pas d'abonnement** : Gratuit une fois installé
- **Spécialisé** : Optimisé pour l'aide au développement et l'analyse de documents
- **Mémoire temporaire** : Se souvient de vos documents et conversations, jusqu'à ce que vous fermez le programme (pour des questions de sécurité)
- **Open source** : Le code est entièrement accessible, modifiable et vérifiable par tous

## 🔧 Installation et Configuration

### Q: Quels sont les prérequis pour installer l'IA ?
**R:** 
- Python 3.8+ (3.10+ recommandé)
- 4 GB RAM minimum (8 GB recommandé)
- ~100 MB d'espace disque
- Windows, macOS ou Linux

### Q: L'installation est-elle compliquée ?
**R:** Non ! Installation en 3 commandes :
```bash
cd My_AI
pip install -r requirements.txt
.\launch.bat
```

### Q: Que faire si l'installation échoue ?
**R:** Vérifiez :
1. Version de Python : `python --version` (doit être 3.8+)
2. Dépendances : `pip install -r requirements.txt`
3. Permissions : Exécutez en administrateur si nécessaire
4. Consultez les logs dans le dossier `logs/`

## 💬 Utilisation et Fonctionnalités

### Q: Comment l'IA reconnaît-elle mes intentions ?
**R:** L'IA analyse vos messages et détecte automatiquement :
- **Salutations** : "slt", "bonjour", "bjr", "hello"
- **Questions techniques** : Code, programmation, debug
- **Questions sur documents** : Après traitement d'un PDF/DOCX
- **Conversation générale** : Discussion libre

### Q: Comment traiter des documents PDF ou DOCX ?
**R:** 
1. **Interface graphique** : Glissez le fichier dans la zone de conversation
2. **Ligne de commande** : `python main.py process votre_document.pdf`
3. **Questions** : Ensuite, tapez "résume ce document" ou posez des questions spécifiques

### Q: L'IA se souvient-elle de ce que je lui dis ?
**R:** Oui ! L'IA garde en mémoire :
- Les documents que vous avez traités
- Le code que vous avez analysé
- Le contexte pour des réponses cohérentes

### Q: Comment effacer l'historique et repartir à zéro ?
**R:** Utilisez le bouton "Clear Chat" dans l'interface graphique, ou redémarrez l'application. Cela efface complètement la conversation et la mémoire.

## 🐛 Dépannage

### Q: L'IA ne démarre pas, que faire ?
**R:** 
1. Vérifiez Python : `python --version`
2. Réinstallez les dépendances : `pip install -r requirements.txt`
3. Vérifiez les logs : dossier `logs/`
4. Essayez en mode debug : `python main.py --debug`

### Q: Les fichiers PDF/DOCX ne se chargent pas
**R:** 
- Vérifiez que le fichier n'est pas corrompu
- Essayez avec un autre fichier
- Vérifiez l'espace disque disponible
- Redémarrez l'application

### Q: L'IA donne des réponses étranges ou incohérentes
**R:** 
- Utilisez "Clear Chat" pour remettre à zéro
- Vérifiez que votre question est claire
- Essayez de reformuler différemment
- Consultez les logs pour diagnostic

### Q: L'interface graphique ne s'affiche pas
**R:** 
- Vérifiez que Tkinter est installé : `python -m tkinter`
- Utilisez l'interface CLI : `python launcher.py gui`
- Sur Linux, installez : `sudo apt-get install python3-tk`

## 📚 Fonctionnalités Avancées

### Q: Puis-je personnaliser le comportement de l'IA ?
**R:** Oui ! Éditez le fichier `config.yaml` pour :
- Changer le nom de l'IA
- Ajuster la longueur des réponses
- Modifier les types de fichiers supportés
- Configurer les paramètres de mémoire

### Q: L'IA peut-elle générer du code ?
**R:** Oui ! L'IA peut :
- Générer des fonctions Python
- Expliquer du code existant
- Suggérer des améliorations
- Détecter des problèmes
- Proposer des alternatives

### Q: Puis-je utiliser l'IA en ligne de commande ?
**R:** Absolument ! 
```bash
# Mode interactif CLI
python main.py --cli

# Commande directe
python main.py chat "votre question"

# Traitement de fichier
python main.py process document.pdf
```

### Q: Comment intégrer l'IA dans mes propres scripts ?
**R:** Utilisez l'API interne :
```python
from core.ai_engine import AIEngine

ai = AIEngine()
response = ai.process_user_input("Votre question")
print(response)
```

## 🔒 Sécurité et Confidentialité

### Q: Mes données sont-elles vraiment sécurisées ?
**R:** Oui ! Garanties :
- **Pas de réseau** : Aucun envoi de données externes
- **Stockage local** : Tout reste sur votre machine
- **Code ouvert** : Architecture vérifiable
- **Pas de télémétrie** : Aucun tracking

### Q: Puis-je utiliser l'IA pour des documents confidentiels ?
**R:** Absolument ! C'est même recommandé. Vos documents restent 100% sur votre machine, idéal pour :
- Documents d'entreprise confidentiels
- Code source propriétaire
- Données personnelles sensibles
- Informations légales ou médicales

### Q: L'IA conserve-t-elle mes données après fermeture ?
**R:** La mémoire de session est effacée à la fermeture, mais vous pouvez configurer la persistance dans `config.yaml` si désiré.

## 🚀 Évolutions et Support

### Q: L'IA va-t-elle s'améliorer avec le temps ?
**R:** Oui ! Évolutions prévues :
- Extension VS Code intégrée
- Support de plus de types de fichiers
- API REST locale
- Recherches Internet

### Q: Puis-je contribuer au développement ?
**R:** Bien sûr ! Le projet est ouvert aux contributions :
- Rapporter des bugs
- Proposer des fonctionnalités
- Améliorer la documentation
- Ajouter des exemples d'usage

### Q: Où trouver de l'aide supplémentaire ?
**R:** 
- **Documentation** : Dossier `docs/`
- **Exemples** : Dossier `examples/`
- **Logs** : Dossier `logs/` pour diagnostic
- **Code source** : Architecture complètement ouverte

---

💡 **Question non listée ?** L'IA peut répondre à vos questions directement ! Lancez-la et demandez-lui de l'aide !

🤖 **My Personal AI** - Votre assistant local intelligent et sécurisé
