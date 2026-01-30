"""Markdown formatting mixin for ModernAIGUI."""

import json
import keyword
import os
import re
import traceback
import webbrowser

try:
    from pygments import lex
    from pygments.lexers.python import PythonLexer

    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False
    PythonLexer = None


class MarkdownFormattingMixin:
    """Markdown, tables, links, and code block formatting."""

    def _preanalyze_markdown_tables(self, text):
        """Pré-analyse les tableaux Markdown pour l'animation progressive"""
        tables = []  # Liste de dictionnaires avec infos sur chaque tableau

        lines = text.split("\n")
        i = 0
        char_pos = 0  # Position en caractères dans le texte

        while i < len(lines):
            line = lines[i]

            # Vérifier si c'est le début d'un tableau
            if "|" in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                separator_pattern = r"^\|?[\s\-:|\s]+\|?$"
                if re.match(separator_pattern, next_line.strip()) and "-" in next_line:
                    # C'est un tableau!
                    table_start_pos = char_pos
                    table_start_line = i
                    table_lines_info = []

                    # Collecter toutes les lignes du tableau
                    j = i
                    table_char_pos = char_pos
                    while j < len(lines) and "|" in lines[j]:
                        line_info = {
                            "line_num": j,
                            "start_pos": table_char_pos,
                            "end_pos": table_char_pos + len(lines[j]),
                            "content": lines[j],
                            "is_separator": j == i + 1,
                        }
                        table_lines_info.append(line_info)
                        table_char_pos += len(lines[j]) + 1  # +1 pour le \n
                        j += 1

                        # Vérifier si c'est un nouveau séparateur (nouveau tableau)
                        if (
                            j < len(lines)
                            and re.match(separator_pattern, lines[j].strip())
                            and "-" in lines[j]
                        ):
                            if j > i + 1:  # Pas le séparateur du tableau actuel
                                break

                    tables.append(
                        {
                            "start_line": table_start_line,
                            "end_line": j - 1,
                            "start_pos": table_start_pos,
                            "end_pos": table_char_pos - 1,
                            "lines": table_lines_info,
                        }
                    )

                    # Avancer après le tableau
                    char_pos = table_char_pos
                    i = j
                    continue

            char_pos += len(line) + 1  # +1 pour le \n
            i += 1

        return tables

    def _check_and_format_table_line(self, text_widget, current_pos):
        """Vérifie si on vient de terminer un tableau complet et le formate"""
        if not hasattr(self, "_table_blocks") or not self._table_blocks:
            return

        if not hasattr(self, "_formatted_tables"):
            self._formatted_tables = set()

        # Vérifier si on vient de terminer un tableau
        for table_idx, table in enumerate(self._table_blocks):
            if table_idx in self._formatted_tables:
                continue  # Déjà formaté

            # Vérifier si le tableau a ARRÊTÉ de grandir
            # On regarde si end_line a changé depuis le dernier appel
            prev_end_line = self._table_blocks_history.get(table_idx, -1)
            current_end_line = table["end_line"]

            # Mettre à jour l'historique
            self._table_blocks_history[table_idx] = current_end_line

            # Si c'est la première fois qu'on voit ce tableau, ne pas formater encore
            if prev_end_line == -1:
                continue

            # Si le tableau a grandi depuis le dernier appel, ne pas formater encore
            if current_end_line > prev_end_line:
                print(
                    f"[DEBUG] Tableau {table_idx} grandit encore : ligne {prev_end_line} -> {current_end_line}"
                )
                continue

            # Si on est ici, le tableau n'a PAS grandi depuis le dernier appel
            # Vérifier qu'on a dépassé la fin du tableau ET qu'il y a une ligne non-tableau après
            if current_pos >= table["end_pos"]:
                buffer_text = self._streaming_buffer[:current_pos]
                lines = buffer_text.split("\n")

                # Vérifier qu'on a au moins 1 ligne après le tableau
                lines_after_table = len(lines) - table["end_line"] - 1

                if lines_after_table >= 1:
                    # Vérifier que cette ligne ne contient pas de |
                    if table["end_line"] + 1 < len(lines):
                        first_line_after = lines[table["end_line"] + 1]
                        if "|" not in first_line_after:
                            # Le tableau est stable et terminé
                            self._formatted_tables.add(table_idx)
                            self._format_completed_table(text_widget, table)
                            break  # Un seul tableau à la fois

    def _format_completed_table(self, text_widget, table_info):
        """Formate un tableau complet dans le widget"""
        try:
            text_widget.configure(state="normal")

            # Récupérer le contenu actuel du widget
            content = text_widget.get("1.0", "end-1c")
            widget_lines = content.split("\n")

            # Extraire les lignes brutes du tableau depuis le texte original
            raw_table_lines = [
                line_info["content"] for line_info in table_info["lines"]
            ]

            if len(raw_table_lines) < 2:
                text_widget.configure(state="disabled")
                return

            # Trouver où se trouve ce tableau dans le widget actuel
            # Chercher la première ligne du tableau (header)
            header_content = raw_table_lines[0].strip()
            table_start_widget_line = None

            for idx, wline in enumerate(widget_lines):
                # Chercher une ligne qui contient | et correspond au header
                if "|" in wline and not any(c in wline for c in "┌┬┐│├┼┤└┴┘─"):
                    # Vérifier si c'est bien notre tableau en comparant le contenu
                    if self._lines_match(wline.strip(), header_content):
                        table_start_widget_line = idx
                        break

            if table_start_widget_line is None:
                text_widget.configure(state="disabled")
                return

            # Compter combien de lignes brutes consécutives avec | on a
            table_end_widget_line = table_start_widget_line
            for idx in range(table_start_widget_line, len(widget_lines)):
                if "|" in widget_lines[idx] and not any(
                    c in widget_lines[idx] for c in "┌┬┐│├┼┤└┴┘─"
                ):
                    table_end_widget_line = idx
                else:
                    break

            # Supprimer les lignes brutes du tableau
            start_line_tk = f"{table_start_widget_line + 1}.0"
            end_line_tk = f"{table_end_widget_line + 2}.0"
            text_widget.delete(start_line_tk, end_line_tk)

            # Positionner le curseur pour l'insertion
            text_widget.mark_set("insert", start_line_tk)

            # Insérer le tableau formaté
            self._insert_formatted_table(text_widget, raw_table_lines)

            text_widget.configure(state="disabled")

        except Exception as e:
            print(f"[DEBUG] Erreur formatage tableau: {e}")
            try:
                text_widget.configure(state="disabled")
            except Exception:
                pass

    def _lines_match(self, line1, line2):
        """Vérifie si deux lignes de tableau correspondent (même contenu de cellules)"""
        cells1 = self._parse_table_row(line1)
        cells2 = self._parse_table_row(line2)
        return cells1 == cells2

    def _insert_table_cell_content(self, text_widget, cell_content, is_header):
        """Insère le contenu d'une cellule avec support complet des formattages markdown"""
        if not cell_content:
            return

        # Appliquer les formattages markdown dans l'ordre de priorité
        # 1. Gras **texte**
        # 2. Code `texte`
        # 3. Texte normal

        parts = []
        current_pos = 0

        # Pattern pour détecter les formattages
        # On cherche soit **texte** soit `code`
        format_pattern = r"(\*\*[^*\n]+\*\*|`[^`\n]+`)"

        for match in re.finditer(format_pattern, cell_content):
            # Texte avant le format
            if match.start() > current_pos:
                parts.append(("normal", cell_content[current_pos : match.start()]))

            # Contenu formaté
            matched_text = match.group(0)
            if matched_text.startswith("**") and matched_text.endswith("**"):
                # Gras
                parts.append(("bold", matched_text[2:-2]))
            elif matched_text.startswith("`") and matched_text.endswith("`"):
                # Code
                parts.append(("code", matched_text[1:-1]))
            else:
                parts.append(("normal", matched_text))

            current_pos = match.end()

        # Texte restant
        if current_pos < len(cell_content):
            parts.append(("normal", cell_content[current_pos:]))

        # Insérer les parties avec leurs tags
        for part_type, part_text in parts:
            if part_type == "bold":
                if is_header:
                    text_widget.insert("insert", part_text, "table_header")
                else:
                    text_widget.insert("insert", part_text, "table_cell_bold")
            elif part_type == "code":
                text_widget.insert("insert", part_text, "code")
            else:
                if is_header:
                    text_widget.insert("insert", part_text, "table_header")
                else:
                    text_widget.insert("insert", part_text, "table_cell")

    def _insert_formatted_table(self, text_widget, raw_lines):
        """Insère un tableau complètement formaté avec support des formattages markdown"""
        separator_pattern = r"^\|?[\s\-:|\s]+\|?$"

        # Calculer les largeurs de colonnes (en comptant le texte sans les marqueurs markdown)
        all_cells = []
        for line_content in raw_lines:
            if re.match(separator_pattern, line_content.strip()):
                continue
            cells = self._parse_table_row(line_content)
            all_cells.append(cells)

        if not all_cells:
            return

        max_cols = max(len(row) for row in all_cells)
        widths = []
        for col in range(max_cols):
            max_width = 0
            for row in all_cells:
                if col < len(row):
                    # Enlever tous les marqueurs markdown pour calculer la largeur
                    cell_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", row[col])
                    cell_text = re.sub(r"`([^`]+)`", r"\1", cell_text)
                    max_width = max(max_width, len(cell_text))
            widths.append(max(max_width, 3))

        # Bordure supérieure
        border_top = "┌" + "┬".join("─" * (w + 2) for w in widths) + "┐\n"
        text_widget.insert("insert", border_top, "table_border")

        for line_idx, line_content in enumerate(raw_lines):
            if line_idx == 1:  # Séparateur
                sep_line = "├" + "┼".join("─" * (w + 2) for w in widths) + "┤\n"
                text_widget.insert("insert", sep_line, "table_border")
                continue

            cells = self._parse_table_row(line_content)
            is_header = line_idx == 0

            text_widget.insert("insert", "│", "table_border")

            for col_idx, width in enumerate(widths):
                cell_content = cells[col_idx] if col_idx < len(cells) else ""

                # Calculer la longueur d'affichage (sans les marqueurs)
                display_length = len(re.sub(r"\*\*([^*]+)\*\*", r"\1", cell_content))
                display_length = len(
                    re.sub(
                        r"`([^`]+)`",
                        r"\1",
                        re.sub(r"\*\*([^*]+)\*\*", r"\1", cell_content),
                    )
                )

                padding = width - display_length
                left_pad = padding // 2
                right_pad = padding - left_pad

                text_widget.insert("insert", " " + " " * left_pad, "table_border")

                # Insérer le contenu avec formatage
                self._insert_table_cell_content(text_widget, cell_content, is_header)

                text_widget.insert("insert", " " * right_pad + " ", "table_border")
                text_widget.insert("insert", "│", "table_border")

            text_widget.insert("insert", "\n")

        # Bordure inférieure
        border_bottom = "└" + "┴".join("─" * (w + 2) for w in widths) + "┘\n"
        text_widget.insert("insert", border_bottom, "table_border")

    def _insert_simple_markdown(self, text_widget, text):
        """Traite le markdown simple (gras, italique, titres, tableaux) sans les blocs de code"""

        # D'abord, détecter et traiter les tableaux Markdown
        lines = text.split("\n")
        i = 0
        segments = []  # Liste de (type, contenu)
        current_text = []

        while i < len(lines):
            line = lines[i]

            # Vérifier si c'est le début d'un tableau
            if "|" in line and i + 1 < len(lines):
                # Vérifier si la ligne suivante est un séparateur de tableau
                next_line = lines[i + 1]
                separator_pattern = r"^\|?[\s\-:|\s]+\|?$"
                if re.match(separator_pattern, next_line.strip()) and "-" in next_line:
                    # C'est un tableau! D'abord sauvegarder le texte précédent
                    if current_text:
                        segments.append(("text", "\n".join(current_text)))
                        current_text = []

                    # Collecter toutes les lignes du tableau
                    table_lines = [line, next_line]
                    i += 2
                    while i < len(lines) and "|" in lines[i]:
                        # Vérifier que ce n'est pas un autre séparateur (nouveau tableau)
                        if (
                            re.match(separator_pattern, lines[i].strip())
                            and "-" in lines[i]
                        ):
                            break
                        table_lines.append(lines[i])
                        i += 1

                    segments.append(("table", table_lines))
                    continue

            current_text.append(line)
            i += 1

        # Ajouter le reste du texte
        if current_text:
            segments.append(("text", "\n".join(current_text)))

        # Traiter chaque segment
        for seg_type, content in segments:
            if seg_type == "table":
                self._insert_markdown_table(text_widget, content)
            else:
                self._apply_simple_markdown_formatting(text_widget, content)

    def _apply_simple_markdown_formatting(self, text_widget, text):
        """Applique le formatage markdown simple (gras, italique, titres)"""
        # Patterns pour le markdown de base
        patterns = [
            (r"^(#{1,6})\s+(.+)$", "title_markdown"),  # Titres
            (r"\*\*([^*\n]+?)\*\*", "bold"),  # Gras
            (r"\*([^*\n]+?)\*", "italic"),  # Italique
            (r"`([^`]+)`", "mono"),  # Code inline
        ]

        def apply_formatting(text, patterns):
            if not patterns:
                text_widget.insert("end", text, "normal")
                return

            pattern, style = patterns[0]
            remaining_patterns = patterns[1:]

            last_pos = 0
            for match in re.finditer(pattern, text, re.MULTILINE):
                # Texte avant le match
                if match.start() > last_pos:
                    pre_text = text[last_pos : match.start()]
                    apply_formatting(pre_text, remaining_patterns)

                # Appliquer le style
                if style == "title_markdown":
                    level = len(match.group(1))
                    title_text = match.group(2)
                    text_widget.insert(
                        "end", title_text + "\n", f"title{min(level, 5)}"
                    )
                else:
                    content = match.group(1)
                    text_widget.insert("end", content, style)

                last_pos = match.end()

            # Texte après le dernier match
            if last_pos < len(text):
                remaining_text = text[last_pos:]
                apply_formatting(remaining_text, remaining_patterns)

        apply_formatting(text, patterns)

    def _parse_table_row(self, line):
        """Parse une ligne de tableau Markdown et retourne les cellules"""
        # Supprimer les | au début et à la fin
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]

        # Séparer par | et nettoyer chaque cellule
        cells = [cell.strip() for cell in line.split("|")]
        return cells

    def _calculate_column_widths(self, table_lines):
        """Calcule la largeur optimale de chaque colonne"""
        if not table_lines:
            return []

        # Parser toutes les lignes (sauf le séparateur)
        all_rows = []
        for i, line in enumerate(table_lines):
            if i == 1:  # Ignorer le séparateur
                continue
            cells = self._parse_table_row(line)
            all_rows.append(cells)

        if not all_rows:
            return []

        # Trouver le nombre max de colonnes
        max_cols = max(len(row) for row in all_rows)

        # Calculer la largeur max de chaque colonne
        widths = []
        for col in range(max_cols):
            max_width = 0
            for row in all_rows:
                if col < len(row):
                    # Compter la longueur sans les marqueurs markdown
                    cell_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", row[col])
                    max_width = max(max_width, len(cell_text))
            widths.append(max(max_width, 3))  # Minimum 3 caractères

        return widths

    def _insert_markdown_table(self, text_widget, table_lines):
        """Affiche un tableau Markdown formaté dans le widget avec support complet des formattages"""
        if not table_lines or len(table_lines) < 2:
            return

        column_widths = self._calculate_column_widths(table_lines)
        if not column_widths:
            return

        # Bordure supérieure
        border_line = "┌" + "┬".join("─" * (w + 2) for w in column_widths) + "┐\n"
        text_widget.insert("end", border_line, "table_border")

        for line_idx, line in enumerate(table_lines):
            if line_idx == 1:  # Séparateur - dessiner une ligne de séparation
                sep_line = "├" + "┼".join("─" * (w + 2) for w in column_widths) + "┤\n"
                text_widget.insert("end", sep_line, "table_border")
                continue

            cells = self._parse_table_row(line)
            is_header = line_idx == 0

            # Début de ligne
            text_widget.insert("end", "│", "table_border")

            for col_idx, width in enumerate(column_widths):
                cell_content = cells[col_idx] if col_idx < len(cells) else ""

                # Calculer la longueur d'affichage (sans les marqueurs markdown)
                display_length = len(re.sub(r"\*\*([^*]+)\*\*", r"\1", cell_content))
                display_length = len(
                    re.sub(
                        r"`([^`]+)`",
                        r"\1",
                        re.sub(r"\*\*([^*]+)\*\*", r"\1", cell_content),
                    )
                )

                # Centrer le contenu
                padding = width - display_length
                left_pad = padding // 2
                right_pad = padding - left_pad

                text_widget.insert("end", " " + " " * left_pad, "table_border")

                # Sauvegarder la position actuelle pour insertion avec formatage
                current_mark = "table_cell_insert"
                text_widget.mark_set(current_mark, "end")

                # Insérer le contenu avec formatage via la fonction helper
                # Temporairement changer "end" en utilisant la marque
                old_insert = text_widget.index("insert")
                text_widget.mark_set("insert", current_mark)
                self._insert_table_cell_content(text_widget, cell_content, is_header)
                text_widget.mark_set("insert", old_insert)
                text_widget.mark_unset(current_mark)

                text_widget.insert("end", " " * right_pad + " ", "table_border")
                text_widget.insert("end", "│", "table_border")

            text_widget.insert("end", "\n")

        # Bordure inférieure
        border_line = "└" + "┴".join("─" * (w + 2) for w in column_widths) + "┘\n"
        text_widget.insert("end", border_line, "table_border")

    def _format_markdown_tables_in_widget(self, text_widget, original_text=None):
        """Détecte et reformate les tableaux Markdown - VERSION CORRIGÉE avec texte original"""
        try:
            text_widget.configure(state="normal")

            # Utiliser le texte original s'il est fourni, sinon lire le widget
            if original_text:
                content = original_text
            else:
                content = text_widget.get("1.0", "end-1c")

            # Vérifier s'il y a potentiellement des tableaux (lignes avec |)
            if "|" not in content:
                return

            # Pattern pour identifier une ligne de séparateur de tableau
            separator_pattern = r"^\|?[\s\-:]+\|[\s\-:|]+\|?$"

            lines = content.split("\n")

            # Vérifier si au moins un tableau existe
            has_table = False
            for i, line in enumerate(lines):
                if "|" in line and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if (
                        re.match(separator_pattern, next_line.strip())
                        and "-" in next_line
                    ):
                        has_table = True
                        break

            if not has_table:
                return

            print("[DEBUG] Tableaux Markdown détectés, reconstruction du widget...")

            # Effacer le widget et reconstruire avec le texte original formaté
            text_widget.delete("1.0", "end")

            # Reconstruire le contenu en utilisant _insert_markdown_segments qui gère les blocs de code
            # et _insert_simple_markdown qui gère maintenant les tableaux
            self._insert_markdown_segments(text_widget, content)

        except Exception as e:
            print(f"[DEBUG] Erreur formatage tableaux: {e}")
            traceback.print_exc()

    def _insert_javascript_code_block(self, text_widget, code):
        """Coloration syntaxique pour JavaScript avec couleurs VS Code"""
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return

        # Mots-clés JavaScript
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

        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            # Tokenisation JavaScript
            # Pattern pour capturer différents éléments
            token_pattern = r"""
                (//.*$)|                     # Commentaires //
                (/\*.*?\*/)|                 # Commentaires /* */
                ("(?:[^"\\]|\\.)*")|         # Chaînes double quotes
                ('(?:[^'\\]|\\.)*')|         # Chaînes simple quotes
                (`(?:[^`\\]|\\.)*`)|         # Template literals
                (\b\d+\.?\d*\b)|             # Nombres
                (\b[a-zA-Z_$]\w*\b)|         # Identifiants
                ([+\-*/%=<>!&|^~]|===|!==|==|!=|<=|>=|&&|\|\||<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=|\+\+|--)|  # Opérateurs
                ([\(\)\[\]{},;:.])|          # Ponctuation
                (\s+)                        # Espaces
            """

            pos = 0
            for match in re.finditer(token_pattern, line, re.VERBOSE | re.DOTALL):
                # Ajouter le texte avant le match si nécessaire
                if match.start() > pos:
                    text_widget.insert("end", line[pos : match.start()], "code_block")

                token = match.group(0)

                if match.group(1):  # Commentaire //
                    text_widget.insert("end", token, "js_comment")
                elif match.group(2):  # Commentaire /* */
                    text_widget.insert("end", token, "js_comment")
                elif match.group(3) or match.group(4) or match.group(5):  # Chaînes
                    text_widget.insert("end", token, "js_string")
                elif match.group(6):  # Nombres
                    text_widget.insert("end", token, "js_number")
                elif match.group(7):  # Identifiants
                    if token in js_keywords:
                        text_widget.insert("end", token, "js_keyword")
                    else:
                        # Vérifier si c'est une fonction (suivi de '(')
                        remaining = line[match.end() :].lstrip()
                        if remaining.startswith("("):
                            text_widget.insert("end", token, "js_function")
                        else:
                            text_widget.insert("end", token, "js_variable")
                elif match.group(8):  # Opérateurs
                    text_widget.insert("end", token, "js_operator")
                elif match.group(9):  # Ponctuation
                    text_widget.insert("end", token, "js_punctuation")
                else:
                    text_widget.insert("end", token, "code_block")

                pos = match.end()

            # Ajouter le reste de la ligne
            if pos < len(line):
                text_widget.insert("end", line[pos:], "code_block")

        text_widget.insert("end", "\n")

    def _insert_html_code_block(self, text_widget, code):
        """Coloration syntaxique pour HTML avec couleurs VS Code"""
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return

        # Pattern pour les balises HTML
        html_pattern = r"""
            (<!--.*?-->)|                    # Commentaires HTML
            (</?[a-zA-Z][\w-]*(?:\s+[^>]*)?>) | # Balises ouvrantes/fermantes
            ([^<]+)                          # Contenu texte
        """

        for match in re.finditer(html_pattern, code, re.VERBOSE | re.DOTALL):
            content = match.group(0)

            if match.group(1):  # Commentaire
                text_widget.insert("end", content, "html_comment")
            elif match.group(2):  # Balise
                self._parse_html_tag(text_widget, content)
            else:  # Texte
                text_widget.insert("end", content, "html_text")

        text_widget.insert("end", "\n")

    def _parse_html_tag(self, text_widget, tag_content):
        """Parse une balise HTML pour colorer ses composants"""
        # Pattern pour décomposer une balise
        tag_pattern = r"(</?)([\w-]+)(\s+[^>]*)?(>)"
        match = re.match(tag_pattern, tag_content)

        if match:
            text_widget.insert("end", match.group(1), "html_punctuation")  # < ou </
            text_widget.insert("end", match.group(2), "html_tag")  # nom de balise

            # Attributs s'il y en a
            if match.group(3):
                self._parse_html_attributes(text_widget, match.group(3))

            text_widget.insert("end", match.group(4), "html_punctuation")  # >
        else:
            text_widget.insert("end", tag_content, "html_tag")

    def _parse_html_attributes(self, text_widget, attr_content):
        """Parse les attributs HTML"""
        # Pattern pour les attributs
        attr_pattern = r'(\s*)([\w-]+)(=)("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|\S+)?'

        pos = 0
        for match in re.finditer(attr_pattern, attr_content):
            # Espaces avant l'attribut
            if match.start() > pos:
                text_widget.insert(
                    "end", attr_content[pos : match.start()], "html_text"
                )

            text_widget.insert("end", match.group(1), "html_text")  # espaces
            text_widget.insert("end", match.group(2), "html_attribute")  # nom attribut
            text_widget.insert("end", match.group(3), "html_punctuation")  # =

            if match.group(4):  # valeur
                text_widget.insert("end", match.group(4), "html_value")

            pos = match.end()

        # Reste du texte
        if pos < len(attr_content):
            text_widget.insert("end", attr_content[pos:], "html_text")

    def _insert_css_code_block(self, text_widget, code):
        """Coloration syntaxique pour CSS avec couleurs VS Code"""
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return

        # Pattern CSS global
        css_pattern = r"""
            (/\*.*?\*/)|                     # Commentaires
            ([\w\-#\.:\[\](),\s>+~*]+)(\s*\{)|  # Sélecteurs + {
            ([\w-]+)(\s*:\s*)([^;}]+)(;?)|   # Propriété: valeur;
            (\})|                            # }
            ([^{}]+)                         # Autres contenus
        """

        for match in re.finditer(css_pattern, code, re.VERBOSE | re.DOTALL):
            if match.group(1):  # Commentaire
                text_widget.insert("end", match.group(1), "css_comment")
            elif match.group(2) and match.group(3):  # Sélecteur + {
                text_widget.insert("end", match.group(2), "css_selector")
                text_widget.insert("end", match.group(3), "css_punctuation")
            elif match.group(4):  # Propriété CSS
                text_widget.insert("end", match.group(4), "css_property")
                text_widget.insert("end", match.group(5), "css_punctuation")  # :
                self._parse_css_value(text_widget, match.group(6))  # valeur
                if match.group(7):  # ;
                    text_widget.insert("end", match.group(7), "css_punctuation")
            elif match.group(8):  # }
                text_widget.insert("end", match.group(8), "css_punctuation")
            else:
                text_widget.insert("end", match.group(0), "code_block")

        text_widget.insert("end", "\n")

    def _parse_css_value(self, text_widget, value):
        """Parse une valeur CSS pour la colorer"""
        # Pattern pour les valeurs CSS
        value_pattern = r"""
            ("(?:[^"\\]|\\.)*")|            # Chaînes double quotes
            ('(?:[^'\\]|\\.)*')|            # Chaînes simple quotes
            (\b\d+(?:\.\d+)?(?:px|em|rem|%|vh|vw|pt|pc|in|cm|mm|ex|ch|vmin|vmax|deg|rad|turn|s|ms)?\b)| # Nombres avec unités
            (#[0-9a-fA-F]{3,8})|            # Couleurs hexadécimales
            (\b(?:rgb|rgba|hsl|hsla|var|calc|url)\([^)]*\))| # Fonctions CSS
            ([^;}\s]+)                      # Autres valeurs
        """

        for match in re.finditer(value_pattern, value, re.VERBOSE):
            token = match.group(0)

            if match.group(1) or match.group(2):  # Chaînes
                text_widget.insert("end", token, "css_string")
            elif match.group(3):  # Nombres avec unités
                text_widget.insert("end", token, "css_number")
            elif match.group(4):  # Couleurs hex
                text_widget.insert("end", token, "css_number")
            elif match.group(5):  # Fonctions CSS
                text_widget.insert("end", token, "css_value")
            else:  # Autres valeurs
                text_widget.insert("end", token, "css_value")

    def _insert_bash_code_block(self, text_widget, code):
        """Coloration syntaxique pour Bash/Shell avec couleurs VS Code"""
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return

        # Mots-clés Bash
        bash_keywords = {
            "if",
            "then",
            "else",
            "elif",
            "fi",
            "for",
            "while",
            "until",
            "do",
            "done",
            "case",
            "esac",
            "in",
            "function",
            "return",
            "exit",
            "break",
            "continue",
            "local",
            "export",
            "readonly",
            "declare",
            "set",
            "unset",
            "source",
            "alias",
            "unalias",
            "type",
            "which",
            "whereis",
            "echo",
            "printf",
            "test",
            "true",
            "false",
        }

        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            # Skip shebang
            if line.startswith("#!"):
                text_widget.insert("end", line, "bash_comment")
                continue

            # Tokenisation Bash
            token_pattern = r"""
                (\#.*$)|                     # Commentaires
                ("(?:[^"\\]|\\.)*")|         # Chaînes double quotes
                ('(?:[^'\\]|\\.)*')|         # Chaînes simple quotes
                (\$\{[^}]*\}|\$\w+|\$\d+)|   # Variables
                (\b\d+\.?\d*\b)|             # Nombres
                (\b[a-zA-Z_]\w*\b)|          # Identifiants
                ([<>=!&|;()\[\]{}]|<<|>>|\|\||&&|==|!=|<=|>=|\+=|-=|\*=|/=|%=)| # Opérateurs
                (\s+)                        # Espaces
            """

            pos = 0
            for match in re.finditer(token_pattern, line, re.VERBOSE):
                # Ajouter le texte avant le match
                if match.start() > pos:
                    text_widget.insert("end", line[pos : match.start()], "code_block")

                token = match.group(0)

                if match.group(1):  # Commentaire
                    text_widget.insert("end", token, "bash_comment")
                elif match.group(2) or match.group(3):  # Chaînes
                    text_widget.insert("end", token, "bash_string")
                elif match.group(4):  # Variables
                    text_widget.insert("end", token, "bash_variable")
                elif match.group(5):  # Nombres
                    text_widget.insert("end", token, "bash_number")
                elif match.group(6):  # Identifiants
                    if token in bash_keywords:
                        text_widget.insert("end", token, "bash_keyword")
                    else:
                        text_widget.insert("end", token, "bash_command")
                elif match.group(7):  # Opérateurs
                    text_widget.insert("end", token, "bash_operator")
                else:
                    text_widget.insert("end", token, "code_block")

                pos = match.end()

            # Reste de la ligne
            if pos < len(line):
                text_widget.insert("end", line[pos:], "code_block")

        text_widget.insert("end", "\n")

    def _insert_sql_code_block(self, text_widget, code):
        """Coloration syntaxique pour SQL avec couleurs VS Code"""
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return

        # Mots-clés SQL
        sql_keywords = {
            "SELECT",
            "FROM",
            "WHERE",
            "JOIN",
            "INNER",
            "LEFT",
            "RIGHT",
            "FULL",
            "OUTER",
            "ON",
            "AND",
            "OR",
            "NOT",
            "IN",
            "EXISTS",
            "BETWEEN",
            "LIKE",
            "IS",
            "NULL",
            "INSERT",
            "INTO",
            "VALUES",
            "UPDATE",
            "SET",
            "DELETE",
            "CREATE",
            "TABLE",
            "ALTER",
            "DROP",
            "INDEX",
            "VIEW",
            "DATABASE",
            "SCHEMA",
            "PRIMARY",
            "KEY",
            "FOREIGN",
            "REFERENCES",
            "UNIQUE",
            "CHECK",
            "DEFAULT",
            "AUTO_INCREMENT",
            "ORDER",
            "BY",
            "GROUP",
            "HAVING",
            "DISTINCT",
            "LIMIT",
            "OFFSET",
            "UNION",
            "CASE",
            "WHEN",
            "THEN",
            "ELSE",
            "END",
            "AS",
            "ASC",
            "DESC",
        }

        # Fonctions SQL communes
        sql_functions = {
            "COUNT",
            "SUM",
            "AVG",
            "MIN",
            "MAX",
            "ROUND",
            "ABS",
            "UPPER",
            "LOWER",
            "LENGTH",
            "SUBSTRING",
            "CONCAT",
            "NOW",
            "DATE",
            "YEAR",
            "MONTH",
            "DAY",
        }

        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            # Tokenisation SQL
            token_pattern = r"""
                (--.*$)|                     # Commentaires --
                (/\*.*?\*/)|                 # Commentaires /* */
                ('(?:[^'\\]|\\.)*')|         # Chaînes simple quotes
                (\b\d+\.?\d*\b)|             # Nombres
                (\b[a-zA-Z_]\w*\b)|          # Identifiants
                ([=<>!]+|<=|>=|<>|\|\|)|     # Opérateurs
                ([(),;.])|                   # Ponctuation
                (\s+)                        # Espaces
            """

            pos = 0
            for match in re.finditer(token_pattern, line, re.VERBOSE | re.DOTALL):
                # Ajouter le texte avant le match
                if match.start() > pos:
                    text_widget.insert("end", line[pos : match.start()], "code_block")

                token = match.group(0)

                if match.group(1) or match.group(2):  # Commentaires
                    text_widget.insert("end", token, "sql_comment")
                elif match.group(3):  # Chaînes
                    text_widget.insert("end", token, "sql_string")
                elif match.group(4):  # Nombres
                    text_widget.insert("end", token, "sql_number")
                elif match.group(5):  # Identifiants
                    token_upper = token.upper()
                    if token_upper in sql_keywords:
                        text_widget.insert("end", token, "sql_keyword")
                    elif token_upper in sql_functions:
                        text_widget.insert("end", token, "sql_function")
                    else:
                        text_widget.insert("end", token, "sql_identifier")
                elif match.group(6):  # Opérateurs
                    text_widget.insert("end", token, "sql_operator")
                elif match.group(7):  # Ponctuation
                    text_widget.insert("end", token, "sql_punctuation")
                else:
                    text_widget.insert("end", token, "code_block")

                pos = match.end()

            # Reste de la ligne
            if pos < len(line):
                text_widget.insert("end", line[pos:], "code_block")

        text_widget.insert("end", "\n")

    def _insert_dockerfile_code_block(self, text_widget, code):
        """Coloration syntaxique pour Dockerfile avec couleurs VS Code"""
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return

        # Instructions Dockerfile
        dockerfile_instructions = {
            "FROM",
            "RUN",
            "COPY",
            "ADD",
            "CMD",
            "ENTRYPOINT",
            "WORKDIR",
            "EXPOSE",
            "ENV",
            "ARG",
            "VOLUME",
            "USER",
            "LABEL",
            "MAINTAINER",
            "ONBUILD",
            "STOPSIGNAL",
            "HEALTHCHECK",
            "SHELL",
        }

        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            line_stripped = line.strip()

            # Commentaires
            if line_stripped.startswith("#"):
                text_widget.insert("end", line, "dockerfile_comment")
                continue

            # Instructions Dockerfile
            instruction_match = re.match(r"^(\s*)(\w+)(\s+)(.*)", line)
            if instruction_match:
                indent, instruction, space, rest = instruction_match.groups()

                text_widget.insert("end", indent, "code_block")

                if instruction.upper() in dockerfile_instructions:
                    text_widget.insert("end", instruction, "dockerfile_instruction")
                else:
                    text_widget.insert("end", instruction, "code_block")

                text_widget.insert("end", space, "code_block")

                # Parser le reste selon l'instruction
                self._parse_dockerfile_rest(text_widget, instruction.upper(), rest)
            else:
                text_widget.insert("end", line, "code_block")

        text_widget.insert("end", "\n")

    def _parse_dockerfile_rest(self, text_widget, instruction, rest):
        """Parse le reste d'une ligne Dockerfile selon l'instruction"""
        # Variables ${VAR} ou $VAR
        _var_pattern = r"(\$\{[^}]*\}|\$\w+)"
        # Chaînes entre guillemets
        _string_pattern = r'("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')'
        # Flags comme --from=
        flag_pattern = r"(--[\w-]+(?:=\S+)?)"

        pos = 0

        # Traiter les flags d'abord (pour certaines instructions)
        if instruction in ["COPY", "ADD", "RUN"]:
            for match in re.finditer(flag_pattern, rest):
                if match.start() > pos:
                    self._parse_simple_dockerfile_content(
                        text_widget, rest[pos : match.start()]
                    )
                text_widget.insert("end", match.group(1), "dockerfile_flag")
                pos = match.end()

        # Traiter le reste
        remaining = rest[pos:]
        self._parse_simple_dockerfile_content(text_widget, remaining)

    def _parse_simple_dockerfile_content(self, text_widget, content):
        """Parse le contenu simple d'une ligne Dockerfile"""
        # Pattern pour variables et chaînes
        pattern = r'(\$\{[^}]*\}|\$\w+)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')'

        pos = 0
        for match in re.finditer(pattern, content):
            if match.start() > pos:
                text_widget.insert("end", content[pos : match.start()], "code_block")

            if match.group(1):  # Variable
                text_widget.insert("end", match.group(1), "dockerfile_variable")
            elif match.group(2):  # Chaîne
                text_widget.insert("end", match.group(2), "dockerfile_string")

            pos = match.end()

        if pos < len(content):
            # Vérifier si le reste ressemble à un chemin
            remaining = content[pos:]
            if re.match(r"^[/\.\w-]+$", remaining.strip()):
                text_widget.insert("end", remaining, "dockerfile_path")
            else:
                text_widget.insert("end", remaining, "code_block")

    def _insert_json_code_block(self, text_widget, code):
        """Coloration syntaxique pour JSON avec couleurs VS Code"""
        text_widget.insert("end", "\n")
        code = code.strip()
        if not code:
            text_widget.insert("end", "\n")
            return

        # Essayer de parser le JSON pour une coloration plus précise
        try:
            # Vérifier si c'est du JSON valide
            json.loads(code)

            # Pattern JSON
            json_pattern = r"""
                ("(?:[^"\\]|\\.)*")(\s*:\s*)|  # Clés JSON
                ("(?:[^"\\]|\\.)*")|           # Chaînes
                (\b(?:true|false|null)\b)|     # Mots-clés JSON
                (\b-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)| # Nombres
                ([\[\]{},:])|                  # Structures JSON
                (\s+)                          # Espaces
            """

            for match in re.finditer(json_pattern, code, re.VERBOSE):
                if match.group(1) and match.group(2):  # Clé + :
                    text_widget.insert(
                        "end", match.group(1), "js_property"
                    )  # Clé en couleur propriété
                    text_widget.insert("end", match.group(2), "js_punctuation")  # :
                elif match.group(3):  # Chaîne valeur
                    text_widget.insert("end", match.group(3), "js_string")
                elif match.group(4):  # true/false/null
                    text_widget.insert("end", match.group(4), "js_keyword")
                elif match.group(5):  # Nombres
                    text_widget.insert("end", match.group(5), "js_number")
                elif match.group(6):  # Structures
                    text_widget.insert("end", match.group(6), "js_punctuation")
                else:
                    text_widget.insert("end", match.group(0), "code_block")

        except json.JSONDecodeError:
            # JSON invalide, coloration basique
            text_widget.insert("end", code, "code_block")

        text_widget.insert("end", "\n")

    # === NOUVELLES FONCTIONS SANS NEWLINES AUTOMATIQUES ===

    def _insert_javascript_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour JavaScript"""
        code = code.strip()
        if not code:
            return

        # Mots-clés JavaScript
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

        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            # Tokenisation JavaScript
            token_pattern = r"""
                (//.*$)|                     # Commentaires //
                (/\*.*?\*/)|                 # Commentaires /* */
                ("(?:[^"\\]|\\.)*")|         # Chaînes double quotes
                ('(?:[^'\\]|\\.)*')|         # Chaînes simple quotes
                (`(?:[^`\\]|\\.)*`)|         # Template literals
                (\b\d+\.?\d*\b)|             # Nombres
                (\b[a-zA-Z_$]\w*\b)|         # Identifiants
                ([+\-*/%=<>!&|^~]|===|!==|==|!=|<=|>=|&&|\|\||<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=|\+\+|--)|  # Opérateurs
                ([\(\)\[\]{},;:.])|          # Ponctuation
                (\s+)                        # Espaces
            """

            pos = 0
            for match in re.finditer(token_pattern, line, re.VERBOSE | re.DOTALL):
                # Ajouter le texte avant le match si nécessaire
                if match.start() > pos:
                    text_widget.insert("end", line[pos : match.start()], "code_block")

                token = match.group(0)

                if match.group(1):  # Commentaire //
                    text_widget.insert("end", token, "js_comment")
                elif match.group(2):  # Commentaire /* */
                    text_widget.insert("end", token, "js_comment")
                elif match.group(3) or match.group(4) or match.group(5):  # Chaînes
                    text_widget.insert("end", token, "js_string")
                elif match.group(6):  # Nombres
                    text_widget.insert("end", token, "js_number")
                elif match.group(7):  # Identifiants
                    if token in js_keywords:
                        text_widget.insert("end", token, "js_keyword")
                    else:
                        # Vérifier si c'est une fonction (suivi de '(')
                        remaining = line[match.end() :].lstrip()
                        if remaining.startswith("("):
                            text_widget.insert("end", token, "js_function")
                        else:
                            text_widget.insert("end", token, "js_variable")
                elif match.group(8):  # Opérateurs
                    text_widget.insert("end", token, "js_operator")
                elif match.group(9):  # Ponctuation
                    text_widget.insert("end", token, "js_punctuation")
                else:
                    text_widget.insert("end", token, "code_block")

                pos = match.end()

            # Ajouter le reste de la ligne
            if pos < len(line):
                text_widget.insert("end", line[pos:], "code_block")

    def _insert_html_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour HTML"""
        code = code.strip()
        if not code:
            return

        # Pattern pour les balises HTML
        html_pattern = r"""
            (<!--.*?-->)|                    # Commentaires HTML
            (</?[a-zA-Z][\w-]*(?:\s+[^>]*)?>) | # Balises ouvrantes/fermantes
            ([^<]+)                          # Contenu texte
        """

        for match in re.finditer(html_pattern, code, re.VERBOSE | re.DOTALL):
            content = match.group(0)

            if match.group(1):  # Commentaire
                text_widget.insert("end", content, "html_comment")
            elif match.group(2):  # Balise
                self._parse_html_tag(text_widget, content)
            else:  # Texte
                text_widget.insert("end", content, "html_text")

    def _insert_css_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour CSS"""
        code = code.strip()
        if not code:
            return

        # Pattern CSS global (version simplifiée)
        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            line_stripped = line.strip()

            # Commentaires CSS
            if "/*" in line and "*/" in line:
                text_widget.insert("end", line, "css_comment")
            # Sélecteurs (lignes se terminant par {)
            elif line_stripped.endswith("{"):
                selector = line_stripped[:-1].strip()
                text_widget.insert("end", selector, "css_selector")
                text_widget.insert("end", " {", "css_punctuation")
            # Propriétés CSS (contenant :)
            elif ":" in line and not line_stripped.startswith("/*"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    prop = parts[0].strip()
                    value = parts[1].strip()

                    text_widget.insert(
                        "end", " " * (len(line) - len(line.lstrip())), "code_block"
                    )  # Indentation
                    text_widget.insert("end", prop, "css_property")
                    text_widget.insert("end", ": ", "css_punctuation")

                    # Enlever le ; final si présent
                    if value.endswith(";"):
                        value_content = value[:-1]
                        text_widget.insert("end", value_content, "css_value")
                        text_widget.insert("end", ";", "css_punctuation")
                    else:
                        text_widget.insert("end", value, "css_value")
                else:
                    text_widget.insert("end", line, "code_block")
            # Fermeture de bloc
            elif line_stripped == "}":
                text_widget.insert("end", line, "css_punctuation")
            else:
                text_widget.insert("end", line, "code_block")

    def _insert_bash_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour Bash"""
        code = code.strip()
        if not code:
            return

        # Mots-clés Bash essentiels
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
            "break",
            "continue",
            "export",
            "local",
            "echo",
            "printf",
        }

        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            # Shebang
            if line.startswith("#!"):
                text_widget.insert("end", line, "bash_comment")
                continue

            # Commentaires
            if line.strip().startswith("#"):
                text_widget.insert("end", line, "bash_comment")
                continue

            # Tokenisation simple
            words = line.split()
            current_pos = 0

            for word in words:
                # Trouver la position du mot dans la ligne
                word_start = line.find(word, current_pos)

                # Ajouter les espaces avant le mot
                if word_start > current_pos:
                    text_widget.insert(
                        "end", line[current_pos:word_start], "code_block"
                    )

                # Colorer le mot
                if word.startswith("$"):
                    text_widget.insert("end", word, "bash_variable")
                elif word.startswith('"') or word.startswith("'"):
                    text_widget.insert("end", word, "bash_string")
                elif word.isdigit():
                    text_widget.insert("end", word, "bash_number")
                elif word in bash_keywords:
                    text_widget.insert("end", word, "bash_keyword")
                else:
                    text_widget.insert("end", word, "bash_command")

                current_pos = word_start + len(word)

            # Ajouter le reste de la ligne (espaces finaux, etc.)
            if current_pos < len(line):
                text_widget.insert("end", line[current_pos:], "code_block")

    def _insert_sql_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour SQL"""
        code = code.strip()
        if not code:
            return

        # Mots-clés SQL essentiels
        sql_keywords = {
            "SELECT",
            "FROM",
            "WHERE",
            "JOIN",
            "INNER",
            "LEFT",
            "RIGHT",
            "ON",
            "AND",
            "OR",
            "INSERT",
            "INTO",
            "VALUES",
            "UPDATE",
            "SET",
            "DELETE",
            "CREATE",
            "TABLE",
            "ALTER",
            "DROP",
            "ORDER",
            "BY",
            "GROUP",
            "HAVING",
        }

        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            # Commentaires
            if line.strip().startswith("--"):
                text_widget.insert("end", line, "sql_comment")
                continue

            # Tokenisation simple par mots
            words = re.findall(r"\S+|\s+", line)

            for word in words:
                if word.isspace():
                    text_widget.insert("end", word, "code_block")
                elif word.startswith("'") and word.endswith("'"):
                    text_widget.insert("end", word, "sql_string")
                elif word.replace(".", "").isdigit():
                    text_widget.insert("end", word, "sql_number")
                elif word.upper() in sql_keywords:
                    text_widget.insert("end", word, "sql_keyword")
                elif word in [",", ";", "(", ")", "=", "<", ">", "<=", ">="]:
                    text_widget.insert("end", word, "sql_punctuation")
                else:
                    text_widget.insert("end", word, "sql_identifier")

    def _insert_dockerfile_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour Dockerfile"""
        code = code.strip()
        if not code:
            return

        # Instructions Dockerfile
        dockerfile_instructions = {
            "FROM",
            "RUN",
            "COPY",
            "ADD",
            "CMD",
            "ENTRYPOINT",
            "WORKDIR",
            "EXPOSE",
            "ENV",
            "ARG",
            "VOLUME",
            "USER",
            "LABEL",
        }

        lines = code.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "code_block")

            line_stripped = line.strip()

            # Commentaires
            if line_stripped.startswith("#"):
                text_widget.insert("end", line, "dockerfile_comment")
                continue

            # Instructions
            words = line.split()
            if words and words[0].upper() in dockerfile_instructions:
                # Indentation
                indent = len(line) - len(line.lstrip())
                if indent > 0:
                    text_widget.insert("end", line[:indent], "code_block")

                # Instruction
                text_widget.insert("end", words[0], "dockerfile_instruction")

                # Reste de la ligne
                rest = line[indent + len(words[0]) :]
                if rest:
                    # Variables simples
                    if "$" in rest:
                        parts = re.split(r"(\$\w+|\$\{[^}]*\})", rest)
                        for part in parts:
                            if part.startswith("$"):
                                text_widget.insert("end", part, "dockerfile_variable")
                            else:
                                text_widget.insert("end", part, "dockerfile_string")
                    else:
                        text_widget.insert("end", rest, "dockerfile_string")
            else:
                text_widget.insert("end", line, "code_block")

    def _insert_json_code_block_without_newlines(self, text_widget, code):
        """Version sans newlines automatiques pour JSON"""
        code = code.strip()
        if not code:
            return

        # Tokenisation JSON simple
        json_pattern = r"""
            ("(?:[^"\\]|\\.)*")(\s*:\s*)|  # Clés JSON + :
            ("(?:[^"\\]|\\.)*")|           # Chaînes
            (\b(?:true|false|null)\b)|     # Mots-clés JSON
            (\b-?\d+(?:\.\d+)?\b)|         # Nombres
            ([\[\]{},:])|                  # Structures JSON
            (\s+)                          # Espaces
        """

        for match in re.finditer(json_pattern, code, re.VERBOSE):
            if match.group(1) and match.group(2):  # Clé + :
                text_widget.insert("end", match.group(1), "js_property")
                text_widget.insert("end", match.group(2), "js_punctuation")
            elif match.group(3):  # Chaîne
                text_widget.insert("end", match.group(3), "js_string")
            elif match.group(4):  # true/false/null
                text_widget.insert("end", match.group(4), "js_keyword")
            elif match.group(5):  # Nombres
                text_widget.insert("end", match.group(5), "js_number")
            elif match.group(6):  # Structures
                text_widget.insert("end", match.group(6), "js_punctuation")
            else:
                text_widget.insert("end", match.group(0), "code_block")

    def _is_position_in_code_block(self, text_widget, position):
        """Vérifie si une position est dans un bloc de code ou un token de code"""
        try:
            # Vérifier si cette position a déjà un tag de code
            tags = text_widget.tag_names(position)
            code_tags = {
                "code_block",
                "code_block_marker",
                "hidden",
                # Python tokens
                "Token.Keyword",
                "Token.Literal.String",
                "Token.Comment.Single",
                "Token.Literal.Number",
                "Token.Name.Function",
                "Token.Name.Class",
                "Token.Name.Builtin",
                "Token.Operator",
                "Token.Punctuation",
                "Token.Name",
                "Token.Name.Variable",
                "Token.Name.Attribute",
                "Token.Comment",
                "Token.Comment.Multiline",
                "Token.String",
                # JavaScript
                "js_keyword",
                "js_string",
                "js_comment",
                "js_number",
                "js_variable",
                "js_operator",
                "js_function",
                # CSS
                "css_selector",
                "css_property",
                "css_value",
                "css_comment",
                "css_unit",
                # HTML
                "html_tag",
                "html_attribute",
                "html_value",
                "html_comment",
                # Bash
                "bash_keyword",
                "bash_command",
                "bash_string",
                "bash_comment",
                "bash_variable",
                # SQL
                "sql_keyword",
                "sql_function",
                "sql_string",
                "sql_comment",
                "sql_number",
                # Java
                "java_keyword",
                "java_string",
                "java_comment",
                "java_number",
                "java_class",
                "java_method",
                "java_annotation",
                # C/C++
                "cpp_keyword",
                "cpp_string",
                "cpp_comment",
                "cpp_number",
                "cpp_preprocessor",
                "cpp_type",
                "cpp_function",
                # C
                "c_keyword",
                "c_string",
                "c_comment",
                "c_number",
                "c_preprocessor",
                "c_type",
                "c_function",
                # C#
                "csharp_keyword",
                "csharp_string",
                "csharp_comment",
                "csharp_number",
                "csharp_class",
                "csharp_method",
                # Go
                "go_keyword",
                "go_string",
                "go_comment",
                "go_number",
                "go_type",
                "go_function",
                "go_package",
                # Ruby
                "ruby_keyword",
                "ruby_string",
                "ruby_comment",
                "ruby_number",
                "ruby_symbol",
                "ruby_method",
                "ruby_class",
                "ruby_variable",
                # Swift
                "swift_keyword",
                "swift_string",
                "swift_comment",
                "swift_number",
                "swift_type",
                "swift_function",
                "swift_attribute",
                # PHP
                "php_keyword",
                "php_string",
                "php_comment",
                "php_number",
                "php_variable",
                "php_function",
                "php_tag",
                # Perl
                "perl_keyword",
                "perl_string",
                "perl_comment",
                "perl_number",
                "perl_variable",
                "perl_regex",
                # Rust
                "rust_keyword",
                "rust_string",
                "rust_comment",
                "rust_number",
                "rust_type",
                "rust_function",
                "rust_macro",
                "rust_lifetime",
            }
            for tag in tags:
                if tag in code_tags:
                    return True
            return False
        except Exception:
            return False

    def _apply_unified_progressive_formatting(self, text_widget):
        """⚡ OPTIMISÉ : Formatage progressif sécurisé avec limitation de zone"""
        try:
            text_widget.configure(state="normal")

            # ⚡ OPTIMISATION: Limiter la zone de recherche aux 800 derniers caractères
            # Cela réduit drastiquement le nombre de regex et de recherches
            widget_end = text_widget.index("end-1c")
            total_chars = int(float(widget_end.split(".")[0]))  # Ligne actuelle

            # Si moins de 80 lignes, traiter tout; sinon traiter les 80 dernières lignes
            if total_chars > 80:
                search_start = f"{total_chars - 80}.0"
            else:
                search_start = "1.0"

            # Obtenir le texte actuellement affiché
            _current_displayed_text = text_widget.get("1.0", "end-1c")

            # === FORMATAGE GRAS **texte** - Toujours actif mais vérifie le texte complet ===
            start_pos = search_start  # ⚡ OPTIMISÉ: Commence à la zone récente
            while True:
                # Chercher le prochain **
                pos_start = text_widget.search("**", start_pos, "end")
                if not pos_start:
                    break

                # Vérifier si on est dans un bloc de code - si oui, ignorer
                if self._is_position_in_code_block(text_widget, pos_start):
                    start_pos = text_widget.index(f"{pos_start}+2c")
                    continue

                # Chercher le ** de fermeture
                search_start = text_widget.index(f"{pos_start}+2c")
                pos_end = text_widget.search("**", search_start, "end")

                if pos_end:
                    # Vérifier que le contenu entre les ** est valide
                    content_start = text_widget.index(f"{pos_start}+2c")
                    content = text_widget.get(content_start, pos_end)

                    # Valider le contenu
                    if (
                        content
                        and len(content) <= 200
                        and "*" not in content
                        and "\n" not in content
                    ):
                        # Vérifier que ce bold complet existe dans le texte source
                        full_bold = f"**{content}**"
                        if hasattr(self, "typing_text") and self.typing_text:
                            if full_bold not in self.typing_text:
                                # Pas encore complet dans le texte source
                                start_pos = text_widget.index(f"{pos_start}+1c")
                                continue

                        # Déduplication par position pour autoriser les répétitions
                        pos_str = str(pos_start)
                        if pos_str not in self._formatted_positions:
                            # Supprimer **texte** et insérer texte en gras
                            end_pos_full = text_widget.index(f"{pos_end}+2c")
                            text_widget.delete(pos_start, end_pos_full)
                            text_widget.insert(pos_start, content, "bold")
                            self._formatted_positions.add(pos_str)
                            # Continuer après le texte inséré
                            start_pos = text_widget.index(
                                f"{pos_start}+{len(content)}c"
                            )
                        else:
                            start_pos = text_widget.index(f"{pos_end}+2c")
                    else:
                        start_pos = text_widget.index(f"{pos_start}+1c")
                else:
                    start_pos = text_widget.index(f"{pos_start}+1c")

            # === FORMATAGE LIENS PRÉTRAITÉS (DÉTECTION DES TITRES) ===
            # Les liens ont été remplacés par leurs titres, on doit les détecter et les marquer
            if hasattr(self, "_pending_links") and self._pending_links:
                # Créer un set de titres uniques pour éviter les recherches dupliquées
                unique_titles = set(
                    link_data["title"] for link_data in self._pending_links
                )

                for title in unique_titles:
                    # Chercher toutes les occurrences de ce titre
                    start_pos = search_start  # ⚡ OPTIMISÉ
                    occurrences_found = 0
                    while True:
                        pos_start = text_widget.search(
                            title, start_pos, "end", nocase=False
                        )
                        if not pos_start:
                            break

                        pos_end = text_widget.index(f"{pos_start}+{len(title)}c")
                        pos_str = str(pos_start)

                        # Vérifier que ce n'est pas déjà formaté et que c'est exactement le titre
                        current_text = text_widget.get(pos_start, pos_end)
                        if (
                            current_text == title
                            and pos_str not in self._formatted_positions
                        ):
                            # Marquer comme lien temporaire
                            text_widget.tag_add("link_temp", pos_start, pos_end)
                            self._formatted_positions.add(pos_str)
                            occurrences_found += 1
                            # ⚡ Debug supprimé pour performance

                        start_pos = text_widget.index(f"{pos_start}+1c")

                    # ⚡ Debug supprimé pour performance

            # === FORMATAGE LIENS [titre](url) AVEC PRIORITÉ SUR TITRES (ANCIEN SYSTÈME POUR COMPATIBILITÉ) ===
            start_pos = search_start  # ⚡ OPTIMISÉ
            links_found = 0
            while True:
                # Chercher le prochain [
                pos_start = text_widget.search("[", start_pos, "end")
                if not pos_start:
                    break

                # NOUVEAU: Vérifier si on est dans un bloc de code - si oui, ignorer
                if self._is_position_in_code_block(text_widget, pos_start):
                    start_pos = text_widget.index(f"{pos_start}+1c")
                    continue

                # Obtenir la ligne complète pour analyser le pattern
                line_start = text_widget.index(f"{pos_start} linestart")
                line_end = text_widget.index(f"{pos_start} lineend")
                line_content = text_widget.get(line_start, line_end)

                # Pattern pour détecter [titre](url)
                link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
                match = re.search(link_pattern, line_content)

                if match:
                    links_found += 1
                    # ⚡ Debug supprimé pour performance
                    title = match.group(1)
                    url = match.group(2)

                    # Calculer les positions dans le widget
                    char_offset = line_content.find(match.group(0))
                    link_start = text_widget.index(f"{line_start}+{char_offset}c")
                    link_end = text_widget.index(f"{link_start}+{len(match.group(0))}c")

                    pos_str = str(link_start)

                    if pos_str not in self._formatted_positions:
                        # Remplacer [titre](url) par juste "titre" pendant l'animation
                        text_widget.delete(link_start, link_end)
                        text_widget.insert(link_start, title, "link_temp")

                        # Stocker l'URL pour plus tard dans une liste (pas dictionnaire)
                        if not hasattr(self, "_pending_links"):
                            self._pending_links = []

                        # Ajouter ce lien à la liste
                        self._pending_links.append(
                            {
                                "title": title,
                                "url": url,
                            }
                        )
                        # ⚡ Debug supprimé pour performance

                        self._formatted_positions.add(pos_str)

                        start_pos = link_start
                    else:
                        start_pos = text_widget.index(f"{pos_start}+1c")
                else:
                    start_pos = text_widget.index(f"{pos_start}+1c")

            # ⚡ Debug supprimé pour performance

            # === FORMATAGE CODE `code` ===
            start_pos = search_start  # ⚡ OPTIMISÉ
            while True:
                # Chercher le prochain `
                pos_start = text_widget.search("`", start_pos, "end")
                if not pos_start:
                    break

                # Vérifier si on est dans un bloc de code - si oui, ignorer
                if self._is_position_in_code_block(text_widget, pos_start):
                    start_pos = text_widget.index(f"{pos_start}+1c")
                    continue

                # Chercher le ` de fermeture
                search_start = text_widget.index(f"{pos_start}+1c")
                pos_end = text_widget.search("`", search_start, "end")

                if pos_end:
                    # Vérifier le contenu
                    content_start = text_widget.index(f"{pos_start}+1c")
                    content = text_widget.get(content_start, pos_end)

                    if (
                        content
                        and len(content) <= 100
                        and "`" not in content
                        and "\n" not in content
                    ):
                        pos_str = str(pos_start)

                        if pos_str not in self._formatted_positions:
                            # Supprimer `code`
                            end_pos_full = text_widget.index(f"{pos_end}+1c")
                            text_widget.delete(pos_start, end_pos_full)

                            # Insérer code formaté
                            text_widget.insert(pos_start, content, "code")

                            self._formatted_positions.add(pos_str)

                            start_pos = pos_start
                        else:
                            start_pos = text_widget.index(f"{pos_end}+1c")
                    else:
                        start_pos = text_widget.index(f"{pos_start}+1c")
                else:
                    start_pos = text_widget.index(f"{pos_start}+1c")

            # === FORMATAGE TITRES # ## ### #### ===
            # Ne pas formater les # qui sont dans des blocs de code (commentaires Python)
            # Formater les titres Markdown avec 1 à 6 #
            start_pos = search_start  # ⚡ OPTIMISÉ
            while True:
                # Chercher le prochain # en début de ligne
                pos_start = text_widget.search("#", start_pos, "end")
                if not pos_start:
                    break

                # Vérifier que c'est bien en début de ligne
                line_start = text_widget.index(f"{pos_start} linestart")
                if pos_start != line_start:
                    start_pos = text_widget.index(f"{pos_start}+1c")
                    continue

                # VÉRIFICATION CRITIQUE: Si ce # a déjà un tag de code (commentaire), ne pas formater comme titre
                if self._is_position_in_code_block(text_widget, pos_start):
                    # C'est un commentaire Python, pas un titre Markdown
                    start_pos = text_widget.index(f"{pos_start}+1c")
                    continue

                # Obtenir la ligne complète
                line_end = text_widget.index(f"{pos_start} lineend")
                line_content = text_widget.get(pos_start, line_end)

                # Analyser la ligne pour détecter le niveau de titre (1 à 6 #)
                title_match = re.match(r"^(#{1,6})\s+(.+)$", line_content)
                if title_match:
                    hash_count = len(title_match.group(1))
                    # Mapper vers title_1, title_2, title_3 (max 3 niveaux de style)
                    level = min(hash_count, 3)
                    title_without_hashes = title_match.group(2)

                    # IMPORTANT: Ne formater que si la ligne est COMPLÈTE
                    # On vérifie si après cette ligne il y a du contenu (donc \n a été affiché)
                    # ou si c'est la fin de l'animation
                    line_is_complete = False

                    # Vérifier s'il y a une ligne après (donc \n a été affiché)
                    next_line_start = text_widget.index(f"{line_end}+1c")
                    widget_end = text_widget.index("end-1c")

                    # Si next_line_start < widget_end, il y a du contenu après cette ligne
                    if text_widget.compare(next_line_start, "<=", widget_end):
                        # Vérifier qu'il y a vraiment du contenu après (pas juste la fin)
                        content_after = text_widget.get(line_end, next_line_start)
                        if content_after == "\n":
                            line_is_complete = True

                    # Si l'animation est terminée (pas de typing_text actif), formater
                    if not hasattr(self, "typing_text") or not self.typing_text:
                        line_is_complete = True
                    # Si typing_index a atteint la fin du texte
                    elif hasattr(self, "typing_index") and hasattr(self, "typing_text"):
                        if self.typing_index >= len(self.typing_text):
                            line_is_complete = True

                    # Utiliser le contenu comme clé pour éviter les doublons
                    content_key = f"title:{title_without_hashes.strip()}"
                    if (
                        line_is_complete
                        and content_key not in self._formatted_bold_contents
                    ):
                        # Remplacer "## titre" par "titre" formaté (sans les ##)
                        text_widget.delete(pos_start, line_end)
                        text_widget.insert(
                            pos_start, title_without_hashes, f"title_{level}"
                        )
                        self._formatted_bold_contents.add(content_key)
                        start_pos = text_widget.index(
                            f"{pos_start}+{len(title_without_hashes)}c"
                        )
                    else:
                        start_pos = text_widget.index(f"{line_end}+1c")
                else:
                    start_pos = text_widget.index(
                        f"{pos_start}+1c"
                    )  # === FORMATAGE DOCSTRINGS '''docstring''' ===
            start_pos = search_start  # ⚡ OPTIMISÉ
            while True:
                # Chercher le prochain '''
                pos_start = text_widget.search("'''", start_pos, "end")
                if not pos_start:
                    break

                # Chercher le ''' de fermeture
                search_start = text_widget.index(f"{pos_start}+3c")
                pos_end = text_widget.search("'''", search_start, "end")

                if pos_end:
                    # Obtenir le contenu COMPLET avec les '''
                    end_pos_full = text_widget.index(f"{pos_end}+3c")
                    full_docstring = text_widget.get(
                        pos_start, end_pos_full
                    )  # '''contenu'''

                    # Obtenir juste le contenu pour validation
                    content_start = text_widget.index(f"{pos_start}+3c")
                    content = text_widget.get(content_start, pos_end)

                    # Valider que c'est une vraie docstring (pas trop courte)
                    if content and len(content.strip()) > 0:
                        pos_str = str(pos_start)

                        if pos_str not in self._formatted_positions:
                            # CORRECTION : Garder les ''' et formater le tout
                            text_widget.delete(pos_start, end_pos_full)

                            # Insérer docstring formatée AVEC les '''
                            text_widget.insert(pos_start, full_docstring, "docstring")

                            self._formatted_positions.add(pos_str)

                            start_pos = pos_start
                        else:
                            start_pos = text_widget.index(f"{pos_end}+1c")
                    else:
                        start_pos = text_widget.index(f"{pos_start}+1c")
                else:
                    start_pos = text_widget.index(f"{pos_start}+1c")

            text_widget.configure(state="disabled")

        except Exception as e:
            print(f"[ERREUR] Formatage unifié: {e}")
            if hasattr(text_widget, "configure"):
                text_widget.configure(state="disabled")

    def _apply_immediate_progressive_formatting(self, text_widget):
        """Formatage progressif IMMÉDIAT et DIRECT"""
        try:
            # Obtenir le contenu actuel
            current_content = text_widget.get("1.0", "end-1c")

            # Pattern pour **texte** complet seulement
            bold_pattern = r"\*\*([^*\n]{1,50}?)\*\*"

            # Chercher et formater tous les **texte** complets
            for match in re.finditer(bold_pattern, current_content):
                try:
                    # Positions des balises et du contenu
                    full_start = match.start()
                    content_start = match.start(1)
                    content_end = match.end(1)
                    full_end = match.end()

                    # Convertir en positions tkinter
                    tk_full_start = self._char_to_tkinter_position(
                        current_content, full_start
                    )
                    tk_content_start = self._char_to_tkinter_position(
                        current_content, content_start
                    )
                    tk_content_end = self._char_to_tkinter_position(
                        current_content, content_end
                    )
                    tk_full_end = self._char_to_tkinter_position(
                        current_content, full_end
                    )

                    if all(
                        [tk_full_start, tk_content_start, tk_content_end, tk_full_end]
                    ):
                        # Supprimer les anciens tags sur cette zone
                        text_widget.tag_remove("bold", tk_full_start, tk_full_end)
                        text_widget.tag_remove("hidden", tk_full_start, tk_full_end)
                        text_widget.tag_remove("normal", tk_full_start, tk_full_end)

                        # Configurer les tags s'ils n'existent pas
                        text_widget.tag_configure(
                            "bold",
                            font=("Segoe UI", 12, "bold"),
                            foreground=self.colors["text_primary"],
                        )
                        text_widget.tag_configure("hidden", elide=True)

                        # Appliquer le formatage : cacher ** et mettre en gras le contenu
                        text_widget.tag_add(
                            "hidden", tk_full_start, tk_content_start
                        )  # Cacher **
                        text_widget.tag_add(
                            "bold", tk_content_start, tk_content_end
                        )  # Gras
                        text_widget.tag_add(
                            "hidden", tk_content_end, tk_full_end
                        )  # Cacher **

                        print(f"[DEBUG] Formaté en gras: {match.group(1)}")

                except Exception as e:
                    print(f"[DEBUG] Erreur formatage match: {e}")
                    continue

            # Pattern pour *texte* italique (pas **texte**)
            italic_pattern = r"(?<!\*)\*([^*\n]{1,50}?)\*(?!\*)"

            for match in re.finditer(italic_pattern, current_content):
                try:
                    full_start = match.start()
                    content_start = match.start(1)
                    content_end = match.end(1)
                    full_end = match.end()

                    tk_full_start = self._char_to_tkinter_position(
                        current_content, full_start
                    )
                    tk_content_start = self._char_to_tkinter_position(
                        current_content, content_start
                    )
                    tk_content_end = self._char_to_tkinter_position(
                        current_content, content_end
                    )
                    tk_full_end = self._char_to_tkinter_position(
                        current_content, full_end
                    )

                    if all(
                        [tk_full_start, tk_content_start, tk_content_end, tk_full_end]
                    ):
                        # Nettoyer la zone
                        text_widget.tag_remove("italic", tk_full_start, tk_full_end)
                        text_widget.tag_remove("hidden", tk_full_start, tk_full_end)

                        # Configurer tag italique
                        text_widget.tag_configure(
                            "italic",
                            font=("Segoe UI", 12, "italic"),
                            foreground=self.colors["text_primary"],
                        )

                        # Appliquer : cacher * et mettre en italique
                        text_widget.tag_add("hidden", tk_full_start, tk_content_start)
                        text_widget.tag_add("italic", tk_content_start, tk_content_end)
                        text_widget.tag_add("hidden", tk_content_end, tk_full_end)

                        print(f"[DEBUG] Formaté en italique: {match.group(1)}")

                except Exception:
                    continue

        except Exception as e:
            print(f"[DEBUG] Erreur formatage immédiat: {e}")

    def _is_in_incomplete_code_block(self, text):
        """Détecte si le texte contient un bloc de code incomplet (tous langages)"""
        # Langages supportés
        supported_languages = [
            "python",
            "javascript",
            "js",
            "html",
            "xml",
            "css",
            "bash",
            "shell",
            "sh",
            "sql",
            "mysql",
            "postgresql",
            "sqlite",
            "dockerfile",
            "docker",
            "json",
        ]

        for lang in supported_languages:
            # Compter les balises d'ouverture et de fermeture pour ce langage
            opening_pattern = rf"```{lang}\b"
            opening_tags = len(re.findall(opening_pattern, text, re.IGNORECASE))

            if opening_tags > 0:
                # Compter les fermetures après chaque ouverture
                closing_tags = len(
                    re.findall(r"```(?!\w)", text)
                )  # ``` non suivi d'une lettre

                # Si on a plus d'ouvertures que de fermetures, on est dans un bloc incomplet
                if opening_tags > closing_tags:
                    # Vérifier si le dernier bloc ouvert est complet
                    last_opening = text.rfind(f"```{lang}")
                    if last_opening == -1:
                        # Essayer avec case insensitive
                        for match in re.finditer(opening_pattern, text, re.IGNORECASE):
                            last_opening = match.start()

                    if last_opening != -1:
                        # Vérifier s'il y a une balise de fermeture après
                        text_after_opening = text[last_opening + len(f"```{lang}") :]
                        has_closing = "```" in text_after_opening

                        # Si pas de fermeture OU si le texte finit par une fermeture partielle
                        if not has_closing or text_after_opening.rstrip().endswith(
                            "``"
                        ):
                            return True

        return False

    def _insert_text_with_safe_formatting(self, text_widget, text):
        """Formatage sécurisé qui ne traite que les blocs de code complets (tous langages)"""
        # 🔧 STRATÉGIE : Séparer le texte en deux parties
        # 1. La partie avec blocs complets qu'on peut formatter
        # 2. La partie avec bloc incomplet qu'on affiche en texte brut
        # Pattern pour tous les langages supportés
        supported_languages = [
            "python",
            "javascript",
            "js",
            "html",
            "xml",
            "css",
            "bash",
            "shell",
            "sh",
            "sql",
            "mysql",
            "postgresql",
            "sqlite",
            "dockerfile",
            "docker",
            "json",
        ]
        languages_pattern = "|".join(supported_languages)

        # Trouver tous les blocs de code complets (tous langages)
        complete_blocks_pattern = rf"```({languages_pattern})\n?(.*?)```"
        matches = list(
            re.finditer(complete_blocks_pattern, text, re.DOTALL | re.IGNORECASE)
        )

        if not matches:
            # Pas de blocs complets, vérifier s'il y a un bloc en cours
            incomplete_pattern = rf"```({languages_pattern})\b"
            if re.search(incomplete_pattern, text, re.IGNORECASE):
                # Il y a un bloc en cours mais incomplet
                # Trouver où commence le bloc incomplet
                incomplete_match = None
                for match in re.finditer(incomplete_pattern, text, re.IGNORECASE):
                    incomplete_match = match

                if incomplete_match:
                    incomplete_start = incomplete_match.start()
                    # Formatter la partie avant le bloc incomplet
                    text_before_incomplete = text[:incomplete_start]
                    incomplete_part = text[incomplete_start:]

                    if text_before_incomplete:
                        self._insert_markdown_segments(
                            text_widget, text_before_incomplete
                        )

                    # Afficher la partie incomplète en texte brut (sans formatage)
                    text_widget.insert("end", incomplete_part, "normal")
                    return

            # Pas de blocs de code du tout, formatage normal
            self._insert_markdown_segments(text_widget, text)
            return

        # Il y a des blocs complets, les traiter normalement
        last_end = 0

        for match in matches:
            # Formatter le texte avant ce bloc
            if match.start() > last_end:
                text_before = text[last_end : match.start()]
                self._insert_markdown_segments(text_widget, text_before)

            # Afficher le bloc complet avec formatage
            block_text = match.group(0)  # Le bloc complet avec ```language```
            self._insert_markdown_segments(text_widget, block_text)

            last_end = match.end()

        # Traiter le reste du texte après le dernier bloc complet
        if last_end < len(text):
            remaining_text = text[last_end:]

            # Vérifier si le reste contient un bloc incomplet
            incomplete_pattern = rf"```({languages_pattern})\b"
            incomplete_match = re.search(
                incomplete_pattern, remaining_text, re.IGNORECASE
            )

            if incomplete_match:
                incomplete_start = incomplete_match.start()
                text_before_incomplete = remaining_text[:incomplete_start]
                incomplete_part = remaining_text[incomplete_start:]

                if text_before_incomplete:
                    self._insert_markdown_segments(text_widget, text_before_incomplete)

                # Afficher la partie incomplète sans formatage
                text_widget.insert("end", incomplete_part, "normal")
            else:
                # Pas de bloc incomplet, formatage normal
                self._insert_markdown_segments(text_widget, remaining_text)

    def _char_to_tkinter_position(self, text, char_index):
        """Convertit un index de caractère en position Tkinter (ligne.colonne)"""
        try:
            if char_index < 0 or char_index > len(text):
                return None

            lines_before = text[:char_index].split("\n")
            line_num = len(lines_before)
            char_num = len(lines_before[-1]) if lines_before else 0

            return f"{line_num}.{char_num}"
        except Exception:
            return None

    def _insert_markdown_segments(self, text_widget, text, _code_blocks=None):
        """Insère du texte avec formatage markdown amélioré - Support optimal des blocs ```python```"""
        # Debug pour voir si le formatage est appliqué
        if "```python" in text:
            print("[DEBUG] Bloc Python détecté dans le texte")

        # Pattern amélioré pour détecter les blocs de code avec langage
        # CORRECTION: Capturer aussi les + pour c++, et # pour c#
        code_block_pattern = r"```([\w+#-]+)?\n?(.*?)```"

        current_pos = 0

        # Traiter chaque bloc de code trouvé
        for match in re.finditer(code_block_pattern, text, re.DOTALL):
            # Insérer le texte avant le bloc de code
            if match.start() > current_pos:
                pre_text = text[current_pos : match.start()]
                self._insert_simple_markdown(text_widget, pre_text)

            # Extraire les informations du bloc de code
            language = match.group(1) or "text"
            code_content = match.group(2).strip()

            print(
                f"[DEBUG] Bloc de code détecté - Langage: {language}, Contenu: {len(code_content)} caractères"
            )

            # Traitement spécialisé selon le langage
            if language.lower() == "python":
                text_widget.insert("end", "\n")
                self._insert_python_code_block_with_syntax_highlighting(
                    text_widget, code_content
                )
                text_widget.insert("end", "\n")
            elif language.lower() in ["javascript", "js"]:
                self._insert_javascript_code_block(text_widget, code_content)
            elif language.lower() in ["html", "xml"]:
                self._insert_html_code_block(text_widget, code_content)
            elif language.lower() == "css":
                self._insert_css_code_block(text_widget, code_content)
            elif language.lower() in ["bash", "shell", "sh"]:
                self._insert_bash_code_block(text_widget, code_content)
            elif language.lower() in ["sql", "mysql", "postgresql", "sqlite"]:
                self._insert_sql_code_block(text_widget, code_content)
            elif language.lower() in ["dockerfile", "docker"]:
                self._insert_dockerfile_code_block(text_widget, code_content)
            elif language.lower() in ["json"]:
                self._insert_json_code_block(text_widget, code_content)
            else:
                # Bloc de code générique
                text_widget.insert("end", "\n")
                text_widget.insert("end", code_content, "code_block")
                text_widget.insert("end", "\n")

            current_pos = match.end()

        # Insérer le texte restant après le dernier bloc
        if current_pos < len(text):
            remaining_text = text[current_pos:]
            self._insert_simple_markdown(text_widget, remaining_text)

    def _insert_python_code_block_with_syntax_highlighting(self, text_widget, code):
        """Version optimisée pour la coloration syntaxique Python avec support VS Code"""
        try:
            code = code.strip()
            if not code:
                return

            lexer = PythonLexer()

            print(f"[DEBUG] Traitement Pygments du code Python: {len(code)} caractères")

            # Appliquer la coloration avec Pygments
            for token_type, value in lex(code, lexer):
                if not value.strip() and value != "\n":
                    text_widget.insert("end", value, "mono")
                else:
                    tag_name = str(token_type)
                    text_widget.insert("end", value, tag_name)

            print("[DEBUG] Coloration Pygments appliquée avec succès")

        except ImportError:
            print("[DEBUG] Pygments non disponible, utilisation du fallback")
            self._insert_python_code_fallback_enhanced(text_widget, code)
        except Exception as e:
            print(f"[DEBUG] Erreur Pygments: {e}, utilisation du fallback")
            self._insert_python_code_fallback_enhanced(text_widget, code)

    def _insert_python_code_fallback_enhanced(self, text_widget, code):
        """Fallback amélioré avec reconnaissance étendue des patterns Python"""
        code = code.strip()
        if not code:
            return

        # Builtins Python étendus
        python_builtins = {
            "print",
            "len",
            "str",
            "int",
            "float",
            "list",
            "dict",
            "set",
            "tuple",
            "range",
            "enumerate",
            "zip",
            "map",
            "filter",
            "sorted",
            "reversed",
            "sum",
            "min",
            "max",
            "abs",
            "round",
            "pow",
            "divmod",
            "isinstance",
            "issubclass",
            "hasattr",
            "getattr",
            "setattr",
            "delattr",
            "vars",
            "dir",
            "type",
            "id",
            "callable",
            "iter",
            "next",
            "open",
            "input",
        }

        lines = code.split("\n")

        for i, line in enumerate(lines):
            if i > 0:
                text_widget.insert("end", "\n", "mono")

            # Tokenisation améliorée avec regex plus précise
            token_pattern = r'''
                (""".*?"""|\'\'\'.*?\'\'\')|  # Triple quotes (docstrings)
                ("#.*$)|                      # Comments
                ("(?:[^"\\]|\\.)*")|         # Double quoted strings
                ('(?:[^'\\]|\\.)*')|         # Single quoted strings
                (\b\d+\.?\d*\b)|             # Numbers
                (\b[a-zA-Z_]\w*\b)|          # Identifiers
                ([+\-*/%=<>!&|^~]|//|\*\*|==|!=|<=|>=|<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=)|  # Operators
                ([\(\)\[\]{},;:.])           # Punctuation
            '''

            tokens = re.findall(token_pattern, line, re.VERBOSE | re.DOTALL)

            pos = 0
            for token_groups in tokens:
                # Trouver quel groupe a matché
                token = next(t for t in token_groups if t)

                # Insérer les espaces avant le token si nécessaire
                token_start = line.find(token, pos)
                if token_start > pos:
                    text_widget.insert("end", line[pos:token_start], "mono")

                # Appliquer la coloration selon le type de token
                if token.startswith('"""') or token.startswith("'''"):
                    text_widget.insert("end", token, "Token.Literal.String.Doc")
                elif token.startswith("#"):
                    text_widget.insert("end", token, "Token.Comment")
                elif token.startswith(('"', "'")):
                    text_widget.insert("end", token, "Token.Literal.String")
                elif token in keyword.kwlist:
                    text_widget.insert("end", token, "Token.Keyword")
                elif token in ["True", "False", "None"]:
                    text_widget.insert("end", token, "Token.Keyword.Constant")
                elif token in python_builtins:
                    text_widget.insert("end", token, "Token.Name.Builtin")
                elif re.match(r"^\d+\.?\d*$", token):
                    text_widget.insert("end", token, "Token.Literal.Number")
                elif re.match(
                    r"^[+\-*/%=<>!&|^~]|//|\*\*|==|!=|<=|>=|<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=",
                    token,
                ):
                    text_widget.insert("end", token, "Token.Operator")
                elif re.match(r"^[\(\)\[\]{},;:.]$", token):
                    text_widget.insert("end", token, "Token.Punctuation")
                elif re.match(r"^[a-zA-Z_]\w*$", token):
                    # Détection des fonctions (suivies de '(')
                    remaining = line[token_start + len(token) :].lstrip()
                    if remaining.startswith("("):
                        text_widget.insert("end", token, "Token.Name.Function")
                    else:
                        text_widget.insert("end", token, "Token.Name")
                else:
                    text_widget.insert("end", token, "mono")

                pos = token_start + len(token)

            # Insérer le reste de la ligne
            if pos < len(line):
                text_widget.insert("end", line[pos:], "mono")

    def _insert_link_with_callback(self, text_widget, link_text, url, link_count):
        """Insère un lien avec callback et formatage"""
        start_index = text_widget.index("end-1c")
        text_widget.insert("end", link_text, ("link",))
        end_index = text_widget.index("end-1c")

        # Créer un tag unique pour ce lien
        tag_name = f"link_{link_count}"
        text_widget.tag_add(tag_name, start_index, end_index)

        # Configuration du tag
        text_widget.tag_configure(
            tag_name, foreground="#3b82f6", underline=True, font=("Segoe UI", 12)
        )

        # Callback pour ouvrir le lien
        def create_callback(target_url):
            def on_click(_event):
                try:
                    clean_url = str(target_url).strip()
                    if clean_url.startswith(("http://", "https://")):
                        webbrowser.open(clean_url)
                    return "break"
                except Exception as e:
                    print(f"[DEBUG] Erreur ouverture lien: {e}")
                    return "break"

            return on_click

        # Bind des événements
        callback = create_callback(url)
        text_widget.tag_bind(tag_name, "<Button-1>", callback)
        text_widget.tag_bind(
            tag_name, "<Enter>", lambda e: text_widget.configure(cursor="hand2")
        )
        text_widget.tag_bind(
            tag_name, "<Leave>", lambda e: text_widget.configure(cursor="xterm")
        )

        # Assurer la priorité du tag
        text_widget.tag_raise(tag_name)

    def _process_links_preserve_formatting(self, text, text_widget):
        """Traite les liens tout en préservant le formatage du reste du texte"""
        # Configuration des liens
        text_widget.tag_configure(
            "link", foreground="#3b82f6", underline=True, font=("Segoe UI", 12)
        )

        # Pattern pour liens Markdown : [texte](url)
        markdown_link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        # Pattern pour liens HTTP directs
        http_link_pattern = r"(https?://[^\s\)]+)"

        # Combinaison des patterns
        combined_pattern = (
            f"(?P<markdown>{markdown_link_pattern})|(?P<direct>{http_link_pattern})"
        )

        processed_text = text
        link_count = 0

        # Remplacer les liens par des marqueurs temporaires pour éviter les conflits
        link_replacements = {}

        for match in re.finditer(combined_pattern, text):
            if match.group("markdown"):
                # Lien Markdown [texte](url)
                markdown_match = re.match(
                    markdown_link_pattern, match.group("markdown")
                )
                if markdown_match:
                    link_text = markdown_match.group(1)
                    url = markdown_match.group(2)

                    if url and url.strip() and url != "None":
                        # Créer un marqueur unique
                        marker = f"__LINK_MARKER_{link_count}__"
                        link_replacements[marker] = {
                            "text": link_text,
                            "url": url,
                            "original": match.group(0),
                        }

                        # Remplacer dans le texte
                        processed_text = processed_text.replace(
                            match.group(0), marker, 1
                        )
                        link_count += 1

            elif match.group("direct"):
                # Lien direct HTTP
                url = match.group("direct")
                link_text = url if len(url) <= 50 else url[:47] + "..."

                if url and url.strip():
                    marker = f"__LINK_MARKER_{link_count}__"
                    link_replacements[marker] = {
                        "text": link_text,
                        "url": url,
                        "original": match.group(0),
                    }

                    processed_text = processed_text.replace(match.group(0), marker, 1)
                    link_count += 1

        # Programmer l'insertion des liens après que le texte soit inséré
        def insert_links_after():
            try:
                current_content = text_widget.get("1.0", "end-1c")

                for marker, link_info in link_replacements.items():
                    if marker in current_content:
                        # Trouver la position du marqueur
                        start_pos = current_content.find(marker)
                        if start_pos != -1:
                            # Calculer les positions tkinter
                            lines_before = current_content[:start_pos].count("\n")
                            chars_in_line = len(
                                current_content[:start_pos].split("\n")[-1]
                            )

                            start_index = f"{lines_before + 1}.{chars_in_line}"
                            end_index = (
                                f"{lines_before + 1}.{chars_in_line + len(marker)}"
                            )

                            # Remplacer le marqueur par le texte du lien
                            text_widget.delete(start_index, end_index)
                            text_widget.insert(start_index, link_info["text"])

                            # Calculer la nouvelle position de fin
                            end_index = f"{lines_before + 1}.{chars_in_line + len(link_info['text'])}"

                            # Créer un tag unique pour ce lien
                            tag_name = f"link_{link_count}_{start_pos}"
                            text_widget.tag_add(tag_name, start_index, end_index)

                            # Callback pour ouvrir le lien
                            def create_callback(target_url):
                                def on_click(_event):
                                    try:
                                        webbrowser.open(str(target_url).strip())
                                        print(f"[DEBUG] ✅ Lien ouvert: {target_url}")
                                    except Exception as e:
                                        print(f"[DEBUG] ❌ Erreur ouverture lien: {e}")
                                    return "break"

                                return on_click

                            # Bind des événements
                            callback = create_callback(link_info["url"])
                            text_widget.tag_bind(tag_name, "<Button-1>", callback)
                            text_widget.tag_bind(
                                tag_name,
                                "<Enter>",
                                lambda e: text_widget.configure(cursor="hand2"),
                            )
                            text_widget.tag_bind(
                                tag_name,
                                "<Leave>",
                                lambda e: text_widget.configure(cursor="xterm"),
                            )

                            # Assurer la priorité du tag
                            text_widget.tag_raise(tag_name)

                            # Mettre à jour le contenu pour les prochaines recherches
                            current_content = text_widget.get("1.0", "end-1c")

            except Exception as e:
                print(f"[DEBUG] Erreur insertion liens: {e}")

        # Programmer l'insertion des liens après un délai
        text_widget.after(50, insert_links_after)

        return processed_text

    def _insert_python_code_block_corrected(self, text_widget, code):
        """Version CORRIGÉE de l'insertion de code Python avec Pygments"""
        try:
            code = code.strip("\n")
            lexer = PythonLexer()

            for token_type, value in lex(code, lexer):
                # Utiliser le nom complet du token pour un mapping précis
                tag_name = str(token_type)
                text_widget.insert("end", value, (tag_name,))

            text_widget.insert("end", "\n", ("mono",))

        except Exception as e:
            print(f"Erreur Pygments : {e}")
            # Fallback avec regex amélioré
            self._insert_python_code_fallback(text_widget, code)

    def _insert_python_code_fallback(self, text_widget, code):
        """Fallback amélioré pour la coloration syntaxique"""
        code = code.strip("\n")
        lines = code.split("\n")

        for line in lines:
            # Pattern plus précis pour tokeniser
            pattern = r'(#.*$|"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"[^"]*"|\'[^\']*\'|\b\d+\.?\d*\b|\b\w+\b|[^\w\s]|\s+)'
            tokens = re.findall(pattern, line)

            for token in tokens:
                if not token:
                    continue
                elif token.startswith("#"):
                    text_widget.insert("end", token, ("Token.Comment",))
                elif token.startswith(('"""', "'''")):
                    text_widget.insert("end", token, ("Token.String",))
                elif token.startswith(('"', "'")):
                    text_widget.insert("end", token, ("Token.String",))
                elif token in keyword.kwlist:
                    text_widget.insert("end", token, ("Token.Keyword",))
                elif token in ["True", "False", "None"]:
                    text_widget.insert("end", token, ("Token.Keyword.Constant",))
                elif token in [
                    "print",
                    "len",
                    "str",
                    "int",
                    "float",
                    "list",
                    "dict",
                    "set",
                    "tuple",
                    "range",
                    "enumerate",
                    "zip",
                    "append",
                    "insert",
                    "remove",
                ]:
                    text_widget.insert("end", token, ("Token.Name.Builtin",))
                elif re.match(r"^\d+\.?\d*$", token):
                    text_widget.insert("end", token, ("Token.Number",))
                elif token in [
                    "=",
                    "+",
                    "-",
                    "*",
                    "/",
                    "//",
                    "%",
                    "**",
                    "==",
                    "!=",
                    "<",
                    ">",
                    "<=",
                    ">=",
                ]:
                    text_widget.insert("end", token, ("Token.Operator",))
                elif token.isspace():
                    text_widget.insert("end", token, ("mono",))
                else:
                    text_widget.insert("end", token, ("Token.Name",))

            text_widget.insert("end", "\n", ("mono",))

    def _insert_python_code_block(self, text_widget, code):
        """Insère un bloc de code python avec coloration syntaxique simple"""
        # Utilise Pygments pour une coloration réaliste
        try:
            code = code.strip("\n")
            for token, value in lex(code, PythonLexer()):
                tag = str(token)
                text_widget.insert("end", value, (tag,))
            text_widget.insert("end", "\n", ("mono",))
        except Exception:
            # Fallback simple
            code = code.strip("\n")
            lines = code.split("\n")
            for line in enumerate(lines):
                tokens = re.split(r'(\s+|#.*|"[^"]*"|\'[^\"]*\'|\b\w+\b)', line)
                for token in tokens:
                    if not token:
                        continue
                    if token.startswith("#"):
                        text_widget.insert("end", token, ("py_comment",))
                    elif token.startswith('"') or token.startswith("'"):
                        text_widget.insert("end", token, ("py_string",))
                    elif token in keyword.kwlist:
                        text_widget.insert("end", token, ("py_keyword",))
                    elif token in dir(__builtins__):
                        text_widget.insert("end", token, ("py_builtin",))
                    else:
                        text_widget.insert("end", token, ("mono",))
                text_widget.insert("end", "\n", ("mono",))

    def insert_formatted_text_tkinter(self, text_widget, text):
        """Version AMÉLIORÉE qui gère les liens ET le formatage Python"""
        text_widget.delete("1.0", "end")

        # Configuration complète des tags
        self._configure_all_formatting_tags(text_widget)

        # 🔧 CORRECTION DU TEXTE avant parsing
        text = re.sub(r"^(\s*)Args:\s*$", r"\1**Args:**", text, flags=re.MULTILINE)
        text = re.sub(
            r"^(\s*)Returns:\s*$", r"\1**Returns:**", text, flags=re.MULTILINE
        )
        text = re.sub(r"(?<!\n)(^##\d+\.\s+.*$)", r"\n\1", text, flags=re.MULTILINE)

        # Correction du nom de fichier temporaire
        temp_file_match = re.search(
            r'Explication détaillée du fichier [`"]?(tmp\w+\.py)[`"]?', text
        )
        if temp_file_match and hasattr(self, "conversation_history"):
            for hist in reversed(self.conversation_history):
                if "text" in hist and isinstance(hist["text"], str):
                    real_file = re.search(r"document: '([\w\-.]+\.py)'", hist["text"])
                    if real_file:
                        text = text.replace(
                            temp_file_match.group(1), real_file.group(1)
                        )
                        break
            else:
                py_files = [f for f in os.listdir(".") if f.endswith(".py")]
                if py_files:
                    text = text.replace(temp_file_match.group(1), py_files[0])

        # 🔧 NOUVEAU : Traitement des liens AVANT le parsing général
        text_with_links_processed = self._process_links_preserve_formatting(
            text, text_widget
        )

        # 🔧 UTILISATION DU NOUVEAU SYSTÈME DE FORMATAGE AMÉLIORÉ
        self._insert_markdown_segments(text_widget, text_with_links_processed)

        text_widget.update_idletasks()

    def _configure_all_formatting_tags(self, text_widget):
        """Configure TOUS les tags de formatage - Version unifiée et optimisée"""
        base_font = ("Segoe UI", 12)

        # === TAGS DE FORMATAGE UNIFIÉ ===
        text_widget.tag_configure(
            "normal", font=base_font, foreground=self.colors["text_primary"]
        )
        text_widget.tag_configure(
            "bold",
            font=("Segoe UI", 12, "bold"),
            foreground=self.colors["text_primary"],
        )
        text_widget.tag_configure(
            "italic",
            font=("Segoe UI", 12, "italic"),
            foreground=self.colors["text_primary"],
        )
        text_widget.tag_configure("code", font=("Consolas", 11), foreground="#f8f8f2")

        # === TAGS DE TITRES ===
        text_widget.tag_configure(
            "title_1",
            font=("Segoe UI", 15, "bold"),
            foreground=self.colors["text_primary"],
        )  # Réduit de 18 à 16
        text_widget.tag_configure(
            "title_2",
            font=("Segoe UI", 13, "bold"),
            foreground=self.colors["text_primary"],
        )  # Réduit de 16 à 14
        text_widget.tag_configure(
            "title_3",
            font=("Segoe UI", 13, "bold"),
            foreground=self.colors["text_primary"],
        )

        # === TAGS SPÉCIAUX ===
        text_widget.tag_configure(
            "link", foreground="#3b82f6", underline=1, font=base_font
        )
        text_widget.tag_configure(
            "link_temp", foreground="#3b82f6", underline=1, font=base_font
        )  # Lien pendant animation - même style que link
        text_widget.tag_configure(
            "docstring", font=("Consolas", 11, "italic"), foreground="#ff8c00"
        )
        text_widget.tag_configure("hidden", elide=True)  # Pour masquer les balises

        # === TAG CODE_BLOCK (pour le code générique et whitespace) ===
        text_widget.tag_configure(
            "code_block", font=("Consolas", 11), foreground="#d4d4d4"
        )
        text_widget.tag_configure("code_block_marker", elide=True)  # Masquer les ```

        # === TAGS PYTHON (compatibilité) ===
        python_tags = {
            "Token.Keyword": ("#569cd6", "bold"),
            "Token.Keyword.Constant": ("#569cd6", "bold"),
            "Token.Keyword.Declaration": ("#569cd6", "bold"),
            "Token.Keyword.Namespace": ("#569cd6", "bold"),
            "Token.Keyword.Pseudo": ("#569cd6", "bold"),
            "Token.Keyword.Reserved": ("#569cd6", "bold"),
            "Token.Keyword.Type": ("#4ec9b0", "bold"),
            "Token.Literal.String": ("#ce9178", "normal"),
            "Token.Literal.String.Double": ("#ce9178", "normal"),
            "Token.Literal.String.Single": ("#ce9178", "normal"),
            "Token.String": ("#ce9178", "normal"),
            "Token.String.Double": ("#ce9178", "normal"),
            "Token.String.Single": ("#ce9178", "normal"),
            "Token.Comment": ("#6a9955", "italic"),
            "Token.Comment.Single": ("#6a9955", "italic"),
            "Token.Comment.Multiline": ("#6a9955", "italic"),
            "Token.Name.Function": ("#dcdcaa", "normal"),
            "Token.Name.Function.Magic": ("#dcdcaa", "normal"),
            "Token.Name.Class": ("#4ec9b0", "bold"),
            "Token.Name.Builtin": ("#dcdcaa", "normal"),
            "Token.Name.Builtin.Pseudo": ("#dcdcaa", "normal"),
            "Token.Literal.Number": ("#b5cea8", "normal"),
            "Token.Literal.Number.Integer": ("#b5cea8", "normal"),
            "Token.Literal.Number.Float": ("#b5cea8", "normal"),
            "Token.Number": ("#b5cea8", "normal"),
            "Token.Number.Integer": ("#b5cea8", "normal"),
            "Token.Number.Float": ("#b5cea8", "normal"),
            "Token.Operator": ("#d4d4d4", "normal"),
            "Token.Punctuation": ("#d4d4d4", "normal"),
            "Token.Name": ("#9cdcfe", "normal"),
            "Token.Name.Variable": ("#9cdcfe", "normal"),
            "Token.Name.Attribute": ("#9cdcfe", "normal"),
            "Token.Name.Constant": ("#569cd6", "bold"),
        }

        for tag, (color, weight) in python_tags.items():
            if weight == "bold":
                text_widget.tag_configure(
                    tag, foreground=color, font=("Consolas", 11, "bold")
                )
            elif weight == "italic":
                text_widget.tag_configure(
                    tag, foreground=color, font=("Consolas", 11, "italic")
                )
            else:
                text_widget.tag_configure(tag, foreground=color, font=("Consolas", 11))

        # === TAGS POUR AUTRES LANGAGES VS CODE ===

        # JavaScript tags
        js_tags = {
            "js_keyword": (
                "#569cd6",
                "bold",
            ),  # var, let, const, function, if, else, etc.
            "js_string": ("#ce9178", "normal"),  # Chaînes de caractères
            "js_comment": ("#6a9955", "italic"),  # Commentaires
            "js_number": ("#b5cea8", "normal"),  # Nombres
            "js_function": ("#dcdcaa", "normal"),  # Noms de fonctions
            "js_operator": ("#d4d4d4", "normal"),  # Opérateurs
            "js_punctuation": ("#d4d4d4", "normal"),  # Ponctuation
            "js_variable": ("#9cdcfe", "normal"),  # Variables
            "js_property": ("#9cdcfe", "normal"),  # Propriétés d'objets
        }

        # CSS tags
        css_tags = {
            "css_selector": ("#d7ba7d", "normal"),  # Sélecteurs CSS
            "css_property": ("#9cdcfe", "normal"),  # Propriétés CSS
            "css_value": ("#ce9178", "normal"),  # Valeurs
            "css_comment": ("#6a9955", "italic"),  # Commentaires
            "css_number": ("#b5cea8", "normal"),  # Nombres/unités
            "css_string": ("#ce9178", "normal"),  # Chaînes
            "css_punctuation": ("#d4d4d4", "normal"),  # Ponctuation
            "css_pseudo": ("#dcdcaa", "normal"),  # Pseudo-classes/éléments
            "css_unit": ("#b5cea8", "normal"),  # Unités (px, em, etc.)
        }

        # HTML tags
        html_tags = {
            "html_tag": ("#569cd6", "bold"),  # Balises HTML
            "html_attribute": ("#9cdcfe", "normal"),  # Attributs
            "html_value": ("#ce9178", "normal"),  # Valeurs d'attributs
            "html_comment": ("#6a9955", "italic"),  # Commentaires
            "html_text": ("#d4d4d4", "normal"),  # Texte contenu
            "html_punctuation": ("#d4d4d4", "normal"),  # < > = " /
            "Token.Name.Tag": ("#569cd6", "bold"),  # Balises HTML
            "Token.Name.Entity": ("#dcdcaa", "normal"),  # Entités HTML
        }

        # Bash/Shell tags
        bash_tags = {
            "bash_keyword": ("#569cd6", "bold"),  # if, then, else, fi, for, while, etc.
            "bash_command": ("#dcdcaa", "normal"),  # Commandes
            "bash_string": ("#ce9178", "normal"),  # Chaînes
            "bash_comment": ("#6a9955", "italic"),  # Commentaires
            "bash_variable": ("#9cdcfe", "normal"),  # Variables $VAR
            "bash_operator": ("#d4d4d4", "normal"),  # Opérateurs
            "bash_number": ("#b5cea8", "normal"),  # Nombres
            "bash_punctuation": ("#d4d4d4", "normal"),  # Ponctuation
            "Token.Name.Variable": ("#9cdcfe", "normal"),  # Variables
        }

        # SQL tags
        sql_tags = {
            "sql_keyword": ("#569cd6", "bold"),  # SELECT, FROM, WHERE, etc.
            "sql_function": ("#dcdcaa", "normal"),  # COUNT, SUM, etc.
            "sql_string": ("#ce9178", "normal"),  # Chaînes
            "sql_comment": ("#6a9955", "italic"),  # Commentaires
            "sql_number": ("#b5cea8", "normal"),  # Nombres
            "sql_operator": ("#d4d4d4", "normal"),  # =, >, <, etc.
            "sql_punctuation": ("#d4d4d4", "normal"),  # Ponctuation
            "sql_identifier": ("#9cdcfe", "normal"),  # Noms de tables/colonnes
        }

        # Dockerfile tags
        dockerfile_tags = {
            "dockerfile_instruction": ("#569cd6", "bold"),  # FROM, RUN, COPY, etc.
            "dockerfile_string": ("#ce9178", "normal"),  # Chaînes
            "dockerfile_comment": ("#6a9955", "italic"),  # Commentaires
            "dockerfile_variable": ("#9cdcfe", "normal"),  # Variables ${}
            "dockerfile_path": ("#ce9178", "normal"),  # Chemins de fichiers
            "dockerfile_flag": ("#dcdcaa", "normal"),  # Flags --from, etc.
        }

        # Java tags
        java_tags = {
            "java_keyword": ("#569cd6", "bold"),
            "java_string": ("#ce9178", "normal"),
            "java_comment": ("#6a9955", "italic"),
            "java_number": ("#b5cea8", "normal"),
            "java_class": ("#4ec9b0", "normal"),
            "java_method": ("#dcdcaa", "normal"),
            "java_annotation": ("#dcdcaa", "normal"),
        }

        # C++ tags
        cpp_tags = {
            "cpp_keyword": ("#569cd6", "bold"),
            "cpp_string": ("#ce9178", "normal"),
            "cpp_comment": ("#6a9955", "italic"),
            "cpp_number": ("#b5cea8", "normal"),
            "cpp_preprocessor": ("#c586c0", "normal"),
            "cpp_type": ("#4ec9b0", "normal"),
            "cpp_function": ("#dcdcaa", "normal"),
        }

        # C tags (mêmes couleurs que C++)
        c_tags = {
            "c_keyword": ("#569cd6", "bold"),
            "c_string": ("#ce9178", "normal"),
            "c_comment": ("#6a9955", "italic"),
            "c_number": ("#b5cea8", "normal"),
            "c_preprocessor": ("#c586c0", "normal"),
            "c_type": ("#4ec9b0", "normal"),
            "c_function": ("#dcdcaa", "normal"),
        }

        # C# tags
        csharp_tags = {
            "csharp_keyword": ("#569cd6", "bold"),
            "csharp_string": ("#ce9178", "normal"),
            "csharp_comment": ("#6a9955", "italic"),
            "csharp_number": ("#b5cea8", "normal"),
            "csharp_class": ("#4ec9b0", "normal"),
            "csharp_method": ("#dcdcaa", "normal"),
        }

        # Go tags
        go_tags = {
            "go_keyword": ("#569cd6", "bold"),
            "go_string": ("#ce9178", "normal"),
            "go_comment": ("#6a9955", "italic"),
            "go_number": ("#b5cea8", "normal"),
            "go_type": ("#4ec9b0", "normal"),
            "go_function": ("#dcdcaa", "normal"),
            "go_package": ("#c586c0", "normal"),
        }

        # Ruby tags
        ruby_tags = {
            "ruby_keyword": ("#569cd6", "bold"),
            "ruby_string": ("#ce9178", "normal"),
            "ruby_comment": ("#6a9955", "italic"),
            "ruby_number": ("#b5cea8", "normal"),
            "ruby_symbol": ("#d7ba7d", "normal"),
            "ruby_method": ("#dcdcaa", "normal"),
            "ruby_class": ("#4ec9b0", "normal"),
            "ruby_variable": ("#9cdcfe", "normal"),
        }

        # Swift tags
        swift_tags = {
            "swift_keyword": ("#569cd6", "bold"),
            "swift_string": ("#ce9178", "normal"),
            "swift_comment": ("#6a9955", "italic"),
            "swift_number": ("#b5cea8", "normal"),
            "swift_type": ("#4ec9b0", "normal"),
            "swift_function": ("#dcdcaa", "normal"),
            "swift_attribute": ("#dcdcaa", "normal"),
        }

        # PHP tags
        php_tags = {
            "php_keyword": ("#569cd6", "bold"),
            "php_string": ("#ce9178", "normal"),
            "php_comment": ("#6a9955", "italic"),
            "php_number": ("#b5cea8", "normal"),
            "php_variable": ("#9cdcfe", "normal"),
            "php_function": ("#dcdcaa", "normal"),
            "php_tag": ("#569cd6", "bold"),
        }

        # Perl tags
        perl_tags = {
            "perl_keyword": ("#569cd6", "bold"),
            "perl_string": ("#ce9178", "normal"),
            "perl_comment": ("#6a9955", "italic"),
            "perl_number": ("#b5cea8", "normal"),
            "perl_variable": ("#9cdcfe", "normal"),
            "perl_regex": ("#d16969", "normal"),
        }

        # Rust tags
        rust_tags = {
            "rust_keyword": ("#569cd6", "bold"),
            "rust_string": ("#ce9178", "normal"),
            "rust_comment": ("#6a9955", "italic"),
            "rust_number": ("#b5cea8", "normal"),
            "rust_type": ("#4ec9b0", "normal"),
            "rust_function": ("#dcdcaa", "normal"),
            "rust_macro": ("#c586c0", "normal"),
            "rust_lifetime": ("#569cd6", "italic"),
        }

        # Configuration de tous les tags
        all_language_tags = {
            **js_tags,
            **css_tags,
            **html_tags,
            **bash_tags,
            **sql_tags,
            **dockerfile_tags,
            **java_tags,
            **cpp_tags,
            **c_tags,
            **csharp_tags,
            **go_tags,
            **ruby_tags,
            **swift_tags,
            **php_tags,
            **perl_tags,
            **rust_tags,
        }

        for tag, (color, weight) in all_language_tags.items():
            if weight == "bold":
                text_widget.tag_configure(
                    tag, foreground=color, font=("Consolas", 11, "bold")
                )
            elif weight == "italic":
                text_widget.tag_configure(
                    tag, foreground=color, font=("Consolas", 11, "italic")
                )
            else:
                text_widget.tag_configure(tag, foreground=color, font=("Consolas", 11))

        text_widget.tag_configure(
            "code_block",
            font=("Consolas", 11),
            foreground="#d4d4d4",
        )

        # Tags pour les tableaux Markdown
        text_widget.tag_configure(
            "table_header",
            font=("Segoe UI", 11, "bold"),
            foreground="#58a6ff",
            background="#1a1a2e",
        )
        text_widget.tag_configure(
            "table_cell",
            font=("Segoe UI", 11),
            foreground="#e6e6e6",
            background="#16213e",
        )
        text_widget.tag_configure(
            "table_border",
            font=("Consolas", 11),
            foreground="#444466",
        )
        text_widget.tag_configure(
            "table_cell_bold",
            font=("Segoe UI", 11, "bold"),
            foreground="#ffd700",
            background="#16213e",
        )

    def _convert_temp_links_to_clickable(self, text_widget):
        """Convertit les liens temporaires en liens bleus clicables à la fin de l'animation"""
        try:
            if not hasattr(self, "_pending_links"):
                print("[DEBUG] Aucun _pending_links trouvé")
                return

            if not self._pending_links:
                print("[DEBUG] _pending_links est vide")
                return

            print(
                f"[DEBUG] Conversion de {len(self._pending_links)} liens en clickables"
            )
            text_widget.configure(state="normal")

            # Récupérer TOUTES les zones avec le tag link_temp
            ranges = text_widget.tag_ranges("link_temp")

            if not ranges:
                print("[DEBUG] ERREUR: Aucune zone link_temp trouvée")
            else:
                print(f"[DEBUG] {len(ranges)//2} zones link_temp trouvées")
                print(
                    f"[DEBUG] Liens disponibles dans _pending_links: {[(l['title'], l['url'][:50]) for l in self._pending_links]}"
                )

                # Créer un index des liens par titre pour recherche rapide
                # Pour gérer les liens avec le même titre, on utilise une liste
                links_by_title = {}
                for link_data in self._pending_links:
                    title = link_data["title"]
                    if title not in links_by_title:
                        links_by_title[title] = []
                    links_by_title[title].append(link_data["url"])

                # Compteur pour chaque titre (pour gérer les doublons)
                title_usage_count = {}
                link_counter = 0

                # Pour chaque zone link_temp, trouver le lien correspondant
                for i in range(0, len(ranges), 2):
                    start_range = ranges[i]
                    end_range = ranges[i + 1]
                    range_text = text_widget.get(start_range, end_range)

                    # Chercher l'URL correspondante
                    url = None
                    if range_text in links_by_title:
                        # Obtenir l'index d'utilisation pour ce titre
                        usage_idx = title_usage_count.get(range_text, 0)

                        # Si on a plusieurs URLs pour ce titre, utiliser l'index
                        urls_list = links_by_title[range_text]
                        if usage_idx < len(urls_list):
                            url = urls_list[usage_idx]
                            title_usage_count[range_text] = usage_idx + 1
                        else:
                            # Réutiliser la dernière URL si on dépasse
                            url = urls_list[-1]

                    if url:
                        # Créer un tag unique pour ce lien
                        unique_tag = f"clickable_link_{link_counter}"
                        link_counter += 1

                        # Remplacer le tag link_temp par le tag unique
                        text_widget.tag_remove("link_temp", start_range, end_range)
                        text_widget.tag_add(unique_tag, start_range, end_range)

                        # Configurer le style du tag unique
                        text_widget.tag_configure(
                            unique_tag,
                            foreground="#3b82f6",
                            underline=1,
                            font=("Segoe UI", 12),
                        )

                        # CORRECTION CLOSURE : Créer une fonction avec l'URL capturée
                        def create_click_handler(url_to_open):
                            def click_handler(_event):
                                print(f"[DEBUG] Clic sur lien: {url_to_open}")
                                webbrowser.open(url_to_open)
                                return "break"

                            return click_handler

                        # Lier l'événement avec l'URL correcte
                        text_widget.tag_bind(
                            unique_tag, "<Button-1>", create_click_handler(url)
                        )
                        print(
                            f"[DEBUG] Lien configuré: '{range_text}' -> {url} (tag: {unique_tag})"
                        )
                    else:
                        print(
                            f"[DEBUG] WARNING: Aucune URL trouvée pour '{range_text}'"
                        )

        except Exception:
            pass
