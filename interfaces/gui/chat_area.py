"""Chat area and scrolling mixin for ModernAIGUI."""

import tkinter as tk
from tkinter import ttk
from ._wheel import wheel_notches

try:
    import customtkinter as ctk

    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    ctk = tk


class ChatAreaMixin:
    """Conversation area and scrolling helpers."""

    # Unités de défilement par cran de molette, comme les bulles
    # (setup_*scroll_forwarding) et, sous Windows, CTkScrollableFrame lui-même
    # (delta / 6 avec yscrollincrement = 1).
    _CHAT_WHEEL_UNITS = 20

    # Marge laissée sous le dernier caractère suivi pendant l'écriture
    _FOLLOW_MARGIN_PX = 12

    # Suivi de la réponse en cours : interrompu dès que l'utilisateur remonte
    # (molette, barre de défilement), repris quand il revient tout en bas et à
    # chaque nouveau message.
    _follow_chat_bottom = True

    # En deçà de cette distance au bas du contenu, la vue est « en bas »
    _BOTTOM_TOLERANCE_PX = 4

    def _scroll_chat_with_wheel(self, event):
        """Fait défiler la conversation d'un cran de molette, à la vitesse native."""
        try:
            target = self._get_parent_canvas()
            if target is None:
                target = self.chat_frame.master
                while target and not hasattr(target, "yview_scroll"):
                    target = target.master
            if target is not None:
                if getattr(event, "delta", 0):
                    units = int(-self._CHAT_WHEEL_UNITS * wheel_notches(event))
                else:
                    units = self._CHAT_WHEEL_UNITS * (-1 if event.num == 4 else 1)
                target.yview_scroll(units, "units")
                self._note_manual_scroll()
        except Exception:
            pass
        return "break"

    def _note_manual_scroll(self):
        """Défilement fait par l'utilisateur : la réponse en cours n'est plus
        suivie, sauf s'il est revenu tout en bas."""
        canvas = self._get_parent_canvas()
        if canvas is None:
            return
        bbox = canvas.bbox("all")
        view_bottom = canvas.canvasy(canvas.winfo_height())
        self._follow_chat_bottom = (
            not bbox or bbox[3] - view_bottom <= self._BOTTOM_TOLERANCE_PX
        )

    def _on_chat_wheel(self, event):
        """Molette hors des bulles : CTkScrollableFrame vient de faire défiler."""
        canvas = self._get_parent_canvas()
        if canvas is None:
            return
        path, area = str(event.widget), str(canvas)
        if path == area or path.startswith(area + "."):
            self._note_manual_scroll()

    def _on_chat_scrollbar(self, *args):
        """Commande de la barre de défilement : glisser, clic ou molette dessus."""
        canvas = self._get_parent_canvas()
        if canvas is not None:
            canvas.yview(*args)
            self._note_manual_scroll()

    def _scroll_to_bottom_if_following(self):
        """scroll_to_bottom, sauf si l'utilisateur est remonté lire plus haut."""
        if self._follow_chat_bottom:
            self.scroll_to_bottom()

    def _scroll_to_bottom_for_new_turn(self):
        """Nouveau message : retour en bas et suivi de la réponse à venir."""
        self._follow_chat_bottom = True
        self.scroll_to_bottom()

    def _get_parent_canvas(self):
        """
        Récupère le canvas parent pour CustomTkinter ScrollableFrame.
        Accès à un attribut protégé nécessaire pour le scrolling.
        """
        # pylint: disable=protected-access
        if (
            self.use_ctk
            and hasattr(self, "chat_frame")
            and hasattr(self.chat_frame, "_parent_canvas")
        ):
            return self.chat_frame._parent_canvas
        return None

    def _disable_text_scroll(self, text_widget):
        """Désactive complètement le scroll interne du widget Text"""

        def block_scroll(_event):
            return "break"

        # Désactiver tous les événements de scroll
        scroll_events = [
            "<MouseWheel>",
            "<Button-4>",
            "<Button-5>",  # Molette souris
            "<Up>",
            "<Down>",  # Flèches haut/bas
            "<Prior>",
            "<Next>",  # Page Up/Down
            "<Control-Home>",
            "<Control-End>",  # Ctrl+Home/End
            "<Shift-MouseWheel>",  # Shift+molette
            "<Control-MouseWheel>",  # Ctrl+molette
        ]

        for event in scroll_events:
            text_widget.bind(event, block_scroll)

        # Transférer la molette à la conversation, à la vitesse normale. Ce
        # blocage est réappliqué à chaque recalcul de hauteur (fin d'écriture,
        # changement de largeur) : à 1 unité par cran, les bulles IA
        # défilaient 20 fois moins vite que le reste de la conversation.
        text_widget.bind("<MouseWheel>", self._scroll_chat_with_wheel)
        text_widget.bind("<Button-4>", self._scroll_chat_with_wheel)
        text_widget.bind("<Button-5>", self._scroll_chat_with_wheel)

    def _reactivate_text_scroll(self, text_widget):
        """Réactive le scroll après l'animation"""
        try:
            # Supprimer tous les bindings de blocage
            scroll_events = [
                "<MouseWheel>",
                "<Button-4>",
                "<Button-5>",
                "<Up>",
                "<Down>",
                "<Prior>",
                "<Next>",
                "<Control-Home>",
                "<Control-End>",
                "<Shift-MouseWheel>",
            ]

            for event in scroll_events:
                try:
                    text_widget.unbind(event)
                except Exception:
                    pass

            # Réactiver le scroll normal via le système de forwarding
            self.setup_improved_scroll_forwarding(text_widget)

        except Exception as e:
            print(f"[DEBUG] Erreur réactivation scroll: {e}")

    def _cleanup_old_messages(self):
        """⚡ OPTIMISATION MÉMOIRE: Supprime les vieux messages pour limiter l'usage mémoire"""
        try:
            if len(self._message_widgets) > self.max_displayed_messages:
                # Calculer combien supprimer (garder les max_displayed_messages derniers)
                num_to_remove = len(self._message_widgets) - self.max_displayed_messages

                # Supprimer les vieux widgets
                for i in range(num_to_remove):
                    widget = self._message_widgets[i]
                    if widget and widget.winfo_exists():
                        widget.destroy()

                # Mettre à jour la liste
                self._message_widgets = self._message_widgets[num_to_remove:]

                # Aussi nettoyer l'historique de conversation dans l'UI
                if len(self.conversation_history) > self.max_displayed_messages:
                    self.conversation_history = self.conversation_history[-self.max_displayed_messages:]

                print(f"🧹 [MEMORY] Nettoyé {num_to_remove} vieux messages pour optimiser la mémoire")

        except Exception as e:
            print(f"⚠️ [MEMORY] Erreur nettoyage messages: {e}")

    def create_conversation_area_in_frame(self, parent):
        """Crée la zone de conversation dans un frame spécifique"""
        # Utiliser le parent fourni au lieu de self.main_container
        original_create = self.create_conversation_area

        # Sauvegarder temporairement self.main_container
        temp_container = self.main_container

        # Remplacer temporairement par le parent fourni
        self.main_container = parent

        # Appeler la méthode originale
        original_create()

        # Restaurer self.main_container
        self.main_container = temp_container

    def create_conversation_area(self):
        """Crée la zone de conversation principale"""
        # Container pour la conversation
        conv_container = self.create_frame(
            self.main_container, fg_color=self.colors["bg_chat"]
        )
        conv_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=(10, 20))
        conv_container.grid_columnconfigure(0, weight=1)
        conv_container.grid_rowconfigure(0, weight=1)
        # Référence pour l'écran d'accueil (masquage/affichage)
        self._conv_container = conv_container

        # Zone de scroll pour les messages
        if self.use_ctk:
            self.chat_frame = ctk.CTkScrollableFrame(
                conv_container,
                fg_color=self.colors["bg_chat"],
                scrollbar_fg_color=self.colors["bg_secondary"],
            )
            # Défilement manuel (cf. _note_manual_scroll). Lié après le
            # gestionnaire de CTkScrollableFrame, qui a donc déjà fait défiler.
            for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.root.bind_all(sequence, self._on_chat_wheel, add="+")
            # pylint: disable=protected-access
            scrollbar = getattr(self.chat_frame, "_scrollbar", None)
            if scrollbar is not None:
                scrollbar.configure(command=self._on_chat_scrollbar)
        else:
            # Fallback avec Canvas et Scrollbar
            canvas = tk.Canvas(
                conv_container, fg_color=self.colors["bg_chat"], highlightthickness=0
            )
            scrollbar = ttk.Scrollbar(
                conv_container, orient="vertical", command=canvas.yview
            )
            self.chat_frame = tk.Frame(canvas, fg_color=self.colors["bg_chat"])

            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")

            canvas.grid(row=0, column=0, sticky="nsew")
            scrollbar.grid(row=0, column=1, sticky="ns")

            # Mise à jour du scroll
            def configure_scroll(_event):
                canvas.configure(scrollregion=canvas.bbox("all"))

            self.chat_frame.bind("<Configure>", configure_scroll)

        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.chat_frame.grid_columnconfigure(0, weight=1)

        # Zone d'animation de réflexion
        self.thinking_frame = self.create_frame(
            conv_container, fg_color=self.colors["bg_chat"]
        )
        self.thinking_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.thinking_frame.grid_remove()  # Caché par défaut

        self.thinking_label = self.create_label(
            self.thinking_frame,
            text="",
            font=(
                "Segoe UI",
                self.get_current_font_size("message"),
            ),  # UNIFIÉ AVEC LES MESSAGES
            text_color=self.colors["text_secondary"],  # text_color au lieu de fg
            fg_color=self.colors["bg_chat"],
        )
        self.thinking_label.grid(row=0, column=0)

    def _scroll_if_needed_user(self):
        """Scroll pour le message utilisateur uniquement si le bas n'est pas visible"""
        try:
            canvas = self._get_parent_canvas()
            if canvas:
                canvas.update_idletasks()
                yview = canvas.yview()

                if yview and yview[1] < 1.0:
                    canvas.yview_moveto(1.0)
            else:
                parent = self.chat_frame.master
                parent.update_idletasks()
                yview = parent.yview() if hasattr(parent, "yview") else None
                if yview and yview[1] < 1.0:
                    parent.yview_moveto(1.0)
        except Exception:
            pass

    def setup_scroll_forwarding(self, text_widget):
        """Configure le transfert du scroll pour les bulles USER"""
        # Transférer la molette à la conversation, comme toutes les bulles
        text_widget.bind("<MouseWheel>", self._scroll_chat_with_wheel)
        text_widget.bind("<Button-4>", self._scroll_chat_with_wheel)  # Linux scroll up
        text_widget.bind("<Button-5>", self._scroll_chat_with_wheel)  # Linux scroll down

        # Désactiver toutes les autres formes de scroll
        text_widget.bind("<Up>", lambda e=None: "break")
        text_widget.bind("<Down>", lambda e=None: "break")
        text_widget.bind("<Prior>", lambda e=None: "break")  # Page Up
        text_widget.bind("<Next>", lambda e=None: "break")  # Page Down
        text_widget.bind("<Home>", lambda e=None: "break")
        text_widget.bind("<End>", lambda e=None: "break")

    def setup_improved_scroll_forwarding(self, text_widget):
        """Transfert ultra rapide du scroll pour les bulles IA"""
        # SOLUTION FINALE: Désactiver COMPLÈTEMENT le scroll interne du Text widget
        text_widget.configure(state="disabled")  # Désactiver temporairement

        # Supprimer TOUTES les fonctions de scroll par défaut
        text_widget.bind("<MouseWheel>", lambda e=None: "break")
        text_widget.bind("<Button-4>", lambda e=None: "break")
        text_widget.bind("<Button-5>", lambda e=None: "break")
        text_widget.bind("<Control-MouseWheel>", lambda e=None: "break")
        text_widget.bind("<Shift-MouseWheel>", lambda e=None: "break")

        # Remettre en mode normal mais sans scroll interne
        text_widget.configure(state="normal")

        # SOLUTION: Désactiver les bindings par défaut de Tkinter qui interceptent le scroll
        text_widget.unbind("<MouseWheel>")
        text_widget.unbind("<Button-4>")
        text_widget.unbind("<Button-5>")

        # Transférer la molette à la conversation, sur la bulle et son parent
        for widget in (text_widget, text_widget.master):
            widget.bind("<MouseWheel>", self._scroll_chat_with_wheel)
            widget.bind("<Button-4>", self._scroll_chat_with_wheel)
            widget.bind("<Button-5>", self._scroll_chat_with_wheel)

    def _smart_scroll_follow_animation(self):
        """Scroll optimisé qui suit le texte en cours d'écriture.
        Met à jour le scrollregion puis cale la vue sur le dernier caractère
        écrit (cf. _typing_follow_fraction)."""
        try:
            if self.use_ctk:
                canvas = self._get_parent_canvas()
                if canvas:
                    canvas.update_idletasks()
                    # Forcer la mise à jour du scrollregion pour refléter
                    # la nouvelle taille du widget texte (titres = police plus grande)
                    bbox = canvas.bbox("all")
                    if bbox:
                        canvas.configure(scrollregion=bbox)
                        # Utilisateur remonté lire plus haut : la vue ne bouge pas
                        if self._follow_chat_bottom:
                            canvas.yview_moveto(self._typing_follow_fraction(canvas, bbox))
            else:
                # Version tkinter standard
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto") and self._follow_chat_bottom:
                    parent.update_idletasks()
                    parent.yview_moveto(1.0)

        except Exception as e:
            print(f"[DEBUG] Erreur scroll animation: {e}")

    def _typing_follow_fraction(self, canvas, bbox):
        """Position de défilement (yview) qui met le dernier caractère écrit
        en bas de la vue.

        Se caler sur le bas du contenu (1.0) montrait ce qu'il y a sous le
        texte au lieu du texte : pendant l'écriture, la bulle peut être plus
        haute que son contenu (sa hauteur ne fait que croître). Retourne 1.0
        quand le caractère n'est pas localisable.
        """
        widget = getattr(self, "typing_widget", None)
        try:
            char = widget.bbox("end-1c") if widget is not None and widget.winfo_exists() else None
        except tk.TclError:
            char = None
        content_height = bbox[3] - bbox[1]
        if not char or content_height <= 0:
            return 1.0
        # Bas du caractère, en coordonnées du canvas
        char_bottom = (
            widget.winfo_rooty() - canvas.winfo_rooty() + canvas.canvasy(0)
            + char[1] + char[3]
        )
        view_top = char_bottom + self._FOLLOW_MARGIN_PX - canvas.winfo_height()
        # Au-delà de la fin, Tk ramène la vue sur le bas du contenu
        return max(0.0, (view_top - bbox[1]) / content_height)

    def _force_scroll_to_bottom(self):
        """Force un scroll vers le bas quand un gros contenu est ajouté"""
        try:
            if self.use_ctk:
                canvas = self._get_parent_canvas()
                if canvas:
                    canvas.update_idletasks()
                    # Scroll directement vers le bas avec une petite marge
                    canvas.yview_moveto(
                        0.9
                    )  # Pas tout à fait au bas pour laisser de l'espace
                    canvas.update()
            else:
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.update_idletasks()
                    parent.yview_moveto(0.9)
                    parent.update()
        except Exception as e:
            print(f"[DEBUG] Erreur force scroll: {e}")

    def _final_smooth_scroll_to_bottom(self):
        """Scroll final fiable — met à jour le scrollregion puis force au bas"""
        # Fin de réponse : l'utilisateur remonté lire plus haut y reste
        if not self._follow_chat_bottom:
            return
        try:
            self.root.update_idletasks()

            if self.use_ctk:
                canvas = self._get_parent_canvas()
                if canvas:
                    # Mettre à jour le scrollregion pour inclure le timestamp/feedback
                    bbox = canvas.bbox("all")
                    if bbox:
                        canvas.configure(scrollregion=bbox)
                    canvas.yview_moveto(1.0)
                    # Double scroll après un court délai pour couvrir les
                    # éventuelles mises à jour de géométrie tardives
                    def _ensure_bottom():
                        if not self._follow_chat_bottom:
                            return
                        try:
                            canvas.update_idletasks()
                            bbox2 = canvas.bbox("all")
                            if bbox2:
                                canvas.configure(scrollregion=bbox2)
                            canvas.yview_moveto(1.0)
                        except Exception:
                            pass
                    self.root.after(100, _ensure_bottom)
            else:
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.update_idletasks()
                    parent.yview_moveto(1.0)
                    self.root.after(100, lambda: parent.yview_moveto(1.0))

        except Exception:
            # Fallback : scroll simple
            try:
                canvas = self._get_parent_canvas()
                if canvas:
                    canvas.yview_moveto(1.0)
                else:
                    parent = self.chat_frame.master
                    if hasattr(parent, "yview_moveto"):
                        parent.yview_moveto(1.0)
            except Exception:
                pass

    def scroll_to_bottom_smooth(self):
        """Scroll vers le bas en douceur, sans clignotement"""

        try:
            # Une seule mise à jour, puis scroll
            self.root.update_idletasks()

            if self.use_ctk:
                if hasattr(self, "chat_frame"):
                    parent = self.chat_frame.master
                    while parent and not hasattr(parent, "yview_moveto"):
                        parent = parent.master

                    if parent and hasattr(parent, "yview_moveto"):
                        parent.yview_moveto(1.0)
            else:
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.yview_moveto(1.0)

        except Exception as e:
            print(f"Erreur scroll doux: {e}")

    def scroll_to_bottom(self):
        """Version CORRIGÉE - Scroll contrôlé avec délai"""
        # CORRECTION : Ajouter un délai pour laisser le temps au contenu de se rendre
        self.root.after(200, self._perform_scroll_to_bottom)

    def _perform_scroll_to_bottom(self):
        """Scroll synchronisé pour éviter le décalage entre icônes et texte"""
        try:
            # Forcer la mise à jour de TOUT l'interface avant le scroll
            self.root.update_idletasks()
            self.main_container.update_idletasks()

            if hasattr(self, "chat_frame"):
                self.chat_frame.update_idletasks()

            if self.use_ctk:
                # CustomTkinter
                if hasattr(self, "chat_frame"):
                    parent = self.chat_frame.master
                    while parent and not hasattr(parent, "yview_moveto"):
                        parent = parent.master

                    if parent and hasattr(parent, "yview_moveto"):
                        # Double mise à jour pour synchronisation parfaite
                        parent.update_idletasks()
                        parent.yview_moveto(1.0)
                        # Petite pause pour éviter le décalage
                        self.root.after(1, lambda: parent.yview_moveto(1.0))
            else:
                # Tkinter standard
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.update_idletasks()
                    parent.yview_moveto(1.0)
                    self.root.after(1, lambda: parent.yview_moveto(1.0))

        except Exception as e:
            print(f"Erreur scroll synchronisé: {e}")

    def _force_scroll_bottom(self):
        """Force le scroll vers le bas - tentative secondaire"""
        try:
            if self.use_ctk:
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.yview_moveto(1.0)
            else:
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.yview_moveto(1.0)
        except Exception:
            pass  # Silencieux pour éviter spam logs

    def scroll_to_top(self):
        """Fait défiler vers le HAUT de la conversation (pour clear chat)"""
        try:
            self.root.update_idletasks()

            if self.use_ctk:
                # CustomTkinter - Chercher le scrollable frame
                if hasattr(self, "chat_frame"):
                    try:
                        # Méthode 1: Via le parent canvas (plus fiable)
                        parent = self.chat_frame.master
                        while parent and not hasattr(parent, "yview_moveto"):
                            parent = parent.master

                        if parent and hasattr(parent, "yview_moveto"):
                            parent.update_idletasks()
                            parent.yview_moveto(0.0)  # 0.0 pour le HAUT
                            self.logger.debug(
                                "Scroll vers le haut CTk via parent canvas"
                            )
                        else:
                            # Méthode 2: Canvas direct
                            canvas = self._get_parent_canvas()
                            if canvas:
                                canvas.update_idletasks()
                                canvas.yview_moveto(0.0)  # 0.0 pour le HAUT
                                self.logger.debug(
                                    "Scroll vers le haut CTk via canvas parent"
                                )
                            else:
                                self.logger.warning("Canvas parent non disponible")
                    except Exception as e:
                        self.logger.error("Erreur scroll vers le haut CTk: %s", e)
            else:
                # Tkinter standard - Chercher le canvas scrollable
                try:
                    parent = self.chat_frame.master
                    if hasattr(parent, "yview_moveto"):
                        parent.update_idletasks()
                        parent.yview_moveto(0.0)  # 0.0 pour le HAUT
                        self.logger.debug(
                            "Scroll vers le haut tkinter via parent direct"
                        )
                    else:
                        # Chercher dans la hiérarchie
                        current = parent
                        while current:
                            if hasattr(current, "yview_moveto"):
                                current.update_idletasks()
                                current.yview_moveto(0.0)  # 0.0 pour le HAUT
                                self.logger.debug(
                                    "Scroll vers le haut tkinter via hiérarchie"
                                )
                                break
                            current = current.master
                except Exception as e:
                    self.logger.error("Erreur scroll vers le haut tkinter: %s", e)

            # Forcer une seconde tentative après délai court
            self.root.after(100, self._force_scroll_top)

        except Exception as e:
            self.logger.error("Erreur critique lors du scroll vers le haut: %s", e)

    def _force_scroll_top(self):
        """Force le scroll vers le haut - tentative secondaire"""
        try:
            if self.use_ctk:
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.yview_moveto(0.0)  # 0.0 pour le HAUT
            else:
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.yview_moveto(0.0)  # 0.0 pour le HAUT
        except Exception:
            pass  # Silencieux pour éviter spam logs
