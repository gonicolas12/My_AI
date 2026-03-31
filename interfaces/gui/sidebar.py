"""Sidebar mixin — panneau latéral gauche (Sessions, Historique, Export, Connaissances).

Le panneau est un overlay place() sur main_container, couvrant toute la hauteur
(header inclus). Il est fermé par défaut et s'ouvre via le bouton ☰ du header.

Chaque section utilise un wrapper frame permanent pour que le pack/unpack du
body ne réordonne pas les sections.
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    ctk = tk


_SIDEBAR_W = 260  # largeur en pixels


class SidebarMixin:
    """Panneau latéral gauche avec Sessions, Historique, Export et Connaissances."""

    # ─── Création principale ────────────────────────────────────────────

    def create_left_sidebar(self, parent):
        """Crée le panneau latéral.

        parent doit être main_container (ou self.root) afin que place() couvre
        toute la hauteur de la fenêtre, header inclus.
        """
        self._sidebar_parent = parent
        self._sidebar_visible = False
        self._sidebar_sections_open = {
            "sessions": True,
            "history": False,
            "export": True,
            "knowledge": False,
        }

        bg = self.colors.get("bg_secondary", "#2f2f2f")

        # ── Frame principale — col 0 de main_container, rowspan header+contenu ──
        if CTK_AVAILABLE:
            self._sidebar_frame = ctk.CTkFrame(
                parent,
                width=_SIDEBAR_W,
                fg_color=bg,
                corner_radius=0,
            )
        else:
            self._sidebar_frame = tk.Frame(parent, width=_SIDEBAR_W, bg=bg)

        # Positionner dans la grille mais masquer immédiatement (grid_remove retient les options)
        self._sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self._sidebar_frame.grid_remove()

        # ── Scrollable interne ────────────────────────────────────────────
        if CTK_AVAILABLE:
            self._sidebar_scroll = ctk.CTkScrollableFrame(
                self._sidebar_frame,
                fg_color=bg,
                corner_radius=0,
            )
        else:
            self._sidebar_scroll = tk.Frame(self._sidebar_frame, bg=bg)
        self._sidebar_scroll.pack(fill="both", expand=True)

        # ── Contenu ───────────────────────────────────────────────────────
        self._make_sidebar_title()
        self._make_section_sessions()
        self._make_section_history()
        self._make_section_export()
        self._make_section_knowledge()

    # ─── Toggle ──────────────────────────────────────────────────────────

    def toggle_sidebar(self):
        """Affiche ou masque le panneau latéral (grid col 0 de main_container)."""
        if not hasattr(self, "_sidebar_frame"):
            return
        if self._sidebar_visible:
            self._sidebar_frame.grid_remove()
            self._sidebar_visible = False
            # Remontre le bouton ☰ du header
            btn = getattr(self, "_sidebar_toggle_btn", None)
            if btn:
                try:
                    btn.grid()
                except Exception:
                    pass
        else:
            self._sidebar_frame.grid()   # restaure row=0, col=0, rowspan=2 mémorisés
            self._sidebar_visible = True
            self._refresh_sidebar()
            # Cache le bouton ☰ du header (la sidebar a le sien)
            btn = getattr(self, "_sidebar_toggle_btn", None)
            if btn:
                try:
                    btn.grid_remove()
                except Exception:
                    pass

    # ─── Helpers widgets ─────────────────────────────────────────────────

    def _sb_label(self, parent, text, font_size=12, bold=False, color=None):
        c = color or self.colors.get("text_primary", "#ffffff")
        font = ("Segoe UI", font_size, "bold" if bold else "normal")
        bg = self.colors.get("bg_secondary", "#2f2f2f")
        if CTK_AVAILABLE:
            return ctk.CTkLabel(
                parent, text=text, font=font, text_color=c, fg_color="transparent"
            )
        return tk.Label(parent, text=text, font=font, fg=c, bg=bg)

    def _sb_button(self, parent, text, command, color=None, width=None):
        bg = color or self.colors.get("bg_primary", "#212121")
        hover = self.colors.get("button_hover", "#404040")
        tc = self.colors.get("text_primary", "#ffffff")
        if CTK_AVAILABLE:
            kw = dict(
                text=text, command=command,
                fg_color=bg, hover_color=hover, text_color=tc,
                font=("Segoe UI", 11), height=30, corner_radius=5,
            )
            if width:
                kw["width"] = width
            return ctk.CTkButton(parent, **kw)
        return tk.Button(parent, text=text, command=command,
                         bg=bg, fg=tc, font=("Segoe UI", 11), relief="flat")

    def _sb_separator(self, parent):
        bg = self.colors.get("border", "#404040")
        f = ctk.CTkFrame(parent, height=1, fg_color=bg, corner_radius=0) if CTK_AVAILABLE \
            else tk.Frame(parent, height=1, bg=bg)
        f.pack(fill="x", padx=8, pady=(4, 2))

    # ─── Titre + bouton fermer ─────────────────────────────────────────

    def _make_sidebar_title(self):
        bg = self.colors.get("bg_secondary", "#2f2f2f")
        frame = ctk.CTkFrame(self._sidebar_scroll, fg_color=bg, corner_radius=0) \
            if CTK_AVAILABLE else tk.Frame(self._sidebar_scroll, bg=bg)
        frame.pack(fill="x", padx=6, pady=(10, 4))

        lbl = self._sb_label(frame, "My_AI", font_size=14, bold=True,
                              color=self.colors.get("accent", "#3b82f6"))
        lbl.pack(side="left", padx=6)

        # Bouton ☰ pour refermer la sidebar
        close_bg = self.colors.get("bg_primary", "#212121")
        if CTK_AVAILABLE:
            close_btn = ctk.CTkButton(
                frame, text="☰", width=34, height=30,
                fg_color=close_bg,
                hover_color=self.colors.get("button_hover", "#404040"),
                text_color=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 14), corner_radius=5,
                command=self.toggle_sidebar,
            )
        else:
            close_btn = tk.Button(
                frame, text="☰", bg=close_bg,
                fg=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 14), relief="flat",
                command=self.toggle_sidebar,
            )
        close_btn.pack(side="right", padx=4)

    # ─── Section helpers ──────────────────────────────────────────────

    def _make_section_wrapper(self):
        """Crée un frame wrapper permanent pour une section."""
        bg = self.colors.get("bg_secondary", "#2f2f2f")
        w = ctk.CTkFrame(self._sidebar_scroll, fg_color=bg, corner_radius=0) \
            if CTK_AVAILABLE else tk.Frame(self._sidebar_scroll, bg=bg)
        w.pack(fill="x")
        return w

    def _make_section_header_btn(self, wrapper, title, key):
        """Bouton d'en-tête expand/collapse, placé dans wrapper."""
        open_ = self._sidebar_sections_open.get(key, True)
        icon = "▼" if open_ else "▶"
        bg = self.colors.get("bg_secondary", "#2f2f2f")
        hover = self.colors.get("button_hover", "#404040")
        tc = self.colors.get("text_secondary", "#9ca3af")
        label = f"  {icon} {title}"
        if CTK_AVAILABLE:
            btn = ctk.CTkButton(
                wrapper, text=label,
                command=lambda k=key: self._toggle_section(k),
                fg_color=bg, hover_color=hover, text_color=tc,
                font=("Segoe UI", 11, "bold"),
                height=28, corner_radius=0, anchor="w",
                width=_SIDEBAR_W,
            )
        else:
            btn = tk.Button(
                wrapper, text=label,
                command=lambda k=key: self._toggle_section(k),
                bg=bg, fg=tc, font=("Segoe UI", 11, "bold"),
                relief="flat", anchor="w",
            )
        btn.pack(fill="x")
        return btn

    def _toggle_section(self, key):
        """Expand/collapse une section. Le body est pack/unpack DANS son wrapper."""
        self._sidebar_sections_open[key] = not self._sidebar_sections_open.get(key, True)
        open_ = self._sidebar_sections_open[key]
        icon = "▼" if open_ else "▶"
        names = {
            "sessions": "💼 Sessions",
            "history": "📜 Historique",
            "export": "📤 Export",
            "knowledge": "🧠 Connaissances",
        }
        hdr = getattr(self, f"_sidebar_hdr_{key}", None)
        if hdr:
            try:
                hdr.configure(text=f"  {icon} {names.get(key, key)}")
            except Exception:
                pass
        body = getattr(self, f"_sidebar_body_{key}", None)
        if body:
            if open_:
                body.pack(fill="x", padx=4, pady=(0, 4))
            else:
                body.pack_forget()

    def _refresh_sidebar(self):
        self._refresh_sessions()
        self._refresh_history()
        self._refresh_knowledge()

    # ─── Section Sessions ─────────────────────────────────────────────

    def _make_section_sessions(self):
        wrapper = self._make_section_wrapper()
        self._sidebar_hdr_sessions = self._make_section_header_btn(
            wrapper, "💼 Sessions", "sessions"
        )
        bg = self.colors.get("bg_secondary", "#2f2f2f")
        body = ctk.CTkFrame(wrapper, fg_color=bg, corner_radius=0) \
            if CTK_AVAILABLE else tk.Frame(wrapper, bg=bg)
        self._sidebar_body_sessions = body

        btn_new = self._sb_button(body, "➕ Nouvelle session", self._session_new,
                                   width=_SIDEBAR_W - 20)
        btn_new.pack(fill="x", padx=8, pady=(4, 2))

        list_bg = self.colors.get("bg_primary", "#212121")
        self._sessions_list_frame = ctk.CTkFrame(body, fg_color=list_bg, corner_radius=4) \
            if CTK_AVAILABLE else tk.Frame(body, bg=list_bg)
        self._sessions_list_frame.pack(fill="x", padx=8, pady=(0, 4))

        if self._sidebar_sections_open["sessions"]:
            body.pack(fill="x", padx=4, pady=(0, 4))
        self._sb_separator(self._sidebar_scroll)

    def _refresh_sessions(self):
        for w in self._sessions_list_frame.winfo_children():
            w.destroy()
        engine = getattr(self, "ai_engine", None)
        sm = getattr(engine, "session_manager", None) if engine else None
        if sm is None:
            self._sb_label(self._sessions_list_frame, "  (aucun gestionnaire)",
                           font_size=10, color=self.colors.get("text_secondary", "#9ca3af")
                           ).pack(anchor="w", padx=4, pady=2)
            return
        try:
            workspaces = sm.list_workspaces()
        except Exception:
            workspaces = []
        if not workspaces:
            self._sb_label(self._sessions_list_frame, "  Aucune session",
                           font_size=10, color=self.colors.get("text_secondary", "#9ca3af")
                           ).pack(anchor="w", padx=4, pady=2)
            return
        try:
            current_id = sm.get_current_workspace()
        except Exception:
            current_id = None
        for ws in workspaces[:15]:
            ws_id = ws.get("id", "")
            ws_name = ws.get("name", ws_id)
            is_cur = ws_id == current_id
            color = self.colors.get("accent", "#3b82f6") if is_cur \
                else self.colors.get("text_primary", "#ffffff")
            icon = "▶ " if is_cur else "   "
            row_bg = self.colors.get("bg_primary", "#212121")
            row = ctk.CTkFrame(self._sessions_list_frame, fg_color=row_bg, corner_radius=3) \
                if CTK_AVAILABLE else tk.Frame(self._sessions_list_frame, bg=row_bg)
            row.pack(fill="x", pady=1)
            self._sb_label(row, f"{icon}{ws_name[:22]}", font_size=10, color=color
                           ).pack(side="left", padx=(4, 2), pady=1, fill="x", expand=True)
            load_btn = self._sb_button(row, "↩", lambda wid=ws_id: self._session_load(wid),
                                        width=28)
            if CTK_AVAILABLE:
                load_btn.configure(height=22)
            load_btn.pack(side="right", padx=(0, 2), pady=1)
            del_btn = self._sb_button(row, "🗑", lambda wid=ws_id: self._session_delete(wid),
                                       color="#ef4444", width=28)
            if CTK_AVAILABLE:
                del_btn.configure(height=22)
            del_btn.pack(side="right", padx=(0, 2), pady=1)

    def _session_new(self):
        name = simpledialog.askstring("Nouvelle session", "Nom de la session :",
                                       parent=self.root)
        if not name or not name.strip():
            return
        engine = getattr(self, "ai_engine", None)
        sm = getattr(engine, "session_manager", None) if engine else None
        if not sm:
            return
        try:
            ws_id = sm.create_workspace(name.strip())
            state = {"history": getattr(self, "conversation_history", []),
                     "name": name.strip()}
            sm.save_workspace(ws_id, state)
            self._refresh_sessions()
            self.show_notification(f"✅ Session '{name}' créée", "success", 2000)
        except Exception as exc:
            self.show_notification(f"❌ Erreur : {exc}", "error", 2500)

    def _session_load(self, workspace_id: str):
        engine = getattr(self, "ai_engine", None)
        sm = getattr(engine, "session_manager", None) if engine else None
        if not sm:
            return
        try:
            state = sm.load_workspace(workspace_id)
            if state is None:
                self.show_notification("❌ Session introuvable", "error", 2000)
                return
            history = state.get("history", [])
            if not messagebox.askyesno(
                "Charger la session",
                f"Charger '{state.get('name', workspace_id)}' ?\n"
                "La conversation actuelle sera remplacée.",
                parent=self.root,
            ):
                return
            self.conversation_history = list(history)
            if hasattr(engine, "conversation_manager"):
                engine.conversation_manager.clear()
            sm.set_current_workspace(workspace_id)
            self.clear_chat()
            for msg in history:
                role = msg.get("role", "user" if msg.get("is_user", True) else "assistant")
                content = msg.get("content", msg.get("text", ""))
                if role == "user" and hasattr(self, "add_user_message_bubble"):
                    self.add_user_message_bubble(content)
                elif role in ("assistant", "ai") and hasattr(self, "add_ai_message_bubble"):
                    self.add_ai_message_bubble(content)
            self.show_notification(
                "✅ Session chargée", "success", 2000
            )
            self._refresh_sessions()
        except Exception as exc:
            self.show_notification(f"❌ Erreur chargement : {exc}", "error", 2500)

    def _session_delete(self, workspace_id: str):
        engine = getattr(self, "ai_engine", None)
        sm = getattr(engine, "session_manager", None) if engine else None
        if not sm:
            return
        try:
            workspaces = sm.list_workspaces()
            name = next((w.get("name", workspace_id) for w in workspaces
                         if w.get("id") == workspace_id), workspace_id)
            if messagebox.askyesno("Supprimer", f"Supprimer '{name}' ?", parent=self.root):
                sm.delete_workspace(workspace_id)
                self._refresh_sessions()
                self.show_notification("🗑️ Session supprimée", "success", 2000)
        except Exception as exc:
            self.show_notification(f"❌ Erreur : {exc}", "error", 2500)

    # ─── Section Historique ────────────────────────────────────────────

    def _make_section_history(self):
        wrapper = self._make_section_wrapper()
        self._sidebar_hdr_history = self._make_section_header_btn(
            wrapper, "📜 Historique", "history"
        )
        bg = self.colors.get("bg_secondary", "#2f2f2f")
        body = ctk.CTkFrame(wrapper, fg_color=bg, corner_radius=0) \
            if CTK_AVAILABLE else tk.Frame(wrapper, bg=bg)
        self._sidebar_body_history = body

        # Barre de recherche
        search_bg = self.colors.get("bg_primary", "#212121")
        sr = ctk.CTkFrame(body, fg_color=search_bg, corner_radius=4) \
            if CTK_AVAILABLE else tk.Frame(body, bg=search_bg)
        sr.pack(fill="x", padx=8, pady=(4, 2))

        self._history_search_var = tk.StringVar()
        self._history_search_var.trace_add("write", lambda *_: self._refresh_history())
        if CTK_AVAILABLE:
            ctk.CTkEntry(
                sr, textvariable=self._history_search_var,
                placeholder_text="🔍 Rechercher...",
                fg_color=search_bg,
                border_color=self.colors.get("border", "#404040"),
                text_color=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 10), height=26,
            ).pack(fill="x", padx=4, pady=3)
        else:
            tk.Entry(
                sr, textvariable=self._history_search_var,
                bg=search_bg, fg=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 10), relief="flat",
            ).pack(fill="x", padx=4, pady=3)

        # Filtre favoris
        self._history_favs_only = tk.BooleanVar(value=False)
        if CTK_AVAILABLE:
            ctk.CTkCheckBox(
                body, text="⭐ Favoris uniquement",
                variable=self._history_favs_only,
                command=self._refresh_history,
                font=("Segoe UI", 10),
                text_color=self.colors.get("text_secondary", "#9ca3af"),
                fg_color=self.colors.get("accent", "#3b82f6"),
                hover_color=self.colors.get("accent_hover", "#2563eb"),
                checkmark_color="#ffffff", height=24,
            ).pack(anchor="w", padx=12, pady=(2, 4))
        else:
            tk.Checkbutton(
                body, text="⭐ Favoris uniquement",
                variable=self._history_favs_only,
                command=self._refresh_history,
                bg=bg, fg=self.colors.get("text_secondary", "#9ca3af"),
                selectcolor=bg, font=("Segoe UI", 10),
            ).pack(anchor="w", padx=12, pady=(2, 4))

        list_bg = self.colors.get("bg_primary", "#212121")
        if CTK_AVAILABLE:
            self._history_list_frame = ctk.CTkScrollableFrame(
                body, fg_color=list_bg, corner_radius=4, height=150
            )
        else:
            self._history_list_frame = tk.Frame(body, bg=list_bg, height=150)
        self._history_list_frame.pack(fill="x", padx=8, pady=(0, 4))

        if self._sidebar_sections_open.get("history", False):
            body.pack(fill="x", padx=4, pady=(0, 4))
        self._sb_separator(self._sidebar_scroll)

    def _refresh_history(self):
        for w in self._history_list_frame.winfo_children():
            w.destroy()
        engine = getattr(self, "ai_engine", None)
        ch = getattr(engine, "command_history", None) if engine else None
        if ch is None:
            self._sb_label(self._history_list_frame, "  (aucun historique)",
                           font_size=10, color=self.colors.get("text_secondary", "#9ca3af")
                           ).pack(anchor="w", padx=4, pady=2)
            return
        query = getattr(self, "_history_search_var", tk.StringVar()).get().strip()
        favs = getattr(self, "_history_favs_only", tk.BooleanVar()).get()
        try:
            if favs:
                entries = ch.get_favorites()
            elif query:
                entries = ch.search(query, limit=20)
            else:
                entries = ch.get_recent(limit=20)
        except Exception:
            entries = []
        if not entries:
            self._sb_label(self._history_list_frame, "  Aucun résultat",
                           font_size=10, color=self.colors.get("text_secondary", "#9ca3af")
                           ).pack(anchor="w", padx=4, pady=2)
            return
        for entry in entries:
            self._make_history_entry(entry)

    def _make_history_entry(self, entry: dict):
        eid = entry.get("id")
        text = entry.get("query", "")[:50]
        is_fav = bool(entry.get("is_favorite", False))
        star = "⭐" if is_fav else "☆"
        row_bg = self.colors.get("bg_primary", "#212121")
        hover = self.colors.get("button_hover", "#404040")
        row = ctk.CTkFrame(self._history_list_frame, fg_color=row_bg, corner_radius=3) \
            if CTK_AVAILABLE else tk.Frame(self._history_list_frame, bg=row_bg)
        row.pack(fill="x", pady=1, padx=2)
        # Bouton favori
        fav_tc = "#f59e0b" if is_fav else self.colors.get("text_secondary", "#9ca3af")
        if CTK_AVAILABLE:
            ctk.CTkButton(
                row, text=star, width=24, height=22,
                fg_color=row_bg, hover_color=hover, text_color=fav_tc,
                font=("Segoe UI", 10), corner_radius=3,
                command=lambda eid_=eid: self._history_toggle_fav(eid_),
            ).pack(side="left", padx=(2, 0))
            ctk.CTkButton(
                row, text=text,
                fg_color=row_bg, hover_color=hover,
                text_color=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 10), height=22, corner_radius=3, anchor="w",
                command=lambda t=entry.get("query", ""): self._history_reuse(t),
            ).pack(side="left", fill="x", expand=True, padx=2)
        else:
            tk.Button(
                row, text=star, bg=row_bg, fg=fav_tc,
                font=("Segoe UI", 10), relief="flat",
                command=lambda eid_=eid: self._history_toggle_fav(eid_),
            ).pack(side="left", padx=(2, 0))
            tk.Button(
                row, text=text, bg=row_bg,
                fg=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 10), relief="flat", anchor="w",
                command=lambda t=entry.get("query", ""): self._history_reuse(t),
            ).pack(side="left", fill="x", expand=True, padx=2)

    def _history_toggle_fav(self, entry_id):
        engine = getattr(self, "ai_engine", None)
        ch = getattr(engine, "command_history", None) if engine else None
        if ch:
            try:
                ch.toggle_favorite(entry_id)
                self._refresh_history()
            except Exception:
                pass

    def _history_reuse(self, text: str):
        if not hasattr(self, "input_text") or self.input_text is None:
            return
        try:
            if getattr(self, "placeholder_active", False):
                self.input_text.delete("1.0", "end")
                self.placeholder_active = False
                try:
                    self.input_text.configure(
                        text_color=self.colors.get("text_primary", "#ffffff")
                    )
                except Exception:
                    pass
            else:
                self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", text)
            self.input_text.focus_set()
        except Exception:
            pass

    # ─── Section Export ────────────────────────────────────────────────

    def _make_section_export(self):
        wrapper = self._make_section_wrapper()
        self._sidebar_hdr_export = self._make_section_header_btn(
            wrapper, "📤 Export", "export"
        )
        bg = self.colors.get("bg_secondary", "#2f2f2f")
        body = ctk.CTkFrame(wrapper, fg_color=bg, corner_radius=0) \
            if CTK_AVAILABLE else tk.Frame(wrapper, bg=bg)
        self._sidebar_body_export = body

        for label, fmt in [
            ("📝 Markdown (.md)", "markdown"),
            ("🌐 HTML (.html)", "html"),
            ("📄 PDF (.pdf)", "pdf"),
        ]:
            btn = self._sb_button(body, label, lambda f=fmt: self._export_conversation(f),
                                   width=_SIDEBAR_W - 20)
            btn.pack(fill="x", padx=8, pady=2)

        if self._sidebar_sections_open.get("export", True):
            body.pack(fill="x", padx=4, pady=(0, 4))
        self._sb_separator(self._sidebar_scroll)

    def _export_conversation(self, fmt: str):
        engine = getattr(self, "ai_engine", None)
        exporter = getattr(engine, "conversation_exporter", None) if engine else None
        if exporter is None:
            messagebox.showwarning(
                "Export indisponible",
                "Le module d'export n'est pas disponible.\n"
                "(ReportLab requis pour PDF)",
                parent=self.root,
            )
            return

        raw_messages = getattr(self, "conversation_history", [])
        if not raw_messages:
            self.show_notification("⚠️ Aucune conversation à exporter", "info", 2000)
            return

        ext_map = {"markdown": ".md", "html": ".html", "pdf": ".pdf"}
        ft_map = {
            "markdown": [("Markdown", "*.md"), ("Tous", "*.*")],
            "html": [("HTML", "*.html"), ("Tous", "*.*")],
            "pdf": [("PDF", "*.pdf"), ("Tous", "*.*")],
        }
        filepath = filedialog.asksaveasfilename(
            title="Exporter la conversation",
            defaultextension=ext_map[fmt],
            filetypes=ft_map[fmt],
            initialfile=f"conversation{ext_map[fmt]}",
            parent=self.root,
        )
        if not filepath:
            return

        # Convertir conversation_history (text/is_user) → format exporter (role/content)
        export_msgs = []
        for msg in raw_messages:
            # Filtrer les placeholders et entrées vides
            if msg.get("type") == "file_generation_placeholder":
                continue
            content = msg.get("text", msg.get("content", "")).strip()
            if not content:
                continue
            is_user = msg.get("is_user", True)
            role = "user" if is_user else "assistant"
            export_msgs.append({"role": role, "content": content})

        if not export_msgs:
            self.show_notification("⚠️ Aucun message à exporter", "info", 2000)
            return

        def _do_export():
            try:
                out_dir = os.path.dirname(filepath)
                fname = os.path.splitext(os.path.basename(filepath))[0]
                exporter.output_dir = Path(out_dir)
                exporter.export(
                    messages=export_msgs,
                    output_format=fmt,
                    filename=fname,
                )
                self.root.after(0, lambda: self.show_notification(
                    f"✅ Exporté en {fmt.upper()}", "success", 2500
                ))
            except Exception as exc:
                self.root.after(0, lambda: self.show_notification(
                    f"❌ Erreur export : {exc}", "error", 3000
                ))

        threading.Thread(target=_do_export, daemon=True).start()

    # ─── Section Connaissances ─────────────────────────────────────────

    def _make_section_knowledge(self):
        wrapper = self._make_section_wrapper()
        self._sidebar_hdr_knowledge = self._make_section_header_btn(
            wrapper, "🧠 Connaissances", "knowledge"
        )
        bg = self.colors.get("bg_secondary", "#2f2f2f")
        body = ctk.CTkFrame(wrapper, fg_color=bg, corner_radius=0) \
            if CTK_AVAILABLE else tk.Frame(wrapper, bg=bg)
        self._sidebar_body_knowledge = body

        # Barre de recherche
        search_bg = self.colors.get("bg_primary", "#212121")
        sr = ctk.CTkFrame(body, fg_color=search_bg, corner_radius=4) \
            if CTK_AVAILABLE else tk.Frame(body, bg=search_bg)
        sr.pack(fill="x", padx=8, pady=(4, 2))

        self._kb_search_var = tk.StringVar()
        self._kb_search_var.trace_add("write", lambda *_: self._refresh_knowledge())
        if CTK_AVAILABLE:
            ctk.CTkEntry(
                sr, textvariable=self._kb_search_var,
                placeholder_text="🔍 Rechercher un fait...",
                fg_color=search_bg,
                border_color=self.colors.get("border", "#404040"),
                text_color=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 10), height=26,
            ).pack(fill="x", padx=4, pady=3)
        else:
            tk.Entry(
                sr, textvariable=self._kb_search_var,
                bg=search_bg, fg=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 10), relief="flat",
            ).pack(fill="x", padx=4, pady=3)

        btn_add = self._sb_button(body, "➕ Ajouter un fait", self._kb_add_fact,
                                   width=_SIDEBAR_W - 20)
        btn_add.pack(fill="x", padx=8, pady=(0, 4))

        list_bg = self.colors.get("bg_primary", "#212121")
        if CTK_AVAILABLE:
            self._kb_list_frame = ctk.CTkScrollableFrame(
                body, fg_color=list_bg, corner_radius=4, height=160
            )
        else:
            self._kb_list_frame = tk.Frame(body, bg=list_bg, height=160)
        self._kb_list_frame.pack(fill="x", padx=8, pady=(0, 4))

        if self._sidebar_sections_open.get("knowledge", False):
            body.pack(fill="x", padx=4, pady=(0, 4))
        self._sb_separator(self._sidebar_scroll)

    def _refresh_knowledge(self):
        for w in self._kb_list_frame.winfo_children():
            w.destroy()
        engine = getattr(self, "ai_engine", None)
        kb = getattr(engine, "knowledge_base", None) if engine else None
        if kb is None:
            self._sb_label(self._kb_list_frame, "  (base indisponible)",
                           font_size=10, color=self.colors.get("text_secondary", "#9ca3af")
                           ).pack(anchor="w", padx=4, pady=2)
            return
        query = getattr(self, "_kb_search_var", tk.StringVar()).get().strip()
        try:
            facts = kb.search_facts(query, limit=20) if query else kb.get_all_facts()[:20]
        except Exception:
            facts = []
        if not facts:
            self._sb_label(self._kb_list_frame, "  Aucun fait enregistré",
                           font_size=10, color=self.colors.get("text_secondary", "#9ca3af")
                           ).pack(anchor="w", padx=4, pady=2)
            return
        for fact in facts:
            self._make_kb_fact_row(fact)

    def _make_kb_fact_row(self, fact: dict):
        fact_id = fact.get("id")
        content = fact.get("content", "")[:45]
        category = fact.get("category", "")
        cat_colors = {
            "preference": "#8b5cf6", "decision": "#f59e0b",
            "person": "#10b981", "procedure": "#3b82f6",
            "technical": "#ef4444", "general": "#9ca3af",
        }
        cat_color = cat_colors.get(category, "#9ca3af")
        row_bg = self.colors.get("bg_primary", "#212121")
        row = ctk.CTkFrame(self._kb_list_frame, fg_color=row_bg, corner_radius=3) \
            if CTK_AVAILABLE else tk.Frame(self._kb_list_frame, bg=row_bg)
        row.pack(fill="x", pady=1, padx=2)
        self._sb_label(row, category[:8], font_size=9, color=cat_color
                       ).pack(side="left", padx=(3, 2))
        self._sb_label(row, content, font_size=10,
                       color=self.colors.get("text_primary", "#ffffff")
                       ).pack(side="left", fill="x", expand=True, padx=2)
        if CTK_AVAILABLE:
            ctk.CTkButton(
                row, text="✕", width=22, height=20,
                fg_color="#ef4444", hover_color="#dc2626",
                text_color="#ffffff", font=("Segoe UI", 9), corner_radius=3,
                command=lambda fid=fact_id: self._kb_delete_fact(fid),
            ).pack(side="right", padx=(0, 2), pady=1)
        else:
            tk.Button(
                row, text="✕", bg="#ef4444", fg="#ffffff",
                font=("Segoe UI", 9), relief="flat",
                command=lambda fid=fact_id: self._kb_delete_fact(fid),
            ).pack(side="right", padx=(0, 2), pady=1)

    def _kb_add_fact(self):
        engine = getattr(self, "ai_engine", None)
        kb = getattr(engine, "knowledge_base", None) if engine else None
        if kb is None:
            messagebox.showwarning("Indisponible",
                                   "La base de connaissances n'est pas disponible.",
                                   parent=self.root)
            return
        categories = ["general", "preference", "decision", "person", "procedure", "technical"]
        cat = simpledialog.askstring(
            "Catégorie", f"Catégorie ({', '.join(categories)}) :",
            initialvalue="general", parent=self.root,
        )
        if not cat or cat.strip() not in categories:
            cat = "general"
        content = simpledialog.askstring("Nouveau fait", "Contenu :", parent=self.root)
        if not content or not content.strip():
            return
        try:
            kb.add_fact(category=cat.strip(), content=content.strip())
            self._refresh_knowledge()
            self.show_notification("✅ Fait ajouté", "success", 2000)
        except Exception as exc:
            self.show_notification(f"❌ Erreur : {exc}", "error", 2500)

    def _kb_delete_fact(self, fact_id):
        engine = getattr(self, "ai_engine", None)
        kb = getattr(engine, "knowledge_base", None) if engine else None
        if kb:
            try:
                kb.delete_fact(fact_id)
                self._refresh_knowledge()
            except Exception as exc:
                self.show_notification(f"❌ Erreur : {exc}", "error", 2500)
