"""Édition + regénération de messages utilisateur avec branchement.

Permet d'éditer un message utilisateur précédent puis de regénérer la réponse,
en conservant l'ancienne version (navigation ‹ k/n › entre les variantes d'un
même tour de conversation).

Modèle de données (léger, à plat) :
  ``self._turn_branches`` : dict ``ordinal_du_tour_utilisateur -> {
        "versions": [ {"user": str, "ai": str|None}, ... ],
        "current":  index_de_la_version_affichée,
  }``

Un « tour » correspond à un message utilisateur et à la réponse IA qui le suit.
Éditer un message tronque la conversation à partir de ce tour, archive la
variante courante, puis regénère. Les messages situés en aval d'un tour édité
en milieu de conversation sont remplacés (comportement de branche, façon
ChatGPT) — l'utilisateur est prévenu avant.

Le rendu s'appuie sur ``add_message_bubble(..., instant=True)`` (même chemin que
le chargement de session) pour reconstruire l'affichage après un changement de
branche.
"""

import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

try:
    import customtkinter as ctk  # noqa: F401

    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False


class MessageEditingMixin:
    """Édition de messages utilisateur + branchement des regénérations."""

    # ── Helpers de structure ───────────────────────────────────────────────

    def _branches(self):
        if not hasattr(self, "_turn_branches"):
            self._turn_branches = {}
        return self._turn_branches

    def _user_ordinal(self, index):
        """Numéro d'ordre (0-based) du message utilisateur à l'index donné."""
        return sum(
            1 for m in self.conversation_history[: index + 1] if m.get("is_user")
        ) - 1

    def _turn_start_index(self, ordinal):
        """Index dans conversation_history du ordinal-ième message utilisateur."""
        count = -1
        for i, m in enumerate(self.conversation_history):
            if m.get("is_user"):
                count += 1
                if count == ordinal:
                    return i
        return None

    # ── Enregistrement des bulles (hook depuis add_message_bubble) ──────────

    def _register_bubble(self, index, container, is_user, text):
        """Attache les contrôles d'édition / navigation à une bulle utilisateur."""
        if not is_user:
            return
        if not isinstance(text, str) or not text.strip():
            return
        ordinal = self._user_ordinal(index)
        self._add_edit_controls(container, ordinal, index)

    def _add_edit_controls(self, container, ordinal, index):
        """Crée la rangée ✏️ + ‹ k/n › sous une bulle utilisateur."""
        colors = getattr(self, "colors", {})
        bg = colors.get("bg_chat", "#212121")
        dim = colors.get("text_secondary", "#9ca3af")
        accent = colors.get("accent", "#3b82f6")

        bar = tk.Frame(container, bg=bg)
        # Aligné sous la bulle (même retrait que le centrage des messages)
        bar.grid(row=1, column=0, sticky="w", padx=(250, 0), pady=(0, 2))

        edit_btn = tk.Label(
            bar, text="✏️ Modifier", font=("Segoe UI", 9), fg=dim, bg=bg,
            cursor="hand2", padx=2,
        )
        edit_btn.pack(side="left")
        edit_btn.bind("<Button-1>", lambda _e, i=index: self._begin_edit(i))
        edit_btn.bind("<Enter>", lambda _e: edit_btn.configure(fg=accent))
        edit_btn.bind("<Leave>", lambda _e: edit_btn.configure(fg=dim))

        branch = self._branches().get(ordinal)
        if branch and len(branch["versions"]) > 1:
            cur = branch["current"]
            total = len(branch["versions"])

            prev_btn = tk.Label(
                bar, text="‹", font=("Segoe UI", 12, "bold"),
                fg=accent if cur > 0 else dim, bg=bg,
                cursor="hand2" if cur > 0 else "arrow", padx=4,
            )
            prev_btn.pack(side="left", padx=(12, 0))
            if cur > 0:
                prev_btn.bind(
                    "<Button-1>",
                    lambda _e, o=ordinal, v=cur - 1: self._navigate(o, v),
                )

            tk.Label(
                bar, text=f"{cur + 1}/{total}", font=("Segoe UI", 9),
                fg=dim, bg=bg, padx=2,
            ).pack(side="left")

            next_btn = tk.Label(
                bar, text="›", font=("Segoe UI", 12, "bold"),
                fg=accent if cur < total - 1 else dim, bg=bg,
                cursor="hand2" if cur < total - 1 else "arrow", padx=4,
            )
            next_btn.pack(side="left")
            if cur < total - 1:
                next_btn.bind(
                    "<Button-1>",
                    lambda _e, o=ordinal, v=cur + 1: self._navigate(o, v),
                )

    # ── Édition ─────────────────────────────────────────────────────────────

    def _begin_edit(self, index):
        """Ouvre un petit éditeur pour le message utilisateur à l'index donné."""
        if getattr(self, "is_thinking", False) or getattr(self, "_streaming_mode", False):
            self.show_notification(
                "⏳ Attendez la fin de la réponse en cours.", "info", 2000
            )
            return
        if index >= len(self.conversation_history):
            return
        entry = self.conversation_history[index]
        if not entry.get("is_user"):
            return

        ordinal = self._user_ordinal(index)
        start = self._turn_start_index(ordinal)
        if start is None or start + 1 >= len(self.conversation_history):
            self.show_notification(
                "Ce message n'a pas encore de réponse à regénérer.", "info", 2500
            )
            return

        original = entry.get("text", "")

        colors = getattr(self, "colors", {})
        bg = colors.get("bg_secondary", "#2f2f2f")
        fg = colors.get("text_primary", "#ffffff")
        accent = colors.get("accent", "#3b82f6")
        input_bg = colors.get("input_bg", "#262626")

        win = tk.Toplevel(self.root)
        win.title("Modifier le message")
        win.configure(bg=bg)
        win.transient(self.root)
        win.geometry("560x240")

        tk.Label(
            win, text="Modifier votre message puis regénérer la réponse :",
            bg=bg, fg=fg, font=("Segoe UI", 11), anchor="w",
        ).pack(fill="x", padx=14, pady=(14, 6))

        editor = tk.Text(
            win, bg=input_bg, fg=fg, insertbackground=fg, relief="flat",
            font=("Segoe UI", 12), wrap="word", height=6, bd=8,
        )
        editor.pack(fill="both", expand=True, padx=14)
        editor.insert("1.0", original)
        editor.focus_set()

        btns = tk.Frame(win, bg=bg)
        btns.pack(fill="x", padx=14, pady=12)

        def _cancel(_e=None):
            win.destroy()

        def _save(_e=None):
            new_text = editor.get("1.0", "end-1c").strip()
            win.destroy()
            if not new_text or new_text == original.strip():
                return
            self._apply_edit(ordinal, new_text)

        tk.Button(
            btns, text="Annuler", command=_cancel, bg=bg, fg=fg,
            relief="flat", font=("Segoe UI", 11), padx=12, cursor="hand2",
        ).pack(side="right")
        tk.Button(
            btns, text="Regénérer ↻", command=_save, bg=accent, fg="#ffffff",
            relief="flat", font=("Segoe UI", 11, "bold"), padx=14, cursor="hand2",
        ).pack(side="right", padx=(0, 8))

        win.bind("<Escape>", _cancel)
        win.bind("<Control-Return>", _save)

    def _apply_edit(self, ordinal, new_text):
        """Archive la variante courante, tronque, puis regénère avec new_text."""
        start = self._turn_start_index(ordinal)
        if start is None:
            return

        history = self.conversation_history
        old_user = history[start].get("text", "")
        old_ai = None
        if start + 1 < len(history) and not history[start + 1].get("is_user"):
            old_ai = history[start + 1].get("text", "")

        # Avertir si des messages en aval vont être remplacés (branche en milieu)
        downstream = history[start + 2:]
        if downstream:
            if not messagebox.askyesno(
                "Modifier le message",
                "Les messages suivants seront remplacés par la nouvelle réponse.\n"
                "L'ancienne version reste accessible via ‹ ›. Continuer ?",
                parent=self.root,
            ):
                return

        branches = self._branches()
        branch = branches.get(ordinal)
        if branch is None:
            branch = {"versions": [{"user": old_user, "ai": old_ai}], "current": 0}
            branches[ordinal] = branch
        else:
            cur = branch["current"]
            branch["versions"][cur]["user"] = old_user
            branch["versions"][cur]["ai"] = old_ai

        branch["versions"].append({"user": new_text, "ai": None})
        branch["current"] = len(branch["versions"]) - 1

        # Tronquer à partir du tour édité, reconstruire l'amont, regénérer
        self.conversation_history = history[:start]
        self._rerender_all()
        self._regenerate(new_text)

    # ── Navigation entre versions ───────────────────────────────────────────

    def _navigate(self, ordinal, target_version):
        """Bascule l'affichage du tour `ordinal` vers `target_version`."""
        if getattr(self, "is_thinking", False) or getattr(self, "_streaming_mode", False):
            self.show_notification(
                "⏳ Attendez la fin de la réponse en cours.", "info", 2000
            )
            return
        branches = self._branches()
        branch = branches.get(ordinal)
        if not branch or not (0 <= target_version < len(branch["versions"])):
            return

        start = self._turn_start_index(ordinal)
        if start is None:
            return

        history = self.conversation_history
        # Persister la variante actuellement affichée depuis l'état live
        cur = branch["current"]
        if start < len(history):
            branch["versions"][cur]["user"] = history[start].get("text", "")
        if start + 1 < len(history) and not history[start + 1].get("is_user"):
            branch["versions"][cur]["ai"] = history[start + 1].get("text", "")

        # Construire la conversation jusqu'à la variante cible
        version = branch["versions"][target_version]
        branch["current"] = target_version
        new_history = history[:start]
        new_history.append({
            "text": version["user"], "is_user": True,
            "timestamp": datetime.now(), "type": "text",
        })
        if version.get("ai") is not None:
            new_history.append({
                "text": version["ai"], "is_user": False,
                "timestamp": datetime.now(), "type": "text",
            })
        self.conversation_history = new_history
        self._rerender_all()

    # ── Reconstruction de l'affichage ───────────────────────────────────────

    def _rerender_all(self):
        """Détruit toutes les bulles et reconstruit depuis conversation_history."""
        snapshot = list(self.conversation_history)
        try:
            for w in self.chat_frame.winfo_children():
                w.destroy()
        except Exception as exc:
            print(f"⚠️ [Edit] Nettoyage du chat échoué : {exc}")

        self.conversation_history = []
        self._message_widgets = []
        self.current_message_container = None

        for msg in snapshot:
            if msg.get("type") == "file_generation_placeholder":
                continue
            content = msg.get("text", "")
            if not content:
                continue
            self.add_message_bubble(
                content, is_user=msg.get("is_user", True), instant=True
            )

        self._rewind_engine_history()
        try:
            self.root.after(60, self.scroll_to_bottom)
        except Exception:
            pass

    def _rewind_engine_history(self):
        """Réaligne l'historique du LLM local sur la conversation affichée."""
        try:
            llm = None
            local_ai = getattr(self.ai_engine, "local_ai", None)
            if local_ai is not None:
                llm = getattr(local_ai, "local_llm", None)
            if llm is None and getattr(self, "custom_ai", None) is not None:
                llm = getattr(self.custom_ai, "local_llm", None)
            if llm is None:
                return
            if hasattr(llm, "clear_history"):
                llm.clear_history()
            if hasattr(llm, "add_to_history"):
                for msg in self.conversation_history:
                    role = "user" if msg.get("is_user") else "assistant"
                    llm.add_to_history(role, msg.get("text", ""))
        except Exception as exc:
            print(f"⚠️ [Edit] Réalignement historique LLM échoué : {exc}")

    # ── Regénération ─────────────────────────────────────────────────────────

    def _regenerate(self, user_text):
        """Réaffiche le message édité et relance le pipeline IA (streaming)."""
        try:
            if hasattr(self, "_dismiss_home_screen"):
                self._dismiss_home_screen()

            self._last_bubble_is_user = True
            self.add_message_bubble(user_text, is_user=True)
            self.scroll_to_bottom()
            self.show_thinking_animation()

            self.current_request_id = getattr(self, "current_request_id", 0) + 1
            request_id = self.current_request_id
            self.is_interrupted = False

            threading.Thread(
                target=self.quel_handle_message_with_id,
                args=(user_text, request_id),
                daemon=True,
            ).start()
        except Exception as exc:
            print(f"⚠️ [Edit] Regénération échouée : {exc}")
            try:
                self.set_input_state(True)
            except Exception:
                pass
