"""
Integration tests for YouTube Service
"""
import pytest
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


class TestYouTubeServiceQueue:
    """Test YouTube Service queue management"""
    
    def test_add_task_to_queue(self, mock_logger):
        """Test adding a task to the queue"""
        from services.youtube_service import YouTubeService
        
        service = YouTubeService(logger=mock_logger)
        task = service.add_task_to_queue(
            video_path="/path/to/video.mp4",
            title="Test Video",
            description="A test video",
            tags_str="test,tag",
            playlist_name="Test Playlist",
            thumbnail_path="/path/to/thumb.jpg",
            privacy_status="public",
            category_id="22"
        )
        
        assert task is not None
        assert task['video_path'] == "/path/to/video.mp4"
        assert task['title'] == "Test Video"
        assert 'id' in task
        assert len(service.queue) == 1
    
    def test_remove_task_from_queue(self, mock_logger):
        """Test removing a task from the queue"""
        from services.youtube_service import YouTubeService
        
        service = YouTubeService(logger=mock_logger)
        task = service.add_task_to_queue(
            video_path="/path/to/video.mp4",
            title="Test Video"
        )
        task_id = task['id']
        
        removed = service.remove_task_from_queue(task_id)
        assert removed is True
        assert len(service.queue) == 0
    
    def test_get_queue(self, mock_logger):
        """Test getting the queue"""
        from services.youtube_service import YouTubeService
        
        service = YouTubeService(logger=mock_logger)
        service.add_task_to_queue(video_path="/path/to/video.mp4", title="Video 1")
        service.add_task_to_queue(video_path="/path/to/video2.mp4", title="Video 2")
        
        queue = service.get_queue()
        assert len(queue) == 2
        assert queue[0]['title'] == "Video 1"
        assert queue[1]['title'] == "Video 2"
    
    def test_title_truncation(self, mock_logger):
        """Test that long titles are truncated"""
        from services.youtube_service import YouTubeService
        
        service = YouTubeService(logger=mock_logger)
        long_title = "A" * 150  # 150 characters
        task = service.add_task_to_queue(
            video_path="/path/to/video.mp4",
            title=long_title
        )
        
        assert len(task['title']) == 100
        mock_logger.warning.assert_called()


class TestYouTubeServiceBatch:
    """Test YouTube Service batch processing"""
    
    def test_start_batch(self, mock_logger):
        """Test starting batch processing"""
        from services.youtube_service import YouTubeService
        
        service = YouTubeService(logger=mock_logger)
        service.add_task_to_queue(video_path="/path/to/video.mp4", title="Video 1")
        first_task_id = service.queue[0]['id']
        
        service.start_batch(first_task_id=first_task_id)
        assert service.is_uploading is True
        assert service.currently_processing_task_id == first_task_id
    
    def test_stop_batch(self, mock_logger):
        """Test stopping batch processing"""
        from services.youtube_service import YouTubeService
        
        service = YouTubeService(logger=mock_logger)
        service.start_batch()
        
        service.stop_batch()
        assert service.is_uploading is False
        assert service.currently_processing_task_id is None
    
    def test_finish_batch(self, mock_logger):
        """Test finishing batch processing"""
        from services.youtube_service import YouTubeService
        
        service = YouTubeService(logger=mock_logger)
        service.start_batch()
        
        service.finish_batch(stopped=False)
        assert service.is_uploading is False
        assert service._batch_finished_once is True
    
    def test_finish_batch_only_once(self, mock_logger):
        """Test that finish_batch can only be called once"""
        from services.youtube_service import YouTubeService
        
        service = YouTubeService(logger=mock_logger)
        service.start_batch()
        
        service.finish_batch()
        service.finish_batch()  # Call again
        
        # Should only finish once
        assert service._batch_finished_once is True

