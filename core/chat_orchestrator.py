"""
ChatOrchestrator — Orchestrateur amélioré pour la page Chat

Implémente les design patterns préconisés par la vidéo sur les agents IA :

  ┌─────────────────────────────────────────────────────────────────────┐
  │  DESIGN PATTERNS IMPLEMENTÉS                                        │
  │  1. ReAct  : Reasoning + Acting — boucle Réfléchis → Agis → Observe │
  │  2. Plan & Execute — scratchpad persistant (objectif, plan,         │
  │     étape, faits, prochaine action)                                 │
  │  3. Sécurités : limite de tours, détection de boucle,               │
  │     validation des arguments, élagage sélectif du contexte          │
  └─────────────────────────────────────────────────────────────────────┘

L'orchestrateur est instancié une fois dans AIEngine et appelé depuis
process_query_stream() pour toute requête qui déclenche du tool-calling.
Il NE touche PAS à agent_orchestrator.py (page Agents).
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

# ─────────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────────

MAX_TOURS: int = 15             # Limite absolue de tours dans la boucle agentique
MAX_HISTORY_MESSAGES: int = 40  # Élagage sélectif : nb max de messages d'historique
LOOP_THRESHOLD: int = 2         # Nb d'appels identiques avant détecter boucle élargie
COMPACT_THRESHOLD: int = 28     # Nb de messages avant compaction (hors system + user)
PLAN_MIN_QUERY_LEN: int = 55    # Longueur minimale pour déclencher la planification
MAX_TOOL_USES: int = 5          # Nb max d'appels outils avant synthèse forcée

# Marqueurs d'hallucination dans la réponse finale
HALLUCINATION_MARKERS: List[str] = [
    "je n'ai pas accès",
    "je n'ai pas la capacité",
    "je n'ai pas accès à internet",
    "je ne peux pas accéder",
    "je suis incapable d'accéder",
    "as a language model",
    "as an ai",
    "en tant que modèle",
    "je ne dispose pas d'informations en temps réel",
    "mes données s'arrêtent",
    "ma date de coupure",
]


# ─────────────────────────────────────────────────────────────────────────────
# LoopDetector — filet de sécurité n°3 (détection de boucle intelligente)
# ─────────────────────────────────────────────────────────────────────────────

class LoopDetector:
    """
    Vérifie si le LLM appelle le même outil avec les mêmes paramètres.

    Deux cas détectés :
      - Boucle immédiate : appel identique consécutif
      - Boucle élargie   : même signature appelée >= LOOP_THRESHOLD fois
    """

    def __init__(self) -> None:
        # Liste ordonnée de (tool_name, args_json) — signatures des appels
        self._signatures: List[Tuple[str, str]] = []

    def check(self, tool_name: str, arguments: Dict) -> Tuple[bool, str]:
        """
        Vérifie si cet appel constitue une boucle.

        Returns:
            (is_loop, warning_message)
        """
        try:
            sig = (tool_name, json.dumps(arguments, sort_keys=True, ensure_ascii=False))
        except (TypeError, ValueError):
            sig = (tool_name, str(arguments))

        # Cas 1 : même appel que le précédent
        if self._signatures and self._signatures[-1] == sig:
            return True, (
                f"Tu viens de faire exactement le même appel à '{tool_name}' "
                "avec les mêmes paramètres. Voici le résultat précédent. "
                "Utilise ces informations pour formuler ta réponse finale — "
                "inutile de rappeler cet outil."
            )

        # Cas 2 : appel déjà effectué LOOP_THRESHOLD fois ou plus
        if self._signatures.count(sig) >= LOOP_THRESHOLD:
            return True, (
                f"Tu as déjà appelé '{tool_name}' avec ces paramètres "
                f"{self._signatures.count(sig)} fois. "
                "Essaie une approche différente ou passe directement à la synthèse."
            )

        self._signatures.append(sig)
        return False, ""


# ─────────────────────────────────────────────────────────────────────────────
# Scratchpad — état interne maintenu entre les tours (technique du scratchpad)
# ─────────────────────────────────────────────────────────────────────────────

class Scratchpad:
    """
    Maintient l'état cognitif de l'agent entre les tours.

    Structure :
        OBJECTIF       : la demande originale de l'utilisateur
        PLAN           : étapes prévues, avec ✓ sur les terminées
        ÉTAPE ACTUELLE : numéro de l'étape en cours
        FAITS COLLECTÉS: résultats d'outils résumés
        TOURS RESTANTS : indicateur de proximité à la limite
        PROCHAINE ACTION: intention du prochain tour
    """

    def __init__(self, goal: str) -> None:
        self.goal = goal
        self.plan: List[str] = []
        self.current_step: int = 0
        self.facts: Dict[str, str] = {}
        self.next_action: str = "Analyser la demande et planifier les étapes"
        self.tour: int = 0

    def set_plan(self, steps: List[str]) -> None:
        """Initialise le plan à partir d'une liste d'étapes générées par le LLM."""
        self.plan = [s.strip() for s in steps if s.strip()]

    def update_from_tool_result(self, tool_name: str, result: str) -> None:
        """Enregistre le résultat d'un outil dans les faits collectés."""
        # Clé lisible basée sur le nom de l'outil
        key = _tool_display_name(tool_name)
        # Tronquer à 400 chars pour éviter de polluer le prompt
        self.facts[key] = result[:400] if len(result) > 400 else result

    def mark_step_done(self) -> None:
        """Avance d'une étape dans le plan."""
        self.current_step = min(self.current_step + 1, len(self.plan))

    def to_context_block(self) -> str:
        """
        Sérialise le scratchpad en bloc XML pour injection dans le system prompt.
        Le modèle DOIT lire ce bloc à chaque tour pour maintenir la cohérence.
        """
        plan_lines = ""
        for i, step in enumerate(self.plan):
            marker = "✓" if i < self.current_step else " "
            plan_lines += f"  {i + 1}. [{marker}] {step}\n"
        if not plan_lines:
            plan_lines = "  (plan à définir au prochain tour)\n"

        facts_lines = ""
        for k, v in self.facts.items():
            facts_lines += f"  • {k} : {v[:200]}\n"
        if not facts_lines:
            facts_lines = "  (aucun fait collecté pour l'instant)\n"

        remaining = max(0, MAX_TOURS - self.tour)
        urgency = " ⚠️ FINALISE MAINTENANT" if remaining <= 3 else ""

        return (
            "<scratchpad>\n"
            f"OBJECTIF : {self.goal}\n"
            f"PLAN :\n{plan_lines}"
            f"ÉTAPE ACTUELLE : {self.current_step + 1}\n"
            f"FAITS COLLECTÉS :\n{facts_lines}"
            f"TOURS RESTANTS : {remaining}/{MAX_TOURS}{urgency}\n"
            f"PROCHAINE ACTION : {self.next_action}\n"
            "</scratchpad>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# ChatOrchestrator — boucle agentique principale
# ─────────────────────────────────────────────────────────────────────────────

class ChatOrchestrator:
    """
    Orchestrateur amélioré pour la page Chat.

    Il remplace l'appel direct à LocalLLM.generate_with_tools_stream() dans
    AIEngine.process_query_stream() et y ajoute :

      1. Scratchpad structuré (plan + état + faits collectés)
      2. Limite de tours avec message forcé avant coupure
      3. Détection de boucle intelligente (LoopDetector)
      4. Élagage sélectif du contexte (pruning)
      5. Validation légère des arguments avant exécution
      6. Synthèse streamée après exécution d'outils

    Interface publique : une seule méthode `run()`.
    """

    # ---------------------------------------------------------------- run ---

    def run(
        self,
        user_input: str,
        tools: List[Dict],
        tool_executor: Callable[[str, Dict], str],
        llm: Any,                          # instance de LocalLLM
        system_prompt: str,
        on_token: Optional[Callable] = None,
        on_thinking_token: Optional[Callable] = None,
        on_thinking_complete: Optional[Callable] = None,
        is_interrupted_callback: Optional[Callable] = None,
    ) -> Optional[str]:
        """
        Lance la boucle agentique ReAct.

        Args:
            user_input:              message utilisateur (peut contenir un contexte
                                     de raisonnement pré-calculé)
            tools:                   liste d'outils au format Ollama
            tool_executor:           callable(tool_name, args) → str
            llm:                     instance LocalLLM (fournit model, chat_url,
                                     timeout, conversation_history, add_to_history,
                                     parse_text_tool_call)
            system_prompt:           prompt système de base (construit par AIEngine)
            on_token:                callback pour streamer la réponse finale
            on_thinking_token:       callback pour streamer le plan dans le widget
                                     raisonnement (même widget que le Thinking Mode)
            is_interrupted_callback: retourne True si l'utilisateur a cliqué STOP

        Returns:
            Réponse finale (str) ou None si interruption / aucun résultat
        """
        if not getattr(llm, "is_ollama_available", False):
            return None

        # ── Initialisation ────────────────────────────────────────────────
        scratchpad = Scratchpad(goal=user_input)
        loop_detector = LoopDetector()
        known_tool_names: List[str] = [
            t.get("function", {}).get("name", "")
            for t in tools
            if isinstance(t, dict)
        ]
        tool_calls_log: List[Dict] = []
        last_tool_results: Dict[str, str] = {}
        blocked_tools: set = set()  # Outils bloqués définitivement pour cette requête
        force_synthesis: bool = False  # Quand True, retirer tous les outils

        # Contexte de messages — élagage sélectif dès le départ
        messages: List[Dict] = self._build_initial_messages(
            system_prompt=system_prompt,
            user_input=user_input,
            history=getattr(llm, "conversation_history", []),
        )

        # ── Compaction du contexte si trop long ───────────────────────────
        messages = self._compact_context_if_needed(messages, llm)

        # ── Plan & Execute : pré-planification pour requêtes complexes ────
        # La planification n'a du sens que si le widget raisonnement est visible
        # (on_thinking_token fourni). Sans widget, les tokens du plan sont
        # générés mais invisibles ET jamais injectés (pas d'outil appelé) :
        # pure perte de 10-15 secondes avant la vraie réponse.
        if self._should_plan(user_input, tools) and on_thinking_token is not None:
            plan_steps = self._generate_plan_stream(
                user_input, llm, on_thinking_token
            )
            if plan_steps:
                scratchpad.set_plan(plan_steps)
                print(
                    f"📋 [ChatOrchestrator] Plan généré ({len(plan_steps)} étapes) : "
                    + " | ".join(plan_steps)
                )
        # Stopper les dots du widget raisonnement maintenant que le plan est affiché.
        # Le widget reste visible avec son contenu ; seule l'animation s'arrête.
        if on_thinking_complete:
            on_thinking_complete()

        # ── Boucle ReAct ─────────────────────────────────────────────────
        for tour in range(MAX_TOURS):
            scratchpad.tour = tour

            # Vérification d'interruption
            if is_interrupted_callback and is_interrupted_callback():
                print(f"🛑 [ChatOrchestrator] Tour {tour + 1} — interruption utilisateur")
                return None

            # Injection du scratchpad dans le system prompt (après 1er outil)
            if tool_calls_log:
                messages = self._inject_scratchpad(messages, scratchpad)

            # Avertissement avant limite
            if tour == MAX_TOURS - 3 and tool_calls_log:
                messages.append({
                    "role": "user",
                    "content": (
                        f"[ORCHESTRATEUR] Tu as utilisé {len(tool_calls_log)} outil(s). "
                        f"Il te reste {MAX_TOURS - tour} tours maximum. "
                        "Si tu as assez d'informations, donne ta réponse finale maintenant."
                    ),
                })
                print(f"⚠️  [ChatOrchestrator] Avertissement de limite — tour {tour + 1}/{MAX_TOURS}")

            # Synthèse forcée à la dernière chance
            if tour >= MAX_TOURS - 1:
                print("🏁 [ChatOrchestrator] Limite atteinte — synthèse forcée")
                messages.append({
                    "role": "user",
                    "content": (
                        f"[ORCHESTRATEUR] Tu as atteint la limite de {MAX_TOURS} actions. "
                        "Donne ta meilleure réponse finale avec ce que tu as collecté jusqu'ici. "
                        "Sois direct et complet. "
                        "Conserve les liens sources au format [Titre](URL)."
                    ),
                })

            # ── Appel Ollama (streaming adaptatif) ─────────────────────
            # Streame les tokens en temps réel quand la réponse est textuelle.
            # Détecte automatiquement les tool_calls (structurés ou textuels).
            # Le streaming vers on_token n'est activé que s'il n'y a pas eu
            # d'appels d'outils précédents (sinon → synthèse séparée).
            if len(tool_calls_log) >= MAX_TOOL_USES or force_synthesis:
                tools_for_call = []
            elif blocked_tools:
                # Retirer les outils bloqués de la liste
                tools_for_call = [
                    t for t in tools
                    if t.get("function", {}).get("name", "") not in blocked_tools
                ]
            else:
                tools_for_call = tools

            _stream_direct = on_token if not tool_calls_log else None
            response_msg = self._call_ollama_smart_stream(
                llm=llm,
                messages=messages,
                tools=tools_for_call,
                on_token=_stream_direct,
                is_interrupted_callback=is_interrupted_callback,
            )
            if response_msg is None:
                print(f"⚠️  [ChatOrchestrator] Appel Ollama échoué au tour {tour + 1}")
                break

            raw_content: str = response_msg.get("content", "")
            tool_calls_in_msg: List[Dict] = response_msg.get("tool_calls", [])
            _content_was_streamed: bool = response_msg.get("streamed", False)

            # ── Cas A : text tool call caché (bug llama3.2 / mistral) ─────
            # Le modèle écrit parfois le JSON de tool call en texte au lieu
            # d'utiliser le champ tool_calls.  Le contenu peut contenir du
            # texte avant/après le JSON (ex: explication en français, code
            # fence markdown ```json ... ```).
            # NB: si le contenu a déjà été streamé vers le GUI, on ne tente
            # pas CAS A (le buffer initial a vérifié que ce n'est pas du JSON).
            if not tool_calls_in_msg and not _content_was_streamed:
                _stripped = raw_content.strip()
                # Retirer les code fences markdown si présentes
                _stripped = re.sub(r'^```\w*\s*', '', _stripped)
                _stripped = re.sub(r'\s*```', '', _stripped, count=1)
                _stripped = _stripped.strip()
                _json_candidate = None
                if _stripped.startswith("{") or _stripped.startswith("["):
                    _json_candidate = _stripped
                else:
                    # Chercher un bloc JSON embarqué dans du texte
                    _m = re.search(r'(\{[\s\S]*?"name"\s*:\s*"[\s\S]*?\})', _stripped)
                    if _m:
                        _json_candidate = _m.group(1)
                if _json_candidate:
                    # Extraire uniquement le JSON (ignorer le texte après)
                    _json_block = self._extract_json_block(_json_candidate)
                    if _json_block:
                        detected = llm.parse_text_tool_call(_json_block, known_tool_names)
                        if detected:
                            tool_calls_in_msg = [{"function": {
                                "name": detected["name"],
                                "arguments": detected.get("arguments", {}),
                            }}]
                            print(f"🔧 [CAS A] Text tool call converti : {detected['name']}")

            # ── Cas B : réponse directe (pas d'outil) ────────────────────
            if not tool_calls_in_msg:
                if tool_calls_log:
                    # Des outils ont été appelés → synthèse streamée + validation
                    print(
                        f"✅ [ChatOrchestrator] {len(tool_calls_log)} outil(s) utilisé(s) "
                        f"→ synthèse streamée (tour {tour + 1})"
                    )
                    synthesis = self._stream_synthesis(
                        messages=messages,
                        user_input=user_input,
                        llm=llm,
                        on_token=on_token,
                        is_interrupted_callback=is_interrupted_callback,
                        tool_calls_log=tool_calls_log,
                    )
                    if synthesis:
                        valid, reason = self._validate_response(
                            synthesis, user_input, tool_calls_log
                        )
                        if not valid:
                            print(
                                f"⚠️  [ChatOrchestrator] Synthèse invalide ({reason}) "
                                f"→ retry sans outils"
                            )
                            retry = self._retry_without_tools(
                                user_input=user_input,
                                llm=llm,
                                system_prompt=system_prompt,
                                on_token=on_token,
                                is_interrupted_callback=is_interrupted_callback,
                            )
                            return retry or synthesis
                    return synthesis
                else:
                    # Réponse directe sans outil
                    if raw_content:
                        # Validation (retry uniquement si pas encore streamé)
                        if not _content_was_streamed:
                            valid, reason = self._validate_response(
                                raw_content, user_input, tool_calls_log
                            )
                            if not valid:
                                print(
                                    f"⚠️  [ChatOrchestrator] Réponse invalide ({reason}) "
                                    f"→ retry sans outils"
                                )
                                retry = self._retry_without_tools(
                                    user_input=user_input,
                                    llm=llm,
                                    system_prompt=system_prompt,
                                    on_token=on_token,
                                    is_interrupted_callback=is_interrupted_callback,
                                )
                                if retry:
                                    return retry
                            # Pas encore streamé → envoyer maintenant
                            if on_token:
                                on_token(raw_content)
                        print(
                            f"✅ [ChatOrchestrator] Réponse directe sans outil "
                            f"(tour {tour + 1})"
                            f"{' [streamé]' if _content_was_streamed else ''}"
                        )
                        llm.add_to_history("user", user_input)
                        llm.add_to_history("assistant", raw_content)
                        return raw_content
                break  # rien à faire, sortir proprement

            # ── Cas C : tool calls détectés ───────────────────────────────
            # Ajouter le message de l'assistant dans le contexte
            messages.append({
                "role": "assistant",
                "content": raw_content,
                "tool_calls": tool_calls_in_msg,
            })

            for tool_call in tool_calls_in_msg:
                if is_interrupted_callback and is_interrupted_callback():
                    return None

                func = tool_call.get("function", {})
                tool_name: str = func.get("name", "")
                arguments: Dict = self._clean_arguments(func.get("arguments", {}))

                if not tool_name:
                    continue

                # ── Filtrage des outils non pertinents ────────────────────
                # generate_code : n'autoriser QUE si la requête demande
                # explicitement du code. Sinon, bloquer.
                if tool_name == "generate_code":
                    _q = user_input.lower()
                    _code_signals = [
                        "code", "programme", "script", "fonction", "class",
                        "implémente", "crée un programme", "génère un code",
                        "développe", "écris un", "coding", "coder",
                        "write a", "create a script", "implement",
                        "génère un script", "génère une fonction",
                    ]
                    if not any(sig in _q for sig in _code_signals):
                        blocked_tools.add(tool_name)
                        print(
                            f"🚫 [ChatOrchestrator] Outil '{tool_name}' bloqué "
                            f"(requête ne demande pas de code)"
                        )
                        continue

                # calculate : bloquer pour les requêtes de recherche / explication
                if tool_name == "calculate":
                    _q = user_input.lower()
                    _search_signals = [
                        "cherche", "recherche", "news", "actualité", "dernière",
                        "résumé", "trouve", "info sur", "qu'est-ce que",
                        "search", "find", "latest", "summary",
                        "explique", "différence", "avantage", "inconvénient",
                        "compare", "c'est quoi", "définition", "comment fonctionne",
                    ]
                    if any(sig in _q for sig in _search_signals):
                        blocked_tools.add(tool_name)
                        print(
                            f"🚫 [ChatOrchestrator] Outil '{tool_name}' bloqué "
                            f"(requête de type recherche/explication)"
                        )
                        continue

                # ── Vérification de boucle ────────────────────────────────
                is_loop, loop_msg = loop_detector.check(tool_name, arguments)
                if is_loop:
                    print(f"🔄 [ChatOrchestrator] Boucle détectée : {tool_name}(…)")
                    prev_result = last_tool_results.get(tool_name, "Résultat précédent non disponible.")
                    messages.append({
                        "role": "tool",
                        "content": (
                            f"AVERTISSEMENT ORCHESTRATEUR : {loop_msg}\n"
                            f"Résultat précédent : {prev_result}"
                        ),
                    })
                    scratchpad.next_action = "Changer d'approche — boucle détectée, aller vers la synthèse"
                    continue


                print(
                    f"🔧 [ChatOrchestrator] Tour {tour + 1}/{MAX_TOURS} "
                    f"| {tool_name}({_truncate(json.dumps(arguments, ensure_ascii=False), 80)})"
                )

                # ── Exécution de l'outil ──────────────────────────────────
                try:
                    tool_result = tool_executor(tool_name, arguments)
                except Exception as exc:
                    tool_result = f"[Erreur lors de l'exécution de '{tool_name}']: {exc}"
                    print(f"   ❌ Erreur outil : {exc}")

                result_str = str(tool_result)
                print(f"   ↳ Résultat [{tour + 1}/{MAX_TOURS}] : {_truncate(result_str, 120)}")

                # ── Mise à jour du scratchpad ─────────────────────────────
                scratchpad.update_from_tool_result(tool_name, result_str)
                scratchpad.mark_step_done()
                scratchpad.next_action = "Analyser le résultat et décider de la prochaine étape"
                last_tool_results[tool_name] = result_str[:2000]

                tool_calls_log.append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "result_preview": result_str[:200],
                })

                # Réinjection du résultat dans le contexte
                messages.append({
                    "role": "tool",
                    "content": result_str,
                })

            # ── Relance adaptative selon la qualité des données collectées ───
            # Utiliser la vraie longueur des résultats stockés (pas le preview tronqué)
            total_data_chars = sum(
                len(last_tool_results.get(tc.get("tool", ""), ""))
                for tc in tool_calls_log
            )
            # Vérifier si les résultats semblent vides ou erreur
            _last_tool_name = tool_calls_log[-1].get("tool", "") if tool_calls_log else ""
            _last_result = last_tool_results.get(_last_tool_name, "")
            _result_is_poor = (
                total_data_chars < 300
                or "Aucun résultat" in _last_result
                or "[Erreur" in _last_result
                or "Information non trouvée" in _last_result
            )

            if _result_is_poor and len(tool_calls_log) < MAX_TOOL_USES:
                # Résultats insuffisants → encourager à retenter avec d'autres termes
                print(
                    f"   ⚠️  [ChatOrchestrator] Résultats pauvres ({total_data_chars} chars) "
                    f"→ incitation à reformuler (tour {tour + 1})"
                )
                messages.append({
                    "role": "user",
                    "content": (
                        "Les résultats de recherche précédents sont insuffisants ou vides. "
                        "Reformule ta recherche avec des mots-clés DIFFÉRENTS. "
                        f"Essaie en anglais (ex: 'Python latest news {datetime.now().year}', "
                        "'Python releases') "
                        "ou avec des termes alternatifs plus spécifiques. "
                        "Utilise l'outil web_search avec cette nouvelle requête."
                    ),
                })
            elif total_data_chars > 500:
                # Données substantielles → FORCER la synthèse en retirant les outils
                force_synthesis = True
                print(
                    f"   ✅ [ChatOrchestrator] Données substantielles ({total_data_chars} chars) "
                    f"→ synthèse forcée (tour {tour + 1})"
                )
                messages.append({
                    "role": "user",
                    "content": (
                        "STOP — tu as collecté suffisamment de données. "
                        "N'appelle PLUS aucun outil. "
                        "En te basant UNIQUEMENT sur les résultats collectés ci-dessus, "
                        f"réponds directement et précisément à ma question : {user_input}\n"
                        "IMPORTANT : dans la section Sources, conserve les URLs sous forme de liens "
                        "cliquables au format [Titre](URL). Ne mets jamais un nom de source sans son URL."
                    ),
                })
            else:
                # Cas intermédiaire → laisser le modèle décider
                messages.append({
                    "role": "user",
                    "content": (
                        "Analyse les résultats obtenus. Si tu as assez d'informations, "
                        f"réponds à ma question : {user_input}. "
                        "Sinon, utilise un autre outil avec une approche différente."
                    ),
                })

        # ── Sortie de boucle : synthèse de secours ────────────────────────
        if tool_calls_log:
            print(
                f"🔁 [ChatOrchestrator] Sortie de boucle — "
                f"{len(tool_calls_log)} outil(s) — synthèse de secours"
            )
            result = self._stream_synthesis(
                messages=messages,
                user_input=user_input,
                llm=llm,
                on_token=on_token,
                is_interrupted_callback=is_interrupted_callback,
                tool_calls_log=tool_calls_log,
            )
            # Validation finale de la synthèse
            if result:
                valid, reason = self._validate_response(result, user_input, tool_calls_log)
                if not valid:
                    print(f"⚠️  [ChatOrchestrator] Synthèse invalide ({reason}) → retry")
                    retry = self._retry_without_tools(
                        user_input=user_input,
                        llm=llm,
                        system_prompt=system_prompt,
                        on_token=on_token,
                        is_interrupted_callback=is_interrupted_callback,
                    )
                    return retry or result
            return result

        return None

    # ─────────────────────────────────────── méthodes internes ──────────────

    # ──────────────────────────── Plan & Execute ────────────────────────────

    @staticmethod
    def _should_plan(user_input: str, tools: List[Dict]) -> bool:
        """
        Décide si la requête mérite une étape de planification préalable.

        Critères :
          - La requête est suffisamment longue (pas une question simple)
          - Et elle contient des signaux de tâche multi-étapes
          - Ou plusieurs outils sont disponibles (capacités larges)
        """
        q = user_input.lower()

        # Questions courtes / conversationnelles → pas de plan
        if len(user_input) < PLAN_MIN_QUERY_LEN:
            return False

        # Signaux de tâche complexe / multi-étapes
        multi_step_signals = [
            "puis", "ensuite", "et aussi", "compare", "comparaison",
            "analyse", "synthèse", "synthétise", "résumé complet",
            "étape", "d'abord", "premièrement", "deuxièmement",
            "en plusieurs", "liste", "énumère", "rapport", "rapport complet",
            "plan", "planifie", "stratégie",
        ]
        if any(sig in q for sig in multi_step_signals):
            return True

        # Plusieurs outils disponibles → requête probablement ambitieuse
        if len(tools) >= 3:
            return True

        return False

    def _generate_plan_stream(
        self,
        user_input: str,
        llm: Any,
        on_thinking_token: Optional[Callable] = None,
    ) -> List[str]:
        """
        Génère un plan en streaming — chaque token est envoyé en temps réel
        au widget raisonnement via on_thinking_token.

        Utilise stream=True pour éviter les timeouts sur cold-start Ollama
        et offrir un affichage progressif identique au Thinking Mode.

        Returns:
            Liste d'étapes (ex: ["Rechercher les données X", "Y", ...])
            Liste vide si la planification échoue.
        """
        plan_prompt = (
            "Liste les actions concrètes et SPÉCIFIQUES à effectuer pour cette tâche.\n"
            "NE RÉPONDS PAS à la question. N'invente AUCUN contenu.\n\n"
            f"Tâche : « {user_input} »\n\n"
            f"Date du jour : {datetime.now().strftime('%d/%m/%Y')}\n\n"
            "Génère entre 3 et 5 étapes numérotées, adaptées au sujet.\n"
            "Chaque étape doit être détaillée et mentionner l'action précise "
            "(ex: le sujet recherché, le type d'analyse, le format attendu).\n"
            "NE COPIE PAS un plan générique. Adapte chaque étape au contenu de la tâche.\n"
            "Format attendu :\n"
            "1. [action détaillée]\n"
            "2. [action détaillée]\n"
            "...\n"
        )
        plan_system = (
            "Tu es un planificateur de tâches. Tu listes entre 3 et 5 étapes "
            "d'action concrètes et spécifiques au sujet demandé. "
            "Chaque étape doit être différente et détaillée. Rien d'autre."
        )
        messages = [
            {"role": "system", "content": plan_system},
            {"role": "user", "content": plan_prompt},
        ]
        data = {
            "model": llm.model,
            "messages": messages,
            "stream": True,
            "think": False,
            "options": {"temperature": 0.3, "num_ctx": 4096, "num_predict": 300},
        }

        full_content: str = ""
        header_sent = False

        try:
            with requests.post(
                llm.chat_url, json=data, timeout=llm.timeout, stream=True
            ) as resp:
                if resp.status_code != 200:
                    return []

                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    try:
                        chunk = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue

                    token: str = chunk.get("message", {}).get("content", "")
                    if token:
                        full_content += token
                        # Envoyer le header une seule fois au premier token
                        if on_thinking_token and not header_sent:
                            on_thinking_token("📋 Plan d'action :\n")
                            header_sent = True
                        if on_thinking_token:
                            on_thinking_token(token)

                    if chunk.get("done"):
                        break

        except Exception as exc:
            print(f"⚠️  [ChatOrchestrator] _generate_plan_stream échoué : {exc}")
            return []

        # Terminer le bloc de plan avec un saut de ligne
        if on_thinking_token and full_content:
            on_thinking_token("\n")

        # Parser les lignes numérotées
        steps: List[str] = []
        for line in full_content.splitlines():
            line = line.strip()
            cleaned = re.sub(r"^[\d]+[.)\-]\s*", "", line).strip()
            if cleaned and len(cleaned) > 3:
                steps.append(cleaned)
        return steps[:6]

    # ──────────────────────────── Validation des sorties ────────────────────

    @staticmethod
    def _validate_response(
        response: str,
        user_input: str,
        tool_calls_log: List[Dict],
    ) -> Tuple[bool, str]:
        """
        Valide la réponse finale selon des règles logiques.

        Vérifie :
          1. La réponse n'est pas vide ou ridiculement courte
          2. Elle ne contient pas de marqueurs d'hallucination
             (ex: "je n'ai pas accès" alors que des outils ont été appelés)
          3. Elle ne contient pas de JSON brut non traité

        Returns:
            (is_valid: bool, reason: str)
        """
        text = response.strip()

        # Règle 1 : trop courte
        if len(text) < 10:
            return False, "réponse trop courte"

        # Règle 1b : réponse anormalement courte pour une question complexe
        if len(user_input) > 80 and len(text) < 25:
            return False, "réponse trop courte pour une question complexe"

        # Règle 2 : marqueurs d'hallucination
        text_lower = text.lower()
        if tool_calls_log:  # Des outils ont été appelés — la réponse doit s'en servir
            for marker in HALLUCINATION_MARKERS:
                if marker in text_lower:
                    return False, f"hallucination détectée : '{marker}'"

        # Règle 3 : JSON brut non traité (outil non exécuté)
        stripped = text.lstrip()
        if stripped.startswith("{") and "\"name\"" in text and "\"parameters\"" in text:
            return False, "JSON de tool call brut non traité"

        return True, "ok"

    def _retry_without_tools(
        self,
        user_input: str,
        llm: Any,
        system_prompt: str,
        on_token: Optional[Callable],
        is_interrupted_callback: Optional[Callable],
    ) -> Optional[str]:
        """
        Relance une génération stream simple, sans outils, quand la réponse
        précédente a échoué la validation.
        """
        print("🔄 [ChatOrchestrator] Retry sans outils…")
        try:
            return llm.generate_stream(
                prompt=user_input,
                system_prompt=system_prompt,
                on_token=on_token,
                is_interrupted_callback=is_interrupted_callback,
            )
        except Exception as exc:
            print(f"⚠️  [ChatOrchestrator] _retry_without_tools échoué : {exc}")
            return None

    # ──────────────────────────── Compaction du contexte ────────────────────

    def _compact_context_if_needed(
        self,
        messages: List[Dict],
        llm: Any,
    ) -> List[Dict]:
        """
        Compacte le contexte quand il dépasse COMPACT_THRESHOLD messages.

        Stratégie (inspirée du diagramme de la vidéo) :
          1. Détecter que les tokens dépassent le seuil (approx. via nb de messages)
          2. Résumer les anciens échanges via un appel Ollama
          3. Créer un bloc de compaction qui remplace ces anciens messages
          4. La suite de la conversation continue avec le contexte allégé

        Le message système et le message utilisateur courant ne sont jamais supprimés.
        """
        # Identifier system + user courant (toujours préservés)
        if len(messages) < 3:
            return messages

        system_msg = messages[0] if messages[0].get("role") == "system" else None
        user_msg = messages[-1]  # Message utilisateur courant

        # Messages intermédiaires (historique)
        start_idx = 1 if system_msg else 0
        history_msgs = messages[start_idx:-1]

        if len(history_msgs) <= COMPACT_THRESHOLD:
            return messages  # Pas encore nécessaire

        # Séparer : vieux messages à compacter / récents à conserver
        split = len(history_msgs) // 2
        to_compact = history_msgs[:split]
        to_keep = history_msgs[split:]

        # Construire le texte à résumer
        summary_input = "\n".join(
            f"[{m.get('role', '?').upper()}] : {str(m.get('content', ''))[:300]}"
            for m in to_compact
        )

        summary_prompt = (
            "Résume de façon concise (5-8 phrases max) les échanges suivants "
            "en préservant tous les faits importants, les décisions prises et "
            "le contexte essentiel pour la suite de la conversation :\n\n"
            + summary_input
        )

        print(
            f"📦 [ChatOrchestrator] Compaction : {len(to_compact)} messages "
            f"→ résumé (seuil : {COMPACT_THRESHOLD})"
        )

        try:
            summary_data = {
                "model": llm.model,
                "messages": [
                    {"role": "system", "content": "Tu es un assistant de résumé. Sois concis et fidèle."},
                    {"role": "user", "content": summary_prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.1, "num_ctx": 8192, "num_predict": 512},
            }
            resp = requests.post(llm.chat_url, json=summary_data, timeout=60)
            if resp.status_code == 200:
                summary_text = resp.json().get("message", {}).get("content", "")
                if summary_text:
                    compaction_block = {
                        "role": "system",
                        "content": (
                            "[BLOC DE COMPACTION — résumé des échanges précédents]\n"
                            + summary_text
                        ),
                    }
                    # Reconstruire : system + compaction_block + récents + user courant
                    new_messages: List[Dict] = []
                    if system_msg:
                        new_messages.append(system_msg)
                    new_messages.append(compaction_block)
                    new_messages.extend(to_keep)
                    new_messages.append(user_msg)
                    print(
                        f"   ↳ Contexte réduit : {len(messages)} → {len(new_messages)} messages"
                    )
                    return new_messages
        except Exception as exc:
            print(f"⚠️  [ChatOrchestrator] Compaction échouée : {exc}")

        return messages  # Fallback : retourner les messages inchangés

    def _build_initial_messages(
        self,
        system_prompt: str,
        user_input: str,
        history: List[Dict],
    ) -> List[Dict]:
        """
        Construit la liste initiale de messages en appliquant l'élagage sélectif.

        L'élagage sélectif (technique de la vidéo) conserve :
          - Le message système (jamais supprimé)
          - Les MAX_HISTORY_MESSAGES messages les plus récents de l'historique
          - Le message utilisateur courant
        """
        messages: List[Dict] = []
        messages.append({"role": "system", "content": system_prompt})

        # Élagage : garder uniquement les N derniers échanges
        pruned_history = list(history)[-MAX_HISTORY_MESSAGES:]
        messages.extend(pruned_history)

        messages.append({"role": "user", "content": user_input})
        return messages

    def _inject_scratchpad(
        self,
        messages: List[Dict],
        scratchpad: Scratchpad,
    ) -> List[Dict]:
        """
        Injecte ou met à jour le bloc <scratchpad> dans le message système.

        Le scratchpad force le LLM à re-synthétiser son état à chaque tour,
        évitant la perte de cohérence sur des tâches multi-étapes.
        """
        if not messages or messages[0].get("role") != "system":
            return messages

        base_content = messages[0]["content"]
        # Retirer l'ancien scratchpad s'il existe
        base_content = re.sub(
            r"\n*<scratchpad>.*?</scratchpad>",
            "",
            base_content,
            flags=re.DOTALL,
        ).rstrip()

        # Ajouter le scratchpad mis à jour
        new_system = base_content + "\n\n" + scratchpad.to_context_block()

        updated = list(messages)
        updated[0] = {"role": "system", "content": new_system}
        return updated

    def _call_ollama_no_stream(
        self,
        llm: Any,
        messages: List[Dict],
        tools: List[Dict],
    ) -> Optional[Dict]:
        """
        Effectue un appel Ollama non-streamé et retourne le message de réponse.

        Non-streamé nécessaire pour pouvoir détecter le champ `tool_calls`
        dans la réponse JSON.
        """
        data = {
            "model": llm.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.7,
                "num_ctx": 32768,
                "num_predict": 4096,
            },
        }
        try:
            resp = requests.post(llm.chat_url, json=data, timeout=llm.timeout)
            if resp.status_code != 200:
                print(f"⚠️  [ChatOrchestrator] HTTP {resp.status_code}")
                return None
            msg = resp.json().get("message", {})
            return msg
        except Exception as exc:
            print(f"⚠️  [ChatOrchestrator] Exception appel Ollama : {exc}")
            return None

    def _call_ollama_smart_stream(
        self,
        llm: Any,
        messages: List[Dict],
        tools: List[Dict],
        on_token: Optional[Callable] = None,
        is_interrupted_callback: Optional[Callable] = None,
    ) -> Optional[Dict]:
        """
        Appel Ollama en streaming adaptatif avec détection de tool_calls.

        Résout le problème du non-streaming : au lieu de bloquer jusqu'à la fin
        de la génération, cette méthode streame les tokens en temps réel.

        Comportement :
          - Les premiers tokens sont bufferisés (BUFFER_CHARS) pour détecter
            si le modèle écrit un tool call en texte (CAS A : bug llama3.2/mistral)
          - Si tool_calls structuré détecté → accumulation silencieuse
          - Si le buffer ressemble à du JSON → accumulation silencieuse (CAS A)
          - Si le buffer est du texte naturel → flush + streaming temps réel
            via on_token

        Returns:
            {"content": str, "tool_calls": list, "streamed": bool} ou None
        """
        data = {
            "model": llm.model,
            "messages": messages,
            "tools": tools,
            "stream": True,
            "think": False,
            "options": {
                "temperature": 0.7,
                "num_ctx": 32768,
                "num_predict": 4096,
            },
        }

        full_content: str = ""
        tool_calls_collected: List[Dict] = []
        content_buffer: str = ""
        buffer_flushed: bool = False
        BUFFER_CHARS = 120  # Seuil avant de décider stream vs accumulation

        try:
            with requests.post(
                llm.chat_url, json=data, timeout=llm.timeout, stream=True
            ) as resp:
                if resp.status_code != 200:
                    print(f"⚠️  [ChatOrchestrator] smart_stream HTTP {resp.status_code}")
                    return None

                for raw_line in resp.iter_lines():
                    if is_interrupted_callback and is_interrupted_callback():
                        break
                    if not raw_line:
                        continue
                    try:
                        chunk_data = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue

                    msg = chunk_data.get("message", {})

                    # ── Détection des tool_calls structurés ───────────────
                    chunk_tc = msg.get("tool_calls")
                    if chunk_tc:
                        tool_calls_collected.extend(chunk_tc)

                    # ── Accumulation du contenu ───────────────────────────
                    token: str = msg.get("content", "")
                    if token:
                        full_content += token

                        if tool_calls_collected:
                            # Tool calls déjà détectés → pas de streaming
                            pass
                        elif not buffer_flushed:
                            # Phase de buffering initial
                            content_buffer += token
                            if len(content_buffer) >= BUFFER_CHARS:
                                # Vérifier si le buffer ressemble à du JSON (CAS A)
                                _stripped = content_buffer.strip()
                                _stripped = re.sub(r'^```\w*\s*', '', _stripped)
                                _stripped = re.sub(
                                    r'\s*```', '', _stripped, count=1
                                ).strip()
                                if _stripped.startswith(("{", "[")):
                                    # JSON probable → ne pas streamer
                                    pass
                                else:
                                    # Texte naturel → flush le buffer
                                    buffer_flushed = True
                                    if on_token:
                                        on_token(content_buffer)
                        else:
                            # Buffer flushé → streamer chaque token
                            if on_token:
                                result = on_token(token)
                                if result is False:
                                    break

                    if chunk_data.get("done"):
                        break

        except Exception as exc:
            print(f"⚠️  [ChatOrchestrator] smart_stream exception : {exc}")
            return None

        # Buffer non flushé et pas de tool calls → flush maintenant
        if content_buffer and not buffer_flushed and not tool_calls_collected:
            buffer_flushed = True
            if on_token:
                on_token(content_buffer)

        return {
            "content": full_content,
            "tool_calls": tool_calls_collected,
            "streamed": buffer_flushed,
        }

    def _stream_synthesis(
        self,
        messages: List[Dict],
        user_input: str,
        llm: Any,
        on_token: Optional[Callable],
        is_interrupted_callback: Optional[Callable],
        tool_calls_log: List[Dict],
    ) -> Optional[str]:
        """
        Synthèse streamée après exécution d'outils.

        Le system prompt de synthèse remplace l'original pour que le modèle
        ne réponde pas « je n'ai pas accès aux données en temps réel ».
        """
        synthesis_system = (
            "Les informations demandées ont été récupérées en temps réel via des outils. "
            "Tu DOIS utiliser UNIQUEMENT ces données pour répondre à la question. "
            "Ne dis JAMAIS que tu n'as pas accès aux données en temps réel — "
            "tu viens de les recevoir via les outils. "
            "Réponds de façon précise, factuelle et concise.\n\n"
            "FORMATAGE DES SOURCES — RÈGLE OBLIGATOIRE :\n"
            "Si les résultats des outils contiennent des URLs ou des liens au format [Titre](URL), "
            "tu DOIS les reproduire EXACTEMENT dans ta section Sources/Références.\n"
            "Format attendu pour chaque source : [Nom du site](URL complète)\n"
            "Exemple : [Real Python](https://realpython.com/article)\n"
            "Ne mets JAMAIS un nom de source sans son URL. "
            "Reprends les URLs telles quelles depuis les résultats des outils."
        )

        # Remplacer le system prompt original par celui de synthèse
        msgs: List[Dict] = list(messages)
        if msgs and msgs[0].get("role") == "system":
            msgs[0] = {"role": "system", "content": synthesis_system}
        else:
            msgs.insert(0, {"role": "system", "content": synthesis_system})

        data = {
            "model": llm.model,
            "messages": msgs,
            "stream": True,
            "think": False,
            "options": {
                "temperature": 0.7,
                "num_ctx": 32768,
                "num_predict": 4096,
            },
        }

        full_response: str = ""
        try:
            with requests.post(
                llm.chat_url, json=data, timeout=llm.timeout, stream=True
            ) as resp:
                if resp.status_code != 200:
                    print(f"⚠️  [ChatOrchestrator] synthesis stream HTTP {resp.status_code}")
                    return None

                for raw_line in resp.iter_lines():
                    if is_interrupted_callback and is_interrupted_callback():
                        break
                    if not raw_line:
                        continue
                    try:
                        chunk_data = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue

                    token: str = chunk_data.get("message", {}).get("content", "")
                    if token:
                        full_response += token
                        if on_token:
                            result = on_token(token)
                            if result is False:
                                break

                    if chunk_data.get("done"):
                        break

        except Exception as exc:
            print(f"⚠️  [ChatOrchestrator] synthesis stream error : {exc}")

        if full_response:
            llm.add_to_history("user", user_input)
            llm.add_to_history("assistant", full_response)
            print(
                f"✅ [ChatOrchestrator] Synthèse terminée "
                f"({len(tool_calls_log)} outil(s), {len(full_response)} chars)"
            )
            return full_response

        return None

    # ─────────────────────────────────────────── utilitaires ────────────────

    @staticmethod
    def _extract_json_block(text: str) -> Optional[str]:
        """
        Extrait le premier objet JSON valide d'un texte qui peut contenir
        du texte avant/après (ex: explication en français après le JSON).
        Supporte les accolades imbriquées.
        """
        depth = 0
        start_idx = None
        for i, ch in enumerate(text):
            if ch == '{':
                if depth == 0:
                    start_idx = i
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0 and start_idx is not None:
                    candidate = text[start_idx:i + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        start_idx = None
                        continue
        return None

    @staticmethod
    def _clean_arguments(arguments: Dict) -> Dict:
        """
        Nettoie les arguments hallucinés par le LLM.

        Certains modèles retournent le schéma JSON au lieu
        de la valeur : {"query": {"type": "string", "description": "..."}}
        → corrigé en {"query": "description_text"}
        """
        cleaned: Dict = {}
        for k, v in arguments.items():
            if (
                isinstance(v, dict)
                and "type" in v
                and "description" in v
                and v.get("description") != "La requête de recherche"
            ):
                cleaned[k] = v["description"]
            else:
                cleaned[k] = v
        return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _tool_display_name(tool_name: str) -> str:
    """Retourne un nom lisible pour afficher dans le scratchpad."""
    mapping = {
        "web_search": "Recherche web",
        "search_memory": "Mémoire vectorielle",
        "read_local_file": "Lecture fichier",
        "list_directory": "Listing répertoire",
        "generate_code": "Génération code",
        "calculate": "Calcul",
    }
    return mapping.get(tool_name, tool_name)


def _truncate(text: str, max_len: int) -> str:
    """Tronque un texte proprement."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"
