# Testing Guide - Piu Application

## Overview

Tests for Piu application to ensure stability after refactoring. Focus on integration tests and smoke tests for critical workflows.

## Quick Start

### Install Dependencies

```bash
pip install pytest pytest-cov pytest-timeout pytest-mock
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/integration/test_youtube_service.py

# Run with coverage
pytest --cov=services --cov-report=html
```

### Run by Category

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Skip API tests
pytest -m "not requires_api"
```

## Test Structure

```
tests/
├── __init__.py                 # Package initialization
├── conftest.py                 # Shared fixtures
├── unit/                       # Unit tests (TODO)
│   ├── test_services.py
│   └── test_utils.py
├── integration/                # Integration tests
│   ├── __init__.py
│   ├── test_services_init.py   # Service initialization tests
│   ├── test_youtube_service.py # YouTube service tests
│   └── test_model_service.py   # Model service tests (TODO)
└── e2e/                        # End-to-end tests (TODO)
    └── test_download_flow.py   # Full workflow tests
```

## Writing Tests

### Basic Test Structure

```python
import pytest
from services.youtube_service import YouTubeService


class TestYouTubeService:
    """Test suite for YouTube Service"""
    
    def test_add_task_to_queue(self, mock_logger):
        """Test adding a task to the queue"""
        service = YouTubeService(logger=mock_logger)
        task = service.add_task_to_queue(
            video_path="/path/to/video.mp4",
            title="Test Video"
        )
        
        assert task is not None
        assert task['title'] == "Test Video"
```

### Using Fixtures

```python
def test_with_temp_dir(temp_dir):
    """Test with temporary directory"""
    file_path = os.path.join(temp_dir, "test.txt")
    # Use temp_dir for test files
```

### Mocking Services

```python
def test_with_mock(mock_logger, mock_openai_client):
    """Test with mocked dependencies"""
    from services.ai_service import AIService
    
    service = AIService(logger=mock_logger)
    # Test service logic
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- Test individual components in isolation
- Fast execution
- No external dependencies

### Integration Tests (`@pytest.mark.integration`)
- Test service interactions
- Verify integration with Piu.py
- May use mocks for external APIs

### End-to-End Tests (`@pytest.mark.e2e`)
- Test complete workflows
- Use real dependencies when possible
- Slower execution

### Manual Tests
- Documented in testing plan
- Require manual verification
- UI testing, API testing with real keys

## Coverage Goals

- **Phase 1:** Basic service initialization (100%)
- **Phase 2:** Critical service methods (80%+)
- **Phase 3:** Integration points (70%+)
- **Overall:** 60%+ for services

## Continuous Testing

Run tests frequently:
- Before committing: `pytest -m "not slow"`
- Before PR: `pytest` (all tests)
- Nightly: Full test suite with coverage

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Ensure project root in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Test timeouts:**
```bash
# Increase timeout for slow tests
pytest --timeout=600
```

**Missing dependencies:**
```bash
# Install all test dependencies
pip install -r requirements-test.txt
```

## Contributing

When adding new features:
1. Write tests first (TDD) when possible
2. Keep tests fast and isolated
3. Use fixtures for common setup
4. Document complex test cases
5. Run tests before committing

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Plan](../.tasks/testing_plan.md)
- [Refactor Progress](../.tasks/refactor_progress.md)

