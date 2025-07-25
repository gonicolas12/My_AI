# 🎨 Interface Graphique Moderne - My Personal AI

## 🆕 Nouveautés 4.0.0
- FAQ locale multi-fichiers thématiques : tous les fichiers `enrichissement*.jsonl` du dossier `data/` sont chargés automatiquement
- Matching FAQ prioritaire, même en mode asynchrone (GUI moderne)
- Debug simplifié et logs épurés
- Organisation des données d’enrichissement par thèmes
- Robustesse accrue et correction du routage FAQ

## ✨ Nouvelles Fonctionnalités v3.0.0

### 🎯 Design Révolutionné Style Claude
- **Interface sombre** élégante avec palette de couleurs professionnelle
- **Bulles de chat optimisées** : Messages utilisateur avec bulles, réponses IA sans bulle
- **Design responsive** adaptation automatique à tous types d'écrans
- **Plein écran automatique** au lancement avec focus optimal
- **Typographie adaptative** : Polices système optimisées par OS

### 💬 Système de Messages Avancé
- **Bulles utilisateur** positionnées à droite avec hauteur adaptative
- **Messages IA simples** sans bulle pour une meilleure lisibilité
- **Formatage Unicode** : **texte** converti en 𝐭𝐞𝐱𝐭𝐞 gras réel
- **Messages non-scrollables** : Labels optimisés pour les performances
- **Timestamps automatiques** discrets sur chaque message
- **Wrapping intelligent** adaptation automatique du texte

### 🖱️ Drag & Drop Intégré
- **Glisser-déposer natif** pour fichiers PDF, DOCX et code
- **Feedback visuel** avec notifications temporaires
- **Support étendu** : .py, .js, .html, .css, .json, .xml, .md, .txt
- **Traitement automatique** et confirmation de réussite

### 🎭 Animations et Feedback
- **Animation de réflexion** : "🤖 L'IA réfléchit..." avec points animés
- **Animation de recherche** : Icônes rotatives pour recherche internet
- **Indicateurs de statut** : Connexion, traitement, erreurs
- **Notifications temporaires** : Messages de succès/erreur auto-disparition

### ⌨️ Raccourcis Clavier Optimisés
- `Entrée` : Envoyer le message
- `Shift + Entrée` : Nouvelle ligne dans le message
- `Ctrl + L` : Effacer la conversation complète
- Focus automatique sur le champ de saisie au démarrage

### 📁 Gestion de Fichiers Avancée
- **Drag & Drop natif** : Glissez vos fichiers directement dans l'interface
- **Boutons spécialisés** : PDF (📄), DOCX (📝), Code (💻)
- **Support étendu** : .pdf, .docx, .py, .js, .html, .css, .json, .xml, .md, .txt
- **Traitement automatique** avec mémoire persistante pour l'IA
- **Notifications** : Succès ✅, erreurs ❌, informations ℹ️

## 🚀 Installation et Nouvelles Dépendances

### Nouvelles Dépendances v3.0.0
```bash
# Dépendances interface moderne
pip install customtkinter>=5.2.0     # Framework UI moderne avec thèmes sombres
pip install tkinterdnd2>=0.3.0       # Support drag & drop natif
pip install pillow>=10.0.0           # Traitement d'images pour l'interface
```

### Installation Automatique Complète
```bash
# Installer toutes les dépendances pour l'interface moderne
python install_gui_deps.py

# Ou installation standard avec nouvelles dépendances
pip install -r requirements.txt
```

### Installation Manuelle
```bash
# Dépendances essentielles
pip install --user customtkinter

# Dépendances optionnelles pour toutes les fonctionnalités
pip install --user tkinterdnd2 pillow
```

## 🎮 Utilisation

### Lancement
```bash
# Via le launcher (recommandé)
python launcher.py gui

# Ou directement
python interfaces/gui_modern.py
```

### Première Utilisation
1. **L'interface se lance en plein écran** automatiquement
2. **Tapez votre message** dans la zone de saisie en bas
3. **Utilisez le formatage** : `**texte en gras**` pour du texte en gras
4. **Glissez des fichiers** directement dans l'interface
5. **Explorez les raccourcis clavier** pour une utilisation efficace

## 🎨 Personnalisation

### Thèmes et Couleurs
L'interface utilise une palette de couleurs moderne définie dans `interfaces/modern_styles.py` :

- **Fond principal** : Noir profond (#0f0f0f)
- **Fond secondaire** : Gris sombre (#1a1a1a)
- **Accent** : Orange Claude (#ff6b47)
- **Messages utilisateur** : Bleu (#2d5aa0)
- **Messages IA** : Gris sombre (#1a1a1a)

### Polices
Les polices s'adaptent automatiquement selon votre système :
- **Windows** : Segoe UI / Consolas
- **macOS** : SF Pro Display / SF Mono
- **Linux** : Ubuntu / Ubuntu Mono

### Responsive Design
L'interface s'adapte automatiquement à 3 tailles :
- **Petit écran** (< 800px) : Interface compacte
- **Écran moyen** (800-1200px) : Interface équilibrée
- **Grand écran** (> 1200px) : Interface étendue

## 🛠️ Fonctionnalités Techniques

### Architecture
- **Base CustomTkinter** pour un look moderne
- **Fallback tkinter** si CustomTkinter n'est pas disponible
- **Gestion d'erreurs** robuste avec messages clairs
- **Threading** pour les opérations IA sans bloquer l'interface

### Performance
- **Traitement asynchrone** des messages
- **Optimisation mémoire** pour les longs conversations
- **Cache intelligent** des ressources
- **Animations optimisées** pour la fluidité

### Compatibilité
- **Windows** : Support complet avec plein écran
- **macOS** : Interface native adaptée
- **Linux** : Compatibilité étendue

## 🔧 Dépannage

### CustomTkinter n'est pas disponible
```
⚠️ CustomTkinter non disponible, utilisation de tkinter standard
```
**Solution** : `pip install --user customtkinter`

### Drag & Drop ne fonctionne pas
```
⚠️ TkinterDnD2 non disponible, drag & drop désactivé
```
**Solution** : `pip install --user tkinterdnd2`

### L'interface ne se lance pas en plein écran
- Vérifiez que vous êtes sur Windows (fonctionnalité optimisée pour Windows)
- L'interface devrait quand même s'ouvrir en mode fenêtré

### Messages sans formatage
- Assurez-vous d'utiliser `**texte**` pour le gras
- Vérifiez que le texte est correctement entouré par les astérisques

## 📱 Fonctionnalités Mobiles

Bien que conçue pour desktop, l'interface s'adapte aux petits écrans :
- **Interface compacte** automatique
- **Boutons agrandis** pour une meilleure accessibilité
- **Scroll optimisé** pour la navigation tactile

## 🎯 Prochaines Améliorations

- [ ] Thèmes multiples (clair/sombre/coloré)
- [ ] Export des conversations en PDF/HTML
- [ ] Support des émojis et images
- [ ] Mode présentation pour démonstrations
- [ ] Plugins visuels personnalisés
- [ ] Intégration avec le presse-papiers
- [ ] Notifications système
- [ ] Raccourcis personnalisables

## 🆘 Support

En cas de problème :
1. **Vérifiez les dépendances** avec `python test_modern_gui.py`
2. **Consultez les logs** dans le dossier `logs/`
3. **Testez le fallback** : l'interface standard devrait fonctionner
4. **Installez les dépendances** avec `python install_gui_deps.py`

---

💡 **Astuce** : Pour une expérience optimale, installez toutes les dépendances optionnelles et utilisez l'interface en plein écran sur un grand moniteur !

🎨 **Design** : Interface inspirée de Claude d'Anthropic, adaptée pour une IA locale avec toutes les fonctionnalités modernes.
