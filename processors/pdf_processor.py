"""
Processeur de fichiers PDF
Lecture, analyse et extraction de contenu
"""

import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import io

class PDFProcessor:
    """
    Processeur pour les fichiers PDF
    """
    
    def __init__(self):
        """
        Initialise le processeur PDF
        """
        self.supported_extensions = ['.pdf']
        self._check_dependencies()
    
    def _check_dependencies(self):
        """
        Vérifie la disponibilité des bibliothèques PDF
        """
        self.pymupdf_available = False
        self.pypdf2_available = False
        
        try:
            import fitz  # PyMuPDF
            self.pymupdf_available = True
        except ImportError:
            pass
        
        try:
            import PyPDF2
            self.pypdf2_available = True
        except ImportError:
            pass
    
    def read_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Lit un fichier PDF et extrait le contenu
        
        Args:
            file_path: Chemin vers le fichier PDF
            
        Returns:
            Dictionnaire avec le contenu extrait
        """
        if not os.path.exists(file_path):
            return {"error": "Fichier non trouvé", "content": ""}
        
        # Essayer PyMuPDF en premier (meilleur)
        if self.pymupdf_available:
            return self._read_with_pymupdf(file_path)
        elif self.pypdf2_available:
            return self._read_with_pypdf2(file_path)
        else:
            return {
                "error": "Aucune bibliothèque PDF disponible. Installez PyMuPDF ou PyPDF2",
                "content": ""
            }
    
    def _read_with_pymupdf(self, file_path: str) -> Dict[str, Any]:
        """
        Lit un PDF avec PyMuPDF (recommandé)
        """
        try:
            import fitz
            
            doc = fitz.open(file_path)
            content = {
                "text": "",
                "pages": [],
                "metadata": doc.metadata,
                "page_count": len(doc)
            }
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                
                content["pages"].append({
                    "page_number": page_num + 1,
                    "text": page_text,
                    "word_count": len(page_text.split())
                })
                content["text"] += page_text + "\n"
            
            doc.close()
            
            return {
                "success": True,
                "content": content,
                "file_info": {
                    "path": file_path,
                    "size": os.path.getsize(file_path),
                    "processor": "PyMuPDF"
                }
            }
            
        except Exception as e:
            return {
                "error": f"Erreur PyMuPDF: {str(e)}",
                "content": ""
            }
    
    def _read_with_pypdf2(self, file_path: str) -> Dict[str, Any]:
        """
        Lit un PDF avec PyPDF2 (fallback)
        """
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                content = {
                    "text": "",
                    "pages": [],
                    "metadata": reader.metadata if reader.metadata else {},
                    "page_count": len(reader.pages)
                }
                
                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    
                    content["pages"].append({
                        "page_number": page_num + 1,
                        "text": page_text,
                        "word_count": len(page_text.split())
                    })
                    content["text"] += page_text + "\n"
                
                return {
                    "success": True,
                    "content": content,
                    "file_info": {
                        "path": file_path,
                        "size": os.path.getsize(file_path),
                        "processor": "PyPDF2"
                    }
                }
                
        except Exception as e:
            return {
                "error": f"Erreur PyPDF2: {str(e)}",
                "content": ""
            }
    
    def extract_text_by_page(self, file_path: str, page_numbers: List[int]) -> Dict[str, Any]:
        """
        Extrait le texte de pages spécifiques
        
        Args:
            file_path: Chemin vers le fichier PDF
            page_numbers: Liste des numéros de pages (1-indexé)
            
        Returns:
            Texte des pages demandées
        """
        result = self.read_pdf(file_path)
        
        if not result.get("success"):
            return result
        
        content = result["content"]
        extracted_pages = []
        
        for page_num in page_numbers:
            if 1 <= page_num <= content["page_count"]:
                page_data = content["pages"][page_num - 1]
                extracted_pages.append(page_data)
        
        return {
            "success": True,
            "extracted_pages": extracted_pages,
            "total_extracted": len(extracted_pages)
        }
    
    def search_in_pdf(self, file_path: str, search_term: str) -> Dict[str, Any]:
        """
        Recherche un terme dans le PDF
        
        Args:
            file_path: Chemin vers le fichier PDF
            search_term: Terme à rechercher
            
        Returns:
            Résultats de la recherche
        """
        result = self.read_pdf(file_path)
        
        if not result.get("success"):
            return result
        
        content = result["content"]
        search_results = []
        
        for page in content["pages"]:
            page_text = page["text"].lower()
            search_lower = search_term.lower()
            
            if search_lower in page_text:
                # Trouve les occurrences avec contexte
                lines = page["text"].split('\n')
                for line_num, line in enumerate(lines):
                    if search_lower in line.lower():
                        search_results.append({
                            "page": page["page_number"],
                            "line": line_num + 1,
                            "context": line.strip(),
                            "match": search_term
                        })
        
        return {
            "success": True,
            "search_term": search_term,
            "results": search_results,
            "total_matches": len(search_results)
        }
    
    def get_pdf_info(self, file_path: str) -> Dict[str, Any]:
        """
        Obtient les informations générales d'un PDF
        
        Args:
            file_path: Chemin vers le fichier PDF
            
        Returns:
            Informations sur le fichier PDF
        """
        if not os.path.exists(file_path):
            return {"error": "Fichier non trouvé"}
        
        file_stats = os.stat(file_path)
        
        info = {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "file_size": file_stats.st_size,
            "file_size_mb": round(file_stats.st_size / (1024 * 1024), 2),
            "created": file_stats.st_ctime,
            "modified": file_stats.st_mtime
        }
        
        # Essayer d'obtenir les métadonnées PDF
        result = self.read_pdf(file_path)
        if result.get("success"):
            content = result["content"]
            info.update({
                "page_count": content["page_count"],
                "metadata": content["metadata"],
                "total_words": sum(page["word_count"] for page in content["pages"])
            })
        
        return info
    
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
            "pymupdf": self.pymupdf_available,
            "pypdf2": self.pypdf2_available,
            "any_available": self.pymupdf_available or self.pypdf2_available
        }
    
    def extract_text(self, file_path: str) -> str:
        """
        Extrait le texte d'un fichier PDF
        
        Args:
            file_path: Chemin vers le fichier PDF
            
        Returns:
            Texte extrait du PDF
        """
        try:
            result = self.read_pdf(file_path)
            if result['success']:
                return result['content']['text']
            else:
                raise Exception(result.get('error', 'Erreur inconnue'))
        except Exception as e:
            raise Exception(f"Erreur lors de l'extraction de texte: {str(e)}")
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Méthode alias pour compatibilité avec l'interface GUI
        """
        return self.extract_text(file_path)
