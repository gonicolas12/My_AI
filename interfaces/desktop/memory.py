"""
Mémoire de la fenêtre (memory_panel.py de Tk)

Faits (base de connaissances SQLite), documents et conversations (ChromaDB),
par le MemoryStore du moteur : pages de 20, recherche, catégorie, ajout d'un
fait, modification du contenu, suppression.

Un message de conversation modifié, ou supprimé « à la source », passe par le
ChatService (change_saved_message) : retrouvé par son texte, il change aussi
dans la conversation ouverte, et une sauvegarde suivante ne le fait pas
réapparaître. La recherche globale réindexe ensuite la session modifiée.

Lister et chercher ne calculent aucun embedding (recherche de texte) ; modifier
un document ou réindexer une session en recalculent, sur le modèle local de
sentence-transformers.

« Ajouter » de l'onglet Documents : les fichiers choisis (ou déposés) sont lus
en arrière-plan, un à la fois, comme une pièce jointe du chat
(core/document_memory.py), puis rangés dans la collection « documents ». Une
image est décrite par le modèle de vision, seul appel à Ollama de la Mémoire.
Les images envoyées dans le chat passent par la même file (le chat les
signale après sa réponse), sans notification, comme les documents joints. La
file part en événements (memory.jobs), chaque fin en notification (ajout à la
main) et en memory.changed : le panneau ouvert se relit.

Un dossier déposé passe par la même file, ses fichiers rangés sous son nom
(« dossier/chemin », métadonnée folder) : l'onglet le montre comme un dossier
à déplier. Un seul bilan à la fin, pas une notification par fichier.

Deux fichiers du même nom restent deux documents, distingués par leur date.
Un fichier ou un dossier remis alors qu'un autre porte son nom : la fenêtre
demande quoi en faire (cf. existing). « Mettre à jour » remplace le plus récent
du même nom (un dossier perd aussi les fichiers qu'il ne contient plus),
« Garder les deux » l'ajoute à côté. L'onglet montre des documents, jamais
leurs morceaux (chunks), qui restent internes.

Aperçu d'un document (clic dans l'onglet) : la copie de son fichier d'origine,
gardée à sa lecture (memory_files.py) et affichée comme une pièce jointe ; à
défaut (document rangé avant, ou par le chat), le texte gardé en mémoire.
"""

import math
import os
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

from core.chat_service import ChatError, display_name, file_type_for
from core.document_memory import (STAGE_READING, DocumentReadError, folder_document_id,
                                  image_document_id, read_document)
from core.i18n import tr
from interfaces.desktop.memory_files import ORIGINALS_DIRNAME, OriginalFiles
from utils.logger import setup_logger

logger = setup_logger("DesktopMemory")

PAGE_SIZE = 20
TABS = ("facts", "document", "conversation")
# Dossier déposé : fichiers au plus (la fenêtre vérifie avant l'envoi)
FOLDER_FILES_MAX = 200
# Son nom, et le chemin d'un fichier dedans (longueurs maximales)
_FOLDER_MAX = 120
_RELATIVE_MAX = 300
# Bilan d'un dossier : fichiers en échec nommés
_FAILED_SHOWN = 3
FACT_CATEGORIES = ("general", "preference", "decision", "person", "procedure", "technical")
# Clé d'un fait ajouté à la main : sa première ligne (Tk)
_KEY_MAX = 80
# Aperçu d'un document sans copie de son fichier : son texte en mémoire, au plus
PREVIEW_TEXT_MAX = 200_000
# Copies des documents retirés ailleurs (pièce jointe oubliée…) : relevées au plus toutes les… (s)
_PRUNE_INTERVAL = 60.0
# Document joint au chat : rangé à l'instant, et non doublon d'un ancien du même nom (s)
_CHAT_DOCUMENT_WINDOW = 180.0


class MemoryPanelError(Exception):
    """Action refusée ou en échec : message affiché."""


def _remove_upload(path: str) -> None:
    """Efface la copie d'un fichier envoyé par un navigateur, et son dossier s'il est vide."""
    try:
        os.remove(path)
        os.rmdir(os.path.dirname(path))
    except OSError:
        pass


def _printable(text: str) -> str:
    """Sans caractères de contrôle (retours à la ligne, tabulations…), espaces aux bords ôtés."""
    return "".join(char for char in str(text or "") if char.isprintable()).strip()


def clean_folder_name(name: str) -> str:
    """Nom d'un dossier déposé, tel qu'affiché : sans séparateur ni caractère de contrôle."""
    cleaned = _printable(str(name or "").replace("/", " ").replace("\\", " "))
    return cleaned[:_FOLDER_MAX].strip() or "folder"


def clean_relative_path(path: str) -> str:
    """Chemin d'un fichier dans un dossier déposé : « a/b/c.py », sans « . » ni « .. ».

    Un simple nom (« dossier/chemin » dans la mémoire) : jamais un chemin
    sur le disque, où chaque fichier envoyé a sa copie à part.
    """
    parts = [_printable(part) for part in str(path or "").replace("\\", "/").split("/")]
    relative = "/".join(part for part in parts if part not in ("", ".", ".."))
    return relative[-_RELATIVE_MAX:]


def _folder_summary(batch: Dict[str, Any]) -> Tuple[str, str]:
    """Niveau et texte du bilan d'un dossier déposé : « 📁 « site » : 2 fichiers
    ajoutés, 1 mis à jour, 3 déjà à jour. », sans les compteurs à zéro."""
    separator = tr("memory.documents.listSeparator")
    parts = [tr(f"memory.documents.folder{kind}", count=batch[key])
             for key, kind in (("added", "Added"), ("updated", "Updated"),
                               ("already", "Unchanged"), ("removed", "Removed"))
             if batch[key]]
    if batch["failed"]:
        names = batch["failed_names"]
        shown = separator.join(names[:_FAILED_SHOWN]) + (
            f"{separator}…" if len(names) > _FAILED_SHOWN else "")
        parts.append(tr("memory.documents.folderFailed", count=batch["failed"], names=shown))
    if batch["failed"]:
        level = "warning"
    elif batch["added"] or batch["updated"] or batch["removed"]:
        level = "success"
    else:
        level = "info"
    return level, tr("memory.documents.folderSummary", name=batch["folder"],
                     parts=separator.join(parts))


class MemoryService:
    """Lecture et modification de la mémoire du moteur."""

    # Image du chat : intervalle de surveillance de la réponse en cours (s)
    CHAT_POLL = 0.5

    def __init__(self, engine: Callable[[], Optional[Any]], chat: Callable[[], Optional[Any]],
                 publish: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
                 file_processor: Any = None):
        """
        Args:
            engine: moteur en cours (None pendant le lancement)
            chat: service de chat (propagation à la source des conversations)
            publish: publie un événement (EventBus.publish) : file des
                documents ajoutés, notifications
            file_processor: utils.file_processor.FileProcessor (lecture des
                documents ajoutés, en repli des processeurs du moteur)
        """
        self._engine = engine
        self._chat = chat
        self._publish_fn = publish
        self._file_processor = file_processor
        # Documents ajoutés pas encore rangés, dans l'ordre : le premier se lit
        self._jobs: List[Dict[str, Any]] = []
        self._jobs_lock = threading.Lock()
        self._worker: Optional[threading.Thread] = None
        # Dossiers déposés en cours : bilan de chacun (ajoutés, déjà là, en échec)
        self._batches: Dict[str, Dict[str, Any]] = {}
        # Dernier relevé des copies de documents retirés ailleurs (time.monotonic)
        self._pruned_at = 0.0

    def _store(self):
        engine = self._engine()
        getter = getattr(engine, "get_memory_store", None)
        store = getter() if callable(getter) else None
        if store is None:
            raise MemoryPanelError(tr("memory.unavailable"))
        return store

    def page(self, tab: str, query: str = "", category: Optional[str] = None,
             page: int = 0) -> Dict[str, Any]:
        """Une page d'un onglet : éléments, total filtré, nombre de pages, compteurs."""
        if tab not in TABS:
            raise MemoryPanelError(tr("memory.unknownTab", tab=tab))
        store = self._store()
        query = (query or "").strip()
        page = max(0, int(page))
        offset = page * PAGE_SIZE
        # Onglet Documents : un élément par document ou dossier déposé ; leurs
        # morceaux (chunks) restent internes
        grouped = tab == "document" and hasattr(store, "list_document_groups")
        if tab == "facts":
            items, total = store.list_facts(query=query, category=category or None,
                                            limit=PAGE_SIZE, offset=offset)
        elif grouped:
            items, total = store.list_document_groups(query=query, limit=PAGE_SIZE,
                                                      offset=offset)
        else:
            items, total = store.list_vectors(collection_type=tab, query=query,
                                              limit=PAGE_SIZE, offset=offset)
        pages = max(1, math.ceil(total / PAGE_SIZE))
        # Page au-delà de la fin (après une suppression) : la dernière (Tk)
        if page >= pages and total:
            return self.page(tab, query, category, pages - 1)
        if grouped and time.monotonic() - self._pruned_at > _PRUNE_INTERVAL:
            self._prune_originals()
        return {
            "items": items if grouped else [self._view(store, item) for item in items],
            "total": total, "page": page, "pages": pages,
            "stats": store.stats(), "categories": list(FACT_CATEGORIES),
            "jobs": self.jobs(),
        }

    def existing(self, names: List[str], folders: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Fichiers (par leur nom) et dossiers déjà dans l'onglet Documents.

        Avant d'envoyer un fichier ou un dossier, la fenêtre demande quoi faire
        de ceux qui y sont déjà : le mettre à jour (remplacer le plus récent du
        même nom, sa « cible »), garder les deux, ou ne pas l'envoyer. Un
        fichier d'un dossier déposé ne compte pas : « rapport.pdf » seul et
        « projet/rapport.pdf » sont deux documents différents.

        Args:
            names: noms des fichiers (un chemin vaut son nom)
            folders: noms des dossiers déposés

        Returns:
            {"files": [...], "folders": [...]}, chacun {"name" (tel qu'envoyé),
            "target" (clé du plus récent), "created" (sa date), "count" (combien
            portent ce nom)}
        """
        files_by_name: Dict[str, List[Dict[str, Any]]] = {}
        folders_by_name: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for doc in self._store().document_index():
            if doc.get("folder_key"):
                instances = folders_by_name.setdefault(doc["folder"], {})
                known = instances.get(doc["folder_key"])
                if known is None or doc["created"] > known["created"]:
                    instances[doc["folder_key"]] = {"target": doc["folder_key"],
                                                    "created": doc["created"]}
            else:
                files_by_name.setdefault(doc["name"], []).append(
                    {"target": doc["id"], "created": doc["created"]})

        def found(name: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
            newest = max(candidates, key=lambda item: item["created"])
            return {"name": name, **newest, "count": len(candidates)}

        files = [found(name, files_by_name[PureWindowsPath(name).name])
                 for name in dict.fromkeys(str(name) for name in names or [])
                 if PureWindowsPath(name).name in files_by_name]
        found_folders = [found(name, list(folders_by_name[clean_folder_name(name)].values()))
                         for name in dict.fromkeys(str(name) for name in folders or [])
                         if clean_folder_name(name) in folders_by_name]
        return {"files": files, "folders": found_folders}

    def delete_document(self, document_id: str) -> int:
        """Supprime un document entier, et la copie de son fichier ; le nombre de
        morceaux supprimés."""
        removed = self._store().delete_document(str(document_id))
        if not removed:
            raise MemoryPanelError(tr("memory.deleteFailed"))
        originals = self._originals()
        if originals is not None:
            originals.forget([str(document_id)])
        return removed

    def delete_folder(self, key: str) -> int:
        """Supprime un dossier déposé et tous ses documents (par sa clé : un autre
        dossier du même nom reste), et les copies de leurs fichiers."""
        store = self._store()
        documents = [doc["id"] for doc in store.document_index()
                     if doc.get("folder_key") == str(key)]
        removed = store.delete_folder(str(key))
        if not removed:
            raise MemoryPanelError(tr("memory.deleteFailed"))
        originals = self._originals()
        if originals is not None:
            originals.forget(documents)
        return removed

    # ── Aperçu d'un document ────────────────────────────────────────────────

    def _originals(self) -> Optional[OriginalFiles]:
        """Copies des fichiers d'origine, à côté de la base vectorielle ; None sans
        mémoire, ou si elle est chiffrée (une copie en clair la contournerait)."""
        try:
            store = self._store()
        except MemoryPanelError:
            return None
        vector_memory = getattr(store, "vector_memory", None)
        folder = getattr(vector_memory, "storage_dir", None)
        if folder is None or getattr(vector_memory, "enable_encryption", False):
            return None
        return OriginalFiles(Path(os.path.abspath(str(folder))) / ORIGINALS_DIRNAME)

    def originals_root(self) -> Optional[str]:
        """Dossier des copies, que la fenêtre peut afficher (liens signés)."""
        originals = self._originals()
        return str(originals.root) if originals is not None else None

    def _prune_originals(self) -> None:
        """Supprime les copies des documents retirés de la mémoire ailleurs que par
        l'onglet (pièce jointe oubliée, version remplacée, dossier mis à jour)."""
        self._pruned_at = time.monotonic()
        originals = self._originals()
        if originals is None or not originals.root.is_dir():
            return

        def documents() -> List[str]:
            try:
                return [doc["id"] for doc in self._store().document_index()]
            except MemoryPanelError:
                return []

        originals.prune(documents)

    def preview(self, document_id: str) -> Dict[str, Any]:
        """Aperçu d'un document de l'onglet : la copie de son fichier d'origine
        (« path », affichée comme une pièce jointe), sinon son texte en mémoire.

        Returns:
            {"id", "name", "label", "folder", "type", "created", "path", "size",
            "text", "truncated"} ; « text » vaut None quand « path » est là

        Raises:
            MemoryPanelError: document absent de la mémoire
        """
        store = self._store()
        document_id = str(document_id or "")
        doc = next((item for item in store.document_index() if item["id"] == document_id),
                   None)
        if doc is None:
            raise MemoryPanelError(tr("memory.documentGone"))
        originals = self._originals()
        path = originals.find(document_id) if originals is not None else None
        view: Dict[str, Any] = {
            "id": doc["id"], "name": doc["name"], "label": doc["label"],
            "folder": doc.get("folder"), "type": doc.get("type"), "created": doc["created"],
            "path": path, "size": None, "text": None, "truncated": False,
        }
        if path is not None:
            try:
                view["size"] = os.path.getsize(path)
            except OSError:
                view["path"] = path = None
        if path is None:
            text = store.document_text(document_id)
            view["text"] = text[:PREVIEW_TEXT_MAX]
            view["truncated"] = len(text) > PREVIEW_TEXT_MAX
        return view

    @staticmethod
    def _view(store, item: Dict[str, Any]) -> Dict[str, Any]:
        """Élément pour la fenêtre, avec sa provenance en clair."""
        view = dict(item)
        view["provenance"] = store.describe_provenance(item)
        if view.get("kind") == "vector":
            view["metadata"] = {key: value for key, value in (item.get("metadata") or {}).items()
                                if isinstance(value, (str, int, float, bool)) or value is None}
        return view

    def add_fact(self, category: str, text: str) -> int:
        """« Ajouter » : un fait saisi à la main (source « manual », confiance 1)."""
        text = (text or "").strip()
        if not text:
            raise MemoryPanelError(tr("memory.emptyContent"))
        if category not in FACT_CATEGORIES:
            category = "general"
        key = text.splitlines()[0].strip()[:_KEY_MAX] or "fait manuel"
        fact_id = self._store().add_fact(category, key, text, source="manual")
        if fact_id is None:
            raise MemoryPanelError(tr("memory.addFailed"))
        return fact_id

    # ── Documents ajoutés (bouton Ajouter, images du chat) ──────────────────

    def _publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        if self._publish_fn is None:
            return
        try:
            self._publish_fn(event_type, payload)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Événement %s non publié : %s", event_type, exc)

    def _notify(self, level: str, message: str) -> None:
        self._publish("notification", {"level": level, "message": message})

    def jobs(self) -> List[Dict[str, Any]]:
        """Documents ajoutés pas encore rangés : en attente, en lecture, en description.

        Un dossier déposé n'en fait qu'un : son nom, ses fichiers restants
        (files) et celui qui se lit (current).
        """
        with self._jobs_lock:
            return self._job_views(self._jobs, self._batches)

    @staticmethod
    def _job_views(jobs: List[Dict[str, Any]],
                   batches: Optional[Dict[str, Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Vue de la file ; un dossier commencé reste « en lecture » entre deux fichiers."""
        views: List[Dict[str, Any]] = []
        folders: Dict[str, Dict[str, Any]] = {}
        for job in jobs:
            batch = job.get("batch")
            if not batch:
                views.append({"id": job["id"], "name": job["name"], "state": job["state"]})
                continue
            view = folders.get(batch)
            if view is None:
                last = (batches or {}).get(batch, {}).get("current")
                view = folders[batch] = {"id": batch, "name": job["folder"],
                                         "state": STAGE_READING if last else "queued",
                                         "folder": job["folder"], "files": 0, "current": last}
                views.append(view)
            view["files"] += 1
            if job["state"] != "queued":
                view["state"] = job["state"]
                view["current"] = job["label"]
        return views

    def _publish_jobs(self) -> None:
        self._publish("memory.jobs", {"jobs": self.jobs()})

    def add_documents(self, paths: List[str], temporary: bool = False,
                      targets: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """« Ajouter » de l'onglet Documents : fichiers lus et rangés en arrière-plan.

        Un à la fois, dans l'ordre : une image occupe le modèle de vision. Un
        fichier refusé (introuvable, format non pris en charge) est renvoyé à
        la fenêtre, qui l'affiche ; les autres sont acceptés.

        Args:
            paths: fichiers choisis ou déposés
            temporary: copies envoyées par un navigateur, effacées une fois lues
            targets: nom de fichier → document qu'il met à jour (l'utilisateur
                l'a voulu : « Mettre à jour ») ; sans cible, il s'ajoute, même si
                un autre document porte son nom

        Returns:
            {"jobs": fichiers acceptés, "refused": [{"name", "message"}]}

        Raises:
            MemoryPanelError: mémoire indisponible
        """
        self._store()
        targets = {str(name): str(key) for name, key in (targets or {}).items() if key}
        accepted: List[Dict[str, Any]] = []
        refused: List[Dict[str, str]] = []
        with self._jobs_lock:
            queued = {os.path.normcase(job["path"]) for job in self._jobs}
        for raw in paths or []:
            path = os.path.abspath(str(raw or ""))
            name = os.path.basename(path) or str(raw)
            if not os.path.isfile(path):
                refused.append({"name": name,
                                "message": tr("memory.documents.notFound", name=name)})
                continue
            if file_type_for(path) is None:
                ext = os.path.splitext(path)[1].lower() or "?"
                refused.append({"name": name, "message": tr("chat.unsupportedFormat", ext=ext)})
                continue
            if os.path.normcase(path) in queued:
                continue  # déjà dans la file : une seule lecture
            queued.add(os.path.normcase(path))
            accepted.append({"id": uuid4().hex, "path": path, "name": name,
                             "state": "queued", "temporary": temporary, "origin": "manual",
                             "replace": targets.get(name)})
        if not accepted:
            return {"jobs": [], "refused": refused}
        views = self._job_views(accepted)  # avant que la lecture ne commence
        self._enqueue(accepted)
        return {"jobs": views, "refused": refused}

    def add_folder(self, folder: str, files: List[Tuple[str, str]],
                   temporary: bool = True, target: Optional[str] = None) -> Dict[str, Any]:
        """Dossier déposé sur l'onglet Documents : ses fichiers, rangés sous son nom.

        Chaque fichier devient le document « dossier/chemin » (métadonnées
        folder, son nom, et folder_id, son identité : deux dossiers du même nom
        restent distincts) ; un bilan unique s'affiche une fois le dernier lu.
        Un fichier introuvable ou d'un format non pris en charge est ignoré (la
        fenêtre ne les envoie pas). Avec une cible (dossier redéposé, « Mettre
        à jour »), ce dossier-là est mis à jour : fichiers inchangés gardés,
        modifiés remplacés, et ceux qu'il ne contient plus retirés
        (prune_folder) ; sans cible, c'est un nouveau dossier.

        Args:
            folder: nom du dossier déposé
            files: (fichier à lire, chemin dans le dossier) de chacun
            temporary: copies envoyées par la fenêtre, effacées une fois lues
            target: clé du dossier déjà en mémoire à mettre à jour

        Returns:
            {"jobs": le dossier dans la file, "refused": []}

        Raises:
            MemoryPanelError: mémoire indisponible, dossier trop gros, rien à lire
        """
        self._store()
        name = clean_folder_name(folder)
        if len(files or []) > FOLDER_FILES_MAX:
            raise MemoryPanelError(tr("memory.documents.folderTooBig", name=name,
                                      max=FOLDER_FILES_MAX))
        known = {doc["folder_key"] for doc in self._store().document_index()
                 if doc.get("folder_key")}
        folder_id = str(target) if target and str(target) in known else uuid4().hex[:16]
        batch = uuid4().hex
        jobs: List[Dict[str, Any]] = []
        seen = set()
        for raw, relative in files or []:
            path = os.path.abspath(str(raw or ""))
            relative = clean_relative_path(relative) or os.path.basename(path)
            if (not os.path.isfile(path) or file_type_for(path) is None
                    or relative.lower() in seen):
                logger.info("Fichier ignoré dans le dossier %s : %s", name, relative)
                if temporary and os.path.isfile(path):
                    _remove_upload(path)
                continue
            seen.add(relative.lower())
            jobs.append({"id": uuid4().hex, "path": path, "name": f"{name}/{relative}",
                         "label": relative, "folder": name, "folder_id": folder_id,
                         "batch": batch, "state": "queued", "temporary": temporary,
                         "origin": "folder"})
        if not jobs:
            raise MemoryPanelError(tr("memory.documents.folderEmpty", name=name))
        with self._jobs_lock:
            self._batches[batch] = {"folder": name, "folder_id": folder_id,
                                    "pending": len(jobs), "added": 0, "updated": 0,
                                    "already": 0, "removed": 0, "failed": 0,
                                    "failed_names": [], "current": None,
                                    "names": [job["name"] for job in jobs]}
        views = self._job_views(jobs)  # avant que la lecture ne commence
        self._enqueue(jobs)
        return {"jobs": views, "refused": []}

    def remember_chat_images(self, paths: List[str]) -> None:
        """Images envoyées dans le chat (PC ou mobile) : rangées dans l'onglet
        Documents, comme les documents joints.

        Décrites une fois le chat sans réponse en cours : le modèle de vision
        sert d'abord la réponse. Sans notification, comme les documents joints ;
        la file s'affiche dans l'onglet, qui se relit. Une image déjà en mémoire
        (même fichier, sous n'importe quel nom) n'est pas décrite de nouveau.
        """
        try:
            self._store()
        except MemoryPanelError as exc:
            logger.info("Images du chat non mises en mémoire : %s", exc)
            return
        with self._jobs_lock:
            queued = {os.path.normcase(job["path"]) for job in self._jobs}
        jobs = []
        for raw in paths or []:
            path = os.path.abspath(str(raw or ""))
            if (not os.path.isfile(path) or file_type_for(path) != "Image"
                    or os.path.normcase(path) in queued):
                continue
            queued.add(os.path.normcase(path))
            jobs.append({"id": uuid4().hex, "path": path, "name": display_name(path),
                         "state": "queued", "temporary": False, "origin": "chat"})
        if jobs:
            self._enqueue(jobs)

    def _enqueue(self, jobs: List[Dict[str, Any]]) -> None:
        """Ajoute des fichiers à la file ; le fil de lecture part s'il ne tourne pas."""
        worker = None
        with self._jobs_lock:
            self._jobs.extend(jobs)
            if self._worker is None:
                worker = self._worker = threading.Thread(
                    target=self._run_jobs, name="memory-documents", daemon=True)
        self._publish_jobs()
        if worker is not None:
            worker.start()

    def _wait_for_chat(self) -> None:
        """Attend que le chat n'ait plus de réponse en cours ni en file."""
        chat = self._chat()
        while chat is not None and getattr(chat, "busy", False):
            time.sleep(self.CHAT_POLL)
            chat = self._chat()

    def _run_jobs(self) -> None:
        """Fil des documents à ranger : le premier en attente, jusqu'au dernier."""
        while True:
            with self._jobs_lock:
                job = next((item for item in self._jobs if item["state"] == "queued"), None)
                if job is None:
                    self._worker = None
            if job is None:
                # File vide : les copies des versions remplacées s'en vont
                self._prune_originals()
                return
            if job["origin"] == "chat":
                self._wait_for_chat()  # « en attente » jusqu'à la fin de la réponse
            with self._jobs_lock:
                job["state"] = STAGE_READING
                if job.get("batch") in self._batches:
                    self._batches[job["batch"]]["current"] = job["label"]
            self._publish_jobs()
            outcome, detail = "failed", ""
            try:
                outcome, detail = self._remember(job)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Document %s non mis en mémoire :\n%s", job["name"],
                             traceback.format_exc())
                detail = str(exc)
            finally:
                with self._jobs_lock:
                    if job in self._jobs:
                        self._jobs.remove(job)
                if job.get("temporary"):
                    _remove_upload(job["path"])
            self._report(job, outcome, detail)
            self._publish_jobs()
            self._publish("memory.changed", {"tab": "document"})

    def _remember(self, job: Dict[str, Any]) -> Tuple[str, str]:
        """Lit un fichier et le range.

        Un fichier remis s'ajoute à côté de celui du même nom, sauf si
        l'utilisateur a choisi « Mettre à jour » : sa cible (le document
        remplacé) est supprimée une fois cette version rangée. Dans un dossier
        déposé, la nouvelle version d'un fichier remplace l'ancienne du même
        dossier.

        Returns:
            (issue, détail) : ("added" | "updated" | "already", "") ou
            ("failed", raison)
        """
        store = self._store()
        folder = job.get("folder")
        manual = job["origin"] != "chat"

        def stage(state: str) -> None:
            with self._jobs_lock:
                job["state"] = state
            self._publish_jobs()

        if folder:
            # Fichier d'un dossier : inchangé depuis un dépôt précédent, il n'est pas relu
            document_id = folder_document_id(job["path"], f"{job['folder_id']}/{job['label']}")
        elif file_type_for(job["path"]) == "Image":
            # Image : rangée sous l'empreinte de son fichier, décrite une seule fois
            document_id = image_document_id(job["path"])
        else:
            document_id = None
        if document_id and store.has_document(document_id):
            if job["origin"] == "manual":
                store.keep_document(document_id)
            # Rangé avant que les fichiers ne soient gardés : il gagne sa copie
            self._keep_original(job, document_id, replace=False)
            # Même contenu : rien à relire ; la version remplacée s'en va quand même
            return ("updated" if self._replace_previous(store, job, document_id)
                    else "already"), ""
        local_ai = getattr(self._engine(), "local_ai", None)
        try:
            content, kind = read_document(job["path"], local_ai=local_ai,
                                          file_processor=self._file_processor, on_stage=stage)
        except DocumentReadError as exc:
            return "failed", str(exc)
        metadata: Dict[str, Any] = (
            {"source": "manual", "type": kind} if manual else {"type": kind})
        if folder:
            metadata.update(folder=folder, folder_id=job["folder_id"])
        result = store.add_document(content, job["name"], metadata, document_id=document_id,
                                    keep=manual)
        status = result.get("status")
        if status not in ("added", "duplicate"):
            return "failed", str(result.get("error") or tr("memory.unavailable"))
        stored_id = str(result.get("document_id") or document_id or "")
        # Copie du fichier lu, pour son aperçu (avant l'effacement d'un envoi temporaire)
        self._keep_original(job, stored_id, replace=status == "added")
        if self._replace_previous(store, job, stored_id):
            return "updated", ""
        return ("added" if status == "added" else "already"), ""

    def keep_chat_document(self, path: str, name: str) -> None:
        """Document joint au chat, rangé en mémoire par le modèle : la copie de son
        fichier, pour l'aperçu de l'onglet Documents.

        Le modèle ne dit pas sous quel identifiant il l'a rangé : c'est le plus
        récent de ce nom, hors dossier, s'il vient d'être rangé. Un doublon d'un
        document plus ancien (même nom, même contenu) n'est pas retouché : un
        autre du même nom pourrait sinon recevoir ce fichier.
        """
        originals = self._originals()
        if originals is None or not path or not os.path.isfile(path):
            return
        try:
            index = self._store().document_index()
        except MemoryPanelError:
            return
        doc = next((item for item in index
                    if item["name"] == name and not item.get("folder")), None)
        if doc is None:
            return
        try:
            created = datetime.fromisoformat(str(doc.get("created") or ""))
        except ValueError:
            return
        now = datetime.now(created.tzinfo) if created.tzinfo else datetime.now()
        if abs((now - created).total_seconds()) <= _CHAT_DOCUMENT_WINDOW:
            originals.keep(doc["id"], path, name, replace=False)

    def _keep_original(self, job: Dict[str, Any], document_id: str, replace: bool) -> None:
        """Garde une copie du fichier lu pour un document (aperçu de l'onglet)."""
        originals = self._originals()
        if originals is not None and document_id:
            originals.keep(document_id, job["path"], job.get("label") or job["name"],
                           replace=replace)

    @staticmethod
    def _replace_previous(store, job: Dict[str, Any], stored_id: str) -> bool:
        """Version remplacée par celle-ci, supprimée une fois celle-ci rangée.

        Dans un dossier : l'ancienne version du même fichier, dans ce dossier.
        Seul : la cible choisie par l'utilisateur (« Mettre à jour »), s'il y en
        a une ; un autre document du même nom reste sinon.
        """
        if not stored_id:
            return False
        if job.get("folder"):
            return bool(store.remove_other_versions(job["name"], stored_id,
                                                    folder_id=job["folder_id"]))
        target = job.get("replace")
        if target and target != stored_id:
            return bool(store.delete_document(target))
        return False

    def _report(self, job: Dict[str, Any], outcome: str, detail: str) -> None:
        """Résultat d'un fichier : notification (ajout à la main), bilan du dossier,
        ou journal seul (image du chat, comme un document joint)."""
        name = job["name"]
        if job["origin"] == "chat":
            if outcome == "failed":
                logger.info("Image du chat non mise en mémoire (%s) : %s", name, detail)
            return
        if job.get("batch"):
            if outcome == "failed":
                logger.info("%s non mis en mémoire : %s", name, detail)
            self._count_in_batch(job, outcome)
        elif outcome == "added":
            self._notify("success", tr("memory.documents.added", name=name))
        elif outcome == "updated":
            self._notify("success", tr("memory.documents.updated", name=name))
        elif outcome == "already":
            self._notify("info", tr("memory.documents.already", name=name))
        else:
            self._notify("error", tr("memory.documents.failed", name=name,
                                     error=detail or tr("memory.unavailable")))

    def _count_in_batch(self, job: Dict[str, Any], outcome: str) -> None:
        """Compte un fichier dans le bilan de son dossier ; le dernier l'affiche."""
        with self._jobs_lock:
            batch = self._batches.get(job["batch"])
            if batch is None:
                return
            batch[outcome] += 1
            if outcome == "failed":
                batch["failed_names"].append(job.get("label") or job["name"])
            batch["pending"] -= 1
            finished = batch["pending"] <= 0
            if finished:
                del self._batches[job["batch"]]
        if finished:
            # Dossier mis à jour : les fichiers qu'il ne contient plus s'en vont
            try:
                batch["removed"] = self._store().prune_folder(batch["folder_id"],
                                                              batch["names"])
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Dossier %s : anciens fichiers non retirés : %s",
                               batch["folder"], exc)
            self._notify(*_folder_summary(batch))

    def update(self, tab: str, entry_id: Any, text: str) -> None:
        """Nouveau contenu d'un élément ; un message de conversation change à la source."""
        text = (text or "").strip()
        if not text:
            raise MemoryPanelError(tr("memory.emptyContent"))
        store = self._store()
        if tab == "facts":
            ok = store.update_fact(int(entry_id), text)
        elif tab == "conversation":
            self._change_conversation(store, str(entry_id), text)
            ok = True
        elif tab == "document":
            ok = store.update_vector(str(entry_id), text, "document", at_source=False)
        else:
            raise MemoryPanelError(tr("memory.unknownTab", tab=tab))
        if not ok:
            raise MemoryPanelError(tr("memory.editFailed"))

    def delete(self, tab: str, entry_id: Any, at_source: bool = True) -> None:
        """Suppression ; un message de conversation peut l'être aussi à la source."""
        store = self._store()
        if tab == "facts":
            ok = store.delete_fact(int(entry_id))
        elif tab == "conversation" and at_source:
            try:
                self._change_conversation(store, str(entry_id), None)
                ok = True
            except MemoryPanelError as exc:
                # Source inaccessible : au moins l'index, comme le MemoryStore
                logger.info("Suppression à la source impossible (%s) : index seul", exc)
                ok = store.delete_vector(str(entry_id), "conversation", at_source=False)
        elif tab in ("document", "conversation"):
            ok = store.delete_vector(str(entry_id), tab, at_source=False)
        else:
            raise MemoryPanelError(tr("memory.unknownTab", tab=tab))
        if not ok:
            raise MemoryPanelError(tr("memory.deleteFailed"))

    def _change_conversation(self, store, entry_id: str, new_text: Optional[str]) -> None:
        """Message d'origine réécrit ou supprimé, puis session réindexée."""
        vector_memory = getattr(store, "vector_memory", None)
        entry = vector_memory.get_entry(entry_id, "conversation") if vector_memory else None
        meta = (entry or {}).get("metadata") or {}
        session_id = meta.get("workspace_id")
        index = meta.get("message_index")
        chat = self._chat()
        if not entry or not session_id or index is None or chat is None:
            raise MemoryPanelError(tr("memory.sourceGone"))
        try:
            chat.change_saved_message(session_id, int(index), entry.get("content") or "", new_text)
        except ChatError as exc:
            raise MemoryPanelError(str(exc)) from exc
        search = getattr(store, "conversation_search", None)
        if search is not None:
            try:
                search.reindex(force=False)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Réindexation des conversations échouée : %s", exc)
