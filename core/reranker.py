"""
Reranker de la mémoire vectorielle et du RAG

Le CrossEncoder relit la question avec chaque passage candidat et les remet dans
l'ordre. ms-marco-MiniLM-L-6-v2, entraîné pour l'anglais, défaisait le gain de
Granite (multilingue) : sur la doc de My_AI (35 questions en 10 langues), les 3
passages retenus contenaient la réponse 60 % du temps après lui, 77 % avec
Granite seul, 86 % après mmarco-mMiniLMv2 (multilingue, 14 langues, Apache 2.0).

Choix : optimization.rag.reranker_model dans config.yaml
- "auto" (défaut) : mmarco-mMiniLMv2 avec un modèle d'embeddings multilingue
  (Granite), ms-marco avec MiniLM (index anglais, ou repli) ;
- "none" : pas de reranking, ordre du modèle d'embeddings ;
- le nom d'un CrossEncoder du Hub Hugging Face.

mmarco (470 Mo) se télécharge une seule fois, en arrière-plan, fichier par
fichier ; en attendant, la recherche garde l'ordre de Granite.

Ses scores servent à trier, pas à filtrer : leur échelle change d'une question
à l'autre. La recherche des conversations filtre alors par distance (seuil
propre au modèle d'embeddings, core.embedding_engine.max_distance_for) ; seul
ms-marco garde son seuil de score historique (search.min_rerank_score).
"""

# Imports différés : le module reste importable sans huggingface_hub
# pylint: disable=import-outside-toplevel

import os
import threading
from typing import Any, Dict, Optional

from core.embedding_engine import is_fallback_model

MULTILINGUAL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
ENGLISH = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Rerankers téléchargés par My_AI à une version figée : une mise à jour du dépôt
# ne change pas les classements en silence. Seulement les fichiers lus par
# sentence-transformers (le dépôt contient aussi des variantes ONNX et OpenVINO).
_PINNED: Dict[str, Dict[str, Any]] = {
    MULTILINGUAL: {
        "revision": "1427fd652930e4ba29e8149678df786c240d8825",
        "files": (
            "config.json",
            "model.safetensors",
            "sentencepiece.bpe.model",
            "special_tokens_map.json",
            "tokenizer.json",
            "tokenizer_config.json",
        ),
        "size": "470 Mo",
    },
}

# Rerankers dont le score sert de seuil de pertinence (recherche des conversations)
_SCORE_FILTERS = {ENGLISH}

_downloads: Dict[str, threading.Thread] = {}
_downloads_lock = threading.Lock()


def configured() -> str:
    """Réglage optimization.rag.reranker_model de config.yaml ("auto" par défaut)."""
    try:
        from core.config import get_config

        value = get_config().get("optimization.rag.reranker_model", "auto")
    except Exception:
        value = "auto"
    if value is False or value is None:
        return "none"
    return str(value).strip() or "none"


def choose(engine: Any) -> Optional[str]:
    """
    Reranker à utiliser avec ce moteur d'embeddings

    Args:
        engine: Moteur d'embeddings de la mémoire (core.embedding_engine), ou None

    Returns:
        Le nom du CrossEncoder, ou None pour ne pas reranker
    """
    value = configured()
    if value.lower() in ("none", "false", "off", "aucun"):
        return None
    if value.lower() != "auto":
        return value
    model_id = getattr(engine, "model_id", None)
    if not model_id or is_fallback_model(model_id):
        return ENGLISH
    return MULTILINGUAL


def filters_by_score(model: Optional[str]) -> bool:
    """Vrai si le score de ce reranker sert de seuil de pertinence."""
    return model in _SCORE_FILTERS


def is_pinned(model: Optional[str]) -> bool:
    """Vrai pour un reranker que My_AI télécharge lui-même, à une version figée."""
    return model in _PINNED


def local_path(model: str) -> Optional[str]:
    """Dossier d'un reranker figé s'il est complet dans le cache, None sinon."""
    pinned = _PINNED.get(model)
    if pinned is None:
        return None
    try:
        from huggingface_hub import try_to_load_from_cache
    except ImportError:
        return None
    paths = [try_to_load_from_cache(model, name, revision=pinned["revision"]) for name in pinned["files"]]
    if not all(isinstance(path, str) for path in paths):
        return None
    return os.path.dirname(paths[0])


def download(model: str) -> bool:
    """
    Télécharge un reranker figé (reprend un téléchargement interrompu)

    Un fichier à la fois, dans le thread appelant : snapshot_download passe par
    un pool de threads qui échoue sous Windows sans droit de lien symbolique
    (WinError 1314) et retient la fermeture de l'appli.

    Returns:
        True si le reranker est disponible
    """
    pinned = _PINNED.get(model)
    if pinned is None:
        return False
    name = model.rsplit("/", 1)[-1]
    print(f"📥 Téléchargement du reranker multilingue {name} ({pinned['size']}, une seule fois)...")
    try:
        from huggingface_hub import hf_hub_download

        for filename in pinned["files"]:
            hf_hub_download(model, filename, revision=pinned["revision"])
    except Exception as exc:
        print(f"⚠️ Reranker {name} non téléchargé : {exc}")
        try:
            from core.network import build_network_error_help

            help_msg = build_network_error_help(exc)
            if help_msg:
                print(help_msg)
        except Exception:
            pass
        print("   Passages triés par le modèle d'embeddings ; nouvel essai au prochain lancement.")
        return False
    print(f"✅ Reranker {name} prêt (utilisé au prochain lancement)")
    return True


def download_in_background(model: str) -> Optional[threading.Thread]:
    """
    Lance le téléchargement d'un reranker figé dans un thread, une fois par processus

    Returns:
        Le thread (lancé ou déjà en cours), None si rien n'est à télécharger
    """
    if not is_pinned(model):
        return None
    with _downloads_lock:
        thread = _downloads.get(model)
        if thread is None:
            thread = threading.Thread(
                target=download, args=(model,), name="reranker-download", daemon=True
            )
            _downloads[model] = thread
            thread.start()
        return thread
