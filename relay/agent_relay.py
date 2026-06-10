"""
Agent Relay Service - Exécution serveur des agents IA pour l'interface mobile.

Ce module porte les fonctionnalités de la page « Agents » du GUI desktop
(``interfaces/agents/``) côté serveur Relay afin que le mobile puisse :

  - lister les agents (built-in + personnalisés)
  - créer / modifier / supprimer des agents personnalisés
  - exécuter un agent seul, un workflow visuel (séquentiel / parallèle / DAG)
  - lancer un débat entre deux agents

Tout tourne sur le PC hôte (modèle local via Ollama) et le contenu ne quitte
jamais le tunnel chiffré : le serveur Relay encapsule chaque message émis par
ce service dans l'enveloppe E2EE AES-256-GCM avant de l'envoyer au mobile.

Contrairement au chat mobile (qui délègue au GUI desktop via le RelayBridge),
les agents s'exécutent intégralement ici — comme le mode agentique VS Code —
parce qu'ils n'ont pas besoin du GUI Tkinter pour fonctionner.
"""

import json
import os
import random
import threading
import time
import base64
import io

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from PIL import Image

from core.agent_orchestrator import AgentOrchestrator
from models.ai_agents import AVAILABLE_AGENTS, AIAgent
from models.local_llm import LocalLLM
from utils.logger import setup_logger

from processors.pdf_processor import PDFProcessor
from processors.docx_processor import DOCXProcessor
from processors.excel_processor import ExcelProcessor

try:
    from core.config import get_default_model as _get_default_model
except Exception:  # pragma: no cover - fallback si config indisponible
    def _get_default_model() -> str:
        return "qwen3.5:4b"

logger = setup_logger("AgentRelay")

# Cadence max d'envoi des chunks de streaming par section (anti-flood WS+tunnel).
_CHUNK_THROTTLE_SEC = 0.06

# Métadonnées des 9 agents built-in (identiques à la grille du GUI desktop,
# cf. interfaces/agents/agent_selection.py).
_BUILTIN_AGENTS: List[Dict[str, str]] = [
    {"key": "code", "icon": "🐍", "name": "CodeAgent",
     "desc": "Génération et debug de code", "color": "#3b82f6"},
    {"key": "web", "icon": "🔍", "name": "WebAgent",
     "desc": "Recherche Internet & Fact-Checking", "color": "#10b981"},
    {"key": "analyst", "icon": "📊", "name": "AnalystAgent",
     "desc": "Analyse de données", "color": "#8b5cf6"},
    {"key": "creative", "icon": "✨", "name": "CreativeAgent",
     "desc": "Contenu créatif", "color": "#f59e0b"},
    {"key": "debug", "icon": "🐛", "name": "DebugAgent",
     "desc": "Debug et correction", "color": "#ef4444"},
    {"key": "planner", "icon": "📋", "name": "PlannerAgent",
     "desc": "Planification de projets", "color": "#06b6d4"},
    {"key": "security", "icon": "🛡", "name": "SecurityAgent",
     "desc": "Audit de sécurité & vulnérabilités", "color": "#ec4899"},
    {"key": "optimizer", "icon": "⚡", "name": "OptimizerAgent",
     "desc": "Optimisation & Performance", "color": "#14b8a6"},
    {"key": "datascience", "icon": "🧬", "name": "DataScienceAgent",
     "desc": "Data Science & Machine Learning", "color": "#f97316"},
]

_BUILTIN_KEYS = {a["key"] for a in _BUILTIN_AGENTS}

# Palette de couleurs pour les agents personnalisés (cf. custom_agents.py).
_CUSTOM_PALETTE = [
    "#e11d48", "#7c3aed", "#0891b2", "#059669", "#d97706",
    "#dc2626", "#9333ea", "#0284c7", "#16a34a", "#ca8a04",
    "#be185d", "#6d28d9", "#0e7490", "#047857", "#b45309",
    "#c026d3", "#4f46e5", "#0369a1", "#15803d", "#a16207",
]

# Prompt de génération de system prompt (identique au GUI desktop).
_AGENT_GEN_PROMPT = """Tu dois créer un system prompt pour un agent IA spécialisé.

Voici le nom de l'agent: {name}
Voici la description de son rôle: {role}

Génère un system prompt complet en suivant EXACTEMENT ce format:

Tu es {name}, un expert en [domaine basé sur la description].

EXPERTISE: [liste des domaines d'expertise basée sur la description]

COMPORTEMENT:
- [comportement 1]
- [comportement 2]
- [comportement 3]
- [comportement 4]
- [comportement 5]

FORMAT DE RÉPONSE:
- [format 1]
- [format 2]
- [format 3]
- [format 4]

Réponds UNIQUEMENT avec le system prompt, rien d'autre. Pas d'explication, pas de commentaire.
Génère aussi à la fin, sur une ligne séparée commençant par "TEMPERATURE:", une valeur de température entre 0.1 et 0.9 adaptée au rôle (précis = bas, créatif = haut).
Ensuite, sur une dernière ligne séparée commençant par "SUMMARY:", génère un résumé de 3-4 mots maximum du rôle de l'agent, avec la première lettre en majuscule (ex: "Recherche web avancée" ou "Analyse de données")."""

_AGENT_GEN_SYSTEM = (
    "Tu es un assistant qui génère des system prompts pour des agents IA. "
    "Réponds uniquement avec le contenu demandé, sans explications."
)


class AgentRelayService:
    """Orchestration serveur des agents pour le Relay mobile.

    Une seule exécution (workflow ou débat) est autorisée à la fois, comme
    sur le GUI desktop. Les appels de création/édition d'agent custom sont
    bloquants (génération du system prompt via le LLM local).
    """

    def __init__(self) -> None:
        self._orchestrator = AgentOrchestrator()
        self._llm = None  # LocalLLM lazy (génération de system prompts custom)

        # Fichier partagé avec le GUI desktop : les agents créés sur mobile
        # apparaissent sur le PC (et inversement après rechargement).
        self._custom_agents_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "custom_agents.json",
        )
        self._custom_agents: Dict[str, Dict[str, Any]] = {}

        # Gate d'exécution unique + drapeaux d'interruption par exec_id.
        self._exec_lock = threading.Lock()
        self._busy = False
        self._interrupts: Dict[str, bool] = {}

        self._load_and_register_custom()
        logger.info(
            "AgentRelayService initialisé (%d agents personnalisés)",
            len(self._custom_agents),
        )

    # ------------------------------------------------------------------
    # LLM paresseux
    # ------------------------------------------------------------------

    @property
    def _local_llm(self):
        if self._llm is None:
            self._llm = LocalLLM(model=_get_default_model())
        return self._llm

    # ------------------------------------------------------------------
    # Agents personnalisés : persistance + enregistrement
    # ------------------------------------------------------------------

    def _load_and_register_custom(self) -> None:
        """Charge data/custom_agents.json et enregistre dans AVAILABLE_AGENTS."""
        try:
            if os.path.exists(self._custom_agents_file):
                with open(self._custom_agents_file, "r", encoding="utf-8") as f:
                    self._custom_agents = json.load(f) or {}
        except Exception as exc:
            logger.warning("Chargement agents personnalisés échoué : %s", exc)
            self._custom_agents = {}
        for key, data in self._custom_agents.items():
            self._register_custom(key, data)

    def _save_custom(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._custom_agents_file), exist_ok=True)
            with open(self._custom_agents_file, "w", encoding="utf-8") as f:
                json.dump(self._custom_agents, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning("Sauvegarde agents personnalisés échouée : %s", exc)

    @staticmethod
    def _register_custom(key: str, data: Dict[str, Any]) -> None:
        """Enregistre un agent personnalisé dans la factory globale."""
        def factory(model=None, _data=data):
            return AIAgent(
                name=_data.get("name", key),
                expertise=_data.get("desc", ""),
                system_prompt=_data.get("system_prompt", ""),
                model=model or _get_default_model(),
                temperature=_data.get("temperature", 0.5),
            )
        AVAILABLE_AGENTS[key] = factory

    # ------------------------------------------------------------------
    # API : liste des agents
    # ------------------------------------------------------------------

    def list_agents(self) -> Dict[str, Any]:
        """Retourne {builtin, custom, default_model}.

        Recharge le fichier custom à chaque appel pour rester synchrone avec
        les agents éventuellement créés depuis le GUI desktop.
        """
        self._load_and_register_custom()
        custom = []
        for key, data in self._custom_agents.items():
            custom.append({
                "key": key,
                "icon": "🧩",
                "name": data.get("name", key),
                "desc": data.get("short_desc") or data.get("desc", ""),
                "full_desc": data.get("desc", ""),
                "color": data.get("color", "#ff6b47"),
                "custom": True,
            })
        return {
            "builtin": list(_BUILTIN_AGENTS),
            "custom": custom,
            "default_model": _get_default_model(),
        }

    # ------------------------------------------------------------------
    # API : CRUD agents personnalisés
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_generated_prompt(response: str, role: str) -> Tuple[str, float, str]:
        """Extrait (system_prompt, temperature, short_desc) de la sortie LLM."""
        temperature = 0.5
        short_desc = role[:30]
        system_prompt = (response or "").strip()

        if "SUMMARY:" in system_prompt:
            parts = system_prompt.rsplit("SUMMARY:", 1)
            system_prompt = parts[0].strip()
            short_desc = parts[1].strip().split("\n")[0].strip()
            if short_desc:
                short_desc = short_desc[0].upper() + short_desc[1:]

        if "TEMPERATURE:" in system_prompt:
            parts = system_prompt.rsplit("TEMPERATURE:", 1)
            system_prompt = parts[0].strip()
            try:
                temperature = max(0.1, min(0.9, float(parts[1].strip().split()[0])))
            except (ValueError, IndexError):
                temperature = 0.5

        return system_prompt, temperature, short_desc

    def create_agent(self, name: str, role: str) -> Dict[str, Any]:
        """Crée un agent personnalisé (génération du system prompt via LLM)."""
        name = (name or "").strip()
        role = (role or "").strip()
        if not name:
            return {"success": False, "error": "Nom requis"}
        if not role:
            return {"success": False, "error": "Rôle requis"}

        try:
            response = self._local_llm.generate(
                prompt=_AGENT_GEN_PROMPT.format(name=name, role=role),
                system_prompt=_AGENT_GEN_SYSTEM,
            )
        except Exception as exc:
            logger.warning("Génération agent échouée : %s", exc)
            return {"success": False, "error": f"Erreur LLM : {exc}"}

        if not response:
            return {
                "success": False,
                "error": "Ollama n'a pas répondu. Vérifiez qu'Ollama est lancé.",
            }

        system_prompt, temperature, short_desc = self._parse_generated_prompt(
            response, role
        )
        color = random.choice(_CUSTOM_PALETTE)
        key = f"custom_{name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}"
        data = {
            "name": name,
            "desc": role,
            "short_desc": short_desc,
            "color": color,
            "system_prompt": system_prompt,
            "temperature": temperature,
        }
        self._custom_agents[key] = data
        self._save_custom()
        self._register_custom(key, data)

        return {
            "success": True,
            "agent": {
                "key": key, "icon": "🧩", "name": name,
                "desc": short_desc, "full_desc": role,
                "color": color, "custom": True,
            },
        }

    def edit_agent(self, key: str, name: str, role: str) -> Dict[str, Any]:
        """Modifie un agent personnalisé. Régénère le prompt si le rôle change."""
        if key not in self._custom_agents:
            return {"success": False, "error": "Agent introuvable"}
        name = (name or "").strip()
        role = (role or "").strip()
        if not name:
            return {"success": False, "error": "Nom requis"}
        if not role:
            return {"success": False, "error": "Rôle requis"}

        old = self._custom_agents[key]
        name_changed = name != old.get("name")
        role_changed = role != old.get("desc")
        if not name_changed and not role_changed:
            return {"success": True, "agent": self._agent_view(key)}

        if role_changed:
            try:
                response = self._local_llm.generate(
                    prompt=_AGENT_GEN_PROMPT.format(name=name, role=role),
                    system_prompt=_AGENT_GEN_SYSTEM,
                )
            except Exception as exc:
                return {"success": False, "error": f"Erreur LLM : {exc}"}
            if not response:
                return {"success": False, "error": "Ollama n'a pas répondu."}
            system_prompt, temperature, short_desc = self._parse_generated_prompt(
                response, role
            )
            old.update({
                "name": name, "desc": role, "short_desc": short_desc,
                "system_prompt": system_prompt, "temperature": temperature,
            })
        else:
            old["name"] = name

        self._save_custom()
        self._register_custom(key, old)
        # Forcer la recréation de l'agent en cache dans l'orchestrateur.
        self._orchestrator.agents.pop(key, None)
        return {"success": True, "agent": self._agent_view(key)}

    def delete_agent(self, key: str) -> Dict[str, Any]:
        """Supprime un agent personnalisé."""
        if key not in self._custom_agents:
            return {"success": False, "error": "Agent introuvable"}
        del self._custom_agents[key]
        self._save_custom()
        AVAILABLE_AGENTS.pop(key, None)
        self._orchestrator.agents.pop(key, None)
        return {"success": True, "key": key}

    def _agent_view(self, key: str) -> Dict[str, Any]:
        data = self._custom_agents.get(key, {})
        return {
            "key": key, "icon": "🧩", "name": data.get("name", key),
            "desc": data.get("short_desc") or data.get("desc", ""),
            "full_desc": data.get("desc", ""),
            "color": data.get("color", "#ff6b47"), "custom": True,
        }

    # ------------------------------------------------------------------
    # Interruption
    # ------------------------------------------------------------------

    def interrupt(self, exec_id: str) -> None:
        """Demande l'interruption d'une exécution en cours (workflow ou débat)."""
        if exec_id:
            self._interrupts[exec_id] = True

    def _interrupted(self, exec_id: str) -> bool:
        return self._interrupts.get(exec_id, False)

    @property
    def busy(self) -> bool:
        """Indique si une exécution est en cours (workflow ou débat)."""
        return self._busy

    # ------------------------------------------------------------------
    # Plan d'exécution (port de WorkflowCanvas.get_execution_plan)
    # ------------------------------------------------------------------

    @staticmethod
    def compute_execution_plan(
        nodes: List[Dict[str, Any]],
        connections: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Analyse la topologie et retourne un plan d'exécution.

        `nodes` : [{"id", "agent_type", "name", "color", "icon"}]
        `connections` : [{"from", "to"}]  (ids référencent nodes[].id)
        """
        node_map: Dict[Any, Dict[str, Any]] = {n["id"]: n for n in nodes}
        if not node_map:
            return {"mode": "empty", "steps": [], "isolated": [], "node_map": {}}

        # Ne conserver que les connexions valides (deux extrémités connues).
        conns = [
            c for c in connections
            if c.get("from") in node_map and c.get("to") in node_map
            and c.get("from") != c.get("to")
        ]

        connected = set()
        for c in conns:
            connected.add(c["from"])
            connected.add(c["to"])
        isolated = [nid for nid in node_map if nid not in connected]

        if not conns:
            # Aucune connexion : tous les nœuds forment une seule étape
            # (parallèle si >1). `isolated` est volontairement vide ici car
            # les nœuds sont déjà couverts par `steps` — sinon ils seraient
            # exécutés deux fois (l'étape ET la passe « isolés »).
            ids = list(node_map.keys())
            return {
                "mode": "single" if len(node_map) == 1 else "parallel",
                "steps": [{"nodes": ids, "parallel": len(node_map) > 1}],
                "isolated": [],
                "node_map": node_map,
                "connections": [],
            }

        # Tri topologique (Kahn).
        in_degree = {nid: 0 for nid in node_map}
        adj: Dict[Any, List[Any]] = {nid: [] for nid in node_map}
        for c in conns:
            adj[c["from"]].append(c["to"])
            in_degree[c["to"]] += 1

        queue = [nid for nid in node_map
                 if in_degree[nid] == 0 and nid in connected]
        steps: List[Dict[str, Any]] = []
        visited = set()
        while queue:
            level = list(queue)
            steps.append({"nodes": level, "parallel": len(level) > 1})
            visited.update(level)
            next_queue: List[Any] = []
            for nid in level:
                for child in adj.get(nid, []):
                    in_degree[child] -= 1
                    if in_degree[child] == 0 and child not in visited:
                        next_queue.append(child)
            queue = next_queue

        is_linear = all(len(s["nodes"]) == 1 for s in steps)
        return {
            "mode": "sequential" if is_linear else "dag",
            "steps": steps,
            "isolated": isolated,
            "node_map": node_map,
            "connections": conns,
        }

    # ------------------------------------------------------------------
    # Helpers de streaming
    # ------------------------------------------------------------------

    def _make_token_sink(self, emit, exec_id, section_id):
        """Retourne un on_token(delta) qui émet le texte cumulé (throttlé).

        Retourne False quand l'exécution est interrompue pour stopper la
        génération côté LLM. Le texte final est flushé par l'appelant.
        """
        state = {"text": "", "last": 0.0}

        def on_token(delta):
            if self._interrupted(exec_id):
                return False
            state["text"] += delta
            now = time.time()
            if now - state["last"] >= _CHUNK_THROTTLE_SEC:
                state["last"] = now
                emit({
                    "type": "agent_section_chunk",
                    "exec_id": exec_id,
                    "section_id": section_id,
                    "text": state["text"],
                })
            return not self._interrupted(exec_id)

        return on_token, state

    # ------------------------------------------------------------------
    # Pièces jointes (mêmes processeurs que la page Agents du GUI desktop)
    # ------------------------------------------------------------------

    @staticmethod
    def _read_attached_file(file_path: str) -> str:
        """Lit le contenu textuel d'un fichier joint (PDF/DOCX/Excel/code/texte).

        Réplique `interfaces/agents/file_handling.py:_read_attached_file` en
        ajoutant la prise en charge d'Excel/CSV via ExcelProcessor.
        """
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".pdf":
                return PDFProcessor().process_file(file_path).get("content", "")
            if ext in (".docx", ".doc"):
                return DOCXProcessor().process_file(file_path).get("content", "")
            if ext in (".xlsx", ".xls", ".csv"):
                res = ExcelProcessor().extract_text(file_path)
                if res.get("success"):
                    return res.get("content", "")
        except Exception as exc:
            logger.warning("Lecture %s échouée : %s", file_path, exc)
        # Texte / code / markdown — lecture directe (limite 200k chars)
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(200_000)
        except Exception:
            try:
                with open(file_path, "rb") as f:
                    return f.read(100_000).decode("utf-8", errors="replace")
            except Exception as exc:
                return f"[Erreur de lecture : {exc}]"

    def _describe_image(self, image_path: str) -> str:
        """Décrit une image via le modèle vision (même pipeline que le GUI)."""
        try:
            img = Image.open(image_path)
            if img.mode != "RGB":
                img = img.convert("RGB")
            if img.width > 1024 or img.height > 1024:
                img.thumbnail((1024, 1024), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=92, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            return self._local_llm.describe_image(b64) or ""
        except Exception as exc:
            logger.warning("Analyse image %s échouée : %s", image_path, exc)
            return ""

    def _augment_task_with_files(
        self,
        task: str,
        image_path: Optional[str],
        file_paths: Optional[List[str]],
    ) -> str:
        """Ajoute le contenu des pièces jointes au prompt de tâche.

        Réplique la logique de `execute_agent_task` du GUI desktop : les
        documents sont lus en texte brut et les images décrites par le modèle
        vision, puis tout est concaténé en sections à la fin de la tâche.
        """
        sections: List[str] = []
        if image_path and os.path.isfile(image_path):
            fname = os.path.basename(image_path)
            desc = self._describe_image(image_path)
            if desc:
                sections.append(
                    f"--- Image jointe : {fname} ---\n"
                    f"Description de l'image :\n{desc}"
                )
            else:
                sections.append(
                    f"--- Image jointe : {fname} ---\n"
                    f"[Aucun modèle vision disponible. "
                    f"Installez-en un : ollama pull minicpm-v]"
                )
        for fp in file_paths or []:
            if not fp or not os.path.isfile(fp):
                continue
            content = self._read_attached_file(fp)
            if content:
                sections.append(
                    f"--- Fichier joint : {os.path.basename(fp)} ---\n{content}"
                )
        if sections:
            return task + "\n\n" + "\n\n".join(sections)
        return task

    # ------------------------------------------------------------------
    # Exécution : workflow (single / sequential / parallel / DAG)
    # ------------------------------------------------------------------

    def run_workflow(
        self,
        exec_id: str,
        task: str,
        nodes: List[Dict[str, Any]],
        connections: List[Dict[str, Any]],
        emit: Callable[[Dict[str, Any]], None],
        image_path: Optional[str] = None,
        file_paths: Optional[List[str]] = None,
    ) -> None:
        """Exécute le workflow visuel et stream les résultats via `emit`.

        Doit être appelé dans un thread dédié (bloquant). `emit` est une
        fonction thread-safe fournie par le serveur (planifie l'envoi WS
        chiffré sur la boucle asyncio). `image_path`/`file_paths` sont les
        pièces jointes éventuelles (déjà résolues depuis les file_ids).
        """
        with self._exec_lock:
            if self._busy:
                emit({"type": "agent_exec_error", "exec_id": exec_id,
                      "message": "Une exécution est déjà en cours."})
                return
            self._busy = True
        self._interrupts[exec_id] = False

        try:
            self._load_and_register_custom()
            # Injecter le contenu des pièces jointes dans la tâche (lecture
            # de fichiers / analyse d'image — bloquant, donc ici dans le thread).
            if image_path or file_paths:
                task = self._augment_task_with_files(task, image_path, file_paths)
            plan = self.compute_execution_plan(nodes, connections)
            if plan["mode"] == "empty":
                emit({"type": "agent_exec_error", "exec_id": exec_id,
                      "message": "Aucun agent dans le workflow."})
                return

            emit({"type": "agent_exec_start", "exec_id": exec_id,
                  "mode": plan["mode"]})

            node_map = plan["node_map"]
            conns = plan.get("connections", [])
            results_by_node: Dict[Any, str] = {}
            success_count = 0
            total_count = 0

            for nid in node_map:
                emit({"type": "agent_node_status", "exec_id": exec_id,
                      "node_id": nid, "status": "idle"})

            def build_task(nid):
                """Compose la tâche d'un nœud avec le contexte de ses parents."""
                parents = [c["from"] for c in conns if c["to"] == nid]
                parts = [
                    f"[{node_map[p]['name']}]:\n{results_by_node[p]}"
                    for p in parents if p in results_by_node
                ]
                if parts:
                    sep = "\n---\n"
                    return f"Contexte précédent:\n{sep.join(parts)}\n\nTâche: {task}"
                return task

            for step in plan["steps"]:
                if self._interrupted(exec_id):
                    break
                nids = step["nodes"]

                if step["parallel"]:
                    threads = []
                    lock = threading.Lock()

                    # `lock` est lié en argument par défaut pour capturer
                    # l'instance de CETTE itération (évite cell-var-from-loop).
                    def run_one(nid, lock=lock):
                        if self._interrupted(exec_id):
                            return
                        nd = node_map[nid]
                        emit({"type": "agent_section_start", "exec_id": exec_id,
                              "section_id": nid, "title": nd["name"],
                              "color": nd.get("color", "#ff6b47")})
                        emit({"type": "agent_node_status", "exec_id": exec_id,
                              "node_id": nid, "status": "running"})
                        on_token, state = self._make_token_sink(emit, exec_id, nid)
                        result = self._orchestrator.execute_single_task_stream(
                            agent_type=nd["agent_type"],
                            task=build_task(nid),
                            on_token=on_token,
                        )
                        ok = bool(result.get("success")) and not self._interrupted(exec_id)
                        text = state["text"] if state["text"] else result.get("result", "")
                        emit({"type": "agent_section_chunk", "exec_id": exec_id,
                              "section_id": nid, "text": text})
                        emit({"type": "agent_section_end", "exec_id": exec_id,
                              "section_id": nid, "success": ok})
                        emit({"type": "agent_node_status", "exec_id": exec_id,
                              "node_id": nid, "status": "done" if ok else "error"})
                        with lock:
                            if ok:
                                results_by_node[nid] = result.get("result", "")

                    for nid in nids:
                        t = threading.Thread(target=run_one, args=(nid,), daemon=True)
                        threads.append(t)
                        t.start()
                    for t in threads:
                        t.join()
                    for nid in nids:
                        total_count += 1
                        if nid in results_by_node:
                            success_count += 1
                else:
                    nid = nids[0]
                    nd = node_map[nid]
                    emit({"type": "agent_section_start", "exec_id": exec_id,
                          "section_id": nid, "title": nd["name"],
                          "color": nd.get("color", "#ff6b47")})
                    emit({"type": "agent_node_status", "exec_id": exec_id,
                          "node_id": nid, "status": "running"})
                    on_token, state = self._make_token_sink(emit, exec_id, nid)
                    result = self._orchestrator.execute_single_task_stream(
                        agent_type=nd["agent_type"],
                        task=build_task(nid),
                        on_token=on_token,
                    )
                    ok = bool(result.get("success")) and not self._interrupted(exec_id)
                    # Afficher ce qui a réellement été streamé (évite un saut
                    # visuel à la fin) ; à défaut, le texte du résultat.
                    text = state["text"] if state["text"] else result.get("result", "")
                    emit({"type": "agent_section_chunk", "exec_id": exec_id,
                          "section_id": nid, "text": text})
                    emit({"type": "agent_section_end", "exec_id": exec_id,
                          "section_id": nid, "success": ok})
                    emit({"type": "agent_node_status", "exec_id": exec_id,
                          "node_id": nid, "status": "done" if ok else "error"})
                    total_count += 1
                    if ok:
                        success_count += 1
                        results_by_node[nid] = result.get("result", "")

            # Nœuds isolés (sans connexion) — exécutés indépendamment.
            for nid in plan["isolated"]:
                if self._interrupted(exec_id):
                    break
                nd = node_map[nid]
                emit({"type": "agent_section_start", "exec_id": exec_id,
                      "section_id": nid, "title": f"Agent isolé : {nd['name']}",
                      "color": nd.get("color", "#ff6b47")})
                emit({"type": "agent_node_status", "exec_id": exec_id,
                      "node_id": nid, "status": "running"})
                on_token, state = self._make_token_sink(emit, exec_id, nid)
                result = self._orchestrator.execute_single_task_stream(
                    agent_type=nd["agent_type"], task=task, on_token=on_token,
                )
                ok = bool(result.get("success")) and not self._interrupted(exec_id)
                text = result.get("result", "") if ok else state["text"]
                emit({"type": "agent_section_chunk", "exec_id": exec_id,
                      "section_id": nid, "text": text})
                emit({"type": "agent_section_end", "exec_id": exec_id,
                      "section_id": nid, "success": ok})
                emit({"type": "agent_node_status", "exec_id": exec_id,
                      "node_id": nid, "status": "done" if ok else "error"})
                total_count += 1
                if ok:
                    success_count += 1

            interrupted = self._interrupted(exec_id)
            if interrupted:
                status_text = "⛔ Génération interrompue"
            else:
                rate = success_count / max(total_count, 1)
                status_text = f"✅ Workflow terminé ({rate:.0%} succès)"
            emit({"type": "agent_exec_end", "exec_id": exec_id,
                  "success": (not interrupted) and success_count == total_count,
                  "interrupted": interrupted, "status_text": status_text})

        except Exception as exc:
            logger.exception("Workflow agents échoué (exec_id=%s)", exec_id)
            emit({"type": "agent_exec_error", "exec_id": exec_id,
                  "message": f"Erreur workflow : {exc}"})
        finally:
            self._interrupts.pop(exec_id, None)
            self._busy = False

    # ------------------------------------------------------------------
    # Exécution : débat entre deux agents
    # ------------------------------------------------------------------

    def run_debate(
        self,
        exec_id: str,
        agent_a: str,
        agent_b: str,
        topic: str,
        rounds: int,
        emit: Callable[[Dict[str, Any]], None],
    ) -> None:
        """Exécute un débat et stream les tours via `emit`."""
        with self._exec_lock:
            if self._busy:
                emit({"type": "agent_exec_error", "exec_id": exec_id,
                      "message": "Une exécution est déjà en cours."})
                return
            self._busy = True
        self._interrupts[exec_id] = False

        # État de section courant (un tour = une section). Variables scalaires
        # mutées via `nonlocal` dans les closures ci-dessous (plus simple et
        # plus sûr qu'un dict imbriqué pour l'analyse statique).
        cur_sid: Optional[str] = None
        cur_text = ""
        cur_last = 0.0

        try:
            self._load_and_register_custom()
            topic = (topic or "").strip()
            if not topic:
                emit({"type": "agent_exec_error", "exec_id": exec_id,
                      "message": "Sujet requis."})
                return
            rounds = max(1, min(10, int(rounds or 3)))
            emit({"type": "agent_exec_start", "exec_id": exec_id, "mode": "debate"})
            emit({"type": "agent_debate_topic", "exec_id": exec_id, "topic": topic})

            names = self.list_agents()
            name_lookup = {a["key"]: a["name"] for a in names["builtin"]}
            color_lookup = {a["key"]: a["color"] for a in names["builtin"]}
            for a in names["custom"]:
                name_lookup[a["key"]] = a["name"]
                color_lookup[a["key"]] = a["color"]

            section_counter = {"n": 0}

            def finish_current(success=True):
                nonlocal cur_sid, cur_text, cur_last
                if cur_sid is not None:
                    emit({"type": "agent_section_end", "exec_id": exec_id,
                          "section_id": cur_sid, "success": success})
                    cur_sid = None
                    cur_text = ""
                    cur_last = 0.0

            def on_round_start(round_num, agent_type):
                nonlocal cur_sid, cur_text, cur_last
                finish_current(True)
                section_counter["n"] += 1
                sid = f"deb_{section_counter['n']}"
                role = "Proposant" if agent_type == agent_a else "Opposant"
                title = f"Tour {round_num} — {name_lookup.get(agent_type, agent_type)} ({role})"
                emit({"type": "agent_section_start", "exec_id": exec_id,
                      "section_id": sid, "title": title,
                      "color": color_lookup.get(agent_type, "#8b5cf6")})
                cur_sid = sid
                cur_text = ""
                cur_last = 0.0

            def on_token(delta):
                nonlocal cur_text, cur_last
                if self._interrupted(exec_id):
                    return False
                if cur_sid is None:
                    return True
                cur_text += delta
                now = time.time()
                if now - cur_last >= _CHUNK_THROTTLE_SEC:
                    cur_last = now
                    emit({"type": "agent_section_chunk", "exec_id": exec_id,
                          "section_id": cur_sid, "text": cur_text})
                return not self._interrupted(exec_id)

            result = self._orchestrator.execute_debate(
                agent_type_a=agent_a, agent_type_b=agent_b, topic=topic,
                rounds=rounds, on_token=on_token, on_round_start=on_round_start,
                on_should_stop=lambda: self._interrupted(exec_id),
            )

            # Flush + clôture de la dernière section.
            if cur_sid is not None:
                emit({"type": "agent_section_chunk", "exec_id": exec_id,
                      "section_id": cur_sid, "text": cur_text})
            finish_current(not self._interrupted(exec_id))

            interrupted = self._interrupted(exec_id)
            if interrupted:
                status_text = "⛔ Débat interrompu"
                ok = False
            elif result.get("success"):
                done = result.get("rounds_completed", 0)
                status_text = f"✅ Débat terminé ({done} tour{'s' if done > 1 else ''})"
                ok = True
            else:
                status_text = f"❌ {result.get('error', 'erreur inconnue')}"
                ok = False
            emit({"type": "agent_exec_end", "exec_id": exec_id,
                  "success": ok, "interrupted": interrupted,
                  "status_text": status_text})

        except Exception as exc:
            logger.exception("Débat agents échoué (exec_id=%s)", exec_id)
            emit({"type": "agent_exec_error", "exec_id": exec_id,
                  "message": f"Erreur débat : {exc}"})
        finally:
            self._interrupts.pop(exec_id, None)
            self._busy = False
