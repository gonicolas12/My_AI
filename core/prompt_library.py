"""
Bibliothèque de prompts réutilisables et slash commands.

Un *template* est un prompt nommé, éventuellement doté d'un déclencheur `/`
(slash command) et de placeholders `{nom}`. Les templates ayant une commande
apparaissent dans l'autocomplétion de la zone de saisie ; tous sont gérables
depuis l'UI (créer / nommer / éditer / supprimer).

Persistance 100 % locale en JSON (cohérent avec data/custom_agents.json).
Thread-safe : le serveur Relay lit la bibliothèque depuis un autre thread que
le GUI.
"""

from __future__ import annotations

import json
import re
import threading
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import setup_logger

logger = setup_logger("prompt_library")

# Placeholders de la forme {nom} — on capture le nom sans les accolades.
_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")

# Placeholder spécial remplacé par le texte saisi après la commande
# (ex. « /code un jeu de morpion » → {arguments} = « un jeu de morpion »).
_ARGS_PLACEHOLDER = "{arguments}"

# Slash commands par défaut : ce sont des *wrappers de prompt engineering*.
# La commande visible reste courte (« /code un jeu de morpion ») mais l'IA
# reçoit le `content` détaillé, avec {arguments} remplacé par le texte saisi.
_DEFAULT_TEMPLATES: List[Dict[str, str]] = [
    {
        "id": "code",
        "command": "code",
        "title": "Génération de code",
        "description": "Génère un programme complet et commenté",
        "content": (
            "Tu es un développeur logiciel expert. Écris un programme complet, "
            "fonctionnel et prêt à l'emploi pour répondre à la demande suivante :\n\n"
            "{arguments}\n\n"
            "Exigences :\n"
            "- Choisis le langage le plus adapté si rien n'est précisé, et indique-le.\n"
            "- Code clair, idiomatique et commenté.\n"
            "- Gère les cas limites et les erreurs éventuelles.\n"
            "- Termine par un court mode d'emploi (comment lancer / utiliser)."
        ),
    },
    {
        "id": "resume",
        "command": "résume",
        "title": "Résumé",
        "description": "Résume le texte ou le sujet fourni",
        "content": (
            "Résume de façon claire, fidèle et concise le contenu suivant :\n\n"
            "{arguments}\n\n"
            "Donne d'abord un résumé en 2 à 3 phrases, puis les points clés "
            "sous forme de liste à puces."
        ),
    },
    {
        "id": "traduis",
        "command": "traduis",
        "title": "Traduction",
        "description": "Traduit le texte fourni",
        "content": (
            "Traduis le texte suivant. Si une langue cible est indiquée, utilise-la ; "
            "sinon, traduis en anglais. Conserve le sens, le ton et la mise en forme.\n\n"
            "{arguments}\n\n"
            "Donne uniquement la traduction, sans commentaire."
        ),
    },
    {
        "id": "explique",
        "command": "explique",
        "title": "Explication",
        "description": "Explique un concept simplement",
        "content": (
            "Explique de façon simple et pédagogique le sujet suivant :\n\n"
            "{arguments}\n\n"
            "Utilise une analogie du quotidien et un exemple concret, puis termine "
            "par un résumé en une phrase. Adapte-toi à un débutant."
        ),
    },
    {
        "id": "corrige",
        "command": "corrige",
        "title": "Correction",
        "description": "Corrige l'orthographe et la grammaire",
        "content": (
            "Corrige l'orthographe, la grammaire, la conjugaison et la ponctuation "
            "du texte suivant, sans en changer le sens ni le style :\n\n"
            "{arguments}\n\n"
            "Donne d'abord le texte corrigé, puis la liste des corrections importantes."
        ),
    },
    {
        "id": "reformule",
        "command": "reformule",
        "title": "Reformulation",
        "description": "Reformule un texte plus clairement",
        "content": (
            "Reformule le texte suivant pour le rendre plus clair, fluide et "
            "professionnel, sans en changer le sens :\n\n"
            "{arguments}\n\n"
            "Propose la version reformulée, puis une variante plus concise."
        ),
    },
]


class PromptLibrary:
    """Gestionnaire CRUD + persistance JSON de la bibliothèque de prompts."""

    def __init__(self, path: str = "data/prompt_templates.json") -> None:
        """
        Initialise la bibliothèque et charge les templates depuis le disque.

        Args:
            path: Chemin du fichier JSON de persistance. S'il est absent ou
                  illisible, les commandes par défaut sont seedées.
        """
        self._path = Path(path)
        self._lock = threading.RLock()
        self._templates: List[Dict[str, Any]] = []
        self._load()
        logger.info(
            "PromptLibrary initialisée (%d templates, fichier=%s)",
            len(self._templates), path,
        )

    # ------------------------------------------------------------------
    # Helpers statiques
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(text: str) -> str:
        """Minuscule + suppression des accents (pour un matching tolérant).

        Permet à `/resume` de correspondre à `/résume`.
        """
        decomposed = unicodedata.normalize("NFD", text or "")
        stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
        return stripped.strip().lower()

    @staticmethod
    def _slugify(text: str) -> str:
        """Construit un identifiant ASCII stable à partir d'un texte."""
        base = PromptLibrary._normalize(text)
        base = re.sub(r"[^a-z0-9]+", "_", base).strip("_")
        return base or "prompt"

    @staticmethod
    def _clean_command(command: Optional[str]) -> str:
        """Nettoie une commande : retire le `/` initial, garde un seul token."""
        if not command:
            return ""
        cmd = command.strip()
        if cmd.startswith("/"):
            cmd = cmd[1:]
        cmd = cmd.strip()
        if not cmd:
            return ""
        # Une slash command est un mot unique (pas d'espace).
        return cmd.split()[0]

    @staticmethod
    def extract_placeholders(content: str) -> List[str]:
        """Retourne la liste ordonnée et unique des placeholders `{nom}`."""
        seen: List[str] = []
        for match in _PLACEHOLDER_RE.finditer(content or ""):
            name = match.group(1).strip()
            if name and name not in seen:
                seen.append(name)
        return seen

    # ------------------------------------------------------------------
    # Chargement / sauvegarde
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Charge les templates ; seede les défauts si le fichier est absent/illisible."""
        if not self._path.exists():
            self._templates = [self._make_default(d) for d in _DEFAULT_TEMPLATES]
            self._save_unlocked()
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            logger.warning("prompt_templates.json illisible (%s) → seed des défauts", exc)
            self._templates = [self._make_default(d) for d in _DEFAULT_TEMPLATES]
            self._save_unlocked()
            return
        # Tolérance de format : liste directe ou {"templates": [...]}.
        if isinstance(raw, dict):
            raw = raw.get("templates", [])
        if not isinstance(raw, list):
            raw = []
        self._templates = [self._coerce(t) for t in raw if isinstance(t, dict)]
        self._sync_builtins()

    def _sync_builtins(self) -> None:
        """Met à jour le contenu des templates builtin existants depuis le code.

        Sert à migrer les prompts par défaut (ex. ancien format `{texte}` → wrapper
        `{arguments}`). N'insère ni ne supprime aucun template, et ne touche pas aux
        templates personnalisés (builtin=False) : une commande supprimée ou éditée
        par l'utilisateur reste telle quelle.
        """
        defaults = {d["id"]: d for d in _DEFAULT_TEMPLATES}
        changed = False
        for tpl in self._templates:
            if not tpl.get("builtin"):
                continue
            default = defaults.get(tpl["id"])
            if default is None:
                continue
            new_vals = {
                "command": default.get("command") or None,
                "title": default["title"],
                "description": default.get("description", ""),
                "content": default["content"],
            }
            if any(tpl.get(key) != val for key, val in new_vals.items()):
                tpl.update(new_vals)
                tpl["updated_at"] = datetime.now().isoformat()
                changed = True
        if changed:
            self._save_unlocked()

    def _save_unlocked(self) -> None:
        """Écrit les templates sur le disque (suppose le lock déjà tenu)."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._templates, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Échec sauvegarde des prompts : %s", exc)

    def save(self) -> None:
        """Persiste explicitement la bibliothèque (les mutations le font déjà)."""
        with self._lock:
            self._save_unlocked()

    @staticmethod
    def _make_default(data: Dict[str, str]) -> Dict[str, Any]:
        """Construit un template par défaut complet (builtin=True)."""
        now = datetime.now().isoformat()
        return {
            "id": data["id"],
            "command": data.get("command") or None,
            "title": data["title"],
            "description": data.get("description", ""),
            "content": data["content"],
            "builtin": True,
            "created_at": now,
            "updated_at": now,
        }

    @staticmethod
    def _coerce(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise un template lu du disque (rétro/forward compat)."""
        now = datetime.now().isoformat()
        command = PromptLibrary._clean_command(data.get("command")) or None
        title = (
            data.get("title")
            or (command or "")
            or str(data.get("id") or "Sans titre")
        )
        return {
            "id": str(data.get("id") or PromptLibrary._slugify(title)),
            "command": command,
            "title": title,
            "description": data.get("description", "") or "",
            "content": data.get("content", "") or "",
            "builtin": bool(data.get("builtin", False)),
            "created_at": data.get("created_at") or now,
            "updated_at": data.get("updated_at") or now,
        }

    # ------------------------------------------------------------------
    # Accès interne (lock déjà tenu)
    # ------------------------------------------------------------------

    def _get_unlocked(self, template_id: str) -> Optional[Dict[str, Any]]:
        for tpl in self._templates:
            if tpl["id"] == template_id:
                return tpl
        return None

    def _find_by_command_unlocked(self, command: str) -> Optional[Dict[str, Any]]:
        if not command:
            return None
        target = self._normalize(command)
        for tpl in self._templates:
            cmd = tpl.get("command")
            if cmd and self._normalize(cmd) == target:
                return tpl
        return None

    def _unique_id(self, seed: str) -> str:
        base = self._slugify(seed)
        existing = {t["id"] for t in self._templates}
        if base not in existing:
            return base
        counter = 2
        while f"{base}_{counter}" in existing:
            counter += 1
        return f"{base}_{counter}"

    # ------------------------------------------------------------------
    # API publique de lecture
    # ------------------------------------------------------------------

    def list(self) -> List[Dict[str, Any]]:
        """Retourne tous les templates (copies), dans l'ordre d'insertion."""
        with self._lock:
            return [dict(t) for t in self._templates]

    def get(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Retourne un template par identifiant (copie) ou ``None``."""
        with self._lock:
            tpl = self._get_unlocked(template_id)
            return dict(tpl) if tpl else None

    def find_by_command(self, command: str) -> Optional[Dict[str, Any]]:
        """Retourne le template correspondant à une commande (accent-insensible)."""
        with self._lock:
            tpl = self._find_by_command_unlocked(self._clean_command(command))
            return dict(tpl) if tpl else None

    def search(self, prefix: str) -> List[Dict[str, Any]]:
        """Templates dont la commande commence par ``prefix`` (pour l'autocomplétion).

        ``prefix`` peut contenir ou non le `/` initial. Un préfixe vide renvoie
        toutes les commandes. Insensible aux accents et à la casse.
        """
        norm = self._normalize(self._clean_command(prefix)) if prefix else ""
        with self._lock:
            matches = [
                dict(t)
                for t in self._templates
                if t.get("command") and self._normalize(t["command"]).startswith(norm)
            ]
        matches.sort(key=lambda t: self._normalize(t["command"]))
        return matches

    # ------------------------------------------------------------------
    # Expansion (prompt engineering)
    # ------------------------------------------------------------------

    def expand(self, text: str) -> Optional[str]:
        """Transforme « /commande arguments » en prompt détaillé pour l'IA.

        L'utilisateur tape une commande courte (ex. « /code un jeu de morpion ») ;
        l'IA reçoit le `content` du template avec le texte saisi injecté à la place
        de ``{arguments}`` (ou ajouté à la suite si le template n'a pas ce
        placeholder).

        Returns:
            Le prompt étendu, ou ``None`` si ``text`` n'est pas une slash command
            connue (dans ce cas l'appelant envoie le texte tel quel).
        """
        if not text:
            return None
        stripped = text.lstrip()
        if not stripped.startswith("/"):
            return None
        match = re.match(r"^/(\S+)\s*(.*)$", stripped, re.DOTALL)
        if not match:
            return None
        command, args = match.group(1), match.group(2).strip()
        tpl = self.find_by_command(command)
        if tpl is None:
            return None
        return self.render(tpl, args)

    @staticmethod
    def render(tpl: Dict[str, Any], args: str) -> str:
        """Injecte ``args`` dans le contenu d'un template.

        - Si le contenu contient ``{arguments}``, on le remplace par ``args``.
        - Sinon, ``args`` (s'il est non vide) est ajouté à la suite du contenu.
        """
        content = tpl.get("content", "") or ""
        args = args or ""
        if _ARGS_PLACEHOLDER in content:
            return content.replace(_ARGS_PLACEHOLDER, args)
        if args:
            return content.rstrip() + "\n\n" + args
        return content

    # ------------------------------------------------------------------
    # API publique de mutation (persistance automatique)
    # ------------------------------------------------------------------

    def add(
        self,
        title: str,
        content: str,
        command: Optional[str] = None,
        description: str = "",
        builtin: bool = False,
    ) -> Dict[str, Any]:
        """
        Crée un template et persiste la bibliothèque.

        Args:
            title: Nom affiché du template.
            content: Corps du prompt (peut contenir des placeholders ``{nom}``).
            command: Slash command optionnelle (sans le `/`). Doit être unique.
            description: Courte description.
            builtin: Marque le template comme fourni par défaut.

        Returns:
            Le template créé (copie).

        Raises:
            ValueError: Si la commande est déjà utilisée.
        """
        with self._lock:
            cmd = self._clean_command(command)
            if cmd and self._find_by_command_unlocked(cmd):
                raise ValueError(f"La commande /{cmd} existe déjà.")
            now = datetime.now().isoformat()
            tpl = {
                "id": self._unique_id(cmd or title),
                "command": cmd or None,
                "title": (title or cmd or "Sans titre").strip(),
                "description": (description or "").strip(),
                "content": content or "",
                "builtin": bool(builtin),
                "created_at": now,
                "updated_at": now,
            }
            self._templates.append(tpl)
            self._save_unlocked()
            return dict(tpl)

    def update(self, template_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
        """
        Met à jour les champs d'un template existant et persiste.

        Champs acceptés : ``title``, ``command``, ``description``, ``content``.

        Returns:
            Le template mis à jour (copie), ou ``None`` s'il n'existe pas.

        Raises:
            ValueError: Si la nouvelle commande est déjà utilisée ailleurs.
        """
        with self._lock:
            tpl = self._get_unlocked(template_id)
            if tpl is None:
                return None
            if "command" in fields:
                cmd = self._clean_command(fields["command"])
                clash = self._find_by_command_unlocked(cmd) if cmd else None
                if clash and clash["id"] != template_id:
                    raise ValueError(f"La commande /{cmd} existe déjà.")
                tpl["command"] = cmd or None
            if fields.get("title") is not None:
                tpl["title"] = str(fields["title"]).strip() or tpl["title"]
            if fields.get("description") is not None:
                tpl["description"] = str(fields["description"]).strip()
            if fields.get("content") is not None:
                tpl["content"] = str(fields["content"])
            # Une fois édité par l'utilisateur, un template par défaut devient
            # « personnel » : la migration des builtins ne l'écrasera plus.
            tpl["builtin"] = False
            tpl["updated_at"] = datetime.now().isoformat()
            self._save_unlocked()
            return dict(tpl)

    def delete(self, template_id: str) -> bool:
        """Supprime un template et persiste. Retourne ``True`` si supprimé."""
        with self._lock:
            before = len(self._templates)
            self._templates = [t for t in self._templates if t["id"] != template_id]
            changed = len(self._templates) != before
            if changed:
                self._save_unlocked()
            return changed
