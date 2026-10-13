"""
Pages d'aperçu du volet de droite : artefacts HTML/SVG et documents

Chaque aperçu est une page servie par le serveur local (GET /preview/<id>) et
affichée dans une iframe isolée (sandbox sans allow-same-origin) : elle ne
peut ni lire la page de l'appli ni appeler son API. La page porte sa propre
politique de sécurité, qui l'isole aussi si on l'ouvrait hors de l'iframe :
  - un artefact garde ses scripts et peut charger des ressources externes
    (CDN, polices), comme dans l'interface Tk (D8) ;
  - l'aperçu HTML d'un document (interfaces/document_preview.py) n'exécute
    aucun script.

Un PDF n'a pas de page d'aperçu : la fenêtre l'affiche avec le lecteur de
WebView2, par un lien signé vers le fichier (files.py).
"""

import threading
import time
import uuid
import webbrowser
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from interfaces.artifacts import ARTIFACTS_DIR, Artifact, build_preview_document
from utils.logger import setup_logger

logger = setup_logger("DesktopPreviews")

PREVIEW_PREFIX = "/preview/"

# Artefact : scripts et ressources externes permis, origine opaque (pas de
# allow-same-origin), formulaires et fenêtres surgissantes comme dans un onglet
ARTIFACT_CSP = "sandbox allow-scripts allow-forms allow-modals allow-popups"
# Document rendu en HTML : aucun script, aucune requête
DOCUMENT_CSP = (
    "sandbox; default-src 'none'; style-src 'unsafe-inline'; "
    "img-src data:; font-src data:"
)

# Aperçus gardés en mémoire (les plus anciens sont oubliés)
_CAPACITY = 64


@dataclass
class Preview:
    """Aperçu affichable dans le volet."""

    id: str
    kind: str  # html, svg (artefacts), document, pdf
    title: str
    html: Optional[str] = None  # page servie ; None pour un PDF
    source_path: Optional[str] = None  # document d'origine
    language: str = ""
    index: int = 0

    @property
    def csp(self) -> str:
        """Politique de sécurité de la page servie."""
        return DOCUMENT_CSP if self.kind == "document" else ARTIFACT_CSP


class PreviewStore:
    """Aperçus créés pendant ce lancement, servis par GET /preview/<id>."""

    def __init__(self, capacity: int = _CAPACITY, directory: Optional[Path] = None):
        self._capacity = capacity
        self._directory = Path(directory) if directory else ARTIFACTS_DIR
        self._items: "OrderedDict[str, Preview]" = OrderedDict()
        self._lock = threading.Lock()

    def _add(self, preview: Preview) -> Preview:
        with self._lock:
            self._items[preview.id] = preview
            while len(self._items) > self._capacity:
                self._items.popitem(last=False)
        return preview

    def get(self, preview_id: str) -> Optional[Preview]:
        """Aperçu par identifiant (None s'il est inconnu ou oublié)."""
        with self._lock:
            return self._items.get(preview_id)

    def add_artifact(self, code: str, kind: str, title: str = "",
                     language: str = "", index: int = 0) -> Preview:
        """Page d'un bloc HTML ou SVG d'une réponse (build_preview_document)."""
        if kind not in ("html", "svg"):
            raise ValueError(f"Type d'artefact inconnu : {kind}")
        artifact = Artifact(kind=kind, code=code or "", title=title or "Aperçu",
                            language=language or kind, index=index)
        return self._add(Preview(
            id=uuid.uuid4().hex, kind=kind, title=artifact.title,
            html=build_preview_document(artifact), language=artifact.language, index=index,
        ))

    def add_document(self, path: str) -> Preview:
        """Aperçu d'un document : page HTML, ou le PDF lui-même.

        Raises:
            ValueError: format sans aperçu
        """
        # pylint: disable=import-outside-toplevel
        from interfaces.document_preview import (build_document_preview, is_previewable,
                                                 needs_native_viewer)

        name = Path(path).name
        if needs_native_viewer(path):
            return self._add(Preview(id=uuid.uuid4().hex, kind="pdf", title=name,
                                     source_path=path))
        if not is_previewable(path):
            raise ValueError(f"Pas d'aperçu pour ce format : {Path(path).suffix or name}")
        return self._add(Preview(id=uuid.uuid4().hex, kind="document", title=name,
                                 html=build_document_preview(path), source_path=path))

    def write_file(self, preview: Preview) -> Path:
        """Fichier de l'aperçu pour le navigateur (outputs/artifacts/, comme Tk).

        Un PDF est ouvert tel quel.
        """
        if preview.kind == "pdf" and preview.source_path:
            return Path(preview.source_path)
        self._directory.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        target = self._directory / f"artifact_{stamp}_{preview.index}.html"
        target.write_text(preview.html or "", encoding="utf-8")
        return target

    def open_in_browser(self, preview_id: str) -> str:
        """Ouvre l'aperçu dans le navigateur du système ; renvoie le fichier ouvert.

        Raises:
            KeyError: aperçu inconnu
        """
        preview = self.get(preview_id)
        if preview is None:
            raise KeyError(preview_id)
        target = self.write_file(preview)
        webbrowser.open(target.resolve().as_uri())
        return str(target)
