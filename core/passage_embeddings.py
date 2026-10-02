"""
Modèle d'embeddings multilingue de la sélection des passages

Granite Embedding 107M multilingue (IBM, licence Apache 2.0, 228 Mo) compare le
sens de la question à celui des passages d'un long document : une question en
français trouve un passage en anglais (« gants » → « gloves »).

Le modèle est téléchargé une seule fois, en arrière-plan, au lancement de l'app
(prefetch_in_background), puis chargé au premier long document. Tant qu'il
manque, les passages sont choisis par mots-clés seulement.
Désactivation : optimization.rag.multilingual_passages: false dans config.yaml.
"""

# Imports différés : le module reste importable sans huggingface_hub ni
# sentence-transformers (le modèle est alors simplement indisponible)
# pylint: disable=import-outside-toplevel

import os
import threading
import warnings
from collections import OrderedDict
from typing import List, Optional

MODEL_ID = "ibm-granite/granite-embedding-107m-multilingual"
# Version figée : une mise à jour du dépôt ne change pas les classements en silence
REVISION = "d6cffd338414d6a1c1f5decfad5fec62eebc90d5"
# Fichiers lus par sentence-transformers ; le dépôt contient aussi des variantes
# ONNX et PyTorch inutiles ici
MODEL_FILES = (
    "1_Pooling/config.json",
    "config.json",
    "model.safetensors",
    "modules.json",
    "sentence_bert_config.json",
    "sentencepiece.bpe.model",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
)

# Vecteurs de passages gardés en mémoire (≈ 6 Mo) : les questions suivantes sur
# le même document ne réencodent rien
_CACHE_SIZE = 4096

# Avertissement bénin sous Windows sans droit de lien symbolique (fichiers copiés)
warnings.filterwarnings("ignore", message=".*cache-system uses symlinks.*")

_lock = threading.Lock()
_model = None
_unusable = False
_vectors: "OrderedDict[str, object]" = OrderedDict()


def enabled() -> bool:
    """
    Indique si la sélection multilingue est activée dans la configuration
    """
    try:
        from core.config import get_config

        return bool(get_config().get("optimization.rag.multilingual_passages", True))
    except Exception:
        return True


def is_downloaded() -> bool:
    """
    Indique si tous les fichiers du modèle sont dans le cache Hugging Face
    """
    try:
        from huggingface_hub import try_to_load_from_cache
    except ImportError:
        return False
    return all(
        isinstance(try_to_load_from_cache(MODEL_ID, name, revision=REVISION), str)
        for name in MODEL_FILES
    )


def ensure_downloaded() -> bool:
    """
    Télécharge le modèle s'il manque (reprend un téléchargement interrompu)

    Returns:
        True si le modèle est disponible
    """
    if not enabled():
        return False
    if is_downloaded():
        return True
    print("📥 Téléchargement du modèle multilingue des longs documents (228 Mo, une seule fois)...")
    try:
        from huggingface_hub import hf_hub_download

        # Un fichier à la fois, dans le thread appelant (pas de pool comme
        # snapshot_download) : fermer l'app n'attend pas la fin du téléchargement,
        # repris au lancement suivant, et sous Windows sans droit de lien
        # symbolique les téléchargements parallèles échouent (WinError 1314)
        for name in MODEL_FILES:
            hf_hub_download(MODEL_ID, name, revision=REVISION)
    except Exception as exc:
        print(f"⚠️ Modèle multilingue non téléchargé : {exc}")
        try:
            from core.network import build_network_error_help

            help_msg = build_network_error_help(exc)
            if help_msg:
                print(help_msg)
        except Exception:
            pass
        print(
            "   Passages des longs documents choisis par mots-clés ; "
            "nouvel essai au prochain lancement."
        )
        return False
    print("✅ Modèle multilingue prêt")
    return True


def prefetch_in_background() -> Optional[threading.Thread]:
    """
    Lance le téléchargement du modèle dans un thread s'il manque

    Returns:
        Le thread lancé, ou None si rien n'est à télécharger
    """
    if not enabled() or is_downloaded():
        return None
    thread = threading.Thread(target=ensure_downloaded, name="passage-model-download", daemon=True)
    thread.start()
    return thread


def similarities(query: str, passages: List[str]) -> Optional[List[float]]:
    """
    Similarité de sens entre la question et chaque passage

    Args:
        query: Question de l'utilisateur
        passages: Passages du document

    Returns:
        Similarité cosinus de chaque passage, ou None si le modèle n'est pas
        disponible (pas encore téléchargé, désactivé ou inutilisable)
    """
    with _lock:
        model = _loaded_model()
        if model is None:
            return None
        try:
            new = [passage for passage in dict.fromkeys(passages) if passage not in _vectors]
            if new:
                vectors = model.encode(new, normalize_embeddings=True, show_progress_bar=False)
                _vectors.update(zip(new, vectors))
            asked = model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
            scores = [float(_vectors[passage] @ asked) for passage in passages]
        except Exception as exc:
            print(f"⚠️ Sélection multilingue des passages impossible : {exc}")
            return None
        for passage in passages:
            _vectors.move_to_end(passage)
        while len(_vectors) > _CACHE_SIZE:
            _vectors.popitem(last=False)
        return scores


def _loaded_model():
    """Modèle chargé au premier usage (≈ 1 s, ≈ 430 Mo de RAM) ; appelé sous _lock."""
    global _model, _unusable  # pylint: disable=global-statement
    if _model is None and not _unusable and enabled() and is_downloaded():
        try:
            from huggingface_hub import try_to_load_from_cache
            from sentence_transformers import SentenceTransformer

            modules = try_to_load_from_cache(MODEL_ID, "modules.json", revision=REVISION)
            _model = SentenceTransformer(os.path.dirname(modules))
        except Exception as exc:
            _unusable = True
            print(f"⚠️ Modèle multilingue inutilisable ({exc}) : passages choisis par mots-clés")
    return _model
