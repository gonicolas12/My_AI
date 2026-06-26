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
            "search": False,
            "sessions": False,
            "project_folders": False,
            "history": False,
            "export": False,
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
        self._make_relay_button()
        self._make_tts_button()
        self._make_settings_button()
        self._make_memory_button()
        self._make_prompts_button()
        self._make_section_search()
        self._make_section_sessions()
        self._make_section_project_folders()
        self._make_section_history()
        self._make_section_export()

    # ─── Bouton Relay ─────────────────────────────────────────────────

    def _make_relay_button(self):
        """Crée le bouton '📡 Relay' dans la sidebar (accès mobile)."""
        bg = self.colors.get("bg_secondary", "#2f2f2f")
        accent = self.colors.get("accent", "#ff6b47")
        hover = self.colors.get("accent_hover", "#e85a3a")
        tc = self.colors.get("text_primary", "#ffffff")

        wrapper = ctk.CTkFrame(self._sidebar_scroll, fg_color=bg, corner_radius=0) \
            if CTK_AVAILABLE else tk.Frame(self._sidebar_scroll, bg=bg)
        wrapper.pack(fill="x", padx=8, pady=(2, 6))

        cmd = getattr(self, "_toggle_relay", lambda: None)
        if CTK_AVAILABLE:
            btn = ctk.CTkButton(
                wrapper, text="📡 Relay",
                command=cmd,
                fg_color=accent, hover_color=hover, text_color=tc,
                font=("Segoe UI", 12, "bold"),
                height=32, corner_radius=6,
            )
            btn.pack(fill="x")
        else:
            btn = tk.Button(
                wrapper, text="📡 Relay", command=cmd,
                bg=accent, fg=tc, font=("Segoe UI", 12, "bold"),
                relief="flat",
            )
            btn.pack(fill="x")
        self._sidebar_relay_btn = btn

        self._sb_separator(self._sidebar_scroll)

    # ─── Bouton Lecture vocale auto (TTS) ─────────────────────────────────

    def _make_tts_button(self):
        """Toggle de lecture vocale automatique des réponses de l'IA (TTS)."""
        bg = self.colors.get("bg_secondary", "#2f2f2f")
        tc = self.colors.get("text_primary", "#ffffff")
        accent = self.colors.get("accent", "#ff6b47")
        inactive = self.colors.get("bg_tertiary", "#3a3a3a")

        if not hasattr(self, "tts_autoread"):
            try:
                from core.config import get_config
                self.tts_autoread = bool(get_config().get("ui.tts_autoread", False))
            except Exception:
                self.tts_autoread = False

        wrapper = ctk.CTkFrame(self._sidebar_scroll, fg_color=bg, corner_radius=0) \
            if CTK_AVAILABLE else tk.Frame(self._sidebar_scroll, bg=bg)
        wrapper.pack(fill="x", padx=8, pady=(2, 6))

        def _label():
            return "🔊 Lecture auto : ON" if self.tts_autoread else "🔇 Lecture auto : OFF"

        def _toggle():
            self.tts_autoread = not self.tts_autoread
            on = self.tts_autoread
            try:
                if CTK_AVAILABLE:
                    btn.configure(text=_label(), fg_color=accent if on else inactive)
                else:
                    btn.configure(text=_label(), bg=accent if on else inactive)
            except Exception:
                pass
            # Si on désactive en pleine lecture, stopper immédiatement
            if not on:
                try:
                    from interfaces.gui.voice_output import VoiceOutput
                    VoiceOutput.get_shared(self.root).stop()
                except Exception:
                    pass
            if hasattr(self, "show_notification"):
                self.show_notification(
                    "🔊 Lecture auto activée" if on else "🔇 Lecture auto désactivée",
                    "success" if on else "info", 1500,
                )

        if CTK_AVAILABLE:
            btn = ctk.CTkButton(
                wrapper, text=_label(), command=_toggle,
                fg_color=inactive, hover_color=accent, text_color=tc,
                font=("Segoe UI", 11), height=30, corner_radius=6,
            )
            btn.pack(fill="x")
        else:
            btn = tk.Button(
                wrapper, text=_label(), command=_toggle,
                bg=inactive, fg=tc, font=("Segoe UI", 11), relief="flat",
            )
            btn.pack(fill="x")
        self._sidebar_tts_btn = btn

        self._sb_separator(self._sidebar_scroll)

    # ─── Bouton Réglages (⚙️) ─────────────────────────────────────────────

    def _make_settings_button(self):
        """Crée le bouton '⚙️ Réglages' ouvrant le panneau de configuration."""
        bg = self.colors.get("bg_secondary", "#2f2f2f")
        accent = self.colors.get("accent", "#ff6b47")
        hover = self.colors.get("accent_hover", "#e85a3a")
        tc = self.colors.get("text_primary", "#ffffff")

        wrapper = ctk.CTkFrame(self._sidebar_scroll, fg_color=bg, corner_radius=0) \
            if CTK_AVAILABLE else tk.Frame(self._sidebar_scroll, bg=bg)
        wrapper.pack(fill="x", padx=8, pady=(2, 6))

        cmd = getattr(self, "open_settings_window", lambda: None)
        if CTK_AVAILABLE:
            btn = ctk.CTkButton(
                wrapper, text="⚙️ Réglages", command=cmd,
                fg_color=accent, hover_color=hover, text_color=tc,
                font=("Segoe UI", 12, "bold"),
                height=32, corner_radius=6,
            )
            btn.pack(fill="x")
        else:
            btn = tk.Button(
                wrapper, text="⚙️ Réglages", command=cmd,
                bg=accent, fg=tc, font=("Segoe UI", 12, "bold"),
                relief="flat",
            )
            btn.pack(fill="x")
        self._sidebar_settings_btn = btn

        self._sb_separator(self._sidebar_scroll)

    # ─── Bouton Mémoire (🧠) ──────────────────────────────────────────────

    def _make_memory_button(self):
        """Crée le bouton '🧠 Mémoire' ouvrant la fenêtre de gestion de la mémoire.

        Remplace l'ancienne section « Connaissances » : la fenêtre Mémoire couvre
        les faits ET les entrées vectorielles (documents + conversations) avec
        édition, pagination et suppression confirmée.
        """
        bg = self.colors.get("bg_secondary", "#2f2f2f")
        accent = self.colors.get("accent", "#ff6b47")
        hover = self.colors.get("accent_hover", "#e85a3a")
        tc = self.colors.get("text_primary", "#ffffff")

        wrapper = ctk.CTkFrame(self._sidebar_scroll, fg_color=bg, corner_radius=0) \
            if CTK_AVAILABLE else tk.Frame(self._sidebar_scroll, bg=bg)
        wrapper.pack(fill="x", padx=8, pady=(2, 6))

        cmd = getattr(self, "open_memory_window", lambda: None)
        if CTK_AVAILABLE:
            btn = ctk.CTkButton(
                wrapper, text="🧠 Mémoire", command=cmd,
                fg_color=accent, hover_color=hover, text_color=tc,
                font=("Segoe UI", 12, "bold"),
                height=32, corner_radius=6,
            )
            btn.pack(fill="x")
        else:
            btn = tk.Button(
                wrapper, text="🧠 Mémoire", command=cmd,
                bg=accent, fg=tc, font=("Segoe UI", 12, "bold"),
                relief="flat",
            )
            btn.pack(fill="x")
        self._sidebar_memory_btn = btn

        self._sb_separator(self._sidebar_scroll)

    # ─── Bouton Prompts (📚) ──────────────────────────────────────────────

    def _make_prompts_button(self):
        """Crée le bouton '📚 Prompts' ouvrant la bibliothèque de prompts.

        Permet de créer / nommer / éditer / supprimer des templates réutilisables.
        Ceux dotés d'une commande « /xxx » alimentent l'autocomplétion du chat.
        """
        bg = self.colors.get("bg_secondary", "#2f2f2f")
        accent = self.colors.get("accent", "#ff6b47")
        hover = self.colors.get("accent_hover", "#e85a3a")
        tc = self.colors.get("text_primary", "#ffffff")

        wrapper = ctk.CTkFrame(self._sidebar_scroll, fg_color=bg, corner_radius=0) \
            if CTK_AVAILABLE else tk.Frame(self._sidebar_scroll, bg=bg)
        wrapper.pack(fill="x", padx=8, pady=(2, 6))

        cmd = getattr(self, "open_prompts_window", lambda: None)
        if CTK_AVAILABLE:
            btn = ctk.CTkButton(
                wrapper, text="📚 Prompts", command=cmd,
                fg_color=accent, hover_color=hover, text_color=tc,
                font=("Segoe UI", 12, "bold"),
                height=32, corner_radius=6,
            )
            btn.pack(fill="x")
        else:
            btn = tk.Button(
                wrapper, text="📚 Prompts", command=cmd,
                bg=accent, fg=tc, font=("Segoe UI", 12, "bold"),
                relief="flat",
            )
            btn.pack(fill="x")
        self._sidebar_prompts_btn = btn

        self._sb_separator(self._sidebar_scroll)

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
            "search": "🔎 Recherche globale",
            "sessions": "💼 Sessions",
            "history": "📜 Historique",
            "export": "📤 Export",
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

    # ─── Section Recherche globale ────────────────────────────────────

    def _make_section_search(self):
        """Recherche sémantique sur TOUTES les conversations/workspaces."""
        wrapper = self._make_section_wrapper()
        self._sidebar_hdr_search = self._make_section_header_btn(
            wrapper, "🔎 Recherche globale", "search"
        )
        bg = self.colors.get("bg_secondary", "#2f2f2f")
        body = ctk.CTkFrame(wrapper, fg_color=bg, corner_radius=0) \
            if CTK_AVAILABLE else tk.Frame(wrapper, bg=bg)
        self._sidebar_body_search = body

        # Barre de recherche + bouton réindexer
        search_bg = self.colors.get("bg_primary", "#212121")
        sr = ctk.CTkFrame(body, fg_color=search_bg, corner_radius=4) \
            if CTK_AVAILABLE else tk.Frame(body, bg=search_bg)
        sr.pack(fill="x", padx=8, pady=(4, 2))

        self._global_search_var = tk.StringVar()
        if CTK_AVAILABLE:
            entry = ctk.CTkEntry(
                sr, textvariable=self._global_search_var,
                placeholder_text="🔍 Rechercher dans tout l'historique…",
                fg_color=search_bg,
                border_color=self.colors.get("border", "#404040"),
                text_color=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 10), height=26,
            )
            entry.pack(fill="x", padx=4, pady=3)
        else:
            entry = tk.Entry(
                sr, textvariable=self._global_search_var,
                bg=search_bg, fg=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 10), relief="flat",
            )
            entry.pack(fill="x", padx=4, pady=3)
        entry.bind("<Return>", lambda _e: self._global_search_run())
        self._global_search_entry = entry

        # Ligne de boutons : Rechercher / Réindexer
        btn_row = ctk.CTkFrame(body, fg_color=bg, corner_radius=0) \
            if CTK_AVAILABLE else tk.Frame(body, bg=bg)
        btn_row.pack(fill="x", padx=8, pady=(0, 2))
        btn_go = self._sb_button(btn_row, "🔍 Rechercher", self._global_search_run,
                                  color=self.colors.get("accent", "#3b82f6"))
        btn_go.pack(side="left", fill="x", expand=True, padx=(0, 2))
        btn_reidx = self._sb_button(btn_row, "🔄", self._global_search_reindex, width=34)
        btn_reidx.pack(side="right")

        # Statut
        self._global_search_status = self._sb_label(
            body, "", font_size=9,
            color=self.colors.get("text_secondary", "#9ca3af"),
        )
        self._global_search_status.pack(anchor="w", padx=10, pady=(0, 2))

        # Liste des résultats
        list_bg = self.colors.get("bg_primary", "#212121")
        if CTK_AVAILABLE:
            self._global_search_results = ctk.CTkScrollableFrame(
                body, fg_color=list_bg, corner_radius=4, height=180
            )
        else:
            self._global_search_results = tk.Frame(body, bg=list_bg, height=180)
        self._global_search_results.pack(fill="x", padx=8, pady=(0, 4))

        if self._sidebar_sections_open.get("search", False):
            body.pack(fill="x", padx=4, pady=(0, 4))
        self._sb_separator(self._sidebar_scroll)

    def _get_conversation_search(self):
        """Récupère la couche de recherche cross-conversations depuis l'engine."""
        engine = getattr(self, "ai_engine", None)
        if engine is None or not hasattr(engine, "get_conversation_search"):
            return None
        try:
            return engine.get_conversation_search()
        except Exception:
            return None

    def _global_search_set_status(self, text: str):
        try:
            self._global_search_status.configure(text=f"  {text}" if text else "")
        except Exception:
            pass

    def _global_search_run(self):
        query = self._global_search_var.get().strip()
        if not query:
            return
        self._global_search_last_query = query
        cs = self._get_conversation_search()
        if cs is None or not cs.is_available():
            self._global_search_set_status("Recherche sémantique indisponible")
            return
        self._global_search_set_status("Recherche en cours…")
        # Vider les résultats précédents
        for w in self._global_search_results.winfo_children():
            w.destroy()

        def _work():
            try:
                results = cs.search(query, n_results=15)
            except Exception as exc:
                results = []
                print(f"[SEARCH][GUI] Erreur recherche globale: {exc}")
            try:
                self.root.after(0, lambda: self._global_search_render(results))
            except Exception:
                pass

        threading.Thread(target=_work, daemon=True).start()

    def _global_search_render(self, results: list):
        for w in self._global_search_results.winfo_children():
            w.destroy()
        if not results:
            self._global_search_set_status("Aucun résultat")
            self._sb_label(self._global_search_results, "  Aucun résultat",
                           font_size=10,
                           color=self.colors.get("text_secondary", "#9ca3af")
                           ).pack(anchor="w", padx=4, pady=2)
            return
        self._global_search_set_status(f"{len(results)} résultat(s)")
        for res in results:
            self._make_global_search_row(res)

    def _make_global_search_row(self, res: dict):
        ws_id = res.get("workspace_id", "")
        ws_name = res.get("workspace_name", ws_id) or "(sans nom)"
        excerpt = (res.get("excerpt", "") or "").replace("\n", " ").strip()
        role = res.get("role", "")
        icon = "🧑" if role == "user" else "🤖"
        preview = excerpt[:48] + ("…" if len(excerpt) > 48 else "")

        row_bg = self.colors.get("bg_primary", "#212121")
        hover = self.colors.get("button_hover", "#404040")
        row = ctk.CTkFrame(self._global_search_results, fg_color=row_bg, corner_radius=3) \
            if CTK_AVAILABLE else tk.Frame(self._global_search_results, bg=row_bg)
        row.pack(fill="x", pady=1, padx=2)

        label = f"{icon} {ws_name[:18]} · {preview}"
        if CTK_AVAILABLE:
            btn = ctk.CTkButton(
                row, text=label,
                fg_color=row_bg, hover_color=hover,
                text_color=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 10), height=24, corner_radius=3, anchor="w",
                command=lambda r=res: self._global_search_open(r),
            )
            btn.pack(fill="x", padx=2, pady=1)
        else:
            btn = tk.Button(
                row, text=label, bg=row_bg,
                fg=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 10), relief="flat", anchor="w",
                command=lambda r=res: self._global_search_open(r),
            )
            btn.pack(fill="x", padx=2, pady=1)
        # Tooltip : extrait complet + nom du workspace
        try:
            self._kb_attach_tooltip(btn, f"[{ws_name}] {excerpt}")
        except Exception:
            pass

    def _global_search_open(self, res):
        """Ouvre la conversation source et surligne le passage trouvé."""
        if isinstance(res, str):  # rétro-compat
            res = {"workspace_id": res}
        ws_id = res.get("workspace_id", "")
        if not ws_id:
            return
        excerpt = res.get("excerpt", "")
        query = getattr(self, "_global_search_last_query", "")
        try:
            self._session_load(ws_id, highlight_excerpt=excerpt, highlight_query=query)
        except Exception as exc:
            self.show_notification(f"❌ Ouverture impossible : {exc}", "error", 2500)

    def _global_search_reindex(self):
        cs = self._get_conversation_search()
        if cs is None or not cs.is_available():
            self._global_search_set_status("Indexation indisponible")
            return
        self._global_search_set_status("Réindexation…")

        def _work():
            try:
                stats = cs.reindex(force=True)
                msg = f"Indexé : {stats['messages']} message(s)"
            except Exception as exc:
                msg = f"Erreur : {exc}"
            try:
                self.root.after(0, lambda: self._global_search_set_status(msg))
            except Exception:
                pass

        threading.Thread(target=_work, daemon=True).start()

    # ─── Surlignage du résultat dans la conversation ─────────────────────

    @staticmethod
    def _norm_text(s: str) -> str:
        return " ".join((s or "").lower().split())

    def _find_result_widget(self, excerpt: str):
        """Trouve le widget Text de la bulle correspondant à l'extrait recherché.

        Le texte affiché peut différer de l'extrait indexé (markdown nettoyé),
        donc on compare en normalisé : préfixe contenu, sinon meilleur
        recouvrement de mots. Retourne (container, text_widget) ou None.
        """
        needle = self._norm_text(excerpt)
        if not needle:
            return None
        short_needle = needle[:60]
        needle_words = set(needle.split())

        best = None
        best_overlap = 0
        for container in list(getattr(self, "_message_widgets", [])):
            try:
                if not container.winfo_exists():
                    continue
            except Exception:
                continue
            for tw in self._iter_text_widgets(container):
                try:
                    content = self._norm_text(tw.get("1.0", "end-1c"))
                except Exception:
                    continue
                if not content:
                    continue
                # Correspondance forte : préfixe de l'extrait présent
                if short_needle and short_needle in content:
                    return container, tw
                # Sinon mémoriser le meilleur recouvrement de mots
                overlap = len(needle_words & set(content.split()))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best = (container, tw)
        # On exige un minimum de recouvrement pour éviter un faux positif
        if best is not None and best_overlap >= 2:
            return best
        return None

    def _highlight_in_chat(self, excerpt: str, query: str = None):
        """Surligne (style sélection bleue) le passage trouvé et le fait défiler
        à l'écran, après ouverture de la conversation source."""
        found = self._find_result_widget(excerpt)
        if not found:
            return
        container, tw = found

        # Tag de surlignage façon sélection souris
        try:
            tw.tag_config("search_hl", background="#2563eb", foreground="#ffffff")
        except Exception:
            return

        applied = False
        # Surligner d'abord les mots de la requête présents littéralement
        tokens = [w for w in (query or "").split() if len(w) >= 2]
        # Essayer aussi la requête entière comme expression
        if query and query.strip():
            tokens = [query.strip()] + tokens
        for pat in tokens:
            start = "1.0"
            while True:
                try:
                    idx = tw.search(pat, start, stopindex="end", nocase=True)
                except Exception:
                    break
                if not idx:
                    break
                end = f"{idx}+{len(pat)}c"
                tw.tag_add("search_hl", idx, end)
                applied = True
                start = end

        # Aucun mot littéral trouvé (recherche sémantique) → surligner tout le message
        if not applied:
            try:
                tw.tag_add("search_hl", "1.0", "end-1c")
            except Exception:
                pass
        try:
            tw.tag_raise("search_hl")
        except Exception:
            pass

        # Comme une vraie sélection souris : le surlignage disparaît au clic
        def _clear_hl(_e=None, _w=tw):
            try:
                _w.tag_remove("search_hl", "1.0", "end")
            except Exception:
                pass
        try:
            tw.bind("<Button-1>", _clear_hl, add="+")
        except Exception:
            pass

        # Faire défiler le passage à l'écran (2e passe : les hauteurs des bulles
        # IA se stabilisent de façon asynchrone, ce qui peut décaler la position)
        self._scroll_widget_into_view(container, tw)
        try:
            self.root.after(250, lambda: self._scroll_widget_into_view(container, tw))
        except Exception:
            pass

    def _scroll_widget_into_view(self, container, text_widget):
        """Défile le chat pour rendre `container` visible (centré en haut)."""
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        canvas = self._get_parent_canvas() if hasattr(self, "_get_parent_canvas") else None
        if canvas is not None:
            try:
                bbox = canvas.bbox("all")
                if bbox:
                    total = max(1, bbox[3] - bbox[1])
                    y = container.winfo_y()
                    frac = max(0.0, min(1.0, (y - 30) / total))
                    canvas.yview_moveto(frac)
                    return
            except Exception:
                pass
        # Repli : scroll interne du widget
        try:
            text_widget.see("1.0")
        except Exception:
            pass

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

    # ─── Section Dossiers du projet (codebase attaché au workspace) ──────

    def _make_section_project_folders(self):
        wrapper = self._make_section_wrapper()
        self._sidebar_hdr_folders = self._make_section_header_btn(
            wrapper, "📁 Dossiers du projet", "project_folders"
        )
        bg = self.colors.get("bg_secondary", "#2f2f2f")
        body = ctk.CTkFrame(wrapper, fg_color=bg, corner_radius=0) \
            if CTK_AVAILABLE else tk.Frame(wrapper, bg=bg)
        self._sidebar_body_folders = body

        btn_attach = self._sb_button(body, "➕ Attacher un dossier",
                                      self._folder_attach, width=_SIDEBAR_W - 20)
        btn_attach.pack(fill="x", padx=8, pady=(4, 2))

        list_bg = self.colors.get("bg_primary", "#212121")
        self._folders_list_frame = ctk.CTkFrame(body, fg_color=list_bg, corner_radius=4) \
            if CTK_AVAILABLE else tk.Frame(body, bg=list_bg)
        self._folders_list_frame.pack(fill="x", padx=8, pady=(0, 4))

        if self._sidebar_sections_open["project_folders"]:
            body.pack(fill="x", padx=4, pady=(0, 4))
        self._sb_separator(self._sidebar_scroll)
        self._refresh_project_folders()

    def _get_folder_indexer(self):
        engine = getattr(self, "ai_engine", None)
        if engine is None or not hasattr(engine, "get_folder_indexer"):
            return None
        try:
            return engine.get_folder_indexer()
        except Exception:
            return None

    def _current_workspace_id(self):
        engine = getattr(self, "ai_engine", None)
        sm = getattr(engine, "session_manager", None) if engine else None
        if sm is None:
            return None
        try:
            return sm.get_current_workspace()
        except Exception:
            return None

    def _refresh_project_folders(self):
        frame = getattr(self, "_folders_list_frame", None)
        if frame is None:
            return
        for w in frame.winfo_children():
            w.destroy()

        sec = self.colors.get("text_secondary", "#9ca3af")
        indexer = self._get_folder_indexer()
        ws_id = self._current_workspace_id()

        if indexer is None:
            self._sb_label(frame, "  (indexeur indisponible)", font_size=10,
                           color=sec).pack(anchor="w", padx=4, pady=2)
            return
        if not ws_id:
            self._sb_label(frame, "  Aucune session active", font_size=10,
                           color=sec).pack(anchor="w", padx=4, pady=2)
            return

        try:
            status = indexer.get_status(ws_id)
        except Exception:
            status = {"folders": []}
        folders = status.get("folders", [])
        if not folders:
            self._sb_label(frame, "  Aucun dossier attaché", font_size=10,
                           color=sec).pack(anchor="w", padx=4, pady=2)
            return

        primary = self.colors.get("text_primary", "#ffffff")
        row_bg = self.colors.get("bg_primary", "#212121")
        for folder in folders:
            path = folder.get("path", "")
            name = Path(path).name or path
            count = folder.get("file_count", 0)
            row = ctk.CTkFrame(frame, fg_color=row_bg, corner_radius=3) \
                if CTK_AVAILABLE else tk.Frame(frame, bg=row_bg)
            row.pack(fill="x", pady=1)
            self._sb_label(row, f"📁 {name[:18]}  ({count})", font_size=10,
                           color=primary).pack(side="left", padx=(4, 2), pady=1,
                                               fill="x", expand=True)
            re_btn = self._sb_button(
                row, "↻", lambda p=path: self._folder_reindex(p), width=28)
            de_btn = self._sb_button(
                row, "🗑", lambda p=path: self._folder_detach(p),
                color="#ef4444", width=28)
            if CTK_AVAILABLE:
                re_btn.configure(height=22)
                de_btn.configure(height=22)
            de_btn.pack(side="right", padx=(0, 2), pady=1)
            re_btn.pack(side="right", padx=(0, 2), pady=1)

    def _folder_attach(self):
        """Sélectionne un dossier et l'attache au workspace courant (indexation BG)."""
        indexer = self._get_folder_indexer()
        if indexer is None:
            self.show_notification("❌ Indexeur indisponible", "error", 2500)
            return
        folder = filedialog.askdirectory(title="Attacher un dossier (codebase / docs)",
                                          parent=self.root)
        if not folder:
            return

        ws_id = self._ensure_workspace_for_folder(folder)
        if not ws_id:
            self.show_notification("❌ Aucune session active", "error", 2500)
            return
        self._index_folder_async(ws_id, folder, reindex=False)

    def _folder_reindex(self, folder_path: str):
        ws_id = self._current_workspace_id()
        if not ws_id:
            return
        self._index_folder_async(ws_id, folder_path, reindex=True)

    def _folder_detach(self, folder_path: str):
        indexer = self._get_folder_indexer()
        ws_id = self._current_workspace_id()
        if indexer is None or not ws_id:
            return
        name = Path(folder_path).name or folder_path
        if not messagebox.askyesno(
            "Détacher le dossier",
            f"Détacher '{name}' du projet ?\nSon index sera supprimé.",
            parent=self.root,
        ):
            return
        try:
            indexer.remove_folder(ws_id, folder_path)
            self._remove_folder_from_workspace(ws_id, folder_path)
            self.show_notification("✅ Dossier détaché", "success", 1800)
        except Exception as exc:
            self.show_notification(f"❌ Erreur : {exc}", "error", 2500)
        self._refresh_project_folders()

    def _ensure_workspace_for_folder(self, folder: str):
        """Renvoie le workspace courant, ou en crée un nommé d'après le dossier."""
        engine = getattr(self, "ai_engine", None)
        sm = getattr(engine, "session_manager", None) if engine else None
        if sm is None:
            return None
        try:
            ws_id = sm.get_current_workspace()
            if ws_id:
                return ws_id
            ws_id = sm.create_workspace(Path(folder).name or "Projet")
            sm.set_current_workspace(ws_id)
            self._refresh_sessions()
            return ws_id
        except Exception:
            return None

    def _index_folder_async(self, ws_id: str, folder: str, reindex: bool):
        """Lance l'indexation en arrière-plan avec progression (UI non bloquante)."""
        indexer = self._get_folder_indexer()
        if indexer is None:
            return
        verb = "Ré-indexation" if reindex else "Indexation"
        name = Path(folder).name or folder
        self.show_notification(f"⏳ {verb} de '{name}'…", "info", 2000)

        def _progress(done, total, rel):
            if done % 10 == 0 or done == total:
                self.root.after(0, lambda: self.show_notification(
                    f"⏳ {verb} '{name}' : {done}/{total}", "info", 1200))

        def _run():
            try:
                res = indexer.index_folder(ws_id, folder, force=reindex,
                                           progress_cb=_progress)
            except Exception as exc:
                self.root.after(0, lambda: self.show_notification(
                    f"❌ Indexation échouée : {exc}", "error", 3000))
                return
            if res.get("status") != "success":
                self.root.after(0, lambda: self.show_notification(
                    f"❌ {res.get('error', 'Indexation impossible')}", "error", 3000))
                return
            self._add_folder_to_workspace(ws_id, res.get("folder", folder))
            msg = (f"✅ '{name}' indexé : {res.get('total_files', 0)} fichiers, "
                   f"{res.get('chunks', 0)} extraits")
            self.root.after(0, lambda: self.show_notification(msg, "success", 2500))
            self.root.after(0, self._refresh_project_folders)

        threading.Thread(target=_run, daemon=True).start()

    # -- Persistance de la liste des dossiers dans l'état du workspace --------

    def _add_folder_to_workspace(self, ws_id: str, folder_key: str):
        engine = getattr(self, "ai_engine", None)
        sm = getattr(engine, "session_manager", None) if engine else None
        if sm is None:
            return
        try:
            state = sm.load_workspace(ws_id) or {}
            folders = state.get("attached_folders", [])
            if folder_key not in folders:
                folders.append(folder_key)
            state["attached_folders"] = folders
            sm.save_workspace(ws_id, state)
        except Exception:
            pass

    def _remove_folder_from_workspace(self, ws_id: str, folder_path: str):
        engine = getattr(self, "ai_engine", None)
        sm = getattr(engine, "session_manager", None) if engine else None
        if sm is None:
            return
        try:
            state = sm.load_workspace(ws_id) or {}
            folders = state.get("attached_folders", [])
            resolved = str(Path(folder_path))
            state["attached_folders"] = [
                f for f in folders
                if f != folder_path and str(Path(f)) != resolved
            ]
            sm.save_workspace(ws_id, state)
        except Exception:
            pass

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
            # Nouveau workspace = historique vide (ne pas hériter de la conv courante)
            state = {"conversation_history": [],
                     "name": name.strip()}
            sm.save_workspace(ws_id, state)
            self._refresh_sessions()
            self.show_notification(f"✅ Session '{name}' créée", "success", 2000)
        except Exception as exc:
            self.show_notification(f"❌ Erreur : {exc}", "error", 2500)

    def _session_save_current(self):
        """Sauvegarde le workspace courant avant de switcher."""
        engine = getattr(self, "ai_engine", None)
        sm = getattr(engine, "session_manager", None) if engine else None
        if not sm:
            return
        current_ws = sm.get_current_workspace()
        if current_ws:
            state = {"conversation_history": getattr(self, "conversation_history", [])}
            sm.save_workspace(current_ws, state)

    def _session_load(self, workspace_id: str, highlight_excerpt: str = None,
                      highlight_query: str = None):
        engine = getattr(self, "ai_engine", None)
        sm = getattr(engine, "session_manager", None) if engine else None
        if not sm:
            return
        try:
            state = sm.load_workspace(workspace_id)
            if state is None:
                self.show_notification("❌ Session introuvable", "error", 2000)
                return
            history = state.get("conversation_history", state.get("history", []))
            ws_name = state.get("metadata", {}).get("name", workspace_id)
            if not messagebox.askyesno(
                "Charger la session",
                f"Charger '{ws_name}' ?\n"
                "La conversation actuelle sera remplacée.",
                parent=self.root,
            ):
                return
            # Sauvegarder le workspace courant avant de switcher
            self._session_save_current()
            # Nettoyer tout
            if hasattr(engine, "conversation_manager"):
                engine.conversation_manager.clear()
            self.clear_chat()
            # Reconstruire l'UI depuis l'historique chargé
            if history:
                # Enlever l'écran d'accueil pour montrer la conversation
                if hasattr(self, "_dismiss_home_screen"):
                    self._dismiss_home_screen()
                # add_message_bubble ajoute aussi à conversation_history
                for msg in history:
                    is_user = msg.get("is_user", msg.get("role", "user") == "user")
                    content = msg.get("text", msg.get("content", ""))
                    if content:
                        self.add_message_bubble(content, is_user=is_user, instant=True)
            sm.set_current_workspace(workspace_id)
            self.show_notification(
                "✅ Session chargée", "success", 2000
            )
            self._refresh_sessions()
            if hasattr(self, "_refresh_project_folders"):
                self._refresh_project_folders()
            # Surligner le passage recherché une fois le rendu stabilisé
            if highlight_excerpt:
                self.root.after(
                    300,
                    lambda: self._highlight_in_chat(highlight_excerpt, highlight_query),
                )
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
        full_query = entry.get("query", "")
        # Aperçu : 4 premiers mots + "…" si plus long
        words = full_query.split()
        if len(words) <= 4:
            text = full_query
        else:
            text = " ".join(words[:4]) + "…"
        is_fav = bool(entry.get("is_favorite", False))
        star = "⭐" if is_fav else "☆"
        row_bg = self.colors.get("bg_primary", "#212121")
        hover = self.colors.get("button_hover", "#404040")
        row = ctk.CTkFrame(self._history_list_frame, fg_color=row_bg, corner_radius=3) \
            if CTK_AVAILABLE else tk.Frame(self._history_list_frame, bg=row_bg)
        row.pack(fill="x", pady=1, padx=2)
        # Poubelle en premier pour réserver sa place à droite
        del_btn = self._sb_button(row, "🗑",
                                   lambda eid_=eid: self._history_delete(eid_),
                                   color="#ef4444", width=28)
        if CTK_AVAILABLE:
            del_btn.configure(height=22)
        del_btn.pack(side="right", padx=(0, 2), pady=1)
        # Bouton favori
        fav_tc = "#f59e0b" if is_fav else self.colors.get("text_secondary", "#9ca3af")
        if CTK_AVAILABLE:
            ctk.CTkButton(
                row, text=star, width=24, height=22,
                fg_color=row_bg, hover_color=hover, text_color=fav_tc,
                font=("Segoe UI", 10), corner_radius=3,
                command=lambda eid_=eid: self._history_toggle_fav(eid_),
            ).pack(side="left", padx=(2, 0))
            cmd_btn = ctk.CTkButton(
                row, text=text,
                fg_color=row_bg, hover_color=hover,
                text_color=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 10), height=22, corner_radius=3, anchor="w",
                command=lambda t=full_query: self._history_reuse(t),
            )
            cmd_btn.pack(side="left", fill="x", expand=True, padx=2)
        else:
            tk.Button(
                row, text=star, bg=row_bg, fg=fav_tc,
                font=("Segoe UI", 10), relief="flat",
                command=lambda eid_=eid: self._history_toggle_fav(eid_),
            ).pack(side="left", padx=(2, 0))
            cmd_btn = tk.Button(
                row, text=text, bg=row_bg,
                fg=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 10), relief="flat", anchor="w",
                command=lambda t=full_query: self._history_reuse(t),
            )
            cmd_btn.pack(side="left", fill="x", expand=True, padx=2)
        # Tooltip : afficher la commande complète au survol
        try:
            self._kb_attach_tooltip(cmd_btn, full_query)
        except Exception:
            pass

    def _history_toggle_fav(self, entry_id):
        engine = getattr(self, "ai_engine", None)
        ch = getattr(engine, "command_history", None) if engine else None
        if ch:
            try:
                ch.toggle_favorite(entry_id)
                self._refresh_history()
            except Exception:
                pass

    def _history_delete(self, entry_id):
        engine = getattr(self, "ai_engine", None)
        ch = getattr(engine, "command_history", None) if engine else None
        if not ch:
            return
        try:
            ch.delete(entry_id)
            self._refresh_history()
        except Exception as exc:
            print(f"[HIST][GUI] Erreur suppression entrée: {exc}")
            self.show_notification(f"❌ Erreur : {exc}", "error", 2500)

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

    # ─── Tooltip simple ────────────────────────────────────────────────

    def _kb_attach_tooltip(self, widget, text: str):
        """Tooltip basique affichant le texte complet au survol."""
        if not text:
            return
        tip = {"win": None}

        def show(_e=None):
            if tip["win"] is not None:
                return
            try:
                x = widget.winfo_rootx() + 12
                y = widget.winfo_rooty() + widget.winfo_height() + 4
            except Exception:
                return
            w = tk.Toplevel(self.root)
            w.wm_overrideredirect(True)
            w.wm_geometry(f"+{x}+{y}")
            bg = self.colors.get("bg_primary", "#212121")
            fg = self.colors.get("text_primary", "#ffffff")
            tk.Label(
                w, text=text[:200], bg=bg, fg=fg,
                font=("Segoe UI", 9), padx=6, pady=3,
                wraplength=320, justify="left",
                borderwidth=1, relief="solid",
            ).pack()
            tip["win"] = w

        def hide(_e=None):
            if tip["win"] is not None:
                try:
                    tip["win"].destroy()
                except Exception:
                    pass
                tip["win"] = None

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)
