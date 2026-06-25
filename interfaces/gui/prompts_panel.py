"""Prompts panel mixin — fenêtre « 📚 Prompts » (bibliothèque réutilisable).

Donne le contrôle total sur la bibliothèque de prompts / slash commands, en
local : créer, nommer, éditer et supprimer des templates. Les templates dotés
d'une commande `/xxx` apparaissent dans l'autocomplétion de la zone de saisie
(cf. interfaces/gui/slash_commands.py).

Conteneur = tk.Toplevel peuplé de widgets CTk (même pattern éprouvé que
memory_panel / settings_panel, évite le bug CTkToplevel). Persistance via
core.prompt_library.PromptLibrary (exposée par AIEngine.prompt_library).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    ctk = tk


_WIN_W, _WIN_H = 760, 620


class PromptsPanelMixin:
    """Fenêtre « Prompts » pour ModernAIGUI."""

    # ─── Ouverture ──────────────────────────────────────────────────────

    def open_prompts_window(self):
        """Ouvre (ou refocus) la fenêtre de gestion des prompts."""
        existing = getattr(self, "_prompts_win", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    return
            except Exception:
                pass

        bg = self.colors.get("bg_primary", "#212121")
        win = tk.Toplevel(self.root)
        win.title("📚 Prompts — My_AI")
        win.configure(bg=bg)
        win.geometry(f"{_WIN_W}x{_WIN_H}")
        win.minsize(560, 420)
        win.transient(self.root)
        self._prompts_win = win

        def _on_close():
            self._prompts_win = None
            try:
                win.destroy()
            except Exception:
                pass

        win.protocol("WM_DELETE_WINDOW", _on_close)
        win.bind("<Escape>", lambda _e: _on_close())

        # ── En-tête ────────────────────────────────────────────────────
        header = self._pl_frame(win, bg)
        header.pack(fill="x", padx=12, pady=(12, 4))
        self._pl_label(
            header, "📚 Bibliothèque de prompts", size=17, bold=True,
            color=self.colors.get("accent", "#ff6b47"), bg=bg,
        ).pack(anchor="w")
        self._pl_label(
            header,
            "Créez des templates réutilisables. Une commande « /xxx » les rend "
            "accessibles par autocomplétion dans le chat. Placeholders : {nom}.",
            size=10, color=self.colors.get("text_secondary", "#9ca3af"), bg=bg,
        ).pack(anchor="w")

        # ── Barre d'outils ─────────────────────────────────────────────
        toolbar = self._pl_frame(win, bg)
        toolbar.pack(fill="x", padx=12, pady=(6, 4))
        self._pl_button(
            toolbar, "➕ Nouveau prompt", lambda: self._pl_open_form(None),
            width=170, accent=True,
        ).pack(side="left")
        self._pl_button(toolbar, "🔄", self._pl_reload, width=44).pack(side="right")

        # ── Liste défilante ─────────────────────────────────────────────
        list_bg = self.colors.get("bg_secondary", "#181818")
        if CTK_AVAILABLE:
            self._pl_list = ctk.CTkScrollableFrame(win, fg_color=list_bg, corner_radius=8)
        else:
            self._pl_list = tk.Frame(win, bg=list_bg)
        self._pl_list.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._pl_reload()

    # ─── Rendu de la liste ──────────────────────────────────────────────

    def _pl_reload(self):
        """Recharge la liste des templates depuis la bibliothèque."""
        if not hasattr(self, "_pl_list") or self._pl_list is None:
            return
        for child in self._pl_list.winfo_children():
            child.destroy()

        lib = self._get_prompt_library()
        if lib is None:
            self._pl_label(
                self._pl_list, "  Bibliothèque de prompts indisponible.",
                size=11, color=self.colors.get("text_secondary", "#9ca3af"),
                bg=self.colors.get("bg_secondary", "#181818"),
            ).pack(anchor="w", padx=8, pady=8)
            return

        try:
            templates = lib.list()
        except Exception:
            templates = []

        if not templates:
            self._pl_label(
                self._pl_list, "  Aucun prompt pour l'instant. Cliquez « ➕ Nouveau prompt ».",
                size=11, color=self.colors.get("text_secondary", "#9ca3af"),
                bg=self.colors.get("bg_secondary", "#181818"),
            ).pack(anchor="w", padx=8, pady=8)
            return

        for tpl in templates:
            self._pl_make_row(tpl)

    def _pl_make_row(self, tpl: dict):
        """Affiche une ligne : commande + titre + description + actions."""
        bg = self.colors.get("bg_primary", "#212121")
        row = self._pl_frame(self._pl_list, bg, corner=8)
        row.pack(fill="x", padx=6, pady=4)

        # Colonne gauche : infos
        info = self._pl_frame(row, bg)
        info.pack(side="left", fill="x", expand=True, padx=10, pady=8)

        command = tpl.get("command")
        title = tpl.get("title", "") or "(sans titre)"
        head = f"/{command}   ·   {title}" if command else title
        self._pl_label(
            info, head, size=12, bold=True,
            color=self.colors.get("text_primary", "#ffffff"), bg=bg,
        ).pack(anchor="w")

        desc = (tpl.get("description") or "").strip()
        if desc:
            self._pl_label(
                info, desc, size=10,
                color=self.colors.get("text_secondary", "#9ca3af"), bg=bg,
            ).pack(anchor="w", pady=(1, 0))

        # Aperçu du contenu (1 ligne tronquée)
        preview = " ".join((tpl.get("content") or "").split())
        if len(preview) > 90:
            preview = preview[:87] + "…"
        if preview:
            self._pl_label(
                info, preview, size=9,
                color=self.colors.get("text_secondary", "#6b7280"), bg=bg,
            ).pack(anchor="w", pady=(2, 0))

        # Colonne droite : actions
        actions = self._pl_frame(row, bg)
        actions.pack(side="right", padx=(0, 8), pady=8)
        self._pl_button(
            actions, "✏️", lambda t=tpl: self._pl_open_form(t), width=40,
        ).pack(side="left", padx=(0, 4))
        self._pl_button(
            actions, "🗑", lambda t=tpl: self._pl_delete(t), width=40,
            color="#ef4444",
        ).pack(side="left")

    # ─── Formulaire création / édition ──────────────────────────────────

    def _pl_open_form(self, tpl: dict | None):
        """Ouvre un dialogue de création (tpl=None) ou d'édition."""
        lib = self._get_prompt_library()
        if lib is None:
            messagebox.showwarning(
                "Indisponible", "La bibliothèque de prompts n'est pas disponible.",
                parent=getattr(self, "_prompts_win", self.root),
            )
            return

        is_edit = tpl is not None
        bg = self.colors.get("bg_primary", "#212121")
        dialog = tk.Toplevel(self.root)
        dialog.title("Modifier le prompt" if is_edit else "Nouveau prompt")
        dialog.configure(bg=bg)
        dialog.geometry("520x520")
        dialog.transient(getattr(self, "_prompts_win", self.root))
        dialog.grab_set()

        title_txt = "✏️ Modifier le prompt" if is_edit else "➕ Nouveau prompt"
        self._pl_label(
            dialog, title_txt, size=15, bold=True,
            color=self.colors.get("text_primary", "#ffffff"), bg=bg,
        ).pack(anchor="w", padx=20, pady=(16, 10))

        # Champ : Titre
        name_entry = self._pl_form_entry(dialog, "Nom", "Ex : Résumé")
        if is_edit:
            name_entry.insert(0, tpl.get("title", ""))

        # Champ : Commande (slash)
        cmd_entry = self._pl_form_entry(
            dialog, "Commande (slash, optionnel)", "Ex : résume",
        )
        if is_edit and tpl.get("command"):
            cmd_entry.insert(0, tpl["command"])

        # Champ : Description
        desc_entry = self._pl_form_entry(
            dialog, "Description (optionnel)", "À quoi sert ce prompt ?",
        )
        if is_edit:
            desc_entry.insert(0, tpl.get("description", ""))

        # Champ : Contenu
        self._pl_label(
            dialog, "Contenu  (placeholders : {nom})", size=11, bold=True,
            color=self.colors.get("text_primary", "#ffffff"), bg=bg,
        ).pack(anchor="w", padx=20, pady=(8, 2))
        if CTK_AVAILABLE:
            content_box = ctk.CTkTextbox(
                dialog, height=130, font=("Segoe UI", 12),
                fg_color=self.colors.get("input_bg", "#2f2f2f"),
                text_color=self.colors.get("text_primary", "#ffffff"),
                border_width=1, border_color=self.colors.get("border", "#404040"),
                corner_radius=6,
            )
        else:
            content_box = tk.Text(
                dialog, height=7, font=("Segoe UI", 12),
                bg=self.colors.get("input_bg", "#2f2f2f"),
                fg=self.colors.get("text_primary", "#ffffff"),
            )
        content_box.pack(fill="both", expand=True, padx=20, pady=(0, 8))
        if is_edit:
            content_box.insert("0.0" if CTK_AVAILABLE else "1.0", tpl.get("content", ""))

        # Message d'erreur inline
        msg_lbl = self._pl_label(
            dialog, "", size=10, color="#ef4444", bg=bg,
        )
        msg_lbl.pack(anchor="w", padx=20)

        # Boutons
        btns = self._pl_frame(dialog, bg)
        btns.pack(fill="x", padx=20, pady=(6, 16))

        def _save():
            title = name_entry.get().strip()
            command = cmd_entry.get().strip()
            description = desc_entry.get().strip()
            content = content_box.get(
                "0.0" if CTK_AVAILABLE else "1.0", "end-1c"
            ).strip()
            if not title and not command:
                msg_lbl.configure(text="Renseignez au moins un nom ou une commande.")
                return
            if not content:
                msg_lbl.configure(text="Le contenu ne peut pas être vide.")
                return
            try:
                if is_edit:
                    lib.update(
                        tpl["id"], title=title, command=command,
                        description=description, content=content,
                    )
                else:
                    lib.add(
                        title=title or command, content=content,
                        command=command or None, description=description,
                    )
            except ValueError as exc:
                msg_lbl.configure(text=str(exc))
                return
            except Exception as exc:
                msg_lbl.configure(text=f"Erreur : {exc}")
                return
            try:
                dialog.destroy()
            except Exception:
                pass
            self._pl_reload()
            self._pl_notify(
                "✅ Prompt enregistré" if is_edit else "✅ Prompt créé", "success"
            )

        self._pl_button(btns, "Annuler", dialog.destroy, width=110).pack(side="right", padx=(8, 0))
        self._pl_button(btns, "Enregistrer", _save, width=130, accent=True).pack(side="right")

        try:
            name_entry.focus_set()
        except Exception:
            pass

    def _pl_delete(self, tpl: dict):
        """Supprime un template après confirmation."""
        lib = self._get_prompt_library()
        if lib is None:
            return
        name = tpl.get("command") and f"/{tpl['command']}" or tpl.get("title", "ce prompt")
        if not messagebox.askyesno(
            "Supprimer le prompt",
            f"Voulez-vous vraiment supprimer « {name} » ?",
            parent=getattr(self, "_prompts_win", self.root),
        ):
            return
        try:
            lib.delete(tpl["id"])
        except Exception as exc:
            self._pl_notify(f"❌ Erreur : {exc}", "error")
            return
        self._pl_reload()
        self._pl_notify("🗑️ Prompt supprimé", "success")

    # ─── Helpers UI ─────────────────────────────────────────────────────

    def _pl_form_entry(self, parent, label, placeholder):
        """Crée un libellé + un Entry, retourne l'Entry."""
        bg = self.colors.get("bg_primary", "#212121")
        self._pl_label(
            parent, label, size=11, bold=True,
            color=self.colors.get("text_primary", "#ffffff"), bg=bg,
        ).pack(anchor="w", padx=20, pady=(8, 2))
        if CTK_AVAILABLE:
            entry = ctk.CTkEntry(
                parent, font=("Segoe UI", 12), height=34,
                fg_color=self.colors.get("input_bg", "#2f2f2f"),
                text_color=self.colors.get("text_primary", "#ffffff"),
                border_color=self.colors.get("border", "#404040"),
                corner_radius=6, placeholder_text=placeholder,
            )
        else:
            entry = tk.Entry(
                parent, font=("Segoe UI", 12),
                bg=self.colors.get("input_bg", "#2f2f2f"),
                fg=self.colors.get("text_primary", "#ffffff"),
            )
        entry.pack(fill="x", padx=20)
        return entry

    def _pl_frame(self, parent, color=None, corner=0):
        bg = color or self.colors.get("bg_primary", "#212121")
        if CTK_AVAILABLE:
            return ctk.CTkFrame(parent, fg_color=bg, corner_radius=corner)
        return tk.Frame(parent, bg=bg)

    def _pl_label(self, parent, text, size=12, bold=False, color=None, bg=None):
        c = color or self.colors.get("text_primary", "#ffffff")
        font = ("Segoe UI", size, "bold" if bold else "normal")
        if CTK_AVAILABLE:
            return ctk.CTkLabel(
                parent, text=text, font=font, text_color=c,
                fg_color="transparent", anchor="w", justify="left",
                wraplength=_WIN_W - 160,
            )
        return tk.Label(
            parent, text=text, font=font, fg=c,
            bg=bg or self.colors.get("bg_primary", "#212121"),
            anchor="w", justify="left", wraplength=_WIN_W - 160,
        )

    def _pl_button(self, parent, text, command, color=None, width=None, accent=False):
        if color:
            bg = color
        elif accent:
            bg = self.colors.get("accent", "#ff6b47")
        else:
            bg = self.colors.get("bg_secondary", "#2f2f2f")
        hover = (self.colors.get("accent_hover", "#e85a3a") if accent
                 else self.colors.get("button_hover", "#404040"))
        tc = self.colors.get("text_primary", "#ffffff")
        if CTK_AVAILABLE:
            kw = dict(
                text=text, command=command, fg_color=bg, hover_color=hover,
                text_color=tc, font=("Segoe UI", 12), height=32, corner_radius=6,
            )
            if width:
                kw["width"] = width
            return ctk.CTkButton(parent, **kw)
        return tk.Button(
            parent, text=text, command=command, bg=bg, fg=tc,
            font=("Segoe UI", 11), relief="flat",
        )

    def _pl_notify(self, message, kind="info"):
        """Notification non bloquante (réutilise show_notification si présent)."""
        if hasattr(self, "show_notification"):
            try:
                self.show_notification(message, kind, 2000)
                return
            except Exception:
                pass
        print(f"[Prompts] {message}")
