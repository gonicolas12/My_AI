"""Mixin : gestion du workflow (ajout/suppression d'agents, save/load/export)."""

from tkinter import filedialog


class WorkflowMixin:
    """Gestion du workflow personnalisé + canvas n8n-style."""

    def add_agent_to_workflow(self, agent_type, name, color):
        """Ajoute un agent au workflow personnalisé"""
        self.custom_workflow.append((agent_type, name, color))
        self.current_agent = agent_type
        self.update_pipeline_display()

        # Mettre à jour le statut
        if len(self.custom_workflow) == 1:
            self._update_status(f"✅ Agent ajouté: {name}", "#10b981")
        else:
            agent_names = " → ".join(n for _, n, _ in self.custom_workflow)
            self._update_status(f"✅ Workflow: {agent_names}", "#10b981")

    def clear_workflow(self):
        """Efface le workflow personnalisé"""
        self.custom_workflow.clear()
        self.current_agent = None
        self.update_pipeline_display()
        # Vider aussi le canvas visuel
        if self.workflow_canvas:
            self.workflow_canvas.clear()
        self._update_status(
            "Glissez-déposez des agents pour créer votre workflow",
            self.colors["text_secondary"],
        )

    # ── Sauvegarde / Chargement / Export de workflow ──

    def _save_workflow(self):
        """Sauvegarde le workflow actuel dans un fichier JSON."""
        if not self.workflow_canvas:
            return
        filepath = filedialog.asksaveasfilename(
            title="Sauvegarder le workflow",
            defaultextension=".json",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous", "*.*")],
            initialfile="workflow.json",
        )
        if filepath:
            self.workflow_canvas.save_to_file(filepath)
            if hasattr(self, "show_notification"):
                self.show_notification("💾 Workflow sauvegardé", "success", 1500)
            print(f"💾 [WORKFLOW] Sauvegardé: {filepath}")

    def _load_workflow(self):
        """Charge un workflow depuis un fichier JSON."""
        if not self.workflow_canvas:
            return
        filepath = filedialog.askopenfilename(
            title="Charger un workflow",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous", "*.*")],
        )
        if filepath:
            success = self.workflow_canvas.load_from_file(filepath)
            if success:
                self._on_canvas_changed()
                if hasattr(self, "show_notification"):
                    self.show_notification("📂 Workflow chargé", "success", 1500)
                print(f"📂 [WORKFLOW] Chargé: {filepath}")
            else:
                if hasattr(self, "show_notification"):
                    self.show_notification("❌ Erreur chargement workflow", "error", 2000)

    def _export_workflow(self):
        """Exporte le workflow et ses résultats en fichier texte."""
        if not self.workflow_canvas:
            return
        filepath = filedialog.asksaveasfilename(
            title="Exporter le workflow",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Texte", "*.txt"), ("Tous", "*.*")],
            initialfile="workflow_export.md",
        )
        if filepath:
            try:
                data = self.workflow_canvas.to_dict()
                lines = ["# Workflow Export\n", f"**Version**: {data.get('version', '7.2.0')}\n"]
                lines.append(f"**Nodes**: {len(data.get('nodes', {}))}\n")
                lines.append(f"**Connections**: {len(data.get('connections', []))}\n\n")
                for nid, node in data.get("nodes", {}).items():
                    lines.append(f"## {node.get('icon', '🤖')} {node.get('name', nid)}\n")
                    lines.append(f"- Type: {node.get('agent_type', 'unknown')}\n")
                    lines.append(f"- Status: {node.get('status', 'idle')}\n\n")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                if hasattr(self, "show_notification"):
                    self.show_notification("📤 Workflow exporté", "success", 1500)
                print(f"📤 [WORKFLOW] Exporté: {filepath}")
            except Exception as e:
                print(f"❌ [WORKFLOW] Erreur export: {e}")

    def _on_canvas_changed(self):
        """Callback quand le canvas de workflow est modifié."""
        if not self.workflow_canvas:
            return
        # Synchroniser custom_workflow avec le canvas
        self.custom_workflow = list(self.workflow_canvas.get_ordered_agents())
        self.current_agent = (
            self.custom_workflow[-1][0] if self.custom_workflow else None
        )
        self.update_pipeline_display()

    def update_pipeline_display(self):
        """Met à jour l'affichage du pipeline de workflow"""
        if not self.pipeline_frame:
            return

        # Nettoyer le contenu existant
        for widget in self.pipeline_frame.winfo_children():
            widget.destroy()

        if not self.custom_workflow:
            # Placeholder
            placeholder = self.create_label(
                self.pipeline_frame,
                text="⇩ Glissez-déposez des agents ici pour créer votre workflow",
                font=("Segoe UI", 10),
                text_color=self.colors["text_secondary"],
                fg_color=self.colors["bg_secondary"],
            )
            placeholder.pack(pady=10)
            return

        # Afficher le pipeline
        pipeline_container = self.create_frame(
            self.pipeline_frame, fg_color=self.colors["bg_secondary"]
        )
        pipeline_container.pack(pady=10, padx=10)

        for idx, (_agent_type, name, color) in enumerate(self.custom_workflow):
            if idx > 0:
                # Flèche entre agents
                arrow = self.create_label(
                    pipeline_container,
                    text="  →  ",
                    font=("Segoe UI", 16, "bold"),
                    text_color=self.colors["text_secondary"],
                    fg_color=self.colors["bg_secondary"],
                )
                arrow.pack(side="left")

            # Badge de l'agent avec sa couleur
            agent_badge = self.create_label(
                pipeline_container,
                text=f" {name} ",
                font=("Segoe UI", 12, "bold"),
                text_color=color,
                fg_color=self.colors["bg_secondary"],
            )
            agent_badge.pack(side="left")
