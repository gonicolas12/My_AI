"""Message bubbles mixin for ModernAIGUI."""

import tkinter as tk
import traceback
from datetime import datetime

try:
    import customtkinter as ctk

    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    ctk = tk


class MessageBubblesMixin:
    """Methods for creating user/AI message bubbles and copy UI."""

    def _show_timestamp_for_current_message(self):
        """Affiche le timestamp sous la bulle du dernier message IA (comme pour l'utilisateur)."""
        if (
            hasattr(self, "current_message_container")
            and self.current_message_container is not None
        ):
            # Vérifier qu'il n'y a pas déjà un timestamp (évite doublons)
            for child in self.current_message_container.winfo_children():
                if isinstance(child, (tk.Label,)):
                    if getattr(child, "is_timestamp", False):
                        return  # Déjà affiché
            timestamp = datetime.now().strftime("%H:%M")
            time_label = self.create_label(
                self.current_message_container,
                text=timestamp,
                font=("Segoe UI", 10),
                fg_color=self.colors["bg_chat"],
                text_color="#b3b3b3",
            )
            time_label.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))
            time_label.is_timestamp = True
        # Sinon, rien à faire (pas de container)

    def add_message_bubble(self, text, is_user=True, message_type="text"):
        """Version FINALE avec animation de frappe pour les messages IA"""
        # Vérifier que le texte est une chaîne
        if not isinstance(text, str):
            if isinstance(text, dict):
                text = (
                    text.get("response")
                    or text.get("text")
                    or text.get("content")
                    or text.get("message")
                    or str(text)
                )
            else:
                text = str(text)

        # Ajouter à l'historique
        self.conversation_history.append(
            {
                "text": text,
                "is_user": is_user,
                "timestamp": datetime.now(),
                "type": message_type,
            }
        )

        # Container principal avec espacement OPTIMAL
        msg_container = self.create_frame(
            self.chat_frame, fg_color=self.colors["bg_chat"]
        )
        msg_container.grid(
            row=len(self.conversation_history) - 1, column=0, sticky="ew", pady=(0, 12)
        )
        msg_container.grid_columnconfigure(0, weight=1)

        # ⚡ OPTIMISATION: Tracker ce widget pour nettoyage ultérieur
        self._message_widgets.append(msg_container)

        # ⚡ OPTIMISATION MÉMOIRE: Nettoyer les vieux messages si trop nombreux
        self._cleanup_old_messages()

        if is_user:
            self.create_user_message_bubble(msg_container, text)
            # Scroll utilisateur : scroller uniquement si le bas n'est pas visible
            self.root.after(50, self._scroll_if_needed_user())
        else:
            # Crée la bulle IA mais insère le texte vide, puis lance l'animation de frappe
            # Frame de centrage
            center_frame = self.create_frame(
                msg_container, fg_color=self.colors["bg_chat"]
            )
            center_frame.grid(
                row=0, column=0, padx=(250, 250), pady=(0, 0), sticky="ew"
            )
            center_frame.grid_columnconfigure(0, weight=0)
            center_frame.grid_columnconfigure(1, weight=1)

            # Icône IA
            icon_label = self.create_label(
                center_frame,
                text="🤖",
                font=("Segoe UI", 16),
                fg_color=self.colors["bg_chat"],
                text_color=self.colors["accent"],
            )
            icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0))

            # Container pour le message IA
            message_container = self.create_frame(
                center_frame, fg_color=self.colors["bg_chat"]
            )
            message_container.grid(row=0, column=1, sticky="ew", padx=0, pady=(2, 2))
            message_container.grid_columnconfigure(0, weight=1)

            # ⚡ SOLUTION FINALE: Appliquer le scroll forwarding SUR LE CONTAINER !
            def setup_container_scroll_forwarding(container):
                """Configure le scroll forwarding sur le container IA pour égaler la vitesse utilisateur"""

                def forward_from_container(event):
                    try:
                        if hasattr(self, "chat_frame") and self.use_ctk:
                            canvas = self._get_parent_canvas()
                            if not canvas:
                                return
                            if hasattr(event, "delta") and event.delta:
                                # AMPLIFICATION 60x pour égaler la vitesse utilisateur
                                scroll_delta = -1 * (event.delta // 6) * 60
                            else:
                                scroll_delta = -20 * 60
                            canvas.yview_scroll(scroll_delta, "units")
                        return "break"
                    except Exception:
                        return "break"

                container.bind("<MouseWheel>", forward_from_container)
                container.bind("<Button-4>", forward_from_container)
                container.bind("<Button-5>", forward_from_container)

            setup_container_scroll_forwarding(message_container)

            # Stocker le container pour l'affichage du timestamp
            self.current_message_container = message_container

            # Zone de texte pour le message IA
            text_widget = tk.Text(
                message_container,
                width=120,
                height=1,
                bg=self.colors["bg_chat"],
                fg=self.colors["text_primary"],
                font=("Segoe UI", 12),
                wrap=tk.WORD,
                relief="flat",
                bd=0,
                highlightthickness=0,
                state="normal",
                cursor="xterm",
                padx=8,
                pady=6,
                selectbackground="#4a90e2",
                selectforeground="#ffffff",
                exportselection=True,
                takefocus=False,
                insertwidth=0,
                # DÉSACTIVER COMPLÈTEMENT LE SCROLL INTERNE
                yscrollcommand=None,
                xscrollcommand=None,
            )
            text_widget.grid(row=0, column=0, padx=0, pady=(0, 0), sticky="nsew")
            # Ajustement avec hauteur généreuse pour éviter les scrollbars
            self.adjust_text_widget_height(text_widget)

            # Bind SEULEMENT pour les touches, pas pour la souris
            def prevent_editing_only(event):
                editing_keys = [
                    "BackSpace",
                    "Delete",
                    "Return",
                    "KP_Enter",
                    "Tab",
                    "space",
                    "Insert",
                ]
                if event.state & 0x4:
                    if event.keysym.lower() in ["a", "c"]:
                        return None
                if event.keysym in editing_keys:
                    return "break"
                if len(event.keysym) == 1 and event.keysym.isprintable():
                    return "break"
                return None

            text_widget.bind("<KeyPress>", prevent_editing_only)

            # UTILISER LA MÊME FONCTION QUE LES BULLES USER !
            # MAIS ON VA FORCER LA VITESSE A ÊTRE IDENTIQUE AUX USER !
            def setup_identical_scroll_to_user(text_widget_ia):
                """SCROLL IDENTIQUE AUX BULLES USER - Version finale"""

                def forward_user_style(event):
                    try:
                        if hasattr(self, "chat_frame") and self.use_ctk:
                            canvas = self._get_parent_canvas()
                            if not canvas:
                                return
                            if hasattr(event, "delta") and event.delta:
                                scroll_delta = -1 * (
                                    event.delta // 6
                                )  # EXACTEMENT comme USER
                            elif hasattr(event, "num"):
                                scroll_delta = (
                                    -20 if event.num == 4 else 20
                                )  # EXACTEMENT comme USER
                            else:
                                scroll_delta = -20
                            canvas.yview_scroll(scroll_delta, "units")
                    except Exception:
                        pass
                    return "break"

                # Bindings IDENTIQUES aux USER
                text_widget_ia.bind("<MouseWheel>", forward_user_style)
                text_widget_ia.bind("<Button-4>", forward_user_style)
                text_widget_ia.bind("<Button-5>", forward_user_style)
                text_widget_ia.bind("<Up>", lambda e: "break")
                text_widget_ia.bind("<Down>", lambda e: "break")
                text_widget_ia.bind("<Prior>", lambda e: "break")
                text_widget_ia.bind("<Next>", lambda e: "break")
                text_widget_ia.bind("<Home>", lambda e: "break")
                text_widget_ia.bind("<End>", lambda e: "break")

            setup_identical_scroll_to_user(text_widget)

            # SOLUTION DÉFINITIVE : Copier EXACTEMENT le système des bulles USER
            def apply_exact_user_scroll_system():
                """Applique EXACTEMENT le même système que les bulles USER"""

                def forward_scroll_to_page_ia(event):
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
                    except Exception:
                        pass
                    return "break"  # Empêcher le scroll local

                # Appliquer le transfert de scroll EXACTEMENT comme USER
                text_widget.bind("<MouseWheel>", forward_scroll_to_page_ia)
                text_widget.bind(
                    "<Button-4>", forward_scroll_to_page_ia
                )  # Linux scroll up
                text_widget.bind(
                    "<Button-5>", forward_scroll_to_page_ia
                )  # Linux scroll down

                # Désactiver toutes les autres formes de scroll EXACTEMENT comme USER
                text_widget.bind("<Up>", lambda e: "break")
                text_widget.bind("<Down>", lambda e: "break")
                text_widget.bind("<Prior>", lambda e: "break")  # Page Up
                text_widget.bind("<Next>", lambda e: "break")  # Page Down
                text_widget.bind("<Home>", lambda e: "break")
                text_widget.bind("<End>", lambda e: "break")

            apply_exact_user_scroll_system()

            # FORCER L'APPLICATION APRÈS TOUS LES AUTRES SETUPS !
            def force_final_bindings():
                """Force finale après que tout soit terminé"""

                def final_scroll_handler(event):
                    try:
                        if hasattr(self, "chat_frame") and self.use_ctk:
                            canvas = self._get_parent_canvas()
                            if not canvas:
                                return
                            if hasattr(event, "delta") and event.delta:
                                scroll_delta = -1 * (event.delta // 6)
                            else:
                                scroll_delta = -20
                            canvas.yview_scroll(scroll_delta, "units")
                    except Exception:
                        pass
                    return "break"

                # Override avec force absolue
                text_widget.bind("<MouseWheel>", final_scroll_handler, add=False)
                text_widget.bind("<Button-4>", final_scroll_handler, add=False)
                text_widget.bind("<Button-5>", final_scroll_handler, add=False)

            # Appliquer après TOUS les autres setups (délais multiples)
            text_widget.after(200, force_final_bindings)
            text_widget.after(500, force_final_bindings)
            text_widget.after(1000, force_final_bindings)

            def copy_on_double_click(_event):
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(text)
                    self.show_copy_notification("✅ Message copié !")
                except Exception:
                    self.show_copy_notification("❌ Erreur de copie")
                return "break"

            text_widget.bind("<Double-Button-1>", copy_on_double_click)
            self.create_copy_menu_with_notification(text_widget, text)

            # Démarrer l'animation de frappe avec hauteur dynamique
            self.start_typing_animation_dynamic(text_widget, text)

    def create_user_message_bubble(self, parent, text):
        """Version avec hauteur précise et sélection activée pour les messages utilisateur"""
        if not isinstance(text, str):
            text = str(text)

        # Frame principale
        main_frame = self.create_frame(parent, fg_color=self.colors["bg_chat"])
        main_frame.grid(row=0, column=0, padx=(250, 250), pady=(0, 0), sticky="ew")
        main_frame.grid_columnconfigure(0, weight=0)
        main_frame.grid_columnconfigure(1, weight=1)

        # Icône utilisateur
        icon_label = self.create_label(
            main_frame,
            text="👤",
            font=("Segoe UI", 16),
            fg_color=self.colors["bg_chat"],
            text_color=self.colors["text_primary"],
        )
        icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0))

        # Bulle utilisateur
        if self.use_ctk:
            bubble = ctk.CTkFrame(
                main_frame,
                fg_color=self.colors["bg_user"],
                corner_radius=12,
                border_width=0,
            )
        else:
            bubble = tk.Frame(
                main_frame,
                bg=self.colors["bg_user"],
                relief="flat",
                bd=0,
                highlightthickness=0,
            )

        bubble.grid(row=0, column=1, sticky="w", padx=0, pady=(2, 2))
        bubble.grid_columnconfigure(0, weight=0)

        # Calcul de hauteur PRÉCISE pour utilisateur
        word_count = len(text.split())

        # Largeur adaptée
        if word_count > 25:
            text_width = 120
        elif word_count > 10:
            text_width = 90
        elif word_count > 3:
            text_width = 70
        else:
            text_width = max(30, len(text) + 10)

        text_widget = tk.Text(
            bubble,
            width=text_width,
            height=2,  # Valeur initiale minimale
            bg=self.colors["bg_user"],
            fg="#ffffff",
            font=("Segoe UI", 12),
            wrap=tk.WORD,
            relief="flat",
            bd=0,
            highlightthickness=0,
            state="normal",
            cursor="xterm",
            padx=10,
            pady=8,
            selectbackground="#2563eb",
            selectforeground="#ffffff",
            exportselection=True,
            takefocus=False,
            insertwidth=0,
        )

        self.insert_formatted_text_tkinter(text_widget, text)

        # Ajustement parfait de la hauteur après rendu
        def adjust_height_later():
            text_widget.update_idletasks()
            line_count = int(text_widget.index("end-1c").split(".", maxsplit=1)[0])
            text_widget.configure(height=max(2, line_count))
            text_widget.update_idletasks()
            # Scroll automatique après ajustement
            if hasattr(self, "_force_scroll_to_bottom"):
                self._force_scroll_to_bottom()

        text_widget.after(30, adjust_height_later)

        # Empêcher l'édition mais permettre la sélection
        def on_key_press(event):
            """Permet les raccourcis de sélection et copie, bloque l'édition"""
            # Autoriser Ctrl+A (tout sélectionner)
            if event.state & 0x4 and event.keysym.lower() == "a":
                text_widget.tag_add("sel", "1.0", "end")
                return "break"

            # Autoriser Ctrl+C (copier)
            elif event.state & 0x4 and event.keysym.lower() == "c":
                try:
                    selected_text = text_widget.selection_get()
                    if selected_text:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(selected_text)
                        if hasattr(self, "show_copy_notification"):
                            self.show_copy_notification("📋 Sélection copiée !")
                except tk.TclError:
                    pass
                return "break"

            # Autoriser les touches de sélection (Shift + flèches, etc.)
            elif event.keysym in ["Left", "Right", "Up", "Down", "Home", "End"] and (
                event.state & 0x1
            ):
                return None  # Laisser le widget gérer la sélection

            # Bloquer toutes les autres touches (édition)
            else:
                return "break"

        text_widget.bind("<Key>", on_key_press)
        text_widget.bind("<KeyPress>", on_key_press)

        # Configuration du scroll amélioré
        self.setup_scroll_forwarding(text_widget)

        # COPIE avec double-clic
        def copy_on_double_click(_event):
            try:
                # Essayer de copier la sélection d'abord
                try:
                    selected_text = text_widget.selection_get()
                    if selected_text.strip():
                        self.root.clipboard_clear()
                        self.root.clipboard_append(selected_text)
                        self.show_copy_notification("📋 Sélection copiée !")
                        return "break"
                except tk.TclError:
                    pass

                # Si pas de sélection, copier tout le message
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.show_copy_notification("📋 Message copié !")
            except Exception:
                self.show_copy_notification("❌ Erreur de copie")
            return "break"

        text_widget.bind("<Double-Button-1>", copy_on_double_click)
        text_widget.grid(row=0, column=0, padx=8, pady=(6, 0), sticky="nw")

        # Timestamp
        timestamp = datetime.now().strftime("%H:%M")
        time_label = self.create_label(
            bubble,
            text=timestamp,
            font=("Segoe UI", 10),
            fg_color=self.colors["bg_user"],
            text_color="#b3b3b3",
        )
        time_label.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))

        # Menu contextuel amélioré
        def show_context_menu(event):
            try:
                context_menu = tk.Menu(
                    self.root,
                    tearoff=0,
                    bg="#3b82f6",
                    fg="white",
                    activebackground="#2563eb",
                    activeforeground="white",
                )

                # Vérifier s'il y a une sélection
                has_selection = False
                try:
                    selected = text_widget.selection_get()
                    has_selection = bool(selected.strip())
                except tk.TclError:
                    pass

                if has_selection:
                    context_menu.add_command(
                        label="📋 Copier la sélection",
                        command=lambda: copy_on_double_click(None),
                    )
                    context_menu.add_separator()

                context_menu.add_command(
                    label="📄 Copier tout le message",
                    command=lambda: (
                        self.root.clipboard_clear(),
                        self.root.clipboard_append(text),
                        self.show_copy_notification("📋 Message copié !"),
                    ),
                )

                context_menu.add_command(
                    label="🔍 Tout sélectionner",
                    command=lambda: text_widget.tag_add("sel", "1.0", "end"),
                )

                context_menu.tk_popup(event.x_root, event.y_root)

            except Exception:
                pass
            finally:
                try:
                    context_menu.grab_release()
                except Exception:
                    pass

        text_widget.bind("<Button-3>", show_context_menu)  # Clic droit

    def create_ai_message_simple(self, parent, text):
        """Version CORRIGÉE pour les résumés - Hauteur automatique sans scroll interne"""
        try:
            # Vérifier que le texte est une chaîne
            if not isinstance(text, str):
                if isinstance(text, dict):
                    text = (
                        text.get("response")
                        or text.get("text")
                        or text.get("content")
                        or text.get("message")
                        or str(text)
                    )
                else:
                    text = str(text)

            # Frame de centrage
            center_frame = self.create_frame(parent, fg_color=self.colors["bg_chat"])
            center_frame.grid(
                row=0, column=0, padx=(250, 250), pady=(0, 0), sticky="ew"
            )
            center_frame.grid_columnconfigure(0, weight=0)
            center_frame.grid_columnconfigure(1, weight=1)

            # Icône IA
            icon_label = self.create_label(
                center_frame,
                text="🤖",
                font=("Segoe UI", 16),
                fg_color=self.colors["bg_chat"],
                text_color=self.colors["accent"],
            )
            icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0))

            # Container pour le message IA
            message_container = self.create_frame(
                center_frame, fg_color=self.colors["bg_chat"]
            )
            message_container.grid(row=0, column=1, sticky="ew", padx=0, pady=(2, 2))
            message_container.grid_columnconfigure(0, weight=1)

            # ⚡ SOLUTION: Appliquer le scroll forwarding SUR LE CONTAINER aussi ici !
            def setup_container_scroll_forwarding_simple(container):
                """Configure le scroll forwarding sur le container IA (version simple)"""

                def forward_from_container(event):
                    try:
                        if hasattr(self, "chat_frame") and self.use_ctk:
                            canvas = self._get_parent_canvas()
                            if not canvas:
                                return
                            if hasattr(event, "delta") and event.delta:
                                # AMPLIFICATION 60x pour égaler la vitesse utilisateur
                                scroll_delta = -1 * (event.delta // 6) * 60
                            else:
                                scroll_delta = -20 * 60
                            canvas.yview_scroll(scroll_delta, "units")
                        return "break"
                    except Exception:
                        return "break"

                container.bind("<MouseWheel>", forward_from_container)
                container.bind("<Button-4>", forward_from_container)
                container.bind("<Button-5>", forward_from_container)

            setup_container_scroll_forwarding_simple(message_container)

            # Stocker le container pour l'affichage du timestamp
            self.current_message_container = message_container

            # 🔧 CALCUL INTELLIGENT DE LA HAUTEUR BASÉ SUR LE CONTENU
            estimated_height = self._calculate_text_height_for_widget(text)

            # Widget Text avec hauteur calculée
            text_widget = tk.Text(
                message_container,
                width=120,
                height=estimated_height,  # Hauteur calculée intelligemment
                bg=self.colors["bg_chat"],
                fg=self.colors["text_primary"],
                font=("Segoe UI", 12),
                wrap=tk.WORD,
                relief="flat",
                bd=0,
                highlightthickness=0,
                state="normal",
                cursor="xterm",
                padx=8,
                pady=6,
                selectbackground="#4a90e2",
                selectforeground="#ffffff",
                exportselection=True,
                takefocus=False,
                insertwidth=0,
            )

            # 🔧 DÉSACTIVER LE SCROLL INTERNE DÈS LA CRÉATION
            self._disable_text_scroll(text_widget)

            text_widget.grid(row=0, column=0, padx=0, pady=(0, 0), sticky="nsew")

            # Bind minimal pour permettre la sélection
            def prevent_editing_only(event):
                editing_keys = [
                    "BackSpace",
                    "Delete",
                    "Return",
                    "KP_Enter",
                    "Tab",
                    "space",
                    "Insert",
                ]
                if event.state & 0x4:
                    if event.keysym.lower() in ["a", "c"]:
                        return None
                if event.keysym in editing_keys:
                    return "break"
                if len(event.keysym) == 1 and event.keysym.isprintable():
                    return "break"
                return None

            text_widget.bind("<KeyPress>", prevent_editing_only)

            def copy_on_double_click(_event):
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(text)
                    self.show_copy_notification("✅ Message copié !")
                except Exception:
                    self.show_copy_notification("❌ Erreur de copie")
                return "break"

            text_widget.bind("<Double-Button-1>", copy_on_double_click)
            self.create_copy_menu_with_notification(text_widget, text)

            # Démarrer l'animation de frappe avec hauteur pré-calculée
            self.start_typing_animation_dynamic(text_widget, text)

        except Exception as e:
            err_msg = f"[ERREUR affichage IA] {e}\n{traceback.format_exc()}"
            if hasattr(self, "logger"):
                self.logger.error(err_msg)
            fallback_text = f"❌ Erreur d'affichage du message IA :\n{e}"
            try:
                self.add_message_bubble(fallback_text, is_user=False)
            except Exception:
                pass

    def debug_text_widget_scroll(self, text_widget, widget_name="Widget"):
        """Debug pour vérifier l'état du scroll d'un widget Text"""
        try:
            text_widget.update_idletasks()

            # Obtenir les informations de scroll
            yview = text_widget.yview()
            height = text_widget.cget("height")

            # Compter les lignes réelles
            line_count = int(text_widget.index("end-1c").split(".")[0])

            print(f"🔍 DEBUG {widget_name}:")
            print(f"   Hauteur configurée: {height} lignes")
            print(f"   Lignes réelles: {line_count}")
            print(f"   YView (scroll): {yview}")
            print(
                f"   Scroll nécessaire: {'OUI' if yview and yview[1] < 1.0 else 'NON'}"
            )
            print(
                f"   État: {'✅ OK' if not yview or yview[1] >= 1.0 else '❌ SCROLL INTERNE'}"
            )
            print()

        except Exception as e:
            print(f"❌ Erreur debug {widget_name}: {e}")

    def _calculate_text_height_for_widget(self, text):
        """Calcule la hauteur optimale pour un texte donné"""
        if not text:
            return 5

        # Compter les lignes de base
        lines = text.split("\n")
        base_lines = len(lines)

        # Estimer les lignes wrappées
        estimated_width_chars = 100  # Estimation conservative
        wrapped_lines = 0

        for line in lines:
            if len(line) > estimated_width_chars:
                # Cette ligne va être wrappée
                additional_lines = (len(line) - 1) // estimated_width_chars
                wrapped_lines += additional_lines

        # Calcul final avec marge de sécurité
        total_estimated_lines = base_lines + wrapped_lines

        # Ajouter une marge généreuse pour éviter tout scroll
        margin = max(
            3, int(total_estimated_lines * 0.2)
        )  # 20% de marge minimum 3 lignes
        final_height = total_estimated_lines + margin

        # ⚡ CORRECTION: Pas de limite maximale pour afficher tout le contenu
        # La hauteur s'adapte automatiquement au contenu, même pour des messages très longs
        final_height = max(5, final_height)  # Minimum 5 lignes, pas de maximum

        return final_height

    def setup_text_copy_functionality(self, text_widget, original_text):
        """Configure la fonctionnalité de copie pour un widget Text"""

        def copy_selected_text():
            """Copie le texte sélectionné ou tout le texte si rien n'est sélectionné"""
            try:
                # Essayer de récupérer la sélection
                selected_text = text_widget.selection_get()
                if selected_text:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(selected_text)
                    self.show_copy_notification("📋 Sélection copiée !")
                else:
                    # Si rien n'est sélectionné, copier tout le texte
                    self.root.clipboard_clear()
                    self.root.clipboard_append(original_text)
                    self.show_copy_notification("📋 Message entier copié !")
            except tk.TclError:
                # Aucune sélection, copier tout le texte
                self.root.clipboard_clear()
                self.root.clipboard_append(original_text)
                self.show_copy_notification("📋 Message copié !")
            except Exception:
                self.show_copy_notification("❌ Erreur de copie")

        # Menu contextuel amélioré
        def show_context_menu(event):
            context_menu = tk.Menu(self.root, tearoff=0)

            # Vérifier s'il y a une sélection
            try:
                selected = text_widget.selection_get()
                if selected:
                    context_menu.add_command(
                        label="📋 Copier la sélection", command=copy_selected_text
                    )
                    context_menu.add_separator()
            except Exception:
                pass

            context_menu.add_command(
                label="📄 Copier tout le message", command=copy_selected_text
            )
            context_menu.add_command(
                label="🔍 Tout sélectionner",
                command=lambda: text_widget.tag_add("sel", "1.0", "end"),
            )

            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            except Exception:
                pass
            finally:
                context_menu.grab_release()

        # Binds pour la copie
        text_widget.bind("<Button-3>", show_context_menu)  # Clic droit
        text_widget.bind("<Control-c>", lambda e: copy_selected_text())  # Ctrl+C
        text_widget.bind(
            "<Control-a>", lambda e: text_widget.tag_add("sel", "1.0", "end")
        )  # Ctrl+A

    def show_copy_notification(self, message):
        """Affiche une notification GUI élégante pour la copie"""
        try:
            # Créer une notification temporaire
            if self.use_ctk:
                notification = ctk.CTkFrame(
                    self.main_container,
                    fg_color="#10b981",  # Vert succès
                    corner_radius=8,
                    border_width=0,
                )

                notif_label = ctk.CTkLabel(
                    notification,
                    text=message,
                    text_color="#ffffff",
                    font=("Segoe UI", 12, "bold"),
                )
            else:
                notification = tk.Frame(
                    self.main_container, bg="#10b981", relief="flat"
                )

                notif_label = tk.Label(
                    notification,
                    text=message,
                    fg="#ffffff",
                    bg="#10b981",
                    font=("Segoe UI", 12, "bold"),
                )

            notif_label.pack(padx=15, pady=8)

            # Positionner en haut à droite
            notification.place(relx=0.95, rely=0.1, anchor="ne")

            # Supprimer automatiquement après 4 secondes
            self.root.after(4000, notification.destroy)

        except Exception:
            pass

    def create_copy_menu_with_notification(self, widget, original_text):
        """Menu contextuel avec notification GUI"""

        def copy_text():
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(original_text)
                self.show_copy_notification("Texte copié !")
            except Exception:
                self.show_copy_notification("❌ Erreur de copie")

        def select_all_and_copy():
            """Sélectionne tout le texte et le copie"""
            copy_text()  # Pour l'instant, même action

        # Créer le menu contextuel
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="📋 Copier le texte", command=copy_text)
        context_menu.add_separator()
        context_menu.add_command(
            label="🔍 Tout sélectionner et copier", command=select_all_and_copy
        )

        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            except Exception:
                pass
            finally:
                context_menu.grab_release()

        # Bind du clic droit
        widget.bind("<Button-3>", show_context_menu)  # Windows/Linux
        widget.bind("<Button-2>", show_context_menu)  # macOS (parfois)
        widget.bind("<Control-Button-1>", show_context_menu)  # Ctrl+clic

        return context_menu
