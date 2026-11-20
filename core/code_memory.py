"""
Mémoire de My_AI dans la conversation Code (relay/code_hub.py) : l'extension
VS Code, la page Code du PC et la vue Code du téléphone.

Elle est cloisonnée par portée (core/knowledge_base_manager.py, SCOPES) :
  - les faits retenus pour le code (« code » : tous les projets ; « project » :
    l'un des dossiers ouverts dans VS Code) vont d'office dans le prompt système
    (prompt_block). Ceux du chat (nom, famille, consignes de ton…) n'y vont pas :
    un modèle qui les a sous les yeux les place n'importe où, jusque dans les
    fichiers qu'il écrit (« Auteur : … Chat : … » en tête d'un script de tri,
    voir AIEngine._generation_memory) ;
  - « retiens que… » est enregistré pour le premier dossier ouvert, ou pour
    tous les projets quand le message le dit (remember). Seul le message de
    l'utilisateur est lu, jamais un fichier du workspace ni un résultat
    d'outil : une phrase glissée dans un README ne peut pas écrire dans sa
    mémoire, que le chat applique ensuite en priorité ;
  - l'outil search_memory, exécuté sur le PC (search) : faits du chat, du code
    et de ces dossiers, et documents de la fenêtre Mémoire.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from core.knowledge_base_manager import (
    SCOPE_CODE,
    SCOPE_PROJECT,
    extract_remember_request,
    fact_for_prompt,
    fact_scope,
    is_only_remember_request,
    memorization_confirmation,
    project_name,
)

# Retenu pour tous ses projets : « retiens pour tous mes projets que… »,
# « … dans tous mes repos », « remember for all my projects that… ».
# « partout » n'en est pas : « je veux des logs partout » parle du code.
_ALL_PROJECTS_RE = re.compile(
    r"(?<![\w'’])(?:"
    r"(?:pour|dans|sur)\s+(?:tous|toutes)\s+(?:mes|les|nos)\s+"
    r"(?:projets|repos|d[ée]p[ôo]ts|codes|workspaces)"
    r"|(?:for|in|across)\s+(?:all|every)\s+(?:of\s+)?(?:my\s+|the\s+|our\s+)?"
    r"(?:projects?|repos(?:itories)?|codebases?|workspaces?)"
    r")(?![\w'’])",
    re.IGNORECASE,
)
# Pour ce projet, ce qui est de toute façon le cas : la précision quitte le fait
_THIS_PROJECT_RE = re.compile(
    r"(?<![\w'’])(?:"
    r"(?:pour|dans|sur)\s+(?:ce|le)\s+(?:projet|repo|d[ée]p[ôo]t|workspace)(?:-ci|-l[àa])?"
    r"|(?:for|in)\s+this\s+(?:project|repo(?:sitory)?|codebase|workspace)"
    r")(?![\w'’])",
    re.IGNORECASE,
)


def _plain(text: str) -> str:
    """Minuscules sans accents ni ponctuation aux bords, pour comparer deux phrases."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    flat = "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()
    return re.sub(r"\s+", " ", flat).strip(" ,.;:!?")


def remember_request(message: str) -> Tuple[Optional[str], str, str]:
    """
    Information que le message demande de retenir dans la conversation Code, sa
    portée et le message sans la précision de portée.

    « Retiens pour tous mes projets que j'indente avec des tabulations » →
    (« j'indente avec des tabulations », « code », …). La précision (« pour tous
    mes projets », « pour ce projet ») est retirée quand elle suit le verbe ou
    ouvre ou ferme l'information ; au milieu de la phrase, elle en fait partie.

    Returns:
        (information ou None, portée SCOPE_CODE ou SCOPE_PROJECT, message lu)
    """
    raw = extract_remember_request(message)
    for pattern, scope in ((_ALL_PROJECTS_RE, SCOPE_CODE), (_THIS_PROJECT_RE, SCOPE_PROJECT)):
        match = pattern.search(message or "")
        if match is None:
            continue
        text = (message[:match.start()].rstrip(" ,") + " "
                + message[match.end():].lstrip(" ,")).strip()
        fact = extract_remember_request(text)
        phrase = _plain(match.group(0))
        if fact and (raw is None or _plain(raw).startswith(phrase) or _plain(raw).endswith(phrase)):
            return fact, scope, text
    return raw, SCOPE_PROJECT, message


@dataclass
class Remembered:
    """Information retenue depuis un message de la conversation Code."""

    fact: str
    fact_id: int
    # Nouvelle (ou désormais valable pour tous les projets), sinon déjà connue
    created: bool
    scope: str
    # Dossier d'un fait de projet ("" pour tous les projets)
    project: str
    # Le message ne demande rien d'autre
    alone: bool

    def where(self) -> str:
        """Pour quoi elle vaut, dans le prompt du modèle."""
        if self.scope == SCOPE_PROJECT:
            return f"le projet « {project_name(self.project)} »"
        return "tous ses projets"

    def prompt_note(self) -> str:
        """Note ajoutée à son message pour le modèle : la mémorisation est faite,
        il la confirme (sans elle, un petit modèle répondait « c'est noté » sans
        rien avoir enregistré, ou relançait des outils)."""
        then = (" Son message ne demande rien d'autre : ta réponse se limite à cela, "
                "sans outil." if self.alone
                else " Puis réponds au reste de son message.")
        fact = fact_for_prompt(self.fact)
        if not self.created:
            return (f"[Mémoire] C'était déjà dans la mémoire de My_AI, pour {self.where()} : "
                    f"{fact}. Dis-le-lui en une phrase.{then}")
        confirmation = memorization_confirmation(self.fact)
        example = f" (par exemple : « {confirmation} »)" if confirmation else ""
        return (f"[Mémoire] À la demande de l'utilisateur, My_AI vient d'enregistrer dans sa "
                f"mémoire, pour {self.where()} : {fact}. Confirme-le-lui en une "
                f"phrase{example}.{then}")


class CodeMemory:
    """Faits et documents de My_AI vus de la conversation Code."""

    def __init__(
        self,
        knowledge_base: Any,
        search: Optional[Callable[..., str]] = None,
        auto_extract: Optional[Callable[[], bool]] = None,
    ):
        """
        Args:
            knowledge_base: KnowledgeBaseManager (faits SQLite).
            search: AIEngine.search_memory (faits donnés, puis documents de la
                fenêtre Mémoire) ; sans elle, les faits seulement.
            auto_extract: réglage knowledge_base.auto_extract : My_AI mémorise-t-il
                depuis les conversations ?
        """
        self._kb = knowledge_base
        self._search = search
        self._auto_extract = auto_extract or (lambda: True)

    def facts(self, roots: Sequence[str]) -> List[Dict[str, Any]]:
        """Faits reçus d'office avec ces dossiers ouverts (prompt_block)."""
        return self._kb.code_facts(roots)

    def prompt_block(self, roots: Sequence[str],
                     facts: Optional[List[Dict[str, Any]]] = None) -> str:
        """Section « Mémoire » du prompt système : les faits du code, puis comment
        lire le reste de la mémoire et y écrire."""
        facts = self.facts(roots) if facts is None else facts
        lines: List[str] = []
        projects: Dict[str, List[Dict[str, Any]]] = {}
        everywhere = []
        for fact in facts:
            scope, folder = fact_scope(fact)
            if scope == SCOPE_PROJECT:
                projects.setdefault(project_name(folder), []).append(fact)
            elif scope == SCOPE_CODE:
                everywhere.append(fact)
        if facts:
            lines.append("Ce que l'utilisateur t'a demandé de retenir pour son code "
                         "(fenêtre 🧠 Mémoire de My_AI) :")
            for name, group in projects.items():
                lines.append(f"Pour le projet {name} :")
                lines.extend(f"- {self._kb.prompt_text(fact)}" for fact in group)
            if everywhere:
                lines.append("Pour tous ses projets :")
                lines.extend(f"- {self._kb.prompt_text(fact)}" for fact in everywhere)
            lines.append("")
            lines.append(
                "Applique ces consignes quand elles concernent ce que tu fais. Ne les recopie "
                "pas dans les fichiers, les commentaires ou les messages de commit, et n'en "
                "parle que si on te le demande.")
        lines.append(
            "Le reste de sa mémoire (ce qu'il t'a dit sur lui, documents qu'il a mis dans "
            "My_AI : cahiers des charges, notes…) se lit avec l'outil search_memory, "
            "seulement quand il en parle.")
        lines.append(
            "Tu ne peux rien enregistrer toi-même dans cette mémoire : l'utilisateur le fait "
            "en écrivant « retiens que… ». Si on te demande de retenir quelque chose et "
            "qu'aucune note [Mémoire] ne suit son message, dis-lui de l'écrire ainsi.")
        return "\n".join(lines)

    def remember(self, message: str, roots: Sequence[str]) -> Optional[Remembered]:
        """
        « Retiens que… » du message de l'utilisateur : enregistré pour le premier
        dossier ouvert (pour tous ses projets si le message le dit, ou si VS Code
        n'a aucun dossier ouvert). None si le message ne le demande pas.
        """
        if not message or not self._auto_extract():
            return None
        fact, scope, text = remember_request(message)
        if not fact:
            return None
        project = next((root for root in roots or () if root), "")
        if scope == SCOPE_PROJECT and not project:
            scope = SCOPE_CODE
        if scope != SCOPE_PROJECT:
            project = ""
        fact_id, created = self._kb.remember(fact, source="code", scope=scope, project=project)
        return Remembered(fact=fact, fact_id=fact_id, created=created, scope=scope,
                          project=project, alone=is_only_remember_request(text, fact))

    def search(self, query: str, n_results: int = 5, document: str = "",
               roots: Sequence[str] = ()) -> str:
        """Outil search_memory de la conversation Code : faits du chat, du code et de
        ces dossiers (pas ceux des autres projets), puis documents de la mémoire.

        Faute de fait correspondant, seuls ceux du code sont proposés : une
        recherche de cahier des charges ne ramène pas les faits du chat (nom,
        famille…), qui n'ont rien à faire dans le code.
        """
        code = self._kb.code_facts(roots)
        pool = self._kb.chat_facts() + code
        if self._search is not None:
            return self._search(query, n_results, document, facts=pool, recent=code)
        found = self._kb.search_text(query, n_results, facts=pool, recent=code)
        return found or "Aucun résultat dans la mémoire (faits mémorisés et documents indexés)."


def code_memory_for(engine: Any) -> Optional[CodeMemory]:
    """Mémoire de la conversation Code, de l'AIEngine de l'appli (None sans base de faits)."""
    knowledge_base = getattr(engine, "knowledge_base", None)
    if knowledge_base is None:
        return None
    return CodeMemory(
        knowledge_base,
        search=getattr(engine, "search_memory", None),
        auto_extract=getattr(engine, "_memory_auto_extract", None),
    )
