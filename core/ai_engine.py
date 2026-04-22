"""
Moteur principal de l'IA personnelle
Gère l'orchestration entre les différents modules
"""

import asyncio
import concurrent.futures
import glob
import os
import re as _re
import tempfile
import threading
import shutil
from pathlib import Path
from datetime import datetime as _dt
from typing import Any, Dict, List, Optional

import requests as _req

from generators.code_generator import CodeGenerator as OllamaCodeGenerator
from generators.document_generator import DocumentGenerator
from memory.vector_memory import VectorMemory
from models.advanced_code_generator import \
    AdvancedCodeGenerator as WebCodeGenerator
from models.conversation_memory import ConversationMemory
from models.custom_ai_model import CustomAIModel
from models.internet_search import (EnhancedInternetSearchEngine,
                                    InternetSearchEngine)
from models.ml_faq_model import MLFAQModel
from models.smart_code_searcher import multi_source_searcher
from models.smart_web_searcher import search_smart_code
from processors.code_processor import CodeProcessor
from processors.docx_processor import DOCXProcessor
from processors.pdf_processor import PDFProcessor
from tools.local_tools import local_math
from utils.file_manager import FileManager
from utils.logger import setup_logger

from .chat_orchestrator import ChatOrchestrator
from .config import get_config
from .conversation import ConversationManager
from .mcp_client import MCPManager
from .validation import validate_input

try:
    from .language_detector import LanguageDetector
    _LANG_DETECT_AVAILABLE = True
except ImportError:
    _LANG_DETECT_AVAILABLE = False

try:
    from .web_cache import WebCache
    _WEB_CACHE_AVAILABLE = True
except ImportError:
    _WEB_CACHE_AVAILABLE = False

try:
    from .conversation_exporter import ConversationExporter
    _EXPORTER_AVAILABLE = True
except ImportError:
    _EXPORTER_AVAILABLE = False

try:
    from .knowledge_base_manager import KnowledgeBaseManager
    _KB_AVAILABLE = True
except ImportError:
    _KB_AVAILABLE = False

try:
    from .command_history import CommandHistory
    _CMD_HISTORY_AVAILABLE = True
except ImportError:
    _CMD_HISTORY_AVAILABLE = False

try:
    from .session_manager import SessionManager
    _SESSION_AVAILABLE = True
except ImportError:
    _SESSION_AVAILABLE = False


class AIEngine:
    """
    Moteur principal de l'IA personnelle
    """

    @staticmethod
    def _run_async(coro):
        """Exécute une coroutine depuis un contexte synchrone, de façon robuste."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result(timeout=60)

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialise le moteur IA

        Args:
            config: Configuration personnalisée (optionnel)
        """
        self.config = config or get_config().get_section("ai")
        self.logger = setup_logger("AIEngine")

        # Initialisation des composants
        self.file_manager = FileManager()

        self.current_request_id = 0

        # Initialiser session_context AVANT tout le reste
        self.session_context = {
            "documents_processed": [],
            "code_files_processed": [],
            "last_document_type": None,
            "current_document": None,
        }

        # Initialisation de la mémoire et du gestionnaire de conversations
        self.conversation_memory = ConversationMemory()
        self.conversation_manager = ConversationManager(memory=self.conversation_memory)

        # Modèle IA local personnalisé avec mémoire de conversation (100% autonome)
        try:
            self.local_ai = CustomAIModel(conversation_memory=self.conversation_memory)
            self.ml_ai = MLFAQModel()  # Modèle ML local (TF-IDF)

            # 📚 Préchargement FAQ en arrière-plan pour éviter le lazy-load
            # de 2-5s sur le premier predict() utilisateur.
            def _preload_faq():
                try:
                    self.ml_ai._ensure_loaded()
                    self.logger.info("📚 FAQ préchargée en arrière-plan")
                except Exception as exc:
                    self.logger.warning("⚠️ Préchargement FAQ échoué : %s", exc)
            threading.Thread(target=_preload_faq, daemon=True).start()

            self.model = (
                self.local_ai
            )  # Alias pour compatibilité avec l'interface graphique
            self.logger.info("✅ Modèle IA local avec mémoire initialisé")
            self.logger.info("✅ Modèle ML (TF-IDF) initialisé")
            # Initialisation du gestionnaire de LLM
            self.llm_manager = (
                self.local_ai
            )  # Pour compatibilité avec les fonctions qui utilisent llm_manager
        except (ImportError, AttributeError) as e:
            self.logger.error("❌ Erreur lors de l'initialisation du modèle IA : %s", e)
            # Fallback sur l'ancien système
            self.local_ai = CustomAIModel()
            self.ml_ai = None
            self.model = self.local_ai
            self.llm_manager = self.local_ai

        # Processeurs
        self.pdf_processor = PDFProcessor()
        self.docx_processor = DOCXProcessor()
        self.code_processor = CodeProcessor()

        # Générateurs avec support Ollama
        llm_instance = (
            self.local_ai.local_llm if hasattr(self.local_ai, "local_llm") else None
        )
        self.document_generator = DocumentGenerator(llm=llm_instance)
        self.ollama_code_generator = OllamaCodeGenerator(
            llm=llm_instance
        )  # Générateur avec Ollama
        self.code_generator = WebCodeGenerator()  # Générateur avec recherche web
        self.web_code_searcher = multi_source_searcher

        self.logger.info(
            "Moteur IA initialisé avec succès (Générateurs Ollama + Web activés)"
        )

        # Initialiser le gestionnaire MCP et enregistrer les outils locaux
        self.mcp_manager = MCPManager()
        self._setup_mcp_tools()

        # Charger l'identité depuis le Modelfile pour l'injecter dans le system prompt
        self._modelfile_system = self._load_modelfile_system()

        # Orchestrateur amélioré pour la page Chat (ReAct + scratchpad + sécurités)
        self._chat_orchestrator = ChatOrchestrator()
        self.logger.info("✅ ChatOrchestrator initialisé (ReAct + scratchpad + détection de boucle)")

        self._current_lang_instruction = ""
        self._init_v7_modules()

    # ------------------------------------------------------------------
    # Chargement du Modelfile
    # ------------------------------------------------------------------

    def _load_modelfile_system(self) -> str:
        """Lit le bloc SYSTEM du Modelfile et le retourne comme chaîne."""
        try:
            modelfile_path = Path(__file__).parent.parent / "Modelfile"
            content = modelfile_path.read_text(encoding="utf-8")
            m = _re.search(r'SYSTEM\s+"""(.*?)"""', content, _re.DOTALL)
            if m:
                return m.group(1).strip()
        except Exception as exc:
            self.logger.warning("Impossible de lire le Modelfile : %s", exc)
        return ""

    def _init_v7_modules(self):
        """Initialise les modules ajoutés en v7.0.0 (chacun optionnel)."""
        full_config = get_config()

        # Détection de langue
        self.language_detector = None
        if _LANG_DETECT_AVAILABLE:
            try:
                lang_cfg = full_config.get_section("language") or {}
                self.language_detector = LanguageDetector(
                    default_language=lang_cfg.get("default", "fr"),
                )
                self.logger.info("✅ LanguageDetector initialisé")
            except Exception as e:
                self.logger.warning("⚠️ LanguageDetector indisponible: %s", e)

        # Cache web
        self.web_cache = None
        if _WEB_CACHE_AVAILABLE:
            try:
                wc_cfg = full_config.get_section("web_cache") or {}
                self.web_cache = WebCache(
                    cache_dir=wc_cfg.get("directory", "data/web_cache"),
                    ttl_seconds=wc_cfg.get("ttl_seconds", 3600),
                    max_entries=wc_cfg.get("max_entries", 1000),
                )
                self.logger.info("✅ WebCache initialisé")
            except Exception as e:
                self.logger.warning("⚠️ WebCache indisponible: %s", e)

        # Exporteur de conversations
        self.conversation_exporter = None
        if _EXPORTER_AVAILABLE:
            try:
                exp_cfg = full_config.get_section("export") or {}
                self.conversation_exporter = ConversationExporter(
                    output_dir=exp_cfg.get("output_directory", "outputs/exports"),
                )
                self.logger.info("✅ ConversationExporter initialisé")
            except Exception as e:
                self.logger.warning("⚠️ ConversationExporter indisponible: %s", e)

        # Base de connaissances structurée
        self.knowledge_base = None
        if _KB_AVAILABLE:
            try:
                kb_cfg = full_config.get_section("knowledge_base") or {}
                self.knowledge_base = KnowledgeBaseManager(
                    db_path=os.path.join(
                        kb_cfg.get("directory", "data/knowledge_base"),
                        "facts.db",
                    ),
                )
                self.logger.info("✅ KnowledgeBaseManager initialisé")
            except Exception as e:
                self.logger.warning("⚠️ KnowledgeBaseManager indisponible: %s", e)

        # Historique des commandes
        self.command_history = None
        if _CMD_HISTORY_AVAILABLE:
            try:
                ch_cfg = full_config.get_section("command_history") or {}
                self.command_history = CommandHistory(
                    db_path=ch_cfg.get("db_path", "data/command_history.db"),
                    max_entries=ch_cfg.get("max_entries", 5000),
                )
                self.logger.info("✅ CommandHistory initialisé")
            except Exception as e:
                self.logger.warning("⚠️ CommandHistory indisponible: %s", e)

        # Gestionnaire de sessions / workspaces
        self.session_manager = None
        if _SESSION_AVAILABLE:
            try:
                ws_cfg = full_config.get_section("workspaces") or {}
                self.session_manager = SessionManager(
                    workspaces_dir=ws_cfg.get("directory", "data/workspaces"),
                )
                self.logger.info("✅ SessionManager initialisé")
            except Exception as e:
                self.logger.warning("⚠️ SessionManager indisponible: %s", e)

    # ── Détection de langue ─────────────────────────────────────────────

    # Suffixes de prompt par code de langue ISO 639-1
    _LANG_SUFFIXES = {
        "fr": "Réponds toujours en français.",
        "en": "Always respond in English.",
        "es": "Responde siempre en español.",
        "de": "Antworte immer auf Deutsch.",
        "it": "Rispondi sempre in italiano.",
        "pt": "Responda sempre em português.",
        "nl": "Antwoord altijd in het Nederlands.",
        "ru": "Всегда отвечай на русском языке.",
        "zh": "请始终用中文回答。",
        "ja": "常に日本語で回答してください。",
        "ko": "항상 한국어로 답변해 주세요。",
        "ar": "أجب دائمًا باللغة العربية.",
    }

    def _get_lang_instruction(self, text: str) -> str:
        """Retourne l'instruction de langue à injecter dans le system prompt."""
        if self.language_detector is not None:
            try:
                code = self.language_detector.detect(text)
                return self._LANG_SUFFIXES.get(code, self._LANG_SUFFIXES["fr"])
            except Exception:
                pass
        return self._LANG_SUFFIXES["fr"]

    def _setup_mcp_tools(self):
        """
        Enregistre toutes les capacités existantes du projet comme outils
        standardisés MCP, accessibles par Ollama via tool calling.

        Cette méthode centralise le routing : au lieu de keyword-matching
        dans _analyze_query_type(), Ollama lui-même décide quel outil utiliser.
        """
        # ----------------------------------------------------------------
        # 1. Recherche Web
        # ----------------------------------------------------------------
        try:
            search_engine = EnhancedInternetSearchEngine(
                llm=(
                    self.local_ai.local_llm
                    if hasattr(self.local_ai, "local_llm")
                    else None
                )
            )
            # Exposer l'instance pour que tool_executor puisse y brancher
            # le callback de streaming de la GUI.
            self._web_search_engine = search_engine

            def web_search(query: str) -> str:
                """Effectue une recherche sur internet et retourne un résumé des résultats."""
                try:
                    return search_engine.search_and_summarize(query)
                except Exception as exc:
                    return f"Recherche impossible : {exc}"

            self.mcp_manager.register_local_tool(
                name="web_search",
                description=(
                    "Effectue une recherche sur internet pour obtenir des informations "
                    "récentes, factuelles ou d'actualité. À utiliser pour : faits, "
                    "données chiffrées, prix, actualités, informations techniques récentes."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "La requête de recherche web",
                        },
                    },
                    "required": ["query"],
                },
                callable_fn=web_search,
            )
        except Exception as exc:
            self.logger.warning("Outil web_search non disponible : %s", exc)

        # ----------------------------------------------------------------
        # 2. Recherche en mémoire vectorielle
        # ----------------------------------------------------------------
        try:
            vector_mem = VectorMemory()

            def search_memory(query: str, n_results: int = 5) -> str:
                """Recherche sémantique dans la mémoire vectorielle locale."""
                try:
                    results = vector_mem.search_similar(query, n_results=n_results)
                    if not results:
                        return "Aucun résultat dans la mémoire vectorielle."
                    parts = []
                    for i, r in enumerate(results, 1):
                        content = r.get("content", r.get("text", str(r)))
                        parts.append(f"[{i}] {content[:500]}")
                    return "\n\n".join(parts)
                except Exception as exc:
                    return f"Erreur mémoire : {exc}"

            self.mcp_manager.register_local_tool(
                name="search_memory",
                description=(
                    "Recherche sémantique dans la mémoire locale de l'IA (documents "
                    "précédemment indexés, historique de conversation, connaissances). "
                    "N'UTILISE PAS cet outil pour retrouver des fichiers fraîchement créés ou d'actions triviales. "
                    "À utiliser UNIQUEMENT pour retrouver des informations passées lointaines si l'utilisateur en parle."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Requête de recherche sémantique",
                        },
                        "n_results": {
                            "type": "integer",
                            "description": "Nombre de résultats à retourner",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
                callable_fn=search_memory,
            )
        except Exception as exc:
            self.logger.warning("Outil search_memory non disponible : %s", exc)

        # ----------------------------------------------------------------
        # 3. Lecture et analyse de fichiers locaux
        # ----------------------------------------------------------------
        def read_local_file(path: str) -> str:
            """Lit le contenu d'un fichier local (PDF, DOCX, code, texte)."""
            # Vérifier d'abord la mémoire interne (documents déjà chargés en session)
            file_name = Path(path).name
            try:
                stored = self.local_ai.conversation_memory.stored_documents
                if stored:
                    # Correspondance exacte par nom de fichier
                    if file_name in stored:
                        content = stored[file_name].get("content", "")
                        if content:
                            return content[:8000]
                    # Correspondance insensible à la casse
                    file_name_lower = file_name.lower()
                    for stored_name, stored_data in stored.items():
                        if stored_name.lower() == file_name_lower:
                            content = stored_data.get("content", "")
                            if content:
                                return content[:8000]
                    # Dernier recours : un seul document en mémoire → le retourner
                    if len(stored) == 1:
                        only_doc = next(iter(stored.values()))
                        content = only_doc.get("content", "")
                        if content:
                            return content[:8000]
                    # Plusieurs documents sans correspondance → signaler à l'IA
                    doc_list = ", ".join(stored.keys())
                    return (
                        f"Impossible d'identifier '{file_name}' parmi les documents chargés. "
                        f"Documents disponibles : {doc_list}. "
                        f"Le contenu des documents est déjà présent dans le contexte de la conversation."
                    )
            except Exception:
                pass

            fpath = Path(path)
            if not fpath.exists():
                return f"Fichier introuvable : {path}"
            ext = fpath.suffix.lower()
            try:
                if ext == ".pdf":
                    text = self.pdf_processor.extract_text(str(fpath))
                    return text[:8000]
                elif ext in (".docx", ".doc"):
                    result = self.docx_processor.extract_text(str(fpath))
                    return result.get("content", "")[:8000]
                else:
                    return fpath.read_text(encoding="utf-8", errors="replace")[:8000]
            except Exception as exc:
                return f"Erreur lecture fichier : {exc}"

        self.mcp_manager.register_local_tool(
            name="read_local_file",
            description=(
                "Lit et extrait le contenu d'un fichier local : PDF, DOCX, Python, "
                "JavaScript, texte brut, JSON, etc. Retourne le texte du fichier. "
                "A un accès total au PC via chemins absolus (ex: 'C:\\Users\\...')."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Chemin absolu (C:\\...) ou relatif vers le fichier",
                    }
                },
                "required": ["path"],
            },
            callable_fn=read_local_file,
        )

        # ----------------------------------------------------------------
        # 4. Liste de fichiers dans un répertoire
        # ----------------------------------------------------------------
        def list_directory(path: str = ".", pattern: str = "*") -> str:
            """Liste les fichiers d'un répertoire."""
            try:
                full_pattern = os.path.join(path, "**", pattern)
                files = glob.glob(full_pattern, recursive=True)
                if not files:
                    return f"Aucun fichier trouvé dans {path} (pattern: {pattern})"
                return "\n".join(sorted(files)[:100])
            except Exception as exc:
                return f"Erreur listage répertoire : {exc}"

        self.mcp_manager.register_local_tool(
            name="list_directory",
            description=(
                "Liste les fichiers présents dans un répertoire local (accès à TOUT le PC, ex: 'C:\\Users\\...'). "
                "Utile pour explorer l'ordinateur ou la structure d'un projet."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Répertoire à explorer (ex: 'C:\\Users\\Nom', ou '.' pour le projet)",
                        "default": ".",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Filtre glob (ex: '*.py', '*.md')",
                        "default": "*",
                    },
                },
            },
            callable_fn=list_directory,
        )

        # ----------------------------------------------------------------
        # 4.1. Recherche avancée de fichiers
        # ----------------------------------------------------------------
        def search_local_files(query: str, path: str = None) -> str:
            """Recherche locale de fichiers par nom complet ou partiel."""
            try:
                base_path = path if path else os.path.expanduser("~")
                results = []
                query_lower = query.lower()

                for root, dirs, files in os.walk(base_path):
                    # Ignorer certains dossiers trop lourds ou inaccessibles par défaut
                    dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'venv', 'env', '__pycache__', 'AppData', 'Local', 'Roaming']]
                    for file in files:
                        if query_lower in file.lower():
                            results.append(os.path.join(root, file))
                            if len(results) >= 50:
                                break
                    if len(results) >= 50:
                        break

                if not results:
                    return f"Aucun fichier contenant '{query}' trouvé dans {base_path}."
                return f"Fichiers trouvés ({len(results)} max) :\n" + "\n".join(results)
            except Exception as exc:
                return f"Erreur de recherche : {exc}"

        self.mcp_manager.register_local_tool(
            name="search_local_files",
            description=(
                "Recherche un fichier par son nom (partiel ou complet) sur le PC. "
                "Très utile quand l'utilisateur demande 'cherche la présentation...' ou un fichier précis."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Texte à chercher dans le nom du fichier (ex: 'présentation VRAI', 'rapport')",
                    },
                    "path": {
                        "type": "string",
                        "description": "Dossier racine pour la recherche (défaut: dossier utilisateur ~)",
                        "default": "",
                    },
                },
                "required": ["query"],
            },
            callable_fn=search_local_files,
        )

        # ----------------------------------------------------------------
        # 4.2. Écriture / Modification de fichiers
        # ----------------------------------------------------------------
        def write_local_file(path: str, content: str) -> str:
            """Crée ou écrase un fichier local."""
            try:
                # Gérer les chemins absolus multiplateformes et les ~, éviter les dossiers relatifs au projet
                fpath = Path(path).expanduser().resolve()
                fpath.parent.mkdir(parents=True, exist_ok=True)
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"Succès : fichier écrit/modifié avec succès à l'emplacement {fpath.absolute()}"
            except Exception as exc:
                return f"Erreur écriture fichier : {exc}"

        self.mcp_manager.register_local_tool(
            name="write_local_file",
            description=(
                "Crée ou remplace le contenu d'un fichier local sur le PC. "
                "Permet d'agir (agentique) en sauvegardant du code, un résumé, ou des modifications."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Chemin absolu ou relatif où écrire le fichier (ex: 'C:\\Users\\...\\fichier.txt')",
                    },
                    "content": {
                        "type": "string",
                        "description": "Le contenu texte complet à écrire dans le fichier",
                    },
                },
                "required": ["path", "content"],
            },
            callable_fn=write_local_file,
        )

        # ----------------------------------------------------------------
        # 4.3. Déplacement / Renommage de fichiers
        # ----------------------------------------------------------------
        def move_local_file(**kwargs) -> str:
            """Déplace ou renomme un fichier ou un dossier."""
            source = kwargs.get("source") or kwargs.get("path")
            destination = kwargs.get("destination") or kwargs.get("path_dest")
            if not source or not destination:
                return "Erreur : paramètres manquants. Vous devez spécifier 'source' et 'destination'."

            try:
                fpath = Path(source)
                if not fpath.exists():
                    return f"Fichier source introuvable : {source}"
                Path(destination).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(source, destination)
                return f"Succès : déplacé/renommé de {source} vers {destination}"
            except Exception as exc:
                return f"Erreur déplacement/renommage : {exc}"

        self.mcp_manager.register_local_tool(
            name="move_local_file",
            description=(
                "Déplace ou renomme un fichier ou un dossier sur le PC. "
                "Permet d'organiser les fichiers de l'utilisateur.\n"
                "IMPORTANT: Fais très attention à bien fournir les chemins ABSOLUS complets et exacts, "
                "notamment si le fichier doit être déplacé dans un dossier spécifique que tu viens de créer."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Chemin actuel du fichier/dossier",
                    },
                    "destination": {
                        "type": "string",
                        "description": "Nouveau chemin ou nouveau nom",
                    },
                    "path": {
                        "type": "string",
                        "description": "Alias pour le chemin actuel (source)",
                    },
                    "path_dest": {
                        "type": "string",
                        "description": "Alias pour le nouveau chemin (destination)",
                    },
                },
                "required": [],
            },
            callable_fn=move_local_file,
        )

        # ----------------------------------------------------------------
        # 4.4. Suppression de fichier/répertoire
        # ----------------------------------------------------------------
        def delete_local_file(path: str) -> str:
            """Supprime un fichier ou un répertoire vide."""
            try:
                fpath = Path(path)
                if not fpath.exists():
                    return f"Erreur : Introuvable à {path}"
                if fpath.is_file():
                    fpath.unlink()
                else:
                    shutil.rmtree(path)
                return f"Succès : élément supprimé {path}"
            except Exception as exc:
                return f"Erreur suppression : {exc}"

        self.mcp_manager.register_local_tool(
            name="delete_local_file",
            description="Supprime de façon permanente un fichier ou un dossier sur le PC.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Chemin du fichier ou dossier à supprimer",
                    }
                },
                "required": ["path"],
            },
            callable_fn=delete_local_file,
        )

        # ----------------------------------------------------------------
        # 4.5. Création de répertoire
        # ----------------------------------------------------------------
        def create_directory(path: str) -> str:
            """Crée un tout nouveau répertoire."""
            try:
                fpath = Path(path)
                fpath.mkdir(parents=True, exist_ok=True)
                return f"Succès : répertoire créé à {fpath.absolute()}"
            except Exception as exc:
                return f"Erreur création répertoire : {exc}"

        self.mcp_manager.register_local_tool(
            name="create_directory",
            description="Crée un nouveau dossier/répertoire sur le PC.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Chemin du nouveau dossier à créer",
                    },
                },
                "required": ["path"],
            },
            callable_fn=create_directory,
        )

        # ----------------------------------------------------------------
        # 5. Génération de code avec recherche web
        # ----------------------------------------------------------------
        async def generate_code(description: str, language: str = "python") -> str:
            """Génère du code en cherchant des exemples récents sur le web."""
            try:
                result = await self.code_generator.generate_code_from_web(
                    description, language
                )
                if result.get("success"):
                    code = result.get("code", "")
                    explanation = result.get("explanation", "")
                    return f"```{language}\n{code}\n```\n\n{explanation}"
                return (
                    f"Génération impossible : {result.get('error', 'erreur inconnue')}"
                )
            except Exception as exc:
                return f"Erreur génération code : {exc}"

        self.mcp_manager.register_local_tool(
            name="generate_code",
            description=(
                "Génère du code source dans le langage demandé en s'appuyant sur "
                "des exemples récents trouvés sur GitHub, Stack Overflow, etc. "
                "À utiliser pour toute demande de création, génération ou écriture de code."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Description précise du code à générer",
                    },
                    "language": {
                        "type": "string",
                        "description": "Langage de programmation (python, javascript, java, etc.)",
                        "default": "python",
                    },
                },
                "required": ["description"],
            },
            callable_fn=generate_code,
        )

        # ----------------------------------------------------------------
        # 6. Calcul et évaluation d'expressions mathématiques
        # ----------------------------------------------------------------
        def calculate(expression: str) -> str:
            """Évalue une expression mathématique de façon sécurisée."""
            try:
                result = local_math(expression)
                return str(result)
            except Exception as exc:
                return f"Erreur calcul : {exc}"

        self.mcp_manager.register_local_tool(
            name="calculate",
            description=(
                "Évalue une expression mathématique précisément. "
                "Supporte: +, -, *, /, **, %, //, et fonctions math.sqrt, math.sin, etc."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Expression mathématique à évaluer",
                    }
                },
                "required": ["expression"],
            },
            callable_fn=calculate,
        )

        # ----------------------------------------------------------------
        # Serveurs MCP externes (depuis config.yaml)
        # ----------------------------------------------------------------
        try:
            cfg = get_config()
            mcp_config = cfg.get_section("mcp") or {}
            servers = mcp_config.get("servers", {})
            for server_name, server_conf in servers.items():
                if server_conf.get("enabled", False):
                    self.mcp_manager.register_mcp_server_from_dict(
                        server_name, server_conf
                    )
            if servers:
                # Connexion asynchrone en arrière-plan
                def _connect():
                    self.mcp_manager.connect_external_servers_sync()

                t = threading.Thread(target=_connect, daemon=True, name="mcp-connect")
                t.start()
        except Exception as exc:
            self.logger.warning("Configuration serveurs MCP ignorée : %s", exc)

        total_tools = len(self.mcp_manager.get_ollama_tools())
        self.logger.info(
            "✅ MCPManager initialisé — %d outil(s) disponible(s)", total_tools
        )

    def process_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Interface synchrone avec validation des entrées

        Args:
            text: Texte de la requête utilisateur
            context: Contexte additionnel (optionnel)

        Returns:
            Réponse générée

        Raises:
            ValueError: Si l'entrée ne passe pas la validation
        """
        try:
            # Validation de l'entrée avec Pydantic
            validated_input = validate_input(
                {"query": text, "context": context}, "query"
            )

            # Utiliser les données validées et nettoyées
            text = validated_input.query
            context = validated_input.context

            self.logger.info("[VALIDÉ] process_text: %s", repr(text[:100]))

            # Analyser rapidement le type de requête
            text_lower = text.lower()

            # 1. Questions factuelles → Recherche web directe
            if any(
                word in text_lower
                for word in [
                    "combien",
                    "population",
                    "habitants",
                    "nombre",
                    "statistiques",
                ]
            ):
                return "🔍 **Recherche web en cours...**\n\nJe recherche cette information sur internet pour vous donner une réponse à jour.\n\n*(Note: Le système de recherche web est en cours d'implémentation)*"

            # 2. Demandes de code → Nouveau générateur web
            code_keywords = [
                "génère",
                "crée",
                "écris",
                "développe",
                "fonction",
                "script",
                "code",
            ]
            if any(keyword in text_lower for keyword in code_keywords):
                try:
                    # Détecter le langage
                    language = "python"  # Défaut
                    if "javascript" in text_lower or "js" in text_lower:
                        language = "javascript"
                    elif "java" in text_lower and "javascript" not in text_lower:
                        language = "java"

                    # Lancer la recherche web via AdvancedCodeGenerator
                    async def run_web_search():
                        return await self.code_generator.generate_code_from_web(
                            text, language
                        )

                    # Exécuter la recherche de façon robuste
                    result = self._run_async(run_web_search())

                    if result.get("success"):
                        code = result.get("code", "")
                        source = result.get("source", "Web")
                        explanation = result.get("explanation", "")

                        return f"🌐 **Code trouvé sur {source}:**\n\n```{language}\n{code}\n```\n\n💬 **Explication:** {explanation}"
                    else:
                        # Fallback minimal seulement si recherche web échoue
                        if "tri" in text_lower or "sort" in text_lower:
                            return f"🛠️ **Code généré localement (recherche web échouée):**\n\n```{language}\ndef sort_list(items):\n    \"\"\"Trie une liste par ordre alphabétique\"\"\"\n    return sorted(items)\n\n# Exemple\nwords = ['pomme', 'banane', 'cerise']\nsorted_words = sort_list(words)\nprint(sorted_words)  # ['banane', 'cerise', 'pomme']\n```"
                        else:
                            return f'❌ **Impossible de trouver du code pour:** "{text}"\n\n🔍 **Recherches effectuées:**\n• GitHub, Stack Overflow, GeeksforGeeks\n\n💡 **Suggestions:**\n• Soyez plus spécifique (ex: "fonction Python qui trie une liste")\n• Précisez le langage souhaité'

                except ImportError:
                    return "❌ **Erreur:** Module de recherche web non disponible.\n\nVeuillez vérifier que tous les modules sont installés correctement."
                except (ConnectionError, TimeoutError) as e:
                    return f"❌ **Erreur lors de la recherche web:** {str(e)}\n\nLe système de recherche web rencontre des difficultés."

            # 3. Questions conversationnelles
            if any(
                phrase in text_lower
                for phrase in [
                    "comment ça va",
                    "comment vas tu",
                    "ça va",
                    "salut",
                    "bonjour",
                ]
            ):
                # Éviter le bug "Très bien, merci de demander"
                if "comment ça va" in text_lower and not any(
                    tech in text_lower for tech in ["python", "code", "fonction"]
                ):
                    return "Salut ! Je vais bien, merci ! 😊 Je suis votre assistant IA et je suis prêt à vous aider. Que puis-je faire pour vous ?"
                else:
                    return "Bonjour ! Comment puis-je vous aider aujourd'hui ? Je peux générer du code, répondre à vos questions techniques, ou rechercher des informations sur internet."

            # 4. Questions sur l'IA
            if any(
                phrase in text_lower
                for phrase in ["qui es-tu", "que fais-tu", "tes capacités"]
            ):
                return """Je suis votre assistant IA personnel ! 🤖

🌐 **Mes capacités principales :**
• **Génération de code** (Python, JavaScript, etc.) avec recherche web
• **Recherche d'informations** sur internet en temps réel
• **Analyse de documents** et de fichiers
• **Assistance technique** et programmation

💡 **Nouveautés :**
• Je cherche maintenant du code sur GitHub, Stack Overflow, etc.
• Plus de templates pré-codés - uniquement du vrai code trouvé sur le web !

Que voulez-vous que je fasse pour vous ?"""

            # 5. Fallback général
            return "Je vois ! Et comment puis-je vous aider avec ça ?\n\n💡 **Je peux :**\n• Générer du code (avec recherche web)\n• Rechercher des informations sur internet\n• Répondre à vos questions techniques\n\nQue souhaitez-vous faire ?"

        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error("Erreur dans le nouveau process_text: %s", e)
            return f"❌ **Erreur système:** {str(e)}\n\nLe nouveau système de recherche web rencontre des difficultés. Veuillez réessayer."

    def _merge_responses(self, response_custom, response_ml):
        """
        Donne la priorité à la FAQ ML : si une réponse MLFAQ existe, elle est utilisée, sinon on utilise la réponse custom.
        """
        if response_ml is not None and str(response_ml).strip():
            return str(response_ml)
        return response_custom

    def _get_help_text(self) -> str:
        """Retourne le texte d'aide"""
        return """🤖 Aide - My AI Personal Assistant

📝 **Génération de code :**
• "génère une fonction pour calculer la factorielle"
• "crée une classe Personne avec nom et âge"
• "génère du code pour lire un fichier CSV"

📊 **Traitement de documents :**
• Utilisez les boutons pour traiter des PDF/DOCX
• Glissez-déposez vos fichiers

💻 **Analyse de code :**
• Utilisez le bouton "Process Code" pour analyser vos fichiers

❓ **Questions générales :**
• Posez vos questions en langage naturel
• Je peux vous aider avec la programmation Python

💡 **Conseils :**
• Soyez spécifique dans vos demandes
• N'hésitez pas à demander des exemples
• Utilisez "aide" pour revoir cette aide"""

    def _generate_fallback_response(self, text: str) -> str:
        """
        Génère une réponse de fallback en cas d'erreur du modèle principal

        Args:
            text: Texte de l'utilisateur

        Returns:
            Réponse de fallback naturelle
        """
        text_lower = text.lower()

        # Salutations
        if any(
            word in text_lower
            for word in ["salut", "bonjour", "hello", "hi", "bonsoir"]
        ):
            return "Salut ! Comment ça va ? En quoi puis-je t'aider ?"

        # Questions d'aide
        if "help" in text_lower or "aide" in text_lower:
            return "Je peux t'aider avec la génération de code Python, l'analyse de documents, et répondre à tes questions techniques. Que veux-tu faire ?"

        # Demandes de code
        elif (
            "génér" in text_lower
            or "créer" in text_lower
            or "fonction" in text_lower
            or "classe" in text_lower
        ):
            if "fonction" in text_lower:
                return self.code_generator.generate_simple_function(text)
            elif "classe" in text_lower:
                return self.code_generator.generate_simple_class(text)
            else:
                return "Je peux générer du code pour toi ! Tu veux une fonction ou une classe ? Dis-moi ce que tu veux créer."

        # Questions sur l'IA
        elif any(
            phrase in text_lower
            for phrase in ["qui es-tu", "que fais-tu", "qu'est-ce que tu fais"]
        ):
            return "Je suis ton assistant IA local. Je peux coder, analyser des documents et répondre à tes questions. Qu'est-ce qui t'intéresse ?"

        # Réponse générale naturelle
        else:
            return "Je vois ! Et en quoi puis-je t'aider avec ça ? Tu veux que je génère du code, que je t'explique quelque chose, ou autre chose ?"

    async def process_message(self, message: str) -> str:
        """
        Traite un message de manière asynchrone

        Args:
            message: Message de l'utilisateur

        Returns:
            Réponse de l'IA
        """
        return self.process_text(message)

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        Récupère l'historique de conversation

        Returns:
            Liste des messages
        """
        return self.conversation_manager.get_history()

    def clear_conversation(self):
        """
        Clear the conversation history and memory
        """
        self.conversation_manager.clear()
        self.conversation_memory.clear()

        # Réinitialiser aussi le session_context
        self.session_context = {
            "documents_processed": [],
            "code_files_processed": [],
            "last_document_type": None,
            "current_document": None,
        }

        self.logger.info("Conversation cleared")

    def initialize_llm(self) -> bool:
        """Initialise les modèles LLM - Mode entreprise local uniquement"""
        try:
            # En mode entreprise, nous utilisons uniquement le modèle local
            return hasattr(self, "local_ai") and self.local_ai is not None
        except AttributeError as e:
            self.logger.error("Erreur initialisation LLM: %s", e)
            return False

    async def process_query(
        self, query: str, context: Optional[Dict] = None, is_interrupted_callback=None
    ) -> Dict[str, Any]:
        """
        Traite une requête utilisateur

        Args:
            query: Question/demande de l'utilisateur
            context: Contexte additionnel (fichiers, historique, etc.)
            is_interrupted_callback: Fonction pour vérifier si l'opération est interrompue

        Returns:
            Réponse structurée de l'IA
        """
        try:
            self.logger.info("Traitement de la requête: %s...", query[:100])

            # Détection automatique de la langue de l'utilisateur
            self._current_lang_instruction = self._get_lang_instruction(query)

            # 0. Vérifier la génération de fichier en priorité absolue pour court-circuiter FAQ et MCP
            query_lower = query.lower()
            file_keywords = [
                "génère moi un fichier",
                "crée moi un fichier",
                "génère un fichier",
                "crée un fichier",
            ]
            if any(keyword in query_lower for keyword in file_keywords):
                print(f"[AIEngine] Ordre de génération de fichier détecté, court-circuit MCP pour: '{query}'")
                response = await self._handle_code_generation(query, is_interrupted_callback)
                self.conversation_manager.add_exchange(query, response)
                return response

            print(f"[AIEngine] Appel FAQ pour: '{query}' (async)")
            # 1. Tenter la FAQ ML d'abord
            response_ml = None
            if hasattr(self, "ml_ai") and self.ml_ai is not None:
                try:
                    response_ml = self.ml_ai.predict(query)
                    self.logger.info("ML model response: %s...", str(response_ml)[:50])
                except (ValueError, AttributeError, TypeError) as e:
                    self.logger.warning("Erreur modèle ML: %s", e)
            if response_ml is not None and str(response_ml).strip():
                # On sauvegarde l'échange
                try:
                    self.conversation_manager.add_exchange(
                        query, {"message": response_ml}
                    )
                except (OSError, AttributeError, TypeError):
                    self.logger.warning(
                        "Impossible de sauvegarder la conversation (FAQ async)"
                    )
                return {"type": "faq", "message": response_ml, "success": True}

            # 2. Routage MCP tool-calling (prioritaire sur le keyword-routing)
            if (
                self.mcp_manager.has_tools()
                and hasattr(self.local_ai, "local_llm")
                and self.local_ai.local_llm is not None
                and self.local_ai.local_llm.is_ollama_available
            ):
                response = await self._handle_with_mcp_tools(
                    query, context, is_interrupted_callback
                )
                if response.get("success"):
                    self.conversation_manager.add_exchange(query, response)
                    return response
                # Fallback si MCP échoue (pas de réponse finale générée)

            # 3. Fallback : routage classique par mots-clés
            query_type = self._analyze_query_type(query)
            full_context = self._prepare_context(query, context)
            if query_type == "web_search":
                response = await self._handle_web_search(query)
            elif query_type == "conversation":
                response = await self._handle_conversation(query, full_context)
            elif query_type == "file_processing":
                response = await self._handle_file_processing(query, full_context)
            elif query_type == "code_generation":
                response = await self._handle_code_generation(
                    query, is_interrupted_callback
                )
            elif query_type == "document_generation":
                response = await self._handle_document_generation(query, full_context)
            else:
                response = await self._handle_general_query(query, full_context)
            # Sauvegarde dans l'historique
            self.conversation_manager.add_exchange(query, response)
            return response
        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error("Erreur lors du traitement: %s", e)
            return {
                "type": "error",
                "message": f"Désolé, une erreur s'est produite: {str(e)}",
                "success": False,
            }

    def _analyze_query_type(self, query: str) -> str:
        """
        Analyse le type de requête

        Args:
            query: Requête utilisateur

        Returns:
            Type de requête identifié
        """
        query_lower = query.lower()

        # PRIORITÉ 1 : Vérifier d'abord les questions d'identité/capacités (AVANT documents)
        identity_keywords = [
            "qui es-tu",
            "qui es tu",
            "qui êtes vous",
            "comment tu t'appelles",
            "ton nom",
            "tu es qui",
            "tu es quoi",
            "présente toi",
            "presente toi",
            "présentez vous",
            "présentez-vous",
            "vous êtes qui",
            "vous êtes quoi",
            "ton identité",
            "votre identité",
            "c'est quoi ton nom",
            "c'est quoi votre nom",
        ]
        capability_keywords = [
            "que peux tu",
            "que sais tu",
            "tes capacités",
            "tu peux faire",
            "que fais-tu",
            "comment vas tu",
            "comment ça va",
        ]

        if any(
            keyword in query_lower
            for keyword in identity_keywords + capability_keywords
        ):
            return "conversation"  # Questions sur l'IA elle-même

        # PRIORITÉ 2 : Vérifier si c'est un texte incompréhensible/aléatoire
        if len(query_lower) > 20 and not any(c.isspace() for c in query_lower[:20]):
            # Si plus de 20 caractères sans espaces = probablement du charabia
            return "conversation"

        # PRIORITÉ 2.5 : Questions factuelles ou de recherche web
        web_keywords = [
            "combien",
            "population",
            "habitants",
            "nombre",
            "statistiques",
            "chiffre",
            "prix",
            "coût",
            "taille",
            "poids",
            "année",
            "date",
        ]
        if any(keyword in query_lower for keyword in web_keywords):
            return "web_search"

        # PRIORITÉ 3 : Vérifier si on a des documents et si la question les concerne SPÉCIFIQUEMENT
        if hasattr(self.local_ai, "conversation_memory"):
            stored_docs = self.local_ai.conversation_memory.get_document_content()
            if stored_docs:
                # Mots-clés SPÉCIFIQUES pour questions sur les documents
                doc_question_keywords = [
                    "résume",
                    "explique",
                    "analyse",
                    "qu'est-ce que",
                    "que dit",
                    "contenu",
                    "parle",
                    "traite",
                    "sujet",
                    "doc",
                    "document",
                    "pdf",
                    "docx",
                    "fichier",
                    "code",
                ]
                if any(keyword in query_lower for keyword in doc_question_keywords):
                    return "file_processing"

        # PRIORITÉ 4 : Mots-clés pour la génération de code (NOUVEAU code, pas analyse)
        # Distinguer entre questions théoriques et demandes de génération
        question_words = [
            "comment",
            "qu'est-ce que",
            "c'est quoi",
            "que signifie",
            "explique",
            "expliquer",
        ]
        is_theoretical_question = any(qword in query_lower for qword in question_words)

        code_generation_keywords = [
            "génère",
            "crée",
            "écris",
            "développe",
            "programme",
            "script",
            "fonction",
            "classe",
        ]

        if any(keyword in query_lower for keyword in code_generation_keywords):
            # Si c'est une question théorique (ex: "comment créer une liste ?"), laisser le CustomAIModel s'en occuper
            if is_theoretical_question:
                return "general"  # Laisser le CustomAIModel traiter
            else:
                return "code_generation"  # Vraie demande de génération

        # PRIORITÉ 5 : Mots-clés pour la génération de documents
        doc_keywords = ["créer", "générer", "rapport", "rédiger", "documenter"]
        if any(keyword in query_lower for keyword in doc_keywords):
            return "document_generation"

        return "conversation"

    def _prepare_context(self, query: str, context: Optional[Dict]) -> Dict[str, Any]:
        """
        Prépare le contexte complet pour la requête
        """
        full_context = {
            "query": query,
            "conversation_history": self.conversation_manager.get_recent_history(),
            "timestamp": self.file_manager.get_timestamp(),
            "user_context": context or {},
        }

        # Ajouter les documents stockés dans la mémoire
        if hasattr(self.local_ai, "conversation_memory"):
            stored_docs = self.local_ai.conversation_memory.stored_documents
            if stored_docs:
                full_context["stored_documents"] = stored_docs
                full_context["document_order"] = (
                    self.local_ai.conversation_memory.document_order
                )
                self.logger.info(
                    "Contexte enrichi avec %d documents stockés", len(stored_docs)
                )

        return full_context

    def _inject_knowledge_base_context(self, query: str, system_prompt: str) -> str:
        """
        Injecte les faits pertinents de la base de connaissances dans le
        system prompt pour favoriser des réponses factuelles.

        Injecte à la fois les faits pertinents à la requête courante ET les
        faits les plus récents tous catégories confondues (plafonné), afin
        que les questions de rappel courtes ("tu es sûr ?", "et alors ?")
        conservent accès aux informations précédemment fournies.
        """
        kb = getattr(self, "knowledge_base", None)
        if kb is None:
            return system_prompt

        collected: Dict[Any, Dict[str, Any]] = {}

        def _add_fact(fact: Dict[str, Any]) -> None:
            fid = fact.get("id")
            key = fid if fid is not None else f"{fact.get('key', '')}|{fact.get('value', '')}"
            if key not in collected:
                collected[key] = fact

        # 1. Faits pertinents à la requête courante
        try:
            for fact in kb.search_facts(query, limit=6) or []:
                _add_fact(fact)
        except Exception as exc:
            self.logger.warning("Recherche base de connaissances indisponible: %s", exc)

        # 2. Toujours inclure les faits les plus récents (contexte persistant)
        try:
            for fact in (kb.get_all_facts() or [])[:6]:
                _add_fact(fact)
        except Exception as exc:
            self.logger.warning("Lecture base de connaissances indisponible: %s", exc)

        if not collected:
            return system_prompt

        lines = ["[Base de connaissances]"]
        for fact in list(collected.values())[:8]:
            confidence = fact.get("confidence", 1.0) or 1.0
            try:
                confidence_pct = int(float(confidence) * 100)
            except (TypeError, ValueError):
                confidence_pct = 100
            category = fact.get("category", "general")
            key = fact.get("key", "")
            value = fact.get("value", "")
            lines.append(f"- [{category}] {key}: {value} (confiance: {confidence_pct}%)")

        return (
            system_prompt
            + "\n\n"
            + "FAITS UTILISATEUR (mémoire persistante — traite-les comme des choses que tu sais déjà) :\n"
            + "\n".join(lines)
            + "\n\n"
            + "Règles STRICTES pour l'utilisation de ces faits :\n"
            "- Réponds directement avec le fait, de manière brève et naturelle, comme si tu t'en souvenais.\n"
            "- N'écris JAMAIS de méta-commentaire du type 'je consulte mes connaissances', "
            "'selon la base de connaissances', 'd'après les informations fournies', "
            "'dans le contexte documentaire', ni aucune mention de niveau de confiance / pourcentage.\n"
            "- N'affirme jamais que tu n'as pas de mémoire si l'information demandée figure ci-dessus.\n"
            "- Si l'utilisateur pose une question de relance courte (ex: 'tu es sûr ?', 'vraiment ?', "
            "'c'est vrai ?', 'confirme', 'really?'), elle porte TOUJOURS sur ta réponse précédente dans "
            "l'historique de conversation — PAS sur ton identité. Tu dois alors confirmer l'information "
            "précédente en t'appuyant sur les faits ci-dessus, et NON te présenter à nouveau.\n"
            "- Exemple 1 : 'qui est mon manager ?' → 'Ton manager est...' (rien de plus)\n"
            "- Exemple 2 : après avoir dit 'Ton manager est...', si on te demande "
            "'tu es sûr ?' → 'Oui, c'est bien toi qui me l'as indiqué.'"
        )

    def _select_relevant_docs(self, query: str, stored_documents: dict) -> dict:
        """
        Retourne uniquement les documents pertinents pour la requête.

        Si l'utilisateur mentionne le nom d'un fichier spécifique dans sa requête,
        seul ce document est retourné. Sinon, tous les documents sont retournés.
        """
        if not stored_documents or len(stored_documents) == 1:
            return stored_documents

        query_lower = query.lower()
        matched = {}

        for doc_name, doc_data in stored_documents.items():
            # Correspondance sur le nom complet (ex: "rapport.xlsx")
            if doc_name.lower() in query_lower:
                matched[doc_name] = doc_data
                continue
            # Correspondance sur le nom sans extension (ex: "rapport")
            stem = Path(doc_name).stem.lower()
            if stem and len(stem) > 2 and stem in query_lower:
                matched[doc_name] = doc_data

        # Si aucune correspondance → retourner tous les documents (pas de filtre)
        return matched if matched else stored_documents

    async def _handle_with_mcp_tools(
        self,
        query: str,
        context: Optional[Dict],
        is_interrupted_callback=None,
    ) -> Dict[str, Any]:
        """
        Traite une requête via la boucle agentique Ollama + outils MCP.

        Le LLM reçoit la liste complète des outils disponibles et décide
        lui-même lesquels appeler, sans keyword-routing hardcodé.
        """
        try:
            llm = self.local_ai.local_llm
            tools = self.mcp_manager.get_ollama_tools()

            if not tools:
                return {"type": "mcp", "message": "", "success": False}

            # Construire le system prompt qui explique les outils
            system_prompt = (
                "Tu es My AI, un assistant IA local, confidentiel et puissant. "
                "Tu as un accès total à l'ordinateur de l'utilisateur. "
                "Tu as accès à des outils que tu peux appeler automatiquement pour "
                "répondre précisément et agir sur les fichiers (chemins absolus possibles). "
                "Utilise les outils pertinents avant de répondre. "
                f"{getattr(self, '_current_lang_instruction', self._LANG_SUFFIXES['fr'])} "
                "Si tu utilises un outil, synthétise les résultats dans une réponse claire."
            )
            system_prompt = self._inject_knowledge_base_context(query, system_prompt)

            # Ajouter le contexte des documents chargés si disponible
            full_context = self._prepare_context(query, context)
            if full_context.get("stored_documents"):
                relevant_docs = self._select_relevant_docs(query, full_context["stored_documents"])
                doc_sections = []
                for doc_name, doc_data in relevant_docs.items():
                    doc_content = doc_data.get("content", "") if isinstance(doc_data, dict) else str(doc_data)
                    if doc_content:
                        doc_sections.append(f"=== {doc_name} ===\n{doc_content[:8000]}")
                if doc_sections:
                    # Le contenu est déjà injecté dans le prompt : aucun outil nécessaire.
                    # Vider tools pour forcer une réponse directe sans appel d'outil.
                    tools = []
                    system_prompt += (
                        "\n\nContenu des documents chargés par l'utilisateur "
                        "(disponible comme contexte — utilise ces données si la question porte sur ce contenu, sinon réponds normalement depuis tes connaissances) :\n"
                        + "\n\n".join(doc_sections)
                    )

            # Outil d'interruption vérification
            def tool_executor(tool_name: str, arguments: dict) -> str:
                if is_interrupted_callback and is_interrupted_callback():
                    return "[Interrompu par l'utilisateur]"
                return self.mcp_manager.execute_tool_sync(tool_name, arguments)

            result = llm.generate_with_tools(
                prompt=query,
                tools=tools,
                tool_executor=tool_executor,
                system_prompt=system_prompt,
            )

            if result.get("success") and result.get("response"):
                return {
                    "type": "mcp",
                    "message": result["response"],
                    "tool_calls": result.get("tool_calls", []),
                    "success": True,
                }

            return {"type": "mcp", "message": "", "success": False}

        except Exception as exc:
            self.logger.warning("Erreur MCP tool-calling : %s", exc)
            return {"type": "mcp", "message": "", "success": False}

    async def _handle_with_mcp_tools_stream(
        self,
        query: str,
        context: Optional[Dict],
        on_token=None,
        on_tool_call=None,
        is_interrupted_callback=None,
    ) -> Dict[str, Any]:
        """
        Version streaming de _handle_with_mcp_tools.
        Utilisée par la GUI pour l'affichage progressif des réponses.
        """
        try:
            llm = self.local_ai.local_llm
            tools = self.mcp_manager.get_ollama_tools()
            if not tools:
                return {"type": "mcp", "message": "", "success": False}

            system_prompt = (
                "Tu es My AI, un assistant IA local, confidentiel et puissant. "
                "Tu as accès à des outils et à l'ensemble du système de fichiers de ce PC. "
                "Utilise les outils quand c'est pertinent, avec des chemins absolus si besoin. "
                f"{getattr(self, '_current_lang_instruction', self._LANG_SUFFIXES['fr'])}"
            )
            system_prompt = self._inject_knowledge_base_context(query, system_prompt)

            full_context = self._prepare_context(query, context)
            if full_context.get("stored_documents"):
                relevant_docs = self._select_relevant_docs(query, full_context["stored_documents"])
                doc_sections = []
                for doc_name, doc_data in relevant_docs.items():
                    doc_content = doc_data.get("content", "") if isinstance(doc_data, dict) else str(doc_data)
                    if doc_content:
                        doc_sections.append(f"=== {doc_name} ===\n{doc_content[:8000]}")
                if doc_sections:
                    # Le contenu est déjà injecté dans le prompt : aucun outil nécessaire.
                    # Vider tools pour forcer une réponse directe sans appel d'outil.
                    tools = []
                    system_prompt += (
                        "\n\nContenu des documents chargés par l'utilisateur "
                        "(disponible comme contexte — utilise ces données si la question porte sur ce contenu, sinon réponds normalement depuis tes connaissances) :\n"
                        + "\n\n".join(doc_sections)
                    )

            def tool_executor(tool_name: str, arguments: dict) -> str:
                if is_interrupted_callback and is_interrupted_callback():
                    return "[Interrompu]"
                return self.mcp_manager.execute_tool_sync(tool_name, arguments)

            result = llm.generate_with_tools_stream(
                prompt=query,
                tools=tools,
                tool_executor=tool_executor,
                system_prompt=system_prompt,
                on_token=on_token,
                on_tool_call=on_tool_call,
            )

            if result.get("success") and result.get("response"):
                return {
                    "type": "mcp",
                    "message": result["response"],
                    "tool_calls": result.get("tool_calls", []),
                    "success": True,
                }

            return {"type": "mcp", "message": "", "success": False}

        except Exception as exc:
            self.logger.warning("Erreur MCP stream : %s", exc)
            return {"type": "mcp", "message": "", "success": False}

    # ------------------------------------------------------------------
    # Point d'entrée unifié pour la GUI (synchrone, streaming)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Détection d'intention côté Python (contournement du bug tool-calling
    # de qui écrit le JSON en texte au lieu d'utiliser l'API)
    # ------------------------------------------------------------------

    # Mots-clés qui signalent le besoin d'une info en temps réel
    _WEB_SEARCH_SIGNALS = [
        # Prix / cours / marchés
        "prix",
        "cours",
        "coût",
        "combien coûte",
        "tarif",
        "valeur",
        "bitcoin",
        "ethereum",
        "crypto",
        "bourse",
        "action",
        "euro",
        "dollar",
        # Datation / actualité
        "aujourd'hui",
        "aujourd'hui",
        "maintenant",
        "actuellement",
        "en ce moment",
        "cette semaine",
        "ce mois",
        "cette année",
        "récent",
        "dernière",
        "dernières nouvelles",
        "actualité",
        "actu",
        "news",
        # Météo
        "météo",
        "meteo",
        "température",
        "temps qu'il fait",
        "va-t-il pleuvoir",
        # Faits / données
        "population",
        "habitants",
        "combien",
        "statistique",
        # Événements sportifs / culturels
        "score",
        "résultat du match",
        "classement",
        # Lieux / adresses / proximité
        "proche",
        "près de",
        "où se trouve",
        "adresse",
        "restaurant",
        "café",
        "bar",
        "magasin",
        "boutique",
        "horaire",
        "ouvert",
        "fermé",
    ]

    # Signaux indiquant une requête purement conversationnelle
    # → le LLM ne doit pas recevoir la liste des outils dans ces cas
    _CONVERSATIONAL_SIGNALS = [
        # Salutations
        "salut", "bonjour", "bonsoir", "bonne nuit", "coucou", "hello", "hi", "hey",
        # État / courtoisie
        "ça va", "sa va", "ca va", "comment vas", "comment allez", "comment tu",
        "tu vas bien", "vous allez bien",
        # Clôture
        "au revoir", "bye", "à bientôt", "a bientot", "bonne journée", "merci",
        # Identité du modèle — nom / présentation
        "qui es tu", "qui êtes vous", "qui etes vous", "qui est tu",
        "tu t'appelles", "comment tu t'appelles", "ton nom", "quel est ton nom",
        "présente-toi", "présentes toi", "tu es quoi", "c'est quoi my ai",
        "c'est quoi my_ai", "my ai c'est quoi", "my_ai c'est quoi",
        # Rôle / utilité / capacités
        "a quoi tu sert", "à quoi tu sert", "à quoi tu sers", "tu sers a quoi", "tu sers à quoi",
        "a quoi ca sert", "à quoi ça sert", "a quoi sert", "à quoi sert",
        "tu fais quoi", "tu peux faire quoi", "tu peux quoi",
        "quel est ton role", "quel est ton rôle", "c'est quoi ton role",
        "c'est quoi ton rôle", "quel est votre role", "quel est votre rôle",
        "ta fonction", "votre fonction", "tes capacités", "vos capacités",
        "tes fonctionnalités", "tu es capable de", "tu peux m'aider",
        "comment tu peux m'aider", "comment peux-tu m'aider",
        "t'es un", "t'es quoi", "qu'est-ce que tu es",
        "qu'est ce que tu es", "qu'est-ce que tu fais", "qu'est ce que tu fais",
        "décris-toi", "décris toi", "parle moi de toi", "parle-moi de toi",
        "présente toi", "dis moi qui tu es",
    ]

    def _is_conversational(self, query: str) -> bool:
        """Retourne True si la requête est purement conversationnelle.
        Dans ce cas, les outils ne doivent PAS être fournis au LLM.
        Utilise des frontières de mots pour éviter les faux positifs
        (ex: 'hi' dans 'machine', 'hey' dans 'they', etc.)
        Une requête de plus de 12 mots ne peut pas être purement conversationnelle
        (ex: "Merci, maintenant explique le machine learning" → non conversational).
        """
        # strip() supprime les espaces de début/fin, rstrip enlève ponctuation
        # puis un second strip() retire l'espace résiduel quand l'utilisateur
        # écrit « ? » avec une espace avant (ex : "à quoi tu sert ?")
        q = query.lower().strip().rstrip("?!.").strip()
        # Retirer les signes de ponctuation internes avant de compter les mots
        # (ex: "qui es tu ? quels sont tes fonctionnalités" → 7 vrais mots, pas 8)
        q_words = [w for w in q.split() if w not in ("?", "!", ".", ",", ";", ":")]
        # Si la requête contient plus de 12 mots, ce n'est pas purement conversationnel
        if len(q_words) > 12:
            return False
        for sig in self._CONVERSATIONAL_SIGNALS:
            # Frontières de mots pour éviter les faux positifs sur les sous-chaînes
            if _re.search(r'\b' + _re.escape(sig) + r'\b', q):
                return True
        return False

    def is_conversational(self, query: str) -> bool:
        """Alias public de _is_conversational pour accès depuis le GUI."""
        return self._is_conversational(query)

    def _needs_web_search(self, query: str) -> bool:
        """Retourne True si la requête nécessite une info fraîche du web."""
        q = query.lower()
        return any(sig in q for sig in self._WEB_SEARCH_SIGNALS)

    def _optimize_search_query(self, query: str, llm) -> str:
        """Optimise la requête de recherche avec le LLM pour de meilleurs résultats."""
        if not llm or not llm.is_ollama_available:
            return query

        now = _dt.now()
        current_year = now.year
        # Dernière année « complète » d'événements : si on est en début d'année,
        # les compétitions/éditions de l'année courante n'ont souvent pas encore
        # eu lieu, donc « dernier/dernière » pointe vers l'année précédente.
        last_completed_year = current_year - 1 if now.month <= 6 else current_year

        try:
            prompt = (
                "Transforme cette demande en mots-clés de recherche web "
                "(2 à 5 mots-clés en anglais, sans phrase ni verbe).\n"
                "Règles :\n"
                "- Utilise l'ANGLAIS pour de meilleurs résultats\n"
                "- Mots-clés courts et précis\n"
                f"- Date du jour : {now.strftime('%Y-%m-%d')}.\n"
                f"- Pour 'dernière', 'dernier', 'récent', 'latest' : utilise l'année {last_completed_year} "
                f"(dernière édition terminée).\n"
                f"- Pour l'actualité en cours : utilise {current_year}.\n"
                "- Si l'utilisateur mentionne une année explicite, GARDE CETTE ANNÉE telle quelle.\n"
                "- Réponds UNIQUEMENT avec les mots-clés\n\n"
                f"Demande: {query}"
            )
            system_prompt = (
                "Tu génères des mots-clés de recherche web. "
                "Réponds uniquement avec les mots-clés, en anglais, sans phrase."
            )

            optimized = llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                save_history=False,
                use_history=False,
            )

            if optimized:
                optimized = optimized.strip().strip("\"'.,!?:;\n\r")
                # Si l'utilisateur a explicitement mentionné une année, la
                # réinjecter pour éviter que le LLM l'écrase avec une autre.
                user_year_match = _re.search(r'\b(20\d{2})\b', query)
                if user_year_match:
                    user_year = user_year_match.group(1)
                    optimized = _re.sub(r'\b20\d{2}\b', user_year, optimized)
                else:
                    # Pas d'année dans la requête : ne corriger QUE les années
                    # clairement obsolètes (< current_year - 2). On ne touche
                    # pas à current_year-1 ou current_year car elles peuvent
                    # être correctes selon le contexte (ex. « dernière
                    # édition terminée » = current_year-1).
                    threshold = current_year - 2

                    def _fix_obsolete_year(match: "_re.Match") -> str:
                        year = int(match.group(0))
                        if year < threshold:
                            return str(last_completed_year)
                        return match.group(0)

                    optimized = _re.sub(r'\b20\d{2}\b', _fix_obsolete_year, optimized)
                if 3 <= len(optimized) <= 120:
                    print(
                        f"🔧 [AIEngine] Requête optimisée : '{query}' → '{optimized}'"
                    )
                    return optimized
        except Exception as e:
            self.logger.warning("Erreur lors de l'optimisation de la requête: %s", e)

        return query

    def is_complex_query(self, query: str) -> bool:
        """Détermine si une requête nécessite un raisonnement multi-étapes (Thinking Mode).

        Critères durcis pour éviter d'activer le thinking sur des questions simples :
        - Requêtes très longues (>200 chars) → toujours complexe
        - 2+ mots-clés complexes détectés → complexe
        - 1 seul mot-clé complexe → complexe seulement si la requête > 60 chars
        - Du code intégré dans la requête → complexe
        - Plusieurs questions (?) → NON suffisant seul (supprimé)
        """
        if len(query) > 200:
            return True
        complex_kw = [
            # Français — explication / analyse
            "explique", "expliquer", "fonctionne", "comment fonctionne",
            "analyse", "analysé", "analyser",
            "compare", "comparé", "comparer",
            "pourquoi", "qu'est-ce que", "qu'est ce que",
            "quelle est la différence", "comment faire pour",
            "démontre", "démontrer", "résous", "résoudre",
            "détaille", "détailler",
            # Français — création / implémentation
            "corrige", "corriger", "optimise", "optimiser",
            "implémente", "implémenter", "améliore", "améliorer",
            "refactor", "architecture", "conception",
            "complexe", "avancé", "programme", "application",
            "projet", "système", "algorithme", "script",
            "générer", "créer", "générez", "créez",
            # Anglais
            "explain", "analyze", "analyse",
            "debug", "optimize", "implement", "design",
            "what is the difference", "how does", "how to",
            "step by step", "étape par étape",
            "how do i", "how can i",
        ]
        q = query.lower()
        kw_count = sum(1 for kw in complex_kw if kw in q)
        # 2+ mots-clés → toujours complexe
        if kw_count >= 2:
            return True
        # 1 mot-clé → complexe seulement si la requête est assez longue
        if kw_count == 1 and len(query) > 60:
            return True
        # Code intégré → complexe
        if "```" in query or query.count("`") >= 4:
            return True
        return False

    def is_ollama_active(self) -> bool:
        """Retourne True si Ollama est disponible et actif (ping live)."""
        llm = getattr(self.local_ai, "local_llm", None)
        if llm is None:
            return False
        try:
            url = getattr(llm, "ollama_url", "http://localhost:11434/api/generate")
            ping_url = url.replace("/api/generate", "")
            resp = _req.get(ping_url, timeout=2)
            alive = resp.status_code == 200
            if alive and not getattr(llm, "is_ollama_available", False):
                # Ollama est maintenant disponible — mettre à jour le flag en cache
                llm.is_ollama_available = True
                self.logger.info("🦙 [OLLAMA] Disponibilité détectée tardivement, flag mis à jour")
            return alive
        except Exception:
            return getattr(llm, "is_ollama_available", False)

    def process_query_stream(
        self,
        user_input: str,
        on_token=None,
        on_tool_call=None,
        on_thinking_token=None,
        on_thinking_complete=None,
        image_base64: Optional[str] = None,
        context: Optional[Dict] = None,
        is_interrupted_callback=None,
        on_delete_confirm=None,
    ) -> str:
        """
        Point d'entrée synchrone et streamé pour la GUI.

        Stratégie :
          1. Image (vision) → direct
          2. Détection d'intention Python → appel direct de l'outil
             (contourne le bug tool-calling Ollama qui écrit le JSON en texte)
          3. Stream final Ollama avec le résultat de l'outil injecté
          4. Fallback → CustomAIModel
        """
        # Détection automatique de la langue de l'utilisateur
        self._current_lang_instruction = self._get_lang_instruction(user_input)

        # ----------------------------------------------------------------
        # 1. Vision
        # ----------------------------------------------------------------
        if image_base64:
            return self.local_ai.generate_response_stream(
                user_input,
                on_token=on_token,
                image_base64=image_base64,
                context=context,
                on_thinking_token=on_thinking_token,
                on_thinking_complete=on_thinking_complete,
            )

        llm = getattr(self.local_ai, "local_llm", None)
        # Rafraîchir le flag si nécessaire (cas : Ollama démarré après le lancement de l'app)
        if llm is not None and not getattr(llm, "is_ollama_available", False):
            llm.is_ollama_available = self.is_ollama_active()
        if llm is None or not llm.is_ollama_available:
            # Pas d'Ollama → fallback direct
            return self.local_ai.generate_response_stream(
                user_input, on_token=on_token, context=context
            )

        # ----------------------------------------------------------------
        # 1.5. FAQ / Enrichissement — Priorité absolue avant MCP et Thinking
        # La FAQ est vérifiée même en mode thinking (requête complexe) : si une
        # réponse est trouvée, elle est retournée immédiatement sans raisonnement.
        # Le widget de raisonnement éventuellement créé par le GUI est fermé via
        # on_thinking_complete() → _finalize_reasoning_widget() → masqué si vide.
        # ----------------------------------------------------------------
        if self.ml_ai is not None:
            try:
                faq_response = self.ml_ai.predict(user_input)
                if faq_response is not None and str(faq_response).strip():
                    print(f"📚 [FAQ ENGINE] ✅ Réponse FAQ trouvée pour: '{user_input}'")
                    # Sauvegarder dans l'historique Ollama pour que les questions
                    # de rappel ("on a parlé de quoi ?") puissent y accéder
                    if llm is not None:
                        llm.add_to_history("user", user_input)
                        llm.add_to_history("assistant", faq_response)
                    try:
                        self.conversation_manager.add_exchange(user_input, faq_response)
                    except Exception:
                        pass
                    # Fermer le widget de raisonnement s'il était ouvert
                    # (requête détectée complexe par le GUI mais couverte par FAQ)
                    if on_thinking_complete:
                        on_thinking_complete()
                    if on_token:
                        on_token(faq_response)
                    return faq_response
            except Exception as _faq_exc:
                self.logger.warning("[FAQ ENGINE] Erreur consultation FAQ: %s", _faq_exc)

        # ----------------------------------------------------------------
        # 1.7. MODE THINKING — géré nativement par Qwen3.5 via generate_stream()
        # ----------------------------------------------------------------
        # Le thinking natif Qwen3.5 est activé directement dans generate_stream()
        # quand on_thinking_token est fourni ("think":True dans la requête Ollama).
        # Les tokens de raisonnement (message.thinking) sont routés vers le widget,
        # les tokens de réponse (message.content) vers le chat — en une seule passe.
        # Le widget raisonnement sert aussi pour le plan du ChatOrchestrator.
        # on_thinking_complete est appelé dans un bloc finally pour couvrir
        # tous les chemins (thinking, plan, outils, erreurs, fallback).
        effective_input = user_input

        # ----------------------------------------------------------------
        # 2. Exécution via MCP Tool Calling (Ollama)
        # ----------------------------------------------------------------
        try:
            tools = self.mcp_manager.get_ollama_tools()

            # Construire le system prompt
            cwd = os.getcwd()
            user_downloads = str(Path.home() / "Downloads")
            user_documents = str(Path.home() / "Documents")
            user_desktop = str(Path.home() / "Desktop")

            # Partir du SYSTEM du Modelfile (identité + règles de formatage),
            # puis ajouter les instructions MCP spécifiques à cette session.
            _base = self._modelfile_system
            system_prompt = (
                (_base + "\n\n") if _base else
                "Tu es My_AI, un assistant personnel local, confidentiel et puissant.\n\n"
            ) + (
                "Tu as un ACCÈS TOTAL ET COMPLET à tout l'ordinateur de l'utilisateur. Tu n'es en aucun cas limité au répertoire de ton projet. "
                "Tu peux lire, écrire, créer, supprimer ou déplacer n'importe quel fichier sur l'ensemble du disque dur (ex: C:\\, D:\\, répertoires systèmes, etc.) via tes outils.\n"
                f"L'utilisateur se trouve actuellement dans le répertoire de travail (racine du projet) : {cwd}. "
                "Cependant, si on te demande de manipuler un fichier ou d'interagir avec le système, utilise systématiquement des CHEMINS ABSOLUS (ex: C:\\Users\\...).\n\n"
                "⚠️ GESTION DES DOSSIERS STANDARDS : \n"
                "Les répertoires systèmes personnels de l'utilisateur EXISTENT DÉJÀ (ils sont natifs à Windows/Linux). "
                "Tu n'as PAS BESOIN de les créer avec 'create_directory'. Utilise directement 'write_local_file' avec ces chemins exacts absolus :\n"
                f"- Téléchargements (Downloads) : {user_downloads}\n"
                f"- Documents : {user_documents}\n"
                f"- Bureau (Desktop) : {user_desktop}\n"
                "Exemple : Si on te dit 'Crée le fichier info.txt dans Téléchargements', lance directement 'write_local_file' avec le path '{user_downloads}\\info.txt'. N'invente pas de sous-dossiers traduits en français comme 'Downloads\\Téléchargements'.\n\n"
                f"{getattr(self, '_current_lang_instruction', self._LANG_SUFFIXES['fr'])} "
                "Sois direct et précis. Pour les requêtes de code, génère toujours le code complet sans te limiter."
            )
            system_prompt = self._inject_knowledge_base_context(user_input, system_prompt)

            # Ajouter le contexte des documents chargés
            full_context = self._prepare_context(user_input, context)
            if full_context.get("stored_documents"):
                relevant_docs = self._select_relevant_docs(user_input, full_context["stored_documents"])
                doc_sections = []
                for doc_name, doc_data in relevant_docs.items():
                    doc_content = doc_data.get("content", "") if isinstance(doc_data, dict) else str(doc_data)
                    if doc_content:
                        doc_sections.append(f"=== {doc_name} ===\n{doc_content[:8000]}")
                if doc_sections:
                    # Le contenu est déjà injecté dans le prompt : aucun outil nécessaire.
                    # Vider tools pour forcer une réponse directe sans appel d'outil.
                    tools = []
                    system_prompt += (
                        "\n\nContenu des documents chargés par l'utilisateur "
                        "(disponible comme contexte — utilise ces données si la question porte sur ce contenu, sinon réponds normalement depuis tes connaissances) :\n"
                        + "\n\n".join(doc_sections)
                    )

            # ----------------------------------------------------------------
            # 2.1. Requêtes sur l'historique de conversation — réponse directe
            # sans outils pour éviter le bug tool-calling
            # ----------------------------------------------------------------
            _history_signals = [
                "on a parlé de quoi", "de quoi on a parlé", "on a discuté",
                "rappelle-moi", "rappelles moi", "résume notre conversation",
                "résumé de notre conversation", "notre conversation",
                "ce qu'on a dit", "qu'est-ce qu'on a dit",
                "tu te souviens", "tu te rappelles",
                "sujets abordés", "sujet de notre conversation",
                "quels sujets", "au cours de cette session",
                "what did we talk", "what have we talked",
                "conversation history", "session history",
            ]
            _q_lower = user_input.lower()
            if any(sig in _q_lower for sig in _history_signals):
                # Source primaire : historique Ollama (contient FAQ + réponses LLM)
                ollama_hist = getattr(llm, "conversation_history", [])
                history_lines = []
                if ollama_hist:
                    # Regrouper les messages user/assistant par paires
                    pairs = []
                    i = 0
                    while i < len(ollama_hist):
                        msg = ollama_hist[i]
                        if msg.get("role") == "user":
                            u_text = msg.get("content", "")
                            a_text = ""
                            if i + 1 < len(ollama_hist) and ollama_hist[i + 1].get("role") == "assistant":
                                a_text = ollama_hist[i + 1].get("content", "")
                                i += 2
                            else:
                                i += 1
                            pairs.append((u_text, a_text))
                        else:
                            i += 1
                    for u, a in pairs[-20:]:
                        if u:
                            history_lines.append(f"- Utilisateur : {u}")
                        if a:
                            history_lines.append(f"  Assistant : {a[:300]}{'…' if len(a) > 300 else ''}")
                # Fallback : conversation_manager
                if not history_lines:
                    recent = self.conversation_manager.get_recent_history()
                    for ex in recent[-20:]:
                        u = ex.get("user_input", "")
                        a_raw = ex.get("ai_response", {})
                        a = a_raw.get("text", a_raw.get("message", "")) if isinstance(a_raw, dict) else str(a_raw)
                        if u:
                            history_lines.append(f"- Utilisateur : {u}")
                        if a:
                            history_lines.append(f"  Assistant : {a[:300]}{'…' if len(a) > 300 else ''}")
                if history_lines:
                    history_text = "\n".join(history_lines)
                    history_system = (
                        system_prompt
                        + f"\n\nVoici l'historique complet de cette conversation :\n{history_text}"
                        "\n\nRéponds directement en te basant sur cet historique, "
                        "sans utiliser d'outils."
                    )
                else:
                    history_system = (
                        system_prompt
                        + "\n\nNous n'avons pas encore échangé dans cette session."
                        " Dis-le à l'utilisateur de façon naturelle."
                    )
                history_response = llm.generate_stream(
                    prompt=user_input,
                    system_prompt=history_system,
                    on_token=on_token,
                    is_interrupted_callback=is_interrupted_callback,
                )
                if history_response:
                    return history_response

            def tool_executor(tool_name: str, arguments: dict) -> str:
                if is_interrupted_callback and is_interrupted_callback():
                    return "[Interrompu par l'utilisateur]"
                if tool_name == "web_search":
                    # Optimiser la requête avant tout affichage ou exécution
                    optimized_q = self._optimize_search_query(user_input, llm)
                    arguments = {**arguments, "query": optimized_q}
                # Confirmation utilisateur pour la suppression de fichier
                if tool_name == "delete_local_file" and on_delete_confirm:
                    file_path = arguments.get("path", "")
                    if not on_delete_confirm(file_path):
                        return (
                            "[Suppression annulée par l'utilisateur] "
                            f"L'utilisateur a refusé la suppression de : {file_path}"
                        )
                # Callback visuel GUI avec les arguments FINAUX (après optimisation)
                if on_tool_call:
                    on_tool_call(tool_name, arguments)
                tool_result = self.mcp_manager.execute_tool_sync(tool_name, arguments)
                return tool_result

            # Requêtes purement conversationnelles : pas d'outils
            if tools and self._is_conversational(user_input):
                tools = []

            if tools:
                # ── ChatOrchestrator : boucle agentique ReAct avec scratchpad,
                # détection de boucle, limite de tours et élagage du contexte ──
                orch_result = self._chat_orchestrator.run(
                    user_input=effective_input,
                    tools=tools,
                    tool_executor=tool_executor,
                    llm=llm,
                    system_prompt=system_prompt,
                    on_token=on_token,
                    on_thinking_token=on_thinking_token,
                    on_thinking_complete=on_thinking_complete,
                    is_interrupted_callback=is_interrupted_callback,
                    on_tool_call=on_tool_call,
                )

                if orch_result:
                    self.logger.info(
                        "process_query_stream ok (ChatOrchestrator, %d chars)",
                        len(orch_result),
                    )
                    return orch_result

                # Si le traitement a été interrompu manuellement, on s'arrête ici
                if is_interrupted_callback and is_interrupted_callback():
                    self.logger.info("Traitement interrompu. Pas de fallback.")
                    return "Opération annulée."

                # Fallback : aucune réponse produite → stream direct sans outils
                self.logger.warning(
                    "[ChatOrchestrator] aucune réponse — fallback generate_stream"
                )
                retry = llm.generate_stream(
                    prompt=effective_input,
                    system_prompt=system_prompt,
                    on_token=on_token,
                    is_interrupted_callback=is_interrupted_callback,
                    on_thinking_token=on_thinking_token,
                    on_thinking_complete=on_thinking_complete,
                )
                if retry:
                    return retry
            else:
                # Fallback si aucun outil n'est disponible
                response = llm.generate_stream(
                    prompt=effective_input,
                    system_prompt=system_prompt,
                    on_token=on_token,
                    is_interrupted_callback=is_interrupted_callback,
                    on_thinking_token=on_thinking_token,
                    on_thinking_complete=on_thinking_complete,
                )
                if response:
                    return response

        except Exception as exc:
            self.logger.warning("process_query_stream Ollama stream échoué : %s", exc)
        finally:
            # Finaliser le widget raisonnement (arrêt animation dots, masquage si vide)
            # Couvre tous les chemins : thinking, plan, outils, erreurs, fallback.
            if on_thinking_complete:
                on_thinking_complete()

        # ----------------------------------------------------------------
        # 3. Fallback → CustomAIModel
        # ----------------------------------------------------------------
        return self.local_ai.generate_response_stream(
            user_input,
            on_token=on_token,
            context=context,
        )

    async def _handle_conversation(self, query: str, context: Dict) -> Dict[str, Any]:
        """
        Gère les conversations générales
        """
        try:
            # Si on a des documents, les inclure dans le contexte
            prompt = query
            if "stored_documents" in context and context["stored_documents"]:
                prompt = """Contexte des documents disponibles:
                
"""
                for doc_name in context["stored_documents"].keys():
                    prompt += f"- {doc_name}\n"

                prompt += f"\nQuestion: {query}\n\nRéponds en tenant compte du contexte si pertinent."

            response = self.local_ai.generate_response(prompt)

            return {"type": "conversation", "message": response, "success": True}
        except (AttributeError, TypeError, ValueError) as e:
            self.logger.error("Erreur conversation: %s", e)
            return {
                "type": "conversation",
                "message": f"Erreur lors de la conversation: {str(e)}",
                "success": False,
            }

    async def _handle_file_processing(
        self, query: str, context: Dict
    ) -> Dict[str, Any]:
        """
        Gère le traitement de fichiers et questions sur les documents - VERSION CORRIGÉE
        """
        try:
            query_lower = query.lower()

            # Récupérer les documents disponibles
            all_docs = context.get("stored_documents", {})
            document_order = context.get("document_order", [])

            # NOUVELLE LOGIQUE : Détecter le type de document demandé VS disponible
            requested_type = self._detect_requested_document_type(query_lower)
            available_types = self._get_available_document_types(all_docs)

            print(f"[DEBUG] Type demandé: {requested_type}")
            print(f"[DEBUG] Types disponibles: {available_types}")

            # VÉRIFICATION DE COHÉRENCE
            if requested_type and requested_type not in available_types:
                return self._generate_type_mismatch_response(
                    requested_type, available_types, all_docs
                )

            # Déterminer le document cible selon le type demandé
            target_document = None

            if requested_type:
                # Chercher un document du type demandé
                target_document = self._find_document_by_type(
                    all_docs, document_order, requested_type
                )

            # Gestion des références numériques (premier, deuxième, etc.)
            is_first_requested = any(
                term in query_lower
                for term in ["premier", "1er", "1ère", "première", "document 1", "le 1"]
            )
            is_second_requested = any(
                term in query_lower
                for term in [
                    "deuxième",
                    "2ème",
                    "2eme",
                    "seconde",
                    "document 2",
                    "le 2",
                ]
            )
            is_last_requested = any(
                term in query_lower for term in ["dernier", "dernière", "last"]
            )

            if is_first_requested and len(document_order) >= 1:
                target_document = document_order[0]
            elif is_second_requested and len(document_order) >= 2:
                target_document = document_order[1]
            elif is_last_requested and document_order:
                target_document = document_order[-1]

            # Si aucun document spécifique trouvé, prendre le plus récent
            if not target_document and document_order:
                target_document = document_order[-1]

            # Traitement spécial pour les fichiers Python (explication détaillée)
            if target_document and target_document.lower().endswith(".py"):
                if any(word in query_lower for word in ["explique", "analyse", "code"]):
                    return self._handle_python_code_explanation(
                        target_document, all_docs
                    )

            # Traitement standard pour les autres documents
            if target_document and target_document in all_docs:
                doc_data = all_docs[target_document]
                doc_content = (
                    doc_data.get("content")
                    if isinstance(doc_data, dict)
                    else str(doc_data)
                )

                if doc_content:
                    # Générer le résumé approprié selon le type de document
                    doc_type = self._determine_document_type(target_document)

                    # Déléguer la création du résumé au modèle IA local
                    response = self.local_ai.create_document_summary(
                        doc_content, target_document, doc_type
                    )

                    return {
                        "type": "file_processing",
                        "message": response,
                        "success": True,
                    }

            return {
                "type": "file_processing",
                "message": "Aucun document approprié trouvé pour traiter votre demande.",
                "success": False,
            }

        except (FileNotFoundError, OSError, ValueError, AttributeError) as e:
            print(f"❌ Erreur traitement fichier: {e}")
            return {
                "type": "file_processing",
                "message": f"Erreur lors du traitement : {str(e)}",
                "success": False,
            }

    def _detect_requested_document_type(self, query_lower: str) -> Optional[str]:
        """
        Détecte le type de document spécifiquement demandé dans la requête

        Returns:
            'pdf', 'docx', 'code', ou None si pas spécifique
        """
        # Détection PDF
        if any(term in query_lower for term in ["pdf", "le pdf", "du pdf", "ce pdf"]):
            return "pdf"

        # Détection DOCX/Word
        if any(
            term in query_lower
            for term in [
                "docx",
                "doc",
                "word",
                "le docx",
                "du docx",
                "le doc",
                "du doc",
            ]
        ):
            return "docx"

        # Détection Code
        if any(
            term in query_lower
            for term in [
                "code",
                "py",
                "python",
                "script",
                "programme",
                "le code",
                "du code",
            ]
        ):
            return "code"

        return None

    def _get_available_document_types(self, all_docs: Dict) -> List[str]:
        """
        Détermine les types de documents disponibles

        Returns:
            Liste des types disponibles: ['pdf', 'docx', 'code']
        """
        available_types = []

        for doc_name, doc_data in all_docs.items():
            doc_type = self._determine_document_type(doc_name, doc_data)
            if doc_type not in available_types:
                available_types.append(doc_type)

        return available_types

    def _determine_document_type(self, doc_name: str, doc_data: Any = None) -> str:
        """
        Détermine le type d'un document

        Returns:
            'pdf', 'docx', ou 'code'
        """
        doc_name_lower = doc_name.lower()

        if doc_name_lower.endswith(".pdf"):
            return "pdf"
        elif doc_name_lower.endswith((".docx", ".doc")):
            return "docx"
        elif doc_name_lower.endswith(
            (".py", ".js", ".html", ".css", ".java", ".cpp", ".c")
        ):
            return "code"
        elif isinstance(doc_data, dict) and doc_data.get("type") == "code":
            return "code"
        else:
            # Par défaut, considérer comme document texte
            return "docx"

    def _find_document_by_type(
        self, all_docs: Dict, document_order: List, requested_type: str
    ) -> Optional[str]:
        """
        Trouve un document du type demandé

        Returns:
            Nom du document trouvé ou None
        """
        # Chercher dans l'ordre inverse (le plus récent en premier)
        for doc_name in reversed(document_order):
            if doc_name in all_docs:
                doc_type = self._determine_document_type(doc_name, all_docs[doc_name])
                if doc_type == requested_type:
                    return doc_name

        return None

    def _generate_type_mismatch_response(
        self, requested_type: str, available_types: List[str], all_docs: Dict
    ) -> Dict[str, Any]:
        """
        Génère une réponse quand le type demandé n'est pas disponible
        """
        # Mappage pour un langage plus naturel
        type_names = {
            "pdf": "fichier PDF",
            "docx": "document Word/DOCX",
            "code": "fichier de code",
        }

        requested_name = type_names.get(requested_type, requested_type)

        # Construire la liste des documents disponibles
        available_docs = []
        for doc_name in all_docs.keys():
            doc_type = self._determine_document_type(doc_name, all_docs[doc_name])
            type_name = type_names.get(doc_type, doc_type)
            available_docs.append(f"• **{doc_name}** ({type_name})")

        response = "❌ **Document non trouvé**\n\n"
        response += f"Vous demandez l'analyse d'un **{requested_name}**, mais je n'ai pas ce type de document en mémoire.\n\n"

        if available_docs:
            response += "📁 **Documents actuellement disponibles :**\n"
            response += "\n".join(available_docs)
            response += "\n\n💡 **Suggestion :** Reformulez votre demande en utilisant le bon type :\n"

            if "pdf" in available_types:
                response += '• "résume le PDF" ou "explique le PDF"\n'
            if "docx" in available_types:
                response += '• "résume le DOCX" ou "explique le document"\n'
            if "code" in available_types:
                response += '• "explique le code" ou "analyse le Python"\n'
        else:
            response += "Aucun document n'est actuellement en mémoire."

        return {"type": "file_processing", "message": response, "success": False}

    def _handle_python_code_explanation(
        self, target_document: str, all_docs: Dict
    ) -> Dict[str, Any]:
        """
        Gère l'explication détaillée des fichiers Python
        """
        try:
            doc_data = all_docs.get(target_document, {})
            doc_content = (
                doc_data.get("content") if isinstance(doc_data, dict) else str(doc_data)
            )

            if not doc_content:
                return {
                    "type": "file_processing",
                    "message": f"Le fichier {target_document} semble vide.",
                    "success": False,
                }

            # Créer un fichier temporaire pour l'analyse
            with tempfile.NamedTemporaryFile(
                "w", delete=False, suffix=".py", encoding="utf-8"
            ) as tmpf:
                tmpf.write(doc_content)
                tmp_path = tmpf.name

            try:
                # Utiliser le code_processor pour l'explication détaillée
                explanation = self.code_processor.generate_detailed_explanation(
                    tmp_path, real_file_name=os.path.basename(target_document)
                )

                return {
                    "type": "file_processing",
                    "message": explanation,
                    "success": True,
                }

            finally:
                # Nettoyer le fichier temporaire
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

        except (OSError, ValueError) as e:
            return {
                "type": "file_processing",
                "message": f"Erreur lors de l'explication du code : {str(e)}",
                "success": False,
            }

    async def _handle_web_search(self, query: str) -> Dict[str, Any]:
        """
        Gère les requêtes de recherche web factuelle
        """
        try:
            search_engine = InternetSearchEngine()
            summary = search_engine.search_and_summarize(query)
            return {"type": "web_search", "message": summary, "success": True}
        except (ConnectionError, TimeoutError) as e:
            self.logger.error("Erreur recherche web: %s", e)
            return {
                "type": "web_search",
                "message": f"Erreur lors de la recherche web: {str(e)}",
                "success": False,
            }

    async def _handle_code_generation(
        self, query: str, is_interrupted_callback=None
    ) -> Dict[str, Any]:
        """
        Gère la génération de code avec Ollama ou recherche web

        Args:
            query: Requête utilisateur
            is_interrupted_callback: Fonction pour vérifier si l'opération est interrompue
        """
        try:
            query_lower = query.lower()
            language = self._detect_code_language(query)

            # PRIORITÉ 0: Détection "génère moi un fichier..." -> Utiliser CodeGenerator avec Ollama
            file_keywords = [
                "génère moi un fichier",
                "crée moi un fichier",
                "génère un fichier",
                "crée un fichier",
            ]
            if any(keyword in query_lower for keyword in file_keywords):
                try:
                    self.logger.info("🔧 Détection génération de fichier avec Ollama")

                    # Utiliser le générateur Ollama déjà initialisé avec callback d'interruption
                    result = await self.ollama_code_generator.generate_file(
                        query, is_interrupted_callback=is_interrupted_callback
                    )

                    # Vérifier IMMÉDIATEMENT si l'opération a été interrompue
                    if result.get("interrupted"):
                        self.logger.info(
                            "⚠️ Génération de fichier interrompue par l'utilisateur"
                        )
                        return {
                            "type": "file_generation",
                            "success": False,
                            "interrupted": True,
                            "message": "⚠️ Création du fichier interrompue.",
                        }

                    if result.get("success"):
                        code = result.get("code", "")
                        filename = result.get("filename", "generated_file")
                        file_path = result.get("file_path", "")

                        return {
                            "type": "file_generation",  # Type spécial pour GUI
                            "code": code,
                            "message": f"Voici votre fichier : {filename}",
                            "filename": filename,
                            "file_path": file_path,
                            "source": "Ollama (Génération locale)",
                            "success": True,
                            "is_file_download": True,  # Flag pour l'interface
                        }
                    else:
                        error_msg = result.get("error", "Erreur inconnue")
                        self.logger.warning("Échec génération fichier: %s", error_msg)
                        # Continuer vers le fallback

                except (ConnectionError, TimeoutError, OSError) as e:
                    self.logger.warning("Erreur génération fichier avec Ollama: %s", e)
                    # Continuer vers le fallback

            # 🌐 PRIORITÉ 1: Recherche web PURE sans templates pré-codés
            try:
                web_result = await self.code_generator.generate_code_from_web(
                    query, language
                )

                if web_result.get("success"):
                    code = web_result.get("code", "")
                    explanation = web_result.get("explanation", "")
                    source = web_result.get("source", "Recherche Web")
                    url = web_result.get("url", "")

                    # Formater la réponse avec source
                    source_info = f" ([Source]({url}))" if url else ""

                    self.logger.info("✅ Code trouvé sur le web: %s", source)
                    return {
                        "type": "code_generation",
                        "code": code,
                        "message": f"🌐 **Code trouvé sur {source}**{source_info}\n\n```{language}\n{code}\n```\n\n💬 **Explication:** {explanation}",
                        "source": source,
                        "url": url,
                        "rating": web_result.get("rating", 4.0),
                        "success": True,
                    }
                else:
                    self.logger.warning(
                        "Recherche web échouée: %s",
                        web_result.get("error", "Erreur inconnue"),
                    )

            except (ConnectionError, TimeoutError, ImportError) as e:
                self.logger.warning("Générateur web pur indisponible: %s", e)

            # 🔄 FALLBACK 1: Système de recherche web intelligent (avec cache)
            try:
                web_results = await search_smart_code(query, language, max_results=3)

                if web_results and len(web_results) > 0:
                    best_result = web_results[0]

                    # Vérifier la pertinence
                    if best_result.relevance_score > 0.4:  # Seuil plus permissif
                        sources_info = "\n".join(
                            [
                                f"• {result.title} ({result.source_name})"
                                for result in web_results[:2]
                            ]
                        )

                        return {
                            "type": "code_generation",
                            "code": best_result.code,
                            "message": f"🌐 **Code trouvé sur le web:**\n{sources_info}\n\n```{language}\n{best_result.code}\n```\n\n💬 **Source:** {best_result.description}",
                            "sources": [
                                {
                                    "title": r.title,
                                    "url": r.source_url,
                                    "source": r.source_name,
                                }
                                for r in web_results
                            ],
                            "rating": best_result.rating,
                            "success": True,
                        }

            except (ConnectionError, TimeoutError, ImportError) as e:
                self.logger.warning("Recherche web intelligente échouée: %s", e)

            # 🔧 FALLBACK 2: Générateur local spécialisé MINIMAL (sans templates complexes)
            local_code = self._generate_minimal_code(query, language)

            if local_code and len(local_code.strip()) > 30:
                return {
                    "type": "code_generation",
                    "code": local_code,
                    "message": f"🛠️ **Code généré localement (recherche web échouée):**\n\n```{language}\n{local_code}\n```\n\n💬 **Note:** Solution basique créée car aucune solution trouvée sur le web.",
                    "source": "Générateur local minimal",
                    "rating": 2.5,
                    "success": True,
                }

            # 🚨 ÉCHEC TOTAL
            return {
                "type": "code_generation",
                "message": f'❌ **Impossible de trouver du code pour:** "{query}"\n\n🔍 **Recherches effectuées:**\n• GitHub, Stack Overflow, GeeksforGeeks\n• Recherche Google générale\n\n💡 **Suggestions:**\n• Reformulez votre demande (ex: "fonction Python qui trie une liste")\n• Précisez le langage (Python, JavaScript, etc.)\n• Décrivez ce que la fonction doit faire exactement',
                "success": False,
            }

        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error("Erreur génération code: %s", e)
            return {
                "type": "code_generation",
                "message": f"❌ Erreur lors de la recherche de code: {str(e)}",
                "success": False,
            }

    async def _handle_document_generation(
        self, query: str, context: Dict
    ) -> Dict[str, Any]:
        """
        Gère la génération de documents
        """
        try:
            # Générer le document sans await (methode sync)
            document = self.document_generator.generate_document(query, context)

            return {
                "type": "document_generation",
                "document": document,
                "message": "Document généré avec succès",
                "success": True,
            }
        except (AttributeError, TypeError, ValueError, OSError) as e:
            self.logger.error("Erreur génération document: %s", e)
            return {
                "type": "document_generation",
                "message": f"Erreur lors de la génération de document: {str(e)}",
                "success": False,
            }

    async def _handle_general_query(self, query: str, context: Dict) -> Dict[str, Any]:
        """
        Gère les requêtes générales
        """
        try:
            # Construire le prompt avec contexte si disponible
            prompt = query
            if "stored_documents" in context and context["stored_documents"]:
                prompt = """Contexte des documents disponibles:
                
"""
                for doc_name in context["stored_documents"].keys():
                    prompt += f"- {doc_name}\n"

                prompt += f"\nQuestion: {query}\n\nRéponds en tenant compte du contexte si pertinent."

            response = self.local_ai.generate_response(prompt)

            return {"type": "general", "message": response, "success": True}
        except (AttributeError, TypeError, ValueError) as e:
            self.logger.error("Erreur requête générale: %s", e)
            return {
                "type": "general",
                "message": f"Erreur lors du traitement: {str(e)}",
                "success": False,
            }

    def _detect_code_language(self, query: str) -> str:
        """Détecte le langage de programmation demandé"""
        query_lower = query.lower()

        if any(word in query_lower for word in ["python", "py"]):
            return "python"
        elif any(word in query_lower for word in ["javascript", "js", "node"]):
            return "javascript"
        elif any(word in query_lower for word in ["html", "page web", "site"]):
            return "html"
        elif any(word in query_lower for word in ["css", "style"]):
            return "css"
        else:
            return "python"  # Par défaut

    def _create_code_accompaniment(self, query: str, language: str) -> str:
        """Crée un message d'accompagnement intelligent pour le code"""
        query_lower = query.lower()

        # Messages spécifiques selon le type de code demandé
        if any(word in query_lower for word in ["factorielle", "factorial"]):
            return f"🔢 **Code pour calculer une factorielle en {language.capitalize()}**\n\nVoici une implémentation efficace avec gestion des cas d'erreur :"

        elif any(word in query_lower for word in ["hello", "world", "bonjour"]):
            return f"👋 **Programme Hello World en {language.capitalize()}**\n\nLe classique pour débuter :"

        elif any(word in query_lower for word in ["fibonacci", "fibo"]):
            return f"🌀 **Séquence de Fibonacci en {language.capitalize()}**\n\nCode optimisé pour générer la suite :"

        elif any(word in query_lower for word in ["tri", "sort", "trier"]):
            return f"📊 **Algorithme de tri en {language.capitalize()}**\n\nImplémentation d'un tri efficace :"

        elif any(word in query_lower for word in ["classe", "class", "objet"]):
            return (
                f"🏗️ **Classe en {language.capitalize()}**\n\nStructure orientée objet :"
            )

        elif any(word in query_lower for word in ["fonction", "function", "def"]):
            return f"⚙️ **Fonction en {language.capitalize()}**\n\nCode modulaire et réutilisable :"

        elif any(word in query_lower for word in ["api", "web", "serveur"]):
            return f"🌐 **Code pour API/Web en {language.capitalize()}**\n\nStructure pour service web :"

        else:
            return f"💻 **Code généré en {language.capitalize()}**\n\nVoici une implémentation pour votre demande :"

    def _enhance_web_solution(self, web_solution, query: str, language: str) -> str:
        """
        Améliore une solution trouvée sur le web en l'adaptant à la demande précise
        """
        base_code = web_solution.code
        query_lower = query.lower()

        # Ajouts intelligents basés sur la demande
        enhanced_code = base_code

        # Ajouter des commentaires explicatifs si manquants
        if not any(
            line.strip().startswith("#")
            or line.strip().startswith("//")
            or line.strip().startswith("/*")
            for line in base_code.split("\n")
        ):
            if language.lower() == "python":
                enhanced_code = f'"""\n{web_solution.title}\nSolution adaptée pour: {query}\n"""\n\n{base_code}'
            elif language.lower() in ["javascript", "js"]:
                enhanced_code = f"/**\n * {web_solution.title}\n * Solution adaptée pour: {query}\n */\n\n{base_code}"

        # Ajout de gestion d'erreurs si nécessaire
        if (
            "error" not in base_code.lower()
            and "try" not in base_code.lower()
            and "except" not in base_code.lower()
        ):
            if language.lower() == "python" and len(base_code.split("\n")) > 5:
                if "def " in base_code:
                    # Wrapper avec try/except pour les fonctions
                    enhanced_code = (
                        enhanced_code.replace("def ", "def ")
                        + '\n\n# Exemple d\'usage sécurisé:\n# try:\n#     result = votre_fonction()\n# except Exception as e:\n#     print(f"Erreur: {e}")'
                    )

        # Ajout d'exemples d'usage si manquants
        if "example" not in base_code.lower() and "test" not in base_code.lower():
            if language.lower() == "python":
                enhanced_code += '\n\n# Exemple d\'utilisation:\nif __name__ == "__main__":\n    # Testez votre code ici\n    pass'

        # Optimisations spécifiques par type de demande
        if any(word in query_lower for word in ["api", "web", "http"]):
            if language.lower() == "python" and "requests" not in base_code:
                enhanced_code = "import requests\n" + enhanced_code

        if any(word in query_lower for word in ["file", "fichier", "csv", "json"]):
            if language.lower() == "python" and "with open" not in base_code:
                enhanced_code += (
                    "\n\n# Gestion sécurisée des fichiers avec context manager"
                )

        return enhanced_code

    def _validate_solution_relevance(self, solution, query: str, language: str) -> bool:
        """
        Valide strictement la pertinence d'une solution web par rapport à la demande
        """
        code_lower = solution.code.lower()
        query_lower = query.lower()

        # 1. Vérifier que le code contient les concepts clés de la requête
        key_concepts = self._extract_query_concepts(query_lower)

        if not key_concepts:
            return False

        # 2. Score de pertinence basé sur les concepts présents dans le code
        concept_matches = 0
        for concept in key_concepts:
            if concept in code_lower:
                concept_matches += 1

        relevance_score = concept_matches / len(key_concepts)

        # 3. Vérifications spécifiques selon le type de demande
        specific_checks = self._perform_specific_validation(
            code_lower, query_lower, language
        )

        # 4. Score final : au moins 70% de pertinence + validations spécifiques
        is_relevant = relevance_score >= 0.7 and specific_checks

        print(
            f"[VALIDATION] Query: '{query[:30]}...' | Score: {relevance_score:.2f} | Spécific: {specific_checks} | Result: {is_relevant}"
        )

        return is_relevant

    def _extract_query_concepts(self, query_lower: str) -> list:
        """Extrait les concepts clés de la requête"""
        concept_mapping = {
            "concat": [
                "concat",
                "concatén",
                "join",
                "joindre",
                "combiner",
                "fusionner",
            ],
            "string": ["string", "chaîne", "chaine", "caractère", "str", "texte"],
            "function": ["fonction", "function", "def"],
            "sort": ["tri", "trier", "sort", "order", "ordonner"],
            "file": ["fichier", "file", "lire", "read", "écrire", "write"],
            "api": ["api", "rest", "endpoint", "requête", "request"],
            "class": ["classe", "class", "objet", "object"],
            "array": ["liste", "array", "list", "tableau"],
            "loop": ["boucle", "loop", "for", "while", "itération"],
        }

        concepts = []
        for main_concept, variations in concept_mapping.items():
            if any(var in query_lower for var in variations):
                concepts.append(main_concept)

        return concepts

    def _perform_specific_validation(
        self, code_lower: str, query_lower: str, language: str
    ) -> bool:
        """Effectue des validations spécifiques selon le type de demande"""

        # Validation pour les fonctions de concaténation
        if "concat" in query_lower or "concatén" in query_lower:
            concat_indicators = [
                "+",
                "join()",
                ".join",
                "concat",
                "format",
                'f"',
                "f'",
                "%s",
            ]
            return any(indicator in code_lower for indicator in concat_indicators)

        # Validation pour les fonctions de tri
        if "tri" in query_lower or "sort" in query_lower:
            sort_indicators = ["sort", "sorted", "key=", "reverse=", "lambda", "order"]
            return any(indicator in code_lower for indicator in sort_indicators)

        # Validation pour la lecture de fichiers
        if "fichier" in query_lower or "file" in query_lower:
            file_indicators = ["open(", "with open", "read()", "write()", "close()"]
            return any(indicator in code_lower for indicator in file_indicators)

        # Validation pour les API
        if "api" in query_lower:
            api_indicators = [
                "request",
                "response",
                "json",
                "get(",
                "post(",
                "flask",
                "fastapi",
            ]
            return any(indicator in code_lower for indicator in api_indicators)

        # Validation pour les classes
        if "classe" in query_lower or "class" in query_lower:
            class_indicators = ["class ", "__init__", "self.", "def "]
            return any(indicator in code_lower for indicator in class_indicators)

        # Validation générale : au moins une structure de code Python valide
        if language.lower() == "python":
            python_indicators = [
                "def ",
                "class ",
                "import ",
                "for ",
                "if ",
                "return",
                "print(",
            ]
            return any(indicator in code_lower for indicator in python_indicators)

        return True  # Pas de validation spécifique, accepter

    def _generate_smart_local_code(self, query: str, language: str) -> str:
        """
        Génère du code local intelligent basé sur des patterns reconnus
        """
        query_lower = query.lower()

        # Template pour concaténation de chaînes
        if (
            "concat" in query_lower
            and "string" in query_lower
            or "chaîne" in query_lower
        ):
            return self._generate_string_concat_code(language)

        # Template pour fonction de tri
        elif "tri" in query_lower or "sort" in query_lower:
            return self._generate_sort_code(language)

        # Template pour lecture de fichier
        elif "fichier" in query_lower or "file" in query_lower:
            return self._generate_file_code(language)

        # Template pour classe basique
        elif "classe" in query_lower or "class" in query_lower:
            return self._generate_class_code(language)

        # Template pour API simple
        elif "api" in query_lower:
            return self._generate_api_code(language)

        return ""  # Aucun template trouvé

    def _generate_string_concat_code(self, language: str) -> str:
        """Génère du code de concaténation de chaînes"""
        if language.lower() == "python":
            return '''def concat_strings(*strings):
    """
    Concatène plusieurs chaînes de caractères

    Args:
        *strings: Chaînes à concaténer

    Returns:
        str: Chaîne concaténée
    """
    return ''.join(str(s) for s in strings)

def concat_with_separator(separator, *strings):
    """
    Concatène des chaînes avec un séparateur

    Args:
        separator (str): Séparateur à utiliser
        *strings: Chaînes à concaténer

    Returns:
        str: Chaîne concaténée avec séparateur
    """
    return separator.join(str(s) for s in strings)

# Exemples d'utilisation
if __name__ == "__main__":
    # Concaténation simple
    result1 = concat_strings("Hello", " ", "World", "!")
    print(f"Résultat 1: {result1}")  # Hello World!

    # Concaténation avec séparateur
    result2 = concat_with_separator(" - ", "Pierre", "Paul", "Jacques")
    print(f"Résultat 2: {result2}")  # Pierre - Paul - Jacques

    # Méthodes alternatives Python
    str1, str2, str3 = "Hello", "World", "!"

    # Méthode 1: Opérateur +
    concat1 = str1 + " " + str2 + str3

    # Méthode 2: f-string (recommandé)
    concat2 = f"{str1} {str2}{str3}"

    # Méthode 3: join()
    concat3 = " ".join([str1, str2]) + str3

    print(f"Méthode +: {concat1}")
    print(f"Méthode f-string: {concat2}")
    print(f"Méthode join: {concat3}")'''

        elif language.lower() == "javascript":
            return """function concatStrings(...strings) {
    /**
     * Concatène plusieurs chaînes de caractères
     * @param {...string} strings - Chaînes à concaténer
     * @returns {string} Chaîne concaténée
     */
    return strings.join('');
}

function concatWithSeparator(separator, ...strings) {
    /**
     * Concatène des chaînes avec un séparateur
     * @param {string} separator - Séparateur à utiliser
     * @param {...string} strings - Chaînes à concaténer
     * @returns {string} Chaîne concaténée avec séparateur
     */
    return strings.join(separator);
}

// Exemples d'utilisation
const result1 = concatStrings("Hello", " ", "World", "!");
console.log("Résultat 1:", result1); // Hello World!

const result2 = concatWithSeparator(" - ", "Pierre", "Paul", "Jacques");
console.log("Résultat 2:", result2); // Pierre - Paul - Jacques

// Méthodes alternatives JavaScript
const str1 = "Hello", str2 = "World", str3 = "!";

// Méthode 1: Opérateur +
const concat1 = str1 + " " + str2 + str3;

// Méthode 2: Template literals (recommandé)
const concat2 = `${str1} ${str2}${str3}`;

// Méthode 3: concat()
const concat3 = str1.concat(" ", str2, str3);

console.log("Méthode +:", concat1);
console.log("Template literals:", concat2);
console.log("Méthode concat():", concat3);"""

        return ""

    def _generate_sort_code(self, language: str) -> str:
        """Génère du code de tri"""
        if language.lower() == "python":
            return '''def sort_list(items, reverse=False):
    """
    Trie une liste d'éléments

    Args:
        items (list): Liste à trier
        reverse (bool): Tri décroissant si True

    Returns:
        list: Liste triée
    """
    return sorted(items, reverse=reverse)

def sort_by_key(items, key_func, reverse=False):
    """
    Trie une liste selon une fonction clé

    Args:
        items (list): Liste à trier
        key_func (function): Fonction pour extraire la clé
        reverse (bool): Tri décroissant si True

    Returns:
        list: Liste triée
    """
    return sorted(items, key=key_func, reverse=reverse)

# Exemples d'utilisation
if __name__ == "__main__":
    # Tri simple
    numbers = [3, 1, 4, 1, 5, 9, 2, 6]
    sorted_numbers = sort_list(numbers)
    print(f"Nombres triés: {sorted_numbers}")

    # Tri décroissant
    sorted_desc = sort_list(numbers, reverse=True)
    print(f"Tri décroissant: {sorted_desc}")

    # Tri de chaînes
    names = ["Pierre", "Paul", "Alice", "Bob"]
    sorted_names = sort_list(names)
    print(f"Noms triés: {sorted_names}")

    # Tri par longueur
    sorted_by_length = sort_by_key(names, len)
    print(f"Tri par longueur: {sorted_by_length}")

    # Tri d'objets complexes
    people = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Charlie", "age": 35}
    ]
    sorted_by_age = sort_by_key(people, lambda x: x["age"])
    print(f"Tri par âge: {sorted_by_age}")'''

        return ""

    def _generate_file_code(self, language: str) -> str:
        """Génère du code de gestion de fichiers"""
        if language.lower() == "python":
            return '''def read_file(file_path, encoding='utf-8'):
    """
    Lit le contenu d'un fichier

    Args:
        file_path (str): Chemin vers le fichier
        encoding (str): Encodage du fichier

    Returns:
        str: Contenu du fichier
    """
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            return file.read()
    except FileNotFoundError:
        print(f"Erreur: Fichier '{file_path}' non trouvé")
        return ""
    except (OSError, UnicodeDecodeError) as e:
        print(f"Erreur lors de la lecture: {e}")
        return ""

def write_file(file_path, content, encoding='utf-8'):
    """
    Écrit du contenu dans un fichier

    Args:
        file_path (str): Chemin vers le fichier
        content (str): Contenu à écrire
        encoding (str): Encodage du fichier

    Returns:
        bool: True si succès
    """
    try:
        with open(file_path, 'w', encoding=encoding) as file:
            file.write(content)
        return True
    except (OSError, PermissionError) as e:
        print(f"Erreur lors de l'écriture: {e}")
        return False

# Exemple d'utilisation
if __name__ == "__main__":
    # Écriture d'un fichier test
    test_content = "Hello World!\\nCeci est un test."

    if write_file("test.txt", test_content):
        print("Fichier écrit avec succès")

        # Lecture du fichier
        content = read_file("test.txt")
        print(f"Contenu lu: {content}")
    else:
        print("Erreur lors de l'écriture")'''

        return ""

    def _generate_class_code(self, language: str) -> str:
        """Génère une classe exemple"""
        if language.lower() == "python":
            return '''class User:
    """
    Classe pour représenter un utilisateur
    """

    def __init__(self, name, email, age=None):
        """
        Initialise un nouvel utilisateur

        Args:
            name (str): Nom de l'utilisateur
            email (str): Email de l'utilisateur
            age (int, optional): Âge de l'utilisateur
        """
        self.name = name
        self.email = email
        self.age = age
        self.is_active = True

    def get_info(self):
        """
        Retourne les informations de l'utilisateur

        Returns:
            dict: Informations utilisateur
        """
        return {
            "name": self.name,
            "email": self.email,
            "age": self.age,
            "is_active": self.is_active
        }

    def update_email(self, new_email):
        """
        Met à jour l'email de l'utilisateur

        Args:
            new_email (str): Nouvel email
        """
        self.email = new_email

    def deactivate(self):
        """Désactive l'utilisateur"""
        self.is_active = False

    def __str__(self):
        """Représentation string de l'utilisateur"""
        return f"User(name='{self.name}', email='{self.email}')"

    def __repr__(self):
        """Représentation technique de l'utilisateur"""
        return f"User(name='{self.name}', email='{self.email}', age={self.age})"

# Exemple d'utilisation
if __name__ == "__main__":
    # Créer un utilisateur
    user = User("Alice Dupont", "alice@example.com", 30)

    # Afficher les informations
    print(user)
    print(f"Infos: {user.get_info()}")

    # Modifier l'email
    user.update_email("alice.dupont@newdomain.com")
    print(f"Nouvel email: {user.email}")

    # Désactiver l'utilisateur
    user.deactivate()
    print(f"Utilisateur actif: {user.is_active}")'''

        return ""

    def _generate_api_code(self, language: str) -> str:
        """Génère du code API basique"""
        if language.lower() == "python":
            return '''from flask import Flask, jsonify, request

app = Flask(__name__)

# Base de données simulée
users = [
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob", "email": "bob@example.com"}
]

@app.route('/api/users', methods=['GET'])
def get_users():
    """
    Récupère la liste des utilisateurs

    Returns:
        JSON: Liste des utilisateurs
    """
    return jsonify({"users": users, "count": len(users)})

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """
    Récupère un utilisateur spécifique

    Args:
        user_id (int): ID de l'utilisateur

    Returns:
        JSON: Utilisateur ou erreur
    """
    user = next((u for u in users if u["id"] == user_id), None)
    if user:
        return jsonify(user)
    return jsonify({"error": "Utilisateur non trouvé"}), 404

@app.route('/api/users', methods=['POST'])
def create_user():
    """
    Crée un nouvel utilisateur

    Returns:
        JSON: Utilisateur créé
    """
    data = request.get_json()

    if not data or 'name' not in data or 'email' not in data:
        return jsonify({"error": "Nom et email requis"}), 400

    new_id = max(u["id"] for u in users) + 1 if users else 1
    new_user = {
        "id": new_id,
        "name": data["name"],
        "email": data["email"]
    }

    users.append(new_user)
    return jsonify(new_user), 201

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)'''

        return ""

    def _generate_minimal_code(self, query: str, language: str) -> str:
        """
        Générateur minimal uniquement si la recherche web échoue complètement
        """
        query_lower = query.lower()

        if language.lower() == "python":
            # Tri alphabétique minimal
            if any(
                word in query_lower for word in ["tri", "sort", "ordre", "alphabétique"]
            ):
                return '''def sort_list(items):
    """Trie une liste par ordre alphabétique"""
    return sorted(items)

# Exemple
words = ["pomme", "banane", "cerise"]
sorted_words = sort_list(words)
print(sorted_words)  # ['banane', 'cerise', 'pomme']'''

            # Conversion majuscules
            elif any(
                word in query_lower for word in ["majuscule", "uppercase", "upper"]
            ):
                return '''def to_uppercase(text):
    """Convertit le texte en majuscules"""
    return text.upper()

# Exemple
result = to_uppercase("hello world")
print(result)  # HELLO WORLD'''

            # Fonction basique
            elif any(word in query_lower for word in ["fonction", "function", "def"]):
                return '''def my_function(parameter):
    """Description de votre fonction"""
    # Votre code ici
    result = parameter
    return result

# Exemple d'utilisation
output = my_function("test")
print(output)'''

        elif language.lower() == "javascript":
            # Tri alphabétique
            if any(
                word in query_lower for word in ["tri", "sort", "ordre", "alphabétique"]
            ):
                return """function sortArray(items) {
    // Trie un tableau par ordre alphabétique
    return items.sort();
}

// Exemple
const words = ["pomme", "banane", "cerise"];
const sortedWords = sortArray([...words]);
console.log(sortedWords); // ["banane", "cerise", "pomme"]"""

            # Fonction basique
            elif any(word in query_lower for word in ["fonction", "function"]):
                return """function myFunction(parameter) {
    // Description de votre fonction
    // Votre code ici
    return parameter;
}

// Exemple d'utilisation
const result = myFunction("test");
console.log(result);"""

        return ""  # Aucun template minimal trouvé

    def get_status(self) -> Dict[str, Any]:
        """
        Retourne le statut du moteur IA
        """
        return {
            "engine": "running",
            "mode": "enterprise_local",
            "llm_status": "local_custom_model_only",
            "conversation_count": (
                len(self.conversation_manager.history)
                if hasattr(self.conversation_manager, "history")
                else 0
            ),
            "local_ai_stats": (
                self.local_ai.get_stats() if hasattr(self.local_ai, "get_stats") else {}
            ),
            "config": self.config,
        }
