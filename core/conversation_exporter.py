"""
Exportateur de conversations - Exporte les conversations en Markdown, HTML et PDF
Permet de sauvegarder et partager les echanges avec l'assistant IA local
"""

import html
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from utils.logger import setup_logger


class ConversationExporter:
    """
    Exporte les conversations de chat en differents formats (Markdown, HTML, PDF).

    Supporte l'export avec metadonnees, horodatage et mise en forme adaptee
    a chaque format de sortie. Les fichiers sont generes dans le repertoire
    de sortie configure avec nommage automatique base sur l'horodatage.
    """

    SUPPORTED_FORMATS = ("markdown", "html", "pdf")

    def __init__(self, output_dir: str = "outputs/exports"):
        """
        Initialise l'exportateur de conversations.

        Args:
            output_dir: Repertoire de sortie pour les fichiers exportes
        """
        self.logger = setup_logger("ConversationExporter")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(
            "Exportateur de conversations initialise (sortie: %s)", self.output_dir
        )

    def _generate_filename(self, extension: str, filename: Optional[str] = None) -> Path:
        """
        Genere un chemin de fichier avec horodatage si aucun nom n'est fourni.

        Args:
            extension: Extension du fichier (md, html, pdf)
            filename: Nom de fichier personnalise (sans extension)

        Returns:
            Chemin complet du fichier de sortie
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_{timestamp}"

        # Retirer l'extension si l'utilisateur l'a incluse
        filename = Path(filename).stem

        return self.output_dir / f"{filename}.{extension}"

    def _build_metadata_block(self, metadata: Optional[Dict] = None) -> Dict:
        """
        Construit un bloc de metadonnees normalise.

        Args:
            metadata: Metadonnees fournies par l'appelant

        Returns:
            Dictionnaire de metadonnees complete
        """
        defaults = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": "Non specifie",
            "session_name": "Session de conversation",
            "total_messages": 0,
        }
        if metadata:
            defaults.update(metadata)
        return defaults

    def _format_role_label(self, role: str) -> str:
        """
        Retourne le libelle affichable pour un role de message.

        Args:
            role: Identifiant du role (user, assistant)

        Returns:
            Libelle en francais
        """
        labels = {
            "user": "Utilisateur",
            "assistant": "Assistant",
            "system": "Systeme",
        }
        return labels.get(role, role.capitalize())

    def _format_timestamp(self, timestamp: Optional[str]) -> str:
        """
        Formate un horodatage pour l'affichage.

        Args:
            timestamp: Horodatage ISO ou chaine libre

        Returns:
            Horodatage formate lisiblement
        """
        if not timestamp:
            return ""
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%H:%M:%S")
        except (ValueError, TypeError):
            return str(timestamp)

    # ─────────────────────────────────────────────
    # Export Markdown
    # ─────────────────────────────────────────────

    def export_markdown(
        self,
        messages: List[Dict],
        filename: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Exporte la conversation au format Markdown.

        Genere un fichier Markdown structure avec en-tete de metadonnees,
        separation par role et preservation des blocs de code.

        Args:
            messages: Liste de messages {"role", "content", "timestamp"}
            filename: Nom du fichier de sortie (optionnel)
            metadata: Metadonnees de la conversation (optionnel)

        Returns:
            Chemin absolu du fichier genere
        """
        meta = self._build_metadata_block(metadata)
        meta["total_messages"] = meta.get("total_messages") or len(messages)
        filepath = self._generate_filename("md", filename)

        lines: List[str] = []

        # En-tete
        lines.append(f"# {meta['session_name']}")
        lines.append("")
        lines.append(f"- **Date** : {meta['date']}")
        lines.append(f"- **Modele** : {meta['model']}")
        lines.append(f"- **Messages** : {meta['total_messages']}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Corps des messages
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = self._format_timestamp(msg.get("timestamp"))

            label = self._format_role_label(role)
            header = f"### {label}"
            if timestamp:
                header += f"  `{timestamp}`"

            lines.append(header)
            lines.append("")
            lines.append(content)
            lines.append("")
            lines.append("---")
            lines.append("")

        # Pied de page
        lines.append(
            f"*Exporte le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
            f"par My_AI v7.1.0*"
        )

        filepath.write_text("\n".join(lines), encoding="utf-8")
        self.logger.info("Export Markdown genere : %s", filepath)
        return str(filepath.resolve())

    # ─────────────────────────────────────────────
    # Export HTML
    # ─────────────────────────────────────────────

    def _build_html_css(self) -> str:
        """
        Retourne le CSS embarque pour l'export HTML (theme sombre style Claude).

        Returns:
            Bloc <style> complet
        """
        return """<style>
    :root {
        --bg-primary: #1a1a2e;
        --bg-secondary: #16213e;
        --bg-user: #0f3460;
        --bg-assistant: #1a1a2e;
        --text-primary: #e8e8e8;
        --text-secondary: #a0a0b0;
        --accent: #e94560;
        --accent-soft: #533483;
        --border: #2a2a4a;
        --code-bg: #0d1117;
        --code-border: #30363d;
    }

    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                     'Helvetica Neue', Arial, sans-serif;
        background-color: var(--bg-primary);
        color: var(--text-primary);
        line-height: 1.6;
        padding: 0;
        margin: 0;
    }

    .container {
        max-width: 900px;
        margin: 0 auto;
        padding: 2rem 1.5rem;
    }

    .header {
        text-align: center;
        padding: 2rem 0;
        border-bottom: 2px solid var(--accent);
        margin-bottom: 2rem;
    }

    .header h1 {
        font-size: 1.8rem;
        color: var(--accent);
        margin-bottom: 1rem;
    }

    .metadata {
        display: flex;
        justify-content: center;
        gap: 2rem;
        flex-wrap: wrap;
        color: var(--text-secondary);
        font-size: 0.9rem;
    }

    .metadata span {
        padding: 0.3rem 0.8rem;
        background: var(--bg-secondary);
        border-radius: 4px;
        border: 1px solid var(--border);
    }

    .message {
        margin-bottom: 1.5rem;
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        border: 1px solid var(--border);
        position: relative;
    }

    .message-user {
        background-color: var(--bg-user);
        border-left: 4px solid var(--accent);
    }

    .message-assistant {
        background-color: var(--bg-assistant);
        border-left: 4px solid var(--accent-soft);
    }

    .message-system {
        background-color: var(--bg-secondary);
        border-left: 4px solid var(--text-secondary);
        font-style: italic;
    }

    .message-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.8rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid var(--border);
    }

    .message-role {
        font-weight: 700;
        font-size: 0.95rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .message-user .message-role { color: var(--accent); }
    .message-assistant .message-role { color: #a78bfa; }
    .message-system .message-role { color: var(--text-secondary); }

    .message-time {
        font-size: 0.8rem;
        color: var(--text-secondary);
    }

    .message-content {
        white-space: pre-wrap;
        word-wrap: break-word;
        font-size: 0.95rem;
    }

    .message-content code {
        background-color: var(--code-bg);
        padding: 0.15rem 0.4rem;
        border-radius: 4px;
        font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
        font-size: 0.88rem;
        border: 1px solid var(--code-border);
    }

    .message-content pre {
        background-color: var(--code-bg);
        padding: 1rem;
        border-radius: 8px;
        overflow-x: auto;
        margin: 0.8rem 0;
        border: 1px solid var(--code-border);
    }

    .message-content pre code {
        background: none;
        padding: 0;
        border: none;
        font-size: 0.88rem;
    }

    .footer {
        text-align: center;
        padding: 2rem 0;
        margin-top: 2rem;
        border-top: 1px solid var(--border);
        color: var(--text-secondary);
        font-size: 0.85rem;
    }

    @media (max-width: 600px) {
        .container { padding: 1rem; }
        .metadata { flex-direction: column; align-items: center; }
        .message { padding: 0.8rem 1rem; }
    }
</style>"""

    def _content_to_html(self, content: str) -> str:
        """
        Convertit le contenu texte en HTML avec gestion des blocs de code.

        Echappe le HTML, puis restaure les blocs de code pre-formates
        et les segments de code en ligne.

        Args:
            content: Contenu brut du message

        Returns:
            Contenu HTML securise et formate
        """
        # Extraire et proteger les blocs de code avant l'echappement
        code_blocks: List[str] = []

        def _replace_code_block(match: re.Match) -> str:
            lang = match.group(1) or ""
            code = match.group(2)
            idx = len(code_blocks)
            escaped_code = html.escape(code)
            block = f"<pre><code class=\"language-{html.escape(lang)}\">{escaped_code}</code></pre>"
            code_blocks.append(block)
            return f"__CODE_BLOCK_{idx}__"

        # Blocs de code triple backtick
        text = re.sub(
            r"```(\w*)\n?(.*?)```",
            _replace_code_block,
            content,
            flags=re.DOTALL,
        )

        # Echapper le HTML restant
        text = html.escape(text)

        # Code en ligne (simple backtick)
        text = re.sub(
            r"`([^`]+)`",
            lambda m: f"<code>{m.group(1)}</code>",
            text,
        )

        # Restaurer les blocs de code proteges
        for idx, block in enumerate(code_blocks):
            text = text.replace(f"__CODE_BLOCK_{idx}__", block)

        # Convertir les sauts de ligne en <br> (hors blocs <pre>)
        parts = re.split(r"(<pre>.*?</pre>)", text, flags=re.DOTALL)
        for i, part in enumerate(parts):
            if not part.startswith("<pre>"):
                parts[i] = part.replace("\n", "<br>\n")
        text = "".join(parts)

        return text

    def export_html(
        self,
        messages: List[Dict],
        filename: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Exporte la conversation au format HTML autonome avec theme sombre.

        Genere un fichier HTML complet avec CSS embarque, theme sombre
        inspire de l'interface Claude, et gestion des blocs de code.

        Args:
            messages: Liste de messages {"role", "content", "timestamp"}
            filename: Nom du fichier de sortie (optionnel)
            metadata: Metadonnees de la conversation (optionnel)

        Returns:
            Chemin absolu du fichier genere
        """
        meta = self._build_metadata_block(metadata)
        meta["total_messages"] = meta.get("total_messages") or len(messages)
        filepath = self._generate_filename("html", filename)

        css = self._build_html_css()

        # Construction des blocs de messages
        message_blocks: List[str] = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = self._format_timestamp(msg.get("timestamp"))

            label = self._format_role_label(role)
            html_content = self._content_to_html(content)

            time_html = (
                f'<span class="message-time">{html.escape(timestamp)}</span>'
                if timestamp
                else ""
            )

            block = f"""        <div class="message message-{html.escape(role)}">
            <div class="message-header">
                <span class="message-role">{html.escape(label)}</span>
                {time_html}
            </div>
            <div class="message-content">{html_content}</div>
        </div>"""
            message_blocks.append(block)

        messages_html = "\n\n".join(message_blocks)

        document = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(meta['session_name'])}</title>
{css}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{html.escape(meta['session_name'])}</h1>
            <div class="metadata">
                <span>Date : {html.escape(meta['date'])}</span>
                <span>Modele : {html.escape(str(meta['model']))}</span>
                <span>Messages : {meta['total_messages']}</span>
            </div>
        </div>

{messages_html}

        <div class="footer">
            Exporte le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            par My_AI v7.1.0
        </div>
    </div>
</body>
</html>"""

        filepath.write_text(document, encoding="utf-8")
        self.logger.info("Export HTML genere : %s", filepath)
        return str(filepath.resolve())

    # ─────────────────────────────────────────────
    # Export PDF
    # ─────────────────────────────────────────────

    def export_pdf(
        self,
        messages: List[Dict],
        filename: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Exporte la conversation au format PDF via ReportLab.

        Genere un document PDF structure avec en-tete, metadonnees,
        messages colores par role et gestion du depassement de page.

        Args:
            messages: Liste de messages {"role", "content", "timestamp"}
            filename: Nom du fichier de sortie (optionnel)
            metadata: Metadonnees de la conversation (optionnel)

        Returns:
            Chemin absolu du fichier genere

        Raises:
            ImportError: Si reportlab n'est pas installe
        """
        try:
            # pylint: disable=import-outside-toplevel
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import cm, mm
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError:
            self.logger.error(
                "reportlab n'est pas installe. Installez-le avec : pip install reportlab"
            )
            raise ImportError(  # noqa: B904
                "Le module reportlab est requis pour l'export PDF. "
                "Installez-le avec : pip install reportlab"
            ) from None

        meta = self._build_metadata_block(metadata)
        meta["total_messages"] = meta.get("total_messages") or len(messages)
        filepath = self._generate_filename("pdf", filename)

        # Configuration du document
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()

        # Styles personnalises
        style_title = ParagraphStyle(
            "ConvTitle",
            parent=styles["Title"],
            fontSize=18,
            textColor=colors.HexColor("#e94560"),
            spaceAfter=12,
            alignment=1,  # Centre
        )

        style_user_label = ParagraphStyle(
            "UserLabel",
            parent=styles["Normal"],
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#e94560"),
            spaceBefore=12,
            spaceAfter=4,
        )

        style_assistant_label = ParagraphStyle(
            "AssistantLabel",
            parent=styles["Normal"],
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#6d28d9"),
            spaceBefore=12,
            spaceAfter=4,
        )

        style_system_label = ParagraphStyle(
            "SystemLabel",
            parent=styles["Normal"],
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#999999"),
            spaceBefore=12,
            spaceAfter=4,
        )

        style_content = ParagraphStyle(
            "ConvContent",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#333333"),
            spaceAfter=8,
        )

        style_code = ParagraphStyle(
            "ConvCode",
            parent=styles["Code"],
            fontSize=8,
            fontName="Courier",
            backColor=colors.HexColor("#f5f5f5"),
            borderColor=colors.HexColor("#dddddd"),
            borderWidth=0.5,
            borderPadding=6,
            leftIndent=12,
            spaceAfter=8,
        )

        style_footer = ParagraphStyle(
            "ConvFooter",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#999999"),
            alignment=1,
            spaceBefore=20,
        )

        label_styles = {
            "user": style_user_label,
            "assistant": style_assistant_label,
            "system": style_system_label,
        }

        # Construction du contenu
        story: list = []

        # Titre
        story.append(Paragraph(self._escape_xml(meta["session_name"]), style_title))
        story.append(Spacer(1, 4 * mm))

        # Metadonnees en tableau
        meta_data = [
            [
                f"Date : {meta['date']}",
                f"Modele : {meta['model']}",
                f"Messages : {meta['total_messages']}",
            ]
        ]
        meta_table = Table(meta_data, colWidths=[6 * cm, 6 * cm, 5 * cm])
        meta_table.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#666666")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(meta_table)
        story.append(Spacer(1, 8 * mm))

        # Ligne de separation
        sep_table = Table([[""] * 1], colWidths=[17 * cm])
        sep_table.setStyle(
            TableStyle(
                [
                    ("LINEABOVE", (0, 0), (-1, 0), 1, colors.HexColor("#e94560")),
                ]
            )
        )
        story.append(sep_table)
        story.append(Spacer(1, 4 * mm))

        # Messages
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = self._format_timestamp(msg.get("timestamp"))

            label = self._format_role_label(role)
            label_style = label_styles.get(role, style_system_label)

            # En-tete du message
            header_text = label
            if timestamp:
                header_text += f"  [{timestamp}]"
            story.append(Paragraph(self._escape_xml(header_text), label_style))

            # Contenu : separer code et texte
            segments = self._split_code_segments(content)
            for seg_type, seg_text in segments:
                if seg_type == "code":
                    # Bloc de code
                    escaped = self._escape_xml(seg_text)
                    story.append(Paragraph(escaped, style_code))
                else:
                    # Texte normal avec retours a la ligne preserves
                    escaped = self._escape_xml(seg_text)
                    escaped = escaped.replace("\n", "<br/>")
                    story.append(Paragraph(escaped, style_content))

            story.append(Spacer(1, 2 * mm))

        # Pied de page
        footer_text = (
            f"Exporte le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
            f"par My_AI v7.1.0"
        )
        story.append(Paragraph(self._escape_xml(footer_text), style_footer))

        # Generation du PDF
        doc.build(story)
        self.logger.info("Export PDF genere : %s", filepath)
        return str(filepath.resolve())

    def _escape_xml(self, text: str) -> str:
        """
        Echappe les caracteres speciaux XML/HTML pour ReportLab Paragraph.

        Args:
            text: Texte brut a echapper

        Returns:
            Texte echappe compatible ReportLab
        """
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text

    def _split_code_segments(self, content: str) -> List[tuple]:
        """
        Decoupe le contenu en segments de texte et de code.

        Detecte les blocs de code Markdown (triple backtick) et retourne
        une liste de tuples (type, contenu).

        Args:
            content: Contenu brut du message

        Returns:
            Liste de tuples ("text"|"code", contenu)
        """
        segments: List[tuple] = []
        pattern = re.compile(r"```\w*\n?(.*?)```", re.DOTALL)

        last_end = 0
        for match in pattern.finditer(content):
            # Texte avant le bloc de code
            text_before = content[last_end : match.start()].strip()
            if text_before:
                segments.append(("text", text_before))

            # Bloc de code
            code = match.group(1).strip()
            if code:
                segments.append(("code", code))

            last_end = match.end()

        # Texte restant apres le dernier bloc
        remaining = content[last_end:].strip()
        if remaining:
            segments.append(("text", remaining))

        # Si aucun segment detecte, retourner tout en texte
        if not segments:
            segments.append(("text", content))

        return segments

    # ─────────────────────────────────────────────
    # Dispatcher
    # ─────────────────────────────────────────────

    def export(
        self,
        messages: List[Dict],
        output_format: str = "markdown",
        filename: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Exporte la conversation dans le format specifie.

        Point d'entree principal qui dispatche vers la methode d'export
        appropriee selon le format demande.

        Args:
            messages: Liste de messages {"role", "content", "timestamp"}
            output_format: Format de sortie ("markdown", "html", "pdf")
            filename: Nom du fichier de sortie (optionnel)
            metadata: Metadonnees de la conversation (optionnel)

        Returns:
            Chemin absolu du fichier genere

        Raises:
            ValueError: Si le format n'est pas supporte
        """
        format_lower = output_format.lower().strip()

        # Accepter les alias courants
        aliases = {
            "md": "markdown",
            "htm": "html",
        }
        format_lower = aliases.get(format_lower, format_lower)

        if format_lower not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Format '{output_format}' non supporte. "
                f"Formats disponibles : {', '.join(self.SUPPORTED_FORMATS)}"
            )

        exporters = {
            "markdown": self.export_markdown,
            "html": self.export_html,
            "pdf": self.export_pdf,
        }

        self.logger.info(
            "Export demande : format=%s, messages=%d", format_lower, len(messages)
        )
        return exporters[format_lower](messages, filename=filename, metadata=metadata)
