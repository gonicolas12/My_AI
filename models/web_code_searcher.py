"""
Module de recherche et extraction de code depuis multiple sources web
Support pour Stack Overflow, GitHub, GeeksforGeeks, CodePen, etc.
"""

import base64
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin

import aiohttp
from bs4 import BeautifulSoup

# Intégration GitHub API avec token depuis config
try:
    import yaml

    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        GITHUB_TOKEN = config.get("github", {}).get("token", "")
    else:
        GITHUB_TOKEN = ""
except Exception:
    GITHUB_TOKEN = ""


@dataclass
class WebCodeSolution:
    """Solution de code trouvée sur le web"""

    code: str
    language: str
    title: str
    description: str
    source_url: str
    source_name: str
    rating: float
    difficulty: str
    tags: List[str]
    author: str
    created_at: datetime
    votes: int


class GeeksForGeeksSearcher:
    """Recherche de code sur GeeksforGeeks"""

    def __init__(self):
        self.base_url = "https://www.geeksforgeeks.org"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    async def search_solutions(
        self, query: str, language: str
    ) -> List[WebCodeSolution]:
        """Recherche des solutions sur GeeksforGeeks"""
        solutions = []

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                # Construire l'URL de recherche
                search_url = f"{self.base_url}/?s={quote(query + ' ' + language)}"

                async with session.get(search_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        # Trouver les liens d'articles
                        article_links = []
                        for link in soup.find_all("a", href=True):
                            href = link["href"]
                            if self.base_url in href and any(
                                keyword in href.lower()
                                for keyword in ["python", "java", "javascript", "cpp"]
                            ):
                                article_links.append(href)

                        # Analyser les premiers articles
                        for url in article_links[:5]:
                            article_solutions = await self._parse_geeksforgeeks_article(
                                session, url, language
                            )
                            solutions.extend(article_solutions)

        except Exception as e:
            print(f"Erreur recherche GeeksforGeeks: {e}")

        return solutions[:3]  # Limiter à 3 solutions

    async def _parse_geeksforgeeks_article(
        self, session: aiohttp.ClientSession, url: str, language: str
    ) -> List[WebCodeSolution]:
        """Parse un article GeeksforGeeks"""
        solutions = []

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Extraire le titre
                    title_elem = soup.find("h1")
                    title = (
                        title_elem.text.strip()
                        if title_elem
                        else "GeeksforGeeks Solution"
                    )

                    # Extraire les blocs de code
                    code_blocks = soup.find_all(["pre", "code"])

                    for code_block in code_blocks:
                        code_text = code_block.get_text().strip()

                        # Vérifier si c'est du code pertinent
                        if self._is_relevant_code_gfg(code_text, language):
                            # Extraire la description autour du code
                            description = self._extract_description_gfg(
                                code_block
                            )

                            solution = WebCodeSolution(
                                code=code_text,
                                language=language,
                                title=title,
                                description=description,
                                source_url=url,
                                source_name="GeeksforGeeks",
                                rating=4.2,  # Note par défaut pour GFG
                                difficulty=self._determine_difficulty_gfg(code_text),
                                tags=[language, "geeksforgeeks", "tutorial"],
                                author="GeeksforGeeks Team",
                                created_at=datetime.now(),
                                votes=0,
                            )
                            solutions.append(solution)

                            if len(solutions) >= 2:  # Limiter par article
                                break

        except Exception as e:
            print(f"Erreur parsing GeeksforGeeks: {e}")

        return solutions

    def _is_relevant_code_gfg(self, code: str, language: str) -> bool:
        """Vérifie si le code est pertinent"""
        if len(code) < 20:
            return False

        language_indicators = {
            "python": ["def ", "import ", "class ", "print(", ".py"],
            "javascript": ["function ", "var ", "let ", "const ", "console.log"],
            "java": ["public class", "public static", "System.out"],
            "cpp": ["#include", "int main", "std::", "cout"],
            "c": ["#include", "int main", "printf"],
        }

        indicators = language_indicators.get(language.lower(), [])
        return any(indicator in code for indicator in indicators)

    def _extract_description_gfg(self, code_block) -> str:
        """Extrait la description autour du bloc de code"""
        # Chercher les paragraphes avant et après le code
        description_parts = []

        # Paragraphe précédent
        prev_element = code_block.find_previous(["p", "h2", "h3"])
        if prev_element:
            description_parts.append(prev_element.get_text().strip())

        # Paragraphe suivant
        next_element = code_block.find_next(["p"])
        if next_element:
            description_parts.append(next_element.get_text().strip())

        description = " ".join(description_parts)
        return description[:300] if description else "Solution GeeksforGeeks"

    def _determine_difficulty_gfg(self, code: str) -> str:
        """Détermine la difficulté du code"""
        lines = len(code.split("\n"))
        complexity_indicators = [
            "class ",
            "def ",
            "for ",
            "while ",
            "if ",
            "try:",
            "except:",
        ]

        complexity_count = sum(
            code.count(indicator) for indicator in complexity_indicators
        )

        if lines <= 10 and complexity_count <= 3:
            return "Débutant"
        elif lines <= 30 and complexity_count <= 8:
            return "Intermédiaire"
        else:
            return "Avancé"


class CodePenSearcher:
    """Recherche de code sur CodePen (spécialement pour web)"""

    def __init__(self):
        self.base_url = "https://codepen.io"
        self.api_url = "https://cpv2api.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/html",
            "Accept-Language": "en-US,en;q=0.5",
        }

    async def search_solutions(
        self, query: str, language: str
    ) -> List[WebCodeSolution]:
        """Recherche des solutions sur CodePen"""
        solutions = []

        # CodePen est principalement pour le web
        if language.lower() not in ["html", "css", "javascript", "js"]:
            return solutions

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                # Recherche via l'interface web
                search_url = f"{self.base_url}/search/pens?q={quote(query)}"

                async with session.get(search_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        # Extraire les liens vers les pens
                        pen_links = []
                        for link in soup.find_all("a", href=True):
                            href = link["href"]
                            if "/pen/" in href:
                                full_url = urljoin(self.base_url, href)
                                pen_links.append(full_url)

                        # Analyser les premiers pens
                        for url in pen_links[:3]:
                            pen_solution = await self._parse_codepen_pen(
                                session, url, language
                            )
                            if pen_solution:
                                solutions.append(pen_solution)

        except Exception as e:
            print(f"Erreur recherche CodePen: {e}")

        return solutions

    async def _parse_codepen_pen(
        self, session: aiohttp.ClientSession, url: str, language: str
    ) -> Optional[WebCodeSolution]:
        """Parse un pen CodePen"""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Extraire le titre
                    title_elem = soup.find("h1", {"class": "item-title"})
                    title = (
                        title_elem.text.strip() if title_elem else "CodePen Solution"
                    )

                    # Extraire l'auteur
                    author_elem = soup.find("a", {"class": "username"})
                    author = author_elem.text.strip() if author_elem else "CodePen User"

                    # Pour CodePen, nous devons extraire le code depuis l'iframe ou les données JSON
                    # C'est plus complexe, donc on fait une extraction simplifiée

                    # Rechercher les scripts inline qui peuvent contenir le code
                    scripts = soup.find_all("script")
                    code_content = ""

                    for script in scripts:
                        if script.string and (
                            "html" in script.string.lower()
                            or "css" in script.string.lower()
                            or "js" in script.string.lower()
                        ):
                            # Extraire le code du JSON
                            try:
                                # Pattern pour extraire le code des données CodePen
                                if (
                                    '"html"' in script.string
                                    or '"css"' in script.string
                                    or '"js"' in script.string
                                ):
                                    code_content = self._extract_code_from_codepen_data(
                                        script.string, language
                                    )
                                    break
                            except Exception:
                                continue

                    if code_content:
                        return WebCodeSolution(
                            code=code_content,
                            language=language,
                            title=title,
                            description=f"Solution CodePen par {author}",
                            source_url=url,
                            source_name="CodePen",
                            rating=3.8,
                            difficulty="Intermédiaire",
                            tags=[language, "codepen", "web", "frontend"],
                            author=author,
                            created_at=datetime.now(),
                            votes=0,
                        )

        except Exception as e:
            print(f"Erreur parsing CodePen: {e}")

        return None

    def _extract_code_from_codepen_data(
        self, script_content: str, language: str
    ) -> str:
        """Extrait le code depuis les données CodePen"""
        # Pattern simplifié pour extraire le code
        language_map = {"html": "html", "css": "css", "javascript": "js", "js": "js"}

        lang_key = language_map.get(language.lower(), "js")

        # Rechercher le pattern JSON pour le langage
        pattern = rf'"{lang_key}"\s*:\s*"([^"]*)"'
        match = re.search(pattern, script_content)

        if match:
            # Décoder les échappements JSON
            code = match.group(1)
            code = (
                code.replace("\\n", "\n")
                .replace("\\t", "\t")
                .replace('\\"', '"')
                .replace("\\\\", "\\")
            )
            return code

        return ""


class LeetCodeSearcher:
    """Recherche de solutions sur LeetCode"""

    def __init__(self):
        self.base_url = "https://leetcode.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/html",
            "Accept-Language": "en-US,en;q=0.5",
        }

    async def search_solutions(
        self, query: str, language: str
    ) -> List[WebCodeSolution]:
        """Recherche des solutions sur LeetCode"""
        solutions = []

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                # LeetCode nécessite une approche différente
                # On peut chercher dans les discussions publiques
                search_terms = self._build_leetcode_search_terms(query)

                # URL pour chercher dans les problems
                search_url = (
                    f"{self.base_url}/problemset/all/?search={quote(search_terms)}"
                )

                async with session.get(search_url) as response:
                    if response.status == 200:

                        # LeetCode utilise beaucoup de JavaScript, donc extraction limitée
                        # On pourrait utiliser une approche alternative avec des sites comme
                        # leetcode-solutions ou des blogs qui répertorient les solutions

                        solutions = await self._search_leetcode_alternatives(
                            session, query, language
                        )

        except Exception as e:
            print(f"Erreur recherche LeetCode: {e}")

        return solutions

    def _build_leetcode_search_terms(self, query: str) -> str:
        """Construit des termes de recherche pour LeetCode"""
        # Mots-clés typiques pour les algorithmes
        algorithm_keywords = {
            "sort": "sorting algorithm",
            "search": "binary search",
            "tree": "binary tree",
            "graph": "graph traversal",
            "array": "array manipulation",
            "string": "string manipulation",
            "dynamic": "dynamic programming",
            "greedy": "greedy algorithm",
        }

        query_lower = query.lower()
        for keyword, replacement in algorithm_keywords.items():
            if keyword in query_lower:
                return replacement

        return query

    async def _search_leetcode_alternatives(
        self, session: aiohttp.ClientSession, query: str, language: str
    ) -> List[WebCodeSolution]:
        """Recherche dans des sites alternatifs avec solutions LeetCode"""
        solutions = []

        # Sites avec solutions LeetCode publiques
        alternative_sites = [
            "https://github.com/topics/leetcode-solutions",
            "https://www.programcreek.com/leetcode/",
            "https://walkccc.me/LeetCode/",
        ]

        try:
            for site_url in alternative_sites[:1]:  # Limiter à un site pour l'exemple
                async with session.get(site_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        # Rechercher des liens pertinents
                        for link in soup.find_all("a", href=True):
                            href = link["href"]
                            link_text = link.get_text().lower()

                            # Si le lien semble pertinent à la query
                            if any(
                                word in link_text for word in query.lower().split()[:3]
                            ):
                                # Ici on pourrait analyser la page, mais pour simplifier
                                # on crée une solution basique
                                solutions.append(
                                    self._create_basic_leetcode_solution(
                                        query, language, href
                                    )
                                )
                                break

                        if solutions:
                            break

        except Exception as e:
            print(f"Erreur recherche alternatives LeetCode: {e}")

        return solutions[:1]  # Une seule solution pour éviter la duplication

    def _create_basic_leetcode_solution(
        self, query: str, language: str, source_url: str
    ) -> WebCodeSolution:
        """Crée une solution LeetCode basique"""
        return WebCodeSolution(
            code=f"# Solution pour: {query}\n# TODO: Implémentation d'algorithme\n\ndef solution():\n    pass",
            language=language,
            title=f"Solution Algorithm: {query}",
            description=f"Solution d'algorithme pour: {query}",
            source_url=source_url,
            source_name="LeetCode Style",
            rating=4.0,
            difficulty="Avancé",
            tags=[language, "algorithm", "leetcode", "problem-solving"],
            author="Algorithm Expert",
            created_at=datetime.now(),
            votes=0,
        )


class W3SchoolsSearcher:
    """Recherche de code sur W3Schools"""

    def __init__(self):
        self.base_url = "https://www.w3schools.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    async def search_solutions(
        self, query: str, language: str
    ) -> List[WebCodeSolution]:
        """Recherche des solutions sur W3Schools"""
        solutions = []

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                # W3Schools a des sections par langage
                language_paths = {
                    "python": "python",
                    "javascript": "js",
                    "html": "html",
                    "css": "css",
                    "sql": "sql",
                    "php": "php",
                    "java": "java",
                }

                lang_path = language_paths.get(language.lower(), "python")

                # URL de recherche sur W3Schools
                search_url = f"{self.base_url}/{lang_path}/"

                async with session.get(search_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        # Trouver les liens vers les tutorials
                        tutorial_links = []
                        for link in soup.find_all("a", href=True):
                            href = link["href"]
                            if f"/{lang_path}/" in href and any(
                                keyword in href.lower()
                                for keyword in query.lower().split()[:2]
                            ):
                                full_url = urljoin(self.base_url, href)
                                tutorial_links.append(full_url)

                        # Analyser les tutorials
                        for url in tutorial_links[:3]:
                            tutorial_solution = await self._parse_w3schools_tutorial(
                                session, url, language
                            )
                            if tutorial_solution:
                                solutions.append(tutorial_solution)

        except Exception as e:
            print(f"Erreur recherche W3Schools: {e}")

        return solutions

    async def _parse_w3schools_tutorial(
        self, session: aiohttp.ClientSession, url: str, language: str
    ) -> Optional[WebCodeSolution]:
        """Parse un tutorial W3Schools"""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Extraire le titre
                    title_elem = soup.find("h1")
                    title = (
                        title_elem.text.strip() if title_elem else "W3Schools Tutorial"
                    )

                    # Extraire les exemples de code
                    code_examples = soup.find_all(
                        ["div"], {"class": ["w3-code", "w3-example"]}
                    )

                    if code_examples:
                        # Prendre le premier exemple de code
                        code_elem = code_examples[0]
                        code_text = code_elem.get_text().strip()

                        # Extraire la description
                        description_elem = code_elem.find_previous(["p", "h2", "h3"])
                        description = (
                            description_elem.text.strip()
                            if description_elem
                            else f"Tutorial W3Schools: {title}"
                        )

                        return WebCodeSolution(
                            code=code_text,
                            language=language,
                            title=title,
                            description=description[:200],
                            source_url=url,
                            source_name="W3Schools",
                            rating=4.0,
                            difficulty="Débutant",
                            tags=[language, "w3schools", "tutorial", "beginner"],
                            author="W3Schools Team",
                            created_at=datetime.now(),
                            votes=0,
                        )

        except Exception as e:
            print(f"Erreur parsing W3Schools: {e}")

        return None


class GitHubSearcher:
    """Recherche de code sur GitHub via API"""

    def __init__(self):
        self.base_url = "https://api.github.com"
        self.headers = {
            "User-Agent": "MyAI-CodeSearcher/1.0",
            "Accept": "application/vnd.github.v3+json",
        }
        if GITHUB_TOKEN:
            self.headers["Authorization"] = f"token {GITHUB_TOKEN}"

    async def search_solutions(
        self, query: str, language: str
    ) -> List[WebCodeSolution]:
        """Recherche des solutions sur GitHub"""
        solutions = []

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                # Construire la requête de recherche GitHub
                search_query = self._build_github_query(query, language)
                search_url = f"{self.base_url}/search/repositories?q={quote(search_query)}&sort=stars&order=desc&per_page=5"

                async with session.get(search_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        repositories = data.get("items", [])

                        # Analyser les premiers repositories
                        for repo in repositories[:3]:
                            repo_solutions = await self._analyze_github_repository(
                                session, repo, query, language
                            )
                            solutions.extend(repo_solutions)

        except Exception as e:
            print(f"Erreur recherche GitHub: {e}")

        return solutions[:2]  # Limiter pour éviter la surcharge

    def _build_github_query(self, query: str, language: str) -> str:
        """Construit une requête optimisée pour GitHub"""
        # Mots-clés spécifiques par langage
        query_parts = [query]

        if language.lower() == "python":
            query_parts.extend(["python", "script", "example"])
        elif language.lower() in ["javascript", "js"]:
            query_parts.extend(["javascript", "js", "example"])
        elif language.lower() == "html":
            query_parts.extend(["html", "template", "example"])

        # Ajouter des filtres de qualité
        query_parts.append("stars:>10")  # Au moins 10 étoiles
        query_parts.append(f"language:{language}")

        return " ".join(query_parts)

    async def _analyze_github_repository(
        self, session: aiohttp.ClientSession, repo: dict, query: str, language: str
    ) -> List[WebCodeSolution]:
        """Analyse un repository GitHub pour extraire le code pertinent"""
        solutions = []

        try:
            repo_name = repo["full_name"]
            repo_url = repo["html_url"]

            # Rechercher les fichiers pertinents dans le repository
            contents_url = f"{self.base_url}/repos/{repo_name}/contents"

            async with session.get(contents_url) as response:
                if response.status == 200:
                    contents = await response.json()

                    # Filtrer les fichiers par extension
                    relevant_files = self._filter_relevant_files(contents, language)

                    for file_info in relevant_files[:2]:  # Max 2 fichiers par repo
                        file_content = await self._get_file_content(
                            session, repo_name, file_info["path"]
                        )

                        if file_content and self._is_relevant_to_query(
                            file_content, query
                        ):
                            solution = WebCodeSolution(
                                code=file_content,
                                language=language,
                                title=f"{repo['name']} - {file_info['name']}",
                                description=f"Code from {repo_name}: {repo.get('description', '')}",
                                source_url=f"{repo_url}/blob/main/{file_info['path']}",
                                source_name="GitHub",
                                rating=min(5.0, repo.get("stargazers_count", 0) / 100),
                                difficulty=self._estimate_difficulty(file_content),
                                tags=[language, "github", "open-source"],
                                author=repo.get("owner", {}).get("login", "Unknown"),
                                created_at=datetime.now(),
                                votes=repo.get("stargazers_count", 0),
                            )
                            solutions.append(solution)

        except Exception as e:
            print(f"Erreur analyse repo {repo.get('name', 'unknown')}: {e}")

        return solutions

    def _filter_relevant_files(self, contents: list, language: str) -> list:
        """Filtre les fichiers pertinents selon le langage"""
        extensions = {
            "python": [".py"],
            "javascript": [".js", ".ts"],
            "html": [".html", ".htm"],
            "css": [".css"],
            "java": [".java"],
            "cpp": [".cpp", ".cc", ".cxx"],
            "c": [".c", ".h"],
        }

        valid_extensions = extensions.get(language.lower(), [".py"])
        relevant_files = []

        for item in contents:
            if item.get("type") == "file":
                file_name = item.get("name", "")
                if any(file_name.lower().endswith(ext) for ext in valid_extensions):
                    # Éviter les fichiers de test ou de documentation
                    if not any(
                        skip in file_name.lower()
                        for skip in ["test", "spec", "readme", "__pycache__"]
                    ):
                        relevant_files.append(item)

        return relevant_files

    async def _get_file_content(
        self, session: aiohttp.ClientSession, repo_name: str, file_path: str
    ) -> str:
        """Récupère le contenu d'un fichier GitHub"""
        try:
            file_url = f"{self.base_url}/repos/{repo_name}/contents/{file_path}"

            async with session.get(file_url) as response:
                if response.status == 200:
                    file_data = await response.json()

                    # Décoder le contenu base64
                    if file_data.get("encoding") == "base64":

                        content = base64.b64decode(file_data["content"]).decode(
                            "utf-8", errors="ignore"
                        )

                        # Limiter la taille du contenu
                        if len(content) > 2000:
                            content = content[:2000] + "\n# ... (fichier tronqué)"

                        return content

        except Exception as e:
            print(f"Erreur récupération fichier {file_path}: {e}")

        return ""

    def _is_relevant_to_query(self, content: str, query: str) -> bool:
        """Vérifie si le contenu est pertinent pour la requête - VERSION STRICTE"""
        content_lower = content.lower()
        query_lower = query.lower()

        # Extraire les mots-clés techniques de la requête
        tech_keywords = self._extract_tech_keywords_from_query(query_lower)

        # Vérification stricte : au moins 60% des mots-clés techniques doivent être présents
        if tech_keywords:
            matches = sum(1 for keyword in tech_keywords if keyword in content_lower)
            relevance_score = matches / len(tech_keywords)

            print(
                f"[DEBUG] Pertinence: {relevance_score:.2f} pour '{query[:30]}...' | Mots-clés: {tech_keywords} | Matches: {matches}"
            )

            # Score minimum de 60% pour la pertinence
            return relevance_score >= 0.6

        return False

    def _extract_tech_keywords_from_query(self, query_lower: str) -> list:
        """Extrait les mots-clés techniques importants de la requête"""
        # Dictionnaire de concepts techniques
        tech_concepts = {
            "concat": ["concat", "concatenate", "join", "combine", "merge"],
            "string": ["string", "chaîne", "chaine", "caractère", "caractere", "str"],
            "function": ["function", "fonction", "def"],
            "sort": ["sort", "tri", "trier", "order"],
            "file": ["file", "fichier", "read", "write", "lire", "écrire"],
            "api": ["api", "rest", "endpoint", "request"],
            "database": ["database", "db", "sql", "base"],
            "array": ["array", "list", "liste", "tableau"],
            "loop": ["loop", "for", "while", "boucle"],
            "class": ["class", "classe", "object", "objet"],
        }

        keywords = []

        # Rechercher les concepts dans la requête
        for variations in tech_concepts.items():
            if any(var in query_lower for var in variations):
                keywords.extend(variations[:2])  # Prendre les 2 premières variations

        # Ajouter les mots importants directement de la requête
        important_words = []
        words = query_lower.split()
        for word in words:
            if len(word) > 3 and word not in [
                "avec",
                "pour",
                "dans",
                "une",
                "des",
                "qui",
                "que",
            ]:
                important_words.append(word)

        # Combiner et dédupliquer
        all_keywords = list(set(keywords + important_words))
        return all_keywords[:5]  # Limiter à 5 mots-clés max

    def _estimate_difficulty(self, content: str) -> str:
        """Estime la difficulté du code"""
        lines = len(content.split("\n"))
        complexity_indicators = [
            "class ",
            "def ",
            "for ",
            "while ",
            "if ",
            "try:",
            "import ",
            "from ",
        ]

        complexity_count = sum(
            content.count(indicator) for indicator in complexity_indicators
        )

        if lines <= 20 and complexity_count <= 5:
            return "Débutant"
        elif lines <= 100 and complexity_count <= 15:
            return "Intermédiaire"
        else:
            return "Avancé"


class MultiSourceCodeSearcher:
    """Coordonnateur pour la recherche multi-sources"""

    def __init__(self):
        self.searchers = {
            "github": GitHubSearcher(),
            "geeksforgeeks": GeeksForGeeksSearcher(),
            "codepen": CodePenSearcher(),
            "leetcode": LeetCodeSearcher(),
            "w3schools": W3SchoolsSearcher(),
        }

        # Configuration par langage avec GitHub en première priorité
        self.source_preferences = {
            "python": ["github", "geeksforgeeks", "leetcode", "w3schools"],
            "javascript": ["github", "codepen", "w3schools", "geeksforgeeks"],
            "html": ["github", "w3schools", "codepen"],
            "css": ["github", "w3schools", "codepen"],
            "java": ["github", "geeksforgeeks", "leetcode"],
            "cpp": ["github", "geeksforgeeks", "leetcode"],
            "sql": ["github", "w3schools", "geeksforgeeks"],
            "php": ["github", "w3schools"],
            "go": ["github", "geeksforgeeks"],
            "rust": ["github", "geeksforgeeks"],
            "swift": ["github"],
            "kotlin": ["github"],
        }

    async def search_all_sources(
        self, query: str, language: str, max_results: int = 6
    ) -> List[WebCodeSolution]:
        """Recherche dans toutes les sources pertinentes"""
        all_solutions = []

        # Déterminer les sources préférées pour ce langage
        preferred_sources = self.source_preferences.get(
            language.lower(), ["geeksforgeeks", "w3schools"]
        )

        # Lancer les recherches en parallèle
        tasks = []
        for source_name in preferred_sources:
            if source_name in self.searchers:
                searcher = self.searchers[source_name]
                task = searcher.search_solutions(query, language)
                tasks.append((source_name, task))

        # Attendre les résultats
        for source_name, task in tasks:
            try:
                solutions = await task
                all_solutions.extend(solutions)
            except Exception as e:
                print(f"Erreur source {source_name}: {e}")

        # Trier et filtrer les résultats
        ranked_solutions = self._rank_solutions(all_solutions, query)

        return ranked_solutions[:max_results]

    def _rank_solutions(
        self, solutions: List[WebCodeSolution], query: str
    ) -> List[WebCodeSolution]:
        """Classe les solutions par pertinence"""
        if not solutions:
            return []

        scored_solutions = []
        query_words = set(query.lower().split())

        for solution in solutions:
            score = 0

            # Score de base
            score += solution.rating

            # Bonus pour correspondance du titre
            title_words = set(solution.title.lower().split())
            title_match = len(query_words & title_words)
            score += title_match * 2

            # Bonus pour correspondance de la description
            desc_words = set(solution.description.lower().split())
            desc_match = len(query_words & desc_words)
            score += desc_match * 1

            # Bonus pour source fiable (GitHub en tête)
            source_bonus = {
                "GitHub": 3,  # Bonus maximum pour GitHub
                "GeeksforGeeks": 2,
                "W3Schools": 1.5,
                "CodePen": 1,
                "LeetCode Style": 1.5,
            }
            score += source_bonus.get(solution.source_name, 0)

            # Bonus pour longueur de code appropriée
            code_length = len(solution.code)
            if 50 <= code_length <= 300:
                score += 2
            elif code_length <= 50:
                score += 1

            scored_solutions.append((score, solution))

        # Trier par score décroissant
        scored_solutions.sort(key=lambda x: x[0], reverse=True)

        return [solution for score, solution in scored_solutions]

    async def get_best_solution(
        self, query: str, language: str
    ) -> Optional[WebCodeSolution]:
        """Récupère la meilleure solution pour une requête"""
        solutions = await self.search_all_sources(query, language, max_results=1)
        return solutions[0] if solutions else None

    def get_supported_languages(self) -> List[str]:
        """Retourne la liste des langages supportés"""
        return list(self.source_preferences.keys())

    def get_available_sources(self) -> List[str]:
        """Retourne la liste des sources disponibles"""
        return list(self.searchers.keys())


# Instance globale
multi_source_searcher = MultiSourceCodeSearcher()


# Fonctions utilitaires
async def search_code_examples(
    query: str, language: str = "python"
) -> List[Dict[str, Any]]:
    """Recherche des exemples de code dans toutes les sources"""
    solutions = await multi_source_searcher.search_all_sources(query, language)

    return [
        {
            "code": sol.code,
            "title": sol.title,
            "description": sol.description,
            "source": sol.source_name,
            "rating": sol.rating,
            "difficulty": sol.difficulty,
            "url": sol.source_url,
        }
        for sol in solutions
    ]


async def get_tutorial_code(topic: str, language: str = "python") -> Optional[str]:
    """Récupère du code tutorial pour un sujet"""
    solution = await multi_source_searcher.get_best_solution(topic, language)
    return solution.code if solution else None


if __name__ == "__main__":
    # Test du système
    async def test_multi_source_search():
        """Test de la recherche multi-sources"""
        searcher = MultiSourceCodeSearcher()

        test_queries = [
            ("bubble sort algorithm", "python"),
            ("form validation", "javascript"),
            ("responsive navbar", "css"),
            ("file upload", "html"),
            ("database connection", "python"),
        ]

        for query, language in test_queries:
            print(f"\n🔍 Recherche: '{query}' en {language}")
            solutions = await searcher.search_all_sources(
                query, language, max_results=3
            )

            if solutions:
                for i, solution in enumerate(solutions, 1):
                    print(f"\n{i}. {solution.title}")
                    print(f"   Source: {solution.source_name}")
                    print(f"   Rating: {solution.rating}/5.0")
                    print(f"   Difficulté: {solution.difficulty}")
                    print(f"   Code (extrait): {solution.code[:100]}...")
            else:
                print("   ❌ Aucune solution trouvée")

    # Exécuter le test
    # asyncio.run(test_multi_source_search())
