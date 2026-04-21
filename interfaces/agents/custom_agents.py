"""Mixin : gestion des agents personnalisés (CRUD + dialogues)."""

import json
import os
import random
import threading
from datetime import datetime
from tkinter import messagebox

from interfaces.agents._common import ctk, tk
from core.config import get_default_model as _get_default_model
from models.ai_agents import AVAILABLE_AGENTS, AIAgent


class CustomAgentsMixin:
    """Persistance, enregistrement et UI des agents personnalisés."""

    def _get_random_color(self):
        """Returns a random vibrant color for custom agents"""
        palette = [
            "#e11d48", "#7c3aed", "#0891b2", "#059669", "#d97706",
            "#dc2626", "#9333ea", "#0284c7", "#16a34a", "#ca8a04",
            "#be185d", "#6d28d9", "#0e7490", "#047857", "#b45309",
            "#c026d3", "#4f46e5", "#0369a1", "#15803d", "#a16207",
        ]
        return random.choice(palette)

    def _load_custom_agents(self):
        """Load custom agents from JSON file"""
        try:
            if os.path.exists(self.custom_agents_file):
                with open(self.custom_agents_file, "r", encoding="utf-8") as f:
                    self.custom_agents = json.load(f)
                print(f"✅ {len(self.custom_agents)} agents personnalisés chargés")
        except Exception as e:
            print(f"⚠️ Erreur chargement agents personnalisés: {e}")
            self.custom_agents = {}

    def _save_custom_agents(self):
        """Save custom agents to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.custom_agents_file), exist_ok=True)
            with open(self.custom_agents_file, "w", encoding="utf-8") as f:
                json.dump(self.custom_agents, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde agents personnalisés: {e}")

    def _register_custom_agent_in_orchestrator(self, agent_key, agent_data):
        """Register a custom agent so it can be used by the orchestrator"""
        def factory(model=None):
            return AIAgent(
                name=agent_data["name"],
                expertise=agent_data["desc"],
                system_prompt=agent_data["system_prompt"],
                model=model or _get_default_model(),
                temperature=agent_data.get("temperature", 0.5),
            )
        # Add to available agents
        AVAILABLE_AGENTS[agent_key] = factory

    def _render_custom_agents_in_grid(self, start_idx=9):
        """Render all custom agents in the agents grid"""
        if not self.agents_grid:
            return
        for idx, (agent_key, agent_data) in enumerate(self.custom_agents.items()):
            total_idx = start_idx + idx
            row = total_idx // 3
            col = total_idx % 3

            card = self._create_custom_agent_card(
                self.agents_grid,
                agent_key,
                agent_data["name"],
                agent_data["desc"],
                agent_data["color"],
            )
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self.agents_grid.grid_columnconfigure(col, weight=1, uniform="agent")

            # Register in orchestrator
            self._register_custom_agent_in_orchestrator(agent_key, agent_data)

    def _create_custom_agent_card(self, parent, agent_key, name, desc, color):
        """Create a custom agent card with edit/delete buttons"""
        card_frame = self.create_frame(parent, fg_color=self.colors["bg_secondary"])

        if self.use_ctk:
            card_frame.configure(
                corner_radius=12, border_width=2, border_color=self.colors["border"]
            )

        try:
            card_frame.configure(cursor="hand2")
        except Exception:
            pass

        content_frame = self.create_frame(
            card_frame, fg_color=self.colors["bg_secondary"]
        )
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Top bar with edit/delete buttons
        top_bar = self.create_frame(content_frame, fg_color=self.colors["bg_secondary"])
        top_bar.pack(fill="x")

        # Icon + Name (left side)
        header_frame = self.create_frame(
            top_bar, fg_color=self.colors["bg_secondary"]
        )
        header_frame.pack(side="left", fill="x", expand=True)

        icon_label = self.create_label(
            header_frame,
            text="🤖",
            font=("Segoe UI", 28),
            fg_color=self.colors["bg_secondary"],
        )
        icon_label.pack(side="left", padx=(0, 10))

        name_label = self.create_label(
            header_frame,
            text=name,
            font=("Segoe UI", 14, "bold"),
            text_color=color,
            fg_color=self.colors["bg_secondary"],
        )
        name_label.pack(side="left", anchor="w")

        # Action buttons (right side, top)
        actions_frame = self.create_frame(
            top_bar, fg_color=self.colors["bg_secondary"]
        )
        actions_frame.pack(side="right")

        # Edit button (pencil)
        if self.use_ctk:
            edit_btn = ctk.CTkButton(
                actions_frame,
                text="📝",
                width=30, height=30,
                fg_color="transparent",
                hover_color=self.colors["bg_primary"],
                font=("Segoe UI", 14),
                corner_radius=6,
                command=lambda k=agent_key: self._open_edit_agent_dialog(k),
            )
        else:
            edit_btn = tk.Button(
                actions_frame,
                text="📝",
                bg=self.colors["bg_secondary"],
                font=("Segoe UI", 12),
                border=0, relief="flat",
                command=lambda k=agent_key: self._open_edit_agent_dialog(k),
            )
        edit_btn.pack(side="left", padx=(0, 4))

        # Delete button (cross)
        if self.use_ctk:
            delete_btn = ctk.CTkButton(
                actions_frame,
                text="✕",
                width=30, height=30,
                fg_color="transparent",
                hover_color=self.colors["bg_primary"],
                text_color="#ef4444",
                font=("Segoe UI", 14, "bold"),
                corner_radius=6,
                command=lambda k=agent_key: self._delete_custom_agent(k),
            )
        else:
            delete_btn = tk.Button(
                actions_frame,
                text="✕",
                bg=self.colors["bg_secondary"],
                fg="#ef4444",
                font=("Segoe UI", 12, "bold"),
                border=0, relief="flat",
                command=lambda k=agent_key: self._delete_custom_agent(k),
            )
        delete_btn.pack(side="left")

        # Short description (use short_desc if available, else desc)
        agent_data = self.custom_agents.get(agent_key, {})
        display_desc = agent_data.get("short_desc", desc)
        desc_label = self.create_label(
            content_frame,
            text=display_desc,
            font=("Segoe UI", 12, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_secondary"],
            wraplength=250,
        )
        desc_label.pack(fill="x", pady=(15, 5))

        # Make draggable (exclude edit/delete buttons)
        all_widgets = [card_frame, content_frame, top_bar, header_frame,
                       icon_label, name_label, desc_label]

        for widget in all_widgets:
            self._make_draggable(widget, agent_key, name, color)

        # Hover effect
        def on_enter(_e):
            if self.use_ctk:
                card_frame.configure(border_color=color, border_width=2)

        def on_leave(_e):
            if self.use_ctk:
                card_frame.configure(
                    border_color=self.colors["border"], border_width=2
                )

        for widget in all_widgets:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        self.agent_buttons[agent_key] = (card_frame, None, color)
        return card_frame

    def _show_notification(self, message, color="#10b981", duration=2500):
        """Show a notification in the top-right corner of the agents page"""
        try:
            if self.use_ctk:
                notif = ctk.CTkFrame(
                    self.parent, fg_color=color, corner_radius=8
                )
                lbl = ctk.CTkLabel(
                    notif, text=message, text_color="#ffffff",
                    font=("Segoe UI", 12, "bold"), fg_color="transparent",
                )
            else:
                notif = tk.Frame(self.parent, bg=color)
                lbl = tk.Label(
                    notif, text=message, fg="#ffffff", bg=color,
                    font=("Segoe UI", 12, "bold"),
                )

            notif.place(relx=0.98, rely=0.02, anchor="ne")
            lbl.pack(padx=15, pady=8)
            notif.lift()
            self.parent.after(duration, notif.destroy)
        except Exception:
            pass

    # === Create Agent Dialog ===

    def _open_create_agent_dialog(self):
        """Open a dialog to create a custom agent"""
        dialog = tk.Toplevel()
        dialog.title("Créer un Agent Personnalisé")
        dialog.geometry("500x380")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors["bg_primary"])
        dialog.transient(self.parent.winfo_toplevel())
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 250
        y = (dialog.winfo_screenheight() // 2) - 190
        dialog.geometry(f"500x380+{x}+{y}")

        # Title
        title_lbl = self.create_label(
            dialog,
            text="🤖 Créer un Agent Personnalisé",
            font=("Segoe UI", 16, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        title_lbl.pack(padx=20, pady=(20, 15))

        # Name field
        name_lbl = self.create_label(
            dialog, text="Nom de l'agent",
            font=("Segoe UI", 11, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        name_lbl.pack(anchor="w", padx=30)

        if self.use_ctk:
            name_entry = ctk.CTkEntry(
                dialog, font=("Segoe UI", 12), height=36,
                fg_color=self.colors["input_bg"],
                text_color=self.colors["text_primary"],
                border_color=self.colors["border"],
                corner_radius=6, placeholder_text="Ex: MyCustomAgent",
            )
        else:
            name_entry = tk.Entry(
                dialog, font=("Segoe UI", 12),
                bg=self.colors["input_bg"], fg=self.colors["text_primary"],
            )
        name_entry.pack(fill="x", padx=30, pady=(4, 12))

        # Role/description field
        role_lbl = self.create_label(
            dialog, text="Rôle / Description",
            font=("Segoe UI", 11, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        role_lbl.pack(anchor="w", padx=30)

        if self.use_ctk:
            role_entry = ctk.CTkTextbox(
                dialog, height=100, font=("Segoe UI", 12),
                fg_color=self.colors["input_bg"],
                text_color=self.colors["text_primary"],
                border_width=1, border_color=self.colors["border"],
                corner_radius=6,
            )
        else:
            role_entry = tk.Text(
                dialog, height=5, font=("Segoe UI", 12),
                bg=self.colors["input_bg"], fg=self.colors["text_primary"],
            )
        role_entry.pack(fill="x", padx=30, pady=(4, 15))

        # Loading indicator (hidden initially)
        loading_frame = self.create_frame(dialog, fg_color=self.colors["bg_primary"])
        loading_frame.pack(fill="x", padx=30)

        loading_label = self.create_label(
            loading_frame, text="",
            font=("Segoe UI", 11),
            text_color="#f59e0b",
            fg_color=self.colors["bg_primary"],
        )
        loading_label.pack()

        # Buttons frame
        btn_frame = self.create_frame(dialog, fg_color=self.colors["bg_primary"])
        btn_frame.pack(fill="x", padx=30, pady=(10, 20))

        # Cancel button
        if self.use_ctk:
            cancel_btn = ctk.CTkButton(
                btn_frame, text="Annuler", width=120,
                fg_color=self.colors["bg_secondary"],
                hover_color=self.colors["border"],
                text_color=self.colors["text_primary"],
                font=("Segoe UI", 11, "bold"),
                corner_radius=8,
                command=dialog.destroy,
            )
        else:
            cancel_btn = tk.Button(
                btn_frame, text="Annuler",
                bg=self.colors["bg_secondary"],
                fg=self.colors["text_primary"],
                font=("Segoe UI", 11, "bold"),
                command=dialog.destroy,
            )
        cancel_btn.pack(side="right", padx=(10, 0))

        # Create button
        if self.use_ctk:
            create_btn = ctk.CTkButton(
                btn_frame, text="Créer", width=120,
                fg_color="#3b82f6", hover_color="#2563eb",
                text_color="#ffffff",
                font=("Segoe UI", 11, "bold"),
                corner_radius=8,
                command=lambda: self._do_create_agent(
                    dialog, name_entry, role_entry,
                    loading_label, create_btn, cancel_btn
                ),
            )
        else:
            create_btn = tk.Button(
                btn_frame, text="Créer",
                bg="#3b82f6", fg="#ffffff",
                font=("Segoe UI", 11, "bold"),
                command=lambda: self._do_create_agent(
                    dialog, name_entry, role_entry,
                    loading_label, create_btn, cancel_btn
                ),
            )
        create_btn.pack(side="right")

    def _do_create_agent(self, dialog, name_entry, role_entry,
                         loading_label, create_btn, cancel_btn):
        """Start the agent creation process"""
        # Get values
        if self.use_ctk:
            name = name_entry.get().strip()
            role = role_entry.get("0.0", "end-1c").strip()
        else:
            name = name_entry.get().strip()
            role = role_entry.get("1.0", "end-1c").strip()

        if not name:
            messagebox.showwarning("Nom requis", "Veuillez entrer un nom pour l'agent.")
            return
        if not role:
            messagebox.showwarning("Rôle requis", "Veuillez décrire le rôle de l'agent.")
            return

        # Disable buttons and show loading
        if self.use_ctk:
            create_btn.configure(state="disabled")
            cancel_btn.configure(state="disabled")
        else:
            create_btn.configure(state="disabled")
            cancel_btn.configure(state="disabled")

        # Loading animation
        self._animate_loading(loading_label, dialog, 0)

        # Generate system prompt in background thread
        threading.Thread(
            target=self._generate_agent_in_background,
            args=(dialog, name, role, loading_label),
            daemon=True,
        ).start()

    def _animate_loading(self, label, dialog, step):
        """Animate a loading indicator"""
        if not dialog.winfo_exists():
            return
        spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        icon = spinner[step % len(spinner)]
        label.configure(text=f"{icon} Génération du system prompt en cours...")
        dialog.after(200, lambda: self._animate_loading(label, dialog, step + 1))

    def _generate_agent_in_background(self, dialog, name, role, loading_label):
        """Generate system prompt via Ollama in background thread"""
        prompt = f"""Tu dois créer un system prompt pour un agent IA spécialisé.

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

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt="Tu es un assistant qui génère des system prompts pour des agents IA. Réponds uniquement avec le contenu demandé, sans explications."
            )

            if response:
                # Parse temperature and summary from response
                temperature = 0.5
                short_desc = role[:30]
                system_prompt = response.strip()

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
                        temp_str = parts[1].strip().split()[0]
                        temperature = float(temp_str)
                        temperature = max(0.1, min(0.9, temperature))
                    except (ValueError, IndexError):
                        temperature = 0.5

                color = self._get_random_color()
                agent_key = f"custom_{name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}"

                agent_data = {
                    "name": name,
                    "desc": role,
                    "short_desc": short_desc,
                    "color": color,
                    "system_prompt": system_prompt,
                    "temperature": temperature,
                }

                self.custom_agents[agent_key] = agent_data
                self._save_custom_agents()
                self._register_custom_agent_in_orchestrator(agent_key, agent_data)

                # Update UI on main thread
                def on_success():
                    if dialog.winfo_exists():
                        dialog.destroy()
                    self._add_custom_agent_card_to_grid(agent_key, agent_data)
                    self._show_notification("✅ Agent créé !", "#10b981")

                self.parent.after(0, on_success)
            else:
                def on_error():
                    if dialog.winfo_exists():
                        loading_label.configure(
                            text="❌ Erreur: Ollama n'a pas répondu. Vérifiez qu'Ollama est lancé.",
                            text_color="#ef4444"
                        )
                self.parent.after(0, on_error)

        except Exception as e:
            def on_error():
                if dialog.winfo_exists():
                    loading_label.configure(
                        text=f"❌ Erreur: {str(e)[:60]}",
                        text_color="#ef4444"
                    )
            self.parent.after(0, on_error)

    def _add_custom_agent_card_to_grid(self, agent_key, agent_data):
        """Add a single custom agent card to the existing grid"""
        if not self.agents_grid:
            return
        # Count existing cards
        total = 9 + len(self.custom_agents) - 1  # 9 built-in + already added custom - current
        row = total // 3
        col = total % 3

        card = self._create_custom_agent_card(
            self.agents_grid,
            agent_key,
            agent_data["name"],
            agent_data["desc"],
            agent_data["color"],
        )
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        self.agents_grid.grid_columnconfigure(col, weight=1, uniform="agent")

    # === Edit Agent Dialog ===

    def _open_edit_agent_dialog(self, agent_key):
        """Open dialog to edit a custom agent"""
        if agent_key not in self.custom_agents:
            return

        agent_data = self.custom_agents[agent_key]

        dialog = tk.Toplevel()
        dialog.title(f"Modifier {agent_data['name']}")
        dialog.geometry("500x380")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors["bg_primary"])
        dialog.transient(self.parent.winfo_toplevel())
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 250
        y = (dialog.winfo_screenheight() // 2) - 190
        dialog.geometry(f"500x380+{x}+{y}")

        # Title
        title_lbl = self.create_label(
            dialog,
            text=f"📝 Modifier {agent_data['name']}",
            font=("Segoe UI", 16, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        title_lbl.pack(padx=20, pady=(20, 15))

        # Name field
        name_lbl = self.create_label(
            dialog, text="Nom de l'agent",
            font=("Segoe UI", 11, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        name_lbl.pack(anchor="w", padx=30)

        if self.use_ctk:
            name_entry = ctk.CTkEntry(
                dialog, font=("Segoe UI", 12), height=36,
                fg_color=self.colors["input_bg"],
                text_color=self.colors["text_primary"],
                border_color=self.colors["border"],
                corner_radius=6,
            )
            name_entry.insert(0, agent_data["name"])
        else:
            name_entry = tk.Entry(
                dialog, font=("Segoe UI", 12),
                bg=self.colors["input_bg"], fg=self.colors["text_primary"],
            )
            name_entry.insert(0, agent_data["name"])
        name_entry.pack(fill="x", padx=30, pady=(4, 12))

        # Role/description field
        role_lbl = self.create_label(
            dialog, text="Rôle / Description",
            font=("Segoe UI", 11, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_primary"],
        )
        role_lbl.pack(anchor="w", padx=30)

        if self.use_ctk:
            role_entry = ctk.CTkTextbox(
                dialog, height=100, font=("Segoe UI", 12),
                fg_color=self.colors["input_bg"],
                text_color=self.colors["text_primary"],
                border_width=1, border_color=self.colors["border"],
                corner_radius=6,
            )
            role_entry.insert("0.0", agent_data["desc"])
        else:
            role_entry = tk.Text(
                dialog, height=5, font=("Segoe UI", 12),
                bg=self.colors["input_bg"], fg=self.colors["text_primary"],
            )
            role_entry.insert("1.0", agent_data["desc"])
        role_entry.pack(fill="x", padx=30, pady=(4, 15))

        # Loading indicator
        loading_frame = self.create_frame(dialog, fg_color=self.colors["bg_primary"])
        loading_frame.pack(fill="x", padx=30)

        loading_label = self.create_label(
            loading_frame, text="",
            font=("Segoe UI", 11),
            text_color="#f59e0b",
            fg_color=self.colors["bg_primary"],
        )
        loading_label.pack()

        # Buttons
        btn_frame = self.create_frame(dialog, fg_color=self.colors["bg_primary"])
        btn_frame.pack(fill="x", padx=30, pady=(10, 20))

        if self.use_ctk:
            cancel_btn = ctk.CTkButton(
                btn_frame, text="Annuler", width=120,
                fg_color=self.colors["bg_secondary"],
                hover_color=self.colors["border"],
                text_color=self.colors["text_primary"],
                font=("Segoe UI", 11, "bold"),
                corner_radius=8,
                command=dialog.destroy,
            )
        else:
            cancel_btn = tk.Button(
                btn_frame, text="Annuler",
                bg=self.colors["bg_secondary"],
                fg=self.colors["text_primary"],
                font=("Segoe UI", 11, "bold"),
                command=dialog.destroy,
            )
        cancel_btn.pack(side="right", padx=(10, 0))

        if self.use_ctk:
            save_btn = ctk.CTkButton(
                btn_frame, text="Sauvegarder", width=140,
                fg_color="#3b82f6", hover_color="#2563eb",
                text_color="#ffffff",
                font=("Segoe UI", 11, "bold"),
                corner_radius=8,
                command=lambda: self._do_edit_agent(
                    dialog, agent_key, name_entry, role_entry,
                    loading_label, save_btn, cancel_btn
                ),
            )
        else:
            save_btn = tk.Button(
                btn_frame, text="Sauvegarder",
                bg="#3b82f6", fg="#ffffff",
                font=("Segoe UI", 11, "bold"),
                command=lambda: self._do_edit_agent(
                    dialog, agent_key, name_entry, role_entry,
                    loading_label, save_btn, cancel_btn
                ),
            )
        save_btn.pack(side="right")

    def _do_edit_agent(self, dialog, agent_key, name_entry, role_entry,
                       loading_label, save_btn, cancel_btn):
        """Process agent edit"""
        if self.use_ctk:
            new_name = name_entry.get().strip()
            new_role = role_entry.get("0.0", "end-1c").strip()
        else:
            new_name = name_entry.get().strip()
            new_role = role_entry.get("1.0", "end-1c").strip()

        if not new_name:
            messagebox.showwarning("Nom requis", "Veuillez entrer un nom pour l'agent.")
            return
        if not new_role:
            messagebox.showwarning("Rôle requis", "Veuillez décrire le rôle de l'agent.")
            return

        old_data = self.custom_agents[agent_key]
        name_changed = new_name != old_data["name"]
        desc_changed = new_role != old_data["desc"]

        if not name_changed and not desc_changed:
            dialog.destroy()
            return

        if desc_changed:
            # Description changed -> regenerate system prompt via Ollama
            if self.use_ctk:
                save_btn.configure(state="disabled")
                cancel_btn.configure(state="disabled")
            else:
                save_btn.configure(state="disabled")
                cancel_btn.configure(state="disabled")

            self._animate_loading(loading_label, dialog, 0)

            threading.Thread(
                target=self._regenerate_agent_prompt,
                args=(dialog, agent_key, new_name, new_role, loading_label),
                daemon=True,
            ).start()
        else:
            # Only name changed -> just update name
            self.custom_agents[agent_key]["name"] = new_name
            self._save_custom_agents()
            self._register_custom_agent_in_orchestrator(agent_key, self.custom_agents[agent_key])
            dialog.destroy()
            self._refresh_agents_grid()
            self._show_notification("✅ Agent modifié !", "#10b981")

    def _regenerate_agent_prompt(self, dialog, agent_key, new_name, new_role, loading_label):
        """Regenerate an agent's system prompt after description change"""
        prompt = f"""Tu dois créer un system prompt pour un agent IA spécialisé.

Voici le nom de l'agent: {new_name}
Voici la description de son rôle: {new_role}

Génère un system prompt complet en suivant EXACTEMENT ce format:

Tu es {new_name}, un expert en [domaine basé sur la description].

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

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt="Tu es un assistant qui génère des system prompts pour des agents IA. Réponds uniquement avec le contenu demandé, sans explications."
            )

            if response:
                temperature = 0.5
                short_desc = new_role[:30]
                system_prompt = response.strip()

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
                        temp_str = parts[1].strip().split()[0]
                        temperature = float(temp_str)
                        temperature = max(0.1, min(0.9, temperature))
                    except (ValueError, IndexError):
                        temperature = 0.5

                self.custom_agents[agent_key]["name"] = new_name
                self.custom_agents[agent_key]["desc"] = new_role
                self.custom_agents[agent_key]["short_desc"] = short_desc
                self.custom_agents[agent_key]["system_prompt"] = system_prompt
                self.custom_agents[agent_key]["temperature"] = temperature
                self._save_custom_agents()
                self._register_custom_agent_in_orchestrator(agent_key, self.custom_agents[agent_key])

                # Remove cached agent from orchestrator so it gets recreated
                if agent_key in self.orchestrator.agents:
                    del self.orchestrator.agents[agent_key]

                def on_success():
                    if dialog.winfo_exists():
                        dialog.destroy()
                    self._refresh_agents_grid()
                    self._show_notification("✅ Agent modifié !", "#10b981")

                self.parent.after(0, on_success)
            else:
                def on_error():
                    if dialog.winfo_exists():
                        loading_label.configure(
                            text="❌ Erreur: Ollama n'a pas répondu.",
                            text_color="#ef4444"
                        )
                self.parent.after(0, on_error)

        except Exception as e:
            def on_error():
                if dialog.winfo_exists():
                    loading_label.configure(
                        text=f"❌ Erreur: {str(e)[:60]}",
                        text_color="#ef4444"
                    )
            self.parent.after(0, on_error)

    # === Delete Agent ===

    def _delete_custom_agent(self, agent_key):
        """Delete a custom agent"""
        if agent_key not in self.custom_agents:
            return

        agent_name = self.custom_agents[agent_key]["name"]
        confirm = messagebox.askyesno(
            "Supprimer l'agent",
            f"Voulez-vous vraiment supprimer l'agent '{agent_name}' ?"
        )

        if confirm:
            # Remove from data
            del self.custom_agents[agent_key]
            self._save_custom_agents()

            # Remove from orchestrator
            if agent_key in self.orchestrator.agents:
                del self.orchestrator.agents[agent_key]
            if agent_key in AVAILABLE_AGENTS:
                del AVAILABLE_AGENTS[agent_key]
            if agent_key in self.agent_buttons:
                del self.agent_buttons[agent_key]

            # Remove from workflow if present
            self.custom_workflow = [
                (at, n, c) for at, n, c in self.custom_workflow if at != agent_key
            ]
            self.update_pipeline_display()

            # Refresh grid
            self._refresh_agents_grid()
            self._show_notification("❌ Agent supprimé", "#ef4444")

    def _refresh_agents_grid(self):
        """Refresh the entire agents grid (rebuild custom agents)"""
        if not self.agents_grid:
            return

        # Remove custom agent cards (children after the 9 built-in cards)
        children = self.agents_grid.winfo_children()
        # Built-in agents have 9 cards (indices 0-8), remove the rest
        for child in children[9:]:
            child.destroy()

        # Re-render custom agents
        self._render_custom_agents_in_grid(9)

    def _get_all_agent_choices(self):
        """Retourne [(key, display, color)] pour tous les agents (built-in + custom)."""
        choices = []
        builtin = getattr(self, "_builtin_agents_info", {})
        for key, info in builtin.items():
            display = f"{info.get('icon', '🤖')} {info.get('name', key)}"
            choices.append((key, display, info.get("color", "#3b82f6")))
        for key, data in self.custom_agents.items():
            display = f"🧩 {data.get('name', key)} (perso)"
            choices.append((key, display, data.get("color", "#ff6b47")))
        return choices
