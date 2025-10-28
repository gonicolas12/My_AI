"""
🚀 Smart Code Searcher - Recherche de code intelligente
Rivalise avec ChatGPT/Claude en combinant recherche web + analyse sémantique
100% local, pas d'IA externe
"""

import asyncio
import hashlib
import json
import re
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote, urlparse

import aiohttp
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer, util


@dataclass
class CodeSnippet:
    """Représente un snippet de code trouvé"""
    code: str
    language: str
    title: str
    description: str
    source_url: str
    source_name: str
    quality_score: float = 0.0
    relevance_score: float = 0.0
    final_score: float = 0.0
    tags: List[str] = field(default_factory=list)
    votes: int = 0
    views: int = 0


class SmartCodeSearcher:
    """
    Recherche de code intelligente avec:
    - Recherche web DuckDuckGo
    - Analyse sémantique avec embeddings
    - Ranking intelligent des solutions
    - Cache avec similarité
    """

    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.timeout = 10
        self.max_results = 8

        # Modèle d'embeddings pour analyse sémantique
        try:
            print("📦 Chargement du modèle d'embeddings...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.embeddings_enabled = True
            print("✅ Modèle d'embeddings chargé")
        except Exception as e:
            print(f"⚠️ Embeddings désactivés: {e}")
            self.embedding_model = None
            self.embeddings_enabled = False

        # Cache intelligent
        self.cache_file = Path(__file__).parent.parent / "context_storage" / "code_cache.json"
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache = self._load_cache()

        # Sites prioritaires pour la recherche de code
        self.priority_sites = [
            "github.com",
            "stackoverflow.com",
            "geeksforgeeks.org",
            "realpython.com",
            "pythontutor.com",
            "w3schools.com",
            "developer.mozilla.org",
            "docs.python.org"
        ]

    def _load_cache(self) -> Dict:
        """Charge le cache depuis le fichier"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Erreur chargement cache: {e}")
        return {"queries": {}, "embeddings": {}}

    def _save_cache(self):
        """Sauvegarde le cache"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde cache: {e}")

    async def search_code(self, query: str, language: str = "python") -> List[CodeSnippet]:
        """
        Recherche intelligente de code

        Args:
            query: La demande utilisateur (ex: "code python pour jouer au shifumi")
            language: Langage de programmation

        Returns:
            Liste de snippets de code classés par pertinence
        """
        print(f"\n🔍 Recherche de code: '{query}' ({language})")

        # 1. Vérifier le cache
        cached_result = self._check_cache(query, language)
        if cached_result:
            print("⚡ Résultat trouvé dans le cache")
            return cached_result

        # 2. Optimiser la requête de recherche
        optimized_query = self._optimize_search_query(query, language)
        print(f"🎯 Requête optimisée: '{optimized_query}'")

        # 3. Recherche web multi-sources
        web_results = await self._search_web(optimized_query, language)
        print(f"📊 {len(web_results)} résultats web trouvés")

        # 4. Extraire les snippets de code
        code_snippets = await self._extract_code_snippets(web_results, query, language)
        print(f"💻 {len(code_snippets)} snippets de code extraits")

        # 5. Scorer et ranker les snippets
        if self.embeddings_enabled:
            ranked_snippets = self._rank_with_embeddings(code_snippets, query)
        else:
            ranked_snippets = self._rank_without_embeddings(code_snippets, query)

        print(f"⭐ Top 3 scores: {[f'{s.final_score:.2f}' for s in ranked_snippets[:3]]}")

        # 6. Sauvegarder dans le cache
        self._save_to_cache(query, language, ranked_snippets[:5])

        return ranked_snippets

    def _optimize_search_query(self, query: str, language: str) -> str:
        """
        Optimise la requête pour la recherche web
        Transforme "code python pour shifumi" en requête optimale
        """
        query_lower = query.lower()

        # Mapper les synonymes français -> anglais (meilleurs résultats)
        synonyms = {
            "shifumi": "rock paper scissors",
            "pierre papier ciseaux": "rock paper scissors",
            "morpion": "tic tac toe",
            "pendu": "hangman game",
            "calculatrice": "calculator",
            "jeu de": "game",
            "générateur": "generator",
            "outil": "tool",
            "script": "script"
        }

        # Remplacer les synonymes
        optimized = query_lower
        for fr, en in synonyms.items():
            if fr in optimized:
                optimized = optimized.replace(fr, en)

        # Ajouter des mots-clés de qualité
        quality_keywords = []

        # Ajouter le langage
        if language.lower() not in optimized:
            quality_keywords.append(language)

        # Ajouter "code" ou "example" si absent
        if "code" not in optimized and "example" not in optimized:
            quality_keywords.append("code example")

        # Ajouter github pour avoir du code de qualité
        quality_keywords.append("github")

        # Construire la requête finale
        final_query = f"{optimized} {' '.join(quality_keywords)}"

        # Nettoyer
        final_query = re.sub(r'\s+', ' ', final_query).strip()

        return final_query

    async def _search_web(self, query: str, _language: str) -> List[Dict]:
        """Recherche web avec DuckDuckGo"""
        results = []

        # Recherche HTML DuckDuckGo (plus de résultats)
        try:
            results.extend(await self._search_duckduckgo_html(query))
        except Exception as e:
            print(f"⚠️ Erreur DuckDuckGo HTML: {e}")

        # Filtrer pour garder les sites de code prioritaires
        filtered_results = []
        for result in results:
            url = result.get("url", "")
            # Bonus pour les sites prioritaires
            if any(site in url for site in self.priority_sites):
                result["priority"] = True
                filtered_results.insert(0, result)  # Mettre en premier
            else:
                result["priority"] = False
                filtered_results.append(result)

        return filtered_results[:self.max_results]

    async def _search_duckduckgo_html(self, query: str) -> List[Dict]:
        """Recherche via la version HTML de DuckDuckGo"""
        results = []

        search_url = f"https://html.duckduckgo.com/html/?q={quote(query)}"

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, headers=headers, timeout=self.timeout) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')

                        for result_div in soup.find_all('div', class_='result')[:self.max_results]:
                            title_elem = result_div.find('a', class_='result__a')
                            snippet_elem = result_div.find('a', class_='result__snippet')

                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                url = title_elem.get('href', '')
                                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                                # 🔧 FIX: Décoder les URLs de redirection DuckDuckGo
                                if '//duckduckgo.com/l/?uddg=' in url or '/l/?uddg=' in url:
                                    # Extraire l'URL réelle depuis le paramètre uddg
                                    if '?uddg=' in url:
                                        encoded_part = url.split('?uddg=')[1].split('&')[0]
                                        try:
                                            url = urllib.parse.unquote(encoded_part)
                                            print(f"✅ URL décodée: {url[:60]}...")
                                        except Exception:
                                            pass

                                # Corriger les URLs relatives
                                if url.startswith('//'):
                                    url = 'https:' + url
                                elif url.startswith('/'):
                                    url = 'https://duckduckgo.com' + url

                                if title and url and url.startswith('http'):
                                    results.append({
                                        "title": title,
                                        "url": url,
                                        "snippet": snippet,
                                        "source": "DuckDuckGo"
                                    })
        except Exception as e:
            print(f"⚠️ Erreur recherche DuckDuckGo: {e}")

        return results

    async def _extract_code_snippets(self, web_results: List[Dict],
                                    query: str, language: str) -> List[CodeSnippet]:
        """Extrait les snippets de code depuis les résultats web"""
        snippets = []

        # Traiter chaque résultat en parallèle
        tasks = []
        async with aiohttp.ClientSession() as session:
            for result in web_results:
                task = self._extract_from_url(session, result, query, language)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    snippets.extend(result)
                elif isinstance(result, Exception):
                    print(f"⚠️ Erreur extraction: {result}")

        return snippets

    async def _extract_from_url(self, session: aiohttp.ClientSession,
                                result: Dict, _query: str, language: str) -> List[CodeSnippet]:
        """Extrait le code d'une URL spécifique"""
        snippets = []
        url = result.get("url", "")

        if not url or not url.startswith("http"):
            print(f"⚠️ URL invalide ignorée: {url}")
            return snippets

        print(f"🔍 Extraction depuis: {url[:60]}...")

        try:
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9"
            }

            async with session.get(url, headers=headers, timeout=self.timeout, allow_redirects=True) as response:
                if response.status != 200:
                    print(f"⚠️ Status {response.status} pour {url}")
                    return snippets

                html = await response.text()
                print(f"✅ HTML récupéré: {len(html)} caractères")

                soup = BeautifulSoup(html, 'html.parser')

                # Extraire les blocs de code
                code_blocks = self._find_code_blocks(soup, language)
                print(f"📦 {len(code_blocks)} blocs de code trouvés")

                # 🔧 FIX: Trier les blocs par taille (les plus longs d'abord)
                # Cela garantit qu'on prend le code complet, pas juste une ligne
                code_blocks.sort(key=lambda x: len(x.get("code", "")), reverse=True)
                print("   🎯 Blocs triés par taille (le plus long en premier)")

                for i, code_block in enumerate(code_blocks[:3]):  # Max 3 par page
                    code_text = code_block.get("code", "").strip()
                    lines_count = len(code_text.split('\n'))
                    print(f"   Bloc #{i+1}: {len(code_text)} caractères, {lines_count} lignes, source: {code_block.get('source', 'unknown')}")
                    print(f"      Aperçu: {code_text[:150].replace(chr(10), ' ')[:150]}...")

                    if self._is_valid_code(code_text, language):
                        print("   ✅ Code valide!")
                        snippet = CodeSnippet(
                            code=code_text,
                            language=language,
                            title=result.get("title", "Code snippet"),
                            description=result.get("snippet", ""),
                            source_url=url,
                            source_name=self._extract_domain(url),
                            tags=[language, "web"]
                        )

                        # Calculer le score de qualité initial
                        snippet.quality_score = self._calculate_quality_score(snippet, url)

                        snippets.append(snippet)
                        print(f"   📊 Snippet ajouté! Total: {len(snippets)}")
                    else:
                        print("   ❌ Code invalide (trop court ou mauvais format)")

                print(f"🎯 {len(snippets)} snippets valides extraits de {url[:40]}...")

        except asyncio.TimeoutError:
            print(f"⏱️ Timeout lors de l'accès à {url}")
        except Exception as e:
            print(f"⚠️ Erreur extraction URL {url}: {e}")

        return snippets

    def _find_code_blocks(self, soup: BeautifulSoup, language: str) -> List[Dict]:
        """Trouve tous les blocs de code dans une page - VERSION AMÉLIORÉE"""
        code_blocks = []
        seen_codes = set()  # Pour éviter les doublons

        def add_unique_code(code_text: str, source: str):
            """Ajoute un code unique"""
            code_hash = hashlib.md5(code_text.encode()).hexdigest()[:8]
            if code_hash not in seen_codes and len(code_text.strip()) > 10:
                seen_codes.add(code_hash)
                code_blocks.append({"code": code_text, "source": source})

        # 1. Balises <pre><code> (priorité haute)
        for pre in soup.find_all('pre'):
            code_elem = pre.find('code')
            if code_elem:
                add_unique_code(code_elem.get_text(), "pre>code")
            else:
                # Parfois le code est directement dans <pre>
                pre_text = pre.get_text()
                if len(pre_text.strip()) > 30:  # Au moins 30 caractères
                    add_unique_code(pre_text, "pre")

        # 2. Balises <code> seules (si assez longues)
        for code in soup.find_all('code'):
            code_text = code.get_text()
            lines = code_text.split('\n')
            # Au moins 3 lignes OU au moins 50 caractères
            if len(lines) >= 3 or len(code_text) >= 50:
                add_unique_code(code_text, "code")

        # 3. Divs et spans avec classes de code (très courant sur GitHub, StackOverflow)
        code_selectors = [
            ('div', 'highlight'),
            ('div', 'code'),
            ('div', 'codehilite'),
            ('div', f'language-{language}'),
            ('div', 'sourceCode'),
            ('div', 'syntax'),
            ('div', 'code-block'),
            ('div', 'snippet'),
            ('div', 'blob-code'),  # GitHub
            ('td', 'blob-code'),   # GitHub
            ('div', 'js-file-line'),  # GitHub
            ('pre', 'sh_sourceCode'),  # StackOverflow
            ('div', 'answer'),  # StackOverflow (chercher le code dedans)
        ]

        for tag_name, class_hint in code_selectors:
            for elem in soup.find_all(tag_name, class_=re.compile(class_hint, re.I)):
                # Pour les divs de réponse, chercher le code à l'intérieur
                if 'answer' in class_hint.lower() or 'post' in class_hint.lower():
                    inner_code = elem.find_all(['pre', 'code'])
                    for inner in inner_code:
                        add_unique_code(inner.get_text(), f"{tag_name}.{class_hint}>code")
                else:
                    elem_text = elem.get_text()
                    if len(elem_text.strip()) > 30:
                        add_unique_code(elem_text, f"{tag_name}.{class_hint}")

        # 4. Recherche aggressive dans le texte brut (dernier recours)
        # Si vraiment aucun bloc n'est trouvé, chercher des patterns de code Python
        if len(code_blocks) == 0 and language.lower() == 'python':
            print("   🔍 Recherche aggressive de code Python...")
            body_text = soup.get_text()

            # Chercher des patterns de code Python
            python_patterns = [
                r'(def\s+\w+\(.*?\):.*?(?=\n\n|\nclass|\ndef|\Z))',
                r'(class\s+\w+.*?:.*?(?=\n\nclass|\ndef|\Z))',
                r'(import\s+\w+.*?(?:\n.*?)+?(?=\n\n|\Z))',
            ]

            for pattern in python_patterns:
                matches = re.findall(pattern, body_text, re.DOTALL)
                for match in matches[:3]:  # Max 3 patterns
                    if len(match) > 50:
                        add_unique_code(match, "regex_pattern")

        print(f"   📊 {len(code_blocks)} blocs uniques trouvés")
        return code_blocks

    def _is_valid_code(self, code: str, language: str) -> bool:
        """Vérifie si le code est valide et pertinent - VERSION ASSOUPLIE"""
        if not code or len(code.strip()) < 20:
            return False

        # Vérifier la présence d'indicateurs de langage
        language_indicators = {
            'python': ['def ', 'import ', 'class ', 'if __name__', 'print(', 'return', 'for ', 'while ', 'if ', ':', '    '],
            'javascript': ['function ', 'const ', 'let ', 'var ', '=>', 'console.', 'return', '{', '}'],
            'java': ['public class', 'public static', 'void ', 'System.out', 'import java', '{', '}'],
            'cpp': ['#include', 'int main', 'std::', 'cout', '::', 'return', '{', '}'],
            'html': ['<html', '<div', '<body', '<head', '<script', '<', '>'],
            'css': ['{', '}', ':', ';', 'px', 'color', 'margin', '#', '.'],
        }

        indicators = language_indicators.get(language.lower(), [])

        # Compter les indicateurs présents
        matches = sum(1 for indicator in indicators if indicator in code)

        # Critères assouplis:
        # - Au moins 2 indicateurs pour les langages stricts (Java, C++)
        # - Au moins 1 indicateur pour les langages flexibles (Python, JS)
        if language.lower() in ['python', 'javascript', 'js']:
            min_indicators = 1
        else:
            min_indicators = 2

        # Bonus: si le code contient des lignes multiples, c'est probablement du vrai code
        line_count = len(code.split('\n'))
        if line_count >= 5:
            min_indicators = max(1, min_indicators - 1)  # Réduire le minimum requis

        is_valid = matches >= min_indicators

        if not is_valid:
            print(f"      ❌ Validation échouée: {matches} indicateurs trouvés (minimum: {min_indicators})")
            print(f"         Code preview: {code[:100]}...")

        return is_valid

    def _calculate_quality_score(self, snippet: CodeSnippet, url: str) -> float:
        """Calcule le score de qualité d'un snippet"""
        score = 0.0

        # Bonus pour les sites de confiance
        domain = self._extract_domain(url)
        site_scores = {
            "github.com": 10.0,
            "stackoverflow.com": 9.0,
            "geeksforgeeks.org": 8.0,
            "realpython.com": 8.5,
            "pythontutor.com": 7.0,
            "w3schools.com": 7.5,
            "developer.mozilla.org": 9.0,
        }

        for site, site_score in site_scores.items():
            if site in domain:
                score += site_score
                break
        else:
            score += 5.0  # Score par défaut

        # Bonus pour la longueur du code (ni trop court ni trop long)
        code_length = len(snippet.code)
        if 100 <= code_length <= 500:
            score += 5.0
        elif 50 <= code_length <= 1000:
            score += 3.0
        elif code_length > 1000:
            score += 1.0

        # Bonus pour les commentaires
        comment_count = snippet.code.count('#') + snippet.code.count('//')
        score += min(comment_count * 0.5, 3.0)

        # Bonus pour les fonctions/classes
        if 'def ' in snippet.code or 'class ' in snippet.code:
            score += 3.0
        if 'function ' in snippet.code:
            score += 3.0

        return score

    def _rank_with_embeddings(self, snippets: List[CodeSnippet], query: str) -> List[CodeSnippet]:
        """Ranking intelligent avec embeddings sémantiques"""
        if not snippets:
            return []

        # Générer l'embedding de la requête
        query_embedding = self.embedding_model.encode(query, convert_to_tensor=True)

        for snippet in snippets:
            # Générer l'embedding du code + description
            text_to_embed = f"{snippet.title} {snippet.description} {snippet.code[:200]}"
            code_embedding = self.embedding_model.encode(text_to_embed, convert_to_tensor=True)

            # Calculer la similarité sémantique
            similarity = util.pytorch_cos_sim(query_embedding, code_embedding).item()
            snippet.relevance_score = similarity * 10  # Normaliser à 0-10

            # Score final = qualité + pertinence
            snippet.final_score = snippet.quality_score + snippet.relevance_score

        # Trier par score final
        snippets.sort(key=lambda x: x.final_score, reverse=True)

        return snippets

    def _rank_without_embeddings(self, snippets: List[CodeSnippet], query: str) -> List[CodeSnippet]:
        """Ranking sans embeddings (fallback)"""
        if not snippets:
            return []

        query_words = set(query.lower().split())

        for snippet in snippets:
            # Calculer la pertinence par mots-clés
            text = f"{snippet.title} {snippet.description} {snippet.code}".lower()
            text_words = set(text.split())

            # Intersection des mots
            common_words = query_words.intersection(text_words)
            snippet.relevance_score = len(common_words) * 2.0

            # Score final
            snippet.final_score = snippet.quality_score + snippet.relevance_score

        # Trier par score final
        snippets.sort(key=lambda x: x.final_score, reverse=True)

        return snippets

    def _extract_domain(self, url: str) -> str:
        """Extrait le domaine d'une URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return "unknown"

    def _check_cache(self, query: str, language: str) -> Optional[List[CodeSnippet]]:
        """Vérifie si une requête similaire est en cache"""
        cache_key = f"{query.lower()}_{language.lower()}"

        if cache_key in self.cache.get("queries", {}):
            cached_data = self.cache["queries"][cache_key]

            # Reconstruire les snippets
            snippets = []
            for data in cached_data:
                snippet = CodeSnippet(**data)
                snippets.append(snippet)

            return snippets

        return None

    def _save_to_cache(self, query: str, language: str, snippets: List[CodeSnippet]):
        """Sauvegarde les résultats dans le cache"""
        cache_key = f"{query.lower()}_{language.lower()}"

        # Convertir les snippets en dict
        snippets_data = []
        for snippet in snippets:
            snippets_data.append({
                "code": snippet.code,
                "language": snippet.language,
                "title": snippet.title,
                "description": snippet.description,
                "source_url": snippet.source_url,
                "source_name": snippet.source_name,
                "quality_score": snippet.quality_score,
                "relevance_score": snippet.relevance_score,
                "final_score": snippet.final_score,
                "tags": snippet.tags,
                "votes": snippet.votes,
                "views": snippet.views
            })

        if "queries" not in self.cache:
            self.cache["queries"] = {}

        self.cache["queries"][cache_key] = snippets_data

        # Limiter la taille du cache (max 100 requêtes)
        if len(self.cache["queries"]) > 100:
            # Garder les 100 plus récentes
            keys = list(self.cache["queries"].keys())
            for old_key in keys[:-100]:
                del self.cache["queries"][old_key]

        self._save_cache()


# Instance globale
smart_code_searcher = SmartCodeSearcher()


# Fonction principale pour utilisation simple
async def search_code_smart(query: str, language: str = "python") -> List[CodeSnippet]:
    """
    Fonction simple pour rechercher du code

    Usage:
        snippets = await search_code_smart("code python pour shifumi")
        print(snippets[0].code)
    """
    return await smart_code_searcher.search_code(query, language)


# Test
if __name__ == "__main__":
    async def test():
        """Test de la recherche intelligente de code"""
        # Test avec shifumi
        results = await search_code_smart("jeu pierre papier ciseaux", "python")

        print(f"\n🎯 Trouvé {len(results)} solutions\n")

        for i, snippet in enumerate(results[:3], 1):
            print(f"{'='*60}")
            print(f"Solution #{i} - Score: {snippet.final_score:.2f}")
            print(f"Source: {snippet.source_name} - {snippet.source_url}")
            print(f"Qualité: {snippet.quality_score:.2f} | Pertinence: {snippet.relevance_score:.2f}")
            print(f"\n{snippet.code[:300]}...")
            print()

    asyncio.run(test())
