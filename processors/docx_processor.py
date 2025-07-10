"""
Processeur de fichiers DOCX
Lecture, analyse et extraction de contenu Word
"""

import os
from typing import Dict, Any, List, Optional
from pathlib import Path

class DOCXProcessor:
    """
    Processeur pour les fichiers DOCX (Word)
    """
    
    def __init__(self):
        """
        Initialise le processeur DOCX
        """
        self.supported_extensions = ['.docx', '.doc']
        self._check_dependencies()
    
    def _check_dependencies(self):
        """
        Vérifie la disponibilité des bibliothèques DOCX
        """
        self.python_docx_available = False
        
        try:
            import docx
            # Test d'import complet
            from docx import Document
            self.python_docx_available = True
            print("✅ Module python-docx disponible")
        except ImportError as e:
            print(f"❌ Module 'python-docx' non installé: {e}")
            print("💡 Installez avec: pip install python-docx")
        except Exception as e:
            print(f"❌ Erreur lors de l'import python-docx: {e}")
    
    def read_docx(self, file_path: str) -> Dict[str, Any]:
        """
        Lit un fichier DOCX et extrait le contenu - Version avec support OneDrive
        """
        # Résoudre le chemin OneDrive en premier
        resolved_path = self._resolve_onedrive_path(file_path)
        
        if not os.path.exists(resolved_path):
            return {
                "success": False,
                "error": f"Fichier non trouvé: {file_path}",
                "error_type": "FILE_NOT_FOUND",
                "resolution": "Vérifiez que le fichier existe ou qu'il est synchronisé depuis OneDrive"
            }
        
        if not self.python_docx_available:
            return {
                "success": False,
                "error": "python-docx non disponible. Installez avec: pip install python-docx",
                "error_type": "MISSING_PACKAGE",
                "resolution": "Installez le package avec : pip install python-docx"
            }
        
        try:
            import docx
            
            print(f"📂 Lecture du fichier: {resolved_path}")
            doc = docx.Document(resolved_path)
            
            content = {
                "text": "",
                "paragraphs": [],
                "tables": [],
                "styles": [],
                "properties": {}
            }
            
            # Extraction des paragraphes
            for para in doc.paragraphs:
                para_data = {
                    "text": para.text,
                    "style": para.style.name if para.style else "Normal",
                    "alignment": str(para.alignment) if para.alignment else "None"
                }
                content["paragraphs"].append(para_data)
                content["text"] += para.text + "\n"
            
            # Extraction des tableaux
            for table_idx, table in enumerate(doc.tables):
                table_data = {
                    "table_number": table_idx + 1,
                    "rows": []
                }
                
                for row in table.rows:
                    row_data = []
                    for cell in row.cells:
                        row_data.append(cell.text.strip())
                    table_data["rows"].append(row_data)
                
                content["tables"].append(table_data)
            
            # Propriétés du document
            if hasattr(doc, 'core_properties'):
                props = doc.core_properties
                content["properties"] = {
                    "title": props.title,
                    "author": props.author,
                    "subject": props.subject,
                    "created": str(props.created) if props.created else None,
                    "modified": str(props.modified) if props.modified else None
                }
            
            return {
                "success": True,
                "content": content,
                "file_info": {
                    "original_path": file_path,
                    "resolved_path": resolved_path,
                    "size": os.path.getsize(resolved_path),
                    "processor": "python-docx"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erreur lors de la lecture DOCX: {str(e)}",
                "error_type": "PROCESSING_ERROR",
                "resolution": "Vérifiez que le fichier n'est pas corrompu et qu'il est accessible"
            }
        
    def _resolve_onedrive_path(self, file_path: str) -> str:
        """
        Résout les chemins OneDrive pour les rendre accessibles
        
        Args:
            file_path: Chemin du fichier (peut être OneDrive)
            
        Returns:
            Chemin résolu et accessible
        """
        import os
        from pathlib import Path
        
        # Si le fichier existe déjà, le retourner tel quel
        if os.path.exists(file_path):
            return file_path
        
        # Chemins OneDrive courants
        onedrive_paths = [
            os.path.expanduser("~/OneDrive"),
            os.path.expanduser("~/OneDrive - Personnel"),
            os.path.expanduser("~/OneDrive - Professionnel"),
            "C:/Users/" + os.getenv('USERNAME', '') + "/OneDrive",
            "C:/Users/" + os.getenv('USERNAME', '') + "/OneDrive - Personnel",
        ]
        
        # Ajouter les chemins OneDrive spécifiques détectés automatiquement
        username = os.getenv('USERNAME', '')
        if username:
            # Chemins OneDrive Business/Enterprise
            enterprise_patterns = [
                f"C:/Users/{username}/OneDrive - *",
                f"C:/Users/{username}/OneDrive*",
            ]
            
            import glob
            for pattern in enterprise_patterns:
                onedrive_paths.extend(glob.glob(pattern))
        
        # Extraire le nom de fichier de base
        file_name = os.path.basename(file_path)
        
        # Chercher le fichier dans tous les répertoires OneDrive
        for onedrive_path in onedrive_paths:
            if os.path.exists(onedrive_path):
                # Recherche récursive dans OneDrive
                for root, dirs, files in os.walk(onedrive_path):
                    if file_name in files:
                        potential_path = os.path.join(root, file_name)
                        print(f"✅ Fichier trouvé dans OneDrive: {potential_path}")
                        return potential_path
        
        # Si pas trouvé, essayer avec le répertoire Desktop OneDrive
        desktop_onedrive = os.path.expanduser("~/OneDrive/Desktop")
        if os.path.exists(desktop_onedrive):
            desktop_file = os.path.join(desktop_onedrive, file_name)
            if os.path.exists(desktop_file):
                print(f"✅ Fichier trouvé sur Bureau OneDrive: {desktop_file}")
                return desktop_file
        
        # Retourner le chemin original si rien trouvé
        print(f"⚠️ Fichier non trouvé dans OneDrive, tentative avec le chemin original")
        return file_path
    
    def extract_paragraphs_by_style(self, file_path: str, style_name: str) -> Dict[str, Any]:
        """
        Extrait les paragraphes d'un style spécifique
        
        Args:
            file_path: Chemin vers le fichier DOCX
            style_name: Nom du style à extraire
            
        Returns:
            Paragraphes du style demandé
        """
        result = self.read_docx(file_path)
        
        if not result.get("success"):
            return result
        
        content = result["content"]
        filtered_paragraphs = [
            para for para in content["paragraphs"] 
            if para["style"] == style_name
        ]
        
        return {
            "success": True,
            "style": style_name,
            "paragraphs": filtered_paragraphs,
            "count": len(filtered_paragraphs)
        }
    
    def extract_tables(self, file_path: str) -> Dict[str, Any]:
        """
        Extrait uniquement les tableaux du document
        
        Args:
            file_path: Chemin vers le fichier DOCX
            
        Returns:
            Tableaux extraits
        """
        result = self.read_docx(file_path)
        
        if not result.get("success"):
            return result
        
        content = result["content"]
        
        return {
            "success": True,
            "tables": content["tables"],
            "table_count": len(content["tables"])
        }
    
    def search_in_docx(self, file_path: str, search_term: str) -> Dict[str, Any]:
        """
        Recherche un terme dans le document DOCX
        
        Args:
            file_path: Chemin vers le fichier DOCX
            search_term: Terme à rechercher
            
        Returns:
            Résultats de la recherche
        """
        result = self.read_docx(file_path)
        
        if not result.get("success"):
            return result
        
        content = result["content"]
        search_results = []
        search_lower = search_term.lower()
        
        # Recherche dans les paragraphes
        for para_idx, para in enumerate(content["paragraphs"]):
            if search_lower in para["text"].lower():
                search_results.append({
                    "type": "paragraph",
                    "index": para_idx,
                    "text": para["text"],
                    "style": para["style"]
                })
        
        # Recherche dans les tableaux
        for table_idx, table in enumerate(content["tables"]):
            for row_idx, row in enumerate(table["rows"]):
                for col_idx, cell in enumerate(row):
                    if search_lower in cell.lower():
                        search_results.append({
                            "type": "table",
                            "table_number": table_idx + 1,
                            "row": row_idx + 1,
                            "column": col_idx + 1,
                            "text": cell
                        })
        
        return {
            "success": True,
            "search_term": search_term,
            "results": search_results,
            "total_matches": len(search_results)
        }
    
    def get_document_stats(self, file_path: str) -> Dict[str, Any]:
        """
        Obtient les statistiques du document
        
        Args:
            file_path: Chemin vers le fichier DOCX
            
        Returns:
            Statistiques du document
        """
        result = self.read_docx(file_path)
        
        if not result.get("success"):
            return result
        
        content = result["content"]
        
        # Comptage des mots
        total_words = len(content["text"].split())
        total_characters = len(content["text"])
        
        # Styles utilisés
        styles_used = list(set(para["style"] for para in content["paragraphs"]))
        
        stats = {
            "success": True,
            "file_path": file_path,
            "paragraph_count": len(content["paragraphs"]),
            "table_count": len(content["tables"]),
            "word_count": total_words,
            "character_count": total_characters,
            "styles_used": styles_used,
            "properties": content["properties"]
        }
        
        return stats
    
    def is_supported(self, file_path: str) -> bool:
        """
        Vérifie si le fichier est supporté
        
        Args:
            file_path: Chemin vers le fichier
            
        Returns:
            True si le fichier est supporté
        """
        return Path(file_path).suffix.lower() in self.supported_extensions
    
    def get_dependencies_status(self) -> Dict[str, bool]:
        """
        Retourne le statut des dépendances
        """
        return {
            "python_docx": self.python_docx_available,
            "available": self.python_docx_available
        }
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extrait le texte d'un fichier DOCX avec gestion améliorée des erreurs
        
        Args:
            file_path: Chemin vers le fichier DOCX
            
        Returns:
            Dict avec le texte extrait et les métadonnées ou l'erreur
        """
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": "Fichier non trouvé",
                "error_type": "FILE_NOT_FOUND"
            }
        
        if not self.python_docx_available:
            return {
                "success": False,
                "error": "Le module python-docx n'est pas installé",
                "error_type": "MISSING_PACKAGE",
                "resolution": "Installez le package avec : pip install python-docx"
            }
            
        try:
            result = self.read_docx(file_path)
            if "error" in result:
                return {
                    "success": False,
                    "error": result["error"],
                    "error_type": "READ_ERROR"
                }
                
            content = result["content"]
            if not content.get("text", "").strip():
                return {
                    "success": False,
                    "error": "Document vide ou non lisible",
                    "error_type": "EMPTY_CONTENT"
                }
                
            return {
                "success": True,
                "content": content["text"],
                "metadata": {
                    "paragraphs": len(content["paragraphs"]),
                    "tables": len(content["tables"]),
                    "properties": content["properties"]
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erreur lors de la lecture du document: {str(e)}",
                "error_type": "PROCESSING_ERROR"
            }
