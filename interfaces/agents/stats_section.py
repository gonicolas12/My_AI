"""Mixin : section Statistiques + moniteur de ressources (CPU/GPU/RAM...)."""

from interfaces.agents._common import tk


class StatsSectionMixin:
    """Construction de la barre de stats et rendu des métriques de ressources."""

    def create_stats_section(self, parent):
        """Crée la section des statistiques"""
        section_frame = self.create_frame(parent, fg_color=self.colors["bg_secondary"])
        section_frame.grid(row=5, column=0, sticky="ew", padx=30, pady=(10, 30))

        if self.use_ctk:
            section_frame.configure(corner_radius=10)

        content = self.create_frame(section_frame, fg_color=self.colors["bg_secondary"])
        content.pack(fill="x", padx=20, pady=15)

        # Titre
        title = self.create_label(
            content,
            text="📊 Statistiques",
            font=("Segoe UI", 12, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_secondary"],
        )
        title.pack(anchor="w", pady=(0, 10))

        # Grid de stats
        stats_grid = self.create_frame(content, fg_color=self.colors["bg_secondary"])
        stats_grid.pack(fill="x")

        stats_names = [
            ("tasks", "Tâches Exécutées", "0"),
            ("agents", "Agents Actifs", "0"),
            ("success", "Taux de Succès", "100%"),
        ]

        for idx, (key, label, default) in enumerate(stats_names):
            stat_frame = self.create_frame(
                stats_grid, fg_color=self.colors["bg_secondary"]
            )
            stat_frame.grid(row=0, column=idx, padx=10, sticky="w")

            lbl = self.create_label(
                stat_frame,
                text=label,
                font=("Segoe UI", 9),
                text_color=self.colors["text_secondary"],
                fg_color=self.colors["bg_secondary"],
            )
            lbl.pack(anchor="w")

            val = self.create_label(
                stat_frame,
                text=default,
                font=("Segoe UI", 16, "bold"),
                text_color=self.colors["accent"],
                fg_color=self.colors["bg_secondary"],
            )
            val.pack(anchor="w")

            self.stats_labels[key] = val

        # ── Section Consommation de ressources ─────────────────────
        separator = self.create_frame(content, fg_color=self.colors["border"])
        separator.pack(fill="x", pady=(15, 10))
        if self.use_ctk:
            separator.configure(height=1)
        else:
            separator.config(height=1)

        res_title = self.create_label(
            content,
            text="⚡ Consommation de ressources (Ollama)",
            font=("Segoe UI", 12, "bold"),
            text_color=self.colors["text_primary"],
            fg_color=self.colors["bg_secondary"],
        )
        res_title.pack(anchor="w", pady=(0, 10))

        # Métriques à afficher
        resource_defs = [
            ("cpu",   "CPU",             "%"),
            ("ram",   "RAM",             ""),
            ("gpu",   "GPU",             "%"),
            ("vram",  "VRAM",            ""),
            ("infer", "Temps inférence", ""),
            ("tps",   "Tokens/sec",      ""),
        ]

        res_grid = self.create_frame(content, fg_color=self.colors["bg_secondary"])
        res_grid.pack(fill="x")
        res_grid.grid_columnconfigure(1, weight=1)

        for row_idx, (key, label, _unit) in enumerate(resource_defs):
            # Label
            lbl = self.create_label(
                res_grid, text=label,
                font=("Segoe UI", 10),
                text_color=self.colors["text_secondary"],
                fg_color=self.colors["bg_secondary"],
                anchor="w", width=120,
            )
            lbl.grid(row=row_idx, column=0, sticky="w", padx=(0, 8), pady=3)

            # Progress bar (canvas-based for color control)
            bar_canvas = tk.Canvas(
                res_grid, height=16, bg=self.colors["bg_primary"],
                highlightthickness=0, bd=0,
            )
            bar_canvas.grid(row=row_idx, column=1, sticky="ew", padx=(0, 8), pady=3)
            self._resource_bars[key] = bar_canvas

            # Value label
            val_lbl = self.create_label(
                res_grid, text="—",
                font=("Segoe UI", 10, "bold"),
                text_color=self.colors["text_primary"],
                fg_color=self.colors["bg_secondary"],
                anchor="e", width=100,
            )
            val_lbl.grid(row=row_idx, column=2, sticky="e", padx=(0, 8), pady=3)
            self._resource_labels[key] = val_lbl

            # Sparkline mini-graph
            spark = tk.Canvas(
                res_grid, width=80, height=16,
                bg=self.colors["bg_primary"], highlightthickness=0, bd=0,
            )
            spark.grid(row=row_idx, column=3, sticky="e", pady=3)
            self._sparkline_canvases[key] = spark

        # Démarrer le monitoring
        self.resource_monitor.add_callback(self._on_resource_update)
        self.resource_monitor.start()

    def _update_stats(self):
        """Met à jour les statistiques"""

        def update():
            stats = self.orchestrator.get_orchestrator_stats()

            if "tasks" in self.stats_labels:
                self.stats_labels["tasks"].configure(text=str(stats["total_tasks"]))

            if "agents" in self.stats_labels:
                self.stats_labels["agents"].configure(text=str(stats["active_agents"]))

            # Calculer le taux de succès basé sur l'historique
            if self.execution_history:
                success_count = sum(
                    1 for h in self.execution_history if h["result"].get("success")
                )
                success_rate = (success_count / len(self.execution_history)) * 100
                if "success" in self.stats_labels:
                    self.stats_labels["success"].configure(text=f"{success_rate:.0f}%")

        if self.parent.winfo_exists():
            self.parent.after(0, update)

    # === Resource Monitoring UI =======================================

    def _on_resource_update(self, metrics: dict):
        """Callback du ResourceMonitor — met à jour les barres."""
        if not self.parent.winfo_exists():
            return
        self.parent.after(0, lambda m=dict(metrics): self._apply_resource_metrics(m))

    def _apply_resource_metrics(self, m: dict):
        """Applique les métriques à l'UI (thread principal)."""
        gpu_ok = m.get("gpu_available", False)

        rows = {
            "cpu":   (m.get("cpu_percent", 0), f"{m['cpu_percent']:.1f} %"),
            "ram":   (
                min(m.get("ram_percent", 0), 100),
                f"{m['ram_used_mb']:.0f} Mo / {m['ram_total_mb']:.0f} Mo  ({m['ram_percent']:.1f} %)",
            ),
            "gpu":   (
                m.get("gpu_percent", 0) if gpu_ok else 0,
                f"{m['gpu_percent']:.1f} %" if gpu_ok else "N/A",
            ),
            "vram":  (
                (m["gpu_mem_used_mb"] / max(m["gpu_mem_total_mb"], 1) * 100) if gpu_ok else 0,
                (f"{m['gpu_mem_used_mb']:.0f} / {m['gpu_mem_total_mb']:.0f} Mo"
                 if gpu_ok else "N/A"),
            ),
            "infer": (
                min(m.get("inference_ms", 0) / 50, 100),  # 5 s = 100%
                f"{m['inference_ms']:.0f} ms" if m.get("inference_ms") else "—",
            ),
            "tps":   (
                min(m.get("tokens_per_sec", 0) / 1, 100),  # cap visuel
                f"{m['tokens_per_sec']:.1f} tok/s" if m.get("tokens_per_sec") else "—",
            ),
        }

        for key, (pct, text) in rows.items():
            self._draw_bar(key, pct)
            lbl = self._resource_labels.get(key)
            if lbl and lbl.winfo_exists():
                lbl.configure(text=text)

        # Sparklines
        hist = self.resource_monitor.history
        spark_map = {"cpu": "cpu", "ram": "ram", "gpu": "gpu", "tps": "tps"}
        for ui_key, h_key in spark_map.items():
            data = hist.get(h_key, [])
            self._draw_sparkline(ui_key, data)

    def _draw_bar(self, key: str, pct: float):
        """Dessine une barre de progression colorée."""
        c = self._resource_bars.get(key)
        if not c or not c.winfo_exists():
            return
        c.delete("all")
        w = c.winfo_width() or 200
        h = c.winfo_height() or 16
        # Background
        c.create_rectangle(0, 0, w, h, fill=self.colors["bg_primary"], outline="")
        # Filled portion
        pct = max(0, min(pct, 100))
        fill_w = w * pct / 100
        color = "#10b981" if pct < 50 else "#f59e0b" if pct < 80 else "#ef4444"
        if fill_w > 0:
            c.create_rectangle(0, 0, fill_w, h, fill=color, outline="")

    def _draw_sparkline(self, key: str, data: list):
        """Dessine un mini graphe sparkline."""
        c = self._sparkline_canvases.get(key)
        if not c or not c.winfo_exists() or len(data) < 2:
            return
        c.delete("all")
        w = c.winfo_width() or 80
        h = c.winfo_height() or 16
        max_v = max(data) or 1
        step = w / max(len(data) - 1, 1)
        pts = []
        for i, v in enumerate(data):
            x = i * step
            y = h - (v / max_v) * (h - 2) - 1
            pts.extend([x, y])
        if len(pts) >= 4:
            c.create_line(*pts, fill=self.colors["accent"], width=1.5, smooth=True)
