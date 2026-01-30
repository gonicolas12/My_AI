"""Animations mixin for ModernAIGUI."""

import random
import re
import tkinter as tk


class AnimationsMixin:
    """Typing, thinking, and search animations."""

    def adjust_text_widget_height(self, text_widget):
        """⚡ OPTIMISÉ : Hauteur illimitée avec moins d'update_idletasks"""
        try:
            # ⚡ OPTIMISATION: Un seul update_idletasks au lieu de 2
            current_state = text_widget.cget("state")
            text_widget.configure(state="normal")

            # ⚡ CORRECTION MAJEURE : Compter les lignes VISUELLES (avec wrapping), pas juste les \n
            display_lines = text_widget.count("1.0", "end", "displaylines")

            if display_lines and len(display_lines) > 0:
                line_count = display_lines[0]  # count() retourne un tuple
            else:
                # Fallback si displaylines échoue
                line_count = int(text_widget.index("end-1c").split(".")[0])

            # ⚡ HAUTEUR GÉNÉREUSE : Toujours assez pour tout afficher
            generous_height = max(line_count + 3, 10)  # Au moins 10 lignes, +3 de marge

            text_widget.configure(height=generous_height, state=current_state)
            # ⚡ OPTIMISATION: update_idletasks() uniquement tous les 5 ajustements
            self._height_adjust_counter += 1
            if self._height_adjust_counter % 5 == 0:
                text_widget.update_idletasks()

        except Exception:
            # Fallback sécurisé : laisser la hauteur par défaut
            try:
                self._disable_text_scroll(text_widget)
            except Exception:
                pass

    def start_typing_animation_dynamic(self, text_widget, full_text):
        """Animation caractère par caractère avec formatage progressif intelligent"""
        # DÉSACTIVER la saisie pendant l'animation
        self.set_input_state(False)

        # Réinitialiser le widget
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")

        # DÉSACTIVER le scroll pendant l'animation pour éviter les saccades
        self._disable_text_scroll(text_widget)

        # Pré-traiter le texte pour remplacer les liens par leurs titres
        processed_text, link_mapping = self._preprocess_links_for_animation(full_text)

        # Pré-analyser les blocs de code pour la coloration en temps réel
        self._code_blocks_map = self._preanalyze_code_blocks(processed_text)

        # Debug: afficher quelques positions du map
        if self._code_blocks_map:
            sample_keys = list(self._code_blocks_map.keys())[:10]
            print(
                f"[DEBUG] start_typing: _code_blocks_map contient {len(self._code_blocks_map)} entrées"
            )
            print(
                f"[DEBUG] Exemples: {[(k, self._code_blocks_map[k]) for k in sample_keys]}"
            )
        else:
            print(
                "[DEBUG] start_typing: _code_blocks_map est VIDE - pas de blocs de code détectés"
            )
            print(f"[DEBUG] Texte reçu (premiers 500 chars): {processed_text[:500]}")

        # Variables pour l'animation CARACTÈRE PAR CARACTÈRE
        self.typing_index = 0
        self.typing_text = processed_text  # Utiliser le texte pré-traité
        self.typing_widget = text_widget
        self.typing_speed = 1

        # Stocker le mapping des liens pour plus tard
        if link_mapping:
            self._pending_links = link_mapping

        # Réinitialiser les positions formatées et le tracking du bold
        self._formatted_positions = set()
        self._formatted_bold_contents = (
            set()
        )  # NOUVEAU: tracking par contenu pour le bold

        # Pré-analyser les tableaux Markdown pour l'animation progressive
        self._table_blocks = self._preanalyze_markdown_tables(processed_text)
        self._formatted_tables = set()  # Tableaux déjà formatés (par index)

        # Configurer tous les tags de formatage
        self._configure_all_formatting_tags(text_widget)

        # Configuration spéciale du tag 'normal' pour l'animation SANS formatage
        text_widget.tag_configure(
            "normal", font=("Segoe UI", 12), foreground=self.colors["text_primary"]
        )

        # Flag d'interruption
        self._typing_interrupted = False

        # Démarrer l'animation caractère par caractère
        self.continue_typing_animation_dynamic()

    def _preprocess_links_for_animation(self, text):
        """Pré-traite le texte pour remplacer les liens [titre](url) par juste le titre pendant l'animation"""
        # Pattern pour détecter [titre](url)
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"

        # Initialiser la liste des liens pour la conversion finale
        if not hasattr(self, "_pending_links"):
            self._pending_links = []

        def replace_link(match):
            title = match.group(1)
            url = match.group(2)

            # Stocker dans _pending_links comme liste
            self._pending_links.append(
                {
                    "title": title,
                    "url": url,
                }
            )

            # Retourner juste le titre (sans marqueur)
            return title

        # Remplacer tous les liens par leurs titres
        processed_text = re.sub(link_pattern, replace_link, text)

        print(f"[DEBUG] Liens prétraités: {len(self._pending_links)} liens trouvés")
        for link_data in self._pending_links:
            print(f"  '{link_data['title']}' -> {link_data['url']}")

        return processed_text, self._pending_links

    def _split_text_for_progressive_formatting(self, text):
        """Divise le texte en segments plus larges pour une animation fluide"""
        segments = []

        # Diviser par phrases ou groupes de mots (5-10 caractères par segment)
        words = re.findall(r"\S+\s*", text)

        current_segment = ""
        target_length = 8  # Caractères par segment pour une animation fluide

        for word in words:
            # Si ajouter ce mot dépasse la longueur cible, finir le segment actuel
            if len(current_segment) + len(word) > target_length and current_segment:
                segments.append(current_segment)
                current_segment = word
            else:
                current_segment += word

        # Ajouter le dernier segment s'il existe
        if current_segment:
            segments.append(current_segment)

        # Nettoyer les segments vides
        segments = [s for s in segments if s.strip()]

        return segments

    def continue_typing_animation_dynamic(self):
        """Animation caractère par caractère avec formatage progressif UNIFIÉ"""
        if not hasattr(self, "typing_widget") or not hasattr(self, "typing_text"):
            return

        if getattr(self, "_typing_interrupted", False):
            self.finish_typing_animation_dynamic(interrupted=True)
            return

        # Vérifier si on a terminé
        if self.typing_index >= len(self.typing_text):
            self.finish_typing_animation_dynamic()
            return

        try:
            # Ajouter le caractère suivant
            char = self.typing_text[self.typing_index]

            self.typing_widget.configure(state="normal")

            # NOUVEAU : Déterminer le tag à utiliser selon la position
            tag_to_use = "normal"  # Tag par défaut

            # Vérifier si ce caractère est dans un bloc de code
            if (
                hasattr(self, "_code_blocks_map")
                and self.typing_index in self._code_blocks_map
            ):
                _language, token_type = self._code_blocks_map[self.typing_index]

                # Masquer les marqueurs de blocs de code (```)
                if token_type == "code_block_marker":
                    tag_to_use = "hidden"  # Les ``` seront cachés
                else:
                    tag_to_use = token_type  # Utiliser le tag de coloration syntaxique

            # Insérer le caractère avec le bon tag
            self.typing_widget.insert("end", char, tag_to_use)

            # La coloration est déjà appliquée via _code_blocks_map, pas besoin de _apply_realtime_syntax_coloring

            # Incrémenter l'index
            self.typing_index += 1

            # FORMATAGE PROGRESSIF INTELLIGENT
            should_format = False

            # Détecter completion d'éléments markdown UNIQUEMENT pour les vrais patterns
            if char == "*":
                current_content = self.typing_widget.get("1.0", "end-1c")
                # Ne formater QUE si on a un vrai pattern **texte**
                if current_content.endswith("**") and len(current_content) >= 4:
                    # Vérifier qu'il y a vraiment un pattern **texte** complet
                    # Chercher le dernier pattern **texte** complet dans le contenu
                    bold_pattern = r"\*\*([^*\n]{1,200}?)\*\*$"
                    if re.search(bold_pattern, current_content):
                        should_format = True
                    else:
                        pass
            elif char == "`":
                # Fin possible de `code` - vérifier que c'est un vrai pattern
                current_content = self.typing_widget.get("1.0", "end-1c")
                code_pattern = r"`([^`\n]+)`$"
                if re.search(code_pattern, current_content):
                    should_format = True
                else:
                    pass
            elif char == "'":
                # Fin possible de '''docstring''' - vérifier qu'on a 3 quotes
                current_content = self.typing_widget.get("1.0", "end-1c")
                if current_content.endswith("'''"):
                    docstring_pattern = r"'''([^']*?)'''$"
                    if re.search(docstring_pattern, current_content, re.DOTALL):
                        should_format = True
                    else:
                        pass
            elif char == " ":
                # NE PAS formater pendant l'écriture d'un titre - attendre la fin de ligne
                # Ancien code qui causait le formatage partiel des titres
                pass  # On attend le \n pour formater les titres complets
            elif char == "\n":
                # Nouvelle ligne - MAINTENANT on peut formater les titres complets
                should_format = True

                # Vérifier si on vient de terminer une ligne de tableau
                self._check_and_format_table_line(self.typing_widget, self.typing_index)

            elif self.typing_index % 100 == 0:  # ⚡ OPTIMISÉ: Formatage tous les 100 caractères (au lieu de 50)
                should_format = True

            # Appliquer le formatage unifié si nécessaire
            if should_format:
                self._apply_unified_progressive_formatting(self.typing_widget)

            # Ajuster la hauteur aux retours à la ligne
            if char == "\n":
                self.adjust_text_widget_height(self.typing_widget)
                self.root.after(5, self._smart_scroll_follow_animation)

            self.typing_widget.configure(state="disabled")

            # Planifier le prochain caractère (animation fluide)
            delay = 10
            self.root.after(delay, self.continue_typing_animation_dynamic)

        except tk.TclError:
            self.finish_typing_animation_dynamic(interrupted=True)

    def finish_typing_animation_dynamic(self, interrupted=False):
        """Version CORRIGÉE - Ne réapplique PAS la coloration syntaxique à la fin"""
        if hasattr(self, "typing_widget") and hasattr(self, "typing_text"):

            # Sauvegarder le texte original avant tout traitement
            original_text = self.typing_text if hasattr(self, "typing_text") else ""

            if interrupted:
                # Réinitialiser les positions pour forcer un formatage complet
                if hasattr(self, "_formatted_positions"):
                    self._formatted_positions.clear()

                # Formatage final même en cas d'interruption
                self.typing_widget.configure(state="normal")

                # Formater les tableaux Markdown EN PREMIER (reconstruit le widget)
                self._format_markdown_tables_in_widget(
                    self.typing_widget, original_text
                )

                self._apply_unified_progressive_formatting(self.typing_widget)

                # Convertir les liens temporaires en liens clickables
                self._convert_temp_links_to_clickable(self.typing_widget)

                # Appliquer un nettoyage final pour les formatages manqués
                self.typing_widget.configure(state="disabled")
            else:
                # Animation complète : formatage FINAL COMPLET

                # NOUVEAU : Réinitialiser les positions pour forcer un formatage complet
                if hasattr(self, "_formatted_positions"):
                    self._formatted_positions.clear()

                # Formatage final unifié
                self.typing_widget.configure(state="normal")

                # NOUVEAU : Formater les tableaux Markdown EN PREMIER (reconstruit le widget)
                self._format_markdown_tables_in_widget(
                    self.typing_widget, original_text
                )

                self._apply_unified_progressive_formatting(self.typing_widget)

                # Convertir les liens temporaires en liens clickables
                self._convert_temp_links_to_clickable(self.typing_widget)

                # Appliquer un nettoyage final pour les formatages manqués
                self.typing_widget.configure(state="disabled")

            # Ajustement final de la hauteur
            self._adjust_height_final_no_scroll(self.typing_widget)

            # RÉACTIVER le scroll maintenant que l'animation est finie
            self._reactivate_text_scroll(self.typing_widget)

            self.typing_widget.configure(state="disabled")

            # Afficher le timestamp sous le message IA
            self._show_timestamp_for_current_message()

            # Réactiver la saisie utilisateur
            self.set_input_state(True)

            # Scroll final contrôlé
            self.root.after(200, self._final_smooth_scroll_to_bottom)

            # Nettoyage des variables d'animation
            if hasattr(self, "_typing_animation_after_id"):
                try:
                    self.root.after_cancel(self._typing_animation_after_id)
                except Exception:
                    pass
                del self._typing_animation_after_id

            delattr(self, "typing_widget")
            delattr(self, "typing_text")
            delattr(self, "typing_index")
            self._typing_interrupted = False

            # Nettoyer le cache de formatage
            if hasattr(self, "_formatted_positions"):
                delattr(self, "_formatted_positions")

    def stop_typing_animation(self):
        """Stoppe proprement l'animation de frappe IA (interruption utilisateur)"""
        self._typing_interrupted = True
        if hasattr(self, "_typing_animation_after_id"):
            try:
                self.root.after_cancel(self._typing_animation_after_id)
            except Exception:
                pass
            del self._typing_animation_after_id

    def is_animation_running(self):
        """Vérifie si une animation d'écriture est en cours"""
        return (
            hasattr(self, "typing_widget")
            and hasattr(self, "typing_text")
            and hasattr(self, "typing_index")
        )

    def _adjust_height_final_no_scroll(self, text_widget):
        """Ajuste la hauteur du widget Text pour qu'il n'y ait aucun scroll interne ni espace vide, basé sur le nombre de lignes réelles tkinter. Désactive aussi le scroll interne."""
        try:
            text_widget.update_idletasks()
            current_state = text_widget.cget("state")
            text_widget.configure(state="normal")

            # ⚡ CORRECTION : Compter les lignes VISUELLES (avec wrapping)
            display_lines = text_widget.count("1.0", "end", "displaylines")
            if display_lines and len(display_lines) > 0:
                line_count = display_lines[0]
            else:
                line_count = int(text_widget.index("end-1c").split(".")[0])

            text_widget.configure(height=max(2, line_count))
            text_widget.update_idletasks()
            text_widget.configure(state=current_state)
            self._disable_text_scroll(text_widget)
        except Exception:
            text_widget.configure(height=10)
            self._disable_text_scroll(text_widget)

    def _adjust_height_smoothly_during_animation(self, text_widget, current_text):
        """Ajustement de hauteur SMOOTH pendant l'animation pour éviter le scroll dans la bulle"""
        try:
            # Calculer le nombre de lignes nécessaires
            lines_needed = current_text.count("\n") + 1

            # ⚡ CORRECTION: Pas de limite maximale pour l'animation
            min_height = 2

            # Calculer la hauteur idéale
            ideal_height = max(min_height, lines_needed)
            current_height = int(text_widget.cget("height"))

            # Ajuster SEULEMENT si nécessaire (éviter les changements constants)
            if abs(ideal_height - current_height) > 1:
                text_widget.configure(height=ideal_height)

                # IMPORTANT: Réinitialiser la vue SANS scroll
                text_widget.yview_moveto(0.0)  # Toujours commencer du haut

        except Exception as e:
            print(f"[DEBUG] Erreur ajustement hauteur smooth: {e}")

    def _adjust_height_during_animation(self, text_widget):
        """Ajuste la hauteur du widget Text pendant l'animation pour qu'il n'y ait aucun scroll interne, basé sur le nombre de lignes réelles tkinter."""
        try:
            text_widget.update_idletasks()

            # ⚡ CORRECTION: Compter les lignes VISUELLES (avec wrapping)
            display_lines = text_widget.count("1.0", "end", "displaylines")
            if display_lines and len(display_lines) > 0:
                line_count = display_lines[0]
            else:
                line_count = int(text_widget.index("end-1c").split(".")[0])

            text_widget.configure(height=max(2, line_count))
            text_widget.update_idletasks()
            self._disable_text_scroll(text_widget)
        except Exception:
            text_widget.configure(height=10)
            self._disable_text_scroll(text_widget)

    def _adjust_text_height_exact(self, text_widget):
        """Ajuste la hauteur du widget Text pour qu'il n'y ait aucun scroll interne ni espace vide, basé sur le nombre de lignes réelles tkinter. Désactive aussi le scroll interne."""
        try:
            text_widget.update_idletasks()
            current_state = text_widget.cget("state")
            text_widget.configure(state="normal")
            # ⚡ CORRECTION: Compter les lignes VISUELLES (avec wrapping)
            display_lines = text_widget.count("1.0", "end", "displaylines")
            if display_lines and len(display_lines) > 0:
                line_count = display_lines[0]
            else:
                line_count = int(text_widget.index("end-1c").split(".")[0])

            # Pas de limite maximale, juste un minimum de 2 lignes
            height = max(2, line_count)
            text_widget.configure(height=height)
            text_widget.configure(state=current_state)
            self._disable_text_scroll(text_widget)
        except Exception:
            try:
                text_widget.configure(height=7)
            except Exception:
                pass

    def adjust_text_height_no_scroll(self, text_widget, text):
        """Ajuste la hauteur EXACTE pour afficher tout le contenu sans scroll"""
        try:
            # Attendre que le widget soit rendu
            text_widget.update_idletasks()

            if self.use_ctk:
                # Pour CustomTkinter CTkTextbox - CALCUL TRÈS PRÉCIS
                lines = text.split("\n")
                total_lines = 0

                # Obtenir la largeur réelle du widget
                try:
                    widget_width = text_widget.winfo_width()
                    if widget_width <= 50:
                        widget_width = 400  # Largeur par défaut

                    # Estimation caractères par ligne TRÈS précise
                    font_size = self.get_current_font_size("message")
                    char_width = font_size * 0.6  # Approximation largeur caractère
                    chars_per_line = max(30, int((widget_width - 30) / char_width))

                    for line in lines:
                        if len(line) == 0:
                            total_lines += 1
                        else:
                            # Calculer lignes wrapped précisément
                            line_wrapped = max(
                                1, (len(line) + chars_per_line - 1) // chars_per_line
                            )
                            total_lines += line_wrapped

                except Exception:
                    # Fallback conservateur
                    total_lines = len(lines) + 3  # Plus conservateur

                # Calculer hauteur COMPACTE en pixels
                line_height = 18  # Hauteur d'une ligne (plus compact)
                padding = 8  # Padding minimal (plus compact)
                min_height = 30  # Minimum absolu (plus compact)
                max_height = 600  # Maximum raisonnable (plus grand)

                exact_height = max(
                    min_height, min(total_lines * line_height + padding, max_height)
                )

                # MARGE DE SÉCURITÉ pour éviter tout scroll
                exact_height = int(exact_height * 1.1)  # 10% de marge (réduit)
                text_widget.configure(height=exact_height)

            else:
                # Pour tkinter standard Text - CALCUL EN LIGNES
                current_state = text_widget.cget("state")
                text_widget.configure(state="normal")

                # Forcer le rendu puis mesurer SANS déplacer la vue
                text_widget.update_idletasks()

                # Compter lignes réelles affichées
                line_count = int(text_widget.index("end-1c").split(".")[0])

                # Restaurer l'état
                text_widget.configure(state=current_state)

                # Hauteur GÉNÉREUSE - plus de marge pour éviter scroll
                exact_height = max(
                    2, min(line_count + 3, 30)
                )  # +3 de marge au lieu de 0
                text_widget.configure(height=exact_height)

            # Forcer la mise à jour
            text_widget.update_idletasks()

        except Exception as e:
            self.logger.error("Erreur ajustement hauteur: %s", e)
            # Hauteur par défaut GÉNÉREUSE si erreur
            if self.use_ctk:
                text_widget.configure(height=80)  # Plus généreux
            else:
                text_widget.configure(height=5)  # Plus généreux

    def adjust_text_height(self, text_widget, text):
        """Ajuste la hauteur du widget de texte selon le contenu"""
        try:
            if self.use_ctk:
                # Pour CustomTkinter CTkTextbox, mesure plus précise
                text_widget.update_idletasks()  # Forcer la mise à jour

                # Pour CustomTkinter, on ne peut pas changer l'état facilement
                # On va calculer la hauteur autrement
                lines = text.split("\n")
                total_lines = len(lines)

                # Estimer les lignes avec retour automatique
                widget_width = 600  # Largeur approximative
                chars_per_line = widget_width // 8  # Approximation

                for line in lines:
                    if len(line) > chars_per_line:
                        additional_lines = (len(line) - 1) // chars_per_line
                        total_lines += additional_lines

                # Calculer la hauteur nécessaire (ligne_height * nb_lignes + padding)
                line_height = 18  # Hauteur d'une ligne en pixels
                padding = 15  # Padding total
                min_height = 40  # Hauteur minimale
                # ⚡ CORRECTION: Pas de limite maximale pour afficher tout le contenu

                calculated_height = max(min_height, total_lines * line_height + padding)
                text_widget.configure(height=calculated_height)

            else:
                # Pour tkinter standard Text
                text_widget.update_idletasks()

                # Mesurer le contenu réel
                current_state = text_widget.cget("state")
                text_widget.configure(state="normal")
                text_widget.delete("1.0", "end")
                text_widget.insert("1.0", text)
                text_widget.update_idletasks()

                # Obtenir le nombre de lignes
                line_count = int(text_widget.index("end-1c").split(".")[0])

                # Restaurer l'état
                text_widget.configure(state=current_state)

                # Ajuster en nombre de lignes (plus précis pour tkinter)
                height = max(
                    2, min(line_count + 1, 25)
                )  # +1 pour la marge, max 25 lignes
                text_widget.configure(height=height)

        except Exception as e:
            self.logger.error("Erreur lors de l'ajustement de la hauteur: %s", e)
            # Hauteur par défaut en cas d'erreur
            if self.use_ctk:
                text_widget.configure(height=100)
            else:
                text_widget.configure(height=5)

    def start_animations(self):
        """Démarre les animations de l'interface"""
        self.animate_thinking()
        self.animate_search()

    def animate_thinking(self):
        """Animation de réflexion de l'IA"""
        if hasattr(self, "thinking_label") and self.is_thinking:
            # Animations avancées qui montrent l'intelligence de l'IA
            advanced_animations = [
                "⚡ Traitement neural en cours.",
                "💡 Génération de réponse intelligente.",
                "🎯 Optimisation de la réponse.",
                "⚙️ Moteur de raisonnement actif.",
                "📊 Analyse des patterns.",
                "💻 Processing linguistique avancé.",
                "🎪 Préparation d'une réponse.",
            ]

            # Choisir une animation aléatoire pour plus de variété
            if (
                not hasattr(self, "current_thinking_text")
                or self.thinking_dots % 4 == 0
            ):
                self.current_thinking_text = random.choice(advanced_animations)

            # Animation de points progressifs
            dots = ["", ".", "..", "..."][self.thinking_dots % 4]
            display_text = self.current_thinking_text + dots

            self.thinking_dots = (self.thinking_dots + 1) % 4
            self.thinking_label.configure(text=display_text)

            # Animation plus rapide pour donner l'impression de vitesse
            self.root.after(400, self.animate_thinking)
        elif hasattr(self, "thinking_label"):
            self.thinking_label.configure(text="")

    def animate_search(self):
        """Animation de recherche internet"""
        if hasattr(self, "thinking_label") and self.is_searching:
            # Animations de recherche variées
            animations = [
                "🔍 Recherche sur internet",
                "🌐 Recherche sur internet",
                "📡 Recherche sur internet",
                "🔎 Recherche sur internet",
                "💫 Recherche sur internet",
                "⚡ Recherche sur internet",
            ]

            self.search_frame = (self.search_frame + 1) % len(animations)
            self.thinking_label.configure(text=animations[self.search_frame])

            # Continuer l'animation toutes les 800ms
            self.root.after(800, self.animate_search)
        elif hasattr(self, "thinking_label"):
            self.thinking_label.configure(text="")

    def show_thinking_animation(self):
        """Affiche l'animation de réflexion et désactive la saisie"""
        self.is_thinking = True
        # NOUVEAU : Désactiver la zone de saisie
        self.set_input_state(False)

        if hasattr(self, "thinking_frame"):
            self.thinking_frame.grid(
                row=1, column=0, sticky="ew", padx=20, pady=(0, 10)
            )
            self.animate_thinking()

    def show_search_animation(self):
        """Affiche l'animation de recherche et désactive la saisie"""
        self.is_searching = True
        # NOUVEAU : Désactiver la zone de saisie
        self.set_input_state(False)

        if hasattr(self, "thinking_frame"):
            self.thinking_frame.grid(
                row=1, column=0, sticky="ew", padx=20, pady=(0, 10)
            )
            self.animate_search()
