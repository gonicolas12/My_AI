"""
Réindexation de la mémoire vectorielle quand le modèle d'embeddings change

Chaque modèle a ses propres collections ChromaDB (core.embedding_engine.
collection_name) : les vecteurs de deux modèles ne sont pas comparables, même à
dimension égale, et ne se mélangent jamais. Au changement de modèle, les
entrées des anciennes collections sont recalculées avec le nouveau, en
arrière-plan, depuis le texte stocké : déchiffré pour le calcul s'il est
chiffré, recopié tel quel (donc toujours chiffré) avec les mêmes identifiants
et métadonnées.

Pendant ce temps :
- les nouvelles entrées vont dans la nouvelle collection, qui gagne toujours
  (une entrée déjà présente n'est jamais écrasée par l'ancienne) ;
- une suppression touche aussi l'ancienne collection, et une modification y
  retire l'entrée, qui vit désormais dans la nouvelle : rien ne revient ;
- la recherche ne voit que ce qui est déjà recalculé.

L'ancienne collection reste intacte jusqu'à la fin de la copie, puis elle est
supprimée. Appli fermée avant : la copie reprend au lancement suivant, là où
elle en était. Une entrée qui ne se recalcule pas (texte chiffré sans sa clé)
garde l'ancienne collection jusqu'au lancement suivant.
"""

import threading
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

# Entrées recalculées à la fois : le modèle reste libre pour les questions de
# l'utilisateur entre deux lots (≈ 0,5 s par lot avec Granite sur CPU)
BATCH_SIZE = 16

_REINDEXERS: Dict[str, "Reindexer"] = {}
_REGISTRY_LOCK = threading.Lock()


def reindexer_for(
    storage_key: str,
    client: Any,
    embed_documents: Callable[[List[str]], Any],
    decrypt: Callable[[str], str],
) -> "Reindexer":
    """
    Réindexeur d'un dossier de stockage, unique dans le processus

    L'appli crée plusieurs VectorMemory sur le même dossier : elles partagent
    la même copie et le même verrou d'écriture.

    Args:
        storage_key: Chemin absolu du dossier de stockage et modèle des vecteurs
        client: Client ChromaDB de ce dossier
        embed_documents: Calcul des vecteurs de passages (liste de textes)
        decrypt: Déchiffrement d'un texte stocké chiffré

    Returns:
        Le réindexeur de ce dossier
    """
    with _REGISTRY_LOCK:
        reindexer = _REINDEXERS.get(storage_key)
        if reindexer is None:
            reindexer = _REINDEXERS[storage_key] = Reindexer(client, embed_documents, decrypt)
        return reindexer


class Reindexer:
    """Copie, en arrière-plan, d'anciennes collections vers celles du modèle actif."""

    def __init__(self, client: Any, embed_documents: Callable[[List[str]], Any],
                 decrypt: Callable[[str], str]):
        self.client = client
        self.embed_documents = embed_documents
        self.decrypt = decrypt
        # Sérialise les écritures de l'appli et celles de la copie
        self.lock = threading.RLock()
        # Collection active -> anciennes collections encore présentes
        self._sources: Dict[str, List[str]] = {}
        # Copies (cible, ancienne) à faire, en cours, finies pendant cette session
        self._todo: List[tuple] = []
        self._current: Optional[tuple] = None
        self._finished: set = set()
        self._collections: Dict[str, Any] = {}
        self._thread: Optional[threading.Thread] = None
        # Changé sous self.lock seulement : start() ne rate jamais une copie
        # annoncée pendant que le thread s'arrête
        self._running = False
        self.copied = 0
        self.total = 0

    # ── Suivi ──────────────────────────────────────────────────────────────

    def add_job(self, target: str, sources: Sequence[str]) -> None:
        """
        Programme la copie des collections `sources` vers `target`

        Une autre VectorMemory du même dossier peut annoncer les mêmes
        collections pendant la copie : elles ne sont ni recopiées ni reprises
        une fois supprimées.
        """
        with self.lock:
            known = self._sources.setdefault(target, [])
            for source in sources:
                job = (target, source)
                if job in self._finished:
                    continue
                if source not in known:
                    known.append(source)
                if job not in self._todo and job != self._current:
                    self._todo.append(job)

    def source_collections(self, target: str) -> List[Any]:
        """Anciennes collections de `target` encore présentes (appelé sous self.lock)."""
        collections = []
        for name in list(self._sources.get(target, ())):
            try:
                collections.append(self._collection(name))
            except Exception:
                # Supprimée entre-temps (mémoire vidée par une autre instance)
                self._sources[target].remove(name)
        return collections

    def is_running(self) -> bool:
        """Vrai pendant une copie."""
        return self._running

    def start(self) -> Optional[threading.Thread]:
        """Lance la copie dans un thread, s'il y a quelque chose à copier."""
        with self.lock:
            if not self._todo or self._running:
                return self._thread
            self._running = True
            self._thread = threading.Thread(target=self._run, name="memory-reindex", daemon=True)
            self._thread.start()
            return self._thread

    def forget(self, target: Optional[str] = None) -> None:
        """Abandonne la copie vers `target` (toutes si None) : mémoire vidée."""
        with self.lock:
            targets = list(self._sources) if target is None else [target]
            for name in targets:
                for source in self._sources.pop(name, []):
                    self._collections.pop(source, None)
            self._todo = [job for job in self._todo if job[0] not in targets]

    # ── Écritures de l'appli pendant la copie (MigratingCollection) ────────

    def adopt(self, target: str, ids: Sequence[str]) -> None:
        """
        Recalcule tout de suite les entrées `ids` pas encore copiées

        Appelé avant une modification : l'entrée doit exister dans la nouvelle
        collection pour y être modifiée.
        """
        with self.lock:
            for source in self.source_collections(target):
                self._copy_ids(source, self._collection(target), list(ids))

    # ── Copie ──────────────────────────────────────────────────────────────

    def _collection(self, name: str):
        collection = self._collections.get(name)
        if collection is None:
            collection = self._collections[name] = self.client.get_collection(name)
        return collection

    def _run(self) -> None:
        while True:
            with self.lock:
                if not self._todo:
                    self._current = None
                    self._running = False
                    return
                self._current = self._todo.pop(0)
                target, source = self._current
            try:
                self._copy_collection(target, source)
            except Exception as exc:
                print(f"⚠️ Réindexation de la collection {source} interrompue ({exc}) : "
                      "nouvel essai au prochain lancement")

    def _copy_collection(self, target_name: str, source_name: str) -> None:
        source = self._collection(source_name)
        target = self._collection(target_name)
        ids = source.get(include=[])["ids"]
        start = time.monotonic()
        if ids:
            print(f"🔄 Réindexation de la mémoire ({source_name} → {target_name}) : "
                  f"{len(ids)} entrée(s), en arrière-plan")
        with self.lock:
            self.total += len(ids)
        failed = 0
        for begin in range(0, len(ids), BATCH_SIZE):
            with self.lock:
                if source_name not in self._sources.get(target_name, ()):
                    return  # mémoire vidée entre-temps
            batch = ids[begin:begin + BATCH_SIZE]
            failed += self._copy_ids(source, target, batch)
            with self.lock:
                self.copied += len(batch)
        with self.lock:
            # Dernière vérification sous verrou : toute entrée de l'ancienne
            # collection doit exister dans la nouvelle avant de la supprimer
            if source_name not in self._sources.get(target_name, ()):
                return
            left = self._missing(source, target)
            if left:
                failed = self._copy_ids(source, target, left)
                left = self._missing(source, target)
            if failed or left:
                print(f"⚠️ {len(left) or failed} entrée(s) de {source_name} non réindexée(s) : "
                      "ancienne collection gardée, nouvel essai au prochain lancement")
                return
            self._sources[target_name].remove(source_name)
            self._finished.add((target_name, source_name))
            self._collections.pop(source_name, None)
            self.client.delete_collection(source_name)
        if ids:
            print(f"✅ Réindexation terminée : {len(ids)} entrée(s) en "
                  f"{time.monotonic() - start:.0f} s ({source_name} supprimée)")

    @staticmethod
    def _missing(source, target) -> List[str]:
        """Entrées de l'ancienne collection absentes de la nouvelle."""
        source_ids = source.get(include=[])["ids"]
        if not source_ids:
            return []
        present = set(target.get(ids=source_ids, include=[])["ids"])
        return [entry_id for entry_id in source_ids if entry_id not in present]

    def _copy_ids(self, source, target, ids: List[str]) -> int:
        """
        Copie les entrées `ids` de `source` vers `target`, vecteurs recalculés

        Returns:
            Nombre d'entrées qui n'ont pas pu être recalculées
        """
        if not ids:
            return 0
        data = source.get(ids=ids, include=["documents", "metadatas"])
        present = set(target.get(ids=data["ids"], include=[])["ids"])
        rows = []
        failed = 0
        for entry_id, stored, metadata in zip(data["ids"], data["documents"], data["metadatas"]):
            if entry_id in present:
                continue
            stored = stored or ""
            try:
                text = self.decrypt(stored) if (metadata or {}).get("encrypted") else stored
            except Exception:
                failed += 1
                continue
            rows.append((entry_id, stored, metadata or None, text))
        if not rows:
            return failed
        # Calcul hors verrou : l'appli peut écrire pendant ce temps
        try:
            vectors = self.embed_documents([row[3] for row in rows])
        except Exception as exc:
            print(f"⚠️ Réindexation : calcul des vecteurs impossible ({exc})")
            return failed + len(rows)
        with self.lock:
            row_ids = [row[0] for row in rows]
            # L'appli a pu supprimer (de l'ancienne) ou réécrire (dans la
            # nouvelle) ces entrées pendant le calcul
            still = set(source.get(ids=row_ids, include=[])["ids"])
            present = set(target.get(ids=row_ids, include=[])["ids"])
            keep = [(row, vector) for row, vector in zip(rows, vectors)
                    if row[0] in still and row[0] not in present]
            if keep:
                target.upsert(
                    ids=[row[0] for row, _ in keep],
                    embeddings=[_as_list(vector) for _, vector in keep],
                    documents=[row[1] for row, _ in keep],
                    metadatas=[row[2] for row, _ in keep],
                )
        return failed


class MigratingCollection:
    """
    Collection active pendant une réindexation

    Lectures inchangées. Écritures sérialisées avec les lots de la copie ;
    suppressions recopiées sur les anciennes collections ; une entrée modifiée
    est d'abord recalculée dans la nouvelle collection, puis retirée de
    l'ancienne. Une fois la copie finie, simple relais vers la collection.
    """

    def __init__(self, collection: Any, reindexer: Reindexer):
        self._collection = collection
        self._reindexer = reindexer

    def __getattr__(self, name: str):
        if name.startswith("__"):
            raise AttributeError(name)
        return getattr(self._collection, name)

    @property
    def wrapped(self):
        """Collection ChromaDB sous-jacente."""
        return self._collection

    def add(self, *args, **kwargs):
        """add() de ChromaDB, sérialisé avec la copie."""
        with self._reindexer.lock:
            return self._collection.add(*args, **kwargs)

    def upsert(self, *args, **kwargs):
        """upsert() de ChromaDB, sérialisé avec la copie."""
        with self._reindexer.lock:
            return self._collection.upsert(*args, **kwargs)

    def update(self, ids, *args, **kwargs):
        """update() de ChromaDB, après avoir recalculé les entrées pas encore copiées."""
        id_list = [ids] if isinstance(ids, str) else list(ids)
        with self._reindexer.lock:
            name = self._collection.name
            if not self._reindexer.source_collections(name):
                return self._collection.update(ids, *args, **kwargs)
            self._reindexer.adopt(name, id_list)
            result = self._collection.update(ids, *args, **kwargs)
            for source in self._reindexer.source_collections(name):
                _quiet_delete(source, ids=id_list)
            return result

    def delete(self, *args, **kwargs):
        """delete() de ChromaDB, recopié sur les anciennes collections."""
        with self._reindexer.lock:
            result = self._collection.delete(*args, **kwargs)
            for source in self._reindexer.source_collections(self._collection.name):
                _quiet_delete(source, *args, **kwargs)
            return result


def _quiet_delete(collection, *args, **kwargs) -> None:
    try:
        collection.delete(*args, **kwargs)
    except Exception as exc:
        print(f"⚠️ Suppression dans l'ancienne collection {getattr(collection, 'name', '?')} "
              f"impossible : {exc}")


def _as_list(vector) -> List[float]:
    return vector.tolist() if hasattr(vector, "tolist") else list(vector)
