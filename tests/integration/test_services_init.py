"""
Basic initialization tests for all services
"""
import pytest
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


class TestServicesInit:
    """Test that all services can be initialized"""
    
    def test_ai_service_init(self, mock_logger):
        """Test AIService initialization"""
        from services.ai_service import AIService
        
        service = AIService(logger=mock_logger)
        assert service is not None
        assert service.logger == mock_logger
        mock_logger.info.assert_called()
    
    def test_image_service_init(self, mock_logger):
        """Test ImageService initialization"""
        from services.image_service import ImageService
        
        service = ImageService(logger=mock_logger)
        assert service is not None
        assert service.logger == mock_logger
        mock_logger.info.assert_called()
    
    def test_model_service_init(self, mock_logger):
        """Test ModelService initialization"""
        from services.model_service import ModelService
        
        service = ModelService(logger=mock_logger)
        assert service is not None
        assert service.logger == mock_logger
        assert service.current_model is None
        mock_logger.info.assert_called()
    
    def test_metadata_service_init(self, mock_logger):
        """Test MetadataService initialization"""
        from services.metadata_service import MetadataService
        
        service = MetadataService(logger=mock_logger)
        assert service is not None
        assert service.logger == mock_logger
        assert service.cache == {}
        mock_logger.info.assert_called()
    
    def test_youtube_service_init(self, mock_logger):
        """Test YouTubeService initialization"""
        from services.youtube_service import YouTubeService
        
        service = YouTubeService(logger=mock_logger)
        assert service is not None
        assert service.logger == mock_logger
        assert service.queue == []
        assert service.is_uploading is False
        mock_logger.info.assert_called()

