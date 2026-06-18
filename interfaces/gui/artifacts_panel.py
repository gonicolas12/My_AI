"""Volet « Artifacts » pour ModernAIGUI.

Affiche un rendu live du HTML/CSS/SVG généré par l'IA, à côté du chat,
façon Claude Artifacts.

Moteur de rendu (ordre de préférence) :
1. **Edge --app embarqué** (Windows) : Chromium, rendu EXACT, sans dépendance
   Python supplémentaire — la fenêtre Edge est ré-parentée dans le volet.
2. **tkinterweb** : moteur léger pur Python, rendu approximatif (CSS limité).
3. **Fallback** : code source + bouton « Ouvrir dans le navigateur ».

Le bouton 🌐 reste toujours disponible pour ouvrir le rendu exact dans le
navigateur par défaut.
"""

import tkinter as tk
import webbrowser

try:
    import customtkinter as ctk

    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    ctk = tk

# Rendu HTML embarqué léger optionnel (fallback si Edge indisponible).
try:
    from tkinterweb import HtmlFrame  # type: ignore

    TKINTERWEB_AVAILABLE = True
except Exception:
    TKINTERWEB_AVAILABLE = False
    HtmlFrame = None

from interfaces.artifacts import build_preview_document, write_artifact_html
from interfaces.gui._edge_embed import EdgeEmbed

# Largeur par défaut / bornes du volet (px). Il occupe la col 1 du content_container.
_PANEL_WIDTH = 560
_PANEL_MIN = 320
_PANEL_MAX = 1200
_GRIP_W = 6  # largeur de la poignée de redimensionnement


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

        # Largeur courante (modifiable par la poignée de redimensionnement).
        self._panel_width = _PANEL_WIDTH

        panel = self.create_frame(container, fg_color=self.colors["bg_secondary"])
        panel.grid(row=0, column=1, sticky="nsew", padx=(0, 0), pady=0)
        # col 0 = poignée de redimensionnement, col 1 = contenu
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(1, weight=1)
        panel.grid_propagate(False)
        try:
            panel.configure(width=self._panel_width)
        except Exception:
            pass

        # ── Poignée de redimensionnement (bord gauche du volet) ──
        self._build_resize_grip(panel)

        self._artifacts_panel = panel
        self._artifacts_current = None  # Artifact actuellement affiché
        self._artifacts_last_file = None  # dernier fichier écrit (fallback navigateur)
        self._artifacts_mode = None  # "edge" | "tkinterweb" | "fallback"

        # Moteur Edge embarqué (Windows) — rendu Chromium exact.
        self._edge_embed = EdgeEmbed()

        self._build_header(panel)
        self._artifacts_body = self.create_frame(
            panel, fg_color=self.colors["bg_chat"]
        )
        self._artifacts_body.grid(row=1, column=1, sticky="nsew", padx=6, pady=(0, 6))
        self._artifacts_body.grid_rowconfigure(0, weight=1)
        self._artifacts_body.grid_columnconfigure(0, weight=1)
        self._artifacts_view = None  # widget de rendu (HtmlFrame ou fallback Text)

        # Synchroniser la taille de la fenêtre Edge embarquée avec le body.
        self._artifacts_body.bind("<Configure>", self._on_artifacts_body_resize)

        # Bandeau d'info (affiché uniquement quand le moteur léger tkinterweb
        # est utilisé, car son rendu est approximatif).
        self._artifacts_hint = self.create_label(
            panel,
            text="⚠ Rendu approximatif (CSS limité) — cliquez 🌐 pour le rendu exact",
            font=("Segoe UI", 9),
            fg_color=self.colors["bg_secondary"],
            text_color=self.colors["text_secondary"],
        )
        # Masqué par défaut ; affiché seulement en mode tkinterweb.
        self._artifacts_hint.grid(row=2, column=1, sticky="ew", padx=8, pady=(0, 6))
        self._artifacts_hint.grid_remove()

        # Nettoyage de la fenêtre Edge à la fermeture de l'application.
        try:
            self.root.bind("<Destroy>", self._on_root_destroy, add="+")
        except Exception:
            pass

        # Caché par défaut
        panel.grid_remove()
        self._artifacts_visible = False
        return panel

    def _on_artifacts_body_resize(self, event):
        """Redimensionne la fenêtre Edge embarquée pour épouser le body."""
        embed = getattr(self, "_edge_embed", None)
        if embed is not None and getattr(self, "_artifacts_mode", None) == "edge":
            embed.resize(event.width, event.height)

    def _on_root_destroy(self, event):
        """Ferme proprement Edge quand la fenêtre racine est détruite."""
        if event.widget is self.root:
            embed = getattr(self, "_edge_embed", None)
            if embed is not None:
                embed.close()

    def _build_resize_grip(self, panel):
        """Poignée verticale (bord gauche) pour redimensionner le volet à la souris."""
        grip = tk.Frame(panel, width=_GRIP_W, bg=self.colors.get("border", "#404040"),
                        cursor="sb_h_double_arrow")
        grip.grid(row=0, column=0, rowspan=3, sticky="ns")
        panel.grid_columnconfigure(0, weight=0, minsize=_GRIP_W)

        def _press(e):
            self._resize_start_x = e.x_root
            self._resize_start_w = self._panel_width

        def _drag(e):
            # Glisser vers la gauche élargit le volet (la souris s'éloigne du bord droit).
            delta = self._resize_start_x - e.x_root
            new_w = max(_PANEL_MIN, min(_PANEL_MAX, self._resize_start_w + delta))
            self._set_panel_width(new_w)

        grip.bind("<Button-1>", _press)
        grip.bind("<B1-Motion>", _drag)
        # Survol : éclaircir la poignée
        grip.bind("<Enter>", lambda _e: grip.configure(bg=self.colors.get("accent", "#ff6b47")))
        grip.bind("<Leave>", lambda _e: grip.configure(bg=self.colors.get("border", "#404040")))

    def _set_panel_width(self, width):
        """Applique une nouvelle largeur de volet et resynchronise Edge."""
        self._panel_width = int(width)
        try:
            self.content_container.grid_columnconfigure(1, minsize=self._panel_width)
            self._artifacts_panel.configure(width=self._panel_width)
            self._artifacts_panel.update_idletasks()
        except Exception:
            pass
        embed = getattr(self, "_edge_embed", None)
        if embed is not None and getattr(self, "_artifacts_mode", None) == "edge":
            body = self._artifacts_body
            embed.resize(body.winfo_width(), body.winfo_height())

    def _build_header(self, panel):
        """Barre de titre + toolbar (rafraîchir / navigateur / fermer)."""
        header = self.create_frame(panel, fg_color=self.colors["bg_secondary"])
        header.grid(row=0, column=1, sticky="ew", padx=6, pady=6)
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
        # Afficher le volet AVANT de rendre : le body doit être mappé et
        # dimensionné pour que le ré-parentage Edge cible la bonne géométrie.
        self.show_artifacts_panel()
        self._artifacts_body.update_idletasks()
        self._render_artifact(artifact)

    def show_artifacts_panel(self):
        """Affiche le volet (colonne droite)."""
        self._ensure_artifacts_panel()
        self.content_container.grid_columnconfigure(1, minsize=self._panel_width)
        self._artifacts_panel.grid()
        self._artifacts_visible = True
        # Rétrécir la colonne chat re-wrappe les messages (hauteur change) et
        # Tk replace le scroll en haut : on restaure la position bas pour que
        # la fin du message (et le bouton Aperçu) reste visible.
        self._restore_chat_scroll_bottom()

    def hide_artifacts_panel(self):
        """Masque le volet et rend toute la largeur au chat."""
        # Fermer la fenêtre Edge embarquée (sinon elle resterait orpheline).
        embed = getattr(self, "_edge_embed", None)
        if embed is not None:
            embed.close()
        self._artifacts_mode = None
        if getattr(self, "_artifacts_panel", None) is not None:
            self._artifacts_panel.grid_remove()
        self.content_container.grid_columnconfigure(1, minsize=0)
        self._artifacts_visible = False
        self._restore_chat_scroll_bottom()

    def _restore_chat_scroll_bottom(self):
        """Re-scrolle la conversation vers le bas après un reflow du layout.

        Rétrécir/élargir la colonne chat re-wrappe les widgets Text : leur
        hauteur change en plusieurs étapes (géométrie, puis re-rendu). On force
        donc le bas sur plusieurs passes échelonnées pour absorber ces étapes.
        """
        def _to_bottom():
            try:
                canvas = self._get_parent_canvas() if hasattr(self, "_get_parent_canvas") else None
                if canvas is not None:
                    canvas.update_idletasks()
                    bbox = canvas.bbox("all")
                    if bbox:
                        canvas.configure(scrollregion=bbox)
                    canvas.yview_moveto(1.0)
                else:
                    fn = getattr(self, "_final_smooth_scroll_to_bottom", None)
                    if fn:
                        fn()
            except Exception:
                pass

        try:
            for delay in (50, 200, 400, 700, 1000):
                self.root.after(delay, _to_bottom)
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
        """Rend l'artifact : Edge embarqué (exact) → tkinterweb → fallback."""
        # Fermer une éventuelle fenêtre Edge précédente
        embed = getattr(self, "_edge_embed", None)
        if embed is not None:
            embed.close()
        # Détruire l'ancien widget de rendu Tk
        if getattr(self, "_artifacts_view", None) is not None:
            try:
                self._artifacts_view.destroy()
            except Exception:
                pass
            self._artifacts_view = None

        # 1) Edge --app embarqué (rendu Chromium exact) — lancement non bloquant
        if embed is not None and embed.available and self._artifacts_last_file is not None:
            if self._render_with_edge(artifact):
                return

        # 2) tkinterweb (rendu approximatif)
        if TKINTERWEB_AVAILABLE:
            self._render_with_tkinterweb(artifact)
            return

        # 3) Fallback : code source
        self._render_fallback(artifact)

    def _render_with_edge(self, artifact) -> bool:
        """Lance Edge --app puis sonde son attachement (non bloquant). True si lancé."""
        try:
            self._artifacts_body.update_idletasks()
            w = self._artifacts_body.winfo_width() or self._panel_width
            h = self._artifacts_body.winfo_height() or 600
            if not self._edge_embed.start(
                str(self._artifacts_last_file), self._artifacts_body, w, h
            ):
                return False
            self._artifacts_mode = "edge"
            self._artifacts_hint.grid_remove()
            self._poll_edge_attach(artifact, 0)
            return True
        except Exception as e:
            print(f"⚠️ [ARTIFACTS] Lancement Edge échoué: {e}")
        return False

    def _poll_edge_attach(self, artifact, attempts):
        """Sonde périodiquement l'attachement Edge (via root.after, non bloquant)."""
        if getattr(self, "_artifacts_mode", None) != "edge":
            return
        body = self._artifacts_body
        try:
            res = self._edge_embed.poll_attach(body.winfo_width(), body.winfo_height())
        except Exception:
            res = None

        if res is True:
            # Fenêtre attachée : le layout a bougé, on resynchronise le scroll.
            self._restore_chat_scroll_bottom()
            return
        if res is None:
            # Échec/timeout → repli sur tkinterweb puis code source.
            print("⚠️ [ARTIFACTS] Edge non attaché → repli")
            if TKINTERWEB_AVAILABLE:
                self._render_with_tkinterweb(artifact)
            else:
                self._render_fallback(artifact)
            return
        # Toujours en attente
        if attempts < 70:
            self.root.after(120, lambda: self._poll_edge_attach(artifact, attempts + 1))

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
            self._artifacts_mode = "tkinterweb"
            # Rendu approximatif → afficher le bandeau d'avertissement.
            self._artifacts_hint.grid()
        except Exception as e:
            print(f"⚠️ [ARTIFACTS] Rendu tkinterweb échoué: {e}")
            self._render_fallback(artifact, error=str(e))

    def _render_fallback(self, artifact, error=None):
        """Affichage de repli : message + code source + invite navigateur."""
        frame = self.create_frame(self._artifacts_body, fg_color=self.colors["bg_chat"])
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        self._artifacts_mode = "fallback"
        if error:
            msg = "Rendu embarqué indisponible. Utilisez « 🌐 Ouvrir dans le navigateur »."
        else:
            msg = (
                "Rendu embarqué indisponible sur ce système.\n"
                "Utilisez « 🌐 Ouvrir dans le navigateur » pour le rendu exact."
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
                from pathlib import Path as _P
                webbrowser.open(_P(path).as_uri())
            elif hasattr(self, "show_notification"):
                self.show_notification("Aucun artifact à ouvrir.", "error", 2500)
        except Exception as e:
            print(f"⚠️ [ARTIFACTS] Ouverture navigateur échouée: {e}")
            if hasattr(self, "show_notification"):
                self.show_notification("Impossible d'ouvrir le navigateur.", "error", 2500)
