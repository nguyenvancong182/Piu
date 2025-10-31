"""
Integration tests for Metadata Service
"""
import pytest
import os
import sys
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


class TestMetadataServiceCache:
    """Test MetadataService cache operations"""
    
    def test_load_cache_empty_file(self, mock_logger, temp_dir):
        """Test loading empty cache file"""
        from services.metadata_service import MetadataService
        
        # Create empty cache file
        cache_file = os.path.join(temp_dir, "cache.json")
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write("{}")
        
        service = MetadataService(logger=mock_logger)
        result = service.load_cache(cache_file)
        
        assert result is True
        assert service.cache == {}
        assert mock_logger.info.called
    
    def test_load_cache_with_data(self, mock_logger, temp_dir):
        """Test loading cache with existing data"""
        from services.metadata_service import MetadataService
        
        cache_file = os.path.join(temp_dir, "cache.json")
        test_data = {
            "key1": {"title": "Title 1", "base_thumbnail": "thumb1.jpg"},
            "key2": {"title": "Title 2", "base_thumbnail": "thumb2.jpg"}
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)
        
        service = MetadataService(logger=mock_logger)
        result = service.load_cache(cache_file)
        
        assert result is True
        assert len(service.cache) == 2
        assert service.cache["key1"]["title"] == "Title 1"
    
    def test_load_cache_nonexistent_file(self, mock_logger, temp_dir):
        """Test loading non-existent cache file"""
        from services.metadata_service import MetadataService
        
        service = MetadataService(logger=mock_logger)
        result = service.load_cache("nonexistent.json")
        
        assert result is False
        assert service.cache == {}
        mock_logger.info.assert_called()
    
    def test_save_cache(self, mock_logger, temp_dir):
        """Test saving cache to file"""
        from services.metadata_service import MetadataService
        
        cache_file = os.path.join(temp_dir, "cache.json")
        service = MetadataService(logger=mock_logger)
        
        # Add some data
        service.cache = {"test_key": {"title": "Test Title"}}
        result = service.save_cache(cache_file)
        
        assert result is True
        assert os.path.exists(cache_file)
        
        # Verify saved data
        with open(cache_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        assert saved_data == {"test_key": {"title": "Test Title"}}
    
    def test_get_metadata_nonexistent(self, mock_logger):
        """Test getting metadata for non-existent key"""
        from services.metadata_service import MetadataService
        
        service = MetadataService(logger=mock_logger)
        result = service.get_metadata("nonexistent_key")
        
        assert result is None
    
    def test_get_metadata_existing(self, mock_logger):
        """Test getting existing metadata"""
        from services.metadata_service import MetadataService
        
        service = MetadataService(logger=mock_logger)
        service.cache = {
            "test_key": {"title": "Test Title", "base_thumbnail": "thumb.jpg"}
        }
        
        result = service.get_metadata("test_key")
        
        assert result is not None
        assert result["title"] == "Test Title"
        assert result["base_thumbnail"] == "thumb.jpg"
    
    def test_has_metadata(self, mock_logger):
        """Test checking if metadata exists"""
        from services.metadata_service import MetadataService
        
        service = MetadataService(logger=mock_logger)
        service.cache = {"test_key": {"title": "Test Title"}}
        
        assert service.has_metadata("test_key") is True
        assert service.has_metadata("nonexistent") is False
    
    def test_update_metadata_new(self, mock_logger):
        """Test updating metadata for new key"""
        from services.metadata_service import MetadataService
        
        service = MetadataService(logger=mock_logger)
        result = service.update_metadata(
            key="new_key",
            title="New Title",
            thumbnail="new_thumb.jpg"
        )
        
        assert result is True
        assert service.has_metadata("new_key") is True
        metadata = service.get_metadata("new_key")
        assert metadata["title"] == "New Title"
        assert metadata["thumbnail"] == "new_thumb.jpg"
    
    def test_update_metadata_existing(self, mock_logger):
        """Test updating existing metadata"""
        from services.metadata_service import MetadataService
        
        service = MetadataService(logger=mock_logger)
        service.cache = {"test_key": {"title": "Old Title"}}
        
        service.update_metadata(
            key="test_key",
            title="Updated Title"
        )
        
        metadata = service.get_metadata("test_key")
        assert metadata["title"] == "Updated Title"
    
    def test_update_metadata_autoincrement_thumbnail(self, mock_logger):
        """Test auto-increment thumbnail feature"""
        from services.metadata_service import MetadataService
        
        service = MetadataService(logger=mock_logger)
        
        # Test auto-increment with filename containing number
        service.update_metadata(
            key="test_key",
            title="Test",
            base_thumbnail_for_increment="thumb_1.jpg",
            auto_increment_thumb=True
        )
        
        metadata = service.get_metadata("test_key")
        # Should auto-increment to thumb_2.jpg
        assert "thumb_2.jpg" in metadata.get("thumbnail", "")


class TestMetadataServiceAutofill:
    """Test MetadataService autofill functionality"""
    
    def test_autofill_from_cache(self, mock_logger):
        """Test autofilling from cached metadata"""
        from services.metadata_service import MetadataService
        
        service = MetadataService(logger=mock_logger)
        service.cache = {
            "test_file": {
                "title": "Cached Title",
                "description": "Cached Description",
                "thumbnail": "thumb.jpg"
            }
        }
        
        result = service.autofill_youtube_fields("/path/to/test_file.mp4")
        
        assert result is not None
        assert result["title"] == "Cached Title"
        assert result["description"] == "Cached Description"
        assert result["thumbnail"] == "thumb.jpg"
    
    def test_autofill_nonexistent(self, mock_logger):
        """Test autofill for non-existent key"""
        from services.metadata_service import MetadataService
        
        service = MetadataService(logger=mock_logger)
        result = service.autofill_youtube_fields("/path/to/nonexistent.mp4")
        
        # Should return dict with empty fields, not None
        assert result is not None
        assert isinstance(result, dict)
        assert result["title"] == ""
        assert result["description"] == ""
    
    def test_get_title_from_filename(self, mock_logger):
        """Test extracting title from filename"""
        from services.metadata_service import MetadataService
        
        service = MetadataService(logger=mock_logger)
        
        test_cases = [
            ("Episode 01 - Title.mp4", "Episode 01 - Title"),
            ("Series_S01E02", "Series_S01E02"),  # Keep underscores
            ("simple_filename.mp4", "simple_filename")
        ]
        
        for filename, expected in test_cases:
            result = service.get_title_from_filename(filename)
            assert result == expected

