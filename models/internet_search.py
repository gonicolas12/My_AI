"""
Module de recherche internet avec extraction de réponse directe
Version corrigée sans doublons ni erreurs de syntaxe
"""

import concurrent.futures
import re
import statistics
import string
import time
import traceback
from collections import Counter
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
from rapidfuzz import fuzz
from bs4 import BeautifulSoup


class EnhancedInternetSearchEngine:
    """Moteur de recherche internet avec extraction de réponse directe"""

    def __init__(self):
        self.search_apis = {
            "duckduckgo": "https://api.duckduckgo.com/",
            "bing": "https://api.bing.microsoft.com/v7.0/search",
            "google_custom": "https://www.googleapis.com/customsearch/v1",
        }

        # Configuration
        self.max_results = 8
        self.max_content_length = 3000
        self.timeout = 15  # Augmenté à 15 secondes

        # User-agents multiples pour éviter la détection
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        ]

        self.current_user_agent_index = 0
        self.user_agent = self.user_agents[0]

        # Cache des résultats récents
        self.search_cache = {}
        self.cache_duration = 3600

        # Patterns pour l'extraction de réponses directes
        self.answer_patterns = self._init_answer_patterns()

    def _get_next_user_agent(self) -> str:
        """Obtient le prochain user-agent pour éviter la détection"""
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.user_agents)
        self.user_agent = self.user_agents[self.current_user_agent_index]
        return self.user_agent

    def _correct_common_typos(self, query: str) -> str:
        """Corrige les fautes d'orthographe courantes dans les requêtes - VERSION SIMPLE"""
        corrections = {
            # Monuments et lieux célèbres
            'effeil': 'eiffel',
            'eifeil': 'eiffel',
            'effell': 'eiffel',
            'eifel': 'eiffel',

            # Villes
            'pariss': 'paris',
            'paaris': 'paris',

            # Mesures courantes
            'tail': 'taille',
            'taile': 'taille',
            'mesur': 'mesure',

            # Mots courants mal orthographiés
            'populatoin': 'population',
            'populaton': 'population',
            'hauteure': 'hauteur',
        }

        words = query.split()
        corrected_words = []
        has_correction = False

        for word in words:
            # Enlever la ponctuation pour la comparaison
            clean_word = word.lower().strip('.,;:!?')

            # Chercher une correction
            if clean_word in corrections:
                corrected_word = corrections[clean_word]
                # Préserver la ponctuation originale
                if word != clean_word:
                    corrected_word = corrected_word + word[len(clean_word):]
                corrected_words.append(corrected_word)
                has_correction = True
                print(f"✏️ Correction: '{word}' → '{corrected_word}'")
            else:
                corrected_words.append(word)

        corrected_query = ' '.join(corrected_words)

        if has_correction:
            print(f"✏️ Requête corrigée: '{query}' → '{corrected_query}'")

        return corrected_query

    def _init_answer_patterns(self) -> Dict[str, List[str]]:
        """Initialise les patterns pour extraire des réponses directes"""
        return {
            "taille": [
                r"(?:mesure|fait|taille|hauteur)(?:\s+de)?\s+([\d,]+\.?\d*)\s*(mètres?|m|km|centimètres?|cm)",
                r"([\d,]+\.?\d*)\s*(mètres?|m|km|centimètres?|cm)(?:\s+de|d')?\s+(?:haut|hauteur|taille)",
                r"(?:est|fait)(?:\s+de)?\s+([\d,]+\.?\d*)\s*(mètres?|m|km)",
            ],
            "poids": [
                r"(?:pèse|poids)(?:\s+de)?\s+([\d,]+\.?\d*)\s*(kilogrammes?|kg|tonnes?|grammes?|g)",
                r"([\d,]+\.?\d*)\s*(kilogrammes?|kg|tonnes?|grammes?|g)(?:\s+de|d')?\s+(?:poids|lourd)",
            ],
            "population": [
                r"(?:population|habitants?)(?:\s+de)?\s+([\d\s,]+\.?\d*)",
                r"([\d\s,]+\.?\d*)(?:\s+d')?\s*habitants?",
                r"compte\s+([\d\s,]+\.?\d*)(?:\s+d')?\s*habitants?",
            ],
            "date": [
                r"(?:en|depuis|dans|créé|fondé|construit|né)\s+(\d{4})",
                r"(\d{1,2})\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})",
                r"(\d{4})(?:\s*-\s*\d{4})?",
            ],
            "prix": [
                r"(?:coûte|prix|vaut)\s+([\d,]+\.?\d*)\s*(euros?|dollars?|\$|€)",
                r"([\d,]+\.?\d*)\s*(euros?|dollars?|\$|€)(?:\s+pour|de)?",
            ],
            "definition": [
                r"(?:est|sont)\s+([^.!?]{20,100})",
                r"([^.!?]{20,100})(?:\s+est|\s+sont)",
                r"(?:c'est|ce sont)\s+([^.!?]{20,100})",
            ],
        }

    def search_and_summarize(self, query: str) -> str:
        """Recherche sur internet et extrait la réponse directe"""
        try:
            print(f"🔍 Recherche internet pour: '{query}'")

            # NOUVEAU : Corriger les fautes d'orthographe courantes
            corrected_query = self._correct_common_typos(query)

            # Vérifier le cache (avec la requête corrigée)
            cache_key = self._generate_cache_key(corrected_query)
            if self._is_cache_valid(cache_key):
                print("📋 Résultats trouvés en cache")
                return self.search_cache[cache_key]["summary"]

            # Effectuer la recherche avec la requête corrigée
            search_results = self._perform_search(corrected_query)

            if not search_results:
                return f"❌ Désolé, je n'ai pas pu trouver d'informations sur '{query}'. Vérifiez votre connexion internet."

            # Extraire le contenu des pages
            page_contents = self._extract_page_contents(search_results)

            # Extraire la réponse directe (avec la requête originale pour l'affichage)
            direct_answer = self._extract_direct_answer(corrected_query, page_contents)

            # Générer le résumé
            summary = self._generate_answer_focused_summary(
                query, direct_answer, page_contents
            )

            # Mettre en cache
            self._cache_results(cache_key, summary, search_results)

            return summary

        except Exception as e:
            print(f"❌ Erreur lors de la recherche: {str(e)}")
            return f"Désolé, une erreur s'est produite lors de la recherche internet : {str(e)}"

    def _extract_direct_answer(
        self, query: str, page_contents: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Extrait la réponse directe à partir des contenus des pages"""
        print(f"🎯 Extraction de réponse directe pour: '{query}'")

        # Analyser le type de question
        question_type = self._analyze_question_type(query)
        print(f"🔍 Type de question détecté: {question_type}")

        # Extraire toutes les phrases candidates
        candidate_sentences = self._extract_candidate_sentences(page_contents, query)
        print(f"📝 {len(candidate_sentences)} phrases candidates trouvées")

        # Utiliser différentes stratégies selon le type de question
        if question_type == "factual":
            return self._extract_factual_answer(query, candidate_sentences)
        elif question_type == "measurement":
            return self._extract_measurement_answer(candidate_sentences, query)
        elif question_type == "definition":
            return self._extract_definition_answer(candidate_sentences)
        elif question_type == "date":
            return self._extract_date_answer(candidate_sentences)
        else:
            return self._extract_general_answer(query, candidate_sentences)

    def _analyze_question_type(self, query: str) -> str:
        """Analyse le type de question pour adapter l'extraction"""
        query_lower = query.lower()

        if any(
            word in query_lower
            for word in [
                "taille",
                "hauteur",
                "mesure",
                "fait",
                "mètres",
                "long",
                "large",
            ]
        ):
            return "measurement"

        if any(
            word in query_lower
            for word in [
                "qu'est-ce",
                "c'est quoi",
                "qui est",
                "que signifie",
                "définition",
            ]
        ):
            return "definition"

        if any(
            word in query_lower
            for word in ["quand", "date", "année", "créé", "fondé", "né", "construit"]
        ):
            return "date"

        if any(
            word in query_lower
            for word in [
                "combien",
                "quel",
                "quelle",
                "prix",
                "coût",
                "population",
                "nombre",
            ]
        ):
            return "factual"

        return "general"

    def _extract_candidate_sentences(
        self, page_contents: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """Extrait les phrases candidates contenant potentiellement la réponse"""
        candidates = []
        query_words = set(
            word.lower().strip(string.punctuation)
            for word in query.split()
            if len(word) > 2
        )

        # Extraire les noms propres potentiels (mots de >=4 lettres non-question)
        entity_words = set()
        for word in query.split():
            clean_word = word.strip('?.,!;:').lower()
            if len(clean_word) >= 4 and clean_word not in ['quel', 'quelle', 'comment', 'taille', 'hauteur', 'fait', 'mesure', 'what', 'which', 'height', 'size']:
                entity_words.add(clean_word)

        print(f"🎯 [FILTER] Entité(s) recherchée(s): {entity_words}")

        for page in page_contents:
            for content_field in ["snippet", "full_content"]:
                text = page.get(content_field, "")
                if text:
                    # Découper en phrases
                    sentences = re.split(r"(?<=[.!?])\s+", text)

                    for sentence in sentences:
                        sentence = sentence.strip()
                        if len(sentence) < 10 or len(sentence) > 500:
                            continue

                        # Calculer la pertinence
                        sentence_words = set(
                            word.lower().strip(string.punctuation)
                            for word in sentence.split()
                        )
                        relevance_score = len(query_words.intersection(sentence_words))

                        # BONUS MAJEUR si la phrase contient les mots de l'entité recherchée
                        entity_matches = len(entity_words.intersection(sentence_words))
                        if entity_matches > 0:
                            relevance_score += entity_matches * 5  # Très fort bonus !
                            print(f"  ✅ Phrase avec entité '{entity_words}': {sentence[:80]}...")

                        # Bonus pour les phrases avec des nombres ou des faits précis
                        if re.search(r"\d+", sentence):
                            relevance_score += 2

                        # Bonus pour les débuts de phrase indicatifs
                        if any(
                            sentence.lower().startswith(start)
                            for start in [
                                "la",
                                "le",
                                "il",
                                "elle",
                                "c'est",
                                "ce sont",
                                "on trouve",
                                "situé",
                            ]
                        ):
                            relevance_score += 1

                        if relevance_score > 0:
                            candidates.append(
                                {
                                    "sentence": sentence,
                                    "relevance": relevance_score,
                                    "source": page.get("title", "Source inconnue"),
                                    "url": page.get("url", ""),
                                }
                            )

        # Trier par pertinence
        candidates.sort(key=lambda x: x["relevance"], reverse=True)
        return candidates[:20]

    def _extract_factual_answer(
        self, query: str, candidates: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Extrait une réponse factuelle (nombre, mesure, etc.)"""
        query_lower = query.lower()

        # Patterns spécifiques selon le type de fait recherché
        if "taille" in query_lower or "hauteur" in query_lower:
            pattern = r"([\d,]+\.?\d*)\s*(mètres?|m|km|centimètres?|cm)"
        elif "population" in query_lower or "habitant" in query_lower:
            pattern = r"([\d\s,]+\.?\d*)\s*(?:habitants?|personnes?)"
        elif "prix" in query_lower or "coût" in query_lower:
            pattern = r"([\d,]+\.?\d*)\s*(euros?|dollars?|\$|€)"
        else:
            pattern = r"([\d,]+\.?\d*)"

        # Rechercher dans les candidates
        answer_counts = Counter()

        for candidate in candidates:
            sentence = candidate["sentence"]
            matches = re.findall(pattern, sentence, re.IGNORECASE)

            for match in matches:
                if isinstance(match, tuple):
                    answer_key = (
                        f"{match[0]} {match[1]}" if len(match) > 1 else match[0]
                    )
                else:
                    answer_key = match

                answer_counts[answer_key] += candidate["relevance"]

        if answer_counts:
            # Prendre la réponse la plus consensuelle
            best_answer = answer_counts.most_common(1)[0][0]

            # Trouver la phrase complète contenant cette réponse
            for candidate in candidates:
                if best_answer.split()[0] in candidate["sentence"]:
                    # Nettoyer et formater la phrase
                    cleaned_sentence = self._universal_word_spacing_fix(
                        candidate["sentence"]
                    )
                    return cleaned_sentence.strip()

        return None

    def _extract_measurement_answer(
        self, candidates: List[Dict[str, Any]], query: str = ""
    ) -> Optional[str]:
        """Extrait une réponse de mesure spécifique avec validation multi-sources"""
        measurement_patterns = [
            # Patterns existants
            r"(?:mesure|fait|taille|hauteur)(?:\s+de)?\s+([\d,\s]+\.?\d*)\s*(mètres?|m\b|km|centimètres?|cm)",
            r"([\d,\s]+\.?\d*)\s*(mètres?|m\b|km|centimètres?|cm)(?:\s+de|d')?\s+(?:haut|hauteur|taille)",
            r"(?:s'élève à|atteint|culmine)\s+([\d,\s]+\.?\d*)\s*(mètres?|m\b|km)",
            # NOUVEAUX patterns plus agressifs
            r"([\d,\s]+\.?\d*)\s*(?:m\b|mètres?)\s+(?:de haut|d'altitude|au-dessus)",
            r"(?:environ|plus de|près de|quelque)\s+([\d,\s]+\.?\d*)\s*(mètres?|m\b)",
            r"\b(\d{2,4})\s*(?:m\b|mètres?)\b",  # Capture simple comme "828 m"
        ]

        # Extraire les mots-clés de l'entité recherchée depuis la query
        entity_keywords = set()
        for word in query.split():
            clean_word = word.strip('?.,!;:').lower()
            if len(clean_word) >= 4 and clean_word not in ['quel', 'quelle', 'comment', 'taille', 'hauteur', 'fait', 'mesure', 'what', 'which', 'height', 'size']:
                entity_keywords.add(clean_word)

        print(f"🔑 [MEASUREMENT] Mots-clés de l'entité: {entity_keywords}")

        # Collecter toutes les mesures avec leurs sources
        measurements_with_sources = []

        for candidate in candidates:
            sentence = candidate["sentence"]
            source = candidate.get("source", "Source inconnue")

            for pattern in measurement_patterns:
                # Utiliser finditer pour avoir la position de chaque match
                for match_obj in re.finditer(pattern, sentence, re.IGNORECASE):
                    match = match_obj.groups()
                    match_position = match_obj.start()

                    # Gérer à la fois les tuples et les strings simples
                    if isinstance(match, tuple):
                        if len(match) == 2 and match[1]:  # (nombre, unité)
                            value_str = match[0]
                            unit_str = match[1]
                        elif len(match) == 1:  # (nombre,) sans unité
                            value_str = match[0]
                            unit_str = "m"  # Défaut
                        else:
                            continue
                    else:
                        # Match simple (string)
                        value_str = match
                        unit_str = "m"

                    # Normaliser la valeur en nombre
                    value_str_clean = value_str.replace(',', '.').replace(' ', '').strip()

                    try:
                        value_num = float(value_str_clean)
                        # Filtrer les valeurs aberrantes (trop petites ou trop grandes)
                        if value_num < 10 or value_num > 10000:
                            continue

                        unit = unit_str.lower()

                        # NOUVEAU : Vérifier l'entité dans le CONTEXTE LOCAL de la mesure (pas toute la phrase)
                        entity_match_score = 0

                        if entity_keywords:
                            # Extraire un contexte de ~15 mots AVANT et 5 mots APRÈS la mesure
                            # Plus de mots avant car l'entité est généralement avant la mesure
                            words = sentence.split()

                            # Trouver la position du mot dans la liste de mots
                            char_count = 0
                            word_position = 0
                            for i, word in enumerate(words):
                                if char_count >= match_position:
                                    word_position = i
                                    break
                                char_count += len(word) + 1  # +1 pour l'espace

                            # Extraire SEULEMENT le contexte AVANT la mesure (plus important)
                            # et un petit contexte APRÈS (pour capturer l'unité et contexte immédiat)
                            context_before_start = max(0, word_position - 15)
                            context_before_words = words[context_before_start:word_position]

                            context_after_words = words[word_position:min(len(words), word_position + 5)]

                            # Vérifier l'entité PRIORITAIREMENT dans le contexte AVANT
                            context_before_set = set(word.lower().strip(string.punctuation) for word in context_before_words)
                            entity_in_before = len(entity_keywords.intersection(context_before_set))

                            # RÈGLE STRICTE : L'entité DOIT être COMPLÈTEMENT AVANT la mesure
                            # Si l'entité est après ou partiellement après, c'est une autre mesure dans une liste
                            if entity_in_before >= len(entity_keywords):
                                # ✅ Toute l'entité est AVANT la mesure → ACCEPTÉ
                                entity_match_score = entity_in_before
                            else:
                                # ❌ L'entité n'est pas complète avant → REJETÉ
                                # Même si elle est après, c'est probablement une autre mesure dans une liste
                                entity_match_score = 0

                            context = ' '.join(context_before_words + context_after_words).lower()

                            if entity_match_score > 0:
                                print(f"  ✅ [LOCAL] Mesure {value_num} {unit} avec entité dans contexte: '{context[:80]}...'")
                            else:
                                print(f"  ❌ [LOCAL] Mesure {value_num} {unit} SANS entité dans contexte: '{context[:80]}...'")

                        # Score de pertinence total = pertinence candidate + bonus entité
                        total_relevance = candidate["relevance"] + (entity_match_score * 10)

                        measurements_with_sources.append({
                            'value': value_num,
                            'unit': unit,
                            'value_str': f"{value_str} {unit_str}",
                            'source': source,
                            'sentence': sentence,
                            'relevance': candidate["relevance"],
                            'entity_relevance': entity_match_score,
                            'total_relevance': total_relevance
                        })
                    except (ValueError, IndexError):
                        continue

        if not measurements_with_sources:
            return None

        print(f"📊 [MULTI-SOURCE] {len(measurements_with_sources)} mesures trouvées")

        # Afficher toutes les valeurs trouvées pour debug avec leur pertinence entité
        for m in measurements_with_sources:
            entity_indicator = f" 🎯x{m['entity_relevance']}" if m['entity_relevance'] > 0 else ""
            print(f"  📍 {m['value']} {m['unit']}{entity_indicator} (source: {m['source']})")

        # FILTRER d'abord par pertinence à l'entité si on a des mots-clés
        if entity_keywords:
            # Séparer les mesures avec et sans match d'entité
            entity_matches = [m for m in measurements_with_sources if m['entity_relevance'] > 0]
            non_entity_matches = [m for m in measurements_with_sources if m['entity_relevance'] == 0]

            if entity_matches:
                print(f"🎯 [FILTER] {len(entity_matches)} mesures correspondent à l'entité '{entity_keywords}'")
                print(f"  ⚠️ {len(non_entity_matches)} mesures d'autres entités ignorées")
                # Utiliser SEULEMENT les mesures qui mentionnent l'entité recherchée
                measurements_with_sources = entity_matches
            else:
                print("⚠️ [FILTER] Aucune mesure avec l'entité recherchée, utilisation de toutes les mesures")

        # Validation multi-sources et détection d'outliers
        validated_measurement = self._validate_measurements_consensus(measurements_with_sources, query)

        if validated_measurement:
            return validated_measurement

        # Fallback sur l'ancienne méthode si pas assez de données
        measurements = Counter()
        source_sentences = {}

        for m in measurements_with_sources:
            measurement_key = m['value_str']
            measurements[measurement_key] += m['relevance']
            if measurement_key not in source_sentences:
                source_sentences[measurement_key] = m['sentence']

        if measurements:
            best_measurement = measurements.most_common(1)[0][0]
            cleaned_sentence = self._universal_word_spacing_fix(
                source_sentences[best_measurement]
            )
            return cleaned_sentence.strip()

        return None

    def _validate_measurements_consensus(
        self, measurements: List[Dict[str, Any]], query: str = ""
    ) -> Optional[str]:
        """
        Valide les mesures en croisant plusieurs sources et détecte les outliers

        Args:
            measurements: Liste de dictionnaires avec 'value', 'unit', 'source', 'sentence'
            query: La requête originale de l'utilisateur pour extraire l'entité

        Returns:
            str: Phrase avec la mesure consensuelle et les sources, ou None
        """
        if len(measurements) < 2:
            # Pas assez de sources pour validation
            return None

        print("🔍 [CONSENSUS] Validation multi-sources en cours...")

        # Normaliser toutes les valeurs dans la même unité (mètres)
        normalized_measurements = []
        for m in measurements:
            value = m['value']
            unit = m['unit']

            # Convertir en mètres
            if 'km' in unit or 'kilo' in unit:
                value = value * 1000
            elif 'cm' in unit or 'centi' in unit:
                value = value / 100

            normalized_measurements.append({
                **m,
                'normalized_value': value
            })

        # Extraire les valeurs normalisées
        values = [m['normalized_value'] for m in normalized_measurements]

        # Calculer les statistiques
        mean_value = statistics.mean(values)

        if len(values) >= 3:
            median_value = statistics.median(values)
            # Calculer l'écart-type pour détecter les outliers
            std_dev = statistics.stdev(values) if len(values) > 1 else 0
        else:
            median_value = mean_value
            std_dev = 0

        print(f"  📊 Moyenne: {mean_value:.1f}m, Médiane: {median_value:.1f}m, Écart-type: {std_dev:.1f}m")

        # Détection des outliers (valeurs à plus de 2 écart-types)
        inliers = []
        outliers = []

        for m in normalized_measurements:
            if std_dev == 0 or abs(m['normalized_value'] - mean_value) <= 2 * std_dev:
                inliers.append(m)
            else:
                outliers.append(m)
                print(f"  ⚠️ Outlier détecté: {m['value']} {m['unit']} de {m['source']} (trop éloigné du consensus)")

        # Si on a au moins 2 sources qui concordent, utiliser le consensus
        if len(inliers) >= 2:
            # Prendre la médiane des valeurs fiables
            consensus_value = statistics.median([m['normalized_value'] for m in inliers])

            # Trouver la mesure la plus proche du consensus
            closest_measurement = min(
                inliers,
                key=lambda m: abs(m['normalized_value'] - consensus_value)
            )

            # Compter les sources qui confirment (valeurs similaires à ±5%)
            tolerance = consensus_value * 0.05
            confirming_sources = [
                m for m in inliers
                if abs(m['normalized_value'] - consensus_value) <= tolerance
            ]

            num_confirming = len(set(m['source'] for m in confirming_sources))

            print(f"  ✅ Consensus trouvé: {consensus_value:.0f}m ({num_confirming} sources concordantes)")

            # NOUVELLE APPROCHE : Générer une réponse SIMPLE et DIRECTE
            # Au lieu d'extraire de phrases complexes, construire la réponse nous-mêmes

            # STRATÉGIE PRIORITAIRE : Extraire l'entité depuis la REQUÊTE utilisateur
            entity_name = None

            if query:
                # Extraire les mots significatifs (>= 4 lettres, pas de mots-questions)
                query_words = query.split()
                entity_words = []
                stop_words = {'quel', 'quelle', 'comment', 'taille', 'hauteur', 'fait', 'mesure', 'what', 'which', 'height', 'size', 'est', 'la', 'le', 'du', 'de', 'des'}

                for word in query_words:
                    clean_word = word.strip('?.,!;:').lower()
                    if len(clean_word) >= 4 and clean_word not in stop_words:
                        entity_words.append(word.strip('?.,!;:'))

                # Si on a au moins 2 mots, les combiner
                if len(entity_words) >= 2:
                    entity_name = ' '.join(entity_words[:2])  # Prendre les 2 premiers
                    # Capitaliser correctement (première lettre de chaque mot en majuscule)
                    entity_name = ' '.join(w.capitalize() for w in entity_name.split())
                    print(f"  🎯 [ENTITY] Nom extrait de la REQUÊTE: '{entity_name}'")

            # Stratégie 2 : Chercher dans les sources Wikipedia
            if not entity_name:
                for m in inliers:
                    source = m.get('source', '')
                    # Nettoyer le nom de la source
                    clean_source = source.replace('(Article direct)', '').replace('Wikipedia FR', '').replace('Wikipedia EN', '').strip()

                    # Vérifier si c'est une page spécifique (pas une liste générique)
                    if clean_source and clean_source not in ['Structure', 'Source inconnue', 'Liste des plus hautes structures du monde', 'Listes des plus hautes constructions du monde', 'Ordres de grandeur de longueur', 'Chronologie des plus hautes structures du monde']:
                        entity_name = clean_source
                        print(f"  🎯 [ENTITY] Nom trouvé depuis source: '{entity_name}'")
                        break

            # Stratégie 3 : Extraire depuis la phrase
            if not entity_name:
                sentence = closest_measurement['sentence']

                # Chercher un pattern comme "Burj Khalifa" ou "le/la Nom"
                name_patterns = [
                    r'([A-Z][a-zA-Z\s]+?)\s+\(',  # Nom avant une parenthèse
                    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b',  # Nom propre (mots en majuscule)
                ]

                for pattern in name_patterns:
                    match = re.search(pattern, sentence)
                    if match:
                        potential_name = match.group(1).strip()
                        # Vérifier que ce n'est pas un mot commun
                        if potential_name not in ['La', 'Le', 'Un', 'Une', 'De', 'Du', 'Des', 'Il', 'Elle']:
                            entity_name = potential_name
                            print(f"  🎯 [ENTITY] Nom extrait de la phrase: '{entity_name}'")
                            break

            # Stratégie 4 : Fallback générique
            if not entity_name:
                entity_name = "structure"
                print("  ⚠️ [ENTITY] Nom générique utilisé")

            # Construire la réponse simple et directe
            # Adapter l'article selon le genre (si commence par voyelle, utiliser "l'")
            if entity_name[0].lower() in 'aeiouhéèê':
                article = "L'"
                simple_answer = f"{article}{entity_name} mesure **{int(consensus_value)} mètres** de hauteur."
            else:
                # Détecter si c'est masculin ou féminin (par défaut masculin)
                if entity_name.lower().startswith(('tour', 'flèche', 'antenne', 'structure')):
                    article = "La"
                else:
                    article = "Le"
                simple_answer = f"{article} {entity_name} mesure **{int(consensus_value)} mètres** de hauteur."

            print(f"  📝 [SIMPLE] Réponse générée: {simple_answer}")

            # Ajouter l'information de validation si pertinent
            if num_confirming >= 3:
                validation_note = f" (✅ Confirmé par {num_confirming} sources indépendantes)"
                simple_answer += validation_note

            return simple_answer.strip()

        # Pas de consensus clair
        print(f"  ⚠️ Pas de consensus clair ({len(inliers)} sources fiables sur {len(measurements)})")
        return None

    def _extract_definition_answer(
        self, candidates: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Extrait une définition"""
        definition_patterns = [
            r"(?:est|sont)\s+([^.!?]{20,150})",
            r"(?:c'est|ce sont)\s+([^.!?]{20,150})",
            r"([^.!?]{20,150})(?:\s+est|\s+sont)",
        ]

        definitions = Counter()
        source_sentences = {}

        for candidate in candidates:
            sentence = candidate["sentence"]
            for pattern in definition_patterns:
                matches = re.findall(pattern, sentence, re.IGNORECASE)
                for match in matches:
                    clean_match = match.strip()
                    if len(clean_match) > 15:
                        definitions[clean_match] += candidate["relevance"]
                        if clean_match not in source_sentences:
                            source_sentences[clean_match] = sentence

        if definitions:
            best_definition = definitions.most_common(1)[0][0]
            cleaned_sentence = self._universal_word_spacing_fix(
                source_sentences[best_definition]
            )
            return cleaned_sentence.strip()

        return None

    def _extract_date_answer(
        self, candidates: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Extrait une réponse de date"""
        date_patterns = [
            r"(?:en|depuis|dans|créé|fondé|construit|né|inauguré)\s+(\d{4})",
            r"(\d{1,2})\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})",
            r"(\d{4})(?:\s*-\s*\d{4})?",
        ]

        dates = Counter()
        source_sentences = {}

        for candidate in candidates:
            sentence = candidate["sentence"]
            for pattern in date_patterns:
                matches = re.findall(pattern, sentence, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        date_key = " ".join(str(m) for m in match if m)
                    else:
                        date_key = str(match)

                    dates[date_key] += candidate["relevance"]
                    if date_key not in source_sentences:
                        source_sentences[date_key] = sentence

        if dates:
            best_date = dates.most_common(1)[0][0]
            cleaned_sentence = self._universal_word_spacing_fix(
                source_sentences[best_date]
            )
            return cleaned_sentence.strip()

        return None

    def _extract_general_answer(
        self, query: str, candidates: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Extrait une réponse générale basée sur le consensus"""
        if not candidates:
            return None

        # Analyser les mots-clés de la question
        query_words = set(
            word.lower().strip(string.punctuation)
            for word in query.split()
            if len(word) > 2
        )

        # Calculer un score de consensus pour chaque phrase
        sentence_scores = {}

        for candidate in candidates:
            sentence = candidate["sentence"]

            # Score basé sur la pertinence originale
            score = candidate["relevance"]

            # Bonus pour les phrases contenant plusieurs mots-clés de la question
            sentence_words = set(
                word.lower().strip(string.punctuation) for word in sentence.split()
            )
            keyword_overlap = len(query_words.intersection(sentence_words))
            score += keyword_overlap * 2

            # Bonus pour les phrases avec des informations précises (nombres, dates, etc.)
            if re.search(r"\d+", sentence):
                score += 3

            # Bonus pour les phrases qui semblent être des réponses directes
            if any(
                sentence.lower().startswith(start)
                for start in [
                    "la",
                    "le",
                    "il",
                    "elle",
                    "c'est",
                    "ce sont",
                    "on trouve",
                    "située",
                    "situé",
                ]
            ):
                score += 2

            sentence_scores[sentence] = score

        # Prendre la phrase avec le meilleur score
        if sentence_scores:
            best_sentence = max(sentence_scores, key=sentence_scores.get)
            cleaned_sentence = self._universal_word_spacing_fix(best_sentence)
            return cleaned_sentence.strip()

        return None

    def _generate_answer_focused_summary(
        self,
        query: str,
        direct_answer: Optional[str],
        page_contents: List[Dict[str, Any]],
    ) -> str:
        """Génère un résumé centré sur la réponse directe - VERSION CORRIGÉE"""
        summary = ""

        if direct_answer:
            # Appliquer TOUTES les corrections dans l'ordre
            cleaned_answer = self._universal_word_spacing_fix(direct_answer)
            enhanced_answer = self._intelligent_bold_formatting(cleaned_answer)
            summary += f"{enhanced_answer}\n\n"
        else:
            key_info = self._extract_concentrated_summary(query, page_contents)
            cleaned_info = self._universal_word_spacing_fix(key_info)
            enhanced_info = self._intelligent_bold_formatting(cleaned_info)
            summary += f"📍 **Information trouvée :**\n{enhanced_info}\n\n"

        # Format horizontal pour les sources
        summary += "🔗 **Sources** : "

        source_links = []
        for result in page_contents[:3]:
            if result.get("title") and result.get("url"):
                title = self._clean_title(result["title"])
                clean_title = self._universal_word_spacing_fix(title)
                url = result.get("url")

                if url and url.startswith("http"):
                    source_links.append(f"[{clean_title}]({url})")
                else:
                    source_links.append(f"[{clean_title}]")

        if source_links:
            summary += ", ".join(source_links) + "\n"
        else:
            summary += "Aucune source disponible\n"

        print(f"[DEBUG] Résumé généré avec {len(source_links)} liens:")
        print(f"[DEBUG] Résumé complet:\n{summary[:500]}")

        return summary

    def _enhance_answer_formatting(self, text: str) -> str:
        """Améliore le formatage de la réponse"""
        if not text:
            return text

        # 1. CORRECTION UNIVERSELLE DES ESPACEMENTS
        cleaned_text = self._universal_word_spacing_fix(text)

        # 2. FORMATAGE INTELLIGENT DES MOTS IMPORTANTS
        formatted_text = self._intelligent_bold_formatting(cleaned_text)

        return formatted_text

    def _intelligent_bold_formatting(self, text: str) -> str:
        """Formatage intelligent en gras"""

        if not text:
            return text

        # 1. CHIFFRES + UNITÉS
        text = re.sub(
            r"\b(\d+(?:[,.\s]\d+)?)\s*(mètres?|kilomètres?|centimètres?|m|km|cm)(?!\w)",
            r"**\1 \2**",
            text,
            flags=re.IGNORECASE,
        )

        # Poids
        text = re.sub(
            r"\b(\d+(?:[,.\s]\d+)?)\s*(kilogrammes?|tonnes?|grammes?|kg|g)(?!\w)",
            r"**\1 \2**",
            text,
            flags=re.IGNORECASE,
        )

        # Monnaie
        text = re.sub(
            r"\b(\d+(?:[,.\s]\d+)?)\s*(euros?|dollars?|\$|€)(?!\w)",
            r"**\1 \2**",
            text,
            flags=re.IGNORECASE,
        )

        # 2. DATES
        text = re.sub(r"\b(\d{4})\b", r"**\1**", text)

        # 3. Noms propres importants
        important_names = [r"\bTour\s+Eiffel\b", r"\bNotre[-\s]Dame\b", r"\bLouvre\b"]

        for pattern in important_names:
            text = re.sub(
                pattern, lambda m: f"**{m.group(0)}**", text, flags=re.IGNORECASE
            )

        # 4. Nettoyer le formatage
        text = re.sub(r"\*{3,}", "**", text)
        text = re.sub(r"\*\*\s*\*\*", "", text)

        return text

    def _universal_word_spacing_fix(self, text: str) -> str:
        """Correction AMÉLIORÉE qui ne casse pas les mots valides"""

        if not text:
            return text

        # Étape 1: Séparer SEULEMENT les mots vraiment collés (minuscule + majuscule)
        text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

        # Étape 2: Séparer les chiffres des lettres
        text = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", text)
        text = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", text)

        # Étape 3: CORRECTION - Seulement les cas évidents de mots collés
        # Ne pas toucher aux mots valides comme "mesure", "actuellement", etc.

        # Liste RESTREINTE aux vrais cas de mots collés courants
        obvious_splits = [
            # Cas très évidents uniquement
            (r"\b(la|le|les)(tour|ville|monde|france|paris)\b", r"\1 \2"),
            (r"\b(tour|ville)(eiffel|paris|france)\b", r"\1 \2"),
            (r"\b(de|du|des)(la|le|les)\b", r"\1 \2"),
            # Prépositions collées évidentes
            (r"\b(dans|sur|pour|avec|sans)(le|la|les|un|une)\b", r"\1 \2"),
        ]

        # Appliquer SEULEMENT les cas évidents
        for pattern, replacement in obvious_splits:
            old_text = text
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            if text != old_text:
                print(f"[DEBUG] Appliqué: {pattern} -> changé en: {repr(text)}")

        # Étape 4: Nettoyer les espaces
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s+([.!?:;,])", r"\1", text)
        text = re.sub(r"([.!?:;,])([a-zA-Z])", r"\1 \2", text)

        result = text.strip()
        return result

    def _clean_title(self, title: str) -> str:
        """Nettoie le titre et s'assure qu'il n'est pas None"""
        if not title:
            return "Source"

        cleaned = str(title)  # Conversion sécurisée en string

        # CORRECTION : Remplacer les caractères problématiques pour les liens
        cleaned = cleaned.replace(":", " -")

        # Remplacer d'autres caractères potentiellement problématiques
        cleaned = cleaned.replace("|", "-")
        cleaned = cleaned.replace("[", "(").replace("]", ")")

        # Supprimer les parties indésirables
        cleaned = re.sub(r"\s*[\[\(].*?[\]\)]\s*$", "", cleaned)
        cleaned = re.sub(r"\s*[-|—]\s*[^-]+$", "", cleaned)

        # Limiter la longueur
        if len(cleaned) > 60:
            cleaned = cleaned[:57] + "..."

        # Appliquer la correction d'espacement
        cleaned = self._universal_word_spacing_fix(cleaned)

        return cleaned.strip() if cleaned.strip() else "Source"

    def _extract_concentrated_summary(
        self, query: str, page_contents: List[Dict[str, Any]]
    ) -> str:
        """Extrait un résumé concentré quand pas de réponse directe"""
        # Combiner tous les snippets
        all_snippets = []
        for content in page_contents:
            snippet = content.get("snippet", "")
            if snippet:
                # Nettoyer le snippet avec la correction universelle
                cleaned_snippet = self._universal_word_spacing_fix(snippet)
                all_snippets.append(cleaned_snippet)

        combined_text = " ".join(all_snippets)

        # Extraire les phrases les plus pertinentes
        sentences = re.split(r"[.!?]+", combined_text)
        query_words = set(word.lower() for word in query.split() if len(word) > 2)

        scored_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:
                sentence_words = set(word.lower() for word in sentence.split())
                score = len(query_words.intersection(sentence_words))
                if score > 0:
                    # Nettoyer la phrase avec la correction universelle
                    cleaned_sentence = self._universal_word_spacing_fix(sentence)
                    scored_sentences.append((cleaned_sentence, score))

        # Prendre la meilleure phrase
        scored_sentences.sort(key=lambda x: x[1], reverse=True)

        if scored_sentences:
            return scored_sentences[0][0]

        return "Information trouvée mais nécessite une recherche plus spécifique."

    def _perform_search(self, query: str) -> List[Dict[str, Any]]:
        """Effectue la recherche sur internet"""
        search_methods = [
            self._search_duckduckgo_instant,
            self._search_with_requests,
            self._search_fallback,
        ]

        for method in search_methods:
            try:
                results = method(query)
                if results:
                    print(f"✅ {len(results)} résultats trouvés avec {method.__name__}")
                    return results
            except Exception as e:
                print(f"⚠️ {method.__name__} a échoué: {str(e)}")
                continue

        return []

    def _search_duckduckgo_instant(self, query: str) -> List[Dict[str, Any]]:
        """Recherche via l'API instant de DuckDuckGo"""
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_redirect": "1",
            "no_html": "1",
            "skip_disambig": "1",
        }

        headers = {"User-Agent": self.user_agent}

        response = requests.get(
            url, params=params, headers=headers, timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        results = []

        # Résultat instant
        if data.get("Abstract"):
            results.append(
                {
                    "title": data.get("Heading", "Information"),
                    "snippet": data.get("Abstract", ""),
                    "url": data.get("AbstractURL", ""),
                    "source": "DuckDuckGo Instant",
                }
            )

        # Résultats de topics
        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(
                    {
                        "title": topic.get("FirstURL", "")
                        .split("/")[-1]
                        .replace("_", " ")
                        .title(),
                        "snippet": topic.get("Text", ""),
                        "url": topic.get("FirstURL", ""),
                        "source": "DuckDuckGo",
                    }
                )

        return results[: self.max_results]

    def _search_with_requests(self, query: str) -> List[Dict[str, Any]]:
        """Recherche en scrapant les résultats DuckDuckGo HTML - VERSION AMÉLIORÉE"""
        # Essayer d'abord DuckDuckGo Lite (plus simple à scraper)
        try:
            results = self._search_duckduckgo_lite(query)
            if results:
                return results
        except Exception as e:
            print(f"⚠️ DuckDuckGo Lite a échoué: {str(e)}")

        # Fallback vers DuckDuckGo HTML classique
        search_url = f"https://html.duckduckgo.com/html/?q={quote(query)}"

        # Utiliser un user-agent rotatif
        current_ua = self._get_next_user_agent()

        headers = {
            "User-Agent": current_ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }

        # Ajouter un petit délai pour éviter le rate limiting
        time.sleep(0.5)

        response = requests.get(search_url, headers=headers, timeout=self.timeout, allow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        results = []

        # Essayer plusieurs sélecteurs CSS pour plus de robustesse
        result_selectors = [
            ("div", {"class": "result"}),
            ("div", {"class": "results_links"}),
            ("div", {"class": "web-result"}),
            ("div", {"id": lambda x: x and x.startswith("r1-")}),
        ]

        for selector_tag, selector_attrs in result_selectors:
            result_divs = soup.find_all(selector_tag, selector_attrs, limit=self.max_results)
            if result_divs:
                break

        for result_div in result_divs:
            try:
                # Essayer différents sélecteurs pour le titre
                title_elem = (
                    result_div.find("a", class_="result__a")
                    or result_div.find("a", class_="result-link")
                    or result_div.find("h2").find("a") if result_div.find("h2") else None
                )

                # Essayer différents sélecteurs pour le snippet
                snippet_elem = (
                    result_div.find("a", class_="result__snippet")
                    or result_div.find("div", class_="result__snippet")
                    or result_div.find("span", class_="result-snippet")
                    or result_div.find("div", class_="snippet")
                )

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")

                    # Le snippet peut être dans plusieurs endroits
                    if snippet_elem:
                        snippet = snippet_elem.get_text(strip=True)
                    else:
                        # Fallback: prendre tout le texte du div
                        snippet = result_div.get_text(strip=True)[:200]

                    if title and snippet and len(snippet) > 20:
                        results.append(
                            {
                                "title": title,
                                "snippet": snippet,
                                "url": url,
                                "source": "DuckDuckGo",
                            }
                        )
            except Exception as e:
                print(f"⚠️ Erreur lors du parsing d'un résultat: {str(e)}")
                continue

        return results[:self.max_results]

    def _search_duckduckgo_lite(self, query: str) -> List[Dict[str, Any]]:
        """Recherche via DuckDuckGo Lite (version simplifiée et plus stable)"""
        search_url = f"https://lite.duckduckgo.com/lite/?q={quote(query)}"

        current_ua = self._get_next_user_agent()

        headers = {
            "User-Agent": current_ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        response = requests.get(search_url, headers=headers, timeout=self.timeout, allow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        results = []

        # DuckDuckGo Lite utilise une structure de table simple
        result_tables = soup.find_all("table", class_="result-table")

        for table in result_tables[:self.max_results]:
            try:
                # Le titre est dans un lien avec class="result-link"
                title_elem = table.find("a", class_="result-link")

                # Le snippet est dans un td avec class="result-snippet"
                snippet_elem = table.find("td", class_="result-snippet")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")

                    if snippet_elem:
                        snippet = snippet_elem.get_text(strip=True)
                    else:
                        snippet = ""

                    if title and len(title) > 3:
                        results.append(
                            {
                                "title": title,
                                "snippet": snippet if snippet else title,
                                "url": url,
                                "source": "DuckDuckGo Lite",
                            }
                        )
            except Exception as e:
                print(f"⚠️ Erreur lors du parsing DuckDuckGo Lite: {str(e)}")
                continue

        print(f"✅ DuckDuckGo Lite: {len(results)} résultats trouvés")
        return results[:self.max_results]

    def _search_fallback(self, query: str) -> List[Dict[str, Any]]:
        """Méthode de recherche de secours - UTILISE WIKIPEDIA"""
        print("🔄 Tentative de recherche de secours avec Wikipedia...")

        try:
            # Essayer d'abord Wikipedia français
            results = self._search_wikipedia_fr(query)
            if results:
                print(f"✅ {len(results)} résultats trouvés via Wikipedia FR")
                return results

        except Exception as e:
            print(f"⚠️ Recherche Wikipedia FR a échoué: {str(e)}")

        try:
            # Fallback vers Wikipedia anglais
            results = self._search_wikipedia_en(query)
            if results:
                print(f"✅ {len(results)} résultats trouvés via Wikipedia EN")
                return results

        except Exception as e:
            print(f"⚠️ Recherche Wikipedia EN a échoué: {str(e)}")

        # Si tout échoue, retourner un message informatif
        return [
            {
                "title": f"Recherche sur '{query}'",
                "snippet": f"Je n'ai pas pu accéder aux moteurs de recherche pour '{query}'. Vérifiez votre connexion internet ou reformulez votre question.",
                "url": "",
                "source": "Système local",
            }
        ]

    def _search_wikipedia_fr(self, query: str) -> List[Dict[str, Any]]:
        """Recherche sur Wikipedia français avec CONTENU COMPLET et correction orthographique"""
        try:
            # Utiliser l'API Wikipedia
            api_url = "https://fr.wikipedia.org/w/api.php"

            # Étape 0: Demander une suggestion orthographique à Wikipedia
            suggestion_params = {
                "action": "opensearch",
                "search": query,
                "limit": 1,
                "format": "json",
            }

            headers = {"User-Agent": self.user_agent}

            print(f"🔍 Recherche de suggestion pour: '{query}'")

            suggestion_response = requests.get(api_url, params=suggestion_params, headers=headers, timeout=10)
            suggestion_response.raise_for_status()
            suggestion_data = suggestion_response.json()

            # La réponse est [query, [suggestions], [descriptions], [urls]]
            suggested_query = query
            if len(suggestion_data) > 1 and suggestion_data[1]:
                suggested_query = suggestion_data[1][0]  # Première suggestion
                if suggested_query.lower() != query.lower():
                    print(f"✏️ Wikipedia suggère: '{query}' → '{suggested_query}'")

            # Étape 1: Rechercher les pages pertinentes avec la suggestion
            # Détecter les noms propres (mots significatifs en majuscules OU mots de >=4 lettres dans question)
            potential_names = []
            for word in query.split():
                clean_word = word.strip('?.,!;:')
                # Majuscule OU mot long dans question de type "burj khalifa"
                if len(clean_word) >= 4 and clean_word.lower() not in ['quel', 'quelle', 'comment', 'taille', 'hauteur', 'fait', 'mesure']:
                    potential_names.append(clean_word)

            has_proper_noun = len(potential_names) >= 2  # Au moins 2 mots significatifs (ex: "burj khalifa")
            search_limit = 5 if has_proper_noun else 3

            if has_proper_noun:
                direct_search_term = ' '.join(potential_names)
                print(f"🎯 Entité détectée: '{direct_search_term}', recherche élargie à {search_limit} pages + recherche directe")

            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": suggested_query,
                "format": "json",
                "srlimit": search_limit,  # Ajusté dynamiquement
            }

            print(f"🌐 Requête Wikipedia FR avec: '{suggested_query}'")

            # Initialiser la liste des résultats
            results = []

            # NOUVELLE ÉTAPE 1.5: Si entité détectée, chercher DIRECTEMENT l'article spécifique
            if has_proper_noun:
                direct_article_title = direct_search_term.title()  # "burj khalifa" → "Burj Khalifa"
                print(f"🎯 Tentative de récupération directe de l'article: '{direct_article_title}'")

                # D'abord, chercher une suggestion de Wikipedia si l'orthographe est incorrecte
                article_title_to_fetch = direct_article_title

                try:
                    # Utiliser l'API opensearch pour obtenir des suggestions
                    opensearch_params = {
                        "action": "opensearch",
                        "search": direct_search_term,
                        "limit": 5,
                        "namespace": 0,
                        "format": "json"
                    }

                    opensearch_response = requests.get(api_url, params=opensearch_params, headers=headers, timeout=10)
                    opensearch_response.raise_for_status()
                    opensearch_data = opensearch_response.json()

                    # Format de la réponse: [query, [titles], [descriptions], [urls]]
                    if len(opensearch_data) > 1 and opensearch_data[1]:
                        suggestions = opensearch_data[1]
                        if suggestions:
                            # Calculer la similarité avec fuzzy matching
                            best_match = None
                            best_score = 0

                            for suggestion in suggestions:
                                score = fuzz.ratio(direct_search_term.lower(), suggestion.lower())
                                if score > best_score:
                                    best_score = score
                                    best_match = suggestion

                            # Si on a un bon match (score > 70), l'utiliser
                            if best_match and best_score > 70:
                                if best_match.lower() != direct_article_title.lower():
                                    print(f"📝 Correction orthographique: '{direct_article_title}' → '{best_match}' (score: {best_score})")
                                    article_title_to_fetch = best_match
                                else:
                                    print(f"✓ Orthographe correcte confirmée (score: {best_score})")
                except Exception as e:
                    print(f"⚠️ Suggestion orthographique échouée: {str(e)}")

                try:
                    direct_content_params = {
                        "action": "query",
                        "titles": article_title_to_fetch,
                        "prop": "extracts",
                        "exintro": False,
                        "explaintext": True,
                        "format": "json",
                    }

                    direct_response = requests.get(api_url, params=direct_content_params, headers=headers, timeout=10)
                    direct_response.raise_for_status()
                    direct_data = direct_response.json()

                    direct_pages = direct_data.get("query", {}).get("pages", {})
                    for page_id, page_data in direct_pages.items():
                        if page_id != "-1":  # -1 signifie page not found
                            extract = page_data.get("extract", "")
                            if extract and len(extract) > 100:
                                print(f"✅ Article direct trouvé: {len(extract)} caractères")
                                results.append({
                                    "title": page_data.get("title", article_title_to_fetch),
                                    "snippet": extract[:500],
                                    "full_content": extract,
                                    "url": f"https://fr.wikipedia.org/wiki/{quote(page_data.get('title', article_title_to_fetch))}",
                                    "source": "Wikipedia FR (Article direct)",
                                })
                                break
                except Exception as e:
                    print(f"⚠️ Recherche directe échouée: {str(e)}")

            response = requests.get(api_url, params=search_params, headers=headers, timeout=10)

            print(f"📡 Status code: {response.status_code}")

            response.raise_for_status()

            search_data = response.json()

            print(f"📊 Réponse JSON reçue: {len(str(search_data))} caractères")

            if "query" in search_data and "search" in search_data["query"]:
                print(f"🔍 Wikipedia FR: {len(search_data['query']['search'])} pages trouvées")

                # Étape 2: Pour chaque page trouvée, récupérer le contenu complet
                for item in search_data["query"]["search"]:
                    title = item.get("title", "")

                    if not title:
                        continue

                    print(f"📖 Récupération du contenu de: {title}")

                    try:
                        # Récupérer le contenu complet de la page (pas seulement l'intro)
                        content_params = {
                            "action": "query",
                            "titles": title,
                            "prop": "extracts",
                            "exintro": False,  # Récupérer l'article complet, pas juste l'intro
                            "explaintext": True,  # Texte brut sans HTML
                            "format": "json",
                            "exchars": 5000,  # Limiter à 5000 caractères pour performance
                        }

                        content_response = requests.get(api_url, params=content_params, headers=headers, timeout=10)
                        content_response.raise_for_status()
                        content_data = content_response.json()

                        # Extraire le contenu
                        pages = content_data.get("query", {}).get("pages", {})
                        for page_data in pages.values():
                            extract = page_data.get("extract", "")

                            if extract and len(extract) > 50:
                                print(f"✅ Contenu récupéré: {len(extract)} caractères")
                                results.append({
                                    "title": title,
                                    "snippet": extract[:500],  # Premier 500 caractères
                                    "full_content": extract,  # Contenu complet
                                    "url": f"https://fr.wikipedia.org/wiki/{quote(title)}",
                                    "source": "Wikipedia FR",
                                })
                                break  # Un seul résultat par page
                            else:
                                print(f"⚠️ Contenu vide ou trop court pour: {title}")

                    except Exception as e:
                        print(f"❌ Erreur lors de la récupération du contenu de '{title}': {str(e)}")
                        continue

            print(f"✅ Wikipedia FR: {len(results)} résultats avec contenu complet")
            return results[:self.max_results]

        except Exception as e:
            print(f"❌ Erreur globale Wikipedia FR: {str(e)}")
            traceback.print_exc()
            return []

    def _search_wikipedia_en(self, query: str) -> List[Dict[str, Any]]:
        """Recherche sur Wikipedia anglais avec CONTENU COMPLET et correction orthographique"""
        try:
            # Utiliser l'API Wikipedia
            api_url = "https://en.wikipedia.org/w/api.php"

            # Étape 0: Demander une suggestion orthographique à Wikipedia
            suggestion_params = {
                "action": "opensearch",
                "search": query,
                "limit": 1,
                "format": "json",
            }

            headers = {"User-Agent": self.user_agent}

            print(f"🔍 Recherche de suggestion pour: '{query}'")

            suggestion_response = requests.get(api_url, params=suggestion_params, headers=headers, timeout=10)
            suggestion_response.raise_for_status()
            suggestion_data = suggestion_response.json()

            # La réponse est [query, [suggestions], [descriptions], [urls]]
            suggested_query = query
            if len(suggestion_data) > 1 and suggestion_data[1]:
                suggested_query = suggestion_data[1][0]  # Première suggestion
                if suggested_query.lower() != query.lower():
                    print(f"✏️ Wikipedia suggère: '{query}' → '{suggested_query}'")

            # Étape 1: Rechercher les pages pertinentes avec la suggestion
            # Détecter les noms propres (mots significatifs en majuscules OU mots de >=4 lettres dans question)
            potential_names = []
            for word in query.split():
                clean_word = word.strip('?.,!;:')
                # Majuscule OU mot long dans question de type "burj khalifa"
                if len(clean_word) >= 4 and clean_word.lower() not in ['what', 'which', 'size', 'height', 'tall', 'quel', 'quelle', 'comment', 'taille', 'hauteur', 'fait', 'mesure']:
                    potential_names.append(clean_word)

            has_proper_noun = len(potential_names) >= 2  # Au moins 2 mots significatifs (ex: "burj khalifa")
            search_limit = 5 if has_proper_noun else 3

            if has_proper_noun:
                direct_search_term = ' '.join(potential_names)
                print(f"🎯 Entité détectée: '{direct_search_term}', recherche élargie à {search_limit} pages + recherche directe")

            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": suggested_query,
                "format": "json",
                "srlimit": search_limit,  # Ajusté dynamiquement
            }

            print(f"🌐 Requête Wikipedia EN avec: '{suggested_query}'")

            # Initialiser la liste des résultats
            results = []

            # NOUVELLE ÉTAPE 1.5: Si entité détectée, chercher DIRECTEMENT l'article spécifique
            if has_proper_noun:
                direct_article_title = direct_search_term.title()  # "burj khalifa" → "Burj Khalifa"
                print(f"🎯 Tentative de récupération directe de l'article EN: '{direct_article_title}'")

                # D'abord, chercher une suggestion de Wikipedia si l'orthographe est incorrecte
                article_title_to_fetch = direct_article_title

                try:
                    # Utiliser l'API opensearch pour obtenir des suggestions
                    opensearch_params = {
                        "action": "opensearch",
                        "search": direct_search_term,
                        "limit": 5,
                        "namespace": 0,
                        "format": "json"
                    }

                    opensearch_response = requests.get(api_url, params=opensearch_params, headers=headers, timeout=10)
                    opensearch_response.raise_for_status()
                    opensearch_data = opensearch_response.json()

                    # Format de la réponse: [query, [titles], [descriptions], [urls]]
                    if len(opensearch_data) > 1 and opensearch_data[1]:
                        suggestions = opensearch_data[1]
                        if suggestions:
                            # Calculer la similarité avec fuzzy matching
                            best_match = None
                            best_score = 0

                            for suggestion in suggestions:
                                score = fuzz.ratio(direct_search_term.lower(), suggestion.lower())
                                if score > best_score:
                                    best_score = score
                                    best_match = suggestion

                            # Si on a un bon match (score > 70), l'utiliser
                            if best_match and best_score > 70:
                                if best_match.lower() != direct_article_title.lower():
                                    print(f"📝 Correction orthographique EN: '{direct_article_title}' → '{best_match}' (score: {best_score})")
                                    article_title_to_fetch = best_match
                                else:
                                    print(f"✓ Orthographe correcte confirmée EN (score: {best_score})")
                except Exception as e:
                    print(f"⚠️ Suggestion orthographique EN échouée: {str(e)}")

                try:
                    direct_content_params = {
                        "action": "query",
                        "titles": article_title_to_fetch,
                        "prop": "extracts",
                        "exintro": False,
                        "explaintext": True,
                        "format": "json",
                    }

                    direct_response = requests.get(api_url, params=direct_content_params, headers=headers, timeout=10)
                    direct_response.raise_for_status()
                    direct_data = direct_response.json()

                    direct_pages = direct_data.get("query", {}).get("pages", {})
                    for page_id, page_data in direct_pages.items():
                        if page_id != "-1":  # -1 signifie page not found
                            extract = page_data.get("extract", "")
                            if extract and len(extract) > 100:
                                print(f"✅ Article direct EN trouvé: {len(extract)} caractères")
                                results.append({
                                    "title": page_data.get("title", article_title_to_fetch),
                                    "snippet": extract[:500],
                                    "full_content": extract,
                                    "url": f"https://en.wikipedia.org/wiki/{quote(page_data.get('title', article_title_to_fetch))}",
                                    "source": "Wikipedia EN (Article direct)",
                                })
                                break
                except Exception as e:
                    print(f"⚠️ Recherche directe EN échouée: {str(e)}")

            response = requests.get(api_url, params=search_params, headers=headers, timeout=10)

            print(f"📡 Status code: {response.status_code}")

            response.raise_for_status()

            search_data = response.json()

            print(f"📊 Réponse JSON reçue: {len(str(search_data))} caractères")

            results = []

            if "query" in search_data and "search" in search_data["query"]:
                print(f"🔍 Wikipedia EN: {len(search_data['query']['search'])} pages trouvées")

                # Étape 2: Pour chaque page trouvée, récupérer le contenu complet
                for item in search_data["query"]["search"]:
                    title = item.get("title", "")

                    if not title:
                        continue

                    print(f"📖 Récupération du contenu de: {title}")

                    try:
                        # Récupérer le contenu complet de la page (pas seulement l'intro)
                        content_params = {
                            "action": "query",
                            "titles": title,
                            "prop": "extracts",
                            "exintro": False,  # CHANGÉ: Récupérer l'article complet, pas juste l'intro
                            "explaintext": True,  # Texte brut sans HTML
                            "format": "json",
                            "exchars": 5000,  # Limiter à 5000 caractères pour performance
                        }

                        content_response = requests.get(api_url, params=content_params, headers=headers, timeout=10)
                        content_response.raise_for_status()
                        content_data = content_response.json()

                        # Extraire le contenu
                        pages = content_data.get("query", {}).get("pages", {})
                        for _, page_data in pages.items():
                            extract = page_data.get("extract", "")

                            if extract and len(extract) > 50:
                                print(f"✅ Contenu récupéré: {len(extract)} caractères")
                                results.append({
                                    "title": title,
                                    "snippet": extract[:500],  # Premier 500 caractères
                                    "full_content": extract,  # Contenu complet
                                    "url": f"https://en.wikipedia.org/wiki/{quote(title)}",
                                    "source": "Wikipedia EN",
                                })
                                break  # Un seul résultat par page
                            else:
                                print(f"⚠️ Contenu vide ou trop court pour: {title}")

                    except Exception as e:
                        print(f"❌ Erreur lors de la récupération du contenu de '{title}': {str(e)}")
                        continue

            print(f"✅ Wikipedia EN: {len(results)} résultats avec contenu complet")
            return results[:self.max_results]

        except Exception as e:
            print(f"❌ Erreur globale Wikipedia EN: {str(e)}")
            traceback.print_exc()
            return []

    def _extract_page_contents(
        self, search_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extrait le contenu des pages"""
        enriched_results = []

        def extract_single_page(result):
            try:
                if not result.get("url") or not result["url"].startswith("http"):
                    return result

                headers = {"User-Agent": self.user_agent}
                response = requests.get(result["url"], headers=headers, timeout=7)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "html.parser")

                # Supprimer les scripts et styles
                for element in soup(
                    ["script", "style", "nav", "footer", "header", "aside"]
                ):
                    element.decompose()

                # Extraire le texte principal
                main_content = ""

                # Priorité aux balises principales
                for tag in [
                    "main",
                    "article",
                    '[role="main"]',
                    ".content",
                    ".article",
                    ".post",
                ]:
                    content_elem = soup.select_one(tag)
                    if content_elem:
                        main_content = content_elem.get_text(separator=" ", strip=True)
                        break

                # Fallback sur les paragraphes
                if not main_content:
                    paragraphs = soup.find_all("p")
                    main_content = " ".join(
                        [p.get_text(strip=True) for p in paragraphs[:10]]
                    )

                # Limiter la longueur
                if len(main_content) > self.max_content_length:
                    main_content = main_content[: self.max_content_length] + "..."

                result["full_content"] = main_content

            except Exception as e:
                print(
                    f"⚠️ Impossible d'extraire le contenu de {result.get('url', 'URL inconnue')}: {str(e)}"
                )
                result["full_content"] = result.get("snippet", "")

            return result

        # Traitement parallèle
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            enriched_results = list(executor.map(extract_single_page, search_results))

        return enriched_results

    def _generate_cache_key(self, query: str) -> str:
        """Génère une clé de cache pour la requête"""
        return f"search_{hash(query.lower().strip())}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Vérifie si le cache est encore valide"""
        if cache_key not in self.search_cache:
            return False

        cache_time = self.search_cache[cache_key]["timestamp"]
        return (time.time() - cache_time) < self.cache_duration

    def _cache_results(
        self, cache_key: str, summary: str, results: List[Dict[str, Any]]
    ):
        """Met en cache les résultats"""
        self.search_cache[cache_key] = {
            "summary": summary,
            "results": results,
            "timestamp": time.time(),
        }

        # Nettoyer le cache ancien (garder max 20 entrées)
        if len(self.search_cache) > 20:
            oldest_key = min(
                self.search_cache.keys(),
                key=lambda k: self.search_cache[k]["timestamp"],
            )
            del self.search_cache[oldest_key]

    def get_search_history(self) -> List[str]:
        """Retourne l'historique des recherches récentes"""
        history = []
        for data in sorted(
            self.search_cache.items(), key=lambda x: x[1]["timestamp"], reverse=True
        ):
            if data.get("results") and data["results"]:
                history.append(f"Recherche récente - {len(data['results'])} résultats")

        return history[:10]

    def summarize_url(self, url: str) -> str:
        """
        Récupère et résume le contenu d'une URL directe

        Args:
            url: L'URL de la page à résumer

        Returns:
            str: Un résumé formaté du contenu de la page
        """
        try:
            print(f"🌐 Récupération de la page: {url}")

            # Vérifier le cache
            cache_key = f"url_{hash(url)}"
            if self._is_cache_valid(cache_key):
                print("📋 Contenu trouvé en cache")
                return self.search_cache[cache_key]["summary"]

            # Récupérer le contenu de la page
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "fr-FR,fr;q=0.5",
            }

            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            # Parser le HTML
            soup = BeautifulSoup(response.content, "html.parser")

            # Extraire le titre
            title = soup.title.string if soup.title else "Page Web"
            title = self._clean_title(title)

            # Supprimer les éléments non pertinents
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
                element.decompose()

            # Extraire le contenu principal
            main_content = ""

            # Essayer de trouver le contenu principal avec différentes stratégies
            for selector in ["main", "article", '[role="main"]', ".content", ".article", ".post", ".entry-content", "#content"]:
                content_elem = soup.select_one(selector)
                if content_elem:
                    main_content = content_elem.get_text(separator="\n", strip=True)
                    break

            # Fallback: extraire tous les paragraphes
            if not main_content or len(main_content) < 100:
                paragraphs = soup.find_all("p")
                main_content = "\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30])

            # Si toujours pas de contenu, extraire tout le texte du body
            if not main_content or len(main_content) < 100:
                body = soup.find("body")
                if body:
                    main_content = body.get_text(separator="\n", strip=True)

            # Nettoyer le contenu
            lines = main_content.split("\n")
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                # Garder seulement les lignes avec du contenu significatif
                if len(line) > 20 and not line.startswith(("©", "Cookie", "JavaScript")):
                    cleaned_lines.append(line)

            main_content = "\n".join(cleaned_lines)

            # Vérifier qu'on a du contenu
            if not main_content or len(main_content) < 50:
                return "❌ Impossible d'extraire le contenu de cette page. L'URL est peut-être protégée ou le format n'est pas supporté."

            # Générer le résumé
            summary = self._generate_url_summary(title, url, main_content)

            # Mettre en cache
            self.search_cache[cache_key] = {
                "summary": summary,
                "timestamp": time.time(),
            }

            return summary

        except requests.exceptions.Timeout:
            return f"⏱️ La requête a pris trop de temps. L'URL ne répond pas assez rapidement: {url}"
        except requests.exceptions.ConnectionError:
            return f"🔌 Impossible de se connecter à cette URL. Vérifiez votre connexion internet et que l'URL est correcte: {url}"
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return f"🔍 Page non trouvée (erreur 404). Cette URL n'existe pas ou plus: {url}"
            elif e.response.status_code == 403:
                return f"🚫 Accès refusé (erreur 403). Cette page bloque les accès automatisés: {url}"
            else:
                return f"❌ Erreur HTTP {e.response.status_code} lors de l'accès à: {url}"
        except Exception as e:
            print(f"❌ Erreur lors du résumé de l'URL: {str(e)}")
            return f"❌ Une erreur s'est produite lors de la récupération de cette page: {str(e)}"

    def _generate_url_summary(self, title: str, url: str, content: str) -> str:
        """
        Génère un résumé structuré du contenu d'une URL

        Args:
            title: Titre de la page
            url: URL de la page
            content: Contenu extrait de la page

        Returns:
            str: Résumé formaté en markdown
        """
        # Limiter le contenu pour l'analyse
        if len(content) > 5000:
            content_for_analysis = content[:5000]
        else:
            content_for_analysis = content

        # Extraire les points clés
        sentences = re.split(r'[.!?]+', content_for_analysis)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]

        # Prendre les premières phrases significatives comme résumé
        summary_sentences = sentences[:5] if len(sentences) >= 5 else sentences

        # Construire le résumé
        summary = f"📄 **{title}**"
        summary += f" ({url})\n\n"
        summary += "📝 **Résumé du contenu:**\n\n"

        for i, sentence in enumerate(summary_sentences, 1):
            # Nettoyer la phrase
            sentence = self._universal_word_spacing_fix(sentence)
            summary += f"{i}. {sentence}.\n\n"

        # Ajouter statistiques
        word_count = len(content.split())
        summary += f"\n📊 **Statistiques:** {word_count} mots, {len(sentences)} phrases analysées\n"

        # Extraire des mots-clés importants
        words = content.lower().split()
        # Filtrer les mots courts et communs
        stop_words = {'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou', 'mais', 'pour', 'dans', 'sur', 'avec', 'est', 'sont', 'qui', 'que', 'ce', 'se', 'ne', 'pas', 'plus', 'comme', 'tout', 'nous', 'vous', 'leur', 'leurs', 'son', 'sa', 'ses'}
        keywords = [w for w in words if len(w) > 4 and w not in stop_words]

        # Compter les occurrences
        keyword_counts = Counter(keywords)
        top_keywords = [kw for kw, count in keyword_counts.most_common(5)]

        if top_keywords:
            summary += f"🏷️ **Mots-clés:** {', '.join(top_keywords)}\n\n\n"

        return summary


# Alias pour remplacer l'ancienne classe
InternetSearchEngine = EnhancedInternetSearchEngine
