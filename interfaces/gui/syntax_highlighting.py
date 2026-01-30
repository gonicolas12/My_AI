"""Syntax highlighting mixin for ModernAIGUI."""

import keyword
import re

try:
    from pygments import lex
    from pygments.lexers.python import PythonLexer

    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False
    PythonLexer = None


class SyntaxHighlightingMixin:
    """Syntax highlighting helpers for multiple languages."""

    def _configure_formatting_tags(self, text_widget):
        """Configure tous les tags de formatage pour l'animation avec coloration Python COMPLÈTE"""
        base_font = ("Segoe UI", 12)

        # 🔧 CONFIGURATION IDENTIQUE à insert_formatted_text_tkinter
        text_widget.tag_configure(
            "bold",
            font=("Segoe UI", 12, "bold"),
            foreground=self.colors["text_primary"],
        )

        # 🔧 TITRES MARKDOWN avec tailles progressives
        text_widget.tag_configure(
            "title1",
            font=("Segoe UI", 16, "bold"),
            foreground=self.colors["text_primary"],
        )
        text_widget.tag_configure(
            "title2",
            font=("Segoe UI", 14, "bold"),
            foreground=self.colors["text_primary"],
        )
        text_widget.tag_configure(
            "title3",
            font=("Segoe UI", 13, "bold"),
            foreground=self.colors["text_primary"],
        )
        text_widget.tag_configure(
            "title4",
            font=("Segoe UI", 12, "bold"),
            foreground=self.colors["text_primary"],
        )
        text_widget.tag_configure(
            "title5",
            font=("Segoe UI", 12, "bold"),
            foreground=self.colors["text_primary"],
        )

        text_widget.tag_configure(
            "italic",
            font=("Segoe UI", 12, "italic"),
            foreground=self.colors["text_primary"],
        )
        text_widget.tag_configure("mono", font=("Consolas", 11), foreground="#f8f8f2")

        # 🔧 DOCSTRING - ESSENTIEL pour le code Python
        text_widget.tag_configure(
            "docstring", font=("Consolas", 11, "italic"), foreground="#ff8c00"
        )

        text_widget.tag_configure(
            "normal", font=base_font, foreground=self.colors["text_primary"]
        )
        text_widget.tag_configure(
            "link", foreground="#3b82f6", underline=1, font=base_font
        )

        # Tag pour placeholder de code
        text_widget.tag_configure(
            "code_placeholder", font=base_font, foreground=self.colors["text_primary"]
        )

        # 🔧 PYTHON COMPLET - Couleurs VS Code EXACTES

        # Keywords - BLEU VS Code
        python_keyword_tags = [
            "Token.Keyword",
            "Token.Keyword.Constant",
            "Token.Keyword.Declaration",
            "Token.Keyword.Namespace",
            "Token.Keyword.Pseudo",
            "Token.Keyword.Reserved",
        ]
        for tag in python_keyword_tags:
            text_widget.tag_configure(
                tag, foreground="#569cd6", font=("Consolas", 11, "bold")
            )

        text_widget.tag_configure(
            "Token.Keyword.Type", foreground="#4ec9b0", font=("Consolas", 11, "bold")
        )

        # Strings - ORANGE-BRUN VS Code
        string_tags = [
            "Token.Literal.String",
            "Token.Literal.String.Double",
            "Token.Literal.String.Single",
            "Token.String",
            "Token.String.Double",
            "Token.String.Single",
        ]
        for tag in string_tags:
            text_widget.tag_configure(tag, foreground="#ce9178", font=("Consolas", 11))

        # Commentaires - VERT VS Code
        comment_tags = [
            "Token.Comment",
            "Token.Comment.Single",
            "Token.Comment.Multiline",
        ]
        for tag in comment_tags:
            text_widget.tag_configure(
                tag, foreground="#6a9955", font=("Consolas", 11, "italic")
            )

        # Fonctions et classes - JAUNE VS Code
        text_widget.tag_configure(
            "Token.Name.Function", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "Token.Name.Function.Magic", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "Token.Name.Class", foreground="#4ec9b0", font=("Consolas", 11, "bold")
        )

        # Builtins - JAUNE VS Code
        text_widget.tag_configure(
            "Token.Name.Builtin", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "Token.Name.Builtin.Pseudo", foreground="#dcdcaa", font=("Consolas", 11)
        )

        # Nombres - VERT CLAIR VS Code
        number_tags = [
            "Token.Literal.Number",
            "Token.Literal.Number.Integer",
            "Token.Literal.Number.Float",
            "Token.Number",
            "Token.Number.Integer",
            "Token.Number.Float",
        ]
        for tag in number_tags:
            text_widget.tag_configure(tag, foreground="#b5cea8", font=("Consolas", 11))

        # Opérateurs - BLANC VS Code
        text_widget.tag_configure(
            "Token.Operator", foreground="#d4d4d4", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "Token.Punctuation", foreground="#d4d4d4", font=("Consolas", 11)
        )

        # Variables et noms - BLEU CLAIR VS Code
        name_tags = ["Token.Name", "Token.Name.Variable", "Token.Name.Attribute"]
        for tag in name_tags:
            text_widget.tag_configure(tag, foreground="#9cdcfe", font=("Consolas", 11))

        # Constantes spéciales - BLEU VS Code
        text_widget.tag_configure(
            "Token.Name.Constant", foreground="#569cd6", font=("Consolas", 11, "bold")
        )

        # AJOUT : Tags pour les blocs de code
        text_widget.tag_configure(
            "code_block",
            font=("Consolas", 11),
            foreground="#d4d4d4",
        )

        # === JAVASCRIPT - Couleurs VS Code ===
        text_widget.tag_configure(
            "js_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "js_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "js_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "js_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "js_function", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "js_variable", foreground="#9cdcfe", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "js_operator", foreground="#d4d4d4", font=("Consolas", 11)
        )

        # === CSS - Couleurs VS Code ===
        text_widget.tag_configure(
            "css_selector", foreground="#d7ba7d", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "css_property", foreground="#9cdcfe", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "css_value", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "css_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "css_unit", foreground="#b5cea8", font=("Consolas", 11)
        )

        # === HTML - Couleurs VS Code ===
        text_widget.tag_configure(
            "html_tag", foreground="#569cd6", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "html_attribute", foreground="#9cdcfe", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "html_value", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "html_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )

        # === BASH - Couleurs VS Code ===
        text_widget.tag_configure(
            "bash_command", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "bash_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "bash_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "bash_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "bash_variable", foreground="#9cdcfe", font=("Consolas", 11)
        )

        # === SQL - Couleurs VS Code ===
        text_widget.tag_configure(
            "sql_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "sql_function", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "sql_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "sql_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "sql_number", foreground="#b5cea8", font=("Consolas", 11)
        )

        # === JAVA - Couleurs VS Code ===
        text_widget.tag_configure(
            "java_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "java_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "java_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "java_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "java_class", foreground="#4ec9b0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "java_method", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "java_annotation", foreground="#dcdcaa", font=("Consolas", 11)
        )

        # === C/C++ - Couleurs VS Code ===
        text_widget.tag_configure(
            "cpp_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "cpp_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "cpp_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "cpp_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "cpp_preprocessor", foreground="#c586c0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "cpp_type", foreground="#4ec9b0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "cpp_function", foreground="#dcdcaa", font=("Consolas", 11)
        )

        # === C - Couleurs VS Code (mêmes couleurs que C++) ===
        text_widget.tag_configure(
            "c_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "c_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "c_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "c_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "c_preprocessor", foreground="#c586c0", font=("Consolas", 11)
        )
        text_widget.tag_configure("c_type", foreground="#4ec9b0", font=("Consolas", 11))
        text_widget.tag_configure(
            "c_function", foreground="#dcdcaa", font=("Consolas", 11)
        )

        # === C# - Couleurs VS Code ===
        text_widget.tag_configure(
            "csharp_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "csharp_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "csharp_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "csharp_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "csharp_class", foreground="#4ec9b0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "csharp_method", foreground="#dcdcaa", font=("Consolas", 11)
        )

        # === Go - Couleurs VS Code ===
        text_widget.tag_configure(
            "go_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "go_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "go_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "go_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "go_type", foreground="#4ec9b0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "go_function", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "go_package", foreground="#c586c0", font=("Consolas", 11)
        )

        # === Ruby - Couleurs VS Code ===
        text_widget.tag_configure(
            "ruby_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "ruby_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "ruby_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "ruby_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "ruby_symbol", foreground="#d7ba7d", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "ruby_method", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "ruby_class", foreground="#4ec9b0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "ruby_variable", foreground="#9cdcfe", font=("Consolas", 11)
        )

        # === Swift - Couleurs VS Code ===
        text_widget.tag_configure(
            "swift_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "swift_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "swift_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "swift_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "swift_type", foreground="#4ec9b0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "swift_function", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "swift_attribute", foreground="#c586c0", font=("Consolas", 11)
        )

        # === PHP - Couleurs VS Code ===
        text_widget.tag_configure(
            "php_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "php_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "php_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "php_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "php_variable", foreground="#9cdcfe", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "php_function", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "php_tag", foreground="#569cd6", font=("Consolas", 11)
        )

        # === Perl - Couleurs VS Code ===
        text_widget.tag_configure(
            "perl_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "perl_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "perl_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "perl_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "perl_variable", foreground="#9cdcfe", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "perl_regex", foreground="#d16969", font=("Consolas", 11)
        )

        # === Rust - Couleurs VS Code ===
        text_widget.tag_configure(
            "rust_keyword", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "rust_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "rust_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )
        text_widget.tag_configure(
            "rust_number", foreground="#b5cea8", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "rust_type", foreground="#4ec9b0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "rust_function", foreground="#dcdcaa", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "rust_macro", foreground="#c586c0", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "rust_lifetime", foreground="#569cd6", font=("Consolas", 11, "italic")
        )

        # === Dockerfile - Couleurs VS Code ===
        text_widget.tag_configure(
            "dockerfile_instruction", foreground="#569cd6", font=("Consolas", 11, "bold")
        )
        text_widget.tag_configure(
            "dockerfile_string", foreground="#ce9178", font=("Consolas", 11)
        )
        text_widget.tag_configure(
            "dockerfile_comment", foreground="#6a9955", font=("Consolas", 11, "italic")
        )

        # Tag caché pour les marqueurs ```
        text_widget.tag_configure("hidden", elide=True, font=("Consolas", 1))

        print(
            "✅ Tags de coloration Python/JS/TS/CSS/HTML/Bash/SQL/Java/C++/C/C#/Go/Ruby/Swift/PHP/Perl/Rust/Dockerfile configurés pour l'animation"
        )

    def _preanalyze_code_blocks(self, text):
        """Pré-analyse les blocs de code pour la coloration en temps réel"""
        code_blocks_map = {}  # Position -> (language, token_type)

        # Pattern pour détecter les blocs de code avec langage
        # CORRECTION: Capturer aussi les + pour c++, et # pour c#
        code_block_pattern = r"```([\w+#-]+)?\n?(.*?)```"

        matches_found = list(re.finditer(code_block_pattern, text, re.DOTALL))
        print(
            f"[DEBUG] _preanalyze_code_blocks: {len(matches_found)} blocs de code trouvés dans le texte"
        )

        for match in matches_found:
            language = (match.group(1) or "text").lower()
            code_content = match.group(2).strip() if match.group(2) else ""

            print(
                f"[DEBUG] Bloc de code détecté: langage='{language}', longueur={len(code_content)}, position={match.start()}-{match.end()}"
            )

            if not code_content:
                print("[DEBUG] Bloc ignoré car contenu vide")
                continue

            # Marquer la zone des backticks d'ouverture + newline comme "hidden"
            opening_start = match.start()
            # Calculer la fin de l'ouverture (```language\n)
            opening_text = f"```{match.group(1) or ''}"
            opening_end = match.start() + len(opening_text)

            # Chercher le \n après ```language
            newline_pos = text.find("\n", opening_end)
            if newline_pos != -1 and newline_pos < match.end() - 3:
                # Inclure le \n dans le hidden
                opening_end = newline_pos + 1

            # Marquer tout de opening_start à opening_end comme hidden
            for pos in range(opening_start, opening_end):
                if pos < len(text):
                    code_blocks_map[pos] = (language, "code_block_marker")

            # Le code commence après le \n
            code_start = opening_end

            # Calculer la vraie position de fin du code (avant le ``` de fermeture)
            code_end = match.end() - 3

            # Chercher le \n avant les ``` de fermeture pour le masquer aussi
            if code_end > 0 and text[code_end - 1] == "\n":
                code_end -= 1

            # Obtenir le vrai contenu du code SANS strip pour garder les positions correctes
            raw_code_content = text[code_start:code_end]

            # Masquer le \n avant les ``` de fermeture s'il existe
            if code_end < match.end() - 3:
                for pos in range(code_end, match.end() - 3):
                    code_blocks_map[pos] = (language, "code_block_marker")

            if language == "python":
                self._analyze_python_tokens(
                    raw_code_content, code_start, code_blocks_map
                )
            elif language in ["javascript", "js"]:
                self._analyze_javascript_tokens(
                    raw_code_content, code_start, code_blocks_map
                )
            elif language == "css":
                self._analyze_css_tokens(raw_code_content, code_start, code_blocks_map)
            elif language in ["html", "xml"]:
                self._analyze_html_tokens(raw_code_content, code_start, code_blocks_map)
            elif language in ["bash", "shell", "sh"]:
                self._analyze_bash_tokens(raw_code_content, code_start, code_blocks_map)
            elif language in ["sql", "mysql", "postgresql", "sqlite"]:
                self._analyze_sql_tokens(raw_code_content, code_start, code_blocks_map)
            elif language == "java":
                self._analyze_java_tokens(raw_code_content, code_start, code_blocks_map)
            elif language in ["c", "cpp", "c++", "cxx"]:
                self._analyze_cpp_tokens(
                    raw_code_content, code_start, code_blocks_map, language
                )
            elif language in ["csharp", "cs", "c#"]:
                self._analyze_csharp_tokens(
                    raw_code_content, code_start, code_blocks_map
                )
            elif language in ["go", "golang"]:
                self._analyze_go_tokens(raw_code_content, code_start, code_blocks_map)
            elif language in ["ruby", "rb"]:
                self._analyze_ruby_tokens(raw_code_content, code_start, code_blocks_map)
            elif language == "swift":
                self._analyze_swift_tokens(
                    raw_code_content, code_start, code_blocks_map
                )
            elif language == "php":
                self._analyze_php_tokens(raw_code_content, code_start, code_blocks_map)
            elif language in ["perl", "pl"]:
                self._analyze_perl_tokens(raw_code_content, code_start, code_blocks_map)
            elif language in ["rust", "rs"]:
                self._analyze_rust_tokens(raw_code_content, code_start, code_blocks_map)
            else:
                # Code générique
                for i in range(len(raw_code_content)):
                    pos = code_start + i
                    code_blocks_map[pos] = (language, "code_block")

            # Marquer la zone des backticks de fermeture comme "hidden"
            closing_start = match.end() - 3
            for pos in range(closing_start, match.end()):
                if pos < len(text):
                    code_blocks_map[pos] = (language, "code_block_marker")

        print(
            f"[DEBUG] _preanalyze_code_blocks: {len(code_blocks_map)} positions mappées au total"
        )

        # Debug: afficher les types de tokens trouvés par langage
        token_types_by_lang = {}
        for pos, (lang, token_type) in code_blocks_map.items():
            if lang not in token_types_by_lang:
                token_types_by_lang[lang] = set()
            token_types_by_lang[lang].add(token_type)
        print(
            f"[DEBUG] Types de tokens par langage: {dict((k, list(v)) for k, v in token_types_by_lang.items())}"
        )

        return code_blocks_map

    def _analyze_python_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Python pour la coloration en temps réel avec couleurs VS Code"""
        try:
            lexer = PythonLexer()
            current_pos = start_offset
            tokens_added = 0

            for token_type, value in lex(code, lexer):
                # Convertir le type de token Pygments en tag configuré
                tag = self._pygments_token_to_tag(token_type)

                for i in range(len(value)):
                    pos = current_pos + i
                    code_map[pos] = ("python", tag)
                    tokens_added += 1
                current_pos += len(value)

            print(
                f"[DEBUG] _analyze_python_tokens: {tokens_added} tokens ajoutés (offset {start_offset})"
            )

        except Exception as e:
            print(f"[DEBUG] Erreur Pygments: {e}, utilisation du fallback")
            # Fallback sans Pygments
            self._analyze_python_simple(code, start_offset, code_map)

    def _pygments_token_to_tag(self, token_type):
        """Convertit un token Pygments en tag tkinter configuré avec couleurs VS Code"""
        token_str = str(token_type)

        # Mapping des tokens Pygments vers les tags configurés
        # Keywords (bleu #569cd6)
        if "Keyword" in token_str:
            return "Token.Keyword"

        # Strings (orange-brun #ce9178)
        if "String" in token_str or "Literal.String" in token_str:
            return "Token.Literal.String"

        # Comments (vert #6a9955)
        if "Comment" in token_str:
            return "Token.Comment.Single"

        # Numbers (vert clair #b5cea8)
        if "Number" in token_str or "Literal.Number" in token_str:
            return "Token.Literal.Number"

        # Functions (jaune #dcdcaa)
        if "Name.Function" in token_str:
            return "Token.Name.Function"

        # Classes (cyan #4ec9b0)
        if "Name.Class" in token_str:
            return "Token.Name.Class"

        # Builtins (jaune #dcdcaa)
        if "Name.Builtin" in token_str:
            return "Token.Name.Builtin"

        # Decorators (jaune #dcdcaa)
        if "Name.Decorator" in token_str or "Decorator" in token_str:
            return "Token.Name.Function"

        # Operators (blanc #d4d4d4)
        if "Operator" in token_str:
            return "Token.Operator"

        # Punctuation (blanc #d4d4d4)
        if "Punctuation" in token_str:
            return "Token.Punctuation"

        # Variables/Names (bleu clair #9cdcfe)
        if "Name" in token_str:
            return "Token.Name"

        # Text/Whitespace - utiliser le style code_block par défaut
        if "Text" in token_str or "Whitespace" in token_str:
            return "code_block"

        # Par défaut, utiliser code_block
        return "code_block"

    def _analyze_python_simple(self, code, start_offset, code_map):
        """Analyse Python simple sans Pygments"""
        keywords = set(keyword.kwlist)
        tokens_added = 0

        # Pattern pour identifier différents éléments
        token_pattern = r'''
            (#.*$)|                      # Commentaires
            (""".*?""")|                 # Docstrings triple quotes
            ("(?:[^"\\]|\\.)*")|         # Chaînes double quotes
            ('(?:[^'\\]|\\.)*')|         # Chaînes simple quotes
            (\b\d+\.?\d*\b)|             # Nombres
            (\b[a-zA-Z_]\w*\b)|          # Identifiants
            ([+\-*/%=<>!&|^~]|//|\*\*|<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=|==|!=|<=|>=|and|or|not|\+=|-=)  # Opérateurs
        '''

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line, re.VERBOSE):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "Token.Comment.Single"
                elif match.group(2) or match.group(3) or match.group(4):  # Chaînes
                    tag = "Token.Literal.String"
                elif match.group(5):  # Nombres
                    tag = "Token.Literal.Number"
                elif match.group(6):  # Identifiants
                    if value in keywords:
                        tag = "Token.Keyword"
                    else:
                        tag = "Token.Name"
                else:  # Opérateurs
                    tag = "Token.Operator"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("python", tag)
                    tokens_added += 1

            current_pos += len(line) + 1  # +1 pour le \n

        print(f"[DEBUG] _analyze_python_simple: {tokens_added} tokens ajoutés")

    def _analyze_javascript_tokens(self, code, start_offset, code_map):
        """Analyse les tokens JavaScript pour la coloration en temps réel"""
        js_keywords = {
            "var",
            "let",
            "const",
            "function",
            "return",
            "if",
            "else",
            "for",
            "while",
            "do",
            "switch",
            "case",
            "default",
            "break",
            "continue",
            "try",
            "catch",
            "finally",
            "throw",
            "new",
            "this",
            "super",
            "class",
            "extends",
            "import",
            "export",
            "from",
            "async",
            "await",
            "yield",
            "typeof",
            "instanceof",
            "in",
            "of",
            "true",
            "false",
            "null",
            "undefined",
        }

        # Pattern pour identifier différents éléments JS - sans mode VERBOSE
        token_pattern = r'(//.*$)|(/\*.*?\*/)|("(?:[^"\\]|\\.)*")|(\x27(?:[^\x27\\]|\\.)*\x27)|(`(?:[^`\\]|\\.)*`)|(\b\d+\.?\d*\b)|(\b[a-zA-Z_$]\w*\b)|([+\-*/%=<>!&|^~]+)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1) or match.group(2):  # Commentaires
                    tag = "js_comment"
                elif match.group(3) or match.group(4) or match.group(5):  # Chaînes
                    tag = "js_string"
                elif match.group(6):  # Nombres
                    tag = "js_number"
                elif match.group(7):  # Identifiants
                    if value in js_keywords:
                        tag = "js_keyword"
                    else:
                        tag = "js_variable"
                else:  # Opérateurs
                    tag = "js_operator"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("javascript", tag)

            current_pos += len(line) + 1

        print(
            f"[DEBUG] _analyze_javascript_tokens: {len([k for k in code_map if code_map.get(k, ('', ''))[0] == 'javascript'])} tokens ajoutés (offset {start_offset})"
        )

    def _analyze_css_tokens(self, code, start_offset, code_map):
        """Analyse les tokens CSS pour la coloration en temps réel"""
        # Pattern pour CSS - sans mode VERBOSE pour éviter les problèmes avec #
        token_pattern = r"(/\*.*?\*/)|(\#[a-fA-F0-9]{3,8}\b)|(\d+\.?\d*(px|em|rem|%|vh|vw|pt)?)|([a-zA-Z-]+)\s*:|([\.#]?[a-zA-Z_-][\w-]*)|([{}:;,])"

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "css_comment"
                elif match.group(2):  # Couleur hex
                    tag = "css_value"
                elif match.group(3):  # Nombre
                    tag = "css_unit"
                elif match.group(5):  # Propriété
                    tag = "css_property"
                elif match.group(6):  # Sélecteur
                    tag = "css_selector"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("css", tag)

            current_pos += len(line) + 1

        print(
            f"[DEBUG] _analyze_css_tokens: tokens CSS ajoutés (offset {start_offset})"
        )

    def _analyze_html_tokens(self, code, start_offset, code_map):
        """Analyse les tokens HTML pour la coloration en temps réel"""
        # Pattern amélioré pour HTML - capture séparément les différents éléments
        # Groupe 1: Commentaires <!-- ... -->
        # Groupe 2: Tags fermants </tag> ou tags ouvrants <tag
        # Groupe 3: Attributs name= (sans le =)
        # Groupe 4: Valeurs entre guillemets "..." ou '...'
        # Groupe 5: Fermeture de tag > ou />
        token_pattern = r'(<!--[\s\S]*?-->)|(</?[a-zA-Z][a-zA-Z0-9:-]*)|([a-zA-Z_:][a-zA-Z0-9_:.-]*)(?==)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')|(/?>)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line, re.DOTALL):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "html_comment"
                elif match.group(2):  # Tag
                    tag = "html_tag"
                elif match.group(3):  # Attribut (nom avant le =)
                    tag = "html_attribute"
                elif match.group(4):  # Valeur entre guillemets
                    tag = "html_value"
                elif match.group(5):  # Fermeture de tag
                    tag = "html_tag"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("html", tag)

            current_pos += len(line) + 1

        print(
            f"[DEBUG] _analyze_html_tokens: tokens HTML ajoutés (offset {start_offset})"
        )

    def _analyze_bash_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Bash pour la coloration en temps réel"""
        bash_keywords = {
            "if",
            "then",
            "else",
            "elif",
            "fi",
            "for",
            "while",
            "do",
            "done",
            "case",
            "esac",
            "function",
            "return",
            "exit",
            "export",
            "local",
            "in",
            "until",
            "select",
            "break",
            "continue",
        }
        bash_commands = {
            "echo",
            "cd",
            "ls",
            "cat",
            "grep",
            "sed",
            "awk",
            "find",
            "chmod",
            "chown",
            "mkdir",
            "rm",
            "cp",
            "mv",
            "touch",
            "pwd",
            "source",
            "sudo",
            "apt",
            "pip",
            "npm",
            "git",
            "docker",
            "python",
            "node",
        }

        # Pattern sans mode VERBOSE pour éviter les problèmes avec #
        token_pattern = r'(\#.*$)|("(?:[^"\\]|\\.)*"|\'[^\']*\')|(\$\{?[a-zA-Z_]\w*\}?)|(\b[a-zA-Z_]\w*\b)|([|&;<>])'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "bash_comment"
                elif match.group(2):  # Chaîne
                    tag = "bash_string"
                elif match.group(3):  # Variable
                    tag = "bash_variable"
                elif match.group(4):  # Mot
                    if value in bash_keywords:
                        tag = "bash_keyword"
                    elif value in bash_commands:
                        tag = "bash_command"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("bash", tag)

            current_pos += len(line) + 1

    def _analyze_sql_tokens(self, code, start_offset, code_map):
        """Analyse les tokens SQL pour la coloration en temps réel"""
        sql_keywords = {
            "SELECT",
            "FROM",
            "WHERE",
            "AND",
            "OR",
            "NOT",
            "IN",
            "LIKE",
            "ORDER",
            "BY",
            "GROUP",
            "HAVING",
            "JOIN",
            "LEFT",
            "RIGHT",
            "INNER",
            "OUTER",
            "ON",
            "AS",
            "INSERT",
            "INTO",
            "VALUES",
            "UPDATE",
            "SET",
            "DELETE",
            "CREATE",
            "TABLE",
            "DROP",
            "ALTER",
            "INDEX",
            "VIEW",
            "DISTINCT",
            "LIMIT",
            "OFFSET",
            "UNION",
            "ALL",
            "NULL",
            "IS",
            "ASC",
            "DESC",
            "PRIMARY",
            "KEY",
            "FOREIGN",
            "REFERENCES",
            "CONSTRAINT",
        }
        sql_functions = {
            "COUNT",
            "SUM",
            "AVG",
            "MIN",
            "MAX",
            "CONCAT",
            "SUBSTRING",
            "UPPER",
            "LOWER",
            "TRIM",
            "COALESCE",
            "IFNULL",
            "CAST",
            "CONVERT",
        }

        # Pattern SQL - sans mode VERBOSE
        token_pattern = r"(--.*$|/\*.*?\*/)|(\x27(?:[^\x27\\]|\\.)*\x27)|(\b\d+\.?\d*\b)|(\b[a-zA-Z_]\w*\b)"

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line, re.IGNORECASE):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "sql_comment"
                elif match.group(2):  # Chaîne
                    tag = "sql_string"
                elif match.group(3):  # Nombre
                    tag = "sql_number"
                elif match.group(4):  # Mot
                    upper_val = value.upper()
                    if upper_val in sql_keywords:
                        tag = "sql_keyword"
                    elif upper_val in sql_functions:
                        tag = "sql_function"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("sql", tag)

            current_pos += len(line) + 1

    def _analyze_java_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Java pour la coloration en temps réel"""
        java_keywords = {
            "abstract",
            "assert",
            "boolean",
            "break",
            "byte",
            "case",
            "catch",
            "char",
            "class",
            "const",
            "continue",
            "default",
            "do",
            "double",
            "else",
            "enum",
            "extends",
            "final",
            "finally",
            "float",
            "for",
            "goto",
            "if",
            "implements",
            "import",
            "instanceof",
            "int",
            "interface",
            "long",
            "native",
            "new",
            "package",
            "private",
            "protected",
            "public",
            "return",
            "short",
            "static",
            "strictfp",
            "super",
            "switch",
            "synchronized",
            "this",
            "throw",
            "throws",
            "transient",
            "try",
            "void",
            "volatile",
            "while",
            "true",
            "false",
            "null",
        }
        java_types = {
            "String",
            "Integer",
            "Boolean",
            "Double",
            "Float",
            "Long",
            "Short",
            "Byte",
            "Character",
            "Object",
            "List",
            "ArrayList",
            "HashMap",
            "Map",
            "Set",
            "HashSet",
            "Exception",
            "System",
            "Math",
            "Arrays",
        }

        token_pattern = r'(//.*$|/\*.*?\*/)|("(?:[^"\\]|\\.)*")|(\b\d+\.?\d*[fFdDlL]?\b)|(@\w+)|(\b[a-zA-Z_]\w*\b)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "java_comment"
                elif match.group(2):  # Chaîne
                    tag = "java_string"
                elif match.group(3):  # Nombre
                    tag = "java_number"
                elif match.group(4):  # Annotation
                    tag = "java_annotation"
                elif match.group(5):  # Mot
                    if value in java_keywords:
                        tag = "java_keyword"
                    elif value in java_types or value[0].isupper():
                        tag = "java_class"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("java", tag)

            current_pos += len(line) + 1

    def _analyze_cpp_tokens(self, code, start_offset, code_map, language="cpp"):
        """Analyse les tokens C/C++ pour la coloration en temps réel"""
        cpp_keywords = {
            "auto",
            "break",
            "case",
            "catch",
            "class",
            "const",
            "continue",
            "default",
            "delete",
            "do",
            "else",
            "enum",
            "explicit",
            "export",
            "extern",
            "false",
            "for",
            "friend",
            "goto",
            "if",
            "inline",
            "mutable",
            "namespace",
            "new",
            "operator",
            "private",
            "protected",
            "public",
            "register",
            "return",
            "sizeof",
            "static",
            "struct",
            "switch",
            "template",
            "this",
            "throw",
            "true",
            "try",
            "typedef",
            "typeid",
            "typename",
            "union",
            "unsigned",
            "using",
            "virtual",
            "void",
            "volatile",
            "while",
            "nullptr",
            "constexpr",
            "noexcept",
            "override",
            "final",
        }
        cpp_types = {
            "int",
            "char",
            "float",
            "double",
            "bool",
            "long",
            "short",
            "unsigned",
            "signed",
            "size_t",
            "string",
            "vector",
            "map",
            "set",
            "list",
            "pair",
            "unique_ptr",
            "shared_ptr",
            "weak_ptr",
            "array",
            "deque",
            "stack",
            "queue",
        }

        token_pattern = r'(//.*$|/\*.*?\*/)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')|(\b\d+\.?\d*[fFlLuU]*\b)|(\#\w+)|(\b[a-zA-Z_]\w*\b)'

        # Normaliser le nom de langue pour les tags (c ou cpp)
        tag_lang = "c" if language == "c" else "cpp"

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = f"{tag_lang}_comment"
                elif match.group(2):  # Chaîne/Char
                    tag = f"{tag_lang}_string"
                elif match.group(3):  # Nombre
                    tag = f"{tag_lang}_number"
                elif match.group(4):  # Préprocesseur
                    tag = f"{tag_lang}_preprocessor"
                elif match.group(5):  # Mot
                    if value in cpp_keywords:
                        tag = f"{tag_lang}_keyword"
                    elif value in cpp_types:
                        tag = f"{tag_lang}_type"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = (language, tag)

            current_pos += len(line) + 1

    def _analyze_csharp_tokens(self, code, start_offset, code_map):
        """Analyse les tokens C# pour la coloration en temps réel"""
        csharp_keywords = {
            "abstract",
            "as",
            "base",
            "bool",
            "break",
            "byte",
            "case",
            "catch",
            "char",
            "checked",
            "class",
            "const",
            "continue",
            "decimal",
            "default",
            "delegate",
            "do",
            "double",
            "else",
            "enum",
            "event",
            "explicit",
            "extern",
            "false",
            "finally",
            "fixed",
            "float",
            "for",
            "foreach",
            "goto",
            "if",
            "implicit",
            "in",
            "int",
            "interface",
            "internal",
            "is",
            "lock",
            "long",
            "namespace",
            "new",
            "null",
            "object",
            "operator",
            "out",
            "override",
            "params",
            "private",
            "protected",
            "public",
            "readonly",
            "ref",
            "return",
            "sbyte",
            "sealed",
            "short",
            "sizeof",
            "stackalloc",
            "static",
            "string",
            "struct",
            "switch",
            "this",
            "throw",
            "true",
            "try",
            "typeof",
            "uint",
            "ulong",
            "unchecked",
            "unsafe",
            "ushort",
            "using",
            "virtual",
            "void",
            "volatile",
            "while",
            "var",
            "async",
            "await",
            "dynamic",
            "nameof",
        }
        csharp_types = {
            "String",
            "Int32",
            "Int64",
            "Boolean",
            "Double",
            "Float",
            "Object",
            "List",
            "Dictionary",
            "Console",
            "Exception",
            "Task",
            "Action",
            "Func",
        }

        token_pattern = r'(//.*$|/\*.*?\*/)|("(?:[^"\\]|\\.)*"|@"[^"]*")|(\b\d+\.?\d*[fFdDmM]?\b)|(\b[a-zA-Z_]\w*\b)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "csharp_comment"
                elif match.group(2):  # Chaîne
                    tag = "csharp_string"
                elif match.group(3):  # Nombre
                    tag = "csharp_number"
                elif match.group(4):  # Mot
                    if value in csharp_keywords:
                        tag = "csharp_keyword"
                    elif value in csharp_types or value[0].isupper():
                        tag = "csharp_class"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("csharp", tag)

            current_pos += len(line) + 1

    def _analyze_go_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Go pour la coloration en temps réel"""
        go_keywords = {
            "break",
            "case",
            "chan",
            "const",
            "continue",
            "default",
            "defer",
            "else",
            "fallthrough",
            "for",
            "func",
            "go",
            "goto",
            "if",
            "import",
            "interface",
            "map",
            "package",
            "range",
            "return",
            "select",
            "struct",
            "switch",
            "type",
            "var",
            "true",
            "false",
            "nil",
            "iota",
        }
        go_types = {
            "bool",
            "byte",
            "complex64",
            "complex128",
            "error",
            "float32",
            "float64",
            "int",
            "int8",
            "int16",
            "int32",
            "int64",
            "rune",
            "string",
            "uint",
            "uint8",
            "uint16",
            "uint32",
            "uint64",
            "uintptr",
        }
        go_builtins = {
            "append",
            "cap",
            "close",
            "complex",
            "copy",
            "delete",
            "imag",
            "len",
            "make",
            "new",
            "panic",
            "print",
            "println",
            "real",
            "recover",
        }

        token_pattern = r'(//.*$|/\*.*?\*/)|("(?:[^"\\]|\\.)*"|`[^`]*`)|(\b\d+\.?\d*\b)|(\b[a-zA-Z_]\w*\b)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "go_comment"
                elif match.group(2):  # Chaîne
                    tag = "go_string"
                elif match.group(3):  # Nombre
                    tag = "go_number"
                elif match.group(4):  # Mot
                    if value in go_keywords:
                        tag = "go_keyword"
                    elif value in go_types:
                        tag = "go_type"
                    elif value in go_builtins:
                        tag = "go_function"
                    elif value in {"package", "import"}:
                        tag = "go_package"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("go", tag)

            current_pos += len(line) + 1

    def _analyze_ruby_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Ruby pour la coloration en temps réel"""
        ruby_keywords = {
            "alias",
            "and",
            "begin",
            "break",
            "case",
            "class",
            "def",
            "defined",
            "do",
            "else",
            "elsif",
            "end",
            "ensure",
            "false",
            "for",
            "if",
            "in",
            "module",
            "next",
            "nil",
            "not",
            "or",
            "redo",
            "rescue",
            "retry",
            "return",
            "self",
            "super",
            "then",
            "true",
            "undef",
            "unless",
            "until",
            "when",
            "while",
            "yield",
            "require",
            "include",
            "extend",
            "attr_accessor",
            "attr_reader",
            "attr_writer",
            "private",
            "protected",
            "public",
        }
        ruby_builtins = {
            "puts",
            "print",
            "gets",
            "chomp",
            "to_s",
            "to_i",
            "to_f",
            "to_a",
            "each",
            "map",
            "select",
            "reject",
            "reduce",
            "inject",
            "sort",
            "reverse",
        }

        token_pattern = r'(\#.*$)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')|(\b\d+\.?\d*\b)|(:\w+)|(@{1,2}\w+)|(\b[a-zA-Z_]\w*[!?]?\b)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "ruby_comment"
                elif match.group(2):  # Chaîne
                    tag = "ruby_string"
                elif match.group(3):  # Nombre
                    tag = "ruby_number"
                elif match.group(4):  # Symbol
                    tag = "ruby_symbol"
                elif match.group(5):  # Variable instance/classe
                    tag = "ruby_variable"
                elif match.group(6):  # Mot
                    if value in ruby_keywords:
                        tag = "ruby_keyword"
                    elif value in ruby_builtins:
                        tag = "ruby_method"
                    elif value[0].isupper():
                        tag = "ruby_class"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("ruby", tag)

            current_pos += len(line) + 1

    def _analyze_swift_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Swift pour la coloration en temps réel"""
        swift_keywords = {
            "associatedtype",
            "class",
            "deinit",
            "enum",
            "extension",
            "fileprivate",
            "func",
            "import",
            "init",
            "inout",
            "internal",
            "let",
            "open",
            "operator",
            "private",
            "protocol",
            "public",
            "rethrows",
            "static",
            "struct",
            "subscript",
            "typealias",
            "var",
            "break",
            "case",
            "continue",
            "default",
            "defer",
            "do",
            "else",
            "fallthrough",
            "for",
            "guard",
            "if",
            "in",
            "repeat",
            "return",
            "switch",
            "where",
            "while",
            "as",
            "catch",
            "is",
            "nil",
            "super",
            "self",
            "Self",
            "throw",
            "throws",
            "try",
            "true",
            "false",
            "async",
            "await",
        }
        swift_types = {
            "Any",
            "AnyObject",
            "Bool",
            "Character",
            "Double",
            "Float",
            "Int",
            "Int8",
            "Int16",
            "Int32",
            "Int64",
            "Never",
            "Optional",
            "String",
            "UInt",
            "UInt8",
            "UInt16",
            "UInt32",
            "UInt64",
            "Void",
            "Array",
            "Dictionary",
            "Set",
        }

        token_pattern = r'(//.*$|/\*.*?\*/)|("(?:[^"\\]|\\.)*")|(\b\d+\.?\d*\b)|(@\w+)|(\b[a-zA-Z_]\w*\b)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "swift_comment"
                elif match.group(2):  # Chaîne
                    tag = "swift_string"
                elif match.group(3):  # Nombre
                    tag = "swift_number"
                elif match.group(4):  # Attribut
                    tag = "swift_attribute"
                elif match.group(5):  # Mot
                    if value in swift_keywords:
                        tag = "swift_keyword"
                    elif value in swift_types or value[0].isupper():
                        tag = "swift_type"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("swift", tag)

            current_pos += len(line) + 1

    def _analyze_php_tokens(self, code, start_offset, code_map):
        """Analyse les tokens PHP pour la coloration en temps réel"""
        php_keywords = {
            "abstract",
            "and",
            "as",
            "break",
            "callable",
            "case",
            "catch",
            "class",
            "clone",
            "const",
            "continue",
            "declare",
            "default",
            "do",
            "else",
            "elseif",
            "enddeclare",
            "endfor",
            "endforeach",
            "endif",
            "endswitch",
            "endwhile",
            "extends",
            "final",
            "finally",
            "for",
            "foreach",
            "function",
            "global",
            "goto",
            "if",
            "implements",
            "include",
            "include_once",
            "instanceof",
            "insteadof",
            "interface",
            "namespace",
            "new",
            "or",
            "private",
            "protected",
            "public",
            "require",
            "require_once",
            "return",
            "static",
            "switch",
            "throw",
            "trait",
            "try",
            "use",
            "var",
            "while",
            "xor",
            "yield",
            "yield from",
            "true",
            "false",
            "null",
            "echo",
            "print",
        }
        php_builtins = {
            "array",
            "empty",
            "isset",
            "unset",
            "list",
            "die",
            "exit",
            "eval",
            "count",
            "strlen",
            "substr",
            "strpos",
            "str_replace",
            "explode",
            "implode",
        }

        token_pattern = r'(//.*$|\#.*$|/\*.*?\*/)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')|(\b\d+\.?\d*\b)|(<\?php|\?>)|(\$[a-zA-Z_]\w*)|(\b[a-zA-Z_]\w*\b)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "php_comment"
                elif match.group(2):  # Chaîne
                    tag = "php_string"
                elif match.group(3):  # Nombre
                    tag = "php_number"
                elif match.group(4):  # Tag PHP
                    tag = "php_tag"
                elif match.group(5):  # Variable
                    tag = "php_variable"
                elif match.group(6):  # Mot
                    if value.lower() in php_keywords:
                        tag = "php_keyword"
                    elif value.lower() in php_builtins:
                        tag = "php_function"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("php", tag)

            current_pos += len(line) + 1

    def _analyze_perl_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Perl pour la coloration en temps réel"""
        perl_keywords = {
            "my",
            "our",
            "local",
            "sub",
            "package",
            "use",
            "require",
            "no",
            "if",
            "elsif",
            "else",
            "unless",
            "while",
            "until",
            "for",
            "foreach",
            "do",
            "last",
            "next",
            "redo",
            "return",
            "goto",
            "die",
            "warn",
            "print",
            "say",
            "open",
            "close",
            "read",
            "write",
            "seek",
            "tell",
            "eof",
            "defined",
            "undef",
            "exists",
            "delete",
            "push",
            "pop",
            "shift",
            "unshift",
            "splice",
            "sort",
            "reverse",
            "keys",
            "values",
            "each",
            "length",
            "substr",
            "index",
            "rindex",
            "split",
            "join",
            "chomp",
            "chop",
            "lc",
            "uc",
            "scalar",
            "wantarray",
            "caller",
            "eval",
            "exec",
            "system",
            "fork",
            "wait",
            "exit",
        }

        token_pattern = r'(\#.*$)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')|(\b\d+\.?\d*\b)|([\$@%]\w+)|(/(?:[^/\\]|\\.)+/[gimsx]*)|(\b[a-zA-Z_]\w*\b)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "perl_comment"
                elif match.group(2):  # Chaîne
                    tag = "perl_string"
                elif match.group(3):  # Nombre
                    tag = "perl_number"
                elif match.group(4):  # Variable
                    tag = "perl_variable"
                elif match.group(5):  # Regex
                    tag = "perl_regex"
                elif match.group(6):  # Mot
                    if value in perl_keywords:
                        tag = "perl_keyword"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("perl", tag)

            current_pos += len(line) + 1

    def _analyze_rust_tokens(self, code, start_offset, code_map):
        """Analyse les tokens Rust pour la coloration en temps réel"""
        rust_keywords = {
            "as",
            "async",
            "await",
            "break",
            "const",
            "continue",
            "crate",
            "dyn",
            "else",
            "enum",
            "extern",
            "false",
            "fn",
            "for",
            "if",
            "impl",
            "in",
            "let",
            "loop",
            "match",
            "mod",
            "move",
            "mut",
            "pub",
            "ref",
            "return",
            "self",
            "Self",
            "static",
            "struct",
            "super",
            "trait",
            "true",
            "type",
            "unsafe",
            "use",
            "where",
            "while",
            "abstract",
            "become",
            "box",
            "do",
            "final",
            "macro",
            "override",
            "priv",
            "typeof",
            "unsized",
            "virtual",
            "yield",
        }
        rust_types = {
            "bool",
            "char",
            "str",
            "i8",
            "i16",
            "i32",
            "i64",
            "i128",
            "isize",
            "u8",
            "u16",
            "u32",
            "u64",
            "u128",
            "usize",
            "f32",
            "f64",
            "String",
            "Vec",
            "Option",
            "Result",
            "Box",
            "Rc",
            "Arc",
            "Cell",
            "RefCell",
            "HashMap",
            "HashSet",
            "BTreeMap",
            "BTreeSet",
            "VecDeque",
            "LinkedList",
        }

        token_pattern = r'(//.*$|/\*.*?\*/)|("(?:[^"\\]|\\.)*"|r#*"[^"]*"#*)|(\b\d+\.?\d*(?:_\d+)*(?:i8|i16|i32|i64|i128|isize|u8|u16|u32|u64|u128|usize|f32|f64)?\b)|(\'[a-zA-Z_]\w*)|(\b[a-zA-Z_]\w*!)|(\b[a-zA-Z_]\w*\b)'

        lines = code.split("\n")
        current_pos = start_offset

        for line in lines:
            for match in re.finditer(token_pattern, line):
                value = match.group(0)
                match_start = current_pos + match.start()

                if match.group(1):  # Commentaire
                    tag = "rust_comment"
                elif match.group(2):  # Chaîne
                    tag = "rust_string"
                elif match.group(3):  # Nombre
                    tag = "rust_number"
                elif match.group(4):  # Lifetime 'a
                    tag = "rust_lifetime"
                elif match.group(5):  # Macro println!
                    tag = "rust_macro"
                elif match.group(6):  # Mot
                    if value in rust_keywords:
                        tag = "rust_keyword"
                    elif value in rust_types or (
                        value[0].isupper() and not value.isupper()
                    ):
                        tag = "rust_type"
                    else:
                        tag = "code_block"
                else:
                    tag = "code_block"

                for i in range(len(value)):
                    pos = match_start + i
                    code_map[pos] = ("rust", tag)

            current_pos += len(line) + 1
