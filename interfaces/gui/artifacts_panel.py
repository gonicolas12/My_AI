"""Volet « Artifacts » pour ModernAIGUI.

Affiche un rendu live du HTML/CSS/SVG généré par l'IA, à côté du chat,
façon Claude Artifacts. Rendu embarqué via ``tkinterweb`` quand disponible
(léger, pur Python, mais CSS limité), avec un fallback systématique
« Ouvrir dans le navigateur » pour la fidélité totale.

100% local : aucune ressource réseau n'est chargée.
"""

import tkinter as tk
import webbrowser

try:
    import customtkinter as ctk

    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    ctk = tk

# Rendu HTML embarqué optionnel. Absence gérée proprement (cf. _build_body).
try:
    from tkinterweb import HtmlFrame  # type: ignore

    TKINTERWEB_AVAILABLE = True
except Exception:
    TKINTERWEB_AVAILABLE = False
    HtmlFrame = None

from interfaces.artifacts import build_preview_document, write_artifact_html

# Largeur par défaut du volet (px). Il occupe la colonne 1 du content_container.
_PANEL_WIDTH = 520


class ArtifactsPanelMixin:
    """Volet repliable de preview des artifacts (HTML/SVG)."""

    # ── Construction paresseuse ───────────────────────────────────────────

    def _ensure_artifacts_panel(self):
        """Crée le volet (une seule fois) dans la colonne 1 du content_container."""
        if getattr(self, "_artifacts_panel", None) is not None:
            return self._artifacts_panel

        container = self.content_container
        # Réserver une colonne à droite pour le volet (poids 0 = largeur fixe).
        container.grid_columnconfigure(1, weight=0, minsize=0)

        panel = self.create_frame(container, fg_color=self.colors["bg_secondary"])
        panel.grid(row=0, column=1, sticky="nsew", padx=(1, 0), pady=0)
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_propagate(False)
        try:
            panel.configure(width=_PANEL_WIDTH)
        except Exception:
            pass

        self._artifacts_panel = panel
        self._artifacts_current = None  # Artifact actuellement affiché
        self._artifacts_last_file = None  # dernier fichier écrit (fallback navigateur)

        self._build_header(panel)
        self._artifacts_body = self.create_frame(
            panel, fg_color=self.colors["bg_chat"]
        )
        self._artifacts_body.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self._artifacts_body.grid_rowconfigure(0, weight=1)
        self._artifacts_body.grid_columnconfigure(0, weight=1)
        self._artifacts_view = None  # widget de rendu (HtmlFrame ou fallback Text)

        # Bandeau d'info : le rendu embarqué (tkinterweb) est approximatif
        # (pas de flexbox/grid/JS) — invite à utiliser le navigateur pour le
        # rendu exact. Affiché uniquement quand tkinterweb fait le rendu.
        if TKINTERWEB_AVAILABLE:
            hint = self.create_label(
                panel,
                text="⚠ Rendu approximatif (CSS limité) — cliquez 🌐 pour le rendu exact",
                font=("Segoe UI", 9),
                fg_color=self.colors["bg_secondary"],
                text_color=self.colors["text_secondary"],
            )
            hint.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 6))

        # Caché par défaut
        panel.grid_remove()
        self._artifacts_visible = False
        return panel

    def _build_header(self, panel):
        """Barre de titre + toolbar (rafraîchir / navigateur / fermer)."""
        header = self.create_frame(panel, fg_color=self.colors["bg_secondary"])
        header.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        header.grid_columnconfigure(1, weight=1)

        icon = self.create_label(
            header, text="🎨", font=("Segoe UI Emoji", 14),
            fg_color=self.colors["bg_secondary"],
            text_color=self.colors["text_primary"],
        )
        icon.grid(row=0, column=0, padx=(2, 6))

        self._artifacts_title_label = self.create_label(
            header, text="Aperçu", font=("Segoe UI", 12, "bold"),
            fg_color=self.colors["bg_secondary"],
            text_color=self.colors["text_primary"],
        )
        self._artifacts_title_label.grid(row=0, column=1, sticky="w")

        tools = self.create_frame(header, fg_color=self.colors["bg_secondary"])
        tools.grid(row=0, column=2, sticky="e")

        def _mini_btn(parent, text, command, tooltip=""):
            if self.use_ctk:
                btn = ctk.CTkButton(
                    parent, text=text, command=command, width=32, height=28,
                    fg_color=self.colors["bg_chat"],
                    hover_color=self.colors["button_hover"],
                    text_color=self.colors["text_primary"],
                    font=("Segoe UI", 13), corner_radius=6,
                )
            else:
                btn = tk.Button(
                    parent, text=text, command=command,
                    bg=self.colors["bg_chat"], fg=self.colors["text_primary"],
                    font=("Segoe UI", 12), relief="flat", bd=0, cursor="hand2",
                )
            return btn

        # 🌐 Ouvrir dans le navigateur (fallback fidélité totale)
        _mini_btn(tools, "🌐", self._open_artifact_in_browser).pack(
            side="left", padx=2
        )
        # ✕ Fermer le volet
        _mini_btn(tools, "✕", self.hide_artifacts_panel).pack(side="left", padx=2)

    # ── API publique ──────────────────────────────────────────────────────

    def open_artifact_preview(self, artifact):
        """Ouvre le volet et y rend l'artifact donné."""
        self._ensure_artifacts_panel()
        self._artifacts_current = artifact

        # Toujours écrire le fichier : sert au fallback navigateur ET au rendu
        # tkinterweb par URL locale (plus fiable que load_html pour le CSS).
        try:
            self._artifacts_last_file = write_artifact_html(artifact)
        except Exception as e:
            self._artifacts_last_file = None
            print(f"⚠️ [ARTIFACTS] Écriture fichier échouée: {e}")

        self._artifacts_title_label.configure(text=artifact.title or "Aperçu")
        self._render_artifact(artifact)
        self.show_artifacts_panel()

    def show_artifacts_panel(self):
        """Affiche le volet (colonne droite)."""
        self._ensure_artifacts_panel()
        self.content_container.grid_columnconfigure(1, minsize=_PANEL_WIDTH)
        self._artifacts_panel.grid()
        self._artifacts_visible = True
        # Rétrécir la colonne chat re-wrappe les messages (hauteur change) et
        # Tk replace le scroll en haut : on restaure la position bas pour que
        # la fin du message (et le bouton Aperçu) reste visible.
        self._restore_chat_scroll_bottom()

    def hide_artifacts_panel(self):
        """Masque le volet et rend toute la largeur au chat."""
        if getattr(self, "_artifacts_panel", None) is not None:
            self._artifacts_panel.grid_remove()
        self.content_container.grid_columnconfigure(1, minsize=0)
        self._artifacts_visible = False
        self._restore_chat_scroll_bottom()

    def _restore_chat_scroll_bottom(self):
        """Re-scrolle la conversation vers le bas après un reflow du layout."""
        fn = getattr(self, "_final_smooth_scroll_to_bottom", None)
        if fn is None:
            return
        try:
            # Deux passes : une fois la géométrie recalculée, puis après le
            # re-rendu des widgets Text (wrap) qui peut arriver tardivement.
            self.root.after(60, fn)
            self.root.after(220, fn)
        except Exception:
            pass

    def toggle_artifacts_panel(self):
        """Bascule l'affichage du volet."""
        if getattr(self, "_artifacts_visible", False):
            self.hide_artifacts_panel()
        else:
            self.show_artifacts_panel()

    # ── Rendu ───────────────────────────────────────────────────────────--

    def _render_artifact(self, artifact):
        """Rend l'artifact dans le body via tkinterweb, sinon fallback texte."""
        # Détruire l'ancien widget de rendu
        if getattr(self, "_artifacts_view", None) is not None:
            try:
                self._artifacts_view.destroy()
            except Exception:
                pass
            self._artifacts_view = None

        if TKINTERWEB_AVAILABLE:
            self._render_with_tkinterweb(artifact)
        else:
            self._render_fallback(artifact)

    def _render_with_tkinterweb(self, artifact):
        """Rendu embarqué via tkinterweb (CSS limité — voir doc)."""
        try:
            view = HtmlFrame(self._artifacts_body, messages_enabled=False)
            view.grid(row=0, column=0, sticky="nsew")
            # Charger par fichier si possible (meilleur support des chemins
            # relatifs / du CSS), sinon par contenu.
            if self._artifacts_last_file is not None:
                view.load_file(str(self._artifacts_last_file), force=True)
            else:
                view.load_html(build_preview_document(artifact))
            self._artifacts_view = view
        except Exception as e:
            print(f"⚠️ [ARTIFACTS] Rendu tkinterweb échoué: {e}")
            self._render_fallback(artifact, error=str(e))

    def _render_fallback(self, artifact, error=None):
        """Affichage de repli : message + code source + invite navigateur."""
        frame = self.create_frame(self._artifacts_body, fg_color=self.colors["bg_chat"])
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        if error:
            msg = "Rendu embarqué indisponible. Utilisez « 🌐 Ouvrir dans le navigateur »."
        else:
            msg = (
                "Rendu embarqué désactivé (module 'tkinterweb' absent).\n"
                "Installez-le avec : pip install tkinterweb\n"
                "En attendant, utilisez « 🌐 Ouvrir dans le navigateur »."
            )
        info = self.create_label(
            frame, text=msg, font=("Segoe UI", 11),
            fg_color=self.colors["bg_chat"],
            text_color=self.colors["text_secondary"],
        )
        info.grid(row=0, column=0, sticky="ew", padx=8, pady=8)

        # Aperçu du code source en lecture seule
        code_view = tk.Text(
            frame, bg="#1a1a1a", fg="#d4d4d4", font=("Consolas", 10),
            wrap="none", relief="flat", bd=0, padx=8, pady=8,
        )
        code_view.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        code_view.insert("1.0", artifact.code)
        code_view.configure(state="disabled")
        self._artifacts_view = frame

    # ── Fallback navigateur ────────────────────────────────────────────────

    def _open_artifact_in_browser(self):
        """Ouvre l'artifact courant dans le navigateur par défaut (fidélité totale)."""
        try:
            path = getattr(self, "_artifacts_last_file", None)
            if path is None and getattr(self, "_artifacts_current", None) is not None:
                path = write_artifact_html(self._artifacts_current)
                self._artifacts_last_file = path
            if path is not None:
                webbrowser.open(f"file://{path}")
            elif hasattr(self, "show_notification"):
                self.show_notification("Aucun artifact à ouvrir.", "error", 2500)
        except Exception as e:
            print(f"⚠️ [ARTIFACTS] Ouverture navigateur échouée: {e}")
            if hasattr(self, "show_notification"):
                self.show_notification("Impossible d'ouvrir le navigateur.", "error", 2500)
