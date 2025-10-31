# 🧪 Chạy Tests - Piu Application

## ⚡ Nhanh (30 giây)

```bash
# 1. Cài đặt (chỉ lần đầu)
pip install pytest pytest-cov pytest-timeout pytest-mock

# 2. Chạy tests
pytest -v
```

**Done! ✅**

---

## 📖 Chi tiết

### Windows: Chạy Script Tự Động
```bash
setup_tests.bat
```

### Manual: Từng Bước
```bash
# Install dependencies
pip install pytest pytest-cov pytest-timeout pytest-mock

# Run all tests
pytest -v

# Run specific file
pytest tests/integration/test_youtube_service.py -v

# Run with coverage
pytest --cov=services --cov-report=html

# Skip slow tests
pytest -m "not slow"
```

---

## 🆘 Lỗi?

### "pytest not found"
```bash
pip install pytest
```

### "Import error"
```bash
# Đảm bảo ở thư mục root
cd D:\Cong\Code\Piu
pytest
```

---

## 📚 Hướng Dẫn Đầy Đủ

👉 [START_HERE.md](START_HERE.md) - Bắt đầu từ đây!  
👉 [QUICK_START_TESTING.md](.tasks/QUICK_START_TESTING.md) - Hướng dẫn chi tiết  
👉 [tests/README.md](tests/README.md) - Docs kỹ thuật

---

**Need help?** Xem [QUICK_START_TESTING.md](.tasks/QUICK_START_TESTING.md) → FAQ section

