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

## 1.5. Installation automatique (zéro config)

Par défaut (`image_generation.auto_setup: true`), **rien à installer** : à la
**première** demande d'image, si aucun backend n'est détecté, My_AI télécharge
et lance automatiquement **ComfyUI portable** (Windows) :

1. téléchargement du build **ComfyUI portable** de votre GPU (~1,5–2 Go,
   **Python + torch embarqués** — n'altère **pas** l'environnement Python de
   My_AI) dans `tools/` :

   | GPU détecté | Build | Calcul sur |
   |---|---|---|
   | NVIDIA (séries 20 et plus) | `nvidia` | GPU (CUDA) |
   | AMD (RDNA 2 à 4) | `amd` | GPU (ROCm) |
   | Intel **Arc** (cartes Arc, GPU intégré des Core Ultra) | `intel` | GPU (XPU) |
   | aucun de ceux-là (Intel UHD / Iris Xe, pas de GPU) | `nvidia` | **CPU** |

2. extraction avec **7-Zip** (téléchargé s'il manque) ;
3. téléchargement d'un **modèle par défaut** (SD-Turbo, ~5 Go) ;
4. lancement de ComfyUI en arrière-plan et bascule automatique du backend. S'il
   s'arrête au démarrage sur le GPU (pilote trop ancien, carte non prise en
   charge), il est **relancé sur le CPU**.

Toute la progression (téléchargement %, extraction, démarrage) s'affiche sous la
réponse en cours, avec une **barre de progression**, et le bouton **Arrêter la
réponse** (ou **Échap**) annule l'opération.
ComfyUI reste lancé tant que My_AI est ouvert (réutilisé d'une image à l'autre)
et s'arrête avec l'appli. Sa sortie va dans `logs/comfyui.log` : en cas d'échec,
la réponse cite sa dernière erreur.

> **Ordres de grandeur** (SD-Turbo 512×512, 4 étapes) : ~2 s par image sur le
> GPU intégré Intel Arc 140T, ~30 s sur le CPU (Core Ultra 7 255H). ComfyUI
> démarre en ~20 s et la première image d'une session attend le chargement du
> modèle (~40 s). Le premier lancement après l'installation peut prendre
> quelques minutes (~3 min mesurées) : l'antivirus analyse les DLL de torch à
> leur premier chargement.

> **Build qui ne correspond pas au GPU** (le build NVIDIA, seul installé
> jusqu'ici, sur un PC Intel Arc ou AMD) : il est remplacé par le bon à la
> demande d'image suivante, **modèles gardés**. Si ce remplacement échoue (hors
> ligne…), l'ancien build tourne sur le CPU.

> **Non-Windows** : l'auto-installation du portable n'est pas disponible —
> installez ComfyUI ou Forge manuellement (§3). Pour désactiver
> l'auto-installation : `image_generation.auto_setup: false`.

## 2. Choix du backend

| Backend          | Installation                    | VRAM 6 Go | Vitesse        |
|------------------|---------------------------------|-----------|----------------|
| **automatic1111**| service séparé (comme Ollama)   | `--medvram`, coexiste avec Ollama | GPU rapide |
| **comfyui**      | service séparé                  | très économe | GPU rapide  |
| **diffusers**    | `pip` lourd (torch adapté au GPU) | concurrence Ollama (risque OOM) | dépend du device |
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
  turbo_steps: 4                  # modèle Turbo sous ComfyUI : 1 à 4 étapes, sans CFG
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

Les demandes sont reconnues dans les 12 langues de l'interface : « *generate an
image of an astronaut cat* », « *genera una imagen de…* », « *erstelle ein Bild
von…* », « *猫の画像を生成して* »… ([`core/image_intent.py`](../core/image_intent.py)).
Comme en français, il faut un verbe de création suivi d'un nom d'image :
« *create an image resizer* » reste une demande de code, « *draw me a diagram* »
un schéma.

L'image s'affiche dans la conversation (clic = taille réelle) et est sauvegardée
dans `outputs/img_AAAAMMJJ_HHMMSS_<slug>.png`.

> L'**analyse** d'image (« décris cette image », « analyse cette photo ») reste
> gérée par la vision Ollama et n'est **pas** confondue avec la génération.

> « **Tableau** » seul désigne un tableau de données (« génère un tableau
> excel des ventes ») : la demande part vers la génération de documents ou le
> chat. Il ne vaut peinture qu'avec un style pictural — « un tableau
> impressionniste », « cubiste », « surréaliste », « abstrait », « à l'huile »,
> « à la manière de… » — ou avec « peins-moi ». La même règle s'applique dans
> `core/ai_engine.py` et dans le classifieur de repli
> (`models/linguistic_patterns.py`).

## 6. Support matériel (tous GPU + CPU)

My_AI parle au backend en **HTTP**, il est donc **agnostique au matériel** : les
backends **AUTOMATIC1111/Forge** et **ComfyUI** gèrent eux-mêmes **NVIDIA (CUDA),
AMD (ROCm/DirectML/ZLUDA), Apple Silicon (MPS) et Intel Arc** — installez la
variante adaptée à votre carte, la config My_AI ne change pas.

Le backend **`diffusers`** (en process) détecte automatiquement le meilleur
device, **dans cet ordre** :

| Device détecté | Matériel | dtype |
|---|---|---|
| `cuda` | **NVIDIA** (CUDA) **et AMD** (build torch-ROCm, Linux) | float16 |
| `mps` | **Apple Silicon** M1/M2/M3/M4 (Metal) | float16 |
| `xpu` | **Intel Arc** (oneAPI / IPEX) | float16 |
| DirectML | **Windows** AMD / Intel / NVIDIA (DirectX 12, via `torch-directml`) | float16 |
| `cpu` | **aucun GPU** — repli universel | float32 |

> **Sans GPU** : tout fonctionne sur **CPU** (repli automatique), mais comptez
> **plusieurs minutes par image**. Privilégiez des modèles **« Turbo »**
> (SD-Turbo / SDXL-Turbo, 1–4 steps). Pour les backends HTTP : `--use-cpu all`
> (A1111/Forge) ou `--cpu` (ComfyUI).
>
> Pour **AMD/Intel sous Windows** avec le backend `diffusers`, installez
> `torch-directml` ; pour **AMD sous Linux**, installez un build **torch-ROCm**.
> Le device réellement utilisé est affiché dans la console au chargement.

## 7. Accès mobile & chiffrement (E2EE)

L'image générée transite vers le mobile **chiffrée AES-256-GCM**, dans la même
enveloppe que les pièces jointes : le serveur Relay envoie un événement WS
`ai_image` via `encrypt_json()`, et le client l'affiche en `data:` URI — le PNG
n'apparaît **jamais en clair** sur le réseau ni dans une URL servie.

> Voir `_broadcast_image()` dans [`relay/relay_server.py`](../relay/relay_server.py)
> et `addImageMessage()` dans [`relay/static/app.js`](../relay/static/app.js).

## 8. Dépannage

| Symptôme | Cause probable | Solution |
|----------|----------------|----------|
| « Génération d'image indisponible » | aucun backend joignable | lancer Forge avec `--api`, vérifier `automatic1111_url` |
| « L'installation automatique de ComfyUI a échoué : … » | téléchargement, extraction ou démarrage en échec (cause citée) | lire `logs/comfyui.log` ; pour réinstaller, supprimer `tools/ComfyUI_windows_portable` (le modèle sera retéléchargé) |
| Timeout | image trop lourde / VRAM saturée | réduire `width`/`height`/`steps`, ajouter `--medvram` |
| « Aucun checkpoint trouvé » (ComfyUI) | pas de modèle chargé | placer un checkpoint dans ComfyUI `models/checkpoints/` |
| OOM avec `diffusers` | Ollama + diffusers se partagent 6 Go | préférer le backend HTTP (a1111/comfyui) |
