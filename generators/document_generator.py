"""
Générateur de documents
Création de DOCX, PDF, PPTX, XLSX et formats texte avec Ollama

Le contenu est rédigé par le LLM local en Markdown, puis converti en blocs par
``generators/markdown_document.py`` et rendu par le backend du format demandé.
Chaque backend restitue réellement la structure (titres, listes, tableaux,
gras/italique, code) plutôt que d'empiler des paragraphes bruts.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from generators.markdown_document import (
    Block,
    CodeBlock,
    Heading,
    Inline,
    ListBlock,
    Paragraph,
    Quote,
    Rule,
    Table,
    extract_title,
    inlines_to_text,
    parse_inlines,
    parse_markdown,
    strip_leading_title,
)

# Import du LLM local (Ollama)
if TYPE_CHECKING:
    from models.local_llm import LocalLLM

try:
    from models.local_llm import LocalLLM
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# Racine projet (…/My_AI). Ce fichier est dans …/My_AI/generators/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = PROJECT_ROOT / "outputs" / "documents"

# Formats produits par le générateur, et leur extension de fichier.
FORMAT_EXTENSIONS = {
    "docx": ".docx",
    "pdf": ".pdf",
    "pptx": ".pptx",
    "xlsx": ".xlsx",
    "csv": ".csv",
    "md": ".md",
    "html": ".html",
    "txt": ".txt",
}

# Synonymes acceptés dans une requête utilisateur ou un appel d'outil.
_FORMAT_ALIASES = {
    "word": "docx", "doc": "docx", "docx": "docx",
    "pdf": "pdf",
    "powerpoint": "pptx", "ppt": "pptx", "pptx": "pptx",
    "présentation": "pptx", "presentation": "pptx", "diaporama": "pptx",
    "slides": "pptx", "diapo": "pptx", "diapositive": "pptx",
    "excel": "xlsx", "xls": "xlsx", "xlsx": "xlsx",
    "tableur": "xlsx", "classeur": "xlsx", "spreadsheet": "xlsx",
    "csv": "csv",
    "markdown": "md", "md": "md",
    "html": "html",
    "texte": "txt", "txt": "txt", "text": "txt",
}

# Palette du rendu documentaire (cohérente entre DOCX, PDF, PPTX et XLSX).
_ACCENT = "1F4E79"        # bleu foncé des titres
_ACCENT_LIGHT = "DCE6F1"  # fond des en-têtes de tableau
_CODE_BG = "F2F2F2"       # fond des blocs de code

# Nombre de titres à partir duquel un sommaire est inséré dans le DOCX.
_TOC_MIN_HEADINGS = 3
# Nombre maximal de puces par diapositive avant découpe automatique.
_PPTX_MAX_BULLETS = 9


class DocumentGenerator:
    """
    Générateur de documents dans différents formats avec génération IA
    """

    def __init__(self, llm: Optional["LocalLLM"] = None):
        """
        Initialise le générateur de documents

        Args:
            llm: Instance de LocalLLM (Ollama) pour la génération de contenu.
                None (défaut) en crée une ; passer False s'en dispense, pour
                les usages qui fournissent eux-mêmes le contenu (rendu pur,
                tests) et n'ont pas à sonder Ollama.
        """
        if llm is None:
            self.llm = LocalLLM() if OLLAMA_AVAILABLE else None
        else:
            self.llm = llm or None
        self._check_dependencies()

    def _check_dependencies(self):
        """
        Vérifie la disponibilité des bibliothèques de rendu
        """
        self.reportlab_available = _module_available("reportlab")
        self.python_docx_available = _module_available("docx")
        self.python_pptx_available = _module_available("pptx")
        self.openpyxl_available = _module_available("openpyxl")

    # ── API publique ───────────────────────────────────────────────────────

    async def generate_document(
        self,
        brief: str,
        fmt: str = "",
        title: str = "",
        content: str = "",
        filename: str = "",
        research: str = "",
        is_interrupted_callback=None,
    ) -> Dict[str, Any]:
        """
        Génère un document complet dans le format demandé.

        Args:
            brief: Demande de l'utilisateur (sujet, consignes de rédaction)
            fmt: Format cible ("docx", "pdf", "pptx", "xlsx", "md", "txt",
                 "html", "csv"). Déduit de `brief` s'il est vide.
            title: Titre du document. Déduit du contenu s'il est vide.
            content: Corps en Markdown. Rédigé par le LLM s'il est vide.
            filename: Nom de fichier souhaité. Dérivé du titre s'il est vide.
            research: Informations déjà collectées (recherche web, mémoire,
                fichiers lus) à utiliser en priorité pour la rédaction.
            is_interrupted_callback: Fonction rendant True si l'utilisateur
                a interrompu l'opération

        Returns:
            {success, file_path, file_name, format, size} ou {success: False, error}
        """
        try:
            fmt = self.detect_format(fmt or brief)

            if not content or not content.strip():
                content = await self._write_content(
                    brief, title, fmt, research, is_interrupted_callback
                )
                if is_interrupted_callback and is_interrupted_callback():
                    return {
                        "success": False,
                        "interrupted": True,
                        "message": "⚠️ Génération du document interrompue.",
                    }
                if not content:
                    return {
                        "success": False,
                        "error": (
                            "Le modèle local n'a produit aucun contenu. "
                            "Vérifiez qu'Ollama est démarré (ollama serve)."
                        ),
                    }

            blocks = parse_markdown(content)
            if not title:
                title = extract_title(blocks) or _first_sentence(brief)
            blocks = strip_leading_title(blocks, title)

            filepath = self._resolve_output_path(filename, title, fmt)
            self.build(blocks, fmt, title, filepath)

            return {
                "success": True,
                "file_path": str(filepath),
                "file_name": filepath.name,
                "format": fmt,
                "title": title,
                "size": filepath.stat().st_size,
                # Plan du document : permet de le présenter à l'utilisateur
                # sans le relire (le rédacteur est un appel LLM séparé).
                "outline": [
                    block.text for block in blocks
                    if isinstance(block, Heading) and block.level <= 2 and block.text
                ],
            }

        except (OSError, ValueError, KeyError, ImportError) as e:
            return {
                "success": False,
                "error": f"Erreur lors de la génération du document: {e}",
            }

    def build(self, blocks: List[Block], fmt: str, title: str, filepath: Path) -> Path:
        """
        Rend une liste de blocs dans le format demandé et écrit le fichier.

        Args:
            blocks: Blocs issus de `parse_markdown`
            fmt: Format cible normalisé
            title: Titre du document
            filepath: Chemin de destination

        Returns:
            Le chemin du fichier écrit
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)

        builders = {
            "docx": self._build_docx,
            "pdf": self._build_pdf,
            "pptx": self._build_pptx,
            "xlsx": self._build_xlsx,
            "csv": self._build_csv,
            "md": self._build_markdown,
            "html": self._build_html,
            "txt": self._build_txt,
        }
        builder = builders.get(fmt)
        if builder is None:
            raise ValueError(f"Format non supporté : {fmt}")
        builder(blocks, title, filepath)
        return filepath

    @staticmethod
    def detect_format(text: str) -> str:
        """
        Déduit le format cible d'une requête ou d'un nom de format.

        Args:
            text: Requête utilisateur ou format brut

        Returns:
            Un format normalisé ; "docx" par défaut.
        """
        lowered = (text or "").strip().lower()
        if not lowered:
            return "docx"
        if lowered in _FORMAT_ALIASES:
            return _FORMAT_ALIASES[lowered]
        # Recherche du premier alias mentionné, en privilégiant les plus longs
        # pour éviter qu'un alias court n'éclipse un alias qui le contient.
        for alias in sorted(_FORMAT_ALIASES, key=len, reverse=True):
            if re.search(rf"\b{re.escape(alias)}\b", lowered):
                return _FORMAT_ALIASES[alias]
        return "docx"

    # ── Rédaction du contenu par le LLM ────────────────────────────────────

    async def _write_content(
        self,
        brief: str,
        title: str,
        fmt: str,
        research: str = "",
        is_interrupted_callback=None,
    ) -> str:
        """
        Demande au LLM local de rédiger le corps du document en Markdown.

        Renvoie une chaîne vide si Ollama est indisponible ou interrompu.
        """
        if self.llm is None or not getattr(self.llm, "is_ollama_available", False):
            return ""
        if is_interrupted_callback and is_interrupted_callback():
            return ""

        user_prompt = f"Rédige le document demandé ci-dessous.\n\nDemande : {brief}\n"
        if title:
            user_prompt += f"Titre imposé : {title}\n"
        if research and research.strip():
            # Le modèle a cherché avant d'écrire : ces faits priment sur sa
            # mémoire paramétrique, sans quoi la recherche n'aurait servi à rien.
            user_prompt += (
                "\nINFORMATIONS COLLECTÉES — appuie-toi EN PRIORITÉ dessus et "
                "n'invente pas de faits qui les contrediraient :\n"
                f"{research.strip()}\n"
            )
        user_prompt += "\nRéponds UNIQUEMENT avec le Markdown du document."

        # save_history/use_history à False : la rédaction du document ne doit
        # pas polluer le fil de conversation du chat.
        raw = self.llm.generate(
            user_prompt,
            system_prompt=self._content_system_prompt(fmt),
            save_history=False,
            use_history=False,
        )
        if not raw:
            return ""
        return _strip_markdown_fence(raw)

    @staticmethod
    def _content_system_prompt(fmt: str) -> str:
        """Construit la consigne de rédaction adaptée au format cible."""
        common = (
            "Tu es un rédacteur professionnel. Tu produis des documents "
            "structurés, factuels et directement exploitables.\n"
            "Règles de sortie STRICTES :\n"
            "- Réponds UNIQUEMENT en Markdown, sans phrase d'introduction ni "
            "de commentaire sur ton propre travail.\n"
            "- N'encadre JAMAIS ta réponse entière dans un bloc de code.\n"
            "- Structure avec des titres `#`, `##`, `###`.\n"
            "- Utilise des listes à puces et des tableaux Markdown quand cela "
            "clarifie le propos.\n"
            "- Mets en gras (`**`) les termes clés.\n"
            "- Écris dans la langue de la demande.\n"
        )
        specific = {
            "pptx": (
                "- Le document servira de PRÉSENTATION : chaque `##` devient "
                "une diapositive. Vise 4 à 6 puces courtes par `##`, pas de "
                "longs paragraphes.\n"
            ),
            "xlsx": (
                "- Le document servira de CLASSEUR : privilégie les tableaux "
                "Markdown, un par `##`, avec une ligne d'en-tête explicite et "
                "des valeurs dans les cellules.\n"
            ),
        }
        return common + specific.get(fmt, "- Vise un document complet et détaillé.\n")

    # ── Backend DOCX ───────────────────────────────────────────────────────

    def _build_docx(self, blocks: List[Block], title: str, filepath: Path) -> None:
        """Rend les blocs en document Word avec styles, sommaire et pied de page."""
        import docx
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Pt, RGBColor

        document = docx.Document()
        document.core_properties.title = title
        document.core_properties.author = "My_AI"

        if title:
            heading = document.add_heading(title, level=0)
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
            subtitle = document.add_paragraph(
                f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
            )
            subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in subtitle.runs:
                run.font.size = Pt(9)
                run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)

        if sum(1 for b in blocks if isinstance(b, Heading)) >= _TOC_MIN_HEADINGS:
            _docx_add_toc(document)

        for block in blocks:
            if isinstance(block, Heading):
                para = document.add_heading("", level=min(block.level, 4))
                _docx_write_inlines(para, block.inlines)
            elif isinstance(block, Paragraph):
                _docx_write_inlines(document.add_paragraph(), block.inlines)
            elif isinstance(block, ListBlock):
                base_style = "List Number" if block.ordered else "List Bullet"
                for item in block.items:
                    # Word nomme les styles imbriqués « List Bullet 2 », « 3 »…
                    style = base_style if item.level == 0 else f"{base_style} {min(item.level + 1, 3)}"
                    try:
                        para = document.add_paragraph(style=style)
                    except KeyError:
                        para = document.add_paragraph(style=base_style)
                    _docx_write_inlines(para, item.inlines)
            elif isinstance(block, Table):
                _docx_add_table(document, block)
            elif isinstance(block, CodeBlock):
                _docx_add_code(document, block)
            elif isinstance(block, Quote):
                try:
                    para = document.add_paragraph(style="Intense Quote")
                except KeyError:
                    para = document.add_paragraph()
                _docx_write_inlines(para, block.inlines)
            elif isinstance(block, Rule):
                rule = document.add_paragraph("─" * 40)
                rule.alignment = WD_ALIGN_PARAGRAPH.CENTER

        _docx_add_page_number_footer(document)
        document.save(str(filepath))

    # ── Backend PDF ────────────────────────────────────────────────────────

    def _build_pdf(self, blocks: List[Block], title: str, filepath: Path) -> None:
        """Rend les blocs en PDF paginé via reportlab platypus."""
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            HRFlowable,
            ListFlowable,
            ListItem as PdfListItem,
            Paragraph as PdfParagraph,
            Preformatted,
            SimpleDocTemplate,
            Spacer,
        )

        styles = getSampleStyleSheet()
        accent = colors.HexColor(f"#{_ACCENT}")
        body_style = ParagraphStyle(
            "MyAiBody", parent=styles["BodyText"],
            fontSize=10.5, leading=15, spaceAfter=7,
        )
        quote_style = ParagraphStyle(
            "MyAiQuote", parent=body_style,
            leftIndent=14, textColor=colors.HexColor("#555555"),
            borderPadding=4, spaceBefore=6, spaceAfter=8,
        )
        code_style = ParagraphStyle(
            "MyAiCode", parent=styles["Code"],
            fontName="Courier", fontSize=8.5, leading=11,
            backColor=colors.HexColor(f"#{_CODE_BG}"),
            borderPadding=6, spaceBefore=6, spaceAfter=8,
        )
        heading_styles = {
            level: ParagraphStyle(
                f"MyAiH{level}", parent=styles["Heading1"],
                fontSize=max(18 - 2 * level, 10.5),
                leading=max(22 - 2 * level, 13),
                textColor=accent,
                spaceBefore=16 if level == 1 else 12,
                spaceAfter=6,
            )
            for level in range(1, 7)
        }
        title_style = ParagraphStyle(
            "MyAiTitle", parent=styles["Title"],
            fontSize=22, leading=26, textColor=accent, spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "MyAiSubtitle", parent=styles["Normal"],
            fontSize=9, alignment=TA_CENTER,
            textColor=colors.HexColor("#808080"), spaceAfter=18,
        )

        story = []
        if title:
            story.append(PdfParagraph(_pdf_escape(title), title_style))
            story.append(
                PdfParagraph(
                    f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
                    subtitle_style,
                )
            )

        for block in blocks:
            if isinstance(block, Heading):
                story.append(
                    PdfParagraph(_pdf_inlines(block.inlines), heading_styles[min(block.level, 6)])
                )
            elif isinstance(block, Paragraph):
                story.append(PdfParagraph(_pdf_inlines(block.inlines), body_style))
            elif isinstance(block, ListBlock):
                items = [
                    PdfListItem(
                        PdfParagraph(_pdf_inlines(item.inlines), body_style),
                        leftIndent=12 * (item.level + 1),
                    )
                    for item in block.items
                ]
                if items:
                    story.append(
                        ListFlowable(
                            items,
                            bulletType="1" if block.ordered else "bullet",
                            bulletFontSize=9,
                            leftIndent=14,
                        )
                    )
                    story.append(Spacer(1, 6))
            elif isinstance(block, Table):
                story.append(_pdf_table(block, body_style, PdfParagraph, colors))
                story.append(Spacer(1, 10))
            elif isinstance(block, CodeBlock):
                story.append(Preformatted(block.code, code_style))
            elif isinstance(block, Quote):
                story.append(PdfParagraph(_pdf_inlines(block.inlines), quote_style))
            elif isinstance(block, Rule):
                story.append(
                    HRFlowable(width="100%", color=colors.HexColor("#CCCCCC"),
                               spaceBefore=8, spaceAfter=8)
                )

        if not story:
            story.append(PdfParagraph("(document vide)", body_style))

        document = SimpleDocTemplate(
            str(filepath), pagesize=A4, title=title or filepath.stem, author="My_AI",
            leftMargin=20 * mm, rightMargin=20 * mm,
            topMargin=18 * mm, bottomMargin=18 * mm,
        )
        document.build(story, onFirstPage=_pdf_page_number, onLaterPages=_pdf_page_number)

    # ── Backend PPTX ───────────────────────────────────────────────────────

    def _build_pptx(self, blocks: List[Block], title: str, filepath: Path) -> None:
        """Rend les blocs en présentation PowerPoint, une diapo par `##`."""
        from pptx import Presentation
        from pptx.util import Pt

        presentation = Presentation()
        layouts = presentation.slide_layouts
        content_layout = layouts[1]
        title_only_layout = layouts[5] if len(layouts) > 5 else layouts[1]

        # Diapositive de couverture
        cover = presentation.slides.add_slide(layouts[0])
        cover.shapes.title.text = title or filepath.stem
        if len(cover.placeholders) > 1:
            cover.placeholders[1].text = datetime.now().strftime("%d/%m/%Y")

        # « emitted » compte les diapos déjà produites pour le titre courant :
        # un tableau coupe l'accumulation, et la suite doit être numérotée
        # comme une continuation plutôt que de répéter le titre à l'identique.
        state = {"heading": "", "bullets": [], "emitted": 0}

        def flush_slide() -> None:
            """Écrit les puces accumulées, en découpant si la diapo déborde."""
            bullets = state["bullets"]
            # Sans puces il n'y a rien à montrer : le titre sera porté par la
            # diapo suivante (tableau ou section), plutôt qu'une diapo vide.
            if not bullets:
                return
            chunks = [
                bullets[i:i + _PPTX_MAX_BULLETS]
                for i in range(0, len(bullets), _PPTX_MAX_BULLETS)
            ]
            for index, chunk in enumerate(chunks):
                rank = state["emitted"] + index
                slide = presentation.slides.add_slide(content_layout)
                heading = state["heading"] or title
                slide.shapes.title.text = heading if rank == 0 else f"{heading} ({rank + 1})"
                body = _pptx_body_placeholder(slide)
                if body is None:
                    continue
                frame = body.text_frame
                frame.clear()
                for position, (text, level) in enumerate(chunk):
                    para = frame.paragraphs[0] if position == 0 else frame.add_paragraph()
                    para.text = text
                    para.level = min(level, 4)
                    para.font.size = Pt(18 if level == 0 else 15)
            state["emitted"] += len(chunks)
            state["bullets"] = []

        for block in blocks:
            if isinstance(block, Heading):
                if block.level <= 2:
                    flush_slide()
                    state["heading"] = block.text
                    state["emitted"] = 0
                else:
                    state["bullets"].append((block.text, 0))
            elif isinstance(block, Paragraph):
                state["bullets"].append((block.text, 0))
            elif isinstance(block, Quote):
                state["bullets"].append((f"« {block.text} »", 0))
            elif isinstance(block, ListBlock):
                state["bullets"].extend((item.text, item.level) for item in block.items)
            elif isinstance(block, CodeBlock):
                state["bullets"].extend(
                    (line, 1) for line in block.code.splitlines() if line.strip()
                )
            elif isinstance(block, Table):
                flush_slide()
                _pptx_add_table(
                    presentation, title_only_layout, state["heading"] or title, block
                )

        flush_slide()
        presentation.save(str(filepath))

    # ── Backend XLSX ───────────────────────────────────────────────────────

    def _build_xlsx(self, blocks: List[Block], title: str, filepath: Path) -> None:
        """Rend les tableaux en feuilles Excel et la prose en feuille « Notes »."""
        from openpyxl import Workbook

        workbook = Workbook()
        workbook.remove(workbook.active)

        used_names: List[str] = []
        section = title or "Données"
        notes: List[tuple] = []  # (niveau de titre, texte) ; niveau 0 = prose

        for block in blocks:
            if isinstance(block, Heading):
                section = block.text or section
                notes.append((block.level, block.text))
            elif isinstance(block, Table):
                sheet = workbook.create_sheet(_unique_sheet_name(section, used_names))
                _xlsx_write_table(sheet, block)
            elif isinstance(block, Paragraph):
                notes.append((0, block.text))
            elif isinstance(block, Quote):
                notes.append((0, f"« {block.text} »"))
            elif isinstance(block, ListBlock):
                notes.extend(
                    (0, f"{'    ' * item.level}• {item.text}") for item in block.items
                )
            elif isinstance(block, CodeBlock):
                notes.extend((0, line) for line in block.code.splitlines())

        if notes:
            sheet = workbook.create_sheet(_unique_sheet_name("Notes", used_names), 0)
            _xlsx_write_notes(sheet, title, notes)

        if not workbook.sheetnames:
            workbook.create_sheet("Document")["A1"] = title or "Document vide"

        workbook.save(str(filepath))

    # ── Backends texte ─────────────────────────────────────────────────────

    def _build_markdown(self, blocks: List[Block], title: str, filepath: Path) -> None:
        """Réécrit les blocs en Markdown canonique."""
        filepath.write_text(_blocks_to_markdown(blocks, title), encoding="utf-8")

    def _build_txt(self, blocks: List[Block], title: str, filepath: Path) -> None:
        """Rend les blocs en texte brut indenté."""
        lines: List[str] = []
        if title:
            lines += [title, "=" * len(title), ""]
        for block in blocks:
            if isinstance(block, Heading):
                underline = "=" if block.level == 1 else "-"
                lines += ["", block.text, underline * max(len(block.text), 3), ""]
            elif isinstance(block, Paragraph):
                lines += [block.text, ""]
            elif isinstance(block, ListBlock):
                for index, item in enumerate(block.items, start=1):
                    prefix = f"{index}." if block.ordered else "-"
                    lines.append(f"{'    ' * item.level}{prefix} {item.text}")
                lines.append("")
            elif isinstance(block, Table):
                widths = _table_column_widths(block)
                lines.append(_txt_table_row(block.header, widths))
                lines.append("-+-".join("-" * width for width in widths))
                lines += [_txt_table_row(row, widths) for row in block.rows]
                lines.append("")
            elif isinstance(block, CodeBlock):
                lines += ["    " + line for line in block.code.splitlines()]
                lines.append("")
            elif isinstance(block, Quote):
                lines += [f"> {block.text}", ""]
            elif isinstance(block, Rule):
                lines += ["-" * 60, ""]
        filepath.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    def _build_html(self, blocks: List[Block], title: str, filepath: Path) -> None:
        """Rend les blocs en page HTML autonome (même rendu que l'aperçu)."""
        from interfaces.document_preview import render_blocks_html, wrap_preview_page

        filepath.write_text(
            wrap_preview_page(title, render_blocks_html(blocks, title)), encoding="utf-8"
        )

    def _build_csv(self, blocks: List[Block], title: str, filepath: Path) -> None:
        """Écrit le premier tableau rencontré en CSV (séparateur « ; »)."""
        import csv

        tables = [block for block in blocks if isinstance(block, Table)]
        with open(filepath, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle, delimiter=";")
            if tables:
                writer.writerow([_cell_text(label) for label in tables[0].header])
                writer.writerows(
                    [_cell_text(value) for value in row] for row in tables[0].rows
                )
            else:
                writer.writerow([title or "Contenu"])
                for block in blocks:
                    text = getattr(block, "text", "")
                    if text:
                        writer.writerow([text])

    # ── Chemins de sortie ──────────────────────────────────────────────────

    def _resolve_output_path(self, filename: str, title: str, fmt: str) -> Path:
        """
        Construit le chemin de destination dans outputs/documents/.

        Un nom fourni par l'appelant est conservé (extension corrigée si
        besoin) ; sinon le nom dérive du titre, suffixé d'un horodatage.
        """
        extension = FORMAT_EXTENSIONS.get(fmt, ".txt")
        if filename:
            stem = Path(filename).stem
        else:
            stem = _slugify(title) or "document"
            stem = f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return DOCUMENTS_DIR / f"{stem}{extension}"

    # ── Compatibilité ──────────────────────────────────────────────────────

    async def generate_pdf(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Génère un PDF à partir d'un contenu Markdown déjà rédigé."""
        return await self.generate_document(
            content, fmt="pdf", title=(context or {}).get("title", ""), content=content
        )

    async def generate_docx(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Génère un DOCX à partir d'un contenu Markdown déjà rédigé."""
        return await self.generate_document(
            content, fmt="docx", title=(context or {}).get("title", ""), content=content
        )

    async def generate_text(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Génère un fichier texte à partir d'un contenu Markdown déjà rédigé."""
        return await self.generate_document(
            content, fmt="txt", title=(context or {}).get("title", ""), content=content
        )


# ══════════════════════════════════════════════════════════════════════════
#  Aides DOCX
# ══════════════════════════════════════════════════════════════════════════


def _docx_write_inlines(paragraph, inlines: List[Inline]) -> None:
    """Écrit des fragments stylés dans un paragraphe python-docx."""
    from docx.shared import Pt, RGBColor

    for text, styles, url in inlines:
        run = paragraph.add_run(text)
        run.bold = "bold" in styles
        run.italic = "italic" in styles
        if "code" in styles:
            run.font.name = "Consolas"
            run.font.size = Pt(9.5)
        if url:
            run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
            run.underline = True


def _docx_add_table(document, block: Table) -> None:
    """Ajoute un tableau stylé avec sa ligne d'en-tête en gras."""
    from docx.shared import Pt

    columns = max(len(block.header), 1)
    table = document.add_table(rows=1, cols=columns)
    try:
        table.style = "Light Grid Accent 1"
    except KeyError:
        table.style = "Table Grid"

    for index, label in enumerate(block.header):
        cell = table.rows[0].cells[index]
        # En-tête : toujours en gras, en plus des styles Markdown de la cellule.
        _docx_write_inlines(cell.paragraphs[0], _cell_inlines(label, force={"bold"}))
        for run in cell.paragraphs[0].runs:
            run.font.size = Pt(10)
        _docx_shade_cell(cell, _ACCENT_LIGHT)

    for row in block.rows:
        cells = table.add_row().cells
        for index, value in enumerate(row[:columns]):
            # Les cellules contiennent du Markdown (« **Taille** ») : sans
            # interprétation, les astérisques apparaissaient dans le document.
            _docx_write_inlines(cells[index].paragraphs[0], _cell_inlines(value))
    document.add_paragraph()


def _docx_shade_cell(cell, hex_color: str) -> None:
    """Applique une couleur de fond à une cellule (pas d'API haut niveau)."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:fill"), hex_color)
    cell._tc.get_or_add_tcPr().append(shading)  # noqa: SLF001 - pas d'API publique


def _docx_add_code(document, block: CodeBlock) -> None:
    """Ajoute un bloc de code en monospace sur fond tramé."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt

    paragraph = document.add_paragraph()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:fill"), _CODE_BG)
    paragraph._p.get_or_add_pPr().append(shading)  # noqa: SLF001 - pas d'API publique

    run = paragraph.add_run(block.code)
    run.font.name = "Consolas"
    run.font.size = Pt(9)


def _docx_add_toc(document) -> None:
    """
    Insère un champ TOC (sommaire Word).

    Word calcule la table à l'ouverture du document ; python-docx n'expose pas
    d'API pour cela, d'où l'insertion du champ en XML brut.
    """
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    document.add_heading("Sommaire", level=1)
    run = document.add_paragraph().add_run()

    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = r'TOC \o "1-3" \h \z \u'
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "Ouvrez le document dans Word puis F9 pour calculer le sommaire."
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")

    for element in (begin, instruction, separate, placeholder, end):
        run._r.append(element)  # noqa: SLF001 - pas d'API publique
    document.add_page_break()


def _docx_add_page_number_footer(document) -> None:
    """Ajoute « Page N » centré dans le pied de page de toutes les sections."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt

    for section in document.sections:
        paragraph = section.footer.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        label = paragraph.add_run("Page ")
        label.font.size = Pt(8)

        field_run = paragraph.add_run()
        field_run.font.size = Pt(8)
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        instruction = OxmlElement("w:instrText")
        instruction.set(qn("xml:space"), "preserve")
        instruction.text = "PAGE"
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        for element in (begin, instruction, end):
            field_run._r.append(element)  # noqa: SLF001 - pas d'API publique


# ══════════════════════════════════════════════════════════════════════════
#  Aides PDF
# ══════════════════════════════════════════════════════════════════════════


def _pdf_escape(text: str) -> str:
    """Échappe le mini-HTML interprété par les Paragraph reportlab."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _pdf_inlines(inlines: List[Inline]) -> str:
    """Convertit des fragments stylés en balisage reportlab."""
    parts = []
    for text, styles, url in inlines:
        rendered = _pdf_escape(text)
        if "code" in styles:
            rendered = f'<font face="Courier" size="9">{rendered}</font>'
        if "bold" in styles:
            rendered = f"<b>{rendered}</b>"
        if "italic" in styles:
            rendered = f"<i>{rendered}</i>"
        if url:
            rendered = f'<link href="{_pdf_escape(url)}" color="#1F4E79">{rendered}</link>'
        parts.append(rendered)
    return "".join(parts) or " "


def _pdf_table(block: Table, body_style, PdfParagraph, colors):
    """Construit un Table reportlab dont les cellules savent passer à la ligne."""
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Table as PdfTable, TableStyle

    cell_style = ParagraphStyle(
        "MyAiCell", parent=body_style, fontSize=9, leading=12, spaceAfter=0
    )
    header_style = ParagraphStyle("MyAiCellHead", parent=cell_style, textColor=colors.white)

    data = [[
        PdfParagraph(_pdf_inlines(_cell_inlines(label, force={"bold"})), header_style)
        for label in block.header
    ]]
    data += [
        [PdfParagraph(_pdf_inlines(_cell_inlines(cell)), cell_style) for cell in row]
        for row in block.rows
    ]

    table = PdfTable(data, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(f"#{_ACCENT}")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BFBFBF")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
        ])
    )
    return table


def _pdf_page_number(canvas, document) -> None:
    """Callback de page reportlab : numéro centré en pied de page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillGray(0.5)
    canvas.drawCentredString(document.pagesize[0] / 2.0, 12, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


# ══════════════════════════════════════════════════════════════════════════
#  Aides PPTX
# ══════════════════════════════════════════════════════════════════════════


def _pptx_body_placeholder(slide):
    """Retourne le placeholder de corps d'une diapo, ou None s'il n'y en a pas."""
    for placeholder in slide.placeholders:
        # idx 0 = titre ; le premier autre placeholder textuel fait office de corps.
        if placeholder.placeholder_format.idx != 0 and placeholder.has_text_frame:
            return placeholder
    return None


def _pptx_add_table(presentation, layout, heading: str, block: Table) -> None:
    """Ajoute une diapositive contenant uniquement un tableau."""
    from pptx.util import Inches, Pt

    slide = presentation.slides.add_slide(layout)
    if slide.shapes.title is not None:
        slide.shapes.title.text = heading

    rows = len(block.rows) + 1
    columns = max(len(block.header), 1)
    table = slide.shapes.add_table(
        rows, columns, Inches(0.6), Inches(1.8), Inches(8.8), Inches(0.4 * rows)
    ).table

    for index, label in enumerate(block.header):
        _pptx_write_cell(table.cell(0, index), _cell_inlines(label, force={"bold"}), Pt(12))

    for row_index, row in enumerate(block.rows, start=1):
        for column_index, value in enumerate(row[:columns]):
            _pptx_write_cell(
                table.cell(row_index, column_index), _cell_inlines(value), Pt(11)
            )


def _pptx_write_cell(cell, inlines: List[Inline], size) -> None:
    """Écrit des fragments stylés dans une cellule de tableau PowerPoint."""
    cell.text = ""
    paragraph = cell.text_frame.paragraphs[0]
    for text, styles, _url in inlines:
        run = paragraph.add_run()
        run.text = text
        run.font.size = size
        run.font.bold = "bold" in styles
        run.font.italic = "italic" in styles


# ══════════════════════════════════════════════════════════════════════════
#  Aides XLSX
# ══════════════════════════════════════════════════════════════════════════

# Caractères interdits par Excel dans un nom de feuille.
_SHEET_FORBIDDEN_RE = re.compile(r"[\[\]:*?/\\]")
_SHEET_NAME_MAX = 31


def _unique_sheet_name(raw: str, used: List[str]) -> str:
    """Normalise un nom de feuille Excel et garantit son unicité."""
    name = (_SHEET_FORBIDDEN_RE.sub(" ", raw or "Feuille").strip() or "Feuille")[:_SHEET_NAME_MAX]
    candidate = name
    counter = 2
    taken = {existing.lower() for existing in used}
    while candidate.lower() in taken:
        suffix = f" {counter}"
        candidate = name[: _SHEET_NAME_MAX - len(suffix)] + suffix
        counter += 1
    used.append(candidate)
    return candidate


def _xlsx_write_table(sheet, block: Table) -> None:
    """Écrit un tableau dans une feuille : en-tête stylé, filtre, largeurs."""
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    # Une cellule Excel n'a qu'un style : on retire les marqueurs Markdown et
    # on passe la cellule en gras quand elle l'est entièrement.
    sheet.append([_cell_text(label) for label in block.header])
    for row in block.rows:
        sheet.append([_coerce_cell(_cell_text(value)) for value in row])
        for column, value in enumerate(row, start=1):
            if _cell_is_bold(value):
                sheet.cell(row=sheet.max_row, column=column).font = Font(bold=True)

    fill = PatternFill("solid", fgColor=_ACCENT)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)

    sheet.freeze_panes = "A2"
    if block.header:
        last_column = get_column_letter(len(block.header))
        sheet.auto_filter.ref = f"A1:{last_column}{len(block.rows) + 1}"

    for index, label in enumerate(block.header, start=1):
        values = [label] + [row[index - 1] for row in block.rows if index - 1 < len(row)]
        width = max((len(_cell_text(str(value))) for value in values), default=10)
        sheet.column_dimensions[get_column_letter(index)].width = min(max(width + 3, 12), 60)


def _xlsx_write_notes(sheet, title: str, notes: List[tuple]) -> None:
    """Écrit la prose du document dans une feuille de notes hiérarchisée."""
    from openpyxl.styles import Alignment, Font

    row = 1
    if title:
        sheet.cell(row=row, column=1, value=title).font = Font(bold=True, size=14, color=_ACCENT)
        row += 2

    for level, text in notes:
        cell = sheet.cell(row=row, column=1, value=text)
        if level:
            cell.font = Font(bold=True, size=max(13 - level, 10), color=_ACCENT)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        row += 1

    sheet.column_dimensions["A"].width = 110


def _coerce_cell(value: str):
    """Convertit une cellule textuelle en nombre quand c'en est un."""
    text = (value or "").strip()
    if not text:
        return ""
    normalized = text.replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        number = float(normalized)
    except ValueError:
        return text
    return int(number) if number.is_integer() and "." not in normalized else number


# ══════════════════════════════════════════════════════════════════════════
#  Aides communes
# ══════════════════════════════════════════════════════════════════════════


def _cell_inlines(text: str, force=frozenset()) -> List[Inline]:
    """
    Interprète le Markdown d'une cellule de tableau (« **Taille** »…).

    Le parseur conserve les cellules en texte brut ; chaque backend passe par
    ici pour restituer gras/italique/code au lieu d'écrire les marqueurs.

    Args:
        text: Contenu brut de la cellule
        force: Styles ajoutés à tous les fragments (ex. {"bold"} pour l'en-tête)
    """
    inlines = parse_inlines(text or "") or [("", frozenset(), None)]
    if force:
        extra = frozenset(force)
        inlines = [(part, styles | extra, url) for part, styles, url in inlines]
    return inlines


def _cell_text(text: str) -> str:
    """Texte d'une cellule sans ses marqueurs Markdown (xlsx, csv, txt)."""
    return inlines_to_text(parse_inlines(text or ""))


def _cell_is_bold(text: str) -> bool:
    """True si toute la cellule est en gras (« **Taille** »)."""
    inlines = [item for item in parse_inlines(text or "") if item[0].strip()]
    return bool(inlines) and all("bold" in styles for _part, styles, _url in inlines)


def _module_available(name: str) -> bool:
    """Teste la présence d'un module sans le charger."""
    import importlib.util

    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _strip_markdown_fence(text: str) -> str:
    """
    Retire la fence englobante quand le LLM emballe tout le document.

    Les petits modèles répondent régulièrement ```markdown … ``` malgré la
    consigne ; sans ce nettoyage le document entier deviendrait un bloc de code.
    """
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) < 2:
        return stripped
    language = lines[0].strip().lstrip("`").strip().lower()
    if language and language not in {"markdown", "md", "text", "txt"}:
        return stripped
    if lines[-1].strip().startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return "\n".join(lines[1:]).strip()


def _slugify(text: str) -> str:
    """Réduit un titre à un nom de fichier sûr (ASCII, underscores)."""
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text).strip("_").lower()[:60]


def _first_sentence(text: str, limit: int = 70) -> str:
    """Extrait un titre de repli depuis la demande de l'utilisateur."""
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return "Document"
    return (re.split(r"[.!?\n]", cleaned)[0][:limit] or "Document").strip()


def _table_column_widths(block: Table) -> List[int]:
    """Calcule la largeur d'affichage de chaque colonne d'un tableau texte."""
    widths = [len(_cell_text(label)) for label in block.header]
    for row in block.rows:
        for index, value in enumerate(row):
            if index < len(widths):
                widths[index] = max(widths[index], len(_cell_text(value)))
    return [max(width, 3) for width in widths]


def _txt_table_row(cells: List[str], widths: List[int]) -> str:
    """Formate une ligne de tableau en colonnes alignées, sans marqueurs Markdown."""
    return " | ".join(
        _cell_text(cells[index] if index < len(cells) else "").ljust(width)
        for index, width in enumerate(widths)
    )


def _blocks_to_markdown(blocks: List[Block], title: str) -> str:
    """Réécrit des blocs en Markdown canonique."""
    lines: List[str] = []
    if title:
        lines += [f"# {title}", ""]
    for block in blocks:
        if isinstance(block, Heading):
            lines += ["#" * min(block.level, 6) + f" {block.text}", ""]
        elif isinstance(block, Paragraph):
            lines += [_inlines_to_markdown(block.inlines), ""]
        elif isinstance(block, ListBlock):
            for index, item in enumerate(block.items, start=1):
                prefix = f"{index}." if block.ordered else "-"
                lines.append(f"{'  ' * item.level}{prefix} {_inlines_to_markdown(item.inlines)}")
            lines.append("")
        elif isinstance(block, Table):
            lines.append("| " + " | ".join(block.header) + " |")
            lines.append("|" + "|".join("---" for _ in block.header) + "|")
            lines += ["| " + " | ".join(row) + " |" for row in block.rows]
            lines.append("")
        elif isinstance(block, CodeBlock):
            lines += [f"```{block.language}", block.code, "```", ""]
        elif isinstance(block, Quote):
            lines += [f"> {_inlines_to_markdown(block.inlines)}", ""]
        elif isinstance(block, Rule):
            lines += ["---", ""]
    return "\n".join(lines).rstrip() + "\n"


def _inlines_to_markdown(inlines: List[Inline]) -> str:
    """Réécrit des fragments stylés en Markdown."""
    parts = []
    for text, styles, url in inlines:
        rendered = text
        if "code" in styles:
            rendered = f"`{rendered}`"
        if "bold" in styles:
            rendered = f"**{rendered}**"
        if "italic" in styles:
            rendered = f"*{rendered}*"
        if url:
            rendered = f"[{rendered}]({url})"
        parts.append(rendered)
    return "".join(parts)
