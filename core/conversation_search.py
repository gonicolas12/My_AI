"""
Recherche globale cross-conversations / cross-workspaces.

Interroge TOUTES les conversations sauvegardees (workspaces) a la fois, en
semantique, en REUTILISANT l'index ChromaDB existant (collection "conversations"
de memory.vector_memory) et l'embedding partage (core.shared). Aucun second
pipeline d'embedding n'est cree.

Principe :
  - L'indexation est incrementale : un manifeste (conversation_index.json) garde
    le `last_modified` de chaque workspace deja indexe. Au reindex, seuls les
    workspaces nouveaux/modifies sont re-traites, et les workspaces supprimes
    sont retires de l'index.
  - La recherche est hybride : similarite semantique (+ reranking CrossEncoder
    si dispo, herite de VectorMemory.search_similar) puis post-filtres optionnels
    mot-cle / role / date.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import get_config

try:
    from utils.logger import setup_logger
    logger = setup_logger("conversation_search")
except Exception:  # pragma: no cover - logger optionnel
    import logging
    logger = logging.getLogger("conversation_search")


# Version du schema d'indexation : incrementer force une reindexation complete
# (utile quand la LOGIQUE d'indexation change, a donnees inchangees).
_INDEX_SCHEMA = 3

# Types techniques (placeholders, images) qui n'ont pas de texte a chercher.
# Aucun filtre de longueur : tout message non vide est indexable, quel que
# soit le role, pour ne jamais limiter les recherches de l'utilisateur.
_SKIP_TYPES = {"file_generation_placeholder", "image"}

# Mots-outils ignores par le filet lexical (sinon "qui", "the"... matchent tout).
_STOPWORDS = {
    "qui", "que", "quoi", "est", "es", "tu", "moi", "toi", "les", "des", "une",
    "uns", "ses", "mes", "tes", "pour", "avec", "dans", "sur", "par", "pas",
    "the", "and", "for", "with", "what", "who", "you", "are", "this", "that",
    "aujourd", "hui",
}


class ConversationSearch:
    """Recherche semantique globale sur l'ensemble des workspaces."""

    def __init__(self, session_manager: Any, vector_memory: Any,
                 min_rerank_score: Optional[float] = None,
                 max_distance: Optional[float] = None) -> None:
        """
        Args:
            session_manager: instance de core.session_manager.SessionManager
            vector_memory: instance de memory.vector_memory.VectorMemory (partagee)
            min_rerank_score: score CrossEncoder minimal pour qu'un resultat soit
                conserve (defaut config `search.min_rerank_score`, sinon -7.0).
                Les requetes sans rapport produisent des scores ~ -11 ; le seuil
                par defaut elimine ce bruit tout en gardant les vrais resultats.
            max_distance: distance cosinus maximale utilisee SEULEMENT en repli
                si aucun reranker n'est disponible (defaut 0.55).
        """
        self.session_manager = session_manager
        self.vector_memory = vector_memory
        self._lock = threading.Lock()

        self.min_rerank_score = (
            min_rerank_score if min_rerank_score is not None
            else self._cfg("search.min_rerank_score", -7.0)
        )
        self.max_distance = (
            max_distance if max_distance is not None
            else self._cfg("search.max_distance", 0.55)
        )

        # Manifeste d'indexation, range a cote de l'index ChromaDB
        try:
            storage_dir = Path(getattr(vector_memory, "storage_dir", "memory/vector_store"))
        except Exception:
            storage_dir = Path("memory/vector_store")
        self._manifest_path = storage_dir / "conversation_index.json"

    @staticmethod
    def _cfg(key: str, default):
        """Lit une valeur de config, avec repli silencieux."""
        try:
            return get_config().get(key, default)
        except Exception:
            return default

    # ------------------------------------------------------------------
    # Disponibilite
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """La recherche n'est exploitable que si embedding + collection presents."""
        vm = self.vector_memory
        return bool(
            vm is not None
            and getattr(vm, "embedding_model", None) is not None
            and getattr(vm, "conversation_collection", None) is not None
            and self.session_manager is not None
        )

    @property
    def _collection(self):
        return getattr(self.vector_memory, "conversation_collection", None)

    # ------------------------------------------------------------------
    # Manifeste
    # ------------------------------------------------------------------

    def _load_manifest(self) -> Dict[str, str]:
        """Charge la table {workspace_id: last_modified}.

        Renvoie {} si le schema d'indexation a change, ce qui force une
        reindexation complete (les regles d'indexation ont evolue).
        """
        if not self._manifest_path.is_file():
            return {}
        try:
            with open(self._manifest_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Manifeste de recherche illisible: %s", exc)
            return {}
        if not isinstance(data, dict) or data.get("schema") != _INDEX_SCHEMA:
            return {}  # schema obsolete -> tout reindexer
        workspaces = data.get("workspaces", {})
        return workspaces if isinstance(workspaces, dict) else {}

    def _save_manifest(self, manifest: Dict[str, str]) -> None:
        try:
            self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._manifest_path.with_suffix(".json.tmp")
            payload = {"schema": _INDEX_SCHEMA, "workspaces": manifest}
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
            tmp.replace(self._manifest_path)
        except OSError as exc:
            logger.warning("Sauvegarde du manifeste echouee: %s", exc)

    # ------------------------------------------------------------------
    # Indexation
    # ------------------------------------------------------------------

    @staticmethod
    def _iter_indexable_messages(history: List[dict]):
        """Genere (index, role, text, timestamp) pour les messages indexables.

        Indexe TOUT message non vide (utilisateur comme assistant), sans aucun
        filtre de longueur.
        """
        for idx, msg in enumerate(history):
            if not isinstance(msg, dict):
                continue
            if msg.get("type") in _SKIP_TYPES:
                continue
            text = (msg.get("text") or msg.get("content") or "").strip()
            if not text:
                continue
            is_user = msg.get("is_user", msg.get("role", "user") == "user")
            role = "user" if is_user else "assistant"
            timestamp = str(msg.get("timestamp", ""))
            yield idx, role, text, timestamp

    def _delete_workspace_entries(self, workspace_id: str) -> None:
        """Supprime de l'index toutes les entrees d'un workspace."""
        col = self._collection
        if col is None:
            return
        try:
            col.delete(where={"workspace_id": workspace_id})
        except Exception as exc:
            logger.warning("Suppression index workspace '%s' echouee: %s", workspace_id, exc)

    def _index_workspace(self, workspace_id: str, workspace_name: str) -> int:
        """(Re)indexe un workspace. Retourne le nombre de messages indexes."""
        col = self._collection
        model = getattr(self.vector_memory, "embedding_model", None)
        if col is None or model is None:
            return 0

        state = self.session_manager.load_workspace(workspace_id)
        if not state:
            return 0
        history = state.get("conversation_history", state.get("history", []))
        if not isinstance(history, list):
            return 0

        # Repartir de zero pour ce workspace (gere les editions/suppressions)
        self._delete_workspace_entries(workspace_id)

        ids: List[str] = []
        embeddings: List[list] = []
        documents: List[str] = []
        metadatas: List[dict] = []

        for idx, role, text, timestamp in self._iter_indexable_messages(history):
            ids.append(f"conv_{workspace_id}_{idx}")
            embeddings.append(model.encode(text).tolist())
            documents.append(text)
            metadatas.append(
                {
                    "workspace_id": workspace_id,
                    "workspace_name": workspace_name,
                    "message_index": idx,
                    "role": role,
                    "timestamp": timestamp,
                }
            )

        if ids:
            try:
                col.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                )
            except Exception as exc:
                logger.error("Indexation workspace '%s' echouee: %s", workspace_id, exc)
                return 0

        return len(ids)

    def reindex(self, force: bool = False) -> Dict[str, int]:
        """
        Synchronise l'index avec les workspaces sur disque (incremental).

        Args:
            force: si True, reindexe tous les workspaces sans tenir compte du
                   manifeste.

        Returns:
            {"indexed": n_workspaces, "messages": n_messages, "removed": n_supprimes}
        """
        if not self.is_available():
            return {"indexed": 0, "messages": 0, "removed": 0}

        with self._lock:
            manifest = {} if force else self._load_manifest()
            try:
                workspaces = self.session_manager.list_workspaces()
            except Exception as exc:
                logger.warning("Liste des workspaces indisponible: %s", exc)
                return {"indexed": 0, "messages": 0, "removed": 0}

            current_ids = {ws.get("id") for ws in workspaces if ws.get("id")}

            # Workspaces disparus -> purge de l'index + du manifeste
            removed = 0
            for old_id in list(manifest.keys()):
                if old_id not in current_ids:
                    self._delete_workspace_entries(old_id)
                    manifest.pop(old_id, None)
                    removed += 1

            indexed = 0
            messages = 0
            for ws in workspaces:
                ws_id = ws.get("id")
                if not ws_id:
                    continue
                last_modified = str(ws.get("last_modified", ""))
                if not force and manifest.get(ws_id) == last_modified:
                    continue  # inchange depuis le dernier index
                ws_name = ws.get("name", ws_id)
                n = self._index_workspace(ws_id, ws_name)
                manifest[ws_id] = last_modified
                indexed += 1
                messages += n

            self._save_manifest(manifest)
            if indexed or removed:
                logger.info(
                    "Reindex termine: %d workspace(s), %d message(s), %d supprime(s)",
                    indexed, messages, removed,
                )
            return {"indexed": indexed, "messages": messages, "removed": removed}

    # ------------------------------------------------------------------
    # Recherche
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        n_results: int = 10,
        role: Optional[str] = None,
        keyword: Optional[str] = None,
        since: Optional[str] = None,
        auto_reindex: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Recherche semantique globale sur toutes les conversations.

        Args:
            query: requete en langage naturel
            n_results: nombre de resultats finaux
            role: filtre "user" | "assistant" (None = tous)
            keyword: sous-chaine devant apparaitre dans l'extrait (filtre exact)
            since: date ISO minimale (timestamp >= since)
            auto_reindex: rafraichit l'index avant de chercher (incremental)

        Returns:
            Liste de resultats tries par pertinence :
            {workspace_id, workspace_name, message_index, role, timestamp,
             excerpt, score, distance}
        """
        if not self.is_available() or not query or not query.strip():
            return []

        if auto_reindex:
            try:
                self.reindex(force=False)
            except Exception as exc:
                logger.warning("Reindex avant recherche ignore: %s", exc)

        # Sur-echantillonner largement : on filtre ensuite par pertinence reelle.
        fetch_n = max(n_results * 6, 40)
        try:
            # rerank=False : on recupere les plus proches voisins + distances,
            # puis on reranke nous-memes pour pouvoir appliquer un SEUIL.
            raw = self.vector_memory.search_similar(
                query, n_results=fetch_n, collection_type="conversation", rerank=False,
            ) or []
        except Exception as exc:
            logger.warning("Recherche conversations echouee: %s", exc)
            raw = []

        # Balayage mot-exact sur TOUTE la base : garantit qu'un message contenant
        # litteralement les mots de la requete n'est jamais manque, meme s'il est
        # hors des plus proches voisins semantiques (corpus volumineux, autre
        # langue ou le reranker est faible...). Insensible a la casse -> OK pour
        # toutes les langues.
        raw = self._merge_lexical_hits(query, raw)

        if not raw:
            return []

        raw = self._filter_by_relevance(query, raw)

        keyword_lc = keyword.lower() if keyword else None
        results: List[Dict[str, Any]] = []
        for r in raw:
            meta = r.get("metadata", {}) or {}
            content = r.get("content", "")

            if role and meta.get("role") != role:
                continue
            if keyword_lc and keyword_lc not in content.lower():
                continue
            ts = str(meta.get("timestamp", ""))
            if since and ts and ts < since:
                continue

            results.append(
                {
                    "workspace_id": meta.get("workspace_id", ""),
                    "workspace_name": meta.get("workspace_name", ""),
                    "message_index": meta.get("message_index", 0),
                    "role": meta.get("role", ""),
                    "timestamp": ts,
                    "excerpt": content,
                    "score": r.get("rerank_score"),
                    "distance": r.get("distance"),
                }
            )
            if len(results) >= n_results:
                break

        return results

    @staticmethod
    def _content_tokens(query: str) -> List[str]:
        """Mots significatifs de la requete pour le matching exact :
        >= 2 lettres et hors mots-outils (sinon "qui", "the"... matchent tout)."""
        return [w for w in (query or "").lower().split()
                if len(w) >= 2 and w not in _STOPWORDS]

    @staticmethod
    def _lexical_match(query: str, content: str) -> bool:
        """True si tous les mots significatifs de la requete apparaissent
        litteralement dans le contenu. Filet par mot-exact, insensible a la
        casse (toutes langues), la ou le reranker anglophone est peu fiable."""
        content_lc = content.lower()
        tokens = ConversationSearch._content_tokens(query)
        if not tokens:
            return False
        return all(tok in content_lc for tok in tokens)

    @staticmethod
    def _result_key(r: dict):
        """Cle d'unicite d'un resultat (workspace + position du message)."""
        meta = r.get("metadata") or {}
        return (meta.get("workspace_id"), meta.get("message_index"))

    def _lexical_full_scan(self, query: str, cap: int = 200) -> List[dict]:
        """Cherche les mots-exacts dans TOUTE la collection (pas seulement les
        plus proches voisins). Insensible a la casse. Retourne des resultats au
        meme format que search_similar (sans distance)."""
        col = self._collection
        tokens = self._content_tokens(query)
        if col is None or not tokens:
            return []
        try:
            data = col.get(include=["documents", "metadatas"])
        except Exception as exc:
            logger.warning("Balayage mot-exact echoue: %s", exc)
            return []

        ids = data.get("ids") or []
        docs = data.get("documents") or []
        metas = data.get("metadatas") or []
        hits: List[dict] = []
        for i, doc in enumerate(docs):
            if not doc:
                continue
            doc_lc = doc.lower()
            if all(tok in doc_lc for tok in tokens):
                hits.append({
                    "chunk_id": ids[i] if i < len(ids) else None,
                    "content": doc,
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": None,
                })
                if len(hits) >= cap:
                    break
        return hits

    def _merge_lexical_hits(self, query: str, raw: List[dict]) -> List[dict]:
        """Ajoute a `raw` les correspondances mot-exact du corpus entier qui ne
        sont pas deja presentes (dedup par workspace+position)."""
        lex = self._lexical_full_scan(query)
        if not lex:
            return raw
        seen = {self._result_key(r) for r in raw}
        for hit in lex:
            key = self._result_key(hit)
            if key not in seen:
                raw.append(hit)
                seen.add(key)
        return raw

    def _filter_by_relevance(self, query: str, raw: List[dict]) -> List[dict]:
        """Ecarte les resultats hors-sujet.

        Le bi-encodeur (MiniLM) ne separe pas bien pertinent/non-pertinent sur
        des requetes courtes ; on s'appuie donc sur le CrossEncoder, bien plus
        discriminant : les requetes sans rapport produisent des scores tres bas
        (~ -11) que le seuil elimine. Un resultat est conserve si :
          - son score CrossEncoder >= seuil, OU
          - il contient litteralement les mots-cles de la requete (filet lexical).
        En l'absence de reranker, repli sur un seuil de distance cosinus.
        """
        reranker = getattr(self.vector_memory, "reranker", None)

        if reranker is None:
            kept = [
                r for r in raw
                if (r.get("distance") is None or r["distance"] <= self.max_distance)
                or self._lexical_match(query, r.get("content", ""))
            ]
            kept.sort(key=lambda r: (r.get("distance")
                                     if r.get("distance") is not None else 1.0))
            return kept

        try:
            pairs = [[query, r.get("content", "")] for r in raw]
            scores = reranker.predict(pairs)
        except Exception as exc:
            logger.warning("Reranking recherche echoue: %s", exc)
            return raw

        kept = []
        for r, s in zip(raw, scores):
            r["rerank_score"] = float(s)
            if r["rerank_score"] >= self.min_rerank_score \
                    or self._lexical_match(query, r.get("content", "")):
                kept.append(r)
        kept.sort(key=lambda r: r["rerank_score"], reverse=True)
        return kept
