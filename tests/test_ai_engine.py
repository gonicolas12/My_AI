"""
Tests for the AI Engine core module.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.ai_engine import AIEngine
from core.config import Config


class TestAIEngine(unittest.TestCase):
    """Test cases for AIEngine class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Config()
        self.ai_engine = AIEngine(self.config)
    
    def test_initialization(self):
        """Test AIEngine initialization."""
        self.assertIsNotNone(self.ai_engine)
        self.assertEqual(self.ai_engine.config, self.config)
        self.assertIsNotNone(self.ai_engine.conversation)
        self.assertIsNone(self.ai_engine.llm_manager)
    
    @patch('models.local_llm.LocalLLMManager')
    def test_initialize_llm_success(self, mock_llm_manager):
        """Test successful LLM initialization."""
        mock_instance = Mock()
        mock_llm_manager.return_value = mock_instance
        mock_instance.initialize.return_value = True
        
        result = self.ai_engine.initialize_llm()
        
        self.assertTrue(result)
        self.assertEqual(self.ai_engine.llm_manager, mock_instance)
        mock_instance.initialize.assert_called_once()
    
    @patch('models.local_llm.LocalLLMManager')
    def test_initialize_llm_failure(self, mock_llm_manager):
        """Test LLM initialization failure."""
        mock_instance = Mock()
        mock_llm_manager.return_value = mock_instance
        mock_instance.initialize.return_value = False
        
        result = self.ai_engine.initialize_llm()
        
        self.assertFalse(result)
        self.assertIsNone(self.ai_engine.llm_manager)
    
    def test_process_text_no_llm(self):
        """Test text processing without initialized LLM."""
        response = self.ai_engine.process_text("Hello")
        
        self.assertIn("LLM not initialized", response)
    
    @patch('models.local_llm.LocalLLMManager')
    def test_process_text_with_llm(self, mock_llm_manager):
        """Test text processing with initialized LLM."""
        mock_instance = Mock()
        mock_llm_manager.return_value = mock_instance
        mock_instance.initialize.return_value = True
        mock_instance.generate_response.return_value = "AI response"
        
        self.ai_engine.initialize_llm()
        response = self.ai_engine.process_text("Hello")
        
        self.assertEqual(response, "AI response")
        mock_instance.generate_response.assert_called_once()
    
    def test_get_conversation_history(self):
        """Test getting conversation history."""
        history = self.ai_engine.get_conversation_history()
        
        self.assertIsInstance(history, list)
    
    def test_clear_conversation(self):
        """Test clearing conversation."""
        # Add some conversation
        self.ai_engine.conversation.add_message("user", "Hello")
        self.ai_engine.conversation.add_message("assistant", "Hi")
        
        # Clear and verify
        self.ai_engine.clear_conversation()
        history = self.ai_engine.get_conversation_history()
        
        self.assertEqual(len(history), 0)


if __name__ == '__main__':
    unittest.main()
