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

            msg_container.grid(
                row=len(self.conversation_history) - 1,
                column=0,
                sticky="ew",
                pady=(0, 12),
            )
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

            # Icône IA
            icon_label = self.create_label(
                center_frame,
                text="🤖",
                font=("Segoe UI", 16),
                fg_color=self.colors["bg_chat"],
                text_color=self.colors["accent"],
            )
            icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(1, 0))

            # Container pour le message
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

            # Vérifier si on a des caractères à afficher
            if self.typing_index < buffer_length:
                # 🔗 DÉTECTION ET TRAITEMENT DES LIENS MARKDOWN
                # Vérifier si on est au début d'un lien [titre](url)
                link_detected = self._detect_and_process_markdown_link()

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
                    self.root.after(5, self._smart_scroll_follow_animation)

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
                return

            # Récupérer le texte ACTUEL du widget (déjà coloré pendant l'animation)
            self.typing_widget.configure(state="normal")
            current_widget_text = self.typing_widget.get("1.0", "end-1c")

            # Mettre à jour l'historique avec le texte actuel du widget
            if self.conversation_history:
                self.conversation_history[-1]["text"] = current_widget_text

            # IMPORTANT: S'assurer que typing_text est défini pour le formatage
            self.typing_text = current_widget_text

            # Réinitialiser les positions pour forcer un formatage complet
            # Mais ne PAS réinitialiser _pending_links qui contient les liens déjà détectés
            if hasattr(self, "_formatted_positions"):
                self._formatted_positions.clear()
            if hasattr(self, "_formatted_bold_contents"):
                self._formatted_bold_contents.clear()

            # ============================================================
            # 🎨 PAS DE RÉ-ANALYSE DES BLOCS DE CODE
            # La coloration a déjà été faite pendant l'animation
            # On applique juste le formatage Markdown (gras, italique, etc.)
            # ============================================================

            print(
                f"[DEBUG] _finish_streaming: Formatage final sur {len(current_widget_text)} caractères (coloration déjà faite)"
            )

            # Vérifier si les tableaux sont déjà formatés (présence de bordures)
            tables_already_formatted = any(
                c in current_widget_text for c in "┌┬┐│├┼┤└┴┘─"
            )

            if tables_already_formatted:
                print(
                    "[DEBUG] _finish_streaming: Tableaux déjà formatés, pas de reconstruction"
                )
                # Les tableaux sont déjà formatés pendant l'animation
                # On applique juste le formatage Markdown sans détruire le widget
                self._apply_unified_progressive_formatting(self.typing_widget)
            else:
                print(
                    "[DEBUG] _finish_streaming: Tableaux non formatés, formatage nécessaire"
                )
                # Pré-analyser les tableaux
                self._table_blocks = self._preanalyze_markdown_tables(
                    current_widget_text
                )

                # Formater les tableaux Markdown (reconstruit le widget)
                self._format_markdown_tables_in_widget(
                    self.typing_widget, current_widget_text
                )

                # Formatage unifié (gras, italique, code inline, etc.)
                self._apply_unified_progressive_formatting(self.typing_widget)

            # Les liens ont déjà été collectés pendant l'animation dans _pending_links
            # Ne PAS les rescanner ni les effacer
            print(
                f"[DEBUG] _finish_streaming: {len(self._pending_links) if hasattr(self, '_pending_links') else 0} liens dans _pending_links"
            )

            # Convertir les liens en cliquables
            self._convert_temp_links_to_clickable(self.typing_widget)

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

            # STOCKER les valeurs de feedback pour le RLHF AVANT d'afficher le timestamp
            if hasattr(self, "current_message_container") and self.current_message_container is not None:
                self.current_message_container.feedback_query = getattr(self, "_last_user_query", None)
                self.current_message_container.feedback_response = current_widget_text
                print(f"[DEBUG STOCKAGE FEEDBACK] Query: {getattr(self, '_last_user_query', 'None')[:50]}...")
                print(f"[DEBUG STOCKAGE FEEDBACK] Response: {current_widget_text[:50]}...")

            # Afficher le timestamp
            self._show_timestamp_for_current_message()

            # Réactiver la saisie
            self.set_input_state(True)

            # Scroll final
            self.root.after(200, self._final_smooth_scroll_to_bottom)

            # Nettoyage des variables streaming
            self._streaming_mode = False
            self._streaming_buffer = ""
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
                f"✅ [STREAM] Animation terminée: {len(current_widget_text)} caractères"
            )

        except Exception as e:
            print(f"❌ [STREAM] Erreur finalisation: {e}")
            traceback.print_exc()
            self.set_input_state(True)
