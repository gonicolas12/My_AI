"""
Mémoire de conversation persistante pour l'IA locale
Garde en mémoire toutes les interactions durant la session
"""

import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ConversationEntry:
    """Représente une entrée de conversation"""
    timestamp: float
    user_message: str
    ai_response: str
    intent: str
    confidence: float
    context: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationEntry':
        """Crée depuis un dictionnaire"""
        return cls(**data)


class ConversationMemory:
    """Gestion de la mémoire de conversation"""
    
    def __init__(self):
        self.conversations: List[ConversationEntry] = []
        self.session_start = time.time()
        self.user_preferences = {}
        self.context_cache = {}
        # Stockage des documents analysés pendant la session avec ordre chronologique
        self.stored_documents = {}  # filename -> content
        self.document_order = []  # Liste chronologique des noms de fichiers
        
    def add_conversation(self, user_message: str, ai_response: str, 
                        intent: str = "unknown", confidence: float = 0.0,
                        context: Dict[str, Any] = None) -> None:
        """Ajoute une conversation à la mémoire"""
        entry = ConversationEntry(
            timestamp=time.time(),
            user_message=user_message,
            ai_response=ai_response,
            intent=intent,
            confidence=confidence,
            context=context or {}
        )
        self.conversations.append(entry)
        
        # Mise à jour du cache contextuel
        self._update_context_cache(entry)
    
    def _update_context_cache(self, entry: ConversationEntry) -> None:
        """Met à jour le cache contextuel"""
        # Détection de préférences utilisateur
        if entry.intent == "compliment":
            self.user_preferences["positive_feedback"] = True
        elif entry.intent == "negation":
            self.user_preferences["negative_feedback"] = True
            
        # Mise à jour des sujets récents
        if "recent_topics" not in self.context_cache:
            self.context_cache["recent_topics"] = []
            
        self.context_cache["recent_topics"].append({
            "intent": entry.intent,
            "timestamp": entry.timestamp,
            "keywords": self._extract_keywords(entry.user_message)
        })
        
        # Garder seulement les 10 derniers sujets
        if len(self.context_cache["recent_topics"]) > 10:
            self.context_cache["recent_topics"] = self.context_cache["recent_topics"][-10:]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrait les mots-clés d'un texte"""
        # Mots-clés techniques courants
        keywords = []
        technical_terms = [
            "fonction", "classe", "variable", "python", "code", "script",
            "algorithm", "data", "file", "json", "html", "css", "javascript",
            "api", "database", "server", "client", "framework", "library"
        ]
        
        text_lower = text.lower()
        for term in technical_terms:
            if term in text_lower:
                keywords.append(term)
                
        return keywords
    
    def get_recent_conversations(self, limit: int = 5) -> List[ConversationEntry]:
        """Récupère les conversations récentes"""
        return self.conversations[-limit:] if limit > 0 else self.conversations
    
    def get_conversation_by_intent(self, intent: str, limit: int = 3) -> List[ConversationEntry]:
        """Récupère les conversations par intention"""
        matching = [conv for conv in self.conversations if conv.intent == intent]
        return matching[-limit:] if limit > 0 else matching
    
    def get_context_for_response(self, current_intent: str) -> Dict[str, Any]:
        """Génère le contexte pour une réponse"""
        context = {
            "session_duration": time.time() - self.session_start,
            "total_interactions": len(self.conversations),
            "user_preferences": self.user_preferences,
            "recent_topics": self.context_cache.get("recent_topics", [])
        }
        
        # Ajout du contexte spécifique à l'intention
        if current_intent in ["identity_question", "capabilities_question"]:
            # Pour les questions sur l'identité, inclure les interactions récentes
            context["recent_interactions"] = [
                {
                    "intent": conv.intent,
                    "user_message": conv.user_message[:50] + "..." if len(conv.user_message) > 50 else conv.user_message,
                    "time_ago": time.time() - conv.timestamp
                }
                for conv in self.conversations[-3:]
            ]
        
        return context
    
    def has_similar_recent_question(self, user_message: str, threshold: float = 0.7) -> Optional[ConversationEntry]:
        """Vérifie si une question similaire a été posée récemment"""
        if not self.conversations:
            return None
            
        # Vérifier d'abord si c'est exactement la même question (cas exact)
        user_lower = user_message.lower().strip()
        # Analyse des 5 dernières conversations
        recent = self.get_recent_conversations(5)
        
        for conv in reversed(recent):
            # Si la question est identique (insensible à la casse), retourner immédiatement
            if user_lower == conv.user_message.lower().strip():
                return conv
        
        # Sinon, chercher des questions similaires mais non identiques
        for conv in reversed(recent):
            conv_lower = conv.user_message.lower()
            
            # Ne pas détecter les questions courtes comme similaires pour éviter les faux positifs
            if len(user_lower) < 10 or len(conv_lower) < 10:
                continue
                
            # Similarité simple basée sur les mots en commun
            user_words = set(user_lower.split())
            conv_words = set(conv_lower.split())
            
            if user_words and conv_words:
                similarity = len(user_words & conv_words) / len(user_words | conv_words)
                if similarity > threshold:
                    return conv
        
        return None
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Génère un résumé de la conversation"""
        if not self.conversations:
            return {"status": "no_conversations"}
        
        intent_counts = {}
        total_confidence = 0
        
        for conv in self.conversations:
            intent_counts[conv.intent] = intent_counts.get(conv.intent, 0) + 1
            total_confidence += conv.confidence
        
        avg_confidence = total_confidence / len(self.conversations)
        
        return {
            "total_conversations": len(self.conversations),
            "session_duration_minutes": (time.time() - self.session_start) / 60,
            "intent_distribution": intent_counts,
            "average_confidence": avg_confidence,
            "most_common_intent": max(intent_counts.items(), key=lambda x: x[1])[0] if intent_counts else "none",
            "user_preferences": self.user_preferences
        }
    
    def clear(self) -> None:
        """Vide la mémoire de conversation"""
        self.conversations.clear()
        self.user_preferences.clear()
        self.context_cache.clear()
        self.stored_documents.clear()
        self.document_order.clear()
        self.session_start = time.time()
    
    def export_conversation(self, filepath: str) -> None:
        """Exporte la conversation vers un fichier JSON"""
        data = {
            "session_start": self.session_start,
            "conversations": [conv.to_dict() for conv in self.conversations],
            "user_preferences": self.user_preferences,
            "summary": self.get_conversation_summary()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def import_conversation(self, filepath: str) -> None:
        """Importe une conversation depuis un fichier JSON"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.session_start = data.get("session_start", time.time())
            self.conversations = [
                ConversationEntry.from_dict(conv) 
                for conv in data.get("conversations", [])
            ]
            self.user_preferences = data.get("user_preferences", {})
            
            # Reconstruction du cache contextuel
            self.context_cache = {}
            for conv in self.conversations:
                self._update_context_cache(conv)
                
        except Exception as e:
            print(f"Erreur lors de l'import: {e}")
    
    def store_document_content(self, filename: str, content: str) -> None:
        """
        Stocke le contenu d'un document dans la mémoire de session
        
        Args:
            filename: Nom du fichier
            content: Contenu du document
        """
        print(f"💾 Stockage du document: '{filename}'")
        
        # Si c'est un nouveau document, l'ajouter à la liste chronologique
        if filename not in self.stored_documents:
            self.document_order.append(filename)
            print(f"📝 Nouveau document ajouté à l'ordre: {self.document_order}")
        else:
            print(f"🔄 Document existant mis à jour: '{filename}'")
        
        self.stored_documents[filename] = {
            "content": content,
            "timestamp": time.time(),
            "word_count": len(content.split()),
            "char_count": len(content),
            "order_index": len(self.document_order) - 1 if filename not in self.stored_documents else self.stored_documents[filename].get("order_index", 0)
        }
        
        print(f"✅ Document '{filename}' stocké en mémoire ({len(content.split())} mots) - Position: {self.stored_documents[filename]['order_index'] + 1}")
        print(f"📋 État actuel - Ordre: {self.document_order}")
        print(f"📚 Documents stockés: {list(self.stored_documents.keys())}")
    
    
    def get_document_by_reference(self, reference: str) -> Dict[str, Any]:
        """
        Récupère un document par référence temporelle
        
        Args:
            reference: Référence comme "premier", "dernier", "précédent", etc.
            
        Returns:
            Dict contenant le document trouvé
        """
        print(f"🔍 Recherche de document par référence: '{reference}'")
        print(f"📚 Documents disponibles: {self.document_order}")
        
        if not self.document_order:
            print("❌ Aucun document en mémoire")
            return {}
        
        reference_lower = reference.lower()
        
        # Références au premier document
        if any(ref in reference_lower for ref in ["premier", "première", "first", "1er", "1ère"]):
            first_filename = self.document_order[0]
            print(f"✅ Premier document trouvé: '{first_filename}'")
            return {first_filename: self.stored_documents[first_filename]}
        
        # Références au dernier document
        elif any(ref in reference_lower for ref in ["dernier", "dernière", "last", "récent", "recent"]):
            last_filename = self.document_order[-1]
            print(f"✅ Dernier document trouvé: '{last_filename}'")
            return {last_filename: self.stored_documents[last_filename]}
        
        # Références au précédent document
        elif any(ref in reference_lower for ref in ["précédent", "precedent", "previous", "avant", "d'avant"]):
            if len(self.document_order) >= 2:
                prev_filename = self.document_order[-2]  # Avant-dernier
                print(f"✅ Document précédent trouvé: '{prev_filename}'")
                return {prev_filename: self.stored_documents[prev_filename]}
            elif len(self.document_order) == 1:
                # S'il n'y a qu'un document, le retourner
                first_filename = self.document_order[0]
                print(f"✅ Un seul document, retour du premier: '{first_filename}'")
                return {first_filename: self.stored_documents[first_filename]}
        
        # Références par numéro
        elif any(ref in reference_lower for ref in ["deuxième", "deuxieme", "second", "2ème", "2eme"]):
            if len(self.document_order) >= 2:
                second_filename = self.document_order[1]
                print(f"✅ Deuxième document trouvé: '{second_filename}'")
                return {second_filename: self.stored_documents[second_filename]}
        
        elif any(ref in reference_lower for ref in ["troisième", "troisieme", "third", "3ème", "3eme"]):
            if len(self.document_order) >= 3:
                third_filename = self.document_order[2]
                print(f"✅ Troisième document trouvé: '{third_filename}'")
                return {third_filename: self.stored_documents[third_filename]}
        
        # Si aucune référence spécifique trouvée, retourner le dernier document
        if self.document_order:
            last_filename = self.document_order[-1]
            print(f"🔄 Aucune référence spécifique, retour du dernier: '{last_filename}'")
            return {last_filename: self.stored_documents[last_filename]}
        
        print("❌ Aucun document trouvé")
        return {}
    
    def get_document_content(self, filename: str = None) -> Dict[str, Any]:
        """
        Récupère le contenu d'un document stocké
        
        Args:
            filename: Nom du fichier (si None, retourne tous les documents)
            
        Returns:
            Contenu du document ou dictionnaire de tous les documents
        """
        if filename:
            return self.stored_documents.get(filename)
        return self.stored_documents
    
    def search_in_documents(self, query: str) -> List[Dict[str, Any]]:
        """
        Recherche dans tous les documents stockés
        
        Args:
            query: Terme à rechercher
            
        Returns:
            Liste des résultats de recherche
        """
        results = []
        query_lower = query.lower()
        
        for filename, doc_data in self.stored_documents.items():
            content = doc_data["content"]
            if query_lower in content.lower():
                # Trouver les contextes où le terme apparaît
                contexts = []
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        # Contexte de 3 lignes
                        start = max(0, i - 1)
                        end = min(len(lines), i + 2)
                        context = '\n'.join(lines[start:end])
                        contexts.append(context.strip())
                        
                        if len(contexts) >= 3:  # Limiter à 3 contextes
                            break
                
                results.append({
                    "filename": filename,
                    "contexts": contexts,
                    "total_matches": content.lower().count(query_lower)
                })
        
        return results
    
    def clear_documents(self) -> None:
        """Vide la mémoire des documents"""
        self.stored_documents.clear()
        print("💾 Mémoire des documents effacée")
    
    def store_code_content(self, filename: str, code_info: Dict[str, Any]) -> None:
        """
        Stocke le contenu d'un fichier de code dans la mémoire
        
        Args:
            filename: Nom du fichier de code
            code_info: Informations sur le code (contenu, langage, etc.)
        """
        if filename not in self.stored_documents:
            self.document_order.append(filename)
        self.stored_documents[filename] = {
            "type": "code",
            "content": code_info.get("code", ""),
            "language": code_info.get("language", "unknown"),
            "timestamp": code_info.get("timestamp", datetime.now().isoformat()),
            "file_path": code_info.get("file_path", ""),
            "metadata": {
                "lines": len(code_info.get("code", "").split("\n")),
                "language": code_info.get("language", "unknown")
            }
        }
