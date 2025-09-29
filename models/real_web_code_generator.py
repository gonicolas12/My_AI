"""
Générateur de Code Basé sur Recherche Web Pure
AUCUN template pré-codé - uniquement recherche web réelle
"""

import asyncio
import aiohttp
import re
import json
from typing import Dict, List, Any, Optional
from urllib.parse import quote
from bs4 import BeautifulSoup
import hashlib
import time
from pathlib import Path

class RealWebCodeGenerator:
    """
    Générateur qui cherche VRAIMENT sur le web comme ChatGPT/Claude
    """

    def __init__(self):
        self.session = None
        # Configuration GitHub
        try:
            import yaml
            config_path = Path(__file__).parent.parent / "config.yaml"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                self.github_token = config.get('github', {}).get('token', '')
            else:
                self.github_token = ''
        except:
            self.github_token = ''

    async def generate_code_from_web(self, query: str, language: str = "python") -> Dict[str, Any]:
        """
        Génère du code UNIQUEMENT à partir de recherches web réelles
        """
        try:
            # 1. Recherche parallèle sur toutes les sources
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
                self.session = session

                # Recherches en parallèle
                tasks = [
                    self._search_github_real(query, language),
                    self._search_stackoverflow_real(query, language),
                    self._search_geeksforgeeks_real(query, language),
                    self._search_google_code(query, language)
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                all_solutions = []
                for result in results:
                    if isinstance(result, list):
                        all_solutions.extend(result)

                # 2. Trier par pertinence et qualité
                if all_solutions:
                    best_solution = self._select_best_solution(all_solutions, query)

                    if best_solution:
                        return {
                            "success": True,
                            "code": best_solution["code"],
                            "explanation": best_solution["explanation"],
                            "source": best_solution["source"],
                            "url": best_solution.get("url", ""),
                            "rating": best_solution.get("rating", 3.0)
                        }

                # 3. Si aucune solution trouvée, recherche plus large
                fallback_result = await self._fallback_web_search(query, language)
                if fallback_result:
                    return fallback_result

                # 4. Échec total
                return {
                    "success": False,
                    "error": f"Aucune solution trouvée sur le web pour: {query}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Erreur recherche web: {str(e)}"
            }

    async def _search_github_real(self, query: str, language: str) -> List[Dict]:
        """Recherche RÉELLE sur GitHub via API"""
        solutions = []

        try:
            # Construire une requête GitHub optimisée
            search_terms = self._build_github_search_query(query, language)
            url = f"https://api.github.com/search/code?q={quote(search_terms)}&sort=indexed&per_page=10"

            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'CodeGenerator/1.0'
            }
            if self.github_token:
                headers['Authorization'] = f'token {self.github_token}'

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get('items', [])[:5]:  # Top 5 résultats
                        # Récupérer le contenu du fichier
                        file_content = await self._fetch_github_file(item.get('url', ''))

                        if file_content and self._is_relevant_for_query(file_content, query):
                            solutions.append({
                                "code": file_content,
                                "explanation": f"Solution trouvée sur GitHub dans {item.get('repository', {}).get('full_name', '')}",
                                "source": "GitHub",
                                "url": item.get('html_url', ''),
                                "rating": self._calculate_github_rating(item),
                                "relevance": self._calculate_relevance(file_content, query)
                            })

        except Exception as e:
            print(f"[WARNING] Erreur GitHub: {e}")

        return solutions

    async def _search_stackoverflow_real(self, query: str, language: str) -> List[Dict]:
        """Recherche RÉELLE sur Stack Overflow"""
        solutions = []

        try:
            # API Stack Overflow
            search_query = f"{query} {language}"
            url = "https://api.stackexchange.com/2.3/search/advanced"
            params = {
                'order': 'desc',
                'sort': 'relevance',
                'q': search_query,
                'tagged': language,
                'site': 'stackoverflow',
                'filter': 'withbody',
                'pagesize': 5
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get('items', []):
                        body = item.get('body', '')
                        code_blocks = self._extract_code_from_html(body)

                        for code in code_blocks:
                            if self._is_relevant_for_query(code, query) and len(code.strip()) > 30:
                                solutions.append({
                                    "code": code,
                                    "explanation": f"Solution Stack Overflow: {item.get('title', 'Sans titre')[:100]}",
                                    "source": "Stack Overflow",
                                    "url": item.get('link', ''),
                                    "rating": self._calculate_stackoverflow_rating(item),
                                    "relevance": self._calculate_relevance(code, query)
                                })

        except Exception as e:
            print(f"[WARNING] Erreur Stack Overflow: {e}")

        return solutions

    async def _search_geeksforgeeks_real(self, query: str, language: str) -> List[Dict]:
        """Recherche RÉELLE sur GeeksforGeeks"""
        solutions = []

        try:
            # Recherche Google ciblée GeeksforGeeks
            search_query = f"site:geeksforgeeks.org {query} {language} example code"
            google_url = f"https://www.google.com/search?q={quote(search_query)}&num=5"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            async with self.session.get(google_url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Extraire les liens GeeksforGeeks
                    gfg_links = []
                    for link in soup.find_all('a'):
                        href = link.get('href', '')
                        if 'geeksforgeeks.org' in href and '/url?q=' in href:
                            clean_url = href.split('/url?q=')[1].split('&')[0]
                            if 'geeksforgeeks.org' in clean_url:
                                gfg_links.append(clean_url)

                    # Visiter les pages GeeksforGeeks
                    for url in gfg_links[:3]:
                        try:
                            async with self.session.get(url, headers=headers) as page_response:
                                if page_response.status == 200:
                                    page_html = await page_response.text()
                                    page_soup = BeautifulSoup(page_html, 'html.parser')

                                    # Extraire le code
                                    code_elements = page_soup.find_all(['pre', 'code'])
                                    for code_elem in code_elements:
                                        code_text = code_elem.get_text()
                                        if (len(code_text.strip()) > 50 and
                                            self._is_relevant_for_query(code_text, query)):

                                            title = page_soup.find('title')
                                            page_title = title.get_text() if title else "GeeksforGeeks"

                                            solutions.append({
                                                "code": code_text,
                                                "explanation": f"Solution GeeksforGeeks: {page_title[:100]}",
                                                "source": "GeeksforGeeks",
                                                "url": url,
                                                "rating": 4.0,
                                                "relevance": self._calculate_relevance(code_text, query)
                                            })
                                            break

                        except Exception as e:
                            print(f"[WARNING] Erreur page GeeksforGeeks: {e}")
                            continue

        except Exception as e:
            print(f"[WARNING] Erreur GeeksforGeeks: {e}")

        return solutions

    async def _search_google_code(self, query: str, language: str) -> List[Dict]:
        """Recherche Google générale pour du code"""
        solutions = []

        try:
            # Recherche Google avec mots-clés spécifiques
            search_query = f"{query} {language} example code function tutorial"
            google_url = f"https://www.google.com/search?q={quote(search_query)}&num=10"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            async with self.session.get(google_url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Extraire les liens utiles (éviter les gros sites)
                    useful_links = []
                    for link in soup.find_all('a'):
                        href = link.get('href', '')
                        if '/url?q=' in href:
                            clean_url = href.split('/url?q=')[1].split('&')[0]
                            # Éviter les gros sites déjà traités
                            if (any(domain in clean_url for domain in ['github.com', 'stackoverflow.com', 'geeksforgeeks.org']) or
                                any(skip in clean_url for skip in ['youtube.com', 'facebook.com', 'twitter.com', 'linkedin.com'])):
                                continue
                            if clean_url.startswith('http') and len(useful_links) < 3:
                                useful_links.append(clean_url)

                    # Visiter quelques pages
                    for url in useful_links:
                        try:
                            async with self.session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as page_response:
                                if page_response.status == 200:
                                    page_html = await page_response.text()
                                    page_soup = BeautifulSoup(page_html, 'html.parser')

                                    # Chercher du code
                                    code_elements = page_soup.find_all(['pre', 'code'])
                                    for code_elem in code_elements:
                                        code_text = code_elem.get_text()
                                        if (len(code_text.strip()) > 40 and
                                            self._is_relevant_for_query(code_text, query)):

                                            title = page_soup.find('title')
                                            page_title = title.get_text()[:100] if title else "Web Result"

                                            solutions.append({
                                                "code": code_text,
                                                "explanation": f"Solution Web: {page_title}",
                                                "source": "Web Search",
                                                "url": url,
                                                "rating": 3.0,
                                                "relevance": self._calculate_relevance(code_text, query)
                                            })
                                            break

                        except Exception as e:
                            print(f"[WARNING] Erreur page web: {e}")
                            continue

        except Exception as e:
            print(f"[WARNING] Erreur Google search: {e}")

        return solutions

    async def _fallback_web_search(self, query: str, language: str) -> Optional[Dict]:
        """Recherche de fallback plus large"""
        try:
            # Recherche avec termes plus génériques
            broad_query = f"{language} function example tutorial"

            # Essayer DuckDuckGo comme alternative
            ddg_url = f"https://duckduckgo.com/html/?q={quote(f'{broad_query} {query}')}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            async with self.session.get(ddg_url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Extraire quelques liens
                    links = []
                    for link in soup.find_all('a', class_='result__a'):
                        href = link.get('href', '')
                        if href.startswith('http') and len(links) < 2:
                            links.append(href)

                    # Essayer de trouver du code sur ces pages
                    for url in links:
                        try:
                            async with self.session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as page_response:
                                if page_response.status == 200:
                                    page_html = await page_response.text()
                                    page_soup = BeautifulSoup(page_html, 'html.parser')

                                    code_elements = page_soup.find_all(['pre', 'code'])
                                    for code_elem in code_elements:
                                        code_text = code_elem.get_text()
                                        if len(code_text.strip()) > 30:
                                            return {
                                                "success": True,
                                                "code": code_text,
                                                "explanation": f"Solution trouvée via recherche élargie",
                                                "source": "Web Search (Fallback)",
                                                "url": url,
                                                "rating": 2.5
                                            }
                        except:
                            continue

        except Exception as e:
            print(f"[WARNING] Erreur fallback search: {e}")

        return None

    def _build_github_search_query(self, query: str, language: str) -> str:
        """Construit une requête GitHub optimisée"""
        query_lower = query.lower()

        # Patterns spécifiques
        if any(word in query_lower for word in ["tri", "sort", "ordre", "alphabétique"]):
            return f"sort function {language} language:{language}"
        elif any(word in query_lower for word in ["convertir", "convert", "majuscule", "uppercase"]):
            return f"convert uppercase {language} language:{language}"
        elif any(word in query_lower for word in ["liste", "list", "array", "tableau"]):
            return f"list array {language} language:{language}"
        elif any(word in query_lower for word in ["fonction", "function", "def"]):
            return f"function example {language} language:{language}"
        else:
            # Extraire les mots-clés principaux
            words = re.findall(r'\b\w{3,}\b', query_lower)
            main_words = [w for w in words if w not in ['une', 'des', 'pour', 'qui', 'que', 'avec']][:3]
            return f"{' '.join(main_words)} {language} language:{language}"

    async def _fetch_github_file(self, api_url: str) -> Optional[str]:
        """Récupère le contenu d'un fichier GitHub"""
        try:
            headers = {'Accept': 'application/vnd.github.v3+json'}
            if self.github_token:
                headers['Authorization'] = f'token {self.github_token}'

            async with self.session.get(api_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data.get('content', '')
                    if content:
                        import base64
                        return base64.b64decode(content).decode('utf-8', errors='ignore')
        except:
            pass
        return None

    def _extract_code_from_html(self, html: str) -> List[str]:
        """Extrait les blocs de code d'un HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        code_blocks = []

        for pre in soup.find_all('pre'):
            code_elem = pre.find('code')
            if code_elem:
                code_text = code_elem.get_text()
            else:
                code_text = pre.get_text()

            if len(code_text.strip()) > 20:
                code_blocks.append(code_text)

        return code_blocks

    def _is_relevant_for_query(self, code: str, query: str) -> bool:
        """Vérifie si le code est pertinent pour la requête"""
        code_lower = code.lower()
        query_lower = query.lower()

        # Extraire les mots-clés de la requête
        query_words = re.findall(r'\b\w{3,}\b', query_lower)
        main_words = [w for w in query_words if w not in ['une', 'des', 'pour', 'qui', 'que', 'avec', 'fonction', 'code']]

        # Vérifier la présence des mots-clés
        matches = 0
        for word in main_words:
            if word in code_lower:
                matches += 1

        # Au moins 30% des mots-clés doivent être présents
        if len(main_words) == 0:
            return len(code.strip()) > 20  # Fallback basique

        return matches >= len(main_words) * 0.3

    def _calculate_relevance(self, code: str, query: str) -> float:
        """Calcule un score de pertinence 0-1"""
        code_lower = code.lower()
        query_lower = query.lower()

        query_words = re.findall(r'\b\w{3,}\b', query_lower)
        if not query_words:
            return 0.5

        matches = 0
        for word in query_words:
            if word in code_lower:
                matches += 1

        return min(1.0, matches / len(query_words))

    def _calculate_github_rating(self, item: Dict) -> float:
        """Calcule un rating pour GitHub"""
        repo = item.get('repository', {})
        stars = repo.get('stargazers_count', 0)

        if stars > 1000:
            return 4.5
        elif stars > 100:
            return 4.0
        elif stars > 10:
            return 3.5
        else:
            return 3.0

    def _calculate_stackoverflow_rating(self, item: Dict) -> float:
        """Calcule un rating pour Stack Overflow"""
        score = item.get('score', 0)
        is_answered = item.get('is_answered', False)

        rating = 3.0
        if is_answered:
            rating += 0.5
        if score > 10:
            rating += 1.0
        elif score > 5:
            rating += 0.5

        return min(5.0, rating)

    def _select_best_solution(self, solutions: List[Dict], query: str) -> Optional[Dict]:
        """Sélectionne la meilleure solution"""
        if not solutions:
            return None

        # Trier par pertinence puis rating
        solutions.sort(key=lambda s: (s.get('relevance', 0), s.get('rating', 0)), reverse=True)

        best = solutions[0]

        # Vérifier que la solution a un minimum de qualité
        if best.get('relevance', 0) > 0.3 and len(best.get('code', '').strip()) > 30:
            return best

        return None


# Instance globale
real_web_generator = RealWebCodeGenerator()

async def generate_code_from_web_only(query: str, language: str = "python") -> Dict[str, Any]:
    """Point d'entrée pour génération pure depuis le web"""
    return await real_web_generator.generate_code_from_web(query, language)