"""
Moteur d'embeddings de la mémoire vectorielle et du RAG

Modèle par défaut : Granite Embedding 107M multilingue (IBM, Apache 2.0),
réglable par optimization.rag.embedding_model dans config.yaml. Une question en
français retrouve un passage anglais, arabe ou chinois, là où all-MiniLM-L6-v2,
entraîné pour l'anglais, échouait : rappel des 3 bons passages 0,76 contre 0,28
sur la documentation de My_AI (29 questions en 9 langues), à vitesse égale.
C'est aussi le modèle de la sélection des passages des longs documents
(core/passage_embeddings.py) : une seule instance chargée pour les deux.

Le moteur garde l'interface encode() de sentence-transformers, celle des appels
existants, et ajoute encode_query() et encode_document() : un modèle qui
distingue la question du passage (« prompts » de sa configuration) les
applique ; pour Granite et MiniLM, c'est le même calcul.

Repli : si le modèle choisi manque, MiniLM (s'il est en cache) le remplace pour
la session, et le modèle choisi est téléchargé en arrière-plan pour le lancement
suivant. Au tout premier lancement (rien en cache), le modèle choisi est
téléchargé directement.

Chaque modèle a ses collections ChromaDB (collection_name) : deux modèles ne
partagent jamais un index, même à dimension égale, car leurs vecteurs ne sont
pas comparables. memory/embedding_reindex.py recalcule l'ancien index avec le
nouveau modèle.
"""

# Imports différés : le module reste importable sans sentence-transformers ni
# huggingface_hub (aucun moteur n'est alors disponible)
# pylint: disable=import-outside-toplevel

import fnmatch
import hashlib
import os
import re
import threading
from typing import Any, Dict, List, Optional

from core import passage_embeddings

DEFAULT_MODEL = passage_embeddings.MODEL_ID
FALLBACK_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# Nom court accepté par sentence-transformers pour le même modèle
_FALLBACK_NAMES = {FALLBACK_MODEL, "all-MiniLM-L6-v2"}

# Distance cosinus au-delà de laquelle la recherche des conversations écarte un
# message, quand aucun score de reranker ne sert de seuil. Granite : mesurée au
# lot 5 bis (18 questions en 9 langues sur 36 messages : 17 trouvées et aucun
# résultat pour 10 questions hors sujet à 0,32 ; tout passe à 0,55). MiniLM,
# et tout modèle non mesuré : 0,55, l'ancien seuil.
_MAX_DISTANCE = {DEFAULT_MODEL: 0.32, FALLBACK_MODEL: 0.55}
_DEFAULT_MAX_DISTANCE = 0.55

# Fichiers inutiles à sentence-transformers (PyTorch) : le dépôt de MiniLM, par
# exemple, pèse près de 1 Go avec ses variantes ONNX et OpenVINO
_IGNORED_FILES = [
    "onnx/*", "openvino/*", "*.onnx", "*.h5", "*.msgpack", "*.ot", "*.tflite",
    "coreml/*", "*.mlmodel", "*.py", ".gitattributes",
]

_engines: Dict[str, "EmbeddingEngine"] = {}
_engines_lock = threading.Lock()


class EmbeddingEngine:
    """
    Modèle d'embeddings partagé, utilisable depuis plusieurs threads

    Les calculs sont sérialisés : le tokenizer rapide de Hugging Face refuse
    deux appels simultanés (« Already borrowed »), et la réindexation encode en
    arrière-plan pendant que l'utilisateur cherche.
    """

    def __init__(self, model: Any, model_id: str, revision: Optional[str] = None):
        """
        Args:
            model: Modèle sentence-transformers chargé
            model_id: Nom du modèle (dépôt Hugging Face ou dossier)
            revision: Version figée du modèle, s'il y en a une
        """
        self.model = model
        self.model_id = model_id
        self.revision = revision
        # Vrai quand ce modèle remplace pour la session celui de config.yaml
        self.fallback = False
        self._lock = threading.Lock()
        self.dimension = _dimension_of(model)

    @property
    def key(self) -> str:
        """Identité du modèle, version comprise quand elle est figée."""
        return f"{self.model_id}@{self.revision}" if self.revision else self.model_id

    @property
    def name(self) -> str:
        """Nom court pour les messages."""
        return _short_name(self.model_id)

    def encode(self, sentences, **kwargs):
        """encode() de sentence-transformers, sans barre de progression par défaut."""
        return self._run("encode", sentences, kwargs)

    def encode_query(self, sentences, **kwargs):
        """Vecteurs de questions (prompt « query » du modèle s'il en a un)."""
        return self._run("encode_query", sentences, kwargs)

    def encode_document(self, sentences, **kwargs):
        """Vecteurs de passages à retrouver (prompt « document » s'il y en a un)."""
        return self._run("encode_document", sentences, kwargs)

    def get_sentence_embedding_dimension(self) -> int:
        """Dimension des vecteurs, comme le modèle sentence-transformers."""
        return self.dimension

    def _run(self, method: str, sentences, kwargs: Dict[str, Any]):
        kwargs.setdefault("show_progress_bar", False)
        # encode_query et encode_document datent de sentence-transformers 5
        call = getattr(self.model, method, None) or self.model.encode
        with self._lock:
            return call(sentences, **kwargs)


def encode_documents(model: Any, sentences):
    """
    Vecteurs de passages avec n'importe quel modèle à encode()

    Args:
        model: EmbeddingEngine, modèle sentence-transformers ou objet de test
        sentences: Texte ou liste de textes

    Returns:
        Ce que renvoie encode_document (encode si le modèle n'en a pas)
    """
    call = getattr(model, "encode_document", None) or model.encode
    return call(sentences)


def encode_queries(model: Any, sentences):
    """Vecteurs de questions avec n'importe quel modèle à encode()."""
    call = getattr(model, "encode_query", None) or model.encode
    return call(sentences)


def configured_model() -> str:
    """Modèle choisi dans config.yaml (optimization.rag.embedding_model)."""
    try:
        from core.config import get_config

        value = get_config().get("optimization.rag.embedding_model", DEFAULT_MODEL)
    except Exception:
        value = DEFAULT_MODEL
    return str(value or "").strip() or DEFAULT_MODEL


def is_fallback_model(model_id: str) -> bool:
    """Vrai pour all-MiniLM-L6-v2, le modèle historique et de repli."""
    return model_id in _FALLBACK_NAMES


def revision_of(model_id: str) -> Optional[str]:
    """Version figée d'un modèle connu (Granite), None pour les autres."""
    return passage_embeddings.REVISION if model_id == passage_embeddings.MODEL_ID else None


def max_distance_for(model_id: Optional[str]) -> float:
    """
    Distance cosinus maximale d'un résultat pertinent avec ce modèle

    Seuil de la recherche des conversations quand aucun score de reranker ne
    sert de filtre ; search.max_distance de config.yaml le remplace.
    """
    if model_id and is_fallback_model(model_id):
        model_id = FALLBACK_MODEL
    return _MAX_DISTANCE.get(model_id or "", _DEFAULT_MAX_DISTANCE)


def collection_name(base: str, model_id: str, dimension: int,
                    revision: Optional[str] = None) -> str:
    """
    Nom de la collection ChromaDB d'un modèle

    MiniLM garde les noms historiques (« documents », « conversations »,
    « codebase ») : un repli sur MiniLM retrouve l'index existant sans rien
    recalculer. Les autres modèles ont base__<nom>-<empreinte>__<dimension>,
    l'empreinte distinguant deux modèles de même nom ou deux versions.

    Args:
        base: Nom historique de la collection
        model_id: Modèle des vecteurs
        dimension: Dimension des vecteurs
        revision: Version figée du modèle

    Returns:
        Nom de la collection
    """
    if is_fallback_model(model_id):
        return base
    slug = re.sub(r"[^a-z0-9]+", "-", _short_name(model_id).lower()).strip("-")[:32].strip("-")
    key = f"{model_id}@{revision}" if revision else model_id
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]
    return f"{base}__{slug or 'model'}-{digest}__{int(dimension)}"


def belongs_to(name: str, base: str) -> bool:
    """Vrai si la collection `name` est une collection `base`, quel que soit son modèle."""
    return name == base or name.startswith(base + "__")


def local_path(model_id: str) -> Optional[str]:
    """Dossier du modèle s'il est utilisable sans réseau, None sinon."""
    if os.path.isdir(model_id):
        return model_id
    try:
        if model_id == passage_embeddings.MODEL_ID:
            if not passage_embeddings.is_downloaded():
                return None
            from huggingface_hub import try_to_load_from_cache

            # Seulement les fichiers de la version figée : pas de refs/main
            modules = try_to_load_from_cache(model_id, "modules.json", revision=revision_of(model_id))
            return os.path.dirname(modules) if isinstance(modules, str) else None
        from huggingface_hub import snapshot_download

        return snapshot_download(_hub_id(model_id), local_files_only=True)
    except Exception:
        return None


def download(model_id: str) -> bool:
    """
    Télécharge un modèle d'embeddings (premier lancement ou arrière-plan)

    Returns:
        True si le modèle est disponible
    """
    if model_id == passage_embeddings.MODEL_ID:
        return passage_embeddings.download()
    if os.path.isdir(model_id):
        return True
    print(f"📥 Téléchargement du modèle d'embeddings {model_id}... (une seule fois)")
    try:
        fetch_files(_hub_id(model_id))
    except Exception as exc:
        print(f"⚠️ Modèle d'embeddings {model_id} non téléchargé : {exc}")
        _print_network_help(exc)
        return False
    print(f"✅ Modèle d'embeddings {model_id} prêt")
    return True


def fetch_files(repo_id: str, revision: Optional[str] = None) -> List[str]:
    """
    Télécharge les fichiers utiles d'un dépôt du Hub, un à la fois

    Dans le thread appelant, sans snapshot_download : son pool de threads échoue
    sous Windows sans droit de lien symbolique (WinError 1314) et retient la
    fermeture de l'appli. Les poids PyTorch en double (.bin à côté d'un
    .safetensors) et les variantes ONNX, OpenVINO, TensorFlow... sont sautés.

    Returns:
        Les fichiers téléchargés (ou déjà en cache)
    """
    from huggingface_hub import HfApi, hf_hub_download

    names = HfApi().list_repo_files(repo_id, revision=revision)
    has_safetensors = any(name.endswith(".safetensors") for name in names)
    wanted = [
        name for name in names
        if not any(fnmatch.fnmatch(name, pattern) for pattern in _IGNORED_FILES)
        and not (has_safetensors and name.endswith(".bin") and "/" not in name)
    ]
    for name in wanted:
        hf_hub_download(repo_id, name, revision=revision)
    return wanted


def download_in_background(model_id: str) -> Optional[threading.Thread]:
    """Télécharge le modèle dans un thread, pour le lancement suivant."""
    if model_id == passage_embeddings.MODEL_ID:
        # Même téléchargement que celui des longs documents, jamais deux à la fois
        return passage_embeddings.prefetch_in_background()
    thread = threading.Thread(
        target=download, args=(model_id,), name="embedding-model-download", daemon=True
    )
    thread.start()
    return thread


def engine_for(model_id: str) -> Optional[EmbeddingEngine]:
    """
    Moteur d'un modèle déjà téléchargé, chargé une seule fois par processus

    Returns:
        Le moteur, ou None si le modèle manque ou ne se charge pas
    """
    if is_fallback_model(model_id):
        model_id = FALLBACK_MODEL
    revision = revision_of(model_id)
    key = f"{model_id}@{revision}" if revision else model_id
    with _engines_lock:
        engine = _engines.get(key)
        if engine is None:
            path = local_path(model_id)
            if path is None:
                return None
            try:
                from sentence_transformers import SentenceTransformer

                engine = EmbeddingEngine(SentenceTransformer(path), model_id, revision)
            except Exception as exc:
                print(f"⚠️ Modèle d'embeddings {_short_name(model_id)} inutilisable : {exc}")
                return None
            _engines[key] = engine
        return engine


def load_engine(model_id: Optional[str] = None) -> Optional[EmbeddingEngine]:
    """
    Moteur de la mémoire et du RAG, avec repli sur MiniLM

    1. Le modèle choisi, s'il est en cache.
    2. Sinon MiniLM, s'il est en cache, pour cette session ; le modèle choisi
       se télécharge en arrière-plan et sert dès le lancement suivant.
    3. Sinon (premier lancement), téléchargement du modèle choisi, puis de
       MiniLM si le premier échoue.

    Args:
        model_id: Modèle voulu (celui de config.yaml par défaut)

    Returns:
        Le moteur, ou None si aucun modèle n'est utilisable
    """
    wanted = model_id or configured_model()
    engine = engine_for(wanted)
    if engine is not None:
        engine.fallback = False
        print(f"✅ Modèle d'embeddings chargé depuis le cache ({engine.name})")
        return engine
    if not is_fallback_model(wanted):
        engine = engine_for(FALLBACK_MODEL)
        if engine is not None:
            engine.fallback = True
            print(
                f"⚠️ Modèle d'embeddings {_short_name(wanted)} indisponible : "
                "MiniLM le remplace pour cette session (index MiniLM) ; "
                "téléchargé en arrière-plan s'il manque, utilisé au prochain lancement"
            )
            download_in_background(wanted)
            return engine
    print("📥 Premier lancement détecté - Téléchargement du modèle d'embeddings... "
          "(Cela peut prendre plusieurs minutes)")
    for candidate in dict.fromkeys((wanted, FALLBACK_MODEL)):
        if download(candidate):
            engine = engine_for(candidate)
            if engine is not None:
                engine.fallback = candidate != wanted and not is_fallback_model(wanted)
                print(f"✅ Modèle d'embeddings prêt ({engine.name})")
                return engine
    print("   Vérifiez votre connexion internet et réessayez.")
    return None


def _dimension_of(model: Any) -> int:
    # get_embedding_dimension depuis sentence-transformers 5.7, l'ancien nom avant
    for getter in ("get_embedding_dimension", "get_sentence_embedding_dimension"):
        method = getattr(model, getter, None)
        if callable(method):
            try:
                value = method()
                if value:
                    return int(value)
            except Exception:
                pass
    try:
        return len(model.encode("dimension", show_progress_bar=False))
    except Exception:
        return 0


def _short_name(model_id: str) -> str:
    return model_id.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1] or model_id


def _hub_id(model_id: str) -> str:
    """Nom complet sur le Hub (« all-MiniLM-L6-v2 » → sentence-transformers/...)."""
    return model_id if "/" in model_id else f"sentence-transformers/{model_id}"


def _print_network_help(exc: Exception) -> None:
    try:
        from core.network import build_network_error_help

        help_msg = build_network_error_help(exc)
        if help_msg:
            print(help_msg)
    except Exception:
        pass
