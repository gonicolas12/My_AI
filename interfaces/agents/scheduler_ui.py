"""Mixin : UI de gestion des tâches planifiées (page Agents).

Permet de créer / éditer / supprimer / activer des exécutions récurrentes
d'agents, de workflows (canvas) ou de débats. Délègue toute la logique au
``SchedulerService`` (core/scheduler.py) — cette UI n'est qu'une façade CRUD.
"""

import os
from datetime import datetime

from interfaces.agents._common import ctk, tk

from core.scheduler import SchedulerService, _CRONITER_AVAILABLE

_DAY_LABELS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


class SchedulerMixin:
    """Section « 📅 Tâches planifiées » + dialogues de création/édition."""

    # ------------------------------------------------------------------
    # Accès au service + métadonnées d'agents
    # ------------------------------------------------------------------

    def _get_scheduler(self):
        """Retourne le SchedulerService singleton (créé à la demande)."""
        svc = getattr(self, "_scheduler_service", None)
        if svc is None:
            from core.scheduler import get_scheduler
            svc = get_scheduler()
            self._scheduler_service = svc
        return svc

    def _scheduler_agent_meta(self, key):
        """Métadonnées (agent_type/name/color/icon) d'un agent built-in ou custom."""
        info = getattr(self, "_builtin_agents_info", {}).get(key)
        if info:
            return {"agent_type": key, "name": info.get("name", key),
                    "color": info.get("color", "#3b82f6"), "icon": info.get("icon", "🤖")}
        data = self.custom_agents.get(key, {})
        return {"agent_type": key, "name": data.get("name", key),
                "color": data.get("color", "#ff6b47"), "icon": "🧩"}

    def _canvas_nodes_connections(self):
        """Convertit le workflow du canvas au format attendu par run_workflow."""
        canvas = getattr(self, "workflow_canvas", None)
        if not canvas:
            return [], []
        data = canvas.to_dict()
        nodes = [
            {"id": str(nid), "agent_type": nd["agent_type"], "name": nd["name"],
             "color": nd.get("color", "#3b82f6"), "icon": nd.get("icon", "🤖")}
            for nid, nd in data.get("nodes", {}).items()
        ]
        conns = [
            {"from": str(c["from"]), "to": str(c["to"])}
            for c in data.get("connections", [])
        ]
        return nodes, conns

    @staticmethod
    def _fmt_dt(iso):
        """Date ISO → 'JJ/MM HH:MM' (ou '—')."""
        try:
            return datetime.fromisoformat(iso).strftime("%d/%m %H:%M")
        except (ValueError, TypeError):
            return "—"

    # ------------------------------------------------------------------
    # Section principale
    # ------------------------------------------------------------------

    def create_scheduler_section(self, parent):
        """Crée la section de gestion des tâches planifiées (grid row 6)."""
        section = self.create_frame(parent, fg_color=self.colors["bg_secondary"])
        section.grid(row=6, column=0, sticky="ew", padx=30, pady=(0, 30))
        if self.use_ctk:
            section.configure(corner_radius=12)

        content = self.create_frame(section, fg_color=self.colors["bg_secondary"])
        content.pack(fill="x", padx=20, pady=15)

        header = self.create_frame(content, fg_color=self.colors["bg_secondary"])
        header.pack(fill="x")
        self.create_label(
            header, text="📅 Tâches planifiées",
            font=("Segoe UI", 16, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_secondary"],
        ).pack(side="left")

        if self.use_ctk:
            ctk.CTkButton(
                header, text="➕ Nouvelle tâche", width=160,
                fg_color="#3b82f6", hover_color="#2563eb", text_color="#ffffff",
                font=("Segoe UI", 11, "bold"), corner_radius=8,
                command=self._open_scheduler_dialog,
            ).pack(side="right")
        else:
            tk.Button(
                header, text="➕ Nouvelle tâche", command=self._open_scheduler_dialog,
                bg="#3b82f6", fg="#ffffff", font=("Segoe UI", 11, "bold"), relief="flat",
            ).pack(side="right")

        self.create_label(
            content,
            text="Exécutez automatiquement un agent, un workflow ou un débat "
                 "de façon récurrente (ex. veille quotidienne, audit hebdomadaire).",
            font=("Segoe UI", 11), text_color=self.colors["text_secondary"],
            fg_color=self.colors["bg_secondary"], wraplength=860, justify="left",
        ).pack(anchor="w", pady=(2, 10))

        # Exécution en arrière-plan (Windows uniquement)
        self._build_background_control(content)

        self._scheduler_list_frame = self.create_frame(
            content, fg_color=self.colors["bg_secondary"]
        )
        self._scheduler_list_frame.pack(fill="x")
        self._refresh_scheduler_list()

    def _refresh_scheduler_list(self):
        """Reconstruit la liste des tâches."""
        frame = getattr(self, "_scheduler_list_frame", None)
        if frame is None:
            return
        for child in frame.winfo_children():
            child.destroy()
        try:
            tasks = self._get_scheduler().list_tasks()
        except Exception as exc:
            print(f"⚠️ Lecture des tâches planifiées échouée: {exc}")
            tasks = []
        if not tasks:
            self.create_label(
                frame, text="Aucune tâche planifiée. Cliquez sur « ➕ Nouvelle tâche ».",
                font=("Segoe UI", 11), text_color=self.colors["text_secondary"],
                fg_color=self.colors["bg_secondary"],
            ).pack(anchor="w", pady=8)
            return
        for task in tasks:
            self._render_scheduler_task_row(frame, task)

    def _render_scheduler_task_row(self, parent, task):
        """Affiche une ligne (carte) de tâche avec ses actions."""
        enabled = task.get("enabled", True)
        status = task.get("last_status")
        status_color = {
            "success": "#10b981", "partial": "#f59e0b", "interrupted": "#f59e0b",
            "deferred": "#06b6d4", "error": "#ef4444",
        }.get(status, self.colors["text_secondary"])

        row = self.create_frame(parent, fg_color=self.colors["bg_primary"])
        row.pack(fill="x", pady=4)
        if self.use_ctk:
            row.configure(corner_radius=8)
        inner = self.create_frame(row, fg_color=self.colors["bg_primary"])
        inner.pack(fill="x", padx=12, pady=8)

        # --- Infos (gauche) ---
        left = self.create_frame(inner, fg_color=self.colors["bg_primary"])
        left.pack(side="left", fill="x", expand=True)

        name_color = self.colors["text_primary"] if enabled else self.colors["text_secondary"]
        self.create_label(
            left, text=("📅 " if enabled else "⏸ ") + task.get("name", "(sans nom)"),
            font=("Segoe UI", 13, "bold"), text_color=name_color,
            fg_color=self.colors["bg_primary"], anchor="w",
        ).pack(anchor="w")

        meta = SchedulerService.describe_schedule(task.get("schedule") or {})
        meta += f"   •   prochaine : {self._fmt_dt(task.get('next_run'))}"
        if task.get("last_run"):
            meta += f"   •   dernier : {self._fmt_dt(task.get('last_run'))}"
            if status:
                meta += f" ({status})"
        self.create_label(
            left, text=meta, font=("Segoe UI", 10),
            text_color=status_color if status else self.colors["text_secondary"],
            fg_color=self.colors["bg_primary"], anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        # --- Actions (droite) ---
        right = self.create_frame(inner, fg_color=self.colors["bg_primary"])
        right.pack(side="right")
        task_id = task.get("id")

        switch_var = tk.BooleanVar(value=enabled)
        if self.use_ctk:
            ctk.CTkSwitch(
                right, text="", width=40, variable=switch_var,
                progress_color="#10b981",
                command=lambda i=task_id, v=switch_var: self._toggle_scheduled(i, v.get()),
            ).pack(side="left", padx=(0, 8))
        else:
            tk.Checkbutton(
                right, variable=switch_var, bg=self.colors["bg_primary"],
                command=lambda i=task_id, v=switch_var: self._toggle_scheduled(i, v.get()),
            ).pack(side="left", padx=(0, 8))

        for label, color, cmd in (
            ("▶", "#10b981", lambda i=task_id: self._run_scheduled_now(i)),
            ("📝", self.colors["text_primary"], lambda t=task: self._open_scheduler_dialog(t)),
            ("✕", "#ef4444", lambda i=task_id, n=task.get("name", ""): self._delete_scheduled(i, n)),
        ):
            if self.use_ctk:
                ctk.CTkButton(
                    right, text=label, width=32, height=30, fg_color="transparent",
                    hover_color=self.colors["bg_secondary"], text_color=color,
                    font=("Segoe UI", 14, "bold"), corner_radius=6, command=cmd,
                ).pack(side="left", padx=2)
            else:
                tk.Button(
                    right, text=label, command=cmd, bg=self.colors["bg_primary"],
                    fg=color, font=("Segoe UI", 12), border=0, relief="flat",
                ).pack(side="left", padx=2)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _toggle_scheduled(self, task_id, enabled):
        try:
            self._get_scheduler().set_enabled(task_id, bool(enabled))
            self._refresh_scheduler_list()
        except Exception as exc:
            self._show_notification(f"❌ {exc}", "#ef4444")

    def _run_scheduled_now(self, task_id):
        try:
            res = self._get_scheduler().run_now(task_id)
        except Exception as exc:
            res = {"success": False, "error": str(exc)}
        if res.get("success"):
            self._show_notification("▶ Exécution lancée…", "#10b981")
        else:
            self._show_notification(f"❌ {res.get('error', 'Échec')}", "#ef4444")

    def _delete_scheduled(self, task_id, name):
        from tkinter import messagebox
        if not messagebox.askyesno(
            "Supprimer la tâche", f"Supprimer la tâche planifiée « {name} » ?"
        ):
            return
        try:
            self._get_scheduler().delete_task(task_id)
            self._refresh_scheduler_list()
            self._show_notification("✕ Tâche supprimée", "#ef4444")
        except Exception as exc:
            self._show_notification(f"❌ {exc}", "#ef4444")

    def notify_scheduled_result(self, result):
        """Appelé (thread Tk) par le GUI à la fin d'une tâche planifiée."""
        status = result.get("status")
        color = {"success": "#10b981", "error": "#ef4444"}.get(status, "#f59e0b")
        msg = f"📅 {result.get('name', 'Tâche')} — {result.get('status_text') or status}"
        try:
            self._show_notification(msg[:90], color, duration=4500)
        except Exception:
            pass
        try:
            self._refresh_scheduler_list()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Exécution en arrière-plan (Planificateur de tâches Windows)
    # ------------------------------------------------------------------

    def _build_background_control(self, parent):
        """Switch « Exécuter même l'appli fermée » (Windows uniquement)."""
        if os.name != "nt":
            return
        from core import scheduler_runner
        try:
            registered = scheduler_runner.is_windows_task_registered()
        except Exception:
            registered = False
        self._bg_task_var = tk.BooleanVar(value=registered)
        label = "🖥️ Exécuter même l'appli fermée (session Windows ouverte)"
        if self.use_ctk:
            ctk.CTkSwitch(
                parent, text=label, variable=self._bg_task_var,
                progress_color="#10b981", font=("Segoe UI", 11),
                text_color=self.colors["text_primary"],
                command=self._toggle_background_task,
            ).pack(anchor="w", pady=(0, 10))
        else:
            tk.Checkbutton(
                parent, text=label, variable=self._bg_task_var,
                command=self._toggle_background_task,
                bg=self.colors["bg_secondary"], fg=self.colors["text_primary"],
                selectcolor=self.colors["bg_secondary"], font=("Segoe UI", 11),
            ).pack(anchor="w", pady=(0, 10))

    def _toggle_background_task(self):
        """Enregistre/supprime la tâche Planificateur Windows."""
        from core import scheduler_runner
        want = bool(self._bg_task_var.get())
        if want:
            interval = 5
            try:
                from core.config import get_config
                interval = int(get_config().get("scheduler.background_interval_minutes", 5))
            except Exception:
                pass
            ok, msg = scheduler_runner.register_windows_task(interval)
        else:
            ok, msg = scheduler_runner.unregister_windows_task()
        self._show_notification(("✅ " if ok else "❌ ") + msg,
                                "#10b981" if ok else "#ef4444")
        if not ok:
            self._bg_task_var.set(not want)   # revert le switch si échec

    # ------------------------------------------------------------------
    # Dialogue créer / éditer
    # ------------------------------------------------------------------

    def _open_scheduler_dialog(self, task=None):
        """Ouvre le dialogue de création (task=None) ou d'édition d'une tâche.

        À l'édition, la source (agent/workflow/débat) n'est pas modifiable —
        seuls le nom, la tâche, le planning et l'option « rattraper » le sont.
        Pour changer de source, supprimer et recréer la tâche.
        """
        editing = task is not None
        choices = self._get_all_agent_choices()
        display_to_key = {disp: key for key, disp, _ in choices}
        display_values = list(display_to_key.keys()) or ["(aucun agent)"]

        dialog = tk.Toplevel()
        dialog.title("Modifier la tâche" if editing else "Nouvelle tâche planifiée")
        dialog.geometry("560x700")
        dialog.configure(bg=self.colors["bg_primary"])
        dialog.transient(self.parent.winfo_toplevel())
        dialog.grab_set()
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 280
        y = (dialog.winfo_screenheight() // 2) - 350
        dialog.geometry(f"560x700+{x}+{y}")

        self.create_label(
            dialog, text=("📝 Modifier la tâche" if editing else "📅 Nouvelle tâche planifiée"),
            font=("Segoe UI", 16, "bold"), text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        ).pack(padx=20, pady=(18, 12))

        # --- Nom ---
        self._sched_field_label(dialog, "Nom")
        name_entry = self._sched_entry(dialog, default=task.get("name", "") if editing else "",
                                       width=480, placeholder="Ex: Veille IA matinale")
        name_entry.pack(fill="x", padx=30, pady=(2, 10))

        # --- Source (création seulement) ---
        source_var = tk.StringVar(value=task.get("kind", "single") if editing else "single")
        src_widgets = {}
        if editing:
            self._sched_field_label(dialog, "Source")
            self.create_label(
                dialog, text=self._describe_source(task), font=("Segoe UI", 11),
                text_color=self.colors["text_secondary"], fg_color=self.colors["bg_primary"],
            ).pack(anchor="w", padx=30, pady=(2, 10))
        else:
            self._sched_field_label(dialog, "Source")
            src_row = self.create_frame(dialog, fg_color=self.colors["bg_primary"])
            src_row.pack(fill="x", padx=30, pady=(2, 4))
            src_params = self.create_frame(dialog, fg_color=self.colors["bg_primary"])
            src_params.pack(fill="x", padx=30, pady=(0, 10))

            def render_source(*_):
                for ch in src_params.winfo_children():
                    ch.destroy()
                src_widgets.clear()
                stype = source_var.get()
                if stype == "single":
                    var = tk.StringVar(value=display_values[0])
                    self._sched_option(src_params, display_values, var, width=480).pack(fill="x")
                    src_widgets["agent"] = var
                elif stype == "debate":
                    va = tk.StringVar(value=display_values[0])
                    vb = tk.StringVar(value=display_values[1] if len(display_values) > 1 else display_values[0])
                    self._sched_option(src_params, display_values, va, width=480).pack(fill="x", pady=(0, 6))
                    self._sched_option(src_params, display_values, vb, width=480).pack(fill="x", pady=(0, 6))
                    rrow = self.create_frame(src_params, fg_color=self.colors["bg_primary"])
                    rrow.pack(fill="x")
                    self.create_label(
                        rrow, text="Tours :", font=("Segoe UI", 11),
                        text_color=self.colors["text_primary"], fg_color=self.colors["bg_primary"],
                    ).pack(side="left")
                    rv = tk.IntVar(value=3)
                    tk.Spinbox(rrow, from_=1, to=10, width=5, textvariable=rv,
                               font=("Segoe UI", 11), bg=self.colors["input_bg"],
                               fg=self.colors["text_primary"], relief="flat").pack(side="left", padx=(8, 0))
                    src_widgets.update({"a": va, "b": vb, "rounds": rv})
                else:  # workflow
                    nodes, _ = self._canvas_nodes_connections()
                    self.create_label(
                        src_params,
                        text=(f"Utilise le workflow du canvas ({len(nodes)} nœud(s))."
                              if nodes else "⚠️ Le canvas est vide — déposez des agents d'abord."),
                        font=("Segoe UI", 11), text_color=self.colors["text_secondary"],
                        fg_color=self.colors["bg_primary"], wraplength=480, justify="left",
                    ).pack(anchor="w")

            for val, lbl in (("single", "Agent seul"), ("workflow", "Workflow (canvas)"),
                             ("debate", "Débat")):
                self._sched_radio(src_row, lbl, source_var, val, render_source).pack(side="left", padx=(0, 12))
            render_source()

        # --- Tâche / sujet ---
        self._sched_field_label(dialog, "Tâche / Sujet (débat)")
        if self.use_ctk:
            task_box = ctk.CTkTextbox(
                dialog, height=90, font=("Segoe UI", 12), fg_color=self.colors["input_bg"],
                text_color=self.colors["text_primary"], border_width=1,
                border_color=self.colors["border"], corner_radius=6,
            )
        else:
            task_box = tk.Text(dialog, height=4, font=("Segoe UI", 12),
                               bg=self.colors["input_bg"], fg=self.colors["text_primary"])
        if editing:
            task_box.insert("0.0" if self.use_ctk else "1.0", task.get("task", ""))
        task_box.pack(fill="x", padx=30, pady=(2, 10))

        # --- Planning ---
        self._sched_field_label(dialog, "Planning")
        sched = task.get("schedule") if editing else None
        type_var = tk.StringVar(value=(sched or {}).get("type", "daily"))
        type_row = self.create_frame(dialog, fg_color=self.colors["bg_primary"])
        type_row.pack(fill="x", padx=30, pady=(2, 4))
        params_frame = self.create_frame(dialog, fg_color=self.colors["bg_primary"])
        params_frame.pack(fill="x", padx=30, pady=(0, 8))
        sw = {}

        def render_params(*_):
            for ch in params_frame.winfo_children():
                ch.destroy()
            sw.clear()
            stype = type_var.get()
            pre = sched if (sched and sched.get("type") == stype) else {}
            if stype in ("daily", "weekly"):
                trow = self.create_frame(params_frame, fg_color=self.colors["bg_primary"])
                trow.pack(fill="x")
                self.create_label(trow, text="Heure (HH:MM) :", font=("Segoe UI", 11),
                                  text_color=self.colors["text_primary"],
                                  fg_color=self.colors["bg_primary"]).pack(side="left")
                te = self._sched_entry(trow, default=pre.get("at", "08:00"), width=80)
                te.pack(side="left", padx=(8, 0))
                sw["time"] = te
                if stype == "weekly":
                    drow = self.create_frame(params_frame, fg_color=self.colors["bg_primary"])
                    drow.pack(fill="x", pady=(8, 0))
                    predays = set(pre.get("days", []))
                    day_vars = {}
                    for i, lbl in enumerate(_DAY_LABELS):
                        v = tk.BooleanVar(value=(i in predays))
                        self._sched_check(drow, lbl, v).pack(side="left", padx=(0, 6))
                        day_vars[i] = v
                    sw["days"] = day_vars
            elif stype == "interval":
                irow = self.create_frame(params_frame, fg_color=self.colors["bg_primary"])
                irow.pack(fill="x")
                self.create_label(irow, text="Toutes les", font=("Segoe UI", 11),
                                  text_color=self.colors["text_primary"],
                                  fg_color=self.colors["bg_primary"]).pack(side="left")
                pre_secs = int(pre.get("seconds", 3600))
                pre_unit = "heures" if pre_secs % 3600 == 0 else "minutes"
                pre_n = pre_secs // 3600 if pre_unit == "heures" else max(1, pre_secs // 60)
                ne = self._sched_entry(irow, default=str(pre_n), width=70)
                ne.pack(side="left", padx=8)
                uvar = tk.StringVar(value=pre_unit)
                self._sched_option(irow, ["minutes", "heures"], uvar, width=120).pack(side="left")
                sw.update({"num": ne, "unit": uvar})
            elif stype == "cron":
                if not _CRONITER_AVAILABLE:
                    self.create_label(
                        params_frame,
                        text="⚠️ croniter requis (pip install croniter) pour les expressions cron.",
                        font=("Segoe UI", 10), text_color="#f59e0b",
                        fg_color=self.colors["bg_primary"], wraplength=480, justify="left",
                    ).pack(anchor="w")
                ce = self._sched_entry(params_frame, default=pre.get("expr", "0 8 * * *"),
                                       width=480, placeholder="min heure jour mois jour_semaine")
                ce.pack(fill="x")
                sw["cron"] = ce

        for val, lbl in (("daily", "Quotidien"), ("weekly", "Hebdo"),
                         ("interval", "Intervalle"), ("cron", "Cron")):
            self._sched_radio(type_row, lbl, type_var, val, render_params).pack(side="left", padx=(0, 12))
        render_params()

        # --- run_if_missed ---
        missed_var = tk.BooleanVar(value=task.get("run_if_missed", True) if editing else True)
        self._sched_check(
            dialog, "Rattraper au prochain démarrage si manquée", missed_var,
        ).pack(anchor="w", padx=30, pady=(6, 4))

        err_label = self.create_label(
            dialog, text="", font=("Segoe UI", 10), text_color="#ef4444",
            fg_color=self.colors["bg_primary"], wraplength=500, justify="left",
        )
        err_label.pack(anchor="w", padx=30)

        # --- Boutons ---
        btns = self.create_frame(dialog, fg_color=self.colors["bg_primary"])
        btns.pack(fill="x", padx=30, pady=(8, 18))

        def on_save():
            self._save_scheduled_task(
                dialog, err_label, editing, task,
                name_entry, task_box, source_var, src_widgets,
                type_var, sw, missed_var, display_to_key,
            )

        if self.use_ctk:
            ctk.CTkButton(btns, text="Annuler", width=120,
                          fg_color=self.colors["bg_secondary"], hover_color=self.colors["border"],
                          text_color=self.colors["text_primary"], font=("Segoe UI", 11, "bold"),
                          corner_radius=8, command=dialog.destroy).pack(side="left")
            ctk.CTkButton(btns, text="💾 Enregistrer", width=160,
                          fg_color="#3b82f6", hover_color="#2563eb", text_color="#ffffff",
                          font=("Segoe UI", 11, "bold"), corner_radius=8,
                          command=on_save).pack(side="right")
        else:
            tk.Button(btns, text="Annuler", command=dialog.destroy,
                      bg=self.colors["bg_secondary"], fg=self.colors["text_primary"],
                      font=("Segoe UI", 11, "bold"), relief="flat").pack(side="left")
            tk.Button(btns, text="💾 Enregistrer", command=on_save,
                      bg="#3b82f6", fg="#ffffff", font=("Segoe UI", 11, "bold"),
                      relief="flat").pack(side="right")

    def _save_scheduled_task(self, dialog, err_label, editing, task, name_entry,
                             task_box, source_var, src_widgets, type_var, sw,
                             missed_var, display_to_key):
        """Valide les champs et crée/met à jour la tâche via le service."""
        def fail(msg):
            try:
                err_label.configure(text=f"❌ {msg}")
            except Exception:
                pass

        name = name_entry.get().strip()
        if not name:
            return fail("Nom requis.")
        try:
            task_text = task_box.get("0.0" if self.use_ctk else "1.0", "end").strip()
        except Exception:
            task_text = ""
        if not task_text:
            return fail("Tâche / sujet requis.")

        # Planning
        try:
            schedule = self._build_schedule(type_var.get(), sw)
        except ValueError as exc:
            return fail(str(exc))

        run_if_missed = bool(missed_var.get())

        try:
            if editing:
                self._get_scheduler().update_task(
                    task["id"], name=name, task=task_text, schedule=schedule,
                    run_if_missed=run_if_missed,
                )
            else:
                kind, nodes, conns, debate = self._resolve_source(
                    source_var.get(), src_widgets, display_to_key
                )
                self._get_scheduler().create_task(
                    name=name, kind=kind, task=task_text, schedule=schedule,
                    nodes=nodes, connections=conns, debate=debate,
                    run_if_missed=run_if_missed,
                )
        except ValueError as exc:
            return fail(str(exc))
        except Exception as exc:
            return fail(f"Erreur : {exc}")

        dialog.destroy()
        self._refresh_scheduler_list()
        self._show_notification("✅ Tâche planifiée enregistrée", "#10b981")

    def _resolve_source(self, source, src_widgets, display_to_key):
        """Construit (kind, nodes, connections, debate) depuis la source choisie."""
        if source == "debate":
            ka = display_to_key.get(src_widgets["a"].get())
            kb = display_to_key.get(src_widgets["b"].get())
            if not ka or not kb:
                raise ValueError("Choisissez deux agents.")
            if ka == kb:
                raise ValueError("Choisissez deux agents différents.")
            rounds = int(src_widgets["rounds"].get() or 3)
            return "debate", [], [], {"agent_a": ka, "agent_b": kb, "rounds": rounds}
        if source == "workflow":
            nodes, conns = self._canvas_nodes_connections()
            if not nodes:
                raise ValueError("Le canvas est vide.")
            return "workflow", nodes, conns, None
        # single
        key = display_to_key.get(src_widgets["agent"].get())
        if not key:
            raise ValueError("Choisissez un agent.")
        return "workflow", [{"id": "n1", **self._scheduler_agent_meta(key)}], [], None

    @staticmethod
    def _build_schedule(stype, sw):
        """Construit le dict de planning depuis les widgets (peut lever ValueError)."""
        if stype == "daily":
            return {"type": "daily", "at": (sw["time"].get().strip() or "08:00")}
        if stype == "weekly":
            days = [i for i, v in sw.get("days", {}).items() if v.get()]
            if not days:
                raise ValueError("Sélectionnez au moins un jour.")
            return {"type": "weekly", "days": days, "at": (sw["time"].get().strip() or "08:00")}
        if stype == "interval":
            try:
                n = int(sw["num"].get().strip())
            except (ValueError, AttributeError):
                raise ValueError("Intervalle invalide.")
            if n < 1:
                raise ValueError("Intervalle invalide.")
            secs = n * 3600 if sw["unit"].get() == "heures" else n * 60
            return {"type": "interval", "seconds": max(60, secs)}
        if stype == "cron":
            expr = sw["cron"].get().strip()
            if not expr:
                raise ValueError("Expression cron requise.")
            return {"type": "cron", "expr": expr}
        raise ValueError("Type de planning inconnu.")

    def _describe_source(self, task):
        kind = task.get("kind")
        if kind == "debate":
            d = task.get("debate") or {}
            a = self._scheduler_agent_meta(d.get("agent_a")).get("name")
            b = self._scheduler_agent_meta(d.get("agent_b")).get("name")
            return f"Débat : {a} vs {b}"
        nodes = task.get("nodes") or []
        if len(nodes) == 1:
            return f"Agent : {nodes[0].get('name', nodes[0].get('agent_type'))}"
        return f"Workflow : {len(nodes)} agents"

    # ------------------------------------------------------------------
    # Petits constructeurs de widgets (ctk / tk)
    # ------------------------------------------------------------------

    def _sched_field_label(self, parent, text):
        self.create_label(
            parent, text=text, font=("Segoe UI", 11, "bold"),
            text_color=self.colors["text_primary"], fg_color=self.colors["bg_primary"],
        ).pack(anchor="w", padx=30)

    def _sched_entry(self, parent, default="", width=120, placeholder=""):
        if self.use_ctk:
            e = ctk.CTkEntry(
                parent, font=("Segoe UI", 11), height=32, width=width,
                fg_color=self.colors["input_bg"], text_color=self.colors["text_primary"],
                border_color=self.colors["border"], corner_radius=6,
                placeholder_text=placeholder,
            )
        else:
            e = tk.Entry(parent, font=("Segoe UI", 11), width=max(8, width // 8),
                         bg=self.colors["input_bg"], fg=self.colors["text_primary"])
        if default:
            e.insert(0, default)
        return e

    def _sched_option(self, parent, values, var, width=160):
        if self.use_ctk:
            return ctk.CTkOptionMenu(
                parent, values=values, variable=var, width=width, height=32,
                font=("Segoe UI", 11), fg_color=self.colors["input_bg"],
                button_color=self.colors["accent"], button_hover_color="#ff5730",
                text_color=self.colors["text_primary"],
                dropdown_fg_color=self.colors["bg_secondary"],
                dropdown_text_color=self.colors["text_primary"], corner_radius=6,
            )
        return tk.OptionMenu(parent, var, *values)

    def _sched_radio(self, parent, text, var, value, command):
        if self.use_ctk:
            return ctk.CTkRadioButton(
                parent, text=text, variable=var, value=value, command=command,
                font=("Segoe UI", 11), text_color=self.colors["text_primary"],
                fg_color="#3b82f6",
            )
        return tk.Radiobutton(
            parent, text=text, variable=var, value=value, command=command,
            bg=self.colors["bg_primary"], fg=self.colors["text_primary"],
            selectcolor=self.colors["bg_secondary"], font=("Segoe UI", 11),
        )

    def _sched_check(self, parent, text, var):
        if self.use_ctk:
            return ctk.CTkCheckBox(
                parent, text=text, variable=var, font=("Segoe UI", 11),
                text_color=self.colors["text_primary"], fg_color="#3b82f6",
            )
        return tk.Checkbutton(
            parent, text=text, variable=var, bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"], selectcolor=self.colors["bg_secondary"],
            font=("Segoe UI", 11),
        )
