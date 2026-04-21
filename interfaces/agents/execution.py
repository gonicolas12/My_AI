"""Mixin : exécution des tâches (agent unique, workflow classique, canvas DAG)."""

import os
import threading
import time
from datetime import datetime
from tkinter import messagebox


class ExecutionMixin:
    """Orchestration de l'exécution + contrôle du bouton Exécuter/Stop."""

    def execute_agent_task(self):
        """Exécute une tâche avec l'agent ou le workflow personnalisé"""
        if self.is_processing:
            messagebox.showwarning(
                "Agent Occupé", "Un agent est déjà en train de traiter une tâche."
            )
            return

        # Vérifier s'il y a des nœuds sur le canvas OU dans le workflow classique
        has_canvas_nodes = (
            self.workflow_canvas and len(self.workflow_canvas.nodes) > 0
        )
        if not self.custom_workflow and not has_canvas_nodes:
            messagebox.showwarning(
                "Aucun Agent",
                "Glissez-déposez un ou plusieurs agents pour commencer.",
            )
            return

        # Récupérer la tâche
        task = self._get_task_text()
        if not task or task.strip() == "":
            messagebox.showwarning(
                "Tâche Vide", "Veuillez décrire la tâche à effectuer."
            )
            return

        # Inclure le contenu des fichiers attachés dans le prompt
        attached = self._agent_get_pending_files()
        if attached:
            file_sections = []
            for fpath, ftype in attached:
                try:
                    if ftype == "Image":
                        # Pipeline vision : analyser l'image avec le modèle
                        # vision puis inclure la description textuelle
                        description = self._analyze_image_for_agent(fpath)
                        if description:
                            fname = os.path.basename(fpath)
                            file_sections.append(
                                f"--- Image jointe : {fname} ---\n"
                                f"Description de l'image :\n{description}"
                            )
                        else:
                            file_sections.append(
                                f"--- Image jointe : {os.path.basename(fpath)} ---\n"
                                f"[Aucun modèle vision disponible. "
                                f"Installez-en un : ollama pull minicpm-v]"
                            )
                    else:
                        content = self._read_attached_file(fpath, ftype)
                        if content:
                            fname = os.path.basename(fpath)
                            file_sections.append(
                                f"--- Fichier joint : {fname} ({ftype}) ---\n{content}"
                            )
                except Exception as exc:
                    file_sections.append(
                        f"--- Fichier joint : {os.path.basename(fpath)} ---\n"
                        f"[Erreur de lecture : {exc}]"
                    )
            if file_sections:
                task = task + "\n\n" + "\n\n".join(file_sections)
            self._agent_clear_previews()

        self.is_interrupted = False
        self._set_execute_button_stop()

        # Utiliser le plan d'exécution du canvas si des nœuds y sont présents
        if has_canvas_nodes:
            plan = self.workflow_canvas.get_execution_plan()
            self.is_processing = True
            if plan["mode"] in ("sequential", "dag"):
                self._update_status("⏳ Workflow visuel en cours...", "#f59e0b")
                threading.Thread(
                    target=self._execute_canvas_workflow_thread,
                    args=(task, plan),
                    daemon=True,
                ).start()
            elif plan["mode"] == "single":
                nid = plan["steps"][0]["nodes"][0]
                nd = plan["node_map"][nid]
                agent_type = nd["agent_type"]
                self._update_status("⏳ Traitement en cours...", "#f59e0b")
                threading.Thread(
                    target=self._execute_task_thread,
                    args=(agent_type, task, nd["name"], nd.get("color"), nid),
                    daemon=True,
                ).start()
            else:
                # parallel (tous isolés)
                self._update_status("⏳ Exécution parallèle...", "#f59e0b")
                threading.Thread(
                    target=self._execute_canvas_workflow_thread,
                    args=(task, plan),
                    daemon=True,
                ).start()
        elif len(self.custom_workflow) == 1:
            # Mode agent unique (workflow classique)
            agent_type, wf_name, wf_color = self.custom_workflow[0]
            self.is_processing = True
            self._update_status("⏳ Traitement en cours...", "#f59e0b")
            threading.Thread(
                target=self._execute_task_thread,
                args=(agent_type, task, wf_name, wf_color),
                daemon=True,
            ).start()
        else:
            # Mode workflow personnalisé multi-agents (classique)
            self.is_processing = True
            self._update_status("⏳ Workflow personnalisé en cours...", "#f59e0b")
            threading.Thread(
                target=self._execute_custom_workflow_thread,
                args=(task,),
                daemon=True,
            ).start()

    def _execute_task_thread(self, agent_type, task, explicit_name=None, explicit_color=None, canvas_node_id=None):
        """Exécute la tâche dans un thread séparé avec streaming"""
        try:
            # Préparer la zone de sortie
            self._clear_output_sections_sync()

            # Mettre à jour le statut du nœud canvas si applicable
            if canvas_node_id is not None:
                self._set_canvas_node_status(canvas_node_id, "running")

            # Trouver le nom et la couleur de l'agent
            agent_colors = {
                "code": "#3b82f6", "web": "#10b981", "analyst": "#8b5cf6",
                "creative": "#f59e0b", "debug": "#ef4444", "planner": "#06b6d4",
                "security": "#ec4899", "optimizer": "#14b8a6", "datascience": "#f97316",
            }
            agent_names = {
                "code": "CodeAgent", "web": "WebAgent", "analyst": "AnalystAgent",
                "creative": "CreativeAgent", "debug": "DebugAgent",
                "planner": "PlannerAgent", "security": "SecurityAgent",
                "optimizer": "OptimizerAgent", "datascience": "DataScienceAgent",
            }
            if explicit_color:
                color = explicit_color
            else:
                color = agent_colors.get(agent_type)
                if not color:
                    ca = self.custom_agents.get(agent_type, {})
                    color = ca.get("color", "#ff6b47")
            if explicit_name:
                name = explicit_name
            else:
                name = agent_names.get(agent_type)
                if not name:
                    ca = self.custom_agents.get(agent_type, {})
                    name = ca.get("name", agent_type.capitalize())

            section = self._create_step_section_sync(name, color)
            self._active_section = section

            # Exécuter avec streaming
            t_start = time.time()
            result = self.orchestrator.execute_single_task_stream(
                agent_type=agent_type,
                task=task,
                on_token=self._on_token_received
            )
            elapsed_ms = (time.time() - t_start) * 1000
            self.resource_monitor.update_inference(elapsed_ms, 0)

            if self.is_interrupted:
                self._finish_section(section, success=False)
                self._update_status("⛔ Génération interrompue", "#ef4444")
                if canvas_node_id is not None:
                    self._set_canvas_node_status(canvas_node_id, "error")
            elif result.get("success"):
                self._finish_section(section, success=True)
                self._update_status(
                    f"✅ Tâche terminée avec {result['agent']}", "#10b981"
                )
                if canvas_node_id is not None:
                    self._set_canvas_node_status(canvas_node_id, "done")
            else:
                self._finish_section(section, success=False)
                self._update_status("❌ Erreur lors de l'exécution", "#ef4444")
                if canvas_node_id is not None:
                    self._set_canvas_node_status(canvas_node_id, "error")

            self._active_section = None
            self._update_stats()

            self.execution_history.append(
                {
                    "agent": agent_type,
                    "task": task,
                    "result": result if not self.is_interrupted else {"success": False, "error": "interrupted"},
                    "timestamp": datetime.now().isoformat(),
                }
            )

        except Exception:
            self._finish_section(self._active_section, success=False)
            self._active_section = None
            self._update_status("❌ Erreur critique", "#ef4444")
            if canvas_node_id is not None:
                self._set_canvas_node_status(canvas_node_id, "error")
        finally:
            self.is_processing = False
            self.is_interrupted = False
            self._set_execute_button_normal()

    def _execute_custom_workflow_thread(self, task):
        """Exécute un workflow personnalisé multi-agents"""
        try:
            self._clear_output_sections_sync()

            workflow = []
            for idx, (agent_type, _name, _color) in enumerate(self.custom_workflow):
                workflow.append(
                    {
                        "agent": agent_type,
                        "task": (
                            task
                            if idx == 0
                            else f"Continue en te basant sur le résultat précédent pour: {task}"
                        ),
                        "pass_result": idx > 0,
                    }
                )

            step_sections = {}

            def on_step_start(step_idx, agent_type, _step_task):
                if self.is_interrupted:
                    return
                name = next(
                    (n for at, n, _ in self.custom_workflow if at == agent_type),
                    agent_type,
                )
                color = next(
                    (c for at, _n, c in self.custom_workflow if at == agent_type),
                    "#ff6b47",
                )
                sec = self._create_step_section_sync(
                    f"Étape {step_idx}/{len(workflow)}: {name}", color
                )
                step_sections[step_idx] = sec
                self._active_section = sec

            def on_step_complete(step_idx, result):
                if self.is_interrupted:
                    return
                sec = step_sections.get(step_idx)
                self._finish_section(sec, success=result.get("success", False))
                self._active_section = None

            result = self.orchestrator.execute_multi_agent_task_stream(
                task,
                workflow,
                on_step_start=on_step_start,
                on_token=self._on_token_received,
                on_step_complete=on_step_complete,
                on_should_stop=lambda: self.is_interrupted,
            )

            if self.is_interrupted:
                self._update_status("⛔ Génération interrompue", "#ef4444")
            else:
                summary = result["summary"]
                self._update_status(
                    f"✅ Workflow terminé ({summary['success_rate']:.0%} succès)",
                    "#10b981",
                )
            self._update_stats()

            self.execution_history.append(
                {
                    "agent": "workflow_custom",
                    "task": task,
                    "result": result if not self.is_interrupted else {"success": False, "error": "interrupted"},
                    "timestamp": datetime.now().isoformat(),
                }
            )

        except Exception as e:
            self._append_output(f"❌ Erreur workflow: {str(e)}\n\n")
            self._update_status("❌ Erreur workflow", "#ef4444")
        finally:
            self.is_processing = False
            self.is_interrupted = False
            self._set_execute_button_normal()

    def _execute_canvas_workflow_thread(self, task, plan):
        """Exécute un workflow basé sur le plan d'exécution du canvas (DAG)."""
        try:
            self._clear_output_sections_sync()

            node_map = plan["node_map"]
            steps = plan["steps"]
            isolated = plan["isolated"]
            total_steps = len(steps)
            results_by_node = {}
            success_count = 0
            total_count = 0

            for nid in node_map:
                self._set_canvas_node_status(nid, "idle")

            for step_idx, step in enumerate(steps):
                if self.is_interrupted:
                    break

                nids = step["nodes"]
                is_parallel = step["parallel"]

                if is_parallel:
                    # Label d'en-tête
                    par_names = ", ".join(node_map[n]["name"] for n in nids)
                    self._create_output_header_sync(
                        f"⚡ Étape {step_idx+1}/{total_steps} — parallèle: {par_names}"
                    )

                    # Créer les sections dépliantes (repliées pendant l'exécution)
                    par_sections = {}
                    for nid in nids:
                        nd = node_map[nid]
                        sec = self._create_step_section_sync(
                            nd["name"], nd.get("color", "#ff6b47"), expanded=True
                        )
                        par_sections[nid] = sec

                    # Exécuter en parallèle — chaque agent stream en temps réel
                    threads = []
                    local_results = {}
                    par_lock = threading.Lock()

                    def _make_runner(shared_results, shared_lock, sections_map):
                        def run_agent(nid):
                            if self.is_interrupted:
                                return
                            nd = node_map[nid]
                            self._set_canvas_node_status(nid, "running")
                            agent_task = task
                            parents = [
                                c["from"]
                                for c in (self.workflow_canvas.connections if self.workflow_canvas else [])
                                if c["to"] == nid
                            ]
                            if parents:
                                context_parts = [
                                    f"[{node_map[pid]['name']}]:\n{results_by_node[pid]}"
                                    for pid in parents
                                    if pid in results_by_node
                                ]
                                if context_parts:
                                    _sep = "\n---\n"
                                    agent_task = (
                                        f"Contexte précédent:\n{_sep.join(context_parts)}\n\n"
                                        f"Tâche: {task}"
                                    )

                            sec = sections_map[nid]  # pylint: disable=cell-var-from-loop

                            def stream_token(token, _sec=sec):
                                self._append_to_section(_sec, token)
                                return not self.is_interrupted

                            t_start = time.time()
                            result = self.orchestrator.execute_single_task_stream(
                                agent_type=nd["agent_type"],
                                task=agent_task,
                                on_token=stream_token,
                            )
                            elapsed = (time.time() - t_start) * 1000
                            self.resource_monitor.update_inference(elapsed, 0)

                            with shared_lock:
                                shared_results[nid] = result
                            if result.get("success"):
                                self._set_canvas_node_status(nid, "done")
                                with shared_lock:
                                    shared_results[nid] = result.get("result", "")
                            else:
                                self._set_canvas_node_status(nid, "error")
                        return run_agent

                    agent_runner = _make_runner(local_results, par_lock, par_sections)
                    for nid in nids:
                        t = threading.Thread(target=agent_runner, args=(nid,), daemon=True)
                        threads.append(t)
                        t.start()
                    for t in threads:
                        t.join()

                    # Finaliser les sections
                    for nid in nids:
                        sec = par_sections.get(nid)
                        if sec is None:
                            continue
                        ok = isinstance(local_results.get(nid), str) or (
                            isinstance(local_results.get(nid), dict) and local_results[nid].get("success")
                        )
                        self._finish_section(sec, success=ok)

                    # Collecter les résultats
                    for nid, res in local_results.items():
                        total_count += 1
                        if isinstance(res, str):
                            results_by_node[nid] = res
                            success_count += 1
                        elif isinstance(res, dict) and res.get("success"):
                            results_by_node[nid] = res.get("result", "")
                            success_count += 1
                else:
                    # Séquentiel
                    nid = nids[0]
                    nd = node_map[nid]

                    sec = self._create_step_section_sync(
                        f"Étape {step_idx+1}/{total_steps}: {nd['name']}",
                        nd.get("color", "#ff6b47"),
                    )
                    self._active_section = sec
                    self._set_canvas_node_status(nid, "running")

                    agent_task = task
                    if self.workflow_canvas:
                        parents = [c["from"] for c in self.workflow_canvas.connections
                                   if c["to"] == nid]
                        if parents:
                            context_parts = [
                                f"[{node_map[p]['name']}]:\n{results_by_node[p]}"
                                for p in parents
                                if p in results_by_node
                            ]
                            if context_parts:
                                _sep = "\n---\n"
                                agent_task = (
                                    f"Contexte précédent:\n{_sep.join(context_parts)}\n\n"
                                    f"Tâche: {task}"
                                )

                    t_start = time.time()
                    result = self.orchestrator.execute_single_task_stream(
                        agent_type=nd["agent_type"],
                        task=agent_task,
                        on_token=self._on_token_received,
                    )
                    elapsed = (time.time() - t_start) * 1000
                    self.resource_monitor.update_inference(elapsed, 0)

                    total_count += 1
                    if result.get("success"):
                        results_by_node[nid] = result.get("result", "")
                        success_count += 1
                        self._set_canvas_node_status(nid, "done")
                        self._finish_section(sec, success=True)
                    else:
                        self._set_canvas_node_status(nid, "error")
                        self._finish_section(sec, success=False)
                    self._active_section = None

            # Exécuter les nœuds isolés
            for nid in isolated:
                if self.is_interrupted:
                    break
                if nid not in node_map:
                    continue
                nd = node_map[nid]
                sec = self._create_step_section_sync(
                    f"Agent isolé: {nd['name']}", nd.get("color", "#ff6b47")
                )
                self._active_section = sec
                self._set_canvas_node_status(nid, "running")
                t_start = time.time()
                result = self.orchestrator.execute_single_task_stream(
                    agent_type=nd["agent_type"],
                    task=task,
                    on_token=self._on_token_received,
                )
                elapsed = (time.time() - t_start) * 1000
                self.resource_monitor.update_inference(elapsed, 0)
                total_count += 1
                ok = result.get("success", False)
                if ok:
                    success_count += 1
                    self._set_canvas_node_status(nid, "done")
                else:
                    self._set_canvas_node_status(nid, "error")
                self._finish_section(sec, success=ok)
                self._active_section = None

            # Résumé
            if self.is_interrupted:
                self._update_status("⛔ Génération interrompue", "#ef4444")
            else:
                rate = success_count / max(total_count, 1)
                self._update_status(
                    f"✅ Workflow visuel terminé ({rate:.0%} succès)", "#10b981"
                )

            self._update_stats()
            self.execution_history.append({
                "agent": "workflow_canvas",
                "task": task,
                "result": {"success": success_count == total_count,
                           "total": total_count, "successful": success_count},
                "timestamp": datetime.now().isoformat(),
            })

        except Exception as e:
            self._update_status(f"❌ Erreur workflow: {str(e)}", "#ef4444")
        finally:
            self._active_section = None
            self.is_processing = False
            self.is_interrupted = False
            self._set_execute_button_normal()

    def _set_canvas_node_status(self, nid: int, status: str):
        """Met à jour le statut visuel d'un nœud du canvas."""
        if self.workflow_canvas:
            def _update():
                self.workflow_canvas.set_node_status(nid, status)
            if self.parent.winfo_exists():
                self.parent.after(0, _update)

    # === Bouton Exécuter / Stop =======================================

    def interrupt_agents(self):
        """Interrompt la génération en cours"""
        if self.is_processing:
            self.is_interrupted = True
            self._update_status("⛔ Interruption en cours...", "#ef4444")

    def _set_execute_button_stop(self):
        """Transforme le bouton Exécuter en bouton STOP (carré noir sur fond blanc)"""
        def update():
            if self.execute_btn and self.execute_btn.winfo_exists():
                if self.use_ctk:
                    self.execute_btn.configure(
                        text="  ■  ",
                        command=self.interrupt_agents,
                        state="normal",
                        fg_color="#ffffff",
                        hover_color="#f3f3f3",
                        text_color="#111111",
                        border_color="#111111",
                        border_width=2,
                        font=("Segoe UI", 16, "bold"),
                    )
                else:
                    self.execute_btn.configure(
                        text="  ■  ",
                        command=self.interrupt_agents,
                        bg="#ffffff",
                        fg="#111111",
                        activebackground="#f3f3f3",
                        font=("Segoe UI", 16, "bold"),
                    )
        if self.parent.winfo_exists():
            self.parent.after(0, update)

    def _set_execute_button_normal(self):
        """Restaure le bouton Exécuter en mode normal (identique à la création)"""
        def update():
            if self.execute_btn and self.execute_btn.winfo_exists():
                if self.use_ctk:
                    self.execute_btn.configure(
                        text="▶ Exécuter",
                        command=self.execute_agent_task,
                        state="normal",
                        fg_color=self.colors["accent"],
                        hover_color="#ff5730",
                        text_color="#ffffff",
                        font=("Segoe UI", 13, "bold"),
                        corner_radius=8,
                        border_width=0,
                        border_color=self.colors["accent"],
                    )
                else:
                    self.execute_btn.configure(
                        text="▶ Exécuter",
                        command=self.execute_agent_task,
                        bg=self.colors["accent"],
                        fg="#ffffff",
                        font=("Segoe UI", 12, "bold"),
                        border=0,
                        relief="flat",
                    )
        if self.parent.winfo_exists():
            self.parent.after(0, update)

    def _make_output_readonly(self):
        """No-op: les sections gèrent leur propre état."""

    def _update_status(self, text, color):
        """Met à jour le label de statut"""

        def update():
            if self.status_label and self.status_label.winfo_exists():
                self.status_label.configure(text=text, text_color=color)

        if self.parent.winfo_exists():
            self.parent.after(0, update)
