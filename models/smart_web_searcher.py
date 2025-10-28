"""
Système de Recherche Web Intelligent pour Code
Recherche sur GitHub, Stack Overflow, et autres sources avec validation de pertinence
"""

import asyncio
import base64
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote

import aiohttp
from bs4 import BeautifulSoup

# Configuration GitHub
try:
    import yaml
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        GITHUB_TOKEN = config.get('github', {}).get('token', '')
    else:
        GITHUB_TOKEN = ''
except Exception:
    GITHUB_TOKEN = ''

@dataclass
class CodeSearchResult:
    """Résultat de recherche de code"""
    code: str
    title: str
    description: str
    language: str
    source_url: str
    source_name: str
    rating: float
    relevance_score: float
    author: str
    created_at: datetime
    tags: List[str]

class SmartWebSearcher:
    """Recherche intelligente de code avec validation de pertinence"""

    def __init__(self):
        self.cache_db = self._init_cache_db()
        self.session = None
        self.github_headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Python-Code-Generator/1.0'
        }
        if GITHUB_TOKEN:
            self.github_headers['Authorization'] = f'token {GITHUB_TOKEN}'

    def _init_cache_db(self) -> sqlite3.Connection:
        """Initialise le cache pour les résultats de recherche"""
        db_path = Path(__file__).parent.parent / "context_storage/web_search_cache.db"
        conn = sqlite3.connect(str(db_path))

        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT,
                language TEXT,
                source_name TEXT,
                title TEXT,
                code TEXT,
                description TEXT,
                source_url TEXT,
                rating REAL,
                relevance_score REAL,
                author TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        return conn

    async def search_code_solutions(
        self,
        query: str,
        language: str = "python",
        max_results: int = 5,
        sources: List[str] = None
    ) -> List[CodeSearchResult]:
        """
        Recherche des solutions de code sur multiple sources
        """
        if sources is None:
            sources = ["github", "stackoverflow", "geeksforgeeks"]

        query_hash = self._hash_query(query, language)

        # Vérifier le cache
        cached_results = self._get_cached_results(query_hash, max_results)
        if cached_results:
            return cached_results

        all_results = []

        # Créer session aiohttp
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            self.session = session

            # Recherche parallèle sur toutes les sources
            tasks = []

            if "github" in sources:
                tasks.append(self._search_github(query, language, max_results // len(sources) + 1))

            if "stackoverflow" in sources:
                tasks.append(self._search_stackoverflow(query, language, max_results // len(sources) + 1))

            if "geeksforgeeks" in sources:
                tasks.append(self._search_geeksforgeeks(query, language, max_results // len(sources) + 1))

            # Exécuter toutes les recherches en parallèle
            try:
                results_lists = await asyncio.gather(*tasks, return_exceptions=True)

                for results in results_lists:
                    if isinstance(results, list):
                        all_results.extend(results)
                    elif isinstance(results, Exception):
                        print(f"[WARNING] Erreur de recherche: {results}")

            except Exception as e:
                print(f"[ERROR] Erreur recherche parallèle: {e}")

        # Filtrer et trier par pertinence
        filtered_results = self._filter_and_rank_results(all_results)

        # Limiter le nombre de résultats
        final_results = filtered_results[:max_results]

        # Mettre en cache
        self._cache_results(query_hash, final_results)

        return final_results

    async def _search_github(self, query: str, language: str, max_results: int) -> List[CodeSearchResult]:
        """Recherche sur GitHub via l'API"""
        results = []

        try:
            # Construire la requête de recherche GitHub
            search_query = self._build_github_query(query, language)
            url = f"https://api.github.com/search/code?q={quote(search_query)}&sort=indexed&order=desc&per_page={min(max_results, 10)}"

            async with self.session.get(url, headers=self.github_headers) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get('items', []):
                        # Récupérer le contenu du fichier
                        file_content = await self._get_github_file_content(item.get('url', ''))

                        if file_content and self._is_relevant_code(file_content, query, language):
                            result = CodeSearchResult(
                                code=file_content,
                                title=item.get('name', 'GitHub Code'),
                                description=f"From {item.get('repository', {}).get('full_name', 'Unknown repo')}",
                                language=language,
                                source_url=item.get('html_url', ''),
                                source_name="GitHub",
                                rating=self._calculate_github_rating(item),
                                relevance_score=self._calculate_relevance_score(file_content, query),
                                author=item.get('repository', {}).get('owner', {}).get('login', 'Unknown'),
                                created_at=datetime.now(),
                                tags=self._extract_tags_from_github(item)
                            )
                            results.append(result)

                elif response.status == 403:
                    print("[WARNING] Rate limit GitHub atteint")
                else:
                    print(f"[WARNING] Erreur GitHub API: {response.status}")

        except Exception as e:
            print(f"[ERROR] Erreur recherche GitHub: {e}")

        return results

    async def _search_stackoverflow(self, query: str, language: str, max_results: int) -> List[CodeSearchResult]:
        """Recherche sur Stack Overflow"""
        results = []

        try:
            # API Stack Overflow
            search_terms = f"{query} {language}"
            url = "https://api.stackexchange.com/2.3/search/advanced"
            params = {
                'order': 'desc',
                'sort': 'relevance',
                'q': search_terms,
                'tagged': language,
                'site': 'stackoverflow',
                'filter': 'withbody',
                'pagesize': min(max_results, 10)
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get('items', []):
                        # Extraire le code de la réponse
                        body = item.get('body', '')
                        code_blocks = self._extract_code_blocks(body)

                        for code_block in code_blocks:
                            if self._is_relevant_code(code_block, query, language):
                                result = CodeSearchResult(
                                    code=code_block,
                                    title=item.get('title', 'Stack Overflow Solution'),
                                    description=self._clean_html(body)[:200] + "...",
                                    language=language,
                                    source_url=item.get('link', ''),
                                    source_name="Stack Overflow",
                                    rating=self._calculate_stackoverflow_rating(item),
                                    relevance_score=self._calculate_relevance_score(code_block, query),
                                    author=item.get('owner', {}).get('display_name', 'Unknown'),
                                    created_at=datetime.fromtimestamp(item.get('creation_date', 0)),
                                    tags=item.get('tags', [])
                                )
                                results.append(result)

        except Exception as e:
            print(f"[ERROR] Erreur recherche Stack Overflow: {e}")

        return results

    async def _search_geeksforgeeks(self, query: str, language: str, max_results: int) -> List[CodeSearchResult]:
        """Recherche sur GeeksforGeeks"""
        results = []

        try:
            # Recherche Google avec site:geeksforgeeks.org
            search_query = f"site:geeksforgeeks.org {query} {language}"
            url = f"https://www.google.com/search?q={quote(search_query)}&num={max_results}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Extraire les liens GeeksforGeeks
                    links = []
                    for link in soup.find_all('a'):
                        href = link.get('href', '')
                        if 'geeksforgeeks.org' in href and '/url?q=' in href:
                            # Nettoyer l'URL Google
                            clean_url = href.split('/url?q=')[1].split('&')[0]
                            if clean_url not in links:
                                links.append(clean_url)

                    # Visiter chaque page GeeksforGeeks
                    for url in links[:max_results]:
                        try:
                            async with self.session.get(url, headers=headers) as page_response:
                                if page_response.status == 200:
                                    page_html = await page_response.text()
                                    page_soup = BeautifulSoup(page_html, 'html.parser')

                                    # Extraire le code
                                    code_elements = page_soup.find_all(['pre', 'code'])
                                    for code_elem in code_elements:
                                        code_text = code_elem.get_text()
                                        if (len(code_text) > 50 and
                                            self._is_relevant_code(code_text, query, language)):

                                            title = page_soup.find('title')
                                            title_text = title.get_text() if title else "GeeksforGeeks Solution"

                                            result = CodeSearchResult(
                                                code=code_text,
                                                title=title_text,
                                                description="Solution from GeeksforGeeks",
                                                language=language,
                                                source_url=url,
                                                source_name="GeeksforGeeks",
                                                rating=4.0,  # GeeksforGeeks a généralement du bon contenu
                                                relevance_score=self._calculate_relevance_score(code_text, query),
                                                author="GeeksforGeeks",
                                                created_at=datetime.now(),
                                                tags=[language, "tutorial"]
                                            )
                                            results.append(result)
                                            break

                        except Exception as e:
                            print(f"[WARNING] Erreur page GeeksforGeeks: {e}")
                            continue

        except Exception as e:
            print(f"[ERROR] Erreur recherche GeeksforGeeks: {e}")

        return results

    def _build_github_query(self, query: str, language: str) -> str:
        """Construit une requête optimisée pour GitHub"""
        # Extraire les mots-clés importants
        keywords = re.findall(r'\b\w+\b', query.lower())

        # Mots-clés spécialisés par contexte
        if any(word in keywords for word in ["tri", "sort", "ordre", "alphabétique"]):
            return f"sort algorithm {language} function"
        elif any(word in keywords for word in ["fonction", "function", "def"]):
            return f"function {language} implementation"
        elif any(word in keywords for word in ["classe", "class", "objet"]):
            return f"class {language} implementation"
        else:
            # Requête générique
            main_keywords = [kw for kw in keywords if len(kw) > 3][:3]
            return f"{' '.join(main_keywords)} {language}"

    async def _get_github_file_content(self, api_url: str) -> Optional[str]:
        """Récupère le contenu d'un fichier GitHub via l'API"""
        try:
            async with self.session.get(api_url, headers=self.github_headers) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data.get('content', '')
                    if content:
                        return base64.b64decode(content).decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"[WARNING] Erreur récupération fichier GitHub: {e}")
        return None

    def _extract_code_blocks(self, html_content: str) -> List[str]:
        """Extrait les blocs de code d'un contenu HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        code_blocks = []

        # Rechercher les balises <pre><code> (Stack Overflow)
        for pre in soup.find_all('pre'):
            code_elem = pre.find('code')
            if code_elem:
                code_text = code_elem.get_text()
                if len(code_text.strip()) > 20:  # Ignorer les codes trop courts
                    code_blocks.append(code_text)

        # Rechercher aussi les balises <code> seules
        for code in soup.find_all('code'):
            if not code.find_parent('pre'):  # Éviter les doublons
                code_text = code.get_text()
                if len(code_text.strip()) > 20:
                    code_blocks.append(code_text)

        return code_blocks

    def _is_relevant_code(self, code: str, query: str, language: str) -> bool:
        """Vérifie si un bloc de code est pertinent pour la requête"""
        code_lower = code.lower()
        query_lower = query.lower()

        # Vérifier que c'est bien du code dans le bon langage
        if language.lower() == "python":
            if not any(indicator in code_lower for indicator in ["def ", "import ", "class ", "for ", "if ", "return"]):
                return False
        elif language.lower() == "javascript":
            if not any(indicator in code_lower for indicator in ["function", "var ", "let ", "const ", "for ", "if "]):
                return False

        # Vérifier la pertinence sémantique
        query_keywords = re.findall(r'\b\w{3,}\b', query_lower)
        matches = 0

        for keyword in query_keywords:
            if keyword in code_lower:
                matches += 1

        # Au moins 30% des mots-clés doivent être présents
        return matches >= len(query_keywords) * 0.3

    def _calculate_relevance_score(self, code: str, query: str) -> float:
        """Calcule un score de pertinence entre 0 et 1"""
        code_lower = code.lower()
        query_lower = query.lower()

        query_keywords = re.findall(r'\b\w{3,}\b', query_lower)
        if not query_keywords:
            return 0.5

        matches = 0
        weighted_matches = 0

        for keyword in query_keywords:
            if keyword in code_lower:
                matches += 1
                # Poids supplémentaire pour les mots-clés dans les noms de fonctions/variables
                if re.search(rf'\b{keyword}\w*\s*[\(=]', code_lower):
                    weighted_matches += 1

        base_score = matches / len(query_keywords)
        bonus_score = weighted_matches / len(query_keywords) * 0.3

        return min(1.0, base_score + bonus_score)

    def _calculate_github_rating(self, item: Dict) -> float:
        """Calcule un rating pour un résultat GitHub"""
        repo = item.get('repository', {})
        stars = repo.get('stargazers_count', 0)
        forks = repo.get('forks_count', 0)

        # Rating basé sur la popularité du repo
        if stars > 1000:
            return 4.5
        elif stars > 100:
            return 4.0
        elif stars > 10:
            return 3.5
        elif forks > 5:
            return 3.0
        else:
            return 2.5

    def _calculate_stackoverflow_rating(self, item: Dict) -> float:
        """Calcule un rating pour un résultat Stack Overflow"""
        score = item.get('score', 0)
        is_answered = item.get('is_answered', False)
        view_count = item.get('view_count', 0)

        base_rating = 3.0

        if is_answered:
            base_rating += 0.5

        if score > 10:
            base_rating += 1.0
        elif score > 5:
            base_rating += 0.5
        elif score > 0:
            base_rating += 0.2

        if view_count > 1000:
            base_rating += 0.3

        return min(5.0, base_rating)

    def _extract_tags_from_github(self, item: Dict) -> List[str]:
        """Extrait des tags d'un résultat GitHub"""
        tags = []
        repo = item.get('repository', {})

        if 'language' in repo:
            tags.append(repo['language'])

        name = item.get('name', '').lower()
        if 'test' in name:
            tags.append('testing')
        if 'example' in name:
            tags.append('example')
        if 'util' in name:
            tags.append('utility')

        return tags

    def _clean_html(self, html_content: str) -> str:
        """Nettoie le contenu HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text()

    def _filter_and_rank_results(
        self,
        results: List[CodeSearchResult],
    ) -> List[CodeSearchResult]:
        """Filtre et classe les résultats par pertinence"""

        # Filtrer les résultats de mauvaise qualité
        filtered = []
        for result in results:
            # Éviter les codes trop courts ou trop longs
            if 20 <= len(result.code) <= 5000:
                # Éviter les codes qui semblent être de la configuration
                if not self._looks_like_config(result.code):
                    filtered.append(result)

        # Trier par score de pertinence puis par rating
        filtered.sort(key=lambda r: (r.relevance_score, r.rating), reverse=True)

        # Éviter les doublons
        unique_results = []
        seen_codes = set()

        for result in filtered:
            code_hash = hashlib.md5(result.code.encode()).hexdigest()
            if code_hash not in seen_codes:
                seen_codes.add(code_hash)
                unique_results.append(result)

        return unique_results

    def _looks_like_config(self, code: str) -> bool:
        """Vérifie si le code ressemble à de la configuration"""

        config_indicators = [
            'config', 'settings', 'constants', 'const ',
            'version', 'author', 'license', 'import os',
            'import sys', '__version__', '__author__'
        ]

        # Si plus de 50% des lignes contiennent des indicateurs de config
        lines = code.split('\n')
        config_lines = 0

        for line in lines:
            line_lower = line.lower().strip()
            if any(indicator in line_lower for indicator in config_indicators):
                config_lines += 1

        return config_lines > len(lines) * 0.5

    def _hash_query(self, query: str, language: str) -> str:
        """Génère un hash pour identifier une requête"""
        content = f"{query.lower().strip()}|{language.lower()}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cached_results(self, query_hash: str, max_results: int) -> Optional[List[CodeSearchResult]]:
        """Récupère les résultats du cache"""
        # Vérifier si le cache n'est pas trop ancien (24h)
        cutoff_time = datetime.now() - timedelta(hours=24)

        cursor = self.cache_db.execute("""
            SELECT title, code, description, source_url, source_name, rating,
                   relevance_score, author, tags, created_at
            FROM search_results
            WHERE query_hash = ? AND cached_at > ?
            ORDER BY relevance_score DESC, rating DESC
            LIMIT ?
        """, (query_hash, cutoff_time, max_results))

        rows = cursor.fetchall()
        if not rows:
            return None

        results = []
        for row in rows:
            result = CodeSearchResult(
                title=row[0],
                code=row[1],
                description=row[2],
                source_url=row[3],
                source_name=row[4],
                rating=row[5],
                relevance_score=row[6],
                author=row[7],
                tags=json.loads(row[8]) if row[8] else [],
                created_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now(),
                language=""  # Sera rempli par le contexte
            )
            results.append(result)

        return results

    def _cache_results(self, query_hash: str, results: List[CodeSearchResult]):
        """Met en cache les résultats"""
        for result in results:
            self.cache_db.execute("""
                INSERT OR REPLACE INTO search_results
                (query_hash, language, source_name, title, code, description,
                 source_url, rating, relevance_score, author, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                query_hash,
                result.language,
                result.source_name,
                result.title,
                result.code,
                result.description,
                result.source_url,
                result.rating,
                result.relevance_score,
                result.author,
                json.dumps(result.tags)
            ))
        self.cache_db.commit()


# Instance globale
smart_searcher = SmartWebSearcher()

async def search_smart_code(query: str, language: str = "python", max_results: int = 5) -> List[CodeSearchResult]:
    """Point d'entrée pour la recherche intelligente de code"""
    return await smart_searcher.search_code_solutions(query, language, max_results)
