# 🔌 Intégration MCP (Model Context Protocol)

## 📋 Vue d'Ensemble

My Personal AI intègre désormais le **Model Context Protocol (MCP)**, un standard ouvert qui permet aux modèles d'IA (comme Ollama) d'interagir de manière sécurisée et standardisée avec des outils locaux et des sources de données externes.

Grâce à cette intégration, l'IA n'est plus limitée à ses connaissances internes ou à la recherche web basique. Elle peut désormais :
- Lire et écrire dans votre système de fichiers local.
- Interagir avec des bases de données (SQLite, etc.).
- Exécuter des commandes Git.
- Utiliser n'importe quel serveur MCP compatible.

## 🏗️ Architecture MCP dans My AI

L'intégration repose sur le module `core/mcp_client.py` qui agit comme un pont entre Ollama et les outils/serveurs MCP.

### 1. Outils Locaux (LocalTools)
Ce sont des fonctions Python exécutées directement dans le processus de l'application. Elles encapsulent les capacités de My AI de manière standardisée pour qu'Ollama puisse les appeler de manière autonome.

**Nouvelles capacités phares d'interaction système :**
L'IA a maintenant un accès direct encadré à votre PC pour travailler selon ses plans :
- `write_local_file` : Créé ou écrit dans un fichier sur votre ordinateur.
- `move_local_file` : Renomme ou déplace un fichier (conserve les dossiers parents grâce à Mkdir intégré).
- `create_directory` : Crée de nouveaux dossiers de travail.
- `search_local_files` : Explore la racine de votre PC par glob pattern (ex: `*.py`).
- `read_local_file` : Analyse et relit le contenu de n'importe quel de vos fichiers locaux.
- Et bien d'autres outils (mémoire vectorielle RAG, recherche web via DuckDuckGo, etc.).

### 2. Serveurs MCP Externes (MCPServers)
My AI peut se connecter à des serveurs MCP externes via le transport `stdio`. Cela permet d'étendre les capacités de l'IA de manière infinie en utilisant l'écosystème grandissant des serveurs MCP (ex: serveurs pour GitHub, Slack, bases de données d'entreprise, etc.).

## 🚀 Comment ça marche ?

1. **Découverte** : Au démarrage, le `mcp_client` recense tous les outils locaux disponibles et se connecte aux serveurs MCP externes configurés pour récupérer leurs outils.
2. **Exposition** : Tous ces outils sont convertis au format JSON Schema attendu par l'API d'Ollama.
3. **Décision** : Lors d'une requête utilisateur, la liste des outils est envoyée à Ollama avec le prompt. Ollama décide intelligemment s'il a besoin d'utiliser un outil pour répondre.
4. **Exécution** : Si Ollama décide d'utiliser un outil, le `mcp_client` intercepte l'appel, exécute l'outil local ou transfère la requête au serveur MCP externe, puis renvoie le résultat à Ollama.
5. **Synthèse** : Ollama utilise le résultat de l'outil pour formuler sa réponse finale à l'utilisateur.

## ⚙️ Configuration

*(À venir : La configuration des serveurs MCP externes se fera via le fichier `config.yaml` ou une interface dédiée).*

## 🛠️ Dépendances

L'intégration MCP utilise le SDK officiel `mcp` pour Python.
Si le SDK n'est pas installé, My AI gère la situation de manière gracieuse (dégradation gracieuse) et continue de fonctionner avec ses capacités de base.

Pour installer le SDK MCP :
```bash
pip install mcp
```

## 🌟 Avantages

- **Autonomie** : L'IA décide elle-même quand et comment utiliser les outils.
- **Extensibilité** : Ajout facile de nouvelles capacités via des serveurs MCP standards.
- **Standardisation** : Utilisation d'un protocole ouvert adopté par l'industrie (Anthropic, etc.).
