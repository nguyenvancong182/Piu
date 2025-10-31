# 🚀 Bắt Đầu Testing - Piu Application

**Welcome!** Đây là hướng dẫn nhanh để bắt đầu testing cho dự án Piu.

---

## 🎯 Mục Tiêu

Sau refactoring lớn, chúng ta cần tests để:
- ✅ Đảm bảo không có bugs
- ✅ Confidence khi phát triển tiếp
- ✅ Document cách code hoạt động

---

## ⚡ Quick Start (5 phút)

### Option 1: Chạy Script Tự Động (Khuyên dùng!)

**Windows:**
```bash
setup_tests.bat
```

Script sẽ tự động:
1. Check Python version
2. Install pytest và dependencies
3. Verify installation
4. Chạy tests đầu tiên

### Option 2: Thủ Công

**Bước 1:** Cài đặt
```bash
pip install pytest pytest-cov pytest-timeout pytest-mock
```

**Bước 2:** Verify
```bash
pytest --version
```

**Bước 3:** Chạy tests
```bash
pytest -v
```

---

## 📚 Tài Liệu

### Cho Người Mới Bắt Đầu 👶

**👉 BẮT ĐẦU Ở ĐÂY:** [QUICK_START_TESTING.md](.tasks/QUICK_START_TESTING.md)

Hướng dẫn chi tiết từng bước:
- ✅ Cài đặt pytest
- ✅ Chạy test đầu tiên
- ✅ Hiểu kết quả
- ✅ Viết test đơn giản
- ✅ FAQ và troubleshooting

**Thời gian:** 30-60 phút để thành thạo basic

### Kế Hoạch Testing Chi Tiết 📋

[testing_plan.md](.tasks/testing_plan.md)

5 phases:
1. **Phase 1:** Foundation (✅ 40% done)
2. **Phase 2:** Integration tests
3. **Phase 3:** Regression tests
4. **Phase 4:** Manual validation
5. **Phase 5:** Performance (optional)

### Hướng Dẫn Cho Developers 💻

[tests/README.md](tests/README.md)

Chi tiết kỹ thuật:
- Test structure
- Writing tests
- Using fixtures
- Coverage goals
- Best practices

---

## 🏃 Chạy Tests

### Basic Commands

```bash
# Chạy tất cả tests
pytest

# Chi tiết hơn
pytest -v

# Một file cụ thể
pytest tests/integration/test_youtube_service.py -v

# Một test cụ thể
pytest tests/integration/test_youtube_service.py::TestYouTubeServiceQueue::test_add_task_to_queue -v

# Với coverage
pytest --cov=services --cov-report=html --cov-report=term
```

### Filter by Markers

```bash
# Chỉ integration tests
pytest -m integration

# Bỏ qua slow tests
pytest -m "not slow"

# Bỏ qua API tests (cần API keys)
pytest -m "not requires_api"
```

---

## 📊 Kết Quả Mong Đợi

### Khi Tests PASS ✅

```
tests/integration/test_services_init.py .....               [ 41%]
tests/integration/test_youtube_service.py .......           [100%]

======================== 12 passed in 2.5s =========================
```

**Ý nghĩa:** Mọi thứ hoạt động OK!

### Khi Tests FAIL ❌

```
tests/integration/test_youtube_service.py::test_something FAILED

================================== FAILURES ===================================
...
AssertionError: assert 1 == 2
```

**Action:** Đọc error message, sửa code hoặc test

### Xem Coverage 📈

```bash
pytest --cov=services --cov-report=html
```

Sau đó mở `htmlcov/index.html` trong browser

---

## 🆘 Cần Giúp?

### Common Issues

**1. "Module 'pytest' not found"**
```bash
pip install pytest
```

**2. "Import error: services.xxx"**
```bash
# Đảm bảo đang ở thư mục root của project
cd D:\Cong\Code\Piu
pytest
```

**3. "Tests pass nhưng có warning"**
- Có thể bỏ qua nếu không critical
- Hoặc fix warnings để code clean hơn

### Resources

- **Pytest docs:** https://docs.pytest.org/
- **Python testing:** https://realpython.com/python-testing/
- **Our guide:** [QUICK_START_TESTING.md](.tasks/QUICK_START_TESTING.md)

---

## 🎯 Next Steps

### Cho Newbie 🟢

1. Đọc [QUICK_START_TESTING.md](.tasks/QUICK_START_TESTING.md)
2. Chạy `setup_tests.bat`
3. Chạy `pytest -v`
4. Xem code test để hiểu
5. Viết test đầu tiên

### Cho Advanced Users 🔵

1. Review [testing_plan.md](.tasks/testing_plan.md)
2. Chạy coverage: `pytest --cov=services`
3. Viết integration tests cho services còn lại
4. Proceed to Phase 2

### Cho Contributors 🔴

1. Check [refactor_progress.md](.tasks/refactor_progress.md)
2. Review test coverage gaps
3. Pick tasks từ testing plan
4. Submit PR with tests

---

## 📈 Progress Tracking

### Completed ✅

- ✅ Test infrastructure setup
- ✅ Basic service initialization tests
- ✅ YouTube service comprehensive tests
- ✅ Documentation
- ✅ Quick start guide

### In Progress ⏳

- ⏳ More service tests
- ⏳ Integration tests
- ⏳ End-to-end tests

### TODO 📝

- [ ] Metadata service tests
- [ ] AI service tests
- [ ] Model service tests
- [ ] Critical workflows
- [ ] Manual validation checklist
- [ ] Performance tests

**Track progress:** [testing_plan.md](.tasks/testing_plan.md)

---

## 🏆 Success Metrics

### Current Status

- **Test Files:** 2
- **Test Cases:** 12
- **Coverage:** TBD (chưa run coverage chính thức)
- **Phase:** 1/5 (Foundation)

### Goals

- **Phase 1:** 100% service initialization tests
- **Phase 2:** 80% critical workflows
- **Phase 3:** 70% edge cases
- **Overall:** 60%+ coverage for services

---

## 💡 Tips & Best Practices

### Viết Test Tốt

1. **Tên test rõ ràng:** `test_add_task_to_queue_with_valid_input`
2. **Mỗi test độc lập:** Không phụ thuộc test khác
3. **AAA Pattern:** Arrange → Act → Assert
4. **Test behavior, not implementation**
5. **Mock external dependencies**

### Debugging Tests

1. **Chạy một test:** `pytest path/to/test.py::function -v`
2. **Add print:** `print(variable)` trong test
3. **Use pdb:** `import pdb; pdb.set_trace()`
4. **Check logs:** Xem log output

### Maintain Tests

1. **Chạy tests thường xuyên:** Trước mỗi commit
2. **Fix tests failing:** Đừng skip!
3. **Update khi refactor:** Test phải reflect code mới
4. **Keep tests fast:** < 1s mỗi test

---

## 🎉 Ready to Start!

**Hãy bắt đầu với:**
👉 [QUICK_START_TESTING.md](.tasks/QUICK_START_TESTING.md)

**Chúc bạn thành công! 🚀**

---

**Questions?** Xem FAQ trong QUICK_START_TESTING.md hoặc hỏi team!

