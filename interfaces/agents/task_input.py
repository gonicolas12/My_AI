"""Mixin : zone de saisie de tâche + boutons d'action + canvas workflow."""

import os
from tkinter import scrolledtext

from PIL import Image, ImageGrab

from interfaces.agents._common import ctk, tk
from interfaces.workflow_canvas import WorkflowCanvas


class TaskInputMixin:
    """Construction de la zone de saisie + boutons Exécuter/Créer/Débat/Clear + canvas."""

    def create_task_input(self, parent):
        """Crée la zone de saisie de tâche avec zone de drop"""
        section_frame = self.create_frame(parent, fg_color=self.colors["bg_primary"])
        section_frame.grid(row=3, column=0, sticky="ew", padx=30, pady=(20, 10))
        self.task_section_frame = section_frame

        # Frame pour input + boutons
        input_frame = self.create_frame(
            section_frame, fg_color=self.colors["bg_primary"]
        )
        input_frame.pack(fill="x")
        input_frame.grid_columnconfigure(0, weight=1)

        # Wrapper pour la zone de texte (contient preview + textbox + bouton +)
        task_wrapper = self.create_frame(
            input_frame, fg_color=self.colors["input_bg"], corner_radius=8
        )
        if self.use_ctk:
            task_wrapper.configure(border_width=2, border_color=self.colors["border"])
        task_wrapper.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=(0, 10))
        task_wrapper.grid_columnconfigure(0, weight=1)
        # Row 1 (text area) prend tout l'espace restant à l'intérieur du wrapper
        task_wrapper.grid_rowconfigure(1, weight=1)
        task_wrapper.grid_propagate(False)
        # Hauteur fixe du wrapper : identique à l'originale
        if self.use_ctk:
            task_wrapper.configure(height=160)
        else:
            task_wrapper.configure(height=160)

        # ── Zone d'aperçu des documents attachés (agents) ──
        self._agent_preview_frame = self.create_frame(
            task_wrapper, fg_color=self.colors["input_bg"], corner_radius=0
        )
        self._agent_preview_frame.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 0))
        self._agent_preview_frame.grid_remove()
        self._agent_pending_files = []

        # Zone de texte
        if self.use_ctk:
            self.task_entry = ctk.CTkTextbox(
                task_wrapper,
                height=100,
                font=("Segoe UI", 12),
                fg_color=self.colors["input_bg"],
                text_color=self.colors["text_primary"],
                border_width=0,
                corner_radius=0,
            )
        else:
            self.task_entry = scrolledtext.ScrolledText(
                task_wrapper,
                height=5,
                font=("Segoe UI", 12),
                bg=self.colors["input_bg"],
                fg=self.colors["text_primary"],
                insertbackground=self.colors["text_primary"],
                relief="flat",
                borderwidth=0,
            )

        self.task_entry.grid(row=1, column=0, sticky="nsew", padx=4, pady=2)

        # ── Barre d'outils sous le textbox (bouton + pour fichiers) ──
        task_toolbar = self.create_frame(
            task_wrapper, fg_color=self.colors["input_bg"], corner_radius=0
        )
        task_toolbar.grid(row=2, column=0, sticky="ew", padx=4, pady=(0, 4))

        _agent_file_entries = [
            ("📄  PDF",         lambda: self._agent_load_file("PDF")),
            ("📝  DOCX",        lambda: self._agent_load_file("DOCX")),
            ("📊  Excel / CSV", lambda: self._agent_load_file("Excel")),
            ("💻  Code",        lambda: self._agent_load_file("Code")),
            ("🖼  Image",       lambda: self._agent_load_file("Image")),
        ]
        _agent_popup_ref = [None]

        def _close_agent_popup(popup):
            try:
                popup.destroy()
            except Exception:
                pass
            _agent_popup_ref[0] = None

        def _open_agent_file_menu():
            if _agent_popup_ref[0] is not None:
                _close_agent_popup(_agent_popup_ref[0])
                return
            bg     = self.colors.get("bg_secondary", "#1e1e1e")
            fg     = self.colors.get("text_primary",  "#ffffff")
            accent = self.colors.get("accent",        "#ff6b47")
            font   = ("Segoe UI", 11)
            popup = tk.Toplevel(self.parent.winfo_toplevel())
            popup.overrideredirect(True)
            popup.configure(bg=bg)
            popup.attributes("-topmost", True)
            _agent_popup_ref[0] = popup
            for i, (_lbl, _cmd) in enumerate(_agent_file_entries):
                def _make_cb(cmd, pop=popup):
                    def _cb():
                        _close_agent_popup(pop)
                        cmd()
                    return _cb
                btn = tk.Label(
                    popup, text=_lbl, bg=bg, fg=fg, font=font,
                    anchor="w", padx=14, pady=7, cursor="hand2",
                )
                btn.grid(row=i, column=0, sticky="ew")
                popup.grid_columnconfigure(0, weight=1)
                cb = _make_cb(_cmd)
                btn.bind("<Button-1>", lambda _e, c=cb: c())
                btn.bind("<Enter>", lambda _e, b=btn: b.configure(bg=accent, fg="#ffffff"))
                btn.bind("<Leave>", lambda _e, b=btn: b.configure(bg=bg, fg=fg))
            popup.update_idletasks()
            ph = popup.winfo_reqheight()
            bx = self._agent_file_btn.winfo_rootx()
            by = self._agent_file_btn.winfo_rooty() - ph
            popup.geometry(f"+{bx}+{by}")
            def _on_focus_out(_e):
                self.parent.winfo_toplevel().after(50, lambda: _close_agent_popup(popup) if _agent_popup_ref[0] is popup else None)
            popup.bind("<FocusOut>", _on_focus_out)
            popup.bind("<Escape>", lambda _e: _close_agent_popup(popup))
            self.parent.winfo_toplevel().bind("<Button-1>",
                           lambda _e: _close_agent_popup(popup) if _agent_popup_ref[0] is popup else None,
                           add="+")
            popup.focus_set()

        if self.use_ctk:
            self._agent_file_btn = ctk.CTkButton(
                task_toolbar, text="＋", command=_open_agent_file_menu,
                fg_color=self.colors.get("bg_secondary", "#2a2a2a"),
                hover_color=self.colors.get("button_hover", "#3a3a3a"),
                text_color=self.colors.get("text_secondary", "#aaaaaa"),
                font=("Segoe UI", 16), corner_radius=6, width=36, height=28,
            )
        else:
            self._agent_file_btn = tk.Button(
                task_toolbar, text="＋", command=_open_agent_file_menu,
                bg=self.colors.get("bg_secondary", "#2a2a2a"),
                fg=self.colors.get("text_secondary", "#aaaaaa"),
                font=("Segoe UI", 16), relief="flat", bd=0, padx=6,
            )
        self._agent_file_btn.pack(side="left", padx=(2, 0))

        # Placeholder
        self._set_placeholder(
            "Décrivez la tâche à confier aux agents sélectionnés...\n"
        )

        # Frame pour les boutons (à droite, étiré pour s'aligner avec la zone de texte)
        buttons_frame = self.create_frame(
            input_frame, fg_color=self.colors["bg_primary"]
        )
        buttons_frame.grid(row=0, column=1, rowspan=3, sticky="nsew")

        # Bouton Exécuter
        if self.use_ctk:
            self.execute_btn = ctk.CTkButton(
                buttons_frame,
                text="▶ Exécuter",
                command=self.execute_agent_task,
                fg_color=self.colors["accent"],
                hover_color="#ff5730",
                text_color="#ffffff",
                font=("Segoe UI", 13, "bold"),
                corner_radius=8,
                width=160,
                border_width=0,
            )
        else:
            self.execute_btn = tk.Button(
                buttons_frame,
                text="▶ Exécuter",
                command=self.execute_agent_task,
                bg=self.colors["accent"],
                fg="#ffffff",
                font=("Segoe UI", 13, "bold"),
                border=0,
                relief="flat",
            )
        self.execute_btn.pack(fill="both", expand=True, pady=(0, 4))

        # Bouton Créer Agent (bleu, entre les deux)
        if self.use_ctk:
            create_agent_btn = ctk.CTkButton(
                buttons_frame,
                text="➕ Créer Agent",
                command=self._open_create_agent_dialog,
                fg_color="#3b82f6",
                hover_color="#2563eb",
                text_color="#ffffff",
                font=("Segoe UI", 13, "bold"),
                corner_radius=8,
                width=160,
            )
        else:
            create_agent_btn = tk.Button(
                buttons_frame,
                text="➕ Créer Agent",
                command=self._open_create_agent_dialog,
                bg="#3b82f6",
                fg="#ffffff",
                font=("Segoe UI", 13, "bold"),
                border=0,
                relief="flat",
            )
        create_agent_btn.pack(fill="both", expand=True, pady=4)

        # Bouton Mode Débat (violet)
        if self.use_ctk:
            debate_btn = ctk.CTkButton(
                buttons_frame,
                text="🎭 Mode Débat",
                command=self._open_debate_dialog,
                fg_color="#8b5cf6",
                hover_color="#7c3aed",
                text_color="#ffffff",
                font=("Segoe UI", 13, "bold"),
                corner_radius=8,
                width=160,
            )
        else:
            debate_btn = tk.Button(
                buttons_frame,
                text="🎭 Mode Débat",
                command=self._open_debate_dialog,
                bg="#8b5cf6",
                fg="#ffffff",
                font=("Segoe UI", 13, "bold"),
                border=0,
                relief="flat",
            )
        debate_btn.pack(fill="both", expand=True, pady=4)

        # Bouton Clear Workflow (rouge)
        if self.use_ctk:
            clear_btn = ctk.CTkButton(
                buttons_frame,
                text="❌ Clear Workflow",
                command=self.clear_workflow,
                fg_color="#dc2626",
                hover_color="#b91c1c",
                text_color="#ffffff",
                font=("Segoe UI", 13, "bold"),
                corner_radius=8,
                width=160,
            )
        else:
            clear_btn = tk.Button(
                buttons_frame,
                text="❌ Clear Workflow",
                command=self.clear_workflow,
                bg="#dc2626",
                fg="#ffffff",
                font=("Segoe UI", 13, "bold"),
                border=0,
                relief="flat",
            )
        clear_btn.pack(fill="both", expand=True, pady=(4, 0))

        # drop_zone_frame / pipeline_frame conservés comme attributs vides
        # pour compatibilité — le canvas visuel remplace l'ancienne zone de drop
        self.drop_zone_frame = None
        self.pipeline_frame = None

        # ── Canvas de workflow visuel (style n8n) ──────────────────
        self.canvas_outer = self.create_frame(
            section_frame, fg_color=self.colors["bg_secondary"]
        )
        canvas_outer = self.canvas_outer
        if self.use_ctk:
            canvas_outer.configure(
                corner_radius=10, border_width=2,
                border_color=self.colors["border"],
            )
        canvas_outer.pack(fill="both", expand=True, pady=(10, 0))

        # ── Barre de titre + boutons workflow ──
        canvas_header = self.create_frame(
            canvas_outer, fg_color=self.colors["bg_secondary"]
        )
        canvas_header.pack(fill="x", padx=12, pady=(8, 0))

        canvas_title = self.create_label(
            canvas_header,
            text="🔗 Workflow Visuel — glissez des agents, connectez les ports",
            font=("Segoe UI", 10),
            text_color=self.colors["text_secondary"],
            fg_color=self.colors["bg_secondary"],
        )
        canvas_title.pack(side="left")

        # Boutons Save / Load / Export
        wf_btn_style = {
            "font": ("Segoe UI", 10),
            "corner_radius": 4,
            "width": 70,
            "height": 24,
        } if self.use_ctk else {}

        def _make_wf_btn(parent, text, cmd):
            if self.use_ctk:
                return ctk.CTkButton(
                    parent, text=text, command=cmd,
                    fg_color=self.colors.get("bg_primary", "#1a1a1a"),
                    hover_color=self.colors.get("button_hover", "#3a3a3a"),
                    text_color=self.colors.get("text_secondary", "#aaaaaa"),
                    **wf_btn_style,
                )
            else:
                return tk.Button(
                    parent, text=text, command=cmd,
                    bg=self.colors.get("bg_primary", "#1a1a1a"),
                    fg=self.colors.get("text_secondary", "#aaaaaa"),
                    font=("Segoe UI", 10), relief="flat", bd=0,
                )

        export_btn = _make_wf_btn(canvas_header, "📤 Export", self._export_workflow)
        export_btn.pack(side="right", padx=(4, 0))
        load_btn = _make_wf_btn(canvas_header, "📂 Load", self._load_workflow)
        load_btn.pack(side="right", padx=(4, 0))
        save_btn = _make_wf_btn(canvas_header, "💾 Save", self._save_workflow)
        save_btn.pack(side="right", padx=(4, 0))

        self.workflow_canvas = WorkflowCanvas(
            canvas_outer,
            self.colors,
            width=800,
            height=380,
            on_workflow_changed=self._on_canvas_changed,
            snap_to_grid=True,
        )
        self.workflow_canvas.pack(fill="both", expand=True, padx=4, pady=4)

    def _set_placeholder(self, text):
        """Définit le placeholder de la zone de saisie"""
        if self.use_ctk:
            self.task_entry.insert("0.0", text)
            self.task_entry.configure(text_color=self.colors["placeholder"])

            def on_focus_in(_event):
                if self.task_entry.get("0.0", "end-1c") == text:
                    self.task_entry.delete("0.0", "end")
                    self.task_entry.configure(text_color=self.colors["text_primary"])

            def on_focus_out(_event):
                if not self.task_entry.get("0.0", "end-1c").strip():
                    self.task_entry.insert("0.0", text)
                    self.task_entry.configure(text_color=self.colors["placeholder"])

            self.task_entry.bind("<FocusIn>", on_focus_in)
            self.task_entry.bind("<FocusOut>", on_focus_out)
            self.task_entry.bind("<Control-v>", self._on_agent_paste)

    def _on_agent_paste(self, _event=None):
        """Gère le collage d'image depuis le presse-papier dans la page agents."""
        try:
            import tempfile  # pylint: disable=import-outside-toplevel
        except ImportError:
            return None  # Pas de Pillow, laisser le comportement par défaut (texte)

        try:
            img = ImageGrab.grabclipboard()
            if img is not None and isinstance(img, Image.Image):
                print("🖼️ [AGENTS CLIPBOARD] Image détectée dans le presse-papier")
                temp_path = os.path.join(tempfile.gettempdir(), "clipboard_agent_image.png")
                img.save(temp_path, format="PNG")
                self._agent_add_preview(temp_path, "Image")
                return "break"

            if isinstance(img, list):
                for item in img:
                    if isinstance(item, str) and os.path.isfile(item):
                        ext = os.path.splitext(item)[1].lower()
                        if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
                            self._agent_add_preview(item, "Image")
                            return "break"
        except Exception as e:
            print(f"⚠️ [AGENTS CLIPBOARD] Erreur: {e}")

        return None  # Pas d'image → coller du texte normalement

    def _get_task_text(self):
        """Récupère le texte de la tâche"""
        if self.use_ctk:
            text = self.task_entry.get("0.0", "end-1c").strip()
        else:
            text = self.task_entry.get("1.0", "end-1c").strip()

        # Vérifier si c'est le placeholder
        if "Décrivez la tâche" in text:
            return ""

        return text
