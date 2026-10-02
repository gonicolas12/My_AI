"""
🧠 Analyseur de Documents Intelligent - Sans LLM externe
Architecture modulaire pour comprendre, analyser et répondre sur n'importe quel document

Ce module implémente une vraie intelligence documentaire basée sur:
- Extraction d'entités et de relations
- Graphe de connaissances dynamique
- Analyse syntaxique et sémantique
- Génération de réponses naturelles
"""

import re
import hashlib
from collections import defaultdict, Counter
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class EntityType(Enum):
    """Types d'entités reconnaissables"""

    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    TIME = "time"
    NUMBER = "number"
    VERSION = "version"
    TECHNOLOGY = "technology"
    CONCEPT = "concept"
    ACTION = "action"
    PROPERTY = "property"
    VALUE = "value"
    CODE = "code"
    FILE = "file"
    URL = "url"


class RelationType(Enum):
    """Types de relations entre entités"""

    IS_A = "is_a"
    HAS = "has"
    BELONGS_TO = "belongs_to"
    CREATED_BY = "created_by"
    LOCATED_IN = "located_in"
    OCCURRED_AT = "occurred_at"
    VALUE_OF = "value_of"
    USES = "uses"
    PRODUCES = "produces"
    REQUIRES = "requires"
    EQUALS = "equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"


@dataclass
class Entity:
    """Représente une entité extraite d'un document"""

    text: str
    entity_type: EntityType
    start_pos: int
    end_pos: int
    confidence: float
    context: str = ""
    normalized_form: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash((self.text.lower(), self.entity_type))

    def __eq__(self, other):
        if isinstance(other, Entity):
            return (
                self.text.lower() == other.text.lower()
                and self.entity_type == other.entity_type
            )
        return False


@dataclass
class Relation:
    """Représente une relation entre deux entités"""

    source: Entity
    target: Entity
    relation_type: RelationType
    confidence: float
    context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Fact:
    """Représente un fait extrait (triplet sujet-prédicat-objet)"""

    subject: str
    predicate: str
    object: str
    confidence: float
    source_text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentSection:
    """Représente une section de document analysée"""

    title: str
    content: str
    level: int  # Niveau hiérarchique (1=titre principal, 2=sous-titre, etc.)
    entities: List[Entity] = field(default_factory=list)
    facts: List[Fact] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    summary: str = ""
    parent: Optional["DocumentSection"] = None
    children: List["DocumentSection"] = field(default_factory=list)


class IntelligentDocumentAnalyzer:
    """
    🧠 Analyseur de documents intelligent sans LLM externe

    Capacités:
    - Extraction d'entités nommées (NER)
    - Construction de graphe de connaissances
    - Analyse syntaxique et sémantique
    - Réponses en langage naturel
    """

    def __init__(self):
        # Graphe de connaissances: stocke les entités et relations
        self.knowledge_graph: Dict[str, Dict] = {}
        self.entities: List[Entity] = []
        self.relations: List[Relation] = []
        self.facts: List[Fact] = []
        self.sections: List[DocumentSection] = []
        # Document dont l'analyse est en mémoire (une seule à la fois)
        self.analyzed_document = ""

        # Index inversé pour recherche rapide
        self.entity_index: Dict[str, List[Entity]] = defaultdict(list)
        self.fact_index: Dict[str, List[Fact]] = defaultdict(list)
        self.keyword_index: Dict[str, List[Tuple[str, float]]] = defaultdict(list)

        # Patterns pour extraction d'entités
        self._init_extraction_patterns()

        # Vocabulaire sémantique
        self._init_semantic_vocabulary()

        # Statistiques du document
        self.document_stats = {
            "total_words": 0,
            "total_sentences": 0,
            "total_sections": 0,
            "entity_counts": Counter(),
            "keyword_frequency": Counter(),
        }

        print("🧠 Analyseur de documents intelligent initialisé")

    def _init_extraction_patterns(self):
        """Initialise les patterns regex pour extraction d'entités"""

        # Patterns pour différents types d'entités
        self.patterns = {
            EntityType.VERSION: [
                r"(?:version|v|ver|V)\s*[:\s]*(\d+\.\d+(?:\.\d+)?(?:-\w+)?)",
                r'"version"\s*:\s*"(\d+\.\d+(?:\.\d+)?)"',
                r"'version'\s*:\s*'(\d+\.\d+(?:\.\d+)?)'",
                r"(\d+\.\d+\.\d+)",
            ],
            EntityType.NUMBER: [
                r"(\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?)\s*(?:tokens?|octets?|bytes?|MB|GB|KB|ms|secondes?|minutes?|heures?|%)",
                r"[<>≤≥]\s*(\d+(?:\.\d+)?)\s*(?:secondes?|ms|s\b)",
                r"(\d+(?:\.\d+)?)\s*(?:secondes?|ms|s\b)",
            ],
            EntityType.DATE: [
                r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
                r"(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})",
                r"(?:en\s+)?(\d{4})\b(?!\.\d)",  # Années seules
                r"(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})",
            ],
            EntityType.PERSON: [
                r"\b([A-Z][a-zéèêëàâäùûüôöîïç]+(?:\s+[A-Z][a-zéèêëàâäùûüôöîïç]+)+)\b",
                r"(?:M\.|Mme|Dr|Pr|Prof)\s+([A-Z][a-zéèêëàâäùûüôöîïç]+(?:\s+[A-Z][a-zéèêëàâäùûüôöîïç]+)?)",
            ],
            EntityType.TECHNOLOGY: [
                r"\b(Python|JavaScript|Java|C\+\+|C#|Ruby|Go|Rust|TypeScript|PHP|Swift|Kotlin)\b",
                r"\b(React|Vue|Angular|Django|Flask|FastAPI|Node\.js|Express|Spring|Laravel)\b",
                r"\b(TensorFlow|PyTorch|scikit-learn|pandas|numpy|Keras|OpenCV)\b",
                r"\b(Docker|Kubernetes|AWS|Azure|GCP|Linux|Windows|MacOS)\b",
                r"\b(SQL|NoSQL|MongoDB|PostgreSQL|MySQL|Redis|Elasticsearch)\b",
                r"\b(Git|GitHub|GitLab|CI/CD|DevOps|Agile|Scrum)\b",
                r"\b(API|REST|GraphQL|WebSocket|HTTP|HTTPS|JSON|XML|YAML)\b",
                r"\b(Machine Learning|Deep Learning|NLP|Computer Vision|IA|AI)\b",
            ],
            EntityType.CODE: [
                r"```[\w]*\n([\s\S]*?)```",
                r"`([^`]+)`",
                r"\b(def\s+\w+|class\s+\w+|function\s+\w+|const\s+\w+|let\s+\w+|var\s+\w+)\b",
            ],
            EntityType.URL: [
                r'(https?://[^\s<>"\']+)',
                r'(www\.[^\s<>"\']+)',
            ],
            EntityType.FILE: [
                r"([a-zA-Z0-9_\-]+\.(?:py|js|ts|html|css|json|yaml|yml|xml|txt|md|pdf|docx|csv))",
            ],
        }

        # Patterns pour extraction de relations/faits
        self.relation_patterns = [
            # "X est Y"
            (r"(.+?)\s+(?:est|sont|était|étaient)\s+(.+)", RelationType.IS_A),
            # "X a Y"
            (r"(.+?)\s+(?:a|ont|possède|contient)\s+(.+)", RelationType.HAS),
            # "X utilise Y"
            (r"(.+?)\s+(?:utilise|emploie|exploite)\s+(.+)", RelationType.USES),
            # "X produit Y"
            (r"(.+?)\s+(?:produit|génère|crée|fournit)\s+(.+)", RelationType.PRODUCES),
            # "X nécessite Y"
            (
                r"(.+?)\s+(?:nécessite|requiert|demande|exige)\s+(.+)",
                RelationType.REQUIRES,
            ),
            # "X = Y" ou "X : Y"
            (r'"?(\w+)"?\s*[:=]\s*"?([^"]+)"?', RelationType.EQUALS),
            # Comparaisons
            (r"(.+?)\s*[<]\s*(.+)", RelationType.LESS_THAN),
            (r"(.+?)\s*[>]\s*(.+)", RelationType.GREATER_THAN),
        ]

    def _init_semantic_vocabulary(self):
        """Initialise le vocabulaire sémantique pour comprendre les questions"""

        # Mots-clés pour identifier le type de question
        self.question_types = {
            "what": ["quel", "quelle", "quels", "quelles", "qu'est-ce", "que", "quoi"],
            "who": ["qui", "par qui", "de qui"],
            "when": ["quand", "à quelle date", "en quelle année", "depuis quand"],
            "where": ["où", "à quel endroit", "dans quel"],
            "how": ["comment", "de quelle manière", "par quel moyen"],
            "how_much": ["combien", "quel nombre", "quelle quantité", "quel montant"],
            "why": ["pourquoi", "pour quelle raison", "à cause de quoi"],
            "which": ["lequel", "laquelle", "lesquels", "lesquelles"],
        }

        # Synonymes et équivalences sémantiques
        self.semantic_equivalences = {
            "version": ["version", "v", "ver", "numéro de version", "release"],
            "performance": [
                "performance",
                "vitesse",
                "rapidité",
                "temps de réponse",
                "latence",
            ],
            "temps": [
                "temps",
                "durée",
                "secondes",
                "minutes",
                "heures",
                "ms",
                "millisecondes",
            ],
            "capacité": ["capacité", "taille", "volume", "quantité", "nombre"],
            "algorithme": ["algorithme", "algo", "méthode", "procédure", "fonction"],
            "langage": ["langage", "language", "langue", "programmation"],
            "créateur": ["créateur", "auteur", "inventeur", "fondateur", "développeur"],
            "date": ["date", "année", "jour", "mois", "période", "moment"],
        }

        # Mots de liaison et structures
        self.connectors = {
            "cause": ["car", "parce que", "puisque", "étant donné que", "du fait que"],
            "consequence": [
                "donc",
                "ainsi",
                "par conséquent",
                "c'est pourquoi",
                "de ce fait",
            ],
            "condition": ["si", "à condition que", "pourvu que", "dans le cas où"],
            "opposition": ["mais", "cependant", "toutefois", "néanmoins", "pourtant"],
            "addition": ["et", "de plus", "en outre", "également", "aussi"],
            "exemple": ["par exemple", "notamment", "comme", "tel que", "c'est-à-dire"],
        }

    def analyze_document(self, content: str, document_name: str = "") -> Dict[str, Any]:
        """
        🔍 Analyse complète d'un document

        1. Segmentation en sections
        2. Extraction d'entités
        3. Extraction de faits/relations
        4. Construction du graphe de connaissances
        5. Indexation pour recherche
        """
        print(f"🧠 [ANALYZE] Début analyse de '{document_name}'...")

        # Reset pour nouveau document (ou fusionner si multi-documents)
        self._prepare_for_analysis()
        self.analyzed_document = document_name

        # Étape 1: Segmentation
        sections = self._segment_document(content)
        print(f"📄 [ANALYZE] {len(sections)} sections identifiées")

        # Étape 2: Extraction d'entités par section
        all_entities = []
        for section in sections:
            entities = self._extract_entities(section.content)
            section.entities = entities
            all_entities.extend(entities)

            # Extraction de mots-clés
            section.keywords = self._extract_keywords(section.content)

        self.entities = all_entities
        self.sections = sections
        print(f"🏷️ [ANALYZE] {len(all_entities)} entités extraites")

        # Étape 3: Extraction de faits
        facts = self._extract_facts(content)
        self.facts = facts
        print(f"📊 [ANALYZE] {len(facts)} faits extraits")

        # Étape 4: Construction du graphe
        self._build_knowledge_graph()

        # Étape 5: Indexation
        self._build_indexes()

        # Statistiques
        self._compute_statistics(content)

        print(
            f"✅ [ANALYZE] Analyse terminée - Graphe: {len(self.knowledge_graph)} nœuds"
        )

        return {
            "success": True,
            "sections": len(sections),
            "entities": len(all_entities),
            "facts": len(facts),
            "graph_nodes": len(self.knowledge_graph),
            "stats": self.document_stats,
        }

    def forget(self, document_name: str) -> bool:
        """
        Efface l'analyse en mémoire si elle porte sur ce document (pièce jointe retirée)

        Returns:
            True si l'analyse a été effacée
        """
        if not document_name or document_name != self.analyzed_document:
            return False
        self._prepare_for_analysis()
        self.analyzed_document = ""
        return True

    def _prepare_for_analysis(self):
        """Prépare les structures pour une nouvelle analyse (réinitialise l'état)."""
        # Réinitialiser le graphe et les collections d'analyses
        self.knowledge_graph = {}
        self.entities = []
        self.relations = []
        self.facts = []
        self.sections = []

        # Réinitialiser les index inversés
        self.entity_index = defaultdict(list)
        self.fact_index = defaultdict(list)
        self.keyword_index = defaultdict(list)

        # Réinitialiser les statistiques documentaires
        self.document_stats = {
            "total_words": 0,
            "total_sentences": 0,
            "total_sections": 0,
            "entity_counts": Counter(),
            "keyword_frequency": Counter(),
        }

    def _segment_document(self, content: str) -> List[DocumentSection]:
        """Segmente le document en sections hiérarchiques"""
        sections = []

        # Patterns pour détecter les titres de sections
        title_patterns = [
            (r"^#{1,6}\s+(.+)$", lambda m: len(m.group(0).split()[0])),  # Markdown
            (r"^([A-Z][^.!?]*?)(?:\n|$)", lambda m: 1),  # Titre en majuscules
            (
                r"^(\d+\.(?:\d+\.)*)\s*(.+)$",
                lambda m: m.group(1).count(".") + 1,
            ),  # Numérotation
            (
                r"^(?:Chapitre|Section|Partie)\s+(\d+|[IVX]+)[:\s]*(.+)?$",
                lambda m: 1,
            ),  # Titres explicites
        ]

        lines = content.split("\n")
        current_section = None
        current_content = []

        for line in lines:
            is_title = False
            title_text = ""
            level = 1

            # Vérifier si c'est un titre
            for pattern, level_func in title_patterns:
                match = re.match(pattern, line.strip(), re.MULTILINE)
                if match:
                    # Sauvegarder la section précédente
                    if current_section is not None:
                        current_section.content = "\n".join(current_content).strip()
                        sections.append(current_section)

                    # Nouvelle section
                    title_text = (
                        match.group(1) if match.lastindex >= 1 else line.strip()
                    )
                    level = level_func(match) if callable(level_func) else 1

                    current_section = DocumentSection(
                        title=title_text.strip(), content="", level=level
                    )
                    current_content = []
                    is_title = True
                    break

            if not is_title:
                current_content.append(line)

        # Dernière section
        if current_section is not None:
            current_section.content = "\n".join(current_content).strip()
            sections.append(current_section)
        elif current_content:
            # Pas de titre trouvé, tout est une seule section
            sections.append(
                DocumentSection(
                    title="Contenu principal",
                    content="\n".join(current_content).strip(),
                    level=1,
                )
            )

        return sections

    def _extract_entities(self, text: str) -> List[Entity]:
        """Extrait les entités nommées d'un texte"""
        entities = []

        for entity_type, patterns in self.patterns.items():
            for pattern in patterns:
                try:
                    for match in re.finditer(
                        pattern, text, re.IGNORECASE | re.MULTILINE
                    ):
                        entity_text = (
                            match.group(1) if match.lastindex >= 1 else match.group(0)
                        )

                        # Calculer le contexte (texte autour)
                        start = max(0, match.start() - 50)
                        end = min(len(text), match.end() + 50)
                        context = text[start:end]

                        entity = Entity(
                            text=entity_text.strip(),
                            entity_type=entity_type,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            confidence=0.8,  # Confidence par défaut
                            context=context,
                            normalized_form=self._normalize_entity(
                                entity_text, entity_type
                            ),
                        )

                        # Éviter les doublons
                        if entity not in entities:
                            entities.append(entity)
                except Exception:
                    continue

        return entities

    def _normalize_entity(self, text: str, entity_type: EntityType) -> str:
        """Normalise une entité pour faciliter la comparaison"""
        text = text.strip().lower()

        if entity_type == EntityType.VERSION:
            # Garder uniquement les chiffres et points
            return re.sub(r"[^0-9.]", "", text)
        elif entity_type == EntityType.NUMBER:
            # Normaliser les nombres
            text = text.replace(",", "").replace(" ", "")
            try:
                return str(float(text))
            except Exception:
                return text
        elif entity_type == EntityType.DATE:
            # Normaliser les dates (format ISO)
            # Simplification: garder tel quel pour l'instant
            return text
        else:
            return text

    def _extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """Extrait les mots-clés importants d'un texte (TF-IDF simplifié)"""
        # Nettoyage et tokenization
        words = re.findall(r"\b[a-zA-ZÀ-ÿ]{3,}\b", text.lower())

        # Stopwords français
        stopwords = {
            "les",
            "des",
            "une",
            "pour",
            "avec",
            "dans",
            "sur",
            "par",
            "est",
            "sont",
            "qui",
            "que",
            "quoi",
            "mais",
            "donc",
            "car",
            "cette",
            "ces",
            "aux",
            "pas",
            "plus",
            "peut",
            "être",
            "fait",
            "faire",
            "ont",
            "été",
            "comme",
            "tout",
            "tous",
            "aussi",
            "leur",
            "leurs",
            "nous",
            "vous",
            "ils",
            "elle",
            "elles",
            "son",
            "ses",
            "notre",
            "votre",
            "lui",
            "très",
            "bien",
            "encore",
            "même",
            "sans",
            "entre",
            "après",
            "avant",
            "sous",
            "chez",
            "peu",
            "trop",
            "autre",
            "autres",
            "celui",
            "celle",
            "ceux",
            "celles",
            "dont",
            "alors",
            "ainsi",
        }

        # Filtrer et compter
        word_freq = Counter(w for w in words if w not in stopwords)

        # Top N mots-clés
        return [word for word, _ in word_freq.most_common(top_n)]

    def _extract_facts(self, text: str) -> List[Fact]:
        """Extrait les faits (triplets sujet-prédicat-objet) du texte"""
        facts = []

        # Diviser en phrases
        sentences = re.split(r"[.!?]+", text)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue

            # Appliquer les patterns de relation
            for pattern, rel_type in self.relation_patterns:
                try:
                    match = re.search(pattern, sentence, re.IGNORECASE)
                    if match and match.lastindex >= 2:
                        subject = match.group(1).strip()
                        obj = match.group(2).strip()

                        # Nettoyer
                        subject = re.sub(
                            r"^(?:le|la|les|un|une|des)\s+",
                            "",
                            subject,
                            flags=re.IGNORECASE,
                        )
                        obj = re.sub(
                            r"^(?:le|la|les|un|une|des)\s+",
                            "",
                            obj,
                            flags=re.IGNORECASE,
                        )

                        if len(subject) > 2 and len(obj) > 2:
                            fact = Fact(
                                subject=subject[:100],  # Limiter la taille
                                predicate=rel_type.value,
                                object=obj[:100],
                                confidence=0.7,
                                source_text=sentence[:200],
                            )
                            facts.append(fact)
                except Exception:
                    continue

        return facts

    def _build_knowledge_graph(self):
        """Construit le graphe de connaissances à partir des entités et faits"""

        # Ajouter les entités comme nœuds
        for entity in self.entities:
            node_id = self._get_node_id(entity.text)

            if node_id not in self.knowledge_graph:
                self.knowledge_graph[node_id] = {
                    "text": entity.text,
                    "type": entity.entity_type.value,
                    "normalized": entity.normalized_form,
                    "contexts": [],
                    "relations": [],
                    "mentions": 0,
                }

            self.knowledge_graph[node_id]["contexts"].append(entity.context)
            self.knowledge_graph[node_id]["mentions"] += 1

        # Ajouter les faits comme arêtes
        for fact in self.facts:
            subj_id = self._get_node_id(fact.subject)
            obj_id = self._get_node_id(fact.object)

            # Créer les nœuds s'ils n'existent pas
            for node_id, text in [(subj_id, fact.subject), (obj_id, fact.object)]:
                if node_id not in self.knowledge_graph:
                    self.knowledge_graph[node_id] = {
                        "text": text,
                        "type": "concept",
                        "normalized": text.lower(),
                        "contexts": [fact.source_text],
                        "relations": [],
                        "mentions": 1,
                    }

            # Ajouter la relation
            self.knowledge_graph[subj_id]["relations"].append(
                {
                    "predicate": fact.predicate,
                    "target": obj_id,
                    "confidence": fact.confidence,
                }
            )

    def _get_node_id(self, text: str) -> str:
        """Génère un ID unique pour un nœud du graphe"""
        return hashlib.md5(text.lower().strip().encode()).hexdigest()[:12]

    def _build_indexes(self):
        """Construit les index inversés pour recherche rapide"""

        # Index des entités par texte
        for entity in self.entities:
            key = entity.text.lower()
            self.entity_index[key].append(entity)

            # Aussi indexer par type
            type_key = f"type:{entity.entity_type.value}"
            self.entity_index[type_key].append(entity)

        # Index des faits par sujet et objet
        for fact in self.facts:
            self.fact_index[fact.subject.lower()].append(fact)
            self.fact_index[fact.object.lower()].append(fact)

        # Index des mots-clés
        for section in self.sections:
            for keyword in section.keywords:
                self.keyword_index[keyword].append((section.title, 1.0))

    def _compute_statistics(self, content: str):
        """Calcule les statistiques du document"""
        self.document_stats["total_words"] = len(content.split())
        self.document_stats["total_sentences"] = len(re.split(r"[.!?]+", content))
        self.document_stats["total_sections"] = len(self.sections)

        # Comptage des entités par type
        for entity in self.entities:
            self.document_stats["entity_counts"][entity.entity_type.value] += 1

        # Fréquence des mots-clés globaux
        all_keywords = []
        for section in self.sections:
            all_keywords.extend(section.keywords)
        self.document_stats["keyword_frequency"] = Counter(all_keywords)

    def answer_question(self, question: str) -> Dict[str, Any]:
        """
        🎯 Répond à une question sur le document analysé

        1. Analyse de la question
        2. Recherche dans le graphe de connaissances
        3. Extraction des informations pertinentes
        4. Génération de la réponse en langage naturel
        """
        print(f"❓ [QUESTION] '{question}'")

        # Étape 1: Analyser la question
        question_analysis = self._analyze_question(question)
        print(
            f"🔍 [QUESTION] Type: {question_analysis['type']}, Focus: {question_analysis['focus']}"
        )

        # Étape 2: Rechercher les informations pertinentes
        relevant_info = self._search_knowledge(question_analysis)
        print(
            f"📚 [QUESTION] {len(relevant_info['entities'])} entités, {len(relevant_info['facts'])} faits trouvés"
        )

        # Étape 3: Générer la réponse
        response = self._generate_answer(question_analysis, relevant_info)

        return {
            "answer": response["text"],
            "confidence": response["confidence"],
            "sources": response["sources"],
            "entities_used": relevant_info["entities"],
            "facts_used": relevant_info["facts"],
        }

    def _analyze_question(self, question: str) -> Dict[str, Any]:
        """Analyse une question pour comprendre ce qui est demandé"""
        question_lower = question.lower()

        # Déterminer le type de question
        question_type = "what"  # Par défaut
        for qtype, keywords in self.question_types.items():
            if any(kw in question_lower for kw in keywords):
                question_type = qtype
                break

        # Extraire les entités de la question
        question_entities = self._extract_entities(question)

        # Identifier le focus de la question (ce sur quoi porte la question)
        focus_terms = []

        # Chercher les termes sémantiques
        for concept, synonyms in self.semantic_equivalences.items():
            if any(syn in question_lower for syn in synonyms):
                focus_terms.append(concept)

        # Extraire les mots-clés de la question
        keywords = self._extract_keywords(question, top_n=5)

        # Détecter les contraintes (comparaisons, valeurs attendues)
        constraints = []
        if re.search(r"[<>≤≥]", question):
            constraints.append("comparison")
        if re.search(r"\d+", question):
            constraints.append("numeric")

        return {
            "type": question_type,
            "focus": focus_terms,
            "keywords": keywords,
            "entities": question_entities,
            "constraints": constraints,
            "original": question,
        }

    def _search_knowledge(self, question_analysis: Dict) -> Dict[str, Any]:
        """Recherche les informations pertinentes dans le graphe de connaissances"""
        relevant_entities = []
        relevant_facts = []
        relevant_sections = []

        # Recherche par mots-clés
        keywords = question_analysis["keywords"]
        focus_terms = question_analysis["focus"]

        # Recherche dans les entités
        for keyword in keywords + focus_terms:
            if keyword in self.entity_index:
                relevant_entities.extend(self.entity_index[keyword])

            # Recherche partielle
            for key, entities in self.entity_index.items():
                if keyword in key or key in keyword:
                    relevant_entities.extend(entities)

        # Recherche dans les faits
        for keyword in keywords + focus_terms:
            if keyword in self.fact_index:
                relevant_facts.extend(self.fact_index[keyword])

            # Recherche partielle
            for key, facts in self.fact_index.items():
                if keyword in key or key in keyword:
                    relevant_facts.extend(facts)

        # Recherche dans les sections
        for section in self.sections:
            score = 0
            section_lower = section.content.lower()

            for keyword in keywords:
                if keyword in section_lower:
                    score += section_lower.count(keyword)

            for term in focus_terms:
                for syn in self.semantic_equivalences.get(term, [term]):
                    if syn in section_lower:
                        score += 2

            if score > 0:
                relevant_sections.append((section, score))

        # Trier par pertinence
        relevant_sections.sort(key=lambda x: x[1], reverse=True)

        # Dédupliquer
        seen_entities = set()
        unique_entities = []
        for e in relevant_entities:
            if e.text.lower() not in seen_entities:
                seen_entities.add(e.text.lower())
                unique_entities.append(e)

        seen_facts = set()
        unique_facts = []
        for f in relevant_facts:
            fact_key = f"{f.subject}:{f.predicate}:{f.object}"
            if fact_key not in seen_facts:
                seen_facts.add(fact_key)
                unique_facts.append(f)

        return {
            "entities": unique_entities[:10],  # Top 10
            "facts": unique_facts[:10],
            "sections": [s for s, _ in relevant_sections[:5]],  # Top 5 sections
        }

    def _generate_answer(
        self, analysis: Dict, info: Dict
    ) -> Dict[str, Any]:
        """Génère une réponse en langage naturel"""

        question_type = analysis["type"]
        focus = analysis["focus"]
        entities = info["entities"]
        facts = info["facts"]
        sections = info["sections"]

        # Aucune information trouvée
        if not entities and not facts and not sections:
            return {
                "text": "Je n'ai pas trouvé d'information pertinente dans les documents analysés pour répondre à cette question.",
                "confidence": 0.0,
                "sources": [],
            }

        # Construire la réponse selon le type de question
        answer_parts = []
        confidence = 0.0
        sources = []

        # Questions sur une valeur spécifique (version, nombre, date)
        if question_type == "what" or question_type == "how_much":
            # Chercher les entités pertinentes selon le focus
            for entity in entities:
                if self._entity_matches_focus(entity, focus):
                    answer_parts.append(self._format_entity_answer(entity, focus))
                    confidence = max(confidence, entity.confidence)
                    sources.append(entity.context[:100])

        # Questions temporelles
        elif question_type == "when":
            date_entities = [e for e in entities if e.entity_type == EntityType.DATE]
            if date_entities:
                best_date = max(date_entities, key=lambda e: e.confidence)
                answer_parts.append(f"Cela s'est passé en {best_date.text}.")
                confidence = best_date.confidence
                sources.append(best_date.context)

        # Questions sur une personne
        elif question_type == "who":
            person_entities = [
                e for e in entities if e.entity_type == EntityType.PERSON
            ]
            if person_entities:
                persons = [e.text for e in person_entities]
                answer_parts.append(f"Il s'agit de {', '.join(persons)}.")
                confidence = max(e.confidence for e in person_entities)
                sources.extend([e.context for e in person_entities])

        # Si pas assez d'entités, utiliser les faits
        if not answer_parts and facts:
            relevant_fact = facts[0]  # Le plus pertinent
            answer_parts.append(
                f"{relevant_fact.subject.capitalize()} {self._predicate_to_french(relevant_fact.predicate)} {relevant_fact.object}."
            )
            confidence = relevant_fact.confidence
            sources.append(relevant_fact.source_text)

        # Si toujours rien, utiliser les sections
        if not answer_parts and sections:
            best_section = sections[0]
            # Extraire un passage pertinent
            passage = self._extract_relevant_passage(
                best_section.content, analysis["keywords"]
            )
            if passage:
                answer_parts.append(passage)
                confidence = 0.6
                sources.append(f"Section: {best_section.title}")

        # Construire la réponse finale
        if answer_parts:
            final_answer = " ".join(answer_parts)
        else:
            final_answer = "Je n'ai pas pu trouver une réponse précise à cette question dans les documents."
            confidence = 0.2

        return {
            "text": final_answer,
            "confidence": confidence,
            "sources": sources[:3],  # Max 3 sources
        }

    def _entity_matches_focus(self, entity: Entity, focus: List[str]) -> bool:
        """Vérifie si une entité correspond au focus de la question"""
        if not focus:
            return True

        entity_type_mapping = {
            "version": [EntityType.VERSION],
            "performance": [EntityType.NUMBER],
            "temps": [EntityType.NUMBER, EntityType.DATE],
            "capacité": [EntityType.NUMBER],
            "langage": [EntityType.TECHNOLOGY],
            "date": [EntityType.DATE],
            "créateur": [EntityType.PERSON],
        }

        for f in focus:
            if f in entity_type_mapping:
                if entity.entity_type in entity_type_mapping[f]:
                    return True

        return False

    def _format_entity_answer(self, entity: Entity, focus: List[str]) -> str:
        """Formate une entité en réponse naturelle"""
        if entity.entity_type == EntityType.VERSION:
            return f"La version est {entity.text}."
        elif entity.entity_type == EntityType.NUMBER:
            if "temps" in focus or "performance" in focus:
                return f"Le temps est de {entity.text}."
            elif "capacité" in focus:
                return f"La capacité est de {entity.text}."
            else:
                return f"La valeur est {entity.text}."
        elif entity.entity_type == EntityType.DATE:
            return f"La date est {entity.text}."
        elif entity.entity_type == EntityType.PERSON:
            return f"Il s'agit de {entity.text}."
        elif entity.entity_type == EntityType.TECHNOLOGY:
            return f"La technologie utilisée est {entity.text}."
        else:
            return f"{entity.text}."

    def _predicate_to_french(self, predicate: str) -> str:
        """Convertit un prédicat en verbe français"""
        mapping = {
            "is_a": "est",
            "has": "a",
            "belongs_to": "appartient à",
            "created_by": "a été créé par",
            "located_in": "se trouve à",
            "occurred_at": "s'est passé le",
            "value_of": "a pour valeur",
            "uses": "utilise",
            "produces": "produit",
            "requires": "nécessite",
            "equals": "est égal à",
            "greater_than": "est supérieur à",
            "less_than": "est inférieur à",
        }
        return mapping.get(predicate, predicate)

    def _extract_relevant_passage(self, content: str, keywords: List[str]) -> str:
        """Extrait le passage le plus pertinent d'un contenu"""
        sentences = re.split(r"[.!?]+", content)

        best_sentence = ""
        best_score = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue

            score = sum(1 for kw in keywords if kw.lower() in sentence.lower())

            if score > best_score:
                best_score = score
                best_sentence = sentence

        if best_sentence:
            return best_sentence + "."

        # Fallback: premiers 200 caractères
        return content[:200].strip() + "..."

    def get_document_summary(self) -> str:
        """Génère un résumé du document analysé"""
        if not self.sections:
            return "Aucun document n'a été analysé."

        summary_parts = []

        # Statistiques générales
        summary_parts.append("📊 **Statistiques du document:**")
        summary_parts.append(f"- {self.document_stats['total_words']} mots")
        summary_parts.append(f"- {self.document_stats['total_sections']} sections")
        summary_parts.append(f"- {len(self.entities)} entités identifiées")
        summary_parts.append(f"- {len(self.facts)} faits extraits")

        # Principaux sujets
        top_keywords = self.document_stats["keyword_frequency"].most_common(5)
        if top_keywords:
            kw_list = ", ".join([kw for kw, _ in top_keywords])
            summary_parts.append(f"\n📌 **Sujets principaux:** {kw_list}")

        # Entités clés
        if self.entities:
            entity_types = Counter(e.entity_type.value for e in self.entities)
            summary_parts.append("\n🏷️ **Types d'entités:**")
            for etype, count in entity_types.most_common(5):
                summary_parts.append(f"- {etype}: {count}")

        # Titres des sections principales
        main_sections = [s for s in self.sections if s.level == 1][:5]
        if main_sections:
            summary_parts.append("\n📑 **Sections principales:**")
            for section in main_sections:
                summary_parts.append(f"- {section.title}")

        return "\n".join(summary_parts)


# Instance globale pour utilisation
document_analyzer = IntelligentDocumentAnalyzer()
