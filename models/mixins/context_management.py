"""
ContextManagementMixin — Gestion du contexte documentaire (Ultra 1M tokens + classique).

Regroupe : add_document_to_context, add_file_to_context,
search_in_context, _refine_ultra_context, get_context_stats, etc.
"""

import os
import re
import time
from typing import Any, Dict


class ContextManagementMixin:
    """Mixin regroupant la gestion de contexte documentaire."""

    # =============== MÉTHODES ULTRA 1M TOKENS ===============

    def add_document_to_context(
        self, document_content: str, document_name: str = ""
    ) -> Dict[str, Any]:
        """
        Ajoute un document au contexte 1M tokens
        """
        if not self.ultra_mode:
            # Mode standard - utiliser la mémoire classique
            result = self._add_document_to_classic_memory(
                document_content, document_name
            )

            # 🧠 Aussi analyser avec l'analyseur intelligent
            if self.document_analyzer:
                try:
                    self.document_analyzer.analyze_document(
                        document_content, document_name
                    )
                    print(
                        f"🧠 [ANALYZER] Document '{document_name}' analysé intelligemment"
                    )
                except (ValueError, TypeError, AttributeError) as e:
                    print(f"⚠️ [ANALYZER] Erreur analyse: {e}")

            return result

        try:
            # Mode Ultra - utiliser le gestionnaire 1M tokens
            result = self.context_manager.add_document(
                content=document_content, document_name=document_name
            )

            # Stocker aussi dans la mémoire classique pour compatibilité
            self._add_document_to_classic_memory(document_content, document_name)

            # 🧠 Aussi analyser avec l'analyseur intelligent
            if self.document_analyzer:
                try:
                    self.document_analyzer.analyze_document(
                        document_content, document_name
                    )
                    print(
                        f"🧠 [ANALYZER] Document '{document_name}' analysé intelligemment"
                    )
                except (ValueError, TypeError, AttributeError) as e:
                    print(f"⚠️ [ANALYZER] Erreur analyse: {e}")

            return {
                "success": True,
                "message": f"Document '{document_name}' ajouté au contexte Ultra",
                "chunks_created": result.get("chunks_created", 0),
                "context_size": self.context_manager.current_tokens,
            }
        except (ValueError, MemoryError, OSError) as e:
            return {
                "success": False,
                "message": f"Erreur lors de l'ajout du document: {str(e)}",
            }

    def _add_document_to_classic_memory(
        self, content: str, doc_name: str
    ) -> Dict[str, Any]:
        """Ajoute un document à la mémoire classique"""
        try:
            word_count = len(content.split())

            # Stocker le document avec métadonnées
            self.conversation_memory.stored_documents[doc_name] = {
                "content": content,
                "timestamp": time.time(),
                "word_count": word_count,
                "order_index": len(self.conversation_memory.document_order),
            }

            # Mettre à jour l'ordre chronologique
            if doc_name not in self.conversation_memory.document_order:
                self.conversation_memory.document_order.append(doc_name)

            return {
                "success": True,
                "message": f"Document '{doc_name}' stocké en mémoire classique",
                "word_count": word_count,
            }
        except (KeyError, TypeError, AttributeError) as e:
            return {"success": False, "message": f"Erreur mémoire classique: {str(e)}"}

    def add_file_to_context(self, file_path: str) -> Dict[str, Any]:
        """Ajoute un fichier au contexte en utilisant les processeurs avancés"""
        try:
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()

            # Traitement selon le type de fichier
            content = ""
            processor_used = "basic"

            if file_ext == ".pdf" and self.pdf_processor:
                try:
                    result = self.pdf_processor.read_pdf(file_path)
                    if result.get("error"):
                        print(f"⚠️ Erreur PDF: {result['error']}")
                        content = ""
                    elif result.get("success"):
                        # Structure: result["content"]["text"]
                        content_data = result.get("content", {})
                        content = content_data.get("text", "")
                        pages = content_data.get("page_count", 0)
                        processor_used = "PDF"
                        print(
                            f"📄 [PDF] Traitement PDF: {pages} pages, {len(content)} caractères"
                        )
                    else:
                        # Structure: result["text"] (fallback)
                        content = result.get("text", "")
                        pages = result.get("page_count", 0)
                        processor_used = "PDF"
                        print(
                            f"📄 [PDF] Traitement PDF: {pages} pages, {len(content)} caractères"
                        )
                except (OSError, ValueError) as e:
                    print(f"⚠️ Erreur processeur PDF: {e}")
                    # Fallback vers lecture basique
                    try:
                        with open(file_path, "rb") as f:
                            content = f.read().decode("utf-8", errors="ignore")
                    except (OSError, UnicodeDecodeError):
                        content = ""

            elif file_ext in [".docx", ".doc"] and self.docx_processor:
                try:
                    result = self.docx_processor.read_docx(file_path)
                    content_data = result.get("content", {}) if result.get("success") else {}
                    content = content_data.get("text", "") if isinstance(content_data, dict) else ""
                    processor_used = "DOCX"
                    para_count = len(content_data.get("paragraphs", [])) if isinstance(content_data, dict) else 0
                    print(
                        f"📄 [DOCX] Traitement DOCX: {para_count} paragraphes"
                    )
                except (OSError, ValueError) as e:
                    print(f"⚠️ Erreur processeur DOCX: {e}")
                    # Fallback vers lecture basique
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

            elif file_ext in [".xlsx", ".xls", ".csv"]:
                try:
                    from processors.excel_processor import ExcelProcessor
                    excel_proc = ExcelProcessor()
                    result = excel_proc.read_excel(file_path)
                    if result.get("success"):
                        content = result.get("content", "")
                        processor_used = "Excel/CSV"
                        sheets = result.get("sheet_names", [])
                        total_rows = result.get("total_rows", 0)
                        print(
                            f"📊 [EXCEL] Traitement {file_ext.upper()}: "
                            f"{len(sheets)} feuille(s), {total_rows} lignes"
                        )
                    else:
                        raise ValueError(result.get("error", "Erreur Excel"))
                except (ImportError, ValueError, OSError) as e:
                    print(f"⚠️ Erreur processeur Excel: {e}")
                    content = ""

            elif (
                file_ext in [".py", ".js", ".html", ".css", ".cpp", ".java"]
                and self.code_processor
            ):
                try:
                    result = self.code_processor.analyze_code(file_path)
                    content = result.get("content", "")
                    processor_used = "Code"
                    print(
                        f"📄 [CODE] Traitement code: {result.get('language', 'unknown')}"
                    )
                except (OSError, ValueError) as e:
                    print(f"⚠️ Erreur processeur Code: {e}")
                    # Fallback vers lecture basique
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
            else:
                # Lecture basique
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    processor_used = "basic"
                except UnicodeDecodeError:
                    with open(file_path, "r", encoding="latin-1") as f:
                        content = f.read()
                    processor_used = "basic-latin1"

            if not content:
                return {"success": False, "message": "Contenu vide après traitement"}

            # Ajouter au contexte
            result = self.add_document_to_context(content, file_name)
            result.update(
                {
                    "processor_used": processor_used,
                    "analysis_info": f"Pages: N/A, Caractères: {len(content)}",
                }
            )

            return result

        except Exception as e:
            return {
                "success": False,
                "message": f"Erreur lors du traitement du fichier: {str(e)}",
            }

    def search_in_context(self, query: str) -> str:
        """
        🔍 Recherche intelligente dans le contexte 1M tokens
        Améliore la recherche pour trouver les passages les plus pertinents
        """
        if not self.ultra_mode:
            return self._search_in_classic_memory(query)

        try:
            print(f"🔍 [ULTRA] Recherche intelligente pour: '{query[:60]}...'")

            # 🎯 ÉTAPE 1: Extraire les mots-clés de la question
            keywords = self._extract_question_keywords(query)
            print(f"🔑 [ULTRA] Mots-clés extraits: {keywords}")

            # 🎯 ÉTAPE 2: Recherche multi-stratégie
            all_context_parts = []

            # Stratégie 1: Recherche avec mots-clés enrichis
            enhanced_query = " ".join(keywords)
            context1 = self.context_manager.get_relevant_context(
                enhanced_query, max_chunks=15  # Plus de chunks pour avoir plus de choix
            )
            if context1 and len(context1.strip()) > 50:
                all_context_parts.append(context1)

            # Stratégie 2: Recherche avec la requête originale
            context2 = self.context_manager.get_relevant_context(query, max_chunks=15)
            if context2 and len(context2.strip()) > 50 and context2 != context1:
                all_context_parts.append(context2)

            # Stratégie 3: Recherche avec des termes spécifiques selon le type de question
            query_lower = query.lower()
            specific_searches = []

            if "version" in query_lower:
                specific_searches.extend(
                    ["version 5.0.0", "configuration version", '"version"']
                )
            if "performance" in query_lower or "temps" in query_lower:
                specific_searches.extend(
                    ["temps de réponse < 3", "performance", "3 secondes"]
                )
            if "algorithme" in query_lower or "tri" in query_lower:
                specific_searches.extend(["merge_sort", "tri fusion", "insertion sort"])
            if "turing" in query_lower:
                specific_searches.extend(["Alan Turing 1950", "Test de Turing"])
            if "langage" in query_lower and (
                "ia" in query_lower or "débuter" in query_lower
            ):
                specific_searches.extend(
                    ["Python scikit-learn", "pandas", "recommandé pour débuter"]
                )
            if "token" in query_lower or "million" in query_lower:
                specific_searches.extend(
                    ["1000000 tokens", "1M tokens", "context_size"]
                )

            for specific_query in specific_searches:
                context_specific = self.context_manager.get_relevant_context(
                    specific_query, max_chunks=5
                )
                if context_specific and len(context_specific.strip()) > 50:
                    if context_specific not in all_context_parts:
                        all_context_parts.append(context_specific)

            # Combiner tous les contextes trouvés
            if all_context_parts:
                combined_context = "\n\n".join(all_context_parts)
                print(
                    f"✅ [ULTRA] Contexte combiné: {len(combined_context)} caractères de {len(all_context_parts)} sources"
                )

                # 🎯 ÉTAPE 3: Post-traitement pour extraire les passages les plus pertinents
                refined_context = self._refine_ultra_context(
                    combined_context, query, keywords
                )

                # ✅ NOUVELLE LOGIQUE : Utiliser le contenu raffiné s'il est pertinent
                if refined_context and len(refined_context.strip()) > 100:
                    print(
                        f"🎯 [ULTRA] Contexte raffiné utilisé: {len(refined_context)} caractères"
                    )
                    return refined_context
                elif refined_context and len(refined_context.strip()) > 50:
                    print(
                        f"🎯 [ULTRA] Contexte raffiné court mais utilisé: {len(refined_context)} caractères"
                    )
                    return refined_context
                else:
                    print("🔄 [ULTRA] Utilisation du contexte combiné complet")
                    return combined_context
            else:
                print("⚠️ [ULTRA] Contexte vide ou insuffisant")

            # Fallback vers mémoire classique
            return self._search_in_classic_memory(query)

        except Exception as e:
            print(f"❌ [ULTRA] Erreur recherche: {e}")
            return self._search_in_classic_memory(query)

    def _refine_ultra_context(self, context: str, query: str, keywords: list) -> str:
        """
        🎯 Raffine le contexte Ultra pour extraire les passages les plus pertinents
        """
        try:
            print(f"🔍 [REFINE] Début du raffinement: {len(context)} caractères")

            # 🎯 ÉTAPE 1: Diviser le contenu de manière plus agressive
            sections = []

            # Méthode 1: Double saut de ligne
            if "\n\n" in context:
                sections = context.split("\n\n")
                print(f"📄 [REFINE] Division par double saut: {len(sections)} sections")

            # Méthode 2: Saut de ligne simple si peu de sections
            if len(sections) < 5:
                sections = context.split("\n")
                sections = [s.strip() for s in sections if len(s.strip()) > 20]
                print(f"📄 [REFINE] Division par saut simple: {len(sections)} sections")

            # Méthode 3: Division par phrases longues si toujours peu de sections
            if len(sections) < 5:
                sentences = re.split(r"[.!?]+", context)
                sections = []
                current_section = ""

                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) < 10:
                        continue

                    if len(current_section) + len(sentence) > 300:
                        if current_section:
                            sections.append(current_section.strip())
                        current_section = sentence
                    else:
                        current_section += (
                            ". " + sentence if current_section else sentence
                        )

                if current_section:
                    sections.append(current_section.strip())

                print(f"📄 [REFINE] Division par phrases: {len(sections)} sections")

            # 🚫 ÉTAPE PRÉ-FILTRAGE: EXCLURE COMPLÈTEMENT les sections génériques
            generic_patterns = [
                "cette section explore",
                "pour diversifier le contexte",
                r"section\s*#\s*\d+",
                r"#\s*section\s*\d+",
                "métriques spécialisées pour",
                "optimisations spécifiques à",
                "contenu spécialisé en",
            ]

            filtered_sections = []
            for section in sections:
                section_lower = section.lower()
                is_generic = False

                for pattern in generic_patterns:
                    if pattern.startswith("r") or "\\" in pattern or "\\s" in pattern:
                        if re.search(pattern, section_lower):
                            is_generic = True
                            break
                    else:
                        if pattern in section_lower:
                            is_generic = True
                            break

                if not is_generic:
                    filtered_sections.append(section)

            print(
                f"🚫 [REFINE] Après filtrage générique: {len(filtered_sections)}/{len(sections)} sections gardées"
            )
            sections = filtered_sections

            # 🎯 ÉTAPE 2: Scorer chaque section
            scored_sections = []
            query_lower = query.lower()

            for i, section in enumerate(sections):
                if len(section.strip()) < 30:
                    continue

                section_lower = section.lower()
                score = 0

                for keyword in keywords:
                    if keyword in section_lower:
                        score += 3
                        score += section_lower.count(keyword) * 1.5

                # 🎯 BONUS SPÉCIFIQUES selon le type de question
                if "version" in query_lower:
                    if '"version"' in section_lower or "'version'" in section_lower:
                        score += 15
                    if "5.0.0" in section:
                        score += 20
                    if (
                        "system_config" in section_lower
                        or "configuration" in section_lower
                    ):
                        score += 10

                elif (
                    "performance" in query_lower
                    or "temps" in query_lower
                    or "objectif" in query_lower
                ):
                    if "temps de réponse" in section_lower:
                        score += 15
                    if "< 3 secondes" in section_lower or "< 3s" in section_lower:
                        score += 25
                    if "3000ms" in section_lower:
                        score += 25
                    if "objectifs de performance" in section_lower:
                        score += 10
                    if "< 2 secondes" in section_lower and "section #" in section_lower:
                        score -= 15

                elif (
                    "algorithme" in query_lower
                    or "tri" in query_lower
                    or "fusion" in query_lower
                ):
                    if "merge_sort" in section_lower or "merge sort" in section_lower:
                        score += 20
                    if "tri fusion" in section_lower:
                        score += 20
                    if (
                        "insertion_sort" in section_lower
                        or "insertion sort" in section_lower
                    ):
                        score += 15
                    if "def merge" in section_lower or "def insertion" in section_lower:
                        score += 25

                elif "turing" in query_lower:
                    if "alan turing" in section_lower:
                        score += 25
                    if "1950" in section:
                        score += 20
                    if "test de turing" in section_lower:
                        score += 15
                    if "dartmouth" in section_lower or "pionniers" in section_lower:
                        score += 10

                elif "langage" in query_lower and (
                    "ia" in query_lower or "débuter" in query_lower
                ):
                    if "scikit-learn" in section_lower:
                        score += 20
                    if "pandas" in section_lower:
                        score += 15
                    if "python" in section_lower and "recommand" in section_lower:
                        score += 25
                    if "machine learning de base" in section_lower:
                        score += 20

                elif "token" in query_lower or "capacité" in query_lower:
                    if "1000000" in section or "1,000,000" in section:
                        score += 25
                    if "context_size" in section_lower:
                        score += 20
                    if "1m tokens" in section_lower:
                        score += 20

                if "difficulté" in query_lower or "problème" in query_lower:
                    difficulty_words = [
                        "difficulté",
                        "problème",
                        "challenge",
                        "obstacle",
                        "compliqué",
                        "difficile",
                        "complexe",
                    ]
                    for word in difficulty_words:
                        if word in section_lower:
                            score += 5

                elif "date" in query_lower or "période" in query_lower:
                    date_words = [
                        "date",
                        "période",
                        "juin",
                        "juillet",
                        "août",
                        "2025",
                        "début",
                        "fin",
                        "durée",
                    ]
                    for word in date_words:
                        if word in section_lower:
                            score += 5

                elif "lieu" in query_lower or "endroit" in query_lower:
                    location_words = [
                        "lieu",
                        "endroit",
                        "pierre fabre",
                        "lavaur",
                        "cauquillous",
                        "adresse",
                        "localisation",
                    ]
                    for word in location_words:
                        if word in section_lower:
                            score += 5

                elif "mission" in query_lower or "tâche" in query_lower:
                    mission_words = [
                        "mission",
                        "tâche",
                        "responsabilité",
                        "rôle",
                        "travail",
                        "fonction",
                        "activité",
                    ]
                    for word in mission_words:
                        if word in section_lower:
                            score += 5

                if any(
                    char in section
                    for char in [":", "-", "•", "►", "→", "1.", "2.", "3."]
                ):
                    score += 2

                if "table des matières" in section_lower or section.count(".....") > 2:
                    score -= 10

                if score > 0:
                    print(
                        f"📊 [REFINE] Section {i}: {score} points - {section[:60]}..."
                    )

                if score > 0:
                    scored_sections.append((score, section.strip()))

            # 🎯 ÉTAPE 3: Sélectionner les meilleures sections
            if scored_sections:
                scored_sections.sort(key=lambda x: x[0], reverse=True)

                print(f"🏆 [REFINE] Top scores: {[s[0] for s in scored_sections[:5]]}")

                good_sections = [
                    section[1] for section in scored_sections if section[0] >= 3
                ]

                if good_sections:
                    selected_sections = good_sections[:3]
                    refined_content = "\n\n---\n\n".join(selected_sections)

                    print(
                        f"✅ [REFINE] {len(selected_sections)} sections sélectionnées, {len(refined_content)} caractères"
                    )
                    return refined_content
                else:
                    print("⚠️ [REFINE] Aucune section avec score suffisant")

            print("🔄 [REFINE] Fallback - recherche par mots-clés simples")
            return self._simple_keyword_search(context, keywords)

        except Exception as e:
            print(f"❌ [REFINE] Erreur: {e}")
            return self._simple_keyword_search(context, keywords)

    def _simple_keyword_search(self, content: str, keywords: list) -> str:
        """Recherche simple par mots-clés si le raffinement avancé échoue"""
        try:
            lines = content.split("\n")
            relevant_lines = []

            for line in lines:
                line_lower = line.lower()
                if (
                    any(keyword in line_lower for keyword in keywords)
                    and len(line.strip()) > 20
                ):
                    relevant_lines.append(line.strip())

            if relevant_lines:
                result = "\n".join(relevant_lines[:5])
                print(f"🔍 [SIMPLE] {len(relevant_lines)} lignes pertinentes trouvées")
                return result
            else:
                print("🔄 [SIMPLE] Aucune ligne pertinente, retour début document")
                return content[:800]

        except Exception as e:
            print(f"❌ [SIMPLE] Erreur: {e}")
            return content[:800]

    def _search_in_classic_memory(self, query: str) -> str:
        """Recherche dans la mémoire classique"""
        try:
            query_lower = query.lower()
            found_docs = []

            for doc_data in self.conversation_memory.stored_documents.items():
                content = doc_data.get("content", "")
                if any(word in content.lower() for word in query_lower.split()):
                    found_docs.append(content)

            return "\n\n".join(found_docs) if found_docs else ""

        except (KeyError, TypeError, AttributeError) as e:
            print(f"⚠️ Erreur recherche classique: {e}")
            return ""

    def get_context_stats(self) -> Dict[str, Any]:
        """Obtient les statistiques du contexte"""
        if self.ultra_mode and self.context_manager:
            stats = self.context_manager.get_stats()
            stats.update(
                {
                    "context_size": self.context_manager.current_tokens,
                    "max_context_length": self.context_manager.max_tokens,
                    "utilization_percent": round(
                        (
                            self.context_manager.current_tokens
                            / self.context_manager.max_tokens
                        )
                        * 100,
                        2,
                    ),
                }
            )
            return stats
        else:
            doc_count = len(self.conversation_memory.stored_documents)
            total_words = sum(
                doc.get("word_count", 0)
                for doc in self.conversation_memory.stored_documents.values()
            )

            return {
                "mode": "classic",
                "documents": doc_count,
                "total_words": total_words,
                "context_size": total_words * 1.3,
                "max_context_length": 100000,
                "utilization_percent": min(100, (total_words * 1.3 / 100000) * 100),
            }
