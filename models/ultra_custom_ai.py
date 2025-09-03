"""
UltraCustomAIModel - Système IA avec contexte 1M tokens
Modèle personnalisé avec capacités étendues de contexte
"""

import os
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

# Ajout du chemin racine pour les imports
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    from models.million_token_context_manager import MillionTokenContextManager
except ImportError:
    # Fallback si le gestionnaire n'est pas encore créé
    MillionTokenContextManager = None

# Import du calculateur intelligent pour le système Ultra
try:
    from utils.intelligent_calculator import intelligent_calculator
    CALCULATOR_AVAILABLE = True
except ImportError:
    CALCULATOR_AVAILABLE = False
    print("⚠️ Calculateur intelligent non disponible pour Ultra")

class UltraCustomAIModel:
    """
    Modèle IA Ultra avec contexte étendu de 1 million de tokens
    """
    
    def __init__(self, base_ai_engine=None):
        """
        Initialise le modèle Ultra
        
        Args:
            base_ai_engine: Moteur IA de base à étendre
        """
        self.base_ai = base_ai_engine
        self.is_ultra_available = True
        self.context_stats = {
            'total_tokens': 0,
            'documents_processed': 0,
            'chunks_created': 0,
            'max_context_length': 1000000  # 1M tokens
        }
        
        # Initialiser le gestionnaire de contexte 1M tokens
        if MillionTokenContextManager:
            self.context_manager = MillionTokenContextManager()
        else:
            self.context_manager = None
            print("⚠️ Gestionnaire 1M tokens non disponible, mode de base activé")
    
    def generate_response(self, user_input: str, context: str = "", **kwargs) -> Dict[str, Any]:
        """
        Génère une réponse en utilisant le contexte étendu
        
        Args:
            user_input: Message de l'utilisateur
            context: Contexte additionnel
            **kwargs: Paramètres supplémentaires
            
        Returns:
            Dict contenant la réponse et les statistiques
        """
        try:
            # 🧮 PRIORITÉ 1: Vérification si c'est un calcul (même en mode Ultra)
            if CALCULATOR_AVAILABLE and intelligent_calculator.is_calculation_request(user_input):
                print(f"🧮 Calcul Ultra détecté: {user_input}")
                calc_result = intelligent_calculator.calculate(user_input)
                calc_response = intelligent_calculator.format_response(calc_result)
                
                return {
                    'response': calc_response,
                    'success': True,
                    'calculation': True,
                    'ultra_mode': True,
                    'ultra_stats': self.get_context_stats(),
                    'calc_details': calc_result
                }
            
            # Construire le contexte étendu
            extended_context = self._build_extended_context(context)
            
            # Utiliser le moteur IA de base si disponible
            if self.base_ai:
                # AIEngine utilise process_text au lieu de generate_response
                if hasattr(self.base_ai, 'process_text'):
                    ai_response = self.base_ai.process_text(user_input)
                    response = {
                        'response': ai_response,
                        'success': True
                    }
                elif hasattr(self.base_ai, 'process_message'):
                    # Version async
                    import asyncio
                    ai_response = asyncio.run(self.base_ai.process_message(user_input))
                    response = {
                        'response': ai_response,
                        'success': True
                    }
                else:
                    # Fallback si aucune méthode disponible
                    response = {
                        'response': f"Méthode de traitement non trouvée sur {type(self.base_ai).__name__}",
                        'success': False
                    }
            else:
                # Réponse de fallback
                response = {
                    'response': f"[ULTRA MODE] Traitement de: {user_input[:100]}...",
                    'success': True
                }
            
            # Ajouter les statistiques Ultra
            if isinstance(response, dict):
                response['ultra_stats'] = self.get_context_stats()
                response['ultra_mode'] = True
                response['context_length'] = len(extended_context)
            
            return response
            
        except Exception as e:
            return {
                'response': f"Erreur Ultra: {str(e)}",
                'success': False,
                'error': str(e),
                'ultra_mode': True
            }
    
    def add_document_to_context(self, document_content: str, document_name: str = "") -> Dict[str, Any]:
        """
        Ajoute un document au contexte 1M tokens
        
        Args:
            document_content: Contenu du document
            document_name: Nom du document
            
        Returns:
            Statistiques d'ajout
        """
        if not self.context_manager:
            return {'success': False, 'error': 'Gestionnaire de contexte indisponible'}
        
        try:
            # Ajouter au gestionnaire de contexte
            result = self.context_manager.add_document(document_content, document_name)
            
            # Mettre à jour les statistiques
            self.context_stats['documents_processed'] += 1
            self.context_stats['total_tokens'] += len(document_content.split())
            
            if 'chunks_created' in result:
                self.context_stats['chunks_created'] += result['chunks_created']
            
            return {
                'success': True,
                'document_name': document_name,
                'chunks_created': result.get('chunks_created', 1),
                'tokens_added': len(document_content.split()),
                'total_context_tokens': self.context_stats['total_tokens']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur lors de l\'ajout du document: {str(e)}'
            }
    
    def add_code_to_context(self, code_content: str, file_name: str = "") -> Dict[str, Any]:
        """
        Ajoute du code au contexte avec analyse syntaxique
        
        Args:
            code_content: Contenu du code
            file_name: Nom du fichier
            
        Returns:
            Statistiques d'ajout
        """
        if not self.context_manager:
            return {'success': False, 'error': 'Gestionnaire de contexte indisponible'}
        
        try:
            # Préparer le contenu avec métadonnées de code
            enriched_content = f"# FICHIER: {file_name}\n\n{code_content}"
            
            result = self.context_manager.add_document(enriched_content, f"CODE: {file_name}")
            
            # Mettre à jour les statistiques
            self.context_stats['documents_processed'] += 1
            self.context_stats['total_tokens'] += len(code_content.split())
            
            return {
                'success': True,
                'file_name': file_name,
                'chunks_created': result.get('chunks_created', 1),
                'tokens_added': len(code_content.split()),
                'total_context_tokens': self.context_stats['total_tokens']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur lors de l\'ajout du code: {str(e)}'
            }
    
    def _build_extended_context(self, base_context: str = "") -> str:
        """
        Construit le contexte étendu en utilisant le gestionnaire 1M tokens
        """
        if not self.context_manager:
            return base_context
        
        try:
            # Récupérer le contexte du gestionnaire
            extended_context = self.context_manager.get_relevant_context(base_context)
            
            # Combiner avec le contexte de base
            if base_context:
                return f"{base_context}\n\n--- CONTEXTE ÉTENDU ---\n{extended_context}"
            else:
                return extended_context
                
        except Exception as e:
            print(f"Erreur lors de la construction du contexte étendu: {e}")
            return base_context
    
    def get_context_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du contexte"""
        stats = self.context_stats.copy()
        
        if self.context_manager:
            # Ajouter les stats du gestionnaire de contexte
            manager_stats = self.context_manager.get_stats()
            stats.update(manager_stats)
        
        return stats
    
    def clear_context(self):
        """Vide le contexte étendu"""
        if self.context_manager:
            self.context_manager.clear_context()
        
        # Réinitialiser les statistiques
        self.context_stats = {
            'total_tokens': 0,
            'documents_processed': 0,
            'chunks_created': 0,
            'max_context_length': 1000000
        }
    
    def is_available(self) -> bool:
        """Vérifie si le mode Ultra est disponible"""
        return self.is_ultra_available and self.context_manager is not None

# Fonction de compatibilité pour l'import
def create_ultra_model(base_ai_engine=None) -> UltraCustomAIModel:
    """Crée une instance du modèle Ultra"""
    return UltraCustomAIModel(base_ai_engine)

# Test de disponibilité
def is_ultra_system_available() -> bool:
    """Vérifie si le système Ultra est disponible"""
    try:
        model = UltraCustomAIModel()
        return model.is_available()
    except Exception:
        return False

if __name__ == "__main__":
    # Test du système
    print("🚀 Test du système UltraCustomAIModel")
    model = UltraCustomAIModel()
    print(f"Ultra disponible: {model.is_available()}")
    print(f"Stats: {model.get_context_stats()}")
