"""Édition + regénération de messages utilisateur avec branchement.

Permet d'éditer un message utilisateur précédent puis de regénérer la réponse,
en conservant l'ancienne version (navigation ‹ k/n › entre les variantes d'un
même tour de conversation).

Modèle de données (léger, à plat) :
  ``self._turn_branches`` : dict ``mid_du_message_utilisateur -> {
        "versions": [ {"user": str, "ai": str|None,
                       "attachments": [(path, type), ...],
                       "image_path": str|None,
                       "tail": [entrées d'historique en aval]}, ... ],
        "current":  index_de_la_version_affichée,
  }``

``tail`` porte la suite de la conversation propre à chaque variante : sans lui,
revenir sur une ancienne version supprimerait définitivement les messages
échangés après la regénération.

La clé est le ``mid`` (identifiant stable posé par ``add_message_bubble``) et
non la position du message : deux variantes pouvant avoir des queues de
longueurs différentes, une même position ne désigne pas le même message d'une
branche à l'autre — indexer par position rattachait des variantes au mauvais
message.

Les pièces jointes suivent la variante : éditer un message conserve ses
fichiers/images, et l'image de vision est ré-encodée depuis son chemin avant
la regénération (cf. ``_restore_attachment_context``).

Un « tour » correspond à un message utilisateur et à la réponse IA qui le suit.
Éditer un message tronque la conversation à partir de ce tour, archive la
variante courante, puis regénère. Les messages situés en aval d'un tour édité
en milieu de conversation sont remplacés (comportement de branche, façon
ChatGPT) — l'utilisateur est prévenu avant.

Le rendu s'appuie sur ``add_message_bubble(..., instant=True)`` (même chemin que
le chargement de session) pour reconstruire l'affichage après un changement de
branche.
"""

import os
import re
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from uuid import uuid4

# Ligne de pièce jointe telle que produite par `_build_attachment_lines`
ATTACH_LINE_RE = re.compile(r"^(?:📎|🖼️|🖼)\s+\S")


class MessageEditingMixin:
    """Édition de messages utilisateur + branchement des regénérations."""

    # ── Helpers de structure ───────────────────────────────────────────────

    def _branches(self):
        if not hasattr(self, "_turn_branches"):
            self._turn_branches = {}
        return self._turn_branches

    def _turn_key(self, index):
        """Identifiant stable du message utilisateur à l'index donné.

        Les branches sont indexées par cet identifiant et NON par la position
        du message : deux variantes d'un même tour peuvent avoir des queues de
        longueurs différentes, si bien qu'une même position ne désigne pas le
        même message d'une branche à l'autre.
        """
        try:
            return self.conversation_history[index].get("mid")
        except (IndexError, AttributeError):
            return None

    def _turn_start_index(self, turn_key):
        """Index dans conversation_history du message portant `turn_key`."""
        if not turn_key:
            return None
        for i, m in enumerate(self.conversation_history):
            if m.get("is_user") and m.get("mid") == turn_key:
                return i
        return None

    def _turn_end_index(self, start):
        """Index du premier message situé APRÈS le tour commençant à `start`.

        Un tour = le message utilisateur + la réponse IA qui le suit (si elle
        existe déjà). Tout ce qui vient ensuite appartient à la « queue » de la
        variante affichée.
        """
        history = self.conversation_history
        has_ai = start + 1 < len(history) and not history[start + 1].get("is_user")
        return start + 2 if has_ai else start + 1

    def _persist_version(self, branch, start):
        """Recopie l'état affiché du tour `start` dans la variante courante.

        Inclut la queue (messages en aval) : sans elle, basculer de variante
        ferait disparaître définitivement la suite de la conversation.
        """
        history = self.conversation_history
        version = branch["versions"][branch["current"]]
        if start < len(history):
            entry = history[start]
            version["user"] = entry.get("text", "")
            version["attachments"] = list(entry.get("attachments") or [])
            version["image_path"] = entry.get("image_path")
        end = self._turn_end_index(start)
        has_ai = end == start + 2
        version["ai"] = history[start + 1].get("text", "") if has_ai else None
        version["ai_mid"] = history[start + 1].get("mid") if has_ai else None
        version["tail"] = [dict(m) for m in history[end:]]

    # ── Enregistrement des bulles (hook depuis add_message_bubble) ──────────

    def _register_bubble(self, index, container, is_user, text):
        """Attache timestamp + contrôles (📝 / 📋 / ‹ k/n ›) à une bulle utilisateur."""
        if not is_user:
            return
        self._add_edit_controls(container, self._turn_key(index), index, text)

    def _add_edit_controls(self, container, turn_key, index, text=""):
        """Crée la rangée « hh:mm 📝 📋 ‹ k/n › » sous une bulle utilisateur.

        Le timestamp vit ici (et non dans la bulle bleue) pour que la bulle
        n'occupe en hauteur que le texte du message.
        """
        colors = getattr(self, "colors", {})
        bg = colors.get("bg_chat", "#212121")
        dim = colors.get("text_secondary", "#9ca3af")
        accent = colors.get("accent", "#3b82f6")

        actions = tk.Frame(container, bg=bg)
        # Aligné sous la bulle (même retrait que le centrage des messages)
        actions.grid(row=1, column=0, sticky="w", padx=(250, 0), pady=(0, 2))

        # ── Timestamp (sorti de la bulle) ──
        try:
            stamp = self.conversation_history[index].get("timestamp")
        except (IndexError, AttributeError):
            stamp = None
        tk.Label(
            actions, text=self._format_stamp(stamp),
            font=("Segoe UI", 9), fg="#b3b3b3", bg=bg, padx=2,
        ).pack(side="left", padx=(36, 0))

        editable = isinstance(text, str) and bool(text.strip())

        # ── 📝 Modifier (icône seule, à droite du timestamp) ──
        if editable:
            edit_btn = tk.Label(
                actions, text="📝", font=("Segoe UI Emoji", 10), fg=dim, bg=bg,
                cursor="hand2", padx=2,
            )
            edit_btn.pack(side="left", padx=(10, 0))
            edit_btn.bind("<Button-1>", lambda _e, i=index: self._begin_edit(i))
            edit_btn.bind("<Enter>", lambda _e: edit_btn.configure(fg=accent))
            edit_btn.bind("<Leave>", lambda _e: edit_btn.configure(fg=dim))

        # ── 📋 Copier tout le message ──
        if isinstance(text, str) and text:
            copy_btn = tk.Label(
                actions, text="📋", font=("Segoe UI Emoji", 10), fg=dim, bg=bg,
                cursor="hand2", padx=2,
            )
            copy_btn.pack(side="left", padx=(6, 0))
            copy_btn.bind(
                "<Button-1>", lambda _e, t=text, b=copy_btn: self._copy_message(t, b)
            )
            copy_btn.bind("<Enter>", lambda _e: copy_btn.configure(fg=accent))
            copy_btn.bind("<Leave>", lambda _e: copy_btn.configure(fg=dim))

        branch = self._branches().get(turn_key)
        if branch and len(branch["versions"]) > 1:
            cur = branch["current"]
            total = len(branch["versions"])

            prev_btn = tk.Label(
                actions, text="‹", font=("Segoe UI", 12, "bold"),
                fg=accent if cur > 0 else dim, bg=bg,
                cursor="hand2" if cur > 0 else "arrow", padx=4,
            )
            prev_btn.pack(side="left", padx=(12, 0))
            if cur > 0:
                prev_btn.bind(
                    "<Button-1>",
                    lambda _e, k=turn_key, v=cur - 1: self._navigate(k, v),
                )

            tk.Label(
                actions, text=f"{cur + 1}/{total}", font=("Segoe UI", 9),
                fg=dim, bg=bg, padx=2,
            ).pack(side="left")

            next_btn = tk.Label(
                actions, text="›", font=("Segoe UI", 12, "bold"),
                fg=accent if cur < total - 1 else dim, bg=bg,
                cursor="hand2" if cur < total - 1 else "arrow", padx=4,
            )
            next_btn.pack(side="left")
            if cur < total - 1:
                next_btn.bind(
                    "<Button-1>",
                    lambda _e, k=turn_key, v=cur + 1: self._navigate(k, v),
                )

    @staticmethod
    def _format_stamp(stamp):
        """Formate un timestamp en « hh:mm », qu'il soit datetime ou chaîne.

        Après un aller-retour par les sessions, `timestamp` revient sous forme
        de chaîne ISO (`json.dump(..., default=str)`) et n'a plus de strftime.
        """
        if isinstance(stamp, datetime):
            return stamp.strftime("%H:%M")
        if isinstance(stamp, str):
            try:
                return datetime.fromisoformat(stamp).strftime("%H:%M")
            except ValueError:
                return ""
        return datetime.now().strftime("%H:%M")

    def _copy_message(self, text, button=None):
        """Copie l'intégralité du message utilisateur dans le presse-papier."""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            if hasattr(self, "show_copy_notification"):
                self.show_copy_notification("📋 Message copié !")
        except Exception as exc:
            print(f"⚠️ [Edit] Copie échouée : {exc}")
            if hasattr(self, "show_copy_notification"):
                self.show_copy_notification("❌ Erreur de copie")
            return

        # Retour visuel bref sur l'icône
        if button is not None:
            def _restore():
                try:
                    button.configure(text="📋")
                except tk.TclError:
                    pass  # bulle reconstruite entre-temps

            try:
                button.configure(text="✅")
                button.after(1200, _restore)
            except tk.TclError:
                pass

    # ── Pièces jointes ──────────────────────────────────────────────────────

    @staticmethod
    def _split_attachments(text):
        """Sépare le corps du message des lignes de pièces jointes finales.

        `send_message` construit la bulle en suffixant `📎 nom` / `🖼️ nom`
        (cf. `_build_attachment_lines`). L'édition ne doit porter que sur le
        corps ; les lignes de pièces jointes sont réappliquées telles quelles.
        """
        lines = (text or "").split("\n")
        attach = []
        while lines and ATTACH_LINE_RE.match(lines[-1]):
            attach.insert(0, lines.pop())
        return "\n".join(lines).rstrip(), attach

    def _restore_attachment_context(self, entry):
        """Réarme le contexte des pièces jointes avant une regénération.

        Les documents (PDF/DOCX/code…) restent indexés dans le contexte de
        `custom_ai`, donc rien à faire pour eux. L'image de vision, elle, est
        consommée puis remise à None après le premier envoi : on la ré-encode
        depuis son chemin, sinon l'IA regénérerait « à l'aveugle ».
        """
        image_path = (entry or {}).get("image_path")
        if not image_path or not os.path.isfile(image_path):
            if image_path:
                print(f"⚠️ [Edit] Image jointe introuvable : {image_path}")
            return
        try:
            # Repositionne _pending_image_base64 / _pending_image_path
            self._process_image_file(image_path)
        except Exception as exc:
            print(f"⚠️ [Edit] Ré-encodage de l'image échoué : {exc}")

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

        turn_key = self._turn_key(index)
        start = self._turn_start_index(turn_key)
        if start is None or start + 1 >= len(self.conversation_history):
            self.show_notification(
                "Ce message n'a pas encore de réponse à regénérer.", "info", 2500
            )
            return

        # N'éditer que le corps : les lignes 📎/🖼️ restent attachées au message
        original, attach_lines = self._split_attachments(entry.get("text", ""))

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

        if attach_lines:
            tk.Label(
                win,
                text="Pièces jointes conservées : " + ", ".join(attach_lines),
                bg=bg, fg=colors.get("text_secondary", "#9ca3af"),
                font=("Segoe UI", 9), anchor="w", wraplength=520, justify="left",
            ).pack(fill="x", padx=14, pady=(6, 0))

        btns = tk.Frame(win, bg=bg)
        btns.pack(fill="x", padx=14, pady=12)

        def _cancel(_e=None):
            win.destroy()

        def _save(_e=None):
            new_text = editor.get("1.0", "end-1c").strip()
            win.destroy()
            if not new_text or new_text == original.strip():
                return
            self._apply_edit(turn_key, new_text)

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

    def _apply_edit(self, turn_key, new_text):
        """Archive la variante courante, tronque, puis regénère avec new_text."""
        start = self._turn_start_index(turn_key)
        if start is None:
            return

        history = self.conversation_history
        old_entry = history[start]
        old_user = old_entry.get("text", "")
        attachments = list(old_entry.get("attachments") or [])
        image_path = old_entry.get("image_path")
        _, attach_lines = self._split_attachments(old_user)

        # Avertir si des messages en aval sortent de l'affichage (branche en
        # milieu de conversation). Ils ne sont pas perdus : _persist_version les
        # archive dans la variante courante, restaurée en revenant via ‹ ›.
        downstream = history[self._turn_end_index(start):]
        if downstream:
            if not messagebox.askyesno(
                "Modifier le message",
                "Les messages suivants laisseront place à la nouvelle réponse.\n"
                "Ils restent accessibles en revenant sur l'ancienne version "
                "via ‹ ›. Continuer ?",
                parent=self.root,
            ):
                return

        # La bulle éditée réaffiche les mêmes lignes de pièces jointes
        bubble_text = new_text
        if attach_lines:
            bubble_text = (new_text.rstrip() + "\n" + "\n".join(attach_lines)).strip()

        version_meta = {"attachments": attachments, "image_path": image_path}

        branches = self._branches()
        branch = branches.get(turn_key)
        if branch is None:
            branch = {"versions": [{}], "current": 0}
            branches[turn_key] = branch
        # Archiver l'état affiché (texte, PJ, réponse IA ET messages en aval)
        # dans la variante courante avant d'en créer une nouvelle.
        self._persist_version(branch, start)

        # La nouvelle variante démarre sans queue : sa suite se construira au
        # fil des messages envoyés après la regénération.
        branch["versions"].append(
            dict(version_meta, user=bubble_text, ai=None, tail=[])
        )
        branch["current"] = len(branch["versions"]) - 1

        # Tronquer à partir du tour édité, reconstruire l'amont, regénérer
        self.conversation_history = history[:start]
        self._rerender_all()
        self._restore_attachment_context(
            {"attachments": attachments, "image_path": image_path}
        )
        self._regenerate(new_text, bubble_text, attachments, image_path, turn_key)

    # ── Navigation entre versions ───────────────────────────────────────────

    def _navigate(self, turn_key, target_version):
        """Bascule l'affichage du tour `turn_key` vers `target_version`."""
        if getattr(self, "is_thinking", False) or getattr(self, "_streaming_mode", False):
            self.show_notification(
                "⏳ Attendez la fin de la réponse en cours.", "info", 2000
            )
            return
        branches = self._branches()
        branch = branches.get(turn_key)
        versions = branch["versions"] if branch else []
        if not 0 <= target_version < len(versions):
            return

        start = self._turn_start_index(turn_key)
        if start is None:
            return

        history = self.conversation_history
        # Persister la variante actuellement affichée (queue comprise) avant
        # de basculer, sinon la suite de la conversation serait perdue.
        self._persist_version(branch, start)

        # Construire la conversation jusqu'à la variante cible
        version = branch["versions"][target_version]
        branch["current"] = target_version
        new_history = history[:start]
        # Le message utilisateur reprend le mid du tour : c'est lui qui porte
        # la branche, quelle que soit la variante affichée.
        new_history.append({
            "text": version["user"], "is_user": True,
            "timestamp": version.get("timestamp") or datetime.now(), "type": "text",
            "attachments": list(version.get("attachments") or []),
            "image_path": version.get("image_path"),
            "mid": turn_key,
        })
        if version.get("ai") is not None:
            new_history.append({
                "text": version["ai"], "is_user": False,
                "timestamp": datetime.now(), "type": "text",
                "mid": version.get("ai_mid") or uuid4().hex,
            })
        # Restaurer les messages échangés en aval dans cette variante
        new_history.extend(dict(m) for m in version.get("tail") or [])
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
            # `mid` est repropagé : le régénérer détacherait les branches des
            # messages auxquels elles appartiennent.
            self.add_message_bubble(
                content,
                is_user=msg.get("is_user", True),
                instant=True,
                attachments=msg.get("attachments"),
                image_path=msg.get("image_path"),
                mid=msg.get("mid"),
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

    def _regenerate(
        self, user_text, bubble_text=None, attachments=None, image_path=None,
        mid=None,
    ):
        """Réaffiche le message édité et relance le pipeline IA (streaming).

        `user_text` est le corps envoyé au modèle ; `bubble_text` est ce qui
        s'affiche (corps + lignes de pièces jointes). `mid` reprend l'identifiant
        du tour édité pour que la nouvelle bulle reste rattachée à sa branche.
        """
        try:
            if hasattr(self, "_dismiss_home_screen"):
                self._dismiss_home_screen()

            self._last_bubble_is_user = True
            self.add_message_bubble(
                bubble_text or user_text,
                is_user=True,
                attachments=attachments,
                image_path=image_path,
                mid=mid,
            )
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
