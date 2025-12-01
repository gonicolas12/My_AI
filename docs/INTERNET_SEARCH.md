# 🌐 Guide de la Recherche Internet - My Personal AI v5.7.0

## 📋 Vue d'ensemble

La version 5.7.0 apporte des améliorations majeures : **recherche internet optimisée** et **météo en temps réel**. Votre IA peut maintenant accéder aux informations web avec une fiabilité accrue, détecte automatiquement les questions météo et fournit des données actualisées pour **toutes les villes du monde** grâce à wttr.in.

## 🚀 Fonctionnalités

### 🔍 Recherche Web Intelligente
- **DuckDuckGo API Instant** : Recherches rapides et stables (priorité #1)
- **Ordre optimisé** : Moteurs réorganisés pour éviter timeouts et CAPTCHA
- **Résumés automatiques** : Synthèse intelligente des résultats
- **Extraction de contenu** : Analyse des pages web avec BeautifulSoup
- **Traitement parallèle** : Analyse simultanée de plusieurs sources
- **Types de recherche** : Adaptation automatique selon le contexte
- **Fallback intelligent** : Wikipedia API et Cloudscraper si nécessaire

### 🌤️ Météo Temps Réel (v5.7.0)
- **Service wttr.in gratuit** : Aucune clé API requise
- **Détection automatique** : Reconnaît les questions météo naturellement
- **Toutes les villes du monde** : Paris, Tokyo, New York, Londres, Sydney, São Paulo, etc.
- **Données complètes** :
  - Conditions météorologiques actuelles
  - Température et ressenti
  - Humidité et précipitations
  - Vitesse et direction du vent
  - Phase lunaire
- **Prévisions 3 jours** : Conditions futures incluses
- **Format convivial** : Réponses structurées avec emojis
- **Fallback** : Liens Météo-France si service indisponible

### 🧠 Intelligence Contextuelle
- **Détection d'intention** : Reconnaissance automatique des demandes de recherche
- **Extraction de requêtes** : Analyse du langage naturel pour extraire les mots-clés
- **Adaptation de format** : Réponses personnalisées selon le type de recherche
- **Gestion d'erreurs** : Fallback gracieux en cas de problème réseau

## 💬 Comment Utiliser

### Exemples de Commandes

#### Météo (v5.7.0)
```
🤖 "Quelle est la météo à Paris ?"
🤖 "Quel temps fait-il à Toulouse aujourd'hui ?"
🤖 "Météo Lyon"
🤖 "Température à Marseille ?"
🤖 "Prévisions météo Nice"
```

#### Recherches Générales
```
🤖 "Cherche sur internet les actualités Python"
🤖 "Recherche des informations sur l'intelligence artificielle"
🤖 "Trouve-moi des news sur Tesla"
🤖 "Quelle est la hauteur de la Tour Eiffel ?"
```

#### Recherches Spécialisées
```
🤖 "Comment faire du pain ?" (détecté comme tutoriel)
🤖 "Qu'est-ce que le machine learning ?" (détecté comme définition)
🤖 "Dernières actualités climatiques" (détecté comme news)
🤖 "Prix du Bitcoin aujourd'hui" (détecté comme prix)
```

#### Variations de Langage
```
🤖 "Peux-tu chercher..."
🤖 "Trouve-moi..."
🤖 "Recherche moi..."
🤖 "J'aimerais des infos sur..."
🤖 "Qu'est-ce qu'on dit sur..."
```

### Types de Recherche Détectés

| Type | Mots-clés Détectés | Format de Réponse |
|------|-------------------|-------------------|
| **Météo** ⭐ NEW | météo, temps, température, prévisions, climat | Données temps réel + prévisions 3 jours |
| **News** | actualité, news, récent, dernières nouvelles | Résumé des dernières informations |
| **Tutorial** | comment, how to, guide, étapes | Instructions étape par étape |
| **Definition** | qu'est-ce que, définition, c'est quoi | Explication claire et concise |
| **Price** | prix, coût, combien | Information tarifaire actuelle |
| **Review** | avis, opinion, critique | Synthèse des opinions |
| **General** | (autres) | Résumé informatif général |

## 🛠️ Architecture Technique

### Moteur de Recherche v5.7.0
```python
class InternetSearchEngine:
    """Moteur de recherche internet intelligent avec météo"""
    
    def search_and_summarize(self, query: str, context: Dict) -> str:
        """Recherche et résume les résultats web"""
        # 1. Détection météo (_is_weather_query)
        # 2. Si météo: wttr.in API + extraction ville
        # 3. Sinon: DuckDuckGo API Instant (priorité #1)
        # 4. Extraction de contenu des pages
        # 5. Analyse et résumé intelligent
        # 6. Formatage contextuel de la réponse
    
    def _handle_weather_query(self, query: str) -> str:
        """Gère les requêtes météo (NEW v5.7.0)"""
        # 1. Extraction ville (40+ villes FR reconnues)
        # 2. Appel wttr.in API (format pipe-separated)
        # 3. Parsing conditions|temp|humidité|vent|précip|lune
        # 4. Formatage réponse avec emojis
        # 5. Fallback Météo-France si erreur
```

### Ordre des Moteurs (Optimisé v5.7.0)
```python
# Priorité 1: DuckDuckGo API Instant
# - Rapide et stable (< 500ms)
# - Pas de CAPTCHA
# - JSON structuré (Abstract + RelatedTopics)

# Priorité 2: Météo wttr.in (si détection météo)
# - Gratuit sans API key
# - Format texte simple
# - Supporte langue française

# Priorité 3: Wikipedia API
# - Fallback fiable
# - Contenu structuré
# - Peut timeout sur proxy entreprise

# Priorité 4: DuckDuckGo Lite (dernière chance)
# - Scraping HTML
# - Problèmes CAPTCHA fréquents (status 202)
# - Utilisé uniquement si tout échoue
```

### Flux de Traitement v5.7.0
1. **Détection d'intention** : Pattern `internet_search` reconnu
2. **Extraction de requête** : Analyse du langage naturel
3. **Détection météo** : Mots-clés (météo, temps, température, etc.)
4. **Route spécialisée** :
   - Si météo → `_handle_weather_query()` + wttr.in
   - Sinon → `_perform_search()` + DuckDuckGo
5. **Recherche web** : DuckDuckGo API Instant (priorité #1)
6. **Extraction contenu** : Scraping des pages pertinentes
7. **Résumé intelligent** : Synthèse des informations
8. **Formatage** : Adaptation selon le type de recherche

### Gestion des Erreurs
- **Timeout réseau** : 10 secondes par requête
- **Retry automatique** : 3 tentatives maximum
- **Fallback gracieux** : Message informatif en cas d'échec
- **Validation contenu** : Vérification de la qualité des résultats

## 🔧 Configuration

### Variables d'Environnement
```bash
# Optionnel : Configuration proxy
HTTP_PROXY=http://proxy:8080
HTTPS_PROXY=https://proxy:8080

# Optionnel : Timeout personnalisé (en secondes)
SEARCH_TIMEOUT=15
```

### Paramètres Avancés
```python
# Dans internet_search.py
TIMEOUT = 10  # Timeout par requête
MAX_RETRIES = 3  # Nombre de tentatives
MAX_PAGES = 5  # Pages à analyser
MIN_CONTENT_LENGTH = 100  # Taille minimale du contenu

# Météo wttr.in (v5.7.0)
WTTR_BASE_URL = "https://wttr.in/"
WTTR_FORMAT = "%C|%t|%h|%w|%p|%m"  # Conditions|Temp|Humid|Wind|Precip|Moon
WTTR_LANG = "fr"  # Langue française

# Villes supportées (40+)
FRENCH_CITIES = [
    "paris", "lyon", "marseille", "toulouse", "nice",
    "nantes", "montpellier", "strasbourg", "bordeaux", ...
]
```

## 📊 Performances

### Métriques Typiques
- **Temps météo wttr.in** : 1-3 secondes (API externe)
- **Temps DuckDuckGo Instant** : 200-500ms (optimisé v5.7.0)
- **Temps recherche complète** : 2-5 secondes
- **Pages analysées** : 3-5 sources
- **Taille des résumés** : 200-800 mots
- **Taux de succès** : >98% avec API Instant (amélioration +3%)
- **Villes météo supportées** : Toutes les villes du monde (via wttr.in)

### Optimisations v5.7.0
- **Ordre moteurs optimisé** : API Instant prioritaire (évite timeouts)
- **Détection météo précoce** : Route spécialisée avant recherche générale
- **Traitement parallèle** : Analyse simultanée des pages
- **Cache DNS** : Résolution rapide des domaines
- **Compression** : Requêtes HTTP compressées
- **Headers optimisés** : Évite les blocages anti-bot
- **Cloudscraper fallback** : Contournement CAPTCHA si nécessaire

## 🔒 Sécurité et Confidentialité

### Protection des Données
- **Recherches anonymes** : Aucun tracking via DuckDuckGo
- **Pas de cookies** : Sessions sans persistance
- **Headers génériques** : User-agent standard
- **Données locales** : Aucune sauvegarde des recherches

### Bonnes Pratiques
- ✅ Utilisez des requêtes spécifiques
- ✅ Vérifiez votre connexion internet
- ✅ Reformulez en cas d'échec
- ❌ Évitez les requêtes trop larges
- ❌ N'abusez pas des recherches répétitives

## 🐛 Dépannage

### Problèmes Courants

#### "Pas de connexion internet"
```
Solution :
1. Vérifiez votre connexion
2. Testez avec ping google.com
3. Vérifiez les paramètres proxy
```

#### "Météo indisponible" (v5.7.0)
```
Problème : ConnectionResetError ou timeout wttr.in
Cause : Proxy/firewall entreprise bloque wttr.in

Solution :
1. Utilisez les liens Météo-France fournis en fallback
2. Configurez proxy dans internet_search.py si disponible
3. Accédez à wttr.in/{ville} directement dans navigateur
```

#### "DuckDuckGo CAPTCHA" (Résolu v5.7.0)
```
Problème : DuckDuckGo Lite retourne status 202
Solution : Ordre moteurs optimisé, API Instant maintenant prioritaire
Résultat : Plus de CAPTCHA avec nouveau système
```

#### "Recherche échouée"
```
Solution :
1. Reformulez votre requête
2. Soyez plus spécifique
3. Réessayez dans quelques instants
4. Vérifiez que tous les moteurs ne sont pas bloqués
```

#### "Contenu non trouvé"
```
Solution :
1. Utilisez des mots-clés différents
2. Élargissez votre recherche
3. Vérifiez l'orthographe
4. Pour météo: vérifiez que la ville est dans les 40+ supportées
```

### Logs de Débogage
```python
# Activation des logs détaillés
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 📞 Support

Pour toute question ou problème :
1. Consultez d'abord ce guide
2. Vérifiez les logs dans `/logs/`
3. Testez avec des requêtes simples
4. Redémarrez l'application si nécessaire
5. Utilisez le script `clean_project.bat` pour nettoyer le cache

**Amusez-vous bien avec la recherche internet ! 🌐✨**
