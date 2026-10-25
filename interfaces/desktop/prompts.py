"""
Prompts de la fenêtre (prompts_panel.py de Tk)

Bibliothèque de prompts réutilisables du moteur (core/prompt_library.py) :
liste, création, modification, suppression. Les prompts dotés d'une commande
« /xxx » apparaissent dans l'autocomplétion de la zone de saisie
(/api/prompts/commands).
"""

from typing import Any, Callable, Dict, List, Optional

from core.i18n import tr


class PromptsError(Exception):
    """Action refusée ou en échec : message affiché."""


def _view(template: Dict[str, Any]) -> Dict[str, Any]:
    """Prompt pour la fenêtre."""
    return {
        "id": template.get("id"),
        "command": template.get("command") or None,
        "title": template.get("title") or "",
        "description": template.get("description") or "",
        "content": template.get("content") or "",
        "builtin": bool(template.get("builtin")),
    }


class PromptsService:
    """Lecture et modification de la bibliothèque de prompts."""

    def __init__(self, engine: Callable[[], Optional[Any]]):
        """
        Args:
            engine: moteur en cours (None pendant le lancement)
        """
        self._engine = engine

    def _library(self):
        library = getattr(self._engine(), "prompt_library", None)
        if library is None:
            raise PromptsError(tr("prompts.unavailable"))
        return library

    def list(self) -> List[Dict[str, Any]]:
        """Tous les prompts, dans l'ordre de la bibliothèque."""
        return [_view(template) for template in self._library().list()]

    def save(self, template_id: Optional[str], fields: Dict[str, str]) -> Dict[str, Any]:
        """
        Crée (template_id None) ou modifie un prompt, avec les contrôles du formulaire Tk.

        Args:
            fields: title, command, description, content
        """
        title, command, description, content = (
            (fields.get(name) or "").strip()
            for name in ("title", "command", "description", "content"))
        if not title and not command:
            raise PromptsError(tr("prompts.nameOrCommand"))
        if not content:
            raise PromptsError(tr("prompts.emptyContent"))
        library = self._library()
        try:
            if template_id is None:
                template = library.add(title=title or command, content=content,
                                       command=command or None, description=description)
            else:
                template = library.update(template_id, title=title, command=command,
                                          description=description, content=content)
        except ValueError as exc:
            # Commande déjà prise : « La commande /xxx existe déjà. »
            raise PromptsError(str(exc)) from exc
        if template is None:
            raise PromptsError(tr("prompts.notFound"))
        return _view(template)

    def delete(self, template_id: str) -> None:
        """Supprime un prompt."""
        if not self._library().delete(template_id):
            raise PromptsError(tr("prompts.notFound"))
