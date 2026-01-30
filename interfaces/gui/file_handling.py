"""File handling mixin for ModernAIGUI."""

import os
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

try:
    import customtkinter as ctk

    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    ctk = tk

from .layout import DND_AVAILABLE

try:
    from tkinterdnd2 import DND_FILES
except Exception:
    DND_FILES = None


class FileHandlingMixin:
    """File loading, drag & drop, and notifications."""

    def setup_drag_drop(self):
        """Configure le drag & drop pour les fichiers"""
        if DND_AVAILABLE:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self.on_file_drop)

    def on_file_drop(self, event):
        """Gère le drop de fichiers"""
        files = self.root.tk.splitlist(event.data)
        for file_path in files:
            if os.path.isfile(file_path):
                self.process_dropped_file(file_path)
            else:
                self.show_notification(f"❌ Chemin invalide : {file_path}", "error")

    def process_dropped_file(self, file_path):
        """Traite un fichier glissé-déposé"""
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        # Déterminer le type de fichier
        if ext == ".pdf":
            file_type = "PDF"
        elif ext in [".docx", ".doc"]:
            file_type = "DOCX"
        elif ext in [".py", ".js", ".html", ".css", ".json", ".xml", ".md", ".txt"]:
            file_type = "Code"
        else:
            self.show_notification(f"❌ **Format non supporté** : {ext}", "error")
            return

        # Ajouter message utilisateur
        self.add_message_bubble(f"📎 **Fichier glissé** : {filename}", is_user=True)

        # Traiter le fichier
        self.process_file(file_path, file_type)

    def show_notification(self, message, type_notif="info", duration=2000):
        """
        Affiche une notification temporaire améliorée

        Args:
            message: Message à afficher
            type_notif: Type de notification (info, success, error, warning)
            duration: Durée d'affichage en millisecondes
        """
        # Couleurs selon le type
        colors_map = {
            "error": "#ef4444",
            "success": "#10b981",
            "warning": "#f59e0b",
            "info": "#3b82f6",
        }

        bg_color = colors_map.get(type_notif, "#3b82f6")

        # Créer une notification en overlay
        if self.use_ctk:
            notif_frame = ctk.CTkFrame(
                self.main_container, fg_color=bg_color, corner_radius=8, border_width=0
            )

            notif_label = ctk.CTkLabel(
                notif_frame,
                text=message,
                text_color="#ffffff",
                font=("Segoe UI", self.get_current_font_size("message"), "bold"),
                fg_color="transparent",
            )
        else:
            notif_frame = tk.Frame(
                self.main_container, bg=bg_color, relief="flat", bd=0
            )

            notif_label = tk.Label(
                notif_frame,
                text=message,
                fg="#ffffff",
                bg=bg_color,
                font=("Segoe UI", self.get_current_font_size("message"), "bold"),
            )

        # Positionner en haut à droite
        notif_frame.place(relx=0.98, rely=0.02, anchor="ne")
        notif_label.pack(padx=15, pady=8)

        # Animation d'apparition (optionnelle)
        notif_frame.lift()  # Mettre au premier plan

        # Supprimer automatiquement après la durée spécifiée
        self.root.after(duration, notif_frame.destroy)

    def download_file_to_downloads(self, source_path, filename):
        """Télécharge un fichier vers le dossier Téléchargements de l'utilisateur."""
        try:
            # Obtenir le dossier Téléchargements
            downloads_folder = Path.home() / "Downloads"
            if not downloads_folder.exists():
                downloads_folder = Path.home() / "Téléchargements"  # Windows FR

            # Créer le chemin de destination
            dest_path = downloads_folder / filename

            # Copier le fichier
            shutil.copy2(source_path, dest_path)

            # Afficher la notification
            if hasattr(self, "show_copy_notification"):
                self.show_copy_notification(
                    f"✅ Votre fichier {filename} a été téléchargé dans : {dest_path}"
                )
            return True

        except Exception as e:
            if hasattr(self, "show_copy_notification"):
                self.show_copy_notification(f"❌ Erreur de téléchargement : {str(e)}")
            return False

    def load_pdf_file(self):
        """Charge un fichier PDF"""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier PDF", filetypes=[("Fichiers PDF", "*.pdf")]
        )

        if file_path:
            self.process_file(file_path, "PDF")

    def load_docx_file(self):
        """Charge un fichier DOCX"""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier DOCX",
            filetypes=[("Fichiers Word", "*.docx")],
        )

        if file_path:
            self.process_file(file_path, "DOCX")

    def load_code_file(self):
        """Charge un fichier de code"""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier de code",
            filetypes=[
                ("Fichiers Python", "*.py"),
                ("Fichiers JavaScript", "*.js"),
                ("Fichiers HTML", "*.html"),
                ("Tous les fichiers", "*.*"),
            ],
        )

        if file_path:
            self.process_file(file_path, "Code")

    def process_file(self, file_path, file_type):
        """Traite un fichier"""
        try:
            filename = os.path.basename(file_path)

            # Animation de traitement
            self.is_thinking = True
            self.add_message_bubble(f"📎 Fichier chargé : **{filename}**", is_user=True)

            # Traitement en arrière-plan
            threading.Thread(
                target=self.process_file_background,
                args=(file_path, file_type, filename),
                daemon=True,
            ).start()

        except Exception as e:
            self.logger.error("Erreur lors du chargement du fichier: %s", e)
            messagebox.showerror("Erreur", f"Impossible de charger le fichier: {e}")

    def process_file_background(self, file_path, file_type, filename):
        """Traite le fichier en arrière-plan avec système 1M tokens"""
        try:
            self.logger.info(
                "Traitement du fichier: %s (type: %s)", filename, file_type
            )

            # Utiliser le processeur unifié
            result = self.file_processor.process_file(file_path)

            if result.get("error"):
                raise ValueError(result["error"])

            content = result.get("content", "")
            self.logger.info("Fichier traité: %s caractères", len(content))

            # Vérifier que le contenu n'est pas vide
            if not content or not content.strip():
                raise ValueError(f"Le fichier {filename} semble vide ou illisible")

            # 🚀 NOUVEAU: Stocker dans CustomAI unifié avec processeurs avancés
            chunks_created = 0
            if self.custom_ai:
                try:
                    self.logger.info(
                        "🚀 Ajout au CustomAI avec processeurs avancés: %s", filename
                    )

                    # Utiliser la nouvelle méthode qui exploite les processeurs PDF/DOCX/Code
                    if hasattr(self.custom_ai, "add_file_to_context"):
                        # Méthode avancée qui utilise les processeurs spécialisés
                        result = self.custom_ai.add_file_to_context(file_path)
                        chunk_ids = result.get("chunk_ids", [])
                        chunks_created = result.get(
                            "chunks_created", len(chunk_ids) if chunk_ids else 0
                        )

                        if result.get("success"):
                            processor_used = result.get("processor_used", "advanced")
                            analysis_info = result.get(
                                "analysis_info", f"{len(content)} caractères"
                            )
                            self.logger.info(
                                "📄 Processeur %s utilisé: %s",
                                processor_used,
                                analysis_info,
                            )
                            print(
                                f"🔧 Traitement avancé: {processor_used} - {analysis_info}"
                            )
                        else:
                            self.logger.warning(
                                "Échec traitement avancé: %s",
                                result.get("message", "Erreur inconnue"),
                            )
                    else:
                        # Méthode de fallback - utiliser add_document_to_context
                        result = self.custom_ai.add_document_to_context(
                            content, filename
                        )
                        chunks_created = result.get("chunks_created", 0)

                    # Statistiques après ajout
                    stats = self.custom_ai.get_context_stats()
                    self.logger.info(
                        "📊 Nouveau contexte: %s tokens (%s)",
                        stats.get("context_size", 0),
                        stats.get("utilization_percent", 0),
                    )

                    print(
                        f"🚀 Document ajouté au CustomAI: {chunks_created} chunks créés"
                    )

                except Exception as e:
                    self.logger.warning("Erreur ajout CustomAI: %s", e)
                    chunks_created = 0

            # Stocker aussi dans la mémoire classique pour compatibilité
            if hasattr(self.ai_engine, "local_ai") and hasattr(
                self.ai_engine.local_ai, "conversation_memory"
            ):
                self.ai_engine.local_ai.conversation_memory.store_document_content(
                    filename, content
                )
                self.logger.info(
                    "Contenu stocké dans la mémoire classique pour %s", filename
                )
            else:
                self.logger.warning("Mémoire de conversation classique non disponible")

            # Arrêter l'animation
            self.is_thinking = False

            # Confirmer le traitement avec informations système 1M tokens
            preview = content[:200] + "..." if len(content) > 200 else content

            if chunks_created > 0:
                # Message avec informations CustomAI
                stats = self.custom_ai.get_context_stats()
                success_msg = f"""✅ **{filename}** traité avec succès !

🚀 **Ajouté au CustomAI {'Ultra' if self.custom_ai.ultra_mode else 'Classique'}:**
• {chunks_created} chunks créés
• Contexte total: {stats.get('context_size', 0):,} / {stats.get('max_context_length', 1000000):,} tokens
• Utilisation: {stats.get('utilization_percent', 0):.1f}%

Vous pouvez maintenant me poser des questions sur ce document."""
            else:
                # Message standard
                success_msg = f"✅ **{filename}** traité avec succès !\n\n**Aperçu du contenu:**\n{preview}\n\nVous pouvez maintenant me poser des questions dessus."

            self.root.after(0, lambda: self.add_ai_response(success_msg))

        except Exception as e:
            self.logger.error("Erreur lors du traitement de %s: %s", filename, str(e))
            self.is_thinking = False
            error_msg = f"❌ Erreur lors du traitement de **{filename}** : {str(e)}"
            self.root.after(0, lambda: self.add_ai_response(error_msg))
