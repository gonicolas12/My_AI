"""Mixin : drag & drop des cartes d'agents vers le canvas de workflow."""

from interfaces.agents._common import tk


class DragDropMixin:
    """Gestion du drag & drop d'agents."""

    def _make_draggable(self, widget, agent_type, name, color):
        """Rend un widget draggable pour le drag & drop d'agents"""
        widget.bind(
            "<ButtonPress-1>",
            lambda e: self._on_drag_start(e, agent_type, name, color),
        )
        widget.bind("<B1-Motion>", self._on_drag_motion)
        widget.bind("<ButtonRelease-1>", self._on_drag_end)

    def _on_drag_start(self, event, agent_type, name, color):
        """Début du drag - crée un indicateur flottant"""
        self._drag_data["agent"] = (agent_type, name, color)

        # Créer un toplevel flottant comme indicateur visuel
        top = tk.Toplevel()
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        try:
            top.attributes("-alpha", 0.85)
        except Exception:
            pass

        # Contenu du toplevel
        frame = tk.Frame(top, bg=color, padx=12, pady=8, relief="solid", bd=1)
        frame.pack()

        label = tk.Label(
            frame,
            text=f"🤖 {name}",
            font=("Segoe UI", 12, "bold"),
            fg="white",
            bg=color,
        )
        label.pack()

        # Positionner
        top.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        self._drag_data["toplevel"] = top

    def _on_drag_motion(self, event):
        """Mouvement pendant le drag"""
        top = self._drag_data.get("toplevel")
        if top and top.winfo_exists():
            top.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

        # Highlight canvas outer frame border when dragging over it
        if self.workflow_canvas and self.workflow_canvas.is_over(event.x_root, event.y_root):
            try:
                if self.use_ctk and hasattr(self, 'canvas_outer'):
                    self.canvas_outer.configure(
                        border_color=self.colors["accent"], border_width=3
                    )
            except Exception:
                pass
        else:
            try:
                if self.use_ctk and hasattr(self, 'canvas_outer'):
                    self.canvas_outer.configure(
                        border_color=self.colors["border"], border_width=2
                    )
            except Exception:
                pass

    def _on_drag_end(self, event):
        """Fin du drag - vérifie si on est sur la zone de drop"""
        agent_data = self._drag_data.get("agent")
        top = self._drag_data.get("toplevel")

        # Détruire l'indicateur flottant
        if top and top.winfo_exists():
            top.destroy()

        # Reset canvas outer border
        if self.use_ctk and hasattr(self, 'canvas_outer'):
            try:
                self.canvas_outer.configure(
                    border_color=self.colors["border"], border_width=2
                )
            except Exception:
                pass

        if not agent_data:
            self._drag_data = {"agent": None, "toplevel": None}
            return

        agent_type, name, color = agent_data

        # Trouver l'icône de l'agent
        icon = self._get_agent_icon(agent_type)

        # Drop uniquement sur le canvas de workflow visuel
        if self.workflow_canvas and self.workflow_canvas.is_over(event.x_root, event.y_root):
            self.workflow_canvas.drop_agent(
                agent_type, name, color, event.x_root, event.y_root, icon=icon
            )

        self._drag_data = {"agent": None, "toplevel": None}

    def _is_over_drop_zone(self, x_root, y_root):
        """Vérifie si les coordonnées sont sur la zone de drop"""
        # Vérifier la zone de drop principale
        if self.drop_zone_frame and self.drop_zone_frame.winfo_exists():
            try:
                dz_x = self.drop_zone_frame.winfo_rootx()
                dz_y = self.drop_zone_frame.winfo_rooty()
                dz_w = self.drop_zone_frame.winfo_width()
                dz_h = self.drop_zone_frame.winfo_height()
                if (dz_x <= x_root <= dz_x + dz_w) and (
                    dz_y <= y_root <= dz_y + dz_h
                ):
                    return True
            except Exception:
                pass

        # Vérifier aussi la zone de texte de la tâche
        if self.task_section_frame and self.task_section_frame.winfo_exists():
            try:
                ts_x = self.task_section_frame.winfo_rootx()
                ts_y = self.task_section_frame.winfo_rooty()
                ts_w = self.task_section_frame.winfo_width()
                ts_h = self.task_section_frame.winfo_height()
                if (ts_x <= x_root <= ts_x + ts_w) and (
                    ts_y <= y_root <= ts_y + ts_h
                ):
                    return True
            except Exception:
                pass

        return False

    def _is_over_task_entry(self, x_root, y_root):
        """Vérifie si les coordonnées sont sur la zone de texte de la tâche"""
        if self.task_entry and self.task_entry.winfo_exists():
            try:
                te_x = self.task_entry.winfo_rootx()
                te_y = self.task_entry.winfo_rooty()
                te_w = self.task_entry.winfo_width()
                te_h = self.task_entry.winfo_height()
                if (te_x <= x_root <= te_x + te_w) and (
                    te_y <= y_root <= te_y + te_h
                ):
                    return True
            except Exception:
                pass
        return False
