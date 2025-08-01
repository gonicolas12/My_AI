"""
Module de recherche internet avec extraction de réponse directe
Version corrigée sans doublons ni erreurs de syntaxe
"""

import requests
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
import concurrent.futures
import threading
from collections import Counter, defaultdict
import string


class EnhancedInternetSearchEngine:
    """Moteur de recherche internet avec extraction de réponse directe"""
    
    def __init__(self):
        self.search_apis = {
            "duckduckgo": "https://api.duckduckgo.com/",
            "bing": "https://api.bing.microsoft.com/v7.0/search",
            "google_custom": "https://www.googleapis.com/customsearch/v1"
        }
        
        # Configuration
        self.max_results = 8
        self.max_content_length = 3000
        self.timeout = 10
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        
        # Cache des résultats récents
        self.search_cache = {}
        self.cache_duration = 3600
        
        # Patterns pour l'extraction de réponses directes
        self.answer_patterns = self._init_answer_patterns()
        
    def _init_answer_patterns(self) -> Dict[str, List[str]]:
        """Initialise les patterns pour extraire des réponses directes"""
        return {
            "taille": [
                r"(?:mesure|fait|taille|hauteur)(?:\s+de)?\s+([\d,]+\.?\d*)\s*(mètres?|m|km|centimètres?|cm)",
                r"([\d,]+\.?\d*)\s*(mètres?|m|km|centimètres?|cm)(?:\s+de|d')?\s+(?:haut|hauteur|taille)",
                r"(?:est|fait)(?:\s+de)?\s+([\d,]+\.?\d*)\s*(mètres?|m|km)"
            ],
            "poids": [
                r"(?:pèse|poids)(?:\s+de)?\s+([\d,]+\.?\d*)\s*(kilogrammes?|kg|tonnes?|grammes?|g)",
                r"([\d,]+\.?\d*)\s*(kilogrammes?|kg|tonnes?|grammes?|g)(?:\s+de|d')?\s+(?:poids|lourd)"
            ],
            "population": [
                r"(?:population|habitants?)(?:\s+de)?\s+([\d\s,]+\.?\d*)",
                r"([\d\s,]+\.?\d*)(?:\s+d')?\s*habitants?",
                r"compte\s+([\d\s,]+\.?\d*)(?:\s+d')?\s*habitants?"
            ],
            "date": [
                r"(?:en|depuis|dans|créé|fondé|construit|né)\s+(\d{4})",
                r"(\d{1,2})\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})",
                r"(\d{4})(?:\s*-\s*\d{4})?"
            ],
            "prix": [
                r"(?:coûte|prix|vaut)\s+([\d,]+\.?\d*)\s*(euros?|dollars?|\$|€)",
                r"([\d,]+\.?\d*)\s*(euros?|dollars?|\$|€)(?:\s+pour|de)?"
            ],
            "definition": [
                r"(?:est|sont)\s+([^.!?]{20,100})",
                r"([^.!?]{20,100})(?:\s+est|\s+sont)",
                r"(?:c'est|ce sont)\s+([^.!?]{20,100})"
            ]
        }
    
    def search_and_summarize(self, query: str, context: Dict[str, Any] = None) -> str:
        """Recherche sur internet et extrait la réponse directe"""
        try:
            print(f"🔍 Recherche internet pour: '{query}'")
            
            # Vérifier le cache
            cache_key = self._generate_cache_key(query)
            if self._is_cache_valid(cache_key):
                print("📋 Résultats trouvés en cache")
                return self.search_cache[cache_key]["summary"]
            
            # Effectuer la recherche
            search_results = self._perform_search(query)
            
            if not search_results:
                return f"❌ Désolé, je n'ai pas pu trouver d'informations sur '{query}'. Vérifiez votre connexion internet."
            
            # Extraire le contenu des pages
            page_contents = self._extract_page_contents(search_results)
            
            # Extraire la réponse directe
            direct_answer = self._extract_direct_answer(query, page_contents)
            
            # Générer le résumé
            summary = self._generate_answer_focused_summary(query, direct_answer, page_contents)
            
            # Mettre en cache
            self._cache_results(cache_key, summary, search_results)
            
            return summary
            
        except Exception as e:
            print(f"❌ Erreur lors de la recherche: {str(e)}")
            return f"Désolé, une erreur s'est produite lors de la recherche internet : {str(e)}"
    
    def _extract_direct_answer(self, query: str, page_contents: List[Dict[str, Any]]) -> Optional[str]:
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
            return self._extract_measurement_answer(query, candidate_sentences)
        elif question_type == "definition":
            return self._extract_definition_answer(query, candidate_sentences)
        elif question_type == "date":
            return self._extract_date_answer(query, candidate_sentences)
        else:
            return self._extract_general_answer(query, candidate_sentences)
    
    def _analyze_question_type(self, query: str) -> str:
        """Analyse le type de question pour adapter l'extraction"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["taille", "hauteur", "mesure", "fait", "mètres", "long", "large"]):
            return "measurement"
        
        if any(word in query_lower for word in ["qu'est-ce", "c'est quoi", "qui est", "que signifie", "définition"]):
            return "definition"
        
        if any(word in query_lower for word in ["quand", "date", "année", "créé", "fondé", "né", "construit"]):
            return "date"
        
        if any(word in query_lower for word in ["combien", "quel", "quelle", "prix", "coût", "population", "nombre"]):
            return "factual"
        
        return "general"
    
    def _extract_candidate_sentences(self, page_contents: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Extrait les phrases candidates contenant potentiellement la réponse"""
        candidates = []
        query_words = set(word.lower().strip(string.punctuation) for word in query.split() if len(word) > 2)
        
        for page in page_contents:
            for content_field in ["snippet", "full_content"]:
                text = page.get(content_field, "")
                if text:
                    # Découper en phrases
                    sentences = re.split(r'(?<=[.!?])\s+', text)
                    
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if len(sentence) < 10 or len(sentence) > 500:
                            continue
                        
                        # Calculer la pertinence
                        sentence_words = set(word.lower().strip(string.punctuation) for word in sentence.split())
                        relevance_score = len(query_words.intersection(sentence_words))
                        
                        # Bonus pour les phrases avec des nombres ou des faits précis
                        if re.search(r'\d+', sentence):
                            relevance_score += 2
                        
                        # Bonus pour les débuts de phrase indicatifs
                        if any(sentence.lower().startswith(start) for start in 
                               ["la", "le", "il", "elle", "c'est", "ce sont", "on trouve", "situé"]):
                            relevance_score += 1
                        
                        if relevance_score > 0:
                            candidates.append({
                                "sentence": sentence,
                                "relevance": relevance_score,
                                "source": page.get("title", "Source inconnue"),
                                "url": page.get("url", "")
                            })
        
        # Trier par pertinence
        candidates.sort(key=lambda x: x["relevance"], reverse=True)
        return candidates[:20]
    
    def _extract_factual_answer(self, query: str, candidates: List[Dict[str, Any]]) -> Optional[str]:
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
                    answer_key = f"{match[0]} {match[1]}" if len(match) > 1 else match[0]
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
                    cleaned_sentence = self._universal_word_spacing_fix(candidate["sentence"])
                    return cleaned_sentence.strip()
        
        return None
    
    def _extract_measurement_answer(self, query: str, candidates: List[Dict[str, Any]]) -> Optional[str]:
        """Extrait une réponse de mesure spécifique"""
        measurement_patterns = [
            r"(?:mesure|fait|taille|hauteur)(?:\s+de)?\s+([\d,]+\.?\d*)\s*(mètres?|m|km|centimètres?|cm)",
            r"([\d,]+\.?\d*)\s*(mètres?|m|km|centimètres?|cm)(?:\s+de|d')?\s+(?:haut|hauteur|taille)",
            r"(?:s'élève à|atteint)\s+([\d,]+\.?\d*)\s*(mètres?|m|km)"
        ]
        
        measurements = Counter()
        source_sentences = {}
        
        for candidate in candidates:
            sentence = candidate["sentence"]
            for pattern in measurement_patterns:
                matches = re.findall(pattern, sentence, re.IGNORECASE)
                for match in matches:
                    measurement_key = f"{match[0]} {match[1]}"
                    measurements[measurement_key] += candidate["relevance"]
                    if measurement_key not in source_sentences:
                        source_sentences[measurement_key] = sentence
        
        if measurements:
            best_measurement = measurements.most_common(1)[0][0]
            cleaned_sentence = self._universal_word_spacing_fix(source_sentences[best_measurement])
            return cleaned_sentence.strip()
        
        return None
    
    def _extract_definition_answer(self, query: str, candidates: List[Dict[str, Any]]) -> Optional[str]:
        """Extrait une définition"""
        definition_patterns = [
            r"(?:est|sont)\s+([^.!?]{20,150})",
            r"(?:c'est|ce sont)\s+([^.!?]{20,150})",
            r"([^.!?]{20,150})(?:\s+est|\s+sont)"
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
            cleaned_sentence = self._universal_word_spacing_fix(source_sentences[best_definition])
            return cleaned_sentence.strip()
        
        return None
    
    def _extract_date_answer(self, query: str, candidates: List[Dict[str, Any]]) -> Optional[str]:
        """Extrait une réponse de date"""
        date_patterns = [
            r"(?:en|depuis|dans|créé|fondé|construit|né|inauguré)\s+(\d{4})",
            r"(\d{1,2})\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})",
            r"(\d{4})(?:\s*-\s*\d{4})?"
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
            cleaned_sentence = self._universal_word_spacing_fix(source_sentences[best_date])
            return cleaned_sentence.strip()
        
        return None
    
    def _extract_general_answer(self, query: str, candidates: List[Dict[str, Any]]) -> Optional[str]:
        """Extrait une réponse générale basée sur le consensus"""
        if not candidates:
            return None
        
        # Analyser les mots-clés de la question
        query_words = set(word.lower().strip(string.punctuation) for word in query.split() if len(word) > 2)
        
        # Calculer un score de consensus pour chaque phrase
        sentence_scores = {}
        
        for candidate in candidates:
            sentence = candidate["sentence"]
            
            # Score basé sur la pertinence originale
            score = candidate["relevance"]
            
            # Bonus pour les phrases contenant plusieurs mots-clés de la question
            sentence_words = set(word.lower().strip(string.punctuation) for word in sentence.split())
            keyword_overlap = len(query_words.intersection(sentence_words))
            score += keyword_overlap * 2
            
            # Bonus pour les phrases avec des informations précises (nombres, dates, etc.)
            if re.search(r'\d+', sentence):
                score += 3
            
            # Bonus pour les phrases qui semblent être des réponses directes
            if any(sentence.lower().startswith(start) for start in 
                   ["la", "le", "il", "elle", "c'est", "ce sont", "on trouve", "située", "situé"]):
                score += 2
            
            sentence_scores[sentence] = score
        
        # Prendre la phrase avec le meilleur score
        if sentence_scores:
            best_sentence = max(sentence_scores, key=sentence_scores.get)
            cleaned_sentence = self._universal_word_spacing_fix(best_sentence)
            return cleaned_sentence.strip()
        
        return None
    
    def _generate_answer_focused_summary(self, query: str, direct_answer: Optional[str], 
                                       page_contents: List[Dict[str, Any]]) -> str:
        """Génère un résumé centré sur la réponse directe"""
        summary = f""
        
        if direct_answer:
            # Nettoyer la réponse directe et ajouter des mots en gras
            cleaned_answer = self._enhance_answer_formatting(direct_answer)
            summary += f"{cleaned_answer}\n\n"
        else:
            # Si pas de réponse directe, essayer un résumé intelligent concentré
            key_info = self._extract_concentrated_summary(query, page_contents)
            cleaned_info = self._enhance_answer_formatting(key_info)
            summary += f"📍 **Information trouvée :**\n{cleaned_info}\n\n"
        
        # Ajouter les sources principales - FORMAT SIMPLIFIÉ
        summary += "🔗 Sources :"
        
        for result in page_contents[:3]:  # Top 3 sources
            if result.get("title") and result.get("url"):
                title = self._clean_title(result["title"])
                url = result.get("url")
                
                if url and url.startswith("http"):
                    # Format simple: numéro + lien cliquable
                    summary += f"[{title}]({url}) "
                else:
                    summary += f"{title}"
        
        return summary + "\n"
    
    def _enhance_answer_formatting(self, text: str) -> str:
        """Améliore le formatage de la réponse - VERSION UNIVERSELLE"""
        if not text:
            return text
        
        # 1. CORRECTION UNIVERSELLE DES ESPACEMENTS
        cleaned_text = self._universal_word_spacing_fix(text)
        
        # 2. FORMATAGE INTELLIGENT DES MOTS IMPORTANTS
        formatted_text = self._intelligent_bold_formatting(cleaned_text)
        
        return formatted_text
    
    def _universal_word_spacing_fix(self, text: str) -> str:
        """Correction universelle des problèmes d'espacement pour TOUTES les recherches"""
        import re
        
        # Étape 1: Séparer TOUS les mots collés (minuscule suivie de majuscule)
        # Ceci fonctionne pour: appelaitlatour, drapeaufrançais, motscollés, etc.
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        # Étape 2: Séparer les mots collés avec des chiffres
        # Ex: "mesure300mètres" -> "mesure 300 mètres"
        text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
        text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)
        
        # Étape 3: Corriger la ponctuation collée
        # Ex: "mots.Autres" -> "mots. Autres"
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        text = re.sub(r'([,;:])([a-zA-Z])', r'\1 \2', text)
        
        # Étape 4: Séparer les mots de liaison collés courants
        # Ex: "motde", "elet", "avec", etc.
        liaison_words = ['de', 'du', 'des', 'le', 'la', 'les', 'un', 'une', 'et', 'ou', 'avec', 
                        'dans', 'sur', 'pour', 'par', 'elle', 'il', 'qui', 'que', 'son', 'sa', 
                        'ses', 'cette', 'ce', 'ces', 'tout', 'tous', 'plus']
        
        for word in liaison_words:
            # Séparer si collé à droite: "mot" + "de" + "Autre"
            pattern = f'([a-z])({word})([A-Z])'
            text = re.sub(pattern, r'\1 \2 \3', text, flags=re.IGNORECASE)
        
        # Étape 5: Nettoyer les espaces multiples
        text = re.sub(r'\s+', ' ', text)
        
        # Étape 6: Corriger les espaces autour de la ponctuation
        text = re.sub(r'\s+([.!?:;,])', r'\1', text)
        text = re.sub(r'([.!?:;,])([a-zA-Z])', r'\1 \2', text)
        
        return text.strip()
    
    def _intelligent_bold_formatting(self, text: str) -> str:
        """Formatage intelligent en gras - UNIVERSEL pour tous types de données"""
        import re
        
        # 1. CHIFFRES + UNITÉS (universel pour toutes mesures)
        # Mètres, kilomètres, centimètres
        text = re.sub(r'(\d+(?:[,.\s]\d+)?)\s*(mètres?|m\b|km|centimètres?|cm|kilomètres?)', 
                     r'**\1 \2**', text, flags=re.IGNORECASE)
        
        # Poids: kilogrammes, tonnes, grammes
        text = re.sub(r'(\d+(?:[,.\s]\d+)?)\s*(kilogrammes?|kg|tonnes?|grammes?|g\b)', 
                     r'**\1 \2**', text, flags=re.IGNORECASE)
        
        # Monnaie: euros, dollars
        text = re.sub(r'(\d+(?:[,.\s]\d+)?)\s*(euros?|dollars?|\$|€)', 
                     r'**\1 \2**', text, flags=re.IGNORECASE)
        
        # Population: habitants, personnes
        text = re.sub(r'(\d+(?:[,.\s]\d+)?)\s*(?:millions?|milliards?)?\s*(habitants?|personnes?)', 
                     r'**\1 \2**', text, flags=re.IGNORECASE)
        
        # Pourcentages
        text = re.sub(r'(\d+(?:[,.\s]\d+)?)\s*%', r'**\1%**', text)
        
        # 2. DATES (années, dates complètes)
        text = re.sub(r'\b(\d{4})\b', r'**\1**', text)
        text = re.sub(r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})', 
                     r'**\1 \2 \3**', text, flags=re.IGNORECASE)
        
        # 3. NOMS PROPRES IMPORTANTS (adaptatif selon le contexte)
        # Détecter automatiquement les noms propres répétés
        words = text.split()
        word_count = {}
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word)
            if len(clean_word) > 2 and clean_word[0].isupper():
                word_count[clean_word] = word_count.get(clean_word, 0) + 1
        
        # Mettre en gras les noms propres qui apparaissent plus d'une fois
        for word, count in word_count.items():
            if count > 1 and len(word) > 3:
                text = re.sub(f'\\b{re.escape(word)}\\b', f'**{word}**', text)
        
        # 4. MOTS D'IMPORTANCE UNIVERSELS
        important_words = [
            # Mesures et tailles
            'hauteur', 'taille', 'mesure', 'poids', 'longueur', 'largeur',
            # Temps
            'actuellement', 'aujourd\'hui', 'maintenant', 'désormais', 'récemment',
            # Précision
            'exactement', 'précisément', 'officiellement', 'environ', 'approximativement',
            # Importance
            'important', 'principal', 'majeur', 'essentiel', 'fondamental',
            # Superlatifs
            'plus grand', 'plus petit', 'plus haut', 'plus important', 'premier', 'dernier'
        ]
        
        for word in important_words:
            text = re.sub(f'\\b{re.escape(word)}\\b', f'**{word}**', text, flags=re.IGNORECASE)
        
        # 5. NETTOYER LE FORMATAGE EN GRAS
        # Éviter les doubles gras
        text = re.sub(r'\*{4,}', '**', text)
        text = re.sub(r'\*\*\s*\*\*', '**', text)
        
        # Éviter les gras vides
        text = re.sub(r'\*\*\s*\*\*', '', text)
        
        return text
    
    def _universal_word_spacing_fix(self, text: str) -> str:
        """Correction douce des problèmes d'espacement (évite de casser les mots valides)"""
        # 1. Séparer chiffres collés à des lettres (ex: "324m" -> "324 m")
        text = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', text)
        text = re.sub(r'([0-9])([a-zA-Z])', r'\1 \2', text)
        # 2. Corriger la ponctuation collée (ex: "mots.Autres" -> "mots. Autres")
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        text = re.sub(r'([,;:])([a-zA-Z])', r'\1 \2', text)
        # 3. Nettoyer les espaces multiples
        text = re.sub(r'\s+', ' ', text)
        # 4. Corriger les espaces autour de la ponctuation
        text = re.sub(r'\s+([.!?:;,])', r'\1', text)
        text = re.sub(r'([.!?:;,])([a-zA-Z])', r'\1 \2', text)
        return text.strip()
        result = text
        for pattern, replacement in fixes:
            try:
                result = re.sub(pattern, replacement, result)
            except re.error:
                # Ignorer les patterns problématiques
                continue
        
        return result.strip()
    
    def _clean_title(self, title: str) -> str:
        """Nettoie le titre des sources pour un affichage optimal"""
        # Supprimer les parties indésirables
        cleaned = title
        
        # Supprimer les références de site entre crochets ou parenthèses à la fin
        cleaned = re.sub(r'\s*[\[\(].*?[\]\)]\s*$', '', cleaned)
        
        # Supprimer les tirets et barres en fin de titre
        cleaned = re.sub(r'\s*[-|—]\s*[^-]+$', '', cleaned)
        
        # Limiter la longueur
        if len(cleaned) > 60:
            cleaned = cleaned[:57] + "..."
        
        # Corriger l'espacement
        cleaned = self._universal_word_spacing_fix(cleaned)
        
        return cleaned.strip()
    
    def _extract_concentrated_summary(self, query: str, page_contents: List[Dict[str, Any]]) -> str:
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
        sentences = re.split(r'[.!?]+', combined_text)
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
            self._search_fallback
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
            "skip_disambig": "1"
        }
        
        headers = {"User-Agent": self.user_agent}
        
        response = requests.get(url, params=params, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        # Résultat instant
        if data.get("Abstract"):
            results.append({
                "title": data.get("Heading", "Information"),
                "snippet": data.get("Abstract", ""),
                "url": data.get("AbstractURL", ""),
                "source": "DuckDuckGo Instant"
            })
        
        # Résultats de topics
        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " ").title(),
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", ""),
                    "source": "DuckDuckGo"
                })
        
        return results[:self.max_results]
    
    def _search_with_requests(self, query: str) -> List[Dict[str, Any]]:
        """Recherche en scrapant les résultats"""
        search_url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
        
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        
        response = requests.get(search_url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        results = []
        
        for result_div in soup.find_all('div', class_='result')[:self.max_results]:
            title_elem = result_div.find('a', class_='result__a')
            snippet_elem = result_div.find('a', class_='result__snippet')
            
            if title_elem and snippet_elem:
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                snippet = snippet_elem.get_text(strip=True)
                
                if title and snippet:
                    results.append({
                        "title": title,
                        "snippet": snippet,
                        "url": url,
                        "source": "DuckDuckGo"
                    })
        
        return results
    
    def _search_fallback(self, query: str) -> List[Dict[str, Any]]:
        """Méthode de recherche de secours"""
        return [{
            "title": f"Recherche sur '{query}'",
            "snippet": f"Je n'ai pas pu accéder aux moteurs de recherche pour '{query}'. Vérifiez votre connexion internet ou reformulez votre question.",
            "url": "",
            "source": "Système local"
        }]
    
    def _extract_page_contents(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extrait le contenu des pages"""
        enriched_results = []
        
        def extract_single_page(result):
            try:
                if not result.get("url") or not result["url"].startswith("http"):
                    return result
                
                headers = {"User-Agent": self.user_agent}
                response = requests.get(result["url"], headers=headers, timeout=7)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Supprimer les scripts et styles
                for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    element.decompose()
                
                # Extraire le texte principal
                main_content = ""
                
                # Priorité aux balises principales
                for tag in ['main', 'article', '[role="main"]', '.content', '.article', '.post']:
                    content_elem = soup.select_one(tag)
                    if content_elem:
                        main_content = content_elem.get_text(separator=" ", strip=True)
                        break
                
                # Fallback sur les paragraphes
                if not main_content:
                    paragraphs = soup.find_all('p')
                    main_content = " ".join([p.get_text(strip=True) for p in paragraphs[:10]])
                
                # Limiter la longueur
                if len(main_content) > self.max_content_length:
                    main_content = main_content[:self.max_content_length] + "..."
                
                result["full_content"] = main_content
                
            except Exception as e:
                print(f"⚠️ Impossible d'extraire le contenu de {result.get('url', 'URL inconnue')}: {str(e)}")
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
    
    def _cache_results(self, cache_key: str, summary: str, results: List[Dict[str, Any]]):
        """Met en cache les résultats"""
        self.search_cache[cache_key] = {
            "summary": summary,
            "results": results,
            "timestamp": time.time()
        }
        
        # Nettoyer le cache ancien (garder max 20 entrées)
        if len(self.search_cache) > 20:
            oldest_key = min(self.search_cache.keys(), 
                           key=lambda k: self.search_cache[k]["timestamp"])
            del self.search_cache[oldest_key]
    
    def get_search_history(self) -> List[str]:
        """Retourne l'historique des recherches récentes"""
        history = []
        for cache_key, data in sorted(self.search_cache.items(), 
                                    key=lambda x: x[1]["timestamp"], reverse=True):
            if data.get("results") and data["results"]:
                history.append(f"Recherche récente - {len(data['results'])} résultats")
        
        return history[:10]


# Alias pour remplacer l'ancienne classe
InternetSearchEngine = EnhancedInternetSearchEngine