"""Streaming mixin for ModernAIGUI."""

import re
import traceback
from datetime import datetime
import tkinter as tk

try:
    from pygments import lex
    from pygments.lexers.python import PythonLexer

    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False
    PythonLexer = None


class StreamingMixin:
    """Streaming response handling and animation."""

    def _create_streaming_bubble_with_animation(self):
        """
        Crée la bulle IA et démarre l'animation de frappe en mode streaming.
        L'animation lit depuis le buffer qui se remplit en temps réel.
        """
        try:
            # Finaliser le widget Raisonnement AVANT de créer la bulle.
            # Si le widget est vide (pas de thinking tokens reçus), il sera
            # masqué et _last_bubble_is_user restauré, ce qui permet d'afficher
            # correctement l'icône 🤖 sur cette bulle réponse.
            if hasattr(self, "_finalize_reasoning_widget"):
                self._finalize_reasoning_widget()

            # Effacer l'indicateur MCP inline s'il est toujours affiché
            if hasattr(self, "_hide_mcp_tool_indicator"):
                self._hide_mcp_tool_indicator()

            # Cacher l'animation de réflexion immédiatement
            self.is_thinking = False
            if hasattr(self, "thinking_frame"):
                self.thinking_frame.grid_remove()

            # Créer le container principal
            msg_container = self.create_frame(
                self.chat_frame, fg_color=self.colors["bg_chat"]
            )

            # Ajouter un placeholder dans l'historique
            self.conversation_history.append(
                {
                    "text": "",  # Sera mis à jour à la fin
                    "is_user": False,
                    "timestamp": datetime.now(),
                    "type": "streaming",
                }
            )

            _base_row = len(self.conversation_history) - 1
            # Plus besoin de _row_offset : le reasoning widget ajoute
            # désormais un placeholder dans conversation_history, donc les
            # rows sont déjà correctement comptées.
            msg_container.grid(
                row=_base_row,
                column=0,
                sticky="ew",
                pady=(0, 0),
            )
            self._reasoning_widget_row = None  # Reset après usage
            msg_container.grid_columnconfigure(0, weight=1)

            # Frame de centrage
            center_frame = self.create_frame(
                msg_container, fg_color=self.colors["bg_chat"]
            )
            center_frame.grid(
                row=0, column=0, padx=(250, 250), pady=(0, 0), sticky="ew"
            )
            center_frame.grid_columnconfigure(0, weight=0)
            center_frame.grid_columnconfigure(1, weight=1)

            # Icône IA — masquée (invisible) si un widget Raisonnement vient d'être affiché,
            # ou si le dernier élément affiché est un output IA (pour éviter les doublons)
            # mais toujours présente comme spacer pour que le texte reste aligné à column=1
            _show_icon = getattr(self, "_last_bubble_is_user", True)
            self._last_bubble_is_user = False  # Cette bulle réponse est un output IA
            self._thinking_mode_active = False  # Reset après usage
            icon_label = self.create_label(
                center_frame,
                text="🤖",
                font=("Segoe UI", 16),
                fg_color=self.colors["bg_chat"],
                # Visible si pas de Raisonnement, invisible sinon (même couleur que fond)
                text_color=self.colors["accent"] if _show_icon else self.colors["bg_chat"],
            )
            icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0))

            # Container pour le message — toujours à column=1 pour un alignement cohérent
            message_container = self.create_frame(
                center_frame, fg_color=self.colors["bg_chat"]
            )
            message_container.grid(row=0, column=1, sticky="ew", padx=0, pady=(2, 2))
            message_container.grid_columnconfigure(0, weight=1)

            self._streaming_container = message_container
            self.current_message_container = message_container

            # Widget texte pour le streaming
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
                insertwidth=0,
                yscrollcommand=None,
                xscrollcommand=None,
            )
            text_widget.grid(row=0, column=0, sticky="ew")

            self._streaming_widget = text_widget

            # Configurer le scroll forwarding
            self.setup_improved_scroll_forwarding(text_widget)

            # Démarrer l'animation de frappe en mode streaming
            self._start_streaming_typing_animation(text_widget)

            # Scroll vers le bas
            self.scroll_to_bottom()

        except Exception as e:
            print(f"❌ [STREAM] Erreur création bulle: {e}")
            traceback.print_exc()

    def _start_streaming_typing_animation(self, text_widget):
        """
        Démarre l'animation de frappe en MODE STREAMING.
        Similaire à start_typing_animation_dynamic mais lit depuis le buffer en temps réel.
        """
        # DÉSACTIVER la saisie pendant l'animation
        self.set_input_state(False)

        # Réinitialiser le widget
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")

        # DÉSACTIVER le scroll pendant l'animation
        self._disable_text_scroll(text_widget)

        # Variables pour l'animation streaming
        self.typing_index = 0
        self.typing_widget = text_widget
        self.typing_speed = 1
        self._typing_interrupted = False

        # IMPORTANT: typing_text est utilisé par _apply_unified_progressive_formatting
        # On le synchronise avec le buffer de streaming
        self.typing_text = self._streaming_buffer

        # Initialiser le code_blocks_map vide (sera mis à jour périodiquement)
        self._code_blocks_map = {}

        # Tracker pour éviter de recoloriser le même bloc plusieurs fois
        self._last_colored_block_end = -1

        # Réinitialiser les positions formatées
        self._formatted_positions = set()
        self._formatted_bold_contents = set()
        self._formatted_tables = set()
        self._pending_links = []
        self._table_blocks = []

        # 🔗 Tracker pour les liens Markdown en cours d'écriture
        self._link_skip_positions = {}  # {start_pos: (title, url, end_pos)}
        self._current_link_info = None  # Info du lien en cours d'affichage
        # pylint: disable=attribute-defined-outside-init
        self._table_blocks_history = (
            {}
        )  # Pour tracker l'évolution des tableaux (attribut temporaire de streaming)

        # 🎨 Progressive code block tracking
        self._streaming_in_code_block = False
        self._streaming_code_language = ""
        self._streaming_code_widget_start = None
        self._streaming_code_content = ""
        self._streaming_code_rehighlight_counter = 0

        # Configurer tous les tags de formatage
        self._configure_all_formatting_tags(text_widget)

        # Configuration du tag 'normal'
        text_widget.tag_configure(
            "normal", font=("Segoe UI", 12), foreground=self.colors["text_primary"]
        )

        # Démarrer l'animation en mode streaming
        self._continue_streaming_typing_animation()

    def _detect_and_process_markdown_link(self):
        """
        Détecte si on est au début d'un lien Markdown [titre](url) et prépare son traitement.
        Retourne 'start' si un lien commence, 'wait' si incomplet, False sinon.
        """
        buffer_length = len(self._streaming_buffer)

        # Vérifier si on est sur un '[' qui pourrait être un lien
        if (
            self.typing_index >= buffer_length
            or self._streaming_buffer[self.typing_index] != "["
        ):
            return False

        # Chercher le pattern complet [titre](url) à partir de la position actuelle
        remaining_text = self._streaming_buffer[self.typing_index :]
        link_pattern = r"^\[([^\]]+)\]\(([^)]+)\)"
        match = re.match(link_pattern, remaining_text)

        if match:
            # Lien détecté avec pattern complet !
            title = match.group(1)
            url = match.group(2)
            full_link_text = match.group(0)

            # Vérifier qu'on a bien tout le lien dans le buffer
            link_end_pos = self.typing_index + len(full_link_text)
            if link_end_pos > buffer_length:
                # Le lien n'est pas encore complet dans le buffer, attendre
                return "wait"

            # 🔗 Marquer le début du lien pour affichage progressif
            self._current_link_info = {
                "title": title,
                "url": url,
                "start_pos": self.typing_index + 1,  # +1 pour sauter le [
                "title_end_pos": self.typing_index + 1 + len(title),  # Fin du titre
                "full_end_pos": link_end_pos,  # Fin du pattern complet
            }

            # 🔗 Stocker le lien pour le rendre cliquable plus tard
            if not hasattr(self, "_pending_links"):
                self._pending_links = []

            self._pending_links.append({"title": title, "url": url})

            print(
                f"[DEBUG LINK] Lien détecté pendant streaming: '{title}' -> {url[:50]}..."
            )

            # Sauter le caractère '[' et commencer à afficher le titre
            self.typing_index += 1

            return "start"

        # Vérifier si on a un début de lien potentiel (pattern incomplet)
        partial_pattern = r"^\[([^\]]*)\]?(\([^)]*)?$"
        partial_match = re.match(partial_pattern, remaining_text)

        if partial_match and not self._streaming_complete:
            # On a peut-être un lien en cours de construction, attendre plus de données
            return "wait"

        # Pas un lien valide, continuer normalement
        return False

    def _continue_streaming_typing_animation(self):
        """
        Continue l'animation de frappe en mode streaming.
        Attend si l'animation rattrape le buffer, continue quand de nouveaux tokens arrivent.
        AMÉLIORATION: Détecte la fermeture des blocs de code et applique la coloration immédiatement.
        MODE RATTRAPAGE: Quand le streaming est terminé et qu'il reste beaucoup de
        contenu non affiché, accélère en insérant plusieurs caractères par frame
        ou finalise d'un bloc pour éviter 30-60s d'animation inutile.
        """
        if not hasattr(self, "typing_widget") or self.typing_widget is None:
            return

        if getattr(self, "_typing_interrupted", False):
            self._finish_streaming_animation(_interrupted=True)
            return

        try:
            buffer_length = len(self._streaming_buffer)

            # IMPORTANT: Synchroniser typing_text avec le buffer pour le formatage
            self.typing_text = self._streaming_buffer

            # ── MODE RATTRAPAGE / AFFICHAGE RAPIDE ───────────────────────
            # S'active dès que le buffer est en avance sur l'affichage,
            # pendant ET après le streaming, pour ne pas brider le modèle :
            #  • > 800 chars ET streaming terminé → finalisation immédiate
            #  • > 50 chars (en cours OU terminé) → batch 25 chars / 5ms
            #  • sinon → mode typewriter 1 char / 10ms (effet saisie lente)
            remaining = buffer_length - self.typing_index
            # Pas de dump immédiat si on est dans un bloc de code progressif :
            # _handle_progressive_code_block le gérera en batch (200 chars/5ms).
            if remaining > 800 and self._streaming_complete and not getattr(self, '_streaming_in_code_block', False):
                # Trop de retard après la fin du streaming → finaliser d'un bloc
                print(
                    f"⚡ [STREAM] Rattrapage immédiat : {remaining} chars restants"
                )
                self._finish_streaming_animation()
                return
            elif remaining > 50 and not getattr(self, '_streaming_in_code_block', False):
                # Affichage rapide — batch jusqu'au prochain caractère spécial.
                # Les backticks (blocs/inline code) et crochets (liens) sont
                # traités un par un pour préserver toute la logique progressive.
                batch_size = min(25, remaining)
                for _bi in range(batch_size):
                    if self._streaming_buffer[self.typing_index + _bi] in ('`', '['):
                        batch_size = _bi
                        break

                if batch_size > 0:
                    # Insérer le segment sans caractères spéciaux
                    self.typing_widget.configure(state="normal")
                    chunk = self._streaming_buffer[self.typing_index:self.typing_index + batch_size]
                    self.typing_widget.insert("end", chunk)
                    self.typing_index += batch_size

                    # Déclencher le formatage sur les marqueurs Markdown courants
                    if any(c in chunk for c in ('\n', '*', '#')):
                        self._apply_unified_progressive_formatting(self.typing_widget)
                        self.adjust_text_widget_height(self.typing_widget)
                        self.root.after(2, self._smart_scroll_follow_animation)
                    elif self.typing_index % 60 == 0:
                        self.adjust_text_widget_height(self.typing_widget)
                        self.root.after(2, self._smart_scroll_follow_animation)

                    self.typing_widget.configure(state="disabled")
                    self.root.after(5, self._continue_streaming_typing_animation)
                    return
                # batch_size == 0 : prochain char est '`' ou '[' → laisser
                # le chemin caractère par caractère ci-dessous le traiter.

            # Vérifier si on a des caractères à afficher
            if self.typing_index < buffer_length:
                # 🔗 DÉTECTION ET TRAITEMENT DES LIENS MARKDOWN
                # Vérifier si on est au début d'un lien [titre](url)
                # (sauf si on est dans un bloc de code — les liens y sont du texte brut)
                link_detected = (
                    False if getattr(self, '_streaming_in_code_block', False)
                    else self._detect_and_process_markdown_link()
                )

                if link_detected == "start":
                    # Le lien commence, continuer l'animation pour afficher le titre
                    self.root.after(10, self._continue_streaming_typing_animation)
                    return
                elif link_detected == "wait":
                    # Lien incomplet, attendre plus de données
                    self.root.after(20, self._continue_streaming_typing_animation)
                    return

                # 🔗 GESTION D'UN LIEN EN COURS
                if self._current_link_info:
                    # On est dans un lien, vérifier où on en est
                    if self.typing_index < self._current_link_info["title_end_pos"]:
                        # On est dans le titre, afficher le caractère avec tag link_temp
                        char = self._streaming_buffer[self.typing_index]
                        self.typing_widget.configure(state="normal")
                        self.typing_widget.insert("end", char, "link_temp")
                        self.typing_index += 1
                        self.typing_widget.configure(state="disabled")

                        # Continuer rapidement
                        self.root.after(10, self._continue_streaming_typing_animation)
                        return
                    else:
                        # On a fini le titre, sauter le reste ](url)
                        self.typing_index = self._current_link_info["full_end_pos"]
                        self._current_link_info = None  # Fin du lien

                        # Continuer l'animation
                        self.root.after(10, self._continue_streaming_typing_animation)
                        return

                # 🎨 PROGRESSIVE CODE BLOCK HANDLING
                if self._handle_progressive_code_block():
                    return

                # Il y a du contenu à afficher (pas dans un lien)
                char = self._streaming_buffer[self.typing_index]

                self.typing_widget.configure(state="normal")

                # Déterminer le tag à utiliser (coloration syntaxique)
                tag_to_use = "normal"
                if (
                    hasattr(self, "_code_blocks_map")
                    and self.typing_index in self._code_blocks_map
                ):
                    _language, token_type = self._code_blocks_map[self.typing_index]
                    if token_type == "code_block_marker":
                        tag_to_use = "hidden"
                    else:
                        tag_to_use = token_type

                # Insérer le caractère
                self.typing_widget.insert("end", char, tag_to_use)
                self.typing_index += 1

                # ============================================================
                # 🎨 DÉTECTION FERMETURE BLOC DE CODE - Coloration immédiate
                # ============================================================
                # Détecter quand un bloc de code vient de se fermer (``` suivi de \n ou fin)
                code_block_just_closed = False
                if char == "`":
                    # Vérifier si on vient de fermer un bloc de code (les 3 derniers chars sont ```)
                    current_buffer = self._streaming_buffer[: self.typing_index]
                    if current_buffer.endswith("```"):
                        # Compter les occurrences de ``` pour voir si c'est une fermeture
                        triple_backticks = current_buffer.count("```")
                        if triple_backticks >= 2 and triple_backticks % 2 == 0:
                            # Vérifier qu'on n'a pas déjà traité ce bloc
                            last_block_end = getattr(
                                self, "_last_colored_block_end", -1
                            )
                            if self.typing_index > last_block_end:
                                code_block_just_closed = True
                                self._last_colored_block_end = self.typing_index
                                print(
                                    f"🎨 [STREAM] Bloc de code fermé détecté à position {self.typing_index}"
                                )

                # Si un bloc de code vient de se fermer, appliquer la coloration sur CE bloc uniquement
                if code_block_just_closed:
                    self._apply_streaming_syntax_coloring()

                # Formatage progressif (gras, italique, code inline)
                should_format = False
                if char == "*":
                    current_content = self.typing_widget.get("1.0", "end-1c")
                    if current_content.endswith("**") and len(current_content) >= 4:
                        bold_pattern = r"\*\*([^*\n]{1,200}?)\*\*$"
                        if re.search(bold_pattern, current_content):
                            should_format = True
                    # Détecter *texte* (italique) — un seul * non précédé de *
                    if not should_format and current_content.endswith("*") and not current_content.endswith("**"):
                        italic_pattern = r"(?<!\*)\*([^*\n]{1,200}?)\*$"
                        if re.search(italic_pattern, current_content):
                            should_format = True
                elif char == "`":
                    current_content = self.typing_widget.get("1.0", "end-1c")
                    code_pattern = r"`([^`\n]+)`$"
                    if re.search(code_pattern, current_content):
                        should_format = True
                elif char == "\n":
                    should_format = True
                    # Mettre à jour la pré-analyse des tableaux avec le contenu actuel
                    self._table_blocks = self._preanalyze_markdown_tables(
                        self._streaming_buffer[: self.typing_index]
                    )
                    self._check_and_format_table_line(
                        self.typing_widget, self.typing_index
                    )
                elif self.typing_index % 50 == 0:
                    should_format = True

                if should_format:
                    self._apply_unified_progressive_formatting(self.typing_widget)

                # Ajuster la hauteur aux retours à la ligne
                if char == "\n":
                    self.adjust_text_widget_height(self.typing_widget)
                    self.root.after(1, self._smart_scroll_follow_animation)
                elif self.typing_index % 25 == 0:
                    # Scroll périodique même sans \n pour suivre le word-wrap
                    self.adjust_text_widget_height(self.typing_widget)
                    self.root.after(1, self._smart_scroll_follow_animation)

                self.typing_widget.configure(state="disabled")

                # Continuer rapidement (10ms)
                self.root.after(10, self._continue_streaming_typing_animation)

            elif not self._streaming_complete:
                # Buffer rattrapé mais streaming pas terminé - attendre
                self.root.after(20, self._continue_streaming_typing_animation)

            else:
                # Streaming terminé et tout affiché
                self._finish_streaming_animation()

        except tk.TclError:
            self._finish_streaming_animation(_interrupted=True)
        except Exception as e:
            print(f"⚠️ [STREAM ANIM] Erreur: {e}")
            self._finish_streaming_animation(_interrupted=True)

    def _apply_streaming_syntax_coloring(self):
        """
        Applique la coloration syntaxique sur le PREMIER bloc de code non encore traité.
        MÉTHODE: Chercher directement dans le widget (pas dans le buffer).
        """
        try:
            self.typing_widget.configure(state="normal")
            widget_text = self.typing_widget.get("1.0", "end-1c")

            # Chercher le PREMIER bloc de code avec balises encore présentes dans le widget
            # Pattern: ```langage\n...code...```
            # CORRECTION: Capturer aussi les + pour c++, et # pour c#
            code_block_pattern = r"```([\w+#-]+)\n(.*?)```"
            widget_match = re.search(code_block_pattern, widget_text, re.DOTALL)

            if not widget_match:
                self.typing_widget.configure(state="disabled")
                return

            # Extraire les informations du bloc
            language = widget_match.group(1).lower()
            code_content = widget_match.group(2)
            w_block_start = widget_match.start()
            w_block_end = widget_match.end()

            print(
                f"🎨 [STREAM] Coloration bloc '{language}' positions {w_block_start}-{w_block_end}"
            )

            # Calculer les positions des balises
            opening_marker = "```" + language + "\n"
            opening_len = len(opening_marker)

            # Analyser le code pour obtenir les tokens
            code_tokens = self._get_code_tokens(language, code_content)

            # ============================================================
            # ÉTAPE 1: Supprimer les balises de fermeture ``` (en premier car ça ne décale pas le début)
            # ============================================================
            closing_start = w_block_start + opening_len + len(code_content)
            tk_close_start = f"1.0 + {closing_start} chars"
            tk_close_end = f"1.0 + {closing_start + 3} chars"
            self.typing_widget.delete(tk_close_start, tk_close_end)

            # ============================================================
            # ÉTAPE 2: Appliquer la coloration sur le code (avant de supprimer l'ouverture)
            # ============================================================
            code_start_in_widget = w_block_start + opening_len

            for rel_pos, token_type in code_tokens.items():
                abs_pos = code_start_in_widget + rel_pos
                if rel_pos < len(code_content):
                    tk_start = f"1.0 + {abs_pos} chars"
                    tk_end = f"1.0 + {abs_pos + 1} chars"
                    self.typing_widget.tag_add(token_type, tk_start, tk_end)

            # ============================================================
            # ÉTAPE 3: Supprimer les balises d'ouverture ```langage\n
            # ============================================================
            tk_open_start = f"1.0 + {w_block_start} chars"
            tk_open_end = f"1.0 + {w_block_start + opening_len} chars"
            self.typing_widget.delete(tk_open_start, tk_open_end)

            self.typing_widget.configure(state="disabled")

            # Mettre à jour l'index d'écriture pour compenser les suppressions
            chars_removed = opening_len + 3  # ```langage\n + ```
            self.typing_index -= chars_removed

            # Mettre à jour le buffer en supprimant les balises de CE bloc
            # Chercher le même bloc dans le buffer
            buffer_match = re.search(
                r"```" + re.escape(language) + r"\n(.*?)```",
                self._streaming_buffer,
                re.DOTALL,
            )
            if buffer_match:
                new_buffer = (
                    self._streaming_buffer[: buffer_match.start()]
                    + buffer_match.group(1)  # Garder juste le code
                    + self._streaming_buffer[buffer_match.end() :]
                )
                self._streaming_buffer = new_buffer
                self.typing_text = self._streaming_buffer

            # ============================================================
            # IMPORTANT: Vider le cache de formatage car les positions ont changé
            # ============================================================
            if hasattr(self, "_formatted_positions"):
                self._formatted_positions.clear()
            if hasattr(self, "_formatted_bold_contents"):
                self._formatted_bold_contents.clear()

        except Exception as e:
            print(f"⚠️ [STREAM] Erreur coloration bloc: {e}")
            traceback.print_exc()

    # ================================================================
    # 🎨 PROGRESSIVE CODE BLOCK METHODS
    # ================================================================

    def _handle_progressive_code_block(self):
        """
        Handle progressive code block detection and formatting during streaming.
        Hides opening/closing markers and applies syntax highlighting in real-time.
        Returns True if the current position was handled (caller should return).
        """
        buffer = self._streaming_buffer
        idx = self.typing_index
        buffer_len = len(buffer)

        if idx >= buffer_len:
            return False

        if not getattr(self, '_streaming_in_code_block', False):
            # === NOT IN CODE BLOCK: Check for opening marker ===
            if buffer[idx] != '`':
                return False

            remaining = buffer[idx:]
            if not remaining.startswith('```'):
                # Possibly partial ``` at start of line — wait for more data
                if (idx == 0 or buffer[idx - 1] == '\n') and len(remaining) < 3:
                    if not self._streaming_complete:
                        self.root.after(20, self._continue_streaming_typing_animation)
                        return True
                return False

            # We have ``` — must be at start of line
            if idx > 0 and buffer[idx - 1] != '\n':
                return False

            # Look for the full opening marker: ```language\n
            after_backticks = remaining[3:]
            newline_pos = after_backticks.find('\n')

            if newline_pos == -1:
                # Opening marker incomplete — wait
                if not self._streaming_complete:
                    self.root.after(20, self._continue_streaming_typing_animation)
                    return True
                else:
                    return False

            # Extract and validate language tag
            language_raw = after_backticks[:newline_pos].strip()
            if language_raw:
                language_part = language_raw.split()[0]
                if not re.match(r'^[\w+#.-]+$', language_part):
                    return False  # Not a valid language tag
                language = language_part.lower()
            else:
                language = ""

            # === ENTERING CODE BLOCK ===
            marker_length = 3 + newline_pos + 1  # ``` + lang chars + \n

            # Remove marker from buffer (keeps buffer/widget in sync)
            self._streaming_buffer = buffer[:idx] + buffer[idx + marker_length:]
            self.typing_text = self._streaming_buffer
            # typing_index stays the same — first code char is now at idx

            self._streaming_in_code_block = True
            self._streaming_code_language = language
            self._streaming_code_widget_start = self.typing_widget.index("end-1c")
            self._streaming_code_content = ""
            self._streaming_code_rehighlight_counter = 0

            print(f"🎨 [STREAM] Début bloc code progressif '{language}'")

            self.root.after(10, self._continue_streaming_typing_animation)
            return True

        else:
            # === IN CODE BLOCK: Process code characters ===
            remaining = buffer[idx:]

            # Check for closing marker (``` preceded by newline in code content)
            prev_is_newline = (
                self._streaming_code_content == ''
                or self._streaming_code_content.endswith('\n')
            )

            if prev_is_newline and remaining.startswith('`'):
                if remaining.startswith('```'):
                    after_close = remaining[3:]

                    if after_close == '' and not self._streaming_complete:
                        # Wait for more data to confirm closing
                        self.root.after(20, self._continue_streaming_typing_animation)
                        return True

                    # Closing marker: followed by \n, end-of-buffer, or non-alpha
                    if after_close == '' or not after_close[0].isalpha():
                        # === CLOSING CODE BLOCK ===
                        # Remove closing ``` from buffer
                        self._streaming_buffer = buffer[:idx] + buffer[idx + 3:]
                        self.typing_text = self._streaming_buffer

                        # Final syntax highlighting
                        self._finalize_progressive_code_block()

                        self._streaming_in_code_block = False
                        self._streaming_code_language = ""
                        self._streaming_code_content = ""

                        print("🎨 [STREAM] Fin bloc code progressif")

                        self.root.after(10, self._continue_streaming_typing_animation)
                        return True
                elif len(remaining) < 3 and not self._streaming_complete:
                    # Only 1-2 backticks — might be incomplete closing ```
                    self.root.after(20, self._continue_streaming_typing_animation)
                    return True

            # === BATCH INSERT CODE CHARACTERS ===
            # Scan ahead for the next potential closing marker (``` at line start).
            # Everything before it is safe to insert in one shot with code_block tag.
            look = idx
            batch_limit = min(buffer_len, idx + 200)
            batch_end = batch_limit
            while look < batch_limit:
                nl = buffer.find('\n', look, batch_limit)
                if nl == -1:
                    break
                # If the char after \n is ` we must stop before it
                if nl + 1 < buffer_len and buffer[nl + 1] == '`':
                    batch_end = nl + 1  # include the \n, stop before `
                    break
                look = nl + 1

            # Leave a safety margin at the live streaming frontier
            if not self._streaming_complete and batch_end > buffer_len - 4:
                batch_end = max(idx, buffer_len - 4)

            if batch_end <= idx:
                batch_end = idx + 1  # always make at least 1 char of progress

            chunk = buffer[idx:batch_end]
            self.typing_widget.configure(state="normal")
            self.typing_widget.insert("end", chunk, "code_block")
            self.typing_index += len(chunk)
            self._streaming_code_content += chunk
            self._streaming_code_rehighlight_counter += len(chunk)

            # Re-highlight once per batch (on newline or every 200 chars)
            if '\n' in chunk:
                self._rehighlight_progressive_code_block()
                self.adjust_text_widget_height(self.typing_widget)
                self.root.after(1, self._smart_scroll_follow_animation)
                self._streaming_code_rehighlight_counter = 0
            elif self._streaming_code_rehighlight_counter >= 200:
                self._rehighlight_progressive_code_block()
                self._streaming_code_rehighlight_counter = 0

            self.typing_widget.configure(state="disabled")

            self.root.after(5, self._continue_streaming_typing_animation)
            return True

    def _rehighlight_progressive_code_block(self):
        """Re-apply syntax highlighting on the current progressive code block content."""
        try:
            language = self._streaming_code_language
            code = self._streaming_code_content
            if not code or not self._streaming_code_widget_start:
                return

            code_tokens = self._get_code_tokens(language, code)

            self.typing_widget.configure(state="normal")
            start_idx = self._streaming_code_widget_start

            for rel_pos, token_type in code_tokens.items():
                if rel_pos < len(code):
                    tk_start = f"{start_idx} + {rel_pos} chars"
                    tk_end = f"{start_idx} + {rel_pos + 1} chars"
                    self.typing_widget.tag_add(token_type, tk_start, tk_end)

            self.typing_widget.configure(state="disabled")
        except Exception:
            pass  # Silent — don't disrupt animation for periodic highlight failures

    def _finalize_progressive_code_block(self):
        """Apply final syntax highlighting when a code block closes."""
        try:
            language = self._streaming_code_language
            code = self._streaming_code_content
            if not code:
                return

            code_tokens = self._get_code_tokens(language, code)

            self.typing_widget.configure(state="normal")
            start_idx = self._streaming_code_widget_start

            for rel_pos, token_type in code_tokens.items():
                if rel_pos < len(code):
                    tk_start = f"{start_idx} + {rel_pos} chars"
                    tk_end = f"{start_idx} + {rel_pos + 1} chars"
                    self.typing_widget.tag_add(token_type, tk_start, tk_end)

            self.typing_widget.configure(state="disabled")

            print(f"🎨 [STREAM] Coloration finale '{language}' ({len(code)} chars)")
        except Exception as e:
            print(f"⚠️ [STREAM] Erreur finalisation bloc code: {e}")

    def _rehighlight_all_code_blocks_from_buffer(self, text_widget, raw_source):
        """
        Re-applique la coloration syntaxique à TOUS les blocs de code du widget
        en se basant sur le buffer original (raw_source) pour identifier les
        langages. Cela corrige les pertes de couleur après la finalisation.
        """
        try:
            if not raw_source or not text_widget:
                return

            text_widget.configure(state="normal")

            # Trouver tous les blocs de code dans le source original
            code_pattern = re.compile(r"```([\w+#-]+)?\n(.*?)```", re.DOTALL)
            blocks = []
            for match in code_pattern.finditer(raw_source):
                language = (match.group(1) or "").strip().lower()
                code = match.group(2)
                if code and language:
                    # Utiliser les premières lignes comme signature pour trouver
                    # le bloc dans le widget (les positions ont pu changer)
                    blocks.append((language, code))

            if not blocks:
                text_widget.configure(state="disabled")
                return

            widget_text = text_widget.get("1.0", "end-1c")

            for language, code_raw in blocks:
                code = code_raw.strip()
                if not code:
                    continue

                # Trouver le code dans le widget en cherchant le contenu
                # (les marqueurs ``` ont été supprimés pendant le streaming)
                # Utiliser la première ligne significative comme ancre
                code_lines = code.split("\n")
                anchor = ""
                for line in code_lines:
                    if line.strip():
                        anchor = line.strip()
                        break
                if not anchor or len(anchor) < 3:
                    continue

                # Chercher l'ancre dans le widget
                search_pos = "1.0"
                found = False
                while not found:
                    pos = text_widget.search(anchor, search_pos, "end")
                    if not pos:
                        break

                    # Vérifier que cette position est dans un bloc de code
                    tags = text_widget.tag_names(pos)
                    is_code = any(
                        t in tags for t in (
                            "code_block", "Token.Keyword", "Token.Name",
                            "js_keyword", "bash_keyword", "html_tag",
                            "css_property", "sql_keyword",
                        )
                    )
                    if not is_code:
                        search_pos = text_widget.index(f"{pos}+1c")
                        continue

                    # Remonter au début du bloc de code (chercher la première
                    # position qui a le tag code_block dans cette zone)
                    line_num = int(pos.split(".")[0])
                    block_start_line = line_num
                    for back_line in range(line_num - 1, max(0, line_num - 5), -1):
                        test_pos = f"{back_line}.0"
                        try:
                            test_tags = text_widget.tag_names(test_pos)
                            if any(t.startswith("Token.") or t in (
                                "code_block", "js_keyword", "bash_keyword",
                                "html_tag", "css_property",
                            ) for t in test_tags):
                                block_start_line = back_line
                            else:
                                break
                        except Exception:
                            break

                    # Extraire tout le texte du bloc depuis le widget
                    block_start = f"{block_start_line}.0"
                    # Chercher la fin du bloc (jusqu'à ce qu'on sorte des tags code)
                    current_line = block_start_line
                    max_search = current_line + len(code_lines) + 5
                    total_lines = int(text_widget.index("end-1c").split(".")[0])
                    while current_line <= min(max_search, total_lines):
                        test_pos = f"{current_line}.0"
                        try:
                            line_content = text_widget.get(
                                f"{current_line}.0", f"{current_line}.end"
                            )
                            if not line_content.strip():
                                current_line += 1
                                continue
                            test_tags = text_widget.tag_names(test_pos)
                            if not any(t.startswith("Token.") or t in (
                                "code_block", "js_keyword", "js_string",
                                "bash_keyword", "bash_command",
                                "html_tag", "css_property", "sql_keyword",
                            ) for t in test_tags):
                                break
                        except Exception:
                            break
                        current_line += 1

                    block_end = f"{current_line}.0"
                    block_text = text_widget.get(block_start, block_end).rstrip("\n")

                    if not block_text:
                        search_pos = text_widget.index(f"{pos}+1c")
                        continue

                    # Appliquer la coloration syntaxique
                    tokens = self._get_code_tokens(language, block_text)
                    for rel_pos, token_type in tokens.items():
                        if token_type != "code_block" and rel_pos < len(block_text):
                            tk_start = f"{block_start} + {rel_pos} chars"
                            tk_end = f"{block_start} + {rel_pos + 1} chars"
                            try:
                                text_widget.tag_add(token_type, tk_start, tk_end)
                            except Exception:
                                pass

                    found = True

            text_widget.configure(state="disabled")
            print(f"🎨 [STREAM] Re-coloration de {len(blocks)} bloc(s) de code terminée")

        except Exception as e:
            print(f"⚠️ [STREAM] Erreur re-highlighting blocs de code: {e}")
            try:
                text_widget.configure(state="disabled")
            except Exception:
                pass

    def _get_code_tokens(self, language: str, code: str) -> dict:
        """
        Analyse le code et retourne un dictionnaire position_relative -> token_type.
        """
        tokens = {}

        # Marquer tout comme code_block par défaut
        for i in range(len(code)):
            tokens[i] = "code_block"

        try:
            if language == "python":
                try:
                    lexer = PythonLexer()
                    pos = 0
                    for token_type, token_value in lex(code, lexer):
                        token_name = str(token_type)
                        for _ in token_value:
                            tokens[pos] = token_name
                            pos += 1
                except Exception:
                    pass
            else:
                # Patterns pour chaque langage
                patterns = self._get_language_patterns(language)
                for pattern, token_type in patterns:
                    for match in re.finditer(
                        pattern, code, re.MULTILINE | re.IGNORECASE
                    ):
                        for i in range(match.start(), match.end()):
                            tokens[i] = token_type
        except Exception:
            pass

        return tokens

    def _get_language_patterns(self, language: str) -> list:
        """Retourne les patterns regex pour un langage donné."""
        patterns_map = {
            "javascript": [
                (r"//.*$", "js_comment"),
                (r"/\*.*?\*/", "js_comment"),
                (r'"[^"]*"', "js_string"),
                (r"'[^']*'", "js_string"),
                (r"`[^`]*`", "js_string"),
                (
                    r"\b(const|let|var|function|return|if|else|for|while|class|import|export|from|async|await)\b",
                    "js_keyword",
                ),
                (r"\b(console|document|window)\b", "js_variable"),
            ],
            "java": [
                (r"//.*$", "java_comment"),
                (r"/\*.*?\*/", "java_comment"),
                (r'"[^"]*"', "java_string"),
                (
                    r"\b(public|private|protected|static|void|class|interface|extends|implements|new|return|if|else|for|while|int|String|boolean|package|import)\b",
                    "java_keyword",
                ),
                (r"\b[A-Z][a-zA-Z0-9]*\b", "java_class"),
            ],
            "c": [
                (r"//.*$", "c_comment"),
                (r"/\*.*?\*/", "c_comment"),
                (r'"[^"]*"', "c_string"),
                (r"#\w+.*$", "c_preprocessor"),
                (
                    r"\b(int|void|char|float|double|return|if|else|for|while|include|using|namespace|std)\b",
                    "c_keyword",
                ),
                (r"\b\d+\b", "c_number"),
            ],
            "cpp": [
                (r"//.*$", "c_comment"),
                (r"/\*.*?\*/", "c_comment"),
                (r'"[^"]*"', "c_string"),
                (r"#\w+.*$", "c_preprocessor"),
                (
                    r"\b(int|void|char|float|double|return|if|else|for|while|include|using|namespace|std|class|public|private)\b",
                    "c_keyword",
                ),
                (r"\b\d+\b", "c_number"),
            ],
            "csharp": [
                (r"//.*$", "csharp_comment"),
                (r"/\*.*?\*/", "csharp_comment"),
                (r'"[^"]*"', "csharp_string"),
                (
                    r"\b(public|private|protected|static|void|class|interface|namespace|using|new|return|if|else|for|while|int|string|bool|var)\b",
                    "csharp_keyword",
                ),
                (r"\b[A-Z][a-zA-Z0-9]*\b", "csharp_class"),
            ],
            "html": [
                (r"<!--.*?-->", "html_comment"),
                (r"<[^>]+>", "html_tag"),
                (r'"[^"]*"', "html_value"),
            ],
            "css": [
                (r"/\*.*?\*/", "css_comment"),
                (r"[.#]?[a-zA-Z_][a-zA-Z0-9_-]*(?=\s*\{)", "css_selector"),
                (r"[a-zA-Z-]+(?=\s*:)", "css_property"),
                (r"\d+(\.\d+)?(px|em|rem|%|vh|vw)", "css_unit"),
                (r"#[a-fA-F0-9]{3,8}", "css_value"),
            ],
            "sql": [
                (r"--.*$", "sql_comment"),
                (r"'[^']*'", "sql_string"),
                (
                    r"\b(SELECT|FROM|WHERE|INSERT|UPDATE|DELETE|CREATE|TABLE|INTO|VALUES|AND|OR|JOIN|ON|AS|ORDER|BY|GROUP|HAVING|LIMIT)\b",
                    "sql_keyword",
                ),
            ],
            "bash": [
                (r"#.*$", "bash_comment"),
                (r'"[^"]*"', "bash_string"),
                (r"'[^']*'", "bash_string"),
                (
                    r"\b(echo|cd|ls|mkdir|rm|cp|mv|cat|grep|sed|awk|if|then|else|fi|for|do|done|while)\b",
                    "bash_command",
                ),
            ],
            "php": [
                (r"//.*$", "php_comment"),
                (r"/\*.*?\*/", "php_comment"),
                (r'"[^"]*"', "php_string"),
                (r"'[^']*'", "php_string"),
                (r"<\?php|\?>", "php_tag"),
                (
                    r"\b(echo|print|function|return|if|else|for|while|class|public|private)\b",
                    "php_keyword",
                ),
            ],
            "ruby": [
                (r"#.*$", "ruby_comment"),
                (r'"[^"]*"', "ruby_string"),
                (r"'[^']*'", "ruby_string"),
                (
                    r"\b(def|end|class|module|if|else|elsif|unless|while|do|puts|print|require)\b",
                    "ruby_keyword",
                ),
                (r"\b(puts|print|gets)\b", "ruby_method"),
            ],
            "swift": [
                (r"//.*$", "swift_comment"),
                (r"/\*.*?\*/", "swift_comment"),
                (r'"[^"]*"', "swift_string"),
                (
                    r"\b(func|var|let|class|struct|import|return|if|else|for|while|print)\b",
                    "swift_keyword",
                ),
            ],
            "go": [
                (r"//.*$", "go_comment"),
                (r"/\*.*?\*/", "go_comment"),
                (r'"[^"]*"', "go_string"),
                (r"`[^`]*`", "go_string"),
                (
                    r"\b(package|import|func|var|const|type|struct|interface|return|if|else|for|range|switch|case|break|continue|defer|go|chan|map|make|new)\b",
                    "go_keyword",
                ),
                (r"\b(fmt|Println|Printf)\b", "go_function"),
                (r"\b[A-Z][a-zA-Z0-9]*\b", "go_type"),
            ],
            "rust": [
                (r"//.*$", "rust_comment"),
                (r"/\*.*?\*/", "rust_comment"),
                (r'"[^"]*"', "rust_string"),
                (
                    r"\b(fn|let|mut|const|use|pub|mod|struct|enum|impl|trait|return|if|else|match|for|while|loop|break|continue)\b",
                    "rust_keyword",
                ),
                (r"\b(println!|print!|vec!|format!)\b", "rust_macro"),
                (r"\b[A-Z][a-zA-Z0-9]*\b", "rust_type"),
                (r"&'[a-z]+\b", "rust_lifetime"),
            ],
            "perl": [
                (r"#.*$", "perl_comment"),
                (r'"[^"]*"', "perl_string"),
                (r"'[^']*'", "perl_string"),
                (
                    r"\b(sub|my|local|our|use|require|if|else|elsif|unless|while|for|foreach|do|return|package)\b",
                    "perl_keyword",
                ),
                (r"[$@%]\w+", "perl_variable"),
                (r"/(\\.|[^\\/])+/[gimsx]*", "perl_regex"),
            ],
            "dockerfile": [
                (r"#.*$", "dockerfile_comment"),
                (
                    r"\b(FROM|RUN|CMD|COPY|ADD|EXPOSE|ENV|WORKDIR|ENTRYPOINT|VOLUME|USER|ARG)\b",
                    "dockerfile_instruction",
                ),
                (r'"[^"]*"', "dockerfile_string"),
            ],
        }

        # Alias
        patterns_map["js"] = patterns_map["javascript"]
        patterns_map["ts"] = patterns_map["javascript"]
        patterns_map["typescript"] = patterns_map["javascript"]
        patterns_map["c++"] = patterns_map["cpp"]
        patterns_map["cs"] = patterns_map["csharp"]
        patterns_map["sh"] = patterns_map["bash"]
        patterns_map["shell"] = patterns_map["bash"]
        patterns_map["rb"] = patterns_map["ruby"]
        patterns_map["docker"] = patterns_map["dockerfile"]
        patterns_map["golang"] = patterns_map["go"]
        patterns_map["rs"] = patterns_map["rust"]
        patterns_map["pl"] = patterns_map["perl"]

        return patterns_map.get(language, [])

    def _analyze_single_code_block(
        self, language: str, code_content: str, block_start: int
    ) -> dict:
        """
        Analyse un seul bloc de code et retourne un dictionnaire position -> (language, token_type).
        """
        tokens_map = {}

        try:
            # Offset pour le contenu du code (après ```langage\n)
            marker_length = 3 + len(language) + 1  # ``` + language + \n
            code_offset = block_start + marker_length

            # Marquer les ``` d'ouverture comme hidden
            for i in range(3):
                tokens_map[block_start + i] = (language, "code_block_marker")
            # Marquer le nom du langage comme hidden aussi
            for i in range(len(language)):
                tokens_map[block_start + 3 + i] = (language, "code_block_marker")
            # Marquer le \n après le langage
            tokens_map[block_start + 3 + len(language)] = (
                language,
                "code_block_marker",
            )

            # Marquer les ``` de fermeture comme hidden
            closing_start = block_start + marker_length + len(code_content)
            for i in range(3):
                tokens_map[closing_start + i] = (language, "code_block_marker")

            # Analyser le code selon le langage
            if language == "python":
                self._analyze_python_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("javascript", "js", "typescript", "ts"):
                self._analyze_js_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("java",):
                self._analyze_java_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("c", "cpp", "c++", "csharp", "cs"):
                self._analyze_c_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("html", "xml"):
                self._analyze_html_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("sql",):
                self._analyze_sql_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("bash", "sh", "shell"):
                self._analyze_bash_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("php",):
                self._analyze_php_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("ruby", "rb"):
                self._analyze_ruby_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("css", "scss", "sass"):
                self._analyze_css_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            elif language in ("dockerfile", "docker"):
                self._analyze_dockerfile_tokens_for_block(
                    code_content, code_offset, tokens_map, language
                )
            else:
                # Langage non reconnu - marquer tout comme code_block
                for i, _ in enumerate(code_content):
                    tokens_map[code_offset + i] = (language, "code_block")

        except Exception as e:
            print(f"⚠️ Erreur analyse bloc {language}: {e}")

        return tokens_map

    def _analyze_python_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens Python avec Pygments."""
        try:
            lexer = PythonLexer()
            pos = 0
            for token_type, token_value in lex(code, lexer):
                token_name = str(token_type)
                for _ in token_value:
                    tokens_map[offset + pos] = (language, token_name)
                    pos += 1
        except Exception:
            for i, _ in enumerate(code):
                tokens_map[offset + i] = (language, "code_block")

    def _analyze_js_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens JavaScript."""
        patterns = [
            (r"//.*$", "js_comment"),
            (r"/\*.*?\*/", "js_comment"),
            (r'"[^"]*"', "js_string"),
            (r"'[^']*'", "js_string"),
            (r"`[^`]*`", "js_string"),
            (
                r"\b(const|let|var|function|return|if|else|for|while|class|import|export|from|async|await)\b",
                "js_keyword",
            ),
            (r"\b(console|document|window)\b", "js_variable"),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_java_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens Java."""
        patterns = [
            (r"//.*$", "java_comment"),
            (r"/\*.*?\*/", "java_comment"),
            (r'"[^"]*"', "java_string"),
            (
                r"\b(public|private|protected|static|void|class|interface|extends|implements|new|return|if|else|for|while|int|String|boolean)\b",
                "java_keyword",
            ),
            (r"\b[A-Z][a-zA-Z0-9]*\b", "java_class"),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_c_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens C/C++/C#."""
        prefix = "csharp" if language in ("csharp", "cs") else "c"
        patterns = [
            (r"//.*$", f"{prefix}_comment"),
            (r"/\*.*?\*/", f"{prefix}_comment"),
            (r'"[^"]*"', f"{prefix}_string"),
            (r"#\w+.*$", f"{prefix}_preprocessor"),
            (
                r"\b(int|void|char|float|double|return|if|else|for|while|class|public|private|static|using|namespace|Console|WriteLine)\b",
                f"{prefix}_keyword",
            ),
            (r"\b[A-Z][a-zA-Z0-9]*\b", f"{prefix}_class"),
            (r"\b\d+\b", f"{prefix}_number"),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_html_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens HTML."""
        patterns = [
            (r"<!--.*?-->", "html_comment"),
            (r"<[^>]+>", "html_tag"),
            (r'"[^"]*"', "html_string"),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_sql_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens SQL."""
        patterns = [
            (r"--.*$", "sql_comment"),
            (r"'[^']*'", "sql_string"),
            (
                r"\b(SELECT|FROM|WHERE|INSERT|UPDATE|DELETE|CREATE|TABLE|INTO|VALUES|AND|OR|JOIN|ON|AS|ORDER|BY|GROUP|HAVING|LIMIT)\b",
                "sql_keyword",
            ),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_bash_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens Bash."""
        patterns = [
            (r"#.*$", "bash_comment"),
            (r'"[^"]*"', "bash_string"),
            (r"'[^']*'", "bash_string"),
            (
                r"\b(echo|cd|ls|mkdir|rm|cp|mv|cat|grep|sed|awk|if|then|else|fi|for|do|done|while)\b",
                "bash_command",
            ),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_php_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens PHP."""
        patterns = [
            (r"//.*$", "php_comment"),
            (r"/\*.*?\*/", "php_comment"),
            (r'"[^"]*"', "php_string"),
            (r"'[^']*'", "php_string"),
            (r"<\?php|\?>", "php_tag"),
            (
                r"\b(echo|print|function|return|if|else|for|while|class|public|private)\b",
                "php_keyword",
            ),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_ruby_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens Ruby."""
        patterns = [
            (r"#.*$", "ruby_comment"),
            (r'"[^"]*"', "ruby_string"),
            (r"'[^']*'", "ruby_string"),
            (
                r"\b(def|end|class|module|if|else|elsif|unless|while|do|puts|print|require)\b",
                "ruby_keyword",
            ),
            (r"\b(puts|print|gets)\b", "ruby_method"),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_css_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens CSS."""
        patterns = [
            (r"/\*.*?\*/", "css_comment"),
            (r"[.#]?[a-zA-Z_][a-zA-Z0-9_-]*(?=\s*\{)", "css_selector"),  # Sélecteurs
            (r"[a-zA-Z-]+(?=\s*:)", "css_property"),  # Propriétés
            (r":\s*([^;{}]+)", "css_value"),  # Valeurs
            (r"\d+(\.\d+)?(px|em|rem|%|vh|vw|pt|cm|mm|in)", "css_unit"),  # Unités
            (r'"[^"]*"', "css_string"),
            (r"'[^']*'", "css_string"),
            (r"#[a-fA-F0-9]{3,8}", "css_value"),  # Couleurs hex
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _analyze_dockerfile_tokens_for_block(
        self, code: str, offset: int, tokens_map: dict, language: str
    ):
        """Analyse les tokens Dockerfile."""
        patterns = [
            (r"#.*$", "dockerfile_comment"),
            (
                r"\b(FROM|RUN|CMD|LABEL|MAINTAINER|EXPOSE|ENV|ADD|COPY|ENTRYPOINT|VOLUME|USER|WORKDIR|ARG|ONBUILD|STOPSIGNAL|HEALTHCHECK|SHELL)\b",
                "dockerfile_instruction",
            ),
            (r'"[^"]*"', "dockerfile_string"),
            (r"'[^']*'", "dockerfile_string"),
            (r"\$\{?[a-zA-Z_][a-zA-Z0-9_]*\}?", "dockerfile_variable"),
            (r"--[a-zA-Z-]+=?", "dockerfile_flag"),
        ]
        self._apply_patterns_to_block(
            code, offset, tokens_map, language, patterns, "code_block"
        )

    def _apply_patterns_to_block(
        self,
        code: str,
        offset: int,
        tokens_map: dict,
        language: str,
        patterns: list,
        default_token: str,
    ):
        """Applique une liste de patterns regex à un bloc de code."""
        # D'abord, marquer tout comme default_token
        for i, _ in enumerate(code):
            if (offset + i) not in tokens_map:
                tokens_map[offset + i] = (language, default_token)

        # Ensuite, appliquer les patterns spécifiques
        for pattern, token_type in patterns:
            for match in re.finditer(pattern, code, re.MULTILINE | re.IGNORECASE):
                for i in range(match.start(), match.end()):
                    tokens_map[offset + i] = (language, token_type)

    def _finish_streaming_animation(self, _interrupted=False):
        """
        Finalise l'animation de streaming avec le formatage complet.
        IMPORTANT: La coloration syntaxique a déjà été appliquée pendant l'animation,
        donc on ne refait PAS le reformatage des blocs de code.
        """
        try:
            if not hasattr(self, "typing_widget") or self.typing_widget is None:
                self.set_input_state(True)
                # Si le message venait du relay, signaler une réponse vide
                if getattr(self, '_current_message_from_relay', False):
                    self._current_message_from_relay = False
                    try:
                        relay_srv = getattr(self, '_relay_server', None)
                        if relay_srv and relay_srv.bridge.active:
                            relay_srv.bridge.submit_ai_response("⚠️ Réponse interrompue.")
                    except Exception:
                        pass
                return

            # Handle unclosed code blocks from progressive streaming
            if getattr(self, '_streaming_in_code_block', False):
                self._finalize_progressive_code_block()
                self._streaming_in_code_block = False

            # Récupérer le texte ACTUEL du widget (déjà coloré pendant l'animation)
            self.typing_widget.configure(state="normal")

            # Si le mode rattrapage immédiat a déclenché, le widget peut être
            # (quasi) vide alors que le buffer contient tout le texte.
            # → insérer le texte manquant avant de formater.
            # NOTE: On compare typing_index (chars consommés par l'animation)
            # avec la taille du buffer, PAS la taille du widget. Le widget
            # est plus court que le buffer car le formatage progressif a
            # supprimé des marqueurs (**, ##, - ) et les a remplacés par
            # des tags visuels. Comparer les longueurs de texte causerait
            # un faux positif qui remplacerait le widget formaté par du
            # texte brut, détruisant tout le formatage.
            buffer_text = getattr(self, "_streaming_buffer", "") or ""
            current_widget_text = self.typing_widget.get("1.0", "end-1c")
            typing_index = getattr(self, "typing_index", 0)
            if typing_index < len(buffer_text) * 0.9:
                # L'animation n'a pas consommé tout le buffer → dump le buffer
                self.typing_widget.delete("1.0", "end")
                self.typing_widget.insert("1.0", buffer_text)
                current_widget_text = self.typing_widget.get("1.0", "end-1c")

            # IMPORTANT: S'assurer que typing_text est défini pour le formatage
            self.typing_text = current_widget_text

            # Réinitialiser les positions pour forcer un formatage complet
            # Mais ne PAS réinitialiser _pending_links qui contient les liens déjà détectés
            if hasattr(self, "_formatted_positions"):
                self._formatted_positions.clear()
            if hasattr(self, "_formatted_bold_contents"):
                self._formatted_bold_contents.clear()

            # ============================================================
            # 🎨 FORMATAGE DES TABLEAUX — Toujours depuis le source original
            # Le check précédent (box-drawing chars dans le widget) échouait
            # quand seulement CERTAINS tableaux étaient formatés pendant
            # l'animation : les autres restaient en markdown brut.
            raw_source = getattr(self, "_streaming_buffer_original", "") or getattr(self, "_streaming_buffer", "") or current_widget_text

            # Normaliser les sauts de ligne multiples (max 2 consécutifs = 1 ligne vide)
            # Évite les grands espaces vides entre tableaux/code et texte
            raw_source = re.sub(r'\n{3,}', '\n\n', raw_source)

            # Normaliser les checkboxes en puces dans le source
            # Les listes numérotées (1. 2. 3.) restent intactes pour
            # conserver la cohérence entre le streaming et l'affichage final.
            raw_source = re.sub(r"^(\s*)[\□☐☑✓✔]\s*", r"\1- ", raw_source, flags=re.MULTILINE)

            # Appliquer dans le widget de façon CIBLÉE (sans delete/insert global
            # qui détruirait tous les tags de formatage déjà appliqués)
            # Seules les checkboxes sont converties en puces.
            # Les listes numérotées (1. 2. 3.) restent telles quelles.
            _numlist_patterns = [
                (r"^[\□☐☑✓✔]\s*", "- "),          # "□ " → "- "
            ]
            try:
                for pattern, replacement in _numlist_patterns:
                    scan_pos = "1.0"
                    while True:
                        match_pos = self.typing_widget.search(
                            pattern, scan_pos, "end", regexp=True
                        )
                        if not match_pos:
                            break
                        # Vérifier qu'on est en début de ligne
                        line_start = self.typing_widget.index(f"{match_pos} linestart")
                        if match_pos != line_start:
                            scan_pos = self.typing_widget.index(f"{match_pos}+1c")
                            continue
                        # Ne PAS modifier à l'intérieur d'un bloc de code
                        if self._is_position_in_code_block(self.typing_widget, match_pos):
                            scan_pos = self.typing_widget.index(f"{match_pos} lineend +1c")
                            continue
                        # Mesurer le match dans le texte
                        line_end = self.typing_widget.index(f"{match_pos} lineend")
                        line_text = self.typing_widget.get(match_pos, line_end)
                        m = re.match(pattern, line_text)
                        if m:
                            match_end = self.typing_widget.index(
                                f"{match_pos}+{len(m.group(0))}c"
                            )
                            self.typing_widget.delete(match_pos, match_end)
                            self.typing_widget.insert(match_pos, replacement)
                        scan_pos = self.typing_widget.index(f"{match_pos} lineend +1c")
            except Exception:
                pass  # Ne pas bloquer le formatage si ça échoue

            # Détecter les tableaux dans le SOURCE ORIGINAL (pas le widget)
            _sep_pattern = re.compile(r'^\|[\s\-:]+\|', re.MULTILINE)
            has_markdown_tables = bool(_sep_pattern.search(raw_source))

            if has_markdown_tables:
                print(
                    "[DEBUG] _finish_streaming: Tableaux markdown détectés dans le source → reconstruction complète"
                )
                # Pré-analyser les tableaux
                self._table_blocks = self._preanalyze_markdown_tables(
                    raw_source
                )

                # Formater les tableaux Markdown (reconstruit le widget à partir du source original)
                self._format_markdown_tables_in_widget(
                    self.typing_widget, raw_source
                )

                # IMPORTANT: Effacer typing_text AVANT le formatage full_scan.
                # Après la reconstruction des tableaux, le widget contient du
                # markdown brut (## **titre**, **bold**, etc.) qu'il faut reformater.
                # Si typing_text reste défini, le formateur de titres refuse de
                # traiter les lignes (line_is_complete=False) et le formateur
                # bold rejette les paires absentes du typing_text stale.
                self.typing_text = ""

                # Après reconstruction, appliquer le formatage unifié complet
                # pour rattraper tout ce que _apply_simple_markdown_formatting
                # pourrait avoir manqué (listes, bold restants, etc.)
                self._apply_unified_progressive_formatting(self.typing_widget, full_scan=True)
            else:
                print(
                    "[DEBUG] _finish_streaming: Pas de tableaux, formatage inline uniquement"
                )
                # IMPORTANT: Effacer typing_text pour le même motif que ci-dessus
                self.typing_text = ""

                # Pas de tableaux : formatage Markdown complet (full_scan) sans détruire le widget
                self._apply_unified_progressive_formatting(self.typing_widget, full_scan=True)

            # Les liens ont déjà été collectés pendant l'animation dans _pending_links
            # Ne PAS les rescanner ni les effacer
            print(
                f"[DEBUG] _finish_streaming: {len(self._pending_links) if hasattr(self, '_pending_links') else 0} liens dans _pending_links"
            )

            # Convertir les liens en cliquables
            self._convert_temp_links_to_clickable(self.typing_widget)

            # ============================================================
            # 🎨 RE-COLORATION des blocs de code après formatage
            # Le formatage full_scan ou la reconstruction des tableaux peut
            # avoir perdu des tokens de coloration syntaxique. On re-applique
            # la coloration à partir du buffer original.
            # ============================================================
            self._rehighlight_all_code_blocks_from_buffer(self.typing_widget, raw_source)

            # ============================================================
            # 📥 GESTION SPÉCIALE DU LIEN DE TÉLÉCHARGEMENT DE FICHIER
            # ============================================================
            if hasattr(self, "_pending_file_download") and self._pending_file_download:
                try:
                    filename = self._pending_file_download.get("filename", "fichier")
                    file_path = self._pending_file_download.get("file_path")

                    # Capturer le widget dans une variable locale
                    current_widget = self.typing_widget

                    # Ajouter le nom du fichier avec lien cliquable
                    current_widget.configure(state="normal")
                    current_widget.insert("end", filename)

                    # Trouver la position du nom de fichier
                    text_content = current_widget.get("1.0", "end-1c")
                    filename_pos = text_content.rfind(filename)
                    if filename_pos != -1:
                        # Calculer la ligne et colonne
                        lines_before = text_content[:filename_pos].count("\n")
                        col_before = (
                            filename_pos - text_content[:filename_pos].rfind("\n") - 1
                            if "\n" in text_content[:filename_pos]
                            else filename_pos
                        )

                        start_idx = f"{lines_before + 1}.{col_before}"
                        end_idx = f"{lines_before + 1}.{col_before + len(filename)}"

                        # Créer un tag unique pour ce lien
                        tag_name = f"file_download_{filename}"

                        # Configurer le tag avec style de lien
                        current_widget.tag_add(tag_name, start_idx, end_idx)
                        current_widget.tag_config(
                            tag_name,
                            foreground="#3b82f6",
                            underline=True,
                            font=("Segoe UI", 10, "bold"),
                        )

                        # Capturer les données dans la closure
                        def make_click_handler(path, name):
                            def on_click(_event):
                                self.download_file_to_downloads(path, name)

                            return on_click

                        def make_enter_handler(widget):
                            def on_enter(_event):
                                widget.config(cursor="hand2")

                            return on_enter

                        def make_leave_handler(widget):
                            def on_leave(_event):
                                widget.config(cursor="")

                            return on_leave

                        # Bind du clic sur le nom du fichier avec closures
                        current_widget.tag_bind(
                            tag_name,
                            "<Button-1>",
                            make_click_handler(file_path, filename),
                        )
                        current_widget.tag_bind(
                            tag_name, "<Enter>", make_enter_handler(current_widget)
                        )
                        current_widget.tag_bind(
                            tag_name, "<Leave>", make_leave_handler(current_widget)
                        )

                    current_widget.configure(state="disabled")

                    # Nettoyer le pending_file_download
                    self._pending_file_download = None

                except Exception as e:
                    print(f"Erreur ajout lien fichier: {e}")

            # Ajustement final de la hauteur
            self._adjust_height_final_no_scroll(self.typing_widget)

            # Réactiver le scroll
            self._reactivate_text_scroll(self.typing_widget)

            self.typing_widget.configure(state="disabled")

            # Mettre à jour l'historique avec le texte brut original (marqueurs markdown)
            # pour permettre la restauration avec formatage lors du chargement de session
            displayed_text = self.typing_widget.get("1.0", "end-1c")
            raw_text = getattr(self, "_streaming_buffer_original", "") or getattr(self, "_streaming_buffer", "")
            history_text = raw_text if raw_text else displayed_text
            if self.conversation_history:
                self.conversation_history[-1]["text"] = history_text
            if hasattr(self, "current_message_container") and self.current_message_container is not None:
                self.current_message_container.feedback_query = getattr(self, "_last_user_query", None)
                self.current_message_container.feedback_response = displayed_text
                print(f"[DEBUG STOCKAGE FEEDBACK] Query: {getattr(self, '_last_user_query', 'None')[:50]}...")
                print(f"[DEBUG STOCKAGE FEEDBACK] Response: {displayed_text[:50]}...")

            # ── RELAY : renvoyer la réponse au mobile si le message venait du relay
            if getattr(self, '_current_message_from_relay', False):
                self._current_message_from_relay = False
                try:
                    relay_srv = getattr(self, '_relay_server', None)
                    if relay_srv and relay_srv.bridge.active:
                        relay_srv.bridge.submit_ai_response(history_text)
                        print("📡 [RELAY] Réponse envoyée au mobile via bridge")
                except Exception as e:
                    print(f"⚠️ [RELAY] Erreur envoi réponse mobile: {e}")

            # Afficher le timestamp
            self._show_timestamp_for_current_message()

            # Réactiver la saisie
            self.set_input_state(True)

            # Scroll final — délai court pour laisser le timestamp se rendre
            self.root.after(50, self._final_smooth_scroll_to_bottom)

            # Nettoyage des variables streaming
            self._streaming_mode = False
            self._streaming_buffer = ""
            self._streaming_buffer_original = ""
            self._streaming_complete = False

            # Nettoyage des variables d'animation (comme finish_typing_animation_dynamic)
            if hasattr(self, "typing_widget"):
                delattr(self, "typing_widget")
            if hasattr(self, "typing_text"):
                delattr(self, "typing_text")
            if hasattr(self, "typing_index"):
                delattr(self, "typing_index")

            self._typing_interrupted = False

            # Nettoyer le cache de formatage
            if hasattr(self, "_formatted_positions"):
                delattr(self, "_formatted_positions")

            print(
                f"✅ [STREAM] Animation terminée et affichage finalisé : {len(current_widget_text)} caractères"
            )

        except Exception as e:
            print(f"❌ [STREAM] Erreur finalisation: {e}")
            traceback.print_exc()

    # ── THINKING MODE — Widget Raisonnement dépliable ────────────────────────

    def _create_reasoning_widget(self):
        """
        Crée le widget Raisonnement dans le même style visuel que l'indicateur MCP :
        🤖 icon + texte animé, centré avec padding 250px, expandable.
        Démarre replié (▶) par défaut.
        """
        try:
            # Ajouter un placeholder dans conversation_history pour que le
            # widget raisonnement occupe une *vraie* row dans le grid.
            # Cela évite les collisions de row entre la bulle streaming qui
            # suit et le prochain message utilisateur.
            self.conversation_history.append(
                {
                    "text": "",
                    "is_user": False,
                    "timestamp": __import__('datetime').datetime.now(),
                    "type": "reasoning_widget",
                }
            )
            self._reasoning_widget_row = len(self.conversation_history) - 1
            self._reasoning_expanded = False   # Replié par défaut
            self._thinking_mode_active = True  # Signale à la bulle réponse de ne pas re-afficher 🤖
            self._last_bubble_is_user = False  # Le widget Raisonnement est un output IA
            self._pending_thinking_tokens = []  # Buffer pour la race condition widget/tokens
            self._reasoning_auto_expanded = False  # Auto-expand initial au 1er token uniquement

            # Container principal — identique aux bulles IA / indicateur MCP
            self._reasoning_container = self.create_frame(
                self.chat_frame, fg_color=self.colors["bg_chat"]
            )
            self._reasoning_container.grid(
                row=self._reasoning_widget_row,
                column=0,
                sticky="ew",
                pady=(0, 4),
            )
            self._reasoning_container.grid_columnconfigure(0, weight=1)

            # Frame de centrage — même padding 250px que les bulles IA
            center_frame = self.create_frame(
                self._reasoning_container, fg_color=self.colors["bg_chat"]
            )
            center_frame.grid(
                row=0, column=0, padx=(250, 250), pady=(0, 0), sticky="ew"
            )
            center_frame.grid_columnconfigure(0, weight=0)
            center_frame.grid_columnconfigure(1, weight=1)

            # Icône IA — identique aux bulles IA
            icon_label = self.create_label(
                center_frame,
                text="🤖",
                font=("Segoe UI", 16),
                fg_color=self.colors["bg_chat"],
                text_color=self.colors["accent"],
            )
            icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(7, 0))

            # Zone reasoning (column 1) — header + contenu dépliable
            reasoning_area = self.create_frame(
                center_frame, fg_color=self.colors["bg_chat"]
            )
            reasoning_area.grid(row=0, column=1, sticky="ew", padx=0, pady=(2, 2))
            reasoning_area.grid_columnconfigure(1, weight=1)

            # ── Header : toggle ▶ (label cliquable, fond identique à l'app) ──
            self._reasoning_toggle_btn = self.create_label(
                reasoning_area,
                text="▸",
                font=("Segoe UI", 24),
                fg_color=self.colors["bg_chat"],
                text_color=self.colors.get("text_secondary", "#888888"),
            )
            try:
                self._reasoning_toggle_btn.configure(cursor="hand2")
            except Exception:
                pass
            self._reasoning_toggle_btn.grid(
                row=0, column=0, padx=(0, 4), pady=(0, 0), sticky="w"
            )
            self._reasoning_toggle_btn.bind(
                "<Button-1>", lambda e: self._toggle_reasoning_widget()
            )

            # Label animé style MCP indicator : gris, taille 11
            self._reasoning_label = self.create_label(
                reasoning_area,
                text="Raisonnement.",
                font=("Segoe UI", 11),
                fg_color=self.colors["bg_chat"],
                text_color="#888888",
            )
            self._reasoning_label.grid(
                row=0, column=1, sticky="w", padx=(8, 0), pady=(5, 0)
            )
            self._reasoning_label.bind(
                "<Button-1>", lambda e: self._toggle_reasoning_widget()
            )

            # ── Contenu dépliable (masqué par défaut) ────────────────────────
            self._reasoning_content = self.create_frame(
                reasoning_area, fg_color=self.colors["bg_chat"]
            )
            self._reasoning_content.grid(
                row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4)
            )
            self._reasoning_content.grid_columnconfigure(0, weight=1)
            # Replié par défaut — cache le contenu
            self._reasoning_content.grid_remove()

            bg_thinking = self.colors.get("bg_secondary", "#1e1e2e")
            self._reasoning_text_widget = tk.Text(
                self._reasoning_content,
                height=6,
                width=80,
                bg=bg_thinking,
                fg="#aaaaaa",
                font=("Segoe UI", 10, "italic"),
                wrap=tk.WORD,
                state="disabled",
                relief="flat",
                bd=0,
                cursor="arrow",
                padx=8,
                pady=4,
            )
            self._reasoning_text_widget.grid(row=0, column=0, sticky="ew")

            # Scroll isolé : la molette ne propage pas vers le chat principal
            def _scroll_reasoning(event, _w=self._reasoning_text_widget):
                if getattr(event, "delta", 0):
                    _w.yview_scroll(int(-1 * (event.delta / 120)), "units")
                elif getattr(event, "num", 0) == 4:
                    _w.yview_scroll(-1, "units")
                elif getattr(event, "num", 0) == 5:
                    _w.yview_scroll(1, "units")
                return "break"  # Bloque la propagation vers le canvas principal

            self._reasoning_text_widget.bind("<MouseWheel>", _scroll_reasoning)
            self._reasoning_text_widget.bind("<Button-4>", _scroll_reasoning)
            self._reasoning_text_widget.bind("<Button-5>", _scroll_reasoning)

            # Démarrer l'animation des points
            self._start_reasoning_dots()
            self.scroll_to_bottom()

        except Exception as exc:
            print(f"⚠️ [Reasoning Widget] Erreur création: {exc}")

    def _stream_thinking_token(self, token):
        """Insère un token de raisonnement dans le widget thinking.
        Bufferise les tokens si le widget n'est pas encore créé (race condition).
        Auto-expand le widget au premier token pour que l'utilisateur voie le raisonnement."""
        try:
            if not hasattr(self, "_reasoning_text_widget") or not self._reasoning_text_widget.winfo_exists():
                # Widget pas encore prêt — bufferiser pour flush ultérieur
                if not hasattr(self, "_pending_thinking_tokens"):
                    self._pending_thinking_tokens = []
                self._pending_thinking_tokens.append(token)
                return

            # Auto-expand une seule fois au premier token — respecte les closes manuelles ensuite
            if not getattr(self, "_reasoning_auto_expanded", False):
                self._reasoning_auto_expanded = True
                if not self._reasoning_expanded:
                    if hasattr(self, "_reasoning_content"):
                        self._reasoning_content.grid()
                    try:
                        self._reasoning_toggle_btn.configure(text="▾")
                    except Exception:
                        pass
                    self._reasoning_expanded = True

            w = self._reasoning_text_widget
            w.configure(state="normal")

            # Flush du buffer si des tokens ont été mis en attente
            pending = getattr(self, "_pending_thinking_tokens", None)
            if pending:
                for buffered in pending:
                    w.insert("end", buffered)
                self._pending_thinking_tokens = []

            w.insert("end", token)
            w.see("end")
            w.configure(state="disabled")
        except Exception as _e:
            print(f"⚠️ [THINKING TOKEN] Erreur insertion: {_e}")

    def _finalize_reasoning_widget(self):
        """Appelé quand la passe thinking est terminée : arrête l'animation.
        Si aucun token de raisonnement n'a été reçu (widget vide), masque
        entièrement le container pour ne pas afficher un encadré vide.
        Dans ce cas, restaure également _last_bubble_is_user pour que la
        bulle de réponse suivante affiche bien l'émoji robot.
        """
        self._stop_reasoning_dots(_success=True)
        # Réactiver l'icône robot pour la prochaine bulle réponse
        self._thinking_mode_active = False
        try:
            # Vérifier si le widget de texte est vide (thinking skippé)
            if (
                hasattr(self, "_reasoning_text_widget")
                and self._reasoning_text_widget.winfo_exists()
            ):
                content = self._reasoning_text_widget.get("1.0", "end-1c").strip()
                if not content and hasattr(self, "_reasoning_container"):
                    # Aucun token reçu → masquer le widget entièrement
                    self._reasoning_container.grid_remove()
                    # Restaurer le flag pour que la bulle réponse affiche
                    # l'émoji robot (le widget vide ne compte pas comme
                    # un output IA visible).
                    self._last_bubble_is_user = True
        except Exception:
            pass

    def _toggle_reasoning_widget(self):
        """Collapse ou expand le contenu du raisonnement."""
        try:
            if not hasattr(self, "_reasoning_content"):
                return
            if self._reasoning_expanded:
                self._reasoning_content.grid_remove()
                try:
                    self._reasoning_toggle_btn.configure(text="▸")
                except Exception:
                    pass
                self._reasoning_expanded = False
            else:
                self._reasoning_content.grid()
                try:
                    self._reasoning_toggle_btn.configure(text="▾")
                except Exception:
                    pass
                self._reasoning_expanded = True
        except Exception:
            self.set_input_state(True)
