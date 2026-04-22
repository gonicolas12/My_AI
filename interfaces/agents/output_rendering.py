"""Mixin : rendu des sections de résultats (markdown, tableaux, coloration)."""

import re
import threading

from interfaces.agents._common import tk
from interfaces.agents.syntax_helper import (
    SYNTAX_ANALYZER,
    SYNTAX_AVAILABLE,
    SyntaxColorHelper,
)


# Commandes LaTeX → équivalents Unicode (flèches, opérateurs, lettres grecques, ensembles).
_LATEX_SYMBOLS = {
    r"\rightarrow": "→", r"\Rightarrow": "⇒",
    r"\leftarrow": "←", r"\Leftarrow": "⇐",
    r"\leftrightarrow": "↔", r"\Leftrightarrow": "⇔",
    r"\longrightarrow": "⟶", r"\longleftarrow": "⟵",
    r"\mapsto": "↦", r"\to": "→", r"\gets": "←",
    r"\implies": "⇒", r"\iff": "⇔",
    r"\uparrow": "↑", r"\downarrow": "↓", r"\updownarrow": "↕",
    r"\times": "×", r"\cdot": "·", r"\div": "÷",
    r"\pm": "±", r"\mp": "∓", r"\ast": "∗", r"\star": "⋆",
    r"\leq": "≤", r"\le": "≤", r"\geq": "≥", r"\ge": "≥",
    r"\neq": "≠", r"\ne": "≠", r"\approx": "≈", r"\equiv": "≡",
    r"\sim": "∼", r"\simeq": "≃", r"\cong": "≅", r"\propto": "∝",
    r"\ll": "≪", r"\gg": "≫",
    r"\infty": "∞", r"\partial": "∂", r"\nabla": "∇",
    r"\sum": "∑", r"\prod": "∏", r"\int": "∫", r"\oint": "∮",
    r"\sqrt": "√", r"\surd": "√",
    r"\forall": "∀", r"\exists": "∃", r"\nexists": "∄",
    r"\in": "∈", r"\notin": "∉", r"\ni": "∋",
    r"\subset": "⊂", r"\supset": "⊃",
    r"\subseteq": "⊆", r"\supseteq": "⊇",
    r"\cup": "∪", r"\cap": "∩", r"\setminus": "∖",
    r"\emptyset": "∅", r"\varnothing": "∅",
    r"\land": "∧", r"\wedge": "∧", r"\lor": "∨", r"\vee": "∨",
    r"\lnot": "¬", r"\neg": "¬",
    r"\top": "⊤", r"\bot": "⊥", r"\vdash": "⊢", r"\models": "⊨",
    r"\ldots": "…", r"\cdots": "⋯", r"\vdots": "⋮", r"\ddots": "⋱",
    r"\circ": "∘", r"\bullet": "•", r"\oplus": "⊕", r"\otimes": "⊗",
    r"\degree": "°",
    # Lettres grecques minuscules
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
    r"\epsilon": "ε", r"\varepsilon": "ε", r"\zeta": "ζ", r"\eta": "η",
    r"\theta": "θ", r"\vartheta": "ϑ", r"\iota": "ι", r"\kappa": "κ",
    r"\lambda": "λ", r"\mu": "μ", r"\nu": "ν", r"\xi": "ξ",
    r"\pi": "π", r"\varpi": "ϖ", r"\rho": "ρ", r"\varrho": "ϱ",
    r"\sigma": "σ", r"\varsigma": "ς", r"\tau": "τ", r"\upsilon": "υ",
    r"\phi": "φ", r"\varphi": "φ", r"\chi": "χ", r"\psi": "ψ", r"\omega": "ω",
    # Lettres grecques majuscules
    r"\Gamma": "Γ", r"\Delta": "Δ", r"\Theta": "Θ", r"\Lambda": "Λ",
    r"\Xi": "Ξ", r"\Pi": "Π", r"\Sigma": "Σ", r"\Upsilon": "Υ",
    r"\Phi": "Φ", r"\Psi": "Ψ", r"\Omega": "Ω",
}

# Trier par longueur décroissante pour que \Rightarrow soit remplacé avant \to, etc.
_LATEX_ORDERED = sorted(_LATEX_SYMBOLS.items(), key=lambda kv: -len(kv[0]))

# Segment `$...$` contenant au moins une commande LaTeX `\word` (évite les faux positifs
# comme "$100 et $200"). Autorise les espaces et autres caractères mais pas de saut de ligne.
_LATEX_INLINE_RE = re.compile(r"\$([^\$\n]*\\[a-zA-Z]+[^\$\n]*)\$")


def _render_latex_symbols(text: str) -> str:
    """Remplace les segments `$...\\cmd...$` par leur équivalent Unicode."""
    if "$" not in text or "\\" not in text:
        return text

    def _replace(match: re.Match) -> str:
        content = match.group(1)
        for cmd, sym in _LATEX_ORDERED:
            content = content.replace(cmd, sym)
        # Supprime les commandes non reconnues (conserve leur nom sans la barre).
        content = re.sub(r"\\([a-zA-Z]+)", r"\1", content)
        return content

    return _LATEX_INLINE_RE.sub(_replace, text)


class OutputRenderingMixin:
    """Gestion des sections dépliantes + formatage Markdown streaming."""

    # ── Section-based output management ────────────────────────────

    def _clear_output_sections(self):
        """Supprime toutes les sections de sortie."""
        for sec in self._output_sections:
            try:
                sec["container"].destroy()
            except Exception:
                pass
        self._output_sections.clear()
        self._active_section = None
        if self._welcome_label:
            try:
                self._welcome_label.destroy()
            except Exception:
                pass
            self._welcome_label = None

    def _create_step_section(self, name, color="#ff6b47", expanded=True):
        """Crée une section dépliante dans la zone de résultats (main thread)."""
        section = {"name": name, "color": color, "expanded": expanded}

        bg1 = self.colors.get("bg_primary", "#0f0f0f")
        bg2 = self.colors.get("bg_secondary", "#1a1a1a")
        bg3 = self.colors.get("bg_tertiary", "#2d2d2d")
        txt2 = self.colors.get("text_secondary", "#9ca3af")

        container = tk.Frame(self._output_scroll, bg=bg1)
        container.pack(fill="x", pady=(0, 6), padx=4)
        section["container"] = container

        # Header (clickable)
        header = tk.Frame(container, bg=bg2, cursor="hand2")
        header.pack(fill="x")

        # Color indicator strip
        indicator = tk.Frame(header, bg=color, width=4)
        indicator.pack(side="left", fill="y")

        # Arrow
        arrow_var = tk.StringVar(value="▾" if expanded else "▸")
        arrow = tk.Label(
            header, textvariable=arrow_var, font=("Segoe UI", 18),
            fg=txt2, bg=bg2, cursor="hand2",
        )
        arrow.pack(side="left", padx=(10, 4), pady=6)
        section["arrow_var"] = arrow_var

        # Name
        name_lbl = tk.Label(
            header, text=name, font=("Segoe UI", 12, "bold"),
            fg="#ffffff", bg=bg2, cursor="hand2",
        )
        name_lbl.pack(side="left", pady=8)

        # Status (right)
        status_var = tk.StringVar(value="⏳ En cours...")
        status_lbl = tk.Label(
            header, textvariable=status_var, font=("Segoe UI", 9),
            fg=txt2, bg=bg2,
        )
        status_lbl.pack(side="right", padx=12, pady=8)
        section["status_var"] = status_var

        # Content frame with agent-colored left border
        border_wrap = tk.Frame(container, bg=color)
        section["border_wrap"] = border_wrap
        if expanded:
            border_wrap.pack(fill="x", padx=(16, 4), pady=(2, 4))

        content = tk.Frame(border_wrap, bg=bg1)
        section["content"] = content
        content.pack(fill="x", padx=(2, 0))

        # Scrollable text area — hauteur max fixe avec scrollbar custom
        text_container = tk.Frame(content, bg=bg1)
        text_container.pack(fill="x")

        tw = tk.Text(
            text_container, wrap="word", font=("Segoe UI", 11),
            bg=bg1, fg=self.colors.get("text_primary", "#ffffff"),
            relief="flat", borderwidth=0, padx=12, pady=10,
            height=3, state="disabled",
            insertbackground=self.colors.get("text_primary", "#ffffff"),
        )
        tw.pack(side="left", fill="both", expand=True)

        # Custom dark scrollbar (canvas-based, matching CTk style)
        sb_width = 6
        sb_canvas = tk.Canvas(
            text_container, width=sb_width + 4, bg=bg1,
            highlightthickness=0, borderwidth=0,
        )
        sb_canvas.pack(side="right", fill="y", padx=(0, 2))
        sb_thumb = sb_canvas.create_rectangle(0, 0, 0, 0, fill=bg3, outline="", width=0)
        section["_sb_canvas"] = sb_canvas
        section["_sb_thumb"] = sb_thumb

        def _update_scrollbar(*args):
            try:
                first, last = float(args[0]), float(args[1])
                if last - first >= 1.0:
                    sb_canvas.coords(sb_thumb, 0, 0, 0, 0)
                    return
                h = sb_canvas.winfo_height()
                y1 = int(first * h)
                y2 = int(last * h)
                x_pad = (sb_width + 4 - sb_width) // 2
                sb_canvas.coords(sb_thumb, x_pad, y1, x_pad + sb_width, y2)
                sb_canvas.itemconfig(sb_thumb, fill=bg3)
            except Exception:
                pass

        tw.configure(yscrollcommand=_update_scrollbar)

        def _sb_drag(event):
            h = sb_canvas.winfo_height()
            if h > 0:
                tw.yview_moveto(event.y / h)

        sb_canvas.bind("<B1-Motion>", _sb_drag)
        sb_canvas.bind("<Button-1>", _sb_drag)

        def _sb_enter(_event):
            sb_canvas.itemconfig(sb_thumb, fill=txt2)
        def _sb_leave(_event):
            sb_canvas.itemconfig(sb_thumb, fill=bg3)
        sb_canvas.bind("<Enter>", _sb_enter)
        sb_canvas.bind("<Leave>", _sb_leave)

        self._setup_markdown_tags(tw)
        section["text_widget"] = tw

        # Mousewheel scrolle le contenu du Text (pas le parent)
        def _text_scroll(event):
            tw.yview_scroll(int(-3 * (event.delta / 120)), "units")
            return "break"
        tw.bind("<MouseWheel>", _text_scroll)
        sb_canvas.bind("<MouseWheel>", _text_scroll)

        # Toggle on click
        def toggle(_event=None):
            self._toggle_section(section)

        for w in (header, arrow, name_lbl):
            w.bind("<Button-1>", toggle)

        self._output_sections.append(section)
        return section

    def _create_step_section_sync(self, name, color="#ff6b47", expanded=True):
        """Thread-safe: crée une section sur le thread principal et attend."""
        result = [None]
        event = threading.Event()

        def create():
            result[0] = self._create_step_section(name, color, expanded)
            event.set()

        if self.parent.winfo_exists():
            self.parent.after(0, create)
            event.wait(timeout=5.0)
        return result[0]

    def _clear_output_sections_sync(self):
        """Thread-safe: efface toutes les sections sur le thread principal."""
        event = threading.Event()

        def clear():
            self._clear_output_sections()
            event.set()

        if self.parent.winfo_exists():
            self.parent.after(0, clear)
            event.wait(timeout=2.0)

    def _create_output_header_sync(self, text):
        """Thread-safe: crée un label d'en-tête dans la zone de résultats."""
        event = threading.Event()

        def create():
            lbl = tk.Label(
                self._output_scroll, text=text, font=("Segoe UI", 10),
                fg=self.colors.get("text_secondary", "#9ca3af"),
                bg=self.colors.get("bg_primary", "#0f0f0f"),
                anchor="w",
            )
            lbl.pack(fill="x", padx=16, pady=(8, 2))
            event.set()

        if self.parent.winfo_exists():
            self.parent.after(0, create)
            event.wait(timeout=2.0)

    def _toggle_section(self, section):
        """Déplie/replie une section."""
        toggle_target = section.get("border_wrap", section["content"])
        if section["expanded"]:
            toggle_target.pack_forget()
            section["arrow_var"].set("▸")
            section["expanded"] = False
        else:
            toggle_target.pack(fill="x", padx=(16, 4), pady=(2, 4))
            section["arrow_var"].set("▾")
            section["expanded"] = True

    def _append_to_section(self, section, text):
        """Ajoute du texte à une section avec formatage Markdown progressif (thread-safe)."""
        if section is None:
            return

        # Initialiser le buffer de ligne si nécessaire
        if "_line_buf" not in section:
            section["_line_buf"] = ""
            section["_in_code_block"] = False
            section["_code_lang"] = ""
            section["_first_line"] = True
            section["_table_buf"] = []  # buffer pour accumuler les lignes de tableau

        section["_line_buf"] += text

        # Extraire et formater les lignes complètes
        while "\n" in section["_line_buf"]:
            line, section["_line_buf"] = section["_line_buf"].split("\n", 1)
            self._format_and_insert_line(section, line, newline=True)

    def _format_and_insert_line(self, section, line, newline=True):  # pylint: disable=unused-argument,W0613
        """Formate et insère une ligne complète avec le bon style Markdown."""
        # Convertit les délimiteurs LaTeX inline (`$\rightarrow$`, etc.) en Unicode
        # avant toute détection de structure (tableau, bullet, etc.).
        line = _render_latex_symbols(line)
        stripped = line.strip()
        table_buf = section.get("_table_buf", [])

        # Détection de ligne de tableau
        is_table_line = ("|" in stripped and stripped.startswith("|") and stripped.endswith("|"))
        is_table_sep = bool(re.match(r'^\s*\|?[\s:]*-{2,}[\s:]*\|', stripped))

        if is_table_line or is_table_sep:
            table_buf.append(line)
            section["_table_buf"] = table_buf
            return  # accumulate, don't render yet

        # Si on avait des lignes de tableau en buffer et qu'on reçoit une non-table line
        if table_buf:
            self._flush_table_buffer(section)

        self._insert_single_line(section, line)

    def _flush_table_buffer(self, section):
        """Rend le tableau accumulé avec box-drawing characters."""
        table_buf = section.get("_table_buf", [])
        if not table_buf:
            return
        section["_table_buf"] = []

        def update():
            tw = section["text_widget"]
            tw.configure(state="normal")

            # Parser toutes les lignes du tableau
            separator_pattern = r'^\s*\|?[\s:]*-{2,}[\s:]*\|'
            data_rows = []
            for tl in table_buf:
                s = tl.strip()
                if re.match(separator_pattern, s):
                    continue  # skip separator
                cells = [c.strip() for c in s.strip("|").split("|")]
                data_rows.append(cells)

            if not data_rows:
                tw.configure(state="disabled")
                return

            # Calculer largeurs de colonnes
            max_cols = max(len(r) for r in data_rows)
            widths = []
            max_col_w = max(10, 100 // max(max_cols, 1) - 3)
            for col in range(max_cols):
                w = 3
                for row in data_rows:
                    if col < len(row):
                        cell_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', row[col])
                        cell_text = re.sub(r'`([^`]+)`', r'\1', cell_text)
                        w = max(w, len(cell_text))
                widths.append(min(w, max_col_w))

            # Newline before table
            if not section.get("_first_line"):
                tw.insert("end", "\n")
            section["_first_line"] = False

            # Top border
            tw.insert("end", "┌" + "┬".join("─" * (w + 2) for w in widths) + "┐", "table_border")

            for row_idx, cells in enumerate(data_rows):
                tw.insert("end", "\n")
                is_header = row_idx == 0

                # Separator after header
                if row_idx == 1:
                    tw.insert("end", "├" + "┼".join("─" * (w + 2) for w in widths) + "┤", "table_border")
                    tw.insert("end", "\n")

                tw.insert("end", "│", "table_border")
                for col_idx, width in enumerate(widths):
                    cell = cells[col_idx] if col_idx < len(cells) else ""
                    # Display length without markdown markers
                    disp = re.sub(r'\*\*([^*]+)\*\*', r'\1', cell)
                    disp = re.sub(r'`([^`]+)`', r'\1', disp)
                    disp_len = len(disp)
                    if disp_len > width:
                        cell = disp[:width - 1] + "…"
                        disp_len = width
                    padding = max(0, width - disp_len)
                    lpad = padding // 2
                    rpad = padding - lpad
                    tw.insert("end", " " + " " * lpad, "table_border")
                    # Insert cell content with inline formatting
                    tag = "table_header" if is_header else "table_cell"
                    self._insert_table_cell(tw, cell, tag)
                    tw.insert("end", " " * rpad + " ", "table_border")
                    tw.insert("end", "│", "table_border")

            # Bottom border
            tw.insert("end", "\n")
            tw.insert("end", "└" + "┴".join("─" * (w + 2) for w in widths) + "┘", "table_border")

            tw.configure(state="disabled")
            self._resize_section_text(tw)
            tw.see("end")
            if section.get("expanded", False):
                self._auto_scroll_output()

        if self.parent.winfo_exists():
            self.parent.after(0, update)

    def _insert_table_cell(self, tw, cell_content, base_tag):
        """Insère le contenu d'une cellule de tableau avec gras/code inline."""
        pattern = r'(\*\*[^*]+\*\*|`[^`]+`)'
        parts = re.split(pattern, cell_content)
        for part in parts:
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                tw.insert("end", part[2:-2], "table_cell_bold")
            elif part.startswith("`") and part.endswith("`"):
                tw.insert("end", part[1:-1], "code_inline")
            else:
                tw.insert("end", part, base_tag)

    def _insert_single_line(self, section, line):
        """Insère une seule ligne formatée (non-table)."""
        def update():
            tw = section["text_widget"]
            tw.configure(state="normal")

            stripped = line.strip()

            # Ajouter un saut de ligne sauf pour la première ligne
            if not section.get("_first_line"):
                tw.insert("end", "\n")
            section["_first_line"] = False

            # Code block markers
            if stripped.startswith("```"):
                if section["_in_code_block"]:
                    section["_in_code_block"] = False
                    section["_code_lang"] = ""
                else:
                    section["_in_code_block"] = True
                    section["_code_lang"] = stripped[3:].strip().lower()
                    # Language label intentionally hidden — used only for highlighting logic
                tw.configure(state="disabled")
                self._resize_section_text(tw)
                return

            if section["_in_code_block"]:
                self._highlight_code_line(tw, line, section.get("_code_lang", ""))
                tw.configure(state="disabled")
                self._resize_section_text(tw)
                return

            # Headers
            if stripped.startswith("#### "):
                tw.insert("end", stripped[5:], "h4")
            elif stripped.startswith("### "):
                tw.insert("end", stripped[4:], "h3")
            elif stripped.startswith("## "):
                tw.insert("end", stripped[3:], "h2")
            elif stripped.startswith("# "):
                tw.insert("end", stripped[2:], "h1")
            # Separators
            elif re.match(r'^[=\-]{3,}$', stripped):
                tw.insert("end", "─" * 60, "separator")
            # Bullet points
            elif re.match(r'^(\s*)[-*]\s+(.*)', line):
                m = re.match(r'^(\s*)[-*]\s+(.*)', line)
                self._insert_inline_md(tw, m.group(1) + "• " + m.group(2), "bullet")
            # Numbered lists
            elif re.match(r'^\s*\d+\.\s+', line):
                self._insert_inline_md(tw, line, "bullet")
            # Normal line
            else:
                self._insert_inline_md(tw, line, "normal")

            tw.configure(state="disabled")
            self._resize_section_text(tw)
            tw.see("end")
            if section.get("expanded", False):
                self._auto_scroll_output()

        if self.parent.winfo_exists():
            self.parent.after(0, update)

    def _auto_scroll_output(self):
        """Scroll la zone de résultats vers le bas pour suivre la génération (délai pour rendu)."""
        def _do_scroll():
            try:
                if self._output_scroll and hasattr(self._output_scroll, '_parent_canvas'):
                    self._output_scroll._parent_canvas.yview_moveto(1.0)  # pylint: disable=protected-access
            except Exception:
                pass
        if self.parent.winfo_exists():
            self.parent.after(30, _do_scroll)

    def _resize_section_text(self, tw):
        """Redimensionne le texte : grandit jusqu'à 20 lignes, puis la scrollbar prend le relais."""
        try:
            tw.update_idletasks()
            info = tw.count("1.0", "end", "displaylines")
            lines = info[0] if info else int(tw.index("end-1c").split(".")[0])
        except Exception:
            lines = int(tw.index("end-1c").split(".")[0])
        tw.configure(height=max(3, min(lines + 1, 20)))

    def _finish_section(self, section, success=True):
        """Finalise une section: flush le buffer restant et met à jour le statut."""
        if section is None:
            return

        # Flush table buffer if any
        table_buf = section.get("_table_buf", [])
        if table_buf:
            self._flush_table_buffer(section)

        # Flush remaining line buffer through the full formatting pipeline
        remaining = section.get("_line_buf", "")
        if remaining.strip():
            self._format_and_insert_line(section, remaining, newline=True)
        section["_line_buf"] = ""

        # Flush table buffer again in case the last line was a table line
        table_buf2 = section.get("_table_buf", [])
        if table_buf2:
            self._flush_table_buffer(section)

        def update():
            section["status_var"].set("✅ Terminé" if success else "❌ Erreur")

        if self.parent.winfo_exists():
            self.parent.after(0, update)

    def _setup_markdown_tags(self, tw):
        """Configure les tags de formatage Markdown sur un widget texte."""
        base = "Segoe UI"
        mono = "Consolas"

        # 1. Appliquer tous les tags de coloration syntaxique par langage depuis le mixin GUI
        if SYNTAX_AVAILABLE:
            try:
                SyntaxColorHelper(self.colors).configure_tags(tw)
            except Exception:
                pass

        # 2. Tags spécifiques à la zone résultats (priorité sur le mixin)
        tw.tag_configure("h1", font=(base, 16, "bold"), foreground="#ffffff",
                         spacing1=10, spacing3=6)
        tw.tag_configure("h2", font=(base, 14, "bold"), foreground="#e0e0ff",
                         spacing1=8, spacing3=4)
        tw.tag_configure("h3", font=(base, 12, "bold"), foreground="#c0c0e0",
                         spacing1=6, spacing3=3)
        tw.tag_configure("h4", font=(base, 11, "bold"), foreground="#a0b0d0",
                         spacing1=4, spacing3=2)
        tw.tag_configure("bold", font=(base, 11, "bold"), foreground="#ffffff")
        tw.tag_configure("italic", font=(base, 11, "italic"), foreground="#d0d0e0")
        tw.tag_configure("code_inline", font=(mono, 10), foreground="#ff9f43")
        # code_block = fallback pour les langages non reconnus ou whitespace non tokenisé
        tw.tag_configure("code_block", font=(mono, 10), foreground="#d4d4d4",
                         spacing1=4, spacing3=4,
                         lmargin1=16, lmargin2=16)
        tw.tag_configure("code_lang", font=(mono, 9, "bold"), foreground="#6090c0",
                         spacing1=6)
        tw.tag_configure("bullet", foreground="#d0d0e0", lmargin1=20,
                         lmargin2=32, font=(base, 11))
        tw.tag_configure("normal", font=(base, 11),
                         foreground=self.colors.get("text_primary", "#ffffff"))
        tw.tag_configure("separator", foreground="#3a3a5c", font=(base, 6))
        # Table tags (matching chat page style)
        tw.tag_configure("table_header", font=(mono, 10, "bold"),
                         foreground="#58a6ff", background="#1a1a2e")
        tw.tag_configure("table_cell", font=(mono, 10),
                         foreground="#e6e6e6", background="#16213e")
        tw.tag_configure("table_border", font=(mono, 10),
                         foreground="#444466")
        tw.tag_configure("table_cell_bold", font=(mono, 10, "bold"),
                         foreground="#ffd700", background="#16213e")

    def _insert_with_markdown(self, tw, full_text):
        """Parse du texte Markdown et insertion formatée dans un widget texte."""
        full_text = _render_latex_symbols(full_text)
        lines = full_text.split("\n")
        in_code_block = False
        current_lang = ""
        i = 0

        while i < len(lines):
            line = lines[i]
            if i > 0:
                tw.insert("end", "\n")

            stripped = line.strip()

            # Code block markers
            if stripped.startswith("```"):
                if in_code_block:
                    in_code_block = False
                    current_lang = ""
                    i += 1
                    continue
                else:
                    in_code_block = True
                    current_lang = stripped[3:].strip().lower()
                    # Language label intentionally hidden — used only for highlighting logic
                    i += 1
                    continue

            if in_code_block:
                self._highlight_code_line(tw, line, current_lang)
                i += 1
                continue

            # Headers
            if stripped.startswith("#### "):
                tw.insert("end", stripped[5:], "h4")
                i += 1
                continue
            if stripped.startswith("### "):
                tw.insert("end", stripped[4:], "h3")
                i += 1
                continue
            if stripped.startswith("## "):
                tw.insert("end", stripped[3:], "h2")
                i += 1
                continue
            if stripped.startswith("# "):
                tw.insert("end", stripped[2:], "h1")
                i += 1
                continue

            # Table separator (|---|---|)
            if re.match(r'^\s*\|?[\s:]*-{2,}[\s:]*\|', stripped):
                i += 1
                continue

            # Table rows (| col | col |)
            if stripped.startswith("|") and stripped.endswith("|"):
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                for ci, cell in enumerate(cells):
                    if ci > 0:
                        tw.insert("end", "  │  ", "separator")
                    self._insert_inline_md(tw, cell, "normal")
                i += 1
                continue

            # Separators
            if re.match(r'^[=\-]{3,}$', stripped):
                tw.insert("end", "─" * 60, "separator")
                i += 1
                continue

            # Bullet points
            m = re.match(r'^(\s*)[-*]\s+(.*)', line)
            if m:
                self._insert_inline_md(tw, m.group(1) + "• " + m.group(2), "bullet")
                i += 1
                continue

            # Numbered lists
            if re.match(r'^\s*\d+\.\s+', line):
                self._insert_inline_md(tw, line, "bullet")
                i += 1
                continue

            # Normal line
            self._insert_inline_md(tw, line, "normal")
            i += 1

    def _highlight_code_line(self, tw, line, lang):
        """Insère une ligne de code avec coloration syntaxique par langage."""
        if not SYNTAX_AVAILABLE or not lang:
            tw.insert("end", line, "code_block")
            return
        SYNTAX_ANALYZER.highlight_line(tw, line, lang)

    def _insert_inline_md(self, tw, text, base_tag):
        """Insère du texte avec formatage inline Markdown (gras, italique, code)."""
        pattern = r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)'
        parts = re.split(pattern, text)
        for part in parts:
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                tw.insert("end", part[2:-2], "bold")
            elif part.startswith("*") and part.endswith("*") and len(part) > 2:
                tw.insert("end", part[1:-1], "italic")
            elif part.startswith("`") and part.endswith("`"):
                tw.insert("end", part[1:-1], "code_inline")
            else:
                tw.insert("end", part, base_tag)

    def _append_output(self, text):
        """Ajoute du texte à la section active."""
        if self._active_section is not None:
            self._append_to_section(self._active_section, text)

    def _on_token_received(self, token):
        """Callback pour chaque token reçu pendant le streaming.
        Retourne False pour interrompre la génération."""
        if self.is_interrupted:
            return False
        self._append_output(token)
        return True
