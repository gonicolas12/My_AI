"""Mixin : gestion des fichiers attachés (PDF, DOCX, Images, Code...)."""

import base64
import io
import os
from tkinter import filedialog

from PIL import Image

from interfaces.agents._common import ctk, tk
from processors.docx_processor import DOCXProcessor
from processors.pdf_processor import PDFProcessor


class FileHandlingMixin:
    """Attaches de fichiers et images dans la zone de tâche Agents."""

    def _agent_load_file(self, file_type: str):
        """Charge un fichier depuis le sélecteur et l'ajoute en aperçu dans la zone agents."""

        filetypes_map = {
            "PDF": [("Fichiers PDF", "*.pdf")],
            "DOCX": [("Fichiers Word", "*.docx")],
            "Excel": [("Excel & CSV", "*.xlsx *.xls *.csv")],
            "Code": [("Code", "*.py *.js *.html *.css *.json *.xml *.md *.txt"), ("Tous", "*.*")],
            "Image": [("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"), ("Tous", "*.*")],
        }
        ft = filetypes_map.get(file_type, [("Tous", "*.*")])
        file_path = filedialog.askopenfilename(title=f"Sélectionner un fichier {file_type}", filetypes=ft)
        if file_path:
            self._agent_add_preview(file_path, file_type)

    def _agent_add_preview(self, file_path: str, file_type: str):
        """Ajoute un aperçu miniature dans la zone de tâche agents."""
        filename = os.path.basename(file_path)
        type_icons = {"PDF": "📄", "DOCX": "📝", "Excel": "📊", "Code": "💻", "Image": "🖼"}
        icon = type_icons.get(file_type, "📎")

        bg = self.colors.get("bg_secondary", "#2a2a2a")
        accent = self.colors.get("accent", "#ff6b47")

        if self.use_ctk:
            thumb = ctk.CTkFrame(
                self._agent_preview_frame, fg_color=bg, corner_radius=6,
                border_width=1, border_color=self.colors.get("border", "#404040"),
            )
        else:
            thumb = tk.Frame(self._agent_preview_frame, bg=bg, relief="solid", bd=1)
        thumb.pack(side="left", padx=(0, 8), pady=4)

        display_name = filename if len(filename) <= 20 else filename[:17] + "..."
        if self.use_ctk:
            lbl = ctk.CTkLabel(
                thumb, text=f"{icon} {display_name}", font=("Segoe UI", 11),
                text_color=self.colors.get("text_primary", "#ffffff"), fg_color="transparent",
            )
        else:
            lbl = tk.Label(
                thumb, text=f"{icon} {display_name}", bg=bg,
                fg=self.colors.get("text_primary", "#ffffff"), font=("Segoe UI", 11),
            )
        lbl.pack(side="left", padx=(8, 4), pady=4)

        def _remove():
            self._agent_pending_files = [
                (p, t, w) for p, t, w in self._agent_pending_files if w is not thumb
            ]
            thumb.destroy()
            if not self._agent_pending_files:
                self._agent_preview_frame.grid_remove()

        if self.use_ctk:
            close_btn = ctk.CTkButton(
                thumb, text="✕", width=24, height=24,
                fg_color="transparent", hover_color=accent,
                text_color=self.colors.get("text_secondary", "#aaaaaa"),
                font=("Segoe UI", 12, "bold"), corner_radius=4, command=_remove,
            )
        else:
            close_btn = tk.Button(
                thumb, text="✕", bg=bg, fg=self.colors.get("text_secondary", "#aaaaaa"),
                font=("Segoe UI", 10, "bold"), relief="flat", bd=0, command=_remove, cursor="hand2",
            )
        close_btn.pack(side="left", padx=(0, 6), pady=4)

        self._agent_pending_files.append((file_path, file_type, thumb))
        self._agent_preview_frame.grid()

        print(f"📎 [AGENTS] Fichier attaché: {filename} ({file_type})")

    def _agent_get_pending_files(self) -> list:
        """Retourne la liste des fichiers attachés aux agents [(path, type), ...]."""
        return [(p, t) for p, t, _ in self._agent_pending_files]

    def _agent_clear_previews(self):
        """Retire tous les aperçus de fichiers de l'interface agents."""
        for _, _, widget in self._agent_pending_files:
            try:
                widget.destroy()
            except Exception:
                pass
        self._agent_pending_files = []
        self._agent_preview_frame.grid_remove()

    def _analyze_image_for_agent(self, file_path: str):
        """Analyse une image via le modèle vision et retourne une description textuelle.

        Utilise le même pipeline vision que la page chat : minicpm-v décrit
        l'image, puis la description est incluse dans le prompt de l'agent
        pour que le modèle texte (qwen3.5) puisse répondre.
        """
        try:
            img = Image.open(file_path)
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Redimensionner si nécessaire
            max_size = 1024
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.LANCZOS)

            # Encoder en base64
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=92, optimize=True)
            img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            # Obtenir la description via le modèle vision (API publique)
            print("🖼️ [AGENTS VISION] Analyse de l'image via le modèle vision...")
            description = self.llm.describe_image(img_base64)

            if description:
                print(f"✅ [AGENTS VISION] Description obtenue ({len(description)} chars)")
            return description

        except Exception as e:
            print(f"⚠️ [AGENTS VISION] Erreur analyse image: {e}")
            return None

    @staticmethod
    def _read_attached_file(file_path: str, file_type: str) -> str:
        """Lit le contenu d'un fichier attaché et retourne le texte brut."""
        ext = os.path.splitext(file_path)[1].lower()

        if file_type == "PDF" or ext == ".pdf":
            try:
                proc = PDFProcessor()
                result = proc.process_file(file_path)
                return result.get("content", "")
            except ImportError:
                pass

        if file_type == "DOCX" or ext in (".docx", ".doc"):
            try:
                proc = DOCXProcessor()
                result = proc.process_file(file_path)
                return result.get("content", "")
            except ImportError:
                pass

        # Fichiers texte / code / CSV / markdown — lecture directe
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(200_000)  # limiter à 200k chars
        except Exception:
            # Fallback binaire
            with open(file_path, "rb") as f:
                return f.read(100_000).decode("utf-8", errors="replace")
