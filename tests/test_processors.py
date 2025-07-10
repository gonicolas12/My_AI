"""
Tests for the processors modules.
"""
import unittest
from unittest.mock import Mock, patch, mock_open
import sys
import os
import tempfile

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from processors.pdf_processor import PDFProcessor
from processors.docx_processor import DOCXProcessor
from processors.code_processor import CodeProcessor


class TestPDFProcessor(unittest.TestCase):
    """Test cases for PDFProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = PDFProcessor()
    
    def test_initialization(self):
        """Test PDFProcessor initialization."""
        self.assertIsNotNone(self.processor)
    
    @patch('processors.pdf_processor.fitz.open')
    def test_extract_text_success(self, mock_pdf_open):
        """Test successful PDF text extraction."""
        # Mock PDF document
        mock_doc = Mock()
        mock_page = Mock()
        mock_page.get_text.return_value = "Sample PDF text"
        mock_doc.__iter__ = Mock(return_value=iter([mock_page]))
        mock_doc.close = Mock()
        mock_pdf_open.return_value = mock_doc
        
        result = self.processor.extract_text("dummy.pdf")
        
        self.assertEqual(result, "Sample PDF text")
        mock_pdf_open.assert_called_once_with("dummy.pdf")
        mock_doc.close.assert_called_once()
    
    def test_extract_text_file_not_found(self):
        """Test PDF text extraction with file not found."""
        result = self.processor.extract_text("nonexistent.pdf")
        
        self.assertIsNone(result)
    
    def test_validate_pdf_valid_extension(self):
        """Test PDF validation with valid extension."""
        self.assertTrue(self.processor.validate_pdf("test.pdf"))
        self.assertTrue(self.processor.validate_pdf("test.PDF"))
    
    def test_validate_pdf_invalid_extension(self):
        """Test PDF validation with invalid extension."""
        self.assertFalse(self.processor.validate_pdf("test.txt"))
        self.assertFalse(self.processor.validate_pdf("test.docx"))


class TestDOCXProcessor(unittest.TestCase):
    """Test cases for DOCXProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = DOCXProcessor()
    
    def test_initialization(self):
        """Test DOCXProcessor initialization."""
        self.assertIsNotNone(self.processor)
    
    @patch('processors.docx_processor.Document')
    def test_extract_text_success(self, mock_document):
        """Test successful DOCX text extraction."""
        # Mock document
        mock_doc = Mock()
        mock_paragraph = Mock()
        mock_paragraph.text = "Sample paragraph text"
        mock_doc.paragraphs = [mock_paragraph]
        mock_document.return_value = mock_doc
        
        result = self.processor.extract_text("dummy.docx")
        
        self.assertEqual(result, "Sample paragraph text")
        mock_document.assert_called_once_with("dummy.docx")
    
    def test_extract_text_file_not_found(self):
        """Test DOCX text extraction with file not found."""
        result = self.processor.extract_text("nonexistent.docx")
        
        self.assertIsNone(result)
    
    def test_validate_docx_valid_extension(self):
        """Test DOCX validation with valid extension."""
        self.assertTrue(self.processor.validate_docx("test.docx"))
        self.assertTrue(self.processor.validate_docx("test.DOCX"))
    
    def test_validate_docx_invalid_extension(self):
        """Test DOCX validation with invalid extension."""
        self.assertFalse(self.processor.validate_docx("test.txt"))
        self.assertFalse(self.processor.validate_docx("test.pdf"))


class TestCodeProcessor(unittest.TestCase):
    """Test cases for CodeProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = CodeProcessor()
    
    def test_initialization(self):
        """Test CodeProcessor initialization."""
        self.assertIsNotNone(self.processor)
    
    def test_read_code_file_success(self):
        """Test successful code file reading."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('Hello, World!')")
            temp_file = f.name
        
        try:
            result = self.processor.read_code_file(temp_file)
            self.assertEqual(result, "print('Hello, World!')")
        finally:
            os.unlink(temp_file)
    
    def test_read_code_file_not_found(self):
        """Test code file reading with file not found."""
        result = self.processor.read_code_file("nonexistent.py")
        
        self.assertIsNone(result)
    
    def test_detect_language_python(self):
        """Test language detection for Python files."""
        language = self.processor.detect_language("test.py")
        self.assertEqual(language, "python")
    
    def test_detect_language_javascript(self):
        """Test language detection for JavaScript files."""
        language = self.processor.detect_language("test.js")
        self.assertEqual(language, "javascript")
    
    def test_detect_language_html(self):
        """Test language detection for HTML files."""
        language = self.processor.detect_language("test.html")
        self.assertEqual(language, "html")
    
    def test_detect_language_unknown(self):
        """Test language detection for unknown files."""
        language = self.processor.detect_language("test.unknown")
        self.assertEqual(language, "unknown")
    
    def test_validate_syntax_python(self):
        """Test Python syntax validation."""
        # Valid Python code
        valid_code = "print('Hello, World!')"
        self.assertTrue(self.processor.validate_syntax(valid_code, "python"))
        
        # Invalid Python code
        invalid_code = "print('Hello, World!'"
        self.assertFalse(self.processor.validate_syntax(invalid_code, "python"))
    
    def test_validate_syntax_non_python(self):
        """Test syntax validation for non-Python languages."""
        # For non-Python languages, it should return True (basic validation)
        code = "console.log('Hello, World!');"
        self.assertTrue(self.processor.validate_syntax(code, "javascript"))


if __name__ == '__main__':
    unittest.main()
