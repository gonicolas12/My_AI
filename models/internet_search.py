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

# Import cloudscraper pour contourner les protections anti-bot
try:
    import cloudscraper

    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False
    print("⚠️ cloudscraper non disponible, utilisation de requests standard")


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

        # Initialiser cloudscraper si disponible
        if CLOUDSCRAPER_AVAILABLE:
            self.scraper = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "mobile": False}
            )
            print("✅ Cloudscraper initialisé (contournement anti-bot activé)")
        else:
            self.scraper = None

        # Patterns pour l'extraction de réponses directes
        self.answer_patterns = self._init_answer_patterns()

    def _get_next_user_agent(self) -> str:
        """Obtient le prochain user-agent pour éviter la détection"""
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(
            self.user_agents
        )
        self.user_agent = self.user_agents[self.current_user_agent_index]
        return self.user_agent

    def _correct_common_typos(self, query: str) -> str:
        """Corrige les fautes d'orthographe courantes dans les requêtes - VERSION SIMPLE"""
        corrections = {
            # Monuments et lieux célèbres
            "effeil": "eiffel",
            "eifeil": "eiffel",
            "effell": "eiffel",
            "eifel": "eiffel",
            # Villes
            "pariss": "paris",
            "paaris": "paris",
            # Mesures courantes
            "tail": "taille",
            "taile": "taille",
            "mesur": "mesure",
            # Mots courants mal orthographiés
            "populatoin": "population",
            "populaton": "population",
            "hauteure": "hauteur",
        }

        words = query.split()
        corrected_words = []
        has_correction = False

        for word in words:
            # Enlever la ponctuation pour la comparaison
            clean_word = word.lower().strip(".,;:!?")

            # Chercher une correction
            if clean_word in corrections:
                corrected_word = corrections[clean_word]
                # Préserver la ponctuation originale
                if word != clean_word:
                    corrected_word = corrected_word + word[len(clean_word) :]
                corrected_words.append(corrected_word)
                has_correction = True
                print(f"✏️ Correction: '{word}' → '{corrected_word}'")
            else:
                corrected_words.append(word)

        corrected_query = " ".join(corrected_words)

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

    def _is_weather_query(self, query: str) -> bool:
        """Détecte si la question concerne la météo"""
        weather_keywords = [
            "météo",
            "meteo",
            "weather",
            "température",
            "temperature",
            "temps",
            "pluie",
            "soleil",
            "neige",
            "vent",
            "climat",
            "chaud",
            "froid",
            "degrés",
            "celsius",
            "forecast",
            "prévisions",
            "previsions",
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in weather_keywords)

    def _handle_weather_query(self, query: str) -> str:
        """
        Gère les questions météo en utilisant wttr.in (service gratuit)
        Fournit la météo temps réel sans clé API
        """
        # Extraire la ville si possible
        city = self._extract_city_from_query(query)

        if not city:
            return """🌤️ **Recherche météo mondiale**

❌ Je n'ai pas pu identifier la ville dans votre question.

💡 **Exemples de questions valides :**
   - "Quelle est la météo à Tokyo ?"
   - "Quel temps fait-il à New York aujourd'hui ?"
   - "Température à Londres ?"
   - "Météo São Paulo"
   - "Weather in Sydney ?"

🌍 **Villes supportées :** Toutes les villes du monde !
   - Europe : Paris, Londres, Berlin, Madrid, Rome...
   - Amérique : New York, Los Angeles, Toronto, São Paulo...
   - Asie : Tokyo, Pékin, Bangkok, Mumbai, Séoul...
   - Océanie : Sydney, Melbourne, Auckland...
   - Afrique : Le Caire, Casablanca, Johannesburg...

🌐 **Sites météo recommandés :**
   - [wttr.in](https://wttr.in/) - Météo mondiale gratuite
   - [Météo-France](https://meteofrance.com/) - Service officiel français"""

        # Obtenir la météo via wttr.in
        try:
            print(f"🌤️ Récupération météo pour: {city.title()}")
            weather_data = self._get_wttr_weather(city)
            return weather_data
        except Exception as e:
            print(f"⚠️ Erreur météo wttr.in: {e}")
            return f"""🌤️ **Météo pour {city.title()}**

⚠️ **Impossible de récupérer la météo en temps réel** (erreur: {str(e)[:100]})

💡 **Solutions alternatives :**

1. **Consultez directement :**
   - 🌐 [Météo {city.title()} sur wttr.in](https://wttr.in/{city})
   - 🌐 [Weather.com](https://weather.com/)

2. **Vérifiez l'orthographe** de la ville (en anglais si possible)

3. **Réessayez dans quelques instants** (problème de connexion temporaire)"""

    def _get_wttr_weather(self, city: str) -> str:
        """
        Récupère la météo via wttr.in (service gratuit, pas de clé API)
        Format français, données temps réel
        """
        # wttr.in API endpoints
        # Format: wttr.in/VILLE?format=...
        # ?0 = conditions actuelles
        # ?1 = température
        # ?2 = vent
        # ?3 = humidité
        # ?4 = précipitations
        # ?format=j1 = JSON complet

        base_url = f"https://wttr.in/{quote(city)}"

        headers = {
            "User-Agent": self.user_agent,
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        }

        try:
            # Récupérer la météo en format texte (plus simple à parser)
            # Format: wttr.in/VILLE?format="%C+%t+%h+%w+%p"
            # %C = Condition (Ensoleillé, Nuageux, etc.)
            # %t = Température
            # %h = Humidité
            # %w = Vent
            # %p = Précipitations

            params = {
                "format": "%C|%t|%h|%w|%p|%m",  # Pipe-separated pour parsing
                "lang": "fr",  # Texte en français
            }

            response = requests.get(
                base_url, params=params, headers=headers, timeout=self.timeout
            )
            response.raise_for_status()

            # Parser la réponse (format: "Condition|Temp|Humidity|Wind|Precip|Moon")
            weather_parts = response.text.strip().split("|")

            if len(weather_parts) >= 5:
                condition = weather_parts[0].strip()
                temperature = weather_parts[1].strip()
                humidity = weather_parts[2].strip()
                wind = weather_parts[3].strip()
                precipitation = weather_parts[4].strip()

                # Récupérer aussi les prévisions sur 3 jours
                try:
                    forecast_params = {"format": "3", "lang": "fr"}
                    forecast_response = requests.get(
                        base_url, params=forecast_params, headers=headers, timeout=10
                    )
                    forecast_text = forecast_response.text.strip()
                except Exception:
                    forecast_text = "Prévisions non disponibles"

                # Formater la réponse
                weather_summary = f"""🌤️**Météo à {city.title()}** (Temps réel)

**Conditions actuelles :**
☁️       **{condition}**
🌡️ Température : **{temperature}**
💧       Humidité : **{humidity}**
💨       Vent : **{wind}**
🌧️ Précipitations : **{precipitation}**

**Prévisions sur 3 jours :**
{forecast_text}

📍 **Source** : [wttr.in/{city}](https://wttr.in/{city})
⏰ Données temps réel mises à jour automatiquement

💡 **Astuce** : Tapez `https://wttr.in/{city}` dans votre navigateur pour voir une météo détaillée en ASCII art !"""

                return weather_summary
            else:
                raise ValueError("Format de réponse inattendu de wttr.in")

        except requests.exceptions.Timeout as e:
            raise Exception(
                f"Timeout lors de la connexion à wttr.in (> {self.timeout}s)"
            ) from e
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(
                    f"Ville '{city}' non trouvée. Vérifiez l'orthographe."
                ) from e
            else:
                raise Exception(f"Erreur HTTP {e.response.status_code}") from e
        except Exception as e:
            raise Exception(f"Erreur inattendue: {str(e)}") from e

    def _extract_city_from_query(self, query: str) -> Optional[str]:
        """
        Extrait le nom de ville d'une requête météo.
        Supporte les villes du monde entier grâce à wttr.in.
        """
        query_lower = query.lower()

        # Mots à exclure (mots communs qui ne sont pas des villes)
        stop_words = {
            "le", "la", "les", "un", "une", "des", "cette", "ce", "cet",
            "météo", "meteo", "weather", "température", "temperature", "temps",
            "pluie", "soleil", "neige", "vent", "climat", "chaud", "froid",
            "degrés", "celsius", "forecast", "prévisions", "previsions",
            "quel", "quelle", "quels", "quelles", "comment", "est", "fait",
            "aujourd'hui", "demain", "semaine", "maintenant", "actuelle",
            "il", "elle", "on", "nous", "vous", "ils", "elles",
            "dans", "sur", "pour", "avec", "sans", "chez",
        }

        # Prépositions à supprimer du début du nom de ville
        prepositions_to_remove = {
            "au", "aux", "en", "à", "a", "de", "du", "des", "le", "la", "les", "l"
        }

        # Pattern pour extraire les noms de villes avec prépositions
        # Supporte les villes multi-mots comme "New York", "Los Angeles", "São Paulo"
        patterns = [
            # "au Népal", "aux États-Unis", "en France"
            r"\b(?:au|aux|en)\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-\s']+?)(?:\s*\?|$|\s+(?:aujourd|demain|cette|il|fait|quel))",
            # "à Paris", "à New York", "à São Paulo"
            r"\bà\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-\s']+?)(?:\s*\?|$|\s+(?:aujourd|demain|cette|il|fait|quel))",
            # "de Paris", "de Tokyo"
            r"\bde\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-\s']+?)(?:\s*\?|$|\s+(?:aujourd|demain|cette|il|fait|quel))",
            # "pour Paris", "pour Londres"
            r"\bpour\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-\s']+?)(?:\s*\?|$|\s+(?:aujourd|demain|cette|il|fait|quel))",
            # "sur Paris"
            r"\bsur\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-\s']+?)(?:\s*\?|$|\s+(?:aujourd|demain|cette|il|fait|quel))",
            # "météo Tokyo", "weather London", "météo au Japon"
            r"(?:météo|meteo|weather)\s+(?:au|aux|en|à|du|de la|de)?\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-\s']+?)(?:\s*\?|$)",
            # "Tokyo météo", "Paris weather"
            r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-\s']+?)\s+(?:météo|meteo|weather)(?:\s*\?|$)",
            # Pattern simple pour villes en fin de phrase: "... à Tokyo?", "... au Japon?"
            r"\b(?:à|au|aux|en)\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-\s']+?)\s*\?",
        ]

        def clean_city_name(city: str) -> str:
            """Nettoie le nom de la ville en supprimant les prépositions au début"""
            city = city.strip()
            # Supprimer les prépositions au début
            words = city.split()
            while words and words[0].lower() in prepositions_to_remove:
                words.pop(0)
            return " ".join(words).strip()

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                potential_city = match.group(1).strip()
                # Nettoyer les espaces en trop
                potential_city = " ".join(potential_city.split())
                # Nettoyer les prépositions au début
                potential_city = clean_city_name(potential_city)
                # Vérifier que ce n'est pas un mot commun
                if potential_city and potential_city.lower() not in stop_words and len(potential_city) >= 2:
                    print(f"🌍 Ville détectée: {potential_city}")
                    return potential_city

        # Dernière tentative: chercher un mot capitalisé qui pourrait être une ville
        # Pattern pour les noms propres (commence par majuscule)
        capital_pattern = r"\b([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+)*)\b"
        matches = re.findall(capital_pattern, query)
        for potential_city in matches:
            cleaned_city = clean_city_name(potential_city)
            if cleaned_city and cleaned_city.lower() not in stop_words and len(cleaned_city) >= 2:
                print(f"🌍 Ville détectée (nom propre): {cleaned_city}")
                return cleaned_city

        return None

    def search_and_summarize(self, query: str) -> str:
        """Recherche sur internet et extrait la réponse directe"""
        try:
            print(f"🔍 Recherche internet pour: '{query}'")

            # Détection des questions météo (nécessitent des données temps réel)
            if self._is_weather_query(query):
                return self._handle_weather_query(query)

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
            clean_word = word.strip("?.,!;:").lower()
            if len(clean_word) >= 4 and clean_word not in [
                "quel",
                "quelle",
                "comment",
                "taille",
                "hauteur",
                "fait",
                "mesure",
                "what",
                "which",
                "height",
                "size",
            ]:
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
                            print(
                                f"  ✅ Phrase avec entité '{entity_words}': {sentence[:80]}..."
                            )

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
            # Patterns de hauteur explicites
            r"(?:mesure|fait|taille|hauteur)(?:\s+de)?\s+([\d,\s]+\.?\d*)\s*(mètres?|m\b|km|centimètres?|cm)",
            r"([\d,\s]+\.?\d*)\s*(mètres?|m\b|km|centimètres?|cm)(?:\s+de|d')?\s+(?:haut|hauteur|taille)",
            r"(?:s'élève à|atteint|culmine)\s+([\d,\s]+\.?\d*)\s*(mètres?|m\b|km)",
            # Patterns avec contexte de hauteur
            r"([\d,\s]+\.?\d*)\s*(?:m\b|mètres?)\s+(?:de haut|d'altitude|au-dessus)",
            r"(?:environ|plus de|près de|quelque)\s+([\d,\s]+\.?\d*)\s*(mètres?|m\b)",
            # Pattern important: "de XXX m de hauteur" ou "de XXX mètres"
            r"de\s+([\d,\s]+\.?\d*)\s*(mètres?|m)\s*(?:\[|de hauteur|d'altitude)",
            r"\b(\d{2,4})\s*(?:m\b|mètres?)\b",  # Capture simple comme "828 m"
        ]

        # Extraire les mots-clés de l'entité recherchée depuis la query
        entity_keywords = set()
        for word in query.split():
            clean_word = word.strip("?.,!;:").lower()
            if len(clean_word) >= 4 and clean_word not in [
                "quel",
                "quelle",
                "comment",
                "taille",
                "hauteur",
                "fait",
                "mesure",
                "what",
                "which",
                "height",
                "size",
            ]:
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
                    value_str_clean = (
                        value_str.replace(",", ".").replace(" ", "").strip()
                    )

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
                            context_before_words = words[
                                context_before_start:word_position
                            ]

                            context_after_words = words[
                                word_position : min(len(words), word_position + 5)
                            ]

                            # Vérifier l'entité PRIORITAIREMENT dans le contexte AVANT
                            context_before_set = set(
                                word.lower().strip(string.punctuation)
                                for word in context_before_words
                            )
                            entity_in_before = len(
                                entity_keywords.intersection(context_before_set)
                            )

                            # RÈGLE STRICTE : L'entité DOIT être COMPLÈTEMENT AVANT la mesure
                            # Si l'entité est après ou partiellement après, c'est une autre mesure dans une liste
                            if entity_in_before >= len(entity_keywords):
                                # ✅ Toute l'entité est AVANT la mesure → ACCEPTÉ
                                entity_match_score = entity_in_before
                            else:
                                # ❌ L'entité n'est pas complète avant → REJETÉ
                                # Même si elle est après, c'est probablement une autre mesure dans une liste
                                entity_match_score = 0

                            context = " ".join(
                                context_before_words + context_after_words
                            ).lower()

                            if entity_match_score > 0:
                                print(
                                    f"  ✅ [LOCAL] Mesure {value_num} {unit} avec entité dans contexte: '{context[:80]}...'"
                                )
                            else:
                                print(
                                    f"  ❌ [LOCAL] Mesure {value_num} {unit} SANS entité dans contexte: '{context[:80]}...'"
                                )

                        # Score de pertinence total = pertinence candidate + bonus entité
                        total_relevance = candidate["relevance"] + (
                            entity_match_score * 10
                        )

                        measurements_with_sources.append(
                            {
                                "value": value_num,
                                "unit": unit,
                                "value_str": f"{value_str} {unit_str}",
                                "source": source,
                                "sentence": sentence,
                                "relevance": candidate["relevance"],
                                "entity_relevance": entity_match_score,
                                "total_relevance": total_relevance,
                            }
                        )
                    except (ValueError, IndexError):
                        continue

        if not measurements_with_sources:
            return None

        print(f"📊 [MULTI-SOURCE] {len(measurements_with_sources)} mesures trouvées")

        # Afficher toutes les valeurs trouvées pour debug avec leur pertinence entité
        for m in measurements_with_sources:
            entity_indicator = (
                f" 🎯x{m['entity_relevance']}" if m["entity_relevance"] > 0 else ""
            )
            print(
                f"  📍 {m['value']} {m['unit']}{entity_indicator} (source: {m['source']})"
            )

        # FILTRER d'abord par pertinence à l'entité si on a des mots-clés
        if entity_keywords:
            # Séparer les mesures avec et sans match d'entité
            entity_matches = [
                m for m in measurements_with_sources if m["entity_relevance"] > 0
            ]
            non_entity_matches = [
                m for m in measurements_with_sources if m["entity_relevance"] == 0
            ]

            if entity_matches:
                print(
                    f"🎯 [FILTER] {len(entity_matches)} mesures correspondent à l'entité '{entity_keywords}'"
                )
                print(
                    f"  ⚠️ {len(non_entity_matches)} mesures d'autres entités ignorées"
                )
                # Utiliser SEULEMENT les mesures qui mentionnent l'entité recherchée
                measurements_with_sources = entity_matches
            else:
                print(
                    "⚠️ [FILTER] Aucune mesure avec l'entité recherchée, utilisation de toutes les mesures"
                )

        # Validation multi-sources et détection d'outliers
        validated_measurement = self._validate_measurements_consensus(
            measurements_with_sources, query
        )

        if validated_measurement:
            return validated_measurement

        # Fallback sur l'ancienne méthode si pas assez de données
        if measurements_with_sources:
            # Trier par pertinence totale
            measurements_with_sources.sort(
                key=lambda x: x["total_relevance"], reverse=True
            )
            best_match = measurements_with_sources[0]

            # Si on a une mesure valide, on essaie de la formater
            # Surtout si on a filtré par entité, c'est probablement la bonne
            print(
                f"  ✅ Utilisation de la meilleure mesure (score {best_match['total_relevance']}) sans consensus"
            )

            # Convertir en mètres pour l'affichage uniforme
            value = best_match["value"]
            unit = best_match["unit"]
            if "km" in unit or "kilo" in unit:
                value = value * 1000
            elif "cm" in unit or "centi" in unit:
                value = value / 100

            return self._generate_formatted_measurement_answer(
                value,
                query,
                best_match.get("source", ""),
                best_match["sentence"],
                1,
            )

        return None

    def _generate_formatted_measurement_answer(
        self,
        value: float,
        query: str,
        source_name: str,
        sentence: str,
        num_confirming: int = 1,
    ) -> str:
        """Génère une réponse formatée pour une mesure"""
        # STRATÉGIE PRIORITAIRE : Extraire l'entité depuis la REQUÊTE utilisateur
        entity_name = None

        if query:
            # Extraire les mots significatifs (>= 4 lettres, pas de mots-questions)
            query_words = query.split()
            entity_words = []
            stop_words = {
                "quel",
                "quelle",
                "comment",
                "taille",
                "hauteur",
                "fait",
                "mesure",
                "what",
                "which",
                "height",
                "size",
                "est",
                "la",
                "le",
                "du",
                "de",
                "des",
            }

            for word in query_words:
                clean_word = word.strip("?.,!;:").lower()
                if len(clean_word) >= 4 and clean_word not in stop_words:
                    entity_words.append(word.strip("?.,!;:"))

            # Si on a au moins 2 mots, les combiner
            if len(entity_words) >= 2:
                entity_name = " ".join(entity_words[:2])  # Prendre les 2 premiers
                # Capitaliser correctement (première lettre de chaque mot en majuscule)
                entity_name = " ".join(w.capitalize() for w in entity_name.split())
                print(f"  🎯 [ENTITY] Nom extrait de la REQUÊTE: '{entity_name}'")

        # Stratégie 2 : Chercher dans la source
        if not entity_name and source_name:
            # Nettoyer le nom de la source
            clean_source = (
                source_name.replace("(Article direct)", "")
                .replace("Wikipedia FR", "")
                .replace("Wikipedia EN", "")
                .strip()
            )

            # Vérifier si c'est une page spécifique (pas une liste générique)
            if clean_source and clean_source not in [
                "Structure",
                "Source inconnue",
                "Liste des plus hautes structures du monde",
                "Listes des plus hautes constructions du monde",
                "Ordres de grandeur de longueur",
                "Chronologie des plus hautes structures du monde",
            ]:
                entity_name = clean_source
                print(f"  🎯 [ENTITY] Nom trouvé depuis source: '{entity_name}'")

        # Stratégie 3 : Extraire depuis la phrase
        if not entity_name and sentence:
            # Chercher un pattern comme "Burj Khalifa" ou "le/la Nom"
            name_patterns = [
                r"([A-Z][a-zA-Z\s]+?)\s+\(",  # Nom avant une parenthèse
                r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b",  # Nom propre (mots en majuscule)
            ]

            for pattern in name_patterns:
                match = re.search(pattern, sentence)
                if match:
                    potential_name = match.group(1).strip()
                    # Vérifier que ce n'est pas un mot commun
                    if potential_name not in [
                        "La",
                        "Le",
                        "Un",
                        "Une",
                        "De",
                        "Du",
                        "Des",
                        "Il",
                        "Elle",
                    ]:
                        entity_name = potential_name
                        print(f"  🎯 [ENTITY] Nom extrait de la phrase: '{entity_name}'")
                        break

        # Stratégie 4 : Fallback générique
        if not entity_name:
            entity_name = "structure"
            print("  ⚠️ [ENTITY] Nom générique utilisé")

            # Construire la réponse simple et directe
        # Adapter l'article selon le genre (si commence par voyelle, utiliser "l'")
        if entity_name[0].lower() in "aeiouhéèê":
            article = "L'"
            simple_answer = f"{article}{entity_name} mesure {int(value)} mètres de hauteur."
        else:
            # Détecter si c'est masculin ou féminin (par défaut masculin)
            if entity_name.lower().startswith(
                ("tour", "flèche", "antenne", "structure")
            ):
                article = "La"
            else:
                article = "Le"
            simple_answer = f"{article} {entity_name} mesure {int(value)} mètres de hauteur."

        print(f"  📝 [SIMPLE] Réponse générée: {simple_answer}")

        # Ajouter l'information de validation si pertinent
        if num_confirming >= 3:
            validation_note = (
                f" (✅ Confirmé par {num_confirming} sources indépendantes)"
            )
            simple_answer += validation_note

        return simple_answer.strip()

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
            value = m["value"]
            unit = m["unit"]

            # Convertir en mètres
            if "km" in unit or "kilo" in unit:
                value = value * 1000
            elif "cm" in unit or "centi" in unit:
                value = value / 100

            normalized_measurements.append({**m, "normalized_value": value})

        # Extraire les valeurs normalisées
        values = [m["normalized_value"] for m in normalized_measurements]

        # Calculer les statistiques
        mean_value = statistics.mean(values)

        if len(values) >= 3:
            median_value = statistics.median(values)
            # Calculer l'écart-type pour détecter les outliers
            std_dev = statistics.stdev(values) if len(values) > 1 else 0
        else:
            median_value = mean_value
            std_dev = 0

        print(
            f"  📊 Moyenne: {mean_value:.1f}m, Médiane: {median_value:.1f}m, Écart-type: {std_dev:.1f}m"
        )

        # Détection des outliers (valeurs à plus de 2 écart-types)
        inliers = []
        outliers = []

        for m in normalized_measurements:
            if std_dev == 0 or abs(m["normalized_value"] - mean_value) <= 2 * std_dev:
                inliers.append(m)
            else:
                outliers.append(m)
            print(
                f"  ⚠️ Outlier détecté: {m['value']} {m['unit']} de {m['source']} (trop éloigné du consensus)"
            )

        # Générer une réponse si on a au moins 1 mesure fiable
        if len(inliers) >= 1:
            # Prendre la médiane des valeurs fiables (ou la seule valeur si 1 seule mesure)
            if len(inliers) >= 2:
                consensus_value = statistics.median(
                    [m["normalized_value"] for m in inliers]
                )
            else:
                # Une seule mesure fiable
                consensus_value = inliers[0]["normalized_value"]

            # Trouver la mesure la plus proche du consensus
            closest_measurement = min(
                inliers, key=lambda m: abs(m["normalized_value"] - consensus_value)
            )

            # Compter les sources qui confirment (valeurs similaires à ±5%)
            tolerance = consensus_value * 0.05
            confirming_sources = [
                m
                for m in inliers
                if abs(m["normalized_value"] - consensus_value) <= tolerance
            ]

            num_confirming = len(set(m["source"] for m in confirming_sources))

            if len(inliers) >= 2:
                print(
                    f"  ✅ Consensus trouvé: {consensus_value:.0f}m ({num_confirming} sources concordantes)"
                )
            else:
                print(
                    f"  ℹ️ Mesure unique trouvée: {consensus_value:.0f}m (source: {inliers[0].get('source', 'inconnue')})"
                )  # NOUVELLE APPROCHE : Générer une réponse SIMPLE et DIRECTE
            # Au lieu d'extraire de phrases complexes, construire la réponse nous-mêmes

            # STRATÉGIE PRIORITAIRE : Extraire l'entité depuis la REQUÊTE utilisateur
            entity_name = None

            if query:
                # Extraire les mots significatifs (>= 3 lettres, pas de mots-questions/articles)
                query_words = query.split()
                entity_words = []
                stop_words = {
                    "quel",
                    "quelle",
                    "quels",
                    "quelles",
                    "comment",
                    "combien",
                    "pourquoi",
                    "taille",
                    "hauteur",
                    "fait",
                    "mesure",
                    "poids",
                    "what",
                    "which",
                    "height",
                    "size",
                    "how",
                    "tall",
                    "est",
                    "sont",
                    "était",
                    "étaient",
                    "la",
                    "le",
                    "les",
                    "l",
                    "un",
                    "une",
                    "des",
                    "du",
                    "de",
                    "d",
                    "au",
                    "aux",
                }

                for word in query_words:
                    # Nettoyer le mot des ponctuations et apostrophes
                    clean_word = word.strip("?.,!;:'\"").lower()
                    # Gérer les mots avec apostrophe comme "l'empire" -> "empire"
                    if "'" in clean_word:
                        parts = clean_word.split("'")
                        clean_word = parts[-1] if len(parts[-1]) > 2 else clean_word

                    if len(clean_word) >= 3 and clean_word not in stop_words:
                        # Garder le mot original (sans ponctuation finale) pour le capitaliser correctement
                        original_word = word.strip("?.,!;:")
                        # Si le mot contient une apostrophe, ne garder que la partie après
                        if "'" in original_word:
                            original_word = original_word.split("'")[-1]
                        entity_words.append(original_word)

                # Si on a au moins 1 mot significatif, l'utiliser
                if len(entity_words) >= 1:
                    # Combiner les mots (max 3 pour éviter les noms trop longs)
                    entity_name = " ".join(entity_words[:3])
                    # Capitaliser correctement (Title Case)
                    entity_name = entity_name.title()
                    print(f"  🎯 [ENTITY] Nom extrait de la REQUÊTE: '{entity_name}'")

            # Stratégie 2 : Chercher dans les sources Wikipedia
            if not entity_name:
                for m in inliers:
                    source = m.get("source", "")
                    # Nettoyer le nom de la source
                    clean_source = (
                        source.replace("(Article direct)", "")
                        .replace("Wikipedia FR", "")
                        .replace("Wikipedia EN", "")
                        .strip()
                    )

                    # Vérifier si c'est une page spécifique (pas une liste générique)
                    if clean_source and clean_source not in [
                        "Structure",
                        "Source inconnue",
                        "Liste des plus hautes structures du monde",
                        "Listes des plus hautes constructions du monde",
                        "Ordres de grandeur de longueur",
                        "Chronologie des plus hautes structures du monde",
                    ]:
                        entity_name = clean_source
                        print(
                            f"  🎯 [ENTITY] Nom trouvé depuis source: '{entity_name}'"
                        )
                        break

            # Stratégie 3 : Extraire depuis la phrase
            if not entity_name:
                sentence = closest_measurement["sentence"]

                # Chercher un pattern comme "Burj Khalifa" ou "le/la Nom"
                name_patterns = [
                    r"([A-Z][a-zA-Z\s]+?)\s+\(",  # Nom avant une parenthèse
                    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b",  # Nom propre (mots en majuscule)
                ]

                for pattern in name_patterns:
                    match = re.search(pattern, sentence)
                    if match:
                        potential_name = match.group(1).strip()
                        # Vérifier que ce n'est pas un mot commun
                        if potential_name not in [
                            "La",
                            "Le",
                            "Un",
                            "Une",
                            "De",
                            "Du",
                            "Des",
                            "Il",
                            "Elle",
                        ]:
                            entity_name = potential_name
                            print(
                                f"  🎯 [ENTITY] Nom extrait de la phrase: '{entity_name}'"
                            )
                            break

            # Stratégie 4 : Fallback générique
            if not entity_name:
                entity_name = "structure"
                print("  ⚠️ [ENTITY] Nom générique utilisé")

            # Construire la réponse simple et directe
            # Nettoyer le nom de l'entité (enlever articles résiduels au début)
            entity_name_clean = entity_name.strip()
            # Enlever les articles au début s'ils sont présents
            for prefix in ["L'", "l'", "Le ", "le ", "La ", "la ", "Les ", "les "]:
                if entity_name_clean.startswith(prefix):
                    entity_name_clean = entity_name_clean[len(prefix) :].strip()
                    break

            # Recapitaliser proprement
            entity_name_clean = entity_name_clean.title()

            # Adapter l'article selon le genre et la première lettre
            first_letter = entity_name_clean[0].lower() if entity_name_clean else ""

            # Mots féminins connus
            feminine_words = (
                "tour",
                "flèche",
                "antenne",
                "structure",
                "statue",
                "pyramide",
                "cathédrale",
                "église",
                "mosquée",
            )
            is_feminine = entity_name_clean.lower().startswith(feminine_words)

            # Construire la phrase naturelle
            if first_letter in "aeiouhéèêy":
                # Voyelle -> utiliser "L'"
                simple_answer = f"L'{entity_name_clean} mesure **{int(consensus_value)} mètres** de hauteur."
            elif is_feminine:
                simple_answer = f"La {entity_name_clean} mesure **{int(consensus_value)} mètres** de hauteur."
            else:
                simple_answer = f"Le {entity_name_clean} mesure **{int(consensus_value)} mètres** de hauteur."

            print(f"  📝 [SIMPLE] Réponse générée: {simple_answer}")

            # Ajouter l'information de validation si pertinent
            if num_confirming >= 3:
                validation_note = (
                    f" (✅ Confirmé par {num_confirming} sources indépendantes)"
                )
                simple_answer += validation_note

            return simple_answer.strip()

        # Pas de consensus clair
        print(
            f"  ⚠️ Pas de consensus clair ({len(inliers)} sources fiables sur {len(measurements)})"
        )
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

    def _extract_date_answer(self, candidates: List[Dict[str, Any]]) -> Optional[str]:
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

    def _is_natural_response(self, text: str) -> bool:
        """
        Vérifie si une réponse est formulée naturellement ou si c'est un extrait brut.

        Une réponse naturelle :
        - Commence par un sujet clair (La/Le/L'/Un/Une + nom)
        - Contient un verbe principal (mesure, est, fait, etc.)
        - Ne contient pas de fragments de navigation (Adresse, Accès, Coordonnées, etc.)

        Returns:
            bool: True si la réponse est naturelle, False si c'est un extrait brut
        """
        if not text:
            return False

        text_lower = text.lower().strip()

        # Indicateurs d'extrait brut de Wikipedia/site web
        raw_indicators = [
            "adresse",
            "accès et transport",
            "coordonnées",
            "modifier le code",
            "modifier wikidata",
            "autobus",
            "ratp",
            "gare",
            "métro",
            "[modifier",
            "| modifier",
            "navigation",
            "menu",
            "sommaire",
            "références",
            "voir aussi",
            "liens externes",
            "notes et références",
            "°",
            "′",
            "″",  # Coordonnées GPS
        ]

        # Si l'un de ces indicateurs est présent, c'est un extrait brut
        for indicator in raw_indicators:
            if indicator in text_lower:
                return False

        # Vérifier si ça commence par une structure de phrase naturelle
        natural_starts = [
            r"^l[ae']?\s+\w+\s+(mesure|fait|est|a|possède|compte|s'élève)",
            r"^(la|le|les|un|une)\s+\w+\s+(mesure|fait|est|a|possède|compte|s'élève)",
            r"^\w+\s+(mesure|fait|est|a|possède|compte|s'élève)",
        ]

        for pattern in natural_starts:
            if re.match(pattern, text_lower):
                return True

        # Si le texte est court et contient une mesure claire, c'est probablement naturel
        if len(text) < 200 and re.search(r"\d+\s*(mètres?|m\b|km)", text_lower):
            # Mais vérifier qu'il n'y a pas trop de bruit
            word_count = len(text.split())
            if word_count < 30:
                return True

        return False

    def _reformulate_raw_extract(self, raw_text: str, query: str) -> str:
        """
        Reformule un extrait brut en réponse naturelle.

        Extrait les informations clés (mesures, dates, faits) et les reformule
        dans une phrase naturelle.

        Args:
            raw_text: L'extrait brut à reformuler
            query: La question originale de l'utilisateur

        Returns:
            str: Une réponse reformulée naturellement
        """
        # Extraire l'entité de la question
        entity_name = self._extract_entity_from_query(query)

        # Chercher les mesures dans le texte brut
        measurement_match = re.search(
            r"(\d+(?:[,.\s]\d+)?)\s*(mètres?|m\b|km|cm)\s*(?:\[|\(|de hauteur|d'altitude)?",
            raw_text,
            re.IGNORECASE,
        )

        if measurement_match:
            value = measurement_match.group(1).replace(",", ".").replace(" ", "")
            unit = measurement_match.group(2).lower()

            # Normaliser l'unité
            if unit == "m":
                unit = "mètres"

            try:
                value_float = float(value)
                value_int = int(value_float)

                # Construire une réponse naturelle
                return self._build_natural_measurement_response(
                    entity_name, value_int, unit
                )
            except ValueError:
                pass

        # Si pas de mesure trouvée, chercher d'autres informations
        # Fallback: nettoyer l'extrait et prendre la première phrase pertinente
        sentences = re.split(r"[.!?]+", raw_text)
        for sentence in sentences:
            sentence = sentence.strip()
            # Ignorer les phrases de navigation
            if len(sentence) > 20 and len(sentence) < 300:
                lower_sent = sentence.lower()
                if not any(
                    x in lower_sent
                    for x in ["adresse", "coordonnées", "modifier", "accès", "autobus"]
                ):
                    # Nettoyer et retourner
                    cleaned = self._universal_word_spacing_fix(sentence)
                    return self._intelligent_bold_formatting(cleaned)

        # Dernier recours: retourner un message générique
        return f"📍 Informations trouvées sur **{entity_name}** - consultez les sources ci-dessous pour plus de détails."

    def _extract_entity_from_query(self, query: str) -> str:
        """Extrait le nom de l'entité depuis la question."""
        stop_words = {
            "quel",
            "quelle",
            "quels",
            "quelles",
            "comment",
            "combien",
            "pourquoi",
            "où",
            "taille",
            "hauteur",
            "fait",
            "mesure",
            "poids",
            "what",
            "which",
            "height",
            "size",
            "how",
            "tall",
            "est",
            "sont",
            "était",
            "étaient",
            "la",
            "le",
            "les",
            "l",
            "un",
            "une",
            "des",
            "du",
            "de",
            "d",
            "au",
            "aux",
        }

        words = query.split()
        entity_words = []

        for word in words:
            clean_word = word.strip("?.,!;:'\"").lower()
            # Gérer les apostrophes
            if "'" in clean_word:
                parts = clean_word.split("'")
                clean_word = parts[-1] if len(parts[-1]) > 2 else clean_word

            if len(clean_word) >= 3 and clean_word not in stop_words:
                original_word = word.strip("?.,!;:")
                if "'" in original_word:
                    original_word = original_word.split("'")[-1]
                entity_words.append(original_word)

        if entity_words:
            return " ".join(entity_words[:3]).title()
        return "cette entité"

    def _build_natural_measurement_response(
        self, entity_name: str, value: int, unit: str
    ) -> str:
        """Construit une réponse naturelle pour une mesure."""
        # Nettoyer le nom de l'entité
        entity_clean = entity_name.strip()
        for prefix in ["L'", "l'", "Le ", "le ", "La ", "la ", "Les ", "les "]:
            if entity_clean.startswith(prefix):
                entity_clean = entity_clean[len(prefix) :].strip()
                break
        entity_clean = entity_clean.title()

        # Déterminer l'article approprié
        first_letter = entity_clean[0].lower() if entity_clean else ""
        feminine_words = (
            "tour",
            "flèche",
            "antenne",
            "structure",
            "statue",
            "pyramide",
            "cathédrale",
            "église",
            "mosquée",
        )
        is_feminine = entity_clean.lower().startswith(feminine_words)

        # Construire la phrase
        if first_letter in "aeiouhéèêy":
            response = f"L'{entity_clean} mesure **{value} {unit}** de hauteur."
        elif is_feminine:
            response = f"La {entity_clean} mesure **{value} {unit}** de hauteur."
        else:
            response = f"Le {entity_clean} mesure **{value} {unit}** de hauteur."

        return response

    def _generate_answer_focused_summary(
        self,
        query: str,
        direct_answer: Optional[str],
        page_contents: List[Dict[str, Any]],
    ) -> str:
        """Génère un résumé centré sur la réponse directe - VERSION CORRIGÉE"""
        summary = ""

        if direct_answer:
            # Vérifier si la réponse est déjà bien formatée (commence par une phrase naturelle)
            # ou si c'est un extrait brut de Wikipedia qu'il faut reformuler
            is_natural_response = self._is_natural_response(direct_answer)

            if is_natural_response:
                # Réponse déjà naturelle, juste nettoyer
                cleaned_answer = self._universal_word_spacing_fix(direct_answer)
                enhanced_answer = self._intelligent_bold_formatting(cleaned_answer)
                summary += f"{enhanced_answer}\n\n"
            else:
                # Extrait brut -> essayer de reformuler naturellement
                reformulated = self._reformulate_raw_extract(direct_answer, query)
                summary += f"{reformulated}\n\n"
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
            self._search_duckduckgo_instant,  # PRIORITÉ 1: API officielle stable et rapide
            self._search_with_cloudscraper,  # PRIORITÉ 2: Contourne anti-bot si API échoue
            self._search_searxng,  # PRIORITÉ 3: Métamoteur alternatif
            self._search_with_requests,  # PRIORITÉ 4: Scraping HTML classique
            self._search_google_html,  # PRIORITÉ 5: Google en dernier recours
            self._search_brave,  # PRIORITÉ 6: Brave alternatif
            self._search_fallback,  # PRIORITÉ 7: Wikipedia fallback
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

    def _search_with_cloudscraper(self, query: str) -> List[Dict[str, Any]]:
        """
        Recherche avec cloudscraper (contourne CAPTCHA et anti-bot)
        Essaie DuckDuckGo Lite en priorité, puis Google si échec
        """
        print(
            f"🚀 [CLOUDSCRAPER] Méthode appelée - AVAILABLE={CLOUDSCRAPER_AVAILABLE}, scraper={self.scraper is not None if hasattr(self, 'scraper') else 'NO_ATTR'}"
        )

        if not CLOUDSCRAPER_AVAILABLE or self.scraper is None:
            print("⚠️ Cloudscraper non disponible ou non initialisé")
            return []

        # Essayer DuckDuckGo Lite d'abord
        print("🔍 Cloudscraper: Recherche sur DuckDuckGo Lite...")
        try:
            search_url = f"https://lite.duckduckgo.com/lite/?q={quote(query)}"
            print(f"📍 URL: {search_url[:80]}...")
            print("📍 Appel scraper.get()...")

            response = self.scraper.get(search_url, timeout=15)
            print(
                f"📍 Réponse reçue: {response.status_code}, Taille: {len(response.text)} chars"
            )
            response.raise_for_status()
            response.encoding = "utf-8"

            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            # DuckDuckGo Lite structure: chercher les résultats dans les éléments de la page
            # Après CAPTCHA, les résultats sont dans des <tr> avec des liens
            result_rows = soup.find_all("tr")
            print(f"📊 Nombre de <tr> trouvés: {len(result_rows)}")

            # Si aucun <tr>, chercher TOUS les liens HTTP dans la page
            if len(result_rows) == 0:
                print("⚠️ Aucun <tr>, recherche de TOUS les liens HTTP...")
                all_links = soup.find_all(
                    "a", href=lambda x: x and x.startswith("http")
                )
                print(f"📊 Liens HTTP trouvés: {len(all_links)}")

                # Utiliser ces liens comme résultats
                for link in all_links[: self.max_results]:
                    url = link.get("href", "")
                    title = link.get_text(strip=True)
                    if title and url and len(title) > 3:
                        results.append(
                            {
                                "title": title,
                                "snippet": title,
                                "url": url,
                                "source": "DuckDuckGo (Cloudscraper - fallback)",
                            }
                        )

                if results:
                    print(f"✅ {len(results)} résultats trouvés via fallback")
                    return results[: self.max_results]

            for row in result_rows[: self.max_results]:
                try:
                    # Chercher le lien principal
                    link = row.find("a", class_="result-link")
                    if not link:
                        # Fallback: n'importe quel lien avec href valide
                        link = row.find("a", href=lambda x: x and x.startswith("http"))

                    if link:
                        title = link.get_text(strip=True)
                        url = link.get("href", "")

                        # Chercher le snippet dans la même row
                        snippet_td = row.find("td", class_="result-snippet")
                        snippet = snippet_td.get_text(strip=True) if snippet_td else ""

                        if title and url and len(title) > 3:
                            results.append(
                                {
                                    "title": title,
                                    "snippet": snippet if snippet else title,
                                    "url": url,
                                    "source": "DuckDuckGo (Cloudscraper)",
                                }
                            )
                except Exception as parse_err:
                    print(f"⚠️ Erreur parsing row: {parse_err}")
                    continue

            print(f"📊 Résultats extraits: {len(results)}")
            if results:
                print(f"✅ Cloudscraper DDG: {len(results)} résultats trouvés")
                return results[: self.max_results]
            else:
                print("⚠️ Aucun résultat extrait des <tr>")

        except Exception as e:
            print(f"⚠️ Cloudscraper DDG échoué: {str(e)}")
            traceback.print_exc()

        # Si DDG échoue, essayer Google
        print("🔍 Cloudscraper: Tentative Google...")
        try:
            search_url = f"https://www.google.com/search?q={quote(query)}&hl=fr"
            print(f"📍 URL Google: {search_url[:80]}...")

            response = self.scraper.get(search_url, timeout=15)
            print(
                f"📍 Réponse Google: {response.status_code}, Taille: {len(response.text)} chars"
            )
            response.raise_for_status()
            response.encoding = "utf-8"

            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            # Google: chercher les divs de résultats
            result_divs = soup.find_all("div", class_="g")
            print(f"📊 Divs class='g' trouvés: {len(result_divs)}")

            if not result_divs:
                # Fallback: chercher les h3 (titres de résultats)
                result_divs = soup.find_all("div", class_=lambda x: x and "Gx5Zad" in x)
                print(f"📊 Fallback divs trouvés: {len(result_divs)}")

            # Si toujours rien, chercher directement les h3
            if not result_divs:
                h3_tags = soup.find_all("h3")
                print(f"📊 H3 tags trouvés: {len(h3_tags)}")

                # Essayer d'utiliser les h3 directement
                for h3 in h3_tags[: self.max_results]:
                    parent = h3.parent
                    while parent and parent.name != "a":
                        parent = parent.parent

                    if parent and parent.name == "a":
                        url = parent.get("href", "")
                        if url.startswith("/url?q="):
                            url = url.split("/url?q=")[1].split("&")[0]

                        if url.startswith("http"):
                            results.append(
                                {
                                    "title": h3.get_text(strip=True),
                                    "snippet": h3.get_text(strip=True),
                                    "url": url,
                                    "source": "Google (Cloudscraper - h3 fallback)",
                                }
                            )

                if results:
                    print(
                        f"✅ Cloudscraper Google (h3): {len(results)} résultats trouvés"
                    )
                    return results[: self.max_results]

            for div in result_divs[: self.max_results]:
                try:
                    # Titre
                    h3 = div.find("h3")
                    if not h3:
                        continue

                    title = h3.get_text(strip=True)

                    # URL
                    link = div.find("a", href=True)
                    if not link:
                        continue

                    url = link.get("href", "")

                    # Nettoyer l'URL Google
                    if url.startswith("/url?q="):
                        url = url.split("/url?q=")[1].split("&")[0]

                    # Snippet
                    snippet_div = div.find(
                        "div", class_=lambda x: x and ("VwiC3b" in x or "IsZvec" in x)
                    )
                    snippet = snippet_div.get_text(strip=True) if snippet_div else ""

                    if title and url.startswith("http"):
                        results.append(
                            {
                                "title": title,
                                "snippet": snippet if snippet else title,
                                "url": url,
                                "source": "Google (Cloudscraper)",
                            }
                        )
                except Exception:
                    continue

            if results:
                print(f"✅ Cloudscraper Google: {len(results)} résultats trouvés")
                return results[: self.max_results]

        except Exception as e:
            print(f"⚠️ Cloudscraper Google échoué: {str(e)}")

        return []

    def _search_duckduckgo_instant(self, query: str) -> List[Dict[str, Any]]:
        """Recherche via l'API instant de DuckDuckGo - AMÉLIORÉE"""
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

        # Résultat instant (Abstract)
        if data.get("Abstract") and len(data.get("Abstract", "")) > 20:
            results.append(
                {
                    "title": data.get("Heading", "Information"),
                    "snippet": data.get("Abstract", ""),
                    "url": data.get("AbstractURL", ""),
                    "source": "DuckDuckGo Instant",
                }
            )

        # Résultats de topics (augmenté à max_results au lieu de 3)
        for topic in data.get("RelatedTopics", []):
            if isinstance(topic, dict) and topic.get("Text"):
                # Extraire un titre propre depuis l'URL ou le texte
                first_url = topic.get("FirstURL", "")
                if first_url:
                    # Extraire le dernier segment de l'URL comme titre
                    title = (
                        first_url.split("/")[-1].replace("_", " ").replace("%20", " ")
                    )
                else:
                    # Utiliser les 50 premiers caractères du texte comme titre
                    title = topic.get("Text", "")[:50] + "..."

                results.append(
                    {
                        "title": title,
                        "snippet": topic.get("Text", ""),
                        "url": first_url,
                        "source": "DuckDuckGo",
                    }
                )
            elif isinstance(topic, dict) and topic.get("Topics"):
                # RelatedTopics peut contenir des sous-topics (pour les catégories)
                for subtopic in topic.get("Topics", []):
                    if subtopic.get("Text"):
                        first_url = subtopic.get("FirstURL", "")
                        title = (
                            first_url.split("/")[-1]
                            .replace("_", " ")
                            .replace("%20", " ")
                            if first_url
                            else subtopic.get("Text", "")[:50]
                        )

                        results.append(
                            {
                                "title": title,
                                "snippet": subtopic.get("Text", ""),
                                "url": first_url,
                                "source": "DuckDuckGo",
                            }
                        )

        # Limiter au nombre max de résultats
        final_results = results[: self.max_results]

        if final_results:
            print(
                f"✅ DuckDuckGo Instant API: {len(final_results)} résultats (Abstract: {bool(data.get('Abstract'))}, Topics: {len(data.get('RelatedTopics', []))})"
            )

        return final_results

    def _search_searxng(self, query: str) -> List[Dict[str, Any]]:
        """
        Recherche via SearXNG (meta-moteur open-source avec API JSON)
        Utilise des instances publiques - pas de scraping, vraie API
        """
        # Liste d'instances SearXNG publiques fiables
        searxng_instances = [
            "https://search.bus-hit.me",
            "https://searx.be",
            "https://search.ononoki.org",
            "https://searx.work",
        ]

        for instance_url in searxng_instances:
            try:
                # SearXNG accepte les requêtes JSON
                api_url = f"{instance_url}/search"

                params = {
                    "q": query,
                    "format": "json",
                    "language": "fr",
                    "safesearch": 0,
                }

                headers = {
                    "User-Agent": self.user_agent,
                    "Accept": "application/json",
                }

                response = requests.get(
                    api_url, params=params, headers=headers, timeout=10
                )

                # Si cette instance ne répond pas, essayer la suivante
                if response.status_code != 200:
                    continue

                data = response.json()
                results = []

                # SearXNG retourne les résultats dans data['results']
                for item in data.get("results", [])[: self.max_results]:
                    title = item.get("title", "")
                    url = item.get("url", "")
                    content = item.get("content", "") or item.get("snippet", "")

                    if title and url:
                        results.append(
                            {
                                "title": title,
                                "snippet": content,
                                "url": url,
                                "source": f"SearXNG ({instance_url})",
                            }
                        )

                if results:
                    print(
                        f"✅ SearXNG ({instance_url}): {len(results)} résultats trouvés"
                    )
                    return results

            except Exception as e:
                # Si cette instance échoue, essayer la suivante
                print(f"⚠️ SearXNG instance {instance_url} échouée: {str(e)}")
                continue

        # Aucune instance n'a fonctionné
        return []

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

        response = requests.get(
            search_url, headers=headers, timeout=self.timeout, allow_redirects=True
        )
        response.raise_for_status()

        # CORRECTION: Forcer l'encodage UTF-8 pour éviter les problèmes de décodage
        response.encoding = "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        # Essayer plusieurs sélecteurs CSS pour plus de robustesse
        result_selectors = [
            ("div", {"class": "result"}),
            ("div", {"class": "results_links"}),
            ("div", {"class": "web-result"}),
            ("div", {"id": lambda x: x and x.startswith("r1-")}),
        ]

        for selector_tag, selector_attrs in result_selectors:
            result_divs = soup.find_all(
                selector_tag, selector_attrs, limit=self.max_results
            )
            if result_divs:
                break

        for result_div in result_divs:
            try:
                # Essayer différents sélecteurs pour le titre
                title_elem = (
                    result_div.find("a", class_="result__a")
                    or result_div.find("a", class_="result-link")
                    or result_div.find("h2").find("a")
                    if result_div.find("h2")
                    else None
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

        return results[: self.max_results]

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

        response = requests.get(
            search_url, headers=headers, timeout=self.timeout, allow_redirects=True
        )
        response.raise_for_status()

        # CORRECTION: Forcer l'encodage UTF-8 pour éviter les problèmes de décodage
        response.encoding = "utf-8"

        # Utiliser response.text au lieu de response.content pour avoir du texte déjà décodé
        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        # DuckDuckGo Lite utilise une structure de table simple
        result_tables = soup.find_all("table", class_="result-table")

        for table in result_tables[: self.max_results]:
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
        return results[: self.max_results]

    def _search_brave(self, query: str) -> List[Dict[str, Any]]:
        """Recherche via Brave Search (moteur alternatif sans API key)"""
        search_url = f"https://search.brave.com/search?q={quote(query)}"

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

        time.sleep(0.5)  # Éviter le rate limiting

        response = requests.get(
            search_url, headers=headers, timeout=self.timeout, allow_redirects=True
        )
        response.raise_for_status()

        # Forcer l'encodage UTF-8
        response.encoding = "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        # Brave Search utilise des divs avec data-type="web"
        result_divs = soup.find_all("div", {"data-type": "web"}, limit=self.max_results)

        # Fallback: chercher les résultats avec d'autres sélecteurs
        if not result_divs:
            result_divs = soup.find_all(
                "div",
                class_=lambda x: x and "snippet" in x.lower(),
                limit=self.max_results,
            )

        for div in result_divs:
            try:
                # Chercher le titre
                title_elem = (
                    div.find("a", class_=lambda x: x and "result" in x.lower())
                    or div.find("h4")
                    or div.find("h3")
                )

                # Chercher le snippet
                snippet_elem = div.find(
                    "p", class_=lambda x: x and "snippet" in x.lower()
                ) or div.find("p")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")

                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    if title and len(title) > 3:
                        results.append(
                            {
                                "title": title,
                                "snippet": snippet if snippet else title,
                                "url": url if url.startswith("http") else "",
                                "source": "Brave Search",
                            }
                        )
            except Exception as e:
                print(f"⚠️ Erreur lors du parsing Brave Search: {str(e)}")
                continue

        print(f"✅ Brave Search: {len(results)} résultats trouvés")
        return results[: self.max_results]

    def _search_google_html(self, query: str) -> List[Dict[str, Any]]:
        """Recherche Google via scraping HTML simple"""
        search_url = f"https://www.google.com/search?q={quote(query)}&hl=fr"

        current_ua = self._get_next_user_agent()

        headers = {
            "User-Agent": current_ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.google.com/",
        }

        time.sleep(1)  # Délai plus long pour Google

        response = requests.get(
            search_url, headers=headers, timeout=self.timeout, allow_redirects=True
        )
        response.raise_for_status()

        # Forcer l'encodage UTF-8
        response.encoding = "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        # Google utilise des divs avec class contenant "g" pour les résultats
        # Essayer plusieurs sélecteurs pour robustesse
        result_divs = soup.find_all("div", class_="g", limit=self.max_results)

        # Fallback si premier sélecteur ne fonctionne pas
        if not result_divs:
            result_divs = soup.find_all(
                "div", attrs={"data-sokoban-container": True}, limit=self.max_results
            )

        # Autre fallback
        if not result_divs:
            result_divs = soup.select("div#search div.tF2Cxc", limit=self.max_results)

        for div in result_divs:
            try:
                # Titre - chercher dans h3 ou lien
                title_elem = div.find("h3") or div.find("a")

                # URL - chercher le premier lien
                link_elem = div.find("a", href=True)

                # Snippet - chercher les spans ou divs de description
                snippet_elem = (
                    div.find(
                        "span",
                        class_=lambda x: x and ("st" in x.lower() or "aCOpRe" in x),
                    )
                    or div.find(
                        "div",
                        class_=lambda x: x
                        and ("VwiC3b" in x or "snippet" in x.lower()),
                    )
                    or div.find("div", attrs={"data-sncf": "1"})
                )

                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    url = link_elem.get("href", "")

                    # Nettoyer l'URL Google (enlever les redirections /url?q=)
                    if url.startswith("/url?q="):
                        url = url.split("/url?q=")[1].split("&")[0]

                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    if title and len(title) > 3 and url.startswith("http"):
                        results.append(
                            {
                                "title": title,
                                "snippet": snippet if snippet else title,
                                "url": url,
                                "source": "Google Search",
                            }
                        )
            except Exception as e:
                print(f"⚠️ Erreur lors du parsing Google: {str(e)}")
                continue

        print(f"✅ Google Search: {len(results)} résultats trouvés")
        return results[: self.max_results]

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

            suggestion_response = requests.get(
                api_url, params=suggestion_params, headers=headers, timeout=10
            )
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
                clean_word = word.strip("?.,!;:")
                # Majuscule OU mot long dans question de type "burj khalifa"
                if len(clean_word) >= 4 and clean_word.lower() not in [
                    "quel",
                    "quelle",
                    "comment",
                    "taille",
                    "hauteur",
                    "fait",
                    "mesure",
                ]:
                    potential_names.append(clean_word)

            has_proper_noun = (
                len(potential_names) >= 2
            )  # Au moins 2 mots significatifs (ex: "burj khalifa")
            search_limit = 5 if has_proper_noun else 3

            if has_proper_noun:
                direct_search_term = " ".join(potential_names)
                print(
                    f"🎯 Entité détectée: '{direct_search_term}', recherche élargie à {search_limit} pages + recherche directe"
                )

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
                direct_article_title = (
                    direct_search_term.title()
                )  # "burj khalifa" → "Burj Khalifa"
                print(
                    f"🎯 Tentative de récupération directe de l'article: '{direct_article_title}'"
                )

                # D'abord, chercher une suggestion de Wikipedia si l'orthographe est incorrecte
                article_title_to_fetch = direct_article_title

                try:
                    # Utiliser l'API opensearch pour obtenir des suggestions
                    opensearch_params = {
                        "action": "opensearch",
                        "search": direct_search_term,
                        "limit": 5,
                        "namespace": 0,
                        "format": "json",
                    }

                    opensearch_response = requests.get(
                        api_url, params=opensearch_params, headers=headers, timeout=10
                    )
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
                                score = fuzz.ratio(
                                    direct_search_term.lower(), suggestion.lower()
                                )
                                if score > best_score:
                                    best_score = score
                                    best_match = suggestion

                            # Si on a un bon match (score > 70), l'utiliser
                            if best_match and best_score > 70:
                                if best_match.lower() != direct_article_title.lower():
                                    print(
                                        f"📝 Correction orthographique: '{direct_article_title}' → '{best_match}' (score: {best_score})"
                                    )
                                    article_title_to_fetch = best_match
                                else:
                                    print(
                                        f"✓ Orthographe correcte confirmée (score: {best_score})"
                                    )
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

                    direct_response = requests.get(
                        api_url,
                        params=direct_content_params,
                        headers=headers,
                        timeout=10,
                    )
                    direct_response.raise_for_status()
                    direct_data = direct_response.json()

                    direct_pages = direct_data.get("query", {}).get("pages", {})
                    for page_id, page_data in direct_pages.items():
                        if page_id != "-1":  # -1 signifie page not found
                            extract = page_data.get("extract", "")
                            if extract and len(extract) > 100:
                                print(
                                    f"✅ Article direct trouvé: {len(extract)} caractères"
                                )
                                results.append(
                                    {
                                        "title": page_data.get(
                                            "title", article_title_to_fetch
                                        ),
                                        "snippet": extract[:500],
                                        "full_content": extract,
                                        "url": f"https://fr.wikipedia.org/wiki/{quote(page_data.get('title', article_title_to_fetch))}",
                                        "source": "Wikipedia FR (Article direct)",
                                    }
                                )
                                break
                except Exception as e:
                    print(f"⚠️ Recherche directe échouée: {str(e)}")

            response = requests.get(
                api_url, params=search_params, headers=headers, timeout=10
            )

            print(f"📡 Status code: {response.status_code}")

            response.raise_for_status()

            search_data = response.json()

            print(f"📊 Réponse JSON reçue: {len(str(search_data))} caractères")

            if "query" in search_data and "search" in search_data["query"]:
                print(
                    f"🔍 Wikipedia FR: {len(search_data['query']['search'])} pages trouvées"
                )

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

                        content_response = requests.get(
                            api_url, params=content_params, headers=headers, timeout=10
                        )
                        content_response.raise_for_status()
                        content_data = content_response.json()

                        # Extraire le contenu
                        pages = content_data.get("query", {}).get("pages", {})
                        for page_data in pages.values():
                            extract = page_data.get("extract", "")

                            if extract and len(extract) > 50:
                                print(f"✅ Contenu récupéré: {len(extract)} caractères")
                                results.append(
                                    {
                                        "title": title,
                                        "snippet": extract[
                                            :500
                                        ],  # Premier 500 caractères
                                        "full_content": extract,  # Contenu complet
                                        "url": f"https://fr.wikipedia.org/wiki/{quote(title)}",
                                        "source": "Wikipedia FR",
                                    }
                                )
                                break  # Un seul résultat par page
                            else:
                                print(f"⚠️ Contenu vide ou trop court pour: {title}")

                    except Exception as e:
                        print(
                            f"❌ Erreur lors de la récupération du contenu de '{title}': {str(e)}"
                        )
                        continue

            print(f"✅ Wikipedia FR: {len(results)} résultats avec contenu complet")
            return results[: self.max_results]

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

            suggestion_response = requests.get(
                api_url, params=suggestion_params, headers=headers, timeout=10
            )
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
                clean_word = word.strip("?.,!;:")
                # Majuscule OU mot long dans question de type "burj khalifa"
                if len(clean_word) >= 4 and clean_word.lower() not in [
                    "what",
                    "which",
                    "size",
                    "height",
                    "tall",
                    "quel",
                    "quelle",
                    "comment",
                    "taille",
                    "hauteur",
                    "fait",
                    "mesure",
                ]:
                    potential_names.append(clean_word)

            has_proper_noun = (
                len(potential_names) >= 2
            )  # Au moins 2 mots significatifs (ex: "burj khalifa")
            search_limit = 5 if has_proper_noun else 3

            if has_proper_noun:
                direct_search_term = " ".join(potential_names)
                print(
                    f"🎯 Entité détectée: '{direct_search_term}', recherche élargie à {search_limit} pages + recherche directe"
                )

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
                direct_article_title = (
                    direct_search_term.title()
                )  # "burj khalifa" → "Burj Khalifa"
                print(
                    f"🎯 Tentative de récupération directe de l'article EN: '{direct_article_title}'"
                )

                # D'abord, chercher une suggestion de Wikipedia si l'orthographe est incorrecte
                article_title_to_fetch = direct_article_title

                try:
                    # Utiliser l'API opensearch pour obtenir des suggestions
                    opensearch_params = {
                        "action": "opensearch",
                        "search": direct_search_term,
                        "limit": 5,
                        "namespace": 0,
                        "format": "json",
                    }

                    opensearch_response = requests.get(
                        api_url, params=opensearch_params, headers=headers, timeout=10
                    )
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
                                score = fuzz.ratio(
                                    direct_search_term.lower(), suggestion.lower()
                                )
                                if score > best_score:
                                    best_score = score
                                    best_match = suggestion

                            # Si on a un bon match (score > 70), l'utiliser
                            if best_match and best_score > 70:
                                if best_match.lower() != direct_article_title.lower():
                                    print(
                                        f"📝 Correction orthographique EN: '{direct_article_title}' → '{best_match}' (score: {best_score})"
                                    )
                                    article_title_to_fetch = best_match
                                else:
                                    print(
                                        f"✓ Orthographe correcte confirmée EN (score: {best_score})"
                                    )
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

                    direct_response = requests.get(
                        api_url,
                        params=direct_content_params,
                        headers=headers,
                        timeout=10,
                    )
                    direct_response.raise_for_status()
                    direct_data = direct_response.json()

                    direct_pages = direct_data.get("query", {}).get("pages", {})
                    for page_id, page_data in direct_pages.items():
                        if page_id != "-1":  # -1 signifie page not found
                            extract = page_data.get("extract", "")
                            if extract and len(extract) > 100:
                                print(
                                    f"✅ Article direct EN trouvé: {len(extract)} caractères"
                                )
                                results.append(
                                    {
                                        "title": page_data.get(
                                            "title", article_title_to_fetch
                                        ),
                                        "snippet": extract[:500],
                                        "full_content": extract,
                                        "url": f"https://en.wikipedia.org/wiki/{quote(page_data.get('title', article_title_to_fetch))}",
                                        "source": "Wikipedia EN (Article direct)",
                                    }
                                )
                                break
                except Exception as e:
                    print(f"⚠️ Recherche directe EN échouée: {str(e)}")

            response = requests.get(
                api_url, params=search_params, headers=headers, timeout=10
            )

            print(f"📡 Status code: {response.status_code}")

            response.raise_for_status()

            search_data = response.json()

            print(f"📊 Réponse JSON reçue: {len(str(search_data))} caractères")

            results = []

            if "query" in search_data and "search" in search_data["query"]:
                print(
                    f"🔍 Wikipedia EN: {len(search_data['query']['search'])} pages trouvées"
                )

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

                        content_response = requests.get(
                            api_url, params=content_params, headers=headers, timeout=10
                        )
                        content_response.raise_for_status()
                        content_data = content_response.json()

                        # Extraire le contenu
                        pages = content_data.get("query", {}).get("pages", {})
                        for _, page_data in pages.items():
                            extract = page_data.get("extract", "")

                            if extract and len(extract) > 50:
                                print(f"✅ Contenu récupéré: {len(extract)} caractères")
                                results.append(
                                    {
                                        "title": title,
                                        "snippet": extract[
                                            :500
                                        ],  # Premier 500 caractères
                                        "full_content": extract,  # Contenu complet
                                        "url": f"https://en.wikipedia.org/wiki/{quote(title)}",
                                        "source": "Wikipedia EN",
                                    }
                                )
                                break  # Un seul résultat par page
                            else:
                                print(f"⚠️ Contenu vide ou trop court pour: {title}")

                    except Exception as e:
                        print(
                            f"❌ Erreur lors de la récupération du contenu de '{title}': {str(e)}"
                        )
                        continue

            print(f"✅ Wikipedia EN: {len(results)} résultats avec contenu complet")
            return results[: self.max_results]

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
            for element in soup(
                [
                    "script",
                    "style",
                    "nav",
                    "footer",
                    "header",
                    "aside",
                    "iframe",
                    "noscript",
                ]
            ):
                element.decompose()

            # Extraire le contenu principal
            main_content = ""

            # Essayer de trouver le contenu principal avec différentes stratégies
            for selector in [
                "main",
                "article",
                '[role="main"]',
                ".content",
                ".article",
                ".post",
                ".entry-content",
                "#content",
            ]:
                content_elem = soup.select_one(selector)
                if content_elem:
                    main_content = content_elem.get_text(separator="\n", strip=True)
                    break

            # Fallback: extraire tous les paragraphes
            if not main_content or len(main_content) < 100:
                paragraphs = soup.find_all("p")
                main_content = "\n".join(
                    [
                        p.get_text(strip=True)
                        for p in paragraphs
                        if len(p.get_text(strip=True)) > 30
                    ]
                )

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
                if len(line) > 20 and not line.startswith(
                    ("©", "Cookie", "JavaScript")
                ):
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
                return (
                    f"❌ Erreur HTTP {e.response.status_code} lors de l'accès à: {url}"
                )
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
        sentences = re.split(r"[.!?]+", content_for_analysis)
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
        stop_words = {
            "le",
            "la",
            "les",
            "un",
            "une",
            "des",
            "de",
            "du",
            "et",
            "ou",
            "mais",
            "pour",
            "dans",
            "sur",
            "avec",
            "est",
            "sont",
            "qui",
            "que",
            "ce",
            "se",
            "ne",
            "pas",
            "plus",
            "comme",
            "tout",
            "nous",
            "vous",
            "leur",
            "leurs",
            "son",
            "sa",
            "ses",
        }
        keywords = [w for w in words if len(w) > 4 and w not in stop_words]

        # Compter les occurrences
        keyword_counts = Counter(keywords)
        top_keywords = [kw for kw, count in keyword_counts.most_common(5)]

        if top_keywords:
            summary += f"🏷️ **Mots-clés:** {', '.join(top_keywords)}\n\n\n"

        return summary


# Alias pour remplacer l'ancienne classe
InternetSearchEngine = EnhancedInternetSearchEngine
