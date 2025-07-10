"""
Tests for the utilities modules.
"""
import unittest
from unittest.mock import Mock, patch, mock_open
import sys
import os
import tempfile
import logging

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.logger import Logger
from utils.file_manager import FileManager
from utils.validators import Validators


class TestLogger(unittest.TestCase):
    """Test cases for Logger class."""
    
    def test_get_logger(self):
        """Test logger creation."""
        logger = Logger.get_logger("test_logger")
        
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test_logger")
    
    def test_get_logger_singleton(self):
        """Test logger singleton behavior."""
        logger1 = Logger.get_logger("same_name")
        logger2 = Logger.get_logger("same_name")
        
        self.assertIs(logger1, logger2)
    
    @patch('utils.logger.os.makedirs')
    def test_setup_file_handler(self, mock_makedirs):
        """Test file handler setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            logger = Logger.get_logger("test_file_logger")
            Logger.setup_file_handler(logger, log_file)
            
            # Check if file handler was added
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            self.assertTrue(len(file_handlers) > 0)


class TestFileManager(unittest.TestCase):
    """Test cases for FileManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.file_manager = FileManager()
    
    def test_read_file_success(self):
        """Test successful file reading."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Test content")
            temp_file = f.name
        
        try:
            content = self.file_manager.read_file(temp_file)
            self.assertEqual(content, "Test content")
        finally:
            os.unlink(temp_file)
    
    def test_read_file_not_found(self):
        """Test file reading with file not found."""
        content = self.file_manager.read_file("nonexistent.txt")
        
        self.assertIsNone(content)
    
    def test_write_file_success(self):
        """Test successful file writing."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name
        
        try:
            result = self.file_manager.write_file(temp_file, "Test content")
            self.assertTrue(result)
            
            # Verify content was written
            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertEqual(content, "Test content")
        finally:
            os.unlink(temp_file)
    
    def test_write_file_directory_creation(self):
        """Test file writing with directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = os.path.join(temp_dir, "subdir", "test.txt")
            
            result = self.file_manager.write_file(nested_path, "Test content")
            self.assertTrue(result)
            self.assertTrue(os.path.exists(nested_path))
    
    def test_file_exists_true(self):
        """Test file existence check - file exists."""
        with tempfile.NamedTemporaryFile() as f:
            self.assertTrue(self.file_manager.file_exists(f.name))
    
    def test_file_exists_false(self):
        """Test file existence check - file doesn't exist."""
        self.assertFalse(self.file_manager.file_exists("nonexistent.txt"))
    
    def test_get_file_extension(self):
        """Test file extension extraction."""
        self.assertEqual(self.file_manager.get_file_extension("test.txt"), ".txt")
        self.assertEqual(self.file_manager.get_file_extension("test.pdf"), ".pdf")
        self.assertEqual(self.file_manager.get_file_extension("test"), "")
    
    def test_get_file_size(self):
        """Test file size calculation."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Test content")
            temp_file = f.name
        
        try:
            size = self.file_manager.get_file_size(temp_file)
            self.assertGreater(size, 0)
        finally:
            os.unlink(temp_file)
    
    def test_get_file_size_not_found(self):
        """Test file size calculation for non-existent file."""
        size = self.file_manager.get_file_size("nonexistent.txt")
        
        self.assertEqual(size, 0)


class TestValidators(unittest.TestCase):
    """Test cases for Validators class."""
    
    def test_is_valid_email_valid(self):
        """Test valid email validation."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org"
        ]
        
        for email in valid_emails:
            with self.subTest(email=email):
                self.assertTrue(Validators.is_valid_email(email))
    
    def test_is_valid_email_invalid(self):
        """Test invalid email validation."""
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user@domain",
            ""
        ]
        
        for email in invalid_emails:
            with self.subTest(email=email):
                self.assertFalse(Validators.is_valid_email(email))
    
    def test_is_valid_url_valid(self):
        """Test valid URL validation."""
        valid_urls = [
            "https://www.example.com",
            "http://example.com",
            "https://subdomain.example.com/path",
            "http://localhost:8080"
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(Validators.is_valid_url(url))
    
    def test_is_valid_url_invalid(self):
        """Test invalid URL validation."""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Not http/https
            "www.example.com",    # Missing protocol
            ""
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(Validators.is_valid_url(url))
    
    def test_is_valid_file_path_valid(self):
        """Test valid file path validation."""
        with tempfile.NamedTemporaryFile() as f:
            self.assertTrue(Validators.is_valid_file_path(f.name))
    
    def test_is_valid_file_path_invalid(self):
        """Test invalid file path validation."""
        invalid_paths = [
            "nonexistent.txt",
            "",
            None
        ]
        
        for path in invalid_paths:
            with self.subTest(path=path):
                self.assertFalse(Validators.is_valid_file_path(path))
    
    def test_is_valid_extension_valid(self):
        """Test valid file extension validation."""
        valid_extensions = [".txt", ".pdf", ".docx", ".py"]
        allowed_extensions = [".txt", ".pdf", ".docx", ".py", ".html"]
        
        for ext in valid_extensions:
            with self.subTest(extension=ext):
                self.assertTrue(Validators.is_valid_extension(ext, allowed_extensions))
    
    def test_is_valid_extension_invalid(self):
        """Test invalid file extension validation."""
        invalid_extensions = [".exe", ".bat", ".unknown"]
        allowed_extensions = [".txt", ".pdf", ".docx", ".py", ".html"]
        
        for ext in invalid_extensions:
            with self.subTest(extension=ext):
                self.assertFalse(Validators.is_valid_extension(ext, allowed_extensions))
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        test_cases = [
            ("normal_file.txt", "normal_file.txt"),
            ("file with spaces.txt", "file_with_spaces.txt"),
            ("file/with\\dangerous:chars.txt", "file_with_dangerous_chars.txt"),
            ("file<>|?*.txt", "file_.txt")
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(filename=input_name):
                result = Validators.sanitize_filename(input_name)
                self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
