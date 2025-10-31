"""
Pytest configuration and shared fixtures for Piu tests
"""
import pytest
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, MagicMock

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_config():
    """Return a sample config dictionary"""
    return {
        "hardware_id": "TEST_HWID_12345",
        "output_folder": "/tmp/test_output",
        "whisper_model": "base",
        "cuda_enabled": False,
    }


@pytest.fixture
def mock_logger():
    """Return a mock logger"""
    logger = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    return logger


@pytest.fixture
def sample_video_path(temp_dir):
    """Return a sample video file path (mock)"""
    return os.path.join(temp_dir, "sample.mp4")


@pytest.fixture
def sample_audio_path(temp_dir):
    """Return a sample audio file path (mock)"""
    return os.path.join(temp_dir, "sample.wav")


@pytest.fixture
def sample_srt_path(temp_dir):
    """Return a sample SRT file path"""
    srt_path = os.path.join(temp_dir, "sample.srt")
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write("""1
00:00:01,000 --> 00:00:03,000
Hello, world!

2
00:00:04,000 --> 00:00:06,000
This is a test subtitle.
""")
    return srt_path


@pytest.fixture
def mock_openai_client():
    """Return a mock OpenAI client"""
    client = Mock()
    client.chat.completions.create = Mock()
    return client


@pytest.fixture
def mock_gemini_model():
    """Return a mock Gemini model"""
    model = Mock()
    model.generate_content = Mock()
    return model


@pytest.fixture
def mock_whisper_model():
    """Return a mock Whisper model"""
    model = Mock()
    model.transcribe = Mock(return_value={
        "segments": [
            {"start": 0.0, "end": 3.0, "text": "Hello, world!"},
            {"start": 4.0, "end": 6.0, "text": "This is a test."}
        ]
    })
    return model


@pytest.fixture
def mock_youtube_service():
    """Return a mock YouTube service"""
    service = Mock()
    service.queue = []
    service.add_task_to_queue = Mock()
    service.remove_task_from_queue = Mock()
    return service


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

