# 🔍 Guide de la Recherche Internet - My Personal AI

## 📋 Vue d'ensemble

La recherche internet donne à l'IA des informations récentes : actualités, prix, classements, documentation technique, météo. Le modèle appelle l'outil `web_search` quand une question le demande. La recherche renvoie des **sources numérotées** (titre, lien, extrait du moteur, passages lus sur les pages) ; le modèle rédige sa réponse à partir d'elles et termine par les liens des sources, cliquables.

La recherche n'appelle jamais le modèle elle-même : elle collecte, le modèle de la conversation rédige.

## 🚀 Fonctionnalités

### 🔍 Recherche web
- **DuckDuckGo** (version HTML sans JavaScript) en premier, **Yahoo** en secours, **Wikipédia** en dernier recours — et seulement pour des articles qui reprennent au moins la moitié des mots de la requête.
- **Lecture des pages** : les 4 premiers résultats sont ouverts en parallèle. Leur texte principal est extrait sans menus, bandeaux de cookies, publicités ni pieds de page, et le modèle reçoit le début de la page puis le passage qui répond le mieux à la requête (1 500 caractères par page). Une page illisible (accès refusé, contenu en JavaScript) garde l'extrait du moteur.
- **Région** : requête en français → résultats France (DuckDuckGo `fr-fr`, `fr.search.yahoo.com`, Wikipédia FR) ; requête en anglais → résultats mondiaux.
- **Une URL dans la requête** : la page est lue directement (« résume https://… »).

### 🌤️ Météo
- **Open-Meteo** : sans clé, données des services météo nationaux (Météo-France pour la France), géocodage multilingue (« Londres », « Saint-Étienne », « São Paulo »).
- Conditions actuelles (température, ressenti, humidité, vent et sa direction, précipitations) et **prévisions sur 7 jours**, les deux premières marquées « aujourd'hui » et « demain » (date du lieu) : le modèle ne connaît pas la date du jour.
- Détection stricte : « météo », « weather », « forecast », « quel temps ». « Combien de temps dure… » ou « temps de cuisson » ne partent plus vers la météo.
- Lieu inconnu d'Open-Meteo (un quartier, une adresse) : recherche web à la place, plutôt qu'un homonyme à l'autre bout du monde.

### 🔗 Sources cliquables
- Chaque résultat se termine par un bloc `📚 **Sources**` (`[n] [Titre](URL)`) que le modèle reprend en fin de réponse. Les liens sont cliquables, et les marqueurs `[n]` aussi quand le bloc est numéroté — sur **desktop** comme sur **mobile** (Relay).
- Construit avec `utils/citations.py` (`parse_citation_map`, `extract_sources`) ; rendu cliquable côté GUI par `markdown_formatting._apply_inline_citations`.
- Les renvois de notes recopiés des wikis (`[1]`, `[réf. nécessaire]`) sont retirés du texte des pages : dans la réponse, ils seraient devenus de faux liens vers nos sources.

## 🛡️ Réseau et sécurité

Le trafic de la recherche est celui d'un client ordinaire :

- **HTTPS vérifié** : les certificats sont contrôlés avec le magasin du système (paquet `truststore`), celui où un réseau d'entreprise installe la racine de son proxy d'inspection TLS. L'ancienne version désactivait toute vérification.
- **User-Agent honnête** : `Mozilla/5.0 (compatible; My_AI/8.1.0; +https://github.com/gonicolas12/My_AI)`, sans rotation d'identité.
- **Aucun contournement anti-robot** : plus de `cloudscraper`, plus d'instances SearXNG publiques (domaines exotiques souvent classés « anonymiseurs » par les pare-feu), plus de scraping de Google ni de Brave.
- **Peu de requêtes** : un moteur à la fois. Un moteur qui renvoie sa page anti-robot est mis en pause 15 minutes au lieu d'être relancé à chaque recherche (1 minute s'il est injoignable). Une recherche déjà faite reste en cache 30 minutes.
- **Une recherche typique** : 1 page de résultats + 4 pages lues. La météo : 2 appels à Open-Meteo.

### Configuration réseau (`config.yaml`, section `network`)

| Clé | Effet sur la recherche |
|-----|------------------------|
| `proxy_url`, `http_proxy`, `https_proxy` | Proxy utilisé (équivalent des variables `HTTP_PROXY` / `HTTPS_PROXY`) |
| `ca_bundle` | Bundle CA à utiliser à la place du magasin du système |
| `use_system_truststore` | `true` (défaut) : magasin de certificats du système |
| `allow_insecure_ssl` | `true` : certificats non vérifiés. Dernier recours, à éviter |

## 💬 Comment Utiliser

### Recherches générales
```
🤖 "Cherche sur internet les meilleures marques de voiture, fais un tableau"
🤖 "Quelles sont les nouveautés de Python 3.14 ?"
🤖 "Prix du bitcoin aujourd'hui"
🤖 "Dernières actualités sur Tesla"
```

### Météo
```
🤖 "Quelle est la météo à Toulouse ?"
🤖 "Quel temps fera-t-il à Saint-Étienne ce week-end ?"
🤖 "Weather in New York tomorrow"
```

### Lire une page
```
🤖 "Résume cette page : https://docs.python.org/3/whatsnew/3.14.html"
```

## 🛠️ Architecture Technique

### Flux
1. Le modèle appelle `web_search(query)` depuis la boucle d'outils (`AIEngine` → `ChatOrchestrator`).
2. `clean_query()` prépare **sa** requête : première ligne seulement, sans « cherche sur internet », sans les années récentes que le modèle ajoute de lui-même (2024, 2025… : il ne connaît pas la date du jour) quand l'utilisateur ne les a pas écrites. Une année ancienne (« construction tour Eiffel 1889 ») ou donnée par l'utilisateur reste.
3. `search_and_summarize()` : URL → lecture directe ; météo → Open-Meteo ; sinon moteurs puis lecture des pages.
4. Le résultat revient au modèle. Quand il est assez fourni, l'orchestrateur passe directement à la synthèse streamée.

Les autres chemins utilisent le même moteur : `CustomAIModel` (`models/mixins/internet_search.py`, qui ajoute lui-même le bloc de sources numérotées sous la réponse) et l'agent de recherche web de la page Agents (`models/ai_agents.py`).

### Module `models/internet_search.py`

| Élément | Rôle |
|---------|------|
| `EnhancedInternetSearchEngine` (alias `InternetSearchEngine`) | `search_and_summarize(query)` (texte pour le modèle, ne lève jamais d'exception), `search(query)` (résultats structurés), `summarize_url(url)` ; `search_best_source_context` est le même que `search_and_summarize` |
| `search_engines(query)` | DuckDuckGo → Yahoo → Wikipédia, pauses partagées par toutes les instances |
| `read_pages(results, query)` | Lecture parallèle des pages, une session HTTP par thread |
| `page_blocks(html)` / `select_passages(blocks, terms, budget)` | Texte principal de la page / passages transmis au modèle |
| `weather(query)` | Météo Open-Meteo, ou `None` pour laisser la recherche web répondre |
| `clean_query(query, user_message)` | Requête du modèle prête pour le moteur |
| `reset_state()` | Oublie les pauses et le cache |

### Format du résultat de l'outil
```
Résultats de recherche web pour « meilleures marques de voitures classement » (DuckDuckGo, 8 octobre 2026) :

[1] Quelle est la meilleure marque de voiture 2026 - autohero.com
Lien : https://www.autohero.com/fr/conseil/choisir/meilleure-voiture/meilleure-marque-de-voiture/
Extrait : Découvrez notre top 10 des meilleures marques de voitures les plus fiables…
Contenu de la page :
Quelle marque de voiture est la plus fiable en 2026 ?
Voici le classement des marques de voitures les plus fiables :
Toyota : Icône japonaise d'ingéniosité et de robustesse…

[2] …

Pour répondre : appuie-toi sur ces sources, place le marqueur [n] après chaque information qui en vient, et termine ta réponse par ce bloc, recopié tel quel :

📚 **Sources**
[1] [Quelle est la meilleure marque de voiture 2026 - autohero.com](https://www.autohero.com/fr/conseil/choisir/meilleure-voiture/meilleure-marque-de-voiture/)
[2] …
```

## 📊 Performances

Mesures du 8 octobre 2026 sur le PC de développement :
- Page de résultats DuckDuckGo : ~1 s
- Lecture de 4 pages en parallèle : ~2 s
- Météo (géocodage + prévisions) : ~0,5 s

Le reste du temps de réponse est celui du modèle : choisir l'outil, puis rédiger la synthèse à partir des sources.

## 🐛 Dépannage

### « Aucun résultat trouvé pour … »
Le message donne l'état de chaque moteur :
- `DuckDuckGo bloqué (HTTP 202)` : page anti-robot (trop de recherches depuis cette adresse IP). Pause de 15 minutes, Yahoo prend le relais.
- `… injoignable` : délai dépassé, DNS ou proxy. Vérifiez la connexion et la section `network` de `config.yaml`.
- `Wikipédia sans résultat` : aucun article ne reprend assez de mots de la requête.

Les pauses et le cache s'oublient au redémarrage de l'application (ou avec `models.internet_search.reset_state()`).

### Erreur de certificat (`SSLError`, `CERTIFICATE_VERIFY_FAILED`)
Réseau d'entreprise dont le certificat racine n'est pas dans le magasin du système : indiquez-le dans `network.ca_bundle`. `allow_insecure_ssl: true` en tout dernier recours seulement.

### Alerte de sécurité réseau (« script Python », « reverse SSH »)
L'ancienne recherche (avant octobre 2026) en déclenchait : contournement anti-robot avec `cloudscraper`, User-Agent de navigateur changé à chaque requête par un script Python, vérification des certificats coupée, requêtes en rafale vers des instances SearXNG aux domaines inconnus. La recherche actuelle n'a plus aucun de ces comportements : des requêtes HTTPS vérifiées vers des moteurs courants et les pages de leurs résultats, avec un User-Agent qui dit qui les fait. Si une alerte revient, notez le domaine ou l'adresse IP qu'elle cite.

À savoir aussi : le **Relay mobile**, quand il démarre avec son tunnel, ouvre des tunnels SSH (`ssh -R`) vers `serveo.net` et `localhost.run` ; `relay.tunnel_providers: ["cloudflared"]` les évite.

### Météo absente
Si le lieu est inconnu d'Open-Meteo ou si le service ne répond pas, la recherche web répond à la place (sites météo). Nommez la ville : « météo Toulouse » plutôt que « météo ».

---

**Amusez-vous bien avec la recherche internet ! 🔍✨**
