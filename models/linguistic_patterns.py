"""
Patterns linguistiques pour l'analyse sémantique
"""

from typing import Dict, List, Any
import re


class LinguisticPatterns:
    """Gestionnaire de patterns linguistiques améliorés"""
    
    def __init__(self):
        self.patterns = self._load_patterns()
        self.tolerance_dict = self._load_tolerance_dictionary()
        self.context_memory = {}
    
    def _load_tolerance_dictionary(self) -> Dict[str, List[str]]:
        """Dictionnaire de tolérance aux fautes d'orthographe et variantes"""
        return {
            # Salutations avec fautes
            "bonjour": ["bonjour", "bnjour", "bonjourr", "bonj", "bjr", "bj", "bonsoir", "bsr", "bonsoirr"],
            "salut": ["salut", "salu", "saluu", "slt", "sl", "cc", "coucou", "ccc", "kikoo", "kikou"],
            "hello": ["hello", "helo", "hllo", "hi", "hey", "yo", "wesh"],
            
            # Questions avec fautes
            "comment": ["comment", "commen", "comant", "cmnt", "coment"],
            "ça_va": ["ça va", "sa va", "ca va", "sa va?", "ça roule", "sa roule", "ca roule"],
            
            # Mots de politesse
            "merci": ["merci", "mercy", "mrci", "thx", "thanks", "remercie"],
            "s'il_vous_plaît": ["s'il vous plaît", "svp", "stp", "s'il te plaît", "sil vous plait"],
            
            # Code et programmation
            "fonction": ["fonction", "fontion", "function", "func", "def", "methode", "méthode"],
            "classe": ["classe", "class", "klass", "clsse"],
            "génère": ["génère", "genere", "generate", "créer", "creer", "create", "faire", "fais", "fait"],
            "code": ["programme", "script", "fichier", "game"],
            
            # Expressions familières
            "ok": ["ok", "okay", "okey", "d'accord", "daccord", "dacord", "oui", "yes", "yep"],
            "non": ["non", "no", "nope", "pas", "jamais", "nan"],
            
            # Erreurs courantes
            "qu'est_ce_que": ["qu'est-ce que", "quest ce que", "quest-ce que", "kestke", "keskeske"],
            "pourquoi": ["pourquoi", "pourkoi", "pq", "pk", "pour quoi"],
            "comment_faire": ["comment faire", "coment faire", "cmnt faire", "comment on fait"],
            
            # Familier/argot
            "ça_marche": ["ça marche", "sa marche", "ca marche", "ça roule", "sa roule"],
            "c'est_cool": ["c'est cool", "cest cool", "c cool", "cool", "sympa", "bien"],
            "pas_mal": ["pas mal", "pa mal", "pas male", "bien", "correct"],
            
            # Variations avec ponctuation
            "aide": ["aide", "aider", "help", "secours", "assistance", "aidez-moi", "aide moi"],
            "expliquer": ["expliquer", "expliquez", "explique", "explain", "dire", "montrer"],
            "résume": ["resume", "résumé", "resumer"],
            "document": ["fichier", "pdf", "doc", "docx"],
            
            # Questions sur l'identité
            "tu_es_qui": ["tu es qui", "qui es-tu", "qui es tu", "tu es qui ?", "qui es-tu ?", "qui tu es", "tu es quoi"],
            "qui_es_tu": ["qui es tu", "qui est tu", "qui es-tu", "qui êtes vous", "qui etes vous", "quel est ton nom", "ton nom", "comment tu t'appelles", "comment tu t'appelle", "comment t'appelles tu", "comment t'appelle tu", "tu es qui", "tu es quoi"],
            "qu_est_ce_que_tu_es": ["qu'est-ce que tu es", "quest ce que tu es", "qu est ce que tu es"],
            
            # Questions sur les capacités
            "que_peux_tu": ["que peux-tu", "que peux tu", "que peut tu", "que peut-tu", "qu'est-ce que tu peux"],
            "que_sais_tu": ["que sais-tu", "que sais tu", "que sait tu", "que sait-tu", "qu'est-ce que tu sais"],
            "tu_peux": ["tu peux", "tu peut", "peux-tu", "peut-tu", "est-ce que tu peux"],
            
            # Réponses courtes
            "oui": ["oui", "yes", "yep", "ouais", "ok", "d'accord", "daccord"],
            "non": ["non", "no", "nope", "pas", "jamais", "nan", "nenni"],
            
            # Expressions de satisfaction
            "super": ["super", "génial", "parfait", "excellent", "cool", "top", "bien"],
            "ça_va": ["ça va", "ca va", "sa va", "ça roule", "sa roule", "ca roule"],
            
            # Demandes d'information
            "dis_moi": ["dis-moi", "dis moi", "dites-moi", "dites moi", "raconte", "raconte-moi"],
            "parle_moi": ["parle-moi", "parle moi", "parlez-moi", "parlez moi"],
            
            # Expressions de politesse étendues
            "s'il_te_plaît": ["s'il te plaît", "stp", "s'il te plait", "sil te plait", "steuplait"],
            "merci_beaucoup": ["merci beaucoup", "merci bcp", "merci bien", "grand merci"],
            "de_rien": ["de rien", "pas de quoi", "il n'y a pas de quoi", "je vous en prie"],
            
            # Expressions informelles
            "wesh": ["wesh", "salut", "hey", "yo", "coucou"],
            "mec": ["mec", "gars", "mon pote", "buddy", "bro"],
            "c'est_parti": ["c'est parti", "go", "allons-y", "on y va", "lets go"],
        }
    
    def _load_patterns(self) -> Dict[str, Any]:
        """Charge les patterns linguistiques améliorés"""
        return {
            "intent_detection": {
                "identity_question": {
                    "patterns": [
                        r"(?:qui|quel|comment).+(?:es[- ]tu|êtes[- ]vous|est ton nom|t'appelles?[- ]tu)",
                        r"tu es qui\b",
                        r"tu es quoi\b",
                        r"\bton nom\b",
                        r"comment (?:tu t'appelles?|t'appelles?[- ]tu)",
                        r"qui êtes[-\s]vous",
                        r"quel est ton nom"
                    ],
                    "indicators": ["qui", "nom", "appelle", "identité"],
                    "weight": 1.0,
                    "priority": "high"
                },
                
                "capabilities_question": {
                    "patterns": [
                        r"(?:que|qu'est[- ]ce que|quoi).+(?:peux[- ]tu|sais[- ]tu|fais[- ]tu|es[- ]tu capable)",
                        r"(?:montre|liste|dis)[- ]moi.+(?:capacités|ce que tu peux faire)",
                        r"que sais[-\s]tu faire",
                        r"quelles sont tes capacités",
                        r"tu peux faire quoi"
                    ],
                    "indicators": ["capable", "peux", "sais", "faire", "capacités"],
                    "weight": 1.0,
                    "priority": "high",
                    "exclude_if": ["code", "fichier", "programme", "script", "fonction"]
                },
                
                # ✅ NOUVEAU: Questions réciproques "ça va et toi ?"
                "how_are_you": {
                    "patterns": [
                        r"^comment\s+(ça|sa|ca)\s+va\s*\??$",
                        r"^(ça|sa|ca)\s+va\s+(et\s+toi|et\s+vous)\s*\??$",
                        r"^(ça|sa|ca)\s+va\s+et\s+toi\s*\??$",
                        r"^(sa|ca|ça)\s+va\s+et\s+toi\s*\??$",
                        r"^comment\s+tu\s+vas\s*\??$",
                        r"^comment\s+vous\s+allez\s*\??$",
                        r"^tu\s+vas\s+bien\s*\??$",
                        r"^vous\s+allez\s+bien\s*\??$",
                        r"^(ça|sa|ca)\s+va\s*\?\s*$"
                    ],
                    "indicators": ["comment", "ça", "va", "et toi", "et vous", "?"],
                    "weight": 1.0,
                    "priority": "high",
                    "exclude_if": ["python", "liste", "créer", "fonction", "variable", "code", "programme", "script", "programmation"]
                },
                
                # ✅ NOUVEAU: Affirmations simples "ça va" (sans question)
                "affirm_doing_well": {
                    "patterns": [
                        r"^(ça|sa|ca)\s+va\s*$",
                        r"^(ça|sa|ca)\s+va\s+bien\s*$",
                        r"^(ça|sa|ca)\s+roule\s*$",
                        r"^je\s+vais\s+bien\s*$",
                        r"^tout\s+va\s+bien\s*$",
                        r"^très\s+bien\s*$",
                        r"^bien\s*$",
                        r"^super\s*$",
                        r"^nickel\s*$"
                    ],
                    "indicators": ["ça", "va", "bien", "roule", "tout"],
                    "weight": 0.9,
                    "priority": "medium"
                }, 
                "document_question": {
                    "patterns": [
                        r"^résume$",  # résume seul
                        r"^resume$",  # resume seul  
                        r"^résumé$",  # résumé seul
                        r"résume\s+(?:le\s+)?(?:pdf|document|fichier|doc)",
                        r"resume\s+(?:le\s+)?(?:pdf|document|fichier|doc)",
                        r"(?:explique|analyse).+(?:document|fichier|pdf|docx)",
                        r"(?:que dit|que contient).+(?:le|ce|du|dans le).+(?:document|pdf|fichier)",
                        r"(?:premier|dernier|précédent).+(?:document|fichier|pdf)",
                        r"le\s+(?:pdf|document|fichier)"
                    ],
                    "indicators": ["document", "pdf", "fichier", "résume", "resume", "contient"],
                    "weight": 1.2,
                    "priority": "high"
                },
                "code_question": {
                    "patterns": [
                        r"(?:explique|expliquer).+(?:code|programme|script|fonction|game\.py)",
                        r"(?:que fait|comment fonctionne).+(?:le|ce|du|cette).+(?:code|programme|fonction|script)",
                        r"(?:analyse|analyser).+(?:code|programme|fichier\.py)",
                        r"explique[-\s]moi.+(?:game\.py|le programme|ce code)",
                        r"comment (?:marche|fonctionne).+(?:ce|le).+(?:code|programme)"
                    ],
                    "indicators": ["code", "programme", "script", "fonction", "game.py", "python"],
                    "weight": 1.1,
                    "priority": "high",
                    "context_boost": ["code_file_processed"]
                },
                
                "programming_question": {
                    "patterns": [
                        r"comment\s+(?:créer|creer|faire|créé|cree)\s+(?:une|un|des).+(?:liste|dictionnaire|fonction|variable|classe|boucle|condition)",
                        r"comment\s+(?:utiliser|employer|se servir de).+(?:python|javascript|html|css)",
                        r"(?:créer|creer|faire|génère|genere).+(?:liste|array|dictionnaire|dict|fonction|def|classe|class)",
                        r"qu[\'']?est[- ]ce qu[\'']?(?:une|un).+(?:liste|dictionnaire|fonction|variable|classe|objet|array)",
                        r"comment\s+(?:on|peut[- ]on|faire|declare|déclare).+(?:variable|liste|fonction|dictionnaire)",
                        r"(?:syntaxe|écriture).+(?:python|liste|fonction|boucle|condition)",
                        r"comment\s+(?:écrit|ecrire|programmer|coder).+(?:en\s+python|une\s+fonction|une\s+liste)",
                        r"(?:apprendre|comprendre).+(?:python|programmation|les\s+listes|les\s+fonctions)",
                        r"(?:différence|difference)\s+entre.+(?:liste|dict|tuple|set)",
                        r"comment\s+(?:marche|fonctionne).+(?:les\s+listes|les\s+dictionnaires|python)"
                    ],
                    "indicators": ["python", "liste", "dictionnaire", "fonction", "variable", "créer", "comment", "syntaxe", "programmation", "code"],
                    "weight": 1.3,
                    "priority": "high"
                },
                
                "internet_search": {
                    "patterns": [
                        r"^(?:cherche|recherche|trouve|search).+(?:sur internet|sur le web|en ligne|sur google)",
                        r"(?:cherche|recherche)\s+(?:sur\s+)?(?:internet|web|google|en ligne)\s+.+",
                        r"(?:recherche|trouve|cherche)\s+(?:moi\s+)?(?:des\s+)?(?:informations?\s+)?(?:sur|à propos de)\s+.+",
                        r"(?:que dit|qu[\'']?est[- ]ce que dit|quelles sont les informations sur).+(?:internet|web)",
                        r"cherche[- ]moi\s+.+",
                        r"peux[- ]tu\s+(?:chercher|rechercher|trouver)\s+.+",
                        r"(?:informations?|info|données|news|actualités?)\s+(?:sur|à propos de|concernant)\s+.+",
                        r"(?:dernières?\s+)?(?:actualités?|news|nouvelles?)\s+(?:sur|de|à propos de)\s+.+",
                        r"qu[\'']?est[- ]ce\s+qu[\'']?on\s+dit\s+(?:sur|de)\s+.+\s+(?:sur internet|en ligne)",
                        r"(?:web|internet|google)\s+search\s+.+"
                    ],
                    "indicators": ["cherche", "recherche", "internet", "web", "google", "informations", "actualités", "trouve", "news"],
                    "weight": 1.4,
                    "priority": "high"
                },
                
                "greeting": {
                    "patterns": [
                        r"^(?:bonjour|salut|hello|hi|hey|coucou|slt|bjr|bsr)\b",
                        r"^(?:bonsoir|good evening)\b",
                        r"^(?:wesh|yo)\b"
                    ],
                    "indicators": ["bonjour", "salut", "hello", "slt", "bjr"],
                    "weight": 0.9,
                    "priority": "medium"
                },
                
                "help": {
                    "patterns": [
                        r"(?:aide|help|assist).+moi",
                        r"j'ai besoin d'aide",
                        r"^(?:aide|help)$"
                    ],
                    "indicators": ["aide", "help", "besoin"],
                    "weight": 0.9,
                    "priority": "medium"
                },
                
                "thank_you": {
                    "patterns": [
                        r"^merci\s*$",
                        r"^merci\s+beaucoup\s*$",
                        r"^merci\s+bien\s*$",
                        r"^merci\s+bcp\s*$",
                        r"^grand\s+merci\s*$",
                        r"^je\s+te\s+remercie\s*$",
                        r"^je\s+vous\s+remercie\s*$",
                        r"^thanks?\s*$",
                        r"^thx\s*$",
                        r"^mercy\s*$",
                        r"^mrci\s*$",
                        r"^(?:oui\s+)?merci\s*!*$",
                        r"^merci\s+vraiment\s*$",
                        r"^merci\s+énormément\s*$",
                        r"^merci\s+infiniment\s*$"
                    ],
                    "indicators": ["merci", "thanks", "thx", "remercie"],
                    "weight": 1.0,
                    "priority": "high"
                },
                
                "goodbye": {
                    "patterns": [
                        r"^(?:au revoir|bye|à bientôt|salut|ciao|adieu)\s*$",
                        r"^(?:je dois y aller|je me sauve|à plus|@\+)\s*$",
                        r"^(?:bonne journée|bonne soirée|bonne nuit)\s*$"
                    ],
                    "indicators": ["au revoir", "bye", "bientôt", "journée", "soirée"],
                    "weight": 0.9,
                    "priority": "medium"
                },
                
                "affirmation": {
                    "patterns": [
                        r"^(?:oui|yes|yep|ouais|ok|d'accord|daccord)\s*$",
                        r"^(?:parfait|excellent|super|génial|cool|top)\s*$",
                        r"^(?:très bien|c'est bon|ça marche)\s*$"
                    ],
                    "indicators": ["oui", "ok", "parfait", "bien", "marche"],
                    "weight": 0.8,
                    "priority": "medium"
                },
                
                "negation": {
                    "patterns": [
                        r"^(?:non|no|nope|pas|jamais|nan)\s*$",
                        r"^(?:pas du tout|absolument pas|certainement pas)\s*$"
                    ],
                    "indicators": ["non", "pas", "jamais", "absolument"],
                    "weight": 0.8,
                    "priority": "medium"
                }
            }
        }
    
    def detect_intent(self, text: str, context: Dict[str, Any] = None) -> Dict[str, float]:
        """Détecte l'intention avec amélioration contextuelle"""
        if not text or not isinstance(text, str):
            return {"unknown": 0.0}
            
        text_lower = text.lower().strip()
        normalized_text = self._normalize_text(text_lower)
        
        if context is None:
            context = {}
        
        scores = {}
        
        # Tri des intentions par priorité
        intents_by_priority = self._sort_intents_by_priority()
        
        for intent in intents_by_priority:
            config = self.patterns["intent_detection"][intent]
            score = 0.0
            
            # Vérifier les exclusions
            exclude_terms = config.get("exclude_if", [])
            if any(term in normalized_text for term in exclude_terms):
                continue
            
            # Vérification des patterns regex
            patterns = config.get("patterns", [])
            for pattern in patterns:
                try:
                    if re.search(pattern, normalized_text, re.IGNORECASE):
                        score += config.get("weight", 1.0) * 0.8
                        break  # Un seul pattern suffit
                except re.error:
                    continue
            
            # Vérification des indicateurs
            indicators = config.get("indicators", [])
            for indicator in indicators:
                if self._fuzzy_match(indicator, normalized_text):
                    score += config.get("weight", 1.0) * 0.3
            
            # Boost contextuel
            context_boosts = config.get("context_boost", [])
            for boost_key in context_boosts:
                if context.get(boost_key, False):
                    score += 0.5
            
            if score > 0:
                scores[intent] = min(score, 1.0)
        
        # Si plusieurs intentions détectées, privilégier celle avec la priorité la plus haute
        if len(scores) > 1:
            scores = self._resolve_intent_conflicts(scores)
        
        return scores if scores else {"unknown": 0.0}
    
    def _sort_intents_by_priority(self) -> List[str]:
        """Trie les intentions par priorité"""
        high_priority = []
        medium_priority = []
        low_priority = []
        
        for intent, config in self.patterns["intent_detection"].items():
            priority = config.get("priority", "low")
            if priority == "high":
                high_priority.append(intent)
            elif priority == "medium":
                medium_priority.append(intent)
            else:
                low_priority.append(intent)
        
        return high_priority + medium_priority + low_priority
    
    def _resolve_intent_conflicts(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Résout les conflits entre intentions"""
        if not scores:
            return scores
        
        # Règles de priorité spécifiques
        priority_rules = {
            "document_question": ["capabilities_question", "help"],  # Document > capacités
            "code_question": ["capabilities_question", "help"],     # Code > capacités  
            "identity_question": ["capabilities_question"],         # Identité > capacités
        }
        
        for primary_intent, secondary_intents in priority_rules.items():
            if primary_intent in scores:
                for secondary in secondary_intents:
                    if secondary in scores:
                        # Réduire le score de l'intention secondaire
                        scores[secondary] *= 0.3
        
        return scores
    
    def _normalize_text(self, text: str) -> str:
        """Normalise le texte avec tolérance aux fautes"""
        normalized = text
        
        # Corrections communes
        corrections = {
            r'\bslt\b': 'salut',
            r'\bbjr\b': 'bonjour', 
            r'\bexpliques?\b': 'explique',
            r'\bresumes?\b': 'résume',
            r'\bgame\.py\b': 'game.py',
            r'\bprogrammes?\b': 'programme'
        }
        
        for pattern, replacement in corrections.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        return normalized
    
    def _fuzzy_match(self, target: str, text: str) -> bool:
        """Correspondance floue améliorée"""
        # Vérification exacte
        if target.lower() in text.lower():
            return True
        
        # Vérification avec variations
        variations = {
            "code": ["programme", "script", "fichier", "game"],
            "explique": ["expliquer", "expliques", "analyse", "analyser"],
            "résume": ["resume", "résumé", "resumer"],
            "document": ["fichier", "pdf", "doc", "docx"]
        }
        
        if target in variations:
            return any(var in text.lower() for var in variations[target])
        
        return False
    
    def _similar_word(self, word1: str, word2: str) -> bool:
        """Vérifie si deux mots sont similaires (tolérance aux fautes)"""
        if abs(len(word1) - len(word2)) > 2:
            return False
        
        # Calcul simple de distance d'édition
        differences = 0
        min_len = min(len(word1), len(word2))
        
        for i in range(min_len):
            if word1[i].lower() != word2[i].lower():
                differences += 1
                if differences > 2:  # Maximum 2 différences
                    return False
        
        return differences <= 2
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extrait les entités du texte"""
        text_lower = text.lower()
        entities = {}
        
        for entity_type, patterns in self.patterns["entity_extraction"].items():
            found_entities = []
            
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                found_entities.extend(matches)
            
            if found_entities:
                entities[entity_type] = list(set(found_entities))
        
        return entities
    
    def analyze_context(self, text: str) -> Dict[str, Any]:
        """Analyse le contexte du texte"""
        text_lower = text.lower()
        context = {}
        
        for context_type, indicators in self.patterns["context_indicators"].items():
            found_indicators = []
            
            for indicator in indicators:
                if indicator.lower() in text_lower:
                    found_indicators.append(indicator)
            
            if found_indicators:
                context[context_type] = found_indicators
        
        return context
    
    def get_semantic_tokens(self, text: str) -> List[str]:
        """Extrait les tokens sémantiques du texte"""
        # Tokenisation basique
        tokens = re.findall(r'\b\w+\b', text.lower())
        
        # Filtrage des mots vides
        stop_words = {'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou', 'mais', 'donc', 'or', 'car', 'ni', 'que', 'qui', 'quoi', 'dont', 'où', 'il', 'elle', 'ils', 'elles', 'je', 'tu', 'nous', 'vous', 'me', 'te', 'se', 'ce', 'cet', 'cette', 'ces', 'mon', 'ton', 'son', 'ma', 'ta', 'sa', 'mes', 'tes', 'ses', 'notre', 'votre', 'leur', 'leurs', 'dans', 'sur', 'sous', 'avec', 'sans', 'pour', 'par', 'vers', 'chez', 'en', 'à', 'au', 'aux', 'du', 'des', 'est', 'sont', 'été', 'être', 'avoir', 'ai', 'as', 'a', 'avons', 'avez', 'ont'}
        
        semantic_tokens = [token for token in tokens if token not in stop_words and len(token) > 2]
        
        return semantic_tokens
