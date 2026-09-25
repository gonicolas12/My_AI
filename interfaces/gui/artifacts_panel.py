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

import os
import subprocess
import sys
import tkinter as tk
import webbrowser
from pathlib import Path

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
from interfaces.gui._dpi_host import DpiAwareHost, is_dpi_virtualized
from interfaces.gui._edge_embed import EdgeEmbed
from interfaces.gui._preview_handler import AsyncNativePreview, supports_native_preview

# Largeur par défaut / bornes du volet (px). Il occupe la col 1 du content_container.
_PANEL_WIDTH = 560
_PANEL_MIN = 320
_PANEL_MAX = 1200
_GRIP_W = 6  # largeur de la poignée de redimensionnement
# Recalages de la fenêtre Edge après ré-parentage (ms) : Chromium peut
# réappliquer ses dimensions à la fin du chargement ou sur changement de DPI.
_EDGE_REPLACE_DELAYS_MS = (200, 700, 1500)
# Application affichée pendant l'ouverture d'une visionneuse native.
_NATIVE_APP_LABELS = {
    ".docx": "Word", ".doc": "Word",
    ".pptx": "PowerPoint", ".ppt": "PowerPoint",
    ".xlsx": "Excel", ".xlsm": "Excel", ".xls": "Excel",
}


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
        # Hôte DPI (cf. _dpi_host) : il flotte au-dessus du volet, il faut
        # donc le recaler quand la fenêtre principale se déplace.
        self._dpi_host = None
        try:
            self.root.bind("<Configure>", self._on_root_configure, add="+")
        except Exception:
            pass

        # Caché par défaut
        panel.grid_remove()
        self._artifacts_visible = False
        return panel

    def _on_artifacts_body_resize(self, _event):
        """Redimensionne la fenêtre embarquée pour épouser le body."""
        self._sync_embedded_geometry()

    def _on_root_configure(self, event):
        """Déplacement/redimensionnement de la fenêtre principale."""
        # Un <Configure> lié à la racine reçoit aussi ceux de TOUS ses
        # descendants (bindtags) : seuls ceux de la racine nous intéressent.
        if event.widget is self.root:
            self._sync_embedded_geometry()

    def _sync_embedded_geometry(self):
        """Aligne l'hôte DPI éventuel, puis Edge ou la visionneuse, sur le body."""
        mode = getattr(self, "_artifacts_mode", None)
        if mode not in ("edge", "native", "native_loading"):
            return
        body = self._artifacts_body
        host = getattr(self, "_dpi_host", None)
        if host is not None and getattr(self, "_artifacts_edge_parent", None) is host:
            # Pendant le chargement, l'hôte suit le body mais reste masqué.
            host.place_over(body, show=mode != "native_loading")
        if mode == "edge":
            embed = getattr(self, "_edge_embed", None)
            if embed is not None:
                embed.resize(body.winfo_width(), body.winfo_height())
        elif mode == "native":
            self._native_preview.resize()

    def _on_root_destroy(self, event):
        """Ferme proprement Edge et la visionneuse quand la racine est détruite."""
        if event.widget is self.root:
            embed = getattr(self, "_edge_embed", None)
            if embed is not None:
                embed.close()
            # Attente bornée : ne pas laisser Office orphelin à la sortie.
            self._close_native_preview(wait=2.0)
            host = getattr(self, "_dpi_host", None)
            if host is not None:
                host.destroy()

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
            # Reflow debounced pendant le drag (évite de recalculer à chaque pixel).
            self._schedule_reflow()

        def _release(_e):
            # Reflow final fiable au relâchement.
            self._reflow_and_scroll()

        grip.bind("<Button-1>", _press)
        grip.bind("<B1-Motion>", _drag)
        grip.bind("<ButtonRelease-1>", _release)
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
        self._sync_embedded_geometry()

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

        # 📂 Ouvrir le vrai fichier — pertinent pour les seuls artifacts
        # « document » ; affiché/masqué par _sync_open_file_button().
        self._artifacts_open_file_btn = _mini_btn(tools, "📂", self._open_artifact_file)
        # 🌐 Ouvrir dans le navigateur (fallback fidélité totale)
        self._artifacts_browser_btn = _mini_btn(tools, "🌐", self._open_artifact_in_browser)
        self._artifacts_browser_btn.pack(side="left", padx=2)
        # ✕ Fermer le volet
        _mini_btn(tools, "✕", self.hide_artifacts_panel).pack(side="left", padx=2)

    def _sync_open_file_button(self, artifact):
        """Affiche le bouton 📂 seulement pour un artifact adossé à un fichier."""
        button = getattr(self, "_artifacts_open_file_btn", None)
        if button is None:
            return
        try:
            if getattr(artifact, "is_file", False):
                # `before` : garder 📂 à gauche de 🌐 malgré le re-packing.
                button.pack(side="left", padx=2, before=self._artifacts_browser_btn)
            else:
                button.pack_forget()
        except tk.TclError:
            pass

    # ── API publique ──────────────────────────────────────────────────────

    def open_artifact_preview(self, artifact):
        """Ouvre le volet et y rend l'artifact donné."""
        self._ensure_artifacts_panel()

        # Même artifact déjà affiché : simple ré-affichage. Relancer Edge
        # ferait clignoter le volet pour rien — c'est le cas typique d'un clic
        # sur « 🔍 Aperçu » juste après l'ouverture automatique.
        if (
            artifact == getattr(self, "_artifacts_current", None)
            and getattr(self, "_artifacts_visible", False)
            and getattr(self, "_artifacts_mode", None) is not None
        ):
            self.show_artifacts_panel()
            return

        self._artifacts_current = artifact

        # Le fichier d'aperçu HTML sert à Edge, à tkinterweb (par URL locale,
        # plus fiable que load_html pour le CSS) et au bouton 🌐. Un document
        # Office confié à sa visionneuse native n'en a pas besoin : le
        # construire (lecture complète du document) gèlerait l'interface pour
        # rien ; il sera produit à la demande (repli, bouton 🌐).
        if getattr(artifact, "is_file", False) and supports_native_preview(artifact.file_path):
            self._artifacts_last_file = None
        else:
            self._artifacts_last_file = self._write_preview_file(artifact)

        self._artifacts_title_label.configure(text=artifact.title or "Aperçu")
        self._sync_open_file_button(artifact)
        # Afficher le volet AVANT de rendre : le body doit être mappé et
        # dimensionné pour que le ré-parentage Edge cible la bonne géométrie.
        self.show_artifacts_panel()
        self._artifacts_body.update_idletasks()
        self._render_artifact(artifact)

    @staticmethod
    def _write_preview_file(artifact):
        """Écrit le fichier d'aperçu HTML de l'artifact (None en cas d'échec)."""
        try:
            return write_artifact_html(artifact)
        except Exception as e:
            print(f"⚠️ [ARTIFACTS] Écriture fichier échouée: {e}")
            return None

    def show_artifacts_panel(self):
        """Affiche le volet (colonne droite)."""
        self._ensure_artifacts_panel()
        self.content_container.grid_columnconfigure(1, minsize=self._panel_width)
        self._artifacts_panel.grid()
        self._artifacts_visible = True
        # Rétrécir la colonne chat re-wrappe les messages : on recalcule les
        # hauteurs (sinon le bas est rogné) puis on recolle le scroll en bas.
        self._schedule_reflow(delay=60)
        self._restore_chat_scroll_bottom()

    def hide_artifacts_panel(self):
        """Masque le volet et rend toute la largeur au chat."""
        # Fermer la fenêtre Edge embarquée (sinon elle resterait orpheline).
        embed = getattr(self, "_edge_embed", None)
        if embed is not None:
            embed.close()
        self._close_native_preview()
        self._hide_dpi_host()
        self._artifacts_render_seq = getattr(self, "_artifacts_render_seq", 0) + 1
        self._artifacts_mode = None
        if getattr(self, "_artifacts_panel", None) is not None:
            self._artifacts_panel.grid_remove()
        self.content_container.grid_columnconfigure(1, minsize=0)
        self._artifacts_visible = False
        # Le chat reprend toute la largeur → recalculer les hauteurs + scroll.
        self._schedule_reflow(delay=60)
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

    # ── Reflow responsive des bulles ───────────────────────────────────────

    def _iter_text_widgets(self, widget):
        """Itère récursivement sur les widgets tk.Text sous `widget`."""
        try:
            for child in widget.winfo_children():
                if isinstance(child, tk.Text):
                    yield child
                else:
                    yield from self._iter_text_widgets(child)
        except Exception:
            return

    def _reflow_chat_messages(self):
        """Recalcule la hauteur des bulles IA après un changement de largeur.

        Les bulles sont des tk.Text à hauteur fixe (en lignes) calculée à la
        largeur du moment ; rétrécir la colonne chat re-wrappe le texte et
        rognerait le bas. On réapplique la mesure pixel-perfect existante.
        """
        adjust = getattr(self, "_adjust_height_final_no_scroll", None)
        if adjust is None:
            return
        for container in list(getattr(self, "_message_widgets", [])):
            try:
                if not container.winfo_exists():
                    continue
                for tw in self._iter_text_widgets(container):
                    adjust(tw)
            except Exception:
                pass

    def _reflow_and_scroll(self):
        """Re-layout : recalcule les hauteurs puis recolle le scroll en bas."""
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        self._reflow_chat_messages()
        self._restore_chat_scroll_bottom()

    def _schedule_reflow(self, delay=140):
        """Reflow debounced (utilisé pendant le drag de la poignée)."""
        prev = getattr(self, "_reflow_after_id", None)
        if prev is not None:
            try:
                self.root.after_cancel(prev)
            except Exception:
                pass
        self._reflow_after_id = self.root.after(delay, self._reflow_and_scroll)

    def toggle_artifacts_panel(self):
        """Bascule l'affichage du volet."""
        if getattr(self, "_artifacts_visible", False):
            self.hide_artifacts_panel()
        else:
            self.show_artifacts_panel()

    # ── Rendu ───────────────────────────────────────────────────────────--

    def _render_artifact(self, artifact):
        """Rend l'artifact : visionneuse native → Edge embarqué → tkinterweb → fallback."""
        # Nouveau rendu : toute sonde d'attachement encore planifiée pour le
        # rendu précédent devient caduque (cf. _poll_edge_attach).
        self._artifacts_render_seq = getattr(self, "_artifacts_render_seq", 0) + 1
        # Fermer une éventuelle fenêtre Edge ou visionneuse précédente
        embed = getattr(self, "_edge_embed", None)
        if embed is not None:
            embed.close()
        self._close_native_preview()
        self._hide_dpi_host()
        self._clear_artifacts_view()

        # 0) Document Office : la visionneuse Windows de son format (Word,
        #    PowerPoint, Excel) l'affiche tel quel — non bloquant
        if getattr(artifact, "is_file", False) and supports_native_preview(artifact.file_path):
            if self._render_native(artifact):
                return

        self._render_html_preview(artifact)

    def _render_html_preview(self, artifact):
        """Rendu HTML : Edge embarqué (exact) → tkinterweb → code source."""
        # 1) Edge --app embarqué (rendu Chromium exact) — lancement non bloquant
        embed = getattr(self, "_edge_embed", None)
        if embed is not None and embed.available and self._artifacts_last_file is not None:
            if self._render_with_edge(artifact):
                return

        # 2) tkinterweb (rendu approximatif)
        if TKINTERWEB_AVAILABLE:
            self._render_with_tkinterweb(artifact)
            return

        # 3) Fallback : code source
        self._render_fallback(artifact)

    def _clear_artifacts_view(self):
        """Détruit le widget de rendu Tk courant (HtmlFrame, repli, chargement)."""
        if getattr(self, "_artifacts_view", None) is not None:
            try:
                self._artifacts_view.destroy()
            except Exception:
                pass
            self._artifacts_view = None

    # ── Visionneuses natives (Word, PowerPoint, Excel) ─────────────────────

    def _render_native(self, artifact) -> bool:
        """Confie le document à la visionneuse Windows de son format.

        Non bloquant : Office peut mettre plusieurs secondes à démarrer. Le
        volet affiche « Ouverture de l'aperçu… » et l'hôte, déjà dimensionné
        mais masqué, n'apparaît qu'une fois la visionneuse prête.
        """
        host = self._ensure_dpi_host()
        if host is None:
            return False
        host.place_over(self._artifacts_body, show=False)
        self._artifacts_edge_parent = host
        self._artifacts_mode = "native_loading"
        self._artifacts_hint.grid_remove()

        app = _NATIVE_APP_LABELS.get(Path(artifact.file_path).suffix.lower(), "")
        loading = self.create_label(
            self._artifacts_body,
            text=f"⏳ Ouverture de l'aperçu {app}…".replace("  ", " "),
            font=("Segoe UI", 11),
            fg_color=self.colors["bg_chat"],
            text_color=self.colors["text_secondary"],
        )
        loading.grid(row=0, column=0, sticky="nsew")
        self._artifacts_view = loading

        if getattr(self, "_native_preview", None) is None:
            self._native_preview = AsyncNativePreview()
        seq = self._artifacts_render_seq

        def _on_result(ok):
            # Appelé depuis le thread COM : repasser sur le thread Tk.
            try:
                self.root.after(0, lambda: self._on_native_ready(seq, ok, artifact))
            except RuntimeError:
                pass  # fenêtre détruite entre-temps

        self._native_preview.open(artifact.file_path, host.hwnd, _on_result)
        return True

    def _on_native_ready(self, seq, ok, artifact):
        """Visionneuse prête (ou en échec) : affichage, ou repli sur l'aperçu HTML."""
        if seq != getattr(self, "_artifacts_render_seq", None):
            return  # rendu remplacé entre-temps : sa fermeture est déjà en file
        self._clear_artifacts_view()
        if ok:
            self._artifacts_mode = "native"
            self._sync_embedded_geometry()
            self._restore_chat_scroll_bottom()
            return
        # Visionneuse indisponible ou en échec → aperçu HTML, produit maintenant
        self._hide_dpi_host()
        self._artifacts_mode = None
        if self._artifacts_last_file is None:
            self._artifacts_last_file = self._write_preview_file(artifact)
        self._render_html_preview(artifact)

    def _close_native_preview(self, wait: float = 0.0):
        """Décharge la visionneuse native éventuelle."""
        preview = getattr(self, "_native_preview", None)
        if preview is not None:
            preview.close(wait=wait)

    def _embedding_parent(self):
        """Fenêtre dans laquelle ré-parenter Edge : le body, ou l'hôte DPI.

        Si la fenêtre principale est mise à l'échelle en bitmap par Windows
        (appli non DPI-aware, écran à 125 %), y ré-parenter Edge fausse son
        rendu ; on passe alors par un hôte DPI par écran posé sur le body.
        """
        self._artifacts_edge_parent = self._artifacts_body
        if not is_dpi_virtualized(self._artifacts_body):
            return self._artifacts_body
        host = self._ensure_dpi_host()
        if host is None:
            return self._artifacts_body
        host.place_over(self._artifacts_body)
        self._artifacts_edge_parent = host
        return host

    def _ensure_dpi_host(self):
        """Hôte DPI par écran partagé par Edge et les visionneuses (ou None)."""
        host = getattr(self, "_dpi_host", None)
        if host is None or not host.alive:
            host = DpiAwareHost(self._artifacts_body, background=self.colors["bg_chat"])
            self._dpi_host = host
        return host if host.alive else None

    def _hide_dpi_host(self):
        """Masque l'hôte DPI (volet fermé ou rendu hors Edge)."""
        host = getattr(self, "_dpi_host", None)
        if host is not None:
            host.hide()
        self._artifacts_edge_parent = None

    def _render_with_edge(self, artifact) -> bool:
        """Lance Edge --app puis sonde son attachement (non bloquant). True si lancé."""
        try:
            self._artifacts_body.update_idletasks()
            w = self._artifacts_body.winfo_width() or self._panel_width
            h = self._artifacts_body.winfo_height() or 600
            if not self._edge_embed.start(
                str(self._artifacts_last_file), self._embedding_parent(), w, h
            ):
                self._hide_dpi_host()
                return False
            self._artifacts_mode = "edge"
            self._artifacts_hint.grid_remove()
            self._poll_edge_attach(artifact, 0, self._artifacts_render_seq)
            return True
        except Exception as e:
            print(f"⚠️ [ARTIFACTS] Lancement Edge échoué: {e}")
        return False

    def _poll_edge_attach(self, artifact, attempts, seq=None):
        """Sonde périodiquement l'attachement Edge (via root.after, non bloquant)."""
        if getattr(self, "_artifacts_mode", None) != "edge":
            return
        # Sonde d'un rendu remplacé depuis : elle agirait sur la nouvelle
        # instance Edge, voire replierait sur l'ANCIEN artifact en cas d'échec.
        if seq is not None and seq != getattr(self, "_artifacts_render_seq", None):
            return
        body = self._artifacts_body
        try:
            res = self._edge_embed.poll_attach(body.winfo_width(), body.winfo_height())
        except Exception:
            res = None

        if res is True:
            # Fenêtre attachée : le layout a bougé, on resynchronise le scroll.
            self._restore_chat_scroll_bottom()
            # Chromium peut réappliquer ses propres dimensions juste après le
            # ré-parentage (fin de chargement, changement de DPI quand la
            # fenêtre naît sur un autre écran) : on recale sa géométrie.
            for delay in _EDGE_REPLACE_DELAYS_MS:
                self.root.after(delay, lambda s=seq: self._resync_edge_geometry(s))
            return
        if res is None:
            # Échec/timeout → repli sur tkinterweb puis code source.
            print("⚠️ [ARTIFACTS] Edge non attaché → repli")
            self._hide_dpi_host()
            if TKINTERWEB_AVAILABLE:
                self._render_with_tkinterweb(artifact)
            else:
                self._render_fallback(artifact)
            return
        # Toujours en attente
        if attempts < 70:
            self.root.after(
                120, lambda: self._poll_edge_attach(artifact, attempts + 1, seq)
            )

    def _resync_edge_geometry(self, seq):
        """Recale la fenêtre Edge embarquée sur le body, si le rendu est toujours actuel."""
        if seq != getattr(self, "_artifacts_render_seq", None):
            return
        if getattr(self, "_artifacts_mode", None) != "edge":
            return
        embed = getattr(self, "_edge_embed", None)
        if embed is None or not embed.attached:
            return
        try:
            self._sync_embedded_geometry()
        except Exception:
            pass

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
        """Affichage de repli : message + code source (ou chemin du document)."""
        frame = self.create_frame(self._artifacts_body, fg_color=self.colors["bg_chat"])
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        self._artifacts_mode = "fallback"
        is_file = getattr(artifact, "is_file", False)
        if is_file:
            msg = (
                "Rendu embarqué indisponible sur ce système.\n"
                "Utilisez « 📂 » pour ouvrir le document dans son application."
            )
        elif error:
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

        # Un document bureautique n'a pas de source affichable : on montre son
        # chemin plutôt que des octets binaires.
        body_text = artifact.file_path if is_file else artifact.code
        code_view = tk.Text(
            frame, bg="#1a1a1a", fg="#d4d4d4", font=("Consolas", 10),
            wrap="word" if is_file else "none", relief="flat", bd=0, padx=8, pady=8,
        )
        code_view.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        code_view.insert("1.0", body_text or "")
        code_view.configure(state="disabled")
        self._artifacts_view = frame

    # ── Fallback navigateur ────────────────────────────────────────────────

    def _open_artifact_file(self):
        """Ouvre le document courant dans l'application système associée."""
        artifact = getattr(self, "_artifacts_current", None)
        path = getattr(artifact, "file_path", None) if artifact is not None else None
        if not path or not os.path.exists(path):
            if hasattr(self, "show_notification"):
                self.show_notification("Document introuvable.", "error", 2500)
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)  # noqa: B606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            print(f"⚠️ [ARTIFACTS] Ouverture du document échouée: {e}")
            if hasattr(self, "show_notification"):
                self.show_notification("Impossible d'ouvrir le document.", "error", 2500)

    def _open_artifact_in_browser(self):
        """Ouvre l'artifact courant dans le navigateur par défaut (fidélité totale)."""
        try:
            path = getattr(self, "_artifacts_last_file", None)
            if path is None and getattr(self, "_artifacts_current", None) is not None:
                path = write_artifact_html(self._artifacts_current)
                self._artifacts_last_file = path
            if path is not None:
                webbrowser.open(Path(path).as_uri())
            elif hasattr(self, "show_notification"):
                self.show_notification("Aucun artifact à ouvrir.", "error", 2500)
        except Exception as e:
            print(f"⚠️ [ARTIFACTS] Ouverture navigateur échouée: {e}")
            if hasattr(self, "show_notification"):
                self.show_notification("Impossible d'ouvrir le navigateur.", "error", 2500)
