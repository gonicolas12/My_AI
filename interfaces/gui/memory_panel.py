"""Memory panel mixin — fenêtre « 🧠 Mémoire » (voir / éditer / supprimer).

Donne à l'utilisateur le contrôle total sur ce que l'IA « sait » de lui, en
local : les faits structurés (SQLite) et les entrées vectorielles (ChromaDB,
collections « documents » et « conversations »). Toutes les opérations sont
réelles via la couche unifiée core.memory_store.MemoryStore (exposée par
AIEngine.get_memory_store()).

Conteneur = tk.Toplevel peuplé de widgets CTk (pattern éprouvé de
settings_panel / _show_relay_info_popup, évite le bug CTkToplevel). Chargements
ChromaDB et réindex tournent en thread, rendu via self.root.after.

Fonctions clés :
  - 3 onglets : Faits · Documents · Conversations
  - recherche + filtre par catégorie (faits), pagination
  - édition inline (✏️) et suppression (🗑) avec dialogue de confirmation stylé
    comme la confirmation MCP (interfaces/gui/base.py)
  - pour les conversations, la suppression/édition peut se propager au message
    d'origine du workspace (sinon l'entrée réapparaît au réindex)
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, simpledialog

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    ctk = tk


_WIN_W, _WIN_H = 880, 700
_PAGE_SIZE = 20

# Onglets : (libellé affiché, clé interne)
_TABS = [("📌 Faits", "facts"), ("📄 Documents", "document"), ("💬 Conversations", "conversation")]
_TAB_LABEL_TO_KEY = {label: key for label, key in _TABS}
_TAB_KEY_TO_LABEL = {key: label for label, key in _TABS}

_FACT_CATEGORIES = [
    "Toutes", "general", "preference", "decision", "person", "procedure", "technical",
]

_CAT_COLORS = {
    "preference": "#8b5cf6", "decision": "#f59e0b",
    "person": "#10b981", "procedure": "#3b82f6",
    "technical": "#ef4444", "general": "#9ca3af",
}


class MemoryPanelMixin:
    """Fenêtre « Mémoire » pour ModernAIGUI."""

    # ─── Accès au store ─────────────────────────────────────────────────

    def _mem_store(self):
        """Récupère la couche d'accès mémoire unifiée depuis l'engine."""
        engine = getattr(self, "ai_engine", None)
        if engine is None or not hasattr(engine, "get_memory_store"):
            return None
        try:
            return engine.get_memory_store()
        except Exception:
            return None

    # ─── Ouverture ──────────────────────────────────────────────────────

    def open_memory_window(self):
        """Ouvre (ou refocus) la fenêtre Mémoire."""
        existing = getattr(self, "_mem_win", None)
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
        win.title("🧠 Mémoire — My_AI")
        win.configure(bg=bg)
        win.geometry(f"{_WIN_W}x{_WIN_H}")
        win.minsize(640, 480)
        win.transient(self.root)
        self._mem_win = win

        # État de navigation
        self._mem_tab = "facts"
        self._mem_page = 0
        self._mem_query = tk.StringVar()
        self._mem_category = tk.StringVar(value="Toutes")
        self._mem_edit_key = None
        self._mem_current_items = []
        self._mem_current_total = 0

        def _on_close():
            self._mem_win = None
            try:
                win.destroy()
            except Exception:
                pass

        win.protocol("WM_DELETE_WINDOW", _on_close)
        win.bind("<Escape>", lambda _e: _on_close())

        # ── En-tête ────────────────────────────────────────────────────
        header = self._mem_frame(win, bg)
        header.pack(fill="x", padx=12, pady=(12, 4))
        self._mem_label(
            header, "🧠 Mémoire locale", size=17, bold=True,
            color=self.colors.get("accent", "#ff6b47"), bg=bg,
        ).pack(anchor="w")
        self._mem_label(
            header,
            "Contrôle total sur ce que l'IA sait de vous — tout est stocké localement.",
            size=10, color=self.colors.get("text_secondary", "#9ca3af"), bg=bg,
        ).pack(anchor="w")
        self._mem_stats_label = self._mem_label(
            header, "", size=9,
            color=self.colors.get("text_secondary", "#9ca3af"), bg=bg,
        )
        self._mem_stats_label.pack(anchor="w", pady=(2, 0))

        # ── Sélecteur d'onglet ──────────────────────────────────────────
        tabbar = self._mem_frame(win, bg)
        tabbar.pack(fill="x", padx=12, pady=(6, 4))
        labels = [label for label, _ in _TABS]
        if CTK_AVAILABLE:
            self._mem_segment = ctk.CTkSegmentedButton(
                tabbar, values=labels, command=self._mem_on_tab_selected,
                fg_color=self.colors.get("bg_secondary", "#2f2f2f"),
                selected_color=self.colors.get("accent", "#ff6b47"),
                selected_hover_color=self.colors.get("accent_hover", "#e85a3a"),
                unselected_color=self.colors.get("bg_secondary", "#2f2f2f"),
                text_color=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 12, "bold"),
            )
            self._mem_segment.set(_TAB_KEY_TO_LABEL["facts"])
            self._mem_segment.pack(fill="x")
        else:
            self._mem_segment = None
            for label, key in _TABS:
                tk.Button(
                    tabbar, text=label,
                    command=lambda k=key: self._mem_set_tab(k),
                    relief="flat",
                ).pack(side="left", padx=2)

        # ── Barre d'outils (recherche / catégorie / actions) ────────────
        self._mem_toolbar = self._mem_frame(win, bg)
        self._mem_toolbar.pack(fill="x", padx=12, pady=(4, 4))

        # ── Liste défilante ─────────────────────────────────────────────
        list_bg = self.colors.get("bg_secondary", "#181818")
        if CTK_AVAILABLE:
            self._mem_list = ctk.CTkScrollableFrame(win, fg_color=list_bg, corner_radius=8)
        else:
            self._mem_list = tk.Frame(win, bg=list_bg)
        self._mem_list.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        # ── Pagination ──────────────────────────────────────────────────
        pager = self._mem_frame(win, bg)
        pager.pack(fill="x", padx=12, pady=(0, 12))
        self._mem_prev_btn = self._mem_button(
            pager, "◀ Précédent", self._mem_prev_page, width=120,
        )
        self._mem_prev_btn.pack(side="left")
        self._mem_next_btn = self._mem_button(
            pager, "Suivant ▶", self._mem_next_page, width=120,
        )
        self._mem_next_btn.pack(side="right")
        self._mem_pager_label = self._mem_label(
            pager, "", size=11, color=self.colors.get("text_secondary", "#9ca3af"), bg=bg,
        )
        self._mem_pager_label.pack(side="top", pady=2)

        self._mem_build_toolbar()
        self._mem_reload()

    # ─── Onglets ────────────────────────────────────────────────────────

    def _mem_on_tab_selected(self, label: str):
        self._mem_set_tab(_TAB_LABEL_TO_KEY.get(label, "facts"))

    def _mem_set_tab(self, tab_key: str):
        if tab_key == self._mem_tab:
            return
        self._mem_tab = tab_key
        self._mem_page = 0
        self._mem_edit_key = None
        self._mem_query.set("")
        self._mem_category.set("Toutes")
        self._mem_update_toolbar()
        self._mem_reload()

    # ─── Barre d'outils ─────────────────────────────────────────────────

    def _mem_build_toolbar(self):
        """Construit la barre d'outils UNE SEULE FOIS (widgets persistants).

        On ne reconstruit jamais les widgets : détruire un CTkEntry lié à un
        StringVar laisse sa callback de placeholder branchée sur le StringVar,
        ce qui provoque des « invalid command name » au prochain .set(). On
        bascule donc seulement la visibilité des contrôles propres aux faits.
        """
        bg = self.colors.get("bg_primary", "#212121")
        search_bg = self.colors.get("bg_secondary", "#2f2f2f")

        # Champ de recherche (persistant)
        if CTK_AVAILABLE:
            self._mem_search_entry = ctk.CTkEntry(
                self._mem_toolbar, textvariable=self._mem_query,
                placeholder_text="🔍 Rechercher…",
                fg_color=search_bg,
                border_color=self.colors.get("border", "#404040"),
                text_color=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 11), height=32,
            )
        else:
            self._mem_search_entry = tk.Entry(
                self._mem_toolbar, textvariable=self._mem_query
            )
        self._mem_search_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._mem_search_entry.bind("<Return>", lambda _e: self._mem_search())

        self._mem_button(self._mem_toolbar, "🔍", self._mem_search, width=44).pack(
            side="left", padx=(0, 6)
        )

        # Contrôles propres aux faits : catégorie + ajout (affichés à la demande)
        self._mem_facts_extra = self._mem_frame(self._mem_toolbar, bg)
        if CTK_AVAILABLE:
            ctk.CTkOptionMenu(
                self._mem_facts_extra, values=_FACT_CATEGORIES,
                variable=self._mem_category, command=lambda _v: self._mem_search(),
                fg_color=search_bg,
                button_color=self.colors.get("accent", "#ff6b47"),
                button_hover_color=self.colors.get("accent_hover", "#e85a3a"),
                text_color=self.colors.get("text_primary", "#ffffff"),
                font=("Segoe UI", 11), width=130,
            ).pack(side="left", padx=(0, 6))
        self._mem_button(
            self._mem_facts_extra, "➕ Ajouter", self._mem_add_fact,
            width=110, accent=True,
        ).pack(side="left")

        # Rafraîchir (toujours à droite)
        self._mem_button(self._mem_toolbar, "🔄", self._mem_reload, width=44).pack(
            side="right"
        )

        self._mem_update_toolbar()

    def _mem_update_toolbar(self):
        """Affiche/masque les contrôles propres aux faits selon l'onglet."""
        extra = getattr(self, "_mem_facts_extra", None)
        if extra is None:
            return
        if self._mem_tab == "facts":
            extra.pack(side="left", padx=(0, 6))
        else:
            extra.pack_forget()

    def _mem_search(self):
        self._mem_page = 0
        self._mem_edit_key = None
        self._mem_reload()

    # ─── Chargement / rendu ─────────────────────────────────────────────

    def _mem_reload(self):
        """Recharge la page courante (en thread) puis la rend."""
        store = self._mem_store()
        if store is None:
            self._mem_render([], 0, unavailable=True)
            return

        tab = self._mem_tab
        page = self._mem_page
        query = self._mem_query.get().strip()
        category = self._mem_category.get() if tab == "facts" else None
        if category == "Toutes":
            category = None
        offset = page * _PAGE_SIZE

        def _work():
            try:
                if tab == "facts":
                    items, total = store.list_facts(
                        query=query, category=category, limit=_PAGE_SIZE, offset=offset,
                    )
                else:
                    items, total = store.list_vectors(
                        tab, query=query, limit=_PAGE_SIZE, offset=offset,
                    )
            except Exception as exc:
                print(f"[MEM][GUI] Erreur chargement: {exc}")
                items, total = [], 0
            try:
                self.root.after(0, lambda: self._mem_render(items, total))
                self.root.after(0, self._mem_refresh_stats)
            except Exception:
                pass

        threading.Thread(target=_work, daemon=True).start()

    def _mem_refresh_stats(self):
        store = self._mem_store()
        if store is None or not getattr(self, "_mem_stats_label", None):
            return
        try:
            s = store.stats()
            txt = (f"{s['facts']} fait(s)  ·  {s['documents']} chunk(s) document  ·  "
                   f"{s['conversations']} entrée(s) conversation")
            self._mem_stats_label.configure(text=txt)
        except Exception:
            pass

    def _mem_render(self, items, total, unavailable: bool = False):
        win = getattr(self, "_mem_win", None)
        if win is None:
            return

        # Recaler la page si elle dépasse (ex. dernier élément supprimé)
        if not unavailable and total > 0 and self._mem_page * _PAGE_SIZE >= total:
            self._mem_page = max(0, (total - 1) // _PAGE_SIZE)
            self._mem_reload()
            return

        self._mem_current_items = items
        self._mem_current_total = total

        for w in self._mem_list.winfo_children():
            w.destroy()

        if unavailable:
            self._mem_label(
                self._mem_list, "  Mémoire indisponible (base non initialisée).",
                size=12, color=self.colors.get("text_secondary", "#9ca3af"),
                bg=self.colors.get("bg_secondary", "#181818"),
            ).pack(anchor="w", padx=10, pady=12)
            self._mem_update_pager(0)
            return

        if not items:
            empty = "Aucun résultat pour cette recherche." if self._mem_query.get().strip() \
                else "Rien ici pour le moment."
            self._mem_label(
                self._mem_list, f"  {empty}", size=12,
                color=self.colors.get("text_secondary", "#9ca3af"),
                bg=self.colors.get("bg_secondary", "#181818"),
            ).pack(anchor="w", padx=10, pady=12)
        else:
            for item in items:
                if self._mem_edit_key == self._mem_item_key(item):
                    self._mem_make_edit_row(item)
                else:
                    self._mem_make_row(item)

        self._mem_update_pager(total)

    def _mem_update_pager(self, total):
        pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
        cur = min(self._mem_page + 1, pages)
        try:
            self._mem_pager_label.configure(text=f"Page {cur} / {pages}   ({total})")
        except Exception:
            pass
        self._mem_set_btn_state(self._mem_prev_btn, self._mem_page > 0)
        self._mem_set_btn_state(self._mem_next_btn, self._mem_page < pages - 1)

    # ─── Lignes ─────────────────────────────────────────────────────────

    def _mem_make_row(self, item):
        row_bg = self.colors.get("bg_primary", "#212121")
        container = self._mem_frame(self._mem_list, row_bg, corner=6)
        container.pack(fill="x", padx=6, pady=4)

        top = self._mem_frame(container, row_bg)
        top.pack(fill="x", padx=8, pady=(6, 0))

        badge_text, badge_color = self._mem_badge(item)
        self._mem_label(top, badge_text, size=10, bold=True, color=badge_color,
                        bg=row_bg).pack(side="left", padx=(0, 8))

        # Actions à droite
        self._mem_button(top, "🗑", lambda it=item: self._mem_delete(it),
                         width=36, height=26, color="#ef4444").pack(side="right")
        self._mem_button(top, "✏️", lambda it=item: self._mem_start_edit(it),
                         width=36, height=26).pack(side="right", padx=(0, 4))

        content = self._mem_item_content(item)
        preview = content.replace("\n", " ").strip()
        if len(preview) > 120:
            preview = preview[:120] + "…"
        prev_lbl = self._mem_label(
            top, preview or "(vide)", size=12,
            color=self.colors.get("text_primary", "#ffffff"), bg=row_bg, anchor="w",
        )
        prev_lbl.pack(side="left", fill="x", expand=True)
        self._mem_tooltip(prev_lbl, content)

        prov = self._mem_provenance_line(item)
        self._mem_label(
            container, prov, size=9,
            color=self.colors.get("text_secondary", "#9ca3af"), bg=row_bg, anchor="w",
        ).pack(fill="x", padx=10, pady=(2, 6))

    def _mem_make_edit_row(self, item):
        row_bg = self.colors.get("bg_primary", "#212121")
        container = self._mem_frame(self._mem_list, row_bg, corner=6)
        container.pack(fill="x", padx=6, pady=4)

        badge_text, badge_color = self._mem_badge(item)
        self._mem_label(container, f"✏️  {badge_text}", size=10, bold=True,
                        color=badge_color, bg=row_bg).pack(anchor="w", padx=10, pady=(6, 2))

        content = self._mem_item_content(item)
        if CTK_AVAILABLE:
            editor = ctk.CTkTextbox(
                container, height=90,
                fg_color=self.colors.get("bg_secondary", "#2f2f2f"),
                text_color=self.colors.get("text_primary", "#ffffff"),
                border_color=self.colors.get("accent", "#ff6b47"), border_width=1,
                font=("Segoe UI", 12), wrap="word",
            )
        else:
            editor = tk.Text(container, height=4, wrap="word")
        editor.pack(fill="x", padx=10, pady=(0, 4))
        try:
            editor.insert("1.0", content)
        except Exception:
            pass

        btn_row = self._mem_frame(container, row_bg)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))
        self._mem_button(
            btn_row, "💾 Enregistrer",
            lambda it=item, ed=editor: self._mem_save_edit(it, ed.get("1.0", "end-1c")),
            accent=True, width=140,
        ).pack(side="left")
        self._mem_button(
            btn_row, "✖ Annuler", self._mem_cancel_edit, width=110,
        ).pack(side="left", padx=(6, 0))

        if self._mem_tab == "conversation":
            self._mem_label(
                container,
                "ⓘ La modification réécrit le message d'origine dans la conversation.",
                size=9, color=self.colors.get("text_secondary", "#9ca3af"), bg=row_bg,
            ).pack(anchor="w", padx=10, pady=(0, 6))

        try:
            editor.focus_set()
        except Exception:
            pass

    # ─── Édition ────────────────────────────────────────────────────────

    def _mem_start_edit(self, item):
        self._mem_edit_key = self._mem_item_key(item)
        self._mem_render(self._mem_current_items, self._mem_current_total)

    def _mem_cancel_edit(self):
        self._mem_edit_key = None
        self._mem_render(self._mem_current_items, self._mem_current_total)

    def _mem_save_edit(self, item, new_text):
        new_text = (new_text or "").strip()
        if not new_text:
            self._mem_notify("⚠️ Le contenu ne peut pas être vide", "info")
            return
        store = self._mem_store()
        if store is None:
            return
        kind = item.get("kind")

        def _work():
            try:
                if kind == "fact":
                    ok = store.update_fact(item["id"], new_text)
                else:
                    ok = store.update_vector(
                        item["id"], new_text, item.get("collection", "document"),
                        at_source=True, metadata=item.get("metadata"),
                    )
            except Exception as exc:
                print(f"[MEM][GUI] Erreur édition: {exc}")
                ok = False

            def _after():
                self._mem_edit_key = None
                self._mem_reload()
                self._mem_notify(
                    "✅ Modifié" if ok else "❌ Échec de la modification",
                    "success" if ok else "error",
                )
            try:
                self.root.after(0, _after)
            except Exception:
                pass

        threading.Thread(target=_work, daemon=True).start()

    # ─── Suppression ────────────────────────────────────────────────────

    def _mem_delete(self, item):
        self._show_memory_delete_confirmation(
            item, lambda at_source: self._mem_do_delete(item, at_source)
        )

    def _mem_do_delete(self, item, at_source: bool):
        store = self._mem_store()
        if store is None:
            return
        kind = item.get("kind")

        def _work():
            try:
                if kind == "fact":
                    ok = store.delete_fact(item["id"])
                else:
                    ok = store.delete_vector(
                        item["id"], item.get("collection", "document"),
                        at_source=at_source, metadata=item.get("metadata"),
                    )
            except Exception as exc:
                print(f"[MEM][GUI] Erreur suppression: {exc}")
                ok = False

            def _after():
                self._mem_reload()
                self._mem_notify(
                    "🗑️ Supprimé" if ok else "❌ Échec de la suppression",
                    "success" if ok else "error",
                )
            try:
                self.root.after(0, _after)
            except Exception:
                pass

        threading.Thread(target=_work, daemon=True).start()

    def _show_memory_delete_confirmation(self, item, on_confirm):
        """Dialogue de confirmation stylé (cohérent avec la confirmation MCP).

        Args:
            item: l'élément de mémoire à supprimer.
            on_confirm: callback appelé avec (at_source: bool) si l'utilisateur confirme.
        """
        accent = self.colors.get("accent", "#ff6b47")
        bg = self.colors.get("bg_secondary", "#1e1e1e")
        bg_dark = self.colors.get("bg_primary", "#121212")
        fg = self.colors.get("text_primary", "#ffffff")
        fg_dim = self.colors.get("text_secondary", "#aaaaaa")

        is_conv = item.get("kind") == "vector" and item.get("collection") == "conversation"
        preview = self._mem_item_content(item).replace("\n", " ").strip()
        if len(preview) > 70:
            preview = preview[:70] + "…"

        dialog = tk.Toplevel(self._mem_win or self.root)
        dialog.title("Confirmation de suppression")
        dialog.configure(bg=bg)
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.transient(self._mem_win or self.root)
        dialog.grab_set()

        h = 270 if is_conv else 230
        dialog.update_idletasks()
        w = 460
        base = self._mem_win or self.root
        try:
            x = base.winfo_x() + (base.winfo_width() - w) // 2
            y = base.winfo_y() + (base.winfo_height() - h) // 2
            dialog.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            dialog.geometry(f"{w}x{h}")

        tk.Label(dialog, text="⚠️", font=("Segoe UI", 32), bg=bg, fg=accent).pack(
            pady=(16, 4)
        )
        tk.Label(
            dialog, text="Supprimer définitivement cet élément ?",
            font=("Segoe UI", 11), bg=bg, fg=fg,
        ).pack()
        tk.Label(
            dialog, text=preview or "(vide)", font=("Consolas", 10, "bold"),
            bg=bg_dark, fg=accent, padx=12, pady=6, relief="groove", bd=1,
            wraplength=420, justify="left",
        ).pack(padx=20, pady=(8, 4))

        at_source_var = tk.BooleanVar(value=True)
        if is_conv:
            cb = tk.Checkbutton(
                dialog,
                text="Supprimer aussi le message d'origine\n(sinon réapparaît au prochain réindex)",
                variable=at_source_var, bg=bg, fg=fg_dim, selectcolor=bg_dark,
                activebackground=bg, activeforeground=fg, font=("Segoe UI", 9),
                justify="left", anchor="w",
            )
            cb.pack(padx=20, pady=(2, 4))

        btn_frame = tk.Frame(dialog, bg=bg)
        btn_frame.pack(pady=(8, 14))

        def _on_yes():
            at_source = at_source_var.get()
            try:
                dialog.destroy()
            except Exception:
                pass
            on_confirm(at_source)

        def _on_no():
            try:
                dialog.destroy()
            except Exception:
                pass

        if CTK_AVAILABLE:
            yes_btn = ctk.CTkButton(
                btn_frame, text="Oui, supprimer", fg_color=accent,
                hover_color=self.colors.get("accent_hover", "#e05535"),
                text_color="#ffffff", font=("Segoe UI", 12, "bold"),
                corner_radius=8, width=150, height=36, command=_on_yes,
            )
            no_btn = ctk.CTkButton(
                btn_frame, text="Non, annuler", fg_color="#2a2a2a",
                hover_color="#3a3a3a", text_color="#ffffff",
                font=("Segoe UI", 12), corner_radius=8, width=150, height=36,
                command=_on_no,
            )
        else:
            yes_btn = tk.Button(btn_frame, text="Oui, supprimer", bg=accent,
                                fg="#ffffff", font=("Segoe UI", 12, "bold"),
                                relief="flat", padx=16, pady=6, command=_on_yes)
            no_btn = tk.Button(btn_frame, text="Non, annuler", bg="#2a2a2a",
                               fg="#ffffff", font=("Segoe UI", 12), relief="flat",
                               padx=16, pady=6, command=_on_no)
        no_btn.pack(side="left", padx=(0, 10))
        yes_btn.pack(side="left")

        dialog.protocol("WM_DELETE_WINDOW", _on_no)
        dialog.bind("<Escape>", lambda _e: _on_no())

    # ─── Ajout de fait ──────────────────────────────────────────────────

    def _mem_add_fact(self):
        store = self._mem_store()
        if store is None:
            messagebox.showwarning("Indisponible", "La mémoire n'est pas disponible.",
                                   parent=self._mem_win)
            return
        categories = ["general", "preference", "decision", "person", "procedure", "technical"]
        cat = simpledialog.askstring(
            "Catégorie", f"Catégorie ({', '.join(categories)}) :",
            initialvalue="general", parent=self._mem_win,
        )
        if not cat or cat.strip() not in categories:
            cat = "general"
        content = simpledialog.askstring("Nouveau fait", "Contenu :", parent=self._mem_win)
        if not content or not content.strip():
            return
        value = content.strip()
        key = value.split("\n", 1)[0].strip()[:80] or "fait manuel"
        fid = store.add_fact(category=cat.strip(), key=key, value=value, source="manual")
        if fid:
            self._mem_page = 0
            self._mem_reload()
            self._mem_notify("✅ Fait ajouté", "success")
        else:
            self._mem_notify("❌ Échec de l'ajout", "error")

    # ─── Pagination ─────────────────────────────────────────────────────

    def _mem_prev_page(self):
        if self._mem_page > 0:
            self._mem_page -= 1
            self._mem_edit_key = None
            self._mem_reload()

    def _mem_next_page(self):
        pages = max(1, (self._mem_current_total + _PAGE_SIZE - 1) // _PAGE_SIZE)
        if self._mem_page < pages - 1:
            self._mem_page += 1
            self._mem_edit_key = None
            self._mem_reload()

    # ─── Helpers données ────────────────────────────────────────────────

    @staticmethod
    def _mem_item_key(item):
        if item.get("kind") == "fact":
            return ("fact", item.get("id"))
        return (item.get("collection", "document"), item.get("id"))

    @staticmethod
    def _mem_item_content(item):
        if item.get("kind") == "fact":
            return str(item.get("value", "") or "")
        return str(item.get("content", "") or "")

    def _mem_provenance_line(self, item):
        store = self._mem_store()
        base = ""
        if store is not None:
            try:
                base = store.describe_provenance(item)
            except Exception:
                base = ""
        if item.get("kind") == "fact":
            key = item.get("key", "")
            return f"🔑 {key}   ·   {base}" if key else base
        return base

    def _mem_badge(self, item):
        if item.get("kind") == "fact":
            cat = item.get("category", "general")
            return cat, _CAT_COLORS.get(cat, "#9ca3af")
        meta = item.get("metadata", {}) or {}
        if item.get("collection") == "conversation":
            role = meta.get("role", "")
            if role == "user":
                return "🧑 vous", "#10b981"
            return "🤖 assistant", "#3b82f6"
        return "📄 document", "#f59e0b"

    def _mem_notify(self, text, level="info", ms=2000):
        if hasattr(self, "show_notification"):
            try:
                self.show_notification(text, level, ms)
                return
            except Exception:
                pass

    def _mem_tooltip(self, widget, text):
        fn = getattr(self, "_kb_attach_tooltip", None)
        if fn is None or not text:
            return
        try:
            fn(widget, text)
        except Exception:
            pass

    # ─── Helpers widgets ────────────────────────────────────────────────

    def _mem_frame(self, parent, color=None, corner=0):
        bg = color or self.colors.get("bg_primary", "#212121")
        if CTK_AVAILABLE:
            return ctk.CTkFrame(parent, fg_color=bg, corner_radius=corner)
        return tk.Frame(parent, bg=bg)

    def _mem_label(self, parent, text, size=12, bold=False, color=None, bg=None,
                   anchor=None):
        c = color or self.colors.get("text_primary", "#ffffff")
        font = ("Segoe UI", size, "bold" if bold else "normal")
        if CTK_AVAILABLE:
            lbl = ctk.CTkLabel(parent, text=text, font=font, text_color=c,
                               fg_color="transparent")
            if anchor:
                try:
                    lbl.configure(anchor=anchor, justify="left")
                except Exception:
                    pass
            return lbl
        return tk.Label(parent, text=text, font=font, fg=c,
                        bg=bg or self.colors.get("bg_primary", "#212121"),
                        anchor=anchor or "w", justify="left")

    def _mem_button(self, parent, text, command, color=None, width=None, height=32,
                    accent=False):
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
            kw = dict(text=text, command=command, fg_color=bg, hover_color=hover,
                      text_color=tc, font=("Segoe UI", 12), height=height,
                      corner_radius=6)
            if width:
                kw["width"] = width
            return ctk.CTkButton(parent, **kw)
        btn = tk.Button(parent, text=text, command=command, bg=bg, fg=tc,
                        font=("Segoe UI", 11), relief="flat")
        return btn

    def _mem_set_btn_state(self, btn, enabled: bool):
        try:
            btn.configure(state=("normal" if enabled else "disabled"))
        except Exception:
            pass
