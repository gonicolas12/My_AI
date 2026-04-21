"""Mixin : mode Débat entre deux agents (dialogue, popup + exécution)."""

import threading
from datetime import datetime

from interfaces.agents._common import ctk, tk


class DebateMixin:
    """Popup de configuration + exécution du mode débat entre deux agents."""

    def _open_debate_dialog(self):
        """Popup pour configurer un débat entre deux agents."""
        if self.is_processing:
            self._show_notification("⏳ Une tâche est déjà en cours", "#f59e0b")
            return

        choices = self._get_all_agent_choices()
        if len(choices) < 2:
            self._show_notification(
                "❌ Il faut au moins 2 agents disponibles", "#ef4444"
            )
            return

        # Map display -> key pour récupérer la sélection
        display_to_key = {disp: key for key, disp, _ in choices}
        display_values = list(display_to_key.keys())

        dialog = tk.Toplevel()
        dialog.title("Mode Débat")
        dialog.geometry("520x480")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors["bg_primary"])
        dialog.transient(self.parent.winfo_toplevel())
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 260
        y = (dialog.winfo_screenheight() // 2) - 240
        dialog.geometry(f"520x480+{x}+{y}")

        # Titre
        self.create_label(
            dialog, text="🎭 Mode Débat entre deux agents",
            font=("Segoe UI", 16, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        ).pack(padx=20, pady=(20, 15))

        # Agent A (proposant)
        self.create_label(
            dialog, text="Agent A — Proposant",
            font=("Segoe UI", 11, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        ).pack(anchor="w", padx=30)

        default_a = display_values[0]
        default_b = display_values[1] if len(display_values) > 1 else display_values[0]
        var_a = tk.StringVar(value=default_a)
        var_b = tk.StringVar(value=default_b)

        if self.use_ctk:
            combo_a = ctk.CTkOptionMenu(
                dialog, values=display_values, variable=var_a,
                font=("Segoe UI", 11), height=34, width=440,
                fg_color=self.colors["input_bg"],
                button_color=self.colors["accent"],
                button_hover_color="#ff5730",
                text_color=self.colors["text_primary"],
                dropdown_font=("Segoe UI", 11),
                dropdown_fg_color=self.colors["bg_secondary"],
                dropdown_text_color=self.colors["text_primary"],
                corner_radius=6,
            )
        else:
            combo_a = tk.OptionMenu(dialog, var_a, *display_values)
        combo_a.pack(fill="x", padx=30, pady=(4, 12))

        # Agent B (opposant)
        self.create_label(
            dialog, text="Agent B — Opposant",
            font=("Segoe UI", 11, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        ).pack(anchor="w", padx=30)

        if self.use_ctk:
            combo_b = ctk.CTkOptionMenu(
                dialog, values=display_values, variable=var_b,
                font=("Segoe UI", 11), height=34, width=440,
                fg_color=self.colors["input_bg"],
                button_color=self.colors["accent"],
                button_hover_color="#ff5730",
                text_color=self.colors["text_primary"],
                dropdown_font=("Segoe UI", 11),
                dropdown_fg_color=self.colors["bg_secondary"],
                dropdown_text_color=self.colors["text_primary"],
                corner_radius=6,
            )
        else:
            combo_b = tk.OptionMenu(dialog, var_b, *display_values)
        combo_b.pack(fill="x", padx=30, pady=(4, 12))

        # Sujet
        self.create_label(
            dialog, text="Sujet du débat",
            font=("Segoe UI", 11, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        ).pack(anchor="w", padx=30)

        if self.use_ctk:
            topic_entry = ctk.CTkTextbox(
                dialog, height=80, font=("Segoe UI", 12),
                fg_color=self.colors["input_bg"],
                text_color=self.colors["text_primary"],
                border_width=1, border_color=self.colors["border"],
                corner_radius=6,
            )
        else:
            topic_entry = tk.Text(
                dialog, height=4, font=("Segoe UI", 12),
                bg=self.colors["input_bg"], fg=self.colors["text_primary"],
            )
        topic_entry.pack(fill="x", padx=30, pady=(4, 12))

        # Nombre de tours
        rounds_row = self.create_frame(dialog, fg_color=self.colors["bg_primary"])
        rounds_row.pack(fill="x", padx=30, pady=(0, 15))
        self.create_label(
            rounds_row, text="Nombre de tours :",
            font=("Segoe UI", 11, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        ).pack(side="left")
        rounds_var = tk.IntVar(value=3)
        rounds_spin = tk.Spinbox(
            rounds_row, from_=1, to=10, width=5, textvariable=rounds_var,
            font=("Segoe UI", 11),
            bg=self.colors["input_bg"], fg=self.colors["text_primary"],
            buttonbackground=self.colors["bg_secondary"],
            relief="flat",
        )
        rounds_spin.pack(side="left", padx=(8, 0))

        # Boutons
        btn_frame = self.create_frame(dialog, fg_color=self.colors["bg_primary"])
        btn_frame.pack(fill="x", padx=30, pady=(0, 20))

        def on_start():
            key_a = display_to_key.get(var_a.get())
            key_b = display_to_key.get(var_b.get())
            if not key_a or not key_b:
                return
            if key_a == key_b:
                self._show_notification(
                    "❌ Choisis deux agents différents", "#ef4444"
                )
                return
            try:
                topic = topic_entry.get("1.0", "end").strip()
            except Exception:
                topic = ""
            if not topic:
                self._show_notification("❌ Sujet requis", "#ef4444")
                return
            rounds = max(1, min(10, int(rounds_var.get() or 3)))
            dialog.destroy()
            self._start_debate(key_a, key_b, topic, rounds)

        if self.use_ctk:
            ctk.CTkButton(
                btn_frame, text="Annuler", width=120,
                fg_color=self.colors["bg_secondary"],
                hover_color=self.colors["border"],
                text_color=self.colors["text_primary"],
                font=("Segoe UI", 11, "bold"),
                corner_radius=8,
                command=dialog.destroy,
            ).pack(side="left")
            ctk.CTkButton(
                btn_frame, text="▶ Démarrer le débat", width=200,
                fg_color="#8b5cf6", hover_color="#7c3aed",
                text_color="#ffffff",
                font=("Segoe UI", 11, "bold"),
                corner_radius=8,
                command=on_start,
            ).pack(side="right")
        else:
            tk.Button(
                btn_frame, text="Annuler", command=dialog.destroy,
                bg=self.colors["bg_secondary"], fg=self.colors["text_primary"],
                font=("Segoe UI", 11, "bold"), relief="flat",
            ).pack(side="left")
            tk.Button(
                btn_frame, text="▶ Démarrer le débat", command=on_start,
                bg="#8b5cf6", fg="#ffffff",
                font=("Segoe UI", 11, "bold"), relief="flat",
            ).pack(side="right")

    def _start_debate(self, agent_a, agent_b, topic, rounds):
        """Lance le débat dans un thread en streamant la sortie dans la zone résultats."""
        if self.is_processing:
            return
        self.is_processing = True
        self.is_interrupted = False
        self._set_execute_button_stop()
        self._update_status(
            f"🎭 Débat: {agent_a} vs {agent_b} ({rounds} tour{'s' if rounds > 1 else ''})",
            "#8b5cf6",
        )
        t = threading.Thread(
            target=self._execute_debate_thread,
            args=(agent_a, agent_b, topic, rounds),
            daemon=True,
        )
        t.start()

    def _execute_debate_thread(self, agent_a, agent_b, topic, rounds):
        try:
            self._clear_output_sections_sync()
            self._create_output_header_sync(f"🎭 Sujet : {topic}")

            agent_colors = {
                "code": "#3b82f6", "web": "#10b981", "analyst": "#8b5cf6",
                "creative": "#f59e0b", "debug": "#ef4444", "planner": "#06b6d4",
                "security": "#ec4899", "optimizer": "#14b8a6",
                "datascience": "#f97316",
            }
            agent_names = {
                "code": "CodeAgent", "web": "WebAgent", "analyst": "AnalystAgent",
                "creative": "CreativeAgent", "debug": "DebugAgent",
                "planner": "PlannerAgent", "security": "SecurityAgent",
                "optimizer": "OptimizerAgent", "datascience": "DataScienceAgent",
            }

            def name_of(key):
                if key in agent_names:
                    return agent_names[key]
                return self.custom_agents.get(key, {}).get("name", key.capitalize())

            def color_of(key):
                if key in agent_colors:
                    return agent_colors[key]
                return self.custom_agents.get(key, {}).get("color", "#ff6b47")

            def on_round_start(round_num, agent_type):
                # Clôture la section précédente avant d'en créer une nouvelle
                if self._active_section is not None:
                    try:
                        self._finish_section(self._active_section, success=True)
                    except Exception:
                        pass
                    self._active_section = None
                role = "Proposant" if agent_type == agent_a else "Opposant"
                section_name = f"Tour {round_num} — {name_of(agent_type)} ({role})"
                section = self._create_step_section_sync(
                    section_name, color_of(agent_type)
                )
                self._active_section = section

            result = self.orchestrator.execute_debate(
                agent_type_a=agent_a,
                agent_type_b=agent_b,
                topic=topic,
                rounds=rounds,
                on_token=self._on_token_received,
                on_round_start=on_round_start,
                on_should_stop=lambda: self.is_interrupted,
            )

            # Finalise la dernière section
            if self._active_section is not None:
                self._finish_section(
                    self._active_section, success=not self.is_interrupted
                )
                self._active_section = None

            if self.is_interrupted:
                self._update_status("⛔ Débat interrompu", "#ef4444")
            elif result.get("success"):
                done = result.get("rounds_completed", 0)
                self._update_status(
                    f"✅ Débat terminé ({done} tour{'s' if done > 1 else ''})",
                    "#10b981",
                )
            else:
                err = result.get("error", "erreur inconnue")
                self._update_status(f"❌ Débat: {err}", "#ef4444")

            self._update_stats()
            self.execution_history.append({
                "mode": "debate",
                "agents": [agent_a, agent_b],
                "topic": topic,
                "rounds": rounds,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            })
        except Exception as exc:
            print(f"⚠️ Erreur mode débat: {exc}")
            if self._active_section is not None:
                try:
                    self._finish_section(self._active_section, success=False)
                except Exception:
                    pass
                self._active_section = None
            self._update_status(f"❌ Erreur débat: {exc}", "#ef4444")
        finally:
            self.is_processing = False
            self.is_interrupted = False
            self._set_execute_button_normal()
