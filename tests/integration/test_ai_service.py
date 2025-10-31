"""
Integration tests for AI Service
"""
import pytest
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


class TestAIServiceValidation:
    """Test AI Service API key validation"""
    
    def test_test_gemini_key_invalid(self, mock_logger):
        """Test Gemini key validation with invalid key"""
        from services.ai_service import AIService
        
        service = AIService(logger=mock_logger)
        is_valid, message = service.test_gemini_key("invalid_key_12345")
        
        # Should return False for invalid key
        assert is_valid is False
        assert message is not None
        assert len(message) > 0
    
    def test_test_openai_key_invalid(self, mock_logger):
        """Test OpenAI key validation with invalid key"""
        from services.ai_service import AIService
        
        service = AIService(logger=mock_logger)
        is_valid, message = service.test_openai_key("invalid-key-sk-12345")
        
        # Should return False for invalid key
        assert is_valid is False
        assert message is not None
        assert len(message) > 0


class TestAIServiceProcessing:
    """Test AI Service processing methods (with mocks)"""
    
    def test_translate_with_openai_no_api_key(self, mock_logger):
        """Test translation without API key"""
        from services.ai_service import AIService
        
        service = AIService(logger=mock_logger)
        result, error = service.translate_with_openai(
            text_list=["Hello", "World"],
            target_lang="vi",
            api_key=None
        )
        
        assert result is None
        assert error is not None
        assert "API Key" in error
    
    def test_translate_with_openai_empty_list(self, mock_logger):
        """Test translation with empty text list"""
        from services.ai_service import AIService
        
        service = AIService(logger=mock_logger)
        # This should return empty list or handle gracefully
        # Note: Need to check actual implementation behavior


class TestAIServiceErrorHandling:
    """Test AI Service error handling"""
    
    def test_process_script_no_api_key(self, mock_logger):
        """Test script processing without API key"""
        from services.ai_service import AIService
        
        service = AIService(logger=mock_logger)
        result, error = service.process_script_with_gemini(
            script_content="Test script",
            user_instruction="Test instruction",
            api_key=""
        )
        
        assert result is None
        assert error is not None
        assert "API Key" in error
    
    def test_divide_scene_no_api_key(self, mock_logger):
        """Test scene division without API key"""
        from services.ai_service import AIService
        
        service = AIService(logger=mock_logger)
        result, error = service.divide_scene_with_gemini(
            script_content="Test script",
            num_images=5,
            api_key=""
        )
        
        assert result is None
        assert error is not None
        assert "API Key" in error

