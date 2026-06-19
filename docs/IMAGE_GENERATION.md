# 🎨 Génération d'images locale (texte → image)

My_AI gère l'**entrée vision** depuis longtemps (décrire une image via Ollama
`minicpm-v`/`llava`). Ce module ajoute la **sortie image** : demandez une image,
l'IA la génère, l'affiche dans le chat (desktop **et** mobile) et la sauvegarde
dans `outputs/`. **100% local, hors-ligne.**

> Code : [`models/image_generation.py`](../models/image_generation.py) ·
> routage : [`core/ai_engine.py`](../core/ai_engine.py) ·
> intention : [`models/linguistic_patterns.py`](../models/linguistic_patterns.py)

---

## 1. Comment ça marche

L'architecture est **calquée sur le pattern Ollama de `LocalLLM`** : au lieu
d'embarquer un modèle lourd dans le process Python, My_AI parle à un **service
Stable Diffusion local en HTTP** (localhost). Avantages :

- **Pas de bloat** des dépendances (les backends HTTP n'utilisent que `requests`).
- **VRAM coordonnée** : le service SD et Ollama tournent séparément ; vous gérez
  la mémoire GPU (ex. `--medvram`) sans qu'ils se marchent dessus en process.
- **Dégradation propre** : si aucun backend n'est joignable, l'IA répond par un
  message clair (comme le fallback Ollama), **jamais un crash**.

```
"génère une image de chat astronaute"
        │
        ▼  détection d'intention (image_generation)
core/ai_engine.py ── process_query_stream ──► ImageGenerator.generate()
        │                                           │ HTTP localhost
        │                                           ▼
        │                                  AUTOMATIC1111 / ComfyUI / diffusers
        ▼                                           │
  on_image(path) ──► bulle desktop + push mobile (chiffré)   outputs/img_*.png
```

## 2. Choix du backend

| Backend          | Installation                    | VRAM 6 Go | Vitesse        |
|------------------|---------------------------------|-----------|----------------|
| **automatic1111**| service séparé (comme Ollama)   | `--medvram`, coexiste avec Ollama | GPU rapide |
| **comfyui**      | service séparé                  | très économe | GPU rapide  |
| **diffusers**    | `pip` lourd + torch CUDA        | concurrence Ollama (risque OOM) | lent sur CPU |
| **auto**         | essaie a1111 → comfyui → diffusers | —      | —              |

**Recommandé : AUTOMATIC1111 / Forge** — même philosophie qu'Ollama, zéro deps
Python supplémentaires.

## 3. Installation du backend recommandé (Forge)

1. Installer **Stable Diffusion WebUI Forge** (fork optimisé d'AUTOMATIC1111,
   idéal pour petite VRAM) : https://github.com/lllyasviel/stable-diffusion-webui-forge
2. Télécharger un **checkpoint** SD 1.5 (léger, ~2 Go) ou SDXL-Turbo et le placer
   dans `models/Stable-diffusion/`.
3. Lancer la WebUI avec l'**API activée** :
   ```bat
   webui-user.bat   REM contenant : set COMMANDLINE_ARGS=--api --medvram
   ```
   Elle écoute par défaut sur `http://127.0.0.1:7860`.
4. C'est tout : My_AI détecte automatiquement le backend au premier message
   « génère une image… ».

> ComfyUI : lancez-le normalement (`http://127.0.0.1:8188`) et mettez
> `backend: comfyui` (ou `auto`) dans la config.

## 4. Configuration (`config.yaml` → `image_generation:`)

```yaml
image_generation:
  enabled: true
  backend: "automatic1111"        # auto | automatic1111 | comfyui | diffusers
  automatic1111_url: "http://127.0.0.1:7860"
  comfyui_url: "http://127.0.0.1:8188"
  width: 512                      # 512x512 adapté à 6 Go VRAM
  height: 512
  steps: 25
  cfg_scale: 7.0
  sampler: "DPM++ 2M Karras"
  negative_prompt: "lowres, bad anatomy, ... blurry"
  diffusers_model: "stabilityai/sd-turbo"   # si backend: diffusers
  timeout: 300
```

## 5. Utilisation

Tapez simplement, dans le chat desktop ou mobile :

- « **génère une image de** chat astronaute, style aquarelle »
- « **dessine-moi** un dragon rouge »
- « **crée un logo** pour ma startup »
- « **crée une illustration de** forêt enchantée »

L'image s'affiche dans la conversation (clic = taille réelle) et est sauvegardée
dans `outputs/img_AAAAMMJJ_HHMMSS_<slug>.png`.

> L'**analyse** d'image (« décris cette image », « analyse cette photo ») reste
> gérée par la vision Ollama et n'est **pas** confondue avec la génération.

## 6. Accès mobile & chiffrement (E2EE)

L'image générée transite vers le mobile **chiffrée AES-256-GCM**, dans la même
enveloppe que les pièces jointes : le serveur Relay envoie un événement WS
`ai_image` via `encrypt_json()`, et le client l'affiche en `data:` URI — le PNG
n'apparaît **jamais en clair** sur le réseau ni dans une URL servie.

> Voir `_broadcast_image()` dans [`relay/relay_server.py`](../relay/relay_server.py)
> et `addImageMessage()` dans [`relay/static/app.js`](../relay/static/app.js).

## 7. Dépannage

| Symptôme | Cause probable | Solution |
|----------|----------------|----------|
| « Génération d'image indisponible » | aucun backend joignable | lancer Forge avec `--api`, vérifier `automatic1111_url` |
| Timeout | image trop lourde / VRAM saturée | réduire `width`/`height`/`steps`, ajouter `--medvram` |
| « Aucun checkpoint trouvé » (ComfyUI) | pas de modèle chargé | placer un checkpoint dans ComfyUI `models/checkpoints/` |
| OOM avec `diffusers` | Ollama + diffusers se partagent 6 Go | préférer le backend HTTP (a1111/comfyui) |
