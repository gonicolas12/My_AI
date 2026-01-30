"""Chat area and scrolling mixin for ModernAIGUI."""

import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk

    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    ctk = tk


class ChatAreaMixin:
    """Conversation area and scrolling helpers."""

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

        # Transférer le scroll vers le conteneur principal
        def forward_to_main_scroll(event):
            try:
                if hasattr(self, "chat_frame"):
                    canvas = self._get_parent_canvas()
                    if canvas:
                        if hasattr(event, "delta") and event.delta:
                            scroll_delta = -1 * (event.delta // 120)
                        else:
                            scroll_delta = -1 if event.num == 4 else 1
                        canvas.yview_scroll(scroll_delta, "units")
                    else:
                        parent = self.chat_frame.master
                        while parent and not hasattr(parent, "yview_scroll"):
                            parent = parent.master
                        if parent:
                            if hasattr(event, "delta") and event.delta:
                                scroll_delta = -1 * (event.delta // 120)
                            else:
                                scroll_delta = -1 if event.num == 4 else 1
                            parent.yview_scroll(scroll_delta, "units")
            except Exception:
                pass
            return "break"

        # Appliquer le transfert de scroll uniquement pour la molette
        text_widget.bind("<MouseWheel>", forward_to_main_scroll)
        text_widget.bind("<Button-4>", forward_to_main_scroll)
        text_widget.bind("<Button-5>", forward_to_main_scroll)

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

        # Zone de scroll pour les messages
        if self.use_ctk:
            self.chat_frame = ctk.CTkScrollableFrame(
                conv_container,
                fg_color=self.colors["bg_chat"],
                scrollbar_fg_color=self.colors["bg_secondary"],
            )
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
        """Configure le transfert du scroll - Version ultra rapide pour bulles USER"""

        def forward_scroll_to_page(event):
            try:
                # Transférer le scroll à la zone de conversation principale
                if hasattr(self, "chat_frame"):
                    # Pour CustomTkinter ScrollableFrame - SCROLL ULTRA RAPIDE
                    canvas = self._get_parent_canvas()
                    if canvas:
                        # Amplifier le delta pour scroll ultra rapide (x20 plus rapide)
                        if hasattr(event, "delta") and event.delta:
                            scroll_delta = -1 * (
                                event.delta // 6
                            )  # 6 au lieu de 120 = 20x plus rapide
                        elif hasattr(event, "num"):
                            scroll_delta = (
                                -20 if event.num == 4 else 20
                            )  # 20x plus rapide
                        else:
                            scroll_delta = -20
                        canvas.yview_scroll(scroll_delta, "units")
                    else:
                        # Pour tkinter standard - SCROLL ULTRA RAPIDE
                        parent = self.chat_frame.master
                        while parent and not hasattr(parent, "yview_scroll"):
                            parent = parent.master
                        if parent:
                            # Amplifier le delta pour scroll MEGA ULTRA rapide (x60 plus rapide !)
                            if hasattr(event, "delta") and event.delta:
                                scroll_delta = -1 * (
                                    event.delta // 2
                                )  # 2 au lieu de 120 = 60x plus rapide !
                            elif hasattr(event, "num"):
                                scroll_delta = (
                                    -60 if event.num == 4 else 60
                                )  # 60x plus rapide
                            else:
                                scroll_delta = -60
                            parent.yview_scroll(scroll_delta, "units")
            except Exception:
                pass
            return "break"  # Empêcher le scroll local

        # Appliquer le transfert de scroll
        text_widget.bind("<MouseWheel>", forward_scroll_to_page)
        text_widget.bind("<Button-4>", forward_scroll_to_page)  # Linux scroll up
        text_widget.bind("<Button-5>", forward_scroll_to_page)  # Linux scroll down

        # Désactiver toutes les autres formes de scroll
        text_widget.bind("<Up>", lambda e: "break")
        text_widget.bind("<Down>", lambda e: "break")
        text_widget.bind("<Prior>", lambda e: "break")  # Page Up
        text_widget.bind("<Next>", lambda e: "break")  # Page Down
        text_widget.bind("<Home>", lambda e: "break")
        text_widget.bind("<End>", lambda e: "break")

    def setup_improved_scroll_forwarding(self, text_widget):
        """Transfert ultra rapide du scroll pour les bulles IA"""
        # SOLUTION FINALE: Désactiver COMPLÈTEMENT le scroll interne du Text widget
        text_widget.configure(state="disabled")  # Désactiver temporairement

        # Supprimer TOUTES les fonctions de scroll par défaut
        text_widget.bind("<MouseWheel>", lambda e: "break")
        text_widget.bind("<Button-4>", lambda e: "break")
        text_widget.bind("<Button-5>", lambda e: "break")
        text_widget.bind("<Control-MouseWheel>", lambda e: "break")
        text_widget.bind("<Shift-MouseWheel>", lambda e: "break")

        # Remettre en mode normal mais sans scroll interne
        text_widget.configure(state="normal")

        # SOLUTION FINALE: Utiliser EXACTEMENT la même logique que les bulles USER
        def forward_scroll_to_page(event):
            try:
                # Transférer le scroll à la zone de conversation principale
                if hasattr(self, "chat_frame"):
                    # Pour CustomTkinter ScrollableFrame - MÊME LOGIQUE QUE USER
                    canvas = self._get_parent_canvas()
                    if canvas:
                        # EXACTEMENT la même amplification que les bulles USER
                        if hasattr(event, "delta") and event.delta:
                            scroll_delta = -1 * (event.delta // 6)  # MÊME que USER
                        elif hasattr(event, "num"):
                            scroll_delta = (
                                -20 if event.num == 4 else 20
                            )  # MÊME que USER
                        else:
                            scroll_delta = -20
                        canvas.yview_scroll(scroll_delta, "units")
                    else:
                        # Pour tkinter standard - MÊME LOGIQUE QUE USER
                        parent = self.chat_frame.master
                        while parent and not hasattr(parent, "yview_scroll"):
                            parent = parent.master
                        if parent:
                            # EXACTEMENT la même amplification que les bulles USER
                            if hasattr(event, "delta") and event.delta:
                                scroll_delta = -1 * (event.delta // 6)  # MÊME que USER
                            elif hasattr(event, "num"):
                                scroll_delta = (
                                    -20 if event.num == 4 else 20
                                )  # MÊME que USER
                            else:
                                scroll_delta = -20
                            parent.yview_scroll(scroll_delta, "units")
            except Exception:
                pass
            return "break"  # Empêcher le scroll local - MÊME que USER

        # SOLUTION: Désactiver les bindings par défaut de Tkinter qui interceptent le scroll
        text_widget.unbind("<MouseWheel>")
        text_widget.unbind("<Button-4>")
        text_widget.unbind("<Button-5>")

        # Appliquer le transfert de scroll ultra rapide
        text_widget.bind("<MouseWheel>", forward_scroll_to_page)
        text_widget.bind("<Button-4>", forward_scroll_to_page)
        text_widget.bind("<Button-5>", forward_scroll_to_page)

        # Vérifier l'état du widget

        # Tester les événements au niveau du PARENT aussi
        parent_frame = text_widget.master

        def parent_test_event(event):
            # Transférer vers notre fonction
            return forward_scroll_to_page(event)

        # Ajouter les bindings au parent ET au text widget
        parent_frame.bind("<MouseWheel>", parent_test_event)
        parent_frame.bind("<Button-4>", parent_test_event)
        parent_frame.bind("<Button-5>", parent_test_event)

    def _smart_scroll_follow_animation(self):
        """Scroll optimisé qui évite le clignotement"""
        try:
            if self.use_ctk:
                canvas = self._get_parent_canvas()
                if canvas:

                    # 🔧 OPTIMISATION : Ne scroll que si nécessaire
                    canvas.update_idletasks()

                    # Vérifier la position actuelle pour éviter les scrolls inutiles
                    current_scroll = canvas.canvasy(canvas.winfo_height())
                    total_height = canvas.bbox("all")[3] if canvas.bbox("all") else 0

                    # Ne scroll que si on n'est pas déjà proche du bas (tolérance de 50px)
                    if total_height - current_scroll > 50:
                        canvas.yview_moveto(1.0)

                    # Mise à jour immédiate
                    canvas.update()

            else:
                # Version tkinter standard
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    parent.update_idletasks()
                    parent.yview_moveto(1.0)
                    parent.update()

        except Exception as e:
            print(f"[DEBUG] Erreur scroll animation: {e}")

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
        """Scroll final en douceur sans saut brutal"""
        try:
            # Une seule mise à jour, puis scroll progressif
            self.root.update_idletasks()

            if self.use_ctk:
                canvas = self._get_parent_canvas()
                if canvas:

                    # Scroll progressif vers le bas
                    for i in range(5):  # 5 étapes progressives
                        current_yview = canvas.yview()
                        if current_yview and current_yview[1] < 1.0:
                            # Calculer la position intermédiaire
                            current_top = current_yview[0]
                            step = (1.0 - current_top) / (5 - i)
                            new_position = min(1.0, current_top + step)
                            canvas.yview_moveto(new_position)
                            canvas.update_idletasks()
                        else:
                            break
            else:
                parent = self.chat_frame.master
                if hasattr(parent, "yview_moveto"):
                    for i in range(5):
                        current_yview = parent.yview()
                        if current_yview and current_yview[1] < 1.0:
                            current_top = current_yview[0]
                            step = (1.0 - current_top) / (5 - i)
                            new_position = min(1.0, current_top + step)
                            parent.yview_moveto(new_position)
                            parent.update_idletasks()
                        else:
                            break

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
