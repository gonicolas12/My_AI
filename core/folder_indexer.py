"""
Indexation incrementale d'un DOSSIER ENTIER rattache a un workspace.

Permet d'attacher un dossier (codebase ou dossier de docs) a un workspace de
facon persistante, facon "@codebase" : l'IA garde ce contexte disponible pour
toutes les questions du workspace, sans re-glisser les fichiers a chaque fois.

Principes (calques sur core.conversation_search, qui fait deja de l'indexation
incrementale reutilisant ChromaDB) :
  - 100% local. REUTILISE les processeurs existants (utils.file_processor ->
    processors/) pour l'extraction et le chunking de memory.vector_memory
    (VectorMemory.split_into_chunks). Aucun nouveau pipeline d'embedding.
  - Stockage dans la collection dediee "codebase" de VectorMemory, chaque chunk
    etiquete par workspace_id / folder_path / file_path -> filtrable et purgeable
    par dossier ou par workspace.
  - Indexation INCREMENTALE : un manifeste par workspace garde mtime+taille+hash
    de chaque fichier deja indexe. Au reindex, seuls les fichiers nouveaux ou
    modifies sont re-traites ; les fichiers supprimes sont retires de l'index.
  - Respecte .gitignore (via pathspec si dispo, sinon un matcher integre) et
    exclut par defaut node_modules/, __pycache__/, .git/, .venv/, dist/, etc.
  - Le contexte est lie au workspace : changer de workspace change le contexte
    projet actif (la recherche filtre par workspace_id).
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from core.config import get_config
except Exception:  # pragma: no cover - config optionnelle
    def get_config():
        return None

try:
    from utils.logger import setup_logger
    logger = setup_logger("folder_indexer")
except Exception:  # pragma: no cover - logger optionnel
    import logging
    logger = logging.getLogger("folder_indexer")

# pathspec donne la semantique .gitignore exacte ; sinon repli sur un matcher
# integre (suffisant pour les motifs courants). Aucune dependance dure.
try:
    import pathspec  # type: ignore
    _PATHSPEC_AVAILABLE = True
except Exception:
    _PATHSPEC_AVAILABLE = False


# Version du schema d'indexation : incrementer force une reindexation complete
# (utile quand la LOGIQUE d'indexation change, a donnees inchangees).
_INDEX_SCHEMA = 1

# Dossiers toujours ignores (bruit, binaires, caches) -- meme esprit que .gitignore
# mais garanti meme sans fichier .gitignore.
_DEFAULT_EXCLUDE_DIRS = {
    ".git", ".svn", ".hg", ".bzr",
    "node_modules", "bower_components", "jspm_packages",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
    ".venv", "venv", "env", ".env", "virtualenv",
    "dist", "build", "out", "target", "bin", "obj",
    ".idea", ".vscode", ".vs",
    ".next", ".nuxt", ".svelte-kit", ".cache", ".parcel-cache",
    "coverage", ".nyc_output", "site-packages", "__MACOSX",
    ".gradle", ".terraform", "vendor",
}

# Taille maximale d'un fichier indexe (octets). Au-dela, on saute : un tres gros
# fichier est en general un binaire/asset ou un dump, pas du contexte utile.
_MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 Mo


class _GitignoreMatcher:
    """Matcher .gitignore minimal (repli si pathspec absent).

    Supporte : commentaires, lignes vides, negation (!), motifs ancres a la
    racine (commencant par /), motifs de dossier (finissant par /), jokers
    fnmatch (* ? [..]). Le matching se fait sur le chemin relatif POSIX et sur
    chaque segment, ce qui couvre l'immense majorite des .gitignore reels.
    """

    def __init__(self, patterns: List[str]):
        self._rules: List[tuple[str, bool, bool]] = []  # (motif, negation, ancre)
        for raw in patterns:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            negate = line.startswith("!")
            if negate:
                line = line[1:]
            line = line.strip().rstrip("/")
            if not line:
                continue
            anchored = line.startswith("/")
            if anchored:
                line = line[1:]
            self._rules.append((line, negate, anchored))

    def match(self, rel_posix: str) -> bool:
        """True si le chemin relatif (POSIX) doit etre ignore."""
        ignored = False
        segments = rel_posix.split("/")
        for pattern, negate, anchored in self._rules:
            if self._matches(pattern, rel_posix, segments, anchored):
                ignored = not negate
        return ignored

    @staticmethod
    def _matches(pattern: str, rel_posix: str, segments: List[str],
                 anchored: bool) -> bool:
        # Motif avec / -> compare au chemin complet (depuis la racine du dossier).
        if "/" in pattern:
            return fnmatch.fnmatch(rel_posix, pattern) or fnmatch.fnmatch(
                rel_posix, pattern + "/*"
            )
        # Motif sans / : ancre -> 1er segment seulement ; sinon n'importe quel segment.
        if anchored:
            return fnmatch.fnmatch(segments[0], pattern)
        return any(fnmatch.fnmatch(seg, pattern) for seg in segments)


class FolderIndexer:
    """Indexe des dossiers entiers et les rattache a un workspace (incremental)."""

    def __init__(
        self,
        vector_memory: Any,
        file_processor: Any = None,
        workspaces_dir: str = "data/workspaces",
    ) -> None:
        """
        Args:
            vector_memory: instance de memory.vector_memory.VectorMemory (partagee).
                Sa collection "codebase" et son embedding_model sont reutilises.
            file_processor: instance de utils.file_processor.FileProcessor pour
                l'extraction PDF/DOCX/Excel/code/texte. Cree a la demande si None.
            workspaces_dir: racine des workspaces (pour ranger les manifestes a
                cote de l'etat de chaque workspace).
        """
        self.vector_memory = vector_memory
        self._workspaces_dir = Path(workspaces_dir)
        self._lock = threading.Lock()

        if file_processor is None:
            try:
                from utils.file_processor import FileProcessor
                file_processor = FileProcessor()
            except Exception as exc:  # pragma: no cover
                logger.warning("FileProcessor indisponible: %s", exc)
                file_processor = None
        self.file_processor = file_processor

        try:
            cfg = get_config()
            self._default_n = int(
                cfg.get("optimization.rag.max_retrieved_chunks", 3)
            ) if cfg else 3
        except Exception:
            self._default_n = 3

    # ------------------------------------------------------------------
    # Disponibilite
    # ------------------------------------------------------------------

    @property
    def _collection(self):
        return getattr(self.vector_memory, "codebase_collection", None)

    def is_available(self) -> bool:
        """Exploitable seulement si embedding + collection codebase presents."""
        vm = self.vector_memory
        return bool(
            vm is not None
            and getattr(vm, "embedding_model", None) is not None
            and self._collection is not None
            and self.file_processor is not None
        )

    # ------------------------------------------------------------------
    # Manifeste (mtime/taille/hash par fichier, par workspace)
    # ------------------------------------------------------------------

    def _manifest_path(self, workspace_id: str) -> Path:
        return self._workspaces_dir / workspace_id / "folder_index.json"

    def _load_manifest(self, workspace_id: str) -> Dict[str, Any]:
        """Charge le manifeste d'un workspace : {folder_path: {files: {...}}}.

        Renvoie {} si le schema a change (force une reindexation complete).
        """
        path = self._manifest_path(workspace_id)
        if not path.is_file():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Manifeste folder illisible (%s): %s", workspace_id, exc)
            return {}
        if not isinstance(data, dict) or data.get("schema") != _INDEX_SCHEMA:
            return {}
        folders = data.get("folders", {})
        return folders if isinstance(folders, dict) else {}

    def _save_manifest(self, workspace_id: str, folders: Dict[str, Any]) -> None:
        path = self._manifest_path(workspace_id)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".json.tmp")
            payload = {"schema": _INDEX_SCHEMA, "folders": folders}
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
            tmp.replace(path)
        except OSError as exc:
            logger.warning("Sauvegarde manifeste folder echouee (%s): %s",
                           workspace_id, exc)

    # ------------------------------------------------------------------
    # Parcours du dossier (respect .gitignore + exclusions)
    # ------------------------------------------------------------------

    def _build_ignore(self, root: Path):
        """Construit un matcher d'exclusion a partir du .gitignore du dossier."""
        gitignore = root / ".gitignore"
        patterns: List[str] = []
        if gitignore.is_file():
            try:
                patterns = gitignore.read_text(
                    encoding="utf-8", errors="ignore"
                ).splitlines()
            except OSError:
                patterns = []
        if not patterns:
            return None
        if _PATHSPEC_AVAILABLE:
            try:
                return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
            except Exception:
                pass
        return _GitignoreMatcher(patterns)

    @staticmethod
    def _is_ignored(spec, rel_posix: str) -> bool:
        if spec is None:
            return False
        try:
            if _PATHSPEC_AVAILABLE and isinstance(spec, pathspec.PathSpec):
                return spec.match_file(rel_posix)
        except Exception:
            return False
        return spec.match(rel_posix)

    def _iter_files(self, root: Path) -> List[Path]:
        """Liste les fichiers indexables du dossier (exclusions appliquees)."""
        spec = self._build_ignore(root)
        files: List[Path] = []
        for dirpath, dirnames, filenames in os.walk(root):
            current = Path(dirpath)
            # Elaguer les dossiers exclus IN PLACE (evite de descendre node_modules)
            kept = []
            for d in dirnames:
                if d in _DEFAULT_EXCLUDE_DIRS:
                    continue
                rel = (current / d).relative_to(root).as_posix()
                if self._is_ignored(spec, rel + "/") or self._is_ignored(spec, rel):
                    continue
                kept.append(d)
            dirnames[:] = kept

            for name in filenames:
                fpath = current / name
                rel = fpath.relative_to(root).as_posix()
                if self._is_ignored(spec, rel):
                    continue
                if self.file_processor and not self.file_processor.is_supported(str(fpath)):
                    continue
                try:
                    if fpath.stat().st_size > _MAX_FILE_BYTES:
                        continue
                except OSError:
                    continue
                files.append(fpath)
        return files

    # ------------------------------------------------------------------
    # Index par fichier
    # ------------------------------------------------------------------

    @staticmethod
    def _file_signature(path: Path) -> Optional[Dict[str, Any]]:
        try:
            st = path.stat()
            return {"mtime": int(st.st_mtime), "size": st.st_size}
        except OSError:
            return None

    @staticmethod
    def _file_hash(path: Path) -> str:
        h = hashlib.md5()
        try:
            with open(path, "rb") as fh:
                for block in iter(lambda: fh.read(65536), b""):
                    h.update(block)
        except OSError:
            return ""
        return h.hexdigest()

    @staticmethod
    def _chunk_id(workspace_id: str, folder_path: str, rel_path: str, idx: int) -> str:
        digest = hashlib.md5(
            f"{workspace_id}|{folder_path}|{rel_path}".encode("utf-8")
        ).hexdigest()
        return f"cb_{digest}_{idx}"

    def _delete_file_entries(self, workspace_id: str, folder_path: str,
                             rel_path: str) -> None:
        col = self._collection
        if col is None:
            return
        try:
            col.delete(where={"$and": [
                {"workspace_id": workspace_id},
                {"folder_path": folder_path},
                {"file_path": rel_path},
            ]})
        except Exception as exc:
            logger.warning("Purge chunks fichier echouee (%s): %s", rel_path, exc)

    def _delete_folder_entries(self, workspace_id: str, folder_path: str) -> None:
        col = self._collection
        if col is None:
            return
        try:
            col.delete(where={"$and": [
                {"workspace_id": workspace_id},
                {"folder_path": folder_path},
            ]})
        except Exception as exc:
            logger.warning("Purge chunks dossier echouee (%s): %s", folder_path, exc)

    def _index_file(self, workspace_id: str, folder_path: str, root: Path,
                    fpath: Path) -> int:
        """(Re)indexe un fichier. Retourne le nombre de chunks crees."""
        col = self._collection
        vm = self.vector_memory
        rel_path = fpath.relative_to(root).as_posix()

        result = self.file_processor.process_file(str(fpath))
        if not isinstance(result, dict) or result.get("error"):
            return 0
        content = (result.get("content") or "").strip()
        if not content:
            return 0

        chunks = vm.split_into_chunks(content)
        if not chunks:
            return 0

        # Repartir de zero pour ce fichier (gere editions/suppressions de chunks)
        self._delete_file_entries(workspace_id, folder_path, rel_path)

        ids: List[str] = []
        embeddings: List[list] = []
        documents: List[str] = []
        metadatas: List[dict] = []
        now = datetime.now().isoformat()
        for i, chunk_text in enumerate(chunks):
            ids.append(self._chunk_id(workspace_id, folder_path, rel_path, i))
            embeddings.append(vm.embedding_model.encode(chunk_text).tolist())
            documents.append(chunk_text)
            metadatas.append({
                "kind": "codebase",
                "workspace_id": workspace_id,
                "folder_path": folder_path,
                "file_path": rel_path,
                "file_name": fpath.name,
                "chunk_index": i,
                "indexed_at": now,
            })

        try:
            col.add(ids=ids, embeddings=embeddings, documents=documents,
                    metadatas=metadatas)
        except Exception as exc:
            logger.error("Indexation fichier '%s' echouee: %s", rel_path, exc)
            return 0
        return len(ids)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def index_folder(
        self,
        workspace_id: str,
        folder_path: str,
        force: bool = False,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
    ) -> Dict[str, Any]:
        """Attache et (re)indexe un dossier dans un workspace, de facon incrementale.

        Args:
            workspace_id: identifiant du workspace cible.
            folder_path: chemin (absolu de preference) du dossier a indexer.
            force: si True, reindexe tous les fichiers sans tenir compte du manifeste.
            progress_cb: callback(done, total, current_rel_path) pour la progression.

        Returns:
            {"status", "folder", "files_indexed", "files_skipped", "files_removed",
             "chunks", "total_files"} ; "status" = "success" | "error" | "unavailable".
        """
        if not self.is_available():
            return {"status": "unavailable", "folder": folder_path,
                    "files_indexed": 0, "chunks": 0}

        root = Path(folder_path).expanduser()
        try:
            root = root.resolve()
        except OSError:
            pass
        if not root.is_dir():
            return {"status": "error", "folder": str(folder_path),
                    "error": "Dossier introuvable", "files_indexed": 0, "chunks": 0}

        folder_key = root.as_posix()

        with self._lock:
            manifest = self._load_manifest(workspace_id)
            folder_entry = manifest.get(folder_key, {}) if not force else {}
            old_files: Dict[str, Any] = folder_entry.get("files", {}) if isinstance(
                folder_entry, dict) else {}

            files = self._iter_files(root)
            total = len(files)
            new_files: Dict[str, Any] = {}
            indexed = skipped = chunks = 0

            for done, fpath in enumerate(files, 1):
                rel = fpath.relative_to(root).as_posix()
                if progress_cb:
                    try:
                        progress_cb(done, total, rel)
                    except Exception:
                        pass

                sig = self._file_signature(fpath)
                if sig is None:
                    continue
                prev = old_files.get(rel)

                # Chemin rapide : mtime + taille inchanges -> on garde tel quel.
                if (not force and prev
                        and prev.get("mtime") == sig["mtime"]
                        and prev.get("size") == sig["size"]):
                    new_files[rel] = prev
                    skipped += 1
                    continue

                # mtime/taille different : verifier le hash (evite un re-embedding
                # si le contenu est identique, ex. apres un git checkout).
                file_hash = self._file_hash(fpath)
                if (not force and prev and prev.get("hash")
                        and prev.get("hash") == file_hash):
                    new_files[rel] = {**sig, "hash": file_hash,
                                      "chunks": prev.get("chunks", 0)}
                    skipped += 1
                    continue

                n = self._index_file(workspace_id, folder_key, root, fpath)
                new_files[rel] = {**sig, "hash": file_hash, "chunks": n}
                indexed += 1
                chunks += n

            # Fichiers disparus depuis le dernier index -> purge de leurs chunks.
            removed = 0
            for rel in list(old_files.keys()):
                if rel not in new_files:
                    self._delete_file_entries(workspace_id, folder_key, rel)
                    removed += 1

            manifest[folder_key] = {
                "files": new_files,
                "indexed_at": datetime.now().isoformat(),
                "file_count": len(new_files),
            }
            self._save_manifest(workspace_id, manifest)

        logger.info(
            "Index dossier '%s' (ws=%s): %d indexes, %d inchanges, %d retires, %d chunks",
            folder_key, workspace_id, indexed, skipped, removed, chunks,
        )
        return {
            "status": "success",
            "folder": folder_key,
            "files_indexed": indexed,
            "files_skipped": skipped,
            "files_removed": removed,
            "chunks": chunks,
            "total_files": len(new_files),
        }

    def reindex(
        self,
        workspace_id: str,
        folder_path: Optional[str] = None,
        force: bool = False,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
    ) -> Dict[str, Any]:
        """Reindexe un dossier precis, ou tous les dossiers attaches du workspace.

        Returns:
            Agregat {"status", "folders", "files_indexed", "chunks", ...}.
        """
        if folder_path is not None:
            res = self.index_folder(workspace_id, folder_path, force=force,
                                    progress_cb=progress_cb)
            res["folders"] = 1 if res.get("status") == "success" else 0
            return res

        folders = self.list_folders(workspace_id)
        agg = {"status": "success", "folders": 0, "files_indexed": 0,
               "files_removed": 0, "chunks": 0, "total_files": 0}
        for folder in folders:
            r = self.index_folder(workspace_id, folder, force=force,
                                  progress_cb=progress_cb)
            if r.get("status") == "success":
                agg["folders"] += 1
                agg["files_indexed"] += r.get("files_indexed", 0)
                agg["files_removed"] += r.get("files_removed", 0)
                agg["chunks"] += r.get("chunks", 0)
                agg["total_files"] += r.get("total_files", 0)
        return agg

    def remove_folder(self, workspace_id: str, folder_path: str) -> bool:
        """Detache un dossier : purge ses chunks et l'efface du manifeste."""
        root = Path(folder_path).expanduser()
        try:
            root = root.resolve()
        except OSError:
            pass
        folder_key = root.as_posix()
        with self._lock:
            manifest = self._load_manifest(workspace_id)
            # Tolerance : accepter aussi la cle telle quelle si non resolue.
            key = folder_key if folder_key in manifest else (
                folder_path if folder_path in manifest else folder_key
            )
            self._delete_folder_entries(workspace_id, key)
            existed = key in manifest
            manifest.pop(key, None)
            self._save_manifest(workspace_id, manifest)
        logger.info("Dossier detache '%s' (ws=%s)", folder_key, workspace_id)
        return existed

    def list_folders(self, workspace_id: str) -> List[str]:
        """Liste les chemins des dossiers attaches au workspace."""
        return list(self._load_manifest(workspace_id).keys())

    def get_status(self, workspace_id: str) -> Dict[str, Any]:
        """Etat indexe du workspace : dossiers, nb de fichiers, date d'index.

        Returns:
            {"folders": [{"path", "file_count", "chunks", "indexed_at"}],
             "total_files", "total_chunks"}.
        """
        manifest = self._load_manifest(workspace_id)
        folders = []
        total_files = total_chunks = 0
        for path, entry in manifest.items():
            files = entry.get("files", {}) if isinstance(entry, dict) else {}
            n_chunks = sum(int(f.get("chunks", 0)) for f in files.values())
            folders.append({
                "path": path,
                "file_count": len(files),
                "chunks": n_chunks,
                "indexed_at": entry.get("indexed_at", "") if isinstance(entry, dict) else "",
            })
            total_files += len(files)
            total_chunks += n_chunks
        return {"folders": folders, "total_files": total_files,
                "total_chunks": total_chunks}

    def search(
        self,
        workspace_id: str,
        query: str,
        n_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Recherche semantique dans les dossiers attaches AU workspace courant.

        Filtre par workspace_id cote ChromaDB : changer de workspace change le
        contexte projet actif. Reutilise le reranking CrossEncoder de VectorMemory.

        Returns:
            Liste de chunks {content, metadata, distance, rerank_score?}.
        """
        if not self.is_available() or not query or not query.strip():
            return []
        n = n_results if n_results is not None else self._default_n
        try:
            return self.vector_memory.search_similar(
                query, n_results=n, collection_type="codebase",
                rerank=True, where={"workspace_id": workspace_id},
            ) or []
        except Exception as exc:
            logger.warning("Recherche codebase echouee (ws=%s): %s", workspace_id, exc)
            return []

    def get_relevant_context(
        self,
        workspace_id: str,
        query: str,
        n_results: Optional[int] = None,
    ) -> str:
        """Contexte projet consolide (texte) pour injection au moment de la question.

        Returns:
            Bloc texte par chunk, prefixe du fichier d'origine, ou "" si rien.
        """
        results = self.search(workspace_id, query, n_results=n_results)
        if not results:
            return ""
        parts = []
        for res in results:
            meta = res.get("metadata", {}) or {}
            name = meta.get("file_path") or meta.get("file_name") or "fichier"
            parts.append(f"--- {name} ---\n{res.get('content', '')}")
        return "\n\n".join(parts)
