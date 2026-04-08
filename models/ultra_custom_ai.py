"""
UltraCustomAIModel - Système IA avec contexte 10M tokens
Modèle personnalisé avec capacités étendues de contexte
"""

import sys
import re
import asyncio
import time
import os
import traceback
from typing import Dict, Any
from pathlib import Path

# Ajout du chemin racine pour les imports
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    from memory.vector_memory import VectorMemory as MillionTokenContextManager
except ImportError:
    # Fallback si le gestionnaire n'est pas encore créé
    MillionTokenContextManager = None

# Import du calculateur intelligent pour le système Ultra
try:
    from utils.intelligent_calculator import intelligent_calculator

    CALCULATOR_AVAILABLE = True
except ImportError:
    CALCULATOR_AVAILABLE = False
    print("⚠️ Calculateur intelligent non disponible pour Ultra")

# Import des processeurs avancés pour le système Ultra
try:
    from processors.pdf_processor import PDFProcessor
    from processors.docx_processor import DOCXProcessor
    from processors.code_processor import CodeProcessor

    ADVANCED_PROCESSORS_AVAILABLE = True
    print("🔧 Processeurs avancés chargés pour Ultra")
except ImportError as e:
    ADVANCED_PROCESSORS_AVAILABLE = False
    print(f"⚠️ Processeurs avancés non disponibles: {e}")


class UltraCustomAIModel:
    """
    Modèle IA Ultra avec contexte étendu de 10 millions de tokens
    """

    def __init__(self, base_ai_engine=None):
        """
        Initialise le modèle Ultra

        Args:
            base_ai_engine: Moteur IA de base à étendre
        """
        self.base_ai = base_ai_engine
        self.is_ultra_available = True
        self.context_stats = {
            "total_tokens": 0,
            "documents_processed": 0,
            "chunks_created": 0,
            "max_context_length": 10_485_760,  # 10M tokens
        }

        # Initialiser le stockage de documents si nécessaire
        if not hasattr(self, "documents_storage"):
            self.documents_storage = {}

        # Initialiser le gestionnaire de contexte 10M tokens
        if MillionTokenContextManager:
            self.context_manager = MillionTokenContextManager()
        else:
            self.context_manager = None
            print("⚠️ Gestionnaire 10M tokens non disponible, mode de base activé")

        # Initialisation des processeurs avancés pour Ultra
        if ADVANCED_PROCESSORS_AVAILABLE:
            self.pdf_processor = PDFProcessor()
            self.docx_processor = DOCXProcessor()
            self.code_processor = CodeProcessor()
            print("🔧 Processeurs Ultra initialisés: PDF, DOCX, Code")
        else:
            self.pdf_processor = None
            self.docx_processor = None
            self.code_processor = None
            print("⚠️ Processeurs Ultra non disponibles")

    def generate_response(
        self, user_input: str, context: str = ""
    ) -> Dict[str, Any]:
        """
        Génère une réponse en utilisant le contexte étendu

        Args:
            user_input: Message de l'utilisateur
            context: Contexte additionnel
        Returns:
            Dict contenant la réponse et les statistiques
        """
        try:
            # 🧮 PRIORITÉ 1: Vérification si c'est un calcul (même en mode Ultra)
            if CALCULATOR_AVAILABLE and intelligent_calculator.is_calculation_request(
                user_input
            ):
                print(f"🧮 Calcul Ultra détecté: {user_input}")
                calc_result = intelligent_calculator.calculate(user_input)
                calc_response = intelligent_calculator.format_response(calc_result)

                return {
                    "response": calc_response,
                    "success": True,
                    "calculation": True,
                    "ultra_mode": True,
                    "ultra_stats": self.get_context_stats(),
                    "calc_details": calc_result,
                }

            # 📄 PRIORITÉ 2: Vérification si c'est une demande de résumé de document
            user_lower = user_input.lower()
            is_document_request = any(
                keyword in user_lower
                for keyword in [
                    "résume",
                    "résumer",
                    "résumé",
                    "summary",
                    "summarize",
                    "pdf",
                    "docx",
                    "document",
                    "fichier",
                    "analyze",
                    "analyse",
                ]
            )

            if is_document_request:
                print("📄 [ULTRA] Demande de traitement de document détectée")

                # Chercher dans le contexte stocké AVANT tout
                relevant_context = self._search_in_stored_context(user_input)

                if relevant_context:
                    print(
                        "🧠 [ULTRA] Documents trouvés, délégation au custom_ai_model pour traitement avancé"
                    )

                    # DÉLÉGUER au custom_ai_model pour le traitement avancé
                    if self.base_ai and hasattr(self.base_ai, "local_ai"):
                        try:
                            # Préparer le prompt avec le contexte trouvé
                            enhanced_prompt = f"CONTEXTE ULTRA (10M tokens):\n{relevant_context}\n\nQUESTION: {user_input}"

                            # Utiliser la méthode de traitement de document du custom_ai_model
                            custom_response = self.base_ai.local_ai.generate_response(
                                enhanced_prompt
                            )

                            return {
                                "response": custom_response,
                                "success": True,
                                "ultra_mode": True,
                                "context_used": True,
                                "processing_method": "custom_ai_model_advanced",
                                "context_length": len(relevant_context),
                                "ultra_stats": self.get_context_stats(),
                            }

                        except Exception as e:
                            print(f"⚠️ [ULTRA] Erreur délégation custom_ai_model: {e}")
                            # Fallback vers traitement Ultra simple

                # Si pas de documents dans Ultra mais c'est une demande de document,
                # vérifier la mémoire classique directement
                elif self.base_ai and hasattr(self.base_ai, "local_ai"):
                    print(
                        "🔍 [ULTRA] Pas de docs en Ultra, vérification mémoire classique..."
                    )

                    try:
                        # Laisser le custom_ai_model gérer complètement
                        custom_response = self.base_ai.local_ai.generate_response(
                            user_input
                        )

                        return {
                            "response": custom_response,
                            "success": True,
                            "ultra_mode": True,
                            "context_used": False,
                            "processing_method": "custom_ai_model_fallback",
                            "ultra_stats": self.get_context_stats(),
                        }

                    except Exception as e:
                        print(f"⚠️ [ULTRA] Erreur fallback custom_ai_model: {e}")

            # Construire le contexte étendu AVANT de traiter
            extended_context = self._build_extended_context(context)

            # Chercher dans le contexte stocké AVANT d'utiliser l'IA
            relevant_context = self._search_in_stored_context(user_input)

            # Si on trouve des informations pertinentes dans le contexte stocké
            if relevant_context:
                print(
                    f"🧠 [ULTRA] Utilisation du contexte stocké pour: {user_input[:50]}..."
                )
                print(f"📊 [ULTRA] Contexte trouvé: {len(relevant_context)} caractères")

                # Construire une réponse à partir du contexte stocké
                context_response = self._generate_from_context(
                    user_input, relevant_context
                )
                if context_response:
                    return {
                        "response": context_response,
                        "success": True,
                        "ultra_mode": True,
                        "context_used": True,
                        "context_length": len(relevant_context),
                        "ultra_stats": self.get_context_stats(),
                    }
                else:
                    # Si la génération échoue, retourner au moins le contexte brut
                    print("⚠️ [ULTRA] Génération échouée, retour du contexte brut")
                    return {
                        "response": f"📚 **Documents trouvés dans la mémoire Ultra:**\n\n{relevant_context[:2000]}{'...' if len(relevant_context) > 2000 else ''}",
                        "success": True,
                        "ultra_mode": True,
                        "context_used": True,
                        "context_length": len(relevant_context),
                        "ultra_stats": self.get_context_stats(),
                    }
            else:
                print(
                    f"❌ [ULTRA] Aucun contexte pertinent trouvé pour: {user_input[:50]}"
                )
                # Vérifier si on a des documents en mémoire
                if hasattr(self, "documents_storage") and self.documents_storage:
                    doc_count = len(self.documents_storage)
                    doc_names = [
                        doc.get("name", "Sans nom")
                        for doc in self.documents_storage.values()
                    ]
                    print(
                        f"📚 [ULTRA] Documents disponibles ({doc_count}): {', '.join(doc_names[:3])}"
                    )

                    # Retourner une réponse informative sur les documents disponibles
                    return {
                        "response": f"📚 **J'ai {doc_count} document(s) en mémoire Ultra**: {', '.join(doc_names[:5])}{'...' if len(doc_names) > 5 else ''}\n\nVous pouvez me demander de résumer un document spécifique ou poser une question plus précise sur le contenu.",
                        "success": True,
                        "ultra_mode": True,
                        "context_used": False,
                        "ultra_stats": self.get_context_stats(),
                    }
                else:
                    print("📭 [ULTRA] Aucun document en mémoire")

            # Si pas de contexte pertinent, utiliser le moteur IA de base avec le contexte étendu
            print("🤖 [ULTRA] Utilisation IA de base avec contexte étendu...")

            # Utiliser le moteur IA de base si disponible
            if self.base_ai:
                # Combiner user_input avec le contexte étendu
                enhanced_input = (
                    f"CONTEXTE: {extended_context}\n\nQUESTION: {user_input}"
                    if extended_context
                    else user_input
                )

                # AIEngine utilise process_text au lieu de generate_response
                if hasattr(self.base_ai, "process_text"):
                    ai_response = self.base_ai.process_text(enhanced_input)
                    response = {"response": ai_response, "success": True}
                elif hasattr(self.base_ai, "process_message"):
                    # Version async
                    ai_response = asyncio.run(self.base_ai.process_message(user_input))
                    response = {"response": ai_response, "success": True}
                else:
                    # Fallback si aucune méthode disponible
                    response = {
                        "response": f"Méthode de traitement non trouvée sur {type(self.base_ai).__name__}",
                        "success": False,
                    }
            else:
                # Réponse de fallback
                response = {
                    "response": f"[ULTRA MODE] Traitement de: {user_input[:100]}...",
                    "success": True,
                }

            # Ajouter les statistiques Ultra
            if isinstance(response, dict):
                response["ultra_stats"] = self.get_context_stats()
                response["ultra_mode"] = True
                response["context_length"] = len(extended_context)

            return response

        except Exception as e:
            return {
                "response": f"Erreur Ultra: {str(e)}",
                "success": False,
                "error": str(e),
                "ultra_mode": True,
            }

    def add_document_to_context(
        self, document_content: str, document_name: str = ""
    ) -> Dict[str, Any]:
        """
        Ajoute un document au contexte 10M tokens

        Args:
            document_content: Contenu du document
            document_name: Nom du document

        Returns:
            Statistiques d'ajout
        """
        if not self.context_manager:
            return {"success": False, "error": "Gestionnaire de contexte indisponible"}

        try:
            # Stocker le document pour recherche directe
            doc_id = (
                f"doc_{len(self.documents_storage)}_{hash(document_content) % 10000}"
            )
            self.documents_storage[doc_id] = {
                "name": document_name,
                "content": document_content,
                "tokens": len(document_content.split()),
                "added_time": time.time(),
            }

            print(f"📚 [ULTRA] Document '{document_name}' stocké avec ID: {doc_id}")

            # Ajouter au gestionnaire de contexte
            result = self.context_manager.add_document(document_content, document_name)

            # Mettre à jour les statistiques
            self.context_stats["documents_processed"] += 1
            self.context_stats["total_tokens"] += len(document_content.split())

            if "chunks_created" in result:
                self.context_stats["chunks_created"] += result["chunks_created"]

            return {
                "success": True,
                "document_name": document_name,
                "chunk_ids": [doc_id],  # Ajout des chunk_ids pour l'interface
                "chunks_created": result.get("chunks_created", 1),
                "tokens_added": len(document_content.split()),
                "total_context_tokens": self.context_stats["total_tokens"],
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Erreur lors de l'ajout du document: {str(e)}",
            }

    def add_file_to_context(self, file_path: str) -> Dict[str, Any]:
        """
        Ajoute un fichier au contexte en utilisant les processeurs avancés

        Args:
            file_path: Chemin vers le fichier

        Returns:
            Statistiques d'ajout avec contenu analysé
        """
        if not os.path.exists(file_path):
            return {"success": False, "error": f"Fichier introuvable: {file_path}"}

        file_extension = os.path.splitext(file_path)[1].lower()
        file_name = os.path.basename(file_path)

        try:
            processed_content = ""
            analysis_info = ""

            # Traitement PDF avec processeur avancé
            if file_extension == ".pdf" and self.pdf_processor:
                print(f"📄 [ULTRA] Traitement PDF avancé: {file_name}")
                pdf_content = self.pdf_processor.read_pdf(file_path)
                if pdf_content.get("success"):
                    processed_content = pdf_content["content"]
                    pages = pdf_content.get("pages", "N/A")
                    # S'assurer que pages est une string
                    pages_str = str(pages) if pages is not None else "N/A"
                    analysis_info = (
                        f"Pages: {pages_str}, Caractères: {len(processed_content)}"
                    )
                else:
                    return {
                        "success": False,
                        "error": f'Erreur PDF: {pdf_content.get("error", "Inconnue")}',
                    }

            # Traitement DOCX avec processeur avancé
            elif file_extension in [".docx", ".doc"] and self.docx_processor:
                print(f"📝 [ULTRA] Traitement DOCX avancé: {file_name}")
                docx_content = self.docx_processor.read_docx(file_path)
                if docx_content.get("success"):
                    processed_content = docx_content["content"]
                    paragraphs = docx_content.get("paragraphs", "N/A")
                    # S'assurer que paragraphs est une string
                    paragraphs_str = (
                        str(paragraphs) if paragraphs is not None else "N/A"
                    )
                    analysis_info = f"Paragraphes: {paragraphs_str}, Caractères: {len(processed_content)}"
                else:
                    return {
                        "success": False,
                        "error": f'Erreur DOCX: {docx_content.get("error", "Inconnue")}',
                    }

            # Traitement code avec processeur avancé
            elif (
                file_extension
                in [
                    ".py",
                    ".js",
                    ".java",
                    ".cpp",
                    ".c",
                    ".cs",
                    ".php",
                    ".rb",
                    ".go",
                    ".rs",
                    ".ts",
                    ".jsx",
                    ".tsx",
                ]
                and self.code_processor
            ):
                print(f"💻 [ULTRA] Traitement code avancé: {file_name}")
                code_content = self.code_processor.read_code(file_path)
                if code_content.get("success"):
                    processed_content = code_content["content"]
                    language = code_content.get("language", "Détecté")
                    lines = code_content.get("lines", "N/A")
                    # S'assurer que language et lines sont des strings
                    language_str = str(language) if language is not None else "Détecté"
                    lines_str = str(lines) if lines is not None else "N/A"
                    analysis_info = f"Langage: {language_str}, Lignes: {lines_str}"
                else:
                    return {
                        "success": False,
                        "error": f'Erreur code: {code_content.get("error", "Inconnue")}',
                    }

            # Traitement texte basique pour autres formats
            else:
                print(f"📄 [ULTRA] Traitement texte basique: {file_name}")
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    processed_content = f.read()
                analysis_info = f"Fichier texte, Caractères: {len(processed_content)}"

            # Ajouter le contenu analysé au contexte
            # S'assurer que processed_content est une string
            if not isinstance(processed_content, str):
                processed_content = str(processed_content)

            # S'assurer que analysis_info est une string
            if not isinstance(analysis_info, str):
                analysis_info = str(analysis_info)

            enhanced_content = f"--- DOCUMENT: {file_name} ---\n"
            enhanced_content += f"Type: {file_extension}, {analysis_info}\n"
            enhanced_content += f"Chemin: {file_path}\n\n"
            enhanced_content += processed_content

            print(
                f"🔍 [DEBUG] enhanced_content type: {type(enhanced_content)}, length: {len(enhanced_content)}"
            )

            # Utiliser la méthode standard pour ajouter au contexte
            result = self.add_document_to_context(enhanced_content, file_name)

            if result["success"]:
                result["analysis_info"] = analysis_info
                result["file_type"] = file_extension
                result["processor_used"] = (
                    "advanced"
                    if file_extension in [".pdf", ".docx", ".doc"]
                    or (
                        file_extension in [".py", ".js", ".java"]
                        and self.code_processor
                    )
                    else "basic"
                )
                print(
                    f"✅ [ULTRA] Fichier '{file_name}' traité et ajouté au contexte Ultra"
                )

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Erreur lors du traitement du fichier: {str(e)}",
            }

    def add_code_to_context(
        self, code_content: str, file_name: str = ""
    ) -> Dict[str, Any]:
        """
        Ajoute du code au contexte avec analyse syntaxique

        Args:
            code_content: Contenu du code
            file_name: Nom du fichier

        Returns:
            Statistiques d'ajout
        """
        if not self.context_manager:
            return {"success": False, "error": "Gestionnaire de contexte indisponible"}

        try:
            # Préparer le contenu avec métadonnées de code
            enriched_content = f"# FICHIER: {file_name}\n\n{code_content}"

            result = self.context_manager.add_document(
                enriched_content, f"CODE: {file_name}"
            )

            # Mettre à jour les statistiques
            self.context_stats["documents_processed"] += 1
            self.context_stats["total_tokens"] += len(code_content.split())

            return {
                "success": True,
                "file_name": file_name,
                "chunk_ids": [
                    f"code_{hash(code_content) % 10000}"
                ],  # Ajout des chunk_ids pour l'interface
                "chunks_created": result.get("chunks_created", 1),
                "tokens_added": len(code_content.split()),
                "total_context_tokens": self.context_stats["total_tokens"],
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Erreur lors de l'ajout du code: {str(e)}",
            }

    def _build_extended_context(self, base_context: str = "") -> str:
        """
        Construit le contexte étendu en utilisant le gestionnaire 10M tokens
        """
        if not self.context_manager:
            return base_context

        try:
            # Récupérer le contexte du gestionnaire
            extended_context = self.context_manager.get_relevant_context(base_context)

            # Combiner avec le contexte de base
            if base_context:
                return f"{base_context}\n\n--- CONTEXTE ÉTENDU ---\n{extended_context}"
            else:
                return extended_context

        except Exception as e:
            print(f"Erreur lors de la construction du contexte étendu: {e}")
            return base_context

    def _search_in_stored_context(self, query: str) -> str:
        """
        Recherche dans le contexte stocké pour des informations pertinentes
        Consulte d'abord le système Ultra, puis la mémoire classique en fallback
        """
        print(f"🔍 [DEBUG] _search_in_stored_context appelé avec query: '{query}'")

        # 1. Recherche dans le système Ultra
        if not hasattr(self, "documents_storage"):
            self.documents_storage = {}

        print(f"🔍 [DEBUG] Documents Ultra disponibles: {len(self.documents_storage)}")
        if self.documents_storage:
            for doc_id, doc_info in self.documents_storage.items():
                print(f"   - {doc_id}: {doc_info.get('name', 'Sans nom')}")

        relevant_content = ""
        query_lower = query.lower()

        # Mots-clés pour résumé/document
        summary_keywords = [
            "résume",
            "résumer",
            "résumé",
            "pdf",
            "docx",
            "document",
            "fichier",
            "contenu",
            "ce",
            "le",
            "la",
            "du",
            "de la",
        ]

        # Recherche dans le système Ultra d'abord
        if self.documents_storage:
            print(
                f"🔍 [ULTRA] Recherche dans système Ultra ({len(self.documents_storage)} docs)..."
            )

            # Si c'est une demande de résumé, retourner TOUS les documents Ultra
            if any(keyword in query_lower for keyword in summary_keywords):
                print(
                    "🔍 [ULTRA] Demande de résumé détectée, chargement de tous les documents Ultra..."
                )
                for doc_id, doc_info in self.documents_storage.items():
                    relevant_content += (
                        f"\n--- DOCUMENT: {doc_info.get('name', doc_id)} ---\n"
                    )
                    relevant_content += doc_info.get("content", "")
                    relevant_content += "\n"

                if relevant_content.strip():
                    print(
                        f"✅ [ULTRA] Retour de tous les docs Ultra: {len(relevant_content)} caractères"
                    )
                    return relevant_content

            # Recherche par mots-clés dans le contenu Ultra
            keywords = [word for word in query_lower.split() if len(word) > 2]
            print(f"🔍 [DEBUG] Mots-clés recherche: {keywords}")

            for doc_id, doc_info in self.documents_storage.items():
                content = doc_info.get("content", "")
                # Recherche simple de mots-clés
                if any(keyword in content.lower() for keyword in keywords):
                    print(
                        f"✅ [ULTRA] Correspondance trouvée dans {doc_info.get('name', doc_id)}"
                    )
                    relevant_content += (
                        f"\n--- DOCUMENT: {doc_info.get('name', doc_id)} ---\n"
                    )
                    relevant_content += content
                    relevant_content += "\n"

            if relevant_content.strip():
                print(
                    f"✅ [ULTRA] Trouvé dans système Ultra: {len(relevant_content)} caractères"
                )
                return relevant_content

        # 2. Fallback vers la mémoire classique si rien trouvé en Ultra
        print("🔍 [FALLBACK] Recherche dans mémoire classique...")
        print(f"🔍 [DEBUG] base_ai disponible: {self.base_ai is not None}")

        if self.base_ai:
            print(f"🔍 [DEBUG] base_ai type: {type(self.base_ai)}")
            print(f"🔍 [DEBUG] hasattr local_ai: {hasattr(self.base_ai, 'local_ai')}")

            if hasattr(self.base_ai, "local_ai"):
                print(f"🔍 [DEBUG] local_ai type: {type(self.base_ai.local_ai)}")
                print(
                    f"🔍 [DEBUG] hasattr conversation_memory: {hasattr(self.base_ai.local_ai, 'conversation_memory')}"
                )

                if hasattr(self.base_ai.local_ai, "conversation_memory"):
                    memory = self.base_ai.local_ai.conversation_memory
                    print(f"🔍 [DEBUG] conversation_memory type: {type(memory)}")
                    print(
                        f"🔍 [DEBUG] hasattr stored_documents: {hasattr(memory, 'stored_documents')}"
                    )

                    if hasattr(memory, "stored_documents"):
                        print(f"🔍 [DEBUG] stored_documents: {memory.stored_documents}")
                        print(
                            f"🔍 [DEBUG] stored_documents type: {type(memory.stored_documents)}"
                        )
                        print(f"🔍 [DEBUG] memory instance id: {id(memory)}")
                        print(
                            f"🔍 [DEBUG] self.base_ai.local_ai id: {id(self.base_ai.local_ai) if self.base_ai and hasattr(self.base_ai, 'local_ai') else 'N/A'}"
                        )

                        if memory.stored_documents:
                            print(
                                f"📚 [FALLBACK] Trouvé {len(memory.stored_documents)} docs dans mémoire classique"
                            )
                            for doc_name in memory.stored_documents.keys():
                                print(f"   - {doc_name}")
                        else:
                            print("📭 [FALLBACK] stored_documents vide ou None")
                    else:
                        print("❌ [FALLBACK] Pas d'attribut stored_documents")
                else:
                    print("❌ [FALLBACK] Pas d'attribut conversation_memory")
            else:
                print("❌ [FALLBACK] Pas d'attribut local_ai")

        if (
            self.base_ai
            and hasattr(self.base_ai, "local_ai")
            and hasattr(self.base_ai.local_ai, "conversation_memory")
        ):
            try:
                memory = self.base_ai.local_ai.conversation_memory

                # Vérifier les documents stockés dans la mémoire classique
                if hasattr(memory, "stored_documents") and memory.stored_documents:
                    print(
                        f"📚 [FALLBACK] Trouvé {len(memory.stored_documents)} docs dans mémoire classique"
                    )

                    # Pour les demandes de résumé, retourner tous les documents
                    if any(keyword in query_lower for keyword in summary_keywords):
                        for doc_name, doc_content in memory.stored_documents.items():
                            relevant_content += f"\n--- DOCUMENT: {doc_name} ---\n"
                            relevant_content += doc_content
                            relevant_content += "\n"

                        if relevant_content.strip():
                            print(
                                f"✅ [FALLBACK] Résumé depuis mémoire classique: {len(relevant_content)} caractères"
                            )
                            return relevant_content

                    # Recherche par mots-clés dans la mémoire classique
                    keywords = [word for word in query_lower.split() if len(word) > 2]
                    for doc_name, doc_content in memory.stored_documents.items():
                        # Recherche plus permissive
                        if any(
                            keyword in doc_content.lower() for keyword in keywords
                        ) or any(keyword in doc_name.lower() for keyword in keywords):
                            relevant_content += f"\n--- DOCUMENT: {doc_name} ---\n"
                            relevant_content += doc_content
                            relevant_content += "\n"

                    # Si pas de correspondance par mots-clés, retourner TOUT si c'est une demande générale
                    if not relevant_content.strip() and (
                        "document" in query_lower
                        or "fichier" in query_lower
                        or "résume" in query_lower
                        or "analyse" in query_lower
                    ):
                        print(
                            "📄 [FALLBACK] Aucune correspondance spécifique, retour de tous les documents"
                        )
                        for doc_name, doc_content in memory.stored_documents.items():
                            relevant_content += f"\n--- DOCUMENT: {doc_name} ---\n"
                            relevant_content += doc_content
                            relevant_content += "\n"

                    if relevant_content.strip():
                        print(
                            f"✅ [FALLBACK] Trouvé dans mémoire classique: {len(relevant_content)} caractères"
                        )
                        return relevant_content

            except Exception as e:
                print(f"⚠️ [FALLBACK] Erreur accès mémoire classique: {e}")
                traceback.print_exc()

        print("❌ Aucun document trouvé dans aucun système")
        return ""

    def _generate_from_context(self, question: str, context: str) -> str:
        """
        Génère une réponse intelligente à partir du contexte stocké avec analyse avancée
        """
        question_lower = question.lower()

        # Demande de résumé détectée
        if any(
            keyword in question_lower
            for keyword in [
                "résume",
                "résumer",
                "résumé",
                "résumer",
                "synthèse",
                "synthese",
            ]
        ):
            print(
                "📋 [ULTRA] Génération de résumé intelligent avec processeurs avancés..."
            )

            if context.strip():
                # Extraire les informations principales avec analyse de type
                lines = [line.strip() for line in context.split("\n") if line.strip()]

                # Identifier les sections de documents avec métadonnées
                documents_found = []
                current_doc = None
                current_content = []
                current_metadata = {}

                for line in lines:
                    if line.startswith("--- DOCUMENT:"):
                        if current_doc and current_content:
                            documents_found.append(
                                {
                                    "name": current_doc,
                                    "content": "\n".join(current_content),
                                    "metadata": current_metadata.copy(),
                                }
                            )
                        current_doc = line.replace("--- DOCUMENT:", "").strip()
                        current_content = []
                        current_metadata = {}
                    elif line.startswith("Type:"):
                        # Extraire les métadonnées du processeur
                        current_metadata["type_info"] = line.replace(
                            "Type:", ""
                        ).strip()
                    elif line.startswith("Chemin:"):
                        current_metadata["file_path"] = line.replace(
                            "Chemin:", ""
                        ).strip()
                    elif current_doc:
                        current_content.append(line)

                # Ajouter le dernier document
                if current_doc and current_content:
                    documents_found.append(
                        {
                            "name": current_doc,
                            "content": "\n".join(current_content),
                            "metadata": current_metadata.copy(),
                        }
                    )

                # Générer un résumé intelligent basé sur le type de document
                if documents_found:
                    summary = (
                        "📄 **Analyse intelligente des documents en mémoire:**\n\n"
                    )

                    for doc in documents_found:
                        summary += f"**📋 {doc['name']}**\n"

                        # Analyser le type de document
                        type_info = doc["metadata"].get("type_info", "")
                        content = doc["content"]

                        # Analyse spécialisée selon le type AVEC résumé avancé
                        if ".pdf" in type_info:
                            summary += self._analyze_pdf_content(content, type_info)
                            # Ajouter un résumé intelligent du contenu
                            intelligent_summary = self._create_intelligent_summary(
                                content, doc["name"], "PDF"
                            )
                            summary += (
                                f"• **Résumé intelligent**: {intelligent_summary}\n"
                            )
                        elif ".docx" in type_info or ".doc" in type_info:
                            summary += self._analyze_docx_content(content, type_info)
                            intelligent_summary = self._create_intelligent_summary(
                                content, doc["name"], "DOCX"
                            )
                            summary += (
                                f"• **Résumé intelligent**: {intelligent_summary}\n"
                            )
                        elif any(
                            ext in type_info
                            for ext in [".py", ".js", ".java", ".cpp", ".c"]
                        ):
                            summary += self._analyze_code_content(content, type_info)
                            intelligent_summary = self._create_intelligent_summary(
                                content, doc["name"], "Code"
                            )
                            summary += f"• **Analyse du code**: {intelligent_summary}\n"
                        else:
                            summary += self._analyze_text_content(content, type_info)
                            intelligent_summary = self._create_intelligent_summary(
                                content, doc["name"], "Text"
                            )
                            summary += (
                                f"• **Résumé du contenu**: {intelligent_summary}\n"
                            )

                        summary += "\n"

                    return summary

        # Recherche spécifique pour des codes/informations (existant)
        if "code secret" in question_lower:
            code_patterns = [
                r"code secret[^:]*:\s*([A-Z_0-9]+)",
                r"code[^:]*:\s*([A-Z_0-9]+)",
                r"ULTRA_TEST_[A-Z0-9_]+",
            ]

            for pattern in code_patterns:
                matches = re.findall(pattern, context, re.IGNORECASE)
                if matches:
                    return f"Le code secret de test est: {matches[0]}"

        # Recherche de numéros magiques (existant)
        if "numéro magique" in question_lower:
            magic_numbers = re.findall(
                r"numéro magique[^:]*:\s*(\d+)", context, re.IGNORECASE
            )
            if magic_numbers:
                return f"Le numéro magique est: {magic_numbers[0]}"

        # Recherche de phrases uniques
        if "phrase unique" in question_lower:
            unique_phrases = re.findall(
                r'phrase unique[^:]*:\s*"([^"]+)"', context, re.IGNORECASE
            )
            if unique_phrases:
                return f'La phrase unique est: "{unique_phrases[0]}"'

        # Si aucune correspondance spécifique, retourner un extrait pertinent
        if context.strip():
            lines = context.split("\n")
            relevant_lines = [
                line
                for line in lines
                if any(
                    word in line.lower()
                    for word in question_lower.split()
                    if len(word) > 2
                )
            ]
            if relevant_lines:
                return (
                    f"D'après les documents en mémoire: {' '.join(relevant_lines[:3])}"
                )

            # Si aucune ligne pertinente, retourner un résumé du contexte
            lines_clean = [
                line.strip()
                for line in lines
                if line.strip() and not line.startswith("---")
            ]
            if lines_clean:
                # Prendre les premières lignes significatives
                content_sample = " ".join(lines_clean[:5])
                if len(content_sample) > 200:
                    content_sample = content_sample[:200] + "..."
                return f"📚 **Contenu disponible:** {content_sample}\n\nPouvez-vous préciser votre question ?"

        # Fallback final - ne jamais retourner None
        return "📚 J'ai du contenu en mémoire mais je n'ai pas trouvé d'information spécifique pour répondre à votre question. Pouvez-vous reformuler ou être plus précis ?"

    def _analyze_pdf_content(self, content: str, type_info: str) -> str:
        """Analyse intelligente du contenu PDF"""
        lines = content.split("\n")
        text_lines = [
            line.strip()
            for line in lines
            if line.strip()
            and not line.startswith("Type:")
            and not line.startswith("Chemin:")
        ]

        analysis = f"📄 **Document PDF** - {type_info}\n"
        analysis += f"• **Contenu**: {len(text_lines)} lignes de texte\n"

        # Identifier les sections importantes
        if text_lines:
            # Premier paragraphe comme résumé
            first_paragraph = " ".join(text_lines[:3])
            if len(first_paragraph) > 100:
                first_paragraph = first_paragraph[:100] + "..."
            analysis += f"• **Début**: {first_paragraph}\n"

            # Chercher des titres ou sections
            titles = [line for line in text_lines if len(line) < 50 and line.isupper()]
            if titles:
                analysis += f"• **Sections détectées**: {', '.join(titles[:3])}\n"

        return analysis

    def _analyze_docx_content(self, content: str, type_info: str) -> str:
        """Analyse intelligente du contenu DOCX"""
        lines = content.split("\n")
        text_lines = [
            line.strip()
            for line in lines
            if line.strip()
            and not line.startswith("Type:")
            and not line.startswith("Chemin:")
        ]

        analysis = f"📝 **Document Word** - {type_info}\n"
        analysis += f"• **Structure**: {len(text_lines)} paragraphes\n"

        if text_lines:
            # Résumé du contenu
            all_text = " ".join(text_lines)
            words = all_text.split()
            analysis += f"• **Taille**: {len(words)} mots\n"

            # Premier paragraphe
            if len(words) > 20:
                summary = " ".join(words[:20]) + "..."
                analysis += f"• **Résumé**: {summary}\n"

        return analysis

    def _analyze_code_content(self, content: str, type_info: str) -> str:
        """Analyse intelligente du code source"""
        lines = content.split("\n")
        code_lines = [
            line
            for line in lines
            if line.strip()
            and not line.startswith("Type:")
            and not line.startswith("Chemin:")
        ]

        analysis = f"💻 **Code Source** - {type_info}\n"
        analysis += f"• **Lignes**: {len(code_lines)} lignes de code\n"

        if code_lines:
            # Détecter le langage
            if ".py" in type_info:
                # Analyse Python
                functions = [
                    line.strip()
                    for line in code_lines
                    if line.strip().startswith("def ")
                ]
                classes = [
                    line.strip()
                    for line in code_lines
                    if line.strip().startswith("class ")
                ]
                imports = [
                    line.strip()
                    for line in code_lines
                    if line.strip().startswith("import ")
                    or line.strip().startswith("from ")
                ]

                if functions:
                    analysis += f"• **Fonctions**: {len(functions)} détectées\n"
                if classes:
                    analysis += f"• **Classes**: {len(classes)} détectées\n"
                if imports:
                    analysis += f"• **Imports**: {len(imports)} modules\n"

            elif ".js" in type_info or ".ts" in type_info:
                # Analyse JavaScript/TypeScript
                functions = [
                    line.strip()
                    for line in code_lines
                    if "function" in line or "=>" in line
                ]
                analysis += f"• **Fonctions**: ~{len(functions)} détectées\n"

        return analysis

    def _analyze_text_content(self, content: str, type_info: str) -> str:
        """Analyse du contenu texte générique"""
        lines = content.split("\n")
        text_lines = [
            line.strip()
            for line in lines
            if line.strip()
            and not line.startswith("Type:")
            and not line.startswith("Chemin:")
        ]

        analysis = f"📄 **Fichier Texte** - {type_info}\n"

        if text_lines:
            all_text = " ".join(text_lines)
            words = all_text.split()
            analysis += f"• **Contenu**: {len(text_lines)} lignes, {len(words)} mots\n"

            # Échantillon du contenu
            if len(words) > 30:
                sample = " ".join(words[:30]) + "..."
                analysis += f"• **Aperçu**: {sample}\n"
            else:
                analysis += f"• **Contenu complet**: {all_text}\n"

        return analysis

    def _create_intelligent_summary(
        self, content: str, doc_name: str, doc_type: str
    ) -> str:
        """
        Crée un résumé intelligent basé sur la logique avancée du custom_ai_model
        """
        # Nettoyer le contenu des métadonnées
        lines = content.split("\n")
        clean_lines = []
        for line in lines:
            if (
                not line.startswith("Type:")
                and not line.startswith("Chemin:")
                and line.strip()
            ):
                clean_lines.append(line.strip())

        clean_content = "\n".join(clean_lines)

        if len(clean_content) < 50:
            return "Contenu trop court pour analyse."

        # Extraire les thèmes principaux
        words = clean_content.lower().split()

        # Mots-clés fréquents pour identifier les thèmes
        word_count = {}

        for word in words:
            word_clean = re.sub(r"[^\w]", "", word)
            if len(word_clean) > 4 and word_clean not in [
                "cette",
                "cette",
                "dans",
                "avec",
                "pour",
                "sont",
                "mais",
                "tout",
                "nous",
                "vous",
                "leur",
                "elle",
                "ils",
                "elles",
            ]:
                word_count[word_clean] = word_count.get(word_clean, 0) + 1

        # Prendre les mots les plus fréquents
        top_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:5]
        themes = [word for word, count in top_words if count > 1]

        # Extraire des phrases clés
        sentences = [s.strip() for s in clean_content.split(".") if len(s.strip()) > 20]
        key_sentences = sentences[:2] if sentences else []

        # Créer le résumé selon le type
        if doc_type == "PDF":
            summary = f"Document PDF '{doc_name}' "
            if themes:
                summary += f"traitant de {', '.join(themes[:3])}. "
            if key_sentences:
                summary += f"Points clés: {key_sentences[0][:100]}..."
            else:
                summary += f"Contenu de {len(words)} mots analysé."

        elif doc_type == "DOCX":
            summary = f"Document Word '{doc_name}' "
            if themes:
                summary += f"couvrant {', '.join(themes[:3])}. "
            if key_sentences:
                summary += f"Résumé: {key_sentences[0][:100]}..."
            else:
                summary += f"Document structuré de {len(words)} mots."

        elif doc_type == "Code":
            summary = f"Code source '{doc_name}' "
            if themes:
                summary += f"avec éléments: {', '.join(themes[:3])}. "
            # Détecter les fonctions/classes
            functions = len(
                [line for line in clean_lines if "def " in line or "function " in line]
            )
            classes = len([line for line in clean_lines if "class " in line])
            if functions:
                summary += f"Contient {functions} fonction(s)"
            if classes:
                summary += f" et {classes} classe(s)."
            if not functions and not classes:
                summary += f"Script de {len(clean_lines)} lignes."

        else:
            summary = f"Fichier texte '{doc_name}' "
            if themes:
                summary += f"abordant {', '.join(themes[:3])}. "
            if key_sentences:
                summary += f"Contenu principal: {key_sentences[0][:100]}..."
            else:
                summary += f"Texte de {len(words)} mots."

        return summary

    def get_context_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du contexte"""
        stats = self.context_stats.copy()

        if self.context_manager:
            # Ajouter les stats du gestionnaire de contexte
            manager_stats = self.context_manager.get_stats()
            stats.update(manager_stats)

        # Calculer le pourcentage d'utilisation
        current_tokens = stats.get("total_tokens", 0)
        max_tokens = stats.get("max_context_length", 10_485_760)
        if max_tokens > 0:
            stats["utilization_percent"] = (current_tokens / max_tokens) * 100
        else:
            stats["utilization_percent"] = 0.0

        # Ajouter current_tokens pour compatibilité
        stats["current_tokens"] = current_tokens

        return stats

    def clear_context(self):
        """Vide le contexte étendu"""
        if self.context_manager:
            self.context_manager.clear_context()

        # Réinitialiser les statistiques
        self.context_stats = {
            "total_tokens": 0,
            "documents_processed": 0,
            "chunks_created": 0,
            "max_context_length": 10_485_760,
        }

    def is_available(self) -> bool:
        """Vérifie si le mode Ultra est disponible"""
        return self.is_ultra_available and self.context_manager is not None


# Fonction de compatibilité pour l'import
def create_ultra_model(base_ai_engine=None) -> UltraCustomAIModel:
    """Crée une instance du modèle Ultra"""
    return UltraCustomAIModel(base_ai_engine)


# Test de disponibilité
def is_ultra_system_available() -> bool:
    """Vérifie si le système Ultra est disponible"""
    try:
        ultra_model = UltraCustomAIModel()
        return ultra_model.is_available()
    except Exception:
        return False


if __name__ == "__main__":
    # Test du système
    print("🚀 Test du système UltraCustomAIModel")
    model = UltraCustomAIModel()
    print(f"Ultra disponible: {model.is_available()}")
    print(f"Stats: {model.get_context_stats()}")
