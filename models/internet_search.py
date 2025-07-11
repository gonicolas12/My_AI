"""
Module de recherche internet avec résumé intelligent
Permet de rechercher des informations sur internet et de les synthétiser
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


class InternetSearchEngine:
    """Moteur de recherche internet avec synthèse intelligente"""
    
    def __init__(self):
        self.search_apis = {
            "duckduckgo": "https://api.duckduckgo.com/",
            "bing": "https://api.bing.microsoft.com/v7.0/search",
            "google_custom": "https://www.googleapis.com/customsearch/v1"
        }
        
        # Configuration
        self.max_results = 5
        self.max_content_length = 2000
        self.timeout = 10
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        
        # Cache des résultats récents
        self.search_cache = {}
        self.cache_duration = 3600  # 1 heure
        
    def search_and_summarize(self, query: str, context: Dict[str, Any] = None) -> str:
        """
        Recherche sur internet et génère un résumé intelligent
        
        Args:
            query: Requête de recherche
            context: Contexte additionnel pour la recherche
            
        Returns:
            str: Résumé intelligent des résultats
        """
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
            
            # Générer le résumé
            summary = self._generate_intelligent_summary(query, page_contents, search_results)
            
            # Mettre en cache
            self._cache_results(cache_key, summary, search_results)
            
            return summary
            
        except Exception as e:
            print(f"❌ Erreur lors de la recherche: {str(e)}")
            return f"Désolé, une erreur s'est produite lors de la recherche internet : {str(e)}"
    
    def _perform_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Effectue la recherche sur internet
        
        Args:
            query: Requête de recherche
            
        Returns:
            List[Dict]: Liste des résultats de recherche
        """
        # Essayer différentes méthodes de recherche
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
        """
        Recherche via l'API instant de DuckDuckGo
        
        Args:
            query: Requête de recherche
            
        Returns:
            List[Dict]: Résultats de recherche
        """
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
        """
        Recherche en scrapant les résultats de moteurs de recherche
        
        Args:
            query: Requête de recherche
            
        Returns:
            List[Dict]: Résultats de recherche
        """
        # Recherche sur DuckDuckGo HTML
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
        
        # Extraire les résultats
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
        """
        Méthode de recherche de secours - simulation de résultats
        
        Args:
            query: Requête de recherche
            
        Returns:
            List[Dict]: Résultats simulés
        """
        # En cas d'échec des autres méthodes, fournir une réponse constructive
        return [{
            "title": f"Recherche sur '{query}'",
            "snippet": f"Je n'ai pas pu accéder aux moteurs de recherche pour '{query}'. Vérifiez votre connexion internet ou reformulez votre question.",
            "url": "",
            "source": "Système local"
        }]
    
    def _extract_page_contents(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extrait le contenu des pages des résultats de recherche
        
        Args:
            search_results: Résultats de recherche
            
        Returns:
            List[Dict]: Contenus extraits
        """
        enriched_results = []
        
        def extract_single_page(result):
            try:
                if not result.get("url") or not result["url"].startswith("http"):
                    return result
                
                headers = {"User-Agent": self.user_agent}
                response = requests.get(result["url"], headers=headers, timeout=5)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Supprimer les scripts et styles
                for element in soup(["script", "style", "nav", "footer", "header"]):
                    element.decompose()
                
                # Extraire le texte principal
                main_content = ""
                
                # Priorité aux balises principales
                for tag in ['main', 'article', 'div[class*="content"]', 'div[class*="article"]']:
                    content_elem = soup.select_one(tag)
                    if content_elem:
                        main_content = content_elem.get_text(separator=" ", strip=True)
                        break
                
                # Fallback sur tout le body
                if not main_content:
                    body = soup.find('body')
                    if body:
                        main_content = body.get_text(separator=" ", strip=True)
                
                # Limiter la longueur
                if len(main_content) > self.max_content_length:
                    main_content = main_content[:self.max_content_length] + "..."
                
                result["full_content"] = main_content
                
            except Exception as e:
                print(f"⚠️ Impossible d'extraire le contenu de {result.get('url', 'URL inconnue')}: {str(e)}")
                result["full_content"] = result.get("snippet", "")
            
            return result
        
        # Traitement parallèle pour accélérer l'extraction
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            enriched_results = list(executor.map(extract_single_page, search_results))
        
        return enriched_results
    
    def _generate_intelligent_summary(self, query: str, page_contents: List[Dict[str, Any]], 
                                    original_results: List[Dict[str, Any]]) -> str:
        """
        Génère un résumé intelligent des résultats de recherche
        
        Args:
            query: Requête originale
            page_contents: Contenus extraits des pages
            original_results: Résultats de recherche originaux
            
        Returns:
            str: Résumé intelligent
        """
        # Construire le résumé
        summary = f"🔍 **Résultats de recherche pour '{query}'**\n\n"
        
        # Analyser le type de requête
        query_lower = query.lower()
        is_definition = any(word in query_lower for word in ["qu'est-ce que", "définition", "c'est quoi", "define"])
        is_howto = any(word in query_lower for word in ["comment", "how to", "tutorial", "guide"])
        is_news = any(word in query_lower for word in ["actualité", "news", "dernières nouvelles"])
        is_comparison = any(word in query_lower for word in ["vs", "versus", "différence", "comparaison"])
        
        # Résumé adapté selon le type de requête
        if is_definition:
            summary += "📖 **Définition :**\n"
        elif is_howto:
            summary += "🛠️ **Guide pratique :**\n"
        elif is_news:
            summary += "📰 **Actualités :**\n"
        elif is_comparison:
            summary += "⚖️ **Comparaison :**\n"
        else:
            summary += "📝 **Synthèse des informations :**\n"
        
        # Extraire les informations clés
        key_info = self._extract_key_information(page_contents, query)
        
        if key_info:
            summary += key_info + "\n\n"
        
        # Ajouter les sources principales
        summary += "🔗 **Sources principales :**\n"
        
        source_count = 0
        for result in page_contents[:3]:  # Top 3 résultats
            if result.get("title") and result.get("snippet"):
                source_count += 1
                title = result["title"][:100] + "..." if len(result["title"]) > 100 else result["title"]
                snippet = result["snippet"][:150] + "..." if len(result["snippet"]) > 150 else result["snippet"]
                
                summary += f"\n**{source_count}. {title}**\n"
                summary += f"   {snippet}\n"
                
                if result.get("url") and result["url"].startswith("http"):
                    summary += f"   🌐 Source: {result['url']}\n"
        
        # Ajouter des suggestions
        suggestions = self._generate_search_suggestions(query)
        if suggestions:
            summary += f"\n💡 **Recherches suggérées :**\n{suggestions}"
        
        # Ajouter timestamp
        timestamp = datetime.now().strftime("%H:%M")
        summary += f"\n\n⏰ *Recherche effectuée à {timestamp}*"
        
        return summary
    
    def _extract_key_information(self, page_contents: List[Dict[str, Any]], query: str) -> str:
        """
        Extrait les informations clés des contenus de pages
        
        Args:
            page_contents: Contenus des pages
            query: Requête originale
            
        Returns:
            str: Informations clés extraites
        """
        # Combiner tous les contenus
        all_content = ""
        for content in page_contents:
            snippet = content.get("snippet", "")
            full_content = content.get("full_content", "")
            all_content += f"{snippet} {full_content} "
        
        if not all_content.strip():
            return "Aucune information détaillée disponible."
        
        # Extraire les phrases les plus pertinentes
        sentences = re.split(r'[.!?]+', all_content)
        relevant_sentences = []
        
        query_words = set(query.lower().split())
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Ignorer les phrases trop courtes
                sentence_words = set(sentence.lower().split())
                
                # Calculer la pertinence
                relevance_score = len(query_words.intersection(sentence_words))
                
                if relevance_score > 0:
                    relevant_sentences.append((sentence, relevance_score))
        
        # Trier par pertinence et prendre les meilleures
        relevant_sentences.sort(key=lambda x: x[1], reverse=True)
        
        key_info = ""
        for sentence, score in relevant_sentences[:3]:  # Top 3 phrases
            key_info += f"• {sentence.strip()}\n"
        
        return key_info if key_info else "Informations générales trouvées mais nécessitent une recherche plus spécifique."
    
    def _generate_search_suggestions(self, query: str) -> str:
        """
        Génère des suggestions de recherche
        
        Args:
            query: Requête originale
            
        Returns:
            str: Suggestions formatées
        """
        suggestions = []
        query_lower = query.lower()
        
        # Suggestions basées sur le type de requête
        if any(word in query_lower for word in ["comment", "how"]):
            suggestions.extend([
                f"{query} étapes",
                f"{query} tutoriel",
                f"{query} guide complet"
            ])
        elif any(word in query_lower for word in ["qu'est", "what is", "définition"]):
            suggestions.extend([
                f"{query} exemples",
                f"{query} explication simple",
                f"avantages {query}"
            ])
        elif any(word in query_lower for word in ["meilleur", "best"]):
            suggestions.extend([
                f"{query} 2025",
                f"{query} comparatif",
                f"{query} avis"
            ])
        else:
            suggestions.extend([
                f"{query} actualités",
                f"{query} guide",
                f"{query} exemples"
            ])
        
        if suggestions:
            return "• " + "\n• ".join(suggestions[:3])
        
        return ""
    
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
        """
        Retourne l'historique des recherches récentes
        
        Returns:
            List[str]: Historique des recherches
        """
        history = []
        for cache_key, data in sorted(self.search_cache.items(), 
                                    key=lambda x: x[1]["timestamp"], reverse=True):
            # Reconstituer la requête à partir des résultats
            if data.get("results") and data["results"]:
                history.append(f"Recherche récente - {len(data['results'])} résultats")
        
        return history[:10]  # 10 dernières recherches
