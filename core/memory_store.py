"""
Couche d'accès CRUD unifiée à la mémoire de My_AI.

Façade au-dessus des DEUX stores locaux où l'IA conserve ce qu'elle « sait » de
l'utilisateur :

  - les faits structurés  → core.knowledge_base_manager.KnowledgeBaseManager (SQLite)
  - la mémoire vectorielle → memory.vector_memory.VectorMemory (ChromaDB), avec ses
    deux collections « documents » (chunks de documents) et « conversations »
    (index de recherche cross-conversations).

Objectif : offrir à la fenêtre « Mémoire » une API homogène (lister, paginer,
filtrer, éditer, supprimer) sans qu'elle ait à connaître les détails de chaque
backend. 100 % local, opérations réelles (pas de mock).

Cas particulier des « conversations » : cette collection est reconstruite depuis
les workspaces par core.conversation_search. Une suppression/édition directe dans
ChromaDB réapparaîtrait au prochain réindex ; pour rester durable (at_source=True),
on modifie le message d'origine dans le workspace puis on relance un réindex
incrémental.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.i18n import tr
from core.knowledge_base_manager import SCOPE_CODE, SCOPE_PROJECT, fact_scope, project_name

try:
    from utils.logger import setup_logger
    logger = setup_logger("memory_store")
except Exception:  # pragma: no cover - logger optionnel
    import logging
    logger = logging.getLogger("memory_store")


def _chunk_index(entry: Dict[str, Any]) -> int:
    try:
        return int((entry.get("metadata") or {}).get("chunk_index", 0))
    except (TypeError, ValueError):
        return 0


def document_key(entry: Dict[str, Any]) -> str:
    """Identifiant du document d'un morceau (document_id, sinon son nom)."""
    meta = entry.get("metadata") or {}
    if meta.get("document_id"):
        return str(meta["document_id"])
    if meta.get("document_name"):
        return f"name:{meta['document_name']}"
    return f"entry:{entry.get('id')}"


def _document_where(key: str) -> Dict[str, Any]:
    """Filtre ChromaDB des morceaux d'un document (cf. document_key)."""
    if key.startswith("name:"):
        return {"document_name": key[len("name:"):]}
    return {"document_id": key}


# Chevauchement des morceaux : 32 tokens (VectorMemory), quelques centaines de caractères
_OVERLAP_MAX_CHARS = 1500
_OVERLAP_PROBE = 40


def join_chunks(chunks: List[str]) -> str:
    """Texte d'un document recomposé de ses morceaux, dans l'ordre.

    Deux morceaux voisins se chevauchent (la fin de l'un ouvre le suivant) :
    le passage commun n'est gardé qu'une fois. Sans passage commun retrouvé,
    les morceaux sont simplement mis bout à bout.
    """
    text = ""
    for chunk in chunks:
        if not chunk:
            continue
        if not text:
            text = chunk
            continue
        tail = text[-_OVERLAP_MAX_CHARS:]
        probe = chunk[:_OVERLAP_PROBE]
        start = tail.find(probe) if len(probe) >= 8 else -1
        merged = False
        while start != -1:
            common = tail[start:]
            if chunk.startswith(common):
                text += chunk[len(common):]
                merged = True
                break
            start = tail.find(probe, start + 1)
        if not merged:
            text += "\n" + chunk
    return text


def folder_key(meta: Dict[str, Any]) -> str:
    """Identité d'un dossier déposé : son identifiant (deux dossiers du même nom
    restent distincts), sinon son nom ; "" hors dossier."""
    return str(meta.get("folder_id") or meta.get("folder") or "")


_DocumentIndex = Tuple[Dict[str, Dict[str, Any]], Dict[str, int]]


def _index_documents(entries: List[Dict[str, Any]]) -> _DocumentIndex:
    """Documents des morceaux donnés (nom, dossier, date, origine), et la position
    du dernier morceau de chacun dans l'ordre de la base (ordre d'ajout)."""
    documents: Dict[str, Dict[str, Any]] = {}
    positions: Dict[str, int] = {}
    for position, entry in enumerate(entries):
        meta = entry.get("metadata") or {}
        key = document_key(entry)
        doc = documents.get(key)
        if doc is None:
            name = str(meta.get("document_name") or "document")
            folder = str(meta.get("folder") or "") or None
            label = name[len(folder) + 1:] if folder and name.startswith(f"{folder}/") else name
            doc = documents[key] = {
                "kind": "document", "id": key, "name": name, "label": label,
                "folder": folder, "folder_key": folder_key(meta) or None, "chunks": 0,
                "created": "", "type": meta.get("type"), "source": None,
            }
        doc["chunks"] += 1
        positions[key] = position
        doc["created"] = max(doc["created"], str(meta.get("created") or ""))
        if meta.get("source") == "manual":
            doc["source"] = "manual"
    return documents, positions


def group_documents(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Documents et dossiers de l'onglet Documents, du plus récent au plus ancien.

    Un document réunit ses morceaux (date du plus récent, type, ajouté à la
    main) ; un dossier déposé (métadonnées « folder », « folder_id ») réunit ses
    documents, rangés par chemin. Deux documents, ou deux dossiers, peuvent
    porter le même nom : leur date les distingue.

    Args:
        entries: Morceaux {"id", "metadata"…} dans l'ordre de la base (ordre d'ajout)

    Returns:
        Groupes {"kind": "document" | "folder", …} ; un dossier a sa clé (« key »)
    """
    documents, positions = _index_documents(entries)
    groups: List[Dict[str, Any]] = []
    folders: Dict[str, Dict[str, Any]] = {}
    for key, doc in documents.items():
        fkey = doc["folder_key"]
        if not doc["folder"] or not fkey:
            groups.append(doc)
            continue
        group = folders.get(fkey)
        if group is None:
            group = folders[fkey] = {
                "kind": "folder", "id": f"folder:{fkey}", "key": fkey, "name": doc["folder"],
                "files": 0, "chunks": 0, "created": "", "source": None, "documents": [],
            }
            groups.append(group)
            positions[group["id"]] = -1
        group["documents"].append(doc)
        group["files"] += 1
        group["chunks"] += doc["chunks"]
        group["created"] = max(group["created"], doc["created"])
        group["source"] = group["source"] or doc["source"]
        positions[group["id"]] = max(positions[group["id"]], positions[key])
    for group in folders.values():
        group["documents"].sort(key=lambda doc: doc["label"].lower())
    groups.sort(key=lambda group: -positions[group["id"]])
    return groups


def _documents_order(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Entrées de la collection « documents » classées pour l'onglet Documents.

    Documents du plus récent au plus ancien (dernier ajout de leurs morceaux,
    dans l'ordre de la base), et les morceaux de chacun dans l'ordre du texte.

    Args:
        entries: Entrées {"id", "metadata"…} dans l'ordre de la base (ordre d'ajout)
    """
    groups: Dict[str, List[Tuple[int, Dict[str, Any]]]] = {}
    for position, entry in enumerate(entries):
        meta = entry.get("metadata") or {}
        key = str(meta.get("document_id") or meta.get("document_name") or entry.get("id"))
        groups.setdefault(key, []).append((position, entry))
    ordered: List[Dict[str, Any]] = []
    for chunks in sorted(groups.values(), key=lambda chunks: -chunks[-1][0]):
        chunks.sort(key=lambda item: (_chunk_index(item[1]), item[0]))
        ordered.extend(entry for _, entry in chunks)
    return ordered


class MemoryStore:
    """Accès CRUD unifié aux faits (SQLite) et aux entrées vectorielles (ChromaDB)."""

    def __init__(
        self,
        knowledge_base: Any = None,
        vector_memory: Any = None,
        session_manager: Any = None,
        conversation_search: Any = None,
    ) -> None:
        """
        Args:
            knowledge_base: instance de KnowledgeBaseManager (faits SQLite).
            vector_memory: instance de VectorMemory (collections ChromaDB).
            session_manager: SessionManager, requis pour la suppression/édition
                « à la source » des entrées de conversation.
            conversation_search: ConversationSearch, pour réindexer après une
                modification à la source.
        """
        self.knowledge_base = knowledge_base
        self.vector_memory = vector_memory
        self.session_manager = session_manager
        self.conversation_search = conversation_search
        # Index des documents (document_index) : (nombre de morceaux, documents)
        self._index_cache: Optional[Tuple[Optional[int], List[Dict[str, Any]]]] = None

    # ------------------------------------------------------------------
    # Faits structurés (SQLite)
    # ------------------------------------------------------------------

    def list_facts(
        self,
        query: str = "",
        category: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Liste paginée des faits, filtrée par recherche et/ou catégorie.

        Returns:
            (items, total) où items est la page demandée et total le nombre de
            faits correspondant au filtre (avant pagination).
        """
        kb = self.knowledge_base
        if kb is None:
            return [], 0
        category = (category or "").strip() or None
        try:
            if query and query.strip():
                facts = kb.search_facts(query.strip(), category=category, limit=10000)
            else:
                facts = kb.get_all_facts(category=category)
        except Exception as exc:
            logger.warning("Lecture des faits échouée: %s", exc)
            return [], 0

        total = len(facts)
        page = facts[offset:offset + limit] if limit else facts[offset:]
        return [self._fact_item(f) for f in page], total

    def add_fact(
        self,
        category: str,
        key: str,
        value: str,
        source: str = "manual",
    ) -> Optional[int]:
        """Ajoute un fait. Retourne son id, ou None en cas d'échec."""
        kb = self.knowledge_base
        if kb is None:
            return None
        try:
            return kb.add_fact(category=category, key=key, value=value, source=source)
        except Exception as exc:
            logger.warning("Ajout de fait échoué: %s", exc)
            return None

    def update_fact(self, fact_id: int, value: str) -> bool:
        """Met à jour la valeur d'un fait."""
        kb = self.knowledge_base
        if kb is None:
            return False
        try:
            return bool(kb.update_fact(fact_id, value))
        except Exception as exc:
            logger.warning("Mise à jour de fait échouée: %s", exc)
            return False

    def delete_fact(self, fact_id: int) -> bool:
        """Supprime un fait."""
        kb = self.knowledge_base
        if kb is None:
            return False
        try:
            return bool(kb.delete_fact(fact_id))
        except Exception as exc:
            logger.warning("Suppression de fait échouée: %s", exc)
            return False

    def fact_categories(self) -> List[str]:
        """Catégories ayant au moins un fait."""
        kb = self.knowledge_base
        if kb is None:
            return []
        try:
            return list(kb.get_categories())
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Entrées vectorielles (ChromaDB)
    # ------------------------------------------------------------------

    def list_vectors(
        self,
        collection_type: str = "document",
        query: str = "",
        limit: int = 25,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Liste paginée des entrées d'une collection vectorielle.

        Sans recherche : pagination native ChromaDB (count + get limit/offset).
        Avec recherche : balayage du corpus + filtre sous-chaîne insensible à la
        casse, puis pagination en mémoire (prévisible, toutes langues).

        Documents : du plus récent au plus ancien, chacun de son premier morceau
        au dernier (_documents_order). Un document ajouté (bouton Ajouter, pièce
        jointe) s'affiche donc en tête de la première page, et non à la fin.
        """
        vm = self.vector_memory
        if vm is None:
            return [], 0
        by_document = collection_type == "document"
        try:
            if query and query.strip():
                q = query.strip().lower()
                everything = vm.list_entries(collection_type, limit=None, offset=0)
                filtered = [
                    e for e in everything
                    if q in (e.get("content", "") or "").lower()
                ]
                if by_document:
                    filtered = _documents_order(filtered)
                total = len(filtered)
                page = filtered[offset:offset + limit] if limit else filtered[offset:]
            elif by_document and hasattr(vm, "list_metadatas") and hasattr(vm, "get_entries"):
                # Classement sur les seules métadonnées, puis le texte de la page
                ordered = _documents_order(vm.list_metadatas(collection_type))
                total = len(ordered)
                chosen = ordered[offset:offset + limit] if limit else ordered[offset:]
                page = vm.get_entries([e["id"] for e in chosen], collection_type)
            else:
                total = vm.count_entries(collection_type)
                page = vm.list_entries(collection_type, limit=limit, offset=offset)
        except Exception as exc:
            logger.warning("Lecture des entrées vectorielles échouée: %s", exc)
            return [], 0

        items = [
            {"kind": "vector", "collection": collection_type, **entry}
            for entry in page
        ]
        return items, total

    def add_document(
        self,
        content: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None,
        keep: bool = True,
    ) -> Dict[str, Any]:
        """Range un document dans la collection « documents » (onglet Documents).

        Même nom et même contenu (ou même image) : il n'est pas recopié ;
        ajouté à la main (keep), il est gardé comme tel, pour que retirer la
        pièce jointe qui l'avait rangé ne l'efface pas. Deux fichiers du même
        nom mais de contenus différents restent deux documents : remplacer
        l'un par l'autre est le choix de l'utilisateur (delete_document,
        remove_other_versions).

        Args:
            document_id: Identifiant imposé (image : empreinte du fichier)
            keep: Ajout à la main (bouton Ajouter) ; False pour une image du chat

        Returns:
            {"status": "added" | "duplicate" | "error", "document_id": id,
            "chunks": n, "error": message}
        """
        vm = self.vector_memory
        if vm is None:
            return {"status": "error", "document_id": "", "chunks": 0,
                    "error": tr("memory.unavailable")}
        result = vm.add_document(content, document_name=name, metadata=metadata,
                                 document_id=document_id) or {}
        status = result.get("status")
        stored_id = str(result.get("document_id") or document_id or "")
        if status == "duplicate":
            chunks = self.keep_document(stored_id) if keep else 0
            self._changed()
            return {"status": "duplicate", "document_id": stored_id, "chunks": chunks,
                    "error": ""}
        # Rangés dans ChromaDB : aucun sans modèle d'embeddings, même découpé
        stored = result.get("chunks_stored", result.get("chunks_created"))
        if status != "success" or not stored:
            error = str(result.get("error") or "") or tr("memory.unavailable")
            return {"status": "error", "document_id": "", "chunks": 0, "error": error}
        self._changed()
        return {"status": "added", "document_id": stored_id, "chunks": int(stored),
                "error": ""}

    def remove_other_versions(self, name: str, document_id: str,
                              folder_id: Optional[str] = None) -> int:
        """Supprime les autres versions d'un fichier d'un dossier déposé : même
        chemin (« dossier/chemin ») dans le même dossier, autre contenu.

        Sans dossier (folder_id None) : les autres documents de ce nom.

        Returns:
            Nombre de morceaux supprimés
        """
        vm = self.vector_memory
        if vm is None or not name or not document_id or not hasattr(vm, "delete_where"):
            return 0
        where: List[Dict[str, Any]] = [{"document_name": name},
                                       {"document_id": {"$ne": document_id}}]
        if folder_id:
            where.append({"folder_id": folder_id})
        removed = int(vm.delete_where({"$and": where}, "document") or 0)
        if removed:
            self._changed()
            logger.info("%s : ancienne version remplacée (%d morceaux)", name, removed)
        return removed

    # ------------------------------------------------------------------
    # Onglet Documents : documents et dossiers
    # ------------------------------------------------------------------

    def list_document_groups(
        self,
        query: str = "",
        limit: int = 25,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Documents et dossiers (group_documents), paginés.

        Avec recherche : ceux dont le nom, le dossier ou le texte la contient
        (casse ignorée). Un dossier n'y montre que ses fichiers trouvés ; s'il en
        a d'autres, « total » dit combien il en a en tout (« 1 fichier sur 4 »).
        Les morceaux (chunks) restent internes : l'onglet n'en montre que les
        documents.

        Returns:
            (groupes de la page, nombre total de groupes)
        """
        vm = self.vector_memory
        if vm is None:
            return [], 0
        totals: Dict[str, int] = {}
        try:
            q = (query or "").strip().lower()
            if q:
                everything = vm.list_entries("document", limit=None, offset=0)
                keys = {
                    document_key(entry) for entry in everything
                    if q in (entry.get("content") or "").lower()
                    or q in str((entry.get("metadata") or {}).get("document_name") or "").lower()
                }
                entries = [entry for entry in everything if document_key(entry) in keys]
                totals = {group["key"]: group["files"] for group in group_documents(everything)
                          if group["kind"] == "folder"}
            elif hasattr(vm, "list_metadatas"):
                entries = vm.list_metadatas("document")
            else:
                entries = vm.list_entries("document", limit=None, offset=0)
        except Exception as exc:
            logger.warning("Lecture des documents échouée: %s", exc)
            return [], 0
        groups = group_documents(entries)
        for group in groups:
            if group["kind"] == "folder" and totals.get(group["key"], 0) > group["files"]:
                group["total"] = totals[group["key"]]
        page = groups[offset:offset + limit] if limit else groups[offset:]
        return page, len(groups)

    def delete_document(self, document_id: str) -> int:
        """Supprime un document entier (tous ses morceaux). Retourne le nombre de morceaux."""
        vm = self.vector_memory
        if vm is None or not document_id:
            return 0
        if document_id.startswith("entry:"):
            removed = int(bool(vm.delete_entry(document_id[len("entry:"):], "document")))
        else:
            removed = int(vm.delete_where(_document_where(document_id), "document"))
        if removed:
            self._changed()
        return removed

    def delete_folder(self, key: str) -> int:
        """Supprime un dossier déposé (tous les morceaux de ses documents).

        Args:
            key: sa clé (folder_key : son identifiant), pas son nom : un autre
                dossier du même nom reste
        """
        vm = self.vector_memory
        if vm is None or not key:
            return 0
        removed = int(vm.delete_where({"folder_id": key}, "document"))
        if removed:
            self._changed()
        return removed

    def _changed(self) -> None:
        """Contenu de l'onglet Documents modifié : l'index des documents se refait."""
        self._index_cache = None

    def document_index(self) -> List[Dict[str, Any]]:
        """Un enregistrement par document de l'onglet Documents, du plus récent au
        plus ancien : {"id", "name", "label", "folder", "folder_key", "created",
        "source", "type"} (sans texte).

        Gardé tant que la collection ne change pas : la fenêtre (« déjà en
        mémoire ? ») et chaque message du chat (documents nommés) le relisent.
        """
        vm = self.vector_memory
        lister = getattr(vm, "list_metadatas", None)
        if not callable(lister):
            return []
        try:
            count = vm.count_entries("document")
        except Exception:
            count = None
        cached = getattr(self, "_index_cache", None)
        if cached is not None and count is not None and cached[0] == count:
            return cached[1]
        try:
            documents, _positions = _index_documents(lister("document"))
        except Exception as exc:
            logger.warning("Lecture des documents échouée: %s", exc)
            return []
        index = sorted(documents.values(), key=lambda doc: doc["created"], reverse=True)
        self._index_cache = (count, index)
        return index

    def prune_folder(self, folder_id: str, keep: Iterable[str]) -> int:
        """Retire d'un dossier déposé les fichiers qu'il ne contient plus (dossier
        mis à jour : redéposé, un fichier supprimé depuis).

        Args:
            folder_id: clé du dossier (folder_key)
            keep: noms (« dossier/chemin ») des fichiers du dernier dépôt

        Returns:
            Nombre de fichiers retirés
        """
        vm = self.vector_memory
        if vm is None or not folder_id or not hasattr(vm, "delete_where"):
            return 0
        kept = set(keep)
        stale = {doc["name"] for doc in self.document_index()
                 if doc["folder_key"] == folder_id and doc["name"] not in kept}
        for name in stale:
            vm.delete_where({"$and": [{"folder_id": folder_id}, {"document_name": name}]},
                            "document")
        if stale:
            self._changed()
            logger.info("Dossier %s : %d fichier(s) retiré(s), absents du dépôt", folder_id,
                        len(stale))
        return len(stale)

    def document_text(self, document_id: str) -> str:
        """Texte d'un document, recomposé de ses morceaux (sans leurs chevauchements).

        Un document rangé sans identifiant (ancien, « name:… » ou « entry:… »,
        cf. document_key) est retrouvé parmi les morceaux de la collection.
        """
        vm = self.vector_memory
        reader = getattr(vm, "document_chunks", None)
        if not callable(reader) or not document_id:
            return ""
        try:
            if document_id.startswith(("name:", "entry:")):
                entries = [entry for entry in vm.list_entries("document", limit=None, offset=0)
                           if document_key(entry) == document_id]
                entries.sort(key=_chunk_index)
                return join_chunks([entry.get("content") or "" for entry in entries])
            return join_chunks(reader(document_id))
        except Exception as exc:
            logger.warning("Lecture du document %s échouée: %s", document_id, exc)
            return ""

    def has_document(self, document_id: str) -> bool:
        """Le document est-il déjà dans l'onglet Documents (au moins un morceau) ?"""
        check = getattr(self.vector_memory, "has_document", None)
        return bool(check(document_id)) if callable(check) else False

    def keep_document(self, document_id: str) -> int:
        """Garde un document déjà rangé comme ajouté à la main ; ses morceaux gardés."""
        keep = getattr(self.vector_memory, "keep_document", None)
        return int(keep(document_id)) if callable(keep) else 0

    def update_vector(
        self,
        entry_id: str,
        new_text: str,
        collection_type: str = "document",
        at_source: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Met à jour le texte d'une entrée vectorielle.

        Pour les conversations avec at_source=True, modifie le message d'origine
        dans le workspace puis réindexe (durable). Sinon, met à jour directement
        l'entrée ChromaDB.
        """
        vm = self.vector_memory
        if vm is None:
            return False

        if collection_type == "conversation" and at_source and self.session_manager:
            meta = metadata if metadata is not None else self._entry_meta(
                entry_id, collection_type
            )
            if self._edit_conversation_source(meta, new_text):
                self._reindex_conversations()
                return True
            return False

        return bool(vm.update_entry(entry_id, new_text, collection_type))

    def delete_vector(
        self,
        entry_id: str,
        collection_type: str = "document",
        at_source: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Supprime une entrée vectorielle.

        Pour les conversations avec at_source=True, supprime le message d'origine
        dans le workspace puis réindexe (la suppression ne réapparaît pas). Sinon,
        suppression directe dans ChromaDB (transitoire pour les conversations).
        """
        vm = self.vector_memory
        if vm is None:
            return False

        if collection_type == "conversation" and at_source and self.session_manager:
            meta = metadata if metadata is not None else self._entry_meta(
                entry_id, collection_type
            )
            if self._delete_conversation_source(meta):
                self._reindex_conversations()
                return True
            # Repli : si la source est inaccessible, au moins retirer l'index.
            return bool(vm.delete_entry(entry_id, collection_type))

        return bool(vm.delete_entry(entry_id, collection_type))

    # ------------------------------------------------------------------
    # Propagation « à la source » pour les conversations
    # ------------------------------------------------------------------

    def _entry_meta(self, entry_id: str, collection_type: str) -> Dict[str, Any]:
        """Récupère les métadonnées d'une entrée (workspace_id, message_index…)."""
        try:
            entry = self.vector_memory.get_entry(entry_id, collection_type)
        except Exception:
            entry = None
        return (entry or {}).get("metadata", {}) or {}

    def _load_history(self, workspace_id: str):
        """Charge l'état d'un workspace et localise sa liste d'historique.

        Returns:
            (state, key, history) ou (None, None, None) si introuvable.
        """
        state = self.session_manager.load_workspace(workspace_id)
        if not state:
            return None, None, None
        key = "conversation_history" if "conversation_history" in state else (
            "history" if "history" in state else "conversation_history"
        )
        history = state.get(key) or []
        if not isinstance(history, list):
            return None, None, None
        return state, key, history

    def _delete_conversation_source(self, meta: Dict[str, Any]) -> bool:
        """Supprime le message d'origine d'une entrée de conversation."""
        if not meta:
            return False
        ws_id = meta.get("workspace_id")
        idx = meta.get("message_index")
        if not ws_id or idx is None:
            return False
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            return False

        state, key, history = self._load_history(ws_id)
        if state is None or idx < 0 or idx >= len(history):
            return False
        del history[idx]
        state[key] = history
        try:
            return bool(self.session_manager.save_workspace(ws_id, state))
        except Exception as exc:
            logger.warning("Sauvegarde workspace après suppression échouée: %s", exc)
            return False

    def _edit_conversation_source(self, meta: Dict[str, Any], new_text: str) -> bool:
        """Réécrit le message d'origine d'une entrée de conversation."""
        if not meta or not new_text or not new_text.strip():
            return False
        ws_id = meta.get("workspace_id")
        idx = meta.get("message_index")
        if not ws_id or idx is None:
            return False
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            return False

        state, key, history = self._load_history(ws_id)
        if state is None or idx < 0 or idx >= len(history):
            return False
        msg = history[idx]
        if not isinstance(msg, dict):
            return False
        # Conserver le champ texte utilisé par le message d'origine.
        if "content" in msg and "text" not in msg:
            msg["content"] = new_text
        else:
            msg["text"] = new_text
        state[key] = history
        try:
            return bool(self.session_manager.save_workspace(ws_id, state))
        except Exception as exc:
            logger.warning("Sauvegarde workspace après édition échouée: %s", exc)
            return False

    def _reindex_conversations(self) -> None:
        """Relance un réindex incrémental (reconstruit le workspace modifié)."""
        cs = self.conversation_search
        if cs is None:
            return
        try:
            cs.reindex(force=False)
        except Exception as exc:
            logger.warning("Réindexation des conversations échouée: %s", exc)

    # ------------------------------------------------------------------
    # Vue d'ensemble / provenance
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, int]:
        """Compteurs par source (faits, documents, conversations)."""
        facts = 0
        if self.knowledge_base is not None:
            try:
                facts = len(self.knowledge_base.get_all_facts())
            except Exception:
                facts = 0
        documents = conversations = 0
        if self.vector_memory is not None:
            documents = self._count_documents()
            conversations = self.vector_memory.count_entries("conversation")
        return {
            "facts": facts,
            "documents": documents,
            "conversations": conversations,
        }

    def _count_documents(self) -> int:
        """Documents de l'onglet Documents, et non leurs morceaux (chunks)."""
        vm = self.vector_memory
        if not callable(getattr(vm, "list_metadatas", None)):
            return vm.count_entries("document")
        return len(self.document_index())

    @staticmethod
    def describe_provenance(item: Dict[str, Any]) -> str:
        """Construit une ligne de provenance lisible pour un item de mémoire."""
        if item.get("kind") == "fact":
            src = item.get("source") or tr("memory.provenance.manual")
            try:
                conf_pct = int(float(item.get("confidence", 1.0)) * 100)
            except (TypeError, ValueError):
                conf_pct = 100
            parts = [tr("memory.provenance.source", source=src),
                     tr("memory.provenance.confidence", percent=conf_pct)]
            # Retenu dans la conversation Code : en tête, que la ligne coupée le garde
            scope, project = fact_scope(item)
            if scope == SCOPE_CODE:
                parts.insert(0, tr("memory.provenance.scopeCode"))
            elif scope == SCOPE_PROJECT:
                parts.insert(0, tr("memory.provenance.scopeProject",
                                   project=project_name(project)))
            updated = str(item.get("updated_at", ""))
            if updated:
                parts.append(tr("memory.provenance.updated", date=updated[:19].replace("T", " ")))
            return "  ·  ".join(parts)

        meta = item.get("metadata", {}) or {}
        if item.get("collection") == "conversation":
            name = meta.get("workspace_name") or meta.get("workspace_id") or "conversation"
            parts = [f"💼 {name}"]
            role = meta.get("role", "")
            if role:
                parts.append(tr("memory.provenance.you" if role == "user"
                                else "memory.provenance.assistant"))
            ts = str(meta.get("timestamp", ""))
            if ts:
                parts.append(ts[:19].replace("T", " "))
            return "  ·  ".join(parts)

        # Collection « documents »
        name = meta.get("document_name") or "document"
        parts = [f"{'🖼️' if meta.get('type') == 'Image' else '📄'} {name}"]
        chunk = meta.get("chunk_index")
        if chunk is not None:
            parts.append(tr("memory.provenance.chunk", n=chunk))
        created = str(meta.get("created", ""))
        if created:
            parts.append(created[:19].replace("T", " "))
        if meta.get("source") == "manual":
            parts.append(tr("memory.provenance.byHand"))
        return "  ·  ".join(parts)

    @staticmethod
    def _fact_item(fact: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise un fait SQLite en item de mémoire homogène."""
        return {
            "kind": "fact",
            "id": fact.get("id"),
            "category": fact.get("category", "general"),
            "key": fact.get("key", ""),
            "value": fact.get("value", fact.get("content", "")),
            "source": fact.get("source", ""),
            "confidence": fact.get("confidence", 1.0),
            "created_at": fact.get("created_at", ""),
            "updated_at": fact.get("updated_at", ""),
            "scope": fact_scope(fact)[0],
            "project": fact_scope(fact)[1],
        }
