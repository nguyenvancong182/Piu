# 🚀 Hướng Dẫn Chạy Tests Cho Người Mới Bắt Đầu

Bạn chưa quen với testing? Đừng lo! Đây là hướng dẫn chi tiết từng bước.

---

## 📝 Mục Tiêu Bài Học

Sau khi làm xong, bạn sẽ biết:
- ✅ Cài đặt pytest
- ✅ Chạy tests cơ bản
- ✅ Hiểu kết quả test
- ✅ Viết test đơn giản

---

## BƯỚC 1: Cài Đặt Pytest (5 phút) ⬇️

### 1.1 Mở Terminal/Command Prompt

Trên Windows:
- Nhấn `Win + R`, gõ `cmd`, Enter
- Hoặc mở PowerShell trong Cursor

### 1.2 Điều hướng đến thư mục dự án

```bash
cd D:\Cong\Code\Piu
```

### 1.3 Cài đặt pytest và plugins

```bash
pip install pytest pytest-cov pytest-timeout pytest-mock
```

**Giải thích:**
- `pytest`: Framework testing chính
- `pytest-cov`: Báo cáo coverage (code được test bao nhiêu %)
- `pytest-timeout`: Tự động stop tests chạy lâu
- `pytest-mock`: Tools để mock/fake objects

### 1.4 Verify cài đặt thành công

```bash
pytest --version
```

**Kết quả mong đợi:**
```
pytest 7.x.x
```

Nếu báo lỗi "command not found", check lại bước 1.3.

---

## BƯỚC 2: Chạy Test Đầu Tiên (2 phút) 🏃

### 2.1 Chạy tất cả tests

```bash
pytest
```

**Lần đầu sẽ thấy:**
```
============================= test session starts ==============================
platform win32 -- Python 3.x.x, pytest-7.x.x
collected 12 items

tests/integration/test_services_init.py .....                               [ 41%]
tests/integration/test_youtube_service.py .......                           [100%]

============================= 12 passed in 2.5s ===============================
```

**Giải thích:**
- `12 items`: Có 12 test cases
- `12 passed`: Tất cả đều pass (thành công)
- `2.5s`: Thời gian chạy

### 2.2 Chạy với output chi tiết hơn

```bash
pytest -v
```

**`-v` = verbose** (chi tiết hơn)

Bạn sẽ thấy từng test case:
```
tests/integration/test_services_init.py::TestServicesInit::test_ai_service_init PASSED
tests/integration/test_services_init.py::TestServicesInit::test_image_service_init PASSED
...
```

### 2.3 Chạy một file test cụ thể

```bash
pytest tests/integration/test_services_init.py -v
```

Chỉ chạy tests trong file này.

### 2.4 Chạy một test cụ thể

```bash
pytest tests/integration/test_youtube_service.py::TestYouTubeServiceQueue::test_add_task_to_queue -v
```

Chạy đúng 1 test.

---

## BƯỚC 3: Hiểu Kết Quả Test (5 phút) 📊

### 3.1 Test PASSED ✅

```
test_add_task_to_queue PASSED
```

**Ý nghĩa:** Test chạy thành công, không có lỗi.

### 3.2 Test FAILED ❌

```
test_something FAILED
```

**Xem chi tiết lỗi:**
```
tests/integration/test_youtube_service.py::test_something FAILED

=================================== FAILURES ===================================
test_something ________________
    def test_something(self, mock_logger):
>       assert 1 == 2
E       assert 1 == 2
E       -1
E       +2

tests/integration/test_youtube_service.py:15: AssertionError
```

**Giải thích:**
- Dòng `>       assert 1 == 2`: Dòng code lỗi
- `E       assert 1 == 2`: Lỗi assertion
- `E       -1`: Giá trị hiện tại
- `E       +2`: Giá trị mong đợi
- `AssertionError`: Loại lỗi

### 3.3 Test ERROR ❌

```
test_something ERROR
```

**Khác với FAILED:**
- **FAILED:** Code chạy nhưng kết quả sai
- **ERROR:** Code không chạy được (syntax error, import error, ...)

### 3.4 Test SKIPPED ⏭️

```
test_something SKIPPED
```

**Ý nghĩa:** Test bị bỏ qua (có thể do điều kiện `@pytest.mark.skip`)

---

## BƯỚC 4: Xem Cấu Trúc Test (10 phút) 🔍

### 4.1 Mở file test để xem

Mở file: `tests/integration/test_youtube_service.py`

```python
class TestYouTubeServiceQueue:
    """Test YouTube Service queue management"""
    
    def test_add_task_to_queue(self, mock_logger):
        """Test adding a task to the queue"""
        # Arrange: Chuẩn bị
        from services.youtube_service import YouTubeService
        service = YouTubeService(logger=mock_logger)
        
        # Act: Hành động
        task = service.add_task_to_queue(
            video_path="/path/to/video.mp4",
            title="Test Video"
        )
        
        # Assert: Kiểm tra kết quả
        assert task is not None
        assert task['title'] == "Test Video"
        assert 'id' in task
        assert len(service.queue) == 1
```

### 4.2 Giải thích cấu trúc

**Class:** `TestYouTubeServiceQueue`
- Nhóm các tests liên quan
- Tên bắt đầu bằng `Test`

**Method:** `test_add_task_to_queue`
- Một test case
- Tên bắt đầu bằng `test_`
- Nhận `mock_logger` làm parameter (fixture)

**Docstring:** `"""Test adding a task to the queue"""`
- Mô tả test làm gì

**3 bước chính:**
1. **Arrange:** Chuẩn bị dữ liệu
2. **Act:** Thực hiện hành động
3. **Assert:** Kiểm tra kết quả

### 4.3 Khái niệm Fixture

```python
def test_something(self, mock_logger):  # ← mock_logger là fixture
```

**Fixture = Dữ liệu/test setup được tái sử dụng**

Xem `tests/conftest.py`:

```python
@pytest.fixture
def mock_logger():
    """Return a mock logger"""
    logger = Mock()
    logger.info = Mock()
    logger.error = Mock()
    return logger
```

**Lợi ích:**
- Không phải khởi tạo lại nhiều lần
- Đồng nhất test setup
- Dễ maintain

---

## BƯỚC 5: Viết Test Đầu Tiên (15 phút) ✏️

### 5.1 Tạo file test mới

Tạo file: `tests/integration/test_example.py`

```python
"""
Example tests để học cách viết test
"""

# 1. Import pytest
import pytest


# 2. Tạo class test
class TestBasicMath:
    """Test các phép toán cơ bản"""
    
    # 3. Viết test đầu tiên
    def test_addition(self):
        """Test phép cộng"""
        result = 1 + 1
        assert result == 2
    
    def test_subtraction(self):
        """Test phép trừ"""
        result = 5 - 3
        assert result == 2
    
    def test_multiplication(self):
        """Test phép nhân"""
        result = 3 * 4
        assert result == 12
    
    def test_division(self):
        """Test phép chia"""
        result = 10 / 2
        assert result == 5


# 4. Test với fixture
class TestWithFixtures:
    """Test sử dụng fixtures"""
    
    def test_with_temp_dir(self, temp_dir):
        """Test sử dụng temporary directory"""
        import os
        
        # Tạo file test
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path, 'w') as f:
            f.write("Hello")
        
        # Kiểm tra file tồn tại
        assert os.path.exists(file_path)
        
        # Đọc lại file
        with open(file_path, 'r') as f:
            content = f.read()
        assert content == "Hello"
```

### 5.2 Chạy test mới

```bash
pytest tests/integration/test_example.py -v
```

**Kết quả mong đợi:**
```
test_example.py::TestBasicMath::test_addition PASSED
test_example.py::TestBasicMath::test_subtraction PASSED
test_example.py::TestBasicMath::test_multiplication PASSED
test_example.py::TestBasicMath::test_division PASSED
test_example.py::TestWithFixtures::test_with_temp_dir PASSED
```

---

## BƯỚC 6: Test Service Thực Tế (20 phút) 🎯

### 6.1 Viết test cho MetadataService

Tạo file: `tests/integration/test_metadata_service.py`

```python
"""
Integration tests for Metadata Service
"""
import pytest
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


class TestMetadataService:
    """Test MetadataService functionality"""
    
    def test_load_cache_empty_file(self, mock_logger, temp_dir):
        """Test loading empty cache file"""
        from services.metadata_service import MetadataService
        
        # Tạo file cache rỗng
        cache_file = os.path.join(temp_dir, "cache.json")
        with open(cache_file, 'w') as f:
            f.write("{}")  # JSON rỗng
        
        # Load cache
        service = MetadataService(logger=mock_logger)
        result = service.load_cache(cache_file)
        
        # Assert
        assert result is True
        assert service.cache == {}
    
    def test_get_metadata_nonexistent(self, mock_logger):
        """Test getting metadata for non-existent key"""
        from services.metadata_service import MetadataService
        
        service = MetadataService(logger=mock_logger)
        result = service.get_metadata("nonexistent_key")
        
        assert result is None
    
    def test_update_metadata(self, mock_logger, temp_dir):
        """Test updating metadata"""
        from services.metadata_service import MetadataService
        
        cache_file = os.path.join(temp_dir, "cache.json")
        
        service = MetadataService(logger=mock_logger)
        service.cache_path = cache_file
        
        # Update metadata
        service.update_metadata(
            key="test_key",
            title="Test Title",
            base_thumbnail="/path/to/thumb.jpg"
        )
        
        # Save cache
        service.save_cache()
        
        # Verify file exists
        assert os.path.exists(cache_file)
        
        # Load lại và verify
        service2 = MetadataService(logger=mock_logger)
        service2.load_cache(cache_file)
        metadata = service2.get_metadata("test_key")
        
        assert metadata is not None
        assert metadata['title'] == "Test Title"
        assert metadata['base_thumbnail'] == "/path/to/thumb.jpg"
```

### 6.2 Chạy test

```bash
pytest tests/integration/test_metadata_service.py -v
```

---

## BƯỚC 7: Chạy Coverage Report (10 phút) 📈

### 7.1 Chạy với coverage

```bash
pytest --cov=services --cov-report=html --cov-report=term
```

**Giải thích:**
- `--cov=services`: Coverage cho thư mục services
- `--cov-report=html`: Tạo report HTML
- `--cov-report=term`: Hiển thị report trên terminal

### 7.2 Xem kết quả

**Trên terminal:**
```
Name                     Stmts   Miss  Cover
--------------------------------------------
services/youtube_service.py     95     30    68%
services/ai_service.py          200    80    60%
...
TOTAL                         1000    400    60%
```

**Trong trình duyệt:**
Mở file: `htmlcov/index.html`

Bạn sẽ thấy:
- Code được test (màu xanh)
- Code chưa được test (màu đỏ)
- Số dòng coverage cho từng file

---

## ❓ Câu Hỏi Thường Gặp (FAQ)

### Q: Test thất bại, phải làm sao?

**A:** Đọc error message cẩn thận:
1. Xem dòng code nào lỗi
2. So sánh giá trị thực tế vs mong đợi
3. Sửa code hoặc sửa test

**Ví dụ:**
```
E       assert len(service.queue) == 1
E       +len(service.queue)
E       +0
```

**Giải thích:** Queue đáng lẽ có 1 item nhưng có 0 items.

### Q: Test chạy quá lâu?

**A:** Có thể do:
1. Real API calls (chậm)
2. File I/O
3. Infinite loop (bug)

**Giải pháp:**
- Dùng `mock` thay vì real API
- Check timeout settings
- Debug step-by-step

### Q: Test pass nhưng code sai?

**A:** Có thể:
1. Test không đủ chi tiết
2. Edge cases chưa cover
3. Mock quá đơn giản

**Giải pháp:**
- Thêm nhiều test cases hơn
- Test edge cases
- Thêm assertions chi tiết

### Q: Không biết viết test cho feature nào?

**A:** Bắt đầu với:
1. Happy path (flow bình thường)
2. Error cases (khi input sai)
3. Edge cases (boundary values)
4. Integration points (nhiều component tương tác)

---

## 🎓 Bài Tập Thực Hành

### Exercise 1: Test Cơ Bản
Viết tests cho function:

```python
def calculate_total(items):
    """Calculate total price of items"""
    return sum(item['price'] for item in items)
```

**Gợi ý:**
- Test với empty list
- Test với 1 item
- Test với nhiều items
- Test với giá trị âm (edge case)

### Exercise 2: Test với Exception
Viết test cho function có throw exception:

```python
def divide(a, b):
    """Divide a by b, raise error if b is 0"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```

**Gợi ý:**
```python
def test_divide_by_zero():
    """Test division by zero raises error"""
    with pytest.raises(ValueError):
        divide(10, 0)
```

### Exercise 3: Mock API
Test service gọi external API:

```python
def get_user_data(user_id, api_client):
    """Get user data from API"""
    response = api_client.get(f"/users/{user_id}")
    return response.json()
```

**Gợi ý:**
Dùng `mock` để fake API response

---

## ✅ Checklist Thành Công

Sau khi hoàn thành hướng dẫn, bạn nên:

- [ ] Cài được pytest thành công
- [ ] Chạy được tests hiện có
- [ ] Hiểu kết quả test (PASSED/FAILED/ERROR)
- [ ] Viết được test đơn giản
- [ ] Sử dụng được fixtures
- [ ] Chạy được coverage report
- [ ] Debug được khi test fail

---

## 📚 Tài Liệu Tham Khảo

- **Pytest docs:** https://docs.pytest.org/
- **Python testing:** https://docs.python.org/3/library/unittest.html
- **Test best practices:** https://realpython.com/python-testing/

---

## 🚀 Bước Tiếp Theo

Sau khi thành thạo basic testing:

1. **Phase 2:** Viết integration tests cho services
2. **Phase 3:** Test workflows end-to-end
3. **Phase 4:** Manual validation checklist
4. **Phase 5:** Performance testing

**Xem chi tiết:** [testing_plan.md](./testing_plan.md)

---

**Chúc bạn thành công! 🎉**

**Có thắc mắc?** Đọc lại phần tương ứng hoặc hỏi!

